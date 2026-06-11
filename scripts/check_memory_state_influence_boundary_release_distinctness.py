#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_ROOT = Path("release/memory-state-governability-overlay/2026-06-11")
CANONICAL_URL = "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html"
CANONICAL_PAGE = Path("docs/memory-state-influence-boundary-try-in-5-minutes.html")
LEGACY_ALIAS_PAGE = Path("docs/memory-state-governability-overlay-try-in-5-minutes.html")
SOCIAL_PAYLOAD = PACK_ROOT / "memory-state-governability-overlay-social-payload.json"
PUBLICATION_BUNDLE = PACK_ROOT / "memory-state-influence-boundary-publication-bundle.json"
HN_POST = PACK_ROOT / "hn-post.md"
LINKEDIN_POST = PACK_ROOT / "linkedin-post.md"
X_THREAD = PACK_ROOT / "x-thread.md"

OLD_RELEASE_URLS = [
    "https://ctxgov.github.io/ctxgov/try-in-5-minutes.html",
    "https://ctxgov.github.io/ctxgov/activation-xray-try-in-5-minutes.html",
    "https://ctxgov.github.io/ctxgov/memory-state-governability-overlay-try-in-5-minutes.html",
]

OLD_POSITIONING_PHRASES = [
    "local claim firewall for AI memory claims",
    "Activation X-Ray Try-in-5-Minutes",
    "local governability overlay for AI memory state",
]

REQUIRED_DISTINCT_PHRASES = [
    "drop in AI memory files",
    "influence-boundary report",
    "user-supplied memory/context/state files",
    "integration_gate",
    "consumer integration",
    "raw_content_included=false",
]


def check_memory_state_influence_boundary_release_distinctness(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    hn_text = _read_text(root, HN_POST, errors)
    linkedin_text = _read_text(root, LINKEDIN_POST, errors)
    x_text = _read_text(root, X_THREAD, errors)
    page_text = _read_text(root, CANONICAL_PAGE, errors)
    legacy_page_text = _read_text(root, LEGACY_ALIAS_PAGE, errors)
    social_payload = _read_json(root, SOCIAL_PAYLOAD, errors)
    publication_bundle = _read_publication_bundle(root, errors)

    _check_hn(hn_text, errors)
    _check_social_payload(social_payload, errors)
    _check_page(page_text, errors)
    _check_legacy_alias(legacy_page_text, errors)
    _check_bundle(publication_bundle, errors)
    _check_release_texts(hn_text, linkedin_text, x_text, page_text, errors, warnings)

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-release-distinctness/v0",
        "status": (
            "pass_memory_state_influence_boundary_release_distinctness"
            if not errors
            else "fail_memory_state_influence_boundary_release_distinctness"
        ),
        "milestone": "Local Memory State Influence Boundary Report",
        "canonical_public_page": CANONICAL_URL,
        "canonical_page": str(CANONICAL_PAGE),
        "legacy_alias_page": str(LEGACY_ALIAS_PAGE),
        "distinct_from": [
            "claim firewall HN launch",
            "Activation X-Ray HN launch",
            "generic memory state governability overlay wording",
        ],
        "required_distinct_phrases": REQUIRED_DISTINCT_PHRASES,
        "old_release_urls_blocked_from_social": OLD_RELEASE_URLS,
        "old_positioning_phrases_blocked_from_hn_title": OLD_POSITIONING_PHRASES,
        "claim_boundary": {
            "public_benchmark_claim_created": False,
            "public_compatibility_claim_created": False,
            "public_security_claim_created": False,
            "stable_protocol_claim_created": False,
        },
        "publication_executed": False,
        "outreach_performed": False,
        "warning_count": len(warnings),
        "warnings": warnings,
        "error_count": len(errors),
        "errors": errors,
    }


def _check_hn(text: str, errors: list[str]) -> None:
    title_prefix = "title: "
    title = ""
    for line in text.splitlines():
        if line.startswith(title_prefix):
            title = line[len(title_prefix) :].strip()
            break
    if title != "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report":
        errors.append(f"HN title must use the BYO influence-boundary positioning, observed: {title!r}")
    if f"url: {CANONICAL_URL}" not in text:
        errors.append("HN worksheet must point at the canonical influence-boundary URL")
    for phrase in OLD_POSITIONING_PHRASES:
        if phrase.lower() in title.lower():
            errors.append(f"HN title reuses old positioning phrase: {phrase}")
    for phrase in ("users can swap in their own local file", "directory scans are supported", "gate-only json output"):
        if phrase not in text.lower():
            errors.append(f"HN first-comment facts missing distinct BYO fact: {phrase}")


def _check_social_payload(payload: dict[str, Any], errors: list[str]) -> None:
    hn = payload.get("hn", {})
    if hn.get("url") != CANONICAL_URL:
        errors.append(f"social payload HN URL must be canonical influence-boundary URL, observed {hn.get('url')!r}")
    if hn.get("submission_type") != "url" or hn.get("text") != "":
        errors.append("social payload HN submission must remain a URL story with empty text")
    x_tweets = payload.get("x", {}).get("tweets", [])
    if not x_tweets or "Drop in AI memory files. Get an influence-boundary report." not in x_tweets[0]:
        errors.append("X thread must open with the BYO influence-boundary hook")
    linkedin = payload.get("linkedin", {}).get("body", "")
    for phrase in (
        "The difference from the last release is user input",
        "For product integration, the JSON includes an integration_gate object",
        "consumer integration smoke check",
    ):
        if phrase not in linkedin:
            errors.append(f"LinkedIn body missing distinctness/integration phrase: {phrase}")


def _check_page(text: str, errors: list[str]) -> None:
    if CANONICAL_URL not in text:
        errors.append("canonical HTML page must include its canonical URL")
    for phrase in (
        "Audit user-supplied local AI memory/context/state files",
        "Then point it at your own local file or directory",
        "To emit only the machine-readable gate",
        "consumer integration smoke test",
    ):
        if phrase not in text:
            errors.append(f"canonical page missing distinct BYO phrase: {phrase}")


def _check_legacy_alias(text: str, errors: list[str]) -> None:
    if CANONICAL_URL not in text:
        errors.append("legacy governability-overlay page must carry the influence-boundary canonical URL")


def _check_bundle(bundle: dict[str, Any], errors: list[str]) -> None:
    if bundle.get("public_page") != CANONICAL_URL:
        errors.append(f"publication bundle public_page must be canonical URL, observed {bundle.get('public_page')!r}")
    publication_files = set(bundle.get("publication_files", []))
    for required in (str(CANONICAL_PAGE), str(LEGACY_ALIAS_PAGE)):
        if required not in publication_files:
            errors.append(f"publication bundle missing required page: {required}")


def _check_release_texts(
    hn_text: str,
    linkedin_text: str,
    x_text: str,
    page_text: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    social_text = "\n".join([hn_text, linkedin_text, x_text])
    for old_url in OLD_RELEASE_URLS:
        if old_url in social_text:
            errors.append(f"social release copy still points at old launch URL: {old_url}")
    if "source-derived overlay" in social_text:
        errors.append("social release copy reuses source-derived overlay wording instead of BYO influence-boundary positioning")
    lower_hn = hn_text.lower()
    for phrase in OLD_POSITIONING_PHRASES:
        if phrase.lower() in lower_hn:
            errors.append(f"HN worksheet reuses old launch positioning phrase: {phrase}")
    combined = "\n".join([hn_text, linkedin_text, x_text, page_text])
    for phrase in REQUIRED_DISTINCT_PHRASES:
        if phrase not in combined:
            errors.append(f"release surface missing required distinct phrase: {phrase}")


def _read_text(root: Path, rel: Path, errors: list[str]) -> str:
    path = root / rel
    if not path.exists():
        errors.append(f"missing file: {rel}")
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(root: Path, rel: Path, errors: list[str]) -> dict[str, Any]:
    text = _read_text(root, rel, errors)
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {rel}: {exc}")
        return {}
    if not isinstance(decoded, dict):
        errors.append(f"JSON root must be object in {rel}")
        return {}
    return decoded


def _read_publication_bundle(root: Path, errors: list[str]) -> dict[str, Any]:
    bundle_path = root / PUBLICATION_BUNDLE
    if not bundle_path.exists():
        builder_path = root / "scripts/build_memory_state_influence_boundary_publication_bundle.py"
        if not builder_path.exists():
            errors.append(f"missing file: {PUBLICATION_BUNDLE}")
            return {}
        spec = importlib.util.spec_from_file_location("memory_state_distinctness_bundle_builder", builder_path)
        if spec is None or spec.loader is None:
            errors.append(f"unable to load bundle builder: {builder_path}")
            return {}
        module = importlib.util.module_from_spec(spec)
        sys.modules["memory_state_distinctness_bundle_builder"] = module
        spec.loader.exec_module(module)
        bundle = module.build_memory_state_influence_boundary_publication_bundle(root)
        if isinstance(bundle, dict):
            return bundle
        errors.append("bundle builder did not return a JSON object")
        return {}
    return _read_json(root, PUBLICATION_BUNDLE, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that the next Memory State HN launch is distinct from prior launches.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_release_distinctness(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_release_distinctness" else 1


if __name__ == "__main__":
    raise SystemExit(main())
