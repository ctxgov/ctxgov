#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from json import JSONDecodeError
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
WRAPPER_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json")
WRAPPER_EXAMPLE = Path("release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json")
WRAPPER_PASS_EXAMPLE = Path("release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json")
SAMPLE_INPUT = Path("examples/memory-state-influence-boundary")
PASS_SAMPLE_INPUT = Path("examples/memory-state-influence-boundary/state-policy.toml")
WRAPPER_SCRIPT = Path("scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py")
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


CLAIM_BOUNDARY = {
    "public_savings_claim_created": False,
    "public_benchmark_claim_created": False,
    "public_adoption_claim_created": False,
    "public_compatibility_claim_created": False,
    "public_support_claim_created": False,
    "public_security_claim_created": False,
    "public_endorsement_claim_created": False,
    "stable_protocol_claim_created": False,
}

SIDE_EFFECT_BOUNDARY = {
    "network_access_performed": False,
    "provider_or_model_call_performed": False,
    "external_runtime_or_adapter_executed": False,
    "memory_backend_written": False,
    "target_file_written": False,
    "sarif_uploaded": False,
    "public_release_created": False,
    "outreach_performed": False,
}


def check_memory_state_influence_boundary_consumer_wrapper_contract(
    root: Path = ROOT,
    *,
    schema_path: Path = WRAPPER_SCHEMA,
    example_path: Path = WRAPPER_EXAMPLE,
    pass_example_path: Path = WRAPPER_PASS_EXAMPLE,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    schema_path = _resolve(root, schema_path)
    example_path = _resolve(root, example_path)
    pass_example_path = _resolve(root, pass_example_path)

    schema = _load_json_object(schema_path, "schema", errors)
    example = _load_json_object(example_path, "blocked example", errors)
    pass_example = _load_json_object(pass_example_path, "pass example", errors)

    blocked_case = _run_wrapper_case(
        root,
        case_id="blocked_sample",
        input_path=None,
        example=example,
        schema=schema,
        expected_decision="block",
        expected_reason="blocked_refs_present",
        expected_gate_returncode=2,
        runner=runner,
        errors=errors,
    )
    pass_case = _run_wrapper_case(
        root,
        case_id="pass_sample",
        input_path=PASS_SAMPLE_INPUT,
        example=pass_example,
        schema=schema,
        expected_decision="allow_inform_only",
        expected_reason="gate_passed_no_blocked_refs",
        expected_gate_returncode=0,
        runner=runner,
        errors=errors,
    )

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-consumer-wrapper-contract-check/v0",
        "status": (
            "pass_memory_state_influence_boundary_consumer_wrapper_contract"
            if not errors
            else "fail_memory_state_influence_boundary_consumer_wrapper_contract"
        ),
        "milestone": "Local Memory State Influence Boundary Report",
        "wrapper_schema": _display_path(schema_path, root),
        "wrapper_example": _display_path(example_path, root),
        "wrapper_pass_example": _display_path(pass_example_path, root),
        "blocked_case_status": blocked_case.get("status"),
        "pass_case_status": pass_case.get("status"),
        "stdout_json_status": _combine_statuses(blocked_case.get("stdout_json_status"), pass_case.get("stdout_json_status")),
        "schema_contract_status": _combine_statuses(blocked_case.get("schema_contract_status"), pass_case.get("schema_contract_status")),
        "example_drift_status": _combine_statuses(blocked_case.get("example_drift_status"), pass_case.get("example_drift_status")),
        "decision_status": _combine_statuses(blocked_case.get("decision_status"), pass_case.get("decision_status")),
        "raw_content_boundary_status": _combine_statuses(
            blocked_case.get("raw_content_boundary_status"),
            pass_case.get("raw_content_boundary_status"),
        ),
        "blocked_decision": blocked_case.get("decision", {}).get("decision"),
        "pass_decision": pass_case.get("decision", {}).get("decision"),
        "blocked_gate_returncode": blocked_case.get("gate_returncode"),
        "pass_gate_returncode": pass_case.get("gate_returncode"),
        "case_results": [blocked_case, pass_case],
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "side_effect_boundary": dict(SIDE_EFFECT_BOUNDARY),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _run_wrapper_case(
    root: Path,
    *,
    case_id: str,
    input_path: Path | None,
    example: dict[str, Any],
    schema: dict[str, Any],
    expected_decision: str,
    expected_reason: str,
    expected_gate_returncode: int,
    runner: CommandRunner,
    errors: list[str],
) -> dict[str, Any]:
    case_errors: list[str] = []
    command = [sys.executable, str(WRAPPER_SCRIPT)]
    if input_path is not None:
        command.extend(["--input", _display_input_arg(input_path)])
    completed = runner(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload = _parse_stdout_json(completed.stdout, case_errors)
    schema_result = _validate_against_schema(payload, schema, case_errors)
    example_result = _validate_example_drift(payload, example, case_errors)
    decision_result = _validate_decision(
        payload,
        completed.returncode,
        expected_decision=expected_decision,
        expected_reason=expected_reason,
        expected_gate_returncode=expected_gate_returncode,
        errors=case_errors,
    )
    raw_content_result = _validate_raw_content_boundary(payload, case_errors)
    errors.extend(f"{case_id}: {error}" for error in case_errors)
    return {
        "case_id": case_id,
        "status": "pass" if not case_errors else "fail",
        "command": "python3 " + " ".join([str(WRAPPER_SCRIPT)] + ([] if input_path is None else ["--input", _display_input_arg(input_path)])),
        "returncode": completed.returncode,
        "input": payload.get("input"),
        "stdout_json_status": "pass" if payload else "fail",
        "schema_contract_status": schema_result,
        "example_drift_status": example_result,
        "decision_status": decision_result,
        "raw_content_boundary_status": raw_content_result,
        "decision": payload.get("decision", {}),
        "gate_returncode": payload.get("gate_returncode"),
        "errors": case_errors,
    }


def _load_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"{label} file missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        errors.append(f"{label} file is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} file must contain a JSON object: {path}")
        return {}
    return payload


def _parse_stdout_json(stdout: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except JSONDecodeError as exc:
        errors.append(f"wrapper stdout is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append("wrapper stdout must be a JSON object")
        return {}
    return payload


def _validate_against_schema(payload: dict[str, Any], schema: dict[str, Any], errors: list[str]) -> str:
    if not payload or not schema:
        return "not_checked"
    before = len(errors)
    _validate_schema_object(payload, schema, "wrapper", errors)
    return "pass" if len(errors) == before else "fail"


def _validate_schema_object(payload: dict[str, Any], schema: dict[str, Any], path: str, errors: list[str]) -> None:
    required = schema.get("required", [])
    if not isinstance(required, list):
        errors.append(f"{path} schema required must be a list")
        required = []
    missing = [field for field in required if field not in payload]
    if missing:
        errors.append(f"{path} missing required fields: {', '.join(missing)}")
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(payload) - set(schema.get("properties", {})))
        if unexpected:
            errors.append(f"{path} has unexpected fields: {', '.join(unexpected)}")
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        properties = {}
    for field, field_schema in properties.items():
        if field not in payload or not isinstance(field_schema, dict):
            continue
        _validate_schema_value(payload[field], field_schema, f"{path}.{field}", errors)


def _validate_schema_value(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} must be one of {schema['enum']!r}")
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path} must be object")
            return
        _validate_schema_object(value, schema, path, errors)
    elif expected_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path} must be array")
            return
        item_schema = schema.get("items", {})
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_schema_value(item, item_schema, f"{path}[{index}]", errors)
    elif expected_type == "boolean" and not isinstance(value, bool):
        errors.append(f"{path} must be boolean")
    elif expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"{path} must be integer")
    elif expected_type == "string" and not isinstance(value, str):
        errors.append(f"{path} must be string")
    if isinstance(value, int) and "minimum" in schema and value < schema["minimum"]:
        errors.append(f"{path} must be >= {schema['minimum']}")
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(f"{path} must be non-empty")


def _validate_example_drift(payload: dict[str, Any], example: dict[str, Any], errors: list[str]) -> str:
    if not payload or not example:
        return "not_checked"
    if payload != example:
        errors.append("wrapper example drifted from live output")
        return "fail"
    return "pass"


def _validate_decision(
    payload: dict[str, Any],
    returncode: int,
    *,
    expected_decision: str,
    expected_reason: str,
    expected_gate_returncode: int,
    errors: list[str],
) -> str:
    if not payload:
        return "not_checked"
    before = len(errors)
    decision = payload.get("decision", {})
    if decision.get("decision") != expected_decision:
        errors.append(f"decision expected {expected_decision!r}, observed {decision.get('decision')!r}")
    if decision.get("reason") != expected_reason:
        errors.append(f"decision reason expected {expected_reason!r}, observed {decision.get('reason')!r}")
    if decision.get("gate_returncode") != expected_gate_returncode:
        errors.append(
            f"decision gate_returncode expected {expected_gate_returncode}, observed {decision.get('gate_returncode')}"
        )
    if payload.get("gate_returncode") != expected_gate_returncode:
        errors.append(f"gate_returncode expected {expected_gate_returncode}, observed {payload.get('gate_returncode')}")
    if returncode != 0:
        errors.append(f"wrapper command should exit 0 for valid example decisions, observed {returncode}")
    return "pass" if len(errors) == before else "fail"


def _validate_raw_content_boundary(payload: dict[str, Any], errors: list[str]) -> str:
    if not payload:
        return "not_checked"
    before = len(errors)
    if payload.get("gate", {}).get("raw_content_included") is not False:
        errors.append("gate raw_content_included must be false")
    if payload.get("decision", {}).get("raw_content_included") is not False:
        errors.append("decision raw_content_included must be false")
    if payload.get("decision", {}).get("consumed_raw_content") is not False:
        errors.append("decision consumed_raw_content must be false")
    if payload.get("publication_executed") is not False:
        errors.append("publication_executed must be false")
    if payload.get("outreach_performed") is not False:
        errors.append("outreach_performed must be false")
    return "pass" if len(errors) == before else "fail"


def _combine_statuses(left: Any, right: Any) -> str:
    return "pass" if left == "pass" and right == "pass" else "fail"


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _display_input_arg(path: Path) -> str:
    return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the Memory State Influence Boundary consumer wrapper contract.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_consumer_wrapper_contract(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_consumer_wrapper_contract" else 1


if __name__ == "__main__":
    raise SystemExit(main())
