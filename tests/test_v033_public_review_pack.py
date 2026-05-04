from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_v033_public_review_pack.py"


def load_review_pack_module():
    spec = importlib.util.spec_from_file_location("run_v033_public_review_pack", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load review pack script: {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V033PublicReviewPackTests(unittest.TestCase):
    def test_owner_public_review_pack_runs_from_public_fixtures(self) -> None:
        module = load_review_pack_module()
        with TemporaryDirectory(dir="/tmp") as tmpdir:
            root = Path(tmpdir) / "ctxvault-v033-public-review"
            summary = module.run_review_pack(root=root)

            self.assertEqual(summary["status"], "pass")
            self.assertEqual(summary["schema_id"], "ctxvault.v0.3.3-public-review-pack/v1")
            self.assertGreaterEqual(len(summary["corpus"]), 13)
            self.assertIn("scenario_manifest_path", summary)
            self.assertEqual(summary["scenario_coverage"]["source_count"], len(summary["corpus"]))
            self.assertEqual(summary["scenario_coverage"]["scenario_count"], len(summary["scenarios"]))
            self.assertEqual(summary["scenario_coverage"]["expected_behaviors"]["ready"], 10)
            self.assertEqual(summary["scenario_coverage"]["expected_behaviors"]["empty"], 1)
            self.assertEqual(summary["scenario_coverage"]["expected_behaviors"]["over_budget"], 1)

            scenarios = {item["id"]: item for item in summary["scenarios"]}
            self.assertGreaterEqual(len(scenarios), 12)
            for scenario_id in {
                "privacy-local-search-handoff",
                "secure-release-readiness",
                "open-source-public-review",
                "cli-onboarding-happy-path",
                "receipt-audit-trail",
                "api-response-triage",
                "connector-boundary-private-surface",
                "license-public-domain-review",
                "decoy-resistant-privacy-only",
                "budget-first-source-trim",
                "empty-query-boundary",
                "budget-overrun-warning",
            }:
                self.assertIn(scenario_id, scenarios)
            for scenario in scenarios.values():
                self.assertEqual(scenario["status"], "pass")
                self.assertIn("review_question", scenario)
                self.assertIn("expected_behavior", scenario)
                self.assertIn("data_shape", scenario)
                self.assertIn("risk_axes", scenario)
                self.assertIn("tags", scenario)
                self.assertIn("pass_reason", scenario)
                self.assertTrue(all(scenario["pass_checks"].values()))
                self.assertEqual(scenario["matched_expected_source_refs"], scenario["expected_source_refs"])
                self.assertEqual(scenario["matched_forbidden_source_refs"], [])
                self.assertTrue(Path(scenario["receipt_path"]).exists())
                if scenario["expected_behavior"] == "ready":
                    self.assertTrue(scenario["handoff_ready"])
                    self.assertEqual(scenario["privacy_decision"], "allow")
                    self.assertEqual(scenario["budget_status"], "within_budget")
                elif scenario["expected_behavior"] == "empty":
                    self.assertFalse(scenario["handoff_ready"])
                    self.assertEqual(scenario["candidate_count"], 0)
                    self.assertEqual(scenario["selection_status"], "empty")
                    self.assertEqual(scenario["selected_slice_refs"], [])
                elif scenario["expected_behavior"] == "over_budget":
                    self.assertFalse(scenario["handoff_ready"])
                    self.assertEqual(scenario["privacy_decision"], "allow")
                    self.assertEqual(scenario["budget_status"], "over_budget")
                    self.assertEqual(scenario["selection_status"], "over_budget")

            blocked = summary["blocked_selection"]
            self.assertEqual(blocked["status"], "pass")
            self.assertTrue(all(blocked["pass_checks"].values()))
            self.assertEqual(blocked["decision"], "block")
            self.assertFalse(blocked["allowed_to_write"])
            self.assertTrue(Path(blocked["receipt_path"]).exists())

            projection = summary["projection"]
            self.assertEqual(projection["status"], "pass")
            self.assertTrue(all(projection["pass_checks"].values()))
            self.assertEqual(projection["privacy_decision"], "allow")
            self.assertTrue(Path(projection["output_path"]).exists())
            self.assertTrue(Path(projection["receipt_path"]).exists())
            receipt = json.loads(Path(projection["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["selected_slice_refs"], projection["selected_slice_refs"])

            summary_path = Path(summary["summary_path"])
            self.assertTrue(summary_path.exists())
            persisted = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["status"], "pass")
            self.assertIn("human_review", persisted)

            report_path = Path(summary["human_review"]["markdown_path"])
            html_path = Path(summary["human_review"]["html_path"])
            self.assertTrue(report_path.exists())
            self.assertTrue(html_path.exists())
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("CtxVault v0.3.3 Owner Review", report)
            self.assertIn("READY FOR OWNER REVIEW", report)
            self.assertIn("Why this is PASS", report)
            self.assertIn("What this does not prove", report)
            self.assertIn("Scenario Coverage", report)
            self.assertIn("Data shapes:", report)
            self.assertIn("Why Each Scenario Passed", report)
            self.assertIn("deterministic package review", report)
            self.assertIn("What Was Selected", report)
            self.assertIn("empty-query-boundary", report)
            self.assertIn("budget-overrun-warning", report)
            self.assertIn("synthetic secret explicit selection", report)
            self.assertIn("Approval Checklist", report)
            self.assertIn("not an automatic publication approval", report)
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("<title>CtxVault v0.3.3 Owner Review</title>", html)
            self.assertIn("Why This Is PASS", html)
            self.assertIn("What This Does Not Prove", html)
            self.assertIn("Scenario Coverage", html)
            self.assertIn("Scenario Results", html)

            with self.assertRaises(RuntimeError):
                module.run_review_pack(root=root)

            rerun = module.run_review_pack(root=root, force=True)
            self.assertEqual(rerun["status"], "pass")
            self.assertEqual(rerun["projection"]["output_sha256"], summary["projection"]["output_sha256"])


if __name__ == "__main__":
    unittest.main()
