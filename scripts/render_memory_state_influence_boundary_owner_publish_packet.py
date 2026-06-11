#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = Path(".ctxvault") / "memory-state-governability-overlay"
FINAL_PREFLIGHT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_final_preflight.py")
SOCIAL_PAYLOAD_SCRIPT = Path("scripts/render_memory_state_governability_overlay_social_payload.py")
SOCIAL_DRAFT_DRIFT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_social_draft_drift.py")
PUBLISH_ENVELOPE_SCRIPT = Path("scripts/render_memory_state_influence_boundary_publish_command_envelope.py")


CLAIM_BOUNDARY = {
    "public_savings_claim_created": False,
    "public_benchmark_claim_created": False,
    "public_adoption_claim_created": False,
    "public_compatibility_claim_created": False,
    "public_support_claim_created": False,
    "public_security_claim_created": False,
    "public_endorsement_claim_created": False,
    "stable_protocol_claim_created": False,
}

SIDE_EFFECT_BOUNDARY = {
    "network_access_performed": False,
    "provider_or_model_call_performed": False,
    "external_target_repo_modified": False,
    "memory_backend_written": False,
    "package_published": False,
    "public_release_created": False,
    "outreach_performed": False,
}


def render_memory_state_influence_boundary_owner_publish_packet(
    root: Path = ROOT,
    *,
    output_json: Path | None = None,
    output_md: Path | None = None,
    final_preflight: dict[str, Any] | None = None,
    social_payload: dict[str, Any] | None = None,
    social_draft_drift: dict[str, Any] | None = None,
    publish_envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    if final_preflight is None:
        final_module = _load_script(root, FINAL_PREFLIGHT_SCRIPT, "memory_state_owner_packet_final_preflight")
        final_preflight = final_module.check_memory_state_influence_boundary_final_preflight(root)
    if social_payload is None:
        social_module = _load_script(root, SOCIAL_PAYLOAD_SCRIPT, "memory_state_owner_packet_social_payload")
        social_payload = social_module.render_memory_state_governability_overlay_social_payload(root)
    if social_draft_drift is None:
        social_drift_module = _load_script(root, SOCIAL_DRAFT_DRIFT_SCRIPT, "memory_state_owner_packet_social_draft_drift")
        social_draft_drift = social_drift_module.check_memory_state_influence_boundary_social_draft_drift(root)
    if publish_envelope is None:
        envelope_module = _load_script(root, PUBLISH_ENVELOPE_SCRIPT, "memory_state_owner_packet_publish_envelope")
        publish_envelope = envelope_module.render_memory_state_influence_boundary_publish_command_envelope(root)

    errors: list[str] = []
    if final_preflight.get("status") != "pass_memory_state_influence_boundary_final_preflight":
        errors.append("final local preflight did not pass")
    if social_payload.get("status") != "pass_memory_state_governability_overlay_social_payload":
        errors.append("social payload did not pass")
    if social_draft_drift.get("status") != "pass_memory_state_influence_boundary_social_draft_drift":
        errors.append("social draft drift check did not pass")
    if publish_envelope.get("status") != "pass_memory_state_influence_boundary_publish_command_envelope":
        errors.append("publish command envelope did not pass")
    if publish_envelope.get("publication_bundle_sha256") != final_preflight.get("publication_bundle_sha256"):
        errors.append("publish envelope digest does not match final preflight digest")
    if any(bool(value) for value in CLAIM_BOUNDARY.values()):
        errors.append("claim boundary contains true values")
    if any(bool(value) for value in SIDE_EFFECT_BOUNDARY.values()):
        errors.append("side-effect boundary contains true values")

    packet = {
        "schema_id": "ctxvault.memory-state-influence-boundary-owner-publish-packet/v0",
        "status": (
            "pass_memory_state_influence_boundary_owner_publish_packet"
            if not errors
            else "fail_memory_state_influence_boundary_owner_publish_packet"
        ),
        "milestone": "Local Memory State Influence Boundary Report",
        "public_page": final_preflight.get(
            "public_page",
            "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
        ),
        "final_preflight": _summarize_final_preflight(final_preflight),
        "social_draft_drift": _summarize_social_draft_drift(social_draft_drift),
        "publication_bundle_sha256": final_preflight.get("publication_bundle_sha256"),
        "publication_file_count": final_preflight.get("publication_file_count"),
        "publish_commands": publish_envelope.get("publish_commands", []),
        "post_publish_commands": publish_envelope.get("post_publish_commands", []),
        "manual_social_actions": publish_envelope.get("manual_social_actions", []),
        "hn": social_payload.get("hn", {}),
        "linkedin": social_payload.get("linkedin", {}),
        "x": social_payload.get("x", {}),
        "owner_review_checklist": [
            "Run python3 scripts/check_memory_state_influence_boundary_final_preflight.py and confirm pass_memory_state_influence_boundary_final_preflight.",
            "Run python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py and confirm static HN/LinkedIn/X drafts match the generated payload.",
            "Confirm the publication bundle digest in this packet matches the final preflight digest.",
            "Run python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py and confirm pass_memory_state_influence_boundary_owner_publish_packet_contract.",
            "Execute the listed git add, commit, and push commands only in the intended public checkout.",
            "Wait for GitHub Pages to deploy, then run python3 scripts/check_memory_state_influence_boundary_live_publication.py --live.",
            "Submit the HN URL post and manually post the prepared X and LinkedIn copy after the live page check passes.",
            "Do not add public benchmark, savings, adoption, compatibility/support, endorsement, security, or stable-protocol claims.",
        ],
        "manual_review_required": "owner_confirms_external_publish_and_social_copy_only",
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "side_effect_boundary": dict(SIDE_EFFECT_BOUNDARY),
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }

    json_path = _resolve(root, output_json or DEFAULT_OUTPUT_DIR / "memory-state-owner-publish-packet.json")
    md_path = _resolve(root, output_md or DEFAULT_OUTPUT_DIR / "memory-state-owner-publish-packet.md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(json_path, json.dumps(packet, indent=2, sort_keys=True) + "\n")
    _write_text_atomic(md_path, _render_markdown(packet))
    packet["packet_outputs"] = {
        "json": _display_path(json_path, root),
        "markdown": _display_path(md_path, root),
    }
    _write_text_atomic(json_path, json.dumps(packet, indent=2, sort_keys=True) + "\n")
    return packet


def _load_script(root: Path, rel_path: Path, module_name: str) -> Any:
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _summarize_final_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "go_no_go": payload.get("go_no_go"),
        "issue_count": payload.get("issue_count"),
        "command_count": payload.get("command_count"),
        "sample_input_file_count": payload.get("sample_input_file_count"),
        "sample_blocked_ref_count": payload.get("sample_blocked_ref_count"),
        "sample_stale_ref_count": payload.get("sample_stale_ref_count"),
        "publication_bundle_status": payload.get("publication_bundle_status"),
        "publication_bundle_sha256": payload.get("publication_bundle_sha256"),
        "publication_file_count": payload.get("publication_file_count"),
        "materialized_copied_file_count": payload.get("materialized_copied_file_count"),
        "publish_command_envelope_status": payload.get("publish_command_envelope_status"),
        "social_draft_drift_status": payload.get("social_draft_drift_status"),
        "social_draft_old_positioning_status": payload.get("social_draft_old_positioning_status"),
        "consumer_wrapper_contract_status": payload.get("consumer_wrapper_contract_status"),
        "consumer_wrapper_contract_blocked_decision": payload.get("consumer_wrapper_contract_blocked_decision"),
        "consumer_wrapper_contract_pass_decision": payload.get("consumer_wrapper_contract_pass_decision"),
        "release_distinctness_status": payload.get("release_distinctness_status"),
        "release_distinctness_warning_count": payload.get("release_distinctness_warning_count"),
    }


def _summarize_social_draft_drift(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "payload_json_drift_status": payload.get("payload_json_drift_status"),
        "payload_markdown_drift_status": payload.get("payload_markdown_drift_status"),
        "hn_draft_drift_status": payload.get("hn_draft_drift_status"),
        "linkedin_draft_drift_status": payload.get("linkedin_draft_drift_status"),
        "x_thread_drift_status": payload.get("x_thread_drift_status"),
        "old_positioning_status": payload.get("old_positioning_status"),
        "old_positioning_hits": payload.get("old_positioning_hits", {}),
    }


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Memory State Influence Boundary Owner Publish Packet",
        "",
        "Status: local owner packet only. No branch, commit, push, Pages deploy, HN submission, X post, LinkedIn post, or outreach has been executed.",
        "",
        f"Milestone: `{packet['milestone']}`",
        f"Status: `{packet['status']}`",
        f"Public page: {packet['public_page']}",
        f"Bundle digest: `{packet.get('publication_bundle_sha256')}`",
        f"Publication files: `{packet.get('publication_file_count')}`",
        "",
        "## Final Preflight",
        "",
        "```json",
        json.dumps(packet["final_preflight"], indent=2, sort_keys=True),
        "```",
        "",
        "## Social Draft Drift",
        "",
        "```json",
        json.dumps(packet["social_draft_drift"], indent=2, sort_keys=True),
        "```",
        "",
        "## Publish Commands",
        "",
        "```sh",
        *packet["publish_commands"],
        "```",
        "",
        "## Post-Publish Check",
        "",
        "```sh",
        *packet["post_publish_commands"],
        "```",
        "",
        "## HN URL Submission",
        "",
        "```text",
        f"title: {packet['hn'].get('title', '')}",
        f"url: {packet['hn'].get('url', '')}",
        "text: empty",
        "```",
        "",
        "## LinkedIn",
        "",
        packet["linkedin"].get("body", ""),
        "",
        "## X Thread",
        "",
    ]
    for tweet in packet["x"].get("tweets", []):
        lines.extend(["```text", tweet, "```", ""])
    lines.extend(
        [
            "## Owner Checklist",
            "",
            *[f"- {item}" for item in packet["owner_review_checklist"]],
            "",
            "Manual platform submission remains manual and unexecuted.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Memory State Influence Boundary owner publish packet.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()
    packet = render_memory_state_influence_boundary_owner_publish_packet(
        args.root,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet["status"] == "pass_memory_state_influence_boundary_owner_publish_packet" else 1


if __name__ == "__main__":
    raise SystemExit(main())
