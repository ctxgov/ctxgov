from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.config import load_config


class ConfigTests(unittest.TestCase):
    def test_example_config_loads(self) -> None:
        config = load_config(ROOT / "config" / "ctxvault.example.toml")

        self.assertEqual(config.vault.project, "ctxvault")
        self.assertEqual(config.vault.root, ".ctxvault")
        self.assertEqual(config.adapters.mode, "disabled")
        self.assertTrue(config.policy.require_backup_for_durable_writes)


if __name__ == "__main__":
    unittest.main()
