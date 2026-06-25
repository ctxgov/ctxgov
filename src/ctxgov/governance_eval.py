from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


CATEGORIES = ["authority", "capability", "scope", "lifecycle", "evidence", "structural"]


def build_governance_replay_receipts(trace_path: Path, *, checked_at: str | None = None) -> dict[str, Any]:
    trace_path = trace_path.resolve()
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    _reject_live_or_external_trace(trace)
    created_at = checked_at or _utc_now()
    trace_id = str(trace.get("trace_id") or trace_path.stem)
    source_refs = _source_refs(trace)
    target = _target(trace)

    coverage_receipt = _coverage_receipt(trace, trace_id, target, source_refs, created_at)
    context_delta = _context_delta_receipt(trace, trace_id, created_at)
    replay_trace = _replay_trace(trace, trace_id, source_refs, coverage_receipt, context_delta, created_at)

    return {
        "schema_id": "ctxgov.governance-eval-replay-result/v0",
        "trace_path": str(trace_path),
        "trace_id": trace_id,
        "coverage_receipt": coverage_receipt,
        "context_delta_raw_telemetry": context_delta,
        "replay_trace": replay_trace,
        "side_effect_boundary": _side_effect_boundary(),
        "claim_boundary": _claim_boundary(),
    }


def _coverage_receipt(
    trace: dict[str, Any],
    trace_id: str,
    target: dict[str, str],
    source_refs: list[dict[str, str]],
    created_at: str,
) -> dict[str, Any]:
    expected = _coverage_map(trace.get("expected_coverage") or {})
    covered = _coverage_map((trace.get("with_governance") or {}).get("covered") or {})
    category_counts: dict[str, Any] = {}
    total_covered = 0
    total_expected = 0
    total_missing = 0
    for category in CATEGORIES:
        expected_items = set(expected[category])
        covered_items = set(covered[category]) & expected_items
        missing_items = expected_items - covered_items
        category_counts[category] = {
            "covered_count": len(covered_items),
            "expected_count": len(expected_items),
            "missing_count": len(missing_items),
            "evidence_refs": sorted(covered_items),
        }
        total_covered += len(covered_items)
        total_expected += len(expected_items)
        total_missing += len(missing_items)

    return {
        "schema_id": "ctxgov.governance-coverage-receipt/v0",
        "object_type": "GovernanceCoverageReceipt",
        "version": "v0",
        "created_at": created_at,
        "run_id": f"coverage-{_digest({'trace_id': trace_id, 'target': target})}",
        "target": target,
        "source_manifest": {
            "source_kind": "saved-local-source",
            "source_refs": source_refs,
            "raw_source_copied": False,
        },
        "category_counts": category_counts,
        "coverage_summary": {
            "category_count": 6,
            "total_covered_count": total_covered,
            "total_expected_count": total_expected,
            "total_missing_count": total_missing,
            "public_metric_boundary": "bounded_six_category_counts_only",
        },
        "claim_boundary": _claim_boundary(),
        "side_effect_boundary": _side_effect_boundary(),
        "rollback_ref": "rollback://discard-governance-coverage-receipt",
    }


def _context_delta_receipt(trace: dict[str, Any], trace_id: str, created_at: str) -> dict[str, Any]:
    before_units = _context_units((trace.get("without_governance") or {}).get("context_units") or [])
    after_units = _context_units((trace.get("with_governance") or {}).get("context_units") or [])
    before_ids = set(before_units)
    after_ids = set(after_units)
    changed_ids = {unit_id for unit_id in before_ids & after_ids if before_units[unit_id]["digest"] != after_units[unit_id]["digest"]}
    source_refs = sorted({unit["source_ref"] for unit in before_units.values()} | {unit["source_ref"] for unit in after_units.values()})
    rows = []
    for source_ref in source_refs:
        before_count = sum(1 for unit in before_units.values() if unit["source_ref"] == source_ref)
        after_count = sum(1 for unit in after_units.values() if unit["source_ref"] == source_ref)
        rows.append(
            {
                "source_ref": source_ref,
                "before_count": before_count,
                "after_count": after_count,
                "change_count": after_count - before_count,
            }
        )
    return {
        "schema_id": "ctxgov.context-delta-raw-telemetry/v0",
        "object_type": "ContextDeltaRawTelemetry",
        "version": "v0",
        "created_at": created_at,
        "telemetry_id": f"context-delta-{_digest({'trace_id': trace_id, 'rows': rows})}",
        "trace_ref": f"trace://{trace_id}",
        "measurement_boundary": {
            "unit": "context_unit",
            "raw_counts_only": True,
            "interpretation": "raw_counts_only_no_conclusion",
            "derived_claim_created": False,
        },
        "raw_counts": {
            "before_context_unit_count": len(before_units),
            "after_context_unit_count": len(after_units),
            "added_context_unit_count": len(after_ids - before_ids),
            "removed_context_unit_count": len(before_ids - after_ids),
            "changed_context_unit_count": len(changed_ids),
        },
        "rows": rows,
        "claim_boundary": _claim_boundary(),
        "side_effect_boundary": _side_effect_boundary(),
        "rollback_ref": "rollback://discard-context-delta-raw-telemetry",
    }


def _replay_trace(
    trace: dict[str, Any],
    trace_id: str,
    source_refs: list[dict[str, str]],
    coverage_receipt: dict[str, Any],
    context_delta: dict[str, Any],
    created_at: str,
) -> dict[str, Any]:
    without_run = trace.get("without_governance") or {}
    with_run = trace.get("with_governance") or {}
    return {
        "schema_id": "ctxgov.governance-replay-trace/v0",
        "object_type": "GovernanceReplayTrace",
        "version": "v0",
        "created_at": created_at,
        "trace_id": trace_id,
        "replay_mode": "saved-trace-deterministic",
        "without_governance_run": _replay_run(without_run, trace_id, False, source_refs),
        "with_governance_run": _replay_run(with_run, trace_id, True, source_refs),
        "replay_observation": {
            "coverage_receipt_ref": f"receipt://{coverage_receipt['run_id']}",
            "context_delta_raw_telemetry_ref": f"receipt://{context_delta['telemetry_id']}",
            "changed_categories": _changed_categories(trace),
            "interpretation_boundary": "deterministic_replay_observation_only",
        },
        "claim_boundary": _claim_boundary(),
        "side_effect_boundary": _side_effect_boundary(),
        "rollback_ref": "rollback://discard-governance-replay-trace",
    }


def _replay_run(run: dict[str, Any], trace_id: str, governance_enabled: bool, source_refs: list[dict[str, str]]) -> dict[str, Any]:
    label = "with" if governance_enabled else "without"
    return {
        "run_id": str(run.get("run_id") or f"{trace_id}-{label}-governance"),
        "governance_enabled": governance_enabled,
        "input_ref": str(run.get("input_ref") or f"trace://{trace_id}/input"),
        "output_ref": str(run.get("output_ref") or f"trace://{trace_id}/{label}-governance-output"),
        "source_refs": [{"ref": item["ref"], "sha256": item["sha256"]} for item in source_refs],
    }


def _target(trace: dict[str, Any]) -> dict[str, str]:
    raw = trace.get("target") or {}
    return {
        "target_id": str(raw.get("target_id") or raw.get("id") or trace.get("trace_id") or "target"),
        "target_kind": str(raw.get("target_kind") or "saved-trace-fixture"),
        "target_ref": str(raw.get("target_ref") or raw.get("ref") or "trace://saved-local"),
    }


def _source_refs(trace: dict[str, Any]) -> list[dict[str, str]]:
    source_refs = []
    for item in trace.get("source_refs") or []:
        ref = str(item.get("ref") or item.get("source_ref") or "")
        sha256 = str(item.get("sha256") or "")
        if not ref or not sha256:
            raise ValueError("source_refs require ref and sha256")
        source_refs.append({"ref": ref, "sha256": sha256, "redaction_state": str(item.get("redaction_state") or "none")})
    if not source_refs:
        encoded = json.dumps(trace, ensure_ascii=True, sort_keys=True).encode()
        source_refs.append({"ref": "trace://inline", "sha256": hashlib.sha256(encoded).hexdigest(), "redaction_state": "none"})
    return source_refs


def _coverage_map(raw: dict[str, Any]) -> dict[str, list[str]]:
    return {category: [str(item) for item in raw.get(category, [])] for category in CATEGORIES}


def _context_units(raw_units: list[Any]) -> dict[str, dict[str, str]]:
    units: dict[str, dict[str, str]] = {}
    for index, item in enumerate(raw_units):
        if isinstance(item, dict):
            unit_id = str(item.get("id") or item.get("unit_id") or f"unit-{index}")
            source_ref = str(item.get("source_ref") or "trace://context")
            supplied_digest = item.get("sha256") or item.get("digest")
            if isinstance(supplied_digest, str) and len(supplied_digest) == 64:
                digest = supplied_digest
            else:
                text = str(item.get("text") or item.get("content") or "")
                digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        else:
            unit_id = f"unit-{index}"
            text = str(item)
            source_ref = "trace://context"
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        units[unit_id] = {"digest": digest, "source_ref": source_ref}
    return units


def _changed_categories(trace: dict[str, Any]) -> list[str]:
    before = _coverage_map((trace.get("without_governance") or {}).get("covered") or {})
    after = _coverage_map((trace.get("with_governance") or {}).get("covered") or {})
    return [category for category in CATEGORIES if set(before[category]) != set(after[category])]


def _reject_live_or_external_trace(trace: dict[str, Any]) -> None:
    forbidden = [
        "network_call_performed",
        "provider_model_call_performed",
        "api_call_performed",
        "scheduler_or_daemon_started",
        "target_file_written",
        "public_repo_written",
        "package_published",
        "live_model_call_performed",
    ]
    _reject_forbidden_side_effects(trace, forbidden)


def _reject_forbidden_side_effects(value: Any, forbidden: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden and item is True:
                raise ValueError(f"saved replay trace declares forbidden side effect: {key}")
            _reject_forbidden_side_effects(item, forbidden)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_side_effects(item, forbidden)


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_call_performed": False,
        "provider_model_call_performed": False,
        "api_call_performed": False,
        "live_model_call_performed": False,
        "scheduler_or_daemon_started": False,
        "target_file_written": False,
        "public_repo_written": False,
        "package_published": False,
    }


def _claim_boundary() -> dict[str, bool]:
    return {
        "public_claim_created": False,
        "comparative_outcome_claim_created": False,
        "external_use_claim_created": False,
        "readiness_or_certification_claim_created": False,
        "universal_fit_claim_created": False,
        "result_authority_claim_created": False,
        "protocol_guarantee_claim_created": False,
    }


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode()).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
