#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import tomllib
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path("fixtures/v0.7.0-mgp-sidecar/memory-xray/memory-state-governability-overlays-20260611.json")
DEFAULT_OUTPUT_DIR = Path(".ctxvault") / "memory-state-governability-overlay"
SAMPLE_INPUT_DIR = Path("examples/memory-state-influence-boundary")
INFLUENCE_BOUNDARY_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py"
SCALE_PROFILES = {"local_single_user", "team_project", "cluster_multi_tenant"}
REQUIRED_SURFACE_FIELDS = {
    "surface_id",
    "display_name",
    "source_refs",
    "scale_profiles",
    "source_visible_state_fields",
    "governability_overlay_requirements",
    "missing_or_ctxgov_owned_proof",
    "allowed_public_phrase",
    "blocked_public_claims",
}
REQUIRED_OVERLAY_FIELDS = {
    "source_refs",
    "selected_refs",
    "omitted_refs",
    "blocked_refs",
    "stale_or_superseded_refs",
    "authority_ceiling",
    "policy_grant",
    "final_state_assertion",
    "rollback_path",
    "delete_or_forget_propagation",
    "side_effect_boundary",
}
CLAIM_BOUNDARY_KEYS = {
    "public_savings_claim_created",
    "public_benchmark_claim_created",
    "public_adoption_claim_created",
    "public_compatibility_claim_created",
    "public_support_claim_created",
    "public_security_claim_created",
    "public_endorsement_claim_created",
    "stable_protocol_claim_created",
}
SUPPORTED_INPUT_SUFFIXES = {".json", ".jsonl", ".md", ".mdx", ".txt", ".toml", ".yaml", ".yml"}
SKIPPED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
}
MAX_INPUT_FILES = 64
MAX_INPUT_FILE_BYTES = 256 * 1024
MAX_TOTAL_INPUT_BYTES = 2 * 1024 * 1024
MAX_SIGNAL_EVIDENCE_PER_FILE = 18
MAX_JSON_KEY_PATHS = 120
MAX_SKIPPED_INPUT_RECORDS = 100
INPUT_REPORT_FILENAMES = {
    "json": "influence-boundary-report.json",
    "markdown": "influence-boundary-report.md",
    "html": "influence-boundary-report.html",
}
INPUT_SIGNAL_RULES = [
    {
        "signal_id": "memory_or_context_state",
        "label": "memory/context/state",
        "terms": (
            "memory",
            "remembered",
            "context",
            "state",
            "checkpoint",
            "thread_id",
            "session",
            "preference",
            "profile",
            "summary",
            "store",
            "namespace",
            "channel_values",
        ),
    },
    {
        "signal_id": "project_instruction",
        "label": "project instruction",
        "terms": ("instruction", "rule", "must", "always", "never", "policy", "guideline", "agent"),
    },
    {
        "signal_id": "scope_or_identity",
        "label": "scope/identity boundary",
        "terms": ("tenant", "workspace", "project", "user_id", "member", "private", "shared", "acl", "rbac"),
    },
    {
        "signal_id": "action_or_tool_authority",
        "label": "action/tool authority",
        "terms": ("tool", "action", "write", "execute", "deploy", "publish", "commit", "push", "post", "mutation"),
    },
    {
        "signal_id": "rollback_or_deletion",
        "label": "rollback/delete path",
        "terms": ("rollback", "delete", "forget", "revoke", "expire", "ttl", "retention", "deletion"),
    },
    {
        "signal_id": "stale_or_superseded",
        "label": "stale/superseded state",
        "terms": ("stale", "superseded", "deprecated", "obsolete", "replaced", "outdated"),
    },
]
JSON_PARSE_ERROR_SIGNAL = {
    "signal_id": "json_parse_error",
    "label": "JSON parse error",
    "matched": "parse_error",
    "raw_content_included": False,
}
TOML_PARSE_ERROR_SIGNAL = {
    "signal_id": "toml_parse_error",
    "label": "TOML parse error",
    "matched": "parse_error",
    "raw_content_included": False,
}
CLAUDE_IMPORT_RE = re.compile(r"^\s*@(?P<path>[A-Za-z0-9_./~@-]+)\s*$")
SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key|token|secret|password)\s*[:=]", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
]


def build_memory_state_governability_overlay_demo(
    root: Path = ROOT,
    *,
    fixture_path: Path = FIXTURE,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(root).resolve()
    fixture_path = _resolve(root, fixture_path)
    output_dir = _resolve(root, output_dir)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    errors = _validate_overlay_fixture(payload)
    surfaces = payload.get("surfaces") if isinstance(payload.get("surfaces"), list) else []
    scale_profile_counts = {profile: 0 for profile in sorted(SCALE_PROFILES)}
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        for profile in surface.get("scale_profiles", []):
            if profile in scale_profile_counts:
                scale_profile_counts[profile] += 1

    report = {
        "schema_id": "ctxvault.memory-state-governability-overlay-demo/v0",
        "status": "pass_memory_state_governability_overlay_demo" if not errors else "fail_memory_state_governability_overlay_demo",
        "milestone": payload.get("milestone"),
        "demo_command": "python3 scripts/run_memory_state_governability_overlay_demo.py",
        "fresh_checkout_commands": [
            "git clone https://github.com/ctxgov/ctxgov.git",
            "cd ctxgov",
            "python3 scripts/run_memory_state_governability_overlay_demo.py",
        ],
        "public_page": "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
        "fixture": _display_path(fixture_path, root),
        "surface_count": len(surfaces),
        "scale_profile_counts": scale_profile_counts,
        "required_overlay_fields": sorted(REQUIRED_OVERLAY_FIELDS),
        "surface_reports": [_surface_report(surface) for surface in surfaces if isinstance(surface, dict)],
        "claim_boundary": payload.get("claim_boundary", {}),
        "side_effect_boundary": payload.get("side_effect_boundary", {}),
        "claim_boundary_note": "This local report does not create compatibility, support, endorsement, adoption, benchmark, savings, security, or stable-protocol claims.",
        "publish_positioning": "A local governability overlay report for memory/state surfaces, not a runtime adapter or compatibility matrix.",
        "errors": errors,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "memory-state-governability-overlay-report.json"
    md_path = output_dir / "memory-state-governability-overlay-report.md"
    html_path = output_dir / "memory-state-governability-overlay-report.html"
    _write_text_atomic(json_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    _write_text_atomic(md_path, _render_markdown(report))
    _write_text_atomic(html_path, _render_html(report))
    report["output_files"] = {
        "json": _display_path(json_path, root),
        "markdown": _display_path(md_path, root),
        "html": _display_path(html_path, root),
    }
    _write_text_atomic(json_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def build_memory_state_influence_boundary_report(
    root: Path = ROOT,
    *,
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(root).resolve()
    output_dir = _resolve(root, output_dir)
    resolved_input = _resolve(root, input_path).resolve()
    input_display_root, input_display_prefix = _input_display_context(root, resolved_input)
    errors: list[str] = []
    skipped_inputs: list[dict[str, Any]] = []
    input_files: list[Path] = []

    if not resolved_input.exists():
        errors.append(f"input path does not exist: {_display_input_path(resolved_input, root, input_display_root, input_display_prefix)}")
        skipped_input_total_count = 0
    else:
        input_files, skipped_inputs, skipped_input_total_count = _collect_input_files(
            resolved_input,
            root,
            input_display_root,
            input_display_prefix,
        )
        if not input_files:
            errors.append("input path contains no supported memory/context/state files")

    file_reports: list[dict[str, Any]] = []
    total_bytes = 0
    for path in input_files:
        try:
            payload = path.read_bytes()
        except OSError as exc:
            errors.append(f"unable to read {path}: {exc}")
            continue
        if len(payload) > MAX_INPUT_FILE_BYTES:
            skipped_input_total_count = _record_skipped_input(
                skipped_inputs,
                skipped_input_total_count,
                _skip_record(
                    path,
                    "max_input_file_bytes_exceeded",
                    root,
                    input_display_root,
                    input_display_prefix,
                    bytes_observed=len(payload),
                ),
            )
            continue
        if total_bytes + len(payload) > MAX_TOTAL_INPUT_BYTES:
            skipped_input_total_count = _record_skipped_input(
                skipped_inputs,
                skipped_input_total_count,
                _skip_record(
                    path,
                    "max_total_input_bytes_exceeded",
                    root,
                    input_display_root,
                    input_display_prefix,
                    bytes_observed=len(payload),
                ),
            )
            continue
        total_bytes += len(payload)
        text = payload.decode("utf-8", errors="replace")
        file_reports.append(_analyze_input_file(path, text, payload, root, input_display_root, input_display_prefix))
    if input_files and not file_reports:
        errors.append("no supported input files were scanned within configured limits")

    influence_boundary = _compile_influence_boundary(file_reports, skipped_inputs)
    findings = _compile_findings(file_reports, skipped_inputs, skipped_input_total_count)
    if errors:
        status = "fail_memory_state_influence_boundary_report"
    else:
        status = "pass_memory_state_influence_boundary_report"
    integration_gate = _compile_integration_gate(status, influence_boundary)

    report = {
        "schema_id": "ctxvault.memory-state-influence-boundary-report/v0",
        "status": status,
        "milestone": "Local Memory State Influence Boundary Report",
        "mode": "user_input",
        "demo_command": f"{INFLUENCE_BOUNDARY_COMMAND} --input {_display_input_path(resolved_input, root, input_display_root, input_display_prefix)}",
        "sample_command": f"{INFLUENCE_BOUNDARY_COMMAND} --input {SAMPLE_INPUT_DIR}",
        "bring_your_own_commands": [
            f"{INFLUENCE_BOUNDARY_COMMAND} --input ./CLAUDE.md",
            f"{INFLUENCE_BOUNDARY_COMMAND} --input ./memory-state/",
        ],
        "fresh_checkout_commands": [
            "git clone https://github.com/ctxgov/ctxgov.git",
            "cd ctxgov",
            f"{INFLUENCE_BOUNDARY_COMMAND} --input {SAMPLE_INPUT_DIR}",
        ],
        "input_path": _display_input_path(resolved_input, root, input_display_root, input_display_prefix),
        "input_kind": "directory" if resolved_input.is_dir() else "file",
        "supported_input_suffixes": sorted(SUPPORTED_INPUT_SUFFIXES),
        "scan_limits": {
            "max_input_files": MAX_INPUT_FILES,
            "max_input_file_bytes": MAX_INPUT_FILE_BYTES,
            "max_total_input_bytes": MAX_TOTAL_INPUT_BYTES,
            "max_skipped_input_records": MAX_SKIPPED_INPUT_RECORDS,
            "raw_content_included": False,
        },
        "input_file_count": len(file_reports),
        "skipped_input_count": skipped_input_total_count,
        "skipped_input_record_count": len(skipped_inputs),
        "skipped_input_records_truncated": skipped_input_total_count > len(skipped_inputs),
        "total_input_bytes": total_bytes,
        "input_files": file_reports,
        "skipped_inputs": skipped_inputs,
        "influence_boundary": influence_boundary,
        "integration_gate": integration_gate,
        "findings": findings,
        "claim_boundary": _false_claim_boundary(),
        "side_effect_boundary": _false_side_effect_boundary(),
        "claim_boundary_note": "This local input audit does not prove runtime selection and does not create compatibility, support, endorsement, adoption, benchmark, savings, security, or stable-protocol claims.",
        "publish_positioning": "A local audit of user-supplied memory/context/state files that reports which state is allowed, blocked, omitted, stale, or unsupported before it can influence behavior.",
        "errors": errors,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / INPUT_REPORT_FILENAMES["json"]
    md_path = output_dir / INPUT_REPORT_FILENAMES["markdown"]
    html_path = output_dir / INPUT_REPORT_FILENAMES["html"]
    report["output_files"] = {
        "json": _display_path(json_path, root),
        "markdown": _display_path(md_path, root),
        "html": _display_path(html_path, root),
    }
    _write_text_atomic(json_path, json.dumps(report, indent=2, sort_keys=True) + "\n")
    _write_text_atomic(md_path, _render_influence_boundary_markdown(report))
    _write_text_atomic(html_path, _render_influence_boundary_html(report))
    return report


def _validate_overlay_fixture(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_id") != "ctxvault.memory-state-governability-overlays/v0":
        errors.append("schema_id must be ctxvault.memory-state-governability-overlays/v0")
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list) or len(surfaces) != 5:
        errors.append(f"surfaces must contain exactly 5 entries, observed {len(surfaces) if isinstance(surfaces, list) else 0}")
        surfaces = []
    required_overlay_fields = set(payload.get("required_overlay_fields") or [])
    if required_overlay_fields != REQUIRED_OVERLAY_FIELDS:
        errors.append("required_overlay_fields must match the governability overlay contract")

    seen_ids: set[str] = set()
    for surface in surfaces:
        if not isinstance(surface, dict):
            errors.append("each surface must be an object")
            continue
        surface_id = str(surface.get("surface_id") or "")
        if not surface_id:
            errors.append("surface_id is required")
        elif surface_id in seen_ids:
            errors.append(f"duplicate surface_id: {surface_id}")
        seen_ids.add(surface_id)
        missing = sorted(REQUIRED_SURFACE_FIELDS - set(surface))
        if missing:
            errors.append(f"{surface_id or '<missing>'} missing fields: {', '.join(missing)}")
        source_refs = surface.get("source_refs")
        if not isinstance(source_refs, list) or not source_refs:
            errors.append(f"{surface_id} source_refs must be a non-empty list")
        else:
            for ref in source_refs:
                if not isinstance(ref, dict) or not str(ref.get("url") or "").startswith("https://"):
                    errors.append(f"{surface_id} source_refs entries must include https URLs")
        scale_profiles = surface.get("scale_profiles")
        if not isinstance(scale_profiles, list) or not scale_profiles:
            errors.append(f"{surface_id} scale_profiles must be a non-empty list")
        elif sorted(set(scale_profiles) - SCALE_PROFILES):
            errors.append(f"{surface_id} has invalid scale_profiles")
        overlay_fields = set(surface.get("governability_overlay_requirements") or [])
        if overlay_fields != REQUIRED_OVERLAY_FIELDS:
            errors.append(f"{surface_id} governability_overlay_requirements must match the required overlay fields")
        for list_field in ("source_visible_state_fields", "missing_or_ctxgov_owned_proof", "blocked_public_claims"):
            if not isinstance(surface.get(list_field), list) or not surface.get(list_field):
                errors.append(f"{surface_id} {list_field} must be a non-empty list")
        blocked_claims_text = " ".join(str(item).lower() for item in surface.get("blocked_public_claims", []))
        for required in ("compatibility", "support", "endorsement", "security", "benchmark"):
            if required not in blocked_claims_text:
                errors.append(f"{surface_id} blocked_public_claims must include {required}")

    claim_boundary = payload.get("claim_boundary")
    if not isinstance(claim_boundary, dict) or set(claim_boundary) != CLAIM_BOUNDARY_KEYS:
        errors.append("claim_boundary must contain the expected claim flags")
    elif any(bool(value) for value in claim_boundary.values()):
        errors.append("claim_boundary flags must all be false")
    side_effect_boundary = payload.get("side_effect_boundary")
    if not isinstance(side_effect_boundary, dict) or any(bool(value) for value in side_effect_boundary.values()):
        errors.append("side_effect_boundary flags must all be false")
    return errors


def _surface_report(surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface_id": surface.get("surface_id"),
        "display_name": surface.get("display_name"),
        "scale_profiles": surface.get("scale_profiles", []),
        "source_ref_count": len(surface.get("source_refs", [])),
        "visible_state_field_count": len(surface.get("source_visible_state_fields", [])),
        "overlay_requirement_count": len(surface.get("governability_overlay_requirements", [])),
        "missing_or_ctxgov_owned_proof_count": len(surface.get("missing_or_ctxgov_owned_proof", [])),
        "allowed_public_phrase": surface.get("allowed_public_phrase"),
        "blocked_public_claims": surface.get("blocked_public_claims", []),
    }


def _collect_input_files(
    input_path: Path,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> tuple[list[Path], list[dict[str, Any]], int]:
    skipped: list[dict[str, Any]] = []
    skipped_total_count = 0
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES:
            return [input_path], skipped, skipped_total_count
        skipped_total_count = _record_skipped_input(
            skipped,
            skipped_total_count,
            _skip_record(input_path, "unsupported_suffix", root, input_display_root, input_display_prefix),
        )
        return [], skipped, skipped_total_count

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(input_path):
        dirnames[:] = sorted(name for name in dirnames if name not in SKIPPED_DIRECTORY_NAMES)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES:
                if len(files) < MAX_INPUT_FILES:
                    files.append(path)
                else:
                    skipped_total_count = _record_skipped_input(
                        skipped,
                        skipped_total_count,
                        _skip_record(path, "max_input_files_exceeded", root, input_display_root, input_display_prefix),
                    )
            else:
                skipped_total_count = _record_skipped_input(
                    skipped,
                    skipped_total_count,
                    _skip_record(path, "unsupported_suffix", root, input_display_root, input_display_prefix),
                )
    return files, skipped, skipped_total_count


def _record_skipped_input(skipped: list[dict[str, Any]], skipped_total_count: int, record: dict[str, Any]) -> int:
    if len(skipped) < MAX_SKIPPED_INPUT_RECORDS:
        skipped.append(record)
    return skipped_total_count + 1


def _skip_record(
    path: Path,
    reason: str,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
    *,
    bytes_observed: int | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": _display_input_path(path, root, input_display_root, input_display_prefix),
        "reason": reason,
    }
    if bytes_observed is not None:
        record["bytes_observed"] = bytes_observed
    return record


def _analyze_input_file(
    path: Path,
    text: str,
    payload: bytes,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> dict[str, Any]:
    lines = text.splitlines()
    text_signal_refs = _scan_text_signal_refs(path, lines, root, input_display_root, input_display_prefix)
    json_signal_refs, json_parse_errors, json_key_paths = _scan_json_signal_refs(path, text, root, input_display_root, input_display_prefix)
    toml_signal_refs, toml_parse_errors, toml_key_paths = _scan_toml_signal_refs(path, text, root, input_display_root, input_display_prefix)
    yaml_signal_refs, yaml_key_paths = _scan_yaml_signal_refs(path, lines, root, input_display_root, input_display_prefix)
    structured_key_paths = json_key_paths + toml_key_paths + yaml_key_paths
    all_signal_refs = _dedupe_signal_refs(text_signal_refs + json_signal_refs + toml_signal_refs + yaml_signal_refs)
    signal_ids = sorted({ref["signal_id"] for ref in all_signal_refs})
    if json_parse_errors:
        parse_ref = dict(JSON_PARSE_ERROR_SIGNAL)
        parse_ref["ref"] = _display_input_path(path, root, input_display_root, input_display_prefix)
        all_signal_refs.append(parse_ref)
        signal_ids = sorted(set(signal_ids + ["json_parse_error"]))
    if toml_parse_errors:
        parse_ref = dict(TOML_PARSE_ERROR_SIGNAL)
        parse_ref["ref"] = _display_input_path(path, root, input_display_root, input_display_prefix)
        all_signal_refs.append(parse_ref)
        signal_ids = sorted(set(signal_ids + ["toml_parse_error"]))
    import_refs = _scan_import_refs(path, lines, root, input_display_root, input_display_prefix)
    secret_refs = _scan_secret_refs(path, lines, root, input_display_root, input_display_prefix)
    if import_refs:
        signal_ids = sorted(set(signal_ids + ["imported_context_ref"]))
        all_signal_refs.extend(import_refs)
    if secret_refs:
        signal_ids = sorted(set(signal_ids + ["secret_like_content"]))
        all_signal_refs.extend(secret_refs)
    decision = _influence_decision(signal_ids)
    return {
        "path": _display_input_path(path, root, input_display_root, input_display_prefix),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "line_count": len(lines),
        "source_family": _source_family(path, signal_ids, structured_key_paths),
        "raw_content_included": False,
        "json_parse_errors": json_parse_errors,
        "toml_parse_errors": toml_parse_errors,
        "json_key_paths_sample": json_key_paths[:MAX_JSON_KEY_PATHS],
        "yaml_key_paths_sample": yaml_key_paths[:MAX_JSON_KEY_PATHS],
        "structured_key_paths_sample": structured_key_paths[:MAX_JSON_KEY_PATHS],
        "signal_ids": signal_ids,
        "signal_evidence": all_signal_refs[:MAX_SIGNAL_EVIDENCE_PER_FILE],
        "secret_like_evidence_count": len(secret_refs),
        "decision": decision,
    }


def _scan_text_signal_refs(
    path: Path,
    lines: list[str],
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        lowered = line.lower()
        for rule in INPUT_SIGNAL_RULES:
            for term in rule["terms"]:
                if term.lower() in lowered:
                    refs.append(
                        {
                            "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{line_number}",
                            "signal_id": rule["signal_id"],
                            "label": rule["label"],
                            "matched": term,
                            "raw_content_included": False,
                        }
                    )
                    break
    return refs


def _scan_json_signal_refs(
    path: Path,
    text: str,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if path.suffix.lower() not in {".json", ".jsonl"}:
        return [], [], []
    parse_errors: list[str] = []
    key_paths: list[str] = []
    values: list[Any] = []
    if path.suffix.lower() == ".json":
        try:
            values.append(json.loads(text))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"json parse error at line {exc.lineno}: {exc.msg}")
    else:
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                parse_errors.append(f"jsonl parse error at line {line_number}: {exc.msg}")
    for value in values:
        key_paths.extend(_json_key_paths(value))
    refs: list[dict[str, Any]] = []
    for key_path in key_paths[:MAX_JSON_KEY_PATHS]:
        lowered = key_path.lower()
        for rule in INPUT_SIGNAL_RULES:
            for term in rule["terms"]:
                if term.lower() in lowered:
                    refs.append(
                        {
                            "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{key_path}",
                            "signal_id": rule["signal_id"],
                            "label": rule["label"],
                            "matched": term,
                            "raw_content_included": False,
                        }
                    )
                    break
    for value in values:
        refs.extend(_scan_structured_value_signal_refs(path, value, root, input_display_root, input_display_prefix))
    return refs, parse_errors, key_paths


def _scan_toml_signal_refs(
    path: Path,
    text: str,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    if path.suffix.lower() != ".toml":
        return [], [], []
    try:
        value = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return [], [f"toml parse error: {exc}"], []
    key_paths = _json_key_paths(value)
    refs: list[dict[str, Any]] = []
    for key_path in key_paths[:MAX_JSON_KEY_PATHS]:
        lowered = key_path.lower()
        for rule in INPUT_SIGNAL_RULES:
            for term in rule["terms"]:
                if term.lower() in lowered:
                    refs.append(
                        {
                            "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{key_path}",
                            "signal_id": rule["signal_id"],
                            "label": rule["label"],
                            "matched": term,
                            "raw_content_included": False,
                        }
                    )
                    break
    refs.extend(_scan_structured_value_signal_refs(path, value, root, input_display_root, input_display_prefix))
    return refs, [], key_paths


def _scan_yaml_signal_refs(
    path: Path,
    lines: list[str],
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    if path.suffix.lower() not in {".yaml", ".yml"}:
        return [], []
    refs: list[dict[str, Any]] = []
    key_paths: list[str] = []
    stack: list[tuple[int, str]] = []
    for line in lines:
        if len(key_paths) >= MAX_JSON_KEY_PATHS:
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        normalized = stripped[2:].lstrip() if stripped.startswith("- ") else stripped
        if ":" not in normalized:
            continue
        key_part, value_part = normalized.split(":", 1)
        key = key_part.strip().strip("'\"")
        if not key or any(char.isspace() for char in key):
            continue
        indent = len(line) - len(line.lstrip(" "))
        while stack and indent <= stack[-1][0]:
            stack.pop()
        stack.append((indent, key))
        key_path = "$." + ".".join(item[1] for item in stack)
        key_paths.append(key_path)
        refs.extend(_structured_key_signal_refs(path, key_path, root, input_display_root, input_display_prefix))
        value = value_part.strip().strip("'\"")
        if value and value not in {"|", ">"}:
            refs.extend(_structured_scalar_value_signal_refs(path, key_path, value, root, input_display_root, input_display_prefix))
    return refs[:MAX_JSON_KEY_PATHS], key_paths[:MAX_JSON_KEY_PATHS]


def _scan_structured_value_signal_refs(
    path: Path,
    value: Any,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    stack: list[tuple[str, Any]] = [("$", value)]
    while stack and len(refs) < MAX_JSON_KEY_PATHS:
        current_path, current = stack.pop()
        if isinstance(current, dict):
            for key in sorted(current, reverse=True):
                stack.append((f"{current_path}.{key}", current[key]))
            continue
        if isinstance(current, list):
            for index in reversed(range(min(len(current), 20))):
                stack.append((f"{current_path}[{index}]", current[index]))
            continue
        if not isinstance(current, str):
            continue
        refs.extend(_structured_scalar_value_signal_refs(path, current_path, current, root, input_display_root, input_display_prefix))
    return refs[:MAX_JSON_KEY_PATHS]


def _structured_key_signal_refs(
    path: Path,
    key_path: str,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    lowered = key_path.lower()
    for rule in INPUT_SIGNAL_RULES:
        for term in rule["terms"]:
            if term.lower() in lowered:
                refs.append(
                    {
                        "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{key_path}",
                        "signal_id": rule["signal_id"],
                        "label": rule["label"],
                        "matched": term,
                        "evidence_kind": "structured_key",
                        "raw_content_included": False,
                    }
                )
                break
    return refs


def _structured_scalar_value_signal_refs(
    path: Path,
    key_path: str,
    value: str,
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    lowered = value.lower()
    for rule in INPUT_SIGNAL_RULES:
        for term in rule["terms"]:
            if term.lower() in lowered:
                refs.append(
                    {
                        "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{key_path}",
                        "signal_id": rule["signal_id"],
                        "label": rule["label"],
                        "matched": term,
                        "evidence_kind": "structured_value",
                        "raw_content_included": False,
                    }
                )
                break
    return refs


def _json_key_paths(value: Any, prefix: str = "$") -> list[str]:
    paths: list[str] = []
    stack: list[tuple[str, Any]] = [(prefix, value)]
    while stack and len(paths) < MAX_JSON_KEY_PATHS:
        current_prefix, current = stack.pop()
        if isinstance(current, dict):
            for key in sorted(current):
                key_path = f"{current_prefix}.{key}"
                paths.append(key_path)
                stack.append((key_path, current[key]))
        elif isinstance(current, list):
            for index, item in enumerate(current[:20]):
                item_path = f"{current_prefix}[{index}]"
                paths.append(item_path)
                stack.append((item_path, item))
    return paths[:MAX_JSON_KEY_PATHS]


def _scan_import_refs(
    path: Path,
    lines: list[str],
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if CLAUDE_IMPORT_RE.match(line):
            refs.append(
                {
                    "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{line_number}",
                    "signal_id": "imported_context_ref",
                    "label": "imported context ref",
                    "matched": "@import",
                    "raw_content_included": False,
                }
            )
    return refs


def _scan_secret_refs(
    path: Path,
    lines: list[str],
    root: Path,
    input_display_root: Path,
    input_display_prefix: str,
) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        for pattern in SECRET_PATTERNS:
            if pattern.search(line):
                refs.append(
                    {
                        "ref": f"{_display_input_path(path, root, input_display_root, input_display_prefix)}:{line_number}",
                        "signal_id": "secret_like_content",
                        "label": "secret-like content",
                        "matched": "redacted_secret_pattern",
                        "raw_content_included": False,
                    }
                )
                break
    return refs


def _dedupe_signal_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for ref in refs:
        key = (str(ref.get("ref")), str(ref.get("signal_id")), str(ref.get("matched")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped


def _source_family(path: Path, signal_ids: list[str], json_key_paths: list[str]) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    key_text = " ".join(json_key_paths).lower()
    if name in {"claude.md", "agents.md", "memory.md"}:
        return "local_project_memory_file"
    if suffix in {".json", ".jsonl"} and any(term in key_text for term in ("checkpoint", "thread_id", "channel_values")):
        return "checkpoint_or_thread_state_json"
    if suffix in {".json", ".jsonl"} and any(term in key_text for term in ("memory", "namespace", "store", "profile")):
        return "memory_store_json"
    if suffix in {".json", ".jsonl"} and "memory_or_context_state" in signal_ids:
        return "memory_store_json"
    if suffix in {".yaml", ".yml"}:
        return "local_state_yaml"
    if suffix == ".toml":
        return "local_state_toml"
    if "project_instruction" in signal_ids:
        return "project_instruction_text"
    if suffix == ".mdx":
        return "local_context_mdx"
    if suffix == ".md":
        return "local_context_markdown"
    return "local_context_text"


def _influence_decision(signal_ids: list[str]) -> dict[str, Any]:
    signal_set = set(signal_ids)
    if not signal_set:
        return {
            "decision": "omit_no_memory_state_signal",
            "authority_ceiling": "none",
            "reason": "No memory/context/state signal was detected in this file.",
        }
    if signal_set & {"secret_like_content", "stale_or_superseded"}:
        return {
            "decision": "blocked_until_review",
            "authority_ceiling": "none",
            "reason": "Secret-like or stale/superseded state must not influence behavior until reviewed.",
        }
    if "json_parse_error" in signal_set or "toml_parse_error" in signal_set:
        return {
            "decision": "blocked_until_parseable_state_export",
            "authority_ceiling": "none",
            "reason": "Malformed JSON/JSONL/TOML state exports require review before they can influence behavior.",
        }
    if "action_or_tool_authority" in signal_set:
        return {
            "decision": "blocked_until_policy_grant",
            "authority_ceiling": "suggest_only",
            "reason": "Action/tool/write authority requires an explicit policy grant, final-state assertion, and rollback path.",
        }
    if "memory_or_context_state" in signal_set or "project_instruction" in signal_set:
        return {
            "decision": "inform_only_allowed_with_receipts",
            "authority_ceiling": "inform_only",
            "reason": "The file may inform behavior only with source refs and without target writes or external side effects.",
        }
    return {
        "decision": "review_required",
        "authority_ceiling": "suggest_only",
        "reason": "The file contains governance-relevant signals but not enough proof for automatic influence.",
    }


def _compile_influence_boundary(file_reports: list[dict[str, Any]], skipped_inputs: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_refs: list[str] = []
    allowed_refs: list[str] = []
    omitted_refs: list[str] = []
    blocked_refs: list[str] = []
    stale_or_superseded_refs: list[str] = []
    rollback_refs: list[str] = []
    imported_refs: list[str] = []

    for file_report in file_reports:
        path = str(file_report["path"])
        signal_ids = set(file_report.get("signal_ids", []))
        decision = str(file_report.get("decision", {}).get("decision"))
        if signal_ids & {"memory_or_context_state", "project_instruction", "scope_or_identity"}:
            candidate_refs.append(path)
        if decision == "inform_only_allowed_with_receipts":
            allowed_refs.append(path)
        elif decision.startswith("omit"):
            omitted_refs.append(path)
        elif decision.startswith("blocked"):
            blocked_refs.append(path)
        else:
            candidate_refs.append(path)
        if "stale_or_superseded" in signal_ids:
            stale_or_superseded_refs.append(path)
        if "rollback_or_deletion" in signal_ids:
            rollback_refs.append(path)
        if "imported_context_ref" in signal_ids:
            imported_refs.append(path)

    for skipped in skipped_inputs:
        omitted_refs.append(str(skipped["path"]))

    return {
        "selected_refs": [],
        "selected_refs_note": "User-input mode audits allowable influence from local files; it does not prove runtime selection by a model or agent.",
        "candidate_influence_refs": sorted(set(candidate_refs)),
        "inform_only_allowed_refs": sorted(set(allowed_refs)),
        "omitted_refs": sorted(set(omitted_refs)),
        "blocked_refs": sorted(set(blocked_refs)),
        "stale_or_superseded_refs": sorted(set(stale_or_superseded_refs)),
        "imported_context_refs": sorted(set(imported_refs)),
        "source_refs": sorted({str(file_report["path"]) for file_report in file_reports}),
        "authority_ceiling": "inform_only unless an explicit policy grant, final-state assertion, and rollback path are present",
        "policy_grant": "not_proven_by_user_input_audit",
        "final_state_assertion": "not_proven_by_user_input_audit",
        "rollback_path": "detected" if rollback_refs else "not_proven_by_user_input_audit",
        "delete_or_forget_propagation": "not_proven_by_user_input_audit",
        "side_effect_boundary": "no provider/model call, adapter execution, memory/backend write, target write, SARIF upload, package publication, or outreach",
    }


def _compile_findings(
    file_reports: list[dict[str, Any]],
    skipped_inputs: list[dict[str, Any]],
    skipped_input_total_count: int,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for file_report in file_reports:
        path = str(file_report["path"])
        signal_ids = set(file_report.get("signal_ids", []))
        decision = str(file_report.get("decision", {}).get("decision"))
        if signal_ids & {"memory_or_context_state", "project_instruction"}:
            findings.append(
                {
                    "finding_id": "candidate_memory_state_influence",
                    "severity": "info",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Keep this ref inform-only unless policy grant, final-state assertion, rollback, and deletion proof are available.",
                    "evidence_refs": [ref["ref"] for ref in file_report.get("signal_evidence", [])[:5]],
                }
            )
        if "action_or_tool_authority" in signal_ids:
            findings.append(
                {
                    "finding_id": "action_authority_requires_policy_grant",
                    "severity": "high",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Block action/tool/write authority until an explicit policy grant and rollback path are reviewed.",
                    "evidence_refs": [ref["ref"] for ref in file_report.get("signal_evidence", []) if ref["signal_id"] == "action_or_tool_authority"][:5],
                }
            )
        if "stale_or_superseded" in signal_ids:
            findings.append(
                {
                    "finding_id": "stale_or_superseded_state_detected",
                    "severity": "high",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Treat stale or superseded state as non-influential until the current state source is supplied.",
                    "evidence_refs": [ref["ref"] for ref in file_report.get("signal_evidence", []) if ref["signal_id"] == "stale_or_superseded"][:5],
                }
            )
        if "secret_like_content" in signal_ids:
            findings.append(
                {
                    "finding_id": "secret_like_content_redacted",
                    "severity": "high",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Remove or rotate secret-like values before allowing this file to influence behavior.",
                    "evidence_refs": [ref["ref"] for ref in file_report.get("signal_evidence", []) if ref["signal_id"] == "secret_like_content"][:5],
                    "raw_content_included": False,
                }
            )
        if "json_parse_error" in signal_ids:
            findings.append(
                {
                    "finding_id": "json_parse_error_blocks_state_export",
                    "severity": "high",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Regenerate or repair the JSON/JSONL export before treating it as state evidence.",
                    "parse_errors": file_report.get("json_parse_errors", []),
                    "raw_content_included": False,
                }
            )
        if "toml_parse_error" in signal_ids:
            findings.append(
                {
                    "finding_id": "toml_parse_error_blocks_state_export",
                    "severity": "high",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Regenerate or repair the TOML export before treating it as state evidence.",
                    "parse_errors": file_report.get("toml_parse_errors", []),
                    "raw_content_included": False,
                }
            )
        if "imported_context_ref" in signal_ids:
            findings.append(
                {
                    "finding_id": "imported_context_ref_requires_boundary_review",
                    "severity": "medium",
                    "path": path,
                    "decision": decision,
                    "recommendation": "Review imported context refs separately before allowing them to extend the influence boundary.",
                    "evidence_refs": [ref["ref"] for ref in file_report.get("signal_evidence", []) if ref["signal_id"] == "imported_context_ref"][:5],
                }
            )
    if skipped_input_total_count:
        findings.append(
            {
                "finding_id": "inputs_omitted_by_scan_boundary",
                "severity": "medium",
                "omitted_count": skipped_input_total_count,
                "omitted_record_count": len(skipped_inputs),
                "omitted_records_truncated": skipped_input_total_count > len(skipped_inputs),
                "reasons": sorted({str(item["reason"]) for item in skipped_inputs}),
                "recommendation": "Review omitted inputs separately or narrow the input directory so only intended memory/context/state files are scanned.",
            }
        )
    return findings


def _compile_integration_gate(status: str, influence_boundary: dict[str, Any]) -> dict[str, Any]:
    blocked_ref_count = len(influence_boundary.get("blocked_refs", []))
    omitted_ref_count = len(influence_boundary.get("omitted_refs", []))
    stale_ref_count = len(influence_boundary.get("stale_or_superseded_refs", []))
    imported_ref_count = len(influence_boundary.get("imported_context_refs", []))
    report_passed = status.startswith("pass_")
    fail_on_blocked_exit_code = 1
    if report_passed:
        fail_on_blocked_exit_code = 2 if blocked_ref_count else 0
    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-integration-gate/v0",
        "mode": "fail_on_blocked",
        "passed": report_passed and blocked_ref_count == 0,
        "default_exit_code": 0 if report_passed else 1,
        "fail_on_blocked_exit_code": fail_on_blocked_exit_code,
        "blocked_ref_count": blocked_ref_count,
        "omitted_ref_count": omitted_ref_count,
        "stale_or_superseded_ref_count": stale_ref_count,
        "imported_context_ref_count": imported_ref_count,
        "raw_content_included": False,
        "policy": "exit 1 when the report fails; exit 2 when --fail-on-blocked is used and blocked refs exist; otherwise exit 0",
        "recommendation": (
            "Treat blocked refs as an integration stop until review, policy grant, final-state assertion, rollback, and deletion proof are available."
            if blocked_ref_count
            else "No blocked refs were detected by the local input audit."
        ),
    }


def _false_claim_boundary() -> dict[str, bool]:
    return {key: False for key in CLAIM_BOUNDARY_KEYS}


def _false_side_effect_boundary() -> dict[str, bool]:
    return {
        "network_access_performed": False,
        "provider_or_model_call_performed": False,
        "external_runtime_or_adapter_executed": False,
        "memory_backend_written": False,
        "target_file_written": False,
        "sarif_uploaded": False,
        "public_release_created": False,
        "outreach_performed": False,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Memory State Governability Overlay Report",
        "",
        f"Status: `{report['status']}`",
        f"Milestone: `{report['milestone']}`",
        f"Surface count: `{report['surface_count']}`",
        "",
        "Fresh checkout command:",
        "",
        "```sh",
        *report["fresh_checkout_commands"],
        "```",
        "",
        "This is a local source-derived overlay report. It is not a runtime adapter, compatibility matrix, provider integration, endorsement, benchmark, or support claim.",
        "",
        "## Surfaces",
        "",
    ]
    for surface in report["surface_reports"]:
        lines.extend(
            [
                f"### {surface['display_name']}",
                "",
                f"- Scale profiles: {', '.join(surface['scale_profiles'])}",
                f"- Source refs: {surface['source_ref_count']}",
                f"- Visible state fields mapped: {surface['visible_state_field_count']}",
                f"- Overlay requirements: {surface['overlay_requirement_count']}",
                f"- CtxGov-owned proof gaps: {surface['missing_or_ctxgov_owned_proof_count']}",
                f"- Allowed phrase: {surface['allowed_public_phrase']}",
                f"- Blocked claims: {', '.join(surface['blocked_public_claims'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            report["claim_boundary_note"],
            "",
        ]
    )
    if report["errors"]:
        lines.extend(["## Errors", "", *[f"- {error}" for error in report["errors"]], ""])
    return "\n".join(lines)


def _render_influence_boundary_markdown(report: dict[str, Any]) -> str:
    boundary = report["influence_boundary"]
    gate = report["integration_gate"]
    lines = [
        "# Local Memory State Influence Boundary Report",
        "",
        f"Status: `{report['status']}`",
        f"Mode: `{report['mode']}`",
        f"Input: `{report['input_path']}`",
        f"Input kind: `{report['input_kind']}`",
        f"Input files scanned: `{report['input_file_count']}`",
        f"Inputs skipped: `{report['skipped_input_count']}`",
        f"Skipped records retained: `{report['skipped_input_record_count']}`",
        "",
        "This report audits user-supplied local memory/context/state files. It does not prove runtime model selection, call a provider, execute an adapter, write memory, write a target file, upload SARIF, publish a package, or perform outreach.",
        "",
        "## Output Files",
        "",
        f"- JSON: `{report['output_files']['json']}`",
        f"- Markdown: `{report['output_files']['markdown']}`",
        f"- HTML: `{report['output_files']['html']}`",
        "",
        "## Influence Boundary",
        "",
        f"- Candidate influence refs: `{len(boundary['candidate_influence_refs'])}`",
        f"- Inform-only allowed refs: `{len(boundary['inform_only_allowed_refs'])}`",
        f"- Blocked refs: `{len(boundary['blocked_refs'])}`",
        f"- Omitted refs: `{len(boundary['omitted_refs'])}`",
        f"- Stale or superseded refs: `{len(boundary['stale_or_superseded_refs'])}`",
        f"- Imported context refs: `{len(boundary['imported_context_refs'])}`",
        f"- Authority ceiling: `{boundary['authority_ceiling']}`",
        f"- Policy grant: `{boundary['policy_grant']}`",
        f"- Final-state assertion: `{boundary['final_state_assertion']}`",
        f"- Rollback path: `{boundary['rollback_path']}`",
        "",
        "## Integration Gate",
        "",
        f"- Mode: `{gate['mode']}`",
        f"- Passed: `{str(gate['passed']).lower()}`",
        f"- Default exit code: `{gate['default_exit_code']}`",
        f"- `--fail-on-blocked` exit code: `{gate['fail_on_blocked_exit_code']}`",
        f"- Blocked refs: `{gate['blocked_ref_count']}`",
        f"- Omitted refs: `{gate['omitted_ref_count']}`",
        f"- Stale/superseded refs: `{gate['stale_or_superseded_ref_count']}`",
        f"- Imported context refs: `{gate['imported_context_ref_count']}`",
        f"- Raw content included: `{str(gate['raw_content_included']).lower()}`",
        f"- Recommendation: {gate['recommendation']}",
        "",
        "## File Decisions",
        "",
    ]
    for file_report in report["input_files"]:
        decision = file_report["decision"]
        lines.extend(
            [
                f"### `{file_report['path']}`",
                "",
                f"- SHA-256: `{file_report['sha256']}`",
                f"- Source family: `{file_report['source_family']}`",
                f"- Decision: `{decision['decision']}`",
                f"- Authority ceiling: `{decision['authority_ceiling']}`",
                f"- Reason: {decision['reason']}",
                f"- Signals: `{', '.join(file_report['signal_ids']) or 'none'}`",
                f"- Raw content included: `{str(file_report['raw_content_included']).lower()}`",
                "",
            ]
        )
        evidence_lines = _render_signal_evidence_markdown(file_report.get("signal_evidence", []))
        if evidence_lines:
            lines.extend(["Evidence refs:", "", *evidence_lines, ""])
    if report["findings"]:
        lines.extend(["## Findings", ""])
        for finding in report["findings"]:
            label = finding.get("finding_id")
            severity = finding.get("severity")
            path = finding.get("path", "")
            recommendation = finding.get("recommendation", "")
            line = f"- `{severity}` `{label}` {path}".rstrip()
            if recommendation:
                line += f": {recommendation}"
            lines.append(line)
        lines.append("")
    if report["skipped_inputs"]:
        lines.extend(["## Skipped Inputs", ""])
        for skipped in report["skipped_inputs"][:20]:
            lines.append(f"- `{skipped['reason']}` `{skipped['path']}`")
        if report["skipped_input_records_truncated"]:
            lines.append(f"- skipped input records truncated after `{report['skipped_input_record_count']}` of `{report['skipped_input_count']}` total skipped inputs")
        lines.append("")
    if report["errors"]:
        lines.extend(["## Errors", "", *[f"- {error}" for error in report["errors"]], ""])
    return "\n".join(lines)


def _render_html(report: dict[str, Any]) -> str:
    cards = []
    for surface in report["surface_reports"]:
        cards.append(
            "<section>"
            f"<h2>{escape(str(surface['display_name']))}</h2>"
            f"<p><strong>Scale profiles:</strong> {escape(', '.join(surface['scale_profiles']))}</p>"
            f"<p><strong>Overlay requirements:</strong> {surface['overlay_requirement_count']}</p>"
            f"<p><strong>Blocked claims:</strong> {escape(', '.join(surface['blocked_public_claims']))}</p>"
            "</section>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Memory State Governability Overlay Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem auto; max-width: 920px; line-height: 1.5; color: #18212f; }}
    code, pre {{ background: #f4f6f8; padding: .15rem .3rem; border-radius: 4px; }}
    section {{ border: 1px solid #d7dde5; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
  </style>
</head>
<body>
  <h1>Memory State Governability Overlay Report</h1>
  <p>Status: <code>{escape(str(report['status']))}</code></p>
  <p>Surface count: <strong>{report['surface_count']}</strong></p>
  <pre>python3 scripts/run_memory_state_governability_overlay_demo.py</pre>
  <p>This local report maps official memory/state surfaces to governability requirements. It is not a compatibility, support, endorsement, security, benchmark, or provider-integration claim.</p>
  {''.join(cards)}
</body>
</html>
"""


def _render_influence_boundary_html(report: dict[str, Any]) -> str:
    boundary = report["influence_boundary"]
    gate = report["integration_gate"]
    file_cards = []
    for file_report in report["input_files"]:
        decision = file_report["decision"]
        evidence = _render_signal_evidence_html(file_report.get("signal_evidence", []))
        file_cards.append(
            "<section>"
            f"<h2><code>{escape(str(file_report['path']))}</code></h2>"
            f"<p><strong>Decision:</strong> <code>{escape(str(decision['decision']))}</code></p>"
            f"<p><strong>Authority ceiling:</strong> {escape(str(decision['authority_ceiling']))}</p>"
            f"<p><strong>Reason:</strong> {escape(str(decision['reason']))}</p>"
            f"<p><strong>Signals:</strong> {escape(', '.join(file_report['signal_ids']) or 'none')}</p>"
            f"<p><strong>Raw content included:</strong> <code>{str(file_report['raw_content_included']).lower()}</code></p>"
            f"{evidence}"
            "</section>"
        )
    findings = "".join(
        f"<li><code>{escape(str(finding.get('severity')))}</code> {escape(str(finding.get('finding_id')))} {escape(str(finding.get('path', '')))}"
        f"{': ' + escape(str(finding.get('recommendation'))) if finding.get('recommendation') else ''}</li>"
        for finding in report["findings"]
    )
    skipped_inputs = "".join(
        f"<li><code>{escape(str(skipped.get('reason')))}</code> <code>{escape(str(skipped.get('path')))}</code></li>"
        for skipped in report.get("skipped_inputs", [])[:20]
    )
    if report.get("skipped_input_records_truncated"):
        skipped_inputs += (
            f"<li>Skipped input records truncated after <code>{report['skipped_input_record_count']}</code> "
            f"of <code>{report['skipped_input_count']}</code> total skipped inputs.</li>"
        )
    skipped_section = f"<h2>Skipped Inputs</h2><ul>{skipped_inputs}</ul>" if skipped_inputs else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Local Memory State Influence Boundary Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 2rem auto; max-width: 980px; line-height: 1.5; color: #18212f; }}
    code, pre {{ background: #f4f6f8; padding: .15rem .3rem; border-radius: 4px; }}
    section {{ border: 1px solid #d7dde5; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
    .counts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: .7rem; }}
    .counts div {{ background: #f7f9fc; border: 1px solid #d7dde5; border-radius: 8px; padding: .8rem; }}
  </style>
</head>
<body>
  <h1>Local Memory State Influence Boundary Report</h1>
  <p>Status: <code>{escape(str(report['status']))}</code></p>
  <p>Input: <code>{escape(str(report['input_path']))}</code></p>
  <p>Output files: <code>{escape(str(report['output_files']['json']))}</code>, <code>{escape(str(report['output_files']['markdown']))}</code>, <code>{escape(str(report['output_files']['html']))}</code></p>
  <p>This local report audits user-supplied memory/context/state files. It does not prove runtime model selection and performs no provider/model call, adapter execution, memory/backend write, target write, SARIF upload, package publication, or outreach.</p>
  <div class="counts">
    <div><strong>Candidate refs</strong><br>{len(boundary['candidate_influence_refs'])}</div>
    <div><strong>Inform-only allowed</strong><br>{len(boundary['inform_only_allowed_refs'])}</div>
    <div><strong>Blocked</strong><br>{len(boundary['blocked_refs'])}</div>
    <div><strong>Omitted</strong><br>{len(boundary['omitted_refs'])}</div>
    <div><strong>Stale/superseded</strong><br>{len(boundary['stale_or_superseded_refs'])}</div>
    <div><strong>Imported refs</strong><br>{len(boundary['imported_context_refs'])}</div>
  </div>
  <p><strong>Authority ceiling:</strong> {escape(str(boundary['authority_ceiling']))}</p>
  <h2>Integration Gate</h2>
  <ul>
    <li>Mode: <code>{escape(str(gate['mode']))}</code></li>
    <li>Passed: <code>{str(gate['passed']).lower()}</code></li>
    <li>Default exit code: <code>{gate['default_exit_code']}</code></li>
    <li><code>--fail-on-blocked</code> exit code: <code>{gate['fail_on_blocked_exit_code']}</code></li>
    <li>Blocked refs: <code>{gate['blocked_ref_count']}</code></li>
    <li>Omitted refs: <code>{gate['omitted_ref_count']}</code></li>
    <li>Stale/superseded refs: <code>{gate['stale_or_superseded_ref_count']}</code></li>
    <li>Imported context refs: <code>{gate['imported_context_ref_count']}</code></li>
    <li>Raw content included: <code>{str(gate['raw_content_included']).lower()}</code></li>
  </ul>
  <p><strong>Gate recommendation:</strong> {escape(str(gate['recommendation']))}</p>
  {''.join(file_cards)}
  <h2>Findings</h2>
  <ul>{findings}</ul>
  {skipped_section}
</body>
</html>
"""


def _render_signal_evidence_markdown(signal_evidence: list[dict[str, Any]], *, limit: int = 12) -> list[str]:
    lines: list[str] = []
    for evidence in signal_evidence[:limit]:
        evidence_kind = evidence.get("evidence_kind", "text_or_key")
        lines.append(
            "- "
            f"`{evidence.get('signal_id')}` "
            f"`{evidence.get('ref')}` "
            f"matched=`{evidence.get('matched')}` "
            f"kind=`{evidence_kind}` "
            f"raw_content_included=`{str(evidence.get('raw_content_included', False)).lower()}`"
        )
    if len(signal_evidence) > limit:
        lines.append(f"- evidence refs truncated after `{limit}` of `{len(signal_evidence)}` refs")
    return lines


def _render_signal_evidence_html(signal_evidence: list[dict[str, Any]], *, limit: int = 12) -> str:
    if not signal_evidence:
        return ""
    items = []
    for evidence in signal_evidence[:limit]:
        evidence_kind = evidence.get("evidence_kind", "text_or_key")
        items.append(
            "<li>"
            f"<code>{escape(str(evidence.get('signal_id')))}</code> "
            f"<code>{escape(str(evidence.get('ref')))}</code> "
            f"matched=<code>{escape(str(evidence.get('matched')))}</code> "
            f"kind=<code>{escape(str(evidence_kind))}</code> "
            f"raw=<code>{str(evidence.get('raw_content_included', False)).lower()}</code>"
            "</li>"
        )
    if len(signal_evidence) > limit:
        items.append(f"<li>Evidence refs truncated after <code>{limit}</code> of <code>{len(signal_evidence)}</code> refs.</li>")
    return f"<h3>Evidence refs</h3><ul>{''.join(items)}</ul>"


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _input_display_context(root: Path, resolved_input: Path) -> tuple[Path, str]:
    try:
        resolved_input.relative_to(root)
        return root, ""
    except ValueError:
        if resolved_input.exists() and resolved_input.is_dir():
            return resolved_input, "input/"
        return resolved_input.parent, "input/"


def _display_input_path(path: Path, root: Path, input_display_root: Path, input_display_prefix: str) -> str:
    if not input_display_prefix:
        return _display_path(path, root)
    try:
        rel = path.resolve().relative_to(input_display_root.resolve())
    except ValueError:
        return f"{input_display_prefix}{Path(path).name}"
    rel_text = "." if str(rel) == "." else rel.as_posix()
    if rel_text == ".":
        return input_display_prefix.rstrip("/") or "."
    return f"{input_display_prefix}{rel_text}"


def _write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _render_summary(report: dict[str, Any]) -> str:
    if report.get("mode") == "user_input":
        boundary = report["influence_boundary"]
        gate = report["integration_gate"]
        lines = [
            "Local Memory State Influence Boundary Report",
            f"status={report['status']}",
            f"input_kind={report['input_kind']}",
            f"input_file_count={report['input_file_count']}",
            f"candidate_influence_refs={len(boundary['candidate_influence_refs'])}",
            f"inform_only_allowed_refs={len(boundary['inform_only_allowed_refs'])}",
            f"blocked_refs={len(boundary['blocked_refs'])}",
            f"omitted_refs={len(boundary['omitted_refs'])}",
            f"stale_or_superseded_refs={len(boundary['stale_or_superseded_refs'])}",
            "raw_content_included=false",
            f"integration_gate_passed={str(gate['passed']).lower()}",
            f"default_exit_code={gate['default_exit_code']}",
            f"fail_on_blocked_exit_code={gate['fail_on_blocked_exit_code']}",
            "public_claim_created=false",
            "runtime_or_adapter_executed=false",
            "compatibility_claim_created=false",
        ]
        for index, error in enumerate(report.get("errors", [])[:5]):
            lines.append(f"error[{index}]={error}")
        for index, skipped in enumerate(report.get("skipped_inputs", [])[:5]):
            lines.append(f"skipped[{index}]={skipped.get('reason')}:{skipped.get('path')}")
        for index, finding in enumerate(report.get("findings", [])[:5]):
            path = finding.get("path", "")
            recommendation = finding.get("recommendation", "")
            line = f"finding[{index}]={finding.get('severity')}:{finding.get('finding_id')}"
            if path:
                line += f":{path}"
            if recommendation:
                line += f" recommendation={recommendation}"
            lines.append(line)
    else:
        lines = [
            "Memory State Governability Overlay Demo",
            f"status={report['status']}",
            f"surface_count={report['surface_count']}",
            "public_claim_created=false",
            "runtime_or_adapter_executed=false",
            "compatibility_claim_created=false",
        ]
        for profile, count in report["scale_profile_counts"].items():
            lines.append(f"scale_profile[{profile}]={count}")
    lines.extend(report.get("output_files", {}).values())
    return "\n".join(lines)


def _exit_code_for_report(report: dict[str, Any], *, fail_on_blocked: bool = False) -> int:
    if not str(report.get("status", "")).startswith("pass_"):
        return 1
    if fail_on_blocked and report.get("mode") == "user_input":
        blocked_refs = report.get("influence_boundary", {}).get("blocked_refs", [])
        if blocked_refs:
            return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local memory-state governability overlay demo.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--fixture", type=Path, default=FIXTURE)
    parser.add_argument("--input", type=Path, help="Audit a user-supplied memory/context/state file or directory.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--format", choices=("json", "summary", "gate"), default="json")
    parser.add_argument("--fail-on-blocked", action="store_true", help="Exit non-zero when user-input mode finds blocked refs.")
    args = parser.parse_args()
    if args.input:
        report = build_memory_state_influence_boundary_report(
            args.root,
            input_path=args.input,
            output_dir=args.output_dir,
        )
    else:
        report = build_memory_state_governability_overlay_demo(
            args.root,
            fixture_path=args.fixture,
            output_dir=args.output_dir,
        )
    if args.format == "summary":
        print(_render_summary(report))
    elif args.format == "gate":
        gate = report.get("integration_gate")
        if gate is None:
            print(
                json.dumps(
                    {
                        "schema_id": "ctxvault.memory-state-influence-boundary-integration-gate/v0",
                        "status": "fail_integration_gate_unavailable",
                        "reason": "--format gate requires --input mode",
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 1
        print(json.dumps(gate, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return _exit_code_for_report(report, fail_on_blocked=args.fail_on_blocked)


if __name__ == "__main__":
    raise SystemExit(main())
