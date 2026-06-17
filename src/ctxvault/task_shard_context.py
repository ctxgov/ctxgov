from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


TASK_SHARD_FIXTURE_SCHEMA_ID = "ctxvault.task-shard-context-control-fixture-pack/v0"
TASK_SHARD_IMPORT_SHAPES_SCHEMA_ID = "ctxvault.task-shard-context-import-shapes/v0"
TASK_SHARD_EVAL_SCHEMA_ID = "ctxvault.task-shard-context-control-eval/v0"
TASK_SHARD_VALIDATE_SCHEMA_ID = "ctxvault.task-shard-context-control-validate-result/v0"
TASK_SHARD_IMPORT_VALIDATE_SCHEMA_ID = "ctxvault.task-shard-context-import-shapes-validate-result/v0"
TASK_SHARD_IMPORT_NEGATIVE_SCHEMA_ID = "ctxvault.task-shard-import-shape-negative-fixtures/v0"
TASK_SHARD_IMPORT_NEGATIVE_VALIDATE_SCHEMA_ID = "ctxvault.task-shard-import-shape-negative-fixtures-validate-result/v0"
TASK_SHARD_SAVED_TRACE_IMPORTS_SCHEMA_ID = "ctxvault.task-shard-saved-trace-imports/v0"
TASK_SHARD_SAVED_TRACE_IMPORTS_VALIDATE_SCHEMA_ID = "ctxvault.task-shard-saved-trace-imports-validate-result/v0"
TASK_SHARD_CONTEXT_REHEARSAL_SCHEMA_ID = "ctxvault.task-shard-context-rehearsal/v0"
TASK_SHARD_CONTEXT_REHEARSAL_VALIDATE_SCHEMA_ID = "ctxvault.task-shard-context-rehearsal-validate-result/v0"
TASK_SHARD_BUDGET_LEDGER_REPORT_SCHEMA_ID = "ctxvault.task-shard-context-budget-ledger-report/v0"
TASK_SHARD_BUDGET_LEDGER_REPORT_VALIDATE_SCHEMA_ID = "ctxvault.task-shard-context-budget-ledger-report-validate-result/v0"
TASK_SHARD_CONTEXT_BUDGET_PUBLIC_REPORT_SCHEMA_ID = "ctxgov.task-shard-context-budget-report/v0"

TASK_SHARD_QUALITY_METRICS = [
    "split_quality",
    "context_minimality",
    "merge_safety",
    "replan_accuracy",
]
EXPECTED_IMPORT_SURFACE_IDS = [
    "claude_dynamic_workflows",
    "cline_task_history",
    "openhands_condenser_trace",
    "aider_repo_map",
    "plandex_context_map",
]
FALSE_SIDE_EFFECTS = [
    "live_workflow_executed",
    "worktree_created",
    "provider_or_model_call_performed",
    "runtime_or_adapter_executed",
    "target_file_written",
    "memory_backend_written",
    "memory_promotion_performed",
    "public_claim_created",
]
FALSE_CLAIMS = [
    "public_benchmark_claim_allowed",
    "public_efficiency_claim_allowed",
    "public_adoption_claim_allowed",
    "public_compatibility_claim_allowed",
    "stable_mgp_claim_allowed",
]


def validate_task_shard_fixture_pack_payload(pack: dict[str, Any]) -> dict[str, Any]:
    """Validate the private Task Shard Context Control fixture shape without executing it."""
    errors: list[str] = []

    if pack.get("schema_id") != TASK_SHARD_FIXTURE_SCHEMA_ID:
        errors.append("schema_id mismatch")
    if pack.get("context_execution_gate") != "ContextExecutionAdmission":
        errors.append("context_execution_gate must be ContextExecutionAdmission")
    if pack.get("status") != "private_fixture_schema_only_no_runtime":
        errors.append("status must stay private fixture only")

    plan = pack.get("task_shard_plan", {}) if isinstance(pack.get("task_shard_plan"), dict) else {}
    shards = pack.get("shard_context_visas", [])
    if not isinstance(shards, list):
        errors.append("shard_context_visas must be a list")
        shards = []
    if plan.get("live_execution_allowed") is not False:
        errors.append("task_shard_plan.live_execution_allowed must be false")
    if plan.get("shard_count") != len(shards):
        errors.append("task_shard_plan.shard_count must match shard_context_visas")

    shard_ids = {shard.get("shard_id") for shard in shards if isinstance(shard, dict)}
    for shard in shards:
        if not isinstance(shard, dict):
            errors.append("shard_context_visas entries must be objects")
            continue
        shard_id = str(shard.get("shard_id") or "<missing>")
        selected = shard.get("selected_context_refs", [])
        if not selected:
            errors.append(f"{shard_id}: selected context refs required")
        if shard.get("live_execution_allowed") is not False:
            errors.append(f"{shard_id}: live execution must remain false")
        budget = shard.get("context_budget", {}) if isinstance(shard.get("context_budget"), dict) else {}
        if float(budget.get("estimated_tokens", 0)) > float(budget.get("max_tokens", 0)):
            errors.append(f"{shard_id}: estimated_tokens must be <= max_tokens")
        if shard.get("cache_stability", {}).get("cache_hit_is_authority") is not False:
            errors.append(f"{shard_id}: cache hits never grant authority")
        for dependency in shard.get("dependency_refs", []):
            if dependency not in shard_ids:
                errors.append(f"{shard_id}: unknown dependency {dependency}")
        compaction_loss = shard.get("compaction_loss", {}) if isinstance(shard.get("compaction_loss"), dict) else {}
        for field in ("decision_refs_preserved", "blockers_preserved", "source_refs_preserved"):
            if compaction_loss.get(field) is not True:
                errors.append(f"{shard_id}: {field} must be preserved")

    ledger = pack.get("context_budget_ledger", {}) if isinstance(pack.get("context_budget_ledger"), dict) else {}
    counts = _context_counts(shards)
    if ledger.get("total_estimated_tokens") != counts["total_estimated_tokens"]:
        errors.append("context_budget_ledger.total_estimated_tokens must match shards")
    if ledger.get("total_max_tokens") != counts["total_max_tokens"]:
        errors.append("context_budget_ledger.total_max_tokens must match shards")
    for field in ("selected_context_ref_count", "omitted_context_ref_count", "searchable_only_ref_count", "compacted_event_ref_count"):
        if ledger.get(field) != counts[field]:
            errors.append(f"context_budget_ledger.{field} must match shards")
    if ledger.get("larger_context_window_is_not_authority") is not True:
        errors.append("larger_context_window_is_not_authority must be true")
    if ledger.get("source_recovery_required") is not True:
        errors.append("source_recovery_required must be true")

    result_ids = {receipt.get("shard_id") for receipt in pack.get("shard_result_receipts", []) if isinstance(receipt, dict)}
    if result_ids != shard_ids:
        errors.append("shard_result_receipts must cover every shard")
    for receipt in pack.get("shard_result_receipts", []):
        if isinstance(receipt, dict) and receipt.get("execution_performed") is not False:
            errors.append(f"{receipt.get('shard_id')}: execution_performed must be false")

    for merge in pack.get("shard_merge_receipts", []):
        if not isinstance(merge, dict):
            errors.append("shard_merge_receipts entries must be objects")
            continue
        conflicts = merge.get("merge_conflict_refs", [])
        trigger = merge.get("replan_trigger", {}) if isinstance(merge.get("replan_trigger"), dict) else {}
        if conflicts and trigger.get("triggered") is not True:
            errors.append("merge conflicts require replan trigger")
        if merge.get("merge_approved") is not False:
            errors.append("merge_approved must remain false")

    gate = pack.get("benchmark_gate", {}) if isinstance(pack.get("benchmark_gate"), dict) else {}
    if gate.get("private_benchmark_only") is not True:
        errors.append("benchmark_gate.private_benchmark_only must be true")
    if gate.get("savings_counted_only_when_quality_passes") is not True:
        errors.append("savings_counted_only_when_quality_passes must be true")
    required_metrics = set(gate.get("required_metrics", [])) if isinstance(gate.get("required_metrics", []), list) else set()
    for metric in TASK_SHARD_QUALITY_METRICS:
        if metric not in required_metrics:
            errors.append(f"benchmark_gate.required_metrics must include {metric}")

    import_refs = pack.get("external_import_shape_refs", [])
    if import_refs and not isinstance(import_refs, list):
        errors.append("external_import_shape_refs must be a list")
        import_refs = []
    for ref in import_refs:
        if not isinstance(ref, dict):
            errors.append("external_import_shape_refs entries must be objects")
            continue
        if ref.get("schema_id") != TASK_SHARD_IMPORT_SHAPES_SCHEMA_ID:
            errors.append("external_import_shape_refs.schema_id mismatch")
        if not ref.get("path"):
            errors.append("external_import_shape_refs.path required")
        surfaces = ref.get("surface_ids", [])
        if not isinstance(surfaces, list) or not surfaces:
            errors.append("external_import_shape_refs.surface_ids required")

    for claim in FALSE_CLAIMS:
        if pack.get("claim_gate", {}).get(claim) is not False:
            errors.append(f"claim_gate.{claim} must remain false")
    for side_effect in FALSE_SIDE_EFFECTS:
        if pack.get("side_effect_boundary", {}).get(side_effect) is not False:
            errors.append(f"side_effect_boundary.{side_effect} must remain false")

    return {
        "schema_id": TASK_SHARD_VALIDATE_SCHEMA_ID,
        "object_type": "TaskShardContextControlValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "summary": _fixture_summary(pack),
        "side_effect_boundary": _side_effect_boundary(
            validation_created=True,
            fixture_read=False,
            import_shape_read=False,
        ),
    }


def validate_task_shard_fixture_pack_file(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    resolved = path.resolve()
    errors: list[str] = []
    try:
        pack = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - JSON parser wording varies
        pack = {}
        errors.append(f"failed to parse JSON: {exc}")
    result = validate_task_shard_fixture_pack_payload(pack)
    result["path"] = str(resolved)
    result["sha256"] = _sha256(resolved) if resolved.exists() and resolved.is_file() else None

    root_path = root.resolve() if root else _default_root_for_fixture(resolved)
    import_validations = _validate_external_import_refs(pack, root_path=root_path)
    result["import_shape_validations"] = import_validations
    for item in import_validations:
        if not item.get("valid"):
            errors.extend([f"{item.get('source_ref')}: {error}" for error in item.get("errors", [])])
    if errors:
        result["errors"].extend(errors)
        result["valid"] = False
        result["status"] = "invalid"
    result["summary"] = _fixture_summary(pack, import_validations=import_validations)
    result["side_effect_boundary"] = _side_effect_boundary(
        validation_created=True,
        fixture_read=True,
        import_shape_read=bool(import_validations),
    )
    return result


def validate_task_shard_import_shapes_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema_id") != TASK_SHARD_IMPORT_SHAPES_SCHEMA_ID:
        errors.append(f"unsupported schema_id: {payload.get('schema_id')}")
    if payload.get("object_type") != "TaskShardContextImportShapes":
        errors.append("object_type must be TaskShardContextImportShapes")
    if payload.get("status") != "private_import_shape_only_no_runtime":
        errors.append("status must stay private import shape only")
    if not payload.get("source_refs"):
        errors.append("source_refs required")
    shapes = payload.get("import_shapes", [])
    if not isinstance(shapes, list) or not shapes:
        errors.append("import_shapes must be a non-empty list")
        shapes = []

    found_surface_ids = set()
    for shape in shapes:
        if not isinstance(shape, dict):
            errors.append("import_shapes entries must be objects")
            continue
        surface_id = str(shape.get("import_surface_id") or "")
        found_surface_ids.add(surface_id)
        if shape.get("runtime_execution_allowed") is not False:
            errors.append(f"{surface_id}: runtime_execution_allowed must be false")
        if not shape.get("expected_artifacts"):
            errors.append(f"{surface_id}: expected_artifacts required")
        if not shape.get("mapped_read_models"):
            errors.append(f"{surface_id}: mapped_read_models required")
        contract = shape.get("context_ref_contract", {}) if isinstance(shape.get("context_ref_contract"), dict) else {}
        if not contract.get("selected_source_ref_fields"):
            errors.append(f"{surface_id}: context_ref_contract.selected_source_ref_fields required")
        if not contract.get("omitted_context_ref_fields"):
            errors.append(f"{surface_id}: context_ref_contract.omitted_context_ref_fields required")
        if contract.get("source_recovery_required") is not True:
            errors.append(f"{surface_id}: context_ref_contract.source_recovery_required must be true")
        if contract.get("omitted_context_visible") is not True:
            errors.append(f"{surface_id}: context_ref_contract.omitted_context_visible must be true")
        for side_effect in FALSE_SIDE_EFFECTS:
            if shape.get("side_effect_boundary", {}).get(side_effect) is not False:
                errors.append(f"{surface_id}: side_effect_boundary.{side_effect} must remain false")
        for claim in FALSE_CLAIMS:
            if shape.get("claim_gate", {}).get(claim) is not False:
                errors.append(f"{surface_id}: claim_gate.{claim} must remain false")

    missing = [surface_id for surface_id in EXPECTED_IMPORT_SURFACE_IDS if surface_id not in found_surface_ids]
    for surface_id in missing:
        errors.append(f"missing expected import surface: {surface_id}")
    for side_effect in FALSE_SIDE_EFFECTS:
        if payload.get("side_effect_boundary", {}).get(side_effect) is not False:
            errors.append(f"side_effect_boundary.{side_effect} must remain false")

    return {
        "schema_id": TASK_SHARD_IMPORT_VALIDATE_SCHEMA_ID,
        "object_type": "TaskShardContextImportShapesValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "summary": {
            "import_shape_count": len(shapes),
            "expected_surface_count": len(EXPECTED_IMPORT_SURFACE_IDS),
            "covered_surface_ids": sorted(found_surface_ids),
            "missing_surface_ids": missing,
        },
        "side_effect_boundary": _side_effect_boundary(
            validation_created=True,
            fixture_read=False,
            import_shape_read=False,
        ),
    }


def validate_task_shard_import_shapes_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    errors: list[str] = []
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - JSON parser wording varies
        payload = {}
        errors.append(f"failed to parse JSON: {exc}")
    result = validate_task_shard_import_shapes_payload(payload)
    result["path"] = str(resolved)
    result["sha256"] = _sha256(resolved) if resolved.exists() and resolved.is_file() else None
    if errors:
        result["errors"].extend(errors)
        result["valid"] = False
        result["status"] = "invalid"
    result["side_effect_boundary"] = _side_effect_boundary(
        validation_created=True,
        fixture_read=False,
        import_shape_read=True,
    )
    return result


def validate_task_shard_import_shape_negative_fixture_file(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    resolved = path.resolve()
    errors: list[str] = []
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - JSON parser wording varies
        payload = {}
        errors.append(f"failed to parse JSON: {exc}")
    if payload.get("schema_id") != TASK_SHARD_IMPORT_NEGATIVE_SCHEMA_ID:
        errors.append(f"unsupported schema_id: {payload.get('schema_id')}")
    if payload.get("status") != "private_negative_fixture_only_no_runtime":
        errors.append("status must stay private negative fixture only")
    root_path = root.resolve() if root else _default_root_for_fixture(resolved)
    source_ref = Path(str(payload.get("source_import_shapes_path") or ""))
    source_path = source_ref.resolve() if source_ref.is_absolute() else (root_path / source_ref).resolve()
    if not source_path.exists():
        errors.append("source_import_shapes_path does not exist")
        source_payload: dict[str, Any] = {}
    else:
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))

    variant_results = []
    variants = payload.get("variants", [])
    if not isinstance(variants, list) or not variants:
        errors.append("variants must be a non-empty list")
        variants = []
    if payload.get("variant_count") != len(variants):
        errors.append("variant_count must match variants")
    for variant in variants:
        if not isinstance(variant, dict):
            errors.append("variants entries must be objects")
            continue
        variant_id = str(variant.get("variant_id") or "")
        expected_error = str(variant.get("expected_error") or "")
        mutated = copy.deepcopy(source_payload)
        _apply_import_shape_negative_variant(mutated, variant_id)
        validation = validate_task_shard_import_shapes_payload(mutated)
        matched = bool(expected_error) and any(expected_error in error for error in validation["errors"])
        variant_results.append(
            {
                "variant_id": variant_id,
                "expected_error": expected_error,
                "valid": validation["valid"],
                "matched_expected_error": matched,
                "errors": validation["errors"],
            }
        )
        if validation["valid"]:
            errors.append(f"{variant_id}: negative variant unexpectedly passed")
        if not matched:
            errors.append(f"{variant_id}: expected error not observed: {expected_error}")

    return {
        "schema_id": TASK_SHARD_IMPORT_NEGATIVE_VALIDATE_SCHEMA_ID,
        "object_type": "TaskShardImportShapeNegativeFixturesValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "path": str(resolved),
        "source_import_shapes_path": str(source_path),
        "variant_count": len(variant_results),
        "variant_pass_count": sum(1 for result in variant_results if result["matched_expected_error"] and not result["valid"]),
        "variant_results": variant_results,
        "errors": errors,
        "side_effect_boundary": _side_effect_boundary(
            validation_created=True,
            fixture_read=True,
            import_shape_read=True,
        ),
    }


def build_task_shard_saved_trace_imports(
    import_shapes_path: Path,
    *,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = import_shapes_path.resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    validation = validate_task_shard_import_shapes_payload(payload)
    if not validation["valid"]:
        raise ValueError("task shard import shapes invalid: " + "; ".join(validation["errors"]))
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    imports = []
    for shape in payload["import_shapes"]:
        contract = shape["context_ref_contract"]
        surface_id = str(shape["import_surface_id"])
        imports.append(
            {
                "object_type": "TaskShardSavedTraceImport",
                "import_id": f"{surface_id}_saved_trace_fixture_import_20260602",
                "source_import_surface_id": surface_id,
                "surface_family": shape.get("surface_family"),
                "import_status": "fixture_imported_no_runtime",
                "source_artifact_refs": [
                    f"{surface_id}:{artifact}"
                    for artifact in shape.get("expected_artifacts", [])
                ],
                "normalized_read_models": shape.get("mapped_read_models", []),
                "selected_source_refs": contract.get("selected_source_ref_fields", []),
                "omitted_context_refs": contract.get("omitted_context_ref_fields", []),
                "blocked_authority": shape.get("blocked_authority", []),
                "runtime_execution_allowed": False,
                "trace_execution_performed": False,
                "provider_or_model_call_performed": False,
                "target_file_written": False,
                "memory_backend_written": False,
                "public_claim_created": False,
            }
        )
    return {
        "schema_id": TASK_SHARD_SAVED_TRACE_IMPORTS_SCHEMA_ID,
        "object_type": "TaskShardSavedTraceImports",
        "version": "post-v0.7.0",
        "status": "private_saved_trace_import_fixture_no_runtime",
        "created_at": checked_at,
        "source_import_shapes": {
            "path": str(resolved),
            "sha256": _sha256(resolved),
            "validation_status": validation["status"],
            "validation_error_count": len(validation["errors"]),
        },
        "saved_trace_imports": imports,
        "summary": {
            "import_count": len(imports),
            "surface_ids": [item["source_import_surface_id"] for item in imports],
            "runtime_execution_allowed": False,
            "trace_execution_performed": False,
        },
        "claim_gate": _claim_gate(),
        "side_effect_boundary": _side_effect_boundary(
            eval_created=True,
            fixture_read=True,
            import_shape_read=True,
        ),
        "rollback": {
            "mode": "discard_task_shard_saved_trace_imports",
            "delete_paths": [],
            "external_state_to_revert": "none",
        },
    }


def validate_task_shard_saved_trace_imports_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema_id") != TASK_SHARD_SAVED_TRACE_IMPORTS_SCHEMA_ID:
        errors.append(f"unsupported schema_id: {payload.get('schema_id')}")
    if payload.get("status") != "private_saved_trace_import_fixture_no_runtime":
        errors.append("status must stay private saved-trace import fixture")
    source = payload.get("source_import_shapes", {})
    if not isinstance(source, dict) or source.get("validation_status") != "valid" or source.get("validation_error_count") != 0:
        errors.append("source_import_shapes must reference a valid import-shapes fixture")
    source_contracts = _saved_trace_import_contracts_from_source(payload, errors)
    imports = payload.get("saved_trace_imports", [])
    if not isinstance(imports, list) or not imports:
        errors.append("saved_trace_imports must be a non-empty list")
        imports = []
    surface_ids = set()
    for item in imports:
        if not isinstance(item, dict):
            errors.append("saved_trace_imports entries must be objects")
            continue
        surface_id = str(item.get("source_import_surface_id") or "")
        surface_ids.add(surface_id)
        if item.get("object_type") != "TaskShardSavedTraceImport":
            errors.append(f"{surface_id}: object_type must be TaskShardSavedTraceImport")
        if item.get("import_status") != "fixture_imported_no_runtime":
            errors.append(f"{surface_id}: import_status must be fixture_imported_no_runtime")
        if item.get("runtime_execution_allowed") is not False:
            errors.append(f"{surface_id}: runtime_execution_allowed must be false")
        for field in [
            "trace_execution_performed",
            "provider_or_model_call_performed",
            "target_file_written",
            "memory_backend_written",
            "public_claim_created",
        ]:
            if item.get(field) is not False:
                errors.append(f"{surface_id}: {field} must remain false")
        if not item.get("selected_source_refs"):
            errors.append(f"{surface_id}: selected_source_refs required")
        if not item.get("omitted_context_refs"):
            errors.append(f"{surface_id}: omitted_context_refs required")
        if not item.get("normalized_read_models"):
            errors.append(f"{surface_id}: normalized_read_models required")
        if surface_id in source_contracts:
            expected = source_contracts[surface_id]
            for field in [
                "surface_family",
                "source_artifact_refs",
                "normalized_read_models",
                "selected_source_refs",
                "omitted_context_refs",
                "blocked_authority",
            ]:
                if item.get(field) != expected[field]:
                    errors.append(f"{surface_id}: {field} must match import shape contract")
    for surface_id in EXPECTED_IMPORT_SURFACE_IDS:
        if surface_id not in surface_ids:
            errors.append(f"missing saved trace import surface: {surface_id}")
    _append_boundary_errors(errors, payload.get("side_effect_boundary", {}))
    return {
        "schema_id": TASK_SHARD_SAVED_TRACE_IMPORTS_VALIDATE_SCHEMA_ID,
        "object_type": "TaskShardSavedTraceImportsValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "summary": {
            "import_count": len(imports),
            "surface_ids": sorted(surface_ids),
            "contract_matched_surface_count": sum(1 for surface_id in surface_ids if surface_id in source_contracts),
        },
        "side_effect_boundary": _side_effect_boundary(
            validation_created=True,
            fixture_read=True,
            import_shape_read=False,
        ),
    }


def validate_task_shard_saved_trace_imports_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    result = validate_task_shard_saved_trace_imports_payload(payload)
    result["path"] = str(resolved)
    result["sha256"] = _sha256(resolved)
    return result


def _saved_trace_import_contracts_from_source(
    payload: dict[str, Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    source = payload.get("source_import_shapes", {})
    if not isinstance(source, dict):
        return {}
    raw_path = Path(str(source.get("path") or ""))
    if not str(raw_path):
        errors.append("source_import_shapes.path required")
        return {}
    resolved = _resolve_import_shape_source_path(raw_path)
    if not resolved.exists():
        errors.append("source_import_shapes.path does not exist")
        return {}
    expected_sha = source.get("sha256")
    actual_sha = _sha256(resolved)
    if expected_sha and expected_sha != actual_sha:
        errors.append("source_import_shapes.sha256 mismatch")
    try:
        source_payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - JSON parser wording varies
        errors.append(f"source_import_shapes failed to parse JSON: {exc}")
        return {}
    validation = validate_task_shard_import_shapes_payload(source_payload)
    if not validation["valid"]:
        errors.append("source_import_shapes.path must reference a valid import-shapes fixture")
        errors.extend([f"source_import_shapes: {error}" for error in validation["errors"]])
        return {}
    contracts: dict[str, dict[str, Any]] = {}
    for shape in source_payload.get("import_shapes", []):
        if not isinstance(shape, dict):
            continue
        surface_id = str(shape.get("import_surface_id") or "")
        contract = shape.get("context_ref_contract", {}) if isinstance(shape.get("context_ref_contract"), dict) else {}
        contracts[surface_id] = {
            "surface_family": shape.get("surface_family"),
            "source_artifact_refs": [
                f"{surface_id}:{artifact}"
                for artifact in shape.get("expected_artifacts", [])
            ],
            "normalized_read_models": shape.get("mapped_read_models", []),
            "selected_source_refs": contract.get("selected_source_ref_fields", []),
            "omitted_context_refs": contract.get("omitted_context_ref_fields", []),
            "blocked_authority": shape.get("blocked_authority", []),
        }
    return contracts


def _resolve_import_shape_source_path(raw_path: Path) -> Path:
    if raw_path.exists():
        return raw_path.resolve()
    parts = raw_path.parts
    if "fixtures" in parts:
        fixture_index = parts.index("fixtures")
        candidate = Path.cwd() / Path(*parts[fixture_index:])
        if candidate.exists():
            return candidate.resolve()
    return raw_path.resolve()


def evaluate_task_shard_fixture_pack(
    path: Path,
    *,
    root: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = path.resolve()
    pack = json.loads(resolved.read_text(encoding="utf-8"))
    validation = validate_task_shard_fixture_pack_file(resolved, root=root)
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    quality = _quality_scores(pack, validation)
    all_quality_passed = validation["valid"] and all(score >= 1.0 for score in quality.values())
    import_validations = validation.get("import_shape_validations", [])
    summary = _fixture_summary(pack, import_validations=import_validations)
    return {
        "schema_id": TASK_SHARD_EVAL_SCHEMA_ID,
        "object_type": "TaskShardContextControlEvalReceipt",
        "version": "post-v0.7.0",
        "status": "passed" if all_quality_passed else "failed",
        "created_at": checked_at,
        "fixture": {
            "path": str(resolved),
            "sha256": _sha256(resolved),
            "schema_id": pack.get("schema_id"),
            "status": pack.get("status"),
        },
        "summary": summary,
        "quality_metrics": quality,
        "quality_gate": {
            "required_metrics": TASK_SHARD_QUALITY_METRICS,
            "minimum_score": 1.0,
            "all_required_metrics_passed": all_quality_passed,
            "savings_counted_only_when_quality_passes": True,
            "oss_efficiency_gate_compatible": True,
        },
        "validation": {
            "valid": validation["valid"],
            "status": validation["status"],
            "errors": validation["errors"],
        },
        "import_shape_validations": import_validations,
        "claim_gate": _claim_gate(),
        "side_effect_boundary": _side_effect_boundary(
            eval_created=True,
            fixture_read=True,
            import_shape_read=bool(import_validations),
        ),
        "rollback": {
            "mode": "discard_task_shard_eval_receipt",
            "delete_paths": [],
            "external_state_to_revert": "none",
        },
    }


def build_task_shard_context_rehearsal(
    path: Path,
    *,
    root: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = path.resolve()
    pack = json.loads(resolved.read_text(encoding="utf-8"))
    validation = validate_task_shard_fixture_pack_file(resolved, root=root)
    if not validation["valid"]:
        raise ValueError("task shard fixture invalid: " + "; ".join(validation["errors"]))
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    packets = [_shard_context_packet(shard) for shard in pack.get("shard_context_visas", [])]
    blocked_operation_count = sum(
        1
        for packet in packets
        for operation in packet["blocked_live_operation_transcript"]
        if operation["status"] == "blocked_until_owner_approval"
    )
    rehearsal = {
        "schema_id": TASK_SHARD_CONTEXT_REHEARSAL_SCHEMA_ID,
        "object_type": "TaskShardContextRehearsal",
        "version": "post-v0.7.0",
        "status": "private_shard_context_rehearsal_no_runtime_no_injection",
        "created_at": checked_at,
        "source_fixture": {
            "path": str(resolved),
            "sha256": _sha256(resolved),
            "validation_status": validation["status"],
            "validation_error_count": len(validation["errors"]),
        },
        "shard_context_packets": packets,
        "rehearsal_result": {
            "packet_count": len(packets),
            "blocked_operation_count": blocked_operation_count,
            "context_injection_executed": False,
            "runtime_or_adapter_executed": False,
            "target_file_written": False,
            "memory_backend_written": False,
            "public_claim_created": False,
        },
        "claim_gate": _claim_gate(),
        "side_effect_boundary": _side_effect_boundary(
            eval_created=True,
            fixture_read=True,
            import_shape_read=False,
        ),
        "rollback": {
            "mode": "discard_task_shard_context_rehearsal",
            "delete_paths": [],
            "external_state_to_revert": "none",
        },
    }
    rehearsal["rehearsal_sha256"] = _stable_payload_hash(rehearsal)
    return rehearsal


def validate_task_shard_context_rehearsal_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema_id") != TASK_SHARD_CONTEXT_REHEARSAL_SCHEMA_ID:
        errors.append(f"unsupported schema_id: {payload.get('schema_id')}")
    if payload.get("status") != "private_shard_context_rehearsal_no_runtime_no_injection":
        errors.append("status must remain private shard context rehearsal")
    expected_hash = _stable_payload_hash(payload)
    if payload.get("rehearsal_sha256") != expected_hash:
        errors.append("rehearsal_sha256 mismatch")
    source = payload.get("source_fixture", {})
    if not isinstance(source, dict) or source.get("validation_status") != "valid" or source.get("validation_error_count") != 0:
        errors.append("source_fixture must reference a valid Task Shard fixture")
    packets = payload.get("shard_context_packets", [])
    if not isinstance(packets, list) or not packets:
        errors.append("shard_context_packets must be a non-empty list")
        packets = []
    blocked_count = 0
    for packet in packets:
        if not isinstance(packet, dict):
            errors.append("shard_context_packets entries must be objects")
            continue
        shard_id = str(packet.get("shard_id") or "")
        if not packet.get("selected_context_refs"):
            errors.append(f"{shard_id}: selected_context_refs required")
        if not packet.get("omitted_context_refs"):
            errors.append(f"{shard_id}: omitted_context_refs required")
        if packet.get("context_injection_executed") is not False:
            errors.append(f"{shard_id}: context_injection_executed must be false")
        if not packet.get("minimal_context_packet", {}).get("packet_sha256"):
            errors.append(f"{shard_id}: minimal_context_packet.packet_sha256 required")
        operations = packet.get("blocked_live_operation_transcript", [])
        if not isinstance(operations, list) or not operations:
            errors.append(f"{shard_id}: blocked_live_operation_transcript required")
            operations = []
        for operation in operations:
            if not isinstance(operation, dict):
                errors.append(f"{shard_id}: transcript operations must be objects")
                continue
            if operation.get("status") == "blocked_until_owner_approval":
                blocked_count += 1
                if operation.get("current_allowed_without_approval") is not False:
                    errors.append(f"{shard_id}: blocked operations must not be allowed without approval")
            if operation.get("status") == "completed_local_preview" and operation.get("current_allowed_without_approval") is not True:
                errors.append(f"{shard_id}: local preview operations must be allowed")
    result = payload.get("rehearsal_result", {})
    if isinstance(result, dict):
        if result.get("packet_count") != len(packets):
            errors.append("rehearsal_result.packet_count mismatch")
        if result.get("blocked_operation_count") != blocked_count:
            errors.append("rehearsal_result.blocked_operation_count mismatch")
        for field in [
            "context_injection_executed",
            "runtime_or_adapter_executed",
            "target_file_written",
            "memory_backend_written",
            "public_claim_created",
        ]:
            if result.get(field) is not False:
                errors.append(f"rehearsal_result.{field} must remain false")
    else:
        errors.append("rehearsal_result must be an object")
    _append_boundary_errors(errors, payload.get("side_effect_boundary", {}))
    return {
        "schema_id": TASK_SHARD_CONTEXT_REHEARSAL_VALIDATE_SCHEMA_ID,
        "object_type": "TaskShardContextRehearsalValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "summary": {
            "packet_count": len(packets),
            "blocked_operation_count": blocked_count,
        },
        "side_effect_boundary": _side_effect_boundary(
            validation_created=True,
            fixture_read=True,
            import_shape_read=False,
        ),
    }


def validate_task_shard_context_rehearsal_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    result = validate_task_shard_context_rehearsal_payload(payload)
    result["path"] = str(resolved)
    result["sha256"] = _sha256(resolved)
    return result


def build_task_shard_context_budget_ledger_report(
    path: Path,
    *,
    root: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = path.resolve()
    pack = json.loads(resolved.read_text(encoding="utf-8"))
    validation = validate_task_shard_fixture_pack_file(resolved, root=root)
    if not validation["valid"]:
        raise ValueError("task shard fixture invalid: " + "; ".join(validation["errors"]))
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    ledger = pack["context_budget_ledger"]
    shard_cards = [_shard_budget_card(shard) for shard in pack.get("shard_context_visas", [])]
    total_estimated = float(ledger.get("total_estimated_tokens", 0))
    total_max = float(ledger.get("total_max_tokens", 0))
    return {
        "schema_id": TASK_SHARD_BUDGET_LEDGER_REPORT_SCHEMA_ID,
        "object_type": "TaskShardContextBudgetLedgerReport",
        "version": "post-v0.7.0",
        "status": "private_budget_ledger_report_no_runtime",
        "created_at": checked_at,
        "source_fixture": {
            "path": str(resolved),
            "sha256": _sha256(resolved),
            "validation_status": validation["status"],
            "validation_error_count": len(validation["errors"]),
        },
        "summary": {
            "shard_count": len(shard_cards),
            "total_estimated_tokens": int(total_estimated),
            "total_max_tokens": int(total_max),
            "total_budget_pressure_ratio": _ratio(total_estimated, total_max),
            "selected_context_ref_count": ledger.get("selected_context_ref_count"),
            "omitted_context_ref_count": ledger.get("omitted_context_ref_count"),
            "searchable_only_ref_count": ledger.get("searchable_only_ref_count"),
            "compacted_event_ref_count": ledger.get("compacted_event_ref_count"),
            "larger_context_window_is_not_authority": ledger.get("larger_context_window_is_not_authority"),
            "source_recovery_required": ledger.get("source_recovery_required"),
            "cache_hit_is_authority_count": sum(1 for card in shard_cards if card["cache_hit_is_authority"]),
            "compaction_source_loss_count": sum(1 for card in shard_cards if not card["source_refs_preserved"]),
        },
        "shard_budget_cards": shard_cards,
        "performance_design_notes": [
            "Token savings are not counted unless Task Shard quality gates pass.",
            "Cache stability can reduce cost but never grants authority.",
            "Source recovery and omitted-context visibility are treated as quality gates, not UX decoration.",
        ],
        "claim_gate": _claim_gate(),
        "side_effect_boundary": _side_effect_boundary(
            eval_created=True,
            fixture_read=True,
            import_shape_read=False,
        ),
        "rollback": {
            "mode": "discard_task_shard_budget_ledger_report",
            "delete_paths": [],
            "external_state_to_revert": "none",
        },
    }


def validate_task_shard_context_budget_ledger_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema_id") != TASK_SHARD_BUDGET_LEDGER_REPORT_SCHEMA_ID:
        errors.append(f"unsupported schema_id: {payload.get('schema_id')}")
    if payload.get("status") != "private_budget_ledger_report_no_runtime":
        errors.append("status must remain private budget ledger report")
    source = payload.get("source_fixture", {})
    if not isinstance(source, dict) or source.get("validation_status") != "valid" or source.get("validation_error_count") != 0:
        errors.append("source_fixture must reference a valid Task Shard fixture")
    summary = payload.get("summary", {})
    if isinstance(summary, dict):
        if summary.get("larger_context_window_is_not_authority") is not True:
            errors.append("summary.larger_context_window_is_not_authority must be true")
        if summary.get("source_recovery_required") is not True:
            errors.append("summary.source_recovery_required must be true")
        if int(summary.get("cache_hit_is_authority_count") or 0) != 0:
            errors.append("summary.cache_hit_is_authority_count must be 0")
        if int(summary.get("compaction_source_loss_count") or 0) != 0:
            errors.append("summary.compaction_source_loss_count must be 0")
    else:
        errors.append("summary must be an object")
    cards = payload.get("shard_budget_cards", [])
    if not isinstance(cards, list) or not cards:
        errors.append("shard_budget_cards must be a non-empty list")
        cards = []
    for card in cards:
        if not isinstance(card, dict):
            errors.append("shard_budget_cards entries must be objects")
            continue
        shard_id = str(card.get("shard_id") or "")
        if card.get("estimated_tokens", 0) > card.get("max_tokens", 0):
            errors.append(f"{shard_id}: estimated_tokens must be <= max_tokens")
        if card.get("cache_hit_is_authority") is not False:
            errors.append(f"{shard_id}: cache_hit_is_authority must be false")
        for field in ["decision_refs_preserved", "blockers_preserved", "source_refs_preserved"]:
            if card.get(field) is not True:
                errors.append(f"{shard_id}: {field} must be true")
    _append_boundary_errors(errors, payload.get("side_effect_boundary", {}))
    return {
        "schema_id": TASK_SHARD_BUDGET_LEDGER_REPORT_VALIDATE_SCHEMA_ID,
        "object_type": "TaskShardContextBudgetLedgerReportValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "summary": {
            "shard_count": len(cards),
            "total_budget_pressure_ratio": summary.get("total_budget_pressure_ratio") if isinstance(summary, dict) else None,
        },
        "side_effect_boundary": _side_effect_boundary(
            validation_created=True,
            fixture_read=True,
            import_shape_read=False,
        ),
    }


def validate_task_shard_context_budget_ledger_report_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    result = validate_task_shard_context_budget_ledger_report_payload(payload)
    result["path"] = str(resolved)
    result["sha256"] = _sha256(resolved)
    return result


def build_task_shard_context_budget_public_report(
    input_path: Path,
    *,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Build a public-safe Task Shard context budget report from a saved plan."""
    resolved = _resolve_task_shard_context_budget_input(input_path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    errors = _validate_public_task_shard_context_budget_example(payload)
    if errors:
        raise ValueError("task shard context budget example invalid: " + "; ".join(errors))

    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    shard_cards = [_public_task_shard_card(shard) for shard in payload.get("shards", [])]
    total_max_tokens = sum(card["max_tokens"] for card in shard_cards)
    total_estimated_tokens = sum(card["estimated_tokens"] for card in shard_cards)
    selected_count = sum(len(card["selected_context_refs"]) for card in shard_cards)
    omitted_count = sum(len(card["omitted_context_refs"]) for card in shard_cards)
    searchable_count = sum(len(card["searchable_only_refs"]) for card in shard_cards)
    compacted_count = sum(len(card["compacted_event_refs"]) for card in shard_cards)
    report = {
        "schema_id": TASK_SHARD_CONTEXT_BUDGET_PUBLIC_REPORT_SCHEMA_ID,
        "object_type": "TaskShardContextBudgetReport",
        "milestone": "Task Shard Context Budget Ledger",
        "status": "pass_task_shard_context_budget_report",
        "created_at": checked_at,
        "source_example": {
            "path": _repo_relative_or_name(resolved),
            "sha256": _sha256(resolved),
            "schema_id": payload.get("schema_id"),
            "example_id": payload.get("example_id"),
        },
        "task": payload.get("task"),
        "summary": {
            "shard_count": len(shard_cards),
            "total_estimated_tokens": total_estimated_tokens,
            "total_max_tokens": total_max_tokens,
            "total_budget_pressure_ratio": _ratio(float(total_estimated_tokens), float(total_max_tokens)),
            "selected_context_ref_count": selected_count,
            "omitted_context_ref_count": omitted_count,
            "searchable_only_ref_count": searchable_count,
            "compacted_event_ref_count": compacted_count,
            "cache_hit_is_not_authority": True,
            "merge_replan_gate_required": True,
            "raw_content_included": False,
        },
        "shard_budget_cards": shard_cards,
        "risk_cards": _public_task_shard_risk_cards(shard_cards),
        "side_effect_boundary": _public_task_shard_side_effect_boundary(),
        "claim_boundary": _public_task_shard_claim_boundary(),
        "raw_content_included": False,
        "rollback": {
            "mode": "discard_local_task_shard_context_budget_reports",
            "external_state_to_revert": "none",
        },
    }
    report["report_sha256"] = _stable_payload_hash(report)
    return report


def validate_task_shard_context_budget_public_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("schema_id") != TASK_SHARD_CONTEXT_BUDGET_PUBLIC_REPORT_SCHEMA_ID:
        errors.append(f"unsupported schema_id: {payload.get('schema_id')}")
    if payload.get("status") != "pass_task_shard_context_budget_report":
        errors.append("status must be pass_task_shard_context_budget_report")
    expected_hash = _stable_payload_hash(payload)
    if payload.get("report_sha256") != expected_hash:
        errors.append("report_sha256 mismatch")
    if payload.get("raw_content_included") is not False:
        errors.append("raw_content_included must remain false")
    source = payload.get("source_example", {})
    if not isinstance(source, dict) or not source.get("sha256"):
        errors.append("source_example.sha256 required")
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        summary = {}
    if summary.get("cache_hit_is_not_authority") is not True:
        errors.append("summary.cache_hit_is_not_authority must be true")
    if summary.get("merge_replan_gate_required") is not True:
        errors.append("summary.merge_replan_gate_required must be true")
    if summary.get("raw_content_included") is not False:
        errors.append("summary.raw_content_included must remain false")

    cards = payload.get("shard_budget_cards", [])
    if not isinstance(cards, list) or not cards:
        errors.append("shard_budget_cards must be a non-empty list")
        cards = []
    for card in cards:
        if not isinstance(card, dict):
            errors.append("shard_budget_cards entries must be objects")
            continue
        shard_id = str(card.get("shard_id") or "<missing>")
        if not card.get("selected_context_refs"):
            errors.append(f"{shard_id}: selected_context_refs required")
        if not card.get("omitted_context_refs"):
            errors.append(f"{shard_id}: omitted_context_refs required")
        if not card.get("searchable_only_refs"):
            errors.append(f"{shard_id}: searchable_only_refs required")
        if not card.get("compacted_event_refs"):
            errors.append(f"{shard_id}: compacted_event_refs required")
        if int(card.get("estimated_tokens") or 0) > int(card.get("max_tokens") or 0):
            errors.append(f"{shard_id}: estimated_tokens must be <= max_tokens")
        if card.get("cache_hit_is_authority") is not False:
            errors.append(f"{shard_id}: cache_hit_is_authority must be false")
        if card.get("cache_hit_is_not_authority") is not True:
            errors.append(f"{shard_id}: cache_hit_is_not_authority must be true")
        if card.get("merge_replan_gate_required") is not True:
            errors.append(f"{shard_id}: merge_replan_gate_required must be true")
        if card.get("raw_content_included") is not False:
            errors.append(f"{shard_id}: raw_content_included must remain false")

    boundary = payload.get("side_effect_boundary", {})
    for field in [
        "workflow_executed",
        "worktree_created",
        "provider_or_model_call_performed",
        "target_file_written",
        "memory_backend_written",
    ]:
        if not isinstance(boundary, dict) or boundary.get(field) is not False:
            errors.append(f"side_effect_boundary.{field} must remain false")
    claims = payload.get("claim_boundary", {})
    for field in [
        "public_benchmark_claim_created",
        "public_savings_claim_created",
        "public_adoption_claim_created",
        "public_security_claim_created",
        "public_compatibility_claim_created",
        "public_support_claim_created",
        "stable_protocol_claim_created",
    ]:
        if not isinstance(claims, dict) or claims.get(field) is not False:
            errors.append(f"claim_boundary.{field} must remain false")
    return {
        "schema_id": "ctxgov.task-shard-context-budget-report-validate-result/v0",
        "object_type": "TaskShardContextBudgetReportValidateResult",
        "valid": not errors,
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "summary": {
            "shard_count": len(cards),
            "error_count": len(errors),
        },
        "side_effect_boundary": _public_task_shard_side_effect_boundary(),
    }


def render_task_shard_context_budget_public_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Task Shard Context Budget Ledger",
        "",
        f"Status: `{report['status']}`",
        "",
        "This local report reads a saved long-agent task plan and previews the",
        "context budget for each shard without executing the workflow.",
        "",
        "## Boundary",
        "",
    ]
    for key, value in report["side_effect_boundary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Summary", ""])
    for key, value in report["summary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Shards", ""])
    for card in report["shard_budget_cards"]:
        lines.extend(
            [
                f"### {card['shard_id']}",
                "",
                f"- max tokens: `{card['max_tokens']}`",
                f"- estimated tokens: `{card['estimated_tokens']}`",
                f"- selected refs: `{len(card['selected_context_refs'])}`",
                f"- omitted refs: `{len(card['omitted_context_refs'])}`",
                f"- searchable-only refs: `{len(card['searchable_only_refs'])}`",
                f"- compacted event refs: `{len(card['compacted_event_refs'])}`",
                f"- cache hit is authority: `{card['cache_hit_is_authority']}`",
                f"- merge/replan gate required: `{card['merge_replan_gate_required']}`",
                "",
            ]
        )
    lines.extend(["## Blocked Claims", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def render_task_shard_context_budget_public_html(report: dict[str, Any]) -> str:
    import html

    def esc(value: object) -> str:
        return html.escape(str(value), quote=True)

    shard_rows = "\n".join(
        "<tr>"
        f"<td>{esc(card['shard_id'])}</td>"
        f"<td>{esc(card['estimated_tokens'])}/{esc(card['max_tokens'])}</td>"
        f"<td>{esc(len(card['selected_context_refs']))}</td>"
        f"<td>{esc(len(card['omitted_context_refs']))}</td>"
        f"<td>{esc(len(card['searchable_only_refs']))}</td>"
        f"<td>{esc(len(card['compacted_event_refs']))}</td>"
        "</tr>"
        for card in report["shard_budget_cards"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Task Shard Context Budget Ledger</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem; line-height: 1.5; color: #111827; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
    code {{ background: #f3f4f6; padding: 0.1rem 0.25rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>Task Shard Context Budget Ledger</h1>
  <p>Status: <code>{esc(report['status'])}</code></p>
  <p>Local/offline report for a saved long-agent task plan. No workflow,
  worktree, provider, target, or memory backend side effect is performed.</p>
  <table>
    <thead>
      <tr>
        <th>Shard</th>
        <th>Tokens</th>
        <th>Selected</th>
        <th>Omitted</th>
        <th>Searchable Only</th>
        <th>Compacted Events</th>
      </tr>
    </thead>
    <tbody>
      {shard_rows}
    </tbody>
  </table>
</body>
</html>
"""


def render_task_shard_summary(report: dict[str, Any]) -> str:
    schema_id = report.get("schema_id")
    if schema_id in {
        TASK_SHARD_VALIDATE_SCHEMA_ID,
        TASK_SHARD_IMPORT_VALIDATE_SCHEMA_ID,
        TASK_SHARD_IMPORT_NEGATIVE_VALIDATE_SCHEMA_ID,
        TASK_SHARD_SAVED_TRACE_IMPORTS_VALIDATE_SCHEMA_ID,
        TASK_SHARD_CONTEXT_REHEARSAL_VALIDATE_SCHEMA_ID,
        TASK_SHARD_BUDGET_LEDGER_REPORT_VALIDATE_SCHEMA_ID,
    }:
        title = _validation_title(schema_id)
        summary = report.get("summary", {})
        surface_count = summary.get("import_surface_count", summary.get("import_shape_count"))
        if surface_count is None:
            surface_ids = summary.get("surface_ids", [])
            surface_count = len(surface_ids) if isinstance(surface_ids, list) else 0
        lines = [
            title,
            f"- status: {report.get('status')}",
            f"- valid: {report.get('valid')}",
            f"- errors: {len(report.get('errors', []))}",
            f"- shards: {summary.get('shard_count', summary.get('packet_count', 0))}",
            f"- import surfaces: {surface_count}",
            f"- variants: {report.get('variant_count', 0)}",
        ]
        if "import_count" in summary:
            lines.append(f"- imports: {summary['import_count']}")
        if "contract_matched_surface_count" in summary:
            lines.append(f"- contract matched surfaces: {summary['contract_matched_surface_count']}")
        return "\n".join(lines)

    if schema_id == TASK_SHARD_SAVED_TRACE_IMPORTS_SCHEMA_ID:
        summary = report["summary"]
        return "\n".join(
            [
                "Task Shard Saved Trace Imports",
                f"- status: {report['status']}",
                f"- imports: {summary['import_count']}",
                f"- surfaces: {', '.join(summary['surface_ids'])}",
                f"- trace executed: {summary['trace_execution_performed']}",
                f"- runtime execution allowed: {summary['runtime_execution_allowed']}",
                f"- public claims allowed: {report['claim_gate']['public_benchmark_claim_allowed']}",
            ]
        )

    if schema_id == TASK_SHARD_CONTEXT_REHEARSAL_SCHEMA_ID:
        result = report["rehearsal_result"]
        return "\n".join(
            [
                "Task Shard Context Rehearsal",
                f"- status: {report['status']}",
                f"- packets: {result['packet_count']}",
                f"- blocked operations: {result['blocked_operation_count']}",
                f"- context injection executed: {result['context_injection_executed']}",
                f"- runtime executed: {result['runtime_or_adapter_executed']}",
                f"- public claims allowed: {report['claim_gate']['public_benchmark_claim_allowed']}",
            ]
        )

    if schema_id == TASK_SHARD_BUDGET_LEDGER_REPORT_SCHEMA_ID:
        summary = report["summary"]
        return "\n".join(
            [
                "Task Shard Context Budget Ledger",
                f"- status: {report['status']}",
                f"- shards: {summary['shard_count']}",
                f"- budget pressure: {summary['total_estimated_tokens']}/{summary['total_max_tokens']} ({summary['total_budget_pressure_ratio']})",
                f"- refs: selected={summary['selected_context_ref_count']} omitted={summary['omitted_context_ref_count']} searchable={summary['searchable_only_ref_count']} compacted={summary['compacted_event_ref_count']}",
                f"- cache hits as authority: {summary['cache_hit_is_authority_count']}",
                f"- compaction source loss: {summary['compaction_source_loss_count']}",
            ]
        )

    summary = report["summary"]
    quality = report["quality_metrics"]
    boundary = report["side_effect_boundary"]
    return "\n".join(
        [
            "Task Shard Context Control",
            f"- status: {report['status']}",
            f"- shards: {summary['shard_count']}",
            f"- context refs: selected={summary['selected_context_ref_count']} omitted={summary['omitted_context_ref_count']} searchable={summary['searchable_only_ref_count']} compacted={summary['compacted_event_ref_count']}",
            f"- quality: split={quality['split_quality']} context_minimality={quality['context_minimality']} merge_safety={quality['merge_safety']} replan_accuracy={quality['replan_accuracy']}",
            f"- merge conflicts: {summary['merge_conflict_count']}; replan triggers: {summary['replan_trigger_count']}",
            f"- import surfaces: {summary['import_surface_count']}",
            f"- workflow executed: {boundary['live_workflow_executed']}",
            f"- public claims allowed: {report['claim_gate']['public_benchmark_claim_allowed']}",
        ]
    )


def _validation_title(schema_id: str) -> str:
    return {
        TASK_SHARD_VALIDATE_SCHEMA_ID: "Task Shard Validate",
        TASK_SHARD_IMPORT_VALIDATE_SCHEMA_ID: "Task Shard Import Shapes Validate",
        TASK_SHARD_IMPORT_NEGATIVE_VALIDATE_SCHEMA_ID: "Task Shard Import Shape Negatives Validate",
        TASK_SHARD_SAVED_TRACE_IMPORTS_VALIDATE_SCHEMA_ID: "Task Shard Saved Trace Imports Validate",
        TASK_SHARD_CONTEXT_REHEARSAL_VALIDATE_SCHEMA_ID: "Task Shard Context Rehearsal Validate",
        TASK_SHARD_BUDGET_LEDGER_REPORT_VALIDATE_SCHEMA_ID: "Task Shard Context Budget Ledger Validate",
    }.get(schema_id, "Task Shard Validate")


def _validate_external_import_refs(pack: dict[str, Any], *, root_path: Path) -> list[dict[str, Any]]:
    validations = []
    refs = pack.get("external_import_shape_refs", [])
    if not isinstance(refs, list):
        return validations
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        raw_path = Path(str(ref.get("path") or ""))
        resolved = raw_path.resolve() if raw_path.is_absolute() else (root_path / raw_path).resolve()
        if not resolved.exists():
            validations.append(
                {
                    "source_ref": str(raw_path),
                    "path": str(resolved),
                    "valid": False,
                    "status": "invalid",
                    "errors": ["import shape file does not exist"],
                }
            )
            continue
        result = validate_task_shard_import_shapes_file(resolved)
        result["source_ref"] = str(raw_path)
        validations.append(result)
    return validations


def _apply_import_shape_negative_variant(payload: dict[str, Any], variant_id: str) -> None:
    shapes = payload.get("import_shapes", [])
    if variant_id == "missing_expected_surface":
        payload["import_shapes"] = [
            shape
            for shape in shapes
            if isinstance(shape, dict) and shape.get("import_surface_id") != "plandex_context_map"
        ]
        return
    if not shapes or not isinstance(shapes[0], dict):
        return
    first = shapes[0]
    if variant_id == "runtime_allowed_flip":
        first["runtime_execution_allowed"] = True
    elif variant_id == "side_effect_flip":
        first.setdefault("side_effect_boundary", {})["provider_or_model_call_performed"] = True
    elif variant_id == "missing_top_level_source_refs":
        payload["source_refs"] = []
    elif variant_id == "missing_selected_source_ref_fields":
        first.setdefault("context_ref_contract", {})["selected_source_ref_fields"] = []
    elif variant_id == "missing_omitted_context_ref_fields":
        first.setdefault("context_ref_contract", {})["omitted_context_ref_fields"] = []
    elif variant_id == "source_recovery_disabled":
        first.setdefault("context_ref_contract", {})["source_recovery_required"] = False
    elif variant_id == "omitted_context_invisible":
        first.setdefault("context_ref_contract", {})["omitted_context_visible"] = False


def _shard_context_packet(shard: dict[str, Any]) -> dict[str, Any]:
    shard_id = str(shard.get("shard_id") or "unknown_shard")
    minimal_packet = {
        "packet_id": f"{shard_id}_minimal_context_packet",
        "selected_context_refs": shard.get("selected_context_refs", []),
        "read_only_paths": shard.get("read_only_paths", []),
        "shared_paths": shard.get("shared_paths", []),
        "max_tokens": shard.get("context_budget", {}).get("max_tokens", 0),
        "estimated_tokens": shard.get("context_budget", {}).get("estimated_tokens", 0),
        "source_recovery_required": True,
    }
    minimal_packet["packet_sha256"] = _stable_payload_hash(minimal_packet)
    return {
        "object_type": "ShardContextRehearsalPacket",
        "shard_id": shard_id,
        "minimal_context_packet": minimal_packet,
        "selected_context_refs": shard.get("selected_context_refs", []),
        "omitted_context_refs": shard.get("omitted_context_refs", []),
        "searchable_only_refs": shard.get("searchable_only_refs", []),
        "compacted_event_refs": shard.get("compacted_event_refs", []),
        "context_injection_executed": False,
        "blocked_live_operation_transcript": [
            {
                "operation_id": f"{shard_id}:validate_context_visa",
                "status": "completed_local_preview",
                "current_allowed_without_approval": True,
                "approval_required": False,
            },
            {
                "operation_id": f"{shard_id}:render_minimal_context_packet",
                "status": "completed_local_preview",
                "current_allowed_without_approval": True,
                "approval_required": False,
            },
            {
                "operation_id": f"{shard_id}:open_runtime_shard",
                "status": "blocked_until_owner_approval",
                "current_allowed_without_approval": False,
                "approval_required": True,
                "approval_action_id": "live_runtime_or_adapter_execution",
            },
            {
                "operation_id": f"{shard_id}:inject_context",
                "status": "blocked_until_owner_approval",
                "current_allowed_without_approval": False,
                "approval_required": True,
                "approval_action_id": "context_injection",
            },
            {
                "operation_id": f"{shard_id}:execute_shard",
                "status": "blocked_until_owner_approval",
                "current_allowed_without_approval": False,
                "approval_required": True,
                "approval_action_id": "live_runtime_or_adapter_execution",
            },
        ],
    }


def _shard_budget_card(shard: dict[str, Any]) -> dict[str, Any]:
    budget = shard.get("context_budget", {}) if isinstance(shard.get("context_budget"), dict) else {}
    cache = shard.get("cache_stability", {}) if isinstance(shard.get("cache_stability"), dict) else {}
    compaction = shard.get("compaction_loss", {}) if isinstance(shard.get("compaction_loss"), dict) else {}
    max_tokens = int(budget.get("max_tokens", 0))
    estimated = int(budget.get("estimated_tokens", 0))
    return {
        "object_type": "ShardContextBudgetCard",
        "shard_id": str(shard.get("shard_id") or "unknown_shard"),
        "estimated_tokens": estimated,
        "max_tokens": max_tokens,
        "budget_pressure_ratio": _ratio(estimated, max_tokens),
        "selected_context_ref_count": len(shard.get("selected_context_refs", [])),
        "omitted_context_ref_count": len(shard.get("omitted_context_refs", [])),
        "searchable_only_ref_count": len(shard.get("searchable_only_refs", [])),
        "compacted_event_ref_count": len(shard.get("compacted_event_refs", [])),
        "cache_hit_is_authority": cache.get("cache_hit_is_authority") is True,
        "prefix_stability_required": bool(cache.get("prefix_stability_required")),
        "cache_risk": cache.get("risk"),
        "decision_refs_preserved": compaction.get("decision_refs_preserved") is True,
        "blockers_preserved": compaction.get("blockers_preserved") is True,
        "source_refs_preserved": compaction.get("source_refs_preserved") is True,
        "loss_risk": compaction.get("loss_risk"),
    }


def _resolve_task_shard_context_budget_input(input_path: Path) -> Path:
    path = input_path.resolve()
    if path.is_dir():
        path = path / "long-agent-task.json"
    return path


def _validate_public_task_shard_context_budget_example(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_id") != "ctxgov.task-shard-context-budget-example/v0":
        errors.append("schema_id mismatch")
    if not payload.get("example_id"):
        errors.append("example_id required")
    if not payload.get("task"):
        errors.append("task required")
    shards = payload.get("shards", [])
    if not isinstance(shards, list) or not shards:
        errors.append("shards must be a non-empty list")
        shards = []
    for shard in shards:
        if not isinstance(shard, dict):
            errors.append("shards entries must be objects")
            continue
        shard_id = str(shard.get("shard_id") or "<missing>")
        if not shard.get("allowed_context_refs"):
            errors.append(f"{shard_id}: allowed_context_refs required")
        if not shard.get("omitted_context_refs"):
            errors.append(f"{shard_id}: omitted_context_refs required")
        if int(shard.get("max_tokens") or 0) <= 0:
            errors.append(f"{shard_id}: max_tokens must be positive")
    boundary = payload.get("side_effect_boundary", {})
    for field in [
        "workflow_executed",
        "worktree_created",
        "provider_or_model_call_performed",
        "target_file_written",
        "memory_backend_written",
    ]:
        if not isinstance(boundary, dict) or boundary.get(field) is not False:
            errors.append(f"side_effect_boundary.{field} must remain false")
    return errors


def _public_task_shard_card(shard: dict[str, Any]) -> dict[str, Any]:
    selected = list(shard.get("allowed_context_refs", []))
    omitted = list(shard.get("omitted_context_refs", []))
    searchable = list(shard.get("searchable_only_refs", ["source://owner-private-chat"]))
    compacted = list(shard.get("compacted_event_refs", ["event://prior-summary-boundary"]))
    max_tokens = int(shard.get("max_tokens") or 0)
    estimated_tokens = min(max_tokens, max(1, len(selected) * 320 + len(omitted) * 120))
    return {
        "object_type": "TaskShardContextBudgetCard",
        "shard_id": str(shard.get("shard_id") or "unknown-shard"),
        "selected_context_refs": selected,
        "omitted_context_refs": omitted,
        "searchable_only_refs": searchable,
        "compacted_event_refs": compacted,
        "max_tokens": max_tokens,
        "estimated_tokens": estimated_tokens,
        "budget_pressure_ratio": _ratio(float(estimated_tokens), float(max_tokens)),
        "cache_hit_is_authority": False,
        "cache_hit_is_not_authority": True,
        "source_recovery_required": True,
        "merge_replan_gate_required": True,
        "raw_content_included": False,
    }


def _public_task_shard_risk_cards(shard_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for card in shard_cards:
        cards.append(
            {
                "shard_id": card["shard_id"],
                "risk_id": "omitted_context_visibility",
                "status": "visible_in_report" if card["omitted_context_refs"] else "missing",
                "claim": "omitted refs are surfaced as review inputs, not silently discarded",
            }
        )
        cards.append(
            {
                "shard_id": card["shard_id"],
                "risk_id": "cache_hit_is_not_authority",
                "status": "blocked_as_authority",
                "claim": "cache reuse can reduce cost but grants no answer or action authority",
            }
        )
        cards.append(
            {
                "shard_id": card["shard_id"],
                "risk_id": "merge_replan_gate",
                "status": "required_before_downstream_use",
                "claim": "merge and replan decisions need explicit review evidence",
            }
        )
    return cards


def _public_task_shard_side_effect_boundary() -> dict[str, bool]:
    return {
        "workflow_executed": False,
        "worktree_created": False,
        "provider_or_model_call_performed": False,
        "target_file_written": False,
        "memory_backend_written": False,
    }


def _public_task_shard_claim_boundary() -> dict[str, bool]:
    return {
        "public_benchmark_claim_created": False,
        "public_savings_claim_created": False,
        "public_adoption_claim_created": False,
        "public_security_claim_created": False,
        "public_compatibility_claim_created": False,
        "public_support_claim_created": False,
        "stable_protocol_claim_created": False,
    }


def _repo_relative_or_name(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _append_boundary_errors(errors: list[str], boundary: Any) -> None:
    if not isinstance(boundary, dict):
        errors.append("side_effect_boundary must be an object")
        return
    for side_effect in FALSE_SIDE_EFFECTS:
        if boundary.get(side_effect) is not False:
            errors.append(f"side_effect_boundary.{side_effect} must remain false")


def _quality_scores(pack: dict[str, Any], validation: dict[str, Any]) -> dict[str, float]:
    summary = validation.get("summary", {})
    errors = validation.get("errors", [])
    split_quality = _score(
        not any("unknown dependency" in error for error in errors)
        and not any("shard_count must match" in error for error in errors)
        and summary.get("all_shards_have_selected_context") is True
    )
    context_minimality = _score(
        summary.get("within_context_budget") is True
        and summary.get("omitted_context_ref_count", 0) > 0
        and summary.get("searchable_only_ref_count", 0) > 0
    )
    merge_safety = _score(
        not any("merge_approved must remain false" in error for error in errors)
        and not any("merge conflicts require replan trigger" in error for error in errors)
        and summary.get("merge_conflict_count", 0) == summary.get("replan_trigger_count", 0)
    )
    gate_metrics = set(pack.get("benchmark_gate", {}).get("required_metrics", []))
    replan_accuracy = _score(
        summary.get("replan_trigger_count", 0) >= 1
        and not any("conflicts require replan trigger" in error for error in errors)
        and "replan_accuracy" in gate_metrics
    )
    return {
        "split_quality": split_quality,
        "context_minimality": context_minimality,
        "merge_safety": merge_safety,
        "replan_accuracy": replan_accuracy,
    }


def _fixture_summary(pack: dict[str, Any], import_validations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    shards = pack.get("shard_context_visas", [])
    shards = shards if isinstance(shards, list) else []
    counts = _context_counts(shards)
    merge_receipts = pack.get("shard_merge_receipts", [])
    merge_receipts = merge_receipts if isinstance(merge_receipts, list) else []
    conflict_count = sum(len(merge.get("merge_conflict_refs", [])) for merge in merge_receipts if isinstance(merge, dict))
    replan_count = sum(
        1
        for merge in merge_receipts
        if isinstance(merge, dict)
        and merge.get("merge_conflict_refs")
        and isinstance(merge.get("replan_trigger"), dict)
        and merge["replan_trigger"].get("triggered") is True
    )
    import_validations = import_validations or []
    import_surface_ids: set[str] = set()
    for validation in import_validations:
        import_surface_ids.update(validation.get("summary", {}).get("covered_surface_ids", []))
    return {
        "shard_count": len(shards),
        "all_shards_have_selected_context": all(bool(shard.get("selected_context_refs")) for shard in shards if isinstance(shard, dict)),
        "within_context_budget": all(
            float(shard.get("context_budget", {}).get("estimated_tokens", 0))
            <= float(shard.get("context_budget", {}).get("max_tokens", 0))
            for shard in shards
            if isinstance(shard, dict)
        ),
        "merge_conflict_count": conflict_count,
        "replan_trigger_count": replan_count,
        "negative_variant_count": pack.get("negative_fixture_contract", {}).get("variant_count", 0),
        "import_shape_ref_count": len(pack.get("external_import_shape_refs", [])) if isinstance(pack.get("external_import_shape_refs", []), list) else 0,
        "import_surface_count": len(import_surface_ids),
        **counts,
    }


def _context_counts(shards: list[Any]) -> dict[str, int]:
    selected = sum(len(shard.get("selected_context_refs", [])) for shard in shards if isinstance(shard, dict))
    omitted = sum(len(shard.get("omitted_context_refs", [])) for shard in shards if isinstance(shard, dict))
    searchable = sum(len(shard.get("searchable_only_refs", [])) for shard in shards if isinstance(shard, dict))
    compacted = sum(len(shard.get("compacted_event_refs", [])) for shard in shards if isinstance(shard, dict))
    estimated = sum(int(shard.get("context_budget", {}).get("estimated_tokens", 0)) for shard in shards if isinstance(shard, dict))
    maximum = sum(int(shard.get("context_budget", {}).get("max_tokens", 0)) for shard in shards if isinstance(shard, dict))
    return {
        "selected_context_ref_count": selected,
        "omitted_context_ref_count": omitted,
        "searchable_only_ref_count": searchable,
        "compacted_event_ref_count": compacted,
        "total_estimated_tokens": estimated,
        "total_max_tokens": maximum,
    }


def _side_effect_boundary(
    *,
    validation_created: bool = False,
    eval_created: bool = False,
    fixture_read: bool = False,
    import_shape_read: bool = False,
) -> dict[str, bool]:
    return {
        "task_shard_validation_created": validation_created,
        "task_shard_eval_receipt_created": eval_created,
        "local_fixture_read": fixture_read,
        "local_import_shape_read": import_shape_read,
        **{field: False for field in FALSE_SIDE_EFFECTS},
    }


def _claim_gate() -> dict[str, bool | list[str]]:
    return {
        **{field: False for field in FALSE_CLAIMS},
        "allowed_private_wording": [
            "private offline Task Shard Context Control eval",
            "fixture-backed task shard validator",
            "no workflow execution",
        ],
        "blocked_public_wording": [
            "public long-task benchmark",
            "workflow execution guarantee",
            "agent productivity claim",
            "stable MGP claim",
        ],
    }


def _default_root_for_fixture(path: Path) -> Path:
    if len(path.parents) >= 4 and path.parents[2].name == "fixtures":
        return path.parents[3]
    return Path.cwd()


def _score(condition: bool) -> float:
    return 1.0 if condition else 0.0


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _stable_payload_hash(payload: dict[str, Any]) -> str:
    cloned = copy.deepcopy(payload)
    cloned.pop("rehearsal_sha256", None)
    cloned.pop("report_sha256", None)
    encoded = json.dumps(cloned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


__all__ = [
    "EXPECTED_IMPORT_SURFACE_IDS",
    "FALSE_CLAIMS",
    "FALSE_SIDE_EFFECTS",
    "TASK_SHARD_QUALITY_METRICS",
    "build_task_shard_context_budget_ledger_report",
    "build_task_shard_context_budget_public_report",
    "build_task_shard_context_rehearsal",
    "build_task_shard_saved_trace_imports",
    "evaluate_task_shard_fixture_pack",
    "render_task_shard_summary",
    "render_task_shard_context_budget_public_html",
    "render_task_shard_context_budget_public_markdown",
    "validate_task_shard_context_budget_ledger_report_file",
    "validate_task_shard_context_budget_ledger_report_payload",
    "validate_task_shard_context_budget_public_report_payload",
    "validate_task_shard_context_rehearsal_file",
    "validate_task_shard_context_rehearsal_payload",
    "validate_task_shard_fixture_pack_file",
    "validate_task_shard_fixture_pack_payload",
    "validate_task_shard_import_shape_negative_fixture_file",
    "validate_task_shard_import_shapes_file",
    "validate_task_shard_import_shapes_payload",
    "validate_task_shard_saved_trace_imports_file",
    "validate_task_shard_saved_trace_imports_payload",
]
