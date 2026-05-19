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

from scripts.validate_fixtures import ValidationError, validate


SCHEMA = ROOT / "schemas" / "json" / "ctxvault-runtime-evidence-receipt-v0.schema.json"
FIXTURE = ROOT / "fixtures" / "evidence" / "runtime-evidence-receipt.json"
DOC = ROOT / "docs" / "runtime-evidence-receipt.md"


class RuntimeEvidenceReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_validates_against_schema(self) -> None:
        validate(self.fixture, self.schema, self.schema, FIXTURE.name)

    def assert_invalid_receipt(self, receipt: dict, expected: str) -> None:
        with self.assertRaises(ValidationError) as raised:
            validate(receipt, self.schema, self.schema, "mutated-runtime-evidence-receipt.json")
        self.assertIn(expected, str(raised.exception))

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

    def test_output_state_invariants_are_schema_enforced(self) -> None:
        missing_digest = copy.deepcopy(self.fixture)
        missing_digest["output_state"]["digest"] = None
        self.assert_invalid_receipt(missing_digest, "expected object")

        missing_size = copy.deepcopy(self.fixture)
        missing_size["output_state"]["size_bytes"] = None
        self.assert_invalid_receipt(missing_size, "expected integer")

        not_produced_with_evidence = copy.deepcopy(self.fixture)
        not_produced_with_evidence["output_state"]["state"] = "not_produced"
        self.assert_invalid_receipt(not_produced_with_evidence, "expected null")

    def test_failure_attribution_and_rollback_are_bounded(self) -> None:
        attribution = self.fixture["outcome"]["failure_attribution"]
        rollback = self.fixture["rollback"]

        self.assertEqual(attribution["level"], "stage_only")
        self.assertIn("does not attribute provider fault", attribution["statement"])
        self.assertIn("provider_fault", self.fixture["claims_not_made"])
        self.assertTrue(rollback["path_available"])
        self.assertEqual(rollback["observed_state"], "path_available_not_executed")
        self.assertIn("rollback_executed", self.fixture["claims_not_made"])

    def test_failure_attribution_source_claim_requires_source_ref(self) -> None:
        attributed = copy.deepcopy(self.fixture)
        attributed["outcome"]["failure_attribution"]["level"] = "source_supported_component"
        attributed["outcome"]["failure_attribution"]["source_ref"] = None

        self.assert_invalid_receipt(attributed, "expected string")

    def test_rollback_observation_invariants_are_schema_enforced(self) -> None:
        timestamp_without_execution = copy.deepcopy(self.fixture)
        timestamp_without_execution["rollback"]["observed_at"] = "2026-05-18T00:00:00Z"
        self.assert_invalid_receipt(timestamp_without_execution, "expected null")

        executed_without_timestamp = copy.deepcopy(self.fixture)
        executed_without_timestamp["rollback"]["observed_state"] = "executed"
        executed_without_timestamp["claims_not_made"].remove("rollback_executed")
        self.assert_invalid_receipt(executed_without_timestamp, "expected string")

        path_claim_without_ref = copy.deepcopy(self.fixture)
        path_claim_without_ref["rollback"]["rollback_ref"] = None
        self.assert_invalid_receipt(path_claim_without_ref, "expected string")

    def test_rollback_executed_claim_boundary_is_schema_enforced(self) -> None:
        executed_with_non_claim = copy.deepcopy(self.fixture)
        executed_with_non_claim["rollback"]["observed_state"] = "executed"
        executed_with_non_claim["rollback"]["observed_at"] = "2026-05-18T00:00:00Z"

        self.assert_invalid_receipt(executed_with_non_claim, "matched disallowed schema")

        executed_without_non_claim = copy.deepcopy(executed_with_non_claim)
        executed_without_non_claim["claims_not_made"].remove("rollback_executed")
        validate(executed_without_non_claim, self.schema, self.schema, "executed-rollback-receipt.json")

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
