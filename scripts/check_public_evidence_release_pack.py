#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "release" / "v0.6.9" / "memory-xray-public-evidence-preview"

REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "index.html",
    ROOT / "docs" / "project-page-and-demo-2026-06-03.md",
    ROOT / "docs" / "public-repo-metadata.md",
    ROOT / "docs" / "public-github-repo-launch-checklist.md",
    ROOT / "release" / "v0.6.9" / "RELEASE_NOTES.md",
    ROOT / "release" / "v0.6.9" / "github-release.md",
    PACK / "README.md",
    PACK / "evidence-summary.json",
    PACK / "claim-lint.json",
    PACK / "leak-scan.json",
    PACK / "link-check.json",
    PACK / "publication-readiness.json",
    PACK / "publication-execution-receipt.json",
    PACK / "owner-approval-minimal-matrix.md",
    PACK / "60-second-demo-script.md",
    PACK / "technical-note.md",
    PACK / "reviewer-packet.md",
    PACK / "manifest.json",
]

TEXT_FILES = [path for path in REQUIRED_FILES if path.suffix.lower() not in {".json"}]

BOUNDARY_PHRASES = [
    "No public benchmark claim",
    "No provider/model call",
    "No memory-backend write",
    "No hosted runtime claim",
    "No adoption claim",
    "No CLI beta claim",
    "python3 scripts/check_public_evidence_release_pack.py",
]

HOMEPAGE_PHRASES = [
    "Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context before agents act.",
    "Run locally",
    "Read evidence",
    "Review limits",
    'id="evidence"',
]

REQUIRED_PACK_ROLES = {
    "pack_overview",
    "public_safe_evidence_summary",
    "claim_boundary_receipt",
    "public_leak_scan_receipt",
    "local_link_check_receipt",
    "publication_readiness_receipt",
    "publication_execution_receipt",
    "owner_approval_minimal_matrix",
    "demo_script",
    "technical_note",
    "external_reviewer_packet",
}

OVERCLAIM_PATTERNS = [
    re.compile(r"\bpublic benchmark (?:complete|passed|result|score|leaderboard)\b", re.I),
    re.compile(r"\bsecurity (?:certification|guarantee)\b", re.I),
    re.compile(r"\bprovider(?:/model)? compatibility claim\b", re.I),
    re.compile(r"\badoption claim\b", re.I),
    re.compile(r"\bpackage publication claim\b", re.I),
    re.compile(r"\bhosted runtime claim\b", re.I),
    re.compile(r"\blive adapter claim\b", re.I),
    re.compile(r"\bpublic spec-stability claim\b", re.I),
]

NEGATION_MARKERS = (
    "bad context",
    "sample",
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
            issues.append(_issue("missing_file", path, "Required public release-pack file is missing."))

    if issues:
        return _finish(issues)

    evidence_summary = _load_json(PACK / "evidence-summary.json", issues)
    claim_lint = _load_json(PACK / "claim-lint.json", issues)
    leak_scan = _load_json(PACK / "leak-scan.json", issues)
    link_check = _load_json(PACK / "link-check.json", issues)
    publication_readiness = _load_json(PACK / "publication-readiness.json", issues)
    publication_execution = _load_json(PACK / "publication-execution-receipt.json", issues)
    manifest = _load_json(PACK / "manifest.json", issues)

    _check_evidence_summary(evidence_summary, issues)
    _check_receipt("claim_lint", claim_lint, issues)
    _check_receipt("leak_scan", leak_scan, issues)
    _check_link_receipt(link_check, issues)
    _check_publication_readiness(publication_readiness, issues)
    _check_publication_execution(publication_execution, issues)
    _check_manifest(manifest, issues)
    _check_homepage(issues)
    _check_local_links(issues)
    _check_text_boundaries(issues)

    return _finish(issues)


def _load_json(path: Path, issues: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - returns diagnostic for bad JSON
        issues.append(_issue("invalid_json", path, str(exc)))
        return {}


def _check_evidence_summary(summary: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "evidence-summary.json"
    if summary.get("status") != "prepared_locally_for_owner_approved_publication":
        issues.append(_issue("bad_status", path, "Evidence summary status must remain local/prepared."))
    if summary.get("positioning") != "agent_context_health_memory_governance_report_shape_release":
        issues.append(_issue("bad_positioning", path, "Positioning must stay report-shape scoped."))

    boundary = summary.get("claim_boundary", {})
    if not boundary:
        issues.append(_issue("missing_claim_boundary", path, "Evidence summary needs claim_boundary."))
    for key, value in boundary.items():
        if value is not False:
            issues.append(_issue("claim_boundary_not_false", path, f"{key} must be false."))

    layers = summary.get("evidence_layers", {})
    negative_matrix = layers.get("negative_matrix", {})
    repeat_run = layers.get("repeat_run_noop_replay", {})
    if negative_matrix.get("case_count") != 10:
        issues.append(_issue("bad_negative_case_count", path, "Expected 10 public-safe negative modes."))
    if repeat_run.get("repeat_runs") != 2:
        issues.append(_issue("bad_repeat_run_count", path, "Expected 2 repeat runs."))
    if repeat_run.get("noop_handoff_replay_steps") != 7:
        issues.append(_issue("bad_replay_step_count", path, "Expected 7 no-op handoff replay steps."))


def _check_receipt(name: str, receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / ("claim-lint.json" if name == "claim_lint" else "leak-scan.json")
    if receipt.get("status") != "pass":
        issues.append(_issue(f"{name}_not_pass", path, "Receipt status must be pass."))
    if receipt.get("violations") not in ([], None):
        issues.append(_issue(f"{name}_violations", path, "Receipt must have no violations."))


def _check_manifest(manifest: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "manifest.json"
    roles = {asset.get("role") for asset in manifest.get("assets", [])}
    missing_roles = sorted(REQUIRED_PACK_ROLES - roles)
    if missing_roles:
        issues.append(_issue("manifest_missing_roles", path, ", ".join(missing_roles)))
    boundary = manifest.get("publication_boundary", {})
    for key in ["github_push_executed", "release_publication_executed", "pages_update_executed"]:
        if boundary.get(key) is not False:
            issues.append(_issue("manifest_publication_boundary", path, f"{key} must be false."))


def _check_link_receipt(receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "link-check.json"
    if receipt.get("status") not in {
        "pass_local_remote_fetch_pending_owner_approval",
        "pass_live_pages_and_release_verified",
    }:
        issues.append(_issue("link_check_status", path, "Unexpected link-check status."))
    if receipt.get("status") == "pass_live_pages_and_release_verified":
        if receipt.get("remote_fetch_executed") is not True:
            issues.append(_issue("link_check_remote_fetch", path, "remote_fetch_executed must be true after publication."))
        if receipt.get("pages_fetch_verification_executed") is not True:
            issues.append(_issue("link_check_pages_fetch", path, "pages_fetch_verification_executed must be true after publication."))
    if receipt.get("violations") not in ([], None):
        issues.append(_issue("link_check_violations", path, "Receipt must have no violations."))


def _check_publication_readiness(receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "publication-readiness.json"
    if receipt.get("status") not in {
        "ready_for_owner_approved_public_repo_patch",
        "published_owner_approved_public_write_bundle",
    }:
        issues.append(_issue("publication_readiness_status", path, "Unexpected publication readiness status."))
    required_never = [
        "provider_model_call_executed",
        "memory_backend_write_executed",
        "external_target_write_executed",
        "outreach_executed",
    ]
    for key in required_never:
        if receipt.get(key) is not False:
            issues.append(_issue("publication_side_effect_boundary", path, f"{key} must be false."))
    if receipt.get("status") == "published_owner_approved_public_write_bundle":
        for key in [
            "github_push_executed",
            "github_release_executed",
            "github_metadata_updated",
            "github_pages_update_executed",
            "pages_fetch_verification_executed",
        ]:
            if receipt.get(key) is not True:
                issues.append(_issue("publication_execution_status", path, f"{key} must be true after publication."))
    if receipt.get("owner_approval_required") is not True:
        issues.append(_issue("publication_owner_approval", path, "owner_approval_required must be true."))


def _check_publication_execution(receipt: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    path = PACK / "publication-execution-receipt.json"
    if receipt.get("status") != "published_and_verified":
        issues.append(_issue("publication_execution_status", path, "Publication execution receipt must be published_and_verified."))
    pages = receipt.get("github_pages_fetch", {})
    release = receipt.get("release_page_fetch", {})
    if pages.get("status") != 200 or not pages.get("first_viewport_phrase_found"):
        issues.append(_issue("publication_pages_verification", path, "Pages verification must show HTTP 200 and expected first-viewport phrase."))
    if release.get("status") != 200:
        issues.append(_issue("publication_release_verification", path, "Release page verification must show HTTP 200."))
    boundary = receipt.get("side_effect_boundary", {})
    for key, value in boundary.items():
        if value is not False:
            issues.append(_issue("publication_execution_side_effect", path, f"{key} must be false."))


def _check_homepage(issues: list[dict[str, Any]]) -> None:
    path = ROOT / "docs" / "index.html"
    text = path.read_text(encoding="utf-8")
    for phrase in HOMEPAGE_PHRASES:
        if phrase not in text:
            issues.append(_issue("homepage_missing_phrase", path, phrase))
    for forbidden in ['id="benchmark"', 'href="#benchmark"', ">Benchmark<"]:
        if forbidden in text:
            issues.append(_issue("homepage_benchmark_surface", path, forbidden))
    if "ctxvault.github.io/ctxvault" in text:
        issues.append(_issue("legacy_homepage_url", path, "Legacy ctxvault Pages URL remains."))


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
    for phrase in BOUNDARY_PHRASES:
        if phrase not in combined:
            issues.append(_issue("missing_boundary_phrase", ROOT, phrase))
    if "/Users/chris/" in combined:
        issues.append(_issue("private_path_leak", ROOT, "Private absolute path appears in public text."))
    if "ctxvault.cli memory-xray" in combined:
        issues.append(_issue("unpublished_cli_reference", ROOT, "Public v0.6.9 must not reference unpublished Memory X-Ray CLI commands."))
    if "private traces published" in combined.lower():
        issues.append(_issue("ambiguous_trace_claim", ROOT, "Avoid ambiguous private trace publication wording."))

    for path in TEXT_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            previous = lines[line_number - 2] if line_number > 1 else ""
            previous_2 = lines[line_number - 3] if line_number > 2 else ""
            context = f"{previous_2} {previous} {line}"
            lowered = context.lower()
            for pattern in OVERCLAIM_PATTERNS:
                if pattern.search(line) and not any(marker in lowered for marker in NEGATION_MARKERS):
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
    return {
        "kind": kind,
        "path": str(rel),
        "detail": detail,
    }


def _finish(issues: list[dict[str, Any]]) -> int:
    report = {
        "schema": "ctxgov.public_evidence_release_pack_check.v0",
        "release": "v0.6.9",
        "status": "pass" if not issues else "fail",
        "issue_count": len(issues),
        "issues": issues,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
