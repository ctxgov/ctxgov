from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.task_shard_context import (
    build_task_shard_context_budget_ledger_report,
    build_task_shard_context_rehearsal,
    build_task_shard_saved_trace_imports,
    evaluate_task_shard_fixture_pack,
    validate_task_shard_context_budget_ledger_report_file,
    validate_task_shard_context_budget_ledger_report_payload,
    validate_task_shard_context_rehearsal_file,
    validate_task_shard_context_rehearsal_payload,
    validate_task_shard_fixture_pack_file,
    validate_task_shard_import_shape_negative_fixture_file,
    validate_task_shard_import_shapes_file,
    validate_task_shard_saved_trace_imports_file,
    validate_task_shard_saved_trace_imports_payload,
)


BASE = ROOT / "fixtures" / "v0.7.0-mgp-sidecar" / "task-shard-context-control"
FIXTURE = BASE / "task-shard-context-control-fixture-pack-20260602.json"
IMPORT_SHAPES = BASE / "task-shard-context-import-shapes-20260602.json"
NEGATIVES = BASE / "task-shard-import-shape-negative-fixtures-20260602.json"
SAVED_IMPORTS = BASE / "task-shard-saved-trace-imports-20260602.json"
REHEARSAL = BASE / "task-shard-context-rehearsal-20260602.json"
BUDGET_LEDGER = BASE / "task-shard-context-budget-ledger-report-20260602.json"


FALSE_BOUNDARIES = [
    "live_workflow_executed",
    "worktree_created",
    "provider_or_model_call_performed",
    "runtime_or_adapter_executed",
    "target_file_written",
    "memory_backend_written",
    "memory_promotion_performed",
    "public_claim_created",
]


def main() -> int:
    errors: list[dict[str, str]] = []
    results = []

    fixture_validation = validate_task_shard_fixture_pack_file(FIXTURE, root=ROOT)
    _append_result(results, errors, "fixture_pack", fixture_validation)

    import_validation = validate_task_shard_import_shapes_file(IMPORT_SHAPES)
    _append_result(results, errors, "import_shapes", import_validation)

    negative_validation = validate_task_shard_import_shape_negative_fixture_file(NEGATIVES, root=ROOT)
    _append_result(results, errors, "import_shape_negatives", negative_validation)

    saved_trace_imports = build_task_shard_saved_trace_imports(
        IMPORT_SHAPES,
        checked_at="2026-06-02T20:20:00-07:00",
    )
    saved_trace_validation = validate_task_shard_saved_trace_imports_payload(saved_trace_imports)
    _append_result(results, errors, "saved_trace_imports_generated", saved_trace_validation)
    _append_result(results, errors, "saved_trace_imports_fixture", validate_task_shard_saved_trace_imports_file(SAVED_IMPORTS))

    rehearsal = build_task_shard_context_rehearsal(
        FIXTURE,
        root=ROOT,
        checked_at="2026-06-02T20:25:00-07:00",
    )
    _append_result(results, errors, "context_rehearsal_generated", validate_task_shard_context_rehearsal_payload(rehearsal))
    _append_result(results, errors, "context_rehearsal_fixture", validate_task_shard_context_rehearsal_file(REHEARSAL))

    budget = build_task_shard_context_budget_ledger_report(
        FIXTURE,
        root=ROOT,
        checked_at="2026-06-02T20:30:00-07:00",
    )
    _append_result(results, errors, "budget_ledger_generated", validate_task_shard_context_budget_ledger_report_payload(budget))
    _append_result(results, errors, "budget_ledger_fixture", validate_task_shard_context_budget_ledger_report_file(BUDGET_LEDGER))

    eval_report = evaluate_task_shard_fixture_pack(
        FIXTURE,
        root=ROOT,
        checked_at="2026-06-02T20:35:00-07:00",
    )
    if eval_report["status"] != "passed":
        errors.append({"gate_id": "task_shard_eval", "error": "task_shard_eval_failed"})
    results.append(
        {
            "gate_id": "task_shard_eval",
            "valid": eval_report["status"] == "passed",
            "status": eval_report["status"],
            "quality_metrics": eval_report["quality_metrics"],
        }
    )

    payload = {
        "schema_id": "ctxvault.task-shard-private-gate-result/v1",
        "status": "pass" if not errors else "fail",
        "gate_count": len(results),
        "results": results,
        "errors": errors,
        "public_benchmark_claim_created": False,
        "public_efficiency_claim_created": False,
        "public_adoption_claim_created": False,
        "package_or_workflow_created": False,
        "side_effect_boundary": {
            "private_gate_result_created": True,
            "local_fixtures_read": True,
            **{field: False for field in FALSE_BOUNDARIES},
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _append_result(results: list[dict], errors: list[dict[str, str]], gate_id: str, validation: dict) -> None:
    result = {
        "gate_id": gate_id,
        "valid": bool(validation.get("valid")),
        "status": validation.get("status"),
        "error_count": len(validation.get("errors", [])),
    }
    if "variant_count" in validation:
        result["variant_count"] = validation["variant_count"]
        result["variant_pass_count"] = validation.get("variant_pass_count")
    if "summary" in validation:
        result["summary"] = validation["summary"]
    results.append(result)
    if not validation.get("valid"):
        for error in validation.get("errors", []):
            errors.append({"gate_id": gate_id, "error": str(error)})


if __name__ == "__main__":
    raise SystemExit(main())
