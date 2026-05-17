from __future__ import annotations

import copy
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


class AuditCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))
        self.fixture_root = ROOT / "fixtures" / "evidence"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _fixture(self, name: str) -> dict:
        return json.loads((self.fixture_root / name).read_text())

    def test_supported_audit_path_is_deterministic_and_indexed(self) -> None:
        claim = self._fixture("claim-record.json")
        evidence = self._fixture("evidence-link.json")

        self.vault.capture_claim(claim)
        self.vault.link_evidence(evidence)

        audit = self.vault.run_audit(
            scope_kind="project",
            scope_value="ctxvault",
            subject_ref=claim["subject_ref"],
        )

        self.assertEqual(audit["verdict"], "supported_by_local_evidence")
        self.assertEqual(audit["review_state"], "approved")
        self.assertEqual(audit["claim_refs"], ["claim://claim_20260419_ctxvault_001"])

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        row = connection.execute(
            "SELECT verdict, review_state FROM audit_runs WHERE object_id = ?",
            (audit["id"],),
        ).fetchone()
        connection.close()

        self.assertEqual(row, ("supported_by_local_evidence", "approved"))

    def test_conflicting_evidence_escalates_to_human_review_then_resolves(self) -> None:
        claim = copy.deepcopy(self._fixture("claim-record.json"))
        claim["id"] = "claim_20260419_ctxvault_conflict_001"
        claim["subject_ref"] = "turn://sess_20260419_ctxvault_001/9"

        support = copy.deepcopy(self._fixture("evidence-link.json"))
        support["id"] = "evid_20260419_ctxvault_conflict_support"
        support["claim_id"] = claim["id"]
        support["confidence"] = 0.97

        contradiction = copy.deepcopy(self._fixture("evidence-link.json"))
        contradiction["id"] = "evid_20260419_ctxvault_conflict_contradiction"
        contradiction["claim_id"] = claim["id"]
        contradiction["relation"] = "contradicts"
        contradiction["confidence"] = 0.91
        contradiction["evidence_ref"] = "repo://ctxvault/README.md"
        contradiction["excerpt"] = "Contradictory local note to force deterministic escalation."

        self.vault.capture_claim(claim)
        self.vault.link_evidence(support)
        self.vault.link_evidence(contradiction)

        audit = self.vault.run_audit(
            scope_kind="project",
            scope_value="ctxvault",
            subject_ref=claim["subject_ref"],
        )

        self.assertEqual(audit["verdict"], "needs_human_review")
        self.assertEqual(audit["review_state"], "open")

        reviewed = self.vault.review_audit(
            audit["id"],
            decision="approved",
            notes="Human resolved the conflict in favor of contradiction.",
            override_verdict="contradicted_by_local_evidence",
        )

        self.assertEqual(reviewed["method"], "human_review")
        self.assertEqual(reviewed["review_state"], "approved")
        self.assertEqual(reviewed["verdict"], "contradicted_by_local_evidence")
        self.assertIn("Human review:", reviewed["notes"])


if __name__ == "__main__":
    unittest.main()
