#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_REL = Path("release/memory-state-governability-overlay/2026-06-11")
SOCIAL_RENDERER = Path("scripts/render_memory_state_governability_overlay_social_payload.py")
SOCIAL_JSON = PACK_REL / "memory-state-governability-overlay-social-payload.json"
SOCIAL_MD = PACK_REL / "memory-state-governability-overlay-social-payload.md"
HN_POST = PACK_REL / "hn-post.md"
LINKEDIN_POST = PACK_REL / "linkedin-post.md"
X_THREAD = PACK_REL / "x-thread.md"

OLD_SOCIAL_POSITIONING_PHRASES = {
    "claim_firewall_title": "Show HN: CtxGov - a local claim firewall for AI memory claims",
    "claim_firewall_phrase": "local claim firewall for AI memory claims",
    "generic_governability_overlay_title": "Show HN: CtxGov - a local governability overlay for AI memory state",
    "source_derived_overlay": "source-derived overlay",
    "claim_firewall_punchline": "AI memory claims need receipts",
    "activation_xray_punchline": "Activation X-Ray shows what state influenced the answer",
    "unsupported_claims_punchline": "Unsupported claims fail closed",
    "claim_firewall_url": "https://ctxgov.github.io/ctxgov/try-in-5-minutes.html",
    "activation_xray_url": "https://ctxgov.github.io/ctxgov/activation-xray-try-in-5-minutes.html",
    "legacy_governability_overlay_url": "https://ctxgov.github.io/ctxgov/memory-state-governability-overlay-try-in-5-minutes.html",
}


def check_memory_state_influence_boundary_social_draft_drift(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    renderer = _load_renderer(root, errors)
    payload = _render_expected_payload(root, renderer, errors) if renderer is not None else {}

    payload_json_errors = _check_payload_json(root, payload)
    payload_markdown_errors = _check_payload_markdown(root, renderer, payload) if renderer is not None else ["social renderer unavailable"]
    hn_errors = _check_hn_draft(root, payload)
    linkedin_errors = _check_linkedin_draft(root, payload)
    x_errors = _check_x_thread(root, payload)
    old_positioning_hits = _old_positioning_hits(root)
    boundary_errors = _check_boundaries(payload)

    for section, section_errors in (
        ("payload_json", payload_json_errors),
        ("payload_markdown", payload_markdown_errors),
        ("hn", hn_errors),
        ("linkedin", linkedin_errors),
        ("x_thread", x_errors),
        ("old_positioning", [f"{key}: {phrase}" for key, phrase in old_positioning_hits.items()]),
        ("boundaries", boundary_errors),
    ):
        errors.extend(f"{section}: {error}" for error in section_errors)

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-social-draft-drift/v0",
        "status": "pass_memory_state_influence_boundary_social_draft_drift" if not errors else "fail_memory_state_influence_boundary_social_draft_drift",
        "milestone": "Local Memory State Influence Boundary Report",
        "payload_status": payload.get("status"),
        "payload_json_drift_status": _section_status(payload_json_errors),
        "payload_markdown_drift_status": _section_status(payload_markdown_errors),
        "hn_draft_drift_status": _section_status(hn_errors),
        "linkedin_draft_drift_status": _section_status(linkedin_errors),
        "x_thread_drift_status": _section_status(x_errors),
        "old_positioning_status": "pass" if not old_positioning_hits else "fail",
        "hn_title": payload.get("hn", {}).get("title"),
        "hn_url": payload.get("hn", {}).get("url"),
        "x_tweet_count": payload.get("x", {}).get("tweet_count"),
        "x_tweet_character_counts": payload.get("x", {}).get("tweet_character_counts", []),
        "old_positioning_hits": old_positioning_hits,
        "claim_boundary": payload.get("claim_boundary", {}),
        "side_effect_boundary": payload.get("side_effect_boundary", {}),
        "manual_review_required": "owner_manual_platform_submit_only",
        "publication_executed": False,
        "outreach_performed": False,
        "error_count": len(errors),
        "errors": errors,
    }


def _load_renderer(root: Path, errors: list[str]) -> Any | None:
    path = root / SOCIAL_RENDERER
    if not path.exists():
        errors.append(f"missing social renderer: {SOCIAL_RENDERER}")
        return None
    spec = importlib.util.spec_from_file_location("memory_state_social_draft_renderer", path)
    if spec is None or spec.loader is None:
        errors.append(f"unable to load social renderer: {SOCIAL_RENDERER}")
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["memory_state_social_draft_renderer"] = module
    spec.loader.exec_module(module)
    return module


def _render_expected_payload(root: Path, renderer: Any, errors: list[str]) -> dict[str, Any]:
    with TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        payload = renderer.render_memory_state_governability_overlay_social_payload(
            root,
            output_json=tmp_root / "social.json",
            output_md=tmp_root / "social.md",
        )
    if not isinstance(payload, dict):
        errors.append("social renderer did not return a JSON object")
        return {}
    expected = dict(payload)
    expected["payload_outputs"] = {
        "json": str(renderer.DEFAULT_OUTPUT_JSON),
        "markdown": str(renderer.DEFAULT_OUTPUT_MD),
    }
    return expected


def _check_payload_json(root: Path, expected_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    observed = _read_json(root / SOCIAL_JSON, errors)
    if observed and _canonical_json(observed) != _canonical_json(expected_payload):
        errors.append("social payload JSON drifted from renderer output")
    return errors


def _check_payload_markdown(root: Path, renderer: Any, expected_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    observed = _read_text(root / SOCIAL_MD, errors)
    expected = renderer._render_markdown(expected_payload)
    if observed and observed != expected:
        errors.append("social payload markdown drifted from renderer output")
    return errors


def _check_hn_draft(root: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    text = _read_text(root / HN_POST, errors)
    if not text:
        return errors
    block = next((fence for fence in _extract_fenced_blocks(text, "text") if "title:" in fence and "url:" in fence), "")
    observed = _parse_hn_submission(block)
    expected_hn = payload.get("hn", {})
    expected = {
        "title": expected_hn.get("title"),
        "url": expected_hn.get("url"),
        "text": "empty" if expected_hn.get("text") == "" else expected_hn.get("text"),
    }
    if observed != expected:
        errors.append(f"HN URL submission drifted from payload: observed={observed!r} expected={expected!r}")
    if "No HN submission has been executed" not in text:
        errors.append("HN worksheet must state that no HN submission has been executed")
    return errors


def _check_linkedin_draft(root: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    text = _read_text(root / LINKEDIN_POST, errors)
    if not text:
        return errors
    observed = _strip_draft_preamble(text, expected_heading="# LinkedIn Post")
    expected = payload.get("linkedin", {}).get("body", "")
    if observed != expected:
        errors.append("LinkedIn draft body drifted from payload body")
    if "No LinkedIn post has been executed" not in text:
        errors.append("LinkedIn draft must state that no LinkedIn post has been executed")
    return errors


def _check_x_thread(root: Path, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    text = _read_text(root / X_THREAD, errors)
    if not text:
        return errors
    observed = _extract_fenced_blocks(text, "text")
    expected = payload.get("x", {}).get("tweets", [])
    if observed != expected:
        errors.append(f"X thread drifted from payload tweets: observed_count={len(observed)} expected_count={len(expected)}")
    if "No X post has been executed" not in text:
        errors.append("X thread draft must state that no X post has been executed")
    return errors


def _old_positioning_hits(root: Path) -> dict[str, str]:
    text = "\n".join(
        _read_text(root / rel, [])
        for rel in (HN_POST, LINKEDIN_POST, X_THREAD, SOCIAL_JSON, SOCIAL_MD)
    )
    lower_text = text.lower()
    return {
        key: phrase
        for key, phrase in OLD_SOCIAL_POSITIONING_PHRASES.items()
        if phrase.lower() in lower_text
    }


def _check_boundaries(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if any(bool(value) for value in payload.get("claim_boundary", {}).values()):
        errors.append("claim boundary contains true values")
    if any(bool(value) for value in payload.get("side_effect_boundary", {}).values()):
        errors.append("side-effect boundary contains true values")
    if payload.get("publication_executed"):
        errors.append("payload claims publication was executed")
    if payload.get("outreach_performed"):
        errors.append("payload claims outreach was performed")
    return errors


def _extract_fenced_blocks(text: str, language: str) -> list[str]:
    pattern = re.compile(rf"```{re.escape(language)}\n(.*?)\n```", re.DOTALL)
    return [match.group(1) for match in pattern.finditer(text)]


def _parse_hn_submission(block: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in block.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        if key in {"title", "url", "text"}:
            parsed[key] = value.strip()
    return parsed


def _strip_draft_preamble(text: str, *, expected_heading: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() == expected_heading:
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    if lines and lines[0].startswith("Status:"):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines).rstrip()


def _read_text(path: Path, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"missing file: {_display_path(path, ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    text = _read_text(path, errors)
    if not text:
        return {}
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {_display_path(path, ROOT)}: {exc}")
        return {}
    if not isinstance(decoded, dict):
        errors.append(f"JSON root must be object in {_display_path(path, ROOT)}")
        return {}
    return decoded


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _section_status(errors: list[str]) -> str:
    return "pass" if not errors else "fail"


def main() -> int:
    parser = argparse.ArgumentParser(description="Check that static HN/LinkedIn/X drafts match the Memory State social payload.")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_social_draft_drift(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_social_draft_drift" else 1


if __name__ == "__main__":
    raise SystemExit(main())
