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


if __name__ == "__main__":
    unittest.main()
