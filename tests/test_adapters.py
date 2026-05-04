from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.adapters import (
    HARNESS_SURFACE_SCHEMA_VERSION,
    PROJECTION_HEALTHCHECK_SCHEMA_VERSION,
    RUNTIME_EVENT_RECEIPT_SCHEMA_VERSION,
    AdapterRegistry,
    agents_md_harness_surface_inventory,
    agents_md_projection_healthcheck,
    claude_md_projection_healthcheck,
    workstream_brief_projection_healthcheck,
)


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

    def test_agents_md_harness_surface_inventory_is_experimental_local(self) -> None:
        inventory = agents_md_harness_surface_inventory(generated_at="2026-04-27T00:00:00+00:00")

        self.assertEqual(inventory["schema_id"], HARNESS_SURFACE_SCHEMA_VERSION)
        self.assertEqual(inventory["surface_id"], "harness.agents-md.local")
        self.assertEqual(inventory["trust_state"], "experimental_local")
        self.assertEqual(inventory["projection_capabilities"][0]["path_pattern"], "AGENTS.md")
        self.assertTrue(inventory["projection_capabilities"][0]["requires_reviewed_context"])

    def test_agents_md_projection_healthcheck_is_read_only_and_passes_for_new_target(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "AGENTS.md"

            result = agents_md_projection_healthcheck(
                root=root,
                target_path=target,
                checked_at="2026-04-27T00:00:00+00:00",
            )

            self.assertEqual(result["schema_id"], PROJECTION_HEALTHCHECK_SCHEMA_VERSION)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["policy_decision"], "allow")
            self.assertFalse(result["observed_state"]["target_exists"])
            self.assertFalse(target.exists())
            self.assertEqual(result["harness_surface"]["schema_id"], HARNESS_SURFACE_SCHEMA_VERSION)
            self.assertEqual(result["runtime_event_receipt"]["schema_id"], RUNTIME_EVENT_RECEIPT_SCHEMA_VERSION)
            self.assertEqual(result["runtime_event_receipt"]["event_kind"], "adapter_healthcheck")
            self.assertFalse(result["write_plan"][0]["will_write"])

    def test_agents_md_projection_healthcheck_warns_before_replacing_manual_target(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "AGENTS.md"
            target.write_text("# Manual agent rules\n", encoding="utf-8")

            result = agents_md_projection_healthcheck(
                root=root,
                target_path=target,
                checked_at="2026-04-27T00:00:00+00:00",
            )

            self.assertEqual(result["status"], "warn")
            self.assertEqual(result["policy_decision"], "warn")
            self.assertTrue(result["observed_state"]["untracked_private_sections"])
            self.assertTrue(result["warnings"])

    def test_projection_healthcheck_supports_claude_md(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "CLAUDE.md"

            result = claude_md_projection_healthcheck(
                root=root,
                target_path=target,
                checked_at="2026-04-27T00:00:00+00:00",
            )

            self.assertEqual(result["adapter_id"], "projection.harness.claude-md")
            self.assertEqual(result["target_surface_id"], "harness.claude-md.local")
            self.assertEqual(result["harness_surface"]["target_kind"], "claude_md")
            self.assertEqual(result["requested_outputs"], ["CLAUDE.md"])
            self.assertEqual(result["status"], "pass")
            self.assertFalse(result["write_plan"][0]["will_write"])
            self.assertFalse(target.exists())

    def test_projection_healthcheck_supports_workstream_brief(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "workstreams" / "brief.md"

            result = workstream_brief_projection_healthcheck(
                root=root,
                target_path=target,
                checked_at="2026-04-27T00:00:00+00:00",
            )

            self.assertEqual(result["adapter_id"], "projection.wiki.markdown-workstream")
            self.assertEqual(result["target_surface_id"], "brief.workstream-markdown.local")
            self.assertEqual(result["harness_surface"]["target_kind"], "workstream_brief")
            self.assertEqual(result["requested_outputs"], ["workstreams/<workstream-id>.md"])
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["policy_decision"], "deny")
            self.assertFalse(result["write_plan"][0]["will_write"])
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
