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
from ctxgov.policy import CtxVaultPolicy


class MemoryCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))
        self.candidate = json.loads((ROOT / "fixtures" / "core" / "memory-candidate.json").read_text())
        self.policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text())
        self.backup = CtxVaultPolicy.freshen_backup_receipt(
            json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text())
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_approved_memory_candidate_promotes_into_searchable_memory(self) -> None:
        self.vault.store_core_object("MemoryCandidate", self.candidate)

        hits = self.vault.list_memory_candidates(scope=("project", "ctxvault"), proposal_state="proposed", limit=10)
        self.assertEqual([hit.object_id for hit in hits], [self.candidate["id"]])

        result = self.vault.review_memory_candidate(
            self.candidate["id"],
            decision="approved",
            reviewer="unit_test",
            notes="Promote to durable project memory.",
            policy_payload=self.policy,
            backup_receipt=self.backup,
        )

        self.assertEqual(result["candidate"]["proposal_state"], "merged")
        self.assertEqual(result["memory"]["approval_state"], "approved")
        self.assertEqual(result["memory"]["id"], "mem_20260419_ctxvault_rule_001")
        self.assertEqual(result["policy_decision"]["decision"], "review_required")

        memories = self.vault.search_memories("deterministic core work", scope=("project", "ctxvault"), limit=5)
        self.assertEqual([memory.object_id for memory in memories], ["mem_20260419_ctxvault_rule_001"])

        receipt_path = Path(result["review_receipt_path"])
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["decision"], "approved")
        self.assertEqual(receipt["result_ref"], "memory://mem_20260419_ctxvault_rule_001")

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        candidate_row = connection.execute(
            "SELECT proposal_state FROM memory_candidates WHERE object_id = ?",
            (self.candidate["id"],),
        ).fetchone()
        memory_row = connection.execute(
            "SELECT approval_state FROM memories WHERE object_id = ?",
            ("mem_20260419_ctxvault_rule_001",),
        ).fetchone()
        connection.close()

        self.assertEqual(candidate_row, ("merged",))
        self.assertEqual(memory_row, ("approved",))

    def test_rejected_memory_candidate_writes_review_receipt_without_memory(self) -> None:
        candidate = dict(self.candidate)
        candidate["id"] = "memc_20260419_ctxvault_rule_002"
        candidate["statement"] = "Rejected candidate for test coverage."
        self.vault.store_core_object("MemoryCandidate", candidate)

        result = self.vault.review_memory_candidate(
            candidate["id"],
            decision="rejected",
            reviewer="unit_test",
            notes="Not durable enough.",
        )

        self.assertEqual(result["candidate"]["proposal_state"], "rejected")
        self.assertIsNone(result["memory"])

        rejected_hits = self.vault.list_memory_candidates(proposal_state="rejected", limit=10)
        self.assertEqual([hit.object_id for hit in rejected_hits], [candidate["id"]])
        self.assertEqual(self.vault.search_memories("Rejected candidate", scope=("project", "ctxvault"), limit=5), [])

    def test_memory_candidate_approval_blocks_when_backup_gate_fails(self) -> None:
        self.vault.store_core_object("MemoryCandidate", self.candidate)

        with self.assertRaisesRegex(ValueError, "memory promotion blocked"):
            self.vault.review_memory_candidate(
                self.candidate["id"],
                decision="approved",
                reviewer="unit_test",
                policy_payload=self.policy,
                backup_receipt=None,
            )


if __name__ == "__main__":
    unittest.main()
