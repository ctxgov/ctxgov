from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "release" / "v0.6.2" / "testpypi-publishing-attempt-2026-05-17.json"


class V062TestPyPIPublishingAttemptTests(unittest.TestCase):
    def test_attempt_receipt_records_blocked_trusted_publishing_without_publication(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema_id"], "ctxvault.v062-testpypi-publishing-attempt/v1")
        self.assertEqual(receipt["selected_package_version"], "0.6.2.post1")
        self.assertEqual(receipt["status"], "blocked_by_missing_testpypi_trusted_publisher")
        self.assertEqual(receipt["workflow_run"]["run_id"], 25983008724)
        self.assertEqual(receipt["workflow_run"]["conclusion"], "failure")
        self.assertEqual(
            receipt["public_source_state"]["head_sha"],
            "c350bb223308237d3aa9bf1a8f2194da5859a742",
        )
        self.assertFalse(receipt["public_source_state"]["github_release_tag_moved"])
        self.assertFalse(receipt["public_source_state"]["package_tag_created"])

        jobs = {job["name"]: job for job in receipt["jobs"]}
        self.assertEqual(jobs["Build and check artifacts"]["conclusion"], "success")
        self.assertEqual(jobs["Publish to TestPyPI"]["conclusion"], "failure")
        self.assertEqual(jobs["Publish to TestPyPI"]["failure_code"], "invalid-publisher")
        self.assertFalse(jobs["Publish to TestPyPI"]["registry_state_changed"])
        self.assertEqual(jobs["Publish to PyPI"]["conclusion"], "skipped")

    def test_observed_claims_are_enough_to_configure_the_next_gate(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        claims = receipt["trusted_publisher_claims_observed"]

        self.assertEqual(claims["repository"], "ctxvault/ctxvault")
        self.assertEqual(claims["repository_owner"], "ctxvault")
        self.assertEqual(claims["environment"], "testpypi")
        self.assertEqual(claims["ref"], "refs/heads/main")
        self.assertEqual(
            claims["workflow_ref"],
            "ctxvault/ctxvault/.github/workflows/publish-python.yml@refs/heads/main",
        )

    def test_receipt_blocks_public_install_and_outreach_claims(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        side_effects = receipt["side_effects"]

        self.assertTrue(side_effects["github_main_pushed"])
        self.assertTrue(side_effects["workflow_run_started"])
        self.assertTrue(side_effects["build_artifacts_created_in_github_actions"])
        for field in [
            "testpypi_upload_completed",
            "testpypi_package_available_verified",
            "pypi_upload_performed",
            "package_first_announcement_published",
            "technical_article_published",
            "maintainer_outreach_performed",
        ]:
            self.assertFalse(side_effects[field], field)

        body = json.dumps(receipt, sort_keys=True)
        self.assertIn("Verify TestPyPI install in a clean environment", body)
        self.assertIn("Create and push v0.6.2.post1 package tag", body)
        self.assertNotIn("available on " + "PyPI", body)
        self.assertNotIn("pip install " + "ctxvault", body)


if __name__ == "__main__":
    unittest.main()
