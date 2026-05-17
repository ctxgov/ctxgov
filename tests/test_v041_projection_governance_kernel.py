from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.validate_fixtures import validate


README = ROOT / "README.md"
NOTE = ROOT / "docs" / "v0.4.1-projection-governance-kernel.md"
APPROVAL_MATRIX = ROOT / "docs" / "v0.4.1-execution-approval-matrix.md"
SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "json"
    / "ctxvault-projection-governance-kernel-v041.schema.json"
)
FIXTURE_DIR = ROOT / "fixtures" / "v0.4.1-projection-governance-kernel"
PROJECTION_FIXTURE = FIXTURE_DIR / "example-projection.json"
RECEIPT_FIXTURE = FIXTURE_DIR / "example-receipt.json"
APPROVAL_MATRIX_FIXTURE = FIXTURE_DIR / "approval-matrix.json"


class V041ProjectionGovernanceKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.projection_packet = json.loads(PROJECTION_FIXTURE.read_text(encoding="utf-8"))
        self.receipt_packet = json.loads(RECEIPT_FIXTURE.read_text(encoding="utf-8"))
        self.approval_matrix = json.loads(APPROVAL_MATRIX_FIXTURE.read_text(encoding="utf-8"))

    def test_projection_and_receipt_examples_match_schema(self) -> None:
        validate(self.projection_packet, self.schema, self.schema, PROJECTION_FIXTURE.name)
        validate(self.receipt_packet, self.schema, self.schema, RECEIPT_FIXTURE.name)

    def test_docs_keep_v041_as_design_preview_and_readme_stays_current_release_focused(self) -> None:
        readme = README.read_text(encoding="utf-8")
        note = NOTE.read_text(encoding="utf-8")
        normalized_readme = " ".join(readme.split())
        normalized_note = " ".join(note.split())

        self.assertIn("Know what your AI tools see.", readme)
        self.assertIn("v0.6.2 public release artifact", readme)
        self.assertIn("Context Health Doctor", readme)
        self.assertNotIn("v0.4.1 is an experimental", normalized_readme)
        self.assertNotIn("Projection Governance Kernel", readme)
        self.assertIn("Know what your AI tools see.", note)
        self.assertIn("Status: experimental, non-normative v0.4.1 schema explanation", note)
        self.assertIn("This is not a v0.4.0 shipped-feature claim.", note)
        self.assertIn("not a stable external API", note)
        self.assertIn("not runtime behavior", note)
        self.assertIn("not a runtime-control contract", normalized_note)
        self.assertIn(
            "sources become candidate context; review decisions govern what may be projected",
            normalized_note,
        )
        self.assertIn("v0.4.1-execution-approval-matrix.md", note)
        self.assertIn("v0.4.1-release-notes.md", note)

    def test_forbidden_claims_are_not_rendered_as_shipped_claims(self) -> None:
        combined = "\n".join(
            [
                README.read_text(encoding="utf-8"),
                NOTE.read_text(encoding="utf-8"),
                json.dumps(self.schema, sort_keys=True),
                json.dumps(self.projection_packet, sort_keys=True),
                json.dumps(self.receipt_packet, sort_keys=True),
            ]
        )

        for forbidden in [
            "CtxVault is a Memory OS",
            "CtxVault is a memory control plane",
            "CtxVault is a unified agent memory",
            "CtxVault ships external memory adapters",
            "CtxVault ships a stable external API",
            "CtxVault is public beta ready",
            "CtxVault controls Codex runtime",
            "CtxVault controls Claude Code runtime",
            "CtxVault controls Cursor runtime",
            "CtxVault controls ChatGPT runtime",
        ]:
            self.assertNotIn(forbidden, combined)

    def test_source_candidate_review_projection_chain_is_explicit(self) -> None:
        source_ids = {item["id"] for item in self.projection_packet["source_evidence"]}
        candidate_ids = {item["id"] for item in self.projection_packet["candidate_context"]}
        decision_by_candidate = {
            item["candidate_id"]: item["decision"]
            for item in self.projection_packet["review_decisions"]
        }

        self.assertEqual(
            {
                "cand_v040_handoff_boundary",
                "cand_external_memory_adapters",
                "cand_runtime_control_claim",
            },
            candidate_ids,
        )
        self.assertEqual(candidate_ids, set(decision_by_candidate))

        for candidate in self.projection_packet["candidate_context"]:
            self.assertEqual("candidate", candidate["status"])
            self.assertTrue(set(candidate["source_ids"]).issubset(source_ids))

        self.assertEqual(
            {
                "cand_v040_handoff_boundary": "selected",
                "cand_external_memory_adapters": "omitted",
                "cand_runtime_control_claim": "blocked",
            },
            decision_by_candidate,
        )

        projection = self.projection_packet["projection"]
        self.assertEqual(
            ["cand_v040_handoff_boundary"],
            projection["included_candidate_ids"],
        )
        self.assertEqual("handoff_packet", projection["target_surface"])

    def test_receipt_states_match_review_decisions_and_written_artifact(self) -> None:
        receipt = self.receipt_packet["receipt"]
        states = receipt["states"]
        review_decisions = self.projection_packet["review_decisions"]
        decisions_by_state = {
            state: sorted(
                decision["candidate_id"]
                for decision in review_decisions
                if decision["decision"] == state
            )
            for state in ["selected", "omitted", "blocked"]
        }

        self.assertEqual(self.projection_packet["projection"]["id"], receipt["projection_id"])
        self.assertEqual(decisions_by_state["selected"], sorted(states["selected"]))
        self.assertEqual(decisions_by_state["omitted"], sorted(states["omitted"]))
        self.assertEqual(decisions_by_state["blocked"], sorted(states["blocked"]))
        self.assertIn(self.projection_packet["handoff_packet"]["artifact_ref"], states["written"])

        for excluded in [
            "memory_os_claim",
            "memory_control_plane_claim",
            "unified_agent_memory_claim",
            "stable_candidate_projection_api",
            "external_memory_adapter",
            "benchmark_claim",
            "runtime_control",
        ]:
            self.assertIn(excluded, states["not_done"])

    def test_handoff_packet_is_artifact_handoff_not_runtime_control(self) -> None:
        handoff = self.projection_packet["handoff_packet"]
        schema_text = json.dumps(self.schema, sort_keys=True)

        self.assertEqual(self.projection_packet["projection"]["id"], handoff["projection_id"])
        self.assertEqual("not_claimed", handoff["runtime_control_claim"])

        for forbidden_surface in [
            "codex_runtime",
            "claude_code_runtime",
            "cursor_runtime",
            "chatgpt_runtime",
            "provider_gateway",
        ]:
            self.assertNotIn(forbidden_surface, schema_text)

    def test_approval_matrix_executes_only_low_risk_no_approval_work(self) -> None:
        doc = APPROVAL_MATRIX.read_text(encoding="utf-8")
        no_approval = self.approval_matrix["no_approval_executed"]

        self.assertIn("No New Owner Approval Needed", doc)
        self.assertIn("Requires Owner Approval", doc)
        self.assertIn("owner A+ decision recorded", doc)
        self.assertIn("No other no-approval v0.4.1 work is open in this tranche.", doc)

        self.assertEqual(
            {
                "v041-noapproval-kernel-schema",
                "v041-noapproval-public-boundary-note",
                "v041-noapproval-readme-pointer",
                "v041-noapproval-fixture-validation",
                "v041-noapproval-approval-matrix",
                "v041-noapproval-release-packaging-boundary",
            },
            {item["id"] for item in no_approval},
        )
        for item in no_approval:
            self.assertEqual("executed", item["status"], item["id"])
            self.assertTrue(item["artifacts"], item["id"])
            if "runtime behavior" in item["boundary"].lower():
                self.assertIn("no runtime behavior change", item["boundary"].lower())

        rendered = json.dumps(no_approval, sort_keys=True)
        for forbidden_path in [
            "src/ctxvault/" + "workbench.py",
            "src/ctxvault/" + "webapp/app.js",
            "release/" + "macos",
            "release/v0.4.0",
            "build/" + "CtxVault" + ".app",
            "release/v0.4.1",
        ]:
            self.assertNotIn(forbidden_path, rendered)

    def test_approval_required_options_preserve_recommended_v041_release_posture(self) -> None:
        doc = APPROVAL_MATRIX.read_text(encoding="utf-8")
        normalized_doc = " ".join(doc.split())
        approval_required = self.approval_matrix["approval_required"]

        expected_ids = {
            "v041-release-shape": "A+",
            "v041-public-doc-timing": "A",
            "v041-trust-floor-depth": "A",
            "v041-code-package-safety": "A",
            "v041-review-workflow-integration": "A",
            "v041-external-adapters": "A",
            "v041-memory-substrate-consolidation": "A",
            "v041-public-claim-level": "A",
        }
        self.assertEqual(expected_ids, {item["id"]: item["recommended_option"] for item in approval_required})

        for item in approval_required:
            self.assertIn("requires_owner_approval_because", item)
            expected_options = {"A+", "B", "C"} if item["id"] == "v041-release-shape" else {"A", "B", "C"}
            self.assertEqual(expected_options, {option["option"] for option in item["options"]})

        for required in [
            "Option 1A+",
            "Option 2A",
            "Option 3A",
            "Option 4A",
            "Option 5A",
            "Option 6A",
            "Option 7A",
            "Option 8A",
            "move operational reviewer UX to v0.4.2",
            "move external candidate/provider protocol work to v0.5",
        ]:
            self.assertIn(required, doc)

        for required in [
            "schema, receipts, routes, deterministic fixtures, and focused tests",
            "experimental, non-normative, not-shipped-behavior",
            "high-risk area and must keep deterministic fixture coverage",
            "should not become the canonical v0.4.1 product surface",
        ]:
            self.assertIn(required, normalized_doc)

    def test_approval_matrix_forbids_scope_expansion_without_owner_approval(self) -> None:
        forbidden = set(self.approval_matrix["forbidden_without_owner_approval"])

        self.assertTrue(
            {
                "runtime_control",
                "provider_or_model_execution",
                "live_registry_lookup",
                "runtime_gate_wiring",
                "workbench_review_ux_change",
                "canonical_code_package_product_surface",
                "live_command_check",
                "supply_chain_scanner_claim",
                "verifier_product_claim",
                "durable_memory_consolidation",
                "anti_hallucination_prevention_claim",
                "external_memory_adapter",
                "stable_external_api",
                "public_beta_readiness_claim",
                "memory_os_claim",
                "memory_control_plane_claim",
                "unified_agent_memory_claim",
                "notarized_app_artifact_change",
                "release_zip_or_checksum_change",
            }.issubset(forbidden)
        )

if __name__ == "__main__":
    unittest.main()
