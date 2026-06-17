from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TaskShardContextBudgetHNCandidateTests(unittest.TestCase):
    def test_demo_command_writes_public_safe_reports(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/run_task_shard_context_budget_demo.py",
                "--input",
                "examples/task-shard-context-budget/",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass_task_shard_context_budget_demo")
        self.assertEqual(payload["milestone"], "Task Shard Context Budget Ledger")
        self.assertFalse(payload["side_effect_boundary"]["workflow_executed"])
        self.assertFalse(payload["side_effect_boundary"]["worktree_created"])
        self.assertFalse(payload["side_effect_boundary"]["provider_or_model_call_performed"])
        self.assertFalse(payload["side_effect_boundary"]["target_file_written"])
        self.assertFalse(payload["claim_boundary"]["public_benchmark_claim_created"])
        self.assertFalse(payload["claim_boundary"]["public_savings_claim_created"])
        self.assertFalse(payload["raw_content_included"])
        for path in payload["output_files"].values():
            self.assertTrue((ROOT / path).exists(), path)

    def test_report_contract_blocks_runtime_and_benchmark_claim_drift(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_task_shard_context_budget_report_contract.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass_task_shard_context_budget_report_contract")
        self.assertEqual(payload["negative_case_count"], 6)
        self.assertIn("workflow_execution_flip", payload["observed_rejection_modes"])
        self.assertIn("benchmark_claim_flip", payload["observed_rejection_modes"])

    def test_social_draft_drift_blocks_old_positioning_and_overclaims(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/check_task_shard_context_budget_social_draft_drift.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass_task_shard_context_budget_social_draft_drift")
        self.assertEqual(payload["hn_title"], "Show HN: CtxGov - audit context budgets for long-running AI agent tasks")
        self.assertEqual(payload["linkedin_draft_drift_status"], "pass")
        self.assertEqual(payload["x_thread_drift_status"], "pass")
        self.assertFalse(payload["publication_executed"])
        self.assertFalse(payload["outreach_performed"])

    def test_publication_bundle_owner_packet_and_live_local_checks_are_side_effect_free(self) -> None:
        checks = [
            (
                "scripts/build_task_shard_context_budget_publication_bundle.py",
                "pass_task_shard_context_budget_publication_bundle",
            ),
            (
                "scripts/check_task_shard_context_budget_owner_publish_packet_contract.py",
                "pass_task_shard_context_budget_owner_publish_packet_contract",
            ),
            (
                "scripts/check_task_shard_context_budget_live_publication.py",
                "pass_task_shard_context_budget_live_publication_check",
            ),
        ]
        for script, expected_status in checks:
            with self.subTest(script=script):
                result = subprocess.run(
                    [sys.executable, script],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], expected_status)
                self.assertFalse(payload["publication_executed"])
                self.assertFalse(payload["outreach_performed"])


if __name__ == "__main__":
    unittest.main()
