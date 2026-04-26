from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.versioning import accept_pairing_offer, apply_replica, apply_restore, apply_sync_manifest, create_snapshot, diff_snapshots, emit_pairing_offer, emit_sync_manifest, emit_sync_receipt, evaluate_replica_trust, import_replica, list_mutations, list_pairing_offers, list_replica_trust_devices, list_snapshots, list_sync_conflicts, list_transport_events, load_replica_trust_registry, plan_restore, record_mutation, review_sync_conflict, set_replica_device_trust, snapshot_lineage, snapshot_provenance, sync_status, verify_replica


class VersioningTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.layout = default_layout(self.repo_root)
        self.vault = CtxVault(self.layout)
        self.fixture_root = ROOT / "fixtures" / "core"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _fixture(self, name: str) -> dict:
        return json.loads((self.fixture_root / name).read_text(encoding="utf-8"))

    def test_create_snapshot_writes_manifest_and_operation_log(self) -> None:
        (self.repo_root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
        (self.repo_root / "src").mkdir()
        (self.repo_root / "src" / "app.py").write_text("print('ctxvault')\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        result = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="initial local snapshot",
        )

        manifest_path = Path(result["manifest_path"])
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "ctxvault.snapshot-manifest/v1")
        self.assertEqual(manifest["label"], "initial local snapshot")
        self.assertGreater(manifest["summary"]["workspace"]["file_count"], 0)
        self.assertGreater(manifest["summary"]["vault"]["object_file_count"], 0)
        self.assertTrue(Path(result["restore_bundle_path"]).exists())
        self.assertEqual(manifest["restore_bundle"]["sha256"], result["restore_bundle_sha256"])

        operation_log_path = Path(result["operation_log_path"])
        self.assertTrue(operation_log_path.exists())
        operations = [json.loads(line) for line in operation_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0]["operation"], "snapshot.create")
        self.assertEqual(operations[0]["snapshot_id"], result["snapshot_id"])

    def test_record_and_list_mutations_roundtrip(self) -> None:
        result = record_mutation(
            layout=self.layout,
            mutation_kind="memory_candidate.review",
            object_ref="memory-candidate://memc_demo",
            actor="unit_test",
            decision="approved",
            scope={"kind": "project", "value": "ctxvault"},
            related_refs=["memory://mem_demo"],
            notes="promoted durable rule",
            details={"proposal_state": "merged"},
        )

        self.assertTrue(Path(result["mutation_ledger_path"]).exists())
        listed = list_mutations(layout=self.layout, limit=10)
        self.assertEqual(listed["summary"]["entry_count"], 1)
        self.assertEqual(listed["entries"][0]["mutation_kind"], "memory_candidate.review")
        self.assertEqual(listed["entries"][0]["decision"], "approved")
        self.assertEqual(listed["entries"][0]["related_refs"], ["memory://mem_demo"])

    def test_pairing_offer_emit_list_and_accept_updates_trust_registry(self) -> None:
        offer = emit_pairing_offer(
            layout=self.layout,
            device_id="iphone-primary",
            label="Chris iPhone",
            notes="mobile companion pair",
            allowed_transports=["local_copy"],
            expires_in_hours=24,
        )

        listed = list_pairing_offers(layout=self.layout, limit=10)
        accepted = accept_pairing_offer(
            layout=self.layout,
            pairing_offer_path=Path(offer["pairing_offer_path"]),
            trust_state="allow",
            reviewed_by="unit_test",
        )
        listed_after_accept = list_pairing_offers(layout=self.layout, limit=10)
        registry = load_replica_trust_registry(layout=self.layout)

        self.assertEqual(listed["summary"]["offer_count"], 1)
        self.assertEqual(listed["offers"][0]["device_id"], "iphone-primary")
        self.assertEqual(accepted["trust_result"]["entry"]["device_id"], "iphone-primary")
        self.assertEqual(accepted["pairing_offer"]["status"], "accepted")
        self.assertEqual(listed_after_accept["offers"][0]["status"], "accepted")
        self.assertEqual(listed_after_accept["offers"][0]["accepted_by"], "unit_test")
        self.assertEqual(registry["devices"]["iphone-primary"]["trust_state"], "allow")

    def test_list_snapshots_returns_latest_first(self) -> None:
        (self.repo_root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        first = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="first",
        )
        second = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="second",
        )

        listed = list_snapshots(layout=self.layout, limit=10)
        self.assertEqual([item["snapshot_id"] for item in listed], [second["snapshot_id"], first["snapshot_id"]])
        self.assertEqual(listed[0]["label"], "second")

    def test_diff_snapshots_reports_workspace_and_vault_changes(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        first = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="before changes",
        )

        readme.write_text("# CtxVault\n\nlocal snapshot diff\n", encoding="utf-8")
        self.vault.store_core_object("KnowledgeArtifact", self._fixture("knowledge-artifact.json"))
        second = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="after changes",
        )

        diff = diff_snapshots(
            layout=self.layout,
            base_snapshot_id=first["snapshot_id"],
            head_snapshot_id=second["snapshot_id"],
        )

        self.assertEqual(diff["summary"]["workspace"]["modified"], 1)
        self.assertEqual(diff["summary"]["vault"]["added"], 1)
        self.assertEqual(diff["changes"]["workspace"]["modified"][0]["path"], "README.md")
        self.assertEqual(
            diff["changes"]["vault_objects"]["added"][0]["path"],
            ".ctxvault/objects/knowledge_artifact/know_proj_ctxvault_profile_v1.json",
        )

    def test_emit_sync_receipt_writes_receipt_and_operation(self) -> None:
        (self.repo_root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="sync source",
        )
        result = emit_sync_receipt(
            layout=self.layout,
            snapshot_id=snapshot["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="macbook-local-backup",
            notes="copied to removable backup",
        )

        receipt_path = Path(result["receipt_path"])
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["schema_version"], "ctxvault.sync-receipt/v1")
        self.assertEqual(receipt["snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(receipt["target"], "file:///Volumes/local-backup/ctxvault")

        operations = [json.loads(line) for line in Path(result["operation_log_path"]).read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(operations[-1]["operation"], "snapshot.sync")
        self.assertEqual(operations[-1]["snapshot_id"], snapshot["snapshot_id"])

    def test_plan_restore_reports_workspace_writes_and_vault_deletes(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="restore base",
        )

        readme.write_text("# CtxVault\n\nrestore me\n", encoding="utf-8")
        self.vault.store_core_object("KnowledgeArtifact", self._fixture("knowledge-artifact.json"))

        plan = plan_restore(
            root=self.repo_root,
            layout=self.layout,
            snapshot_id=snapshot["snapshot_id"],
        )

        self.assertEqual(plan["summary"]["workspace"]["write"], 1)
        self.assertEqual(plan["summary"]["vault"]["delete"], 1)
        self.assertEqual(plan["actions"]["workspace"]["write"][0]["path"], "README.md")
        self.assertEqual(
            plan["actions"]["vault_objects"]["delete"][0]["path"],
            ".ctxvault/objects/knowledge_artifact/know_proj_ctxvault_profile_v1.json",
        )
        self.assertTrue(plan["requires_review"])
        self.assertEqual(len(plan["rebuildable_indexes"]), 1)
        self.assertEqual(
            plan["warnings"],
            ["SQLite and other rebuildable indexes should be refreshed after applying this restore plan."],
        )

    def test_sync_status_reports_targets_that_are_behind(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        base = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="sync base",
        )
        emit_sync_receipt(
            layout=self.layout,
            snapshot_id=base["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="macbook-backup",
        )

        readme.write_text("# CtxVault\n\nnew snapshot\n", encoding="utf-8")
        head = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="sync head",
        )

        status = sync_status(layout=self.layout, limit=10)

        self.assertEqual(status["latest_local_snapshot"]["snapshot_id"], head["snapshot_id"])
        self.assertEqual(status["summary"]["target_count"], 1)
        self.assertEqual(status["summary"]["out_of_date_target_count"], 1)
        self.assertEqual(status["targets"][0]["endpoint_key"], "macbook-backup")
        self.assertEqual(status["targets"][0]["state"], "behind")
        self.assertEqual(status["targets"][0]["snapshot_lag"], 1)
        self.assertEqual(status["targets"][0]["pending_snapshot_ids"], [head["snapshot_id"]])

    def test_apply_restore_replays_bundle_and_rebuilds_indexes(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))

        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="apply base",
        )

        readme.write_text("# CtxVault\n\nmutated\n", encoding="utf-8")
        self.vault.store_core_object("KnowledgeArtifact", self._fixture("knowledge-artifact.json"))

        result = apply_restore(
            root=self.repo_root,
            layout=self.layout,
            snapshot_id=snapshot["snapshot_id"],
            allow_deletes=True,
            reviewed_by="unit_test",
        )

        self.assertEqual(readme.read_text(encoding="utf-8"), "# CtxVault\n")
        self.assertFalse(
            (self.layout.objects_dir / "knowledge_artifact" / "know_proj_ctxvault_profile_v1.json").exists()
        )
        self.assertTrue(Path(result["receipt_path"]).exists())
        self.assertEqual(result["receipt"]["schema_version"], "ctxvault.restore-receipt/v1")
        self.assertEqual(result["receipt"]["reviewed_by"], "unit_test")
        self.assertEqual(result["receipt"]["summary"]["combined"]["delete"], 1)
        self.assertEqual(result["index_refresh"]["indexed_object_count"], 1)

        with sqlite3.connect(self.layout.sqlite_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM object_index WHERE object_kind = 'knowledge_artifact'"
            ).fetchone()
        self.assertEqual(int(row[0]), 0)

        emit_sync_receipt(
            layout=self.layout,
            snapshot_id=snapshot["snapshot_id"],
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="restore-device",
        )
        status = sync_status(layout=self.layout, limit=10)
        self.assertEqual(status["current_local_snapshot"]["snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(status["targets"][0]["state"], "in_sync")

    def test_emit_sync_manifest_uses_current_effective_snapshot(self) -> None:
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        base = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="base",
        )

        readme.write_text("# CtxVault\n\nhead\n", encoding="utf-8")
        head = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="head",
        )
        apply_restore(
            root=self.repo_root,
            layout=self.layout,
            snapshot_id=base["snapshot_id"],
            allow_deletes=False,
        )

        result = emit_sync_manifest(
            layout=self.layout,
            target="file:///Volumes/local-backup/ctxvault",
            transport="local_copy",
            device_id="manifest-device",
        )

        self.assertTrue(Path(result["sync_manifest_path"]).exists())
        self.assertEqual(result["sync_manifest"]["schema_version"], "ctxvault.sync-manifest/v1")
        self.assertEqual(result["sync_manifest"]["snapshot_id"], base["snapshot_id"])
        self.assertEqual(result["sync_manifest"]["summary"]["artifact_count"], 2)
        self.assertEqual(result["sync_manifest"]["device_id"], "manifest-device")
        self.assertIn(
            str(Path(base["manifest_path"]).resolve()),
            result["sync_manifest"]["artifact_paths"] or [],
        )

    def test_apply_sync_manifest_copies_snapshot_artifacts_to_local_target(self) -> None:
        target_root = self.repo_root / "replica-target"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="copy source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=target_root.as_uri(),
            transport="local_copy",
            device_id="copy-device",
            snapshot_id=snapshot["snapshot_id"],
        )

        result = apply_sync_manifest(
            layout=self.layout,
            sync_manifest_path=Path(sync_manifest["sync_manifest_path"]),
        )

        self.assertTrue(Path(result["receipt_path"]).exists())
        self.assertEqual(result["receipt"]["schema_version"], "ctxvault.sync-copy-receipt/v1")
        self.assertEqual(result["receipt"]["status"], "copied")
        self.assertTrue((target_root / "snapshots" / Path(snapshot["manifest_path"]).name).exists())
        self.assertTrue((target_root / "snapshot-bundles" / Path(snapshot["restore_bundle_path"]).name).exists())
        self.assertTrue((target_root / "sync-manifests" / Path(sync_manifest["sync_manifest_path"]).name).exists())

    def test_verify_replica_reports_complete_local_copy(self) -> None:
        replica_root = self.repo_root / "replica-verify-target"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="verify source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        report = verify_replica(replica_root=replica_root, snapshot_id=snapshot["snapshot_id"])

        self.assertEqual(report["schema_version"], "ctxvault.replica-verify/v1")
        self.assertEqual(report["status"], "verified")
        self.assertTrue(report["checks"]["restore_bundle_sha256_matches"])
        self.assertTrue(report["checks"]["snapshot_manifest_exists"])
        self.assertEqual(report["snapshot_id"], snapshot["snapshot_id"])

    def test_evaluate_replica_trust_blocks_untrusted_device(self) -> None:
        replica_root = self.repo_root / "replica-trust-target"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="trust source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="unknown-device",
            snapshot_id=snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        report = evaluate_replica_trust(
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            trust_policy={
                "default_decision": "block",
                "require_sync_manifest": True,
                "trusted_device_ids": ["trusted-device"],
                "allowed_transports": ["local_copy"],
            },
        )

        self.assertEqual(report["schema_version"], "ctxvault.replica-trust-eval/v1")
        self.assertEqual(report["decision"], "block")
        self.assertIn("device is not in trusted_device_ids", report["reasons"])

    def test_replica_trust_registry_roundtrip_and_evaluation(self) -> None:
        replica_root = self.repo_root / "replica-trust-registry-target"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="trust registry source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="trusted-registry-device",
            snapshot_id=snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        set_result = set_replica_device_trust(
            layout=self.layout,
            device_id="trusted-registry-device",
            trust_state="allow",
            label="Primary laptop",
            notes="trusted local receiver",
            allowed_transports=["local_copy"],
        )
        listed = list_replica_trust_devices(layout=self.layout)
        loaded_registry = load_replica_trust_registry(layout=self.layout)
        report = evaluate_replica_trust(
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            trust_policy={
                "default_decision": "review",
                "require_sync_manifest": True,
                "trusted_device_ids": [],
                "allowed_transports": ["local_copy"],
            },
            trust_registry=loaded_registry,
        )

        self.assertTrue(Path(set_result["registry_path"]).exists())
        self.assertEqual(listed["device_count"], 1)
        self.assertEqual(listed["devices"][0]["device_id"], "trusted-registry-device")
        self.assertEqual(loaded_registry["devices"]["trusted-registry-device"]["trust_state"], "allow")
        self.assertEqual(report["decision"], "allow")
        self.assertEqual(report["matched_registry_entry"]["device_id"], "trusted-registry-device")
        self.assertIn("trusted by local trust registry", " ".join(report["reasons"]))

    def test_import_replica_makes_snapshot_restorable_in_fresh_workspace(self) -> None:
        replica_root = self.repo_root / "replica-import-target"
        consumer_root = self.repo_root / "consumer"
        consumer_layout = default_layout(consumer_root)
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="import source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        imported = import_replica(
            layout=consumer_layout,
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            trust_policy={
                "default_decision": "allow",
                "require_sync_manifest": True,
                "trusted_device_ids": [],
                "allowed_transports": ["local_copy"],
            },
        )

        self.assertEqual(imported["receipt"]["schema_version"], "ctxvault.replica-import-receipt/v1")
        self.assertTrue(Path(imported["receipt"]["imported_snapshot_manifest_path"]).exists())
        self.assertTrue(Path(imported["receipt"]["imported_restore_bundle_path"]).exists())

        restored = apply_restore(
            root=consumer_root,
            layout=consumer_layout,
            snapshot_id=snapshot["snapshot_id"],
        )
        self.assertEqual((consumer_root / "README.md").read_text(encoding="utf-8"), "# CtxVault\n")
        self.assertEqual(restored["receipt"]["status"], "applied")

    def test_apply_replica_imports_and_restores_with_delete_gate(self) -> None:
        replica_root = self.repo_root / "replica-apply-target"
        consumer_root = self.repo_root / "consumer-apply"
        consumer_layout = default_layout(consumer_root)
        consumer_vault = CtxVault(consumer_layout)
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="replica apply source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        (consumer_root / "README.md").parent.mkdir(parents=True, exist_ok=True)
        (consumer_root / "README.md").write_text("# Drifted\n", encoding="utf-8")
        consumer_vault.store_core_object("KnowledgeArtifact", self._fixture("knowledge-artifact.json"))

        result = apply_replica(
            root=consumer_root,
            layout=consumer_layout,
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            allow_deletes=True,
            reviewed_by="unit_test",
            trust_policy={
                "default_decision": "allow",
                "require_sync_manifest": True,
                "trusted_device_ids": [],
                "allowed_transports": ["local_copy"],
            },
        )

        self.assertEqual(result["receipt"]["schema_version"], "ctxvault.replica-apply-receipt/v1")
        self.assertEqual(result["receipt"]["status"], "applied")
        self.assertEqual(result["receipt"]["trust_decision"], "allow")
        self.assertEqual((consumer_root / "README.md").read_text(encoding="utf-8"), "# CtxVault\n")
        self.assertFalse(
            (consumer_layout.objects_dir / "knowledge_artifact" / "know_proj_ctxvault_profile_v1.json").exists()
        )
        self.assertEqual(result["restored"]["receipt"]["reviewed_by"], "unit_test")

    def test_apply_replica_writes_conflict_marker_and_requires_review_for_different_local_snapshot(self) -> None:
        replica_root = self.repo_root / "replica-conflict-target"
        consumer_root = self.repo_root / "consumer-conflict"
        consumer_layout = default_layout(consumer_root)
        consumer_vault = CtxVault(consumer_layout)

        source_readme = self.repo_root / "README.md"
        source_readme.write_text("# Source Snapshot\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        incoming_snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="incoming",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=incoming_snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        local_readme = consumer_root / "README.md"
        local_readme.parent.mkdir(parents=True, exist_ok=True)
        local_readme.write_text("# Local Snapshot\n", encoding="utf-8")
        consumer_vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        local_snapshot = create_snapshot(
            root=consumer_root,
            layout=consumer_layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="local",
        )

        with self.assertRaises(ValueError):
            apply_replica(
                root=consumer_root,
                layout=consumer_layout,
                replica_root=replica_root,
                snapshot_id=incoming_snapshot["snapshot_id"],
                trust_policy={
                    "default_decision": "allow",
                    "require_sync_manifest": True,
                    "trusted_device_ids": [],
                    "allowed_transports": ["local_copy"],
                },
            )

        conflicts = list_sync_conflicts(layout=consumer_layout, limit=10)
        self.assertEqual(conflicts["summary"]["conflict_count"], 1)
        self.assertEqual(conflicts["conflicts"][0]["local_snapshot_id"], local_snapshot["snapshot_id"])
        self.assertEqual(conflicts["conflicts"][0]["incoming_snapshot_id"], incoming_snapshot["snapshot_id"])
        self.assertEqual(conflicts["conflicts"][0]["status"], "open")

    def test_review_sync_conflict_marks_resolution_and_activity_feed(self) -> None:
        replica_root = self.repo_root / "replica-review-target"
        consumer_root = self.repo_root / "consumer-review"
        consumer_layout = default_layout(consumer_root)
        consumer_vault = CtxVault(consumer_layout)

        (self.repo_root / "README.md").write_text("# Source Snapshot\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        incoming_snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="incoming",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            snapshot_id=incoming_snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))

        local_readme = consumer_root / "README.md"
        local_readme.parent.mkdir(parents=True, exist_ok=True)
        local_readme.write_text("# Local Snapshot\n", encoding="utf-8")
        consumer_vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        create_snapshot(
            root=consumer_root,
            layout=consumer_layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="local",
        )

        with self.assertRaises(ValueError):
            apply_replica(
                root=consumer_root,
                layout=consumer_layout,
                replica_root=replica_root,
                snapshot_id=incoming_snapshot["snapshot_id"],
                trust_policy={
                    "default_decision": "allow",
                    "require_sync_manifest": True,
                    "trusted_device_ids": [],
                    "allowed_transports": ["local_copy"],
                },
            )

        conflicts = list_sync_conflicts(layout=consumer_layout, limit=10)
        reviewed = review_sync_conflict(
            layout=consumer_layout,
            conflict_marker_path=Path(conflicts["conflicts"][0]["conflict_marker_path"]),
            reviewed_by="unit_test",
            resolution="kept_local",
            notes="Preserve local state until manual reconciliation is complete.",
        )
        events = list_transport_events(layout=consumer_layout, limit=10)

        self.assertEqual(reviewed["conflict_marker"]["status"], "reviewed")
        self.assertEqual(reviewed["conflict_marker"]["resolution"], "kept_local")
        self.assertEqual(reviewed["conflict_marker"]["reviewed_by"], "unit_test")
        self.assertEqual(events["events"][0]["operation"], "sync.conflict-review")

    def test_snapshot_lineage_reports_snapshot_operations(self) -> None:
        replica_root = self.repo_root / "replica-lineage-target"
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="lineage source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="lineage-device",
            snapshot_id=snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))
        import_replica(
            layout=self.layout,
            replica_root=replica_root,
            snapshot_id=snapshot["snapshot_id"],
            trust_policy={
                "default_decision": "allow",
                "require_sync_manifest": True,
                "trusted_device_ids": [],
                "allowed_transports": ["local_copy"],
            },
        )

        lineage = snapshot_lineage(layout=self.layout, snapshot_id=snapshot["snapshot_id"], limit=10)

        self.assertEqual(lineage["snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(lineage["summary"]["matched_event_count"], 4)
        self.assertEqual(
            lineage["summary"]["operation_count_by_type"],
            {
                "snapshot.create": 1,
                "snapshot.sync-manifest": 1,
                "snapshot.sync-copy": 1,
                "replica.import": 1,
            },
        )
        self.assertEqual(
            [event["operation"] for event in lineage["events"]],
            ["snapshot.create", "snapshot.sync-manifest", "snapshot.sync-copy", "replica.import"],
        )

    def test_snapshot_provenance_reports_replica_source_and_trust_entry(self) -> None:
        replica_root = self.repo_root / "replica-provenance-target"
        consumer_root = self.repo_root / "consumer-provenance"
        consumer_layout = default_layout(consumer_root)
        readme = self.repo_root / "README.md"
        readme.write_text("# CtxVault\n", encoding="utf-8")
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        source_snapshot = create_snapshot(
            root=self.repo_root,
            layout=self.layout,
            scope_kind="project",
            scope_value="ctxvault",
            label="provenance source",
        )
        sync_manifest = emit_sync_manifest(
            layout=self.layout,
            target=replica_root.as_uri(),
            transport="local_copy",
            device_id="provenance-device",
            snapshot_id=source_snapshot["snapshot_id"],
        )
        apply_sync_manifest(layout=self.layout, sync_manifest_path=Path(sync_manifest["sync_manifest_path"]))
        set_replica_device_trust(
            layout=consumer_layout,
            device_id="provenance-device",
            trust_state="allow",
            label="Provenance Device",
            allowed_transports=["local_copy"],
        )
        import_replica(
            layout=consumer_layout,
            replica_root=replica_root,
            snapshot_id=source_snapshot["snapshot_id"],
            trust_registry=load_replica_trust_registry(layout=consumer_layout),
        )

        provenance = snapshot_provenance(
            layout=consumer_layout,
            snapshot_id=source_snapshot["snapshot_id"],
            limit=10,
        )

        self.assertEqual(provenance["schema_version"], "ctxvault.snapshot-provenance/v1")
        self.assertTrue(provenance["is_imported_replica"])
        self.assertEqual(provenance["replica_source"]["device_id"], "provenance-device")
        self.assertEqual(provenance["replica_source"]["transport"], "local_copy")
        self.assertEqual(provenance["trust_registry_entry"]["device_id"], "provenance-device")
        self.assertEqual(provenance["lineage"]["summary"]["matched_event_count"], 1)


if __name__ == "__main__":
    unittest.main()
