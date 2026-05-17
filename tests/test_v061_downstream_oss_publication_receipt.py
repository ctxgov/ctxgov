from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = (
    ROOT
    / "release"
    / "v0.6.1"
    / "publication"
    / "downstream-oss-usability-publication-receipt-2026-05-16.json"
)


class V061DownstreamOssPublicationReceiptTests(unittest.TestCase):
    def test_receipt_records_publication_scope_verification_and_rollback(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(
            receipt["schema_id"],
            "ctxvault.v061-downstream-oss-usability-publication-receipt/v1",
        )
        self.assertEqual(receipt["public_repo"]["repo"], "ctxvault/ctxvault")
        self.assertEqual(
            receipt["public_repo"]["base_public_main_before_publication"],
            "9d064232693af72e2ef1c9661d2eb9825f5a5072",
        )
        self.assertEqual(
            receipt["public_repo"]["published_content_commit"],
            "ec07824ba1fdfa7798b8c44dc2c7d83a689b0459",
        )
        for path in receipt["published_scope"]:
            current_path = ROOT / path
            if not current_path.exists() and path.startswith("src/ctxvault/"):
                current_path = ROOT / path.replace("src/ctxvault/", "src/ctxgov/", 1)
            self.assertTrue(current_path.exists(), path)
        for key, url in receipt["published_urls"].items():
            with self.subTest(key=key):
                self.assertTrue(url.startswith("https://github.com/ctxvault/ctxvault/blob/main/"), url)
        self.assertEqual(
            receipt["rollback"]["rollback_command"],
            "git revert ec07824ba1fdfa7798b8c44dc2c7d83a689b0459",
        )
        self.assertEqual(receipt["final_assessment"]["remaining_unconstrained_uncertainty_count"], 0)

    def test_receipt_converts_uncertainty_to_test_audit_rollback_constraints(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(receipt["remaining_uncertainty_to_constraints"]), 4)
        for item in receipt["remaining_uncertainty_to_constraints"]:
            for key in ["uncertainty", "constraint", "test", "audit", "rollback"]:
                self.assertTrue(item[key], (item, key))
        for key in [
            "template_validation",
            "focused_tests",
            "diff_check",
            "leak_scan",
            "pages_render_check",
            "github_head_check",
            "url_verification",
        ]:
            self.assertIn(key, receipt["verification"])

    def test_receipt_boundary_blocks_unapproved_side_effects(self) -> None:
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        boundary = receipt["side_effect_boundary"]

        self.assertTrue(boundary["public_copy_published"])
        self.assertTrue(boundary["github_public_repo_push_performed"])
        self.assertTrue(boundary["remote_target_fetch_code_path_added"])
        for blocked in [
            "github_pages_build_or_cdn_forced",
            "remote_target_fetch_executed",
            "target_fetch_or_clone_performed",
            "target_repo_cloned",
            "target_file_written",
            "runtime_or_adapter_executed",
            "mcp_server_started",
            "provider_or_model_call_performed",
            "package_or_tool_install_performed",
            "memory_promotion_performed",
            "github_action_created",
            "hosted_bot_created",
            "maintainer_outreach_performed",
            "public_paper_published",
            "stable_protocol_claim",
            "target_issue_or_pr_created",
        ]:
            self.assertFalse(boundary[blocked], blocked)


if __name__ == "__main__":
    unittest.main()
