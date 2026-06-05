from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicSurfaceHardeningTest(unittest.TestCase):
    def test_public_surface_hardening_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_public_surface_hardening.py"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["release"], "v0.6.11")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["issue_count"], 0)


if __name__ == "__main__":
    unittest.main()
