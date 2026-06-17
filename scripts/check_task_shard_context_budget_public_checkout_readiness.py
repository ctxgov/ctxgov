from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CLONE_URL = "https://github.com/ctxgov/ctxgov.git"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Task Shard bundle in a clean public checkout.")
    parser.add_argument("--check-live", action="store_true")
    parser.add_argument("--keep-checkout", action="store_true")
    args = parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="ctxgov-task-shard-public-"))
    checkout = tmp / "ctxgov"
    errors = []
    clone = _run(["git", "clone", CLONE_URL, str(checkout)], cwd=tmp)
    if clone["returncode"] != 0:
        errors.append({"issue_id": "public_repo_clone_failed", "detail": clone["returncode"]})
    materialization = _run(
        [
            sys.executable,
            "scripts/materialize_task_shard_context_budget_publication_bundle.py",
            "--source-root",
            str(ROOT),
            "--checkout",
            str(checkout),
        ],
        cwd=ROOT,
    )
    if materialization["returncode"] != 0:
        errors.append({"issue_id": "materialization_failed", "detail": materialization["observed_status"]})
    final_preflight = _run([sys.executable, "scripts/check_task_shard_context_budget_final_preflight.py"], cwd=checkout)
    if final_preflight["observed_status"] != "pass_task_shard_context_budget_final_preflight":
        errors.append({"issue_id": "final_preflight_failed", "detail": final_preflight["observed_status"]})
    live_check = {"status": "skipped", "observed_status": None, "returncode": 0}
    if args.check_live:
        live_check = _run([sys.executable, "scripts/check_task_shard_context_budget_live_publication.py", "--live"], cwd=checkout)
        if live_check["observed_status"] != "pass_task_shard_context_budget_live_publication_check":
            errors.append({"issue_id": "live_publication_check_failed", "detail": live_check["observed_status"]})
    public_base_commit = _run(["git", "rev-parse", "--short", "HEAD"], cwd=checkout)

    if not args.keep_checkout:
        shutil.rmtree(tmp, ignore_errors=True)

    payload = {
        "schema_id": "ctxgov.task-shard-context-budget-public-checkout-readiness/v0",
        "status": "pass_task_shard_context_budget_public_checkout_ready" if not errors else "fail_task_shard_context_budget_public_checkout_ready",
        "milestone": "Task Shard Context Budget Ledger",
        "public_repo": "ctxgov/ctxgov",
        "clone_url": CLONE_URL,
        "public_base_commit": public_base_commit["stdout_tail"].strip() or None,
        "clone": clone,
        "materialization": materialization,
        "final_preflight": final_preflight,
        "live_check": live_check,
        "github_pages_deployed": bool(args.check_live and not errors),
        "issue_count": len(errors),
        "issues": errors,
        "commit_created": False,
        "push_executed": False,
        "release_created": False,
        "publication_executed": False,
        "outreach_performed": False,
        "checkout_removed": not args.keep_checkout,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _run(command: list[str], *, cwd: Path) -> dict:
    if not cwd.exists():
        return {
            "command": command,
            "returncode": 127,
            "status": "fail",
            "observed_status": None,
            "stdout_tail": "",
            "stderr_tail": f"cwd does not exist: {cwd}",
        }
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "returncode": result.returncode,
        "status": "pass" if result.returncode == 0 else "fail",
        "observed_status": _observed_json_status(result.stdout),
        "stdout_tail": result.stdout[-2000:],
        "stderr_tail": result.stderr[-2000:],
    }


def _observed_json_status(text: str) -> str | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    status = payload.get("status")
    return str(status) if status is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
