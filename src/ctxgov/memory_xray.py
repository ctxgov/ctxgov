from __future__ import annotations

import json
from pathlib import Path
from typing import Any


MEMORY_XRAY_PUBLIC_EXAMPLES_PACK_SCHEMA_ID = "ctxvault.memory-xray-public-examples-pack/v0"
MEMORY_XRAY_VALIDATE_RESULT_SCHEMA_ID = "ctxvault.memory-xray-validate-result/v0"
FORBIDDEN_SIDE_EFFECT_FIELDS = {
    "provider_or_model_call_performed",
    "provider_memory_written",
    "memory_backend_written",
    "target_file_written",
    "package_published",
    "public_claim_created",
    "provider_support_claim_created",
}


def validate_memory_xray_file(path: Path) -> dict[str, Any]:
    resolved_path = path.resolve()
    errors: list[str] = []
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except Exception as exc:
        payload = None
        errors.append(f"failed to parse JSON: {exc}")

    if not isinstance(payload, dict):
        errors.append("root value must be a JSON object")
        inspected_schema_id = None
        record_count = 0
    else:
        inspected_schema_id = payload.get("schema_id")
        record_count = _record_count(payload)
        if inspected_schema_id != MEMORY_XRAY_PUBLIC_EXAMPLES_PACK_SCHEMA_ID:
            errors.append(f"unsupported public Memory X-Ray schema_id: {inspected_schema_id}")
        else:
            _validate_public_examples_pack(payload, errors)

    valid = not errors
    return {
        "schema_id": MEMORY_XRAY_VALIDATE_RESULT_SCHEMA_ID,
        "object_type": "MemoryXRayValidateResult",
        "version": "v0.8.0",
        "status": "valid" if valid else "invalid",
        "valid": valid,
        "path": str(resolved_path),
        "inspected_schema_id": inspected_schema_id,
        "record_count": record_count,
        "errors": errors,
        "warnings": [],
        "side_effect_boundary": {
            "network_call": False,
            "provider_model_call": False,
            "public_write": False,
            "target_repo_write": False,
        },
        "rollback": {"mode": "discard_validation_result", "delete_paths": [], "external_state_to_revert": "none"},
    }


def _validate_public_examples_pack(payload: dict[str, Any], errors: list[str]) -> None:
    _require_keys(payload, ["summary", "examples", "claim_boundary", "side_effect_boundary", "rollback"], errors)
    serialized = json.dumps(payload, sort_keys=True)
    if "/Users/" in serialized or "source_trace_path" in serialized:
        errors.append("public examples pack must not contain absolute user paths or source_trace_path fields")

    examples = payload.get("examples")
    if not isinstance(examples, list) or not examples:
        errors.append("examples must be a non-empty list")
        examples = []
    expected_count = payload.get("summary", {}).get("example_count") if isinstance(payload.get("summary"), dict) else None
    if expected_count is not None and expected_count != len(examples):
        errors.append("summary.example_count must match examples length")

    for index, example in enumerate(examples, start=1):
        if not isinstance(example, dict):
            errors.append(f"examples[{index}] must be an object")
            continue
        if example.get("provider_or_framework") != "redacted":
            errors.append(f"examples[{index}].provider_or_framework must be redacted")
        _require_keys(example, ["source_rollback_consequence_evidence", "rollback_template", "consequence_ceiling"], errors)
        evidence = example.get("source_rollback_consequence_evidence")
        if isinstance(evidence, dict):
            for field in ("source_evidence_present", "rollback_evidence_present", "consequence_evidence_present"):
                if evidence.get(field) is not True:
                    errors.append(f"examples[{index}].{field} must be true")
        _validate_no_truthy_side_effects(example, errors, f"examples[{index}]")

    _validate_no_truthy_side_effects(payload.get("side_effect_boundary"), errors, "side_effect_boundary")
    _validate_no_truthy_side_effects(payload, errors, "payload")


def _require_keys(payload: dict[str, Any], keys: list[str], errors: list[str]) -> None:
    for key in keys:
        if key not in payload:
            errors.append(f"missing required key: {key}")


def _validate_no_truthy_side_effects(value: Any, errors: list[str], label: str) -> None:
    for field in sorted(FORBIDDEN_SIDE_EFFECT_FIELDS):
        if _truthy_field(value, field):
            errors.append(f"{label}.{field} must not be true")


def _truthy_field(value: Any, field: str) -> bool:
    if isinstance(value, dict):
        if value.get(field) is True:
            return True
        return any(_truthy_field(item, field) for item in value.values())
    if isinstance(value, list):
        return any(_truthy_field(item, field) for item in value)
    return False


def _record_count(payload: Any) -> int:
    if isinstance(payload, dict):
        examples = payload.get("examples")
        if isinstance(examples, list):
            return len(examples)
        return len(payload)
    if isinstance(payload, list):
        return len(payload)
    return 0
