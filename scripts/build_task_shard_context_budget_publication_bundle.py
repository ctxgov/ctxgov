from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "task-shard-context-budget-ledger" / "2026-06-18"

PUBLICATION_FILES = [
    "docs/task-shard-context-budget-try-in-5-minutes.html",
    "docs/post-memory-state-task-shard-hn-candidate-2026-06-17.md",
    "docs/post-v0.7.0-task-shard-context-control-roadmap-2026-06-02.md",
    "docs/product-taxonomy-and-release-ladder-2026-06-02.md",
    "docs/product-line-ledger.md",
    "examples/task-shard-context-budget/long-agent-task.json",
    "fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-context-control-fixture-pack-20260602.json",
    "fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-context-import-shapes-20260602.json",
    "fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-import-shape-negative-fixtures-20260602.json",
    "fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-saved-trace-imports-20260602.json",
    "fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-context-rehearsal-20260602.json",
    "fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-context-budget-ledger-report-20260602.json",
    "schemas/json/ctxvault-task-shard-context-control-fixture-pack-v0.schema.json",
    "schemas/json/ctxvault-task-shard-context-import-shapes-v0.schema.json",
    "schemas/json/ctxgov-task-shard-context-budget-report-v0.schema.json",
    "src/ctxvault/task_shard_context.py",
    "scripts/check_task_shard_private_gate.py",
    "scripts/run_task_shard_context_budget_demo.py",
    "scripts/check_task_shard_context_budget_report_contract.py",
    "scripts/check_task_shard_context_budget_final_preflight.py",
    "scripts/render_task_shard_context_budget_social_payload.py",
    "scripts/check_task_shard_context_budget_social_draft_drift.py",
    "scripts/build_task_shard_context_budget_publication_bundle.py",
    "scripts/materialize_task_shard_context_budget_publication_bundle.py",
    "scripts/check_task_shard_context_budget_public_checkout_readiness.py",
    "scripts/check_task_shard_context_budget_live_publication.py",
    "scripts/render_task_shard_context_budget_owner_publish_packet.py",
    "scripts/check_task_shard_context_budget_owner_publish_packet_contract.py",
    "scripts/render_task_shard_context_budget_publish_command_envelope.py",
    "release/task-shard-context-budget-ledger/2026-06-18/README.md",
    "release/task-shard-context-budget-ledger/2026-06-18/hn-post.md",
    "release/task-shard-context-budget-ledger/2026-06-18/linkedin-post.md",
    "release/task-shard-context-budget-ledger/2026-06-18/x-thread.md",
    "release/task-shard-context-budget-ledger/2026-06-18/task-shard-context-budget-social-payload.json",
    "release/task-shard-context-budget-ledger/2026-06-18/task-shard-context-budget-social-payload.md",
    "tests/test_task_shard_context_budget_hn_candidate.py",
]


def main() -> int:
    payload = build_bundle()
    RELEASE.mkdir(parents=True, exist_ok=True)
    (RELEASE / "task-shard-context-budget-publication-bundle.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (RELEASE / "task-shard-context-budget-publication-bundle.md").write_text(
        render_bundle_markdown(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass_task_shard_context_budget_publication_bundle" else 1


def build_bundle() -> dict:
    files = []
    errors = []
    for rel in PUBLICATION_FILES:
        path = ROOT / rel
        exists = path.exists()
        if not exists:
            errors.append({"file": rel, "error": "missing"})
        files.append(
            {
                "path": rel,
                "exists": exists,
                "sha256": _sha256(path) if exists and path.is_file() else None,
            }
        )
    digest_source = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "schema_id": "ctxgov.task-shard-context-budget-publication-bundle/v0",
        "status": "pass_task_shard_context_budget_publication_bundle" if not errors else "fail_task_shard_context_budget_publication_bundle",
        "milestone": "Task Shard Context Budget Ledger",
        "publication_file_count": len(files),
        "publication_files": files,
        "publication_bundle_sha256": hashlib.sha256(digest_source).hexdigest(),
        "errors": errors,
        "side_effect_boundary": _side_effect_boundary(),
        "publication_executed": False,
        "outreach_performed": False,
        "commit_created": False,
        "push_executed": False,
        "release_created": False,
    }


def render_bundle_markdown(payload: dict) -> str:
    lines = [
        "# Task Shard Context Budget Publication Bundle",
        "",
        f"Status: `{payload['status']}`",
        f"Files: `{payload['publication_file_count']}`",
        f"SHA-256: `{payload['publication_bundle_sha256']}`",
        "",
    ]
    for item in payload["publication_files"]:
        lines.append(f"- `{item['path']}` `{item['sha256']}`")
    lines.append("")
    return "\n".join(lines)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "workflow_executed": False,
        "worktree_created": False,
        "provider_or_model_call_performed": False,
        "target_file_written": False,
        "memory_backend_written": False,
    }


if __name__ == "__main__":
    raise SystemExit(main())
