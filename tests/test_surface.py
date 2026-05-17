from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.core import CtxVault
from ctxgov.ingest import import_transcript_path
from ctxgov.layout import default_layout
from ctxgov.policy import CtxVaultPolicy
from ctxgov.surface import CtxVaultSurface


class SurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.surface = CtxVaultSurface(CtxVault(default_layout(self.repo_root)))
        self.core_fixture_root = ROOT / "fixtures" / "core"
        self.evidence_fixture_root = ROOT / "fixtures" / "evidence"
        self.controls_fixture_root = ROOT / "fixtures" / "controls"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _core_fixture(self, name: str) -> dict:
        return json.loads((self.core_fixture_root / name).read_text())

    def _evidence_fixture(self, name: str) -> dict:
        return json.loads((self.evidence_fixture_root / name).read_text())

    def _control_fixture(self, name: str) -> dict:
        return json.loads((self.controls_fixture_root / name).read_text())

    def _import_session(
        self,
        *,
        session_id: str,
        title: str,
        task_label: str,
        turns: list[dict[str, str]],
    ) -> None:
        transcript_path = self.repo_root / "transcripts" / f"{session_id}.json"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
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
            self.surface.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

    def test_surface_wraps_named_primitives(self) -> None:
        prompt_record = self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        self.surface.trace_record("Memory", self._core_fixture("memory.json"))
        self.surface.trace_record("KnowledgeArtifact", self._core_fixture("knowledge-artifact.json"))

        resolved = self.surface.prompt_resolve("prompt_schema_designer_v1")
        prompts = self.surface.prompt_list(
            scope_kind="project",
            scope_value="ctxvault",
            limit=3,
        )
        memories = self.surface.memory_search(
            "local LLM",
            scope_kind="project",
            scope_value="ctxvault",
            limit=3,
        )
        bundle = self.surface.context_build(
            {
                "scope_kind": "project",
                "scope_value": "ctxvault",
                "task_label": "continue schema work",
                "prompt_id": "prompt_schema_designer_v1",
                "memory_query": "local LLM",
                "knowledge_query": "local-first context layer",
            }
        )

        self.assertEqual(prompt_record["object_kind"], "prompt_asset")
        self.assertEqual(resolved["object_id"], "prompt_schema_designer_v1")
        self.assertEqual(prompts[0]["object_id"], "prompt_schema_designer_v1")
        self.assertEqual(memories[0]["object_id"], "mem_20260419_ctxvault_rule_001")
        self.assertEqual(bundle["scope"]["value"], "ctxvault")

        claim = self._evidence_fixture("claim-record.json")
        evidence = self._evidence_fixture("evidence-link.json")
        self.surface.vault.capture_claim(claim)
        self.surface.vault.link_evidence(evidence)

        audit = self.surface.audit_run(
            scope_kind="project",
            scope_value="ctxvault",
            subject_ref=claim["subject_ref"],
        )
        self.assertEqual(audit["verdict"], "supported_by_local_evidence")

    def test_surface_emits_backup_bundle(self) -> None:
        (self.repo_root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
        (self.repo_root / "module.yaml").write_text("metadata:\n  name: ctxvault\n", encoding="utf-8")
        (self.repo_root / "src").mkdir()
        (self.repo_root / "src" / "app.py").write_text("print('ctxvault')\n", encoding="utf-8")

        result = self.surface.backup_emit(
            root=self.repo_root,
            output_path=self.repo_root / "backup" / "latest-backup-check.json",
            receipt_format="plan-ledger",
            scope_kind="project",
            scope_value="ctxvault",
            plan_id="p1",
            target="plans/p1.toml",
        )

        self.assertEqual(result["receipt"]["status"], "fresh")
        self.assertTrue(Path(result["archive_path"]).exists())

    def test_surface_runs_prompt_eval(self) -> None:
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))

        result = self.surface.prompt_eval_run(
            "prompt_asset",
            "prompt_schema_designer_v1",
            dataset_ref="eval://surface/prompt-asset",
            assert_contains=["governance hooks"],
            assert_not_contains=["requires remote llm"],
        )

        self.assertEqual(result["eval_run"]["result"], "passed")
        self.assertEqual(result["evaluated_prompt"]["eval_status"], "passed")

    def test_surface_runs_privacy_scan(self) -> None:
        result = self.surface.privacy_scan(
            'Contact me at chris@example.com or use OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"',
            source="unit-test",
        )

        self.assertEqual(result["source"], "unit-test")
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["highest_severity"], "critical")
        self.assertEqual(result["summary"]["total_findings"], 2)

    def test_surface_runs_attachment_privacy_scan(self) -> None:
        attachment = self.repo_root / "attachment.txt"
        attachment.write_text('OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"\n', encoding="utf-8")

        result = self.surface.privacy_scan_files([attachment], source="surface-attachment-test")

        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["summary"]["file_count"], 1)
        self.assertEqual(result["files"][0]["content_scan_state"], "scanned")
        self.assertEqual(result["files"][0]["decision"], "block")

    def test_surface_companion_share_handoff_stage_preview_and_consume(self) -> None:
        shared_root = self.repo_root / "app-group"
        attachment = shared_root / "attachments" / "note.txt"
        attachment.parent.mkdir(parents=True, exist_ok=True)
        attachment.write_text("Keep iPhone capture candidate-first.\n", encoding="utf-8")

        staged = self.surface.companion_share_handoff_stage(
            shared_root=shared_root,
            title="iPhone capture principle",
            text="Use a governed handoff queue before capture promotion.",
            urls=["https://example.com/iphone-capture"],
            attachment_paths=["attachments/note.txt"],
            source_app="share_extension",
            imported_via="ctxvault_share_extension",
        )
        preview = self.surface.companion_share_handoff_preview(
            shared_root=shared_root,
            handoff_path=Path(staged["handoff_path"]),
        )
        consumed = self.surface.companion_share_handoff_consume(
            shared_root=shared_root,
            handoff_path=Path(staged["handoff_path"]),
            why_it_matters="This keeps mobile capture lightweight without bypassing governed review.",
            reviewed_by="surface_share_handoff_test",
        )
        listed = self.surface.companion_share_handoff_list(shared_root=shared_root, include_archived=True)

        self.assertEqual(staged["handoff"]["status"], "pending")
        self.assertEqual(preview["decision"], "allow")
        self.assertEqual(preview["capture_defaults"]["statement"], "iPhone capture principle")
        self.assertEqual(consumed["handoff"]["status"], "consumed")
        self.assertEqual(consumed["handoff"]["consumed_by"], "surface_share_handoff_test")
        self.assertEqual(consumed["capture"]["candidate"]["proposal_state"], "proposed")
        self.assertTrue(
            any(ref.startswith("share-handoff://") for ref in consumed["capture"]["candidate"]["source_refs"])
        )
        self.assertEqual(listed["summary"]["archived_count"], 1)

    def test_surface_share_handoff_consume_blocks_sensitive_payload_by_default(self) -> None:
        shared_root = self.repo_root / "app-group-blocked"
        staged = self.surface.companion_share_handoff_stage(
            shared_root=shared_root,
            text='OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"',
        )

        with self.assertRaises(ValueError):
            self.surface.companion_share_handoff_consume(
                shared_root=shared_root,
                handoff_path=Path(staged["handoff_path"]),
                why_it_matters="This should not be captured without explicit override.",
            )

    def test_surface_emits_context_and_audit_receipts(self) -> None:
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        self.surface.trace_record("Memory", self._core_fixture("memory.json"))
        self.surface.trace_record("KnowledgeArtifact", self._core_fixture("knowledge-artifact.json"))
        claim = self._evidence_fixture("claim-record.json")
        evidence = self._evidence_fixture("evidence-link.json")
        self.surface.vault.capture_claim(claim)
        self.surface.vault.link_evidence(evidence)

        bundle = self.surface.context_build(
            {
                "scope_kind": "project",
                "scope_value": "ctxvault",
                "task_label": "emit receipts",
                "prompt_id": "prompt_schema_designer_v1",
                "memory_query": "local LLM",
                "knowledge_query": "local-first context layer",
            }
        )
        audit = self.surface.audit_run(
            scope_kind="project",
            scope_value="ctxvault",
            subject_ref=claim["subject_ref"],
        )

        context_receipt = self.surface.context_receipt_emit(
            bundle,
            output_path=self.repo_root / "artifacts" / "bundle-receipt.json",
            plan_path=self.repo_root / "plans" / "demo.toml",
            task_id="context",
        )
        audit_receipt = self.surface.audit_receipt_emit(
            audit,
            output_path=self.repo_root / "artifacts" / "audit-receipt.json",
            task_id="audit",
        )

        self.assertTrue(Path(context_receipt["receipt_path"]).exists())
        self.assertEqual(context_receipt["receipt"]["bundle_ref"], f"bundle://{bundle['id']}")
        self.assertEqual(context_receipt["receipt"]["plan_ledger_artifact"]["artifact_type"], "ctxvault_context_bundle_receipt")
        self.assertIn("uv run plan-ledger task artifact", context_receipt["receipt"]["plan_ledger_artifact"]["suggested_command"])
        self.assertTrue(Path(audit_receipt["receipt_path"]).exists())
        self.assertEqual(audit_receipt["receipt"]["audit_ref"], f"audit://{audit['id']}")
        self.assertEqual(audit_receipt["receipt"]["plan_ledger_artifact"]["artifact_type"], "ctxvault_audit_receipt")

    def test_surface_emits_workstream_receipts(self) -> None:
        workstream_candidate = self._core_fixture("workstream-candidate.json")
        workstream = self._core_fixture("workstream.json")
        self.surface.trace_record("WorkstreamCandidate", workstream_candidate)
        self.surface.trace_record("Workstream", workstream)

        candidate_receipt = self.surface.workstream_candidate_receipt_emit(
            workstream_candidate,
            output_path=self.repo_root / "artifacts" / "workstream-candidate-receipt.json",
            task_id="promote-workstream",
        )
        workstream_receipt = self.surface.workstream_receipt_emit(
            workstream,
            output_path=self.repo_root / "artifacts" / "workstream-receipt.json",
            plan_path=self.repo_root / "plans" / "demo.toml",
            task_id="durable-context",
        )

        self.assertTrue(Path(candidate_receipt["receipt_path"]).exists())
        self.assertEqual(
            candidate_receipt["receipt"]["plan_ledger_artifact"]["artifact_type"],
            "ctxvault_workstream_candidate_receipt",
        )
        self.assertEqual(
            candidate_receipt["receipt"]["candidate_ref"],
            f"workstream-candidate://{workstream_candidate['id']}",
        )
        self.assertTrue(Path(workstream_receipt["receipt_path"]).exists())
        self.assertEqual(
            workstream_receipt["receipt"]["plan_ledger_artifact"]["artifact_type"],
            "ctxvault_workstream_receipt",
        )
        self.assertEqual(
            workstream_receipt["receipt"]["workstream_ref"],
            f"workstream://{workstream['id']}",
        )

    def test_surface_lists_and_resolves_plugins(self) -> None:
        manifest = self._evidence_fixture("plugin-manifest.json")

        manifests = self.surface.plugin_status([manifest])
        resolution = self.surface.plugin_resolve([manifest], "projection.harness.agents-md")

        self.assertEqual(manifests[0]["id"], "portable-harness-projection")
        self.assertEqual(resolution["decision"], "use_plugin")
        self.assertEqual(resolution["selected_plugin"]["id"], "portable-harness-projection")

    def test_surface_emits_agents_md_projection(self) -> None:
        workstream = self._core_fixture("workstream.json")
        memory = self._core_fixture("memory.json")
        self.surface.vault.store_core_object("Workstream", workstream)
        self.surface.vault.store_core_object("Memory", memory)

        result = self.surface.harness_agents_md_emit(
            workstream_id=workstream["id"],
            output_path=self.repo_root / "exports" / "AGENTS.md",
            receipt_output_path=self.repo_root / "artifacts" / "agents-md-receipt.json",
            memory_limit=5,
        )

        rendered = (self.repo_root / "exports" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("# AGENTS.md", rendered)
        self.assertIn(workstream["title"], rendered)
        self.assertIn(memory["statement"], rendered)
        self.assertTrue(Path(result["receipt_path"]).exists())
        self.assertEqual(result["receipt"]["target_kind"], "harness.agents-md")
        self.assertEqual(result["receipt"]["plugin_id"], "portable-harness-projection")

    def test_surface_emits_claude_md_projection(self) -> None:
        workstream = self._core_fixture("workstream.json")
        memory = self._core_fixture("memory.json")
        self.surface.vault.store_core_object("Workstream", workstream)
        self.surface.vault.store_core_object("Memory", memory)

        result = self.surface.harness_claude_md_emit(
            workstream_id=workstream["id"],
            output_path=self.repo_root / "exports" / "CLAUDE.md",
            receipt_output_path=self.repo_root / "artifacts" / "claude-md-receipt.json",
            memory_limit=5,
        )

        rendered = (self.repo_root / "exports" / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("# CLAUDE.md", rendered)
        self.assertIn(workstream["title"], rendered)
        self.assertIn(memory["statement"], rendered)
        self.assertTrue(Path(result["receipt_path"]).exists())
        self.assertEqual(result["receipt"]["target_kind"], "harness.claude-md")
        self.assertEqual(result["receipt"]["plugin_id"], "portable-harness-projection")
        self.assertEqual(result["receipt"]["plan_ledger_artifact"]["artifact_type"], "ctxvault_projection_receipt")

    def test_surface_emits_wiki_workstream_projection(self) -> None:
        workstream = self._core_fixture("workstream.json")
        memory = self._core_fixture("memory.json")
        self.surface.vault.store_core_object("Workstream", workstream)
        self.surface.vault.store_core_object("Memory", memory)

        result = self.surface.wiki_workstream_markdown_emit(
            workstream_id=workstream["id"],
            output_path=self.repo_root / "exports" / "ctxvault-workstream.md",
            receipt_output_path=self.repo_root / "artifacts" / "wiki-md-receipt.json",
            memory_limit=5,
        )

        rendered = (self.repo_root / "exports" / "ctxvault-workstream.md").read_text(encoding="utf-8")
        self.assertIn(f"# {workstream['title']}", rendered)
        self.assertIn("## Durable Rules", rendered)
        self.assertIn(memory["statement"], rendered)
        self.assertEqual(result["receipt"]["target_kind"], "wiki.markdown-workstream")
        self.assertEqual(result["receipt"]["projection_kind"], "wiki")

    def test_surface_executes_plugin_capability(self) -> None:
        manifest = self._evidence_fixture("plugin-manifest.json")
        workstream = self._core_fixture("workstream.json")
        memory = self._core_fixture("memory.json")
        self.surface.vault.store_core_object("Workstream", workstream)
        self.surface.vault.store_core_object("Memory", memory)

        executed = self.surface.plugin_execute(
            [manifest],
            "projection.harness.agents-md",
            {
                "workstream_id": workstream["id"],
                "output_path": str(self.repo_root / "exports" / "AGENTS-plugin.md"),
                "receipt_output_path": str(self.repo_root / "artifacts" / "agents-plugin-receipt.json"),
                "memory_limit": 5,
            },
        )

        self.assertEqual(executed["capability"], "projection.harness.agents-md")
        self.assertEqual(executed["plugin"]["id"], "portable-harness-projection")
        self.assertEqual(executed["result"]["receipt"]["target_kind"], "harness.agents-md")
        self.assertTrue(Path(executed["result"]["output_path"]).exists())

    def test_surface_executes_claude_plugin_capability(self) -> None:
        manifest = self._evidence_fixture("plugin-manifest.json")
        workstream = self._core_fixture("workstream.json")
        memory = self._core_fixture("memory.json")
        self.surface.vault.store_core_object("Workstream", workstream)
        self.surface.vault.store_core_object("Memory", memory)

        executed = self.surface.plugin_execute(
            [manifest],
            "projection.harness.claude-md",
            {
                "workstream_id": workstream["id"],
                "output_path": str(self.repo_root / "exports" / "CLAUDE-plugin.md"),
                "receipt_output_path": str(self.repo_root / "artifacts" / "claude-plugin-receipt.json"),
                "memory_limit": 5,
            },
        )

        self.assertEqual(executed["capability"], "projection.harness.claude-md")
        self.assertEqual(executed["plugin"]["id"], "portable-harness-projection")
        self.assertEqual(executed["result"]["receipt"]["target_kind"], "harness.claude-md")
        self.assertTrue(Path(executed["result"]["output_path"]).exists())

    def test_surface_executes_wiki_plugin_capability(self) -> None:
        manifest = self._evidence_fixture("plugin-manifest.json")
        workstream = self._core_fixture("workstream.json")
        memory = self._core_fixture("memory.json")
        self.surface.vault.store_core_object("Workstream", workstream)
        self.surface.vault.store_core_object("Memory", memory)

        executed = self.surface.plugin_execute(
            [manifest],
            "projection.wiki.markdown-workstream",
            {
                "workstream_id": workstream["id"],
                "output_path": str(self.repo_root / "exports" / "wiki-plugin.md"),
                "receipt_output_path": str(self.repo_root / "artifacts" / "wiki-plugin-receipt.json"),
                "memory_limit": 5,
            },
        )

        self.assertEqual(executed["capability"], "projection.wiki.markdown-workstream")
        self.assertEqual(executed["plugin"]["id"], "portable-harness-projection")
        self.assertEqual(executed["result"]["receipt"]["target_kind"], "wiki.markdown-workstream")
        self.assertTrue(Path(executed["result"]["output_path"]).exists())

    def test_surface_creates_and_lists_snapshots(self) -> None:
        (self.repo_root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))

        created = self.surface.snapshot_create(
            scope_kind="project",
            scope_value="ctxvault",
            label="surface snapshot",
        )
        listed = self.surface.snapshot_list(limit=10)

        self.assertTrue(Path(created["manifest_path"]).exists())
        self.assertEqual(listed[0]["snapshot_id"], created["snapshot_id"])
        self.assertEqual(listed[0]["label"], "surface snapshot")

    def test_surface_diffs_snapshots_and_emits_sync_receipt(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        base = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="base")

        readme.write_text("# CtxVault\n\nmodified\n", encoding="utf-8")
        self.surface.trace_record("KnowledgeArtifact", self._core_fixture("knowledge-artifact.json"))
        head = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="head")

        diff = self.surface.snapshot_diff(
            base_snapshot_id=base["snapshot_id"],
            head_snapshot_id=head["snapshot_id"],
        )
        sync = self.surface.sync_receipt_emit(
            snapshot_id=head["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="surface-device",
        )

        self.assertEqual(diff["summary"]["workspace"]["modified"], 1)
        self.assertEqual(diff["summary"]["vault"]["added"], 1)
        self.assertTrue(Path(sync["receipt_path"]).exists())
        self.assertEqual(sync["receipt"]["device_id"], "surface-device")
        self.assertTrue(listed := self.surface.snapshot_list(limit=10))
        self.assertTrue(listed[0]["restore_bundle_available"])

    def test_surface_emits_snapshot_restore_plan(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        base = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="restore base")

        readme.write_text("# CtxVault\n\nmodified\n", encoding="utf-8")
        self.surface.trace_record("KnowledgeArtifact", self._core_fixture("knowledge-artifact.json"))

        plan = self.surface.snapshot_restore_plan(snapshot_id=base["snapshot_id"])

        self.assertEqual(plan["summary"]["workspace"]["write"], 1)
        self.assertEqual(plan["summary"]["vault"]["delete"], 1)
        self.assertTrue(plan["requires_review"])
        self.assertTrue(plan["restore_bundle_available"])

    def test_surface_reports_sync_status(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        base = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="sync base")
        self.surface.sync_receipt_emit(
            snapshot_id=base["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="surface-sync-device",
        )

        readme.write_text("# CtxVault\n\nnew snapshot\n", encoding="utf-8")
        head = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="sync head")
        status = self.surface.sync_status(limit=10)

        self.assertEqual(status["latest_local_snapshot"]["snapshot_id"], head["snapshot_id"])
        self.assertEqual(status["targets"][0]["state"], "behind")
        self.assertEqual(status["targets"][0]["pending_snapshot_ids"], [head["snapshot_id"]])

    def test_surface_applies_snapshot_restore(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        base = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="apply base")

        readme.write_text("# CtxVault\n\nmodified\n", encoding="utf-8")
        self.surface.trace_record("KnowledgeArtifact", self._core_fixture("knowledge-artifact.json"))
        result = self.surface.snapshot_restore_apply(
            snapshot_id=base["snapshot_id"],
            allow_deletes=True,
            reviewed_by="surface-reviewer",
        )

        self.assertEqual(readme.read_text(encoding="utf-8"), "# CtxVault\n")
        self.assertEqual(result["receipt"]["reviewed_by"], "surface-reviewer")
        self.assertFalse(
            (self.surface.vault.layout.objects_dir / "knowledge_artifact" / "know_proj_ctxvault_profile_v1.json").exists()
        )

    def test_surface_emits_sync_manifest(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        base = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="manifest base")
        readme.write_text("# CtxVault\n\nhead\n", encoding="utf-8")
        self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="manifest head")
        self.surface.snapshot_restore_apply(snapshot_id=base["snapshot_id"])

        result = self.surface.sync_manifest_emit(
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="surface-manifest-device",
        )

        self.assertTrue(Path(result["sync_manifest_path"]).exists())
        self.assertEqual(result["sync_manifest"]["snapshot_id"], base["snapshot_id"])
        self.assertEqual(result["sync_manifest"]["device_id"], "surface-manifest-device")

    def test_surface_applies_sync_manifest(self) -> None:
        target_root = self.repo_root / "surface-replica"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="copy base")
        sync_manifest = self.surface.sync_manifest_emit(
            target=target_root.as_uri(),
            transport="local_copy",
            device_id="surface-copy-device",
            snapshot_id=snapshot["snapshot_id"],
        )

        result = self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        self.assertTrue(Path(result["receipt_path"]).exists())
        self.assertTrue((target_root / "snapshots" / Path(snapshot["manifest_path"]).name).exists())
        self.assertEqual(result["receipt"]["status"], "copied")

    def test_surface_writes_verified_local_backup(self) -> None:
        with TemporaryDirectory() as target_tmpdir:
            target_root = Path(target_tmpdir) / "surface-local-backup"
            readme = self.repo_root / "README.md"
            readme.write_text("# CtxVault\n", encoding="utf-8")
            self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))

            result = self.surface.local_backup_write(
                target=target_root.as_uri(),
                scope_kind="project",
                scope_value="ctxvault",
                label="surface local backup",
                device_id="surface-local-backup-device",
            )

            self.assertEqual(result["receipt"]["schema_version"], "ctxvault.local-backup-write-receipt/v1")
            self.assertEqual(result["receipt"]["status"], "verified")
            self.assertEqual(result["verification"]["status"], "verified")
            self.assertTrue(Path(result["receipt_path"]).exists())
            self.assertTrue((target_root / "snapshots" / Path(result["snapshot"]["manifest_path"]).name).exists())
            self.assertTrue((target_root / "snapshot-bundles" / Path(result["snapshot"]["restore_bundle_path"]).name).exists())

    def test_surface_rejects_local_backup_target_inside_workspace(self) -> None:
        target_root = self.repo_root / "surface-local-backup"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))

        with self.assertRaises(ValueError):
            self.surface.local_backup_write(
                target=target_root.as_uri(),
                scope_kind="project",
                scope_value="ctxvault",
            )

    def test_surface_verifies_and_imports_replica(self) -> None:
        replica_root = self.repo_root / "surface-replica-verify"
        consumer_root = self.repo_root / "surface-consumer"
        consumer_surface = CtxVaultSurface(CtxVault(default_layout(consumer_root)))
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="replica source")
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        report = self.surface.replica_verify(replica_root=replica_root, snapshot_id=snapshot["snapshot_id"])
        imported = consumer_surface.replica_import(replica_root=replica_root, snapshot_id=snapshot["snapshot_id"])

        self.assertEqual(report["status"], "verified")
        self.assertEqual(imported["receipt"]["status"], "imported")
        self.assertTrue(Path(imported["receipt"]["imported_snapshot_manifest_path"]).exists())

    def test_surface_evaluates_replica_trust(self) -> None:
        replica_root = self.repo_root / "surface-replica-trust"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="trust source")
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="surface-untrusted-device",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        report = self.surface.replica_trust_evaluate(
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            trust_policy={
                "default_decision": "review",
                "require_sync_manifest": True,
                "trusted_device_ids": ["surface-trusted-device"],
                "allowed_transports": ["local_copy"],
            },
        )

        self.assertEqual(report["decision"], "review")
        self.assertTrue(report["requires_human_review"])

    def test_surface_lists_and_sets_replica_trust(self) -> None:
        result = self.surface.replica_trust_set(
            device_id="surface-device",
            trust_state="allow",
            label="Surface Device",
            notes="trusted by surface test",
            allowed_transports=["local_copy"],
        )
        listed = self.surface.replica_trust_list()

        self.assertTrue(Path(result["registry_path"]).exists())
        self.assertEqual(listed["device_count"], 1)
        self.assertEqual(listed["devices"][0]["device_id"], "surface-device")
        self.assertEqual(listed["devices"][0]["trust_state"], "allow")
        self.assertEqual(listed["devices"][0]["allowed_transports"], ["local_copy"])

    def test_surface_transport_dashboard_summarizes_trust_and_transport_state(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="dashboard source")
        self.surface.sync_receipt_emit(
            snapshot_id=snapshot["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="surface-dashboard-device",
        )
        self.surface.replica_trust_set(
            device_id="surface-dashboard-device",
            trust_state="allow",
            label="Surface Dashboard Device",
            allowed_transports=["local_copy"],
        )
        self.surface.replica_pairing_offer_emit(
            device_id="surface-dashboard-phone",
            label="Surface Dashboard Phone",
            allowed_transports=["local_copy"],
        )
        memory_candidate = self._core_fixture("memory-candidate.json")
        memory_candidate["id"] = "memc_surface_transport_dashboard_001"
        self.surface.vault.store_core_object("MemoryCandidate", memory_candidate)
        self.surface.companion_review_action(
            queue_kind="memory_candidate",
            object_id=memory_candidate["id"],
            decision="rejected",
            reviewer="surface_transport_test",
        )

        dashboard = self.surface.transport_dashboard(
            sync_limit=10,
            mutation_limit=10,
            pairing_limit=10,
            conflict_limit=10,
        )

        self.assertEqual(dashboard["summary"]["latest_local_snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(dashboard["summary"]["out_of_date_target_count"], 0)
        self.assertEqual(dashboard["summary"]["trusted_device_count"], 1)
        self.assertEqual(dashboard["summary"]["open_pairing_offer_count"], 1)
        self.assertEqual(dashboard["summary"]["open_sync_conflict_count"], 0)
        self.assertEqual(dashboard["summary"]["recent_mutation_count"], 1)
        self.assertGreaterEqual(dashboard["summary"]["recent_transport_event_count"], 3)
        self.assertEqual(dashboard["sync"]["targets"][0]["state"], "in_sync")
        self.assertEqual(dashboard["trust_devices"]["devices"][0]["device_id"], "surface-dashboard-device")
        self.assertEqual(dashboard["pairing_offers"]["offers"][0]["device_id"], "surface-dashboard-phone")
        self.assertEqual(dashboard["mutations"]["entries"][0]["mutation_kind"], "memory_candidate.review")
        self.assertTrue(dashboard["activity"]["events"])

    def test_surface_sync_conflict_review_updates_dashboard(self) -> None:
        replica_root = self.repo_root / "surface-conflict-replica"
        consumer_root = self.repo_root / "surface-conflict-consumer"
        consumer_surface = CtxVaultSurface(CtxVault(default_layout(consumer_root)))
        (self.repo_root / "README.md").write_text("# Source Snapshot\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        incoming_snapshot = self.surface.snapshot_create(
            scope_kind="project",
            scope_value="ctxvault",
            label="incoming conflict",
        )
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=incoming_snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        (consumer_root / "README.md").parent.mkdir(parents=True, exist_ok=True)
        (consumer_root / "README.md").write_text("# Local Snapshot\n", encoding="utf-8")
        consumer_surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        consumer_surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="local conflict")

        with self.assertRaises(ValueError):
            consumer_surface.replica_apply(
                replica_root=replica_root,
                snapshot_id=incoming_snapshot["snapshot_id"],
                trust_policy={
                    "default_decision": "allow",
                    "require_sync_manifest": True,
                    "trusted_device_ids": [],
                    "allowed_transports": ["local_copy"],
                },
            )

        conflicts = consumer_surface.sync_conflict_list(limit=10)
        reviewed = consumer_surface.sync_conflict_review(
            conflict_marker_path=Path(conflicts["conflicts"][0]["conflict_marker_path"]),
            reviewed_by="surface_conflict_test",
            resolution="kept_local",
            notes="Local state remains authoritative until manual merge.",
        )
        dashboard = consumer_surface.transport_dashboard()

        self.assertEqual(reviewed["conflict_marker"]["status"], "reviewed")
        self.assertEqual(reviewed["conflict_marker"]["resolution"], "kept_local")
        self.assertEqual(dashboard["summary"]["open_sync_conflict_count"], 0)
        self.assertEqual(dashboard["sync_conflicts"]["conflicts"][0]["status"], "reviewed")
        self.assertEqual(dashboard["activity"]["events"][0]["operation"], "sync.conflict-review")

    def test_surface_applies_replica(self) -> None:
        replica_root = self.repo_root / "surface-replica-apply"
        consumer_root = self.repo_root / "surface-consumer-apply"
        consumer_surface = CtxVaultSurface(CtxVault(default_layout(consumer_root)))
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="replica apply source")
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        (consumer_root / "README.md").parent.mkdir(parents=True, exist_ok=True)
        (consumer_root / "README.md").write_text("# Drifted\n", encoding="utf-8")
        consumer_surface.trace_record("KnowledgeArtifact", self._core_fixture("knowledge-artifact.json"))
        result = consumer_surface.replica_apply(
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            allow_deletes=True,
            reviewed_by="surface-reviewer",
            trust_policy={
                "default_decision": "allow",
                "require_sync_manifest": True,
                "trusted_device_ids": [],
                "allowed_transports": ["local_copy"],
            },
        )

        self.assertEqual(result["receipt"]["status"], "applied")
        self.assertEqual(result["receipt"]["trust_decision"], "allow")
        self.assertEqual((consumer_root / "README.md").read_text(encoding="utf-8"), "# CtxVault\n")
        self.assertEqual(result["restored"]["receipt"]["reviewed_by"], "surface-reviewer")

    def test_surface_reports_snapshot_lineage(self) -> None:
        replica_root = self.repo_root / "surface-lineage-replica"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="lineage source")
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="surface-lineage-device",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))
        self.surface.replica_import(
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            trust_policy={
                "default_decision": "allow",
                "require_sync_manifest": True,
                "trusted_device_ids": [],
                "allowed_transports": ["local_copy"],
            },
        )

        lineage = self.surface.snapshot_lineage(snapshot_id=snapshot["snapshot_id"], limit=10)

        self.assertEqual(lineage["summary"]["matched_event_count"], 4)
        self.assertEqual(
            [event["operation"] for event in lineage["events"]],
            ["snapshot.create", "snapshot.sync-manifest", "snapshot.sync-copy", "replica.import"],
        )

    def test_surface_reports_snapshot_provenance(self) -> None:
        replica_root = self.repo_root / "surface-provenance-replica"
        consumer_root = self.repo_root / "surface-provenance-consumer"
        consumer_surface = CtxVaultSurface(CtxVault(default_layout(consumer_root)))
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="provenance source")
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="surface-provenance-device",
            snapshot_id=snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))
        consumer_surface.replica_trust_set(
            device_id="surface-provenance-device",
            trust_state="allow",
            allowed_transports=["local_copy"],
        )
        consumer_surface.replica_import(
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
        )

        provenance = consumer_surface.snapshot_provenance(snapshot_id=snapshot["snapshot_id"], limit=10)

        self.assertTrue(provenance["is_imported_replica"])
        self.assertEqual(provenance["replica_source"]["device_id"], "surface-provenance-device")
        self.assertEqual(provenance["trust_registry_entry"]["trust_state"], "allow")

    def test_surface_lists_and_searches_sessions(self) -> None:
        self._import_session(
            session_id="sess_demo",
            title="Design Review",
            task_label="Review local app flow",
            turns=[
                {"id": "turn_demo_001", "role": "user", "content": "How should ctxvault ingest local knowledge?"},
                {"id": "turn_demo_002", "role": "assistant", "content": "Use deterministic typed imports first."},
            ],
        )

        listed = self.surface.session_list(scope_kind="project", scope_value="ctxvault", limit=10)
        searched = self.surface.session_search("design review", scope_kind="project", scope_value="ctxvault", limit=10)

        self.assertEqual(listed[0]["object_id"], "sess_demo")
        self.assertEqual(searched[0]["object_id"], "sess_demo")
        self.assertEqual(searched[0]["payload"]["turn_count"], 2)

    def test_surface_reports_related_sessions_and_aggregate_preview(self) -> None:
        self._import_session(
            session_id="sess_schema_design_001",
            title="Schema Design Review",
            task_label="Design vault schema",
            turns=[
                {"id": "turn_schema_001", "role": "user", "content": "Design the vault schema and review the object layout."},
                {"id": "turn_schema_002", "role": "assistant", "content": "Use file-backed objects and rebuildable indexes."},
            ],
        )
        self._import_session(
            session_id="sess_schema_design_002",
            title="Schema Migration Design",
            task_label="Design vault schema",
            turns=[
                {"id": "turn_schema_101", "role": "user", "content": "Plan the schema migration for the local vault."},
                {"id": "turn_schema_102", "role": "assistant", "content": "Keep the schema deterministic and versioned."},
            ],
        )
        self._import_session(
            session_id="sess_release_pkg_001",
            title="Packaging Release Artifact",
            task_label="Package native wrapper",
            turns=[
                {"id": "turn_pkg_001", "role": "user", "content": "Package the app bundle for release."},
                {"id": "turn_pkg_002", "role": "assistant", "content": "Build a macOS wrapper and sign it later."},
            ],
        )
        self.surface.episode_derive("sess_schema_design_001")
        self.surface.episode_derive("sess_schema_design_002")

        related = self.surface.session_related("sess_schema_design_001", limit=5)
        aggregate = self.surface.session_aggregate_preview("sess_schema_design_001", limit=5)

        self.assertEqual(related["anchor_session"]["id"], "sess_schema_design_001")
        self.assertEqual(related["summary"]["returned_count"], 1)
        self.assertEqual(related["related_sessions"][0]["session"]["id"], "sess_schema_design_002")
        self.assertTrue(related["related_sessions"][0]["shared_task_label"])
        self.assertIn("schema", related["related_sessions"][0]["shared_terms"])
        self.assertEqual(aggregate["aggregate"]["session_count"], 2)
        self.assertEqual(aggregate["aggregate"]["task_labels"], ["Design vault schema"])
        self.assertTrue(aggregate["aggregate"]["episode_kind_counts"])
        self.assertIn("schema", [item["term"] for item in aggregate["aggregate"]["recurring_terms"]])

    def test_surface_runs_workstream_preview_candidate_and_review_flow(self) -> None:
        self._import_session(
            session_id="sess_schema_design_001",
            title="Schema Design Review",
            task_label="Design vault schema",
            turns=[
                {"id": "turn_schema_001", "role": "user", "content": "Design the vault schema and review the object layout."},
                {"id": "turn_schema_002", "role": "assistant", "content": "Use file-backed objects and rebuildable indexes."},
            ],
        )
        self._import_session(
            session_id="sess_schema_design_002",
            title="Schema Migration Design",
            task_label="Design vault schema",
            turns=[
                {"id": "turn_schema_101", "role": "user", "content": "Plan the schema migration for the local vault."},
                {"id": "turn_schema_102", "role": "assistant", "content": "Keep the schema deterministic and versioned."},
            ],
        )
        self.surface.episode_derive("sess_schema_design_001")
        self.surface.episode_derive("sess_schema_design_002")

        preview = self.surface.workstream_preview("sess_schema_design_001", limit=5)
        self.assertEqual(preview["anchor_session"]["id"], "sess_schema_design_001")
        self.assertEqual(preview["suggested_workstream"]["task_labels"], ["Design vault schema"])
        self.assertEqual(len(preview["suggested_workstream"]["session_refs"]), 2)
        self.assertIn("promotion_profile", preview["suggested_workstream"])
        self.assertIn(
            preview["suggested_workstream"]["promotion_profile"]["readiness"],
            {"ready", "warning", "blocked"},
        )

        created = self.surface.workstream_candidate_create(
            "sess_schema_design_001",
            limit=5,
            candidate_id="wsc_surface_schema_flow",
        )
        self.assertEqual(created["candidate"]["proposal_state"], "proposed")

        listed_candidates = self.surface.workstream_candidate_list(
            scope_kind="project",
            scope_value="ctxvault",
            proposal_state="proposed",
            limit=10,
        )
        self.assertEqual([item["object_id"] for item in listed_candidates], ["wsc_surface_schema_flow"])

        policy = self._control_fixture("protection-policy.json")
        backup = CtxVaultPolicy.freshen_backup_receipt(self._control_fixture("backup-check-receipt.json"))
        reviewed = self.surface.workstream_candidate_review(
            "wsc_surface_schema_flow",
            decision="approved",
            reviewer="surface_test",
            notes="Promote this grouped schema work.",
            policy_payload=policy,
            backup_receipt=backup,
        )

        self.assertEqual(reviewed["candidate"]["proposal_state"], "merged")
        self.assertEqual(reviewed["workstream"]["approval_state"], "approved")
        self.assertTrue(reviewed["review_receipt"]["path"].endswith(".json"))

        listed_workstreams = self.surface.workstream_list(
            scope_kind="project",
            scope_value="ctxvault",
            status="active",
            limit=10,
        )
        self.assertEqual([item["object_id"] for item in listed_workstreams], ["ws_surface_schema_flow"])

    def test_surface_builds_workstream_intelligence_report(self) -> None:
        workstream = self._core_fixture("workstream.json")
        workstream["id"] = "ws_surface_intelligence"
        workstream["title"] = "CtxVault product intelligence"
        workstream["summary"] = (
            "CtxVault should keep a deterministic local substrate while treating Obsidian as an export bridge "
            "and preserving dense reusable workstream state."
        )
        workstream["knowledge_refs"] = [
            "knowledge://know_surface_policy_001",
            "knowledge://know_surface_policy_002",
        ]
        workstream["source_refs"] = [*workstream["source_refs"], *workstream["knowledge_refs"]]
        workstream["recurring_terms"] = ["ctxvault", "obsidian", "canonical", "substrate"]
        self.surface.vault.store_core_object("Workstream", workstream)

        knowledge_one = self._core_fixture("knowledge-artifact.json")
        knowledge_one["id"] = "know_surface_policy_001"
        knowledge_one["title"] = "Canonical Substrate Rule"
        knowledge_one["body"] = (
            "## Key Points\n"
            "- Do not use Obsidian as the canonical substrate.\n"
            "- Keep ctxvault as the deterministic substrate.\n\n"
            "## Open Questions\n"
            "- What note rotation rule should cap export growth?\n"
        )
        self.surface.vault.store_core_object("KnowledgeArtifact", knowledge_one)

        knowledge_two = self._core_fixture("knowledge-artifact.json")
        knowledge_two["id"] = "know_surface_policy_002"
        knowledge_two["title"] = "Cold Path Intelligence Rule"
        knowledge_two["body"] = (
            "## Key Points\n"
            "- Keep model-assisted intelligence on the cold path.\n"
            "- Promote reusable judgments instead of transcript-shaped notes.\n"
        )
        self.surface.vault.store_core_object("KnowledgeArtifact", knowledge_two)

        memory = self._core_fixture("memory.json")
        memory["id"] = "mem_surface_policy_001"
        memory["statement"] = "Use Obsidian as the canonical substrate for ctxvault context storage."
        memory["source_refs"] = ["knowledge://know_surface_policy_001"]
        self.surface.vault.store_core_object("Memory", memory)

        report = self.surface.workstream_intelligence("ws_surface_intelligence", limit=6)

        self.assertEqual(report["workstream_ref"], "workstream://ws_surface_intelligence")
        self.assertEqual(report["summary"]["knowledge_count"], 2)
        self.assertGreaterEqual(report["summary"]["memory_count"], 1)
        self.assertTrue(report["current_state"]["reusable_judgments"])
        self.assertTrue(report["current_state"]["open_questions"])
        self.assertTrue(report["contradictions"])
        self.assertTrue(report["next_questions"])

    def test_surface_builds_companion_dashboard(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "companion-demo.json"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_companion_demo",
                    "title": "Companion Demo",
                    "task_label": "Review mobile companion",
                    "source_app": "chatgpt",
                    "source_surface": "ios",
                    "source_format": "chatgpt_export",
                    "capture_method": "share_sheet",
                    "turns": [
                        {"id": "turn_companion_001", "role": "user", "content": "review the mobile companion contract"},
                        {"id": "turn_companion_002", "role": "assistant", "content": "keep it read-heavy and review-heavy"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        import_transcript_path(
            self.surface.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        workstream = self._core_fixture("workstream.json")
        workstream["id"] = "ws_companion_demo"
        workstream["title"] = "CtxVault mobile companion"
        workstream["summary"] = "CtxVault should keep the phone as a read-heavy companion surface over the deterministic local core."
        workstream["notes"] = (
            "## Open Questions\n"
            "- What review queue view should the mobile companion show first?\n"
        )
        workstream["task_labels"] = ["Review mobile companion"]
        workstream["recurring_terms"] = ["mobile", "companion", "review", "deterministic"]
        self.surface.vault.store_core_object("Workstream", workstream)

        memory_candidate = self._core_fixture("memory-candidate.json")
        memory_candidate["id"] = "memc_surface_companion_001"
        memory_candidate["statement"] = "Keep mobile capture read-heavy and candidate-first."
        self.surface.vault.store_core_object("MemoryCandidate", memory_candidate)

        prompt_patch = self._core_fixture("prompt-patch.json")
        prompt_patch["id"] = "ppatch_surface_companion_001"
        prompt_patch["prompt_asset_id"] = "prompt_mobile_companion_v1"
        prompt_patch["rationale"] = "The mobile companion prompt should privilege review queue visibility."
        self.surface.vault.store_core_object("PromptPatch", prompt_patch)

        workstream_candidate = self._core_fixture("workstream-candidate.json")
        workstream_candidate["id"] = "wsc_surface_companion_001"
        workstream_candidate["title"] = "CtxVault mobile companion candidate"
        workstream_candidate["summary"] = "Group mobile companion sessions and decisions into one governed candidate."
        self.surface.vault.store_core_object("WorkstreamCandidate", workstream_candidate)

        dashboard = self.surface.companion_dashboard(
            scope_kind="project",
            scope_value="ctxvault",
            session_limit=5,
            workstream_limit=5,
            review_limit=10,
        )

        self.assertEqual(dashboard["summary"]["active_workstream_count"], 1)
        self.assertEqual(dashboard["summary"]["recent_session_count"], 1)
        self.assertEqual(dashboard["summary"]["active_workstream_id"], "ws_companion_demo")
        self.assertEqual(dashboard["recent_sessions"][0]["source_app"], "chatgpt")
        self.assertEqual(dashboard["recent_sessions"][0]["source_surface"], "ios")
        self.assertEqual(dashboard["recent_sessions"][0]["source_format"], "chatgpt_export")
        self.assertEqual(dashboard["recent_sessions"][0]["capture_method"], "share_sheet")
        self.assertEqual(dashboard["active_workstreams"][0]["id"], "ws_companion_demo")
        self.assertTrue(dashboard["active_workstreams"][0]["open_questions"])
        self.assertTrue(dashboard["active_workstreams"][0]["reusable_judgments"])
        self.assertEqual(dashboard["review_queue"]["by_kind"]["memory_candidate"], 1)
        self.assertEqual(dashboard["review_queue"]["by_kind"]["workstream_candidate"], 1)
        self.assertEqual(dashboard["review_queue"]["by_kind"]["prompt_patch"], 1)
        self.assertEqual(
            {item["queue_kind"] for item in dashboard["review_queue"]["items"]},
            {"memory_candidate", "workstream_candidate", "prompt_patch"},
        )
        for item in dashboard["review_queue"]["items"]:
            self.assertIn("ranking_inputs", item)
            self.assertEqual(item["ranking_inputs"]["ranking_semantics"], "advisory_only_no_auto_promotion")
            self.assertIn(item["recommended_bucket"], {"review_first", "normal", "batch_candidate"})
            self.assertGreater(item["ranking_score"], 0.0)

    def test_surface_companion_sync_feed_and_pairing_accept(self) -> None:
        (self.repo_root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        snapshot = self.surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="companion sync feed")
        self.surface.sync_receipt_emit(
            snapshot_id=snapshot["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="surface-companion-device",
        )
        self.surface.companion_trust_device_set(
            device_id="surface-companion-review",
            trust_state="review",
            label="Surface Companion Review Device",
            allowed_transports=["local_copy"],
        )
        offered = self.surface.replica_pairing_offer_emit(
            device_id="surface-companion-phone",
            label="Surface Companion Phone",
            allowed_transports=["local_copy"],
        )

        feed = self.surface.companion_sync_feed()
        accepted = self.surface.companion_pairing_offer_accept(
            pairing_offer_path=Path(offered["pairing_offer_path"]),
            reviewed_by="surface_companion_sync_test",
            trust_state="allow",
        )
        refreshed = self.surface.companion_sync_feed()

        self.assertEqual(feed["summary"]["trusted_device_count"], 0)
        self.assertEqual(feed["summary"]["review_device_count"], 1)
        self.assertEqual(feed["summary"]["open_pairing_offer_count"], 1)
        self.assertEqual(feed["sync_targets"][0]["state"], "in_sync")
        self.assertEqual(feed["open_pairing_offers"][0]["actions"], ["accept_pairing"])
        self.assertEqual(accepted["pairing_offer"]["status"], "accepted")
        self.assertEqual(accepted["trust_entry"]["trust_state"], "allow")
        self.assertEqual(accepted["activity"]["operation"], "replica.pairing-accept")
        self.assertEqual(refreshed["summary"]["trusted_device_count"], 1)
        self.assertEqual(refreshed["summary"]["open_pairing_offer_count"], 0)

    def test_surface_companion_sync_conflict_review_shapes_mobile_result(self) -> None:
        replica_root = self.repo_root / "surface-companion-conflict-replica"
        consumer_root = self.repo_root / "surface-companion-conflict-consumer"
        consumer_surface = CtxVaultSurface(CtxVault(default_layout(consumer_root)))
        (self.repo_root / "README.md").write_text("# Source Snapshot\n", encoding="utf-8")
        self.surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        incoming_snapshot = self.surface.snapshot_create(
            scope_kind="project",
            scope_value="ctxvault",
            label="incoming companion conflict",
        )
        sync_manifest = self.surface.sync_manifest_emit(
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=incoming_snapshot["snapshot_id"],
        )
        self.surface.sync_manifest_apply(sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        (consumer_root / "README.md").parent.mkdir(parents=True, exist_ok=True)
        (consumer_root / "README.md").write_text("# Local Snapshot\n", encoding="utf-8")
        consumer_surface.trace_record("PromptAsset", self._core_fixture("prompt-asset.json"))
        consumer_surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="local companion conflict")

        with self.assertRaises(ValueError):
            consumer_surface.replica_apply(
                replica_root=replica_root,
                snapshot_id=incoming_snapshot["snapshot_id"],
                trust_policy={
                    "default_decision": "allow",
                    "require_sync_manifest": True,
                    "trusted_device_ids": [],
                    "allowed_transports": ["local_copy"],
                },
            )

        feed = consumer_surface.companion_sync_feed()
        reviewed = consumer_surface.companion_sync_conflict_review(
            conflict_marker_path=Path(feed["open_sync_conflicts"][0]["conflict_marker_path"]),
            reviewed_by="surface_companion_conflict_test",
            resolution="accepted_remote",
            notes="Companion flow marked the remote snapshot as the next merge baseline.",
        )
        refreshed = consumer_surface.companion_sync_feed()

        self.assertEqual(feed["summary"]["open_sync_conflict_count"], 1)
        self.assertEqual(feed["open_sync_conflicts"][0]["actions"], ["keep_local", "accept_remote", "needs_followup"])
        self.assertEqual(reviewed["conflict"]["resolution"], "accepted_remote")
        self.assertEqual(reviewed["activity"]["operation"], "sync.conflict-review")
        self.assertEqual(refreshed["summary"]["open_sync_conflict_count"], 0)

    def test_surface_companion_capture_creates_claim_backed_memory_candidate(self) -> None:
        capture = self.surface.companion_capture_candidate(
            statement="Keep mobile capture read-heavy and candidate-first.",
            why_it_matters="This preserves trust while still letting users capture reusable judgments away from the desk.",
            scope_kind="project",
            scope_value="ctxvault",
            source_refs=["https://example.com/mobile-companion"],
            notes="Captured from a share sheet flow.",
            source_app="chatgpt",
            source_surface="ios",
            source_format="share_sheet_text",
            capture_method="share_sheet",
        )

        self.assertTrue(capture["claim"]["id"].startswith("claim_"))
        self.assertTrue(capture["candidate"]["id"].startswith("memc_"))
        self.assertEqual(capture["claim"]["subject_ref"], f"memory-candidate://{capture['candidate']['id']}")
        self.assertIn(f"claim://{capture['claim']['id']}", capture["candidate"]["source_refs"])
        self.assertIn("https://example.com/mobile-companion", capture["candidate"]["source_refs"])
        self.assertIn("source_app=chatgpt", capture["claim"]["notes"])
        self.assertIn("capture_method=share_sheet", capture["claim"]["notes"])
        self.assertEqual(capture["capture_metadata"]["imported_via"], "ctxvault_companion")

        policy = self._control_fixture("protection-policy.json")
        backup = CtxVaultPolicy.freshen_backup_receipt(self._control_fixture("backup-check-receipt.json"))
        reviewed = self.surface.companion_review_action(
            queue_kind="memory_candidate",
            object_id=capture["candidate"]["id"],
            decision="approved",
            reviewer="surface_test",
            policy_payload=policy,
            backup_receipt=backup,
        )

        self.assertEqual(reviewed["queue_kind"], "memory_candidate")
        self.assertEqual(reviewed["decision"], "approved")
        self.assertEqual(reviewed["result"]["candidate"]["proposal_state"], "merged")
        self.assertIsNotNone(reviewed["result"]["memory"])

    def test_surface_companion_review_action_dispatches_each_queue_kind(self) -> None:
        memory_candidate = self._core_fixture("memory-candidate.json")
        memory_candidate["id"] = "memc_surface_review_dispatch_001"
        self.surface.vault.store_core_object("MemoryCandidate", memory_candidate)

        workstream_candidate = self._core_fixture("workstream-candidate.json")
        workstream_candidate["id"] = "wsc_surface_review_dispatch_001"
        self.surface.vault.store_core_object("WorkstreamCandidate", workstream_candidate)

        prompt_asset = self._core_fixture("prompt-asset.json")
        prompt_asset["id"] = "prompt_surface_review_dispatch_v1"
        self.surface.vault.store_core_object("PromptAsset", prompt_asset)
        prompt_patch = self._core_fixture("prompt-patch.json")
        prompt_patch["id"] = "ppatch_surface_review_dispatch_001"
        prompt_patch["prompt_asset_id"] = prompt_asset["id"]
        self.surface.vault.store_core_object("PromptPatch", prompt_patch)

        memory_result = self.surface.companion_review_action(
            queue_kind="memory_candidate",
            object_id=memory_candidate["id"],
            decision="rejected",
            reviewer="surface_test",
        )
        workstream_result = self.surface.companion_review_action(
            queue_kind="workstream_candidate",
            object_id=workstream_candidate["id"],
            decision="rejected",
            reviewer="surface_test",
        )
        prompt_result = self.surface.companion_review_action(
            queue_kind="prompt_patch",
            object_id=prompt_patch["id"],
            decision="rejected",
            reviewer="surface_test",
        )

        self.assertEqual(memory_result["result"]["candidate"]["proposal_state"], "rejected")
        self.assertEqual(workstream_result["result"]["candidate"]["proposal_state"], "rejected")
        self.assertEqual(prompt_result["result"]["patch"]["proposal_state"], "rejected")

    def test_surface_companion_review_batch_updates_mutation_ledger(self) -> None:
        memory_candidate = self._core_fixture("memory-candidate.json")
        memory_candidate["id"] = "memc_surface_review_batch_001"
        self.surface.vault.store_core_object("MemoryCandidate", memory_candidate)

        workstream_candidate = self._core_fixture("workstream-candidate.json")
        workstream_candidate["id"] = "wsc_surface_review_batch_001"
        self.surface.vault.store_core_object("WorkstreamCandidate", workstream_candidate)

        policy = self._control_fixture("protection-policy.json")
        backup = CtxVaultPolicy.freshen_backup_receipt(self._control_fixture("backup-check-receipt.json"))
        result = self.surface.companion_review_batch(
            items=[
                {"queue_kind": "memory_candidate", "object_id": memory_candidate["id"]},
                {"queue_kind": "workstream_candidate", "object_id": workstream_candidate["id"]},
            ],
            decision="approved",
            reviewer="surface_batch_test",
            policy_payload=policy,
            backup_receipt=backup,
        )
        mutations = self.surface.mutation_list(limit=10)

        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["counts_by_queue"]["memory_candidate"], 1)
        self.assertEqual(result["counts_by_queue"]["workstream_candidate"], 1)
        self.assertEqual(result["results"][0]["decision"], "approved")
        self.assertEqual(mutations["summary"]["entry_count"], 2)
        self.assertEqual(
            {entry["mutation_kind"] for entry in mutations["entries"]},
            {"memory_candidate.review", "workstream_candidate.review"},
        )

    def test_surface_companion_ask_from_active_workstream_builds_bound_bundle(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "companion-ask.json"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_companion_ask",
                    "title": "Companion Ask",
                    "task_label": "Review mobile companion",
                    "turns": [
                        {
                            "id": "turn_companion_ask_001",
                            "role": "user",
                            "content": "how should the mobile companion route review queue actions?",
                            "created_at": "2026-04-23T08:00:00+00:00",
                        },
                        {
                            "id": "turn_companion_ask_002",
                            "role": "assistant",
                            "content": "bind review actions to governed candidate APIs rather than a mobile-only queue model.",
                            "created_at": "2026-04-23T08:00:10+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        import_transcript_path(
            self.surface.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        workstream = self._core_fixture("workstream.json")
        workstream["id"] = "ws_companion_ask"
        workstream["title"] = "CtxVault mobile companion"
        workstream["summary"] = "CtxVault should keep the phone as a read-heavy companion surface over the deterministic local core."
        workstream["session_refs"] = ["session://sess_companion_ask"]
        workstream["source_refs"] = ["session://sess_companion_ask", "workstream-candidate://wsc_20260421_ctxvault_schema"]
        workstream["notes"] = (
            "## Open Questions\n"
            "- What review queue view should the mobile companion show first?\n"
        )
        workstream["task_labels"] = ["Review mobile companion"]
        workstream["recurring_terms"] = ["mobile", "companion", "review", "deterministic"]
        self.surface.vault.store_core_object("Workstream", workstream)

        ask = self.surface.companion_ask_from_workstream(
            workstream_id="ws_companion_ask",
            question="How should the mobile companion present review queue actions?",
            max_recent_turns=4,
        )

        self.assertEqual(ask["workstream"]["id"], "ws_companion_ask")
        self.assertEqual(ask["anchor_session"]["id"], "sess_companion_ask")
        self.assertEqual(ask["bundle"]["task_label"], "How should the mobile companion present review queue actions?")
        self.assertEqual(ask["bundle"]["assembly_policy"]["session_id"], "sess_companion_ask")
        self.assertTrue(ask["bundle"]["sections"]["active_task_state"])
        self.assertTrue(
            any("reusable judgments" in item["content"] for item in ask["bundle"]["sections"]["active_task_state"])
        )
        self.assertIn("Mode: ask-from-active-workstream", ask["ask_packet"]["handoff_text"])
        self.assertIn("Bundle ref: bundle://", ask["ask_packet"]["handoff_text"])

    def test_surface_companion_workstream_sessions_returns_recent_first_picker(self) -> None:
        self._import_session(
            session_id="sess_companion_picker_alpha",
            title="Companion Picker Alpha",
            task_label="Review mobile companion alpha",
            turns=[
                {
                    "id": "turn_picker_alpha_001",
                    "role": "user",
                    "content": "how should session selection work on mobile?",
                    "created_at": "2026-04-23T08:00:00+00:00",
                },
                {
                    "id": "turn_picker_alpha_002",
                    "role": "assistant",
                    "content": "default to the latest session in the active workstream.",
                    "created_at": "2026-04-23T08:00:10+00:00",
                },
            ],
        )
        self._import_session(
            session_id="sess_companion_picker_beta",
            title="Companion Picker Beta",
            task_label="Review mobile companion beta",
            turns=[
                {
                    "id": "turn_picker_beta_001",
                    "role": "user",
                    "content": "how should follow-up anchors work?",
                    "created_at": "2026-04-23T09:00:00+00:00",
                },
                {
                    "id": "turn_picker_beta_002",
                    "role": "assistant",
                    "content": "offer recent turns from the selected session rather than a global transcript list.",
                    "created_at": "2026-04-23T09:00:10+00:00",
                },
            ],
        )

        workstream = self._core_fixture("workstream.json")
        workstream["id"] = "ws_companion_picker"
        workstream["title"] = "CtxVault mobile session picker"
        workstream["summary"] = "Companion should keep session selection bound to the active workstream."
        workstream["session_refs"] = ["session://sess_companion_picker_alpha", "session://sess_companion_picker_beta"]
        workstream["source_refs"] = ["session://sess_companion_picker_alpha", "session://sess_companion_picker_beta"]
        workstream["task_labels"] = ["Review mobile companion"]
        workstream["recurring_terms"] = ["mobile", "companion", "session", "followup"]
        self.surface.vault.store_core_object("Workstream", workstream)

        picker = self.surface.companion_workstream_sessions(
            workstream_id="ws_companion_picker",
            session_limit=5,
            recent_turn_limit=3,
        )

        self.assertEqual(picker["workstream"]["id"], "ws_companion_picker")
        self.assertEqual(picker["selected_session_id"], "sess_companion_picker_beta")
        self.assertEqual([item["id"] for item in picker["sessions"]], ["sess_companion_picker_beta", "sess_companion_picker_alpha"])
        self.assertTrue(picker["sessions"][0]["is_selected"])
        self.assertEqual(picker["sessions"][0]["latest_assistant_turn_ref"], "turn://turn_picker_beta_002")
        self.assertEqual(len(picker["sessions"][0]["recent_turns"]), 2)

    def test_surface_companion_followup_ask_binds_selected_session_and_turn(self) -> None:
        self._import_session(
            session_id="sess_companion_followup",
            title="Companion Follow-Up",
            task_label="Refine follow-up ask contract",
            turns=[
                {
                    "id": "turn_followup_001",
                    "role": "user",
                    "content": "how should the phone resume a thread?",
                    "created_at": "2026-04-23T08:00:00+00:00",
                },
                {
                    "id": "turn_followup_002",
                    "role": "assistant",
                    "content": "bind the phone to an explicit workstream session rather than a floating inbox thread.",
                    "created_at": "2026-04-23T08:00:10+00:00",
                },
                {
                    "id": "turn_followup_003",
                    "role": "user",
                    "content": "what should the follow-up anchor be?",
                    "created_at": "2026-04-23T08:01:00+00:00",
                },
                {
                    "id": "turn_followup_004",
                    "role": "assistant",
                    "content": "use the selected turn plus active workstream state to frame the next ask.",
                    "created_at": "2026-04-23T08:01:10+00:00",
                },
            ],
        )

        workstream = self._core_fixture("workstream.json")
        workstream["id"] = "ws_companion_followup"
        workstream["title"] = "CtxVault mobile follow-up"
        workstream["summary"] = "Companion follow-up asks should stay bound to the chosen workstream session."
        workstream["session_refs"] = ["session://sess_companion_followup"]
        workstream["source_refs"] = ["session://sess_companion_followup"]
        workstream["task_labels"] = ["Refine follow-up ask contract"]
        workstream["recurring_terms"] = ["mobile", "companion", "followup", "session"]
        self.surface.vault.store_core_object("Workstream", workstream)

        ask = self.surface.companion_followup_ask(
            workstream_id="ws_companion_followup",
            session_id="sess_companion_followup",
            turn_ref="turn://turn_followup_002",
            question="How should the phone continue the selected thread without losing workstream state?",
            max_recent_turns=3,
        )

        self.assertEqual(ask["selected_session"]["id"], "sess_companion_followup")
        self.assertEqual(ask["followup_turn"]["id"], "turn_followup_002")
        self.assertEqual(ask["ask_packet"]["mode"], "workstream_followup")
        self.assertEqual(ask["ask_packet"]["followup_turn_ref"], "turn://turn_followup_002")
        self.assertEqual(ask["bundle"]["assembly_policy"]["session_id"], "sess_companion_followup")
        self.assertTrue(
            any("follow-up anchor in" in item["content"] for item in ask["bundle"]["sections"]["active_task_state"])
        )
        self.assertTrue(ask["bundle"]["sections"]["recent_conversation"])
        self.assertIn("Mode: follow-up-from-workstream", ask["ask_packet"]["handoff_text"])

    def test_surface_derives_episodes_synthesizes_and_exports_note(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "episode-demo.json"
        transcript_path.parent.mkdir(parents=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_episode_demo",
                    "title": "Episode Demo",
                    "task_label": "Segment and synthesize context",
                    "turns": [
                        {
                            "id": "turn_ep_001",
                            "role": "user",
                            "content": "Plan the local-first context architecture and break it into phases.",
                            "created_at": "2026-04-21T09:00:00+00:00",
                        },
                        {
                            "id": "turn_ep_002",
                            "role": "assistant",
                            "content": "Use a deterministic substrate first, then add privacy and synthesis layers.",
                            "created_at": "2026-04-21T09:00:10+00:00",
                        },
                        {
                            "id": "turn_ep_003",
                            "role": "user",
                            "content": "Now implement episode derivation and wire the CLI.",
                            "created_at": "2026-04-21T09:01:00+00:00",
                        },
                        {
                            "id": "turn_ep_004",
                            "role": "assistant",
                            "content": "I will add episode objects, synthesis artifacts, and a wiki export flow.",
                            "created_at": "2026-04-21T09:01:12+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        import_transcript_path(
            self.surface.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        derived = self.surface.episode_derive("sess_episode_demo")
        self.assertFalse(derived["reused_existing"])
        self.assertEqual([episode["kind"] for episode in derived["episodes"]], ["plan", "execute"])

        listed = self.surface.episode_list(session_id="sess_episode_demo", limit=10)
        self.assertEqual(len(listed), 2)
        self.assertEqual(listed[0]["payload"]["goal"], "Plan the local-first context architecture and break it into phases.")

        synthesized = self.surface.episode_synthesize(derived["episodes"][0]["id"])
        artifact = synthesized["knowledge_artifact"]
        self.assertEqual(artifact["kind"], "synthesis")
        self.assertIn("## Evidence", artifact["body"])
        self.assertIn("episode://", json.dumps(artifact["source_refs"]))

        note = self.surface.knowledge_export_note(
            artifact["id"],
            output_path=self.repo_root / "exports" / "manual" / "episode-demo.md",
            canonical_target="project:ctxvault",
        )
        note_path = Path(note["output_path"])
        self.assertTrue(note_path.exists())
        note_text = note_path.read_text(encoding="utf-8")
        self.assertIn('canonical_target: "project:ctxvault"', note_text)
        self.assertIn("## Evidence", note_text)
        self.assertIn(f"knowledge://{artifact['id']}", note_text)


if __name__ == "__main__":
    unittest.main()
