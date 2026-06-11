#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
REPORT_SCRIPT = Path("scripts/run_memory_state_influence_boundary_report.py")
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def check_memory_state_influence_boundary_byo_smoke(
    root: Path = ROOT,
    *,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    checks: dict[str, Any] = {}
    secret_value = "sk-byo-smoke-test-000000000000000"

    with TemporaryDirectory(prefix="ctxgov-byo-input-") as external_tmp, TemporaryDirectory(
        prefix="ctxgov-byo-output-"
    ) as output_tmp:
        external_root = Path(external_tmp)
        output_root = Path(output_tmp)
        input_dir = external_root / "memory-state"
        input_dir.mkdir()
        safe_file = input_dir / "state-policy.toml"
        blocked_file = input_dir / "CLAUDE.md"
        ignored_file = input_dir / "artifact.bin"

        safe_file.write_text(
            "\n".join(
                [
                    "[profile]",
                    'memory = "team context may inform answers"',
                    'policy = "inform only"',
                    'rollback = "required before influence"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        blocked_file.write_text(
            "\n".join(
                [
                    "Project memory: local context may inform answers only after review.",
                    "@notes.md",
                    "Never execute deploy, commit, push, or publish actions without a policy grant and rollback path.",
                    f"api_key={secret_value}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        ignored_file.write_text("binary export placeholder\n", encoding="utf-8")

        report_command = [
            sys.executable,
            str(REPORT_SCRIPT),
            "--input",
            str(input_dir),
            "--output-dir",
            str(output_root / "report"),
        ]
        report_completed = _run(report_command, root, runner)
        report_payload = _load_json_payload("byo_report", report_completed, errors)
        checks["byo_report"] = _json_receipt(report_command, report_completed, report_payload)

        blocked_gate_command = [
            sys.executable,
            str(REPORT_SCRIPT),
            "--input",
            str(input_dir),
            "--output-dir",
            str(output_root / "blocked-gate"),
            "--format",
            "gate",
            "--fail-on-blocked",
        ]
        blocked_gate_completed = _run(blocked_gate_command, root, runner)
        blocked_gate = _load_json_payload("blocked_gate", blocked_gate_completed, errors)
        checks["blocked_gate"] = _json_receipt(blocked_gate_command, blocked_gate_completed, blocked_gate)

        pass_gate_command = [
            sys.executable,
            str(REPORT_SCRIPT),
            "--input",
            str(safe_file),
            "--output-dir",
            str(output_root / "pass-gate"),
            "--format",
            "gate",
            "--fail-on-blocked",
        ]
        pass_gate_completed = _run(pass_gate_command, root, runner)
        pass_gate = _load_json_payload("pass_gate", pass_gate_completed, errors)
        checks["pass_gate"] = _json_receipt(pass_gate_command, pass_gate_completed, pass_gate)

        _validate_byo_report(
            report_payload,
            external_root=external_root,
            secret_value=secret_value,
            errors=errors,
        )
        _validate_blocked_gate(blocked_gate_completed.returncode, blocked_gate, errors)
        _validate_pass_gate(pass_gate_completed.returncode, pass_gate, errors)
        _validate_rendered_outputs(
            report_payload,
            external_root=external_root,
            secret_value=secret_value,
            errors=errors,
        )

    status = "pass_memory_state_influence_boundary_byo_smoke" if not errors else "fail_memory_state_influence_boundary_byo_smoke"
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-byo-smoke/v0",
        "status": status,
        "milestone": "Local Memory State Influence Boundary Report",
        "byo_command_shape": "python3 scripts/run_memory_state_influence_boundary_report.py --input <external-memory-state-dir>",
        "blocked_gate_command_shape": "python3 scripts/run_memory_state_influence_boundary_report.py --input <external-memory-state-dir> --format gate --fail-on-blocked",
        "pass_gate_command_shape": "python3 scripts/run_memory_state_influence_boundary_report.py --input <external-state-policy.toml> --format gate --fail-on-blocked",
        "report_status": report_payload.get("status"),
        "input_kind": report_payload.get("input_kind"),
        "input_file_count": report_payload.get("input_file_count"),
        "skipped_input_count": report_payload.get("skipped_input_count"),
        "blocked_ref_count": len(report_payload.get("influence_boundary", {}).get("blocked_refs", [])),
        "inform_only_allowed_ref_count": len(report_payload.get("influence_boundary", {}).get("inform_only_allowed_refs", [])),
        "omitted_ref_count": len(report_payload.get("influence_boundary", {}).get("omitted_refs", [])),
        "imported_context_ref_count": len(report_payload.get("influence_boundary", {}).get("imported_context_refs", [])),
        "blocked_gate_returncode": blocked_gate_completed.returncode,
        "pass_gate_returncode": pass_gate_completed.returncode,
        "blocked_gate": blocked_gate,
        "pass_gate": pass_gate,
        "external_absolute_path_leaked": False,
        "secret_like_content_leaked": False,
        "raw_content_included": False,
        "checks": checks,
        "claim_boundary": report_payload.get("claim_boundary", {}),
        "side_effect_boundary": report_payload.get("side_effect_boundary", {}),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _validate_byo_report(
    payload: dict[str, Any],
    *,
    external_root: Path,
    secret_value: str,
    errors: list[str],
) -> None:
    if payload.get("status") != "pass_memory_state_influence_boundary_report":
        errors.append(f"BYO report status unexpected: {payload.get('status')}")
    if payload.get("input_kind") != "directory":
        errors.append(f"BYO report input_kind unexpected: {payload.get('input_kind')}")
    if payload.get("input_path") != "input":
        errors.append(f"BYO report must render external directory as input, observed {payload.get('input_path')}")
    if payload.get("input_file_count") != 2:
        errors.append(f"BYO report should scan two supported files, observed {payload.get('input_file_count')}")
    if payload.get("skipped_input_count") != 1:
        errors.append(f"BYO report should omit one unsupported file, observed {payload.get('skipped_input_count')}")
    boundary = payload.get("influence_boundary", {})
    if "input/CLAUDE.md" not in boundary.get("blocked_refs", []):
        errors.append("BYO report must block input/CLAUDE.md")
    if "input/state-policy.toml" not in boundary.get("inform_only_allowed_refs", []):
        errors.append("BYO report must allow input/state-policy.toml as inform-only")
    if "input/artifact.bin" not in boundary.get("omitted_refs", []):
        errors.append("BYO report must omit input/artifact.bin")
    if "input/CLAUDE.md" not in boundary.get("imported_context_refs", []):
        errors.append("BYO report must record imported context refs")
    rendered_payload = json.dumps(payload, sort_keys=True)
    if str(external_root) in rendered_payload:
        errors.append("BYO report leaked the external absolute input root")
    if secret_value in rendered_payload:
        errors.append("BYO report leaked secret-like content")
    raw_flags = [file_report.get("raw_content_included") for file_report in payload.get("input_files", [])]
    if any(bool(flag) for flag in raw_flags):
        errors.append(f"BYO report included raw content: {raw_flags}")
    if any(bool(value) for value in payload.get("claim_boundary", {}).values()):
        errors.append("BYO report claim boundary contains true values")
    if any(bool(value) for value in payload.get("side_effect_boundary", {}).values()):
        errors.append("BYO report side-effect boundary contains true values")


def _validate_blocked_gate(returncode: int, gate: dict[str, Any], errors: list[str]) -> None:
    if returncode != 2:
        errors.append(f"blocked gate should exit 2, observed {returncode}")
    if gate.get("schema_id") != "ctxvault.memory-state-influence-boundary-integration-gate/v0":
        errors.append(f"blocked gate schema_id unexpected: {gate.get('schema_id')}")
    if gate.get("passed") is not False:
        errors.append(f"blocked gate must fail closed, observed passed={gate.get('passed')}")
    if gate.get("blocked_ref_count", 0) < 1:
        errors.append(f"blocked gate must include blocked refs, observed {gate.get('blocked_ref_count')}")
    if gate.get("fail_on_blocked_exit_code") != 2:
        errors.append(f"blocked gate fail_on_blocked_exit_code unexpected: {gate.get('fail_on_blocked_exit_code')}")
    if gate.get("raw_content_included") is not False:
        errors.append("blocked gate must keep raw_content_included=false")


def _validate_pass_gate(returncode: int, gate: dict[str, Any], errors: list[str]) -> None:
    if returncode != 0:
        errors.append(f"pass gate should exit 0, observed {returncode}")
    if gate.get("schema_id") != "ctxvault.memory-state-influence-boundary-integration-gate/v0":
        errors.append(f"pass gate schema_id unexpected: {gate.get('schema_id')}")
    if gate.get("passed") is not True:
        errors.append(f"pass gate must pass, observed passed={gate.get('passed')}")
    if gate.get("blocked_ref_count") != 0:
        errors.append(f"pass gate must have zero blocked refs, observed {gate.get('blocked_ref_count')}")
    if gate.get("fail_on_blocked_exit_code") != 0:
        errors.append(f"pass gate fail_on_blocked_exit_code unexpected: {gate.get('fail_on_blocked_exit_code')}")
    if gate.get("raw_content_included") is not False:
        errors.append("pass gate must keep raw_content_included=false")


def _validate_rendered_outputs(
    payload: dict[str, Any],
    *,
    external_root: Path,
    secret_value: str,
    errors: list[str],
) -> None:
    for kind, path_text in payload.get("output_files", {}).items():
        path = Path(path_text)
        if not path.exists():
            errors.append(f"BYO rendered {kind} output is missing: {path_text}")
            continue
        rendered = path.read_text(encoding="utf-8")
        if str(external_root) in rendered:
            errors.append(f"BYO rendered {kind} output leaked external absolute input root")
        if secret_value in rendered:
            errors.append(f"BYO rendered {kind} output leaked secret-like content")
        if "input/CLAUDE.md" not in rendered:
            errors.append(f"BYO rendered {kind} output missing input-relative path")


def _run(command: list[str], root: Path, runner: CommandRunner) -> subprocess.CompletedProcess[str]:
    return runner(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _load_json_payload(check_id: str, completed: subprocess.CompletedProcess[str], errors: list[str]) -> dict[str, Any]:
    if completed.returncode not in {0, 2}:
        errors.append(f"{check_id} command returned {completed.returncode}: {completed.stderr[-400:]}")
        return {}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        errors.append(f"{check_id} stdout is not JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{check_id} stdout must be a JSON object")
        return {}
    return payload


def _json_receipt(command: list[str], completed: subprocess.CompletedProcess[str], payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "command_shape": _command_shape(command),
        "returncode": completed.returncode,
        "observed_status": payload.get("status"),
        "stderr_tail": completed.stderr[-400:],
    }


def _command_shape(command: list[str]) -> list[str]:
    shaped: list[str] = []
    for item in command:
        if item.startswith("/"):
            if item.endswith("run_memory_state_influence_boundary_report.py"):
                shaped.append("scripts/run_memory_state_influence_boundary_report.py")
            elif "ctxgov-byo-input-" in item:
                shaped.append("<external-input>")
            elif "ctxgov-byo-output-" in item:
                shaped.append("<output-dir>")
            else:
                shaped.append("<absolute-path>")
        else:
            shaped.append(item)
    return shaped


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BYO local file/directory smoke checks for the influence-boundary report.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_byo_smoke(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_byo_smoke" else 1


if __name__ == "__main__":
    raise SystemExit(main())
