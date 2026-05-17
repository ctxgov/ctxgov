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


class WorkstreamCandidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))
        self.candidate = json.loads((ROOT / "fixtures" / "core" / "workstream-candidate.json").read_text())
        self.policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text())
        self.backup = CtxVaultPolicy.freshen_backup_receipt(
            json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text())
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_approved_workstream_candidate_promotes_into_listable_workstream(self) -> None:
        self.vault.store_core_object("WorkstreamCandidate", self.candidate)

        hits = self.vault.list_workstream_candidates(scope=("project", "ctxvault"), proposal_state="proposed", limit=10)
        self.assertEqual([hit.object_id for hit in hits], [self.candidate["id"]])

        result = self.vault.review_workstream_candidate(
            self.candidate["id"],
            decision="approved",
            reviewer="unit_test",
            notes="Promote the grouped schema sessions into one durable workstream.",
            policy_payload=self.policy,
            backup_receipt=self.backup,
        )

        self.assertEqual(result["candidate"]["proposal_state"], "merged")
        self.assertEqual(result["workstream"]["approval_state"], "approved")
        self.assertEqual(result["workstream"]["status"], "active")
        self.assertEqual(result["workstream"]["id"], "ws_20260421_ctxvault_schema")
        self.assertEqual(result["policy_decision"]["decision"], "review_required")

        workstreams = self.vault.list_workstreams(scope=("project", "ctxvault"), status="active", limit=5)
        self.assertEqual([workstream.object_id for workstream in workstreams], ["ws_20260421_ctxvault_schema"])

        receipt_path = Path(result["review_receipt_path"])
        self.assertTrue(receipt_path.exists())
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["decision"], "approved")
        self.assertEqual(receipt["result_ref"], "workstream://ws_20260421_ctxvault_schema")

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        candidate_row = connection.execute(
            "SELECT proposal_state FROM workstream_candidates WHERE object_id = ?",
            (self.candidate["id"],),
        ).fetchone()
        workstream_row = connection.execute(
            "SELECT approval_state FROM workstreams WHERE object_id = ?",
            ("ws_20260421_ctxvault_schema",),
        ).fetchone()
        connection.close()

        self.assertEqual(candidate_row, ("merged",))
        self.assertEqual(workstream_row, ("approved",))

    def test_rejected_workstream_candidate_writes_review_receipt_without_workstream(self) -> None:
        candidate = dict(self.candidate)
        candidate["id"] = "wsc_20260421_ctxvault_schema_reject"
        candidate["title"] = "Rejected schema workstream"
        candidate["summary"] = "Rejected candidate for test coverage."
        self.vault.store_core_object("WorkstreamCandidate", candidate)

        result = self.vault.review_workstream_candidate(
            candidate["id"],
            decision="rejected",
            reviewer="unit_test",
            notes="Keep this as an ephemeral preview only.",
        )

        self.assertEqual(result["candidate"]["proposal_state"], "rejected")
        self.assertIsNone(result["workstream"])

        rejected_hits = self.vault.list_workstream_candidates(proposal_state="rejected", limit=10)
        self.assertEqual([hit.object_id for hit in rejected_hits], [candidate["id"]])
        self.assertEqual(self.vault.list_workstreams(scope=("project", "ctxvault"), limit=5), [])

    def test_workstream_candidate_approval_blocks_when_backup_gate_fails(self) -> None:
        self.vault.store_core_object("WorkstreamCandidate", self.candidate)

        with self.assertRaisesRegex(ValueError, "workstream promotion blocked"):
            self.vault.review_workstream_candidate(
                self.candidate["id"],
                decision="approved",
                reviewer="unit_test",
                policy_payload=self.policy,
                backup_receipt=None,
            )


if __name__ == "__main__":
    unittest.main()
