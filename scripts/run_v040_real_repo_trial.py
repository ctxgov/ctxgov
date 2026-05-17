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
SCRIPT_ROOT = REPO_ROOT / "scripts"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from ctxgov.core import CtxVault
from ctxgov.layout import default_layout
from ctxgov.surface import CtxVaultSurface
from run_v040_context_handoff_trial import (
    PUBLIC_BOUNDARY,
    _first_run_checklist,
    _receipt_explanation,
    _render_trial_report,
    _safe_reset,
    _what_happened,
)


DEFAULT_ROOT = Path("/tmp/ctxvault-v040-real-repo-trial")
WORKSTREAM_ID = "ws_20260421_ctxvault_schema"
WORKSTREAM_REF = f"workstream://{WORKSTREAM_ID}"
DEFAULT_QUERY = "project purpose install usage architecture contribution trust boundaries"
DEFAULT_TARGET = "workstream-brief"
PREFERRED_FILES = [
    "README.md",
    "README.markdown",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "docs/README.md",
    "docs/index.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "module.yaml",
]
SKIP_DIR_NAMES = {
    ".ctxvault",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".toml", ".json", ".yaml", ".yml"}


def run_real_repo_trial(
    *,
    repo: Path,
    root: Path,
    reset: bool = False,
    max_files: int = 12,
    max_bytes_per_file: int = 6000,
    prepare_query: str = DEFAULT_QUERY,
    target: str = DEFAULT_TARGET,
) -> dict[str, Any]:
    repo = repo.resolve()
    root = root.resolve()
    if reset:
        _safe_reset(root)
    if not repo.exists() or not repo.is_dir():
        raise FileNotFoundError(f"repo path must be an existing directory: {repo}")

    packet_dir = root / "sources" / "real-repo-trial"
    packet = build_repo_source_packet(
        repo=repo,
        packet_dir=packet_dir,
        max_files=max_files,
        max_bytes_per_file=max_bytes_per_file,
    )

    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    surface.vault.import_core_fixtures(REPO_ROOT / "fixtures" / "core")

    dry_run = surface.context_extract(
        source_paths=[packet_dir],
        source_kind="markdown-vault",
        scope_kind="project",
        scope_value=repo.name,
        recursive=True,
        prepare_query=prepare_query,
        workstream_ref=WORKSTREAM_REF,
        project_targets=[target],
        workstream_id=WORKSTREAM_ID,
        dry_run=True,
    )
    run = surface.context_extract(
        source_paths=[packet_dir],
        source_kind="markdown-vault",
        scope_kind="project",
        scope_value=repo.name,
        recursive=True,
        prepare_query=prepare_query,
        workstream_ref=WORKSTREAM_REF,
        project_targets=[target],
        workstream_id=WORKSTREAM_ID,
    )
    inspection = surface.receipt_inspect(receipt_path=Path(str(run["receipt_path"])))
    doctor = surface.doctor_report()
    doctor_checks = {check["name"]: check for check in doctor["checks"]}
    projection_paths = [str(projection.get("output_path")) for projection in run.get("projections") or []]
    receipt_explanation = _receipt_explanation(run=run, inspection=inspection)
    pass_checks = {
        "repo_source_packet_written": bool(packet["source_packet_paths"]),
        "dry_run_writes_plan_without_imports": dry_run["status"] == "dry_run" and not dry_run["imports"],
        "local_sources_imported": any(int(item.get("receipt_count") or 0) > 0 for item in run["imports"]),
        "projection_gated_by_handoff_ready": bool(run["prepare"].get("handoff_ready")) and len(run["projections"]) == 1,
        "receipt_chain_inspects": inspection["status"] == "pass" and not inspection["chains"][0]["missing_links"],
        "doctor_extract_checks_pass": doctor_checks["context_extract_receipts"]["status"] == "pass"
        and doctor_checks["projection_selection_receipts"]["status"] == "pass",
    }
    summary = {
        "schema_id": "ctxvault.v0.4.0-real-repo-trial/v1",
        "status": "pass" if run["status"] == "pass" and all(pass_checks.values()) else "fail",
        "root": str(root),
        "repo_path": str(repo),
        "repo_name": repo.name,
        "operation": "real_repo_sources_to_reviewed_context_to_receipt_backed_handoff",
        "report_generator": "scripts/run_v040_real_repo_trial.py",
        "prepare_query": prepare_query,
        "target": target,
        "source_packet": packet,
        "pass_checks": pass_checks,
        "receipt_path": run["receipt_path"],
        "receipt_inspection_status": inspection["status"],
        "receipt_explanation": receipt_explanation,
        "doctor_status": doctor["status"],
        "first_run_checklist": _first_run_checklist(
            source_imported=pass_checks["local_sources_imported"],
            selected_count=receipt_explanation["states"]["selected"]["count"],
            projection_paths=projection_paths,
            receipt_path=str(run.get("receipt_path") or ""),
            receipt_chain_ok=pass_checks["receipt_chain_inspects"],
        ),
        "what_happened": _what_happened(
            run=run,
            selected_count=receipt_explanation["states"]["selected"]["count"],
            projection_paths=projection_paths,
            receipt_chain_ok=pass_checks["receipt_chain_inspects"],
        ),
        "public_claim_boundary": PUBLIC_BOUNDARY,
        "selected_slice_refs": run["prepare"].get("selected_slice_refs"),
        "projection_output_paths": projection_paths,
        "next_actions": [
            {
                "kind": "inspect_trial_report",
                "description": "Open the generated Markdown report before sharing feedback.",
            },
            {
                "kind": "review_before_sharing",
                "description": "The source packet contains excerpts from the selected local repo files; review it before sharing externally.",
            },
        ],
    }
    artifacts_dir = root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifacts_dir / "v0.4.0-real-repo-trial-summary.json"
    report_path = artifacts_dir / "v0.4.0-real-repo-trial-report.md"
    summary["summary_path"] = str(summary_path)
    summary["scorecard_path"] = str(summary_path)
    summary["trial_report_path"] = str(report_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_render_trial_report(summary), encoding="utf-8")
    return summary


def build_repo_source_packet(
    *,
    repo: Path,
    packet_dir: Path,
    max_files: int,
    max_bytes_per_file: int,
) -> dict[str, Any]:
    if packet_dir.exists():
        shutil.rmtree(packet_dir)
    packet_dir.mkdir(parents=True, exist_ok=True)
    selected = _select_repo_files(repo, max_files=max_files)
    excerpts = [_read_excerpt(path, repo=repo, max_bytes=max_bytes_per_file) for path in selected]
    repo_summary_path = packet_dir / "repo-source-manifest.md"
    repo_question_path = packet_dir / "repo-handoff-question.md"
    repo_summary_path.write_text(_render_repo_source_manifest(repo=repo, excerpts=excerpts), encoding="utf-8")
    repo_question_path.write_text(
        "# Real repo handoff question\n\n"
        "Prepare a reviewed AI work handoff that explains the project purpose, install path, "
        "important docs, contribution surface, and trust boundaries using only the local source packet.\n",
        encoding="utf-8",
    )
    return {
        "schema_id": "ctxvault.v0.4.0-real-repo-source-packet/v1",
        "repo_path": str(repo),
        "source_packet_dir": str(packet_dir),
        "source_packet_paths": [str(repo_summary_path), str(repo_question_path)],
        "selected_files": [
            {
                "relative_path": item["relative_path"],
                "bytes_read": item["bytes_read"],
                "truncated": item["truncated"],
            }
            for item in excerpts
        ],
        "contains_source_excerpts": True,
        "operator_review_required_before_sharing": True,
        "max_files": max_files,
        "max_bytes_per_file": max_bytes_per_file,
    }


def _select_repo_files(repo: Path, *, max_files: int) -> list[Path]:
    selected: list[Path] = []
    seen: set[Path] = set()
    for relative in PREFERRED_FILES:
        candidate = repo / relative
        if candidate.exists() and candidate.is_file() and _is_supported_text_file(candidate):
            selected.append(candidate)
            seen.add(candidate.resolve())
    for path in sorted((repo / "docs").rglob("*")) if (repo / "docs").exists() else []:
        if len(selected) >= max_files:
            break
        if not path.is_file() or path.resolve() in seen:
            continue
        if _is_ignored(path.relative_to(repo)) or not _is_supported_text_file(path):
            continue
        selected.append(path)
        seen.add(path.resolve())
    for path in sorted(repo.glob("*.md")):
        if len(selected) >= max_files:
            break
        if path.resolve() in seen or not _is_supported_text_file(path):
            continue
        selected.append(path)
        seen.add(path.resolve())
    return selected[:max_files]


def _is_ignored(relative: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in relative.parts)


def _is_supported_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES and not _is_ignored(path)


def _read_excerpt(path: Path, *, repo: Path, max_bytes: int) -> dict[str, Any]:
    raw = path.read_bytes()
    truncated = len(raw) > max_bytes
    text = raw[:max_bytes].decode("utf-8", errors="replace")
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(repo)),
        "bytes_read": min(len(raw), max_bytes),
        "truncated": truncated,
        "text": text,
    }


def _render_repo_source_manifest(*, repo: Path, excerpts: list[dict[str, Any]]) -> str:
    if not excerpts:
        return f"""# Real repo source manifest

Repo: `{repo.name}`

No supported README, docs, or metadata files were found. This packet still
records that the trial ran against a real local repo path, but it has no source
excerpts to project.
"""
    sections = []
    for item in excerpts:
        sections.append(
            f"## {item['relative_path']}\n\n"
            f"- bytes_read: {item['bytes_read']}\n"
            f"- truncated: {str(item['truncated']).lower()}\n\n"
            "```text\n"
            f"{item['text'].rstrip()}\n"
            "```\n"
        )
    return (
        "# Real repo source manifest\n\n"
        f"Repo: `{repo.name}`\n\n"
        "This packet contains bounded excerpts from local project docs and metadata. "
        "It is generated under the CtxVault trial root so the trial can create a "
        "receipt-backed handoff without writing into the source repository.\n\n"
        + "\n".join(sections)
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run v0.4.0 against a real local repo without writing projections back into that repo."
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Local repo/project directory to sample.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Vault/output root for the real repo trial.")
    parser.add_argument("--reset", action="store_true", help="Delete an existing /tmp/ctxvault-* trial root before running.")
    parser.add_argument("--max-files", type=int, default=12, help="Maximum repo docs/metadata files to excerpt.")
    parser.add_argument("--max-bytes-per-file", type=int, default=6000, help="Maximum bytes copied from each selected file.")
    parser.add_argument("--prepare-query", default=DEFAULT_QUERY, help="Context selection query for the trial.")
    parser.add_argument(
        "--target",
        choices=("agents-md", "claude-md", "workstream-brief"),
        default=DEFAULT_TARGET,
        help="Projection target written under the CtxVault trial root.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_real_repo_trial(
        repo=args.repo,
        root=args.root,
        reset=args.reset,
        max_files=args.max_files,
        max_bytes_per_file=args.max_bytes_per_file,
        prepare_query=args.prepare_query,
        target=args.target,
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
