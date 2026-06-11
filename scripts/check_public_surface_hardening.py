#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "v0.6.11"
PACK = RELEASE / "self-audit-public-report"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "pyproject.toml",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "memory-xray-demo-report.md",
    ROOT / "docs" / "memory-xray-demo-report.json",
    ROOT / "docs" / "memory-xray-demo-report.html",
    ROOT / "docs" / "try-in-5-minutes.html",
    ROOT / "docs" / "tiny-fixture-memory-xray-demo.html",
    ROOT / "docs" / "tiny-fixture-memory-xray-demo.json",
    ROOT / "docs" / "og.png",
    ROOT / "fixtures" / "memory_xray_tiny_repo" / "README.md",
    ROOT / "fixtures" / "memory_xray_tiny_repo" / "AGENTS.md",
    ROOT / "fixtures" / "memory_xray_tiny_repo" / "terminal.log",
    ROOT / "fixtures" / "memory_xray_tiny_repo" / "memory-summary.md",
    ROOT / "docs" / "case-studies" / "v0.6.9-self-audit.md",
    ROOT / ".github" / "workflows" / "public-surface.yml",
    ROOT / "scripts" / "render_public_memory_xray_preview.py",
    ROOT / "scripts" / "run_memory_xray_demo.py",
    ROOT / "scripts" / "run_tiny_fixture_memory_xray_demo.py",
    ROOT / "scripts" / "run_v012_fresh_clone_product_receipt.py",
    ROOT / "scripts" / "check_v012_fresh_clone_product_receipt.py",
    ROOT / "scripts" / "check_public_surface_hardening.py",
    ROOT / "tests" / "test_render_public_memory_xray_preview.py",
    ROOT / "tests" / "test_run_memory_xray_demo.py",
    ROOT / "tests" / "test_v012_fresh_clone_product_receipt.py",
    ROOT / "tests" / "test_v013_feedback_og_fixture_demo.py",
    ROOT / "tests" / "test_public_surface_hardening.py",
    ROOT / "release" / "v0.12.0" / "RELEASE_NOTES.md",
    ROOT / "release" / "v0.12.0" / "github-release.md",
    ROOT / "release" / "v0.12.0" / "fresh-clone-product-receipt.json",
    RELEASE / "RELEASE_NOTES.md",
    RELEASE / "github-release.md",
    PACK / "README.md",
    PACK / "self-audit-summary.json",
    PACK / "claim-lint.json",
    PACK / "leak-scan.json",
    PACK / "link-check.json",
    PACK / "publication-readiness.json",
    PACK / "publication-execution-receipt.json",
    PACK / "manifest.json",
]

TEXT_FILES = [path for path in REQUIRED_FILES if path.suffix.lower() not in {".json", ".png"}]

LIVE_SURFACE_FILES = [
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "pyproject.toml",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "try-in-5-minutes.html",
    ROOT / "docs" / "tiny-fixture-memory-xray-demo.html",
    ROOT / "docs" / "public-repo-metadata.md",
    ROOT / "docs" / "case-studies" / "v0.6.9-self-audit.md",
    RELEASE / "RELEASE_NOTES.md",
    RELEASE / "github-release.md",
    PACK / "README.md",
]

FORBIDDEN_LIVE_PATTERNS = [
    re.compile(r"pending owner-approved publication", re.I),
    re.compile(r"prepared for owner-approved publication", re.I),
    re.compile(r"License selection remains", re.I),
    re.compile(r"Changelog = \"https://github.com/ctxgov/ctxgov/releases/tag/v0\.6\.2\"", re.I),
]

OVERCLAIM_PATTERNS = [
    re.compile(r"\bpublic benchmark (?:complete|passed|result|score|leaderboard)\b", re.I),
    re.compile(r"\bsecurity (?:certification|guarantee)\b", re.I),
    re.compile(r"\bprovider(?:/model)? compatibility claim\b", re.I),
    re.compile(r"\badoption claim\b", re.I),
    re.compile(r"\bpackage publication claim\b", re.I),
    re.compile(r"\bhosted runtime claim\b", re.I),
    re.compile(r"\blive adapter claim\b", re.I),
    re.compile(r"\bMemory X-Ray CLI beta claim\b", re.I),
]

NEGATION_MARKERS = ("bad context", "no ", "not ", "not a ", "not claimed", "without ", "blocked", "does not")


def main() -> int:
    issues: list[dict[str, Any]] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            issues.append(_issue("missing_file", path, "Required public hardening file is missing."))
    if issues:
        return _finish(issues)

    _check_live_surface_text(issues)
    _check_pyproject(issues)
    _check_self_audit_receipts(issues)
    _check_workflow(issues)
    _check_local_links(issues)
    _check_preview_renderer(issues)
    _check_memory_xray_demo(issues)
    _check_feedback_og_and_fixture_demo(issues)
    _check_claim_boundaries(issues)

    return _finish(issues)


def _check_live_surface_text(issues: list[dict[str, Any]]) -> None:
    for path in LIVE_SURFACE_FILES:
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_LIVE_PATTERNS:
            if pattern.search(text):
                issues.append(_issue("live_surface_drift", path, pattern.pattern))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for phrase in [
        "release/v0.6.11/",
        "scripts/render_public_memory_xray_preview.py",
        "scripts/run_memory_xray_demo.py",
        "scripts/check_v012_fresh_clone_product_receipt.py",
        "release/v0.12.0/",
        "not a Memory X-Ray CLI beta",
        "src/ctxgov/",
        "agent-context-evals` - separate companion repo",
    ]:
        if phrase not in readme:
            issues.append(_issue("readme_missing_phrase", ROOT / "README.md", phrase))


def _check_pyproject(issues: list[dict[str, Any]]) -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    allowed_versions = ('version = "0.6.11"', 'version = "0.6.12"', 'version = "0.6.13"')
    if not any(version in text for version in allowed_versions):
        issues.append(_issue("pyproject_version", ROOT / "pyproject.toml", "version must be v0.6.11 or newer public source metadata"))
    allowed_changelogs = ("releases/tag/v0.6.11", "releases/tag/v0.6.12", "releases/tag/v0.6.13-auto-publish-research")
    if not any(changelog in text for changelog in allowed_changelogs):
        issues.append(_issue("pyproject_changelog", ROOT / "pyproject.toml", "Changelog must point to v0.6.11 or newer public source metadata"))


def _check_self_audit_receipts(issues: list[dict[str, Any]]) -> None:
    summary = _load_json(PACK / "self-audit-summary.json", issues)
    claim_lint = _load_json(PACK / "claim-lint.json", issues)
    leak_scan = _load_json(PACK / "leak-scan.json", issues)
    readiness = _load_json(PACK / "publication-readiness.json", issues)
    execution = _load_json(PACK / "publication-execution-receipt.json", issues)
    manifest = _load_json(PACK / "manifest.json", issues)

    if summary.get("status") not in {"ready_for_owner_approved_publication", "published_owner_approved_public_surface_hardening"}:
        issues.append(_issue("self_audit_status", PACK / "self-audit-summary.json", "Unexpected self-audit status."))
    if len(summary.get("findings", [])) != 4:
        issues.append(_issue("self_audit_findings", PACK / "self-audit-summary.json", "Expected 4 self-audit findings."))
    for receipt_path, receipt in [
        (PACK / "claim-lint.json", claim_lint),
        (PACK / "leak-scan.json", leak_scan),
    ]:
        if receipt.get("status") != "pass" or receipt.get("violations") not in ([], None):
            issues.append(_issue("receipt_not_pass", receipt_path, "Receipt must pass with no violations."))
    if readiness.get("status") not in {"ready_for_owner_approved_public_repo_patch", "published_owner_approved_public_write_bundle"}:
        issues.append(_issue("readiness_status", PACK / "publication-readiness.json", "Unexpected readiness status."))
    if execution.get("status") not in {"prepared_not_published", "published_and_verified"}:
        issues.append(_issue("execution_status", PACK / "publication-execution-receipt.json", "Unexpected execution status."))
    roles = {asset.get("role") for asset in manifest.get("assets", [])}
    for role in {"release_notes", "github_release_copy", "pack_overview", "self_audit_summary", "claim_boundary_receipt", "publication_execution_receipt"}:
        if role not in roles:
            issues.append(_issue("manifest_missing_role", PACK / "manifest.json", role))


def _check_workflow(issues: list[dict[str, Any]]) -> None:
    workflow = (ROOT / ".github" / "workflows" / "public-surface.yml").read_text(encoding="utf-8")
    for phrase in [
        "python3 scripts/check_public_evidence_release_pack.py",
        "python3 scripts/check_ascr_aligned_release_pack.py",
        "python3 scripts/check_public_surface_hardening.py",
        "python3 scripts/check_v012_fresh_clone_product_receipt.py",
        "tests.test_v013_feedback_og_fixture_demo",
        "python3 -m unittest tests.test_public_surface_hardening tests.test_render_public_memory_xray_preview",
    ]:
        if phrase not in workflow:
            issues.append(_issue("workflow_missing_command", ROOT / ".github" / "workflows" / "public-surface.yml", phrase))


def _check_local_links(issues: list[dict[str, Any]]) -> None:
    markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    href_link = re.compile(r'href="([^"]+)"')
    for path in TEXT_FILES:
        if path.suffix.lower() not in {".md", ".html", ".toml"}:
            continue
        text = path.read_text(encoding="utf-8")
        links = markdown_link.findall(text) + href_link.findall(text)
        for raw_link in links:
            link = raw_link.strip()
            if not link or link.startswith(("http://", "https://", "mailto:", "javascript:")):
                continue
            if link.startswith("#"):
                if link[1:] and f'id="{link[1:]}"' not in text:
                    issues.append(_issue("missing_local_anchor", path, link))
                continue
            resolved = (path.parent / link.split("#", 1)[0]).resolve()
            if not resolved.exists():
                issues.append(_issue("missing_local_link_target", path, link))


def _check_preview_renderer(issues: list[dict[str, Any]]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "preview.md"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/render_public_memory_xray_preview.py",
                "--input",
                "release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json",
                "--output",
                str(output),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            issues.append(_issue("preview_renderer_failed", ROOT / "scripts" / "render_public_memory_xray_preview.py", result.stdout + result.stderr))
            return
        report = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        if report.get("example_count") != 5:
            issues.append(_issue("preview_example_count", output.with_suffix(".json"), "Expected 5 rendered examples."))
        markdown = output.read_text(encoding="utf-8")
        for phrase in ["not a Memory X-Ray CLI beta", "No public benchmark claim", "No provider/model call"]:
            if phrase not in markdown:
                issues.append(_issue("preview_missing_phrase", output, phrase))


def _check_memory_xray_demo(issues: list[dict[str, Any]]) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_memory_xray_demo.py",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        issues.append(_issue("memory_xray_demo_failed", ROOT / "scripts" / "run_memory_xray_demo.py", result.stdout + result.stderr))
        return
    markdown = (ROOT / "docs" / "memory-xray-demo-report.md").read_text(encoding="utf-8")
    html = (ROOT / "docs" / "memory-xray-demo-report.html").read_text(encoding="utf-8")
    report = json.loads((ROOT / "docs" / "memory-xray-demo-report.json").read_text(encoding="utf-8"))
    if report.get("schema") != "ctxgov.public_memory_xray_demo.v0":
        issues.append(_issue("memory_xray_demo_schema", ROOT / "docs" / "memory-xray-demo-report.json", "Unexpected demo schema."))
    if report.get("example_count") != 5:
        issues.append(_issue("memory_xray_demo_example_count", ROOT / "docs" / "memory-xray-demo-report.json", "Expected 5 demo examples."))
    for phrase in ["## Before", "## After", "No public benchmark claim", "not a Memory X-Ray CLI beta"]:
        if phrase not in markdown:
            issues.append(_issue("memory_xray_demo_missing_phrase", ROOT / "docs" / "memory-xray-demo-report.md", phrase))
    for phrase in ["Memory X-Ray Demo Report", "Before", "After"]:
        if phrase not in html:
            issues.append(_issue("memory_xray_demo_html_missing_phrase", ROOT / "docs" / "memory-xray-demo-report.html", phrase))
    for phrase in ['<main class="report-shell">', "Before Context", "After Report", "finding-card"]:
        if phrase not in html:
            issues.append(_issue("memory_xray_demo_html_missing_phrase", ROOT / "docs" / "memory-xray-demo-report.html", phrase))
    if "<pre># Memory X-Ray Demo Report" in html:
        issues.append(_issue("memory_xray_demo_html_shape", ROOT / "docs" / "memory-xray-demo-report.html", "Markdown pre wrapper must not be used."))

    try_page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")
    for phrase in ["Try in 5 minutes", "Clone", "Run", "Read report", "Optional eval", "No public benchmark claim", "No provider/model call"]:
        if phrase not in try_page:
            issues.append(_issue("try_page_missing_phrase", ROOT / "docs" / "try-in-5-minutes.html", phrase))


def _png_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", data[16:24])


def _check_feedback_og_and_fixture_demo(issues: list[dict[str, Any]]) -> None:
    og_path = ROOT / "docs" / "og.png"
    if _png_size(og_path) != (1200, 630):
        issues.append(_issue("og_image_size", og_path, "Expected 1200x630 PNG."))
    if og_path.stat().st_size <= 50_000:
        issues.append(_issue("og_image_size", og_path, "Expected non-trivial report UI screenshot."))

    for path in [
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "memory-xray-demo-report.html",
        ROOT / "docs" / "try-in-5-minutes.html",
    ]:
        text = path.read_text(encoding="utf-8")
        for phrase in [
            '<meta property="og:image" content="https://ctxgov.github.io/ctxgov/og.png" />',
            '<meta name="twitter:image" content="https://ctxgov.github.io/ctxgov/og.png" />',
        ]:
            if phrase not in text:
                issues.append(_issue("missing_og_metadata", path, phrase))

    try_page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")
    for phrase in [
        "Copy/paste feedback",
        "GitHub issue #22",
        "Run fixed fixture",
        "python3 scripts/run_tiny_fixture_memory_xray_demo.py",
        "docs/tiny-fixture-memory-xray-demo.html",
        "docs/tiny-fixture-memory-xray-demo.json",
        "fixed public-safe fixture only",
        "Run path clear? yes/no:",
        "Report useful? yes/no:",
        "Missing field:",
        "Integration shape:",
        "Confusing wording:",
        "No adoption claim",
    ]:
        if phrase not in try_page:
            issues.append(_issue("try_page_feedback_missing_phrase", ROOT / "docs" / "try-in-5-minutes.html", phrase))

    result = subprocess.run(
        [sys.executable, "scripts/run_tiny_fixture_memory_xray_demo.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        issues.append(_issue("tiny_fixture_demo_failed", ROOT / "scripts" / "run_tiny_fixture_memory_xray_demo.py", result.stdout + result.stderr))
        return
    fixture_html = (ROOT / "docs" / "tiny-fixture-memory-xray-demo.html").read_text(encoding="utf-8")
    for phrase in [
        "Tiny fixture repo demo",
        "File input",
        "Memory X-Ray report",
        "unsupported_claim",
        "unsafe_instruction",
        "terminal_failure",
        "memory_claim_drift",
        "not an arbitrary repo scanner",
    ]:
        if phrase not in fixture_html:
            issues.append(_issue("tiny_fixture_demo_missing_phrase", ROOT / "docs" / "tiny-fixture-memory-xray-demo.html", phrase))


def _check_claim_boundaries(issues: list[dict[str, Any]]) -> None:
    for path in TEXT_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            context = " ".join(lines[max(0, line_number - 3):line_number]).lower()
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(line) and not any(marker in context for marker in NEGATION_MARKERS):
                    issues.append(_issue("unnegated_overclaim_phrase", path, f"line {line_number}: {line.strip()}"))


def _load_json(path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        issues.append(_issue("invalid_json", path, str(exc)))
        return {}


def _issue(kind: str, path: Path, detail: str) -> dict[str, Any]:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    return {"kind": kind, "path": str(rel), "detail": detail}


def _finish(issues: list[dict[str, Any]]) -> int:
    report = {
        "schema": "ctxgov.public_surface_hardening_check.v0",
        "release": "v0.6.11",
        "status": "pass" if not issues else "fail",
        "issue_count": len(issues),
        "issues": issues,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
