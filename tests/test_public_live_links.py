from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


class PublicLiveLinksTest(unittest.TestCase):
    def test_check_targets_passes_with_fake_fetcher(self) -> None:
        from check_public_live_links import Target, check_targets

        targets = [
            Target("pages", "https://example.test/pages", ("CtxGov", "Reviewer Mode")),
            Target("release", "https://example.test/release", ("v0.6.12", "Live Link Verifier")),
        ]

        def fake_fetcher(url: str, timeout: float) -> tuple[int, str]:
            self.assertGreater(timeout, 0)
            if url.endswith("/pages"):
                return 200, "CtxGov Reviewer Mode"
            return 200, "CtxGov v0.6.12 Live Link Verifier"

        report = check_targets(targets, timeout=1.0, fetcher=fake_fetcher)
        self.assertEqual(report["status"], "pass")
        self.assertFalse(report["claim_boundary"]["provider_model_call"])

    def test_v0613_targets_require_auto_publish_research_phrase(self) -> None:
        from check_public_live_links import build_targets

        targets = build_targets("v0.6.13-auto-publish-research")
        current_release = next(target for target in targets if target.name == "ctxgov_current_release")

        self.assertEqual(current_release.required_phrases, ("v0.6.13-auto-publish-research", "Auto-Publish Research"))

    def test_v0612_targets_keep_live_link_verifier_phrase(self) -> None:
        from check_public_live_links import build_targets

        targets = build_targets("v0.6.12")
        current_release = next(target for target in targets if target.name == "ctxgov_current_release")

        self.assertEqual(current_release.required_phrases, ("v0.6.12", "Live Link Verifier"))

    def test_check_targets_fails_missing_phrase_without_network(self) -> None:
        from check_public_live_links import Target, check_targets

        report = check_targets(
            [Target("release", "https://example.test/release", ("v0.6.13-auto-publish-research", "Auto-Publish Research"))],
            timeout=1.0,
            fetcher=lambda _url, _timeout: (200, "CtxGov v0.6.13-auto-publish-research"),
        )
        self.assertEqual(report["status"], "fail")
        self.assertIn("missing_required_phrase", report["checks"][0]["issue"])

    def test_cli_writes_json_output_with_fake_release_tag_help_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "live-links.json"
            result = subprocess.run(
                [sys.executable, "scripts/check_public_live_links.py", "--help"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("--json-output", result.stdout)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
