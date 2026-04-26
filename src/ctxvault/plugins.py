from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Callable


RUNTIME_PRIORITY = {
    "deterministic-local": 0,
    "local-model": 1,
    "external-tool": 2,
}

SIDE_EFFECT_PRIORITY = {
    "none": 0,
    "governed-candidates": 1,
    "local-files": 2,
    "external-action": 3,
}

REQUIRED_MANIFEST_FIELDS = {
    "schema_version",
    "id",
    "version",
    "display_name",
    "description",
    "kind",
    "capabilities",
    "runtime",
    "accepted_inputs",
    "produced_outputs",
    "side_effect_level",
    "requires_review",
    "requires_network",
    "fallback_policy",
    "supported_surfaces",
    "healthcheck",
}


class PluginRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class PluginResolution:
    capability: str
    selected_plugin: dict[str, Any] | None
    decision: str
    fallback_policy: str
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "selected_plugin": self.selected_plugin,
            "decision": self.decision,
            "fallback_policy": self.fallback_policy,
            "reasons": self.reasons,
        }


LocalPluginExecutor = Callable[[dict[str, Any]], dict[str, Any]]


class PluginRegistry:
    def __init__(self, manifests: list[dict[str, Any]] | None = None):
        self._manifests = [self._validated_manifest(manifest) for manifest in (manifests or [])]

    @classmethod
    def from_path(cls, path: Path) -> "PluginRegistry":
        payload = json.loads(path.read_text())
        if isinstance(payload, list):
            return cls(payload)
        return cls([payload])

    @classmethod
    def from_paths(cls, paths: list[Path]) -> "PluginRegistry":
        manifests: list[dict[str, Any]] = []
        for path in paths:
            payload = json.loads(path.read_text())
            if isinstance(payload, list):
                manifests.extend(payload)
            else:
                manifests.append(payload)
        return cls(manifests)

    def list_manifests(self) -> list[dict[str, Any]]:
        return [dict(manifest) for manifest in self._sorted_manifests(self._manifests)]

    def get_manifest(self, plugin_id: str) -> dict[str, Any]:
        for manifest in self._manifests:
            if str(manifest.get("id")) == plugin_id:
                return dict(manifest)
        raise KeyError(f"unknown plugin {plugin_id}")

    def resolve_capability(self, capability: str) -> PluginResolution:
        matching = [
            dict(manifest)
            for manifest in self._sorted_manifests(self._manifests)
            if capability in list(manifest.get("capabilities", []))
        ]
        if not matching:
            return PluginResolution(
                capability=capability,
                selected_plugin=None,
                decision="fallback",
                fallback_policy="deterministic-only",
                reasons=["no plugin manifest declares this capability"],
            )

        selected = matching[0]
        return PluginResolution(
            capability=capability,
            selected_plugin=selected,
            decision="use_plugin",
            fallback_policy=str(selected.get("fallback_policy", "deterministic-only")),
            reasons=[f"selected plugin runtime is {selected.get('runtime', 'unknown')}"],
        )

    def _validated_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(manifest, dict):
            raise PluginRegistryError("plugin manifest must be an object")
        missing = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
        if missing:
            raise PluginRegistryError(f"plugin manifest is missing required fields: {missing}")
        if str(manifest.get("schema_version")) != "ctxvault.plugin-manifest/v1":
            raise PluginRegistryError("plugin manifest schema_version must be ctxvault.plugin-manifest/v1")
        if not isinstance(manifest.get("capabilities"), list) or not manifest["capabilities"]:
            raise PluginRegistryError("plugin manifest capabilities must be a non-empty list")
        if not isinstance(manifest.get("accepted_inputs"), list) or not manifest["accepted_inputs"]:
            raise PluginRegistryError("plugin manifest accepted_inputs must be a non-empty list")
        if not isinstance(manifest.get("produced_outputs"), list) or not manifest["produced_outputs"]:
            raise PluginRegistryError("plugin manifest produced_outputs must be a non-empty list")
        return dict(manifest)

    def _sorted_manifests(self, manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            manifests,
            key=lambda manifest: (
                RUNTIME_PRIORITY.get(str(manifest.get("runtime", "")), 99),
                SIDE_EFFECT_PRIORITY.get(str(manifest.get("side_effect_level", "")), 99),
                str(manifest.get("id", "")),
            ),
        )


class LocalPluginExecutorRegistry:
    def __init__(self, executors: dict[str, LocalPluginExecutor] | None = None):
        self._executors = dict(executors or {})

    def list_capabilities(self) -> list[str]:
        return sorted(self._executors)

    def execute(
        self,
        manifests: list[dict[str, Any]],
        capability: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        resolution = PluginRegistry(manifests).resolve_capability(capability)
        if resolution.decision != "use_plugin" or resolution.selected_plugin is None:
            raise ValueError(f"no executable plugin is available for capability {capability}")
        executor = self._executors.get(capability)
        if executor is None:
            raise ValueError(f"plugin capability is not implemented in the local executor: {capability}")
        return {
            "capability": capability,
            "plugin": resolution.selected_plugin,
            "resolution": resolution.to_dict(),
            "result": executor(dict(arguments)),
        }
