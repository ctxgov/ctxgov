from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "task-shard-context-budget-ledger" / "2026-06-18"
EXPECTED_HN_TITLE = "Show HN: CtxGov - audit context budgets for long-running AI agent tasks"
OLD_POSITIONING = "AI memory systems are becoming operational state"
POSITIVE_OVERCLAIM_PHRASES = [
    "benchmark result",
    "savings number",
    "security guarantee",
    "provider integration",
    "provider support",
    "compatibility matrix",
    "adoption evidence",
    "worktree execution",
    "target write enabled",
    "stable protocol",
]


def main() -> int:
    payload = _render_payload()
    errors = []
    hn_text = (RELEASE / "hn-post.md").read_text(encoding="utf-8")
    linkedin_text = (RELEASE / "linkedin-post.md").read_text(encoding="utf-8")
    x_text = (RELEASE / "x-thread.md").read_text(encoding="utf-8")
    combined = "\n".join([hn_text, linkedin_text, x_text, json.dumps(payload, sort_keys=True)])

    if payload["hn"]["title"] != EXPECTED_HN_TITLE:
        errors.append("hn title mismatch")
    if OLD_POSITIONING.lower() in combined.lower():
        errors.append("old memory-state positioning reused")
    if "Long-running AI agent tasks fail" not in linkedin_text:
        errors.append("linkedin must lead with long-running agent task pain")
    if "Long-running AI agent tasks fail" not in x_text:
        errors.append("x thread must lead with long-running agent task pain")
    for phrase in POSITIVE_OVERCLAIM_PHRASES:
        if phrase in combined.lower():
            errors.append(f"positive overclaim phrase present: {phrase}")
    if payload.get("publication_executed") is not False:
        errors.append("publication_executed must remain false")
    if payload.get("outreach_performed") is not False:
        errors.append("outreach_performed must remain false")
    for count in payload["x"]["tweet_character_counts"]:
        if count > payload["x"]["max_tweet_chars"]:
            errors.append(f"x tweet exceeds max chars: {count}")

    result = {
        "schema_id": "ctxgov.task-shard-context-budget-social-draft-drift/v0",
        "status": "pass_task_shard_context_budget_social_draft_drift" if not errors else "fail_task_shard_context_budget_social_draft_drift",
        "hn_title": payload["hn"]["title"],
        "hn_draft_drift_status": "pass" if payload["hn"]["title"] == EXPECTED_HN_TITLE else "fail",
        "linkedin_draft_drift_status": "pass" if "Long-running AI agent tasks fail" in linkedin_text else "fail",
        "x_thread_drift_status": "pass" if "Long-running AI agent tasks fail" in x_text else "fail",
        "old_positioning_status": "pass" if OLD_POSITIONING.lower() not in combined.lower() else "fail",
        "x_tweet_character_counts": payload["x"]["tweet_character_counts"],
        "error_count": len(errors),
        "errors": errors,
        "publication_executed": False,
        "outreach_performed": False,
        "claim_boundary": payload["claim_boundary"],
        "side_effect_boundary": payload["side_effect_boundary"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _render_payload() -> dict:
    script = ROOT / "scripts" / "render_task_shard_context_budget_social_payload.py"
    spec = importlib.util.spec_from_file_location("render_task_shard_context_budget_social_payload", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    payload = module.build_payload()
    (RELEASE / "task-shard-context-budget-social-payload.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (RELEASE / "task-shard-context-budget-social-payload.md").write_text(
        module.render_markdown(payload),
        encoding="utf-8",
    )
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
