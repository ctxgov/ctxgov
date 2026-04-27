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

from ctxvault.core import CtxVault
from ctxvault.ingest import import_knowledge_path, import_transcript_path
from ctxvault.layout import default_layout
from ctxvault.policy import CtxVaultPolicy
from ctxvault.surface import CtxVaultSurface


SCOPE_KIND = "project"
SCOPE_VALUE = "ctxvault"
PROMPT_ID = "prompt_schema_designer_v1"
SESSION_ID = "sess_m1_context_injection_001"
APPROVED_MEMORY_CANDIDATE_ID = "memc_m1_context_injection_approved"
REJECTED_MEMORY_CANDIDATE_ID = "memc_m1_context_injection_rejected"
UNREVIEWED_MEMORY_CANDIDATE_ID = "memc_m1_context_injection_unreviewed"
APPROVED_MEMORY_ID = "mem_m1_context_injection_approved"
WORKSTREAM_CANDIDATE_ID = "wsc_m1_context_injection_source_to_injection"
WORKSTREAM_ID = "ws_m1_context_injection_source_to_injection"
BUNDLE_ID = "bundle_m1_context_injection_source_to_injection"


def run_golden_path(*, root: Path, fixture_root: Path) -> dict[str, Any]:
    root = root.resolve()
    fixture_root = fixture_root.resolve()
    _ensure_fixture_root(fixture_root)

    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()

    policy_payload = _read_json(REPO_ROOT / "fixtures" / "controls" / "protection-policy.json")
    backup_receipt = CtxVaultPolicy.freshen_backup_receipt(
        _read_json(REPO_ROOT / "fixtures" / "controls" / "backup-check-receipt.json")
    )

    prompt_payload = _read_json(REPO_ROOT / "fixtures" / "core" / "prompt-asset.json")
    surface.vault.store_core_object("PromptAsset", prompt_payload)

    project_doc_receipts = import_knowledge_path(
        surface.vault,
        fixture_root / "project-docs",
        scope_kind=SCOPE_KIND,
        scope_value=SCOPE_VALUE,
        recursive=True,
    )
    knowledge_receipts = import_knowledge_path(
        surface.vault,
        fixture_root / "knowledge",
        scope_kind=SCOPE_KIND,
        scope_value=SCOPE_VALUE,
        recursive=True,
    )
    session_receipt = import_transcript_path(
        surface.vault,
        fixture_root / "sessions" / "context-injection-session.json",
        scope_kind=SCOPE_KIND,
        scope_value=SCOPE_VALUE,
        client="codex",
        imported_via="ctxvault_m1_golden_path",
    )

    import_receipt = {
        "project_docs": [receipt.to_dict() for receipt in project_doc_receipts],
        "knowledge_sources": [receipt.to_dict() for receipt in knowledge_receipts],
        "session": session_receipt.to_dict(),
    }
    import_receipt_path = root / "artifacts" / "source-import-receipt.json"
    _write_json(import_receipt_path, import_receipt)

    memory_candidates = _read_json(fixture_root / "review" / "memory-candidates.json")
    if not isinstance(memory_candidates, list):
        raise ValueError("memory-candidates fixture must be a JSON array")
    for candidate in memory_candidates:
        surface.vault.store_core_object("MemoryCandidate", candidate)

    approved_memory_review = surface.memory_candidate_review(
        APPROVED_MEMORY_CANDIDATE_ID,
        decision="approved",
        reviewer="m1_golden_path",
        notes="Approved for Context Injection M1 harness projections.",
        memory_id=APPROVED_MEMORY_ID,
        policy_payload=policy_payload,
        backup_receipt=backup_receipt,
    )
    rejected_memory_review = surface.memory_candidate_review(
        REJECTED_MEMORY_CANDIDATE_ID,
        decision="rejected",
        reviewer="m1_golden_path",
        notes="Rejected sentinel candidate must stay out of injected outputs.",
    )

    workstream_candidate = _read_json(fixture_root / "review" / "workstream-candidate.json")
    gathered_knowledge_refs = [
        f"knowledge://{receipt.object_id}"
        for receipt in [*project_doc_receipts, *knowledge_receipts]
    ]
    gathered_session_ref = f"session://{session_receipt.session.object_id}"
    workstream_candidate["source_refs"] = [
        gathered_session_ref,
        *gathered_knowledge_refs,
    ]
    workstream_candidate["session_refs"] = [gathered_session_ref]
    workstream_candidate["knowledge_refs"] = gathered_knowledge_refs
    surface.vault.store_core_object("WorkstreamCandidate", workstream_candidate)

    workstream_review = surface.workstream_candidate_review(
        WORKSTREAM_CANDIDATE_ID,
        decision="approved",
        reviewer="m1_golden_path",
        notes="Approved M1 source-to-injection workstream after fixture review.",
        workstream_id=WORKSTREAM_ID,
        policy_payload=policy_payload,
        backup_receipt=backup_receipt,
    )

    bundle = surface.context_build(
        {
            "scope_kind": SCOPE_KIND,
            "scope_value": SCOPE_VALUE,
            "task_label": "Context Injection M1 source-to-injection golden path",
            "prompt_id": PROMPT_ID,
            "session_id": SESSION_ID,
            "memory_query": "Context Injection M1 reviewed workstream context AGENTS CLAUDE brief",
            "knowledge_query": "Launch Review Note workstream AGENTS CLAUDE stable markdown brief",
            "bundle_id": BUNDLE_ID,
        }
    )
    context_receipt = surface.context_receipt_emit(
        bundle,
        output_path=root / "artifacts" / "context-bundle-receipt.json",
        task_id="context-injection-m1",
    )
    workstream_receipt = surface.workstream_receipt_emit(
        workstream_review["workstream"],
        output_path=root / "artifacts" / "workstream-receipt.json",
        task_id="context-injection-m1",
    )

    agents_projection = surface.harness_agents_md_emit(
        workstream_id=WORKSTREAM_ID,
        output_path=root / "exports" / "AGENTS.md",
        receipt_output_path=root / "artifacts" / "projection-receipts" / "agents-md.json",
        memory_limit=5,
    )
    claude_projection = surface.harness_claude_md_emit(
        workstream_id=WORKSTREAM_ID,
        output_path=root / "exports" / "CLAUDE.md",
        receipt_output_path=root / "artifacts" / "projection-receipts" / "claude-md.json",
        memory_limit=5,
    )
    workstream_projection = surface.wiki_workstream_markdown_emit(
        workstream_id=WORKSTREAM_ID,
        output_path=root / "exports" / "workstreams" / "context-injection-m1.md",
        receipt_output_path=root / "artifacts" / "projection-receipts" / "workstream-md.json",
        memory_limit=5,
    )

    summary = {
        "ok": True,
        "root": str(root),
        "fixture_root": str(fixture_root),
        "golden_path_command": (
            "python3 scripts/run_context_injection_m1_golden_path.py "
            f"--root {root} --fixture-root {fixture_root}"
        ),
        "source_gathering": {
            "receipt_path": str(import_receipt_path.resolve()),
            "project_doc_count": len(project_doc_receipts),
            "knowledge_source_count": len(knowledge_receipts),
            "session_id": session_receipt.session.object_id,
            "turn_count": len(session_receipt.turns),
            "source_refs": [
                gathered_session_ref,
                *gathered_knowledge_refs,
            ],
        },
        "reviewed_context": {
            "approved_memory_ref": approved_memory_review["memory_ref"],
            "approved_memory_review_receipt_path": approved_memory_review["review_receipt_path"],
            "rejected_memory_candidate_ref": rejected_memory_review["candidate_ref"],
            "rejected_memory_review_receipt_path": rejected_memory_review["review_receipt_path"],
            "unreviewed_memory_candidate_ref": f"memory-candidate://{UNREVIEWED_MEMORY_CANDIDATE_ID}",
            "workstream_ref": workstream_review["workstream_ref"],
            "workstream_review_receipt_path": workstream_review["review_receipt_path"],
        },
        "context_bundle": {
            "bundle_id": bundle["id"],
            "bundle_ref": f"bundle://{bundle['id']}",
            "receipt_path": context_receipt["receipt_path"],
            "input_refs": bundle["input_refs"],
        },
        "workstream_receipt": {
            "receipt_path": workstream_receipt["receipt_path"],
            "workstream_ref": workstream_receipt["receipt"]["workstream_ref"],
        },
        "injected_outputs": {
            "agents_md": _projection_summary(agents_projection),
            "claude_md": _projection_summary(claude_projection),
            "workstream_md": _projection_summary(workstream_projection),
        },
    }
    summary_path = root / "artifacts" / "m1-golden-path-summary.json"
    _write_json(summary_path, summary)
    summary["summary_path"] = str(summary_path.resolve())
    _write_json(summary_path, summary)
    return summary


def _projection_summary(projection: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_id": projection["projection_id"],
        "output_path": projection["output_path"],
        "receipt_path": projection["receipt_path"],
        "target_kind": projection["receipt"]["target_kind"],
        "output_sha256": projection["receipt"]["output_sha256"],
        "source_refs": projection["receipt"]["source_refs"],
        "policy_decision": projection["receipt"]["policy_decision"],
        "review_state": projection["receipt"]["review_state"],
    }


def _ensure_fixture_root(fixture_root: Path) -> None:
    required_paths = [
        fixture_root / "project-docs",
        fixture_root / "knowledge",
        fixture_root / "sessions" / "context-injection-session.json",
        fixture_root / "review" / "memory-candidates.json",
        fixture_root / "review" / "workstream-candidate.json",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing Context Injection M1 fixtures: {missing}")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the deterministic Context Injection M1 source-to-injection golden path."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("/tmp/ctxvault-m1-context-injection"),
        help="Vault/output root for the generated M1 demo artifacts.",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=REPO_ROOT / "fixtures" / "m1-context-injection",
        help="Fixture source root containing project docs, session, knowledge, and review inputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_golden_path(root=args.root, fixture_root=args.fixture_root)
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
