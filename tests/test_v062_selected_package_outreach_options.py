from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-python.yml"
SELECTED_OPTIONS = ROOT / "release" / "v0.6.2" / "package-outreach-selected-options-2026-05-16.json"


class V062SelectedPackageOutreachOptionsTests(unittest.TestCase):
    def test_selected_options_match_owner_choices_and_keep_external_actions_blocked(self) -> None:
        receipt = json.loads(SELECTED_OPTIONS.read_text(encoding="utf-8"))
        selected = {item["id"]: item["selected_option"] for item in receipt["selected_options"]}

        self.assertEqual(receipt["selected_package_version"], "0.6.2.post1")
        self.assertEqual(selected["public-preflight-push"], "B")
        self.assertEqual(selected["package-registry-target"], "A")
        self.assertEqual(selected["package-publishing-mechanism"], "A")
        self.assertEqual(selected["external-outreach-channel"], "B")
        self.assertEqual(selected["maintainer-outreach"], "A")

        blocked = receipt["external_actions_blocked"]
        for field in [
            "public_preflight_commit_pushed",
            "github_release_updated",
            "git_tag_moved",
            "testpypi_upload_performed",
            "pypi_upload_performed",
            "trusted_publisher_configured_on_pypi",
            "github_actions_workflow_run_started",
            "package_first_announcement_published",
            "maintainer_outreach_performed",
        ]:
            self.assertFalse(blocked[field], field)

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

        self.assertIn("Configure TestPyPI trusted publisher", body)
        self.assertIn("Run the workflow manually with registry=testpypi", body)
        self.assertIn("v0.6.2.post1", body)
        self.assertIn("Only then approve package-first announcement", body)
        self.assertNotIn("has been published to " + "PyPI", body)
        self.assertNotIn("maintainer outreach is " + "allowed", body)


if __name__ == "__main__":
    unittest.main()
