#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

LEAK_PATTERNS = [
    (re.compile(r"/Users/[^\s`)>\"]+"), "absolute macOS user path"),
    (re.compile(r"/private/[^\s`)>\"]+"), "absolute private filesystem path"),
    (re.compile(r"file://", re.IGNORECASE), "file URI"),
    (re.compile(r"\.ctxvault/reviews/"), "private .ctxvault review path"),
    (re.compile(r"ssh://git@"), "private SSH remote"),
    (re.compile(r"git@github\.com:"), "SSH GitHub remote"),
    (re.compile(r"demons-mind\.tail[^\s`)>\"]*"), "private Forgejo host"),
    (re.compile(r"\bctxray\b", re.IGNORECASE), "specific local dry-run repository identifier"),
    (re.compile(r"\bollama\b", re.IGNORECASE), "specific local dry-run repository identifier"),
    (re.compile(r"\bprompt-sensitivity-bench\b", re.IGNORECASE), "specific local dry-run repository identifier"),
    (re.compile(r"\b6023189\b"), "specific local dry-run snapshot identifier"),
    (re.compile(r"\bc2f2d90a\b"), "specific local dry-run snapshot identifier"),
    (re.compile(r"\b863b2398\b"), "specific local dry-run snapshot identifier"),
]

MUST_NOT_APPEAR = [
    (re.compile(r"\bprovider_model_called:\s*true\b", re.IGNORECASE), "provider/model call side effect"),
    (re.compile(r'"provider_model_called"\s*:\s*true', re.IGNORECASE), "provider/model call side effect"),
    (re.compile(r"\btarget_file_written:\s*true\b", re.IGNORECASE), "target write side effect"),
    (re.compile(r'"target_file_written"\s*:\s*true', re.IGNORECASE), "target write side effect"),
    (re.compile(r"\bprojection_written:\s*true\b", re.IGNORECASE), "projection write side effect"),
    (re.compile(r'"projection_written"\s*:\s*true', re.IGNORECASE), "projection write side effect"),
    (re.compile(r"\bmemory_promoted:\s*true\b", re.IGNORECASE), "memory promotion side effect"),
    (re.compile(r'"memory_promoted"\s*:\s*true', re.IGNORECASE), "memory promotion side effect"),
]


def public_release_artifact_roots(root: Path) -> list[Path]:
    looks_like_repo_root = any(
        (root / marker).exists()
        for marker in ["pyproject.toml", "release", "examples", "docs", "spaces"]
    )
    if not looks_like_repo_root:
        return [root]
    candidates = [
        root / "README.md",
        root / "CHANGELOG.md",
        root / "pyproject.toml",
        root / "docs" / "mechanism",
        root / "release" / "v0.5.0",
        root / "release" / "v0.5.3",
        root / "examples" / "v0.5.0-governed-context-projection",
        root / "examples" / "v0.5.3-experience-evidence",
        root / "spaces" / "huggingface" / "v053-experience-evidence-static",
    ]
    existing = [path for path in candidates if path.exists()]
    return existing or [root]


def iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for artifact_root in public_release_artifact_roots(root):
        paths = [artifact_root] if artifact_root.is_file() else sorted(artifact_root.rglob("*"))
        for path in paths:
            if any(part in SKIP_PARTS for part in path.parts):
                continue
            if not path.is_file():
                continue
            if path.suffix not in TEXT_SUFFIXES:
                continue
            files.append(path)
    return sorted(set(files))


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def scan_file(path: Path, root: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    violations: list[str] = []
    for pattern, label in [*LEAK_PATTERNS, *MUST_NOT_APPEAR]:
        match = pattern.search(text)
        if match:
            violations.append(f"{rel(path, root)}: {label}: {match.group(0)!r}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan v0.5.3 public release artifacts for private leaks and forbidden side effects."
    )
    parser.add_argument("--root", type=Path, required=True, help="Public artifact root to scan.")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.exists():
        print(f"root does not exist: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"root is not a directory: {root}", file=sys.stderr)
        return 2

    violations: list[str] = []
    files = iter_text_files(root)
    for path in files:
        violations.extend(scan_file(path, root))

    if violations:
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1

    print(f"v0.5.3 public artifact scan passed for {len(files)} files under {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
