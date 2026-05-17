from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-python.yml"
SELECTED_OPTIONS = ROOT / "release" / "v0.6.2" / "package-outreach-selected-options-2026-05-16.json"
TESTPYPI_ATTEMPT = ROOT / "release" / "v0.6.2" / "testpypi-publishing-attempt-2026-05-17.json"
CTXGOV_IDENTITY = ROOT / "release" / "v0.6.2" / "ctxgov-package-identity-hardening-2026-05-17.json"
TESTPYPI_SUCCESS = ROOT / "release" / "v0.6.2" / "testpypi-publishing-success-2026-05-17.json"


class V062SelectedPackageOutreachOptionsTests(unittest.TestCase):
    def test_selected_options_match_owner_choices_and_current_external_state(self) -> None:
        receipt = json.loads(SELECTED_OPTIONS.read_text(encoding="utf-8"))
        selected = {item["id"]: item["selected_option"] for item in receipt["selected_options"]}

        self.assertEqual(
            receipt["status"],
            "testpypi_published_install_smoke_passed_pypi_blocked_release_copy_prepared",
        )
        self.assertEqual(receipt["selected_package_distribution"], "ctxgov")
        self.assertEqual(receipt["selected_package_version"], "0.6.2.post1")
        self.assertEqual(
            receipt["latest_execution_receipt"],
            "release/v0.6.2/testpypi-publishing-success-2026-05-17.json",
        )
        self.assertEqual(selected["public-preflight-push"], "B")
        self.assertEqual(selected["package-registry-target"], "A")
        self.assertEqual(selected["package-publishing-mechanism"], "A")
        self.assertEqual(selected["external-outreach-channel"], "B")
        self.assertEqual(selected["maintainer-outreach"], "A")

        state = receipt["external_actions_state"]
        self.assertTrue(state["public_preflight_commit_pushed"])
        self.assertTrue(state["ctxgov_github_org_created"])
        self.assertTrue(state["ctxgov_github_repo_created"])
        self.assertTrue(state["ctxgov_package_identity_prepared"])
        self.assertTrue(state["testpypi_workflow_run_started"])
        self.assertTrue(state["testpypi_upload_completed"])
        self.assertTrue(state["testpypi_package_available_verified"])
        self.assertTrue(state["testpypi_install_smoke_passed"])
        self.assertFalse(state["pypi_account_access_available"])
        for field in [
            "github_release_updated",
            "git_tag_moved",
            "pypi_upload_performed",
            "trusted_publisher_configured_on_pypi",
            "package_first_announcement_published",
            "maintainer_outreach_performed",
        ]:
            self.assertFalse(state[field], field)
        self.assertTrue(state["trusted_publisher_configured_on_testpypi"])

    def test_trusted_publishing_workflow_is_manual_oidc_and_registry_gated(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertNotIn("release:", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("environment: testpypi", workflow)
        self.assertIn("environment: pypi", workflow)
        self.assertIn("repository-url: https://test.pypi.org/legacy/", workflow)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", workflow)
        self.assertIn("inputs.registry == 'testpypi'", workflow)
        self.assertIn("inputs.registry == 'pypi' && startsWith(github.ref, 'refs/tags/v')", workflow)

    def test_receipt_names_remaining_tasks_without_claiming_publication(self) -> None:
        receipt = json.loads(SELECTED_OPTIONS.read_text(encoding="utf-8"))
        body = json.dumps(receipt, sort_keys=True)

        self.assertIn("clean TestPyPI install smoke passed", body)
        self.assertIn("Configure PyPI pending publisher for project ctxgov", body)
        self.assertIn("Wait for PyPI ctxgov organization approval", body)
        self.assertIn("v0.6.2.post1", body)
        self.assertIn("Only then publish GitHub Release and approve package-first announcement", body)
        self.assertNotIn("has been published to " + "PyPI", body)
        self.assertNotIn("maintainer outreach is " + "allowed", body)

    def test_latest_execution_receipt_exists(self) -> None:
        receipt = json.loads(SELECTED_OPTIONS.read_text(encoding="utf-8"))
        latest = ROOT / receipt["latest_execution_receipt"]

        self.assertEqual(latest, TESTPYPI_SUCCESS)
        self.assertTrue(latest.exists())
        self.assertTrue(CTXGOV_IDENTITY.exists())
        self.assertTrue(TESTPYPI_ATTEMPT.exists())


if __name__ == "__main__":
    unittest.main()
