#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FINAL_PREFLIGHT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_final_preflight.py")
MATERIALIZER_SCRIPT = Path("scripts/materialize_memory_state_influence_boundary_publication_bundle.py")
ENVELOPE_SCRIPT = Path("scripts/render_memory_state_influence_boundary_publish_command_envelope.py")
DEFAULT_COMMIT_MESSAGE = "Add local memory state influence boundary report"


def publish_memory_state_influence_boundary_public_patch(
    source_root: Path = ROOT,
    *,
    checkout: Path,
    materialize: bool = False,
    execute_commit: bool = False,
    execute_push: bool = False,
    commit_message: str = DEFAULT_COMMIT_MESSAGE,
) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    checkout = Path(checkout).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    commands_executed: list[list[str]] = []

    if execute_push and not execute_commit:
        errors.append("--execute-push requires --execute-commit")
    if execute_commit and not materialize:
        errors.append("--execute-commit requires --materialize")

    preflight_module = _load_script(source_root, FINAL_PREFLIGHT_SCRIPT, "memory_state_publisher_preflight")
    materializer_module = _load_script(source_root, MATERIALIZER_SCRIPT, "memory_state_publisher_materializer")
    envelope_module = _load_script(source_root, ENVELOPE_SCRIPT, "memory_state_publisher_envelope")

    source_preflight = preflight_module.check_memory_state_influence_boundary_final_preflight(
        source_root,
        include_unittests=False,
        include_publisher_smoke=False,
    )
    envelope = envelope_module.render_memory_state_influence_boundary_publish_command_envelope(source_root)
    checkout_status_before = _git_status(checkout)
    if checkout_status_before.get("returncode") != 0:
        errors.append("target checkout git status failed")
    elif checkout_status_before.get("line_count") and materialize:
        errors.append("target checkout must be clean before --materialize")

    materialization: dict[str, Any] = {"status": "not_requested", "local_checkout_write_executed": False}
    target_preflight: dict[str, Any] = {"status": "not_checked", "checked": False}
    commit_result: dict[str, Any] = {"executed": False}
    push_result: dict[str, Any] = {"executed": False}

    if source_preflight.get("status") != "pass_memory_state_influence_boundary_final_preflight":
        errors.append("source final preflight failed")
    if envelope.get("status") != "pass_memory_state_influence_boundary_publish_command_envelope":
        errors.append("publish command envelope failed")

    if materialize and not errors:
        materialization = materializer_module.materialize_memory_state_influence_boundary_publication_bundle(source_root, checkout)
        if materialization.get("status") != "pass_memory_state_influence_boundary_publication_bundle_materialized":
            errors.append("materialization failed")
        else:
            target_preflight = _run_target_preflight(checkout)
            if target_preflight.get("status") != "pass_memory_state_influence_boundary_target_preflight":
                errors.append("target final preflight failed after materialization")
    elif not materialize:
        warnings.append("dry run only: pass --materialize to copy the bundle into the target checkout")

    if execute_commit and not errors:
        add_paths = _publish_add_paths(envelope)
        add_result = _run_git(checkout, ["add", *add_paths])
        commands_executed.append(["git", "add", *add_paths])
        if add_result.returncode != 0:
            errors.append(f"git add failed: {add_result.stderr.strip()}")
        else:
            commit = _run_git(checkout, ["commit", "-m", commit_message])
            commands_executed.append(["git", "commit", "-m", commit_message])
            commit_result = _completed_receipt(commit, executed=True)
            if commit.returncode != 0:
                errors.append(f"git commit failed: {commit.stderr.strip()}")

    if execute_push and not errors:
        push = _run_git(checkout, ["push", "origin", "main"])
        commands_executed.append(["git", "push", "origin", "main"])
        push_result = _completed_receipt(push, executed=True)
        if push.returncode != 0:
            errors.append(f"git push failed: {push.stderr.strip()}")

    checkout_status_after = _git_status(checkout)
    status = "pass_memory_state_influence_boundary_public_patch_publisher" if not errors else "fail_memory_state_influence_boundary_public_patch_publisher"
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-public-patch-publisher/v0",
        "status": status,
        "mode": _mode(materialize=materialize, execute_commit=execute_commit, execute_push=execute_push),
        "milestone": "Local Memory State Influence Boundary Report",
        "source_root": str(source_root),
        "checkout": str(checkout),
        "source_final_preflight_status": source_preflight.get("status"),
        "source_final_preflight_unittests": source_preflight.get("checks", {}).get("memory_state_unittests", {}).get("status"),
        "publication_bundle_sha256": source_preflight.get("publication_bundle_sha256"),
        "publication_file_count": source_preflight.get("publication_file_count"),
        "materialization": materialization,
        "target_preflight_status": target_preflight.get("status"),
        "target_preflight": _summarize_target_preflight(target_preflight),
        "checkout_status_before": checkout_status_before,
        "checkout_status_after": checkout_status_after,
        "planned_commands": {
            "source_final_preflight": "python3 scripts/check_memory_state_influence_boundary_final_preflight.py",
            "materialize": f"python3 scripts/materialize_memory_state_influence_boundary_publication_bundle.py --checkout {checkout}",
            "target_preflight": f"python3 scripts/check_memory_state_influence_boundary_final_preflight.py --root {checkout} --skip-unittests",
            "publish": envelope.get("publish_commands", []),
            "post_publish": envelope.get("post_publish_commands", []),
        },
        "commands_executed": commands_executed,
        "commit": commit_result,
        "push": push_result,
        "manual_review_required": "owner_explicit_execute_commit_and_execute_push_flags_only",
        "local_checkout_write_executed": bool(materialization.get("local_checkout_write_executed")),
        "commit_created": bool(commit_result.get("executed") and commit_result.get("returncode") == 0),
        "push_executed": bool(push_result.get("executed") and push_result.get("returncode") == 0),
        "publication_executed": bool(push_result.get("executed") and push_result.get("returncode") == 0),
        "outreach_performed": False,
        "warnings": warnings,
        "errors": errors,
    }


def _load_script(root: Path, rel_path: Path, module_name: str) -> Any:
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _git_status(checkout: Path) -> dict[str, Any]:
    if not (checkout / ".git").exists():
        return {
            "returncode": 1,
            "line_count": 0,
            "lines": [],
            "stderr_tail": "checkout must be a git checkout with .git",
        }
    completed = _run_git(checkout, ["status", "--porcelain=v1"])
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return {
        "returncode": completed.returncode,
        "line_count": len(lines),
        "lines": lines,
        "stderr_tail": completed.stderr[-4000:],
    }


def _run_target_preflight(checkout: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/check_memory_state_influence_boundary_final_preflight.py",
            "--skip-unittests",
        ],
        cwd=checkout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload: dict[str, Any] = {}
    try:
        decoded = json.loads(completed.stdout)
        if isinstance(decoded, dict):
            payload = decoded
    except json.JSONDecodeError:
        payload = {}
    expected = "pass_memory_state_influence_boundary_final_preflight"
    return {
        "status": "pass_memory_state_influence_boundary_target_preflight"
        if completed.returncode == 0 and payload.get("status") == expected
        else "fail_memory_state_influence_boundary_target_preflight",
        "returncode": completed.returncode,
        "observed_payload_status": payload.get("status"),
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "payload": payload,
    }


def _run_git(checkout: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=checkout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _publish_add_paths(envelope: dict[str, Any]) -> list[str]:
    commands = envelope.get("publish_commands", [])
    if not commands:
        return []
    first = str(commands[0])
    prefix = "git add "
    if not first.startswith(prefix):
        return []
    return first[len(prefix) :].split()


def _completed_receipt(completed: subprocess.CompletedProcess[str], *, executed: bool) -> dict[str, Any]:
    return {
        "executed": executed,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _summarize_target_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload or payload.get("status") == "not_checked":
        return {"checked": False, "status": payload.get("status", "not_checked")}
    inner = payload.get("payload", {})
    return {
        "checked": True,
        "status": payload.get("status"),
        "observed_payload_status": payload.get("observed_payload_status"),
        "go_no_go": inner.get("go_no_go"),
        "publication_file_count": inner.get("publication_file_count"),
        "materialized_copied_file_count": inner.get("materialized_copied_file_count"),
        "issue_count": inner.get("issue_count"),
        "issues": inner.get("issues", []),
    }


def _mode(*, materialize: bool, execute_commit: bool, execute_push: bool) -> str:
    if execute_push:
        return "execute_push"
    if execute_commit:
        return "execute_commit"
    if materialize:
        return "materialize_only"
    return "dry_run"


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run or execute the Memory State Influence Boundary public patch publication flow.")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--materialize", action="store_true")
    parser.add_argument("--execute-commit", action="store_true")
    parser.add_argument("--execute-push", action="store_true")
    parser.add_argument("--commit-message", default=DEFAULT_COMMIT_MESSAGE)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    receipt = publish_memory_state_influence_boundary_public_patch(
        args.source_root,
        checkout=args.checkout,
        materialize=args.materialize,
        execute_commit=args.execute_commit,
        execute_push=args.execute_push,
        commit_message=args.commit_message,
    )
    if args.output_json:
        output = args.output_json if args.output_json.is_absolute() else args.source_root / args.output_json
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass_memory_state_influence_boundary_public_patch_publisher" else 1


if __name__ == "__main__":
    raise SystemExit(main())
