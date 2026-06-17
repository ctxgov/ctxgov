from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "task-shard-context-budget-ledger" / "2026-06-18"


def main() -> int:
    packet = build_packet()
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


def build_packet() -> dict:
    bundle = _load_bundle()
    return {
        "schema_id": "ctxgov.task-shard-context-budget-owner-publish-packet/v0",
        "status": "pass_task_shard_context_budget_owner_publish_packet",
        "milestone": "Task Shard Context Budget Ledger",
        "hn_title": "Show HN: CtxGov - audit context budgets for long-running AI agent tasks",
        "public_page": "https://ctxgov.github.io/ctxgov/task-shard-context-budget-try-in-5-minutes.html",
        "publication_bundle_sha256": bundle["publication_bundle_sha256"],
        "publication_file_count": bundle["publication_file_count"],
        "manual_review_required": "owner_manual_platform_submit_only",
        "required_owner_actions": [
            "review publication bundle",
            "approve commit and push separately",
            "wait for Pages deployment",
            "run live publication check",
            "manually submit HN/LinkedIn/X copy",
        ],
        "blocked_without_owner_approval": [
            "commit",
            "push",
            "release",
            "Pages deploy",
            "HN submit",
            "LinkedIn post",
            "X post",
            "workflow execution",
            "worktree creation",
            "provider/model call",
            "target write",
            "memory/backend write",
        ],
        "publication_executed": False,
        "outreach_performed": False,
        "commit_created": False,
        "push_executed": False,
        "release_created": False,
    }


def _load_bundle() -> dict:
    script = ROOT / "scripts" / "build_task_shard_context_budget_publication_bundle.py"
    spec = importlib.util.spec_from_file_location("build_task_shard_context_budget_publication_bundle", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.build_bundle()


if __name__ == "__main__":
    raise SystemExit(main())
