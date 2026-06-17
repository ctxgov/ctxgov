from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "task-shard-context-budget-ledger" / "2026-06-18"
PUBLIC_PAGE = "https://ctxgov.github.io/ctxgov/task-shard-context-budget-try-in-5-minutes.html"
HN_TITLE = "Show HN: CtxGov - audit context budgets for long-running AI agent tasks"


def main() -> int:
    payload = build_payload()
    RELEASE.mkdir(parents=True, exist_ok=True)
    json_path = RELEASE / "task-shard-context-budget-social-payload.json"
    md_path = RELEASE / "task-shard-context-budget-social-payload.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_payload() -> dict:
    x_tweets = _x_tweets()
    return {
        "schema_id": "ctxgov.task-shard-context-budget-social-payload/v0",
        "status": "pass_task_shard_context_budget_social_payload",
        "milestone": "Task Shard Context Budget Ledger",
        "public_page": PUBLIC_PAGE,
        "demo_command": "python3 scripts/run_task_shard_context_budget_demo.py --input examples/task-shard-context-budget/",
        "hn": {
            "title": HN_TITLE,
            "url": PUBLIC_PAGE,
            "text": "",
            "first_comment": (RELEASE / "hn-post.md").read_text(encoding="utf-8"),
        },
        "linkedin": {
            "body": (RELEASE / "linkedin-post.md").read_text(encoding="utf-8"),
        },
        "x": {
            "tweets": x_tweets,
            "tweet_count": len(x_tweets),
            "tweet_character_counts": [len(tweet) for tweet in x_tweets],
            "max_tweet_chars": 280,
        },
        "claim_boundary": {
            "public_benchmark_claim_created": False,
            "public_savings_claim_created": False,
            "public_adoption_claim_created": False,
            "public_security_claim_created": False,
            "public_compatibility_claim_created": False,
            "public_support_claim_created": False,
            "stable_protocol_claim_created": False,
        },
        "side_effect_boundary": {
            "workflow_executed": False,
            "worktree_created": False,
            "provider_or_model_call_performed": False,
            "target_file_written": False,
            "memory_backend_written": False,
            "publication_executed": False,
            "outreach_performed": False,
        },
        "publication_executed": False,
        "outreach_performed": False,
        "manual_review_required": "owner_manual_platform_submit_only",
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Task Shard Context Budget Social Payload",
        "",
        f"Status: `{payload['status']}`",
        "",
        f"HN title: {payload['hn']['title']}",
        f"HN URL: {payload['hn']['url']}",
        "",
        "## X Thread",
        "",
    ]
    for tweet in payload["x"]["tweets"]:
        lines.extend([tweet, ""])
    return "\n".join(lines)


def _x_tweets() -> list[str]:
    return [
        "1/ Long-running AI agent tasks fail when context is split, summarized, cached, or omitted without an auditable boundary.\n\nCtxGov's next local milestone is a Task Shard Context Budget Ledger.",
        "2/ The demo reads a saved long-agent task plan and reports selected, omitted, searchable-only, and compacted context refs per shard.\n\nIt also shows per-shard token budgets.",
        "3/ Cache hits are not authority. Larger context windows are not authority.\n\nThe report keeps merge and replan risk visible before downstream work relies on a shard result.",
        "4/ Boundary:\n\nno workflow execution\nno worktree creation\nno provider call\nno target write\nno memory write\nno SARIF upload\nno benchmark, savings, adoption, security, support, or compatibility claim",
        "5/ Public page candidate:\n\nhttps://ctxgov.github.io/ctxgov/task-shard-context-budget-try-in-5-minutes.html\n\nQuestion: what proof should exist before a long-running agent shard is trusted?",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
