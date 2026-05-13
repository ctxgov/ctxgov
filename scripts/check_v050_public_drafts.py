#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES = [
    ROOT / "README.md",
    ROOT / "release" / "v0.5.0" / "RELEASE_NOTES.md",
    ROOT / "release" / "v0.5.0" / "README-v0.5.0-rc-draft.md",
    ROOT / "release" / "v0.5.0" / "v0.5.0-public-release-notes-rc-draft.md",
    ROOT / "release" / "v0.5.0" / "v0.5.0-public-evidence-page-draft.md",
    ROOT / "release" / "v0.5.0" / "v0.5.0-public-demo-script-draft.md",
    ROOT / "release" / "v0.5.0" / "v0.5.0-sanitized-demo-packet.md",
    ROOT / "release" / "v0.5.0" / "contributor-landing-issues-draft.md",
    ROOT / "release" / "v0.5.0" / "public-artifact-manifest-and-checklist.md",
    ROOT / "release" / "v0.5.0" / "publication-kit.md",
    ROOT / "docs" / "mechanism" / "governed-context-projection.md",
    ROOT / "docs" / "mechanism" / "governed-context-projection.zh.md",
    ROOT / "release" / "v0.5.0" / "mechanism-note-governed-context-projection.md",
    ROOT / "release" / "v0.5.0" / "mechanism-note-governed-context-projection.zh.md",
    ROOT / "examples" / "v0.5.0-governed-context-projection" / "README.md",
    ROOT / "examples" / "v0.5.0-governed-context-projection" / "projection-preview" / "INDEX.md",
    ROOT / "examples" / "v0.5.0-governed-context-projection" / "projection-preview" / "caveated.md",
    ROOT / "examples" / "v0.5.0-governed-context-projection" / "projection-preview" / "blocked.md",
    ROOT / "examples" / "v0.5.2-experience-surface" / "README.md",
    ROOT / "examples" / "v0.5.2-experience-surface" / "receipt-viewer" / "README.md",
    ROOT / "examples" / "v0.5.2-experience-surface" / "future-context-review" / "README.md",
    ROOT / "release" / "v0.5.3" / "RELEASE_NOTES.md",
    ROOT / "release" / "v0.5.3" / "public-examples-release-copy.md",
    ROOT / "release" / "v0.5.3" / "experience-evidence-pack.md",
    ROOT / "examples" / "v0.5.3-experience-evidence" / "README.md",
    ROOT / "examples" / "v0.5.3-experience-evidence" / "receipt-viewer" / "README.md",
    ROOT / "examples" / "v0.5.3-experience-evidence" / "future-context-review" / "README.md",
    ROOT / "spaces" / "huggingface" / "v053-experience-evidence-static" / "README.md",
]

LEAK_PATTERNS = [
    (re.compile(r"/Users/[^\s`)>\"]+"), "absolute macOS user path"),
    (re.compile(r"/private/[^\s`)>\"]+"), "absolute private filesystem path"),
    (re.compile(r"file://", re.IGNORECASE), "file URI"),
    (re.compile(r"\.ctxvault/reviews/"), "private .ctxvault review path"),
    (re.compile(r"git@github\.com:"), "SSH remote URL"),
    (re.compile(r"\bctxray\b", re.IGNORECASE), "specific local dry-run repository identifier"),
    (re.compile(r"\bollama\b", re.IGNORECASE), "specific local dry-run repository identifier"),
    (re.compile(r"\bprompt-sensitivity-bench\b", re.IGNORECASE), "specific local dry-run repository identifier"),
    (re.compile(r"\b6023189\b"), "specific local dry-run snapshot identifier"),
    (re.compile(r"\bc2f2d90a\b"), "specific local dry-run snapshot identifier"),
    (re.compile(r"\b863b2398\b"), "specific local dry-run snapshot identifier"),
]

OVERCLAIM_PATTERNS = [
    (re.compile(r"\b(improves?|improved|increase[sd]?)\s+(coding\s+)?(accuracy|reliability|benchmark)\b", re.IGNORECASE), "accuracy/reliability/benchmark improvement claim"),
    (re.compile(r"\bbenchmark\s+(result|win|improvement|score|leaderboard)\b", re.IGNORECASE), "benchmark result claim"),
    (re.compile(r"\bleaderboard\s+(result|score|rank)\b", re.IGNORECASE), "leaderboard result claim"),
    (re.compile(r"\bautomatic\s+(repository\s+)?optimization\b", re.IGNORECASE), "automatic optimization claim"),
    (re.compile(r"\badapter\s+compatibility\b", re.IGNORECASE), "adapter compatibility claim"),
    (re.compile(r"\bprovider/model\s+compatibility\b", re.IGNORECASE), "provider/model compatibility claim"),
    (re.compile(r"\bprovider\s+compatibility\b", re.IGNORECASE), "provider compatibility claim"),
    (re.compile(r"\bmodel\s+compatibility\b", re.IGNORECASE), "model compatibility claim"),
    (re.compile(r"\bhardware/cost\s+(claim|saving|improvement)\b", re.IGNORECASE), "hardware/cost claim"),
    (re.compile(r"\bstable\s+MGP\b", re.IGNORECASE), "stable MGP claim"),
    (re.compile(r"\bMemory OS\b"), "Memory OS claim"),
    (re.compile(r"\bRAG replacement\b", re.IGNORECASE), "RAG replacement claim"),
    (re.compile(r"\bprevents?\s+hallucinations?\b", re.IGNORECASE), "hallucination prevention claim"),
    (re.compile(r"\bsecurity certification\b", re.IGNORECASE), "security certification claim"),
]

NEGATION_MARKERS = (
    " no ",
    " not ",
    "do not",
    "does not",
    "without ",
    "not claimed",
    "not use",
    "not a ",
    "不是",
    "不声称",
    "不承诺",
    "不声明",
    "不发布",
    "不运行",
    "不调用",
    "不写",
    "不训练",
    "不更新",
    "不做",
)

STATUS_PHRASES = [
    "Status: v0.5.0 public release artifact.",
    "Status: draft for public release approval; not published.",
    "Status: local draft for owner review; not published.",
    "Status: local publication kit; account-bound social posting not performed.",
    "Status: sanitized public example draft; not published.",
    "Status: v0.5.3 public release artifact.",
    "Status: v0.5.3 public sanitized example.",
]

REQUIRED_PHRASES = [
    "Governed context projection for AI work.",
    "no target repository writes",
    "no provider/model execution",
]


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def find_violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    violations: list[str] = []
    for pattern, label in LEAK_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append(f"{rel(path)}: {label}: {match.group(0)!r}")
    lines = text.splitlines()
    for pattern, label in OVERCLAIM_PATTERNS:
        for line_number, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if not match:
                continue
            start = max(0, line_number - 8)
            end = min(len(lines), line_number + 1)
            normalized = f" {' '.join(lines[start:end]).lower()} "
            if "## not claimed" in normalized:
                continue
            if "do not use this evidence to claim" in normalized:
                continue
            if any(marker in normalized for marker in NEGATION_MARKERS):
                continue
            violations.append(f"{rel(path)}:{line_number}: {label}: {match.group(0)!r}")
            break
    lower_text = text.lower()
    if not any(phrase.lower() in lower_text for phrase in STATUS_PHRASES):
        violations.append(f"{rel(path)}: missing required draft/publication status phrase")
    for phrase in REQUIRED_PHRASES:
        if phrase.lower() not in lower_text:
            violations.append(f"{rel(path)}: missing required boundary phrase: {phrase!r}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check v0.5.0 public draft wording for leaks and overclaims.")
    parser.add_argument("files", nargs="*", type=Path, help="Markdown draft files to check.")
    args = parser.parse_args()

    if args.files:
        files = [path if path.is_absolute() else ROOT / path for path in args.files]
    else:
        files = [path for path in DEFAULT_FILES if path.exists()]
    violations: list[str] = []
    for path in files:
        if not path.exists():
            violations.append(f"{rel(path)}: file does not exist")
            continue
        violations.extend(find_violations(path))

    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1

    print(f"public draft claim check passed for {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
