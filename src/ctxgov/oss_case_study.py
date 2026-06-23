from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any


OSS_CASE_STUDY_PREVIEW_SCHEMA_ID = "ctxvault.public-oss-case-study-preview/v0"


def build_oss_case_study_preview(
    *,
    target_name: str,
    source_path: Path,
    repo_url: str | None,
    pinned_ref: str,
    license_name: str = "unknown",
    checked_at: str | None = None,
    max_source_bytes: int = 262144,
) -> dict[str, Any]:
    source = source_path.resolve()
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(f"source path does not exist or is not a file: {source}")
    raw = source.read_bytes()
    truncated = len(raw) > max_source_bytes
    raw = raw[:max_source_bytes]
    text = raw.decode("utf-8", "replace")
    return {
        "schema_id": OSS_CASE_STUDY_PREVIEW_SCHEMA_ID,
        "created_at": checked_at or _utc_now(),
        "target": {"target_name": target_name, "repo_url": repo_url, "pinned_ref": pinned_ref, "license": license_name},
        "source": {"path": str(source), "sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw), "line_count": len(text.splitlines()), "truncated": truncated},
        "source_descriptive_preview": {"heading_count": sum(1 for line in text.splitlines() if line.lstrip().startswith("#")), "mentions_target": target_name.lower() in text.lower(), "sample": _compact(text)},
        "authority_layers": _authority_layers(),
        "safe_rewrites": _safe_rewrites(),
        "claim_boundary": _claim_boundary(),
        "side_effect_boundary": _side_effect_boundary(),
    }


def _authority_layers() -> dict[str, dict[str, Any]]:
    return {
        "claim": {"decision": "source_descriptive_only", "blocked": ["quality", "security", "performance", "compatibility", "maintainer_endorsement"]},
        "context": {"decision": "preview_only_with_caveats", "blocked": ["private_refs", "uninspected_target_files"]},
        "memory": {"decision": "not_promoted", "blocked": ["durable_memory_promotion"]},
        "action": {"decision": "not_executed", "blocked": ["target_writes", "runtime_execution", "provider_or_model_calls", "outreach"]},
    }


def _safe_rewrites() -> list[dict[str, str]]:
    return [
        {"unsafe_claim": "The target project is secure.", "safe_rewrite": "The preview did not evaluate target project security."},
        {"unsafe_claim": "The target project is compatible with CtxGov.", "safe_rewrite": "The preview reads saved source material and does not run compatibility checks."},
        {"unsafe_claim": "The target maintainers endorse this preview.", "safe_rewrite": "No maintainer endorsement is claimed."},
    ]


def _claim_boundary() -> dict[str, bool]:
    return {
        "maintainer_endorsement_claim_created": False,
        "compatibility_claim_created": False,
        "security_claim_created": False,
        "runtime_validation_claim_created": False,
        "target_quality_claim_created": False,
        "public_adoption_claim_created": False,
    }


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_access_performed": False,
        "external_clone_performed": False,
        "target_repo_modified": False,
        "target_file_written": False,
        "provider_or_model_call_performed": False,
        "runtime_or_adapter_executed": False,
        "outreach_performed": False,
    }


def _compact(text: str, limit: int = 360) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3].rstrip() + "..."


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
