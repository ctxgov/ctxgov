from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, BinaryIO, Callable, Mapping

from .core import CtxVault
from .layout import default_layout
from .policy import CtxVaultPolicy
from .surface import CtxVaultSurface


JSONDict = dict[str, Any]
ToolHandler = Callable[[JSONDict], Any]
PROTOCOL_VERSION = "2025-03-26"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: JSONDict
    handler: ToolHandler

    def as_tool(self) -> JSONDict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class CtxVaultMcpServer:
    def __init__(
        self,
        *,
        root: Path,
        policy_path: Path | None = None,
        backup_path: Path | None = None,
        profile_path: Path | None = None,
        plugin_path: Path | None = None,
    ) -> None:
        self.root = root.resolve()
        self.policy_path = policy_path.resolve() if policy_path is not None else self.root / "fixtures" / "controls" / "protection-policy.json"
        self.backup_path = backup_path.resolve() if backup_path is not None else self.root / "fixtures" / "controls" / "backup-check-receipt.json"
        self.refresh_backup_timestamps = backup_path is None or self.backup_path.name == "backup-check-receipt.json"
        self.profile_path = profile_path.resolve() if profile_path is not None else self.root / "fixtures" / "evidence" / "adapter-capability-profile.json"
        self.plugin_path = plugin_path.resolve() if plugin_path is not None else self.root / "fixtures" / "evidence" / "plugin-manifest.json"
        self.surface = CtxVaultSurface(CtxVault(default_layout(self.root)))
        self._tools = {
            tool.name: tool
            for tool in [
                ToolSpec(
                    name="trace.record",
                    description="Store a deterministic core object and return its envelope references.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "model_name": {"type": "string"},
                            "payload": {"type": "object"},
                        },
                        "required": ["model_name", "payload"],
                        "additionalProperties": False,
                    },
                    handler=self._trace_record,
                ),
                ToolSpec(
                    name="prompt.resolve",
                    description="Resolve a stored prompt asset by id.",
                    input_schema={
                        "type": "object",
                        "properties": {"prompt_id": {"type": "string"}},
                        "required": ["prompt_id"],
                        "additionalProperties": False,
                    },
                    handler=self._prompt_resolve,
                ),
                ToolSpec(
                    name="session.related",
                    description="Find deterministic related sessions for one anchor session.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    handler=self._session_related,
                ),
                ToolSpec(
                    name="session.aggregate-preview",
                    description="Build a read-only aggregate preview over one session and its related sessions.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    handler=self._session_aggregate_preview,
                ),
                ToolSpec(
                    name="workstream.preview",
                    description="Build a read-only workstream preview from one anchor session.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    handler=self._workstream_preview,
                ),
                ToolSpec(
                    name="workstream.list",
                    description="List durable workstreams in deterministic order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "status": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._workstream_list,
                ),
                ToolSpec(
                    name="workstream.intelligence",
                    description="Build a read-only workstream intelligence report over distilled assets.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "workstream_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "required": ["workstream_id"],
                        "additionalProperties": False,
                    },
                    handler=self._workstream_intelligence,
                ),
                ToolSpec(
                    name="workstream-candidate.create",
                    description="Create a durable workstream candidate from a workstream preview.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                            "candidate_id": {"type": "string"},
                            "candidate_for": {"type": "string"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "rationale": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    handler=self._workstream_candidate_create,
                ),
                ToolSpec(
                    name="workstream-candidate.list",
                    description="List workstream candidates in deterministic review order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "proposal_state": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._workstream_candidate_list,
                ),
                ToolSpec(
                    name="workstream-candidate.review",
                    description="Approve or reject a proposed workstream candidate and emit a review receipt.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "candidate_id": {"type": "string"},
                            "decision": {"type": "string", "enum": ["approved", "rejected"]},
                            "reviewer": {"type": "string"},
                            "notes": {"type": "string"},
                            "workstream_id": {"type": "string"},
                            "policy_payload": {"type": "object"},
                            "backup_receipt": {"type": "object"},
                        },
                        "required": ["candidate_id", "decision"],
                        "additionalProperties": False,
                    },
                    handler=self._workstream_candidate_review,
                ),
                ToolSpec(
                    name="episode.list",
                    description="List derived episodes for a scope or session.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "session_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._episode_list,
                ),
                ToolSpec(
                    name="episode.derive",
                    description="Derive deterministic episodes from an imported session.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "session_id": {"type": "string"},
                        },
                        "required": ["session_id"],
                        "additionalProperties": False,
                    },
                    handler=self._episode_derive,
                ),
                ToolSpec(
                    name="episode.synthesize",
                    description="Compile one derived episode into a source-grounded synthesis knowledge artifact.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "episode_id": {"type": "string"},
                            "knowledge_id": {"type": "string"},
                            "title": {"type": "string"},
                        },
                        "required": ["episode_id"],
                        "additionalProperties": False,
                    },
                    handler=self._episode_synthesize,
                ),
                ToolSpec(
                    name="knowledge.export-note",
                    description="Export a knowledge artifact as a local wiki note candidate with front matter.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "knowledge_id": {"type": "string"},
                            "output_path": {"type": "string"},
                            "canonical_target": {"type": "string"},
                            "privacy": {"type": "string"},
                            "status": {"type": "string"},
                            "note_id": {"type": "string"},
                            "title": {"type": "string"},
                        },
                        "required": ["knowledge_id", "output_path", "canonical_target"],
                        "additionalProperties": False,
                    },
                    handler=self._knowledge_export_note,
                ),
                ToolSpec(
                    name="memory.search",
                    description="Run deterministic memory lookup over SQLite projections.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                            "pinned_only": {"type": "boolean"},
                        },
                        "required": ["query"],
                        "additionalProperties": False,
                    },
                    handler=self._memory_search,
                ),
                ToolSpec(
                    name="memory-candidate.list",
                    description="List memory candidates in deterministic review order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "proposal_state": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._memory_candidate_list,
                ),
                ToolSpec(
                    name="memory-candidate.review",
                    description="Approve or reject a proposed memory candidate and emit a review receipt.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "candidate_id": {"type": "string"},
                            "decision": {"type": "string", "enum": ["approved", "rejected"]},
                            "reviewer": {"type": "string"},
                            "notes": {"type": "string"},
                            "memory_id": {"type": "string"},
                            "policy_payload": {"type": "object"},
                            "backup_receipt": {"type": "object"},
                        },
                        "required": ["candidate_id", "decision"],
                        "additionalProperties": False,
                    },
                    handler=self._memory_candidate_review,
                ),
                ToolSpec(
                    name="prompt-patch.list",
                    description="List prompt patch proposals in deterministic review order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "proposal_state": {"type": "string"},
                            "prompt_asset_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._prompt_patch_list,
                ),
                ToolSpec(
                    name="prompt-patch.review",
                    description="Approve or reject a proposed prompt patch and emit a review receipt.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "patch_id": {"type": "string"},
                            "decision": {"type": "string", "enum": ["approved", "rejected"]},
                            "reviewer": {"type": "string"},
                            "notes": {"type": "string"},
                            "policy_payload": {"type": "object"},
                            "backup_receipt": {"type": "object"},
                        },
                        "required": ["patch_id", "decision"],
                        "additionalProperties": False,
                    },
                    handler=self._prompt_patch_review,
                ),
                ToolSpec(
                    name="prompt-eval.run",
                    description="Run deterministic string assertions against a prompt asset or prompt patch preview.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "target_type": {"type": "string", "enum": ["prompt_asset", "prompt_patch"]},
                            "target_id": {"type": "string"},
                            "dataset_ref": {"type": "string"},
                            "assert_contains": {"type": "array", "items": {"type": "string"}},
                            "assert_not_contains": {"type": "array", "items": {"type": "string"}},
                            "notes": {"type": "string"},
                        },
                        "required": ["target_type", "target_id"],
                        "additionalProperties": False,
                    },
                    handler=self._prompt_eval_run,
                ),
                ToolSpec(
                    name="privacy.scan",
                    description="Run a deterministic privacy preflight over text before sharing it with a model.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "source": {"type": "string"},
                            "max_findings": {"type": "integer", "minimum": 1},
                        },
                        "required": ["text"],
                        "additionalProperties": False,
                    },
                    handler=self._privacy_scan,
                ),
                ToolSpec(
                    name="context.receipt",
                    description="Write a stable context bundle receipt that can be attached to plan-ledger artifacts or dossiers.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "bundle": {"type": "object"},
                            "output_path": {"type": "string"},
                            "plan_path": {"type": "string"},
                            "task_id": {"type": "string"},
                        },
                        "required": ["bundle", "output_path"],
                        "additionalProperties": False,
                    },
                    handler=self._context_receipt,
                ),
                ToolSpec(
                    name="audit.receipt",
                    description="Write a stable audit receipt that can be attached to plan-ledger artifacts or dossiers.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "audit": {"type": "object"},
                            "output_path": {"type": "string"},
                            "plan_path": {"type": "string"},
                            "task_id": {"type": "string"},
                        },
                        "required": ["audit", "output_path"],
                        "additionalProperties": False,
                    },
                    handler=self._audit_receipt,
                ),
                ToolSpec(
                    name="workstream.receipt",
                    description="Write a stable workstream receipt that can be attached to plan-ledger artifacts or dossiers.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "workstream": {"type": "object"},
                            "output_path": {"type": "string"},
                            "plan_path": {"type": "string"},
                            "task_id": {"type": "string"},
                        },
                        "required": ["workstream", "output_path"],
                        "additionalProperties": False,
                    },
                    handler=self._workstream_receipt,
                ),
                ToolSpec(
                    name="workstream-candidate.receipt",
                    description="Write a stable workstream candidate receipt that can be attached to plan-ledger artifacts or dossiers.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "candidate": {"type": "object"},
                            "output_path": {"type": "string"},
                            "plan_path": {"type": "string"},
                            "task_id": {"type": "string"},
                        },
                        "required": ["candidate", "output_path"],
                        "additionalProperties": False,
                    },
                    handler=self._workstream_candidate_receipt,
                ),
                ToolSpec(
                    name="context.build",
                    description="Build a deterministic context bundle from prompt, memory, and knowledge inputs.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "object",
                                "properties": {
                                    "scope_kind": {"type": "string"},
                                    "scope_value": {"type": "string"},
                                    "task_label": {"type": "string"},
                                    "prompt_id": {"type": "string"},
                                    "memory_query": {"type": "string"},
                                    "knowledge_query": {"type": "string"},
                                    "max_memories": {"type": "integer", "minimum": 1},
                                    "max_knowledge": {"type": "integer", "minimum": 1},
                                    "token_budget": {"type": "integer", "minimum": 1},
                                },
                                "required": ["scope_kind", "scope_value", "task_label"],
                                "additionalProperties": True,
                            }
                        },
                        "required": ["request"],
                        "additionalProperties": False,
                    },
                    handler=self._context_build,
                ),
                ToolSpec(
                    name="audit.run",
                    description="Run an evidence-first deterministic audit over stored claims and evidence links.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "subject_ref": {"type": "string"},
                            "claim_refs": {"type": "array", "items": {"type": "string"}},
                            "audit_id": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["scope_kind", "scope_value", "subject_ref"],
                        "additionalProperties": False,
                    },
                    handler=self._audit_run,
                ),
                ToolSpec(
                    name="audit.review",
                    description="Record a human review decision for an audit run.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "audit_id": {"type": "string"},
                            "decision": {"type": "string"},
                            "notes": {"type": "string"},
                            "override_verdict": {"type": "string"},
                        },
                        "required": ["audit_id", "decision"],
                        "additionalProperties": False,
                    },
                    handler=self._audit_review,
                ),
                ToolSpec(
                    name="policy.check",
                    description="Evaluate the deterministic protection policy for an operation.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "policy_payload": {"type": "object"},
                            "operation": {"type": "string"},
                            "sensitivity": {"type": "string"},
                            "backup_receipt": {"type": "object"},
                        },
                        "required": ["operation", "sensitivity"],
                        "additionalProperties": False,
                    },
                    handler=self._policy_check,
                ),
                ToolSpec(
                    name="export.check",
                    description="Evaluate deterministic export controls for a payload.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "policy_payload": {"type": "object"},
                            "sensitivity": {"type": "string"},
                            "exportable": {"type": "boolean"},
                            "redaction_state": {"type": "string"},
                            "secret_refs": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["sensitivity", "exportable", "redaction_state"],
                        "additionalProperties": False,
                    },
                    handler=self._export_check,
                ),
                ToolSpec(
                    name="adapter.status",
                    description="List target-side harness adapter profiles in deterministic priority order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "profiles": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "object"}},
                                    {"type": "object"},
                                ]
                            }
                        },
                        "additionalProperties": False,
                    },
                    handler=self._adapter_status,
                ),
                ToolSpec(
                    name="adapter.resolve",
                    description="Resolve one projection target against the adapter registry.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "capability": {"type": "string"},
                            "profiles": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "object"}},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "required": ["capability"],
                        "additionalProperties": False,
                    },
                    handler=self._adapter_resolve,
                ),
                ToolSpec(
                    name="plugin.status",
                    description="List plugin manifests in deterministic priority order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "manifests": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "object"}},
                                    {"type": "object"},
                                ]
                            }
                        },
                        "additionalProperties": False,
                    },
                    handler=self._plugin_status,
                ),
                ToolSpec(
                    name="plugin.resolve",
                    description="Resolve one capability against the plugin registry.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "capability": {"type": "string"},
                            "manifests": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "object"}},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "required": ["capability"],
                        "additionalProperties": False,
                    },
                    handler=self._plugin_resolve,
                ),
                ToolSpec(
                    name="plugin.execute",
                    description="Execute one capability through the local plugin dispatcher.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "capability": {"type": "string"},
                            "arguments": {"type": "object"},
                            "manifests": {
                                "oneOf": [
                                    {"type": "array", "items": {"type": "object"}},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "required": ["capability", "arguments"],
                        "additionalProperties": False,
                    },
                    handler=self._plugin_execute,
                ),
                ToolSpec(
                    name="projection.agents-md",
                    description="Render an AGENTS.md harness projection from one approved workstream and approved memories in scope.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "workstream_id": {"type": "string"},
                            "output_path": {"type": "string"},
                            "receipt_output_path": {"type": "string"},
                            "memory_limit": {"type": "integer", "minimum": 1},
                        },
                        "required": ["workstream_id", "output_path", "receipt_output_path"],
                        "additionalProperties": False,
                    },
                    handler=self._projection_agents_md,
                ),
                ToolSpec(
                    name="backup.emit",
                    description="Emit a deterministic backup archive, manifest, and receipt.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "output_path": {"type": "string"},
                            "receipt_format": {"type": "string", "enum": ["ctxvault", "plan-ledger"]},
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "max_age_hours": {"type": "integer", "minimum": 1},
                            "restore_tested": {"type": "boolean"},
                            "notes": {"type": "string"},
                            "plan_id": {"type": "string"},
                            "target": {"type": "string"},
                        },
                        "required": ["output_path", "receipt_format", "scope_kind", "scope_value"],
                        "additionalProperties": False,
                    },
                    handler=self._backup_emit,
                ),
                ToolSpec(
                    name="snapshot.create",
                    description="Create a local snapshot manifest and append an operation-log entry.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "scope_kind": {"type": "string"},
                            "scope_value": {"type": "string"},
                            "label": {"type": "string"},
                        },
                        "required": ["scope_kind", "scope_value"],
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_create,
                ),
                ToolSpec(
                    name="snapshot.list",
                    description="List local snapshots in reverse chronological order.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_list,
                ),
                ToolSpec(
                    name="snapshot.diff",
                    description="Compare two local snapshot manifests and report added, modified, and deleted files.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "base_snapshot_id": {"type": "string"},
                            "head_snapshot_id": {"type": "string"},
                        },
                        "required": ["base_snapshot_id", "head_snapshot_id"],
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_diff,
                ),
                ToolSpec(
                    name="snapshot.lineage",
                    description="Read the local operation-log lineage for one snapshot or all local snapshots.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "snapshot_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_lineage,
                ),
                ToolSpec(
                    name="snapshot.provenance",
                    description="Show local provenance for one snapshot, including replica source metadata when available.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "snapshot_id": {"type": "string"},
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "required": ["snapshot_id"],
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_provenance,
                ),
                ToolSpec(
                    name="snapshot.restore-plan",
                    description="Create a dry-run restore plan that shows which files would be written or deleted to match a local snapshot.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "snapshot_id": {"type": "string"},
                            "include_workspace": {"type": "boolean"},
                            "include_vault": {"type": "boolean"},
                        },
                        "required": ["snapshot_id"],
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_restore_plan,
                ),
                ToolSpec(
                    name="snapshot.restore-apply",
                    description="Apply a local snapshot restore bundle with explicit review gating for delete actions.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "snapshot_id": {"type": "string"},
                            "include_workspace": {"type": "boolean"},
                            "include_vault": {"type": "boolean"},
                            "allow_deletes": {"type": "boolean"},
                            "reviewed_by": {"type": "string"},
                            "refresh_indexes": {"type": "boolean"},
                        },
                        "required": ["snapshot_id"],
                        "additionalProperties": False,
                    },
                    handler=self._snapshot_restore_apply,
                ),
                ToolSpec(
                    name="sync.receipt",
                    description="Record that a snapshot was copied or synced to another local target.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "snapshot_id": {"type": "string"},
                            "target": {"type": "string"},
                            "transport": {"type": "string"},
                            "device_id": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["snapshot_id", "target", "transport"],
                        "additionalProperties": False,
                    },
                    handler=self._sync_receipt,
                ),
                ToolSpec(
                    name="sync.manifest",
                    description="Write a sync manifest for the current effective local snapshot so it can be copied to another local target.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "target": {"type": "string"},
                            "transport": {"type": "string"},
                            "device_id": {"type": "string"},
                            "snapshot_id": {"type": "string"},
                            "notes": {"type": "string"},
                        },
                        "required": ["target", "transport"],
                        "additionalProperties": False,
                    },
                    handler=self._sync_manifest,
                ),
                ToolSpec(
                    name="sync.manifest.apply",
                    description="Copy the artifacts referenced by a sync manifest into its local target directory.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "sync_manifest_path": {"type": "string"},
                        },
                        "required": ["sync_manifest_path"],
                        "additionalProperties": False,
                    },
                    handler=self._sync_manifest_apply,
                ),
                ToolSpec(
                    name="replica.verify",
                    description="Verify that a copied local replica target contains a complete snapshot manifest and restore bundle.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "replica_root": {"type": "string"},
                            "snapshot_id": {"type": "string"},
                            "sync_manifest_path": {"type": "string"},
                        },
                        "required": ["replica_root"],
                        "additionalProperties": False,
                    },
                    handler=self._replica_verify,
                ),
                ToolSpec(
                    name="replica.import",
                    description="Import a verified local replica snapshot into the current workspace exports.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "replica_root": {"type": "string"},
                            "snapshot_id": {"type": "string"},
                            "sync_manifest_path": {"type": "string"},
                            "trust_policy": {"type": "object"},
                            "reviewed_by": {"type": "string"},
                        },
                        "required": ["replica_root"],
                        "additionalProperties": False,
                    },
                    handler=self._replica_import,
                ),
                ToolSpec(
                    name="replica.trust-evaluate",
                    description="Evaluate deterministic receiver-side trust policy for a copied local replica.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "replica_root": {"type": "string"},
                            "snapshot_id": {"type": "string"},
                            "sync_manifest_path": {"type": "string"},
                            "trust_policy": {"type": "object"},
                        },
                        "required": ["replica_root"],
                        "additionalProperties": False,
                    },
                    handler=self._replica_trust_evaluate,
                ),
                ToolSpec(
                    name="replica.trust.list",
                    description="List persisted receiver-side device trust entries from the local trust registry.",
                    input_schema={
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                    handler=self._replica_trust_list,
                ),
                ToolSpec(
                    name="replica.trust.set",
                    description="Persist or update one receiver-side device trust entry in the local trust registry.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string"},
                            "trust_state": {"type": "string", "enum": ["allow", "review", "block"]},
                            "label": {"type": "string"},
                            "notes": {"type": "string"},
                            "allowed_transports": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["device_id", "trust_state"],
                        "additionalProperties": False,
                    },
                    handler=self._replica_trust_set,
                ),
                ToolSpec(
                    name="replica.apply",
                    description="Verify, import, and apply a local replica snapshot into the current workspace.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "replica_root": {"type": "string"},
                            "snapshot_id": {"type": "string"},
                            "sync_manifest_path": {"type": "string"},
                            "include_workspace": {"type": "boolean"},
                            "include_vault": {"type": "boolean"},
                            "allow_deletes": {"type": "boolean"},
                            "reviewed_by": {"type": "string"},
                            "refresh_indexes": {"type": "boolean"},
                            "trust_policy": {"type": "object"},
                        },
                        "required": ["replica_root"],
                        "additionalProperties": False,
                    },
                    handler=self._replica_apply,
                ),
                ToolSpec(
                    name="sync.status",
                    description="Summarize the latest sync receipt per local target or device and show which endpoints are behind.",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "minimum": 1},
                        },
                        "additionalProperties": False,
                    },
                    handler=self._sync_status,
                ),
            ]
        }

    def handle_request(self, message: Mapping[str, Any]) -> JSONDict | None:
        method = str(message.get("method", ""))
        request_id = message.get("id")
        params = self._optional_mapping(message.get("params"), field="params") or {}

        try:
            if method == "notifications/initialized":
                return None
            if method == "initialize":
                return self._success(
                    request_id,
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "ctxvault", "version": "0.1.0"},
                    },
                )
            if method == "ping":
                return self._success(request_id, {})
            if method == "tools/list":
                return self._success(request_id, {"tools": [tool.as_tool() for tool in self._tools.values()]})
            if method == "tools/call":
                name = self._string(params.get("name"), field="name")
                tool = self._tools.get(name)
                if tool is None:
                    return self._success(
                        request_id,
                        {
                            "content": [{"type": "text", "text": f"unknown tool {name}"}],
                            "isError": True,
                        },
                    )
                arguments = self._optional_mapping(params.get("arguments"), field="arguments") or {}
                try:
                    result = tool.handler(arguments)
                except Exception as exc:
                    return self._success(
                        request_id,
                        {
                            "content": [{"type": "text", "text": str(exc)}],
                            "isError": True,
                        },
                    )
                return self._success(
                    request_id,
                    {
                        "content": [{"type": "text", "text": _json_text(result)}],
                        "structuredContent": result,
                        "isError": False,
                    },
                )
        except ValueError as exc:
            return self._error(request_id, code=-32602, message=str(exc))

        return self._error(request_id, code=-32601, message=f"method not found: {method}")

    def _trace_record(self, arguments: JSONDict) -> JSONDict:
        return self.surface.trace_record(
            self._string(arguments.get("model_name"), field="model_name"),
            self._mapping(arguments.get("payload"), field="payload"),
        )

    def _prompt_resolve(self, arguments: JSONDict) -> JSONDict:
        return self.surface.prompt_resolve(self._string(arguments.get("prompt_id"), field="prompt_id"))

    def _session_related(self, arguments: JSONDict) -> JSONDict:
        return self.surface.session_related(
            self._string(arguments.get("session_id"), field="session_id"),
            limit=int(arguments.get("limit", 5)),
        )

    def _session_aggregate_preview(self, arguments: JSONDict) -> JSONDict:
        return self.surface.session_aggregate_preview(
            self._string(arguments.get("session_id"), field="session_id"),
            limit=int(arguments.get("limit", 5)),
        )

    def _workstream_preview(self, arguments: JSONDict) -> JSONDict:
        return self.surface.workstream_preview(
            self._string(arguments.get("session_id"), field="session_id"),
            limit=int(arguments.get("limit", 5)),
        )

    def _workstream_list(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.workstream_list(
            scope_kind=self._optional_string(arguments.get("scope_kind")),
            scope_value=self._optional_string(arguments.get("scope_value")),
            status=self._optional_string(arguments.get("status")),
            limit=int(arguments.get("limit", 20)),
        )

    def _workstream_intelligence(self, arguments: JSONDict) -> JSONDict:
        return self.surface.workstream_intelligence(
            self._string(arguments.get("workstream_id"), field="workstream_id"),
            limit=int(arguments.get("limit", 6)),
        )

    def _workstream_candidate_create(self, arguments: JSONDict) -> JSONDict:
        return self.surface.workstream_candidate_create(
            self._string(arguments.get("session_id"), field="session_id"),
            limit=int(arguments.get("limit", 5)),
            candidate_id=self._optional_string(arguments.get("candidate_id")),
            candidate_for=self._optional_string(arguments.get("candidate_for")),
            title=self._optional_string(arguments.get("title")),
            summary=self._optional_string(arguments.get("summary")),
            rationale=self._optional_string(arguments.get("rationale")),
            notes=self._optional_string(arguments.get("notes")),
        )

    def _workstream_candidate_list(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.workstream_candidate_list(
            scope_kind=self._optional_string(arguments.get("scope_kind")),
            scope_value=self._optional_string(arguments.get("scope_value")),
            proposal_state=self._optional_string(arguments.get("proposal_state")),
            limit=int(arguments.get("limit", 20)),
        )

    def _workstream_candidate_review(self, arguments: JSONDict) -> JSONDict:
        decision = self._string(arguments.get("decision"), field="decision")
        policy_payload = None
        backup_receipt = None
        if decision == "approved":
            policy_payload = self._mapping(arguments.get("policy_payload"), field="policy_payload") if "policy_payload" in arguments else self._load_mapping(self.policy_path)
            backup_receipt = (
                self._mapping(arguments.get("backup_receipt"), field="backup_receipt")
                if "backup_receipt" in arguments and arguments.get("backup_receipt") is not None
                else self._load_backup_receipt()
            )
        return self.surface.workstream_candidate_review(
            self._string(arguments.get("candidate_id"), field="candidate_id"),
            decision=decision,
            reviewer=self._optional_string(arguments.get("reviewer")) or "human_review",
            notes=self._optional_string(arguments.get("notes")),
            workstream_id=self._optional_string(arguments.get("workstream_id")),
            policy_payload=policy_payload,
            backup_receipt=backup_receipt,
        )

    def _episode_list(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.episode_list(
            scope_kind=self._optional_string(arguments.get("scope_kind")),
            scope_value=self._optional_string(arguments.get("scope_value")),
            session_id=self._optional_string(arguments.get("session_id")),
            limit=int(arguments.get("limit", 20)),
        )

    def _episode_derive(self, arguments: JSONDict) -> JSONDict:
        return self.surface.episode_derive(self._string(arguments.get("session_id"), field="session_id"))

    def _episode_synthesize(self, arguments: JSONDict) -> JSONDict:
        return self.surface.episode_synthesize(
            self._string(arguments.get("episode_id"), field="episode_id"),
            knowledge_id=self._optional_string(arguments.get("knowledge_id")),
            title=self._optional_string(arguments.get("title")),
        )

    def _knowledge_export_note(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        return self.surface.knowledge_export_note(
            self._string(arguments.get("knowledge_id"), field="knowledge_id"),
            output_path=resolved_output,
            canonical_target=self._string(arguments.get("canonical_target"), field="canonical_target"),
            privacy=self._optional_string(arguments.get("privacy")),
            status=self._optional_string(arguments.get("status")) or "draft",
            note_id=self._optional_string(arguments.get("note_id")),
            title=self._optional_string(arguments.get("title")),
        )

    def _memory_search(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.memory_search(
            self._string(arguments.get("query"), field="query"),
            scope_kind=self._optional_string(arguments.get("scope_kind")),
            scope_value=self._optional_string(arguments.get("scope_value")),
            limit=int(arguments.get("limit", 5)),
            pinned_only=bool(arguments.get("pinned_only", False)),
        )

    def _memory_candidate_list(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.memory_candidate_list(
            scope_kind=self._optional_string(arguments.get("scope_kind")),
            scope_value=self._optional_string(arguments.get("scope_value")),
            proposal_state=self._optional_string(arguments.get("proposal_state")),
            limit=int(arguments.get("limit", 20)),
        )

    def _memory_candidate_review(self, arguments: JSONDict) -> JSONDict:
        decision = self._string(arguments.get("decision"), field="decision")
        policy_payload = None
        backup_receipt = None
        if decision == "approved":
            policy_payload = self._mapping(arguments.get("policy_payload"), field="policy_payload") if "policy_payload" in arguments else self._load_mapping(self.policy_path)
            backup_receipt = (
                self._mapping(arguments.get("backup_receipt"), field="backup_receipt")
                if "backup_receipt" in arguments and arguments.get("backup_receipt") is not None
                else self._load_backup_receipt()
            )
        return self.surface.memory_candidate_review(
            self._string(arguments.get("candidate_id"), field="candidate_id"),
            decision=decision,
            reviewer=self._optional_string(arguments.get("reviewer")) or "human_review",
            notes=self._optional_string(arguments.get("notes")),
            memory_id=self._optional_string(arguments.get("memory_id")),
            policy_payload=policy_payload,
            backup_receipt=backup_receipt,
        )

    def _prompt_patch_list(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.prompt_patch_list(
            scope_kind=self._optional_string(arguments.get("scope_kind")),
            scope_value=self._optional_string(arguments.get("scope_value")),
            proposal_state=self._optional_string(arguments.get("proposal_state")),
            prompt_asset_id=self._optional_string(arguments.get("prompt_asset_id")),
            limit=int(arguments.get("limit", 20)),
        )

    def _prompt_patch_review(self, arguments: JSONDict) -> JSONDict:
        decision = self._string(arguments.get("decision"), field="decision")
        policy_payload = None
        backup_receipt = None
        if decision == "approved":
            policy_payload = self._mapping(arguments.get("policy_payload"), field="policy_payload") if "policy_payload" in arguments else self._load_mapping(self.policy_path)
            backup_receipt = (
                self._mapping(arguments.get("backup_receipt"), field="backup_receipt")
                if "backup_receipt" in arguments and arguments.get("backup_receipt") is not None
                else self._load_backup_receipt()
            )
        return self.surface.prompt_patch_review(
            self._string(arguments.get("patch_id"), field="patch_id"),
            decision=decision,
            reviewer=self._optional_string(arguments.get("reviewer")) or "human_review",
            notes=self._optional_string(arguments.get("notes")),
            policy_payload=policy_payload,
            backup_receipt=backup_receipt,
        )

    def _prompt_eval_run(self, arguments: JSONDict) -> JSONDict:
        assert_contains = arguments.get("assert_contains")
        assert_not_contains = arguments.get("assert_not_contains")
        return self.surface.prompt_eval_run(
            self._string(arguments.get("target_type"), field="target_type"),
            self._string(arguments.get("target_id"), field="target_id"),
            dataset_ref=self._optional_string(arguments.get("dataset_ref")) or "eval://manual/prompt-assertions",
            assert_contains=list(assert_contains) if isinstance(assert_contains, list) else None,
            assert_not_contains=list(assert_not_contains) if isinstance(assert_not_contains, list) else None,
            notes=self._optional_string(arguments.get("notes")),
        )

    def _privacy_scan(self, arguments: JSONDict) -> JSONDict:
        return self.surface.privacy_scan(
            self._string(arguments.get("text"), field="text"),
            source=self._optional_string(arguments.get("source")) or "inline",
            max_findings=int(arguments.get("max_findings", 25)),
        )

    def _context_receipt(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        plan_path_value = self._optional_string(arguments.get("plan_path"))
        return self.surface.context_receipt_emit(
            self._mapping(arguments.get("bundle"), field="bundle"),
            output_path=resolved_output,
            plan_path=Path(plan_path_value).expanduser() if plan_path_value else None,
            task_id=self._optional_string(arguments.get("task_id")),
        )

    def _audit_receipt(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        plan_path_value = self._optional_string(arguments.get("plan_path"))
        return self.surface.audit_receipt_emit(
            self._mapping(arguments.get("audit"), field="audit"),
            output_path=resolved_output,
            plan_path=Path(plan_path_value).expanduser() if plan_path_value else None,
            task_id=self._optional_string(arguments.get("task_id")),
        )

    def _workstream_receipt(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        plan_path_value = self._optional_string(arguments.get("plan_path"))
        return self.surface.workstream_receipt_emit(
            self._mapping(arguments.get("workstream"), field="workstream"),
            output_path=resolved_output,
            plan_path=Path(plan_path_value).expanduser() if plan_path_value else None,
            task_id=self._optional_string(arguments.get("task_id")),
        )

    def _workstream_candidate_receipt(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        plan_path_value = self._optional_string(arguments.get("plan_path"))
        return self.surface.workstream_candidate_receipt_emit(
            self._mapping(arguments.get("candidate"), field="candidate"),
            output_path=resolved_output,
            plan_path=Path(plan_path_value).expanduser() if plan_path_value else None,
            task_id=self._optional_string(arguments.get("task_id")),
        )

    def _context_build(self, arguments: JSONDict) -> JSONDict:
        request = self._mapping(arguments.get("request"), field="request")
        return self.surface.context_build(request)

    def _audit_run(self, arguments: JSONDict) -> JSONDict:
        claim_refs = arguments.get("claim_refs")
        return self.surface.audit_run(
            scope_kind=self._string(arguments.get("scope_kind"), field="scope_kind"),
            scope_value=self._string(arguments.get("scope_value"), field="scope_value"),
            subject_ref=self._string(arguments.get("subject_ref"), field="subject_ref"),
            claim_refs=list(claim_refs) if isinstance(claim_refs, list) else None,
            audit_id=self._optional_string(arguments.get("audit_id")),
            notes=self._optional_string(arguments.get("notes")),
        )

    def _audit_review(self, arguments: JSONDict) -> JSONDict:
        return self.surface.audit_review(
            self._string(arguments.get("audit_id"), field="audit_id"),
            decision=self._string(arguments.get("decision"), field="decision"),
            notes=self._optional_string(arguments.get("notes")),
            override_verdict=self._optional_string(arguments.get("override_verdict")),
        )

    def _policy_check(self, arguments: JSONDict) -> JSONDict:
        policy_payload = self._mapping(arguments.get("policy_payload"), field="policy_payload") if "policy_payload" in arguments else self._load_mapping(self.policy_path)
        backup_receipt = (
            self._mapping(arguments.get("backup_receipt"), field="backup_receipt")
            if "backup_receipt" in arguments and arguments.get("backup_receipt") is not None
            else self._load_backup_receipt()
        )
        return self.surface.policy_check(
            policy_payload=policy_payload,
            operation=self._string(arguments.get("operation"), field="operation"),
            sensitivity=self._string(arguments.get("sensitivity"), field="sensitivity"),
            backup_receipt=backup_receipt,
        )

    def _export_check(self, arguments: JSONDict) -> JSONDict:
        policy_payload = self._mapping(arguments.get("policy_payload"), field="policy_payload") if "policy_payload" in arguments else self._load_mapping(self.policy_path)
        secret_refs = arguments.get("secret_refs")
        return self.surface.export_check(
            policy_payload=policy_payload,
            sensitivity=self._string(arguments.get("sensitivity"), field="sensitivity"),
            exportable=self._bool(arguments.get("exportable"), field="exportable"),
            redaction_state=self._string(arguments.get("redaction_state"), field="redaction_state"),
            secret_refs=list(secret_refs) if isinstance(secret_refs, list) else None,
        )

    def _adapter_status(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.adapter_status(self._profiles(arguments.get("profiles")))

    def _adapter_resolve(self, arguments: JSONDict) -> JSONDict:
        return self.surface.adapter_resolve(
            self._profiles(arguments.get("profiles")),
            self._string(arguments.get("capability"), field="capability"),
        )

    def _plugin_status(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.plugin_status(self._manifests(arguments.get("manifests")))

    def _plugin_resolve(self, arguments: JSONDict) -> JSONDict:
        return self.surface.plugin_resolve(
            self._manifests(arguments.get("manifests")),
            self._string(arguments.get("capability"), field="capability"),
        )

    def _plugin_execute(self, arguments: JSONDict) -> JSONDict:
        payload = self._mapping(arguments.get("arguments"), field="arguments")
        normalized = dict(payload)
        for field in ("output_path", "receipt_output_path"):
            if field in normalized:
                raw_path = Path(self._string(normalized.get(field), field=field))
                normalized[field] = str(raw_path if raw_path.is_absolute() else (self.root / raw_path).resolve())
        return self.surface.plugin_execute(
            self._manifests(arguments.get("manifests")),
            self._string(arguments.get("capability"), field="capability"),
            normalized,
        )

    def _projection_agents_md(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        receipt_output_path = Path(self._string(arguments.get("receipt_output_path"), field="receipt_output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        resolved_receipt = receipt_output_path if receipt_output_path.is_absolute() else self.root / receipt_output_path
        return self.surface.harness_agents_md_emit(
            workstream_id=self._string(arguments.get("workstream_id"), field="workstream_id"),
            output_path=resolved_output.resolve(),
            receipt_output_path=resolved_receipt.resolve(),
            memory_limit=int(arguments.get("memory_limit", 5)),
        )

    def _backup_emit(self, arguments: JSONDict) -> JSONDict:
        output_path = Path(self._string(arguments.get("output_path"), field="output_path"))
        resolved_output = output_path if output_path.is_absolute() else self.root / output_path
        return self.surface.backup_emit(
            root=self.root,
            output_path=resolved_output,
            receipt_format=self._string(arguments.get("receipt_format"), field="receipt_format"),
            scope_kind=self._string(arguments.get("scope_kind"), field="scope_kind"),
            scope_value=self._string(arguments.get("scope_value"), field="scope_value"),
            max_age_hours=int(arguments.get("max_age_hours", 24)),
            restore_tested=bool(arguments.get("restore_tested", False)),
            notes=self._optional_string(arguments.get("notes")),
            plan_id=self._optional_string(arguments.get("plan_id")),
            target=self._optional_string(arguments.get("target")),
        )

    def _snapshot_create(self, arguments: JSONDict) -> JSONDict:
        return self.surface.snapshot_create(
            scope_kind=self._string(arguments.get("scope_kind"), field="scope_kind"),
            scope_value=self._string(arguments.get("scope_value"), field="scope_value"),
            label=self._optional_string(arguments.get("label")),
        )

    def _snapshot_list(self, arguments: JSONDict) -> list[JSONDict]:
        return self.surface.snapshot_list(limit=int(arguments.get("limit", 20)))

    def _snapshot_diff(self, arguments: JSONDict) -> JSONDict:
        return self.surface.snapshot_diff(
            base_snapshot_id=self._string(arguments.get("base_snapshot_id"), field="base_snapshot_id"),
            head_snapshot_id=self._string(arguments.get("head_snapshot_id"), field="head_snapshot_id"),
        )

    def _snapshot_lineage(self, arguments: JSONDict) -> JSONDict:
        return self.surface.snapshot_lineage(
            snapshot_id=self._optional_string(arguments.get("snapshot_id")),
            limit=int(arguments.get("limit", 100)),
        )

    def _snapshot_provenance(self, arguments: JSONDict) -> JSONDict:
        return self.surface.snapshot_provenance(
            snapshot_id=self._string(arguments.get("snapshot_id"), field="snapshot_id"),
            limit=int(arguments.get("limit", 100)),
        )

    def _snapshot_restore_plan(self, arguments: JSONDict) -> JSONDict:
        return self.surface.snapshot_restore_plan(
            snapshot_id=self._string(arguments.get("snapshot_id"), field="snapshot_id"),
            include_workspace=bool(arguments.get("include_workspace", True)),
            include_vault=bool(arguments.get("include_vault", True)),
        )

    def _snapshot_restore_apply(self, arguments: JSONDict) -> JSONDict:
        return self.surface.snapshot_restore_apply(
            snapshot_id=self._string(arguments.get("snapshot_id"), field="snapshot_id"),
            include_workspace=bool(arguments.get("include_workspace", True)),
            include_vault=bool(arguments.get("include_vault", True)),
            allow_deletes=bool(arguments.get("allow_deletes", False)),
            reviewed_by=self._optional_string(arguments.get("reviewed_by")),
            refresh_indexes=bool(arguments.get("refresh_indexes", True)),
        )

    def _sync_receipt(self, arguments: JSONDict) -> JSONDict:
        return self.surface.sync_receipt_emit(
            snapshot_id=self._string(arguments.get("snapshot_id"), field="snapshot_id"),
            target=self._string(arguments.get("target"), field="target"),
            transport=self._string(arguments.get("transport"), field="transport"),
            device_id=self._optional_string(arguments.get("device_id")),
            notes=self._optional_string(arguments.get("notes")),
        )

    def _sync_status(self, arguments: JSONDict) -> JSONDict:
        return self.surface.sync_status(limit=int(arguments.get("limit", 50)))

    def _sync_manifest(self, arguments: JSONDict) -> JSONDict:
        return self.surface.sync_manifest_emit(
            target=self._string(arguments.get("target"), field="target"),
            transport=self._string(arguments.get("transport"), field="transport"),
            device_id=self._optional_string(arguments.get("device_id")),
            snapshot_id=self._optional_string(arguments.get("snapshot_id")),
            notes=self._optional_string(arguments.get("notes")),
        )

    def _sync_manifest_apply(self, arguments: JSONDict) -> JSONDict:
        sync_manifest_path = Path(self._string(arguments.get("sync_manifest_path"), field="sync_manifest_path"))
        resolved_path = sync_manifest_path if sync_manifest_path.is_absolute() else self.root / sync_manifest_path
        return self.surface.sync_manifest_apply(sync_manifest_path=resolved_path.resolve())

    def _replica_verify(self, arguments: JSONDict) -> JSONDict:
        replica_root = Path(self._string(arguments.get("replica_root"), field="replica_root"))
        sync_manifest_path = self._optional_string(arguments.get("sync_manifest_path"))
        return self.surface.replica_verify(
            replica_root=replica_root if replica_root.is_absolute() else (self.root / replica_root).resolve(),
            snapshot_id=self._optional_string(arguments.get("snapshot_id")),
            sync_manifest_path=Path(sync_manifest_path).resolve() if sync_manifest_path else None,
        )

    def _replica_import(self, arguments: JSONDict) -> JSONDict:
        replica_root = Path(self._string(arguments.get("replica_root"), field="replica_root"))
        sync_manifest_path = self._optional_string(arguments.get("sync_manifest_path"))
        return self.surface.replica_import(
            replica_root=replica_root if replica_root.is_absolute() else (self.root / replica_root).resolve(),
            snapshot_id=self._optional_string(arguments.get("snapshot_id")),
            sync_manifest_path=Path(sync_manifest_path).resolve() if sync_manifest_path else None,
            trust_policy=self._optional_mapping(arguments.get("trust_policy"), field="trust_policy"),
            reviewed_by=self._optional_string(arguments.get("reviewed_by")),
        )

    def _replica_trust_evaluate(self, arguments: JSONDict) -> JSONDict:
        replica_root = Path(self._string(arguments.get("replica_root"), field="replica_root"))
        sync_manifest_path = self._optional_string(arguments.get("sync_manifest_path"))
        return self.surface.replica_trust_evaluate(
            replica_root=replica_root if replica_root.is_absolute() else (self.root / replica_root).resolve(),
            snapshot_id=self._optional_string(arguments.get("snapshot_id")),
            sync_manifest_path=Path(sync_manifest_path).resolve() if sync_manifest_path else None,
            trust_policy=self._optional_mapping(arguments.get("trust_policy"), field="trust_policy"),
        )

    def _replica_trust_list(self, arguments: JSONDict) -> JSONDict:
        del arguments
        return self.surface.replica_trust_list()

    def _replica_trust_set(self, arguments: JSONDict) -> JSONDict:
        transports = arguments.get("allowed_transports")
        allowed_transports = None
        if transports is not None:
            allowed_transports = [self._string(item, field="allowed_transports[]") for item in list(transports)]
        return self.surface.replica_trust_set(
            device_id=self._string(arguments.get("device_id"), field="device_id"),
            trust_state=self._string(arguments.get("trust_state"), field="trust_state"),
            label=self._optional_string(arguments.get("label")),
            notes=self._optional_string(arguments.get("notes")),
            allowed_transports=allowed_transports,
        )

    def _replica_apply(self, arguments: JSONDict) -> JSONDict:
        replica_root = Path(self._string(arguments.get("replica_root"), field="replica_root"))
        sync_manifest_path = self._optional_string(arguments.get("sync_manifest_path"))
        return self.surface.replica_apply(
            replica_root=replica_root if replica_root.is_absolute() else (self.root / replica_root).resolve(),
            snapshot_id=self._optional_string(arguments.get("snapshot_id")),
            sync_manifest_path=Path(sync_manifest_path).resolve() if sync_manifest_path else None,
            include_workspace=bool(arguments.get("include_workspace", True)),
            include_vault=bool(arguments.get("include_vault", True)),
            allow_deletes=bool(arguments.get("allow_deletes", False)),
            reviewed_by=self._optional_string(arguments.get("reviewed_by")),
            refresh_indexes=bool(arguments.get("refresh_indexes", True)),
            trust_policy=self._optional_mapping(arguments.get("trust_policy"), field="trust_policy"),
        )

    def _profiles(self, value: Any) -> list[JSONDict]:
        payload = value if value is not None else self._load_json(self.profile_path)
        if isinstance(payload, list):
            return [self._mapping(item, field="profiles[]") for item in payload]
        return [self._mapping(payload, field="profiles")]

    def _manifests(self, value: Any) -> list[JSONDict]:
        payload = value if value is not None else self._load_json(self.plugin_path)
        if isinstance(payload, list):
            return [self._mapping(item, field="manifests[]") for item in payload]
        return [self._mapping(payload, field="manifests")]

    def _load_json(self, path: Path) -> Any:
        return json.loads(path.read_text(encoding="utf-8"))

    def _load_mapping(self, path: Path) -> JSONDict:
        return self._mapping(self._load_json(path), field=str(path))

    def _load_optional_mapping(self, path: Path) -> JSONDict | None:
        if not path.exists():
            return None
        return self._load_mapping(path)

    def _load_backup_receipt(self) -> JSONDict | None:
        payload = CtxVaultPolicy.load_backup_receipt(
            self.backup_path,
            refresh_timestamps=self.refresh_backup_timestamps,
        )
        if payload is None:
            return None
        return self._mapping(payload, field=str(self.backup_path))

    def _success(self, request_id: Any, result: Any) -> JSONDict:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error(self, request_id: Any, *, code: int, message: str) -> JSONDict:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def _mapping(self, value: Any, *, field: str) -> JSONDict:
        if not isinstance(value, Mapping):
            raise ValueError(f"{field} must be an object")
        return dict(value)

    def _optional_mapping(self, value: Any, *, field: str) -> JSONDict | None:
        if value is None:
            return None
        return self._mapping(value, field=field)

    def _string(self, value: Any, *, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} must be a non-empty string")
        return value

    def _optional_string(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("optional string field must be a string when provided")
        return value

    def _bool(self, value: Any, *, field: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{field} must be a boolean")
        return value


def read_message(input_stream: BinaryIO) -> JSONDict | None:
    content_length: int | None = None
    while True:
        line = input_stream.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        header = line.decode("utf-8").strip()
        name, _, value = header.partition(":")
        if name.lower() == "content-length":
            content_length = int(value.strip())
    if content_length is None:
        raise ValueError("missing Content-Length header")
    body = input_stream.read(content_length)
    if len(body) != content_length:
        raise EOFError("truncated JSON-RPC message body")
    return json.loads(body.decode("utf-8"))


def write_message(output_stream: BinaryIO, payload: Mapping[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=True, sort_keys=True).encode("utf-8")
    output_stream.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    output_stream.write(body)
    output_stream.flush()


def serve_stdio(
    *,
    root: Path,
    policy_path: Path | None = None,
    backup_path: Path | None = None,
    profile_path: Path | None = None,
    plugin_path: Path | None = None,
    input_stream: BinaryIO | None = None,
    output_stream: BinaryIO | None = None,
) -> int:
    server = CtxVaultMcpServer(
        root=root,
        policy_path=policy_path,
        backup_path=backup_path,
        profile_path=profile_path,
        plugin_path=plugin_path,
    )
    reader = input_stream or sys.stdin.buffer
    writer = output_stream or sys.stdout.buffer
    while True:
        message = read_message(reader)
        if message is None:
            return 0
        response = server.handle_request(message)
        if response is not None:
            write_message(writer, response)


def main(argv: list[str] | None = None) -> int:
    from argparse import ArgumentParser

    parser = ArgumentParser(prog="ctxvault-mcp")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--policy-json-path", type=Path)
    parser.add_argument("--backup-json-path", type=Path)
    parser.add_argument("--profile-json-path", type=Path)
    parser.add_argument("--plugin-json-path", type=Path)
    args = parser.parse_args(argv)
    return serve_stdio(
        root=args.root.resolve(),
        policy_path=args.policy_json_path.resolve() if args.policy_json_path else None,
        backup_path=args.backup_json_path.resolve() if args.backup_json_path else None,
        profile_path=args.profile_json_path.resolve() if args.profile_json_path else None,
        plugin_path=args.plugin_json_path.resolve() if args.plugin_json_path else None,
    )


def _json_text(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main())
