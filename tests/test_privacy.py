from __future__ import annotations

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.privacy import scan_privacy_files, scan_privacy_text


class PrivacyScanTests(unittest.TestCase):
    def test_scan_blocks_secret_material(self) -> None:
        report = scan_privacy_text(
            'OPENAI_API_KEY="sk-1234567890abcdefghijklmnop" and token "ghp_1234567890abcdefghijklmnopqrstuv"',
            source="unit-test",
        )

        payload = report.to_dict()
        self.assertEqual(payload["source"], "unit-test")
        self.assertEqual(payload["decision"], "block")
        self.assertEqual(payload["highest_severity"], "critical")
        self.assertEqual(payload["summary"]["total_findings"], 2)
        detectors = {finding["detector_id"] for finding in payload["findings"]}
        self.assertEqual(detectors, {"openai_api_key", "github_token"})

    def test_scan_reviews_direct_identifiers(self) -> None:
        report = scan_privacy_text(
            "Reach me at chris@example.com or +1 (415) 555-0101.",
            source="contact-card",
        )

        payload = report.to_dict()
        self.assertEqual(payload["decision"], "review")
        self.assertEqual(payload["highest_severity"], "medium")
        self.assertEqual(payload["summary"]["category_counts"]["direct_identifier"], 2)

    def test_scan_redacts_local_paths(self) -> None:
        report = scan_privacy_text(
            "Path: /Users/example/projects/ctxvault/docs/p1-local-context-os-architecture.md",
        )

        payload = report.to_dict()
        self.assertEqual(payload["decision"], "redact")
        self.assertEqual(payload["highest_severity"], "low")
        self.assertEqual(payload["summary"]["category_counts"]["local_identifier"], 1)

    def test_scan_files_blocks_text_attachment_with_secret(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "attachment.txt"
            path.write_text('OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"\n', encoding="utf-8")

            payload = scan_privacy_files([path], source="attachment-test")

        self.assertEqual(payload["decision"], "block")
        self.assertEqual(payload["highest_severity"], "critical")
        self.assertEqual(payload["summary"]["file_count"], 1)
        self.assertEqual(payload["files"][0]["content_scan_state"], "scanned")
        self.assertEqual(payload["files"][0]["decision"], "block")
        self.assertEqual(payload["files"][0]["summary"]["content_finding_count"], 1)

    def test_scan_files_reviews_binary_attachment(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "image.bin"
            path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00binary")

            payload = scan_privacy_files([path], source="attachment-test")

        self.assertEqual(payload["decision"], "review")
        self.assertEqual(payload["files"][0]["content_scan_state"], "skipped_binary")
        self.assertIn("manual review", " ".join(payload["files"][0]["reasons"]))


if __name__ == "__main__":
    unittest.main()
