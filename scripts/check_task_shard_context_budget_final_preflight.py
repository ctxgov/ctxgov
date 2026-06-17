from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


COMMANDS = [
    {
        "gate_id": "demo",
        "command": [sys.executable, "scripts/run_task_shard_context_budget_demo.py", "--input", "examples/task-shard-context-budget/"],
        "expected_status": "pass_task_shard_context_budget_demo",
    },
    {
        "gate_id": "task_shard_private_gate",
        "command": [sys.executable, "scripts/check_task_shard_private_gate.py"],
        "expected_status": "pass",
    },
    {
        "gate_id": "report_contract",
        "command": [sys.executable, "scripts/check_task_shard_context_budget_report_contract.py"],
        "expected_status": "pass_task_shard_context_budget_report_contract",
    },
    {
        "gate_id": "social_draft_drift",
        "command": [sys.executable, "scripts/check_task_shard_context_budget_social_draft_drift.py"],
        "expected_status": "pass_task_shard_context_budget_social_draft_drift",
    },
    {
        "gate_id": "owner_publish_packet_contract",
        "command": [sys.executable, "scripts/check_task_shard_context_budget_owner_publish_packet_contract.py"],
        "expected_status": "pass_task_shard_context_budget_owner_publish_packet_contract",
    },
    {
        "gate_id": "publication_bundle",
        "command": [sys.executable, "scripts/build_task_shard_context_budget_publication_bundle.py"],
        "expected_status": "pass_task_shard_context_budget_publication_bundle",
    },
    {
        "gate_id": "live_publication_local",
        "command": [sys.executable, "scripts/check_task_shard_context_budget_live_publication.py"],
        "expected_status": "pass_task_shard_context_budget_live_publication_check",
    },
    {
        "gate_id": "unittest",
        "command": [sys.executable, "-m", "unittest", "tests.test_task_shard_context_budget_hn_candidate"],
        "expected_status": None,
    },
]


def main() -> int:
    checks = []
    errors = []
    for item in COMMANDS:
        result = subprocess.run(
            item["command"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        observed_status = _observed_json_status(result.stdout)
        ok = result.returncode == 0 and (
            item["expected_status"] is None or observed_status == item["expected_status"]
        )
        checks.append(
            {
                "gate_id": item["gate_id"],
                "command": item["command"],
                "returncode": result.returncode,
                "observed_status": observed_status,
                "expected_status": item["expected_status"],
                "status": "pass" if ok else "fail",
                "stdout_tail": result.stdout[-2000:],
                "stderr_tail": result.stderr[-2000:],
            }
        )
        if not ok:
            errors.append({"gate_id": item["gate_id"], "observed_status": observed_status, "returncode": result.returncode})

    payload = {
        "schema_id": "ctxgov.task-shard-context-budget-final-preflight/v0",
        "status": "pass_task_shard_context_budget_final_preflight" if not errors else "fail_task_shard_context_budget_final_preflight",
        "go_no_go": "go_local_ready_external_publish_pending" if not errors else "no_go",
        "checks": checks,
        "issue_count": len(errors),
        "issues": errors,
        "publication_executed": False,
        "outreach_performed": False,
        "commit_created": False,
        "push_executed": False,
        "release_created": False,
        "side_effect_boundary": {
            "workflow_executed": False,
            "worktree_created": False,
            "provider_or_model_call_performed": False,
            "target_file_written": False,
            "memory_backend_written": False,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _observed_json_status(text: str) -> str | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    status = payload.get("status")
    return str(status) if status is not None else None


if __name__ == "__main__":
    raise SystemExit(main())
