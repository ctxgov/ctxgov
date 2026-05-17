from __future__ import annotations

import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.backup import emit_backup_bundle


class BackupBundleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name) / "workspace"
        self.repo_root.mkdir()
        (self.repo_root / "README.md").write_text("# Demo\n", encoding="utf-8")
        (self.repo_root / "module.yaml").write_text("metadata:\n  name: demo\n", encoding="utf-8")
        (self.repo_root / "src").mkdir()
        (self.repo_root / "src" / "app.py").write_text("print('demo')\n", encoding="utf-8")
        (self.repo_root / "tests").mkdir()
        (self.repo_root / "tests" / "test_app.py").write_text("assert True\n", encoding="utf-8")
        self.output_dir = self.repo_root / "artifacts"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_emit_ctxvault_backup_bundle_writes_archive_and_receipt(self) -> None:
        output_path = self.output_dir / "ctxvault-backup.json"

        result = emit_backup_bundle(
            root=self.repo_root,
            output_path=output_path,
            receipt_format="ctxvault",
            scope_kind="project",
            scope_value="demo",
            max_age_hours=24,
            restore_tested=False,
            notes=None,
        )

        receipt = json.loads(output_path.read_text(encoding="utf-8"))
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))

        self.assertEqual(receipt["status"], "ok")
        self.assertEqual(receipt["mode"], "preflight")
        self.assertEqual(result["ctxvault_receipt_path"], str(output_path.resolve()))
        self.assertTrue(Path(result["archive_path"]).exists())
        self.assertEqual(manifest["summary"]["file_count"], result["file_count"])

        with tarfile.open(result["archive_path"], "r:gz") as archive:
            names = archive.getnames()

        self.assertIn("README.md", names)
        self.assertIn("src/app.py", names)

    def test_emit_plan_ledger_receipt_also_persists_ctxvault_receipt(self) -> None:
        output_path = self.output_dir / "latest-backup-check.json"

        result = emit_backup_bundle(
            root=self.repo_root,
            output_path=output_path,
            receipt_format="plan-ledger",
            scope_kind="project",
            scope_value="demo",
            max_age_hours=24,
            restore_tested=False,
            notes=None,
            plan_id="p1",
            target="plans/p1.toml",
        )

        receipt = json.loads(output_path.read_text(encoding="utf-8"))
        ctxvault_receipt = json.loads(Path(result["ctxvault_receipt_path"]).read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema_version"], "plan-ledger.backup-receipt/v1")
        self.assertEqual(receipt["status"], "fresh")
        self.assertTrue(receipt["recoverable"])
        self.assertEqual(ctxvault_receipt["status"], "ok")
        self.assertIn("manifest://ctxvault/", result["ctxvault_receipt"]["artifact_refs"][2])


if __name__ == "__main__":
    unittest.main()
