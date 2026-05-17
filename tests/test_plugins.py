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

from ctxgov.plugins import LocalPluginExecutorRegistry, PluginRegistry, PluginRegistryError


class PluginRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.projection_manifest = json.loads((ROOT / "fixtures" / "evidence" / "plugin-manifest.json").read_text())

    def test_registry_lists_manifests(self) -> None:
        registry = PluginRegistry([self.projection_manifest])
        listed = registry.list_manifests()

        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["id"], "portable-harness-projection")

    def test_registry_resolves_declared_capability(self) -> None:
        registry = PluginRegistry([self.projection_manifest])
        resolution = registry.resolve_capability("projection.harness.agents-md")

        self.assertEqual(resolution.decision, "use_plugin")
        self.assertEqual(resolution.selected_plugin["id"], "portable-harness-projection")
        self.assertEqual(resolution.fallback_policy, "skip-with-receipt")

    def test_registry_resolves_claude_projection_capability(self) -> None:
        registry = PluginRegistry([self.projection_manifest])
        resolution = registry.resolve_capability("projection.harness.claude-md")

        self.assertEqual(resolution.decision, "use_plugin")
        self.assertEqual(resolution.selected_plugin["id"], "portable-harness-projection")
        self.assertEqual(resolution.fallback_policy, "skip-with-receipt")

    def test_registry_resolves_wiki_projection_capability(self) -> None:
        registry = PluginRegistry([self.projection_manifest])
        resolution = registry.resolve_capability("projection.wiki.markdown-workstream")

        self.assertEqual(resolution.decision, "use_plugin")
        self.assertEqual(resolution.selected_plugin["id"], "portable-harness-projection")
        self.assertEqual(resolution.fallback_policy, "skip-with-receipt")

    def test_registry_falls_back_for_unknown_capability(self) -> None:
        registry = PluginRegistry([self.projection_manifest])
        resolution = registry.resolve_capability("workstream.gap-detection")

        self.assertEqual(resolution.decision, "fallback")
        self.assertIsNone(resolution.selected_plugin)
        self.assertEqual(resolution.fallback_policy, "deterministic-only")

    def test_registry_rejects_manifest_missing_required_fields(self) -> None:
        broken = copy.deepcopy(self.projection_manifest)
        broken.pop("produced_outputs")

        with self.assertRaises(PluginRegistryError):
            PluginRegistry([broken])

    def test_local_executor_registry_executes_resolved_capability(self) -> None:
        observed: dict[str, object] = {}

        def fake_executor(arguments: dict[str, object]) -> dict[str, object]:
            observed.update(arguments)
            return {"ok": True, "output_path": str(arguments["output_path"])}

        registry = LocalPluginExecutorRegistry(
            {
                "projection.harness.agents-md": fake_executor,
            }
        )

        result = registry.execute(
            [self.projection_manifest],
            "projection.harness.agents-md",
            {
                "workstream_id": "ws_test",
                "output_path": "/tmp/AGENTS.md",
                "receipt_output_path": "/tmp/agents-receipt.json",
            },
        )

        self.assertEqual(result["plugin"]["id"], "portable-harness-projection")
        self.assertEqual(result["resolution"]["decision"], "use_plugin")
        self.assertEqual(observed["workstream_id"], "ws_test")
        self.assertEqual(result["result"]["ok"], True)

    def test_local_executor_registry_rejects_unimplemented_capability(self) -> None:
        registry = LocalPluginExecutorRegistry({})

        with self.assertRaises(ValueError):
            registry.execute(
                [self.projection_manifest],
                "projection.harness.agents-md",
                {
                    "workstream_id": "ws_test",
                    "output_path": "/tmp/AGENTS.md",
                    "receipt_output_path": "/tmp/agents-receipt.json",
                },
            )


if __name__ == "__main__":
    unittest.main()
