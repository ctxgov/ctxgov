from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPT = ROOT / "scripts" / "run_v034_context_quality_scorecards.py"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.surface import CtxVaultSurface
from scripts.validate_fixtures import validate


def load_scorecard_module():
    spec = importlib.util.spec_from_file_location("run_v034_context_quality_scorecards", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load scorecard script: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V034ContextQualityTests(unittest.TestCase):
    def test_v034_context_quality_scorecards_pass(self) -> None:
        module = load_scorecard_module()
        with TemporaryDirectory(dir="/tmp") as tmpdir:
            root = Path(tmpdir) / "ctxvault-v034-quality"
            summary = module.run_scorecards(root=root)

            self.assertEqual(summary["schema_id"], "ctxvault.v0.3.4-context-quality-scorecards/v1")
            self.assertEqual(summary["status"], "pass")
            self.assertTrue(all(summary["pass_checks"].values()))
            self.assertTrue(Path(summary["scorecard_path"]).exists())
            self.assertTrue(Path(summary["density_selection_receipt_path"]).exists())
            self.assertTrue(Path(summary["conflict_selection_receipt_path"]).exists())

            density = summary["context_density_scorecard"]
            self.assertEqual(density["schema_id"], "ctxvault.context-density-scorecard/v1")
            self.assertTrue(density["required_refs_retained"])
            self.assertLess(density["compression_ratio"], 1.0)
            self.assertGreaterEqual(len(density["omitted_refs_with_reason"]), 2)

            retention = summary["source_retention_scorecard"]
            self.assertEqual(retention["schema_id"], "ctxvault.source-retention-scorecard/v1")
            self.assertEqual(retention["status"], "pass")

            gain = summary["retrieval_gain_receipt"]
            self.assertEqual(gain["schema_id"], "ctxvault.retrieval-gain-receipt/v1")
            self.assertGreaterEqual(gain["new_required_refs_resolved"], 1)
            self.assertTrue(gain["misleading_refs_rejected"])

            trace = summary["search_decision_trace"]
            self.assertEqual(trace["schema_id"], "ctxvault.search-decision-trace/v1")
            self.assertTrue(trace["stop_reason"])

            conflict = summary["source_conflict_scorecard"]
            self.assertEqual(conflict["schema_id"], "ctxvault.source-conflict-scorecard/v1")
            self.assertEqual(conflict["status"], "pass")
            self.assertTrue(conflict["misleading_refs_rejected"])

    def test_context_selection_receipt_embeds_quality_contracts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            for object_id, title, body in [
                (
                    "know_quality_required",
                    "Required quality note",
                    "# Required quality note\n\nRetain this required v0.3.4 context quality source.",
                ),
                (
                    "know_quality_omitted",
                    "Omitted noisy quality note",
                    "# Omitted noisy quality note\n\n" + " ".join(["context quality noise"] * 80),
                ),
            ]:
                surface.vault.store_core_object(
                    "KnowledgeArtifact",
                    {
                        "id": object_id,
                        "kind": "project_note",
                        "title": title,
                        "scope": {"kind": "project", "value": "ctxvault"},
                        "body": body,
                        "source_refs": [],
                        "derived_from": [],
                        "status": "active",
                        "sensitivity": "internal",
                        "redaction_state": "none",
                        "secret_refs": [],
                        "exportable": True,
                        "created_at": "2026-05-04T00:00:00Z",
                        "updated_at": "2026-05-04T00:00:00Z",
                    },
                )
            surface.context_slice_rebuild()
            hits = surface.context_search("", scope_kind="project", scope_value="ctxvault", limit=50)
            refs = {
                hit["payload"]["source_ref"]: hit["slice_ref"]
                for hit in hits
                if hit["payload"]["source_ref"].startswith("knowledge://know_quality_")
            }

            result = surface.context_selection_compose(
                "v0.3.4 context quality",
                target_kind="harness.agents-md",
                scope_kind="project",
                scope_value="ctxvault",
                selected_slice_refs=[refs["knowledge://know_quality_required"]],
                required_slice_refs=[refs["knowledge://know_quality_required"]],
                candidate_slice_refs=[
                    refs["knowledge://know_quality_required"],
                    refs["knowledge://know_quality_omitted"],
                ],
                token_budget=120,
                write_receipt=True,
            )

            receipt = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
            schema = json.loads(
                (
                    ROOT
                    / "docs"
                    / "v0.3.2-injection-composer"
                    / "experimental-schemas"
                    / "ctxvault-context-selection-receipt-v1.schema.json"
                ).read_text(encoding="utf-8")
            )
            validate(receipt, schema, schema, "generated-v034-context-selection-receipt.json")
            self.assertEqual(receipt["context_quality_receipt"]["schema_id"], "ctxvault.context-quality-receipt/v1")
            self.assertEqual(receipt["context_density_scorecard"]["schema_id"], "ctxvault.context-density-scorecard/v1")
            self.assertEqual(receipt["retrieval_gain_receipt"]["schema_id"], "ctxvault.retrieval-gain-receipt/v1")
            self.assertEqual(receipt["search_decision_trace"]["schema_id"], "ctxvault.search-decision-trace/v1")
            self.assertEqual(receipt["source_conflict_scorecard"]["schema_id"], "ctxvault.source-conflict-scorecard/v1")
            self.assertTrue(receipt["required_refs_retained"])
            self.assertEqual(receipt["new_required_refs_resolved"], 1)
            self.assertEqual(receipt["required_slice_refs"], [refs["knowledge://know_quality_required"]])
            self.assertEqual(receipt["omitted_refs_with_reason"][0]["source_ref"], "knowledge://know_quality_omitted")

    def test_prompt_patch_density_check_is_candidate_only(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            prompt = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text(encoding="utf-8"))
            patch = json.loads((ROOT / "fixtures" / "core" / "prompt-patch.json").read_text(encoding="utf-8"))
            patch["id"] = "ppatch_v034_density_review"
            patch["changes"] = {
                "instruction": (
                    prompt["instruction"]
                    + "\n- Always keep provenance.\n- Always keep provenance.\n- TODO placeholder."
                )
            }
            surface.vault.store_core_object("PromptAsset", prompt)
            surface.vault.store_core_object("PromptPatch", patch)

            check = surface.prompt_patch_density_check(patch["id"])

            self.assertEqual(check["schema_id"], "ctxvault.prompt-patch-density-check/v1")
            self.assertEqual(check["status"], "needs_review")
            self.assertFalse(check["mutates_active_prompt"])
            self.assertEqual(check["candidate_action"], "review_candidate_only")
            self.assertIn("always keep provenance", check["duplicate_rules"])
            self.assertIn("todo", check["stale_boilerplate"])
            resolved = surface.vault.resolve_prompt(prompt["id"])
            self.assertEqual(resolved.instruction, prompt["instruction"])


if __name__ == "__main__":
    unittest.main()
