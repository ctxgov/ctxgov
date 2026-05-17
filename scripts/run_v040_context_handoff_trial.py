#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ctxgov.core import CtxVault
from ctxgov.layout import default_layout
from ctxgov.surface import CtxVaultSurface


DEFAULT_ROOT = Path("/tmp/ctxvault-v040-trial")
DEFAULT_SOURCE_PATH = REPO_ROOT / "fixtures" / "v0.3.4-context-extract" / "markdown-vault"
WORKSTREAM_ID = "ws_20260421_ctxvault_schema"
WORKSTREAM_REF = f"workstream://{WORKSTREAM_ID}"
PREPARE_QUERY = "stable one click extraction privacy projection receipts"
PUBLIC_BOUNDARY = {
    "no_account": True,
    "no_llm_key": True,
    "no_cloud_service": True,
    "no_provider_call": True,
    "no_hidden_session_scanning": True,
    "no_runtime_control": True,
}


def run_trial(*, root: Path, source_path: Path, reset: bool = False) -> dict[str, Any]:
    root = root.resolve()
    source_path = source_path.resolve()
    if reset:
        _safe_reset(root)

    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    surface.vault.import_core_fixtures(REPO_ROOT / "fixtures" / "core")

    dry_run = surface.context_extract(
        source_paths=[source_path],
        source_kind="markdown-vault",
        scope_kind="project",
        scope_value="ctxvault",
        recursive=True,
        prepare_query=PREPARE_QUERY,
        workstream_ref=WORKSTREAM_REF,
        project_targets=["workstream-brief"],
        workstream_id=WORKSTREAM_ID,
        dry_run=True,
    )
    run = surface.context_extract(
        source_paths=[source_path],
        source_kind="markdown-vault",
        scope_kind="project",
        scope_value="ctxvault",
        recursive=True,
        prepare_query=PREPARE_QUERY,
        workstream_ref=WORKSTREAM_REF,
        project_targets=["workstream-brief"],
        workstream_id=WORKSTREAM_ID,
    )
    inspection = surface.receipt_inspect(receipt_path=Path(str(run["receipt_path"])))
    doctor = surface.doctor_report()
    doctor_checks = {check["name"]: check for check in doctor["checks"]}
    pass_checks = {
        "dry_run_writes_plan_without_imports": dry_run["status"] == "dry_run" and not dry_run["imports"],
        "local_sources_imported": any(int(item.get("receipt_count") or 0) > 0 for item in run["imports"]),
        "projection_gated_by_handoff_ready": bool(run["prepare"].get("handoff_ready")) and len(run["projections"]) == 1,
        "receipt_chain_inspects": inspection["status"] == "pass" and not inspection["chains"][0]["missing_links"],
        "doctor_extract_checks_pass": doctor_checks["context_extract_receipts"]["status"] == "pass"
        and doctor_checks["projection_selection_receipts"]["status"] == "pass",
    }
    projection_paths = [str(projection.get("output_path")) for projection in run.get("projections") or []]
    status = "pass" if run["status"] == "pass" and all(pass_checks.values()) else "fail"
    receipt_explanation = _receipt_explanation(run=run, inspection=inspection)
    first_run_checklist = _first_run_checklist(
        source_imported=pass_checks["local_sources_imported"],
        selected_count=receipt_explanation["states"]["selected"]["count"],
        projection_paths=projection_paths,
        receipt_path=str(run.get("receipt_path") or ""),
        receipt_chain_ok=pass_checks["receipt_chain_inspects"],
    )
    summary = {
        "schema_id": "ctxvault.v0.4.0-context-handoff-trial/v1",
        "status": status,
        "root": str(root),
        "source_path": str(source_path),
        "source_kind": "markdown-vault",
        "operation": "local_sources_to_reviewed_context_to_receipt_backed_handoff",
        "report_generator": "scripts/run_v040_context_handoff_trial.py",
        "prepare_query": PREPARE_QUERY,
        "workstream_ref": WORKSTREAM_REF,
        "pass_checks": pass_checks,
        "receipt_path": run["receipt_path"],
        "receipt_inspection_status": inspection["status"],
        "receipt_explanation": receipt_explanation,
        "doctor_status": doctor["status"],
        "first_run_checklist": first_run_checklist,
        "what_happened": _what_happened(
            run=run,
            selected_count=receipt_explanation["states"]["selected"]["count"],
            projection_paths=projection_paths,
            receipt_chain_ok=pass_checks["receipt_chain_inspects"],
        ),
        "public_claim_boundary": PUBLIC_BOUNDARY,
        "selected_slice_refs": run["prepare"].get("selected_slice_refs"),
        "projection_output_paths": projection_paths,
        "next_actions": run["next_actions"],
    }
    summary_path = root / "artifacts" / "v0.4.0-context-handoff-trial-summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary["summary_path"] = str(summary_path)
    summary["scorecard_path"] = str(summary_path)
    report_path = root / "artifacts" / "v0.4.0-first-run-report.md"
    summary["trial_report_path"] = str(report_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_render_trial_report(summary), encoding="utf-8")
    return summary


def _safe_reset(root: Path) -> None:
    resolved = root.resolve()
    tmp_root = Path("/tmp").resolve()
    if tmp_root not in resolved.parents or not resolved.name.startswith("ctxvault-"):
        raise ValueError("--reset only accepts ctxvault-* roots under the system temporary directory")
    if resolved.exists():
        shutil.rmtree(resolved)


def _receipt_explanation(*, run: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
    prepare = run.get("prepare") if isinstance(run.get("prepare"), dict) else {}
    selected_refs = [str(item) for item in prepare.get("selected_slice_refs") or []]
    omitted_items = ((prepare.get("context_quality_receipt") or {}).get("omitted_refs_with_reason") or [])
    projections = [item for item in run.get("projections") or [] if isinstance(item, dict)]
    skipped = [item for item in run.get("skipped_projections") or [] if isinstance(item, dict)]
    projection_paths = [str(item.get("output_path")) for item in projections if item.get("output_path")]
    receipt_path = str(run.get("receipt_path") or "")
    return {
        "schema_id": "ctxvault.v0.4.0-receipt-explanation/v1",
        "summary": (
            f"CtxVault imported local source evidence, selected {len(selected_refs)} reviewed context slice"
            f"{'' if len(selected_refs) == 1 else 's'}, wrote {len(projection_paths)} handoff artifact"
            f"{'' if len(projection_paths) == 1 else 's'}, and verified the receipt chain."
        ),
        "states": {
            "selected": {
                "count": len(selected_refs),
                "slice_refs": selected_refs,
                "meaning": "context slices allowed into the handoff after deterministic selection and privacy checks",
            },
            "omitted": {
                "count": len(omitted_items),
                "items": omitted_items,
                "meaning": "candidate context not needed for this handoff or not retained by quality gates",
            },
            "blocked": {
                "count": len(skipped),
                "items": skipped,
                "meaning": "projection attempts that were refused because the handoff was not ready",
            },
            "written": {
                "count": len(projection_paths),
                "paths": projection_paths,
                "receipt_path": receipt_path,
                "meaning": "local files written under the trial root; no external service is contacted",
            },
            "not_done": {
                "items": [
                    "no provider call",
                    "no LLM key lookup",
                    "no cloud upload",
                    "no hidden session scan",
                    "no runtime control over Codex, Claude Code, Cursor, ChatGPT, or other AI tools",
                ],
                "meaning": "release boundary states explicitly not exercised by v0.4.0",
            },
        },
        "receipt_chain_status": inspection.get("status"),
        "receipt_chain_missing_links": ((inspection.get("chains") or [{}])[0] or {}).get("missing_links") or [],
    }


def _first_run_checklist(
    *,
    source_imported: bool,
    selected_count: int,
    projection_paths: list[str],
    receipt_path: str,
    receipt_chain_ok: bool,
) -> list[dict[str, Any]]:
    return [
        _first_run_item(
            "local_sources",
            "Local sources imported",
            source_imported,
            "source evidence is in the local vault" if source_imported else "check the source path and rerun",
        ),
        _first_run_item(
            "reviewed_context",
            "Reviewed context selected",
            selected_count > 0,
            f"{selected_count} selected slice(s)" if selected_count > 0 else "adjust the query or source material",
        ),
        _first_run_item(
            "handoff_written",
            "Handoff artifact written",
            bool(projection_paths),
            ", ".join(projection_paths) if projection_paths else "projection was packet-only or blocked",
        ),
        _first_run_item(
            "receipt_generated",
            "Receipt generated",
            bool(receipt_path),
            receipt_path or "enable receipt writing and rerun",
        ),
        _first_run_item(
            "receipt_chain",
            "Receipt chain verifies",
            receipt_chain_ok,
            "receipt chain has no missing links" if receipt_chain_ok else "inspect receipt missing links",
        ),
    ]


def _first_run_item(check_id: str, label: str, done: bool, detail: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "label": label,
        "status": "done" if done else "todo",
        "detail": detail,
    }


def _what_happened(
    *,
    run: dict[str, Any],
    selected_count: int,
    projection_paths: list[str],
    receipt_chain_ok: bool,
) -> list[dict[str, Any]]:
    import_count = sum(int(item.get("receipt_count") or 0) for item in run.get("imports") or [] if isinstance(item, dict))
    return [
        {
            "phase": "source",
            "status": "done" if import_count else "todo",
            "plain_language": f"Imported {import_count} local source receipt(s) as evidence.",
        },
        {
            "phase": "review",
            "status": "done" if selected_count else "todo",
            "plain_language": f"Selected {selected_count} reviewed context slice(s) for the requested handoff.",
        },
        {
            "phase": "write",
            "status": "done" if projection_paths else "not_written",
            "plain_language": (
                f"Wrote handoff artifact(s): {', '.join(projection_paths)}."
                if projection_paths
                else "No handoff artifact was written; inspect skipped_projections for the gate reason."
            ),
        },
        {
            "phase": "receipt",
            "status": "done" if receipt_chain_ok else "warn",
            "plain_language": (
                "Verified the receipt chain for source, selection, projection, and handoff evidence."
                if receipt_chain_ok
                else "Receipt chain did not fully verify; inspect receipt_chain_missing_links."
            ),
        },
        {
            "phase": "boundary",
            "status": "not_done_by_design",
            "plain_language": "No account, LLM key, cloud service, provider call, hidden session scan, or AI runtime control was used.",
        },
    ]


def _render_trial_report(summary: dict[str, Any]) -> str:
    checklist = "\n".join(
        f"- [{'x' if item.get('status') == 'done' else ' '}] {item.get('label')}: {item.get('detail')}"
        for item in summary.get("first_run_checklist") or []
        if isinstance(item, dict)
    )
    happened = "\n".join(
        f"- {item.get('phase')}: {item.get('plain_language')}"
        for item in summary.get("what_happened") or []
        if isinstance(item, dict)
    )
    receipt = summary.get("receipt_explanation") if isinstance(summary.get("receipt_explanation"), dict) else {}
    states = receipt.get("states") if isinstance(receipt.get("states"), dict) else {}
    state_lines = "\n".join(
        f"- {name}: {state.get('count', len(state.get('items') or [])) if isinstance(state, dict) else 'recorded'}"
        for name, state in states.items()
        if isinstance(state, dict)
    )
    return f"""# CtxVault v0.4.0 First-Run Report

Status: `{summary.get('status')}`

This report is generated locally by `{summary.get('report_generator') or 'scripts/run_v040_context_handoff_trial.py'}`.
It documents what the trial allowed into the AI work handoff and what it did
not do.

## What Happened

{happened or "- No events recorded."}

## First-Run Checklist

{checklist or "- No checklist recorded."}

## Receipt States

{state_lines or "- No receipt states recorded."}

## Paths

- Summary JSON: `{summary.get('summary_path')}`
- Receipt: `{summary.get('receipt_path')}`
- Projection outputs: `{', '.join(summary.get('projection_output_paths') or []) or 'none'}`

## Boundary

- No account
- No LLM key
- No cloud service
- No provider call
- No hidden session scanning
- No runtime control
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the v0.4.0 local context handoff trial: local sources -> reviewed context -> receipt-backed handoff."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Vault/output root for the v0.4.0 trial.")
    parser.add_argument(
        "--source-path",
        type=Path,
        default=DEFAULT_SOURCE_PATH,
        help="Local source path to import for the trial. Defaults to the repo-contained Markdown vault fixture.",
    )
    parser.add_argument("--reset", action="store_true", help="Delete an existing /tmp/ctxvault-* trial root before running.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_trial(root=args.root, source_path=args.source_path, reset=args.reset)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
