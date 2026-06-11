#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_SCRIPT = Path("scripts/run_memory_state_influence_boundary_report.py")
DEFAULT_INPUT = Path("examples/memory-state-influence-boundary")
DEFAULT_OUTPUT_DIR = Path(".ctxvault/memory-state-governability-overlay/consumer-wrapper-example")


def run_memory_state_influence_boundary_consumer_wrapper_example(
    root: Path = ROOT,
    *,
    input_path: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(root).resolve()
    input_display = str(input_path)
    input_arg = _resolve_input(root, input_path)
    output_dir = _resolve_output(root, output_dir)
    report_output = output_dir / "report"
    gate_output = output_dir / "gate"
    errors: list[str] = []

    report_result = _run_json(
        [
            sys.executable,
            str(REPORT_SCRIPT),
            "--input",
            str(input_arg),
            "--output-dir",
            str(report_output),
        ],
        root=root,
        allowed_returncodes={0},
    )
    if report_result["returncode"] != 0:
        errors.append(f"report command failed with exit code {report_result['returncode']}")
    if report_result["payload"].get("status") != "pass_memory_state_influence_boundary_report":
        errors.append(f"report status unexpected: {report_result['payload'].get('status')}")

    gate_result = _run_json(
        [
            sys.executable,
            str(REPORT_SCRIPT),
            "--input",
            str(input_arg),
            "--output-dir",
            str(gate_output),
            "--format",
            "gate",
            "--fail-on-blocked",
        ],
        root=root,
        allowed_returncodes={0, 2},
    )
    if gate_result["returncode"] not in {0, 2}:
        errors.append(f"gate command failed with exit code {gate_result['returncode']}")

    decision = _consumer_decision(report_result["payload"], gate_result["payload"], gate_result["returncode"])
    if decision["decision"] not in {"block", "allow_inform_only"}:
        errors.append(f"unsupported consumer decision: {decision['decision']}")
    if decision["decision"] == "block" and gate_result["returncode"] != 2:
        errors.append("blocked consumer decision must preserve gate exit code 2")
    if decision["decision"] == "allow_inform_only" and gate_result["returncode"] != 0:
        errors.append("allow consumer decision must preserve gate exit code 0")
    if gate_result["payload"].get("raw_content_included") is not False:
        errors.append("gate raw_content_included must be false")

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-consumer-wrapper-example/v0",
        "status": (
            "pass_memory_state_influence_boundary_consumer_wrapper_example"
            if not errors
            else "fail_memory_state_influence_boundary_consumer_wrapper_example"
        ),
        "milestone": "Local Memory State Influence Boundary Report",
        "input": input_display,
        "consumer_policy": "block when the report fails, the gate fails, or blocked_ref_count > 0; otherwise allow inform-only use",
        "decision": decision,
        "report_status": report_result["payload"].get("status"),
        "gate_returncode": gate_result["returncode"],
        "gate": {
            "schema_id": gate_result["payload"].get("schema_id"),
            "passed": gate_result["payload"].get("passed"),
            "default_exit_code": gate_result["payload"].get("default_exit_code"),
            "fail_on_blocked_exit_code": gate_result["payload"].get("fail_on_blocked_exit_code"),
            "blocked_ref_count": gate_result["payload"].get("blocked_ref_count"),
            "omitted_ref_count": gate_result["payload"].get("omitted_ref_count"),
            "stale_or_superseded_ref_count": gate_result["payload"].get("stale_or_superseded_ref_count"),
            "imported_context_ref_count": gate_result["payload"].get("imported_context_ref_count"),
            "raw_content_included": gate_result["payload"].get("raw_content_included"),
        },
        "report_output_files": report_result["payload"].get("output_files", {}),
        "command_shapes": {
            "report": "python3 scripts/run_memory_state_influence_boundary_report.py --input <memory-state-path>",
            "gate": "python3 scripts/run_memory_state_influence_boundary_report.py --input <memory-state-path> --format gate --fail-on-blocked",
        },
        "claim_boundary": report_result["payload"].get("claim_boundary", {}),
        "side_effect_boundary": report_result["payload"].get("side_effect_boundary", {}),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _consumer_decision(report: dict[str, Any], gate: dict[str, Any], gate_returncode: int) -> dict[str, Any]:
    report_status = str(report.get("status", ""))
    gate_passed = gate.get("passed") is True
    blocked_ref_count = int(gate.get("blocked_ref_count") or 0)
    if not report_status.startswith("pass_"):
        decision = "block"
        reason = "report_failed"
    elif gate_returncode not in {0, 2}:
        decision = "block"
        reason = "gate_failed"
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
        "gate_returncode": gate_returncode,
        "blocked_ref_count": gate.get("blocked_ref_count"),
        "omitted_ref_count": gate.get("omitted_ref_count"),
        "raw_content_included": gate.get("raw_content_included"),
        "consumed_raw_content": False,
    }


def _run_json(command: list[str], *, root: Path, allowed_returncodes: set[int]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload: dict[str, Any] = {}
    if completed.returncode in allowed_returncodes:
        try:
            decoded = json.loads(completed.stdout)
            if isinstance(decoded, dict):
                payload = decoded
        except json.JSONDecodeError:
            payload = {}
    return {
        "returncode": completed.returncode,
        "payload": payload,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _resolve_input(root: Path, input_path: Path) -> Path:
    input_path = Path(input_path)
    return input_path if input_path.is_absolute() else root / input_path


def _resolve_output(root: Path, output_dir: Path) -> Path:
    output_dir = Path(output_dir)
    return output_dir if output_dir.is_absolute() else root / output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Example consumer wrapper for the Memory State Influence Boundary gate.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    result = run_memory_state_influence_boundary_consumer_wrapper_example(
        args.root,
        input_path=args.input,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_consumer_wrapper_example" else 1


if __name__ == "__main__":
    raise SystemExit(main())
