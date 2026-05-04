from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = ROOT / "scripts" / "run_v032_deterministic_demo.py"
INSPECT_SCRIPT = ROOT / "scripts" / "inspect_v032_demo_receipts.py"
SCORECARD_SCRIPT = ROOT / "scripts" / "run_v032_selection_scorecard.py"


class V032PostReleaseAssetTests(unittest.TestCase):
    def test_deterministic_demo_emits_selection_and_projection_receipts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "demo"
            summary = _run_json(DEMO_SCRIPT, root)

            self.assertTrue(summary["ok"])
            self.assertFalse(summary["claim_boundary"]["requires_model"])
            self.assertFalse(summary["claim_boundary"]["requires_remote_provider"])
            self.assertEqual(summary["selection"]["privacy_decision"], "allow")
            self.assertEqual(summary["selection"]["blocked_candidate"]["privacy_class"], "withheld")
            self.assertFalse(summary["selection"]["blocked_candidate"]["is_selected"])
            self.assertTrue(Path(summary["selection"]["receipt_path"]).exists())

            selected_refs = summary["selection"]["selected_slice_refs"]
            rendered_outputs: list[str] = []
            for projection in summary["projections"].values():
                output_path = Path(projection["output_path"])
                receipt_path = Path(projection["receipt_path"])
                self.assertTrue(output_path.exists())
                self.assertTrue(receipt_path.exists())
                self.assertEqual(projection["selected_slice_refs"], selected_refs)
                self.assertEqual(projection["privacy_decision"], "allow")
                self.assertEqual(projection["policy_decision"], "allow")
                self.assertTrue(str(projection["context_selection_ref"]).startswith("context-selection://ctxsel_"))
                rendered_outputs.append(output_path.read_text(encoding="utf-8"))

            rendered = "\n".join(rendered_outputs)
            self.assertIn("Selected Context Slices", rendered)
            self.assertIn("v0.3.2 demonstrates deterministic context selection", rendered)
            self.assertIn("Projection files are rebuildable views", rendered)
            self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz1234567890", rendered)

            inspection = _run_json_with_args(
                INSPECT_SCRIPT,
                ["--summary-path", str(Path(summary["summary_path"]))],
            )
            self.assertEqual(inspection["status"], "pass")
            self.assertTrue(Path(inspection["report_path"]).exists())
            self.assertTrue(all(check["status"] == "pass" for check in inspection["checks"]))

    def test_selection_scorecard_passes_quality_and_safety_thresholds(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "scorecard"
            scorecard = _run_json(SCORECARD_SCRIPT, root)

            self.assertEqual(scorecard["status"], "pass")
            self.assertEqual(scorecard["summary"]["min_expected_source_recall"], 1.0)
            self.assertEqual(scorecard["summary"]["forbidden_hit_count"], 0)
            self.assertEqual(scorecard["safety"]["decision"], "block")
            self.assertFalse(scorecard["safety"]["allowed_to_write"])
            self.assertTrue(Path(scorecard["scorecard_path"]).exists())

    def test_hugging_face_space_scaffold_stays_toy_source_only(self) -> None:
        app_path = ROOT / "spaces" / "huggingface" / "v032-deterministic-demo" / "app.py"
        readme_path = ROOT / "spaces" / "huggingface" / "v032-deterministic-demo" / "README.md"
        app_text = app_path.read_text(encoding="utf-8")
        readme_text = readme_path.read_text(encoding="utf-8")

        self.assertIn("run_v032_deterministic_demo", app_text)
        self.assertIn("public_demo_summary", app_text)
        self.assertIn("Public receipt summary", app_text)
        self.assertIn("gr.Tabs", app_text)
        self.assertNotIn('"selection": summary["selection"]', app_text)
        self.assertNotIn('"checks": inspection["checks"]', app_text)
        self.assertNotIn("gr.File", app_text)
        self.assertNotIn("gr.UploadButton", app_text)
        self.assertIn("no user uploads", readme_text)
        self.assertIn("no model calls", readme_text)


def _run_json(script: Path, root: Path) -> dict:
    return _run_json_with_args(script, ["--root", str(root)])


def _run_json_with_args(script: Path, args: list[str]) -> dict:
    completed = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()
