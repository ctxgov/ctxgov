#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def require_files(paths: list[Path]) -> list[str]:
    return [str(path.relative_to(ROOT)) for path in paths if not path.exists()]


def private_text_issues(paths: list[Path]) -> list[dict[str, Any]]:
    forbidden = ["/Users/", "/private/tmp", "/var/folders/", "BEGIN PRIVATE KEY", "sk-", "ghp_", "gho_"]
    issues: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden:
            if marker in text:
                issues.append({"path": str(path.relative_to(ROOT)), "marker": marker})
    return issues


def main() -> int:
    receipt_path = ROOT / "release" / "v0.12.0" / "fresh-clone-product-receipt.json"
    required_files = [
        ROOT / "README.md",
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "try-in-5-minutes.html",
        ROOT / "docs" / "memory-xray-demo-report.html",
        receipt_path,
        ROOT / "release" / "v0.12.0" / "RELEASE_NOTES.md",
        ROOT / "release" / "v0.12.0" / "github-release.md",
        ROOT / "scripts" / "run_v012_fresh_clone_product_receipt.py",
        ROOT / "scripts" / "check_v012_fresh_clone_product_receipt.py",
        ROOT / "tests" / "test_v012_fresh_clone_product_receipt.py",
    ]
    failures: list[dict[str, Any]] = []
    missing = require_files(required_files)
    if missing:
        failures.append({"missing_files": missing})

    receipt: dict[str, Any] = {}
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    expected = {
        "schema": "ctxgov.fresh_clone_product_receipt.v0",
        "status": "pass_fresh_clone_product_receipt",
        "release_version": "v0.12.0",
        "source_repo": "https://github.com/ctxgov/ctxgov.git",
        "fresh_clone": True,
        "worktree_reused": False,
        "product_command": "python3 scripts/run_memory_xray_demo.py",
        "provider_model_calls_allowed": False,
        "memory_backend_write_allowed": False,
        "external_target_write_allowed": False,
        "local_private_paths_published": False,
        "publication_allowed": True,
    }
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            failures.append({key: receipt.get(key)})
    if not isinstance(receipt.get("source_commit"), str) or len(receipt.get("source_commit", "")) < 7:
        failures.append({"source_commit": receipt.get("source_commit")})

    report = receipt.get("report", {})
    if report.get("path") != "docs/memory-xray-demo-report.md":
        failures.append({"report_path": report.get("path")})
    if report.get("json_schema") != "ctxgov.public_memory_xray_demo.v0":
        failures.append({"json_schema": report.get("json_schema")})
    if report.get("example_count") != 5:
        failures.append({"example_count": report.get("example_count")})
    for field in ["sha256", "json_sha256", "html_sha256"]:
        value = report.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            failures.append({field: value})

    checks = {item.get("command"): item for item in receipt.get("checks", []) if isinstance(item, dict)}
    for command in [
        "python3 scripts/run_memory_xray_demo.py",
        "python3 scripts/check_public_surface_hardening.py",
    ]:
        entry = checks.get(command)
        if not entry:
            failures.append({"missing_check": command})
        elif entry.get("returncode") != 0:
            failures.append({"failed_check": command, "returncode": entry.get("returncode")})

    boundaries = receipt.get("claim_boundaries", {})
    for field in [
        "public_benchmark_claim_allowed",
        "security_claim_allowed",
        "provider_model_compatibility_claim_allowed",
        "adoption_claim_allowed",
        "human_reviewer_claim_allowed",
        "package_release_claim_allowed",
        "hosted_runtime_claim_allowed",
        "live_adapter_claim_allowed",
        "stable_protocol_claim_allowed",
    ]:
        if boundaries.get(field) is not False:
            failures.append({field: boundaries.get(field)})

    index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    try_page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")
    report_html = (ROOT / "docs" / "memory-xray-demo-report.html").read_text(encoding="utf-8")
    for phrase in ["try-in-5-minutes.html", "v0.12.0", "memory-xray-demo-report.html"]:
        if phrase not in index:
            failures.append({"index_missing_phrase": phrase})
    for phrase in [
        "Try in 5 minutes",
        "Clone",
        "Run",
        "Read report",
        "Optional eval",
        "No public benchmark claim",
        "No provider/model call",
    ]:
        if phrase not in try_page:
            failures.append({"try_page_missing_phrase": phrase})
    for phrase in ['<main class="report-shell">', "Before Context", "After Report", "finding-card"]:
        if phrase not in report_html:
            failures.append({"report_html_missing_phrase": phrase})
    if "<pre># Memory X-Ray Demo Report" in report_html:
        failures.append({"report_html": "markdown_pre_wrapper_present"})

    private_issues = private_text_issues(
        [
            ROOT / "README.md",
            ROOT / "docs" / "index.html",
            ROOT / "docs" / "try-in-5-minutes.html",
            ROOT / "docs" / "memory-xray-demo-report.html",
            ROOT / "release" / "v0.12.0" / "RELEASE_NOTES.md",
            ROOT / "release" / "v0.12.0" / "github-release.md",
            receipt_path,
        ]
    )
    if private_issues:
        failures.append({"private_text_issues": private_issues})

    status = "pass_fresh_clone_product_receipt_ready" if not failures else "fail_fresh_clone_product_receipt_ready"
    readiness = {
        "schema": "ctxgov.v012_fresh_clone_product_receipt_check.v0",
        "status": status,
        "receipt": "release/v0.12.0/fresh-clone-product-receipt.json",
        "source_ref": receipt.get("source_ref"),
        "source_commit": receipt.get("source_commit"),
        "report_sha256": report.get("sha256"),
        "publication_allowed": not failures,
        "public_benchmark_claim_allowed": False,
        "security_claim_allowed": False,
        "adoption_claim_allowed": False,
        "provider_model_compatibility_claim_allowed": False,
        "package_release_claim_allowed": False,
        "human_reviewer_claim_allowed": False,
        "failures": failures,
    }
    print(json.dumps(readiness, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
