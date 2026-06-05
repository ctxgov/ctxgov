#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release" / "v0.6.10"
PACK = RELEASE / "ascr-aligned-evidence-update"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "index.html",
    RELEASE / "RELEASE_NOTES.md",
    RELEASE / "github-release.md",
    PACK / "README.md",
    PACK / "ascr-alignment-summary.json",
    PACK / "claim-lint.json",
    PACK / "leak-scan.json",
    PACK / "link-check.json",
    PACK / "publication-readiness.json",
    PACK / "publication-execution-receipt.json",
    PACK / "manifest.json",
]

TEXT_FILES = [path for path in REQUIRED_FILES if path.suffix.lower() != ".json"]

REQUIRED_MANIFEST_ROLES = {
    "release_notes",
    "github_release_copy",
    "pack_overview",
    "ascr_alignment_summary",
    "claim_boundary_receipt",
    "public_leak_scan_receipt",
    "local_link_check_receipt",
    "publication_readiness_receipt",
    "publication_execution_receipt",
}

ASCR_PHRASES = [
    "Agent State & Context Runtime Contract",
    "https://github.com/ctxgov/ascr",
    "framework-neutral contract/toolkit",
    "No stable ASCR standard claim",
    "python3 scripts/check_ascr_aligned_release_pack.py",
]

HOMEPAGE_PHRASES = [
    "Agent State & Context Runtime Contract",
    "https://github.com/ctxgov/ascr",
    "v0.6.10",
    "ASCR-aligned",
]

README_PHRASES = [
    "ASCR",
    "Agent State & Context Runtime Contract",
    "release/v0.6.10/",
    "https://github.com/ctxgov/ascr",
]

OVERCLAIM_PATTERNS = [
    re.compile(r"\bpublic benchmark (?:complete|passed|result|score|leaderboard)\b", re.I),
    re.compile(r"\bsecurity (?:certification|guarantee)\b", re.I),
    re.compile(r"\bprovider(?:/model)? compatibility claim\b", re.I),
    re.compile(r"\badoption claim\b", re.I),
    re.compile(r"\bpackage publication claim\b", re.I),
    re.compile(r"\bhosted runtime claim\b", re.I),
    re.compile(r"\blive adapter claim\b", re.I),
    re.compile(r"\bpublic spec-stability claim\b", re.I),
    re.compile(r"\bstable ASCR standard claim\b", re.I),
]

NEGATION_MARKERS = (
    "bad context",
    "no ",
    "not ",
    "not a ",
    "not claimed",
    "without ",
    "blocked",
    "remain blocked",
    "does not",
)


def main() -> int:
    issues: list[dict[str, Any]] = []

    for path in REQUIRED_FILES:
        if not path.exists():
            issues.append(_issue("missing_file", path, "Required v0.6.10 file is missing."))

    if issues:
        return _finish(issues)

    alignment = _load_json(PACK / "ascr-alignment-summary.json", issues)
    claim_lint = _load_json(PACK / "claim-lint.json", issues)
    leak_scan = _load_json(PACK / "leak-scan.json", issues)
    link_check = _load_json(PACK / "link-check.json", issues)
    readiness = _load_json(PACK / "publication-readiness.json", issues)
    execution = _load_json(PACK / "publication-execution-receipt.json", issues)
    manifest = _load_json(PACK / "manifest.json", issues)

    _check_alignment(alignment, issues)
    _check_receipt("claim_lint", claim_lint, issues)
    _check_receipt("leak_scan", leak_scan, issues)
    _check_link_check(link_check, issues)
    _check_readiness(readiness, issues)
    _check_execution(execution, issues)
    _check_manifest(manifest, issues)
    _check_homepage(issues)
    _check_readme(issues)
    _check_local_links(issues)
    _check_text_boundaries(issues)

    return _finish(issues)


def _load_json(path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover
        issues.append(_issue("invalid_json", path, str(exc)))
        return {}


def _check_alignment(alignment: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "ascr-alignment-summary.json"
    if alignment.get("status") not in {
        "ready_for_owner_approved_publication",
        "published_owner_approved_ascr_aligned_update",
    }:
        issues.append(_issue("alignment_status", path, "Unexpected ASCR alignment status."))
    ascr = alignment.get("ascr", {})
    if ascr.get("public_repo") != "https://github.com/ctxgov/ascr":
        issues.append(_issue("ascr_repo", path, "ASCR public repo link is missing or incorrect."))
    if ascr.get("stable_standard_claim") is not False:
        issues.append(_issue("ascr_stability_claim", path, "stable_standard_claim must be false."))
    relationship = alignment.get("ctxgov_relationship", {})
    if relationship.get("defines_ascr_standard") is not False:
        issues.append(_issue("ctxgov_defines_ascr", path, "CtxGov must not claim to define ASCR."))
    boundary = alignment.get("claim_boundary", {})
    for key, value in boundary.items():
        if value is not False:
            issues.append(_issue("claim_boundary_not_false", path, f"{key} must be false."))
    side_effects = alignment.get("side_effect_boundary", {})
    for key, value in side_effects.items():
        if value is not False:
            issues.append(_issue("side_effect_boundary_not_false", path, f"{key} must be false."))


def _check_receipt(name: str, receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / ("claim-lint.json" if name == "claim_lint" else "leak-scan.json")
    if receipt.get("status") != "pass":
        issues.append(_issue(f"{name}_not_pass", path, "Receipt status must be pass."))
    if receipt.get("violations") not in ([], None):
        issues.append(_issue(f"{name}_violations", path, "Receipt must have no violations."))


def _check_link_check(receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "link-check.json"
    if receipt.get("status") not in {
        "pass_local_remote_fetch_pending_publication",
        "pass_live_pages_release_and_ascr_verified",
    }:
        issues.append(_issue("link_check_status", path, "Unexpected link-check status."))
    if receipt.get("ascr_repo_http_status") != 200:
        issues.append(_issue("ascr_repo_fetch", path, "ASCR repo fetch must return 200."))
    if receipt.get("status") == "pass_live_pages_release_and_ascr_verified":
        for key in ["release_fetch_verification_executed", "pages_fetch_verification_executed"]:
            if receipt.get(key) is not True:
                issues.append(_issue("live_fetch_missing", path, f"{key} must be true after publication."))
        for key in ["pages_http_status", "release_http_status", "ascr_repo_http_status"]:
            if receipt.get(key) != 200:
                issues.append(_issue("live_fetch_status", path, f"{key} must be 200 after publication."))
    if receipt.get("violations") not in ([], None):
        issues.append(_issue("link_check_violations", path, "Receipt must have no violations."))


def _check_readiness(receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "publication-readiness.json"
    if receipt.get("status") not in {
        "ready_for_owner_approved_public_repo_patch",
        "published_owner_approved_public_write_bundle",
    }:
        issues.append(_issue("publication_readiness_status", path, "Unexpected readiness status."))
    if receipt.get("owner_approval_received") is not True:
        issues.append(_issue("owner_approval", path, "owner_approval_received must be true."))
    for key in [
        "provider_model_call_executed",
        "memory_backend_write_executed",
        "external_target_write_executed",
        "outreach_executed",
    ]:
        if receipt.get(key) is not False:
            issues.append(_issue("side_effect_boundary", path, f"{key} must be false."))
    if receipt.get("status") == "published_owner_approved_public_write_bundle":
        for key in [
            "github_push_executed",
            "github_release_executed",
            "github_metadata_updated",
            "github_pages_update_executed",
            "pages_fetch_verification_executed",
        ]:
            if receipt.get(key) is not True:
                issues.append(_issue("publication_status", path, f"{key} must be true after publication."))


def _check_execution(receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "publication-execution-receipt.json"
    if receipt.get("status") not in {"prepared_not_published", "published_and_verified"}:
        issues.append(_issue("publication_execution_status", path, "Unexpected execution status."))
    if receipt.get("status") == "published_and_verified":
        pages = receipt.get("github_pages_fetch", {})
        release = receipt.get("release_page_fetch", {})
        ascr = receipt.get("ascr_repo_fetch", {})
        if pages.get("status") != 200 or not pages.get("ascr_phrase_found"):
            issues.append(_issue("pages_verification", path, "Pages verification must show 200 and ASCR phrase."))
        if release.get("status") != 200:
            issues.append(_issue("release_verification", path, "Release verification must show 200."))
        if ascr.get("status") != 200:
            issues.append(_issue("ascr_verification", path, "ASCR repo verification must show 200."))
    for key, value in receipt.get("side_effect_boundary", {}).items():
        if value is not False:
            issues.append(_issue("execution_side_effect", path, f"{key} must be false."))


def _check_manifest(manifest: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "manifest.json"
    roles = {asset.get("role") for asset in manifest.get("assets", [])}
    missing_roles = sorted(REQUIRED_MANIFEST_ROLES - roles)
    if missing_roles:
        issues.append(_issue("manifest_missing_roles", path, ", ".join(missing_roles)))
    boundary = manifest.get("publication_boundary", {})
    if boundary.get("provider_model_call_executed") is not False:
        issues.append(_issue("manifest_side_effect", path, "provider_model_call_executed must be false."))
    if boundary.get("memory_backend_write_executed") is not False:
        issues.append(_issue("manifest_side_effect", path, "memory_backend_write_executed must be false."))


def _check_homepage(issues: list[dict[str, Any]]) -> None:
    path = ROOT / "docs" / "index.html"
    text = path.read_text(encoding="utf-8")
    for phrase in HOMEPAGE_PHRASES:
        if phrase not in text:
            issues.append(_issue("homepage_missing_phrase", path, phrase))
    if 'id="benchmark"' in text or 'href="#benchmark"' in text:
        issues.append(_issue("homepage_benchmark_surface", path, "Benchmark surface should stay absent."))


def _check_readme(issues: list[dict[str, Any]]) -> None:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    for phrase in README_PHRASES:
        if phrase not in text:
            issues.append(_issue("readme_missing_phrase", path, phrase))


def _check_local_links(issues: list[dict[str, Any]]) -> None:
    markdown_link = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    href_link = re.compile(r'href="([^"]+)"')
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        links = markdown_link.findall(text) + href_link.findall(text)
        for raw_link in links:
            link = raw_link.strip()
            if not link or link.startswith(("http://", "https://", "mailto:", "javascript:")):
                continue
            if link.startswith("#"):
                anchor = link[1:]
                if anchor and f'id="{anchor}"' not in text:
                    issues.append(_issue("missing_local_anchor", path, link))
                continue
            target = link.split("#", 1)[0]
            if target.startswith("/"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                issues.append(_issue("missing_local_link_target", path, link))


def _check_text_boundaries(issues: list[dict[str, Any]]) -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in TEXT_FILES)
    for phrase in ASCR_PHRASES:
        if phrase not in combined:
            issues.append(_issue("missing_ascr_phrase", ROOT, phrase))
    if "/Users/chris/" in combined:
        issues.append(_issue("private_path_leak", ROOT, "Private absolute path appears in public text."))
    for path in TEXT_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            previous = lines[line_number - 2] if line_number > 1 else ""
            previous_2 = lines[line_number - 3] if line_number > 2 else ""
            context = f"{previous_2} {previous} {line}".lower()
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(line) and not any(marker in context for marker in NEGATION_MARKERS):
                    issues.append(
                        _issue(
                            "unnegated_overclaim_phrase",
                            path,
                            f"line {line_number}: {line.strip()}",
                        )
                    )


def _issue(kind: str, path: Path, detail: str) -> dict[str, Any]:
    try:
        rel = path.relative_to(ROOT)
    except ValueError:
        rel = path
    return {"kind": kind, "path": str(rel), "detail": detail}


def _finish(issues: list[dict[str, Any]]) -> int:
    report = {
        "schema": "ctxgov.ascr_aligned_release_pack_check.v0",
        "release": "v0.6.10",
        "status": "pass" if not issues else "fail",
        "issue_count": len(issues),
        "issues": issues,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
