from __future__ import annotations

import copy
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.task_shard_context import (
    build_task_shard_context_budget_public_report,
    validate_task_shard_context_budget_public_report_payload,
)


EXAMPLE = ROOT / "examples" / "task-shard-context-budget"
NEGATIVE_CASES = {
    "workflow_execution_flip": lambda payload: payload["side_effect_boundary"].update({"workflow_executed": True}),
    "worktree_created_flip": lambda payload: payload["side_effect_boundary"].update({"worktree_created": True}),
    "provider_call_flip": lambda payload: payload["side_effect_boundary"].update({"provider_or_model_call_performed": True}),
    "target_write_flip": lambda payload: payload["side_effect_boundary"].update({"target_file_written": True}),
    "benchmark_claim_flip": lambda payload: payload["claim_boundary"].update({"public_benchmark_claim_created": True}),
    "raw_content_included_flip": lambda payload: payload.update({"raw_content_included": True}),
}


def main() -> int:
    report = build_task_shard_context_budget_public_report(EXAMPLE)
    base_validation = validate_task_shard_context_budget_public_report_payload(report)
    errors: list[dict[str, object]] = []
    observed: list[str] = []
    case_results = []
    if not base_validation["valid"]:
        errors.append({"case_id": "base_report", "errors": base_validation["errors"]})

    for case_id, mutate in NEGATIVE_CASES.items():
        mutated = copy.deepcopy(report)
        mutate(mutated)
        validation = validate_task_shard_context_budget_public_report_payload(mutated)
        passed = not validation["valid"]
        if passed:
            observed.append(case_id)
        else:
            errors.append({"case_id": case_id, "errors": validation["errors"]})
        case_results.append(
            {
                "case_id": case_id,
                "passed": passed,
                "validation_status": validation["status"],
                "errors": validation["errors"],
            }
        )

    payload = {
        "schema_id": "ctxgov.task-shard-context-budget-report-contract/v0",
        "status": "pass_task_shard_context_budget_report_contract" if not errors else "fail_task_shard_context_budget_report_contract",
        "base_validation_status": base_validation["status"],
        "negative_case_count": len(NEGATIVE_CASES),
        "observed_rejection_modes": observed,
        "case_results": case_results,
        "errors": errors,
        "raw_content_included": False,
        "side_effect_boundary": report["side_effect_boundary"],
        "claim_boundary": report["claim_boundary"],
        "publication_executed": False,
        "outreach_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
