#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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
from ctxgov.surface import CtxVaultSurface


SCOPE_KIND = "project"
SCOPE_VALUE = "ctxvault"
WORKSTREAM_ID = "ws_20260421_ctxvault_schema"
WORKSTREAM_REF = f"workstream://{WORKSTREAM_ID}"
TARGET_KIND = "harness.agents-md"

DEMO_SOURCES: tuple[dict[str, str], ...] = (
    {
        "id": "know_v032_demo_release_plan",
        "title": "v0.3.2 release plan",
        "body": (
            "# v0.3.2 release plan\n\n"
            "CtxVault v0.3.2 demonstrates deterministic context selection before context reaches AI tools. "
            "The operator should pick exact local context slices, inspect the token budget, and keep "
            "projection receipts linked to the selection receipt.\n\n"
            "The demo should stay local-first and should not require a model, embedding service, "
            "vector database, remote provider, or private user data."
        ),
    },
    {
        "id": "know_v032_demo_projection_boundary",
        "title": "Projection boundary",
        "body": (
            "# Projection boundary\n\n"
            "Selected context slices can be projected into AGENTS.md, CLAUDE.md, or a workstream brief "
            "only after privacy preflight allows the selection. Projection files are rebuildable views, "
            "not canonical truth.\n\n"
            "The useful public claim is source-grouped selection, privacy preflight, token budget preview, "
            "and receipts that explain what was selected."
        ),
    },
    {
        "id": "know_v032_demo_blocked_secret",
        "title": "Blocked secret sentinel",
        "body": (
            "# Blocked secret sentinel\n\n"
            "This local source intentionally contains a fake credential-like token so the deterministic "
            "privacy layer can withhold it from normal selection suggestions: "
            "sk-abcdefghijklmnopqrstuvwxyz1234567890"
        ),
    },
)


def run_demo(*, root: Path) -> dict[str, Any]:
    root = root.resolve()
    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    surface.vault.import_core_fixtures(REPO_ROOT / "fixtures" / "core")

    source_refs: list[str] = []
    for source in DEMO_SOURCES:
        payload = _knowledge_payload(source["id"], source["title"], source["body"])
        surface.vault.store_core_object("KnowledgeArtifact", payload)
        source_refs.append(f"knowledge://{source['id']}")

    rebuild = surface.context_slice_rebuild()
    all_hits = surface.context_search(
        "",
        scope_kind=SCOPE_KIND,
        scope_value=SCOPE_VALUE,
        limit=200,
        include_blocked=True,
    )

    release_ref = _first_slice_ref(all_hits, "knowledge://know_v032_demo_release_plan")
    boundary_ref = _first_slice_ref(all_hits, "knowledge://know_v032_demo_projection_boundary")
    blocked_ref = _first_slice_ref(all_hits, "knowledge://know_v032_demo_blocked_secret")
    selected_refs = [release_ref, boundary_ref]
    candidate_refs = [release_ref, boundary_ref, blocked_ref]

    selection = surface.context_selection_compose(
        "deterministic context selection privacy preflight projection receipts",
        target_kind=TARGET_KIND,
        scope_kind=SCOPE_KIND,
        scope_value=SCOPE_VALUE,
        workstream_ref=WORKSTREAM_REF,
        selected_slice_refs=selected_refs,
        candidate_slice_refs=candidate_refs,
        token_budget=800,
        include_blocked=True,
        write_receipt=True,
    )

    artifacts_dir = root / "artifacts" / "v0.3.2-demo"
    exports_dir = root / "exports" / "v0.3.2-demo"
    agents_projection = surface.harness_agents_md_emit(
        workstream_id=WORKSTREAM_ID,
        output_path=exports_dir / "AGENTS.md",
        receipt_output_path=artifacts_dir / "projection-receipts" / "agents-md.json",
        selected_slice_refs=selected_refs,
    )
    claude_projection = surface.harness_claude_md_emit(
        workstream_id=WORKSTREAM_ID,
        output_path=exports_dir / "CLAUDE.md",
        receipt_output_path=artifacts_dir / "projection-receipts" / "claude-md.json",
        selected_slice_refs=selected_refs,
    )
    workstream_projection = surface.wiki_workstream_markdown_emit(
        workstream_id=WORKSTREAM_ID,
        output_path=exports_dir / "workstream-brief.md",
        receipt_output_path=artifacts_dir / "projection-receipts" / "workstream-brief.json",
        selected_slice_refs=selected_refs,
    )

    blocked_candidate = _candidate_by_ref(selection, blocked_ref)
    summary = {
        "schema_id": "ctxvault.v0.3.2-deterministic-demo/v1",
        "ok": True,
        "root": str(root),
        "claim_boundary": {
            "requires_model": False,
            "requires_embedding": False,
            "requires_vector_database": False,
            "requires_remote_provider": False,
            "uses_private_user_data": False,
        },
        "toy_sources": source_refs,
        "slice_rebuild": rebuild,
        "selection": {
            "target_kind": TARGET_KIND,
            "selected_slice_refs": selected_refs,
            "candidate_slice_refs": selection["candidate_slice_refs"],
            "source_group_count": len(selection["source_groups"]),
            "token_budget": selection["token_budget"],
            "token_estimate": selection["token_estimate"],
            "budget_status": selection["budget_status"],
            "privacy_decision": selection["privacy_preflight"]["receipt"]["decision"],
            "receipt_path": selection["receipt_path"],
            "selection_ref": selection["receipt"]["selection_ref"],
            "blocked_candidate": {
                "slice_ref": blocked_ref,
                "privacy_class": blocked_candidate["privacy_class"],
                "is_selected": blocked_candidate["is_selected"],
            },
        },
        "projections": {
            "agents_md": _projection_summary(agents_projection),
            "claude_md": _projection_summary(claude_projection),
            "workstream_brief": _projection_summary(workstream_projection),
        },
        "inspection_order": [
            "toy_sources",
            "slice_rebuild",
            "selection",
            "projections",
        ],
    }
    summary_path = artifacts_dir / "summary.json"
    _write_json(summary_path, summary)
    summary["summary_path"] = str(summary_path.resolve())
    _write_json(summary_path, summary)
    return summary


def _knowledge_payload(object_id: str, title: str, body: str) -> dict[str, Any]:
    return {
        "id": object_id,
        "kind": "demo_note",
        "title": title,
        "scope": {"kind": SCOPE_KIND, "value": SCOPE_VALUE},
        "body": body,
        "source_refs": [],
        "derived_from": [],
        "status": "active",
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
        "created_at": "2026-05-02T00:00:00Z",
        "updated_at": "2026-05-02T00:00:00Z",
    }


def _first_slice_ref(hits: list[dict[str, Any]], source_ref: str) -> str:
    for hit in hits:
        if hit["payload"]["source_ref"] == source_ref:
            return str(hit["slice_ref"])
    raise KeyError(f"missing demo context slice for {source_ref}")


def _candidate_by_ref(selection: dict[str, Any], slice_ref: str) -> dict[str, Any]:
    for group in selection["source_groups"]:
        for item in group["slices"]:
            if item["slice_ref"] == slice_ref:
                return item
    raise KeyError(f"missing candidate slice {slice_ref}")


def _projection_summary(projection: dict[str, Any]) -> dict[str, Any]:
    receipt = projection["receipt"]
    return {
        "projection_id": projection["projection_id"],
        "output_path": projection["output_path"],
        "receipt_path": projection["receipt_path"],
        "target_kind": receipt["target_kind"],
        "output_sha256": receipt["output_sha256"],
        "selected_slice_refs": receipt["selected_slice_refs"],
        "context_selection_ref": receipt["context_selection_ref"],
        "context_selection_receipt_id": receipt["context_selection_receipt_id"],
        "privacy_decision": receipt["privacy_preflight"]["decision"],
        "policy_decision": receipt["policy_decision"],
        "review_state": receipt["review_state"],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the offline v0.3.2 deterministic context-selection demo with toy local sources."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/tmp/ctxvault-v032-deterministic-demo"),
        help="Vault/output root for generated demo artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_demo(root=args.root)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
