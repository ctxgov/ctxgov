from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.layout import default_layout


class LayoutTests(unittest.TestCase):
    def test_default_layout_is_repo_relative(self) -> None:
        layout = default_layout(Path("/tmp/ctxvault-repo"))

        self.assertEqual(layout.vault_root, Path("/tmp/ctxvault-repo/.ctxvault"))
        self.assertEqual(layout.objects_dir, Path("/tmp/ctxvault-repo/.ctxvault/objects"))
        self.assertEqual(layout.sqlite_path, Path("/tmp/ctxvault-repo/.ctxvault/indexes/ctxvault.sqlite3"))


if __name__ == "__main__":
    unittest.main()
