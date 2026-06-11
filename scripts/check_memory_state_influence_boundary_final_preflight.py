#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_INPUT = "examples/memory-state-influence-boundary/"
CLEAN_INPUT = "examples/memory-state-influence-boundary/state-policy.toml"
PUBLIC_PAGE = "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html"
CommandRunner = Callable[..., subprocess.CompletedProcess[str]]

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
    "external_runtime_or_adapter_executed": False,
    "memory_backend_written": False,
    "target_file_written": False,
    "sarif_uploaded": False,
    "public_release_created": False,
    "outreach_performed": False,
}

PY_COMPILE_FILES = [
    "scripts/run_memory_state_influence_boundary_report.py",
    "scripts/run_memory_state_governability_overlay_demo.py",
    "scripts/check_memory_state_influence_boundary_byo_smoke.py",
    "scripts/check_memory_state_influence_boundary_integration_gate_contract.py",
    "scripts/check_memory_state_influence_boundary_report_contract.py",
    "scripts/check_memory_state_influence_boundary_consumer_integration.py",
    "scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py",
    "scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py",
    "scripts/check_memory_state_influence_boundary_release_distinctness.py",
    "scripts/render_memory_state_governability_overlay_social_payload.py",
    "scripts/check_memory_state_influence_boundary_social_draft_drift.py",
    "scripts/check_memory_state_governability_overlay_publish_pack.py",
    "scripts/check_memory_state_influence_boundary_final_preflight.py",
    "scripts/check_memory_state_influence_boundary_public_checkout_readiness.py",
    "scripts/check_memory_state_influence_boundary_live_publication.py",
    "scripts/build_memory_state_influence_boundary_publication_bundle.py",
    "scripts/materialize_memory_state_influence_boundary_publication_bundle.py",
    "scripts/render_memory_state_influence_boundary_owner_publish_packet.py",
    "scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
    "scripts/render_memory_state_influence_boundary_publish_command_envelope.py",
    "scripts/publish_memory_state_influence_boundary_public_patch.py",
    "tests/test_memory_state_governability_overlay_demo.py",
]


def check_memory_state_influence_boundary_final_preflight(
    root: Path = ROOT,
    *,
    runner: CommandRunner = subprocess.run,
    include_unittests: bool = True,
    include_publisher_smoke: bool = True,
) -> dict[str, Any]:
    root = Path(root).resolve()
    issues: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}

    json_specs = [
        (
            "sample_input_report",
            [
                sys.executable,
                "scripts/run_memory_state_influence_boundary_report.py",
                "--input",
                SAMPLE_INPUT,
            ],
            "pass_memory_state_influence_boundary_report",
        ),
        (
            "integration_gate_contract",
            [sys.executable, "scripts/check_memory_state_influence_boundary_integration_gate_contract.py"],
            "pass_memory_state_influence_boundary_integration_gate_contract",
        ),
        (
            "report_contract",
            [sys.executable, "scripts/check_memory_state_influence_boundary_report_contract.py"],
            "pass_memory_state_influence_boundary_report_contract",
        ),
        (
            "consumer_integration",
            [sys.executable, "scripts/check_memory_state_influence_boundary_consumer_integration.py"],
            "pass_memory_state_influence_boundary_consumer_integration",
        ),
        (
            "consumer_wrapper_contract",
            [sys.executable, "scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py"],
            "pass_memory_state_influence_boundary_consumer_wrapper_contract",
        ),
        (
            "consumer_wrapper_example",
            [sys.executable, "scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py"],
            "pass_memory_state_influence_boundary_consumer_wrapper_example",
        ),
        (
            "consumer_wrapper_pass_example",
            [
                sys.executable,
                "scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py",
                "--input",
                CLEAN_INPUT,
            ],
            "pass_memory_state_influence_boundary_consumer_wrapper_example",
        ),
        (
            "byo_smoke",
            [sys.executable, "scripts/check_memory_state_influence_boundary_byo_smoke.py"],
            "pass_memory_state_influence_boundary_byo_smoke",
        ),
        (
            "fixture_sample_report",
            [sys.executable, "scripts/run_memory_state_governability_overlay_demo.py"],
            "pass_memory_state_governability_overlay_demo",
        ),
        (
            "social_payload",
            [sys.executable, "scripts/render_memory_state_governability_overlay_social_payload.py"],
            "pass_memory_state_governability_overlay_social_payload",
        ),
        (
            "social_draft_drift",
            [sys.executable, "scripts/check_memory_state_influence_boundary_social_draft_drift.py"],
            "pass_memory_state_influence_boundary_social_draft_drift",
        ),
        (
            "local_publication_page",
            [sys.executable, "scripts/check_memory_state_influence_boundary_live_publication.py"],
            "pass_memory_state_influence_boundary_live_publication_check",
        ),
        (
            "publication_bundle",
            [sys.executable, "scripts/build_memory_state_influence_boundary_publication_bundle.py"],
            "pass_memory_state_influence_boundary_publication_bundle",
        ),
        (
            "publish_pack",
            [sys.executable, "scripts/check_memory_state_governability_overlay_publish_pack.py"],
            "pass_memory_state_governability_overlay_publish_pack",
        ),
        (
            "release_distinctness",
            [sys.executable, "scripts/check_memory_state_influence_boundary_release_distinctness.py"],
            "pass_memory_state_influence_boundary_release_distinctness",
        ),
        (
            "publish_command_envelope",
            [sys.executable, "scripts/render_memory_state_influence_boundary_publish_command_envelope.py"],
            "pass_memory_state_influence_boundary_publish_command_envelope",
        ),
        (
            "owner_packet_contract",
            [sys.executable, "scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py"],
            "pass_memory_state_influence_boundary_owner_publish_packet_contract",
        ),
    ]
    for check_id, command, expected_status in json_specs:
        checks[check_id] = _run_json_check(check_id, command, expected_status, root, runner, issues)

    test_modules = ["tests.test_memory_state_governability_overlay_demo"]
    if (root / "tests/test_activation_xray_scale_profile_demo.py").exists():
        test_modules.extend(
            [
                "tests.test_activation_xray_scale_profile_demo",
                "tests.test_activation_xray_canonical_trace_kernel",
            ]
        )
    if (root / "tests/test_ctxgov_conformance_packs.py").exists():
        test_modules.append("tests.test_ctxgov_conformance_packs")

    command_specs = [
        ("py_compile", [sys.executable, "-m", "py_compile", *PY_COMPILE_FILES]),
        ("git_diff_check", ["git", "diff", "--check"]),
    ]
    if include_unittests:
        command_specs.insert(0, ("memory_state_unittests", [sys.executable, "-m", "unittest", *test_modules]))
    else:
        checks["memory_state_unittests"] = {
            "status": "skipped_by_caller",
            "reason": "caller requested include_unittests=false to avoid self-recursive test execution",
        }
    if (root / "scripts/check_docs_information_architecture.py").exists():
        command_specs.insert(
            2,
            ("docs_information_architecture", [sys.executable, "scripts/check_docs_information_architecture.py"]),
        )
    else:
        checks["docs_information_architecture"] = _skipped_optional("scripts/check_docs_information_architecture.py")

    for check_id, command in command_specs:
        checks[check_id] = _run_plain_check(check_id, command, root, runner, issues)

    sample_payload = checks.get("sample_input_report", {}).get("payload", {})
    publish_pack = checks.get("publish_pack", {}).get("payload", {})
    gate_contract = checks.get("integration_gate_contract", {}).get("payload", {})
    report_contract = checks.get("report_contract", {}).get("payload", {})
    consumer_integration = checks.get("consumer_integration", {}).get("payload", {})
    consumer_wrapper_contract = checks.get("consumer_wrapper_contract", {}).get("payload", {})
    consumer_wrapper_example = checks.get("consumer_wrapper_example", {}).get("payload", {})
    consumer_wrapper_pass_example = checks.get("consumer_wrapper_pass_example", {}).get("payload", {})
    release_distinctness = checks.get("release_distinctness", {}).get("payload", {})
    byo_smoke = checks.get("byo_smoke", {}).get("payload", {})
    publication_bundle = checks.get("publication_bundle", {}).get("payload", {})
    publish_envelope = checks.get("publish_command_envelope", {}).get("payload", {})
    owner_packet_contract = checks.get("owner_packet_contract", {}).get("payload", {})
    social_draft_drift = checks.get("social_draft_drift", {}).get("payload", {})
    _validate_sample_payload(sample_payload, issues)
    if publish_pack.get("input_file_count", 0) < 9:
        issues.append(_issue("publish_pack_sample_too_small", "publish_pack.input_file_count", publish_pack.get("input_file_count")))
    if publish_pack.get("redaction_demo_status") != "pass_memory_state_influence_boundary_report":
        issues.append(_issue("redaction_demo_failed", "publish_pack.redaction_demo_status", publish_pack.get("redaction_demo_status")))
    if gate_contract.get("exit_code_status") != "pass":
        issues.append(_issue("integration_gate_exit_code_failed", "integration_gate_contract.exit_code_status", gate_contract.get("exit_code_status")))
    if gate_contract.get("example_drift_status") != "pass":
        issues.append(_issue("integration_gate_example_drift", "integration_gate_contract.example_drift_status", gate_contract.get("example_drift_status")))
    if report_contract.get("report_contract_status") != "pass":
        issues.append(_issue("report_contract_failed", "report_contract.report_contract_status", report_contract.get("report_contract_status")))
    if report_contract.get("raw_content_boundary_status") != "pass":
        issues.append(
            _issue(
                "report_contract_raw_content_boundary_failed",
                "report_contract.raw_content_boundary_status",
                report_contract.get("raw_content_boundary_status"),
            )
        )
    if report_contract.get("integration_gate_embedded_status") != "pass":
        issues.append(
            _issue(
                "report_contract_embedded_gate_failed",
                "report_contract.integration_gate_embedded_status",
                report_contract.get("integration_gate_embedded_status"),
            )
        )
    _validate_consumer_integration_payload(consumer_integration, issues)
    _validate_consumer_wrapper_contract_payload(consumer_wrapper_contract, issues)
    _validate_consumer_wrapper_example_payload(
        consumer_wrapper_example,
        issues,
        check_id="consumer_wrapper_example",
        expected_decision="block",
        expected_reason="blocked_refs_present",
        expected_gate_returncode=2,
    )
    _validate_consumer_wrapper_example_payload(
        consumer_wrapper_pass_example,
        issues,
        check_id="consumer_wrapper_pass_example",
        expected_decision="allow_inform_only",
        expected_reason="gate_passed_no_blocked_refs",
        expected_gate_returncode=0,
    )
    if release_distinctness.get("status") != "pass_memory_state_influence_boundary_release_distinctness":
        issues.append(
            _issue(
                "release_distinctness_failed",
                "release_distinctness.status",
                release_distinctness.get("status"),
            )
        )
    if social_draft_drift.get("old_positioning_status") != "pass":
        issues.append(
            _issue(
                "social_draft_old_positioning_failed",
                "social_draft_drift.old_positioning_status",
                social_draft_drift.get("old_positioning_hits"),
            )
        )
    _validate_byo_smoke_payload(byo_smoke, issues)
    if publication_bundle.get("publication_file_count", 0) < 25:
        issues.append(_issue("publication_bundle_too_small", "publication_bundle.publication_file_count", publication_bundle.get("publication_file_count")))
    if publish_envelope.get("publication_bundle_sha256") != publication_bundle.get("publication_bundle_sha256"):
        issues.append(
            _issue(
                "publish_envelope_bundle_digest_mismatch",
                "publish_command_envelope.publication_bundle_sha256",
                {
                    "bundle": publication_bundle.get("publication_bundle_sha256"),
                    "envelope": publish_envelope.get("publication_bundle_sha256"),
                },
            )
        )
    if owner_packet_contract.get("publication_bundle_sha256") != publication_bundle.get("publication_bundle_sha256"):
        issues.append(
            _issue(
                "owner_packet_contract_bundle_digest_mismatch",
                "owner_packet_contract.publication_bundle_sha256",
                {
                    "bundle": publication_bundle.get("publication_bundle_sha256"),
                    "owner_packet_contract": owner_packet_contract.get("publication_bundle_sha256"),
                },
            )
        )
    if any(bool(value) for value in CLAIM_BOUNDARY.values()):
        issues.append(_issue("claim_boundary_true", "claim_boundary", CLAIM_BOUNDARY))
    if any(bool(value) for value in SIDE_EFFECT_BOUNDARY.values()):
        issues.append(_issue("side_effect_boundary_true", "side_effect_boundary", SIDE_EFFECT_BOUNDARY))

    checks["publication_bundle_materialization_smoke"] = _run_materialization_smoke_check(
        root,
        runner,
        issues,
        expected_file_count=publication_bundle.get("publication_file_count", 0),
    )
    if include_publisher_smoke:
        checks["public_patch_publisher_dry_run_smoke"] = _run_publisher_dry_run_smoke_check(root, runner, issues)
        smoke_check_count = 2
    else:
        checks["public_patch_publisher_dry_run_smoke"] = {
            "status": "skipped_by_caller",
            "reason": "caller requested include_publisher_smoke=false to avoid self-recursive publisher preflight",
        }
        smoke_check_count = 1

    status = "pass_memory_state_influence_boundary_final_preflight" if not issues else "fail_memory_state_influence_boundary_final_preflight"
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-final-preflight/v0",
        "status": status,
        "go_no_go": "go_local_ready_external_publish_pending" if not issues else "no_go_fix_errors_first",
        "milestone": "Local Memory State Influence Boundary Report",
        "public_page": PUBLIC_PAGE,
        "fresh_checkout_commands": [
            "git clone https://github.com/ctxgov/ctxgov.git",
            "cd ctxgov",
            f"python3 scripts/run_memory_state_influence_boundary_report.py --input {SAMPLE_INPUT}",
        ],
        "bring_your_own_commands": [
            "python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md",
            "python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/",
        ],
        "sample_input_file_count": sample_payload.get("input_file_count"),
        "sample_blocked_ref_count": len(sample_payload.get("influence_boundary", {}).get("blocked_refs", [])),
        "sample_stale_ref_count": len(sample_payload.get("influence_boundary", {}).get("stale_or_superseded_refs", [])),
        "publish_pack_status": publish_pack.get("status"),
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
        "consumer_wrapper_example_status": consumer_wrapper_example.get("status"),
        "consumer_wrapper_example_decision": consumer_wrapper_example.get("decision", {}).get("decision"),
        "consumer_wrapper_example_gate_returncode": consumer_wrapper_example.get("gate_returncode"),
        "consumer_wrapper_block_example_status": consumer_wrapper_example.get("status"),
        "consumer_wrapper_block_example_decision": consumer_wrapper_example.get("decision", {}).get("decision"),
        "consumer_wrapper_block_example_gate_returncode": consumer_wrapper_example.get("gate_returncode"),
        "consumer_wrapper_pass_example_status": consumer_wrapper_pass_example.get("status"),
        "consumer_wrapper_pass_example_decision": consumer_wrapper_pass_example.get("decision", {}).get("decision"),
        "consumer_wrapper_pass_example_gate_returncode": consumer_wrapper_pass_example.get("gate_returncode"),
        "release_distinctness_status": release_distinctness.get("status"),
        "release_distinctness_warning_count": release_distinctness.get("warning_count"),
        "byo_smoke_status": byo_smoke.get("status"),
        "byo_blocked_gate_returncode": byo_smoke.get("blocked_gate_returncode"),
        "byo_pass_gate_returncode": byo_smoke.get("pass_gate_returncode"),
        "publication_bundle_status": publication_bundle.get("status"),
        "publication_bundle_sha256": publication_bundle.get("publication_bundle_sha256"),
        "publication_file_count": publication_bundle.get("publication_file_count"),
        "materialized_copied_file_count": checks["publication_bundle_materialization_smoke"].get("payload", {}).get("copied_file_count"),
        "publish_command_envelope_status": publish_envelope.get("status"),
        "owner_packet_contract_status": owner_packet_contract.get("status"),
        "owner_packet_contract_bundle_sha256": owner_packet_contract.get("publication_bundle_sha256"),
        "owner_packet_contract_publication_file_count": owner_packet_contract.get("publication_file_count"),
        "owner_packet_contract_social_copy_status": owner_packet_contract.get("social_copy_status"),
        "owner_packet_contract_publish_commands_status": owner_packet_contract.get("publish_commands_status"),
        "social_payload_status": checks.get("social_payload", {}).get("payload", {}).get("status"),
        "social_draft_drift_status": social_draft_drift.get("status"),
        "social_draft_hn_drift_status": social_draft_drift.get("hn_draft_drift_status"),
        "social_draft_linkedin_drift_status": social_draft_drift.get("linkedin_draft_drift_status"),
        "social_draft_x_thread_drift_status": social_draft_drift.get("x_thread_drift_status"),
        "social_draft_old_positioning_status": social_draft_drift.get("old_positioning_status"),
        "x_tweet_character_counts": checks.get("social_payload", {}).get("payload", {}).get("x", {}).get("tweet_character_counts", []),
        "command_count": len(json_specs) + len(command_specs) + smoke_check_count,
        "checks": checks,
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "side_effect_boundary": dict(SIDE_EFFECT_BOUNDARY),
        "manual_review_required": "owner_confirms_external_publish_and_social_copy_only",
        "required_external_actions": [
            "commit and push the prepared public repo patch",
            "wait for GitHub Pages to deploy the page",
            "run python3 scripts/check_memory_state_influence_boundary_live_publication.py --live after the page is deployed",
            "manually post the selected HN/X/LinkedIn copy after the page is live",
        ],
        "publication_executed": False,
        "outreach_performed": False,
        "issue_count": len(issues),
        "issues": issues,
    }


def _validate_sample_payload(payload: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if payload.get("input_kind") != "directory":
        issues.append(_issue("sample_input_not_directory", "sample_input_report.input_kind", payload.get("input_kind")))
    if payload.get("input_file_count", 0) < 9:
        issues.append(_issue("sample_input_file_count_too_small", "sample_input_report.input_file_count", payload.get("input_file_count")))
    boundary = payload.get("influence_boundary", {})
    if not boundary.get("blocked_refs"):
        issues.append(_issue("sample_missing_blocked_refs", "sample_input_report.influence_boundary.blocked_refs", boundary.get("blocked_refs")))
    if not boundary.get("stale_or_superseded_refs"):
        issues.append(_issue("sample_missing_stale_refs", "sample_input_report.influence_boundary.stale_or_superseded_refs", boundary.get("stale_or_superseded_refs")))
    if not boundary.get("imported_context_refs"):
        issues.append(_issue("sample_missing_imported_refs", "sample_input_report.influence_boundary.imported_context_refs", boundary.get("imported_context_refs")))
    raw_flags = [file_report.get("raw_content_included") for file_report in payload.get("input_files", [])]
    if any(bool(flag) for flag in raw_flags):
        issues.append(_issue("sample_raw_content_included", "sample_input_report.input_files.raw_content_included", raw_flags))
    if any(bool(value) for value in payload.get("claim_boundary", {}).values()):
        issues.append(_issue("sample_claim_boundary_true", "sample_input_report.claim_boundary", payload.get("claim_boundary")))
    if any(bool(value) for value in payload.get("side_effect_boundary", {}).values()):
        issues.append(_issue("sample_side_effect_boundary_true", "sample_input_report.side_effect_boundary", payload.get("side_effect_boundary")))
    scan_limits = payload.get("scan_limits", {})
    if not isinstance(scan_limits.get("max_skipped_input_records"), int) or scan_limits.get("max_skipped_input_records", 0) <= 0:
        issues.append(_issue("sample_missing_skipped_input_record_limit", "sample_input_report.scan_limits.max_skipped_input_records", scan_limits.get("max_skipped_input_records")))
    if "skipped_input_record_count" not in payload:
        issues.append(_issue("sample_missing_skipped_input_record_count", "sample_input_report.skipped_input_record_count", None))
    if "skipped_input_records_truncated" not in payload:
        issues.append(_issue("sample_missing_skipped_input_truncation_flag", "sample_input_report.skipped_input_records_truncated", None))


def _validate_byo_smoke_payload(payload: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if payload.get("status") != "pass_memory_state_influence_boundary_byo_smoke":
        issues.append(_issue("byo_smoke_failed", "byo_smoke.status", payload.get("status")))
    if payload.get("input_kind") != "directory":
        issues.append(_issue("byo_smoke_not_directory", "byo_smoke.input_kind", payload.get("input_kind")))
    if payload.get("input_file_count") != 2:
        issues.append(_issue("byo_smoke_input_file_count", "byo_smoke.input_file_count", payload.get("input_file_count")))
    if payload.get("skipped_input_count") != 1:
        issues.append(_issue("byo_smoke_skipped_input_count", "byo_smoke.skipped_input_count", payload.get("skipped_input_count")))
    if payload.get("blocked_ref_count", 0) < 1:
        issues.append(_issue("byo_smoke_missing_blocked_ref", "byo_smoke.blocked_ref_count", payload.get("blocked_ref_count")))
    if payload.get("inform_only_allowed_ref_count", 0) < 1:
        issues.append(
            _issue(
                "byo_smoke_missing_inform_only_ref",
                "byo_smoke.inform_only_allowed_ref_count",
                payload.get("inform_only_allowed_ref_count"),
            )
        )
    if payload.get("blocked_gate_returncode") != 2:
        issues.append(_issue("byo_smoke_blocked_gate_returncode", "byo_smoke.blocked_gate_returncode", payload.get("blocked_gate_returncode")))
    if payload.get("pass_gate_returncode") != 0:
        issues.append(_issue("byo_smoke_pass_gate_returncode", "byo_smoke.pass_gate_returncode", payload.get("pass_gate_returncode")))
    if payload.get("external_absolute_path_leaked"):
        issues.append(_issue("byo_smoke_absolute_path_leak", "byo_smoke.external_absolute_path_leaked", True))
    if payload.get("secret_like_content_leaked"):
        issues.append(_issue("byo_smoke_secret_leak", "byo_smoke.secret_like_content_leaked", True))
    if payload.get("raw_content_included"):
        issues.append(_issue("byo_smoke_raw_content_included", "byo_smoke.raw_content_included", True))


def _validate_consumer_integration_payload(payload: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if payload.get("status") != "pass_memory_state_influence_boundary_consumer_integration":
        issues.append(_issue("consumer_integration_failed", "consumer_integration.status", payload.get("status")))
    if payload.get("blocked_gate_returncode") != 2:
        issues.append(
            _issue(
                "consumer_integration_blocked_gate_returncode",
                "consumer_integration.blocked_gate_returncode",
                payload.get("blocked_gate_returncode"),
            )
        )
    if payload.get("pass_gate_returncode") != 0:
        issues.append(
            _issue(
                "consumer_integration_pass_gate_returncode",
                "consumer_integration.pass_gate_returncode",
                payload.get("pass_gate_returncode"),
            )
        )
    if payload.get("blocked_decision", {}).get("decision") != "block":
        issues.append(
            _issue(
                "consumer_integration_blocked_decision",
                "consumer_integration.blocked_decision.decision",
                payload.get("blocked_decision", {}).get("decision"),
            )
        )
    if payload.get("pass_decision", {}).get("decision") != "allow_inform_only":
        issues.append(
            _issue(
                "consumer_integration_pass_decision",
                "consumer_integration.pass_decision.decision",
                payload.get("pass_decision", {}).get("decision"),
            )
        )
    for field in (
        "blocked_report_contract_status",
        "blocked_raw_content_boundary_status",
        "blocked_embedded_gate_status",
        "pass_report_contract_status",
        "pass_raw_content_boundary_status",
        "pass_embedded_gate_status",
    ):
        if payload.get(field) != "pass":
            issues.append(_issue("consumer_integration_contract_failed", f"consumer_integration.{field}", payload.get(field)))
    if payload.get("external_absolute_path_leaked"):
        issues.append(_issue("consumer_integration_absolute_path_leak", "consumer_integration.external_absolute_path_leaked", True))
    if payload.get("secret_like_content_leaked"):
        issues.append(_issue("consumer_integration_secret_leak", "consumer_integration.secret_like_content_leaked", True))
    if payload.get("raw_content_included"):
        issues.append(_issue("consumer_integration_raw_content_included", "consumer_integration.raw_content_included", True))


def _validate_consumer_wrapper_contract_payload(payload: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    if payload.get("status") != "pass_memory_state_influence_boundary_consumer_wrapper_contract":
        issues.append(_issue("consumer_wrapper_contract_failed", "consumer_wrapper_contract.status", payload.get("status")))
    for field in (
        "schema_contract_status",
        "example_drift_status",
        "decision_status",
        "raw_content_boundary_status",
    ):
        if payload.get(field) != "pass":
            issues.append(_issue("consumer_wrapper_contract_field_failed", f"consumer_wrapper_contract.{field}", payload.get(field)))
    if payload.get("blocked_decision") != "block":
        issues.append(_issue("consumer_wrapper_contract_blocked_decision", "consumer_wrapper_contract.blocked_decision", payload.get("blocked_decision")))
    if payload.get("pass_decision") != "allow_inform_only":
        issues.append(_issue("consumer_wrapper_contract_pass_decision", "consumer_wrapper_contract.pass_decision", payload.get("pass_decision")))
    if payload.get("blocked_gate_returncode") != 2:
        issues.append(_issue("consumer_wrapper_contract_blocked_gate_returncode", "consumer_wrapper_contract.blocked_gate_returncode", payload.get("blocked_gate_returncode")))
    if payload.get("pass_gate_returncode") != 0:
        issues.append(_issue("consumer_wrapper_contract_pass_gate_returncode", "consumer_wrapper_contract.pass_gate_returncode", payload.get("pass_gate_returncode")))
    for side_effect_field in (
        "publication_executed",
        "outreach_performed",
    ):
        if payload.get(side_effect_field):
            issues.append(_issue("consumer_wrapper_contract_side_effect_true", f"consumer_wrapper_contract.{side_effect_field}", payload.get(side_effect_field)))


def _validate_consumer_wrapper_example_payload(
    payload: dict[str, Any],
    issues: list[dict[str, Any]],
    *,
    check_id: str,
    expected_decision: str,
    expected_reason: str,
    expected_gate_returncode: int,
) -> None:
    if payload.get("status") != "pass_memory_state_influence_boundary_consumer_wrapper_example":
        issues.append(_issue(f"{check_id}_failed", f"{check_id}.status", payload.get("status")))
    if payload.get("decision", {}).get("decision") != expected_decision:
        issues.append(
            _issue(
                f"{check_id}_decision",
                f"{check_id}.decision.decision",
                {
                    "expected": expected_decision,
                    "observed": payload.get("decision", {}).get("decision"),
                },
            )
        )
    if payload.get("decision", {}).get("reason") != expected_reason:
        issues.append(
            _issue(
                f"{check_id}_reason",
                f"{check_id}.decision.reason",
                {
                    "expected": expected_reason,
                    "observed": payload.get("decision", {}).get("reason"),
                },
            )
        )
    if payload.get("gate_returncode") != expected_gate_returncode:
        issues.append(
            _issue(
                f"{check_id}_gate_returncode",
                f"{check_id}.gate_returncode",
                {
                    "expected": expected_gate_returncode,
                    "observed": payload.get("gate_returncode"),
                },
            )
        )
    if payload.get("gate", {}).get("raw_content_included") is not False:
        issues.append(_issue(f"{check_id}_raw_content_included", f"{check_id}.gate.raw_content_included", payload.get("gate", {}).get("raw_content_included")))
    if payload.get("decision", {}).get("consumed_raw_content"):
        issues.append(_issue(f"{check_id}_consumed_raw_content", f"{check_id}.decision.consumed_raw_content", True))
    for side_effect_field in (
        "publication_executed",
        "outreach_performed",
    ):
        if payload.get(side_effect_field):
            issues.append(_issue(f"{check_id}_side_effect_true", f"{check_id}.{side_effect_field}", payload.get(side_effect_field)))


def _run_json_check(
    check_id: str,
    command: list[str],
    expected_status: str,
    root: Path,
    runner: CommandRunner,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    completed = _run(command, root, runner)
    receipt = _command_receipt(command, completed)
    if completed.returncode != 0:
        issues.append(_issue("command_failed", check_id, _command_error(completed)))
        return {**receipt, "status": "fail", "payload": {}}
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        issues.append(_issue("command_non_json", check_id, str(exc)))
        return {**receipt, "status": "fail", "payload": {}}
    if not isinstance(payload, dict):
        issues.append(_issue("command_json_not_object", check_id, type(payload).__name__))
        return {**receipt, "status": "fail", "payload": {}}
    observed_status = payload.get("status")
    if observed_status != expected_status:
        issues.append(_issue("unexpected_status", check_id, {"expected": expected_status, "observed": observed_status}))
    return {
        **receipt,
        "status": "pass" if observed_status == expected_status else "fail",
        "expected_status": expected_status,
        "observed_status": observed_status,
        "payload": _summarize_payload(payload),
    }


def _run_plain_check(
    check_id: str,
    command: list[str],
    root: Path,
    runner: CommandRunner,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    completed = _run(command, root, runner)
    receipt = _command_receipt(command, completed)
    if completed.returncode != 0:
        issues.append(_issue("command_failed", check_id, _command_error(completed)))
    return {**receipt, "status": "pass" if completed.returncode == 0 else "fail"}


def _run_materialization_smoke_check(
    root: Path,
    runner: CommandRunner,
    issues: list[dict[str, Any]],
    *,
    expected_file_count: int,
) -> dict[str, Any]:
    check_id = "publication_bundle_materialization_smoke"
    with TemporaryDirectory(prefix="ctxgov-memory-state-publication-") as tmp:
        checkout = Path(tmp) / "checkout"
        checkout.mkdir()
        init = runner(
            ["git", "init"],
            cwd=checkout,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if init.returncode != 0:
            issues.append(_issue("command_failed", f"{check_id}.git_init", _command_error(init)))
            return {
                "status": "fail",
                "git_init": _command_receipt(["git", "init"], init),
                "payload": {},
            }

        command = [
            sys.executable,
            "scripts/materialize_memory_state_influence_boundary_publication_bundle.py",
            "--checkout",
            str(checkout),
        ]
        completed = _run(command, root, runner)
        receipt = _command_receipt(command, completed)
        if completed.returncode != 0:
            issues.append(_issue("command_failed", check_id, _command_error(completed)))
            return {**receipt, "status": "fail", "payload": {}}
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            issues.append(_issue("command_non_json", check_id, str(exc)))
            return {**receipt, "status": "fail", "payload": {}}
        observed_status = payload.get("status")
        expected_status = "pass_memory_state_influence_boundary_publication_bundle_materialized"
        if observed_status != expected_status:
            issues.append(_issue("unexpected_status", check_id, {"expected": expected_status, "observed": observed_status}))
        copied_file_count = payload.get("copied_file_count", 0)
        if expected_file_count and copied_file_count != expected_file_count:
            issues.append(
                _issue(
                    "materialized_file_count_mismatch",
                    f"{check_id}.copied_file_count",
                    {"expected": expected_file_count, "observed": copied_file_count},
                )
            )
        if not payload.get("after_status_lines"):
            issues.append(_issue("materialized_checkout_has_no_status_lines", f"{check_id}.after_status_lines", []))
        for side_effect_field in (
            "commit_created",
            "push_executed",
            "publication_executed",
            "outreach_performed",
        ):
            if payload.get(side_effect_field):
                issues.append(_issue("materializer_side_effect_true", f"{check_id}.{side_effect_field}", payload.get(side_effect_field)))
        return {
            **receipt,
            "status": "pass" if observed_status == expected_status else "fail",
            "expected_status": expected_status,
            "observed_status": observed_status,
            "payload": _summarize_payload(payload),
        }


def _run_publisher_dry_run_smoke_check(
    root: Path,
    runner: CommandRunner,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    check_id = "public_patch_publisher_dry_run_smoke"
    with TemporaryDirectory(prefix="ctxgov-memory-state-publisher-") as tmp:
        checkout = Path(tmp) / "checkout"
        checkout.mkdir()
        init = runner(
            ["git", "init"],
            cwd=checkout,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if init.returncode != 0:
            issues.append(_issue("command_failed", f"{check_id}.git_init", _command_error(init)))
            return {
                "status": "fail",
                "git_init": _command_receipt(["git", "init"], init),
                "payload": {},
            }

        command = [
            sys.executable,
            "scripts/publish_memory_state_influence_boundary_public_patch.py",
            "--checkout",
            str(checkout),
        ]
        completed = _run(command, root, runner)
        receipt = _command_receipt(command, completed)
        if completed.returncode != 0:
            issues.append(_issue("command_failed", check_id, _command_error(completed)))
            return {**receipt, "status": "fail", "payload": {}}
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            issues.append(_issue("command_non_json", check_id, str(exc)))
            return {**receipt, "status": "fail", "payload": {}}
        if not isinstance(payload, dict):
            issues.append(_issue("command_json_not_object", check_id, type(payload).__name__))
            return {**receipt, "status": "fail", "payload": {}}

        expected_status = "pass_memory_state_influence_boundary_public_patch_publisher"
        observed_status = payload.get("status")
        if observed_status != expected_status:
            issues.append(_issue("unexpected_status", check_id, {"expected": expected_status, "observed": observed_status}))
        if payload.get("mode") != "dry_run":
            issues.append(_issue("publisher_smoke_not_dry_run", f"{check_id}.mode", payload.get("mode")))
        if payload.get("source_final_preflight_status") != "pass_memory_state_influence_boundary_final_preflight":
            issues.append(
                _issue(
                    "publisher_smoke_source_preflight_failed",
                    f"{check_id}.source_final_preflight_status",
                    payload.get("source_final_preflight_status"),
                )
            )
        for side_effect_field in (
            "local_checkout_write_executed",
            "commit_created",
            "push_executed",
            "publication_executed",
            "outreach_performed",
        ):
            if payload.get(side_effect_field):
                issues.append(_issue("publisher_smoke_side_effect_true", f"{check_id}.{side_effect_field}", payload.get(side_effect_field)))
        for status_field in ("checkout_status_before", "checkout_status_after"):
            checkout_status = payload.get(status_field, {})
            if checkout_status.get("returncode") != 0:
                issues.append(_issue("publisher_smoke_checkout_status_failed", f"{check_id}.{status_field}", checkout_status))
            if checkout_status.get("line_count") != 0:
                issues.append(_issue("publisher_smoke_checkout_not_clean", f"{check_id}.{status_field}.line_count", checkout_status.get("line_count")))

        return {
            **receipt,
            "status": "pass" if observed_status == expected_status else "fail",
            "expected_status": expected_status,
            "observed_status": observed_status,
            "payload": _summarize_payload(payload),
        }


def _run(command: list[str], root: Path, runner: CommandRunner) -> subprocess.CompletedProcess[str]:
    return runner(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _command_receipt(command: list[str], completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _command_error(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }


def _summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    keep = {
        "status",
        "milestone",
        "mode",
        "input_kind",
        "input_file_count",
        "skipped_input_count",
        "skipped_input_record_count",
        "skipped_input_records_truncated",
        "blocked_ref_count",
        "inform_only_allowed_ref_count",
        "omitted_ref_count",
        "imported_context_ref_count",
        "scan_limits",
        "surface_count",
        "scale_profile_counts",
        "claim_boundary",
        "side_effect_boundary",
        "influence_boundary",
        "output_files",
        "demo_command",
        "bring_your_own_command",
        "fixture_demo_status",
        "redaction_demo_status",
        "publication_bundle_sha256",
        "publication_file_count",
        "owner_packet_status",
        "owner_packet_publication_bundle_sha256",
        "owner_packet_publication_file_count",
        "owner_packet_contract_status",
        "owner_packet_contract_bundle_sha256",
        "owner_packet_contract_publication_file_count",
        "owner_packet_contract_social_copy_status",
        "owner_packet_contract_publish_commands_status",
        "owner_review_checklist_status",
        "publish_commands_status",
        "post_publish_commands_status",
        "social_copy_status",
        "rendered_output_boundary_status",
        "publish_commands",
        "pre_publish_commands",
        "post_publish_commands",
        "stdout_json_status",
        "schema_contract_status",
        "report_contract_status",
        "raw_content_boundary_status",
        "decision_status",
        "integration_gate_embedded_status",
        "blocked_report_contract_status",
        "blocked_raw_content_boundary_status",
        "blocked_embedded_gate_status",
        "pass_report_contract_status",
        "pass_raw_content_boundary_status",
        "pass_embedded_gate_status",
        "blocked_decision",
        "pass_decision",
        "decision",
        "gate",
        "gate_returncode",
        "consumer_policy",
        "command_shapes",
        "report_status",
        "consumer_decision_contract",
        "canonical_public_page",
        "distinct_from",
        "required_distinct_phrases",
        "payload_json_drift_status",
        "payload_markdown_drift_status",
        "hn_draft_drift_status",
        "linkedin_draft_drift_status",
        "x_thread_drift_status",
        "old_positioning_status",
        "old_positioning_hits",
        "hn_title",
        "hn_url",
        "x_tweet_count",
        "x_tweet_character_counts",
        "warning_count",
        "error_count",
        "example_drift_status",
        "exit_code_status",
        "gate_command_returncode",
        "expected_fail_on_blocked_exit_code",
        "blocked_gate_returncode",
        "pass_gate_returncode",
        "blocked_gate",
        "pass_gate",
        "external_absolute_path_leaked",
        "secret_like_content_leaked",
        "raw_content_included",
        "source_final_preflight_status",
        "source_final_preflight_unittests",
        "copied_file_count",
        "copied_files",
        "after_status_lines",
        "checkout_status_before",
        "checkout_status_after",
        "local_checkout_write_executed",
        "commit_created",
        "push_executed",
        "publication_executed",
        "outreach_performed",
        "warnings",
        "x",
        "errors",
    }
    return {key: payload[key] for key in keep if key in payload}


def _skipped_optional(path: str) -> dict[str, Any]:
    return {
        "status": "skipped_missing_optional_full_source_check",
        "reason": f"{path} is not present in this checkout",
    }


def _issue(issue_id: str, where: str, detail: Any) -> dict[str, Any]:
    return {"issue_id": issue_id, "where": where, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Memory State Influence Boundary final local preflight.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-unittests", action="store_true")
    parser.add_argument("--skip-publisher-smoke", action="store_true")
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_final_preflight(
        args.root,
        include_unittests=not args.skip_unittests,
        include_publisher_smoke=not args.skip_publisher_smoke,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_final_preflight" else 1


if __name__ == "__main__":
    raise SystemExit(main())
