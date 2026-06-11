#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPO_URL = "https://github.com/ctxgov/ctxgov.git"
DEFAULT_OUTPUT = ROOT / ".ctxvault" / "memory-state-governability-overlay" / "public-checkout-readiness.json"
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def check_memory_state_influence_boundary_public_checkout_readiness(
    source_root: Path = ROOT,
    *,
    checkout: Path | None = None,
    bundle_path: Path | None = None,
    bundle_md_path: Path | None = None,
    clone_url: str = PUBLIC_REPO_URL,
    run_final_preflight: bool = True,
    check_live: bool = False,
    require_live_pass: bool = False,
    keep_checkout: bool = False,
    runner: CommandRunner = subprocess.run,
) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    errors: list[dict[str, Any]] = []
    cleanup_dir: Path | None = None
    bundle_path = _resolve(source_root, bundle_path) if bundle_path is not None else None
    bundle_md_path = _resolve(source_root, bundle_md_path) if bundle_md_path is not None else None

    bundle_command = [sys.executable, "scripts/build_memory_state_influence_boundary_publication_bundle.py"]
    if bundle_path is not None:
        bundle_command.extend(["--output-json", str(bundle_path)])
        bundle_command.extend(["--output-md", str(bundle_md_path or bundle_path.with_suffix(".md"))])
    bundle_check = _run_json(
        bundle_command,
        cwd=source_root,
        runner=runner,
    )
    bundle = bundle_check.get("payload", {})
    if bundle.get("status") != "pass_memory_state_influence_boundary_publication_bundle":
        errors.append(_issue("publication_bundle_not_ready", "bundle.status", bundle.get("status")))

    if checkout is None:
        cleanup_dir = Path(tempfile.mkdtemp(prefix="ctxgov-public-readiness-"))
        checkout = cleanup_dir / "ctxgov"
        clone = _run_plain(["git", "clone", clone_url, str(checkout)], cwd=source_root, runner=runner)
        if clone.get("returncode") != 0:
            errors.append(_issue("public_repo_clone_failed", "clone.returncode", clone.get("returncode")))
    else:
        checkout = Path(checkout).resolve()
        clone = {
            "command": ["use_existing_checkout", str(checkout)],
            "returncode": 0,
            "status": "skipped_existing_checkout",
            "stdout_tail": "",
            "stderr_tail": "",
        }
    if not (checkout / ".git").exists():
        errors.append(_issue("public_checkout_missing_or_not_git", "checkout", str(checkout)))

    base_commit = _run_plain(["git", "rev-parse", "--short", "HEAD"], cwd=checkout, runner=runner) if checkout.exists() else {}
    materialization = _run_json(
        [
            sys.executable,
            "scripts/materialize_memory_state_influence_boundary_publication_bundle.py",
            "--source-root",
            str(source_root),
            "--checkout",
            str(checkout),
            *(["--bundle", str(bundle_path)] if bundle_path is not None else []),
        ],
        cwd=source_root,
        runner=runner,
    )
    materialization_payload = materialization.get("payload", {})
    if materialization_payload.get("status") != "pass_memory_state_influence_boundary_publication_bundle_materialized":
        errors.append(_issue("materialization_failed", "materialization.status", materialization_payload.get("status")))
    if bundle.get("publication_file_count") != materialization_payload.get("copied_file_count"):
        errors.append(
            _issue(
                "materialized_file_count_mismatch",
                "materialization.copied_file_count",
                {
                    "bundle": bundle.get("publication_file_count"),
                    "materialized": materialization_payload.get("copied_file_count"),
                },
            )
        )

    final_preflight = {"status": "skipped_by_caller", "payload": {}}
    if run_final_preflight:
        final_preflight = _run_json(
            [sys.executable, "scripts/check_memory_state_influence_boundary_final_preflight.py"],
            cwd=checkout,
            runner=runner,
        )
        if final_preflight.get("payload", {}).get("status") != "pass_memory_state_influence_boundary_final_preflight":
            errors.append(_issue("final_preflight_failed", "final_preflight.status", final_preflight.get("payload", {}).get("status")))

    live_check = {"status": "skipped_by_caller", "payload": {"live_fetch_performed": False}}
    if check_live:
        live_check = _run_json(
            [sys.executable, "scripts/check_memory_state_influence_boundary_live_publication.py", "--live"],
            cwd=checkout,
            runner=runner,
            allow_nonzero_json=True,
        )
        live_status = live_check.get("payload", {}).get("status")
        if require_live_pass and live_status != "pass_memory_state_influence_boundary_live_publication_check":
            errors.append(_issue("live_publication_check_failed", "live.status", live_status))

    git_status = _run_plain(["git", "status", "--short"], cwd=checkout, runner=runner) if checkout.exists() else {}
    status_lines = [line for line in git_status.get("stdout_tail", "").splitlines() if line.strip()]

    result = {
        "schema_id": "ctxvault.memory-state-influence-boundary-public-checkout-readiness/v0",
        "status": "pass_memory_state_influence_boundary_public_checkout_ready" if not errors else "fail_memory_state_influence_boundary_public_checkout_ready",
        "milestone": "Local Memory State Influence Boundary Report",
        "public_repo": "ctxgov/ctxgov",
        "clone_url": clone_url,
        "checkout": str(checkout),
        "checkout_retained": keep_checkout or cleanup_dir is None,
        "public_base_commit": base_commit.get("stdout_tail", "").strip() or None,
        "publication_bundle_sha256": bundle.get("publication_bundle_sha256"),
        "publication_file_count": bundle.get("publication_file_count"),
        "materialized_copied_file_count": materialization_payload.get("copied_file_count"),
        "final_preflight_status": final_preflight.get("payload", {}).get("status"),
        "live_publication_status": live_check.get("payload", {}).get("status"),
        "live_http_status": live_check.get("payload", {}).get("live_status", {}).get("http_status"),
        "live_error": live_check.get("payload", {}).get("live_status", {}).get("error"),
        "external_publish_pending": True,
        "branch_created": False,
        "commit_created": False,
        "push_executed": False,
        "pull_request_created": False,
        "tag_created": False,
        "release_created": False,
        "github_pages_deployed": False,
        "publication_executed": False,
        "outreach_performed": False,
        "clone": clone,
        "bundle_check": _summarize_check(bundle_check),
        "materialization": _summarize_check(materialization),
        "final_preflight": _summarize_check(final_preflight),
        "live_check": _summarize_check(live_check),
        "git_status_lines": status_lines,
        "issue_count": len(errors),
        "issues": errors,
    }

    if cleanup_dir is not None and not keep_checkout:
        shutil.rmtree(cleanup_dir, ignore_errors=True)
        result["checkout_removed"] = True
    else:
        result["checkout_removed"] = False
    return _redact_paths(result, source_root, checkout)


def _run_json(
    command: list[str],
    *,
    cwd: Path,
    runner: CommandRunner,
    allow_nonzero_json: bool = False,
) -> dict[str, Any]:
    plain = _run_plain(command, cwd=cwd, runner=runner)
    payload: dict[str, Any] = {}
    try:
        decoded = json.loads(plain.get("stdout", ""))
        if isinstance(decoded, dict):
            payload = decoded
    except json.JSONDecodeError:
        payload = {}
    status = "pass" if plain["returncode"] == 0 or (allow_nonzero_json and payload) else "fail"
    return {**plain, "status": status, "payload": payload}


def _resolve(root: Path, path: Path | None) -> Path | None:
    if path is None:
        return None
    path = Path(path)
    return path if path.is_absolute() else root / path


def _run_plain(command: list[str], *, cwd: Path, runner: CommandRunner) -> dict[str, Any]:
    if not cwd.exists():
        return {
            "command": command,
            "returncode": 127,
            "status": "fail",
            "stdout": "",
            "stderr": f"cwd does not exist: {cwd}",
            "stdout_tail": "",
            "stderr_tail": f"cwd does not exist: {cwd}",
        }
    completed = runner(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _summarize_check(check: dict[str, Any]) -> dict[str, Any]:
    payload = check.get("payload", {})
    return {
        "command": check.get("command"),
        "returncode": check.get("returncode"),
        "status": check.get("status"),
        "observed_payload_status": payload.get("status") if isinstance(payload, dict) else None,
        "stdout_tail": check.get("stdout_tail", ""),
        "stderr_tail": check.get("stderr_tail", ""),
    }


def _redact_paths(payload: Any, source_root: Path, checkout: Path) -> Any:
    source = str(source_root)
    target = str(checkout)
    if isinstance(payload, dict):
        return {key: _redact_paths(value, source_root, checkout) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_redact_paths(value, source_root, checkout) for value in payload]
    if isinstance(payload, str):
        return payload.replace(source, "<source-root>").replace(target, "<public-checkout>")
    return payload


def _issue(issue_id: str, where: str, detail: Any) -> dict[str, Any]:
    return {"issue_id": issue_id, "where": where, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Memory State Influence Boundary patch in a clean public ctxgov/ctxgov checkout without publishing.")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--bundle-md", type=Path)
    parser.add_argument("--clone-url", default=PUBLIC_REPO_URL)
    parser.add_argument("--skip-final-preflight", action="store_true")
    parser.add_argument("--check-live", action="store_true")
    parser.add_argument("--require-live-pass", action="store_true")
    parser.add_argument("--keep-checkout", action="store_true")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_public_checkout_readiness(
        args.source_root,
        checkout=args.checkout,
        bundle_path=args.bundle,
        bundle_md_path=args.bundle_md,
        clone_url=args.clone_url,
        run_final_preflight=not args.skip_final_preflight,
        check_live=args.check_live,
        require_live_pass=args.require_live_pass,
        keep_checkout=args.keep_checkout,
    )
    if args.output_json:
        output = args.output_json if args.output_json.is_absolute() else args.source_root / args.output_json
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_public_checkout_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
