from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
README = ROOT / "README.md"
RELEASE_NOTES = ROOT / "release" / "v0.6.2" / "RELEASE_NOTES.md"
GITHUB_RELEASE = ROOT / "release" / "v0.6.2" / "github-release.md"
IDENTITY_RECEIPT = ROOT / "release" / "v0.6.2" / "ctxgov-package-identity-hardening-2026-05-17.json"


class CtxGovPackageIdentityTests(unittest.TestCase):
    def test_python_package_identity_uses_ctxgov_not_ctxvault(self) -> None:
        pyproject = PYPROJECT.read_text(encoding="utf-8")

        self.assertIn('name = "ctxgov"', pyproject)
        self.assertIn('ctxgov = "ctxgov.cli:main"', pyproject)
        self.assertIn('Repository = "https://github.com/ctxgov/ctxgov"', pyproject)
        self.assertFalse((ROOT / "src" / "ctxvault").exists())
        self.assertTrue((ROOT / "src" / "ctxgov" / "cli.py").exists())
        self.assertNotIn('ctxvault = "ctxvault.cli:main"', pyproject)

    def test_current_install_and_run_copy_uses_ctxgov_command_and_output_namespace(self) -> None:
        current_copy = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                RELEASE_NOTES.read_text(encoding="utf-8"),
                GITHUB_RELEASE.read_text(encoding="utf-8"),
            ]
        )

        self.assertIn("python3 -m ctxgov.cli doctor", current_copy)
        self.assertIn("--output .ctxgov/health", current_copy)
        self.assertNotIn("python3 -m ctxvault.cli doctor", current_copy)
        self.assertNotIn("pip install " + "ctxvault", current_copy)

    def test_identity_receipt_blocks_registry_and_outreach_until_account_path_is_fixed(self) -> None:
        receipt = json.loads(IDENTITY_RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema_id"], "ctxgov.v062-package-identity-hardening/v1")
        self.assertEqual(receipt["status"], "ctxgov_package_identity_prepared_pypi_account_blocked")
        self.assertEqual(receipt["package_identity"]["distribution_name"], "ctxgov")
        self.assertEqual(receipt["package_identity"]["console_script"], "ctxgov")
        self.assertEqual(receipt["package_identity"]["retired_distribution_name"], "ctxvault")
        self.assertFalse(receipt["pypi_account_state"]["pypi_login_available"])
        self.assertTrue(receipt["pypi_account_state"]["testpypi_login_available"])
        self.assertIn("Create or recover a working account on https://pypi.org/.", receipt["blocked_until_external_configuration"])
        self.assertFalse(receipt["side_effects"]["pypi_upload_performed"])
        self.assertFalse(receipt["side_effects"]["testpypi_upload_performed"])
        self.assertFalse(receipt["side_effects"]["package_first_announcement_published"])


if __name__ == "__main__":
    unittest.main()
