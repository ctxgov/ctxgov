from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


EXPECTED = {
    "ctxgov_release": "v0.6.8",
    "companion_release": "v0.7.0",
    "project_page": "https://ctxgov.github.io/ctxgov/",
}

PUBLIC_SURFACE_PATHS = [
    "README.md",
    "docs/index.html",
    "docs/public-positioning.md",
    "docs/project-page-and-demo-2026-06-03.md",
    "docs/research-engineering-hiring-packet.md",
    "docs/linkedin-and-outreach-pack-2026-06-03.md",
    "release/v0.6.8/RELEASE_NOTES.md",
    "release/v0.6.8/github-release.md",
]

NEGATION_MARKERS = (
    "no ",
    "not ",
    "not a ",
    "not an ",
    "not for ",
    "does not ",
    "do not ",
    "without ",
    "until ",
)

CLAIM_BOUNDARY_PATTERNS = [
    (re.compile(r"\bsecurity guarantee\b", re.I), "security guarantee"),
    (re.compile(r"\bbenchmark (claim|result|performance)\b", re.I), "benchmark claim"),
    (re.compile(r"\bprovider compatibility claim\b", re.I), "provider compatibility claim"),
    (re.compile(r"\bagent-safety claim\b", re.I), "agent-safety claim"),
    (re.compile(r"\badoption claim\b", re.I), "adoption claim"),
]

STALE_CURRENT_COMPANION_PATTERNS = [
    re.compile(r"\bcompanion evaluation repo and v0\.5\b", re.I),
    re.compile(r"\bcompanion evaluation repo and current v0\.6\b", re.I),
    re.compile(r"\bcurrent companion (evaluation|eval|artifact)\b.*\bv0\.[56]\b", re.I),
    re.compile(r"\bcompanion Agent Context Health Eval v0\.5 artifact\b", re.I),
    re.compile(r"\bcompanion Agent Context Health Eval v0\.6 artifact\b", re.I),
]

PRIVATE_OR_SECRET_PATTERNS = [
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"\b(api[_-]?key|secret|password|token)\s*[:=]\s*\S+", re.I),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"\bgho_[A-Za-z0-9_]+\b"),
]


def _read_public_surfaces(root: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    contents: dict[str, str] = {}
    issues: list[dict[str, Any]] = []
    for relative in PUBLIC_SURFACE_PATHS:
        path = root / relative
        if not path.exists():
            issues.append({"type": "missing_public_surface", "path": relative, "message": "Expected public surface file is missing."})
            continue
        contents[relative] = path.read_text(encoding="utf-8")
    return contents, issues


def _line_is_negated(line: str, match_start: int, previous_line: str = "") -> bool:
    prefix = f"{previous_line} {line[:match_start]}".lower()
    window = prefix[-220:]
    return any(marker in window for marker in NEGATION_MARKERS)


def _check_claim_boundaries(contents: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for path, text in contents.items():
        previous_lines: list[str] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            prefix_context = " ".join(previous_lines[-2:])
            for pattern, claim in CLAIM_BOUNDARY_PATTERNS:
                for match in pattern.finditer(line):
                    if _line_is_negated(line, match.start(), prefix_context):
                        continue
                    issues.append(
                        {
                            "type": "unsupported_public_claim",
                            "path": path,
                            "line": line_number,
                            "claim": claim,
                            "evidence": line.strip(),
                        }
                    )
            previous_lines.append(line)
    return issues


def _check_private_or_secret_markers(contents: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for path, text in contents.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in PRIVATE_OR_SECRET_PATTERNS:
                if pattern.search(line):
                    issues.append(
                        {
                            "type": "private_or_secret_marker",
                            "path": path,
                            "line": line_number,
                            "evidence": line.strip(),
                        }
                    )
    return issues


def _check_release_links(contents: dict[str, str]) -> list[dict[str, Any]]:
    combined = "\n".join(contents.values())
    issues: list[dict[str, Any]] = []
    expected_ctxgov_url = f"https://github.com/ctxgov/ctxgov/releases/tag/{EXPECTED['ctxgov_release']}"
    expected_companion_url = (
        f"https://github.com/ctxgov/agent-context-evals/releases/tag/{EXPECTED['companion_release']}"
    )
    expected_report_url = "https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.7-results.md"

    for url, issue_type in [
        (expected_ctxgov_url, "missing_expected_ctxgov_release_link"),
        (expected_companion_url, "missing_expected_companion_release_link"),
        (expected_report_url, "missing_expected_v07_results_link"),
        (EXPECTED["project_page"], "missing_expected_project_page_link"),
    ]:
        if url not in combined:
            issues.append({"type": issue_type, "message": f"Missing expected public link: {url}"})

    legacy_patterns = [
        (re.compile(r"agent-context-evals/releases/tag/v0\.3\.0"), "legacy_companion_release_link"),
        (re.compile(r"reports/v0\.3-readiness\.md"), "legacy_companion_readiness_link"),
        (re.compile(r"ctxgov/ctxgov/releases/tag/v0\.6\.2"), "legacy_ctxgov_release_link"),
    ]
    for path, text in contents.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern, issue_type in legacy_patterns:
                if pattern.search(line):
                    issues.append(
                        {
                            "type": issue_type,
                            "path": path,
                            "line": line_number,
                            "evidence": line.strip(),
                        }
                    )
    return issues


def _check_current_artifact_wording(contents: dict[str, str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for path, text in contents.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in STALE_CURRENT_COMPANION_PATTERNS:
                if pattern.search(line):
                    issues.append(
                        {
                            "type": "stale_current_companion_artifact_wording",
                            "path": path,
                            "line": line_number,
                            "evidence": line.strip(),
                        }
                    )
    return issues


def check_release_integrity(root: Path) -> dict[str, Any]:
    resolved = root.resolve()
    contents, issues = _read_public_surfaces(resolved)
    issues.extend(_check_release_links(contents))
    issues.extend(_check_current_artifact_wording(contents))
    issues.extend(_check_claim_boundaries(contents))
    issues.extend(_check_private_or_secret_markers(contents))
    return {
        "schema_id": "ctxgov.release-integrity-report/v1",
        "status": "pass" if not issues else "fail",
        "root": str(resolved),
        "expected": EXPECTED,
        "checked_paths": sorted(contents),
        "issue_count": len(issues),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check CtxGov public release-surface integrity without network access.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = check_release_integrity(args.root)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
