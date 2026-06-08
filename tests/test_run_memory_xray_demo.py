from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunMemoryXrayDemoTest(unittest.TestCase):
    def test_demo_writes_before_after_markdown_json_and_html(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "memory-xray-demo-report.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_memory_xray_demo.py",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["example_count"], 5)
            self.assertTrue(Path(summary["markdown"]).exists())
            self.assertTrue(Path(summary["json"]).exists())
            self.assertTrue(Path(summary["html"]).exists())

            markdown = output.read_text(encoding="utf-8")
            self.assertIn("## Before", markdown)
            self.assertIn("## After", markdown)
            self.assertIn("No public benchmark claim", markdown)
            self.assertIn("not a Memory X-Ray CLI beta", markdown)

            report = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "ctxgov.public_memory_xray_demo.v0")
            self.assertFalse(report["claim_boundary"]["provider_model_call"])
            self.assertFalse(report["claim_boundary"]["arbitrary_repo_scan"])
            self.assertEqual(len(report["before"]), 5)
            self.assertEqual(len(report["after"]["findings"]), 5)

    def test_checked_in_demo_report_is_current(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_memory_xray_demo.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        markdown = (ROOT / "docs" / "memory-xray-demo-report.md").read_text(encoding="utf-8")
        html = (ROOT / "docs" / "memory-xray-demo-report.html").read_text(encoding="utf-8")
        self.assertIn("Memory X-Ray Demo Report", markdown)
        self.assertIn("Memory X-Ray Demo Report", html)
        self.assertIn("Before", html)
        self.assertIn("After", html)


if __name__ == "__main__":
    unittest.main()
