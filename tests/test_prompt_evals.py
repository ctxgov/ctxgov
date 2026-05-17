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

from ctxgov.core import CtxVault
from ctxgov.layout import default_layout


class PromptEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))
        self.prompt = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text(encoding="utf-8"))
        self.patch = json.loads((ROOT / "fixtures" / "core" / "prompt-patch.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_prompt_asset_eval_updates_status_and_projection(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)

        result = self.vault.run_prompt_eval(
            "prompt_asset",
            self.prompt["id"],
            dataset_ref="eval://unit/prompt-asset",
            assert_contains=["explicit object types", "governance hooks"],
            assert_not_contains=["requires remote llm"],
            notes="Validate baseline prompt contract.",
        )

        self.assertEqual(result["eval_run"]["result"], "passed")
        self.assertEqual(result["evaluated_prompt"]["eval_status"], "passed")
        self.assertEqual(result["target_ref"], "prompt://prompt_schema_designer_v1")

        resolved = self.vault.resolve_prompt(self.prompt["id"])
        self.assertEqual(resolved.payload["eval_status"], "passed")

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        row = connection.execute(
            "SELECT target_type, target_id, dataset_ref, result FROM eval_runs WHERE object_id = ?",
            (result["eval_run"]["id"],),
        ).fetchone()
        connection.close()
        self.assertEqual(row, ("prompt_asset", self.prompt["id"], "eval://unit/prompt-asset", "passed"))

    def test_prompt_patch_eval_uses_preview_without_mutating_prompt_asset(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)
        self.vault.store_core_object("PromptPatch", self.patch)

        result = self.vault.run_prompt_eval(
            "prompt_patch",
            self.patch["id"],
            dataset_ref="eval://unit/prompt-patch",
            assert_contains=["migration notes", "source-grounded rationale"],
            assert_not_contains=["requires remote llm"],
            notes="Evaluate the patch preview before promotion.",
        )

        self.assertEqual(result["eval_run"]["result"], "passed")
        self.assertEqual(result["target_ref"], f"prompt-patch://{self.patch['id']}")
        self.assertIn("migration notes", result["evaluated_prompt"]["instruction"])

        resolved = self.vault.resolve_prompt(self.prompt["id"])
        self.assertEqual(resolved.instruction, self.prompt["instruction"])
        self.assertEqual(resolved.payload["eval_status"], self.prompt["eval_status"])

    def test_failed_prompt_eval_marks_prompt_failed(self) -> None:
        self.vault.store_core_object("PromptAsset", self.prompt)

        result = self.vault.run_prompt_eval(
            "prompt_asset",
            self.prompt["id"],
            dataset_ref="eval://unit/prompt-asset-failing",
            assert_contains=["migration notes"],
        )

        self.assertEqual(result["eval_run"]["result"], "failed")
        self.assertEqual(result["evaluated_prompt"]["eval_status"], "failed")
        self.assertEqual(result["eval_run"]["metrics"]["contains_failed"], ["migration notes"])


if __name__ == "__main__":
    unittest.main()
