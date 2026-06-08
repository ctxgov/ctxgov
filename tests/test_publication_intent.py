from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))


class PublicationIntentTest(unittest.TestCase):
    def test_publication_intent_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_publication_intent.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["release"], "v0.6.13")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issue_count"], 0)

    def test_publication_intent_rejects_deferred_targets(self) -> None:
        from check_publication_intent import validate_publication_intent

        intent = json.loads((ROOT / "release" / "v0.6.13" / "publication-intent.json").read_text(encoding="utf-8"))
        intent["included_targets"].append("linkedin_x_manual_post")
        issues = validate_publication_intent(intent)

        self.assertTrue(any(issue["kind"] == "included_targets" for issue in issues))
        self.assertTrue(any(issue["kind"] == "forbidden_included_target" for issue in issues))


if __name__ == "__main__":
    unittest.main()
