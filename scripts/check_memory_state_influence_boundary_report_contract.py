#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from json import JSONDecodeError
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = Path("examples/memory-state-influence-boundary")
REPORT_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json")
REPORT_COMMAND = [
    "scripts/run_memory_state_influence_boundary_report.py",
]
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]

EXPECTED_REPORT_FIELDS = [
    "schema_id",
    "status",
    "milestone",
    "mode",
    "demo_command",
    "sample_command",
    "bring_your_own_commands",
    "fresh_checkout_commands",
    "input_path",
    "input_kind",
    "supported_input_suffixes",
    "scan_limits",
    "input_file_count",
    "skipped_input_count",
    "skipped_input_record_count",
    "skipped_input_records_truncated",
    "total_input_bytes",
    "input_files",
    "skipped_inputs",
    "influence_boundary",
    "integration_gate",
    "findings",
    "claim_boundary",
    "side_effect_boundary",
    "claim_boundary_note",
    "publish_positioning",
    "errors",
    "output_files",
]
EXPECTED_INPUT_FILE_FIELDS = [
    "path",
    "sha256",
    "bytes",
    "line_count",
    "source_family",
    "raw_content_included",
    "json_parse_errors",
    "toml_parse_errors",
    "json_key_paths_sample",
    "yaml_key_paths_sample",
    "structured_key_paths_sample",
    "signal_ids",
    "signal_evidence",
    "secret_like_evidence_count",
    "decision",
]
EXPECTED_INFLUENCE_BOUNDARY_FIELDS = [
    "selected_refs",
    "selected_refs_note",
    "candidate_influence_refs",
    "inform_only_allowed_refs",
    "omitted_refs",
    "blocked_refs",
    "stale_or_superseded_refs",
    "imported_context_refs",
    "source_refs",
    "authority_ceiling",
    "policy_grant",
    "final_state_assertion",
    "rollback_path",
    "delete_or_forget_propagation",
    "side_effect_boundary",
]
EXPECTED_GATE_FIELDS = [
    "schema_id",
    "mode",
    "passed",
    "default_exit_code",
    "fail_on_blocked_exit_code",
    "blocked_ref_count",
    "omitted_ref_count",
    "stale_or_superseded_ref_count",
    "imported_context_ref_count",
    "raw_content_included",
    "policy",
    "recommendation",
]
EXPECTED_OUTPUT_FIELDS = ["html", "json", "markdown"]
EXPECTED_CLAIM_BOUNDARY_FIELDS = [
    "public_adoption_claim_created",
    "public_benchmark_claim_created",
    "public_compatibility_claim_created",
    "public_endorsement_claim_created",
    "public_savings_claim_created",
    "public_security_claim_created",
    "public_support_claim_created",
    "stable_protocol_claim_created",
]
EXPECTED_SIDE_EFFECT_FIELDS = [
    "external_runtime_or_adapter_executed",
    "memory_backend_written",
    "network_access_performed",
    "outreach_performed",
    "provider_or_model_call_performed",
    "public_release_created",
    "sarif_uploaded",
    "target_file_written",
]
SUPPORTED_SUFFIXES = [".json", ".jsonl", ".md", ".mdx", ".toml", ".txt", ".yaml", ".yml"]


def check_memory_state_influence_boundary_report_contract(
    root: Path = ROOT,
    *,
    input_path: Path = SAMPLE_INPUT,
    schema_path: Path = REPORT_SCHEMA,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    root = Path(root).resolve()
    schema_path = _resolve(root, schema_path)
    errors: list[str] = []

    schema = _load_json_object(schema_path, "report schema", errors)
    case = _run_report_case(root, input_path=input_path, schema=schema, runner=runner)
    errors.extend(case.get("errors", []))

    status = (
        "pass_memory_state_influence_boundary_report_contract"
        if not errors
        else "fail_memory_state_influence_boundary_report_contract"
    )
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-report-contract-check/v0",
        "status": status,
        "milestone": "Local Memory State Influence Boundary Report",
        "input": case.get("input"),
        "command": case.get("command"),
        "report_schema": _display_path(schema_path, root),
        "report_schema_status": case.get("report_schema_status"),
        "stdout_json_status": case.get("stdout_json_status"),
        "schema_contract_status": case.get("schema_contract_status"),
        "report_contract_status": case.get("report_contract_status"),
        "raw_content_boundary_status": case.get("raw_content_boundary_status"),
        "integration_gate_embedded_status": case.get("integration_gate_embedded_status"),
        "sample_input_file_count": case.get("sample_input_file_count"),
        "sample_blocked_ref_count": case.get("sample_blocked_ref_count"),
        "sample_omitted_ref_count": case.get("sample_omitted_ref_count"),
        "sample_stale_or_superseded_ref_count": case.get("sample_stale_or_superseded_ref_count"),
        "sample_imported_context_ref_count": case.get("sample_imported_context_ref_count"),
        "sample_output_files": case.get("sample_output_files", {}),
        "claim_boundary": case.get("claim_boundary", {}),
        "side_effect_boundary": case.get("side_effect_boundary", {}),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def validate_memory_state_influence_boundary_report_contract(
    report: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    schema_status = _validate_schema_file(schema, errors)
    report_status = _validate_report_against_schema(report, schema, errors)
    raw_content_status = _validate_raw_content_boundary(report, errors)
    gate_status = _validate_embedded_gate(report, errors)
    return {
        "schema_contract_status": schema_status,
        "report_contract_status": report_status,
        "raw_content_boundary_status": raw_content_status,
        "integration_gate_embedded_status": gate_status,
        "errors": errors,
    }


def _run_report_case(
    root: Path,
    *,
    input_path: Path,
    schema: dict[str, Any],
    runner: CommandRunner,
) -> dict[str, Any]:
    case_errors: list[str] = []
    command = [sys.executable, *REPORT_COMMAND, "--input", _display_input_arg(input_path)]
    completed = runner(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    report = _parse_report_stdout(completed.stdout, case_errors)
    contract = validate_memory_state_influence_boundary_report_contract(report, schema)
    case_errors.extend(contract["errors"])
    if completed.returncode != 0:
        case_errors.append(f"report command returned {completed.returncode}: {completed.stderr[-4000:]}")

    influence_boundary = report.get("influence_boundary", {}) if isinstance(report, dict) else {}
    return {
        "input": _display_path(_resolve(root, input_path), root),
        "command": "python3 " + " ".join(REPORT_COMMAND + ["--input", _display_input_arg(input_path)]),
        "returncode": completed.returncode,
        "report_schema_status": "checked" if schema else "missing_or_invalid",
        "stdout_json_status": "pass" if report else "fail",
        "schema_contract_status": contract["schema_contract_status"],
        "report_contract_status": contract["report_contract_status"],
        "raw_content_boundary_status": contract["raw_content_boundary_status"],
        "integration_gate_embedded_status": contract["integration_gate_embedded_status"],
        "sample_input_file_count": report.get("input_file_count") if isinstance(report, dict) else None,
        "sample_blocked_ref_count": len(influence_boundary.get("blocked_refs", [])) if isinstance(influence_boundary, dict) else None,
        "sample_omitted_ref_count": len(influence_boundary.get("omitted_refs", [])) if isinstance(influence_boundary, dict) else None,
        "sample_stale_or_superseded_ref_count": len(influence_boundary.get("stale_or_superseded_refs", [])) if isinstance(influence_boundary, dict) else None,
        "sample_imported_context_ref_count": len(influence_boundary.get("imported_context_refs", [])) if isinstance(influence_boundary, dict) else None,
        "sample_output_files": report.get("output_files", {}) if isinstance(report, dict) else {},
        "claim_boundary": report.get("claim_boundary", {}) if isinstance(report, dict) else {},
        "side_effect_boundary": report.get("side_effect_boundary", {}) if isinstance(report, dict) else {},
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


def _parse_report_stdout(stdout: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except JSONDecodeError as exc:
        errors.append(f"report stdout is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append("report stdout must be a JSON object")
        return {}
    return payload


def _validate_schema_file(schema: dict[str, Any], errors: list[str]) -> str:
    start_error_count = len(errors)
    if not schema:
        return "not_checked"
    if schema.get("description", "").find("not a stable protocol") == -1:
        errors.append("report schema must deny stable protocol claim")
    if schema.get("properties", {}).get("schema_id", {}).get("const") != "ctxvault.memory-state-influence-boundary-report/v0":
        errors.append("report schema has unexpected schema_id const")
    if schema.get("properties", {}).get("mode", {}).get("const") != "user_input":
        errors.append("report schema mode const must be user_input")
    if schema.get("additionalProperties") is not False:
        errors.append("report schema must set top-level additionalProperties=false")
    missing_required = [field for field in EXPECTED_REPORT_FIELDS if field not in schema.get("required", [])]
    if missing_required:
        errors.append(f"report schema missing required fields: {', '.join(missing_required)}")
    scan_limits = schema.get("$defs", {}).get("scan_limits", {})
    if scan_limits.get("properties", {}).get("raw_content_included", {}).get("const") is not False:
        errors.append("report schema must require scan_limits.raw_content_included=false")
    input_file = schema.get("$defs", {}).get("input_file", {})
    if input_file.get("properties", {}).get("raw_content_included", {}).get("const") is not False:
        errors.append("report schema must require input_files[].raw_content_included=false")
    gate = schema.get("$defs", {}).get("integration_gate", {})
    if gate.get("properties", {}).get("raw_content_included", {}).get("const") is not False:
        errors.append("report schema must require integration_gate.raw_content_included=false")
    claim_boundary = schema.get("$defs", {}).get("claim_boundary", {})
    side_effect_boundary = schema.get("$defs", {}).get("side_effect_boundary", {})
    _validate_required_set("claim_boundary schema", claim_boundary, EXPECTED_CLAIM_BOUNDARY_FIELDS, errors)
    _validate_required_set("side_effect_boundary schema", side_effect_boundary, EXPECTED_SIDE_EFFECT_FIELDS, errors)
    return "pass" if len(errors) == start_error_count else "fail"


def _validate_report_against_schema(report: dict[str, Any], schema: dict[str, Any], errors: list[str]) -> str:
    start_error_count = len(errors)
    if not report or not schema:
        return "not_checked"
    required = schema.get("required", [])
    if not isinstance(required, list):
        errors.append("report schema required must be a list")
        return "fail"
    _validate_required_fields("report", report, required, errors)
    if schema.get("additionalProperties") is False:
        unexpected = sorted(set(report) - set(required))
        if unexpected:
            errors.append(f"report has unexpected fields: {', '.join(unexpected)}")
    if report.get("schema_id") != "ctxvault.memory-state-influence-boundary-report/v0":
        errors.append("report schema_id mismatch")
    if report.get("mode") != "user_input":
        errors.append("report mode must be user_input")
    if report.get("milestone") != "Local Memory State Influence Boundary Report":
        errors.append("report milestone mismatch")
    if report.get("status") not in {
        "pass_memory_state_influence_boundary_report",
        "fail_memory_state_influence_boundary_report",
    }:
        errors.append(f"unexpected report status: {report.get('status')}")
    if report.get("input_kind") not in {"directory", "file"}:
        errors.append(f"unexpected input_kind: {report.get('input_kind')}")
    if sorted(report.get("supported_input_suffixes", [])) != SUPPORTED_SUFFIXES:
        errors.append("supported_input_suffixes drifted from schema contract")
    _validate_scan_limits(report.get("scan_limits", {}), errors)
    _validate_input_files(report.get("input_files", []), errors)
    _validate_skipped_inputs(report.get("skipped_inputs", []), errors)
    _validate_influence_boundary(report.get("influence_boundary", {}), errors)
    _validate_findings(report.get("findings", []), errors)
    _validate_false_map("claim_boundary", report.get("claim_boundary", {}), EXPECTED_CLAIM_BOUNDARY_FIELDS, errors)
    _validate_false_map("side_effect_boundary", report.get("side_effect_boundary", {}), EXPECTED_SIDE_EFFECT_FIELDS, errors)
    _validate_required_fields("output_files", report.get("output_files", {}), EXPECTED_OUTPUT_FIELDS, errors)
    return "pass" if len(errors) == start_error_count else "fail"


def _validate_scan_limits(scan_limits: Any, errors: list[str]) -> None:
    if not isinstance(scan_limits, dict):
        errors.append("scan_limits must be an object")
        return
    _validate_required_fields(
        "scan_limits",
        scan_limits,
        [
            "max_input_files",
            "max_input_file_bytes",
            "max_total_input_bytes",
            "max_skipped_input_records",
            "raw_content_included",
        ],
        errors,
    )
    if scan_limits.get("raw_content_included") is not False:
        errors.append("scan_limits.raw_content_included must be false")
    for field in ("max_input_files", "max_input_file_bytes", "max_total_input_bytes", "max_skipped_input_records"):
        if not _is_nonnegative_int(scan_limits.get(field), minimum=1):
            errors.append(f"scan_limits.{field} must be a positive integer")


def _validate_input_files(input_files: Any, errors: list[str]) -> None:
    if not isinstance(input_files, list):
        errors.append("input_files must be a list")
        return
    for index, file_report in enumerate(input_files):
        label = f"input_files[{index}]"
        if not isinstance(file_report, dict):
            errors.append(f"{label} must be an object")
            continue
        _validate_required_fields(label, file_report, EXPECTED_INPUT_FILE_FIELDS, errors)
        unexpected = sorted(set(file_report) - set(EXPECTED_INPUT_FILE_FIELDS))
        if unexpected:
            errors.append(f"{label} has unexpected fields: {', '.join(unexpected)}")
        if file_report.get("raw_content_included") is not False:
            errors.append(f"{label}.raw_content_included must be false")
        sha256 = file_report.get("sha256")
        if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
            errors.append(f"{label}.sha256 must be 64 lowercase hex chars")
        for field in ("bytes", "line_count", "secret_like_evidence_count"):
            if not _is_nonnegative_int(file_report.get(field)):
                errors.append(f"{label}.{field} must be a non-negative integer")
        for field in (
            "json_parse_errors",
            "toml_parse_errors",
            "json_key_paths_sample",
            "yaml_key_paths_sample",
            "structured_key_paths_sample",
            "signal_ids",
            "signal_evidence",
        ):
            if not isinstance(file_report.get(field), list):
                errors.append(f"{label}.{field} must be a list")
        decision = file_report.get("decision", {})
        if not isinstance(decision, dict):
            errors.append(f"{label}.decision must be an object")
        else:
            _validate_required_fields(f"{label}.decision", decision, ["decision", "authority_ceiling", "reason"], errors)
        for evidence_index, evidence in enumerate(file_report.get("signal_evidence", [])):
            _validate_signal_evidence(f"{label}.signal_evidence[{evidence_index}]", evidence, errors)


def _validate_signal_evidence(label: str, evidence: Any, errors: list[str]) -> None:
    if not isinstance(evidence, dict):
        errors.append(f"{label} must be an object")
        return
    _validate_required_fields(label, evidence, ["ref", "signal_id", "label", "matched", "raw_content_included"], errors)
    allowed = {"ref", "signal_id", "label", "matched", "evidence_kind", "raw_content_included"}
    unexpected = sorted(set(evidence) - allowed)
    if unexpected:
        errors.append(f"{label} has unexpected fields: {', '.join(unexpected)}")
    if evidence.get("raw_content_included") is not False:
        errors.append(f"{label}.raw_content_included must be false")


def _validate_skipped_inputs(skipped_inputs: Any, errors: list[str]) -> None:
    if not isinstance(skipped_inputs, list):
        errors.append("skipped_inputs must be a list")
        return
    for index, skipped in enumerate(skipped_inputs):
        label = f"skipped_inputs[{index}]"
        if not isinstance(skipped, dict):
            errors.append(f"{label} must be an object")
            continue
        _validate_required_fields(label, skipped, ["path", "reason"], errors)
        allowed = {"path", "reason", "bytes_observed"}
        unexpected = sorted(set(skipped) - allowed)
        if unexpected:
            errors.append(f"{label} has unexpected fields: {', '.join(unexpected)}")
        if "bytes_observed" in skipped and not _is_nonnegative_int(skipped.get("bytes_observed")):
            errors.append(f"{label}.bytes_observed must be a non-negative integer")


def _validate_influence_boundary(boundary: Any, errors: list[str]) -> None:
    if not isinstance(boundary, dict):
        errors.append("influence_boundary must be an object")
        return
    _validate_required_fields("influence_boundary", boundary, EXPECTED_INFLUENCE_BOUNDARY_FIELDS, errors)
    unexpected = sorted(set(boundary) - set(EXPECTED_INFLUENCE_BOUNDARY_FIELDS))
    if unexpected:
        errors.append(f"influence_boundary has unexpected fields: {', '.join(unexpected)}")
    for field in (
        "selected_refs",
        "candidate_influence_refs",
        "inform_only_allowed_refs",
        "omitted_refs",
        "blocked_refs",
        "stale_or_superseded_refs",
        "imported_context_refs",
        "source_refs",
    ):
        if not isinstance(boundary.get(field), list):
            errors.append(f"influence_boundary.{field} must be a list")


def _validate_findings(findings: Any, errors: list[str]) -> None:
    if not isinstance(findings, list):
        errors.append("findings must be a list")
        return
    for index, finding in enumerate(findings):
        label = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{label} must be an object")
            continue
        _validate_required_fields(label, finding, ["finding_id", "severity", "recommendation"], errors)
        if finding.get("severity") not in {"info", "medium", "high"}:
            errors.append(f"{label}.severity must be info, medium, or high")
        if finding.get("raw_content_included") is True:
            errors.append(f"{label}.raw_content_included must not be true")


def _validate_raw_content_boundary(report: dict[str, Any], errors: list[str]) -> str:
    start_error_count = len(errors)
    for path, value in _walk(report):
        if path.endswith(".raw_content_included") and value is not False:
            errors.append(f"{path} must be false")
    return "pass" if len(errors) == start_error_count else "fail"


def _validate_embedded_gate(report: dict[str, Any], errors: list[str]) -> str:
    start_error_count = len(errors)
    if not isinstance(report, dict):
        return "not_checked"
    gate = report.get("integration_gate", {})
    boundary = report.get("influence_boundary", {})
    if not isinstance(gate, dict) or not isinstance(boundary, dict):
        errors.append("report must include integration_gate and influence_boundary objects")
        return "fail"
    _validate_required_fields("integration_gate", gate, EXPECTED_GATE_FIELDS, errors)
    unexpected = sorted(set(gate) - set(EXPECTED_GATE_FIELDS))
    if unexpected:
        errors.append(f"integration_gate has unexpected fields: {', '.join(unexpected)}")
    if gate.get("schema_id") != "ctxvault.memory-state-influence-boundary-integration-gate/v0":
        errors.append("integration_gate schema_id mismatch")
    if gate.get("mode") != "fail_on_blocked":
        errors.append("integration_gate mode must be fail_on_blocked")
    if gate.get("raw_content_included") is not False:
        errors.append("integration_gate.raw_content_included must be false")

    expected_counts = {
        "blocked_ref_count": len(boundary.get("blocked_refs", [])),
        "omitted_ref_count": len(boundary.get("omitted_refs", [])),
        "stale_or_superseded_ref_count": len(boundary.get("stale_or_superseded_refs", [])),
        "imported_context_ref_count": len(boundary.get("imported_context_refs", [])),
    }
    for field, expected in expected_counts.items():
        if gate.get(field) != expected:
            errors.append(f"integration_gate.{field} {gate.get(field)} != {expected}")
    report_passed = str(report.get("status", "")).startswith("pass_")
    expected_default = 0 if report_passed else 1
    expected_fail_on_blocked = 1
    if report_passed:
        expected_fail_on_blocked = 2 if expected_counts["blocked_ref_count"] else 0
    if gate.get("default_exit_code") != expected_default:
        errors.append(f"integration_gate.default_exit_code {gate.get('default_exit_code')} != {expected_default}")
    if gate.get("fail_on_blocked_exit_code") != expected_fail_on_blocked:
        errors.append(
            f"integration_gate.fail_on_blocked_exit_code {gate.get('fail_on_blocked_exit_code')} != {expected_fail_on_blocked}"
        )
    if gate.get("passed") is not (report_passed and expected_counts["blocked_ref_count"] == 0):
        errors.append("integration_gate.passed does not match report status and blocked refs")
    return "pass" if len(errors) == start_error_count else "fail"


def _validate_required_set(label: str, schema: dict[str, Any], expected: list[str], errors: list[str]) -> None:
    missing = [field for field in expected if field not in schema.get("required", [])]
    if missing:
        errors.append(f"{label} missing required fields: {', '.join(missing)}")


def _validate_required_fields(label: str, payload: Any, required: list[str], errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append(f"{label} must be an object")
        return
    missing = [field for field in required if field not in payload]
    if missing:
        errors.append(f"{label} missing required fields: {', '.join(missing)}")


def _validate_false_map(label: str, payload: Any, required: list[str], errors: list[str]) -> None:
    if not isinstance(payload, dict):
        errors.append(f"{label} must be an object")
        return
    _validate_required_fields(label, payload, required, errors)
    unexpected = sorted(set(payload) - set(required))
    if unexpected:
        errors.append(f"{label} has unexpected fields: {', '.join(unexpected)}")
    true_fields = [field for field in required if payload.get(field) is not False]
    if true_fields:
        errors.append(f"{label} fields must all be false: {', '.join(true_fields)}")


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            items.extend(_walk(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            items.extend(_walk(child, f"{path}[{index}]"))
    return items


def _is_nonnegative_int(value: Any, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_input_arg(path: Path) -> str:
    return path.as_posix()


def _display_path(path: Path, root: Path) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the full Memory State Influence Boundary report contract.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", type=Path, default=SAMPLE_INPUT)
    parser.add_argument("--schema", type=Path, default=REPORT_SCHEMA)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_report_contract(
        args.root,
        input_path=args.input,
        schema_path=args.schema,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_report_contract" else 1


if __name__ == "__main__":
    raise SystemExit(main())
