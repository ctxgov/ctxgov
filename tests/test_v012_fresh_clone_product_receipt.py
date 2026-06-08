from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_receipt_generator():
    path = ROOT / "scripts" / "run_v012_fresh_clone_product_receipt.py"
    spec = importlib.util.spec_from_file_location("ctxgov_v012_receipt_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_local(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *[str(arg) for arg in args]],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class V012FreshCloneProductReceiptTest(unittest.TestCase):
    def test_v012_fresh_clone_product_receipt_gate_passes(self) -> None:
        result = run_local("scripts/check_v012_fresh_clone_product_receipt.py")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["status"], "pass_fresh_clone_product_receipt_ready")
        self.assertTrue(report["publication_allowed"])
        self.assertFalse(report["public_benchmark_claim_allowed"])
        self.assertFalse(report["security_claim_allowed"])
        self.assertFalse(report["adoption_claim_allowed"])
        self.assertFalse(report["provider_model_compatibility_claim_allowed"])
        self.assertFalse(report["package_release_claim_allowed"])

    def test_v012_receipt_records_report_sha_from_public_fresh_clone(self) -> None:
        receipt_path = ROOT / "release" / "v0.12.0" / "fresh-clone-product-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema"], "ctxgov.fresh_clone_product_receipt.v0")
        self.assertEqual(receipt["status"], "pass_fresh_clone_product_receipt")
        self.assertEqual(receipt["source_repo"], "https://github.com/ctxgov/ctxgov.git")
        self.assertTrue(receipt["fresh_clone"])
        self.assertFalse(receipt["worktree_reused"])
        self.assertEqual(receipt["product_command"], "python3 scripts/run_memory_xray_demo.py")
        self.assertEqual(receipt["report"]["path"], "docs/memory-xray-demo-report.md")
        self.assertEqual(receipt["report"]["example_count"], 5)
        self.assertRegex(receipt["report"]["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(receipt["report"]["json_schema"], "ctxgov.public_memory_xray_demo.v0")

        checks = {item["command"]: item for item in receipt["checks"]}
        self.assertIn("python3 scripts/run_memory_xray_demo.py", checks)
        self.assertIn("python3 scripts/check_public_surface_hardening.py", checks)
        self.assertTrue(all(item["returncode"] == 0 for item in checks.values()))

        text = receipt_path.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", text)
        self.assertNotIn("/private/tmp", text)
        self.assertNotIn("BEGIN PRIVATE KEY", text)

    def test_report_ui_and_try_page_are_readable_and_bounded(self) -> None:
        report_html = (ROOT / "docs" / "memory-xray-demo-report.html").read_text(encoding="utf-8")
        self.assertIn('<main class="report-shell">', report_html)
        self.assertIn("finding-card", report_html)
        self.assertIn("Before Context", report_html)
        self.assertIn("After Report", report_html)
        self.assertNotIn("<pre># Memory X-Ray Demo Report", report_html)

        try_page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")
        for phrase in [
            "Try in 5 minutes",
            "Clone",
            "Run",
            "Read report",
            "Optional eval",
            "No public benchmark claim",
            "No provider/model call",
        ]:
            self.assertIn(phrase, try_page)
        self.assertIn("python3 scripts/run_memory_xray_demo.py", try_page)
        self.assertIn("memory-xray-demo-report.html", try_page)
        self.assertIn("agent-context-evals/releases/tag/v0.11.0", try_page)

        index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("try-in-5-minutes.html", index)
        self.assertIn("v0.12.0", index)

    def test_receipt_generator_can_report_output_path_outside_repo(self) -> None:
        module = load_receipt_generator()

        self.assertEqual(
            module.display_output_path(Path("/tmp/ctxgov-v012-post-release.json")),
            "/tmp/ctxgov-v012-post-release.json",
        )


if __name__ == "__main__":
    unittest.main()
