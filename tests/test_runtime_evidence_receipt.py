from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.validate_fixtures import validate


SCHEMA = ROOT / "schemas" / "json" / "ctxvault-runtime-evidence-receipt-v0.schema.json"
FIXTURE = ROOT / "fixtures" / "evidence" / "runtime-evidence-receipt.json"
DOC = ROOT / "docs" / "runtime-evidence-receipt.md"


class RuntimeEvidenceReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_validates_against_schema(self) -> None:
        validate(self.fixture, self.schema, self.schema, FIXTURE.name)

    def test_receipt_is_review_artifact_not_trace_truth(self) -> None:
        self.assertIn("trace_truth", self.fixture["claims_not_made"])
        self.assertIn("runtime_ownership", self.fixture["claims_not_made"])
        self.assertEqual(self.fixture["schema_id"], "ctxvault.runtime-evidence-receipt/v0")
        self.assertEqual(
            self.fixture["identity"]["producer_schema_version"],
            "ctxvault.runtime-evidence-receipt/v0",
        )

    def test_output_absence_is_explicit_state_not_silent_absence(self) -> None:
        output_state = self.fixture["output_state"]

        self.assertEqual(output_state["state"], "observed_digest_only")
        self.assertEqual(output_state["role"], "assistant")
        self.assertGreater(output_state["size_bytes"], 0)
        self.assertEqual(output_state["digest"]["algorithm"], "sha256")
        omission_states = {item["state"] for item in self.fixture["omissions"]}
        self.assertEqual(omission_states, {"redacted", "omitted", "unavailable"})

    def test_failure_attribution_and_rollback_are_bounded(self) -> None:
        attribution = self.fixture["outcome"]["failure_attribution"]
        rollback = self.fixture["rollback"]

        self.assertEqual(attribution["level"], "stage_only")
        self.assertIn("does not attribute provider fault", attribution["statement"])
        self.assertIn("provider_fault", self.fixture["claims_not_made"])
        self.assertTrue(rollback["path_available"])
        self.assertEqual(rollback["observed_state"], "path_available_not_executed")
        self.assertIn("rollback_executed", self.fixture["claims_not_made"])

    def test_public_doc_names_boundary_and_validation(self) -> None:
        text = DOC.read_text(encoding="utf-8")

        for phrase in [
            "not the trace truth",
            "reviewable artifact",
            "`redacted`, `omitted`, and `unavailable`",
            "Having a rollback path is different",
            "does not approve runtime execution",
            "ctxvault-runtime-evidence-receipt-v0.schema.json",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
