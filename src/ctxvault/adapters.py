from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


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
