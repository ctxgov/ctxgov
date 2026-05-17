from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SUCCESS_RECEIPT = ROOT / "release" / "v0.6.2" / "testpypi-publishing-success-2026-05-17.json"
GITHUB_RELEASE_DRAFT = ROOT / "release" / "v0.6.2" / "ctxgov-github-release-draft.md"
ANNOUNCEMENT_DRAFT = ROOT / "release" / "v0.6.2" / "ctxgov-package-first-announcement-draft.md"
ROLLBACK_NOTE = ROOT / "release" / "v0.6.2" / "ctxgov-rollback-correction-note.md"


class V062TestPyPISuccessAndReleaseDraftsTests(unittest.TestCase):
    def test_testpypi_success_receipt_records_preview_publication_and_clean_install(self) -> None:
        receipt = json.loads(SUCCESS_RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema_id"], "ctxgov.v062-testpypi-publishing-success/v1")
        self.assertEqual(receipt["status"], "testpypi_published_and_clean_install_smoke_passed_pypi_blocked")
        self.assertEqual(receipt["selected_package_distribution"], "ctxgov")
        self.assertEqual(receipt["selected_package_version"], "0.6.2.post1")
        self.assertEqual(receipt["workflow_run"]["run_id"], 25985305251)
        self.assertEqual(receipt["workflow_run"]["conclusion"], "success")
        self.assertEqual(receipt["testpypi_project"]["json_api_status"], 200)
        self.assertEqual(receipt["testpypi_project"]["artifacts"][0]["filename"], "ctxgov-0.6.2.post1-py3-none-any.whl")
        self.assertEqual(receipt["clean_install_smoke"]["install_result"], "success")
        self.assertEqual(receipt["clean_install_smoke"]["import_check"]["import_ctxgov"], "success")
        self.assertIsNone(receipt["clean_install_smoke"]["import_check"]["find_spec_ctxvault"])
        self.assertEqual(receipt["clean_install_smoke"]["doctor_sample_smoke"]["exit_code"], 0)
        self.assertEqual(receipt["clean_install_smoke"]["missing_path_smoke"]["exit_code"], 1)

    def test_success_receipt_blocks_official_publication_side_effects(self) -> None:
        receipt = json.loads(SUCCESS_RECEIPT.read_text(encoding="utf-8"))
        side_effects = receipt["side_effects"]

        self.assertTrue(side_effects["testpypi_upload_completed"])
        self.assertTrue(side_effects["testpypi_package_available_verified"])
        self.assertTrue(side_effects["testpypi_install_smoke_passed"])
        for blocked in [
            "pypi_upload_performed",
            "github_release_created",
            "github_release_updated",
            "package_tag_created",
            "package_first_announcement_published",
            "social_post_performed",
            "technical_article_published",
            "maintainer_outreach_performed",
            "github_issue_or_pull_request_outreach_performed",
        ]:
            self.assertFalse(side_effects[blocked], blocked)

    def test_release_and_announcement_drafts_are_blocked_and_current_scope_only(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [GITHUB_RELEASE_DRAFT, ANNOUNCEMENT_DRAFT, ROLLBACK_NOTE]
        )
        normalized = " ".join(combined.split()).lower()

        self.assertIn("blocked draft", normalized)
        self.assertIn("do not publish", normalized)
        self.assertIn("ctxgov==0.6.2.post1", combined)
        self.assertIn("ctxgov doctor --path", combined)
        self.assertIn("does not modify scanned source files", normalized)
        self.assertIn("official pypi publication has not run", normalized)
        self.assertIn("maintainer outreach remains blocked", normalized)
        for forbidden in [
            "guarantees security",
            "benchmark result achieved",
            "performance improvement achieved",
            "universally compatible",
            "stable protocol status achieved",
            "automatically remediates",
            "maintainers endorse",
            "will ship next",
        ]:
            self.assertNotIn(forbidden, normalized)


if __name__ == "__main__":
    unittest.main()
