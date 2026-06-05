from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicMemoryXrayPreviewTest(unittest.TestCase):
    def test_renderer_writes_markdown_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "ctxgov-memory-xray-preview.md"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/render_public_memory_xray_preview.py",
                    "--input",
                    "release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json",
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
            self.assertTrue(output.exists())
            self.assertTrue(output.with_suffix(".json").exists())
            markdown = output.read_text(encoding="utf-8")
            self.assertIn("not a Memory X-Ray CLI beta", markdown)
            self.assertIn("No public benchmark claim", markdown)
            report = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "ctxgov.public_memory_xray_preview.v0")
            self.assertEqual(report["example_count"], 5)
            self.assertFalse(report["claim_boundary"]["provider_model_call"])
            self.assertFalse(report["claim_boundary"]["arbitrary_repo_scan"])


if __name__ == "__main__":
    unittest.main()
