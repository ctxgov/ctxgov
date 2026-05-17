from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.core import CtxVault
from ctxgov.layout import default_layout
from ctxgov.surface import CtxVaultSurface


class ContextExtractTests(unittest.TestCase):
    def test_context_extract_imports_prepares_and_projects_with_receipts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            note = root / "source-note.md"
            note.write_text(
                "# One click source\n\n"
                "One click extraction should retain the source, rebuild context slices, prepare privacy receipts, "
                "and project a stable workstream handoff.",
                encoding="utf-8",
            )
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")

            result = surface.context_extract(
                source_paths=[note],
                source_kind="auto",
                scope_kind="project",
                scope_value="ctxvault",
                prepare_query="one click extraction stable handoff source",
                workstream_ref="workstream://ws_20260421_ctxvault_schema",
                project_targets=["workstream-brief"],
                workstream_id="ws_20260421_ctxvault_schema",
            )

            self.assertEqual(result["schema_id"], "ctxvault.context-extract/v1")
            self.assertEqual(result["status"], "pass")
            self.assertTrue(Path(result["receipt_path"]).exists())
            self.assertEqual(result["imports"][0]["source_kind"], "knowledge")
            self.assertEqual(result["receipt"]["object_counts"]["knowledge"], 1)
            self.assertGreater(result["slice_rebuild"]["slice_count"], 0)
            self.assertEqual(result["prepare"]["selection_status"], "ready")
            self.assertTrue(result["prepare"]["context_quality_receipt"]["required_refs_retained"])
            self.assertEqual(len(result["projections"]), 1)
            self.assertTrue(Path(result["projections"][0]["output_path"]).exists())
            self.assertTrue(Path(result["projections"][0]["receipt_path"]).exists())
            self.assertEqual(result["next_actions"][0]["kind"], "inspect_projections")

            inspection = surface.receipt_inspect(receipt_path=Path(result["receipt_path"]))
            self.assertEqual(inspection["schema_id"], "ctxvault.receipt-inspection/v1")
            self.assertEqual(inspection["status"], "pass")
            chain = inspection["chains"][0]
            self.assertEqual(chain["status"], "pass")
            self.assertEqual(chain["missing_links"], [])
            self.assertIn("context_extract", {node["kind"] for node in chain["nodes"]})
            self.assertIn("context_selection", {node["kind"] for node in chain["nodes"]})
            self.assertIn("projection", {node["kind"] for node in chain["nodes"]})
            self.assertTrue(chain["context_summary"]["selected_slice_refs"])
            self.assertEqual(chain["context_summary"]["quality_statuses"], ["pass"])
            self.assertIn("CtxVault receipt inspection", inspection["summary_text"])
            self.assertIn("Selected slices: 1", inspection["summary_text"])
            self.assertIn("Projection targets: wiki.markdown-workstream", inspection["summary_text"])
            latest_inspection = surface.receipt_inspect(latest=True)
            self.assertEqual(latest_inspection["status"], "pass")
            self.assertEqual(latest_inspection["target"]["kind"], "context_extract")

            doctor = surface.doctor_report()
            checks = {check["name"]: check for check in doctor["checks"]}
            self.assertEqual(checks["context_extract_receipts"]["status"], "pass")
            self.assertEqual(checks["projection_selection_receipts"]["status"], "pass")

            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["schema_id"], "ctxvault.context-extract-receipt/v1")
            self.assertEqual(receipt["idempotency_key"], result["receipt"]["idempotency_key"])
            self.assertEqual(receipt["source_fingerprints"][0]["sha256"], result["receipt"]["source_fingerprints"][0]["sha256"])

            rerun = surface.context_extract(
                source_paths=[note],
                source_kind="auto",
                scope_kind="project",
                scope_value="ctxvault",
                write_receipt=False,
            )
            self.assertEqual(rerun["receipt"]["idempotency_key"], result["receipt"]["idempotency_key"])
            self.assertEqual(rerun["receipt"]["object_refs"], result["receipt"]["object_refs"])

            note.write_text("# One click source\n\nThe source changed after extraction.", encoding="utf-8")
            stale_doctor = surface.doctor_report()
            stale_checks = {check["name"]: check for check in stale_doctor["checks"]}
            self.assertEqual(stale_checks["context_extract_receipts"]["status"], "warn")
            self.assertGreater(stale_checks["context_extract_receipts"]["stale_source_count"], 0)

    def test_context_extract_blocks_projection_when_handoff_is_not_ready(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            note = root / "over-budget-note.md"
            note.write_text("# Over budget source\n\n" + " ".join(["stable extraction handoff"] * 80), encoding="utf-8")
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            surface.vault.import_core_fixtures(ROOT / "fixtures" / "core")

            result = surface.context_extract(
                source_paths=[note],
                source_kind="knowledge",
                scope_kind="project",
                scope_value="ctxvault",
                prepare_query="stable extraction handoff",
                token_budget=1,
                workstream_ref="workstream://ws_20260421_ctxvault_schema",
                project_targets=["workstream-brief"],
                workstream_id="ws_20260421_ctxvault_schema",
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["prepare"]["selection_status"], "over_budget")
            self.assertEqual(result["skipped_projections"][0]["reason"], "handoff_not_ready")
            self.assertEqual(result["projections"], [])

    def test_context_extract_dry_run_fingerprints_without_importing(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            note = root / "dry-run-note.md"
            note.write_text("# Dry run source\n\nPlan extraction without writing governed objects.", encoding="utf-8")
            surface = CtxVaultSurface(CtxVault(default_layout(root)))

            result = surface.context_extract(
                source_paths=[note],
                source_kind="auto",
                scope_kind="project",
                scope_value="ctxvault",
                dry_run=True,
            )

            self.assertEqual(result["status"], "dry_run")
            self.assertTrue(Path(result["receipt_path"]).exists())
            self.assertEqual(result["receipt"]["planned_imports"][0]["source_kind"], "knowledge")
            self.assertEqual(result["imports"], [])
            self.assertIsNone(result["slice_rebuild"])
            self.assertEqual(result["receipt"]["object_refs"], [])
            self.assertFalse((root / ".ctxvault" / "objects" / "knowledge_artifact").exists())

    def test_context_extract_source_shape_fixtures_import_locally(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            fixture_root = ROOT / "fixtures" / "v0.3.4-context-extract"

            transcript_sources = [
                fixture_root / "chatgpt" / "conversations.json",
                fixture_root / "claude" / "conversations.json",
                fixture_root / "gemini" / "messages.json",
                fixture_root / "deepseek" / "messages.json",
                fixture_root / "ollama" / "messages.json",
            ]
            for source_path in transcript_sources:
                with self.subTest(source_path=source_path):
                    result = surface.context_extract(
                        source_paths=[source_path],
                        source_kind="auto",
                        scope_kind="project",
                        scope_value="ctxvault",
                        write_receipt=False,
                    )
                    self.assertEqual(result["imports"][0]["source_kind"], "transcript")
                    self.assertEqual(result["imports"][0]["receipt_count"], 1)
                    self.assertGreater(result["slice_rebuild"]["slice_count"], 0)

            markdown_result = surface.context_extract(
                source_paths=[fixture_root / "markdown-vault"],
                source_kind="markdown-vault",
                scope_kind="project",
                scope_value="ctxvault",
                recursive=True,
                write_receipt=False,
            )
            self.assertEqual(markdown_result["imports"][0]["source_kind"], "markdown-vault")
            self.assertEqual(markdown_result["imports"][0]["receipt_count"], 2)

            prompt_result = surface.context_extract(
                source_paths=[fixture_root / "prompt" / "context-prompt.md"],
                source_kind="prompt",
                scope_kind="project",
                scope_value="ctxvault",
                write_receipt=False,
            )
            self.assertEqual(prompt_result["imports"][0]["source_kind"], "prompt")
            self.assertEqual(prompt_result["receipt"]["object_counts"]["prompt"], 1)

    def test_context_extract_stability_scorecard_script_passes(self) -> None:
        with TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_v034_context_extract_stability.py"),
                    "--root",
                    tmpdir,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["schema_id"], "ctxvault.v0.3.4-context-extract-stability-scorecard/v1")
            self.assertEqual(payload["status"], "pass")
            self.assertTrue(all(payload["pass_checks"].values()))


if __name__ == "__main__":
    unittest.main()
