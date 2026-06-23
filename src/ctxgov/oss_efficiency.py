from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


OSS_EFFICIENCY_MANIFEST_SCHEMA_ID = "ctxgov.public-oss-efficiency-raw-telemetry-manifest/v0"
OSS_EFFICIENCY_RECEIPT_SCHEMA_ID = "ctxgov.public-oss-efficiency-raw-telemetry-receipt/v0"
METRIC_FIELDS = ("token_count", "elapsed_seconds", "command_count", "manual_review_seconds", "rework_count")


def evaluate_oss_efficiency_manifest(
    manifest_path: Path,
    *,
    telemetry_paths: list[Path] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    manifest = manifest_path.resolve()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if payload.get("schema_id") != OSS_EFFICIENCY_MANIFEST_SCHEMA_ID:
        raise ValueError(f"unsupported raw telemetry manifest schema_id: {payload.get('schema_id')}")
    cases = list(payload.get("raw_telemetry_cases") or [])
    for telemetry_path in telemetry_paths or []:
        cases.extend(_load_extra_telemetry(telemetry_path.resolve()))
    case_results = [_evaluate_case(case) for case in cases]
    return {
        "schema_id": OSS_EFFICIENCY_RECEIPT_SCHEMA_ID,
        "created_at": checked_at or _utc_now(),
        "status": "public_raw_measurement_methodology_not_efficiency_claim",
        "manifest": {"path": str(manifest), "sha256": _sha256(manifest), "case_count": len(cases)},
        "case_results": case_results,
        "measurement_boundary": {
            "not_generalized": True,
            "public_efficiency_claim_created": False,
            "public_benchmark_claim_created": False,
            "public_adoption_claim_created": False,
            "provider_compatibility_claim_created": False,
            "stable_protocol_claim_created": False,
        },
        "side_effect_boundary": _side_effect_boundary(),
    }


def validate_oss_efficiency_receipt_file(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    errors: list[str] = []
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"schema_id": "ctxvault.public-oss-efficiency-validate-result/v0", "valid": False, "errors": [str(exc)]}
    if payload.get("schema_id") != OSS_EFFICIENCY_RECEIPT_SCHEMA_ID:
        errors.append("unexpected schema_id")
    for section in ("measurement_boundary", "side_effect_boundary"):
        values = payload.get(section) or {}
        if not isinstance(values, dict):
            errors.append(f"{section} must be an object")
            continue
        for key, value in values.items():
            if key == "not_generalized":
                if value is not True:
                    errors.append("not_generalized must be true")
            elif value is not False:
                errors.append(f"{section}.{key} must be false")
    return {"schema_id": "ctxvault.public-oss-efficiency-validate-result/v0", "valid": not errors, "errors": errors, "path": str(resolved)}


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    baseline = dict(case.get("baseline_observation") or {})
    observed = dict(case.get("ctxgov_observation") or {})
    return {
        "case_id": str(case.get("case_id") or "case"),
        "repo": str(case.get("repo") or "unknown"),
        "commit_sha": str(case.get("commit_sha") or ""),
        "task_type": str(case.get("task_type") or "unknown"),
        "baseline_observation": _numeric_metrics(baseline),
        "ctxgov_observation": _numeric_metrics(observed),
    }


def _numeric_metrics(values: dict[str, Any]) -> dict[str, float]:
    return {field: _number(values.get(field)) for field in METRIC_FIELDS}


def _load_extra_telemetry(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        return list(payload.get("raw_telemetry_cases") or [])
    if isinstance(payload, list):
        return payload
    raise ValueError("extra telemetry must be JSON list, JSONL, or manifest object")


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_access_performed": False,
        "external_clone_performed": False,
        "target_repo_modified": False,
        "target_file_written": False,
        "provider_or_model_call_performed": False,
        "runtime_or_adapter_executed": False,
        "memory_backend_written": False,
        "memory_promotion_performed": False,
        "public_release_created": False,
        "package_published": False,
        "outreach_performed": False,
        "target_issue_or_pr_created": False,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
