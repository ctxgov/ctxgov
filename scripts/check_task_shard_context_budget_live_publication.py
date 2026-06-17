from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PAGE = ROOT / "docs" / "task-shard-context-budget-try-in-5-minutes.html"
PUBLIC_PAGE = "https://ctxgov.github.io/ctxgov/task-shard-context-budget-try-in-5-minutes.html"
REQUIRED_PHRASES = [
    "python3 scripts/run_task_shard_context_budget_demo.py --input examples/task-shard-context-budget/",
    "selected context refs",
    "omitted context refs",
    "searchable-only refs",
    "compacted event refs",
    "per-shard token budget",
    "cache-hit-is-not-authority rule",
    "merge/replan gates",
    "No workflow, worktree, provider, target, or memory backend side effects",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the Task Shard public page locally and optionally live.")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()

    local_status = _check_text(LOCAL_PAGE.read_text(encoding="utf-8") if LOCAL_PAGE.exists() else "")
    live_status = {"checked": False, "url": PUBLIC_PAGE, "http_status": None, "missing_phrases": [], "error": None}
    if args.live:
        live_status = _check_live()
    errors = []
    if not LOCAL_PAGE.exists():
        errors.append("local page missing")
    if local_status["missing_phrases"]:
        errors.append("local page missing required phrases")
    if args.live and (live_status["http_status"] != 200 or live_status["missing_phrases"] or live_status["error"]):
        errors.append("live page check failed")

    payload = {
        "schema_id": "ctxgov.task-shard-context-budget-live-publication-check/v0",
        "status": "pass_task_shard_context_budget_live_publication_check" if not errors else "fail_task_shard_context_budget_live_publication_check",
        "local_page": "docs/task-shard-context-budget-try-in-5-minutes.html",
        "public_page": PUBLIC_PAGE,
        "local_status": local_status,
        "live_status": live_status,
        "live_fetch_performed": bool(args.live),
        "errors": errors,
        "publication_executed": False,
        "outreach_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _check_text(text: str) -> dict:
    return {
        "exists": bool(text),
        "missing_phrases": [phrase for phrase in REQUIRED_PHRASES if phrase not in text],
    }


def _check_live() -> dict:
    try:
        with urlopen(PUBLIC_PAGE, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = int(response.status)
    except URLError as exc:
        return {"checked": True, "url": PUBLIC_PAGE, "http_status": None, "missing_phrases": [], "error": str(exc)}
    checked = _check_text(body)
    return {
        "checked": True,
        "url": PUBLIC_PAGE,
        "http_status": status,
        "missing_phrases": checked["missing_phrases"],
        "error": None,
    }


if __name__ == "__main__":
    raise SystemExit(main())
