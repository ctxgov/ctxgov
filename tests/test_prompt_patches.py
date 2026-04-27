from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.policy import CtxVaultPolicy


class PromptPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))
        self.prompt = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text())
        self.patch = json.loads((ROOT / "fixtures" / "core" / "prompt-patch.json").read_text())
        self.policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text())
        self.backup = CtxVaultPolicy.freshen_backup_receipt(
            json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text())
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_approved_prompt_patch_updates_prompt_asset_and_receipt(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)
        self.vault.store_core_object("PromptPatch", self.patch)

        patches = self.vault.list_prompt_patches(
            scope=("project", "ctxvault"),
            proposal_state="proposed",
            prompt_asset_id="prompt_schema_designer_v1",
            limit=10,
        )
        self.assertEqual([patch.object_id for patch in patches], [self.patch["id"]])

        eval_result = self.vault.run_prompt_eval(
            "prompt_patch",
            self.patch["id"],
            dataset_ref="eval://unit/prompt-patch-review",
            assert_contains=["migration notes", "source-grounded rationale"],
            assert_not_contains=["requires remote llm"],
        )

        result = self.vault.review_prompt_patch(
            self.patch["id"],
            decision="approved",
            reviewer="unit_test",
            notes="Promote the patch into the active prompt.",
            policy_payload=self.policy,
            backup_receipt=self.backup,
        )

        self.assertEqual(result["patch"]["proposal_state"], "merged")
        self.assertEqual(result["prompt"]["id"], "prompt_schema_designer_v1")
        self.assertEqual(result["prompt"]["eval_status"], "pending")
        self.assertIn("migration notes", result["prompt"]["instruction"])
        self.assertIn("prompt-patch://ppatch_20260420_schema_designer_instruction_refresh", result["prompt"]["derived_from"])

        resolved = self.vault.resolve_prompt("prompt_schema_designer_v1")
        self.assertIn("source-grounded rationale", resolved.instruction)

        receipt_path = Path(result["review_receipt_path"])
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["decision"], "approved")
        self.assertEqual(receipt["result_ref"], "prompt://prompt_schema_designer_v1")
        self.assertIn(eval_result["eval_ref"], receipt["eval_refs_before_review"])
        self.assertIn("prompt-patch://ppatch_20260420_schema_designer_instruction_refresh", receipt["lineage"]["derived_from_after"])

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        patch_row = connection.execute(
            "SELECT proposal_state FROM prompt_patches WHERE object_id = ?",
            (self.patch["id"],),
        ).fetchone()
        connection.close()
        self.assertEqual(patch_row, ("merged",))

    def test_rejected_prompt_patch_keeps_prompt_unchanged(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)
        rejected_patch = dict(self.patch)
        rejected_patch["id"] = "ppatch_20260420_schema_designer_reject"
        rejected_patch["rationale"] = "Rejected patch for coverage."
        self.vault.store_core_object("PromptPatch", rejected_patch)

        result = self.vault.review_prompt_patch(
            rejected_patch["id"],
            decision="rejected",
            reviewer="unit_test",
            notes="Keep the baseline prompt.",
        )

        self.assertEqual(result["patch"]["proposal_state"], "rejected")
        self.assertIsNone(result["prompt"])
        resolved = self.vault.resolve_prompt("prompt_schema_designer_v1")
        self.assertEqual(resolved.instruction, self.prompt["instruction"])

    def test_prompt_patch_approval_blocks_without_backup(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)
        self.vault.store_core_object("PromptPatch", self.patch)

        with self.assertRaisesRegex(ValueError, "prompt patch promotion blocked"):
            self.vault.review_prompt_patch(
                self.patch["id"],
                decision="approved",
                reviewer="unit_test",
                policy_payload=self.policy,
                backup_receipt=None,
            )

    def test_prompt_patch_approval_blocks_without_passed_eval(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)
        self.vault.store_core_object("PromptPatch", self.patch)

        with self.assertRaisesRegex(ValueError, "requires a passed prompt_patch eval"):
            self.vault.review_prompt_patch(
                self.patch["id"],
                decision="approved",
                reviewer="unit_test",
                policy_payload=self.policy,
                backup_receipt=self.backup,
            )


if __name__ == "__main__":
    unittest.main()
