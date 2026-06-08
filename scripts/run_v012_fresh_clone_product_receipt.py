#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "https://github.com/ctxgov/ctxgov.git"
DEFAULT_REF = "main"
DEFAULT_OUTPUT = ROOT / "release" / "v0.12.0" / "fresh-clone-product-receipt.json"


def sanitize(text: str, tmp_root: Path, clone_dir: Path) -> str:
    clone_variants = {str(clone_dir), str(clone_dir.resolve())}
    tmp_variants = {str(tmp_root), str(tmp_root.resolve())}
    if str(clone_dir).startswith("/tmp/"):
        clone_variants.add("/private" + str(clone_dir))
    if str(tmp_root).startswith("/tmp/"):
        tmp_variants.add("/private" + str(tmp_root))
    sanitized = text
    for variant in sorted(clone_variants, key=len, reverse=True):
        sanitized = sanitized.replace(variant, "<fresh-clone-repo>")
    for variant in sorted(tmp_variants, key=len, reverse=True):
        sanitized = sanitized.replace(variant, "<fresh-clone-tempdir>")
    sanitized = re.sub(r"/private/tmp/[^\s'\"<>]+", "<fresh-clone-tempdir>", sanitized)
    sanitized = re.sub(r"/tmp/[^\s'\"<>]+", "<fresh-clone-tempdir>", sanitized)
    sanitized = re.sub(r"/var/folders/[^\s'\"<>]+", "<fresh-clone-tempdir>", sanitized)
    return sanitized


def compact_lines(text: str, tmp_root: Path, clone_dir: Path, *, limit: int = 24) -> list[str]:
    lines = [sanitize(line.strip(), tmp_root, clone_dir) for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return lines
    return [*lines[: limit // 2], "...", *lines[-(limit // 2) :]]


def run_command(
    command: list[str],
    *,
    cwd: Path | None,
    display_command: str,
    tmp_root: Path,
    clone_dir: Path,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=env,
    )
    return {
        "command": display_command,
        "returncode": result.returncode,
        "stdout_lines": compact_lines(result.stdout, tmp_root, clone_dir),
        "stderr_lines": compact_lines(result.stderr, tmp_root, clone_dir),
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_receipt(repo_url: str, ref: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ctxgov-fresh-clone-product-") as tmp_name:
        tmp_root = Path(tmp_name)
        clone_dir = tmp_root / "repo"
        clone = run_command(
            ["git", "-c", "advice.detachedHead=false", "clone", "--depth", "1", "--branch", ref, repo_url, str(clone_dir)],
            cwd=None,
            display_command=f"git -c advice.detachedHead=false clone --depth 1 --branch {ref} {repo_url} <fresh-clone-repo>",
            tmp_root=tmp_root,
            clone_dir=clone_dir,
        )

        source_commit = ""
        checks: list[dict[str, Any]] = []
        report_summary: dict[str, Any] = {}
        if clone["returncode"] == 0:
            commit = run_command(
                ["git", "rev-parse", "HEAD"],
                cwd=clone_dir,
                display_command="git rev-parse HEAD",
                tmp_root=tmp_root,
                clone_dir=clone_dir,
            )
            if commit["returncode"] == 0 and commit["stdout_lines"]:
                source_commit = commit["stdout_lines"][0]

            demo = run_command(
                ["python3", "scripts/run_memory_xray_demo.py"],
                cwd=clone_dir,
                display_command="python3 scripts/run_memory_xray_demo.py",
                tmp_root=tmp_root,
                clone_dir=clone_dir,
            )
            checks.append(demo)

            report_md = clone_dir / "docs" / "memory-xray-demo-report.md"
            report_json = clone_dir / "docs" / "memory-xray-demo-report.json"
            report_html = clone_dir / "docs" / "memory-xray-demo-report.html"
            if demo["returncode"] == 0 and report_md.exists() and report_json.exists() and report_html.exists():
                report = load_json(report_json)
                report_summary = {
                    "path": "docs/memory-xray-demo-report.md",
                    "sha256": sha256(report_md),
                    "json_path": "docs/memory-xray-demo-report.json",
                    "json_sha256": sha256(report_json),
                    "html_path": "docs/memory-xray-demo-report.html",
                    "html_sha256": sha256(report_html),
                    "json_schema": report.get("schema"),
                    "example_count": report.get("example_count"),
                }

            public_surface = run_command(
                ["python3", "scripts/check_public_surface_hardening.py"],
                cwd=clone_dir,
                display_command="python3 scripts/check_public_surface_hardening.py",
                tmp_root=tmp_root,
                clone_dir=clone_dir,
            )
            checks.append(public_surface)

    failures: list[dict[str, Any]] = []
    if clone["returncode"] != 0:
        failures.append({"clone_returncode": clone["returncode"]})
    for check in checks:
        if check["returncode"] != 0:
            failures.append({"command": check["command"], "returncode": check["returncode"]})
    if report_summary.get("json_schema") != "ctxgov.public_memory_xray_demo.v0":
        failures.append({"json_schema": report_summary.get("json_schema")})
    if report_summary.get("example_count") != 5:
        failures.append({"example_count": report_summary.get("example_count")})

    return {
        "schema": "ctxgov.fresh_clone_product_receipt.v0",
        "status": "pass_fresh_clone_product_receipt" if not failures else "fail_fresh_clone_product_receipt",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generated_by": "scripts/run_v012_fresh_clone_product_receipt.py",
        "release_version": "v0.12.0",
        "receipt_scope": "fresh clone of the public CtxGov one-command Memory X-Ray product path",
        "source_repo": repo_url,
        "source_ref": ref,
        "source_commit": source_commit,
        "fresh_clone": True,
        "worktree_reused": False,
        "clone_depth": 1,
        "clone": clone,
        "product_command": "python3 scripts/run_memory_xray_demo.py",
        "checks": checks,
        "report": report_summary,
        "claim_boundaries": {
            "public_benchmark_claim_allowed": False,
            "security_claim_allowed": False,
            "provider_model_compatibility_claim_allowed": False,
            "adoption_claim_allowed": False,
            "human_reviewer_claim_allowed": False,
            "package_release_claim_allowed": False,
            "hosted_runtime_claim_allowed": False,
            "live_adapter_claim_allowed": False,
            "stable_protocol_claim_allowed": False,
        },
        "release_operation_network_required": True,
        "provider_model_calls_allowed": False,
        "memory_backend_write_allowed": False,
        "external_target_write_allowed": False,
        "local_private_paths_published": False,
        "publication_allowed": True,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the v0.12 public fresh-clone product receipt.")
    parser.add_argument("--repo-url", default=DEFAULT_REPO)
    parser.add_argument("--ref", default=DEFAULT_REF)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    receipt = build_receipt(args.repo_url, args.ref)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "status": receipt["status"]}, sort_keys=True))
    return 0 if receipt["status"] == "pass_fresh_clone_product_receipt" else 1


if __name__ == "__main__":
    raise SystemExit(main())
