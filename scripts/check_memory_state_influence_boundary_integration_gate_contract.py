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
SAMPLE_INPUT = Path("examples/memory-state-influence-boundary")
PASS_SAMPLE_INPUT = Path("examples/memory-state-influence-boundary/state-policy.toml")
GATE_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json")
GATE_EXAMPLE = Path("release/memory-state-governability-overlay/2026-06-11/integration-gate.example.json")
GATE_PASS_EXAMPLE = Path("release/memory-state-governability-overlay/2026-06-11/integration-gate.pass.example.json")
GATE_COMMAND = [
    "scripts/run_memory_state_influence_boundary_report.py",
    "--format",
    "gate",
    "--fail-on-blocked",
]
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


def check_memory_state_influence_boundary_integration_gate_contract(
    root: Path = ROOT,
    *,
    input_path: Path = SAMPLE_INPUT,
    pass_input_path: Path = PASS_SAMPLE_INPUT,
    schema_path: Path = GATE_SCHEMA,
    example_path: Path = GATE_EXAMPLE,
    pass_example_path: Path = GATE_PASS_EXAMPLE,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    root = Path(root).resolve()
    input_path = Path(input_path)
    pass_input_path = Path(pass_input_path)
    schema_path = _resolve(root, schema_path)
    example_path = _resolve(root, example_path)
    pass_example_path = _resolve(root, pass_example_path)
    errors: list[str] = []

    schema = _load_json_object(schema_path, "schema", errors)
    example = _load_json_object(example_path, "example", errors)
    pass_example = _load_json_object(pass_example_path, "pass example", errors)
    blocked_case = _run_gate_case(
        root,
        case_id="blocked_sample",
        input_path=input_path,
        schema=schema,
        example=example,
        expected_example_input=SAMPLE_INPUT,
        runner=runner,
        errors=errors,
    )
    pass_case = _run_gate_case(
        root,
        case_id="pass_sample",
        input_path=pass_input_path,
        schema=schema,
        example=pass_example,
        expected_example_input=PASS_SAMPLE_INPUT,
        runner=runner,
        errors=errors,
    )

    status = (
        "pass_memory_state_influence_boundary_integration_gate_contract"
        if not errors
        else "fail_memory_state_influence_boundary_integration_gate_contract"
    )
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-integration-gate-contract-check/v0",
        "status": status,
        "milestone": "Local Memory State Influence Boundary Report",
        "input": blocked_case.get("input"),
        "pass_input": pass_case.get("input"),
        "command": blocked_case.get("command"),
        "pass_command": pass_case.get("command"),
        "gate_command_returncode": blocked_case.get("returncode"),
        "expected_fail_on_blocked_exit_code": blocked_case.get("expected_fail_on_blocked_exit_code"),
        "stdout_json_status": _combine_statuses(blocked_case.get("stdout_json_status"), pass_case.get("stdout_json_status")),
        "schema_contract_status": _combine_statuses(blocked_case.get("schema_contract_status"), pass_case.get("schema_contract_status")),
        "example_drift_status": _combine_statuses(blocked_case.get("example_drift_status"), pass_case.get("example_drift_status")),
        "exit_code_status": _combine_statuses(blocked_case.get("exit_code_status"), pass_case.get("exit_code_status")),
        "blocked_case_status": blocked_case.get("status"),
        "pass_case_status": pass_case.get("status"),
        "case_results": [blocked_case, pass_case],
        "gate_schema": _display_path(schema_path, root),
        "gate_example": _display_path(example_path, root),
        "gate_pass_example": _display_path(pass_example_path, root),
        "gate": blocked_case.get("gate", {}),
        "pass_gate": pass_case.get("gate", {}),
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "side_effect_boundary": dict(SIDE_EFFECT_BOUNDARY),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _run_gate_case(
    root: Path,
    *,
    case_id: str,
    input_path: Path,
    schema: dict[str, Any],
    example: dict[str, Any],
    expected_example_input: Path,
    runner: CommandRunner,
    errors: list[str],
) -> dict[str, Any]:
    case_errors: list[str] = []
    command = [sys.executable, *GATE_COMMAND, "--input", _display_input_arg(input_path)]
    completed = runner(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    gate = _parse_gate_stdout(completed.stdout, case_errors)
    schema_result = _validate_gate_against_schema(gate, schema, case_errors)
    exit_code_status = _validate_exit_code(gate, completed.returncode, case_errors)
    example_result = _validate_example_drift(gate, example, input_path, expected_example_input, case_errors)
    errors.extend(f"{case_id}: {error}" for error in case_errors)
    return {
        "case_id": case_id,
        "status": "pass" if not case_errors else "fail",
        "input": _display_path(_resolve(root, input_path), root),
        "command": "python3 " + " ".join(GATE_COMMAND + ["--input", _display_input_arg(input_path)]),
        "returncode": completed.returncode,
        "expected_fail_on_blocked_exit_code": gate.get("fail_on_blocked_exit_code") if gate else None,
        "stdout_json_status": "pass" if gate else "fail",
        "schema_contract_status": schema_result,
        "example_drift_status": example_result,
        "exit_code_status": exit_code_status,
        "gate": gate,
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


def _parse_gate_stdout(stdout: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except JSONDecodeError as exc:
        errors.append(f"gate stdout is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append("gate stdout must be a JSON object")
        return {}
    return payload


def _validate_gate_against_schema(gate: dict[str, Any], schema: dict[str, Any], errors: list[str]) -> str:
    if not gate or not schema:
        return "not_checked"
    required = schema.get("required", [])
    if not isinstance(required, list):
        errors.append("gate schema required must be a list")
        return "fail"
    missing = [field for field in required if field not in gate]
    if missing:
        errors.append(f"gate missing required fields: {', '.join(missing)}")
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(gate) - set(required))
        if unexpected:
            errors.append(f"gate has unexpected fields: {', '.join(unexpected)}")
    properties = schema.get("properties", {})
    for field, value in gate.items():
        field_schema = properties.get(field, {})
        _validate_schema_field(field, value, field_schema, errors)
    return "pass" if not missing else "fail"


def _validate_schema_field(field: str, value: Any, field_schema: dict[str, Any], errors: list[str]) -> None:
    if "const" in field_schema and value != field_schema["const"]:
        errors.append(f"gate field {field} must equal {field_schema['const']!r}")
    if "enum" in field_schema and value not in field_schema["enum"]:
        errors.append(f"gate field {field} must be one of {field_schema['enum']!r}")
    expected_type = field_schema.get("type")
    if expected_type == "boolean" and not isinstance(value, bool):
        errors.append(f"gate field {field} must be boolean")
    elif expected_type == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"gate field {field} must be integer")
    elif expected_type == "string" and not isinstance(value, str):
        errors.append(f"gate field {field} must be string")
    if isinstance(value, int) and "minimum" in field_schema and value < field_schema["minimum"]:
        errors.append(f"gate field {field} must be >= {field_schema['minimum']}")
    if isinstance(value, str) and "minLength" in field_schema and len(value) < field_schema["minLength"]:
        errors.append(f"gate field {field} must be non-empty")


def _validate_exit_code(gate: dict[str, Any], returncode: int, errors: list[str]) -> str:
    if not gate:
        return "not_checked"
    expected = gate.get("fail_on_blocked_exit_code")
    if expected != returncode:
        errors.append(f"gate command returncode {returncode} != fail_on_blocked_exit_code {expected}")
        return "fail"
    return "pass"


def _validate_example_drift(
    gate: dict[str, Any],
    example: dict[str, Any],
    input_path: Path,
    expected_example_input: Path,
    errors: list[str],
) -> str:
    if not gate or not example:
        return "not_checked"
    if _normalize_rel(input_path) != _normalize_rel(expected_example_input):
        return "skipped_for_custom_input"
    if gate != example:
        errors.append("integration gate example drifted from sample --format gate output")
        return "fail"
    return "pass"


def _combine_statuses(*statuses: Any) -> str:
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "not_checked" for status in statuses):
        return "not_checked"
    if all(status == "pass" for status in statuses):
        return "pass"
    return "unknown"


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_input_arg(path: Path) -> str:
    return str(Path(path))


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _normalize_rel(path: Path) -> str:
    return str(Path(path)).rstrip("/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the local Memory State Influence Boundary integration gate contract.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", type=Path, default=SAMPLE_INPUT, help="Input file or directory for the gate command.")
    parser.add_argument("--pass-input", type=Path, default=PASS_SAMPLE_INPUT, help="Input file expected to produce a passing gate.")
    parser.add_argument("--schema", type=Path, default=GATE_SCHEMA)
    parser.add_argument("--example", type=Path, default=GATE_EXAMPLE)
    parser.add_argument("--pass-example", type=Path, default=GATE_PASS_EXAMPLE)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_integration_gate_contract(
        args.root,
        input_path=args.input,
        pass_input_path=args.pass_input,
        schema_path=args.schema,
        example_path=args.example,
        pass_example_path=args.pass_example,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_integration_gate_contract" else 1


if __name__ == "__main__":
    raise SystemExit(main())
