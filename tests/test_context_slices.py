from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.context_slices import build_markdown_context_slices
from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.policy import CtxVaultPolicy
from ctxvault.surface import CtxVaultSurface
from scripts.validate_fixtures import validate


SCHEMA = ROOT / "docs" / "v0.3.1-local-safety" / "experimental-schemas" / "ctxvault-context-slice-v1.schema.json"
FIXTURE = ROOT / "docs" / "v0.3.1-local-safety" / "experimental-fixtures" / "context-slice.json"
PREFLIGHT_SCHEMA = ROOT / "docs" / "v0.3.1-local-safety" / "experimental-schemas" / "ctxvault-privacy-preflight-receipt-v1.schema.json"
PREFLIGHT_FIXTURE = ROOT / "docs" / "v0.3.1-local-safety" / "experimental-fixtures" / "privacy-preflight-receipt.json"
SELECTION_SCHEMA = ROOT / "docs" / "v0.3.2-injection-composer" / "experimental-schemas" / "ctxvault-context-selection-receipt-v1.schema.json"
SELECTION_FIXTURE = ROOT / "docs" / "v0.3.2-injection-composer" / "experimental-fixtures" / "context-selection-receipt.json"


class ContextSliceTests(unittest.TestCase):
    def test_context_slice_fixture_matches_experimental_schema(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

        validate(fixture, schema, schema, FIXTURE.name)

    def test_privacy_preflight_fixture_matches_experimental_schema(self) -> None:
        schema = json.loads(PREFLIGHT_SCHEMA.read_text(encoding="utf-8"))
        fixture = json.loads(PREFLIGHT_FIXTURE.read_text(encoding="utf-8"))

        validate(fixture, schema, schema, PREFLIGHT_FIXTURE.name)

    def test_context_selection_fixture_matches_experimental_schema(self) -> None:
        schema = json.loads(SELECTION_SCHEMA.read_text(encoding="utf-8"))
        fixture = json.loads(SELECTION_FIXTURE.read_text(encoding="utf-8"))

        validate(fixture, schema, schema, SELECTION_FIXTURE.name)

    def test_rebuild_indexes_markdown_slices_and_searches_redacted_previews(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            surface = CtxVaultSurface(vault)
            vault.store_core_object(
                "KnowledgeArtifact",
                {
                    "id": "know_context_picker_fixture",
                    "kind": "project_note",
                    "title": "Context picker note",
                    "scope": {"kind": "project", "value": "ctxvault"},
                    "body": (
                        "# Release context\n\n"
                        "The context picker should group deterministic local slices before projection.\n\n"
                        "# Review contact\n\n"
                        "Internal contact owner@example.com should be reviewed before injection.\n\n"
                        "# Secret material\n\n"
                        "Do not index this credential: sk-abcdefghijklmnopqrstuvwxyz1234567890"
                    ),
                    "source_refs": [],
                    "derived_from": [],
                    "status": "active",
                    "sensitivity": "internal",
                    "redaction_state": "none",
                    "secret_refs": [],
                    "exportable": True,
                    "created_at": "2026-04-30T00:00:00Z",
                    "updated_at": "2026-04-30T00:00:00Z",
                },
            )

            rebuild = surface.context_slice_rebuild()
            hits = surface.context_search("context picker projection", scope_kind="project", scope_value="ctxvault")

            self.assertGreaterEqual(rebuild["slice_count"], 2)
            self.assertTrue(hits)
            self.assertEqual(hits[0]["payload"]["schema_id"], "ctxvault.context-slice/v1")
            self.assertIn("ranking_reasons", hits[0]["payload"])

            with closing(sqlite3.connect(vault.layout.sqlite_path)) as conn:
                rows = conn.execute("SELECT title, body_redacted FROM context_slice_fts").fetchall()
            indexed_text = "\n".join(" ".join(str(part or "") for part in row) for row in rows)
            self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz1234567890", indexed_text)
            self.assertIn("[REDACTED:direct_identifier]", indexed_text)

            all_hits = surface.context_search("", include_blocked=True, limit=20)
            withheld = [hit for hit in all_hits if hit["payload"]["privacy_class"] == "withheld"]
            self.assertTrue(withheld)
            self.assertEqual(withheld[0]["payload"]["redacted_preview"], "")

            preflight = surface.context_selection_preflight(
                [withheld[0]["slice_ref"]],
                target_kind="harness.agents-md",
                query="release context",
            )
            self.assertEqual(preflight["receipt"]["decision"], "block")
            self.assertIn("selection includes withheld slices", preflight["receipt"]["reasons"])

    def test_context_slice_refs_survive_unrelated_neighboring_markdown_edits(self) -> None:
        target = " ".join(["stable-selection-block"] * 90)
        before = " ".join(["before-neighbor"] * 90)
        inserted = " ".join(["new-unrelated-neighbor"] * 90)
        body_a = f"# Plan\n\n{before}\n\n{target}\n"
        body_b = f"# Plan\n\n{inserted}\n\n{before}\n\n{target}\n"

        slices_a = build_markdown_context_slices(
            source_kind="knowledge",
            source_id="know_stability",
            source_ref="knowledge://know_stability",
            source_object_kind="knowledge_artifact",
            title="Stability",
            body_text=body_a,
            scope_kind="project",
            scope_value="ctxvault",
            workstream_ref=None,
            updated_at="2026-04-30T00:00:00Z",
        )
        slices_b = build_markdown_context_slices(
            source_kind="knowledge",
            source_id="know_stability",
            source_ref="knowledge://know_stability",
            source_object_kind="knowledge_artifact",
            title="Stability",
            body_text=body_b,
            scope_kind="project",
            scope_value="ctxvault",
            workstream_ref=None,
            updated_at="2026-04-30T00:00:00Z",
        )

        target_hash = next(item.content_sha256 for item in slices_a if "stable-selection-block" in item.redacted_preview)
        ref_a = next(item.slice_ref for item in slices_a if item.content_sha256 == target_hash)
        ref_b = next(item.slice_ref for item in slices_b if item.content_sha256 == target_hash)

        self.assertEqual(ref_a, ref_b)

    def test_compiled_state_slices_rank_in_context_search(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            vault.import_core_fixtures(ROOT / "fixtures" / "core")
            surface = CtxVaultSurface(vault)

            rebuild = surface.context_slice_rebuild()
            hits = surface.context_search("deterministic schema migration", scope_kind="project", scope_value="ctxvault")

            self.assertGreater(rebuild["source_counts"].get("compiled_workstream_state", 0), 0)
            self.assertTrue(any(hit["payload"]["source_object_kind"] == "compiled_workstream_state" for hit in hits))

    def test_logical_purge_deletes_derived_slices_without_deleting_source(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            surface = CtxVaultSurface(vault)
            vault.store_core_object(
                "KnowledgeArtifact",
                {
                    "id": "know_purge_fixture",
                    "kind": "project_note",
                    "title": "Purge fixture",
                    "scope": {"kind": "project", "value": "ctxvault"},
                    "body": "Sensitive contact owner@example.com should be purged from derived indexes.",
                    "source_refs": [],
                    "derived_from": [],
                    "status": "active",
                    "sensitivity": "sensitive",
                    "redaction_state": "none",
                    "secret_refs": [],
                    "exportable": True,
                    "created_at": "2026-04-30T00:00:00Z",
                    "updated_at": "2026-04-30T00:00:00Z",
                },
            )
            surface.context_slice_rebuild()

            plan = surface.logical_purge_plan(source_refs=["knowledge://know_purge_fixture"])
            self.assertEqual(plan["operation"], "logical_purge_derived")
            self.assertEqual(plan["would_delete"]["context_slice_rows"], 1)
            self.assertTrue(plan["retained"]["governed_source_objects"])

            policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text(encoding="utf-8"))
            backup = CtxVaultPolicy.freshen_backup_receipt(
                json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text(encoding="utf-8"))
            )
            result = surface.logical_purge_apply(
                source_refs=["knowledge://know_purge_fixture"],
                reviewer="privacy-review",
                policy_payload=policy,
                backup_receipt=backup,
                confirm=True,
            )

            self.assertTrue(Path(result["receipt_path"]).exists())
            self.assertEqual(result["receipt"]["secure_deletion_claim"], "none")
            self.assertEqual(surface.context_search("owner@example.com", include_blocked=True), [])
            self.assertTrue((vault.layout.objects_dir / "knowledge_artifact" / "know_purge_fixture.json").exists())

    def test_selected_slice_projection_runs_preflight_and_records_receipt(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            vault.import_core_fixtures(ROOT / "fixtures" / "core")
            surface = CtxVaultSurface(vault)
            surface.context_slice_rebuild()
            hit = surface.context_search("local-first context layer", scope_kind="project", scope_value="ctxvault")[0]
            output = root / "workstream.md"
            receipt_path = root / "workstream-receipt.json"

            result = surface.wiki_workstream_markdown_emit(
                workstream_id="ws_20260421_ctxvault_schema",
                output_path=output,
                receipt_output_path=receipt_path,
                selected_slice_refs=[hit["slice_ref"]],
            )
            receipt = result["receipt"]
            rendered = output.read_text(encoding="utf-8")

            self.assertIn("## Selected Context Slices", rendered)
            self.assertEqual(receipt["selected_slice_refs"], [hit["slice_ref"]])
            self.assertEqual(receipt["privacy_preflight"]["schema_id"], "ctxvault.privacy-preflight-receipt/v1")
            self.assertTrue(receipt["privacy_preflight"]["projection_gate"]["allowed_to_write"])
            self.assertTrue(receipt["context_selection_ref"].startswith("context-selection://ctxsel_"))
            self.assertTrue(receipt["context_selection_receipt_id"].startswith("ctxsel_"))

    def test_context_selection_composer_groups_sources_and_writes_receipt(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            vault.import_core_fixtures(ROOT / "fixtures" / "core")
            surface = CtxVaultSurface(vault)
            for object_id, title, body in [
                (
                    "know_picker_file_a",
                    "Picker file A",
                    "# File A\n\nThe injection composer should choose exact local context slices for the release plan.",
                ),
                (
                    "know_picker_file_b",
                    "Picker file B",
                    "# File B\n\nThe context picker should keep privacy preflight ahead of AGENTS projection.",
                ),
            ]:
                vault.store_core_object(
                    "KnowledgeArtifact",
                    {
                        "id": object_id,
                        "kind": "project_note",
                        "title": title,
                        "scope": {"kind": "project", "value": "ctxvault"},
                        "body": body,
                        "source_refs": [],
                        "derived_from": [],
                        "status": "active",
                        "sensitivity": "internal",
                        "redaction_state": "none",
                        "secret_refs": [],
                        "exportable": True,
                        "created_at": "2026-04-30T00:00:00Z",
                        "updated_at": "2026-04-30T00:00:00Z",
                    },
                )
            surface.context_slice_rebuild()
            all_hits = surface.context_search("", scope_kind="project", scope_value="ctxvault", limit=100)
            selected_refs = [
                next(hit["slice_ref"] for hit in all_hits if hit["payload"]["source_ref"] == "knowledge://know_picker_file_a"),
                next(hit["slice_ref"] for hit in all_hits if hit["payload"]["source_ref"] == "knowledge://know_picker_file_b"),
                next(hit["slice_ref"] for hit in all_hits if hit["payload"]["source_object_kind"] == "compiled_workstream_state"),
            ]

            result = surface.context_selection_compose(
                "release plan privacy projection",
                target_kind="harness.agents-md",
                scope_kind="project",
                scope_value="ctxvault",
                workstream_ref="workstream://ws_20260421_ctxvault_schema",
                selected_slice_refs=selected_refs,
                candidate_slice_refs=selected_refs,
                token_budget=2,
                write_receipt=True,
            )

            self.assertEqual(result["receipt"]["schema_id"], "ctxvault.context-selection-receipt/v1")
            self.assertEqual(result["receipt"]["selected_slice_refs"], selected_refs)
            self.assertEqual(result["budget_status"], "over_budget")
            self.assertEqual(result["privacy_preflight"]["receipt"]["decision"], "allow")
            self.assertTrue(result["receipt"]["privacy_preflight_ref"].startswith("receipt://privacy-preflight/"))
            self.assertEqual(len(result["source_groups"]), 3)
            self.assertTrue(Path(result["receipt_path"]).exists())

    def test_context_selection_preferences_pin_and_hide_candidates(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            surface = CtxVaultSurface(vault)
            for object_id, title, body in [
                ("know_preference_pin", "Preference pin", "Pin this context picker slice for projection."),
                ("know_preference_hide", "Preference hide", "Hide this context picker slice from suggestions."),
            ]:
                vault.store_core_object(
                    "KnowledgeArtifact",
                    {
                        "id": object_id,
                        "kind": "project_note",
                        "title": title,
                        "scope": {"kind": "project", "value": "ctxvault"},
                        "body": body,
                        "source_refs": [],
                        "derived_from": [],
                        "status": "active",
                        "sensitivity": "internal",
                        "redaction_state": "none",
                        "secret_refs": [],
                        "exportable": True,
                        "created_at": "2026-04-30T00:00:00Z",
                        "updated_at": "2026-04-30T00:00:00Z",
                    },
                )
            surface.context_slice_rebuild()
            hits = surface.context_search("context picker slice", scope_kind="project", scope_value="ctxvault", limit=10)
            pin_ref = next(hit["slice_ref"] for hit in hits if hit["payload"]["source_ref"] == "knowledge://know_preference_pin")
            hide_ref = next(hit["slice_ref"] for hit in hits if hit["payload"]["source_ref"] == "knowledge://know_preference_hide")

            surface.context_slice_preference_set(slice_ref=pin_ref, action="pin", target_kind="harness.agents-md")
            surface.context_slice_preference_set(slice_ref=hide_ref, action="hide", target_kind="harness.agents-md")
            result = surface.context_selection_compose(
                "context picker slice",
                target_kind="harness.agents-md",
                scope_kind="project",
                scope_value="ctxvault",
                candidate_slice_refs=[hide_ref, pin_ref],
            )

            candidate_refs = result["candidate_slice_refs"]
            self.assertEqual(candidate_refs, [pin_ref])
            self.assertEqual(result["source_groups"][0]["slices"][0]["preference_action"], "pin")
            actions = {item["slice_ref"]: item["action"] for item in surface.context_slice_preference_list(target_kind="harness.agents-md")}
            self.assertEqual(actions[pin_ref], "pin")
            self.assertEqual(actions[hide_ref], "hide")

    def test_selected_slice_projection_blocks_withheld_slice_before_write(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            vault.import_core_fixtures(ROOT / "fixtures" / "core")
            surface = CtxVaultSurface(vault)
            vault.store_core_object(
                "KnowledgeArtifact",
                {
                    "id": "know_projection_block_fixture",
                    "kind": "project_note",
                    "title": "Projection block fixture",
                    "scope": {"kind": "project", "value": "ctxvault"},
                    "body": "Do not project this credential sk-abcdefghijklmnopqrstuvwxyz1234567890",
                    "source_refs": [],
                    "derived_from": [],
                    "status": "active",
                    "sensitivity": "restricted",
                    "redaction_state": "none",
                    "secret_refs": [],
                    "exportable": True,
                    "created_at": "2026-04-30T00:00:00Z",
                    "updated_at": "2026-04-30T00:00:00Z",
                },
            )
            surface.context_slice_rebuild()
            withheld = [
                hit
                for hit in surface.context_search("", include_blocked=True, limit=50)
                if hit["payload"]["privacy_class"] == "withheld"
            ][0]
            output = root / "blocked.md"
            receipt_path = root / "blocked-receipt.json"

            with self.assertRaisesRegex(ValueError, "preflight blocked projection"):
                surface.wiki_workstream_markdown_emit(
                    workstream_id="ws_20260421_ctxvault_schema",
                    output_path=output,
                    receipt_output_path=receipt_path,
                    selected_slice_refs=[withheld["slice_ref"]],
                )

            self.assertFalse(output.exists())
            self.assertFalse(receipt_path.exists())

    def test_logical_purge_tombstones_projection_receipts_referencing_purged_slices(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault = CtxVault(default_layout(root))
            vault.import_core_fixtures(ROOT / "fixtures" / "core")
            surface = CtxVaultSurface(vault)
            surface.context_slice_rebuild()
            hit = surface.context_search("local-first context layer", scope_kind="project", scope_value="ctxvault")[0]
            output = root / "workstream.md"
            receipt_path = root / "exports" / "receipts" / "workstream-receipt.json"
            surface.wiki_workstream_markdown_emit(
                workstream_id="ws_20260421_ctxvault_schema",
                output_path=output,
                receipt_output_path=receipt_path,
                selected_slice_refs=[hit["slice_ref"]],
            )
            policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text(encoding="utf-8"))
            backup = CtxVaultPolicy.freshen_backup_receipt(
                json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text(encoding="utf-8"))
            )

            purge = surface.logical_purge_apply(
                source_refs=[hit["payload"]["source_ref"]],
                reviewer="privacy-review",
                policy_payload=policy,
                backup_receipt=backup,
                confirm=True,
            )
            report = surface.doctor_report()
            projection_ref_check = next(check for check in report["checks"] if check["name"] == "projection_slice_refs")

            self.assertIn(str(receipt_path.resolve()), purge["receipt"]["tombstoned_receipts"])
            self.assertTrue(all(Path(path).exists() for path in purge["receipt"]["tombstone_paths"]))
            self.assertEqual(projection_ref_check["status"], "warn")
            self.assertIn(hit["slice_ref"], projection_ref_check["missing_slice_refs"])

    def test_logical_purge_requires_explicit_selector(self) -> None:
        with TemporaryDirectory() as tmpdir:
            surface = CtxVaultSurface(CtxVault(default_layout(Path(tmpdir))))

            with self.assertRaisesRegex(ValueError, "at least one source ref or slice ref is required"):
                surface.logical_purge_plan()


if __name__ == "__main__":
    unittest.main()
