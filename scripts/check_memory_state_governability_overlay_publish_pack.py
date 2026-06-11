#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_REL = Path("release/memory-state-governability-overlay/2026-06-11")
DEMO_SCRIPT = Path("scripts/run_memory_state_governability_overlay_demo.py")
INFLUENCE_BOUNDARY_SCRIPT = Path("scripts/run_memory_state_influence_boundary_report.py")
BYO_SMOKE_SCRIPT = Path("scripts/check_memory_state_influence_boundary_byo_smoke.py")
GATE_CONTRACT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_integration_gate_contract.py")
REPORT_CONTRACT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_report_contract.py")
CONSUMER_INTEGRATION_SCRIPT = Path("scripts/check_memory_state_influence_boundary_consumer_integration.py")
CONSUMER_WRAPPER_CONTRACT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py")
SOCIAL_SCRIPT = Path("scripts/render_memory_state_governability_overlay_social_payload.py")
SOCIAL_DRAFT_DRIFT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_social_draft_drift.py")
OWNER_PACKET_CONTRACT_SCRIPT = Path("scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py")
PUBLIC_PAGE = Path("docs/memory-state-influence-boundary-try-in-5-minutes.html")
DEMO_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/"
BYO_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md"
BYO_DIR_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/"
FAIL_ON_BLOCKED_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --fail-on-blocked"
GATE_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked"
BYO_SMOKE_COMMAND = "python3 scripts/check_memory_state_influence_boundary_byo_smoke.py"
GATE_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py"
REPORT_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_report_contract.py"
CONSUMER_INTEGRATION_COMMAND = "python3 scripts/check_memory_state_influence_boundary_consumer_integration.py"
CONSUMER_WRAPPER_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py"
CONSUMER_WRAPPER_COMMAND = "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py"
CONSUMER_WRAPPER_PASS_COMMAND = "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml"
RELEASE_DISTINCTNESS_COMMAND = "python3 scripts/check_memory_state_influence_boundary_release_distinctness.py"
SOCIAL_DRAFT_DRIFT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py"
OWNER_PACKET_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py"
GATE_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json")
REPORT_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json")
CONSUMER_WRAPPER_SCHEMA = Path("schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json")
GATE_EXAMPLE = PACK_REL / "integration-gate.example.json"
GATE_PASS_EXAMPLE = PACK_REL / "integration-gate.pass.example.json"
CONSUMER_WRAPPER_EXAMPLE = PACK_REL / "consumer-wrapper.example.json"
CONSUMER_WRAPPER_PASS_EXAMPLE = PACK_REL / "consumer-wrapper.pass.example.json"
PRODUCT_INTEGRATION_QUICKSTART = PACK_REL / "product-integration-quickstart.md"
FIXTURE_DEMO_COMMAND = "python3 scripts/run_memory_state_governability_overlay_demo.py"
FINAL_PREFLIGHT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_final_preflight.py"
LIVE_CHECK_COMMAND = "python3 scripts/check_memory_state_influence_boundary_live_publication.py --live"
BUNDLE_COMMAND = "python3 scripts/build_memory_state_influence_boundary_publication_bundle.py"
OWNER_PACKET_COMMAND = "python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py"
ENVELOPE_COMMAND = "python3 scripts/render_memory_state_influence_boundary_publish_command_envelope.py"
MATERIALIZE_COMMAND = "python3 scripts/materialize_memory_state_influence_boundary_publication_bundle.py --checkout <clean-ctxgov-checkout>"
PUBLISHER_COMMAND = "python3 scripts/publish_memory_state_influence_boundary_public_patch.py --checkout <clean-ctxgov-checkout>"
SAMPLE_INPUT_DIR = Path("examples/memory-state-influence-boundary")
PUBLIC_URL = "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html"

REQUIRED_FILES = {
    Path("README.md"): [
        "Local Memory State Influence Boundary Report",
        DEMO_COMMAND,
        BYO_COMMAND,
        BYO_DIR_COMMAND,
        GATE_COMMAND,
        BYO_SMOKE_COMMAND,
        GATE_CONTRACT_COMMAND,
        REPORT_CONTRACT_COMMAND,
        CONSUMER_INTEGRATION_COMMAND,
        CONSUMER_WRAPPER_CONTRACT_COMMAND,
        CONSUMER_WRAPPER_COMMAND,
        CONSUMER_WRAPPER_PASS_COMMAND,
        RELEASE_DISTINCTNESS_COMMAND,
        SOCIAL_DRAFT_DRIFT_COMMAND,
        OWNER_PACKET_COMMAND,
        OWNER_PACKET_CONTRACT_COMMAND,
        "integration_gate",
        str(REPORT_SCHEMA),
        str(CONSUMER_WRAPPER_SCHEMA),
        str(PRODUCT_INTEGRATION_QUICKSTART),
        "full report contract",
        "consumer integration",
        "consumer wrapper contract",
        "product integration quickstart",
        "raw_content_included=false",
        "input-relative paths",
        "not a stable protocol",
    ],
    PACK_REL / "README.md": [
        "Local Memory State Influence Boundary Report",
        DEMO_COMMAND,
        BYO_COMMAND,
        FINAL_PREFLIGHT_COMMAND,
        LIVE_CHECK_COMMAND,
        BUNDLE_COMMAND,
        OWNER_PACKET_COMMAND,
        ENVELOPE_COMMAND,
        MATERIALIZE_COMMAND,
        PUBLISHER_COMMAND,
        BYO_DIR_COMMAND,
        FAIL_ON_BLOCKED_COMMAND,
        GATE_COMMAND,
        BYO_SMOKE_COMMAND,
        GATE_CONTRACT_COMMAND,
        REPORT_CONTRACT_COMMAND,
        CONSUMER_INTEGRATION_COMMAND,
        CONSUMER_WRAPPER_CONTRACT_COMMAND,
        CONSUMER_WRAPPER_COMMAND,
        CONSUMER_WRAPPER_PASS_COMMAND,
        RELEASE_DISTINCTNESS_COMMAND,
        SOCIAL_DRAFT_DRIFT_COMMAND,
        OWNER_PACKET_COMMAND,
        OWNER_PACKET_CONTRACT_COMMAND,
        str(REPORT_SCHEMA),
        str(GATE_SCHEMA),
        str(GATE_EXAMPLE),
        str(GATE_PASS_EXAMPLE),
        str(CONSUMER_WRAPPER_SCHEMA),
        str(CONSUMER_WRAPPER_EXAMPLE),
        str(CONSUMER_WRAPPER_PASS_EXAMPLE),
        str(PRODUCT_INTEGRATION_QUICKSTART),
        "full report contract",
        "consumer integration",
        "consumer wrapper contract",
        "consumer wrapper example",
        "product integration quickstart",
        "distinct from the prior",
        "integration_gate",
        "fail_on_blocked_exit_code",
        FIXTURE_DEMO_COMMAND,
        "user-supplied",
        "bounded skipped-input sample",
        "BYO smoke",
        "Malformed JSON/JSONL/TOML state exports are blocked",
        "structured JSON/TOML/YAML key/value path",
        "Input-relative path rendering",
        "review recommendations",
        "MDX",
        "TOML",
        "YAML",
        "not a provider integration",
        "compatibility",
        "benchmark",
    ],
    PACK_REL / "hn-post.md": [
        "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report",
        PUBLIC_URL,
        DEMO_COMMAND,
        BYO_COMMAND,
        BYO_DIR_COMMAND,
        FAIL_ON_BLOCKED_COMMAND,
        GATE_COMMAND,
        CONSUMER_WRAPPER_COMMAND,
        CONSUMER_WRAPPER_PASS_COMMAND,
        "No HN submission has been executed",
    ],
    PACK_REL / "linkedin-post.md": [
        DEMO_COMMAND,
        BYO_COMMAND,
        BYO_DIR_COMMAND,
        PUBLIC_URL,
        "YAML/YML state files",
        "MDX context files",
        "TOML",
        "structured JSON/TOML/YAML",
        "input-relative paths",
        "integration_gate",
        "fail_on_blocked_exit_code",
        GATE_COMMAND,
        BYO_SMOKE_COMMAND,
        GATE_CONTRACT_COMMAND,
        REPORT_CONTRACT_COMMAND,
        CONSUMER_INTEGRATION_COMMAND,
        CONSUMER_WRAPPER_CONTRACT_COMMAND,
        CONSUMER_WRAPPER_COMMAND,
        CONSUMER_WRAPPER_PASS_COMMAND,
        "consumer integration",
        "product-integration shape",
        "allow_inform_only",
        "review recommendations",
        "not a provider integration",
        "compatibility",
        "benchmark",
    ],
    PACK_REL / "x-thread.md": [
        DEMO_COMMAND,
        PUBLIC_URL,
        "YAML",
        "TOML",
        "MDX",
        "Product wrapper shape",
        "allow_inform_only",
        "No compatibility matrix",
        "No benchmark",
    ],
    PUBLIC_PAGE: [
        "Local Memory State Influence Boundary Report",
        DEMO_COMMAND,
        BYO_COMMAND,
        FINAL_PREFLIGHT_COMMAND,
        BYO_DIR_COMMAND,
        FAIL_ON_BLOCKED_COMMAND,
        GATE_COMMAND,
        BYO_SMOKE_COMMAND,
        GATE_CONTRACT_COMMAND,
        REPORT_CONTRACT_COMMAND,
        CONSUMER_INTEGRATION_COMMAND,
        CONSUMER_WRAPPER_CONTRACT_COMMAND,
        CONSUMER_WRAPPER_COMMAND,
        CONSUMER_WRAPPER_PASS_COMMAND,
        RELEASE_DISTINCTNESS_COMMAND,
        OWNER_PACKET_COMMAND,
        OWNER_PACKET_CONTRACT_COMMAND,
        str(REPORT_SCHEMA),
        str(GATE_SCHEMA),
        str(GATE_EXAMPLE),
        str(GATE_PASS_EXAMPLE),
        str(CONSUMER_WRAPPER_SCHEMA),
        str(CONSUMER_WRAPPER_EXAMPLE),
        str(CONSUMER_WRAPPER_PASS_EXAMPLE),
        str(PRODUCT_INTEGRATION_QUICKSTART),
        "full report contract",
        "consumer integration",
        "consumer wrapper example",
        "product integration quickstart",
        "distinct from the prior",
        FIXTURE_DEMO_COMMAND,
        "integration_gate",
        "fail_on_blocked_exit_code",
        "not a provider integration",
        "not a provider integration",
        "compatibility matrix",
        "benchmark",
        "Malformed JSON/JSONL/TOML state exports are blocked",
        "structured JSON/TOML/YAML key/value path",
        "input/CLAUDE.md",
        "recommendations",
        "MDX",
        "TOML",
        "YAML",
    ],
    Path("schemas/README.md"): [
        "ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json",
        "ctxvault-memory-state-influence-boundary-report-v0.schema.json",
        "ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json",
        "full local v0 report payload",
        "local v0 gate payload",
        "consumer wrapper example",
        "local tooling contract only",
    ],
    REPORT_SCHEMA: [
        "ctxvault.memory-state-influence-boundary-report/v0",
        "user-supplied memory/context/state files",
        "raw_content_included",
        "additionalProperties",
        "not a stable protocol",
    ],
    CONSUMER_WRAPPER_SCHEMA: [
        "ctxvault.memory-state-influence-boundary-consumer-wrapper-example/v0",
        "allow_inform_only",
        "consumed_raw_content",
        "raw_content_included",
        "not a stable protocol",
    ],
    GATE_SCHEMA: [
        "ctxvault.memory-state-influence-boundary-integration-gate/v0",
        "fail_on_blocked",
        "raw_content_included",
        "additionalProperties",
        "not a stable protocol",
    ],
    GATE_EXAMPLE: [
        "ctxvault.memory-state-influence-boundary-integration-gate/v0",
        "fail_on_blocked_exit_code",
        "blocked_ref_count",
        "raw_content_included",
    ],
    GATE_PASS_EXAMPLE: [
        "ctxvault.memory-state-influence-boundary-integration-gate/v0",
        "fail_on_blocked_exit_code",
        "blocked_ref_count",
        "raw_content_included",
    ],
    CONSUMER_WRAPPER_EXAMPLE: [
        "ctxvault.memory-state-influence-boundary-consumer-wrapper-example/v0",
        "blocked_refs_present",
        "block",
        "raw_content_included",
    ],
    CONSUMER_WRAPPER_PASS_EXAMPLE: [
        "ctxvault.memory-state-influence-boundary-consumer-wrapper-example/v0",
        "gate_passed_no_blocked_refs",
        "allow_inform_only",
        "raw_content_included",
    ],
    PRODUCT_INTEGRATION_QUICKSTART: [
        "Product Integration Quickstart",
        DEMO_COMMAND,
        BYO_COMMAND,
        BYO_DIR_COMMAND,
        GATE_COMMAND,
        GATE_CONTRACT_COMMAND,
        REPORT_CONTRACT_COMMAND,
        CONSUMER_INTEGRATION_COMMAND,
        CONSUMER_WRAPPER_CONTRACT_COMMAND,
        CONSUMER_WRAPPER_COMMAND,
        CONSUMER_WRAPPER_PASS_COMMAND,
        str(GATE_SCHEMA),
        str(REPORT_SCHEMA),
        str(CONSUMER_WRAPPER_SCHEMA),
        str(GATE_EXAMPLE),
        str(GATE_PASS_EXAMPLE),
        str(CONSUMER_WRAPPER_EXAMPLE),
        str(CONSUMER_WRAPPER_PASS_EXAMPLE),
        "decision.decision=block",
        "decision.decision=allow_inform_only",
        "fail_on_blocked_exit_code=2",
        "raw_content_included=false",
        "consumed_raw_content=false",
        "not a provider API",
        "not a stable protocol",
    ],
}


def check_memory_state_governability_overlay_publish_pack(
    root: Path = ROOT,
    *,
    include_owner_packet_contract: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    file_status: dict[str, Any] = {}
    for rel, phrases in REQUIRED_FILES.items():
        path = root / rel
        status = {"exists": path.exists(), "missing_phrases": []}
        if path.exists():
            text = path.read_text(encoding="utf-8")
            status["missing_phrases"] = [phrase for phrase in phrases if phrase not in text]
            for phrase in status["missing_phrases"]:
                errors.append(f"{rel} missing phrase: {phrase}")
        else:
            errors.append(f"missing required file: {rel}")
        file_status[str(rel)] = status

    demo_module = _load_script(root, DEMO_SCRIPT, "memory_state_overlay_pack_demo")
    byo_smoke_module = _load_script(root, BYO_SMOKE_SCRIPT, "memory_state_overlay_pack_byo_smoke")
    gate_contract_module = _load_script(root, GATE_CONTRACT_SCRIPT, "memory_state_overlay_pack_gate_contract")
    report_contract_module = _load_script(root, REPORT_CONTRACT_SCRIPT, "memory_state_overlay_pack_report_contract")
    consumer_integration_module = _load_script(root, CONSUMER_INTEGRATION_SCRIPT, "memory_state_overlay_pack_consumer_integration")
    consumer_wrapper_contract_module = _load_script(root, CONSUMER_WRAPPER_CONTRACT_SCRIPT, "memory_state_overlay_pack_consumer_wrapper_contract")
    social_module = _load_script(root, SOCIAL_SCRIPT, "memory_state_overlay_pack_social")
    social_draft_drift_module = _load_script(root, SOCIAL_DRAFT_DRIFT_SCRIPT, "memory_state_overlay_pack_social_draft_drift")
    owner_packet_contract_module = (
        _load_script(root, OWNER_PACKET_CONTRACT_SCRIPT, "memory_state_overlay_pack_owner_packet_contract")
        if include_owner_packet_contract
        else None
    )
    fixture_demo = demo_module.build_memory_state_governability_overlay_demo(root)
    sample_input = root / SAMPLE_INPUT_DIR
    if not sample_input.exists():
        errors.append(f"missing sample input directory: {SAMPLE_INPUT_DIR}")
    demo = demo_module.build_memory_state_influence_boundary_report(
        root,
        input_path=sample_input,
    )
    report_schema = _load_json_file(root / REPORT_SCHEMA, errors)
    gate_schema = _load_json_file(root / GATE_SCHEMA, errors)
    consumer_wrapper_schema = _load_json_file(root / CONSUMER_WRAPPER_SCHEMA, errors)
    gate_example = _load_json_file(root / GATE_EXAMPLE, errors)
    gate_pass_example = _load_json_file(root / GATE_PASS_EXAMPLE, errors)
    consumer_wrapper_example = _load_json_file(root / CONSUMER_WRAPPER_EXAMPLE, errors)
    consumer_wrapper_pass_example = _load_json_file(root / CONSUMER_WRAPPER_PASS_EXAMPLE, errors)
    byo_smoke = byo_smoke_module.check_memory_state_influence_boundary_byo_smoke(root)
    gate_contract = gate_contract_module.check_memory_state_influence_boundary_integration_gate_contract(root)
    report_contract = report_contract_module.check_memory_state_influence_boundary_report_contract(root)
    consumer_integration = consumer_integration_module.check_memory_state_influence_boundary_consumer_integration(root)
    consumer_wrapper_contract = consumer_wrapper_contract_module.check_memory_state_influence_boundary_consumer_wrapper_contract(root)
    redaction_secret_leaked = False
    with TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)
        redaction_input = tmp_root / "CLAUDE.md"
        secret_value = "sk-redactiontest000000000000000"
        redaction_input.write_text(
            f"Project memory: local context may inform answers only. api_key={secret_value}\n",
            encoding="utf-8",
        )
        redaction_demo = demo_module.build_memory_state_influence_boundary_report(
            root,
            input_path=redaction_input,
            output_dir=tmp_root / "overlay",
        )
        redaction_outputs = redaction_demo.get("output_files", {})
        redaction_json = tmp_root / redaction_outputs.get("json", "")
        redaction_markdown = tmp_root / redaction_outputs.get("markdown", "")
        redaction_secret_leaked = (
            (redaction_json.exists() and secret_value in redaction_json.read_text(encoding="utf-8"))
            or (redaction_markdown.exists() and secret_value in redaction_markdown.read_text(encoding="utf-8"))
        )
    social = social_module.render_memory_state_governability_overlay_social_payload(root)
    social_draft_drift = social_draft_drift_module.check_memory_state_influence_boundary_social_draft_drift(root)
    owner_packet_contract = (
        owner_packet_contract_module.check_memory_state_influence_boundary_owner_publish_packet_contract(root)
        if owner_packet_contract_module is not None
        else {
            "status": "skipped_by_caller",
            "reason": "bundle builder skips owner packet contract to avoid circular bundle dependency",
        }
    )

    if fixture_demo.get("status") != "pass_memory_state_governability_overlay_demo":
        errors.append("fixture demo did not pass")
    if demo.get("status") != "pass_memory_state_influence_boundary_report":
        errors.append("input influence-boundary demo did not pass")
    if redaction_demo.get("status") != "pass_memory_state_influence_boundary_report":
        errors.append("redaction influence-boundary demo did not pass")
    if social.get("status") != "pass_memory_state_governability_overlay_social_payload":
        errors.append("social payload did not pass")
    if social_draft_drift.get("status") != "pass_memory_state_influence_boundary_social_draft_drift":
        errors.append("social draft drift check did not pass")
    if include_owner_packet_contract and owner_packet_contract.get("status") != "pass_memory_state_influence_boundary_owner_publish_packet_contract":
        errors.append("owner publish packet contract check did not pass")
    if byo_smoke.get("status") != "pass_memory_state_influence_boundary_byo_smoke":
        errors.append("BYO smoke check did not pass")
    if gate_contract.get("status") != "pass_memory_state_influence_boundary_integration_gate_contract":
        errors.append("integration gate contract check did not pass")
    if report_contract.get("status") != "pass_memory_state_influence_boundary_report_contract":
        errors.append("full report contract check did not pass")
    if consumer_integration.get("status") != "pass_memory_state_influence_boundary_consumer_integration":
        errors.append("consumer integration check did not pass")
    if consumer_wrapper_contract.get("status") != "pass_memory_state_influence_boundary_consumer_wrapper_contract":
        errors.append("consumer wrapper contract check did not pass")
    if fixture_demo.get("surface_count") != 5:
        errors.append("fixture demo must cover 5 source-derived surfaces")
    if demo.get("input_file_count", 0) < 9:
        errors.append("input influence-boundary demo must scan the repo sample directory")
    if not demo.get("influence_boundary", {}).get("blocked_refs"):
        errors.append("input influence-boundary demo must produce blocked refs for missing policy grant/action authority")
    if not demo.get("influence_boundary", {}).get("stale_or_superseded_refs"):
        errors.append("sample input must produce stale/superseded refs")
    if redaction_secret_leaked:
        errors.append("redaction demo leaked secret-like input")
    _validate_integration_gate_contract(gate_schema, gate_example, demo.get("integration_gate", {}), errors)
    _validate_report_contract(report_schema, report_contract, errors)
    _validate_consumer_wrapper_contract(consumer_wrapper_schema, consumer_wrapper_example, consumer_wrapper_pass_example, consumer_wrapper_contract, errors)
    if any(bool(value) for value in demo.get("claim_boundary", {}).values()):
        errors.append("demo claim boundary contains true values")
    if any(bool(value) for value in demo.get("side_effect_boundary", {}).values()):
        errors.append("demo side-effect boundary contains true values")
    if any(bool(value) for value in social.get("claim_boundary", {}).values()):
        errors.append("social claim boundary contains true values")
    if any(bool(value) for value in social.get("side_effect_boundary", {}).values()):
        errors.append("social side-effect boundary contains true values")
    if any(count > 280 for count in social.get("x", {}).get("tweet_character_counts", [])):
        errors.append("X thread contains a tweet over 280 characters")
    if byo_smoke.get("blocked_gate_returncode") != 2 or byo_smoke.get("pass_gate_returncode") != 0:
        errors.append("BYO smoke gate exit codes did not match blocked/pass expectations")
    if byo_smoke.get("external_absolute_path_leaked") or byo_smoke.get("secret_like_content_leaked"):
        errors.append("BYO smoke leaked external absolute path or secret-like content")
    _validate_consumer_integration(consumer_integration, errors)

    return {
        "schema_id": "ctxvault.memory-state-governability-overlay-publish-pack-check/v0",
        "status": "pass_memory_state_governability_overlay_publish_pack" if not errors else "fail_memory_state_governability_overlay_publish_pack",
        "milestone": "Local Memory State Influence Boundary Report",
        "public_page": PUBLIC_URL,
        "demo_command": DEMO_COMMAND,
        "bring_your_own_command": BYO_COMMAND,
        "fixture_demo_command": FIXTURE_DEMO_COMMAND,
        "sample_input_dir": str(SAMPLE_INPUT_DIR),
        "pack_root": str(PACK_REL),
        "file_status": file_status,
        "demo_status": demo.get("status"),
        "redaction_demo_status": redaction_demo.get("status"),
        "fixture_demo_status": fixture_demo.get("status"),
        "social_payload_status": social.get("status"),
        "social_draft_drift_status": social_draft_drift.get("status"),
        "social_draft_payload_json_drift_status": social_draft_drift.get("payload_json_drift_status"),
        "social_draft_payload_markdown_drift_status": social_draft_drift.get("payload_markdown_drift_status"),
        "social_draft_hn_drift_status": social_draft_drift.get("hn_draft_drift_status"),
        "social_draft_linkedin_drift_status": social_draft_drift.get("linkedin_draft_drift_status"),
        "social_draft_x_thread_drift_status": social_draft_drift.get("x_thread_drift_status"),
        "social_draft_old_positioning_status": social_draft_drift.get("old_positioning_status"),
        "owner_packet_contract_status": owner_packet_contract.get("status"),
        "owner_packet_contract_bundle_sha256": owner_packet_contract.get("publication_bundle_sha256"),
        "owner_packet_contract_publication_file_count": owner_packet_contract.get("publication_file_count"),
        "byo_smoke_status": byo_smoke.get("status"),
        "byo_blocked_gate_returncode": byo_smoke.get("blocked_gate_returncode"),
        "byo_pass_gate_returncode": byo_smoke.get("pass_gate_returncode"),
        "integration_gate_schema_status": "checked" if gate_schema else "missing_or_invalid",
        "report_schema_status": "checked" if report_schema else "missing_or_invalid",
        "consumer_wrapper_schema_status": "checked" if consumer_wrapper_schema else "missing_or_invalid",
        "integration_gate_example_status": "checked" if gate_example else "missing_or_invalid",
        "integration_gate_pass_example_status": "checked" if gate_pass_example else "missing_or_invalid",
        "consumer_wrapper_example_status": "checked" if consumer_wrapper_example else "missing_or_invalid",
        "consumer_wrapper_pass_example_status": "checked" if consumer_wrapper_pass_example else "missing_or_invalid",
        "integration_gate_contract_status": gate_contract.get("status"),
        "report_contract_status": report_contract.get("status"),
        "report_contract_raw_content_boundary_status": report_contract.get("raw_content_boundary_status"),
        "report_contract_integration_gate_embedded_status": report_contract.get("integration_gate_embedded_status"),
        "consumer_integration_status": consumer_integration.get("status"),
        "consumer_blocked_decision": consumer_integration.get("blocked_decision", {}).get("decision"),
        "consumer_pass_decision": consumer_integration.get("pass_decision", {}).get("decision"),
        "consumer_wrapper_contract_status": consumer_wrapper_contract.get("status"),
        "consumer_wrapper_contract_schema_status": consumer_wrapper_contract.get("schema_contract_status"),
        "consumer_wrapper_contract_example_drift_status": consumer_wrapper_contract.get("example_drift_status"),
        "consumer_wrapper_contract_blocked_decision": consumer_wrapper_contract.get("blocked_decision"),
        "consumer_wrapper_contract_pass_decision": consumer_wrapper_contract.get("pass_decision"),
        "input_file_count": demo.get("input_file_count"),
        "redaction_input_file_count": redaction_demo.get("input_file_count"),
        "surface_count": fixture_demo.get("surface_count"),
        "scale_profile_counts": fixture_demo.get("scale_profile_counts", {}),
        "x_tweet_count": social.get("x", {}).get("tweet_count"),
        "x_tweet_character_counts": social.get("x", {}).get("tweet_character_counts", []),
        "claim_boundary": demo.get("claim_boundary", {}),
        "side_effect_boundary": demo.get("side_effect_boundary", {}),
        "manual_review_required": "owner_selects_final_platform_post_only",
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _load_json_file(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path} is not valid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path} must contain a JSON object")
        return {}
    return payload


def _validate_integration_gate_contract(
    schema: dict[str, Any],
    example: dict[str, Any],
    live_gate: dict[str, Any],
    errors: list[str],
) -> None:
    required = [
        "schema_id",
        "mode",
        "passed",
        "default_exit_code",
        "fail_on_blocked_exit_code",
        "blocked_ref_count",
        "omitted_ref_count",
        "stale_or_superseded_ref_count",
        "imported_context_ref_count",
        "raw_content_included",
        "policy",
        "recommendation",
    ]
    if not schema:
        errors.append("missing integration gate schema")
        return
    if not example:
        errors.append("missing integration gate example")
        return
    if not live_gate:
        errors.append("sample report missing integration_gate")
        return
    if schema.get("additionalProperties") is not False:
        errors.append("integration gate schema must set additionalProperties=false")
    if schema.get("description", "").find("not a stable protocol") == -1:
        errors.append("integration gate schema must deny stable protocol claim")
    if schema.get("properties", {}).get("schema_id", {}).get("const") != "ctxvault.memory-state-influence-boundary-integration-gate/v0":
        errors.append("integration gate schema has unexpected schema_id const")
    if schema.get("properties", {}).get("raw_content_included", {}).get("const") is not False:
        errors.append("integration gate schema must require raw_content_included=false")
    missing_required = [field for field in required if field not in schema.get("required", [])]
    if missing_required:
        errors.append(f"integration gate schema missing required fields: {', '.join(missing_required)}")
    missing_example = [field for field in required if field not in example]
    if missing_example:
        errors.append(f"integration gate example missing fields: {', '.join(missing_example)}")
    unexpected_example = sorted(set(example) - set(required))
    if unexpected_example:
        errors.append(f"integration gate example has unexpected fields: {', '.join(unexpected_example)}")
    for field in required:
        if field in example and field in live_gate and example[field] != live_gate[field]:
            errors.append(f"integration gate example drifted from sample report: {field}")


def _validate_report_contract(
    schema: dict[str, Any],
    contract: dict[str, Any],
    errors: list[str],
) -> None:
    if not schema:
        errors.append("missing full report schema")
        return
    if schema.get("additionalProperties") is not False:
        errors.append("full report schema must set top-level additionalProperties=false")
    if schema.get("description", "").find("not a stable protocol") == -1:
        errors.append("full report schema must deny stable protocol claim")
    if schema.get("properties", {}).get("schema_id", {}).get("const") != "ctxvault.memory-state-influence-boundary-report/v0":
        errors.append("full report schema has unexpected schema_id const")
    if schema.get("properties", {}).get("mode", {}).get("const") != "user_input":
        errors.append("full report schema must require user_input mode")
    scan_limits = schema.get("$defs", {}).get("scan_limits", {})
    if scan_limits.get("properties", {}).get("raw_content_included", {}).get("const") is not False:
        errors.append("full report schema must require scan_limits.raw_content_included=false")
    input_file = schema.get("$defs", {}).get("input_file", {})
    if input_file.get("properties", {}).get("raw_content_included", {}).get("const") is not False:
        errors.append("full report schema must require input_files[].raw_content_included=false")
    if contract.get("schema_contract_status") != "pass":
        errors.append(f"full report schema contract failed: {contract.get('schema_contract_status')}")
    if contract.get("report_contract_status") != "pass":
        errors.append(f"full report contract failed: {contract.get('report_contract_status')}")
    if contract.get("raw_content_boundary_status") != "pass":
        errors.append(f"full report raw-content boundary failed: {contract.get('raw_content_boundary_status')}")
    if contract.get("integration_gate_embedded_status") != "pass":
        errors.append(f"full report embedded gate failed: {contract.get('integration_gate_embedded_status')}")


def _validate_consumer_integration(consumer: dict[str, Any], errors: list[str]) -> None:
    if consumer.get("status") != "pass_memory_state_influence_boundary_consumer_integration":
        errors.append(f"consumer integration status failed: {consumer.get('status')}")
        return
    if consumer.get("blocked_gate_returncode") != 2:
        errors.append(f"consumer blocked gate returncode unexpected: {consumer.get('blocked_gate_returncode')}")
    if consumer.get("pass_gate_returncode") != 0:
        errors.append(f"consumer pass gate returncode unexpected: {consumer.get('pass_gate_returncode')}")
    if consumer.get("blocked_decision", {}).get("decision") != "block":
        errors.append(f"consumer blocked decision unexpected: {consumer.get('blocked_decision', {}).get('decision')}")
    if consumer.get("pass_decision", {}).get("decision") != "allow_inform_only":
        errors.append(f"consumer pass decision unexpected: {consumer.get('pass_decision', {}).get('decision')}")
    if consumer.get("external_absolute_path_leaked") or consumer.get("secret_like_content_leaked"):
        errors.append("consumer integration leaked external absolute path or secret-like content")
    if consumer.get("raw_content_included"):
        errors.append("consumer integration included raw content")


def _validate_consumer_wrapper_contract(
    schema: dict[str, Any],
    example: dict[str, Any],
    pass_example: dict[str, Any],
    contract: dict[str, Any],
    errors: list[str],
) -> None:
    if not schema:
        errors.append("missing consumer wrapper schema")
        return
    if schema.get("additionalProperties") is not False:
        errors.append("consumer wrapper schema must set top-level additionalProperties=false")
    if schema.get("description", "").find("not a stable protocol") == -1:
        errors.append("consumer wrapper schema must deny stable protocol claim")
    if schema.get("properties", {}).get("schema_id", {}).get("const") != "ctxvault.memory-state-influence-boundary-consumer-wrapper-example/v0":
        errors.append("consumer wrapper schema has unexpected schema_id const")
    if not example:
        errors.append("missing consumer wrapper blocked example")
    if not pass_example:
        errors.append("missing consumer wrapper pass example")
    if example.get("decision", {}).get("decision") != "block":
        errors.append(f"consumer wrapper blocked example decision unexpected: {example.get('decision', {}).get('decision')}")
    if pass_example.get("decision", {}).get("decision") != "allow_inform_only":
        errors.append(f"consumer wrapper pass example decision unexpected: {pass_example.get('decision', {}).get('decision')}")
    if contract.get("status") != "pass_memory_state_influence_boundary_consumer_wrapper_contract":
        errors.append(f"consumer wrapper contract status failed: {contract.get('status')}")
    if contract.get("schema_contract_status") != "pass":
        errors.append(f"consumer wrapper schema contract failed: {contract.get('schema_contract_status')}")
    if contract.get("example_drift_status") != "pass":
        errors.append(f"consumer wrapper example drift failed: {contract.get('example_drift_status')}")
    if contract.get("decision_status") != "pass":
        errors.append(f"consumer wrapper decision contract failed: {contract.get('decision_status')}")
    if contract.get("raw_content_boundary_status") != "pass":
        errors.append(f"consumer wrapper raw-content boundary failed: {contract.get('raw_content_boundary_status')}")
    if contract.get("blocked_decision") != "block":
        errors.append(f"consumer wrapper blocked decision unexpected: {contract.get('blocked_decision')}")
    if contract.get("pass_decision") != "allow_inform_only":
        errors.append(f"consumer wrapper pass decision unexpected: {contract.get('pass_decision')}")


def _load_script(root: Path, rel_path: Path, module_name: str) -> Any:
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Memory State Governability Overlay publish pack readiness.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-owner-packet-contract", action="store_true")
    args = parser.parse_args()
    result = check_memory_state_governability_overlay_publish_pack(
        args.root,
        include_owner_packet_contract=not args.skip_owner_packet_contract,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_governability_overlay_publish_pack" else 1


if __name__ == "__main__":
    raise SystemExit(main())
