from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.adapters import AdapterRegistry


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.disabled_profile = json.loads((ROOT / "fixtures" / "evidence" / "adapter-capability-profile.json").read_text())

    def test_disabled_profile_falls_back_deterministically(self) -> None:
        registry = AdapterRegistry([self.disabled_profile])
        resolution = registry.resolve_capability("projection.harness.agents-md")

        self.assertEqual(resolution.decision, "fallback")
        self.assertEqual(resolution.fallback_policy, "deterministic_only")
        self.assertIsNone(resolution.selected_profile)

    def test_healthy_profile_is_selected_for_matching_projection_target(self) -> None:
        local_profile = copy.deepcopy(self.disabled_profile)
        local_profile["id"] = "adapter_local_codex"
        local_profile["mode"] = "local"
        local_profile["harness_name"] = "codex"
        local_profile["supported_projection_types"] = ["projection.harness.agents-md", "projection.harness.claude-md"]
        local_profile["required_files"] = ["AGENTS.md"]
        local_profile["optional_files"] = [".agent/context.json"]
        local_profile["hook_support"] = ["repo-local"]
        local_profile["health_state"] = "healthy"

        registry = AdapterRegistry([self.disabled_profile, local_profile])
        resolution = registry.resolve_capability("projection.harness.agents-md")

        self.assertEqual(resolution.decision, "use_adapter")
        self.assertEqual(resolution.selected_profile["id"], "adapter_local_codex")
        self.assertEqual(resolution.selected_profile["harness_name"], "codex")

    def test_health_recording_updates_profile(self) -> None:
        local_profile = copy.deepcopy(self.disabled_profile)
        local_profile["id"] = "adapter_local_cursor"
        local_profile["mode"] = "local"
        local_profile["harness_name"] = "cursor"
        local_profile["supported_projection_types"] = ["projection.harness.cursor-rules"]
        local_profile["health_state"] = "unknown"

        registry = AdapterRegistry([local_profile])
        updated = registry.record_health("adapter_local_cursor", available=True, checked_at="2026-04-19T14:05:00Z")

        self.assertEqual(updated["health_state"], "healthy")
        self.assertEqual(updated["last_checked_at"], "2026-04-19T14:05:00Z")

    def test_registry_normalizes_legacy_capability_fields(self) -> None:
        legacy_profile = {
            "id": "adapter_legacy_codex",
            "mode": "local",
            "provider": "codex",
            "enabled_capabilities": ["projection.harness.agents-md"],
            "health": "healthy",
            "fallback_policy": "deterministic_only",
            "updated_at": "2026-04-19T14:05:00Z",
        }

        registry = AdapterRegistry([legacy_profile])
        listed = registry.list_profiles()

        self.assertEqual(listed[0]["harness_name"], "codex")
        self.assertEqual(listed[0]["supported_projection_types"], ["projection.harness.agents-md"])
        self.assertEqual(listed[0]["health_state"], "healthy")


if __name__ == "__main__":
    unittest.main()
