from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault import cli
from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.surface import CtxVaultSurface
from ctxvault.versioning import record_mutation


class CliBoundaryTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli.main(list(args))
        return result, stdout.getvalue()

    def _subcommand_names(self, parser) -> set[str]:
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict):
                return set(choices)
        self.fail("parser does not expose subcommands")

    def test_build_parser_omits_workbench_when_surface_is_missing(self) -> None:
        with patch("ctxvault.cli.find_spec", return_value=None):
            parser = cli.build_parser()
        self.assertNotIn("workbench", self._subcommand_names(parser))

    def test_load_workbench_server_raises_helpful_error_when_missing(self) -> None:
        error = ModuleNotFoundError("No module named 'ctxvault.workbench'")
        error.name = "ctxvault.workbench"
        with patch("ctxvault.cli.import_module", side_effect=error):
            with self.assertRaises(RuntimeError) as raised:
                cli.load_workbench_server()
        self.assertIn("workbench surface is not available in this build", str(raised.exception))

    def test_main_dispatches_workbench_through_lazy_loader(self) -> None:
        observed: dict[str, object] = {}

        def fake_server(*, root: Path, host: str, port: int) -> int:
            observed["root"] = root
            observed["host"] = host
            observed["port"] = port
            return 17

        with patch("ctxvault.cli.has_workbench_surface", return_value=True), patch(
            "ctxvault.cli.load_workbench_server", return_value=fake_server
        ):
            result = cli.main(["workbench", "--root", str(ROOT), "--host", "127.0.0.1", "--port", "9000"])

        self.assertEqual(result, 17)
        self.assertEqual(observed["root"], ROOT.resolve())
        self.assertEqual(observed["host"], "127.0.0.1")
        self.assertEqual(observed["port"], 9000)

    def test_seed_fixtures_uses_bundled_repo_fixtures_for_clean_root(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            init_code, _ = self.run_cli("init-vault", "--root", str(root))
            self.assertEqual(init_code, 0)

            seed_code, seed_stdout = self.run_cli("seed-fixtures", "--root", str(root))
            self.assertEqual(seed_code, 0)
            seeded = json.loads(seed_stdout)
            self.assertTrue(any(item["object_id"] == "prompt_schema_designer_v1" for item in seeded))
            self.assertTrue(any(item["object_id"] == "ws_20260421_ctxvault_schema" for item in seeded))

            build_code, build_stdout = self.run_cli(
                "build-context",
                "--root",
                str(root),
                "--task-label",
                "clean root validation",
                "--prompt-id",
                "prompt_schema_designer_v1",
                "--memory-query",
                "local LLM",
            )
            self.assertEqual(build_code, 0)
            bundle = json.loads(build_stdout)
            self.assertEqual(bundle["scope"]["value"], "ctxvault")
            self.assertIn("prompt://prompt_schema_designer_v1", bundle["input_refs"])

    def test_adapter_healthcheck_cli_is_read_only_for_agents_md(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "AGENTS.md"

            code, stdout = self.run_cli(
                "adapter-healthcheck",
                "--root",
                str(root),
                "--target-kind",
                "agents-md",
                "--target-path",
                "AGENTS.md",
            )

            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual(result["schema_id"], "ctxvault.projection-healthcheck/v1")
            self.assertEqual(result["adapter_id"], "projection.harness.agents-md")
            self.assertEqual(result["status"], "pass")
            self.assertFalse(result["write_plan"][0]["will_write"])
            self.assertFalse(target.exists())

    def test_adapter_healthcheck_cli_accepts_existing_projection_targets(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            for target_kind, expected_adapter, output_name in [
                ("claude-md", "projection.harness.claude-md", "CLAUDE.md"),
                ("workstream-brief", "projection.wiki.markdown-workstream", "brief.md"),
            ]:
                with self.subTest(target_kind=target_kind):
                    code, stdout = self.run_cli(
                        "adapter-healthcheck",
                        "--root",
                        str(root),
                        "--target-kind",
                        target_kind,
                        "--target-path",
                        output_name,
                    )

                    self.assertEqual(code, 0)
                    result = json.loads(stdout)
                    self.assertEqual(result["adapter_id"], expected_adapter)
                    self.assertEqual(result["status"], "pass")
                    self.assertFalse(result["write_plan"][0]["will_write"])
                    self.assertFalse((root / output_name).exists())

    def test_compiled_workstream_state_cli_is_read_model(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")

            code, stdout = self.run_cli(
                "compiled-workstream-state",
                "--root",
                str(root),
                "--workstream-id",
                "ws_20260421_ctxvault_schema",
            )

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["schema_id"], "ctxvault.compiled-workstream-state/v1")
            self.assertEqual(payload["contract_state"], "experimental_read_model")
            self.assertEqual(payload["workstream_ref"], "workstream://ws_20260421_ctxvault_schema")

    def test_context_slice_cli_rebuild_search_and_preflight(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")

            rebuild_code, rebuild_stdout = self.run_cli("context-slice-rebuild", "--root", str(root))
            self.assertEqual(rebuild_code, 0)
            rebuild = json.loads(rebuild_stdout)
            self.assertGreater(rebuild["slice_count"], 0)

            search_code, search_stdout = self.run_cli(
                "context-search",
                "--root",
                str(root),
                "--query",
                "local-first context layer",
            )
            self.assertEqual(search_code, 0)
            hits = json.loads(search_stdout)
            self.assertTrue(hits)
            self.assertEqual(hits[0]["payload"]["schema_id"], "ctxvault.context-slice/v1")

            preflight_code, preflight_stdout = self.run_cli(
                "context-selection-preflight",
                "--root",
                str(root),
                "--slice-ref",
                hits[0]["slice_ref"],
                "--target-kind",
                "harness.agents-md",
            )
            self.assertEqual(preflight_code, 0)
            preflight = json.loads(preflight_stdout)
            self.assertIn(preflight["receipt"]["decision"], {"allow", "redact", "review", "block"})
            self.assertEqual(preflight["receipt"]["selected_slice_refs"], [hits[0]["slice_ref"]])

            compose_code, compose_stdout = self.run_cli(
                "context-selection-compose",
                "--root",
                str(root),
                "--query",
                "local-first context layer",
                "--target-kind",
                "harness.agents-md",
                "--slice-ref",
                hits[0]["slice_ref"],
                "--candidate-slice-ref",
                hits[0]["slice_ref"],
                "--token-budget",
                "1000",
                "--write-receipt",
            )
            self.assertEqual(compose_code, 0)
            composed = json.loads(compose_stdout)
            self.assertEqual(composed["receipt"]["schema_id"], "ctxvault.context-selection-receipt/v1")
            self.assertEqual(composed["selected_slice_refs"], [hits[0]["slice_ref"]])
            self.assertTrue(Path(composed["receipt_path"]).exists())

            preference_code, preference_stdout = self.run_cli(
                "context-slice-preference-set",
                "--root",
                str(root),
                "--slice-ref",
                hits[0]["slice_ref"],
                "--action",
                "pin",
                "--target-kind",
                "harness.agents-md",
            )
            self.assertEqual(preference_code, 0)
            preference = json.loads(preference_stdout)
            self.assertEqual(preference["action"], "pin")

            list_code, list_stdout = self.run_cli(
                "context-slice-preference-list",
                "--root",
                str(root),
                "--target-kind",
                "harness.agents-md",
            )
            self.assertEqual(list_code, 0)
            self.assertEqual(json.loads(list_stdout)[0]["slice_ref"], hits[0]["slice_ref"])

    def test_context_prepare_and_project_cli_run_safe_handoff_path(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")

            prepare_code, prepare_stdout = self.run_cli(
                "context-prepare",
                "--root",
                str(root),
                "--query",
                "local-first context layer",
                "--target-kind",
                "harness.agents-md",
                "--workstream-ref",
                "workstream://ws_20260421_ctxvault_schema",
                "--limit",
                "3",
                "--token-budget",
                "1000",
            )
            self.assertEqual(prepare_code, 0)
            prepared = json.loads(prepare_stdout)
            self.assertEqual(prepared["schema_id"], "ctxvault.context-prepare/v1")
            self.assertEqual(prepared["operation"], "safe_context_handoff_prepare")
            self.assertTrue(prepared["selected_slice_refs"])
            self.assertTrue(Path(prepared["receipt_path"]).exists())
            self.assertIn(prepared["privacy_decision"], {"allow", "redact", "review"})
            self.assertTrue(any(action["kind"] == "project_context" for action in prepared["next_actions"]))

            project_code, project_stdout = self.run_cli(
                "context-project",
                "--root",
                str(root),
                "--target",
                "agents-md",
                "--workstream-id",
                "ws_20260421_ctxvault_schema",
                "--output-path",
                "exports/handoff/AGENTS.md",
                "--receipt-output-path",
                "exports/handoff/agents-receipt.json",
                "--slice-ref",
                prepared["selected_slice_refs"][0],
            )
            self.assertEqual(project_code, 0)
            projected = json.loads(project_stdout)
            self.assertEqual(projected["schema_id"], "ctxvault.context-project/v1")
            self.assertEqual(projected["target_kind"], "harness.agents-md")
            self.assertTrue(Path(projected["output_path"]).exists())
            self.assertTrue(Path(projected["receipt_path"]).exists())
            self.assertEqual(projected["selected_slice_refs"], [prepared["selected_slice_refs"][0]])

    def test_context_extract_cli_runs_one_click_local_handoff(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            note = root / "one-click-note.md"
            note.write_text(
                "# One click CLI\n\n"
                "The CLI should extract local source material, rebuild slices, prepare context, and project when ready.",
                encoding="utf-8",
            )
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")

            code, stdout = self.run_cli(
                "context-extract",
                "--root",
                str(root),
                "--source-path",
                str(note),
                "--prepare-query",
                "one click cli extract project",
                "--workstream-ref",
                "workstream://ws_20260421_ctxvault_schema",
                "--workstream-id",
                "ws_20260421_ctxvault_schema",
                "--project-target",
                "workstream-brief",
            )

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["schema_id"], "ctxvault.context-extract/v1")
            self.assertEqual(payload["status"], "pass")
            self.assertTrue(Path(payload["receipt_path"]).exists())
            self.assertEqual(payload["imports"][0]["source_kind"], "knowledge")
            self.assertEqual(payload["prepare"]["selection_status"], "ready")
            self.assertEqual(len(payload["projections"]), 1)
            self.assertTrue(Path(payload["projections"][0]["output_path"]).exists())

            inspect_code, inspect_stdout = self.run_cli(
                "receipt-inspect",
                "--root",
                str(root),
                "--receipt-path",
                payload["receipt_path"],
            )
            self.assertEqual(inspect_code, 0)
            inspection = json.loads(inspect_stdout)
            self.assertEqual(inspection["schema_id"], "ctxvault.receipt-inspection/v1")
            self.assertEqual(inspection["status"], "pass")
            self.assertEqual(inspection["chains"][0]["missing_links"], [])

            summary_code, summary_stdout = self.run_cli(
                "receipt-inspect",
                "--root",
                str(root),
                "--receipt-path",
                payload["receipt_path"],
                "--summary",
            )
            self.assertEqual(summary_code, 0)
            self.assertIn("CtxVault receipt inspection", summary_stdout)
            self.assertIn("Selected slices: 1", summary_stdout)
            self.assertIn("Receipt chain:", summary_stdout)

            latest_code, latest_stdout = self.run_cli(
                "receipt-inspect",
                "--root",
                str(root),
                "--latest",
                "--summary",
            )
            self.assertEqual(latest_code, 0)
            self.assertIn("Target: context extract", latest_stdout)

    def test_logical_purge_cli_requires_reviewed_apply(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")
            self.run_cli("context-slice-rebuild", "--root", str(root))

            plan_code, plan_stdout = self.run_cli(
                "logical-purge-plan",
                "--root",
                str(root),
                "--source-ref",
                "knowledge://know_proj_ctxvault_profile_v1",
            )
            self.assertEqual(plan_code, 0)
            plan = json.loads(plan_stdout)
            self.assertGreater(plan["would_delete"]["context_slice_rows"], 0)

            apply_code, apply_stdout = self.run_cli(
                "logical-purge-apply",
                "--root",
                str(root),
                "--source-ref",
                "knowledge://know_proj_ctxvault_profile_v1",
                "--reviewer",
                "privacy-review",
                "--confirm",
            )
            self.assertEqual(apply_code, 0)
            receipt = json.loads(apply_stdout)
            self.assertEqual(receipt["receipt"]["operation"], "logical_purge_derived")
            self.assertTrue(Path(receipt["receipt_path"]).exists())

    def test_doctor_cli_is_read_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            code, stdout = self.run_cli("doctor", "--root", str(root))

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["schema_id"], "ctxvault.doctor-report/v1")
            self.assertEqual(payload["mode"], "read_only")
            self.assertTrue(all(check["read_only"] for check in payload["checks"]))

    def test_markdown_vault_import_cli_is_bridge_not_plugin(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            vault_root = root / "obsidian-vault"
            nested = vault_root / "Projects"
            nested.mkdir(parents=True)
            (vault_root / "index.md").write_text("# Index\n\nCtxVault bridge note.\n", encoding="utf-8")
            (nested / "decision.markdown").write_text("# Decision\n\nKeep Markdown as source material.\n", encoding="utf-8")
            (vault_root / "scratch.txt").write_text("txt should stay outside the markdown-vault bridge alias", encoding="utf-8")

            code, stdout = self.run_cli(
                "markdown-vault-import",
                "--root",
                str(root),
                "--vault-path",
                str(vault_root),
                "--scope-kind",
                "project",
                "--scope-value",
                "ctxvault",
            )

            self.assertEqual(code, 0)
            receipts = json.loads(stdout)
            self.assertEqual([Path(receipt["source_path"]).suffix for receipt in receipts], [".markdown", ".md"])

    def test_transport_dashboard_reports_aggregated_transport_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            (root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
            prompt = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text(encoding="utf-8"))
            surface.vault.store_core_object("PromptAsset", prompt)
            snapshot = surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="cli transport")
            surface.sync_receipt_emit(
                snapshot_id=snapshot["snapshot_id"],
                target="file:///Volumes/local-backup/ctxvault",
                transport="local_copy",
                device_id="cli-dashboard-device",
            )
            surface.replica_trust_set(
                device_id="cli-dashboard-device",
                trust_state="allow",
                allowed_transports=["local_copy"],
            )
            surface.replica_pairing_offer_emit(
                device_id="cli-dashboard-phone",
                allowed_transports=["local_copy"],
            )
            record_mutation(
                layout=surface.vault.layout,
                mutation_kind="audit.review",
                object_ref="audit://audit_cli_dashboard_001",
                actor="cli_test",
                decision="approved",
                scope={"kind": "project", "value": "ctxvault"},
            )

            code, stdout = self.run_cli("transport-dashboard", "--root", str(root))
            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["summary"]["latest_local_snapshot_id"], snapshot["snapshot_id"])
            self.assertEqual(payload["summary"]["trusted_device_count"], 1)
            self.assertEqual(payload["summary"]["open_pairing_offer_count"], 1)
            self.assertEqual(payload["summary"]["recent_mutation_count"], 1)
            self.assertEqual(payload["sync"]["targets"][0]["state"], "in_sync")

    def test_companion_sync_feed_reports_mobile_safe_transport_state(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            (root / "README.md").write_text("# CtxVault\n", encoding="utf-8")
            prompt = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text(encoding="utf-8"))
            surface.vault.store_core_object("PromptAsset", prompt)
            snapshot = surface.snapshot_create(scope_kind="project", scope_value="ctxvault", label="cli companion sync")
            surface.sync_receipt_emit(
                snapshot_id=snapshot["snapshot_id"],
                target="file:///Volumes/local-backup/ctxvault",
                transport="local_copy",
                device_id="cli-companion-sync-device",
            )
            surface.replica_trust_set(
                device_id="cli-companion-review-device",
                trust_state="review",
                allowed_transports=["local_copy"],
            )
            surface.replica_pairing_offer_emit(
                device_id="cli-companion-phone",
                allowed_transports=["local_copy"],
            )

            code, stdout = self.run_cli("companion-sync-feed", "--root", str(root))
            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["summary"]["review_device_count"], 1)
            self.assertEqual(payload["summary"]["open_pairing_offer_count"], 1)
            self.assertEqual(payload["sync_targets"][0]["state"], "in_sync")
            self.assertEqual(payload["open_pairing_offers"][0]["actions"], ["accept_pairing"])

    def test_local_backup_write_cli_creates_verified_replica(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "workspace"
            root.mkdir()
            target = Path(tmpdir) / "local-backup-target"
            (root / "README.md").write_text("# CtxVault\n", encoding="utf-8")

            code, stdout = self.run_cli(
                "local-backup-write",
                "--root",
                str(root),
                "--target",
                target.as_uri(),
                "--label",
                "cli local backup",
                "--device-id",
                "cli-local-backup-device",
            )

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["receipt"]["schema_version"], "ctxvault.local-backup-write-receipt/v1")
            self.assertEqual(payload["receipt"]["status"], "verified")
            self.assertEqual(payload["verification"]["status"], "verified")
            self.assertTrue((target / "snapshots" / Path(payload["snapshot"]["manifest_path"]).name).exists())
            self.assertTrue((target / "snapshot-bundles" / Path(payload["snapshot"]["restore_bundle_path"]).name).exists())

    def test_privacy_scan_files_reports_attachment_findings(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            attachment = root / "attachment.txt"
            attachment.write_text('OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"\n', encoding="utf-8")

            code, stdout = self.run_cli(
                "privacy-scan-files",
                "--root",
                str(root),
                "--file-path",
                str(attachment),
            )

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["decision"], "block")
            self.assertEqual(payload["summary"]["file_count"], 1)
            self.assertEqual(payload["files"][0]["content_scan_state"], "scanned")

    def test_share_handoff_cli_stage_preview_and_consume(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            shared_root = root / "app-group"
            attachment = shared_root / "attachments" / "note.txt"
            attachment.parent.mkdir(parents=True, exist_ok=True)
            attachment.write_text("Share extension payload.\n", encoding="utf-8")

            stage_code, stage_stdout = self.run_cli(
                "share-handoff-stage",
                "--root",
                str(root),
                "--shared-root",
                str(shared_root),
                "--title",
                "CLI share handoff",
                "--text",
                "Queue mobile ingress before candidate creation.",
                "--attachment-path",
                "attachments/note.txt",
                "--url",
                "https://example.com/share-cli",
                "--source-app",
                "share_extension",
            )
            self.assertEqual(stage_code, 0)
            staged = json.loads(stage_stdout)

            preview_code, preview_stdout = self.run_cli(
                "share-handoff-preview",
                "--root",
                str(root),
                "--shared-root",
                str(shared_root),
                "--handoff-path",
                staged["handoff_path"],
            )
            self.assertEqual(preview_code, 0)
            preview = json.loads(preview_stdout)

            consume_code, consume_stdout = self.run_cli(
                "share-handoff-consume",
                "--root",
                str(root),
                "--shared-root",
                str(shared_root),
                "--handoff-path",
                staged["handoff_path"],
                "--why-it-matters",
                "This keeps mobile capture on the governed candidate path.",
            )
            self.assertEqual(consume_code, 0)
            consumed = json.loads(consume_stdout)

            list_code, list_stdout = self.run_cli(
                "share-handoff-list",
                "--root",
                str(root),
                "--shared-root",
                str(shared_root),
                "--include-archived",
            )
            self.assertEqual(list_code, 0)
            listed = json.loads(list_stdout)

            self.assertEqual(staged["handoff"]["status"], "pending")
            self.assertEqual(preview["decision"], "allow")
            self.assertEqual(preview["capture_defaults"]["statement"], "CLI share handoff")
            self.assertEqual(consumed["handoff"]["status"], "consumed")
            self.assertEqual(consumed["capture"]["candidate"]["proposal_state"], "proposed")
            self.assertEqual(listed["summary"]["archived_count"], 1)

    def test_emit_wiki_projection_writes_projection_receipt(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            workstream = json.loads((ROOT / "fixtures" / "core" / "workstream.json").read_text(encoding="utf-8"))
            memory = json.loads((ROOT / "fixtures" / "core" / "memory.json").read_text(encoding="utf-8"))
            surface.vault.store_core_object("Workstream", workstream)
            surface.vault.store_core_object("Memory", memory)

            code, stdout = self.run_cli(
                "emit-wiki-projection",
                "--root",
                str(root),
                "--workstream-id",
                workstream["id"],
                "--output-path",
                "exports/wiki.md",
                "--receipt-output-path",
                "artifacts/wiki-receipt.json",
            )

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["receipt"]["target_kind"], "wiki.markdown-workstream")
            self.assertTrue((root / "exports" / "wiki.md").exists())
            self.assertTrue((root / "artifacts" / "wiki-receipt.json").exists())

    def test_emit_wiki_projection_with_slice_ref_records_preflight(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")
            surface.context_slice_rebuild()
            hit = surface.context_search("local-first context layer", scope_kind="project", scope_value="ctxvault")[0]

            code, stdout = self.run_cli(
                "emit-wiki-projection",
                "--root",
                str(root),
                "--workstream-id",
                "ws_20260421_ctxvault_schema",
                "--output-path",
                "exports/wiki.md",
                "--receipt-output-path",
                "artifacts/wiki-receipt.json",
                "--slice-ref",
                hit["slice_ref"],
            )

            self.assertEqual(code, 0)
            payload = json.loads(stdout)
            self.assertEqual(payload["receipt"]["selected_slice_refs"], [hit["slice_ref"]])
            self.assertEqual(payload["receipt"]["privacy_preflight"]["schema_id"], "ctxvault.privacy-preflight-receipt/v1")


if __name__ == "__main__":
    unittest.main()
