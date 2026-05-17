from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any


HARNESS_SURFACE_SCHEMA_VERSION = "ctxvault.harness-surface/v1"
RUNTIME_EVENT_RECEIPT_SCHEMA_VERSION = "ctxvault.runtime-event-receipt/v1"
PROJECTION_HEALTHCHECK_SCHEMA_VERSION = "ctxvault.projection-healthcheck/v1"

HEALTH_PRIORITY = {
    "healthy": 0,
    "degraded": 1,
    "unknown": 2,
    "offline": 3,
}

MODE_PRIORITY = {
    "local": 0,
    "remote": 1,
    "disabled": 2,
}

PROJECTION_HEALTHCHECK_TARGETS: tuple[dict[str, Any], ...] = (
    {
        "canonical": "agents-md",
        "aliases": {"agents-md", "harness.agents-md"},
        "surface_id": "harness.agents-md.local",
        "target_kind": "agents_md",
        "target_name": "AGENTS.md local harness projection",
        "adapter_id": "projection.harness.agents-md",
        "healthcheck_prefix": "phc_agents_md",
        "output_kind": "harness_instructions",
        "path_pattern": "AGENTS.md",
        "default_relative_path": Path("AGENTS.md"),
        "requested_outputs": ["AGENTS.md"],
        "source_refs": ["doc://ctxvault/v0.2-m15-contract-drafts"],
        "lossiness": ["target file cannot preserve the full evidence graph inline"],
        "unsupported_features": ["live harness command inspection"],
        "warnings": ["write only reviewed context and emit a projection receipt"],
        "verification_commands": ["python3 scripts/run_context_injection_m1_golden_path.py"],
        "next_action_label": "AGENTS.md",
    },
    {
        "canonical": "claude-md",
        "aliases": {"claude-md", "harness.claude-md"},
        "surface_id": "harness.claude-md.local",
        "target_kind": "claude_md",
        "target_name": "CLAUDE.md local harness projection",
        "adapter_id": "projection.harness.claude-md",
        "healthcheck_prefix": "phc_claude_md",
        "output_kind": "harness_instructions",
        "path_pattern": "CLAUDE.md",
        "default_relative_path": Path("CLAUDE.md"),
        "requested_outputs": ["CLAUDE.md"],
        "source_refs": ["doc://ctxvault/v0.2-m15-contract-drafts"],
        "lossiness": ["target file cannot preserve the full evidence graph inline"],
        "unsupported_features": ["live Claude command inspection"],
        "warnings": ["write only reviewed context and emit a projection receipt"],
        "verification_commands": ["python3 scripts/run_context_injection_m1_golden_path.py"],
        "next_action_label": "CLAUDE.md",
    },
    {
        "canonical": "workstream-brief",
        "aliases": {"workstream-brief", "human-readable-brief", "wiki.markdown-workstream"},
        "surface_id": "brief.workstream-markdown.local",
        "target_kind": "workstream_brief",
        "target_name": "Human-readable workstream brief markdown projection",
        "adapter_id": "projection.wiki.markdown-workstream",
        "healthcheck_prefix": "phc_workstream_brief",
        "output_kind": "workstream_brief",
        "path_pattern": "workstreams/<workstream-id>.md",
        "default_relative_path": Path("workstreams") / "workstream-brief.md",
        "requested_outputs": ["workstreams/<workstream-id>.md"],
        "source_refs": ["doc://ctxvault/v0.2-source-coverage-readiness-plan"],
        "lossiness": ["brief markdown is a curated view and cannot preserve the full evidence graph inline"],
        "unsupported_features": ["automatic brief destination discovery"],
        "warnings": ["write only reviewed context and emit a projection receipt"],
        "verification_commands": ["python3 scripts/run_deterministic_checks.py"],
        "next_action_label": "workstream brief",
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class AdapterResolution:
    capability: str
    selected_profile: dict[str, Any] | None
    decision: str
    fallback_policy: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "selected_profile": self.selected_profile,
            "decision": self.decision,
            "fallback_policy": self.fallback_policy,
            "reasons": self.reasons,
        }


class AdapterRegistry:
    def __init__(self, profiles: list[dict[str, Any]] | None = None):
        self._profiles = [self._normalized_profile(profile) for profile in (profiles or [])]

    @classmethod
    def from_path(cls, path: Path) -> "AdapterRegistry":
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            return cls(payload)
        return cls([payload])

    @classmethod
    def from_config(cls, *, mode: str, allow_remote: bool) -> "AdapterRegistry":
        profile = {
            "id": "adapter_config_default",
            "mode": mode,
            "harness_name": "configured-default",
            "supported_projection_types": [],
            "required_files": [],
            "optional_files": [],
            "hook_support": [],
            "health_state": "offline" if mode == "disabled" else "unknown",
            "fallback_policy": "deterministic_only" if not allow_remote else "human_review_only",
            "last_checked_at": None,
            "updated_at": _utc_now(),
        }
        return cls([profile])

    def list_profiles(self) -> list[dict[str, Any]]:
        return [dict(profile) for profile in self._sorted_profiles(self._profiles)]

    def resolve_capability(self, capability: str) -> AdapterResolution:
        matching = [
            dict(profile)
            for profile in self._sorted_profiles(self._profiles)
            if capability in list(profile.get("supported_projection_types", []))
        ]
        if not matching:
            fallback = self._fallback_policy()
            return AdapterResolution(
                capability=capability,
                selected_profile=None,
                decision="fallback",
                fallback_policy=fallback,
                reasons=["no adapter profile declares this projection target"],
            )

        selected = matching[0]
        health = str(selected.get("health_state", "unknown"))
        if health == "healthy":
            decision = "use_adapter"
            reasons = ["selected adapter supports the requested projection and is healthy"]
        elif health == "degraded":
            decision = "use_with_caution"
            reasons = ["selected adapter supports the requested projection but is degraded"]
        else:
            decision = "fallback"
            reasons = [f"selected adapter health_state is {health}"]

        return AdapterResolution(
            capability=capability,
            selected_profile=selected,
            decision=decision,
            fallback_policy=str(selected.get("fallback_policy", self._fallback_policy())),
            reasons=reasons,
        )

    def record_health(self, profile_id: str, *, available: bool, checked_at: str | None = None) -> dict[str, Any]:
        for index, profile in enumerate(self._profiles):
            if profile.get("id") != profile_id:
                continue

            updated = dict(profile)
            if updated.get("mode") == "disabled":
                updated["health_state"] = "offline"
            else:
                updated["health_state"] = "healthy" if available else "offline"
            updated["last_checked_at"] = checked_at or _utc_now()
            updated["updated_at"] = checked_at or _utc_now()
            self._profiles[index] = updated
            return dict(updated)

        raise KeyError(f"unknown adapter profile {profile_id}")

    def _fallback_policy(self) -> str:
        if not self._profiles:
            return "deterministic_only"
        return str(self._profiles[0].get("fallback_policy", "deterministic_only"))

    def _sorted_profiles(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            profiles,
            key=lambda profile: (
                HEALTH_PRIORITY.get(str(profile.get("health_state", "unknown")), 99),
                MODE_PRIORITY.get(str(profile.get("mode", "disabled")), 99),
                str(profile.get("id", "")),
            ),
        )

    def _normalized_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(profile, dict):
            raise ValueError("adapter profile must be an object")
        mode = str(profile.get("mode", "disabled"))
        harness_name = str(profile.get("harness_name") or profile.get("provider") or "unknown-harness")
        supported_projection_types = self._string_list(
            profile.get("supported_projection_types") or profile.get("enabled_capabilities")
        )
        required_files = self._string_list(profile.get("required_files"))
        optional_files = self._string_list(profile.get("optional_files"))
        hook_support = self._string_list(profile.get("hook_support"))
        health_state = str(profile.get("health_state") or profile.get("health") or ("offline" if mode == "disabled" else "unknown"))
        normalized = {
            "id": str(profile.get("id") or ""),
            "mode": mode,
            "harness_name": harness_name,
            "supported_projection_types": supported_projection_types,
            "required_files": required_files,
            "optional_files": optional_files,
            "hook_support": hook_support,
            "health_state": health_state,
            "fallback_policy": str(profile.get("fallback_policy", "deterministic_only")),
            "last_checked_at": profile.get("last_checked_at"),
            "updated_at": str(profile.get("updated_at") or _utc_now()),
        }
        return normalized

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _projection_healthcheck_target_spec(target_kind: str) -> dict[str, Any]:
    normalized = target_kind.strip().lower().replace("_", "-")
    for spec in PROJECTION_HEALTHCHECK_TARGETS:
        if normalized == spec["canonical"] or normalized in spec["aliases"]:
            return spec
    supported = ", ".join(spec["canonical"] for spec in PROJECTION_HEALTHCHECK_TARGETS)
    raise ValueError(f"unsupported adapter healthcheck target {target_kind}; supported targets: {supported}")


def projection_harness_surface_inventory(
    target_kind: str = "agents-md",
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    spec = _projection_healthcheck_target_spec(target_kind)
    checked_at = generated_at or _utc_now()
    return {
        "schema_id": HARNESS_SURFACE_SCHEMA_VERSION,
        "surface_id": spec["surface_id"],
        "target_kind": spec["target_kind"],
        "target_name": spec["target_name"],
        "target_version": "unknown",
        "inventory_version": "experimental-2026-04-27",
        "generated_at": checked_at,
        "provenance": {
            "source_refs": list(spec["source_refs"]),
            "capture_method": "manual_static_inventory",
        },
        "trust_state": "experimental_local",
        "projection_capabilities": [
            {
                "output_kind": spec["output_kind"],
                "path_pattern": spec["path_pattern"],
                "write_mode": "replace_with_receipt",
                "requires_reviewed_context": True,
            }
        ],
        "command_surfaces": [],
        "tool_surfaces": [],
        "permission_gates": [
            {
                "gate": "projection_write",
                "decision_source": "ctxvault.policy",
            },
            {
                "gate": "reviewed_context_only",
                "decision_source": "ctxvault.review_state",
            },
        ],
        "runtime_modes": ["read_only_healthcheck", "deterministic_projection"],
        "event_shapes": ["adapter_healthcheck", "projection_write"],
        "lossiness": list(spec["lossiness"]),
        "unsupported_features": list(spec["unsupported_features"]),
        "warnings": list(spec["warnings"]),
        "verification_commands": list(spec["verification_commands"]),
        "healthcheck_refs": [],
        "review_state": "draft",
    }


def agents_md_harness_surface_inventory(*, generated_at: str | None = None) -> dict[str, Any]:
    return projection_harness_surface_inventory("agents-md", generated_at=generated_at)


def claude_md_harness_surface_inventory(*, generated_at: str | None = None) -> dict[str, Any]:
    return projection_harness_surface_inventory("claude-md", generated_at=generated_at)


def workstream_brief_harness_surface_inventory(*, generated_at: str | None = None) -> dict[str, Any]:
    return projection_harness_surface_inventory("workstream-brief", generated_at=generated_at)


def projection_adapter_healthcheck(
    *,
    root: Path,
    target_kind: str = "agents-md",
    target_path: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    spec = _projection_healthcheck_target_spec(target_kind)
    timestamp = checked_at or _utc_now()
    resolved_root = root.resolve()
    requested_target = target_path or (resolved_root / spec["default_relative_path"])
    resolved_target = requested_target if requested_target.is_absolute() else resolved_root / requested_target
    resolved_target = resolved_target.resolve()
    target_parent = resolved_target.parent
    target_exists = resolved_target.exists()
    target_is_file = resolved_target.is_file() if target_exists else False
    target_parent_exists = target_parent.exists()
    target_writable = _is_path_writable(resolved_target)
    target_text = _safe_read_text(resolved_target) if target_is_file else ""
    generated_marker_present = "Generated by CtxVault" in target_text
    untracked_private_sections = target_exists and not generated_marker_present

    preflight_checks = [
        _healthcheck_row(
            "harness_surface_known",
            "pass",
            "static experimental inventory is available",
        ),
        _healthcheck_row(
            "target_parent_exists",
            "pass" if target_parent_exists else "fail",
            "target parent exists" if target_parent_exists else "target parent does not exist",
        ),
        _healthcheck_row(
            "target_writable",
            "pass" if target_writable else "fail",
            "target path is writable or can be created" if target_writable else "target path is not writable",
        ),
        _healthcheck_row(
            "target_is_generated_or_new",
            "pass" if not untracked_private_sections else "warn",
            "target is new or already marked as a CtxVault projection"
            if not untracked_private_sections
            else "target exists without the CtxVault projection marker",
        ),
        _healthcheck_row(
            "reviewed_context_only",
            "pass",
            "adapter requires reviewed context before projection writes",
        ),
        _healthcheck_row(
            "projection_receipt_required",
            "pass",
            "adapter requires a projection receipt for every write",
        ),
    ]
    status = _aggregate_healthcheck_status(preflight_checks)
    policy_decision = {"pass": "allow", "warn": "warn", "fail": "deny"}[status]
    warnings = [row["reason"] for row in preflight_checks if row["status"] == "warn"]
    if status == "fail":
        warnings.extend(row["reason"] for row in preflight_checks if row["status"] == "fail")

    surface_inventory = projection_harness_surface_inventory(spec["canonical"], generated_at=timestamp)
    healthcheck_id = f"{spec['healthcheck_prefix']}_{_stable_suffix(str(resolved_target))}"
    runtime_event_receipt = {
        "schema_id": RUNTIME_EVENT_RECEIPT_SCHEMA_VERSION,
        "receipt_id": f"rtrec_{healthcheck_id}",
        "event_id": f"evt_{healthcheck_id}",
        "event_kind": "adapter_healthcheck",
        "occurred_at": timestamp,
        "actor": "ctxvault.adapter-healthcheck",
        "target_surface_id": surface_inventory["surface_id"],
        "scope": {
            "scope_kind": "project",
            "scope_value": resolved_root.name or "unknown",
        },
        "input_refs": [f"file://{resolved_target}"],
        "selected_refs": [f"surface://{surface_inventory['surface_id']}"],
        "excluded_refs": [],
        "policy_checks": [
            {
                "operation": "projection_healthcheck",
                "decision": policy_decision,
                "reason": "read_only_preflight",
            }
        ],
        "permission_decisions": [],
        "budget": {
            "token_budget": None,
            "token_estimate": None,
            "byte_budget": None,
            "byte_estimate": None,
        },
        "output_ref": f"healthcheck://{healthcheck_id}",
        "output_hash": None,
        "warnings": warnings,
        "verification": {
            "command": f"python3 -m ctxgov.cli adapter-healthcheck --target-kind {spec['canonical']}",
            "status": status,
        },
        "review_state": "not_required",
    }

    return {
        "schema_id": PROJECTION_HEALTHCHECK_SCHEMA_VERSION,
        "healthcheck_id": healthcheck_id,
        "adapter_id": spec["adapter_id"],
        "target_surface_id": surface_inventory["surface_id"],
        "checked_at": timestamp,
        "root_ref": f"file://{resolved_root}",
        "requested_outputs": list(spec["requested_outputs"]),
        "required_capabilities": ["replace_with_receipt", "reviewed_context_only"],
        "observed_state": {
            "target_path": str(resolved_target),
            "target_exists": target_exists,
            "target_is_file": target_is_file,
            "target_parent_exists": target_parent_exists,
            "target_writable": target_writable,
            "generated_marker_present": generated_marker_present,
            "untracked_private_sections": untracked_private_sections,
        },
        "preflight_checks": preflight_checks,
        "policy_decision": policy_decision,
        "write_plan": [
            {
                "path": str(resolved_target),
                "mode": "replace",
                "requires_receipt": True,
                "requires_reviewed_context": True,
                "will_write": False,
            }
        ],
        "receipt_plan": [
            {
                "schema_id": "ctxvault.projection-receipt/v1",
                "kind": "projection_receipt",
                "required": True,
            },
            {
                "schema_id": RUNTIME_EVENT_RECEIPT_SCHEMA_VERSION,
                "kind": "runtime_event_receipt",
                "required": False,
            },
        ],
        "status": status,
        "warnings": warnings,
        "next_actions": _healthcheck_next_actions(status, untracked_private_sections, spec["next_action_label"]),
        "harness_surface": surface_inventory,
        "runtime_event_receipt": runtime_event_receipt,
    }


def agents_md_projection_healthcheck(
    *,
    root: Path,
    target_path: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    return projection_adapter_healthcheck(
        root=root,
        target_kind="agents-md",
        target_path=target_path,
        checked_at=checked_at,
    )


def claude_md_projection_healthcheck(
    *,
    root: Path,
    target_path: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    return projection_adapter_healthcheck(
        root=root,
        target_kind="claude-md",
        target_path=target_path,
        checked_at=checked_at,
    )


def workstream_brief_projection_healthcheck(
    *,
    root: Path,
    target_path: Path | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    return projection_adapter_healthcheck(
        root=root,
        target_kind="workstream-brief",
        target_path=target_path,
        checked_at=checked_at,
    )


def _healthcheck_row(check: str, status: str, reason: str) -> dict[str, str]:
    return {
        "check": check,
        "status": status,
        "reason": reason,
    }


def _aggregate_healthcheck_status(rows: list[dict[str, str]]) -> str:
    statuses = {row["status"] for row in rows}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "pass"


def _healthcheck_next_actions(status: str, untracked_private_sections: bool, target_label: str) -> list[str]:
    if status == "fail":
        return ["fix target path permissions or parent directory before projection writes"]
    if untracked_private_sections:
        return [f"review the existing {target_label} manually before allowing replace-mode projection"]
    return ["projection adapter can proceed after normal reviewed-context checks"]


def _is_path_writable(path: Path) -> bool:
    if path.exists():
        return path.is_file() and os.access(path, os.W_OK)
    parent = path.parent
    return parent.exists() and os.access(parent, os.W_OK)


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _stable_suffix(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
