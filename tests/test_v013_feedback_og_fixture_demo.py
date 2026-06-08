from __future__ import annotations

import struct
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def png_size(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path} is not a PNG")
    return struct.unpack(">II", data[16:24])


class V013FeedbackOgFixtureDemoTest(unittest.TestCase):
    def test_try_page_has_short_copy_paste_feedback_form(self) -> None:
        page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")

        self.assertIn("Copy/paste feedback", page)
        self.assertIn("GitHub issue #22", page)
        self.assertIn("https://github.com/ctxgov/agent-context-evals/issues/22", page)
        for phrase in [
            "Run path clear? yes/no:",
            "Report useful? yes/no:",
            "Missing field:",
            "Integration shape:",
            "Confusing wording:",
        ]:
            self.assertIn(phrase, page)
        self.assertIn("No public benchmark claim", page)
        self.assertIn("No adoption claim", page)

    def test_tiny_fixture_demo_shows_file_input_to_report_without_scanner_claim(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_tiny_fixture_memory_xray_demo.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        fixture = ROOT / "fixtures" / "memory_xray_tiny_repo"
        self.assertTrue((fixture / "README.md").exists())
        self.assertTrue((fixture / "AGENTS.md").exists())
        self.assertTrue((fixture / "terminal.log").exists())
        self.assertTrue((fixture / "memory-summary.md").exists())

        demo = ROOT / "docs" / "tiny-fixture-memory-xray-demo.html"
        html = demo.read_text(encoding="utf-8")
        for phrase in [
            "Tiny fixture repo demo",
            "File input",
            "Memory X-Ray report",
            "unsupported_claim",
            "unsafe_instruction",
            "terminal_failure",
            "memory_claim_drift",
            "not an arbitrary repo scanner",
        ]:
            self.assertIn(phrase, html)

        try_page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")
        index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        self.assertIn("tiny-fixture-memory-xray-demo.html", try_page)
        self.assertIn("tiny-fixture-memory-xray-demo.html", index)

    def test_try_page_has_local_tiny_fixture_run_entry(self) -> None:
        page = (ROOT / "docs" / "try-in-5-minutes.html").read_text(encoding="utf-8")

        for phrase in [
            "Run fixed fixture",
            "python3 scripts/run_tiny_fixture_memory_xray_demo.py",
            "docs/tiny-fixture-memory-xray-demo.html",
            "docs/tiny-fixture-memory-xray-demo.json",
            "fixed public-safe fixture only",
            "not an arbitrary repo scanner",
        ]:
            self.assertIn(phrase, page)

    def test_og_image_and_metadata_are_report_ui_specific(self) -> None:
        og = ROOT / "docs" / "og.png"
        self.assertEqual(png_size(og), (1200, 630))
        self.assertGreater(og.stat().st_size, 50_000)

        for path in [
            ROOT / "docs" / "index.html",
            ROOT / "docs" / "memory-xray-demo-report.html",
            ROOT / "docs" / "try-in-5-minutes.html",
        ]:
            text = path.read_text(encoding="utf-8")
            self.assertIn('<meta property="og:image" content="https://ctxgov.github.io/ctxgov/og.png" />', text)
            self.assertIn('<meta name="twitter:image" content="https://ctxgov.github.io/ctxgov/og.png" />', text)

    def test_public_surface_gate_includes_feedback_og_and_fixture_demo(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_public_surface_hardening.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
