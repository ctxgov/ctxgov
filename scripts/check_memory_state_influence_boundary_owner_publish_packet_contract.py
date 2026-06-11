#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from json import JSONDecodeError
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_REL = Path("release/memory-state-governability-overlay/2026-06-11")
BUNDLE_JSON = PACK_REL / "memory-state-influence-boundary-publication-bundle.json"
OWNER_PACKET_SCRIPT = Path("scripts/render_memory_state_influence_boundary_owner_publish_packet.py")
SOCIAL_PAYLOAD_SCRIPT = Path("scripts/render_memory_state_governability_overlay_social_payload.py")
SOCIAL_DRAFT_DRIFT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_social_draft_drift.py")
PUBLISH_ENVELOPE_SCRIPT = Path("scripts/render_memory_state_influence_boundary_publish_command_envelope.py")
CONSUMER_WRAPPER_CONTRACT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py")
RELEASE_DISTINCTNESS_SCRIPT = Path("scripts/check_memory_state_influence_boundary_release_distinctness.py")

PUBLIC_URL = "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html"

OLD_POSITIONING_PHRASES = {
    "Show HN: CtxGov - a local claim firewall for AI memory claims",
    "local claim firewall for AI memory claims",
    "Show HN: CtxGov - a local governability overlay for AI memory state",
    "source-derived overlay",
    "AI memory claims need receipts",
    "Activation X-Ray shows what state influenced the answer",
    "Unsupported claims fail closed",
    "https://ctxgov.github.io/ctxgov/try-in-5-minutes.html",
    "https://ctxgov.github.io/ctxgov/activation-xray-try-in-5-minutes.html",
    "https://ctxgov.github.io/ctxgov/memory-state-governability-overlay-try-in-5-minutes.html",
}

PRIVATE_MARKERS = [
    "/" + "Users" + "/" + "chris",
    "/" + "Users" + "/",
    "/" + "private" + "/",
    "/" + "var" + "/" + "folders" + "/",
    "/" + "tmp" + "/",
    "chrisho" + "hoho",
    "ctxvault-" + "incubation",
]


def check_memory_state_influence_boundary_owner_publish_packet_contract(
    root: Path = ROOT,
    *,
    bundle_path: Path = BUNDLE_JSON,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    bundle_path = _resolve(root, bundle_path)

    owner_module = _load_script(root, OWNER_PACKET_SCRIPT, "memory_state_owner_packet_contract_owner", errors)
    social_module = _load_script(root, SOCIAL_PAYLOAD_SCRIPT, "memory_state_owner_packet_contract_social", errors)
    drift_module = _load_script(root, SOCIAL_DRAFT_DRIFT_SCRIPT, "memory_state_owner_packet_contract_social_drift", errors)
    envelope_module = _load_script(root, PUBLISH_ENVELOPE_SCRIPT, "memory_state_owner_packet_contract_envelope", errors)
    wrapper_module = _load_script(root, CONSUMER_WRAPPER_CONTRACT_SCRIPT, "memory_state_owner_packet_contract_wrapper", errors)
    distinct_module = _load_script(root, RELEASE_DISTINCTNESS_SCRIPT, "memory_state_owner_packet_contract_distinct", errors)

    bundle = _load_json_object(bundle_path, "publication bundle", errors)
    social_payload = _render_social_payload(root, social_module, errors) if social_module is not None else {}
    social_draft_drift = (
        drift_module.check_memory_state_influence_boundary_social_draft_drift(root)
        if drift_module is not None
        else {}
    )
    publish_envelope = (
        envelope_module.render_memory_state_influence_boundary_publish_command_envelope(root, bundle_path=bundle_path)
        if envelope_module is not None
        else {}
    )
    consumer_wrapper_contract = (
        wrapper_module.check_memory_state_influence_boundary_consumer_wrapper_contract(root)
        if wrapper_module is not None
        else {}
    )
    release_distinctness = (
        distinct_module.check_memory_state_influence_boundary_release_distinctness(root)
        if distinct_module is not None
        else {}
    )

    final_preflight = _synthetic_final_preflight(
        bundle=bundle,
        publish_envelope=publish_envelope,
        social_draft_drift=social_draft_drift,
        consumer_wrapper_contract=consumer_wrapper_contract,
        release_distinctness=release_distinctness,
    )

    packet: dict[str, Any] = {}
    rendered_json: dict[str, Any] = {}
    rendered_texts: dict[str, str] = {}
    if owner_module is not None:
        contract_tmp_parent = root / ".ctxvault" / "memory-state-governability-overlay"
        contract_tmp_parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix="owner-packet-contract-", dir=contract_tmp_parent) as tmp:
            tmp_path = Path(tmp)
            output_json = tmp_path / "owner-packet.json"
            output_md = tmp_path / "owner-packet.md"
            packet = owner_module.render_memory_state_influence_boundary_owner_publish_packet(
                root,
                output_json=output_json,
                output_md=output_md,
                final_preflight=final_preflight,
                social_payload=social_payload,
                social_draft_drift=social_draft_drift,
                publish_envelope=publish_envelope,
            )
            rendered_json = _load_json_object(output_json, "rendered owner packet JSON", errors)
            rendered_texts = {
                "json": output_json.read_text(encoding="utf-8") if output_json.exists() else "",
                "markdown": output_md.read_text(encoding="utf-8") if output_md.exists() else "",
            }
            if not output_json.exists():
                errors.append("owner packet JSON output was not written")
            if not output_md.exists():
                errors.append("owner packet markdown output was not written")

    _validate_component_statuses(
        bundle=bundle,
        social_payload=social_payload,
        social_draft_drift=social_draft_drift,
        publish_envelope=publish_envelope,
        consumer_wrapper_contract=consumer_wrapper_contract,
        release_distinctness=release_distinctness,
        errors=errors,
    )
    _validate_packet(
        packet=packet,
        rendered_json=rendered_json,
        social_payload=social_payload,
        social_draft_drift=social_draft_drift,
        publish_envelope=publish_envelope,
        bundle=bundle,
        errors=errors,
    )
    _validate_rendered_texts(rendered_texts, errors)

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-owner-publish-packet-contract-check/v0",
        "status": (
            "pass_memory_state_influence_boundary_owner_publish_packet_contract"
            if not errors
            else "fail_memory_state_influence_boundary_owner_publish_packet_contract"
        ),
        "milestone": "Local Memory State Influence Boundary Report",
        "owner_packet_status": packet.get("status"),
        "publication_bundle_status": bundle.get("status"),
        "publication_bundle_sha256": bundle.get("publication_bundle_sha256"),
        "publication_file_count": bundle.get("publication_file_count"),
        "owner_packet_publication_bundle_sha256": packet.get("publication_bundle_sha256"),
        "owner_packet_publication_file_count": packet.get("publication_file_count"),
        "publish_command_envelope_status": publish_envelope.get("status"),
        "social_payload_status": social_payload.get("status"),
        "social_draft_drift_status": social_draft_drift.get("status"),
        "social_draft_old_positioning_status": social_draft_drift.get("old_positioning_status"),
        "consumer_wrapper_contract_status": consumer_wrapper_contract.get("status"),
        "release_distinctness_status": release_distinctness.get("status"),
        "owner_review_checklist_status": _owner_review_checklist_status(packet),
        "publish_commands_status": _publish_commands_status(packet),
        "post_publish_commands_status": _post_publish_commands_status(packet),
        "social_copy_status": _social_copy_status(packet, social_payload),
        "rendered_output_boundary_status": _rendered_output_boundary_status(rendered_texts),
        "hn_title": packet.get("hn", {}).get("title"),
        "hn_url": packet.get("hn", {}).get("url"),
        "x_tweet_count": packet.get("x", {}).get("tweet_count"),
        "x_tweet_character_counts": social_payload.get("x", {}).get("tweet_character_counts", []),
        "claim_boundary": packet.get("claim_boundary", {}),
        "side_effect_boundary": packet.get("side_effect_boundary", {}),
        "manual_review_required": packet.get("manual_review_required"),
        "publication_executed": bool(packet.get("publication_executed")),
        "outreach_performed": bool(packet.get("outreach_performed")),
        "error_count": len(errors),
        "errors": errors,
    }


def _synthetic_final_preflight(
    *,
    bundle: dict[str, Any],
    publish_envelope: dict[str, Any],
    social_draft_drift: dict[str, Any],
    consumer_wrapper_contract: dict[str, Any],
    release_distinctness: dict[str, Any],
) -> dict[str, Any]:
    file_count = bundle.get("publication_file_count")
    return {
        "status": "pass_memory_state_influence_boundary_final_preflight",
        "go_no_go": "go_local_ready_external_publish_pending",
        "issue_count": 0,
        "command_count": 0,
        "sample_input_file_count": bundle.get("sample_input_file_count"),
        "sample_blocked_ref_count": bundle.get("sample_blocked_ref_count"),
        "sample_stale_ref_count": bundle.get("sample_stale_ref_count"),
        "publication_bundle_status": bundle.get("status"),
        "publication_bundle_sha256": bundle.get("publication_bundle_sha256"),
        "publication_file_count": file_count,
        "materialized_copied_file_count": file_count,
        "publish_command_envelope_status": publish_envelope.get("status"),
        "social_draft_drift_status": social_draft_drift.get("status"),
        "social_draft_old_positioning_status": social_draft_drift.get("old_positioning_status"),
        "consumer_wrapper_contract_status": consumer_wrapper_contract.get("status"),
        "consumer_wrapper_contract_blocked_decision": consumer_wrapper_contract.get("blocked_decision"),
        "consumer_wrapper_contract_pass_decision": consumer_wrapper_contract.get("pass_decision"),
        "release_distinctness_status": release_distinctness.get("status"),
        "release_distinctness_warning_count": release_distinctness.get("warning_count"),
        "public_page": bundle.get("public_page", PUBLIC_URL),
    }


def _validate_component_statuses(
    *,
    bundle: dict[str, Any],
    social_payload: dict[str, Any],
    social_draft_drift: dict[str, Any],
    publish_envelope: dict[str, Any],
    consumer_wrapper_contract: dict[str, Any],
    release_distinctness: dict[str, Any],
    errors: list[str],
) -> None:
    expected = {
        "publication_bundle": (bundle, "pass_memory_state_influence_boundary_publication_bundle"),
        "social_payload": (social_payload, "pass_memory_state_governability_overlay_social_payload"),
        "social_draft_drift": (social_draft_drift, "pass_memory_state_influence_boundary_social_draft_drift"),
        "publish_envelope": (publish_envelope, "pass_memory_state_influence_boundary_publish_command_envelope"),
        "consumer_wrapper_contract": (
            consumer_wrapper_contract,
            "pass_memory_state_influence_boundary_consumer_wrapper_contract",
        ),
        "release_distinctness": (release_distinctness, "pass_memory_state_influence_boundary_release_distinctness"),
    }
    for label, (payload, expected_status) in expected.items():
        if payload.get("status") != expected_status:
            errors.append(f"{label} status mismatch: expected {expected_status}, observed {payload.get('status')}")
    if publish_envelope.get("publication_bundle_sha256") != bundle.get("publication_bundle_sha256"):
        errors.append("publish envelope bundle digest does not match publication bundle digest")
    if publish_envelope.get("publication_file_count") != bundle.get("publication_file_count"):
        errors.append("publish envelope file count does not match publication bundle file count")
    if social_draft_drift.get("old_positioning_status") != "pass":
        errors.append("social draft drift old positioning check did not pass")
    if social_draft_drift.get("old_positioning_hits"):
        errors.append(f"social draft drift reported old positioning hits: {social_draft_drift.get('old_positioning_hits')!r}")
    if any(count > 280 for count in social_payload.get("x", {}).get("tweet_character_counts", [])):
        errors.append("social payload contains an X tweet over 280 characters")


def _validate_packet(
    *,
    packet: dict[str, Any],
    rendered_json: dict[str, Any],
    social_payload: dict[str, Any],
    social_draft_drift: dict[str, Any],
    publish_envelope: dict[str, Any],
    bundle: dict[str, Any],
    errors: list[str],
) -> None:
    if packet.get("status") != "pass_memory_state_influence_boundary_owner_publish_packet":
        errors.append(f"owner packet status mismatch: {packet.get('status')}")
    if rendered_json and rendered_json != packet:
        errors.append("rendered owner packet JSON drifted from returned packet")
    if packet.get("publication_bundle_sha256") != bundle.get("publication_bundle_sha256"):
        errors.append("owner packet digest does not match publication bundle digest")
    if packet.get("publication_bundle_sha256") != publish_envelope.get("publication_bundle_sha256"):
        errors.append("owner packet digest does not match publish envelope digest")
    if packet.get("publication_file_count") != bundle.get("publication_file_count"):
        errors.append("owner packet file count does not match publication bundle file count")
    if packet.get("public_page") != PUBLIC_URL:
        errors.append(f"owner packet public page mismatch: {packet.get('public_page')}")
    if packet.get("hn") != social_payload.get("hn"):
        errors.append("owner packet HN copy drifted from social payload")
    if packet.get("linkedin") != social_payload.get("linkedin"):
        errors.append("owner packet LinkedIn copy drifted from social payload")
    if packet.get("x") != social_payload.get("x"):
        errors.append("owner packet X copy drifted from social payload")
    if packet.get("social_draft_drift", {}).get("status") != social_draft_drift.get("status"):
        errors.append("owner packet social drift summary status mismatch")
    if packet.get("social_draft_drift", {}).get("old_positioning_hits") not in ({}, None):
        errors.append("owner packet social drift summary contains old positioning hits")
    if _owner_review_checklist_status(packet) != "pass":
        errors.append("owner packet checklist is missing required review items")
    if _publish_commands_status(packet) != "pass":
        errors.append("owner packet publish commands are incomplete")
    if _post_publish_commands_status(packet) != "pass":
        errors.append("owner packet post-publish commands are incomplete")
    if _social_copy_status(packet, social_payload) != "pass":
        errors.append("owner packet social copy is incomplete or over character limits")
    if any(bool(value) for value in packet.get("claim_boundary", {}).values()):
        errors.append("owner packet claim boundary contains true values")
    if any(bool(value) for value in packet.get("side_effect_boundary", {}).values()):
        errors.append("owner packet side-effect boundary contains true values")
    if packet.get("publication_executed"):
        errors.append("owner packet claims publication was executed")
    if packet.get("outreach_performed"):
        errors.append("owner packet claims outreach was performed")
    if packet.get("manual_review_required") != "owner_confirms_external_publish_and_social_copy_only":
        errors.append(f"owner packet manual_review_required mismatch: {packet.get('manual_review_required')}")


def _owner_review_checklist_status(packet: dict[str, Any]) -> str:
    checklist = "\n".join(packet.get("owner_review_checklist", []))
    required_fragments = [
        "check_memory_state_influence_boundary_final_preflight.py",
        "check_memory_state_influence_boundary_social_draft_drift.py",
        "publication bundle digest",
        "check_memory_state_influence_boundary_owner_publish_packet_contract.py",
        "git add, commit, and push",
        "check_memory_state_influence_boundary_live_publication.py --live",
        "HN",
        "Do not add public benchmark",
    ]
    return "pass" if all(fragment in checklist for fragment in required_fragments) else "fail"


def _publish_commands_status(packet: dict[str, Any]) -> str:
    commands = packet.get("publish_commands", [])
    joined = "\n".join(commands)
    required_fragments = [
        "git add",
        "scripts/render_memory_state_influence_boundary_owner_publish_packet.py",
        "scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
        "git commit -m",
        "git push origin main",
    ]
    return "pass" if all(fragment in joined for fragment in required_fragments) else "fail"


def _post_publish_commands_status(packet: dict[str, Any]) -> str:
    commands = "\n".join(packet.get("post_publish_commands", []))
    return "pass" if "python3 scripts/check_memory_state_influence_boundary_live_publication.py --live" in commands else "fail"


def _social_copy_status(packet: dict[str, Any], social_payload: dict[str, Any]) -> str:
    if packet.get("hn", {}).get("title") != social_payload.get("hn", {}).get("title"):
        return "fail"
    if packet.get("hn", {}).get("url") != PUBLIC_URL:
        return "fail"
    if packet.get("hn", {}).get("text") != "":
        return "fail"
    if not packet.get("linkedin", {}).get("body"):
        return "fail"
    tweets = packet.get("x", {}).get("tweets", [])
    if not tweets:
        return "fail"
    if any(len(tweet) > 280 for tweet in tweets):
        return "fail"
    return "pass"


def _validate_rendered_texts(rendered_texts: dict[str, str], errors: list[str]) -> None:
    if _rendered_output_boundary_status(rendered_texts) != "pass":
        for name, text in rendered_texts.items():
            for phrase in OLD_POSITIONING_PHRASES:
                if phrase.lower() in text.lower():
                    errors.append(f"{name} output contains old positioning phrase: {phrase}")
            for marker in PRIVATE_MARKERS:
                if marker in text:
                    errors.append(f"{name} output contains private marker: {marker}")


def _rendered_output_boundary_status(rendered_texts: dict[str, str]) -> str:
    joined = "\n".join(rendered_texts.values())
    if any(phrase.lower() in joined.lower() for phrase in OLD_POSITIONING_PHRASES):
        return "fail"
    if any(marker in joined for marker in PRIVATE_MARKERS):
        return "fail"
    return "pass"


def _render_social_payload(root: Path, social_module: Any, errors: list[str]) -> dict[str, Any]:
    contract_tmp_parent = root / ".ctxvault" / "memory-state-governability-overlay"
    contract_tmp_parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="owner-packet-social-", dir=contract_tmp_parent) as tmp:
        tmp_path = Path(tmp)
        payload = social_module.render_memory_state_governability_overlay_social_payload(
            root,
            output_json=tmp_path / "social.json",
            output_md=tmp_path / "social.md",
        )
    if not isinstance(payload, dict):
        errors.append("social payload renderer did not return a JSON object")
        return {}
    return payload


def _load_script(root: Path, rel_path: Path, module_name: str, errors: list[str]) -> Any | None:
    path = root / rel_path
    if not path.exists():
        errors.append(f"missing script: {rel_path}")
        return None
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        errors.append(f"unable to load script: {rel_path}")
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing {label}: {_display_path(path, ROOT)}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as exc:
        errors.append(f"{label} is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object")
        return {}
    return payload


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the Memory State Influence Boundary owner publish packet contract.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path, default=BUNDLE_JSON)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_owner_publish_packet_contract(
        args.root,
        bundle_path=args.bundle,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_owner_publish_packet_contract" else 1


if __name__ == "__main__":
    raise SystemExit(main())
