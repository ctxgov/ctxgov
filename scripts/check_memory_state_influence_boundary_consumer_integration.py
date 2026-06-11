#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REPORT_SCRIPT = Path("scripts/run_memory_state_influence_boundary_report.py")
REPORT_CONTRACT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_report_contract.py")
REPORT_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json")
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def check_memory_state_influence_boundary_consumer_integration(
    root: Path = ROOT,
    *,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    checks: dict[str, Any] = {}
    secret_value = "sk-consumer-smoke-test-000000000000000"
    contract_module = _load_report_contract_module(root)
    report_schema = _load_json(root / REPORT_SCHEMA, "report schema", errors)

    with TemporaryDirectory(prefix="ctxgov-consumer-input-") as external_tmp, TemporaryDirectory(
        prefix="ctxgov-consumer-output-"
    ) as output_tmp:
        external_root = Path(external_tmp)
        output_root = Path(output_tmp)
        input_dir = external_root / "memory-state"
        input_dir.mkdir()
        blocked_file = input_dir / "MEMORY.md"
        pass_file = input_dir / "state-policy.toml"
        blocked_file.write_text(
            "\n".join(
                [
                    "Project memory may inform answers after review.",
                    "Deploy, commit, push, or publish only after explicit policy grant and rollback proof.",
                    f"api_key={secret_value}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        pass_file.write_text(
            "\n".join(
                [
                    "[profile]",
                    'memory = "team preference may inform answers"',
                    'policy = "inform only"',
                    'rollback = "required before influence"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        blocked_report = _run_json_command(
            "blocked_report",
            [
                sys.executable,
                str(REPORT_SCRIPT),
                "--input",
                str(input_dir),
                "--output-dir",
                str(output_root / "blocked-report"),
            ],
            root,
            runner,
            errors,
        )
        checks["blocked_report"] = blocked_report["receipt"]
        blocked_gate = _run_json_command(
            "blocked_gate",
            [
                sys.executable,
                str(REPORT_SCRIPT),
                "--input",
                str(input_dir),
                "--output-dir",
                str(output_root / "blocked-gate"),
                "--format",
                "gate",
                "--fail-on-blocked",
            ],
            root,
            runner,
            errors,
            allowed_returncodes={2},
        )
        checks["blocked_gate"] = blocked_gate["receipt"]
        pass_report = _run_json_command(
            "pass_report",
            [
                sys.executable,
                str(REPORT_SCRIPT),
                "--input",
                str(pass_file),
                "--output-dir",
                str(output_root / "pass-report"),
            ],
            root,
            runner,
            errors,
        )
        checks["pass_report"] = pass_report["receipt"]
        pass_gate = _run_json_command(
            "pass_gate",
            [
                sys.executable,
                str(REPORT_SCRIPT),
                "--input",
                str(pass_file),
                "--output-dir",
                str(output_root / "pass-gate"),
                "--format",
                "gate",
                "--fail-on-blocked",
            ],
            root,
            runner,
            errors,
        )
        checks["pass_gate"] = pass_gate["receipt"]

        blocked_contract = _validate_report_contract(
            contract_module,
            blocked_report["payload"],
            report_schema,
            "blocked_report",
            errors,
        )
        pass_contract = _validate_report_contract(
            contract_module,
            pass_report["payload"],
            report_schema,
            "pass_report",
            errors,
        )
        blocked_decision = _consumer_decision(blocked_report["payload"], blocked_gate["payload"])
        pass_decision = _consumer_decision(pass_report["payload"], pass_gate["payload"])
        _validate_consumer_decisions(blocked_decision, pass_decision, errors)
        _validate_no_raw_or_path_leak(
            [blocked_report["payload"], pass_report["payload"], blocked_gate["payload"], pass_gate["payload"]],
            external_root=external_root,
            secret_value=secret_value,
            errors=errors,
        )

    status = (
        "pass_memory_state_influence_boundary_consumer_integration"
        if not errors
        else "fail_memory_state_influence_boundary_consumer_integration"
    )
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-consumer-integration-smoke/v0",
        "status": status,
        "milestone": "Local Memory State Influence Boundary Report",
        "consumer_policy": "block when report fails, gate fails, or blocked_ref_count > 0; allow inform-only when gate passes",
        "consumer_decision_contract": {
            "blocked_case_expected_decision": "block",
            "pass_case_expected_decision": "allow_inform_only",
            "raw_content_required_by_consumer": False,
        },
        "blocked_report_contract_status": blocked_contract.get("report_contract_status"),
        "blocked_raw_content_boundary_status": blocked_contract.get("raw_content_boundary_status"),
        "blocked_embedded_gate_status": blocked_contract.get("integration_gate_embedded_status"),
        "pass_report_contract_status": pass_contract.get("report_contract_status"),
        "pass_raw_content_boundary_status": pass_contract.get("raw_content_boundary_status"),
        "pass_embedded_gate_status": pass_contract.get("integration_gate_embedded_status"),
        "blocked_gate_returncode": blocked_gate["returncode"],
        "pass_gate_returncode": pass_gate["returncode"],
        "blocked_decision": blocked_decision,
        "pass_decision": pass_decision,
        "external_absolute_path_leaked": False,
        "secret_like_content_leaked": False,
        "raw_content_included": False,
        "checks": checks,
        "claim_boundary": blocked_report["payload"].get("claim_boundary", {}),
        "side_effect_boundary": blocked_report["payload"].get("side_effect_boundary", {}),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _consumer_decision(report: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    report_status = str(report.get("status", ""))
    gate_passed = gate.get("passed") is True
    blocked_ref_count = gate.get("blocked_ref_count", 0)
    if not report_status.startswith("pass_"):
        decision = "block"
        reason = "report_failed"
    elif not gate_passed or blocked_ref_count:
        decision = "block"
        reason = "blocked_refs_present"
    else:
        decision = "allow_inform_only"
        reason = "gate_passed_no_blocked_refs"
    return {
        "decision": decision,
        "reason": reason,
        "report_status": report.get("status"),
        "gate_passed": gate.get("passed"),
        "default_exit_code": gate.get("default_exit_code"),
        "fail_on_blocked_exit_code": gate.get("fail_on_blocked_exit_code"),
        "blocked_ref_count": gate.get("blocked_ref_count"),
        "omitted_ref_count": gate.get("omitted_ref_count"),
        "raw_content_included": gate.get("raw_content_included"),
        "consumed_raw_content": False,
    }


def _validate_consumer_decisions(
    blocked_decision: dict[str, Any],
    pass_decision: dict[str, Any],
    errors: list[str],
) -> None:
    if blocked_decision.get("decision") != "block":
        errors.append(f"blocked consumer decision must be block, observed {blocked_decision.get('decision')}")
    if blocked_decision.get("reason") != "blocked_refs_present":
        errors.append(f"blocked consumer reason unexpected: {blocked_decision.get('reason')}")
    if blocked_decision.get("fail_on_blocked_exit_code") != 2:
        errors.append("blocked consumer decision must preserve fail_on_blocked_exit_code=2")
    if pass_decision.get("decision") != "allow_inform_only":
        errors.append(f"pass consumer decision must be allow_inform_only, observed {pass_decision.get('decision')}")
    if pass_decision.get("reason") != "gate_passed_no_blocked_refs":
        errors.append(f"pass consumer reason unexpected: {pass_decision.get('reason')}")
    if pass_decision.get("fail_on_blocked_exit_code") != 0:
        errors.append("pass consumer decision must preserve fail_on_blocked_exit_code=0")
    if blocked_decision.get("consumed_raw_content") or pass_decision.get("consumed_raw_content"):
        errors.append("consumer decisions must not consume raw content")


def _validate_report_contract(
    contract_module: Any,
    report: dict[str, Any],
    schema: dict[str, Any],
    label: str,
    errors: list[str],
) -> dict[str, Any]:
    if not report or not schema:
        errors.append(f"{label} contract cannot be checked")
        return {}
    result = contract_module.validate_memory_state_influence_boundary_report_contract(report, schema)
    for key in ("schema_contract_status", "report_contract_status", "raw_content_boundary_status", "integration_gate_embedded_status"):
        if result.get(key) != "pass":
            errors.append(f"{label} {key} failed: {result.get(key)}")
    for error in result.get("errors", []):
        errors.append(f"{label} contract error: {error}")
    return result


def _validate_no_raw_or_path_leak(
    payloads: list[dict[str, Any]],
    *,
    external_root: Path,
    secret_value: str,
    errors: list[str],
) -> None:
    rendered = json.dumps(payloads, sort_keys=True)
    if str(external_root) in rendered:
        errors.append("consumer integration payload leaked external absolute input root")
    if secret_value in rendered:
        errors.append("consumer integration payload leaked secret-like content")
    for path, value in _walk(payloads):
        if path.endswith(".raw_content_included") and value is not False:
            errors.append(f"{path} must be false")


def _run_json_command(
    check_id: str,
    command: list[str],
    root: Path,
    runner: CommandRunner,
    errors: list[str],
    *,
    allowed_returncodes: set[int] | None = None,
) -> dict[str, Any]:
    allowed = {0} if allowed_returncodes is None else allowed_returncodes
    completed = runner(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    payload: dict[str, Any] = {}
    if completed.returncode not in allowed:
        errors.append(f"{check_id} command returned {completed.returncode}: {completed.stderr[-400:]}")
    try:
        decoded = json.loads(completed.stdout)
        if isinstance(decoded, dict):
            payload = decoded
        else:
            errors.append(f"{check_id} stdout must be a JSON object")
    except json.JSONDecodeError as exc:
        errors.append(f"{check_id} stdout is not JSON: {exc}")
    return {
        "returncode": completed.returncode,
        "payload": payload,
        "receipt": {
            "command_shape": _command_shape(command),
            "returncode": completed.returncode,
            "observed_status": payload.get("status"),
            "stderr_tail": completed.stderr[-400:],
        },
    }


def _command_shape(command: list[str]) -> list[str]:
    shaped: list[str] = []
    for item in command:
        text = str(item)
        if text.startswith("/"):
            shaped.append("<absolute-path>")
        elif text.startswith("-"):
            shaped.append(text)
        elif "ctxgov-consumer-" in text:
            shaped.append("<consumer-temp-path>")
        else:
            shaped.append(text)
    return shaped


def _load_report_contract_module(root: Path) -> Any:
    script = root / REPORT_CONTRACT_SCRIPT
    spec = importlib.util.spec_from_file_location("memory_state_consumer_report_contract", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["memory_state_consumer_report_contract"] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"{label} missing: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} must be a JSON object")
        return {}
    return payload


def _walk(value: Any, path: str = "$") -> list[tuple[str, Any]]:
    items = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            items.extend(_walk(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            items.extend(_walk(child, f"{path}[{index}]"))
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test product consumption of the Memory State Influence Boundary report and gate.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_consumer_integration(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_consumer_integration" else 1


if __name__ == "__main__":
    raise SystemExit(main())
