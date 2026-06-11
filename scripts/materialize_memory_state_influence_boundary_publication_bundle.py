#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "release" / "memory-state-governability-overlay" / "2026-06-11" / "memory-state-influence-boundary-publication-bundle.json"


def materialize_memory_state_influence_boundary_publication_bundle(
    source_root: Path,
    checkout: Path,
    *,
    bundle_path: Path = DEFAULT_BUNDLE,
) -> dict[str, Any]:
    source_root = Path(source_root).resolve()
    checkout = Path(checkout).resolve()
    bundle_path = Path(bundle_path)
    if not bundle_path.is_absolute():
        bundle_path = source_root / bundle_path

    errors: list[str] = []
    copied_files: list[str] = []
    before_status_lines: list[str] = []
    after_status_lines: list[str] = []

    if not bundle_path.exists():
        errors.append(f"missing publication bundle {bundle_path}")
        bundle: dict[str, Any] = {}
    else:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))

    if not (checkout / ".git").exists():
        errors.append("checkout must be a git checkout with .git")
    else:
        before = _run_git(checkout, ["status", "--porcelain=v1"])
        if before.returncode != 0:
            errors.append(f"git status failed: {before.stderr.strip()}")
        before_status_lines = [line for line in before.stdout.splitlines() if line.strip()]
        if before_status_lines:
            errors.append("checkout must be clean before materialization")

    if bundle.get("status") != "pass_memory_state_influence_boundary_publication_bundle":
        errors.append(f"publication bundle is not ready: {bundle.get('status')}")

    publication_files = bundle.get("publication_files", [])
    file_digests = bundle.get("file_digests", {})
    if not isinstance(publication_files, list):
        errors.append("publication_files must be a list")
        publication_files = []
    if not isinstance(file_digests, dict):
        errors.append("file_digests must be an object")
        file_digests = {}

    if not errors:
        for rel in publication_files:
            rel_path = Path(str(rel))
            if rel_path.is_absolute() or ".." in rel_path.parts:
                errors.append(f"unsafe publication path {rel}")
                break
            src = source_root / rel_path
            dst = checkout / rel_path
            if not src.exists():
                errors.append(f"missing source file {rel}")
                break
            data = src.read_bytes()
            expected_sha = file_digests.get(str(rel), {}).get("sha256")
            observed_sha = _sha256_bytes(data)
            if expected_sha != observed_sha:
                errors.append(f"source digest mismatch for {rel}")
                break
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_files.append(str(rel))

    if not errors:
        after = _run_git(checkout, ["status", "--porcelain=v1"])
        if after.returncode != 0:
            errors.append(f"git status after materialization failed: {after.stderr.strip()}")
        after_status_lines = [line for line in after.stdout.splitlines() if line.strip()]

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-publication-bundle-materialization/v0",
        "status": "pass_memory_state_influence_boundary_publication_bundle_materialized" if not errors else "fail_memory_state_influence_boundary_publication_bundle_materialized",
        "milestone": bundle.get("milestone"),
        "public_repo": bundle.get("public_repo"),
        "publication_bundle_sha256": bundle.get("publication_bundle_sha256"),
        "copied_file_count": len(copied_files),
        "copied_files": copied_files,
        "before_status_line_count": len(before_status_lines),
        "after_status_lines": after_status_lines,
        "local_checkout_write_executed": bool(copied_files),
        "branch_created": False,
        "commit_created": False,
        "push_executed": False,
        "pull_request_created": False,
        "tag_created": False,
        "release_created": False,
        "github_pages_deployed": False,
        "live_url_checked": False,
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_git(checkout: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=checkout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the Memory State Influence Boundary publication bundle into a clean local checkout.")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args()
    receipt = materialize_memory_state_influence_boundary_publication_bundle(
        args.source_root,
        args.checkout,
        bundle_path=args.bundle,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass_memory_state_influence_boundary_publication_bundle_materialized" else 1


if __name__ == "__main__":
    raise SystemExit(main())
