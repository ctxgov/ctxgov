#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ctxgov.core import CtxVault
from ctxgov.layout import default_layout
from ctxgov.quality import build_source_retention_scorecard
from ctxgov.surface import CtxVaultSurface


SCOPE = ("project", "ctxvault-v034-quality")
TARGET_KIND = "harness.agents-md"
FIXTURE_SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "know_v034_required_current",
        "title": "Required current retrieval boundary",
        "body": (
            "# Required current retrieval boundary\n\n"
            "v0.3.4 context quality must retain the required privacy preflight and projection receipt refs. "
            "The current rule is governed source -> selection -> privacy preflight -> receipts -> projection."
        ),
    },
    {
        "id": "know_v034_long_noisy",
        "title": "Long noisy density decoy",
        "body": "# Long noisy density decoy\n\n" + " ".join(["density filler context"] * 180),
    },
    {
        "id": "know_v034_stale_conflict",
        "title": "Stale conflicting retrieval rule",
        "body": (
            "# Stale conflicting retrieval rule\n\n"
            "STALE and conflicting note: old automation should bypass privacy preflight and auto promote memory. "
            "This contradicts v0.3.4 governed context quality rules."
        ),
    },
    {
        "id": "know_v034_current_conflict_resolution",
        "title": "Current retrieval resolution rule",
        "body": (
            "# Current retrieval resolution rule\n\n"
            "Current v0.3.4 retrieval quality rejects older or risky refs unless the ambiguity is surfaced for review. "
            "Durable truth still requires provenance and human review."
        ),
    },
    {
        "id": "know_v034_duplicate_noise",
        "title": "Duplicate density noise",
        "body": "# Duplicate density noise\n\n" + " ".join(["density filler context"] * 180),
    },
)


def run_scorecards(*, root: Path) -> dict[str, Any]:
    root = root.resolve()
    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    for source in FIXTURE_SOURCES:
        surface.vault.store_core_object("KnowledgeArtifact", _knowledge_payload(source))
    rebuild = surface.context_slice_rebuild()

    hits = surface.context_search("", scope_kind=SCOPE[0], scope_value=SCOPE[1], include_blocked=True, limit=100)
    refs = _refs_by_source(hits)
    density_selection = surface.context_selection_compose(
        "v0.3.4 context quality density privacy preflight projection receipts",
        target_kind=TARGET_KIND,
        scope_kind=SCOPE[0],
        scope_value=SCOPE[1],
        selected_slice_refs=[refs["knowledge://know_v034_required_current"]],
        required_slice_refs=[refs["knowledge://know_v034_required_current"]],
        candidate_slice_refs=[
            refs["knowledge://know_v034_required_current"],
            refs["knowledge://know_v034_long_noisy"],
            refs["knowledge://know_v034_duplicate_noise"],
        ],
        token_budget=180,
        write_receipt=True,
    )
    conflict_selection = surface.context_selection_compose(
        "v0.3.4 retrieval quality current resolution stale misleading refs",
        target_kind=TARGET_KIND,
        scope_kind=SCOPE[0],
        scope_value=SCOPE[1],
        selected_slice_refs=[refs["knowledge://know_v034_current_conflict_resolution"]],
        required_slice_refs=[refs["knowledge://know_v034_current_conflict_resolution"]],
        candidate_slice_refs=[
            refs["knowledge://know_v034_current_conflict_resolution"],
            refs["knowledge://know_v034_stale_conflict"],
        ],
        token_budget=240,
        write_receipt=True,
    )

    retention = build_source_retention_scorecard(
        scenarios=[
            {
                "id": "density-required-ref-retention",
                "query": density_selection["query"],
                "expected_source_refs": ["knowledge://know_v034_required_current"],
                "selected_source_refs": _selected_source_refs(density_selection),
                "forbidden_source_refs": [
                    "knowledge://know_v034_long_noisy",
                    "knowledge://know_v034_duplicate_noise",
                ],
            },
            {
                "id": "misleading-conflict-rejection",
                "query": conflict_selection["query"],
                "expected_source_refs": ["knowledge://know_v034_current_conflict_resolution"],
                "selected_source_refs": _selected_source_refs(conflict_selection),
                "forbidden_source_refs": ["knowledge://know_v034_stale_conflict"],
            },
        ]
    )

    density = density_selection["context_density_scorecard"]
    gain = conflict_selection["retrieval_gain_receipt"]
    conflict = conflict_selection["source_conflict_scorecard"]
    pass_checks = {
        "density_required_refs_retained": bool(density["required_refs_retained"]),
        "density_omitted_noisy_refs": {
            "knowledge://know_v034_long_noisy",
            "knowledge://know_v034_duplicate_noise",
        }.issubset(_omitted_source_refs(density_selection)),
        "density_compresses_candidates": density["compression_ratio"] < 1.0,
        "source_retention_pass": retention["status"] == "pass",
        "retrieval_gain_receipt_present": gain["schema_id"] == "ctxvault.retrieval-gain-receipt/v1",
        "stale_conflict_rejected": refs["knowledge://know_v034_stale_conflict"] in conflict["misleading_refs_rejected"],
        "search_trace_records_stop_reason": bool(conflict_selection["search_decision_trace"]["stop_reason"]),
    }
    status = "pass" if all(pass_checks.values()) else "fail"
    summary = {
        "schema_id": "ctxvault.v0.3.4-context-quality-scorecards/v1",
        "status": status,
        "root": str(root),
        "scope": {"kind": SCOPE[0], "value": SCOPE[1]},
        "rebuild": rebuild,
        "pass_checks": pass_checks,
        "density_selection_receipt_path": density_selection["receipt_path"],
        "conflict_selection_receipt_path": conflict_selection["receipt_path"],
        "context_density_scorecard": density,
        "source_retention_scorecard": retention,
        "retrieval_gain_receipt": gain,
        "search_decision_trace": conflict_selection["search_decision_trace"],
        "source_conflict_scorecard": conflict,
    }
    scorecard_path = root / "artifacts" / "v0.3.4-context-quality-scorecards.json"
    summary["scorecard_path"] = str(scorecard_path.resolve())
    _write_json(scorecard_path, summary)
    return summary


def _knowledge_payload(source: dict[str, str]) -> dict[str, Any]:
    return {
        "id": source["id"],
        "kind": "quality_fixture_note",
        "title": source["title"],
        "scope": {"kind": SCOPE[0], "value": SCOPE[1]},
        "body": source["body"],
        "source_refs": [],
        "derived_from": [],
        "status": "active",
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
        "created_at": "2026-05-04T00:00:00Z",
        "updated_at": "2026-05-04T00:00:00Z",
    }


def _refs_by_source(hits: list[dict[str, Any]]) -> dict[str, str]:
    refs: dict[str, str] = {}
    for hit in hits:
        payload = hit.get("payload") if isinstance(hit.get("payload"), dict) else {}
        source_ref = str(payload.get("source_ref") or "")
        slice_ref = str(hit.get("slice_ref") or "")
        if source_ref and slice_ref and source_ref not in refs:
            refs[source_ref] = slice_ref
    missing = [f"knowledge://{source['id']}" for source in FIXTURE_SOURCES if f"knowledge://{source['id']}" not in refs]
    if missing:
        raise RuntimeError(f"missing fixture slice refs: {missing}")
    return refs


def _selected_source_refs(selection: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for item in selection.get("selected_slices") or []:
        source_ref = str(item.get("source_ref") or "")
        if source_ref and source_ref not in refs:
            refs.append(source_ref)
    return refs


def _omitted_source_refs(selection: dict[str, Any]) -> set[str]:
    quality = selection.get("context_quality_receipt") if isinstance(selection.get("context_quality_receipt"), dict) else {}
    return {str(item.get("source_ref") or "") for item in quality.get("omitted_refs_with_reason") or []}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic v0.3.4 context quality, density, retention, retrieval-gain, and conflict scorecards."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/tmp/ctxvault-v034-context-quality-scorecards"),
        help="Vault/output root for generated v0.3.4 scorecard artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_scorecards(root=args.root)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
