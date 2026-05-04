#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from html import escape as html_escape
import json
from pathlib import Path
import shutil
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.surface import CtxVaultSurface


CORPUS_DIR = REPO_ROOT / "fixtures" / "v0.3.3-public-review" / "sources"
SCENARIO_MANIFEST = REPO_ROOT / "fixtures" / "v0.3.3-public-review" / "scenarios.json"
SCOPE = ("project", "ctxvault-public-review")
WORKSTREAM_ID = "ws_v033_public_review"
WORKSTREAM_REF = f"workstream://{WORKSTREAM_ID}"
TARGET_KIND = "harness.agents-md"


def run_review_pack(*, root: Path, force: bool = False) -> dict[str, Any]:
    root = root.resolve()
    _prepare_review_root(root, force=force)
    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    corpus = _load_corpus_sources()
    scenarios = _load_scenarios()
    for source in corpus:
        surface.vault.store_core_object("KnowledgeArtifact", _knowledge_payload(source))
    _store_review_context(surface)

    rebuild = surface.context_slice_rebuild()
    scenario_results = [_run_scenario(surface, scenario) for scenario in scenarios]
    blocked = _run_blocked_scenario(surface)
    projection = _project_first_ready_scenario(root, surface, scenario_results)
    status = "pass" if all(item["status"] == "pass" for item in scenario_results) and blocked["status"] == "pass" and projection["status"] == "pass" else "fail"
    summary = {
        "schema_id": "ctxvault.v0.3.3-public-review-pack/v1",
        "status": status,
        "root": str(root),
        "scope": {"kind": SCOPE[0], "value": SCOPE[1]},
        "corpus": [
            {
                "id": source["id"],
                "title": source["title"],
                "source_ref": f"knowledge://{source['id']}",
                "source_url": source["source_url"],
                "content_sha256": hashlib.sha256(source["body"].encode("utf-8")).hexdigest(),
            }
            for source in corpus
        ],
        "scenario_manifest_path": str(SCENARIO_MANIFEST),
        "scenario_coverage": _scenario_coverage(corpus, scenarios),
        "rebuild": rebuild,
        "scenarios": scenario_results,
        "blocked_selection": blocked,
        "projection": projection,
        "review_instructions": [
            "Inspect selected_source_refs for each scenario before reading expected_source_refs.",
            "Confirm forbidden_source_refs are absent from selected_source_refs.",
            "Inspect projection.output_path and projection.receipt_path.",
            "Approve publication only if the result is understandable without private context.",
        ],
    }
    artifacts_dir = root / "artifacts" / "v0.3.3-public-review"
    summary_path = artifacts_dir / "summary.json"
    summary["summary_path"] = str(summary_path.resolve())
    report_path = artifacts_dir / "owner-review.md"
    html_path = artifacts_dir / "owner-review.html"
    summary["human_review"] = {
        "markdown_path": str(report_path.resolve()),
        "html_path": str(html_path.resolve()),
        "recommended_first_step": "Open owner-review.md or owner-review.html before inspecting raw JSON receipts.",
    }
    _write_json(summary_path, summary)
    report = _render_owner_review_markdown(summary)
    _write_text(report_path, report)
    _write_text(html_path, _render_owner_review_html(summary, report))
    return summary


def _prepare_review_root(root: Path, *, force: bool) -> None:
    if not root.exists():
        return
    if not any(root.iterdir()):
        return
    if not force:
        raise RuntimeError(f"review root already exists and is not empty: {root}; pass --force or choose a new --root")
    allowed_roots = [Path("/tmp").resolve(), REPO_ROOT.resolve() / ".staging"]
    if not any(allowed == root or allowed in root.parents for allowed in allowed_roots):
        allowed = ", ".join(str(path) for path in allowed_roots)
        raise RuntimeError(f"refusing to force-delete review root outside scratch roots ({allowed}): {root}")
    shutil.rmtree(root)


def _load_corpus_sources() -> list[dict[str, str]]:
    sources: list[dict[str, str]] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        metadata = _frontmatter(text)
        source_id = metadata.get("id")
        title = metadata.get("title")
        if not source_id or not title:
            raise ValueError(f"public review source missing id or title: {path}")
        sources.append(
            {
                "id": source_id,
                "title": title,
                "source_url": metadata.get("source_url", ""),
                "body": text,
            }
        )
    return sources


def _load_scenarios() -> list[dict[str, Any]]:
    payload = json.loads(SCENARIO_MANIFEST.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios") if isinstance(payload, dict) else None
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError(f"scenario manifest must contain a non-empty scenarios list: {SCENARIO_MANIFEST}")
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(scenarios, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"scenario {index} must be an object")
        scenario_id = str(item.get("id") or "").strip()
        query = str(item.get("query") or "").strip()
        question = str(item.get("review_question") or "").strip()
        if not scenario_id or not query or not question:
            raise ValueError(f"scenario {index} requires id, query, and review_question")
        if scenario_id in seen_ids:
            raise ValueError(f"duplicate scenario id: {scenario_id}")
        seen_ids.add(scenario_id)
        behavior = str(item.get("expected_behavior") or "ready")
        if behavior not in {"ready", "empty", "over_budget"}:
            raise ValueError(f"unsupported expected_behavior for {scenario_id}: {behavior}")
        normalized.append(
            {
                **item,
                "id": scenario_id,
                "query": query,
                "review_question": question,
                "expected_behavior": behavior,
                "expected_source_refs": _string_list(item.get("expected_source_refs")),
                "forbidden_source_refs": _string_list(item.get("forbidden_source_refs")),
                "tags": _string_list(item.get("tags")),
                "risk_axes": _string_list(item.get("risk_axes")),
                "data_shape": str(item.get("data_shape") or "unspecified"),
                "token_budget": int(item.get("token_budget") or 420),
            }
        )
    return normalized


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    _, _, rest = text.partition("---\n")
    block, _, _ = rest.partition("---\n")
    metadata: dict[str, str] = {}
    for line in block.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            metadata[key.strip()] = value.strip()
    return metadata


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _knowledge_payload(source: dict[str, str]) -> dict[str, Any]:
    sensitivity = "restricted" if source["id"] == "public_review_synthetic_secret_blocker" else "public"
    exportable = source["id"] != "public_review_synthetic_secret_blocker"
    return {
        "id": source["id"],
        "kind": "public_review_note",
        "title": source["title"],
        "scope": {"kind": SCOPE[0], "value": SCOPE[1]},
        "body": source["body"],
        "source_refs": [source["source_url"]],
        "derived_from": [],
        "status": "active",
        "sensitivity": sensitivity,
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": exportable,
        "created_at": "2026-05-04T00:00:00Z",
        "updated_at": "2026-05-04T00:00:00Z",
    }


def _store_review_context(surface: CtxVaultSurface) -> None:
    surface.vault.store_core_object(
        "Memory",
        {
            "id": "mem_v033_public_review_rule_001",
            "type": "workflow_pattern",
            "scope": {"kind": SCOPE[0], "value": SCOPE[1]},
            "status": "active",
            "approval_state": "approved",
            "statement": "The v0.3.3 public review output must be understandable without private project context.",
            "source_refs": ["fixtures/v0.3.3-public-review/README.md"],
            "confidence": 0.98,
            "valid_from": "2026-05-04T00:00:00Z",
            "valid_to": None,
            "supersedes": [],
            "retracts": [],
            "retrieval_policy": {"pinned": True, "priority": 1.0, "decay": "low"},
            "sensitivity": "public",
            "redaction_state": "none",
            "secret_refs": [],
            "exportable": True,
            "created_at": "2026-05-04T00:00:00Z",
            "updated_at": "2026-05-04T00:00:00Z",
        },
    )
    surface.vault.store_core_object(
        "Workstream",
        {
            "id": WORKSTREAM_ID,
            "scope": {"kind": SCOPE[0], "value": SCOPE[1]},
            "title": "CtxVault v0.3.3 public package review",
            "summary": "Owner-operated review path for verifying safe context handoff, privacy preflight, and receipt evidence before publication.",
            "status": "active",
            "approval_state": "approved",
            "source_refs": ["repo://fixtures/v0.3.3-public-review/README.md"],
            "session_refs": [],
            "episode_refs": [],
            "knowledge_refs": [],
            "derived_from": [],
            "recurring_terms": ["safe handoff", "privacy", "receipts", "public review"],
            "task_labels": ["Review v0.3.3 public package"],
            "episode_kind_counts": {},
            "notes": "Synthetic public review workstream used only for deterministic owner package review.",
            "sensitivity": "public",
            "redaction_state": "none",
            "secret_refs": [],
            "exportable": True,
            "created_at": "2026-05-04T00:00:00Z",
            "updated_at": "2026-05-04T00:00:00Z",
        },
    )


def _run_scenario(surface: CtxVaultSurface, scenario: dict[str, Any]) -> dict[str, Any]:
    prepared = surface.context_prepare(
        str(scenario["query"]),
        target_kind=TARGET_KIND,
        scope_kind=SCOPE[0],
        scope_value=SCOPE[1],
        workstream_ref=None,
        limit=8,
        token_budget=int(scenario["token_budget"]),
        rebuild=False,
        write_receipt=True,
    )
    selected_source_refs = _selected_source_refs(prepared)
    expected = list(scenario["expected_source_refs"])
    forbidden = list(scenario["forbidden_source_refs"])
    matched_expected = [ref for ref in expected if ref in selected_source_refs]
    matched_forbidden = [ref for ref in forbidden if ref in selected_source_refs]
    behavior = str(scenario["expected_behavior"])
    pass_checks = _scenario_pass_checks(
        behavior=behavior,
        prepared=prepared,
        expected=expected,
        matched_expected=matched_expected,
        matched_forbidden=matched_forbidden,
    )
    scenario_status = "pass" if all(pass_checks.values()) else "fail"
    return {
        "id": scenario["id"],
        "review_question": scenario["review_question"],
        "expected_behavior": behavior,
        "data_shape": scenario["data_shape"],
        "risk_axes": scenario["risk_axes"],
        "tags": scenario["tags"],
        "query": scenario["query"],
        "status": scenario_status,
        "pass_checks": pass_checks,
        "pass_reason": _scenario_pass_reason(behavior, pass_checks, matched_expected, matched_forbidden),
        "candidate_count": prepared["candidate_count"],
        "selection_status": prepared["selection_status"],
        "handoff_ready": prepared["handoff_ready"],
        "budget_status": prepared["budget_status"],
        "privacy_decision": prepared["privacy_decision"],
        "selected_slice_refs": prepared["selected_slice_refs"],
        "selected_source_refs": selected_source_refs,
        "expected_source_refs": expected,
        "matched_expected_source_refs": matched_expected,
        "forbidden_source_refs": forbidden,
        "matched_forbidden_source_refs": matched_forbidden,
        "warnings": prepared["warnings"],
        "receipt_path": prepared["receipt_path"],
    }


def _scenario_pass_checks(
    *,
    behavior: str,
    prepared: dict[str, Any],
    expected: list[str],
    matched_expected: list[str],
    matched_forbidden: list[str],
) -> dict[str, bool]:
    receipt_written = bool(prepared["receipt_path"]) and Path(str(prepared["receipt_path"])).exists()
    warning_codes = {
        str(item.get("code") or "")
        for item in prepared.get("warnings", [])
        if isinstance(item, dict)
    }
    if behavior == "ready":
        return {
            "handoff_ready": bool(prepared["handoff_ready"]),
            "budget_within_limit": prepared["budget_status"] == "within_budget",
            "privacy_allowed": prepared["privacy_decision"] == "allow",
            "expected_sources_present": len(matched_expected) == len(expected),
            "forbidden_sources_absent": not matched_forbidden,
            "selection_receipt_written": receipt_written,
            "selected_slice_count_nonzero": bool(prepared["selected_slice_refs"]),
        }
    if behavior == "empty":
        return {
            "no_candidate_slices": int(prepared["candidate_count"]) == 0,
            "no_selected_slices": not prepared["selected_slice_refs"],
            "selection_status_empty": prepared["selection_status"] == "empty",
            "handoff_not_ready": not bool(prepared["handoff_ready"]),
            "no_candidate_warning_present": "no_candidate_slices" in warning_codes,
            "selection_receipt_written": receipt_written,
        }
    if behavior == "over_budget":
        return {
            "expected_sources_present": len(matched_expected) == len(expected),
            "forbidden_sources_absent": not matched_forbidden,
            "budget_status_over_budget": prepared["budget_status"] == "over_budget",
            "selection_status_over_budget": prepared["selection_status"] == "over_budget",
            "handoff_not_ready": not bool(prepared["handoff_ready"]),
            "privacy_allowed": prepared["privacy_decision"] == "allow",
            "over_budget_warning_present": "over_budget" in warning_codes,
            "selection_receipt_written": receipt_written,
        }
    raise ValueError(f"unsupported expected behavior: {behavior}")


def _selected_source_refs(prepared: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    selection = prepared.get("selection") if isinstance(prepared.get("selection"), dict) else {}
    for item in selection.get("selected_slices") or []:
        source_ref = str(item.get("source_ref") or "")
        if source_ref and source_ref not in refs:
            refs.append(source_ref)
    return refs


def _run_blocked_scenario(surface: CtxVaultSurface) -> dict[str, Any]:
    hits = surface.context_search(
        "",
        scope_kind=SCOPE[0],
        scope_value=SCOPE[1],
        include_blocked=True,
        limit=100,
    )
    blocker = next(
        hit
        for hit in hits
        if hit["payload"]["source_ref"] == "knowledge://public_review_synthetic_secret_blocker"
        and hit["payload"]["privacy_class"] == "withheld"
    )
    preflight = surface.context_selection_preflight(
        [blocker["slice_ref"]],
        target_kind=TARGET_KIND,
        query="synthetic blocked credential secret",
        write_receipt=True,
    )
    receipt = preflight["receipt"]
    pass_checks = {
        "withheld_slice_found": True,
        "preflight_decision_block": receipt["decision"] == "block",
        "write_not_allowed": not receipt["projection_gate"]["allowed_to_write"],
        "withheld_reason_present": "selection includes withheld slices" in receipt["reasons"],
        "receipt_written": bool(preflight["receipt_path"]) and Path(str(preflight["receipt_path"])).exists(),
    }
    return {
        "id": "synthetic-secret-blocker",
        "status": "pass" if all(pass_checks.values()) else "fail",
        "pass_checks": pass_checks,
        "pass_reason": "The explicit withheld slice selection produced a block decision, denied writes, and wrote a preflight receipt.",
        "selected_slice_ref": blocker["slice_ref"],
        "decision": receipt["decision"],
        "reasons": receipt["reasons"],
        "allowed_to_write": receipt["projection_gate"]["allowed_to_write"],
        "receipt_path": preflight["receipt_path"],
    }


def _project_first_ready_scenario(root: Path, surface: CtxVaultSurface, scenario_results: list[dict[str, Any]]) -> dict[str, Any]:
    ready = next((item for item in scenario_results if item["status"] == "pass"), None)
    if ready is None:
        return {"status": "fail", "error": "no passing scenario available for projection"}
    output_path = root / "artifacts" / "v0.3.3-public-review" / "projection.md"
    receipt_path = root / "artifacts" / "v0.3.3-public-review" / "projection-receipt.json"
    projected = surface.context_project(
        target="workstream-brief",
        workstream_id=WORKSTREAM_ID,
        output_path=output_path,
        receipt_output_path=receipt_path,
        selected_slice_refs=ready["selected_slice_refs"],
    )
    receipt = projected["projection"]["receipt"]
    output_exists = Path(projected["output_path"]).exists()
    receipt_exists = Path(projected["receipt_path"]).exists()
    selected_refs_match = list(receipt.get("selected_slice_refs") or []) == list(projected["selected_slice_refs"])
    pass_checks = {
        "projection_output_written": output_exists,
        "projection_receipt_written": receipt_exists,
        "privacy_allowed": projected["privacy_decision"] == "allow",
        "selected_slice_refs_match_receipt": selected_refs_match,
        "context_selection_ref_present": bool(projected["context_selection_ref"]),
    }
    return {
        "status": "pass" if all(pass_checks.values()) else "fail",
        "pass_checks": pass_checks,
        "pass_reason": "Projection wrote both artifact and receipt, privacy allowed the selected slices, and receipt slice refs match the projection summary.",
        "source_scenario_id": ready["id"],
        "output_path": projected["output_path"],
        "receipt_path": projected["receipt_path"],
        "target_kind": projected["target_kind"],
        "selected_slice_refs": projected["selected_slice_refs"],
        "context_selection_ref": projected["context_selection_ref"],
        "privacy_decision": projected["privacy_decision"],
        "output_sha256": receipt["output_sha256"],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(content.rstrip() + "\n", encoding="utf-8")


def _scenario_pass_reason(
    behavior: str,
    pass_checks: dict[str, bool],
    matched_expected: list[str],
    matched_forbidden: list[str],
) -> str:
    if all(pass_checks.values()):
        if behavior == "empty":
            return (
                "The no-match query returned zero candidates, selected no slices, reported an empty selection, "
                "and still wrote a selection receipt for auditability."
            )
        if behavior == "over_budget":
            expected = ", ".join(f"`{ref}`" for ref in matched_expected)
            return (
                f"The package selected the expected source {expected}, kept privacy allowed, "
                "and surfaced an over-budget warning instead of marking the handoff ready."
            )
        expected = ", ".join(f"`{ref}`" for ref in matched_expected)
        return (
            "The prepared handoff was ready, within budget, privacy-allowed, "
            f"matched expected sources {expected}, selected no forbidden sources, and wrote a selection receipt."
        )
    failed = [key for key, ok in pass_checks.items() if not ok]
    return f"Failed checks: {failed}; matched_expected={matched_expected}; matched_forbidden={matched_forbidden}."


def _render_owner_review_markdown(summary: dict[str, Any]) -> str:
    status = str(summary["status"]).upper()
    ready_label = "READY FOR OWNER REVIEW" if summary["status"] == "pass" else "BLOCKED"
    corpus_titles = _source_titles(summary)
    lines = [
        "# CtxVault v0.3.3 Owner Review",
        "",
        f"Status: **{status} - {ready_label}**",
        "",
        "This report is a human review entry point. It is not an automatic publication approval.",
        "",
        "## Owner Decision",
        "",
        "- Approve publication only if the selected sources, blocked-source behavior, and projection preview below make sense without private context.",
        "- Hold publication if any expected source is missing, any forbidden source is selected, the synthetic secret is allowed to write, or the projection is hard to understand.",
        "",
        "## Quick Verdict",
        "",
        f"- Scenarios passing: {_pass_count(summary['scenarios'])}/{len(summary['scenarios'])}",
        f"- Sources in reusable suite: {len(summary['corpus'])}",
        f"- Scenario behaviors: {_format_counter(summary['scenario_coverage']['expected_behaviors'])}",
        f"- Synthetic secret blocker: {_status_label(summary['blocked_selection']['status'])}",
        f"- Projection: {_status_label(summary['projection']['status'])}",
        f"- Privacy decision for projection: `{summary['projection'].get('privacy_decision')}`",
        f"- Projection hash: `{summary['projection'].get('output_sha256')}`",
        "",
        "Why this is PASS:",
        "",
        "- Ready scenarios have explicit selected-source expectations and explicit forbidden-source checks.",
        "- Ready scenarios produced a handoff-ready result, stayed within token budget, received privacy `allow`, and wrote a selection receipt.",
        "- Boundary scenarios cover no-match and over-budget behavior without pretending those are publication-ready handoffs.",
        "- The synthetic secret fixture was explicitly selected once and correctly blocked projection writes.",
        "- The projection wrote both the human artifact and receipt, and the receipt selected slice refs match the projection summary.",
        "",
        "What this does not prove:",
        "",
        "- It is not a broad retrieval-quality benchmark over arbitrary user documents.",
        "- It does not prove model, embedding, vector, remote provider, official connector, or Workbench behavior.",
        "- It uses deterministic fixture anchors so release-package behavior is stable and auditable; natural-language retrieval quality belongs in a separate scorecard.",
        "",
        "## Scenario Coverage",
        "",
        f"- Data shapes: {_format_counter(summary['scenario_coverage']['data_shapes'])}",
        f"- Risk axes: {_format_counter(summary['scenario_coverage']['risk_axes'])}",
        f"- Tags: {_format_counter(summary['scenario_coverage']['tags'])}",
        "",
        "## What Was Selected",
        "",
        "| Scenario | Behavior | Review Question | Deterministic Query | Selected Sources | Gate Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in summary["scenarios"]:
        selected = _format_source_refs(scenario["selected_source_refs"], corpus_titles)
        gate = _scenario_gate_label(scenario)
        lines.append(
            f"| `{scenario['id']}` | `{scenario['expected_behavior']}` | {scenario['review_question']} | `{scenario['query']}` | {selected} | {gate} |"
        )

    lines.extend(
        [
            "",
            "## Why Each Scenario Passed",
            "",
        ]
    )
    for scenario in summary["scenarios"]:
        lines.extend(
            [
                f"### `{scenario['id']}`",
                "",
                scenario["pass_reason"],
                "",
                "| Check | Result |",
                "| --- | --- |",
            ]
        )
        for key, value in scenario["pass_checks"].items():
            lines.append(f"| `{key}` | {_status_label('pass' if value else 'fail')} |")
        lines.append("")

    lines.extend(
        [
            "## Safety Checks",
            "",
            "| Check | Result | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for scenario in summary["scenarios"]:
        missing = [ref for ref in scenario["expected_source_refs"] if ref not in scenario["matched_expected_source_refs"]]
        forbidden = scenario["matched_forbidden_source_refs"]
        evidence = "expected present; forbidden absent" if not missing and not forbidden else f"missing={missing}; forbidden={forbidden}"
        lines.append(f"| `{scenario['id']}` | {_status_label(scenario['status'])} | {evidence} |")
    blocked = summary["blocked_selection"]
    blocked_evidence = f"decision=`{blocked['decision']}`, allowed_to_write=`{str(blocked['allowed_to_write']).lower()}`"
    lines.append(f"| synthetic secret explicit selection | {_status_label(blocked['status'])} | {blocked_evidence} |")
    lines.append("")
    lines.append("Synthetic secret blocker reason:")
    lines.append("")
    lines.append(f"- {blocked['pass_reason']}")

    lines.extend(
        [
            "",
            "Projection reason:",
            "",
            f"- {summary['projection']['pass_reason']}",
        ]
    )

    lines.extend(
        [
            "",
            "## Projection Preview",
            "",
            f"- Projection path: `{summary['projection']['output_path']}`",
            f"- Projection receipt: `{summary['projection']['receipt_path']}`",
            f"- Source scenario: `{summary['projection']['source_scenario_id']}`",
            "",
            "Selected slice refs:",
        ]
    )
    for ref in summary["projection"]["selected_slice_refs"]:
        lines.append(f"- `{ref}`")

    lines.extend(
        [
            "",
            "## Evidence Files",
            "",
            f"- Human Markdown report: `{summary['human_review']['markdown_path']}`",
            f"- Human HTML report: `{summary['human_review']['html_path']}`",
            f"- Machine summary: `{summary['summary_path']}`",
            f"- Projection: `{summary['projection']['output_path']}`",
            f"- Projection receipt: `{summary['projection']['receipt_path']}`",
            "",
            "## Approval Checklist",
            "",
            "- [ ] I inspected the selected sources before relying on expected-source checks.",
            "- [ ] Every expected source is present for each scenario.",
            "- [ ] No forbidden source appears in selected sources.",
            "- [ ] The synthetic secret blocker returns `decision=block` and `allowed_to_write=false`.",
            "- [ ] The projection is understandable without private project context.",
            "- [ ] The projection receipt selected slice refs match the projection summary.",
            "- [ ] I understand this is a deterministic package review, not a broad retrieval-quality benchmark.",
            "",
            "## Public Corpus",
            "",
            "| Source | URL | Content SHA-256 |",
            "| --- | --- | --- |",
        ]
    )
    for source in summary["corpus"]:
        lines.append(
            f"| {source['title']} | {source['source_url']} | `{source['content_sha256']}` |"
        )
    return "\n".join(lines)


def _render_owner_review_html(summary: dict[str, Any], markdown_report: str) -> str:
    status_class = "pass" if summary["status"] == "pass" else "fail"
    scenario_rows = "\n".join(
        "<tr>"
        f"<td><code>{html_escape(str(scenario['id']))}</code></td>"
        f"<td><code>{html_escape(str(scenario['expected_behavior']))}</code></td>"
        f"<td>{html_escape(str(scenario['review_question']))}</td>"
        f"<td><code>{html_escape(str(scenario['query']))}</code></td>"
        f"<td>{html_escape(', '.join(scenario['selected_source_refs']))}</td>"
        f"<td class=\"{html_escape(str(scenario['status']))}\">{html_escape(str(scenario['status']).upper())}</td>"
        "</tr>"
        for scenario in summary["scenarios"]
    )
    checklist = "".join(
        f"<li>{html_escape(item)}</li>"
        for item in [
            "Review selected sources before expected-source checks.",
            "Confirm ready scenarios are handoff-ready and boundary scenarios fail closed in the expected way.",
            "Confirm forbidden sources are absent.",
            "Confirm synthetic secret selection is blocked.",
            "Read the projection as a first-time reviewer.",
            "Open the projection receipt if any selected slice looks surprising.",
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CtxVault v0.3.3 Owner Review</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #1f2933; background: #fafafa; }}
    main {{ max-width: 1080px; margin: 0 auto; background: #fff; border: 1px solid #d8dee4; border-radius: 8px; padding: 28px; }}
    h1, h2 {{ margin-top: 0; }}
    .banner {{ border-radius: 8px; padding: 16px; margin: 16px 0 24px; border: 1px solid #b8d8be; background: #edf8ef; }}
    .banner.fail {{ border-color: #f0b4ae; background: #fff1f0; }}
    .pass {{ color: #176b35; font-weight: 700; }}
    .fail {{ color: #b42318; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0 24px; }}
    th, td {{ border: 1px solid #d8dee4; padding: 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f4f6f8; }}
    code {{ background: #f4f6f8; padding: 1px 4px; border-radius: 4px; }}
    pre {{ white-space: pre-wrap; background: #f4f6f8; padding: 16px; border-radius: 8px; overflow: auto; }}
    ul {{ line-height: 1.6; }}
  </style>
</head>
<body>
<main>
  <h1>CtxVault v0.3.3 Owner Review</h1>
  <div class="banner {status_class}">
    <strong>Status:</strong> {html_escape(str(summary['status']).upper())}. This is ready for owner review, not automatic publication approval.
  </div>
  <h2>Decision Checklist</h2>
  <ul>{checklist}</ul>
  <h2>Why This Is PASS</h2>
  <ul>
    <li>Ready scenarios matched expected source refs, selected no forbidden refs, were handoff-ready, and wrote receipts.</li>
    <li>Boundary scenarios covered no-match and over-budget behavior without marking those handoffs ready.</li>
    <li>The synthetic secret blocker produced a block decision and denied writes when explicitly selected.</li>
    <li>The projection wrote both artifact and receipt, with selected slice refs matching the receipt.</li>
  </ul>
  <h2>What This Does Not Prove</h2>
  <ul>
    <li>It is not a broad retrieval-quality benchmark over arbitrary user documents.</li>
    <li>It does not prove model, embedding, vector, remote provider, connector, or Workbench behavior.</li>
    <li>It uses deterministic fixture anchors so package review remains stable and auditable.</li>
  </ul>
  <h2>Scenario Coverage</h2>
  <p>Data shapes: {html_escape(_format_counter(summary['scenario_coverage']['data_shapes']))}</p>
  <p>Risk axes: {html_escape(_format_counter(summary['scenario_coverage']['risk_axes']))}</p>
  <p>Tags: {html_escape(_format_counter(summary['scenario_coverage']['tags']))}</p>
  <h2>Scenario Results</h2>
  <table>
    <thead><tr><th>Scenario</th><th>Behavior</th><th>Review question</th><th>Deterministic query</th><th>Selected sources</th><th>Status</th></tr></thead>
    <tbody>{scenario_rows}</tbody>
  </table>
  <h2>Blocked Selection</h2>
  <p>Decision: <code>{html_escape(str(summary['blocked_selection']['decision']))}</code>;
  allowed_to_write: <code>{html_escape(str(summary['blocked_selection']['allowed_to_write']).lower())}</code>.</p>
  <h2>Projection</h2>
  <p>Projection: <code>{html_escape(str(summary['projection']['output_path']))}</code></p>
  <p>Receipt: <code>{html_escape(str(summary['projection']['receipt_path']))}</code></p>
  <h2>Markdown Report</h2>
  <pre>{html_escape(markdown_report)}</pre>
</main>
</body>
</html>"""


def _pass_count(items: list[dict[str, Any]]) -> int:
    return sum(1 for item in items if item.get("status") == "pass")


def _status_label(status: str) -> str:
    return "**PASS**" if status == "pass" else "**FAIL**"


def _scenario_gate_label(scenario: dict[str, Any]) -> str:
    behavior = str(scenario.get("expected_behavior") or "ready")
    if behavior == "empty":
        if scenario["status"] == "pass":
            return "PASS: no candidates; empty warning present"
        return "FAIL: expected empty selection boundary"
    if behavior == "over_budget":
        if scenario["status"] == "pass":
            return "PASS: over-budget warning; handoff not ready"
        return "FAIL: expected over-budget boundary"
    missing = [ref for ref in scenario["expected_source_refs"] if ref not in scenario["matched_expected_source_refs"]]
    forbidden = scenario["matched_forbidden_source_refs"]
    if scenario["status"] == "pass" and not missing and not forbidden:
        return "PASS: expected present; forbidden absent"
    return f"FAIL: missing={missing}; forbidden={forbidden}"


def _source_titles(summary: dict[str, Any]) -> dict[str, str]:
    return {str(source["source_ref"]): str(source["title"]) for source in summary["corpus"]}


def _format_source_refs(source_refs: list[str], titles: dict[str, str]) -> str:
    if not source_refs:
        return "(none)"
    return "<br>".join(f"`{ref}` ({titles.get(ref, 'unknown source')})" for ref in source_refs)


def _scenario_coverage(corpus: list[dict[str, str]], scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "source_count": len(corpus),
        "scenario_count": len(scenarios),
        "expected_behaviors": dict(Counter(str(item["expected_behavior"]) for item in scenarios)),
        "data_shapes": dict(Counter(str(item["data_shape"]) for item in scenarios)),
        "risk_axes": dict(Counter(axis for item in scenarios for axis in item["risk_axes"])),
        "tags": dict(Counter(tag for item in scenarios for tag in item["tags"])),
    }


def _format_counter(counter: dict[str, int]) -> str:
    if not counter:
        return "(none)"
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the v0.3.3 owner-operated public review pack.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/tmp/ctxvault-v033-public-review"),
        help="Vault/output root for generated review artifacts.",
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing scratch review root.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_review_pack(root=args.root, force=bool(args.force))
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
