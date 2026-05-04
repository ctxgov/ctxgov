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

from run_v032_deterministic_demo import DEMO_SOURCES, SCOPE_KIND, SCOPE_VALUE, TARGET_KIND, _knowledge_payload

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.surface import CtxVaultSurface


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "id": "release-selection",
        "query": "deterministic context selection before context reaches AI tools",
        "expected_source_refs": [
            "knowledge://know_v032_demo_release_plan",
            "knowledge://know_v032_demo_projection_boundary",
        ],
        "forbidden_source_refs": ["knowledge://know_v032_demo_blocked_secret"],
    },
    {
        "id": "projection-receipts",
        "query": "privacy preflight projection receipts token budget",
        "expected_source_refs": [
            "knowledge://know_v032_demo_release_plan",
            "knowledge://know_v032_demo_projection_boundary",
        ],
        "forbidden_source_refs": ["knowledge://know_v032_demo_blocked_secret"],
    },
)


def run_scorecard(*, root: Path) -> dict[str, Any]:
    root = root.resolve()
    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    surface.vault.import_core_fixtures(REPO_ROOT / "fixtures" / "core")

    for source in DEMO_SOURCES:
        surface.vault.store_core_object(
            "KnowledgeArtifact",
            _knowledge_payload(source["id"], source["title"], source["body"]),
        )
    rebuild = surface.context_slice_rebuild()

    scenario_results = [_run_candidate_scenario(surface, scenario) for scenario in SCENARIOS]
    safety_result = _run_withheld_preflight_scenario(surface)
    min_recall = min(item["expected_source_recall"] for item in scenario_results)
    forbidden_hits = sum(item["forbidden_hit_count"] for item in scenario_results)
    status = "pass" if min_recall >= 1.0 and forbidden_hits == 0 and safety_result["status"] == "pass" else "fail"

    scorecard = {
        "schema_id": "ctxvault.selection-scorecard/v1",
        "status": status,
        "root": str(root),
        "rebuild": rebuild,
        "thresholds": {
            "min_expected_source_recall": 1.0,
            "max_forbidden_hit_count": 0,
            "withheld_preflight_must_block": True,
        },
        "summary": {
            "scenario_count": len(scenario_results),
            "min_expected_source_recall": min_recall,
            "forbidden_hit_count": forbidden_hits,
            "withheld_preflight_status": safety_result["status"],
        },
        "scenarios": scenario_results,
        "safety": safety_result,
    }
    scorecard_path = root / "artifacts" / "v0.3.2-selection-scorecard.json"
    _write_json(scorecard_path, scorecard)
    scorecard["scorecard_path"] = str(scorecard_path.resolve())
    _write_json(scorecard_path, scorecard)
    return scorecard


def _run_candidate_scenario(surface: CtxVaultSurface, scenario: dict[str, Any]) -> dict[str, Any]:
    selection = surface.context_selection_compose(
        str(scenario["query"]),
        target_kind=TARGET_KIND,
        scope_kind=SCOPE_KIND,
        scope_value=SCOPE_VALUE,
        limit=8,
        token_budget=800,
        include_blocked=False,
        write_receipt=False,
    )
    candidate_source_refs = _candidate_source_refs(selection)
    expected = list(scenario["expected_source_refs"])
    forbidden = list(scenario["forbidden_source_refs"])
    matched = [source_ref for source_ref in expected if source_ref in candidate_source_refs]
    forbidden_matched = [source_ref for source_ref in forbidden if source_ref in candidate_source_refs]
    return {
        "id": scenario["id"],
        "query": scenario["query"],
        "candidate_slice_refs": selection["candidate_slice_refs"],
        "candidate_source_refs": candidate_source_refs,
        "expected_source_refs": expected,
        "matched_expected_source_refs": matched,
        "expected_source_recall": len(matched) / len(expected) if expected else 1.0,
        "forbidden_source_refs": forbidden,
        "forbidden_matched_source_refs": forbidden_matched,
        "forbidden_hit_count": len(forbidden_matched),
        "source_group_count": len(selection["source_groups"]),
    }


def _run_withheld_preflight_scenario(surface: CtxVaultSurface) -> dict[str, Any]:
    hits = surface.context_search("", scope_kind=SCOPE_KIND, scope_value=SCOPE_VALUE, include_blocked=True, limit=200)
    withheld_ref = next(
        hit["slice_ref"]
        for hit in hits
        if hit["payload"]["source_ref"] == "knowledge://know_v032_demo_blocked_secret"
        and hit["payload"]["privacy_class"] == "withheld"
    )
    preflight = surface.context_selection_preflight(
        [withheld_ref],
        target_kind=TARGET_KIND,
        query="blocked secret sentinel",
        write_receipt=False,
    )
    decision = preflight["receipt"]["decision"]
    return {
        "id": "withheld-selection-blocks-projection",
        "status": "pass" if decision == "block" else "fail",
        "selected_slice_ref": withheld_ref,
        "decision": decision,
        "reasons": preflight["receipt"]["reasons"],
        "allowed_to_write": preflight["receipt"]["projection_gate"]["allowed_to_write"],
    }


def _candidate_source_refs(selection: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for group in selection["source_groups"]:
        source_ref = str(group["source_ref"])
        if source_ref not in refs:
            refs.append(source_ref)
    return refs


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a lightweight deterministic scorecard for v0.3.2 context selection quality and safety."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/tmp/ctxvault-v032-selection-scorecard"),
        help="Vault/output root for generated scorecard artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scorecard = run_scorecard(root=args.root)
    print(json.dumps(scorecard, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if scorecard["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
