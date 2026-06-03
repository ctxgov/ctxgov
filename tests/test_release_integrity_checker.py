from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from check_release_integrity import check_release_integrity


class ReleaseIntegrityCheckerTests(unittest.TestCase):
    def test_current_public_surface_passes_release_integrity_check(self) -> None:
        report = check_release_integrity(ROOT)

        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issue_count"], 0)
        self.assertEqual(report["expected"]["ctxgov_release"], "v0.6.6")
        self.assertEqual(report["expected"]["companion_release"], "v0.6.0")
        self.assertIn("README.md", report["checked_paths"])
        self.assertIn("docs/index.html", report["checked_paths"])

    def test_flags_version_drift_and_unbounded_public_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for relative in [
                "README.md",
                "docs/index.html",
                "docs/public-positioning.md",
                "docs/project-page-and-demo-2026-06-03.md",
                "docs/research-engineering-hiring-packet.md",
                "docs/linkedin-and-outreach-pack-2026-06-03.md",
                "release/v0.6.6/RELEASE_NOTES.md",
                "release/v0.6.6/github-release.md",
            ]:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "\n".join(
                        [
                            "CtxGov provides a security guarantee for agent runs.",
                            "https://github.com/ctxgov/ctxgov/releases/tag/v0.6.6",
                            "https://github.com/ctxgov/agent-context-evals/releases/tag/v0.3.0",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )

            report = check_release_integrity(root)

        issue_types = {issue["type"] for issue in report["issues"]}
        self.assertEqual(report["status"], "fail")
        self.assertIn("legacy_companion_release_link", issue_types)
        self.assertIn("missing_expected_companion_release_link", issue_types)
        self.assertIn("unsupported_public_claim", issue_types)

    def test_report_is_json_serializable(self) -> None:
        report = check_release_integrity(ROOT)

        self.assertIsInstance(json.dumps(report, sort_keys=True), str)


if __name__ == "__main__":
    unittest.main()
