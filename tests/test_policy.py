from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.policy import CtxVaultPolicy


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text())
        self.backup = CtxVaultPolicy.freshen_backup_receipt(
            json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text())
        )
        self.engine = CtxVaultPolicy(self.policy)

    def test_operation_gate_requires_review_when_backup_is_fresh(self) -> None:
        decision = self.engine.evaluate_operation(
            operation="memory_promotion",
            sensitivity="internal",
            backup_receipt=self.backup,
        )

        self.assertEqual(decision.decision, "review_required")
        self.assertEqual(decision.backup_status, "ok")
        self.assertTrue(decision.requires_human_review)

    def test_operation_gate_rolls_back_when_backup_is_missing(self) -> None:
        decision = self.engine.evaluate_operation(
            operation="destructive_redaction",
            sensitivity="sensitive",
            backup_receipt=None,
        )

        self.assertEqual(decision.decision, "rollback_required")
        self.assertEqual(decision.backup_status, "missing")

    def test_operation_gate_treats_old_backup_as_stale(self) -> None:
        stale_backup = copy.deepcopy(self.backup)
        stale_backup["checked_at"] = "2026-04-17T09:30:00Z"
        decision = self.engine.evaluate_operation(
            operation="memory_promotion",
            sensitivity="internal",
            backup_receipt=stale_backup,
        )

        self.assertEqual(decision.decision, "block")
        self.assertEqual(decision.backup_status, "stale")

    def test_export_gate_blocks_restricted_payloads(self) -> None:
        decision = self.engine.evaluate_export(
            sensitivity="restricted",
            exportable=True,
            redaction_state="none",
            secret_refs=["secret://db-password"],
        )

        self.assertEqual(decision.decision, "block")
        self.assertTrue(decision.requires_human_review)

    def test_export_gate_requires_redaction_for_secret_refs(self) -> None:
        decision = self.engine.evaluate_export(
            sensitivity="internal",
            exportable=True,
            redaction_state="none",
            secret_refs=["secret://token"],
        )

        self.assertEqual(decision.decision, "redact")
        self.assertTrue(decision.redactions_required)

    def test_logical_purge_requires_review_and_fresh_backup(self) -> None:
        decision = self.engine.evaluate_operation(
            operation="logical_purge_derived",
            sensitivity="sensitive",
            backup_receipt=self.backup,
        )

        self.assertEqual(decision.decision, "review_required")
        self.assertEqual(decision.backup_status, "ok")
        self.assertTrue(decision.requires_human_review)

    def test_remote_model_external_send_is_review_gated(self) -> None:
        decision = self.engine.evaluate_operation(
            operation="model_external_send",
            sensitivity="internal",
            backup_receipt=None,
        )

        self.assertEqual(decision.decision, "review_required")
        self.assertEqual(decision.backup_status, "not_required")
        self.assertTrue(decision.requires_human_review)


if __name__ == "__main__":
    unittest.main()
