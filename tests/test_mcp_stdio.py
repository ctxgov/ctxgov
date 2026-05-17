from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.ingest import import_transcript_path
from ctxgov.mcp_stdio import CtxVaultMcpServer, read_message, write_message


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.policy_path = ROOT / "fixtures" / "controls" / "protection-policy.json"
        self.backup_path = ROOT / "fixtures" / "controls" / "backup-check-receipt.json"
        self.profile_path = ROOT / "fixtures" / "evidence" / "adapter-capability-profile.json"
        self.plugin_path = ROOT / "fixtures" / "evidence" / "plugin-manifest.json"
        self.server = CtxVaultMcpServer(
            root=self.repo_root,
            policy_path=self.policy_path,
            backup_path=self.backup_path,
            profile_path=self.profile_path,
            plugin_path=self.plugin_path,
        )
        self.prompt_payload = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text())
        self.prompt_patch_payload = json.loads((ROOT / "fixtures" / "core" / "prompt-patch.json").read_text())
        self.memory_candidate_payload = json.loads((ROOT / "fixtures" / "core" / "memory-candidate.json").read_text())

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _request(self, request_id: int, method: str, params: dict | None = None) -> dict:
        response = self.server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        self.assertIsNotNone(response)
        return response

    def test_tools_list_exposes_ctxvault_surface_methods(self) -> None:
        initialize = self._request(1, "initialize")
        self.assertEqual(initialize["result"]["serverInfo"]["name"], "ctxvault")

        listed = self._request(2, "tools/list")
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(
            names,
            [
                "trace.record",
                "prompt.resolve",
                "session.related",
                "session.aggregate-preview",
                "workstream.preview",
                "workstream.list",
                "workstream.intelligence",
                "workstream.compiled-state",
                "workstream-candidate.create",
                "workstream-candidate.list",
                "workstream-candidate.review",
                "episode.list",
                "episode.derive",
                "episode.synthesize",
                "knowledge.export-note",
                "memory.search",
                "memory-candidate.list",
                "memory-candidate.review",
                "prompt-patch.list",
                "prompt-patch.density-check",
                "prompt-patch.review",
                "prompt-eval.run",
                "privacy.scan",
                "context.search",
                "context.selection-preflight",
                "context.selection-compose",
                "context.prepare",
                "context.extract",
                "context.slice-preference-set",
                "context.slice-preference-list",
                "logical-purge.plan",
                "logical-purge.apply",
                "context.receipt",
                "audit.receipt",
                "workstream.receipt",
                "workstream-candidate.receipt",
                "context.build",
                "audit.run",
                "audit.review",
                "policy.check",
                "export.check",
                "adapter.status",
                "adapter.resolve",
                "doctor.report",
                "receipt.inspect",
                "plugin.status",
                "plugin.resolve",
                "plugin.execute",
                "projection.agents-md",
                "backup.emit",
                "local-backup.write",
                "snapshot.create",
                "snapshot.list",
                "snapshot.diff",
                "snapshot.lineage",
                "snapshot.provenance",
                "snapshot.restore-plan",
                "snapshot.restore-apply",
                "sync.receipt",
                "sync.manifest",
                "sync.manifest.apply",
                "replica.verify",
                "replica.import",
                "replica.trust-evaluate",
                "replica.trust.list",
                "replica.trust.set",
                "replica.apply",
                "sync.status",
            ],
        )

    def test_tools_call_supports_plugin_registry_queries(self) -> None:
        listed = self._request(
            3,
            "tools/call",
            {
                "name": "plugin.status",
                "arguments": {},
            },
        )
        resolved = self._request(
            4,
            "tools/call",
            {
                "name": "plugin.resolve",
                "arguments": {"capability": "projection.harness.agents-md"},
            },
        )

        self.assertEqual(listed["result"]["structuredContent"][0]["id"], "portable-harness-projection")
        self.assertEqual(resolved["result"]["structuredContent"]["decision"], "use_plugin")
        self.assertEqual(
            resolved["result"]["structuredContent"]["selected_plugin"]["id"],
            "portable-harness-projection",
        )

    def test_tools_call_searches_context_slices(self) -> None:
        self.server.surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")
        self.server.surface.context_slice_rebuild()

        searched = self._request(
            5,
            "tools/call",
            {
                "name": "context.search",
                "arguments": {"query": "local-first context layer", "limit": 3},
            },
        )

        hits = searched["result"]["structuredContent"]
        self.assertTrue(hits)
        self.assertEqual(hits[0]["payload"]["schema_id"], "ctxvault.context-slice/v1")

        composed = self._request(
            6,
            "tools/call",
            {
                "name": "context.selection-compose",
                "arguments": {
                    "query": "local-first context layer",
                    "target_kind": "harness.agents-md",
                    "selected_slice_refs": [hits[0]["slice_ref"]],
                    "candidate_slice_refs": [hits[0]["slice_ref"]],
                    "write_receipt": True,
                },
            },
        )
        selection = composed["result"]["structuredContent"]
        self.assertEqual(selection["receipt"]["schema_id"], "ctxvault.context-selection-receipt/v1")
        self.assertEqual(selection["selected_slice_refs"], [hits[0]["slice_ref"]])

        prepared = self._request(
            7,
            "tools/call",
            {
                "name": "context.prepare",
                "arguments": {
                    "query": "local-first context layer",
                    "target_kind": "harness.agents-md",
                    "workstream_ref": "workstream://ws_20260421_ctxvault_schema",
                    "limit": 3,
                    "token_budget": 1000,
                    "rebuild": False,
                },
            },
        )
        handoff = prepared["result"]["structuredContent"]
        self.assertEqual(handoff["schema_id"], "ctxvault.context-prepare/v1")
        self.assertEqual(handoff["operation"], "safe_context_handoff_prepare")
        self.assertTrue(handoff["selected_slice_refs"])
        self.assertEqual(handoff["selection_status"], "ready")
        self.assertTrue(handoff["handoff_ready"])
        self.assertTrue(Path(handoff["receipt_path"]).exists())

        preview = self._request(
            8,
            "tools/call",
            {
                "name": "context.prepare",
                "arguments": {
                    "query": "local-first context layer",
                    "selected_slice_refs": [hits[0]["slice_ref"]],
                    "rebuild": False,
                    "write_receipt": False,
                },
            },
        )
        preview_handoff = preview["result"]["structuredContent"]
        self.assertIsNone(preview_handoff["slice_rebuild"])
        self.assertIsNone(preview_handoff["receipt_path"])

        empty = self._request(
            9,
            "tools/call",
            {
                "name": "context.prepare",
                "arguments": {
                    "query": "zzzz-no-context-slice-match",
                    "scope_kind": "project",
                    "scope_value": "missing-project",
                    "rebuild": False,
                    "write_receipt": False,
                },
            },
        )
        empty_handoff = empty["result"]["structuredContent"]
        self.assertEqual(empty_handoff["selection_status"], "empty")
        self.assertFalse(empty_handoff["handoff_ready"])
        self.assertEqual(empty_handoff["empty_selection_reason"], "no_candidate_slices")
        self.assertEqual(empty_handoff["warnings"][0]["code"], "no_candidate_slices")

        over_budget = self._request(
            10,
            "tools/call",
            {
                "name": "context.prepare",
                "arguments": {
                    "query": "local-first context layer",
                    "selected_slice_refs": [hits[0]["slice_ref"]],
                    "token_budget": 1,
                    "rebuild": False,
                    "write_receipt": False,
                },
            },
        )
        over_budget_handoff = over_budget["result"]["structuredContent"]
        self.assertEqual(over_budget_handoff["selection_status"], "over_budget")
        self.assertFalse(over_budget_handoff["handoff_ready"])
        self.assertEqual(over_budget_handoff["warnings"][0]["code"], "over_budget")

        source_note = self.repo_root / "mcp-one-click.md"
        source_note.write_text(
            "# MCP one click\n\nExtract source material and prepare a stable handoff from one MCP call.",
            encoding="utf-8",
        )
        extracted = self._request(
            11,
            "tools/call",
            {
                "name": "context.extract",
                "arguments": {
                    "source_paths": [str(source_note)],
                    "prepare_query": "mcp one click stable handoff",
                    "workstream_ref": "workstream://ws_20260421_ctxvault_schema",
                    "workstream_id": "ws_20260421_ctxvault_schema",
                    "project_targets": ["workstream-brief"],
                },
            },
        )
        extraction = extracted["result"]["structuredContent"]
        self.assertEqual(extraction["schema_id"], "ctxvault.context-extract/v1")
        self.assertEqual(extraction["status"], "pass")
        self.assertTrue(Path(extraction["receipt_path"]).exists())
        self.assertEqual(extraction["imports"][0]["source_kind"], "knowledge")
        self.assertEqual(len(extraction["projections"]), 1)

        inspected = self._request(
            12,
            "tools/call",
            {
                "name": "receipt.inspect",
                "arguments": {
                    "receipt_path": extraction["receipt_path"],
                },
            },
        )
        inspection = inspected["result"]["structuredContent"]
        self.assertEqual(inspection["schema_id"], "ctxvault.receipt-inspection/v1")
        self.assertEqual(inspection["status"], "pass")
        self.assertEqual(inspection["chains"][0]["missing_links"], [])
        self.assertIn("CtxVault receipt inspection", inspection["summary_text"])

        inspected_latest = self._request(
            13,
            "tools/call",
            {
                "name": "receipt.inspect",
                "arguments": {
                    "latest": True,
                },
            },
        )
        latest_inspection = inspected_latest["result"]["structuredContent"]
        self.assertEqual(latest_inspection["status"], "pass")
        self.assertEqual(latest_inspection["target"]["kind"], "context_extract")

        invalid_bool = self._request(
            14,
            "tools/call",
            {
                "name": "context.prepare",
                "arguments": {
                    "query": "local-first context layer",
                    "rebuild": "false",
                },
            },
        )
        self.assertTrue(invalid_bool["result"]["isError"])
        self.assertIn("rebuild must be a boolean", invalid_bool["result"]["content"][0]["text"])
        self.assertEqual(invalid_bool["result"]["structuredContent"]["error_code"], "invalid_boolean")

        invalid_slice = self._request(
            15,
            "tools/call",
            {
                "name": "context.prepare",
                "arguments": {
                    "query": "local-first context layer",
                    "selected_slice_refs": ["slice://missing"],
                    "rebuild": False,
                },
            },
        )
        self.assertTrue(invalid_slice["result"]["isError"])
        self.assertEqual(invalid_slice["result"]["structuredContent"]["error_code"], "unknown_slice_ref")

        pinned = self._request(
            16,
            "tools/call",
            {
                "name": "context.slice-preference-set",
                "arguments": {
                    "slice_ref": hits[0]["slice_ref"],
                    "action": "pin",
                    "target_kind": "harness.agents-md",
                },
            },
        )
        self.assertEqual(pinned["result"]["structuredContent"]["action"], "pin")

    def test_tools_call_emits_agents_md_projection(self) -> None:
        workstream = json.loads((ROOT / "fixtures" / "core" / "workstream.json").read_text())
        memory = json.loads((ROOT / "fixtures" / "core" / "memory.json").read_text())
        self.server.surface.vault.store_core_object("Workstream", workstream)
        self.server.surface.vault.store_core_object("Memory", memory)

        projected = self._request(
            5,
            "tools/call",
            {
                "name": "projection.agents-md",
                "arguments": {
                    "workstream_id": workstream["id"],
                    "output_path": "exports/AGENTS.md",
                    "receipt_output_path": "artifacts/agents-md-receipt.json",
                    "memory_limit": 5,
                },
            },
        )

        rendered = (self.repo_root / "exports" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(workstream["title"], rendered)
        self.assertIn(memory["statement"], rendered)
        self.assertEqual(projected["result"]["structuredContent"]["receipt"]["target_kind"], "harness.agents-md")
        self.assertTrue(Path(projected["result"]["structuredContent"]["receipt_path"]).exists())

    def test_tools_call_writes_verified_local_backup(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")

        with TemporaryDirectory() as target_tmpdir:
            target_root = Path(target_tmpdir) / "mcp-local-backup"
            written = self._request(
                6,
                "tools/call",
                {
                    "name": "local-backup.write",
                    "arguments": {
                        "target": target_root.as_uri(),
                        "label": "mcp local backup",
                        "device_id": "mcp-local-backup-device",
                    },
                },
            )

            payload = written["result"]["structuredContent"]
            self.assertEqual(payload["receipt"]["schema_version"], "ctxvault.local-backup-write-receipt/v1")
            self.assertEqual(payload["receipt"]["status"], "verified")
            self.assertEqual(payload["verification"]["status"], "verified")
            self.assertTrue((target_root / "snapshots" / Path(payload["snapshot"]["manifest_path"]).name).exists())
            self.assertTrue((target_root / "snapshot-bundles" / Path(payload["snapshot"]["restore_bundle_path"]).name).exists())

    def test_tools_call_executes_plugin_capability(self) -> None:
        workstream = json.loads((ROOT / "fixtures" / "core" / "workstream.json").read_text())
        memory = json.loads((ROOT / "fixtures" / "core" / "memory.json").read_text())
        self.server.surface.vault.store_core_object("Workstream", workstream)
        self.server.surface.vault.store_core_object("Memory", memory)

        executed = self._request(
            6,
            "tools/call",
            {
                "name": "plugin.execute",
                "arguments": {
                    "capability": "projection.harness.agents-md",
                    "arguments": {
                        "workstream_id": workstream["id"],
                        "output_path": "exports/AGENTS-plugin.md",
                        "receipt_output_path": "artifacts/agents-plugin-receipt.json",
                        "memory_limit": 5,
                    },
                },
            },
        )

        self.assertEqual(executed["result"]["structuredContent"]["plugin"]["id"], "portable-harness-projection")
        self.assertEqual(executed["result"]["structuredContent"]["result"]["receipt"]["target_kind"], "harness.agents-md")
        self.assertTrue(Path(executed["result"]["structuredContent"]["result"]["output_path"]).exists())

    def test_tools_call_supports_session_intelligence_preview(self) -> None:
        transcript_dir = self.repo_root / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        for session_id, title, task_label, turns in [
            (
                "sess_schema_design_001",
                "Schema Design Review",
                "Design vault schema",
                [
                    {"id": "turn_schema_001", "role": "user", "content": "Design the vault schema and review the object layout."},
                    {"id": "turn_schema_002", "role": "assistant", "content": "Use file-backed objects and rebuildable indexes."},
                ],
            ),
            (
                "sess_schema_design_002",
                "Schema Migration Design",
                "Design vault schema",
                [
                    {"id": "turn_schema_101", "role": "user", "content": "Plan the schema migration for the local vault."},
                    {"id": "turn_schema_102", "role": "assistant", "content": "Keep the schema deterministic and versioned."},
                ],
            ),
            (
                "sess_release_pkg_001",
                "Packaging Release Artifact",
                "Package native wrapper",
                [
                    {"id": "turn_pkg_001", "role": "user", "content": "Package the app bundle for release."},
                    {"id": "turn_pkg_002", "role": "assistant", "content": "Build a macOS wrapper and sign it later."},
                ],
            ),
        ]:
            transcript_path = transcript_dir / f"{session_id}.json"
            transcript_path.write_text(
                json.dumps(
                    {
                        "id": session_id,
                        "title": title,
                        "task_label": task_label,
                        "turns": turns,
                    }
                ),
                encoding="utf-8",
            )
            import_transcript_path(
                self.server.surface.vault,
                transcript_path,
                scope_kind="project",
                scope_value="ctxvault",
            )
        self.server.surface.episode_derive("sess_schema_design_001")
        self.server.surface.episode_derive("sess_schema_design_002")

        related = self._request(
            3,
            "tools/call",
            {
                "name": "session.related",
                "arguments": {"session_id": "sess_schema_design_001", "limit": 5},
            },
        )
        aggregate = self._request(
            4,
            "tools/call",
            {
                "name": "session.aggregate-preview",
                "arguments": {"session_id": "sess_schema_design_001", "limit": 5},
            },
        )

        self.assertEqual(related["result"]["structuredContent"]["summary"]["returned_count"], 1)
        self.assertEqual(
            related["result"]["structuredContent"]["related_sessions"][0]["session"]["id"],
            "sess_schema_design_002",
        )
        self.assertIn(
            "schema",
            related["result"]["structuredContent"]["related_sessions"][0]["shared_terms"],
        )
        self.assertEqual(aggregate["result"]["structuredContent"]["aggregate"]["session_count"], 2)

    def test_tools_call_supports_workstream_lifecycle(self) -> None:
        transcript_dir = self.repo_root / "transcripts"
        transcript_dir.mkdir(parents=True, exist_ok=True)
        for session_id, title, task_label, turns in [
            (
                "sess_schema_design_001",
                "Schema Design Review",
                "Design vault schema",
                [
                    {"id": "turn_schema_001", "role": "user", "content": "Design the vault schema and review the object layout."},
                    {"id": "turn_schema_002", "role": "assistant", "content": "Use file-backed objects and rebuildable indexes."},
                ],
            ),
            (
                "sess_schema_design_002",
                "Schema Migration Design",
                "Design vault schema",
                [
                    {"id": "turn_schema_101", "role": "user", "content": "Plan the schema migration for the local vault."},
                    {"id": "turn_schema_102", "role": "assistant", "content": "Keep the schema deterministic and versioned."},
                ],
            ),
        ]:
            transcript_path = transcript_dir / f"{session_id}.json"
            transcript_path.write_text(
                json.dumps(
                    {
                        "id": session_id,
                        "title": title,
                        "task_label": task_label,
                        "turns": turns,
                    }
                ),
                encoding="utf-8",
            )
            import_transcript_path(
                self.server.surface.vault,
                transcript_path,
                scope_kind="project",
                scope_value="ctxvault",
            )
        self.server.surface.episode_derive("sess_schema_design_001")
        self.server.surface.episode_derive("sess_schema_design_002")

        preview = self._request(
            5,
            "tools/call",
            {
                "name": "workstream.preview",
                "arguments": {"session_id": "sess_schema_design_001", "limit": 5},
            },
        )
        created = self._request(
            6,
            "tools/call",
            {
                "name": "workstream-candidate.create",
                "arguments": {
                    "session_id": "sess_schema_design_001",
                    "limit": 5,
                    "candidate_id": "wsc_mcp_schema_flow",
                },
            },
        )
        listed = self._request(
            7,
            "tools/call",
            {
                "name": "workstream-candidate.list",
                "arguments": {"proposal_state": "proposed", "scope_kind": "project", "scope_value": "ctxvault"},
            },
        )
        reviewed = self._request(
            8,
            "tools/call",
            {
                "name": "workstream-candidate.review",
                "arguments": {
                    "candidate_id": "wsc_mcp_schema_flow",
                    "decision": "approved",
                    "reviewer": "unit_test",
                },
            },
        )
        workstreams = self._request(
            9,
            "tools/call",
            {
                "name": "workstream.list",
                "arguments": {"scope_kind": "project", "scope_value": "ctxvault", "status": "active"},
            },
        )
        intelligence = self._request(
            10,
            "tools/call",
            {
                "name": "workstream.intelligence",
                "arguments": {"workstream_id": "ws_mcp_schema_flow", "limit": 6},
            },
        )
        compiled_state = self._request(
            11,
            "tools/call",
            {
                "name": "workstream.compiled-state",
                "arguments": {"workstream_id": "ws_mcp_schema_flow", "limit": 6},
            },
        )
        candidate_receipt = self._request(
            12,
            "tools/call",
            {
                "name": "workstream-candidate.receipt",
                "arguments": {
                    "candidate": reviewed["result"]["structuredContent"]["candidate"],
                    "output_path": "artifacts/workstream-candidate-receipt.json",
                    "task_id": "promote-workstream",
                },
            },
        )
        workstream_receipt = self._request(
            13,
            "tools/call",
            {
                "name": "workstream.receipt",
                "arguments": {
                    "workstream": reviewed["result"]["structuredContent"]["workstream"],
                    "output_path": "artifacts/workstream-receipt.json",
                    "plan_path": str((self.repo_root / "plans" / "demo.toml").resolve()),
                    "task_id": "durable-context",
                },
            },
        )

        self.assertEqual(preview["result"]["structuredContent"]["suggested_workstream"]["task_labels"], ["Design vault schema"])
        self.assertEqual(created["result"]["structuredContent"]["candidate"]["proposal_state"], "proposed")
        self.assertEqual([item["object_id"] for item in listed["result"]["structuredContent"]], ["wsc_mcp_schema_flow"])
        self.assertEqual(reviewed["result"]["structuredContent"]["candidate"]["proposal_state"], "merged")
        self.assertEqual(reviewed["result"]["structuredContent"]["workstream"]["id"], "ws_mcp_schema_flow")
        self.assertEqual([item["object_id"] for item in workstreams["result"]["structuredContent"]], ["ws_mcp_schema_flow"])
        self.assertEqual(
            intelligence["result"]["structuredContent"]["workstream_ref"],
            "workstream://ws_mcp_schema_flow",
        )
        self.assertGreaterEqual(intelligence["result"]["structuredContent"]["summary"]["gap_count"], 1)
        self.assertEqual(
            compiled_state["result"]["structuredContent"]["schema_id"],
            "ctxvault.compiled-workstream-state/v1",
        )
        self.assertEqual(
            compiled_state["result"]["structuredContent"]["contract_state"],
            "experimental_read_model",
        )
        self.assertEqual(
            candidate_receipt["result"]["structuredContent"]["receipt"]["plan_ledger_artifact"]["artifact_type"],
            "ctxvault_workstream_candidate_receipt",
        )
        self.assertEqual(
            workstream_receipt["result"]["structuredContent"]["receipt"]["plan_ledger_artifact"]["artifact_type"],
            "ctxvault_workstream_receipt",
        )

    def test_tools_call_runs_read_only_doctor_report(self) -> None:
        report = self._request(
            3,
            "tools/call",
            {
                "name": "doctor.report",
                "arguments": {},
            },
        )

        payload = report["result"]["structuredContent"]
        self.assertEqual(payload["schema_id"], "ctxvault.doctor-report/v1")
        self.assertEqual(payload["mode"], "read_only")
        self.assertTrue(all(check["read_only"] for check in payload["checks"]))

    def test_tools_call_routes_requests_and_returns_structured_content(self) -> None:
        recorded = self._request(
            3,
            "tools/call",
            {
                "name": "trace.record",
                "arguments": {
                    "model_name": "PromptAsset",
                    "payload": self.prompt_payload,
                },
            },
        )
        self.assertFalse(recorded["result"]["isError"])
        self.assertEqual(recorded["result"]["structuredContent"]["object_id"], "prompt_schema_designer_v1")

        resolved = self._request(
            4,
            "tools/call",
            {
                "name": "prompt.resolve",
                "arguments": {"prompt_id": "prompt_schema_designer_v1"},
            },
        )
        self.assertEqual(resolved["result"]["structuredContent"]["instruction"], self.prompt_payload["instruction"])

        policy = self._request(
            5,
            "tools/call",
            {
                "name": "policy.check",
                "arguments": {
                    "operation": "memory_promotion",
                    "sensitivity": "internal",
                },
            },
        )
        self.assertEqual(policy["result"]["structuredContent"]["decision"], "review_required")

        candidate = self._request(
            6,
            "tools/call",
            {
                "name": "trace.record",
                "arguments": {
                    "model_name": "MemoryCandidate",
                    "payload": self.memory_candidate_payload,
                },
            },
        )
        self.assertEqual(candidate["result"]["structuredContent"]["object_id"], self.memory_candidate_payload["id"])

        listed = self._request(
            7,
            "tools/call",
            {
                "name": "memory-candidate.list",
                "arguments": {"proposal_state": "proposed"},
            },
        )
        self.assertEqual(len(listed["result"]["structuredContent"]), 1)

        reviewed = self._request(
            8,
            "tools/call",
            {
                "name": "memory-candidate.review",
                "arguments": {
                    "candidate_id": self.memory_candidate_payload["id"],
                    "decision": "approved",
                    "reviewer": "unit_test",
                },
            },
        )
        self.assertEqual(reviewed["result"]["structuredContent"]["candidate"]["proposal_state"], "merged")
        self.assertEqual(reviewed["result"]["structuredContent"]["memory"]["id"], "mem_20260419_ctxvault_rule_001")

        patch = self._request(
            9,
            "tools/call",
            {
                "name": "trace.record",
                "arguments": {
                    "model_name": "PromptPatch",
                    "payload": self.prompt_patch_payload,
                },
            },
        )
        self.assertEqual(patch["result"]["structuredContent"]["object_id"], self.prompt_patch_payload["id"])

        patch_list = self._request(
            10,
            "tools/call",
            {
                "name": "prompt-patch.list",
                "arguments": {"proposal_state": "proposed", "prompt_asset_id": "prompt_schema_designer_v1"},
            },
        )
        self.assertEqual(len(patch_list["result"]["structuredContent"]), 1)

        patch_eval = self._request(
            110,
            "tools/call",
            {
                "name": "prompt-eval.run",
                "arguments": {
                    "target_type": "prompt_patch",
                    "target_id": self.prompt_patch_payload["id"],
                    "dataset_ref": "eval://mcp/prompt-patch",
                    "assert_contains": ["migration notes", "source-grounded rationale"],
                    "assert_not_contains": ["requires remote llm"],
                },
            },
        )
        self.assertEqual(patch_eval["result"]["structuredContent"]["eval_run"]["result"], "passed")

        patch_reviewed = self._request(
            11,
            "tools/call",
            {
                "name": "prompt-patch.review",
                "arguments": {
                    "patch_id": self.prompt_patch_payload["id"],
                    "decision": "approved",
                    "reviewer": "unit_test",
                },
            },
        )
        self.assertEqual(patch_reviewed["result"]["structuredContent"]["patch"]["proposal_state"], "merged")
        self.assertIn("migration notes", patch_reviewed["result"]["structuredContent"]["prompt"]["instruction"])

        prompt_eval = self._request(
            12,
            "tools/call",
            {
                "name": "prompt-eval.run",
                "arguments": {
                    "target_type": "prompt_asset",
                    "target_id": "prompt_schema_designer_v1",
                    "dataset_ref": "eval://mcp/prompt-asset",
                    "assert_contains": ["migration notes", "source-grounded rationale"],
                    "assert_not_contains": ["requires remote llm"],
                },
            },
        )
        self.assertEqual(prompt_eval["result"]["structuredContent"]["eval_run"]["result"], "passed")
        self.assertEqual(prompt_eval["result"]["structuredContent"]["evaluated_prompt"]["eval_status"], "passed")

        privacy = self._request(
            13,
            "tools/call",
            {
                "name": "privacy.scan",
                "arguments": {
                    "text": 'Email chris@example.com and use sk-1234567890abcdefghijklmnop',
                    "source": "mcp-test",
                },
            },
        )
        self.assertEqual(privacy["result"]["structuredContent"]["source"], "mcp-test")
        self.assertEqual(privacy["result"]["structuredContent"]["decision"], "block")
        self.assertEqual(privacy["result"]["structuredContent"]["summary"]["total_findings"], 2)

        claim = json.loads((ROOT / "fixtures" / "evidence" / "claim-record.json").read_text())
        evidence = json.loads((ROOT / "fixtures" / "evidence" / "evidence-link.json").read_text())
        self.server.surface.vault.capture_claim(claim)
        self.server.surface.vault.link_evidence(evidence)

        bundle = self._request(
            14,
            "tools/call",
            {
                "name": "context.build",
                "arguments": {
                    "request": {
                        "scope_kind": "project",
                        "scope_value": "ctxvault",
                        "task_label": "mcp context receipt",
                        "prompt_id": "prompt_schema_designer_v1",
                        "memory_query": "local LLM",
                        "knowledge_query": "source-grounded rationale",
                    }
                },
            },
        )
        context_receipt = self._request(
            15,
            "tools/call",
            {
                "name": "context.receipt",
                "arguments": {
                    "bundle": bundle["result"]["structuredContent"],
                    "output_path": "artifacts/context-receipt.json",
                    "task_id": "context",
                },
            },
        )
        self.assertEqual(
            context_receipt["result"]["structuredContent"]["receipt"]["plan_ledger_artifact"]["artifact_type"],
            "ctxvault_context_bundle_receipt",
        )
        self.assertTrue(Path(context_receipt["result"]["structuredContent"]["receipt_path"]).exists())

        audit = self._request(
            16,
            "tools/call",
            {
                "name": "audit.run",
                "arguments": {
                    "scope_kind": "project",
                    "scope_value": "ctxvault",
                    "subject_ref": claim["subject_ref"],
                },
            },
        )
        audit_receipt = self._request(
            17,
            "tools/call",
            {
                "name": "audit.receipt",
                "arguments": {
                    "audit": audit["result"]["structuredContent"],
                    "output_path": "artifacts/audit-receipt.json",
                    "task_id": "audit",
                },
            },
        )
        self.assertEqual(
            audit_receipt["result"]["structuredContent"]["receipt"]["plan_ledger_artifact"]["artifact_type"],
            "ctxvault_audit_receipt",
        )
        self.assertTrue(Path(audit_receipt["result"]["structuredContent"]["receipt_path"]).exists())

        transcript_path = self.repo_root / "episode-demo.json"
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_episode_demo",
                    "title": "Episode Demo",
                    "turns": [
                        {"id": "turn_ep_001", "role": "user", "content": "Plan the rollout and break it into phases."},
                        {"id": "turn_ep_002", "role": "assistant", "content": "Start with deterministic storage, then privacy checks."},
                        {"id": "turn_ep_003", "role": "user", "content": "Now implement episode derivation in the CLI."},
                        {"id": "turn_ep_004", "role": "assistant", "content": "I will add episode objects and synthesis export."},
                    ],
                }
            ),
            encoding="utf-8",
        )
        from ctxgov.ingest import import_transcript_path

        import_transcript_path(
            self.server.surface.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        derived = self._request(
            18,
            "tools/call",
            {
                "name": "episode.derive",
                "arguments": {"session_id": "sess_episode_demo"},
            },
        )
        self.assertEqual(
            [episode["kind"] for episode in derived["result"]["structuredContent"]["episodes"]],
            ["plan", "execute"],
        )

        listed_episodes = self._request(
            19,
            "tools/call",
            {
                "name": "episode.list",
                "arguments": {"session_id": "sess_episode_demo"},
            },
        )
        self.assertEqual(len(listed_episodes["result"]["structuredContent"]), 2)

        synthesized = self._request(
            20,
            "tools/call",
            {
                "name": "episode.synthesize",
                "arguments": {"episode_id": derived["result"]["structuredContent"]["episodes"][0]["id"]},
            },
        )
        artifact_id = synthesized["result"]["structuredContent"]["knowledge_artifact"]["id"]
        self.assertEqual(
            synthesized["result"]["structuredContent"]["knowledge_artifact"]["kind"],
            "synthesis",
        )

        exported = self._request(
            21,
            "tools/call",
            {
                "name": "knowledge.export-note",
                "arguments": {
                    "knowledge_id": artifact_id,
                    "output_path": "artifacts/episode-note.md",
                    "canonical_target": "project:ctxvault",
                },
            },
        )
        self.assertTrue(Path(exported["result"]["structuredContent"]["output_path"]).exists())
        self.assertEqual(exported["result"]["structuredContent"]["canonical_target"], "project:ctxvault")

        snapshot = self._request(
            22,
            "tools/call",
            {
                "name": "snapshot.create",
                "arguments": {
                    "scope_kind": "project",
                    "scope_value": "ctxvault",
                    "label": "mcp snapshot",
                },
            },
        )
        self.assertTrue(Path(snapshot["result"]["structuredContent"]["manifest_path"]).exists())

        snapshots = self._request(
            23,
            "tools/call",
            {
                "name": "snapshot.list",
                "arguments": {"limit": 5},
            },
        )
        self.assertEqual(snapshots["result"]["structuredContent"][0]["snapshot_id"], snapshot["result"]["structuredContent"]["snapshot_id"])

        readme = self.repo_root / "README.md"
        readme.write_text("# ctxvault\n", encoding="utf-8")
        base_snapshot = self._request(
            24,
            "tools/call",
            {
                "name": "snapshot.create",
                "arguments": {
                    "scope_kind": "project",
                    "scope_value": "ctxvault",
                    "label": "base diff",
                },
            },
        )
        readme.write_text("# ctxvault\n\nchanged\n", encoding="utf-8")
        self.server.surface.trace_record("KnowledgeArtifact", json.loads((ROOT / "fixtures" / "core" / "knowledge-artifact.json").read_text()))
        head_snapshot = self._request(
            25,
            "tools/call",
            {
                "name": "snapshot.create",
                "arguments": {
                    "scope_kind": "project",
                    "scope_value": "ctxvault",
                    "label": "head diff",
                },
            },
        )
        diff = self._request(
            26,
            "tools/call",
            {
                "name": "snapshot.diff",
                "arguments": {
                    "base_snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "head_snapshot_id": head_snapshot["result"]["structuredContent"]["snapshot_id"],
                },
            },
        )
        self.assertEqual(diff["result"]["structuredContent"]["summary"]["workspace"]["modified"], 1)

        lineage = self._request(
            27,
            "tools/call",
            {
                "name": "snapshot.lineage",
                "arguments": {
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "limit": 10,
                },
            },
        )
        self.assertEqual(lineage["result"]["structuredContent"]["summary"]["matched_event_count"], 1)

        provenance = self._request(
            28,
            "tools/call",
            {
                "name": "snapshot.provenance",
                "arguments": {
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "limit": 10,
                },
            },
        )
        self.assertFalse(provenance["result"]["structuredContent"]["is_imported_replica"])

        restore_plan = self._request(
            29,
            "tools/call",
            {
                "name": "snapshot.restore-plan",
                "arguments": {
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                },
            },
        )
        self.assertEqual(restore_plan["result"]["structuredContent"]["summary"]["workspace"]["write"], 1)
        self.assertEqual(restore_plan["result"]["structuredContent"]["summary"]["vault"]["delete"], 1)
        self.assertTrue(restore_plan["result"]["structuredContent"]["requires_review"])
        self.assertTrue(restore_plan["result"]["structuredContent"]["restore_bundle_available"])

        restore_apply = self._request(
            30,
            "tools/call",
            {
                "name": "snapshot.restore-apply",
                "arguments": {
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "allow_deletes": True,
                    "reviewed_by": "mcp-reviewer",
                },
            },
        )
        self.assertEqual(restore_apply["result"]["structuredContent"]["receipt"]["reviewed_by"], "mcp-reviewer")
        self.assertEqual(readme.read_text(encoding="utf-8"), "# ctxvault\n")

        sync_manifest = self._request(
            31,
            "tools/call",
            {
                "name": "sync.manifest",
                "arguments": {
                    "target": (self.repo_root / "mcp-replica").as_uri(),
                    "transport": "local_copy",
                    "device_id": "mcp-device",
                },
            },
        )
        self.assertEqual(sync_manifest["result"]["structuredContent"]["sync_manifest"]["snapshot_id"], base_snapshot["result"]["structuredContent"]["snapshot_id"])
        self.assertTrue(Path(sync_manifest["result"]["structuredContent"]["sync_manifest_path"]).exists())

        sync_manifest_apply = self._request(
            32,
            "tools/call",
            {
                "name": "sync.manifest.apply",
                "arguments": {
                    "sync_manifest_path": sync_manifest["result"]["structuredContent"]["sync_manifest_path"],
                },
            },
        )
        self.assertEqual(sync_manifest_apply["result"]["structuredContent"]["receipt"]["status"], "copied")
        self.assertTrue(
            Path(self.repo_root / "mcp-replica" / "snapshots" / Path(base_snapshot["result"]["structuredContent"]["manifest_path"]).name).exists()
        )

        replica_verify = self._request(
            33,
            "tools/call",
            {
                "name": "replica.verify",
                "arguments": {
                    "replica_root": str(self.repo_root / "mcp-replica"),
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                },
            },
        )
        self.assertEqual(replica_verify["result"]["structuredContent"]["status"], "verified")

        replica_import = self._request(
            34,
            "tools/call",
            {
                "name": "replica.import",
                "arguments": {
                    "replica_root": str(self.repo_root / "mcp-replica"),
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "trust_policy": {
                        "default_decision": "allow",
                        "require_sync_manifest": True,
                        "trusted_device_ids": [],
                        "allowed_transports": ["local_copy"],
                    },
                },
            },
        )
        self.assertEqual(replica_import["result"]["structuredContent"]["receipt"]["status"], "imported")

        replica_trust = self._request(
            35,
            "tools/call",
            {
                "name": "replica.trust-evaluate",
                "arguments": {
                    "replica_root": str(self.repo_root / "mcp-replica"),
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "trust_policy": {
                        "default_decision": "review",
                        "require_sync_manifest": True,
                        "trusted_device_ids": ["another-device"],
                        "allowed_transports": ["local_copy"],
                    },
                },
            },
        )
        self.assertEqual(replica_trust["result"]["structuredContent"]["decision"], "review")

        replica_trust_set = self._request(
            36,
            "tools/call",
            {
                "name": "replica.trust.set",
                "arguments": {
                    "device_id": "mcp-device",
                    "trust_state": "allow",
                    "label": "MCP Device",
                    "allowed_transports": ["local_copy"],
                },
            },
        )
        self.assertEqual(replica_trust_set["result"]["structuredContent"]["entry"]["device_id"], "mcp-device")

        replica_trust_list = self._request(
            37,
            "tools/call",
            {
                "name": "replica.trust.list",
                "arguments": {},
            },
        )
        self.assertEqual(replica_trust_list["result"]["structuredContent"]["device_count"], 1)

        readme.write_text("# ctxvault\n\ndrift\n", encoding="utf-8")
        self.server.surface.trace_record("KnowledgeArtifact", json.loads((ROOT / "fixtures" / "core" / "knowledge-artifact.json").read_text()))

        replica_apply = self._request(
            38,
            "tools/call",
            {
                "name": "replica.apply",
                "arguments": {
                    "replica_root": str(self.repo_root / "mcp-replica"),
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "allow_deletes": True,
                    "reviewed_by": "mcp-apply-reviewer",
                    "trust_policy": {
                        "default_decision": "allow",
                        "require_sync_manifest": True,
                        "trusted_device_ids": [],
                        "allowed_transports": ["local_copy"],
                    },
                },
            },
        )
        self.assertEqual(replica_apply["result"]["structuredContent"]["receipt"]["status"], "applied")
        self.assertEqual(replica_apply["result"]["structuredContent"]["receipt"]["trust_decision"], "allow")
        self.assertEqual(replica_apply["result"]["structuredContent"]["restored"]["receipt"]["reviewed_by"], "mcp-apply-reviewer")
        self.assertEqual(readme.read_text(encoding="utf-8"), "# ctxvault\n")

        sync_receipt = self._request(
            39,
            "tools/call",
            {
                "name": "sync.receipt",
                "arguments": {
                    "snapshot_id": base_snapshot["result"]["structuredContent"]["snapshot_id"],
                    "target": "file:///Volumes/local-backup/ctxvault",
                    "transport": "local_copy",
                    "device_id": "mcp-device",
                },
            },
        )
        self.assertTrue(Path(sync_receipt["result"]["structuredContent"]["receipt_path"]).exists())
        self.assertEqual(sync_receipt["result"]["structuredContent"]["receipt"]["device_id"], "mcp-device")

        sync_status = self._request(
            40,
            "tools/call",
            {
                "name": "sync.status",
                "arguments": {"limit": 10},
            },
        )
        self.assertEqual(sync_status["result"]["structuredContent"]["summary"]["target_count"], 1)
        self.assertEqual(sync_status["result"]["structuredContent"]["summary"]["out_of_date_target_count"], 0)
        self.assertEqual(sync_status["result"]["structuredContent"]["targets"][0]["state"], "in_sync")

    def test_stdio_transport_handles_initialize_list_and_call(self) -> None:
        env = dict(os.environ)
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(SRC) if not existing_pythonpath else f"{SRC}{os.pathsep}{existing_pythonpath}"
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ctxgov.cli",
                "serve-mcp",
                "--root",
                str(self.repo_root),
                "--policy-json-path",
                str(self.policy_path),
                "--backup-json-path",
                str(self.backup_path),
                "--profile-json-path",
                str(self.profile_path),
            ],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        try:
            assert process.stdin is not None
            assert process.stdout is not None

            write_message(
                process.stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-03-26"},
                },
            )
            initialize = read_message(process.stdout)
            self.assertEqual(initialize["result"]["serverInfo"]["name"], "ctxvault")

            write_message(
                process.stdin,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
            )
            write_message(
                process.stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                },
            )
            listed = read_message(process.stdout)
            names = [tool["name"] for tool in listed["result"]["tools"]]
            self.assertIn("adapter.resolve", names)

            write_message(
                process.stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "trace.record",
                        "arguments": {
                            "model_name": "PromptAsset",
                            "payload": self.prompt_payload,
                        },
                    },
                },
            )
            recorded = read_message(process.stdout)
            self.assertEqual(recorded["result"]["structuredContent"]["object_id"], "prompt_schema_designer_v1")

            write_message(
                process.stdin,
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": "prompt.resolve",
                        "arguments": {"prompt_id": "prompt_schema_designer_v1"},
                    },
                },
            )
            resolved = read_message(process.stdout)
            self.assertEqual(resolved["result"]["structuredContent"]["instruction"], self.prompt_payload["instruction"])
        finally:
            if process.stdin is not None:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()
            stderr = ""
            if process.stderr is not None:
                stderr = process.stderr.read().decode("utf-8")
                process.stderr.close()
            returncode = process.wait(timeout=5)
            self.assertEqual(returncode, 0, msg=stderr)


if __name__ == "__main__":
    unittest.main()
