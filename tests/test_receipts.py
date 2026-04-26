from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.core import ContextBuildRequest, CtxVault
from ctxvault.layout import default_layout
from ctxvault.receipts import emit_audit_receipt, emit_context_bundle_receipt, emit_projection_receipt, emit_workstream_candidate_receipt, emit_workstream_receipt


class ReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_emit_context_bundle_receipt_writes_stable_fields(self) -> None:
        prompt = json.loads((ROOT / "fixtures" / "core" / "prompt-asset.json").read_text())
        memory = json.loads((ROOT / "fixtures" / "core" / "memory.json").read_text())
        knowledge = json.loads((ROOT / "fixtures" / "core" / "knowledge-artifact.json").read_text())
        self.vault.store_core_object("PromptAsset", prompt)
        self.vault.store_core_object("Memory", memory)
        self.vault.store_core_object("KnowledgeArtifact", knowledge)

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="receipt test",
                prompt_id="prompt_schema_designer_v1",
                memory_query="local LLM",
                knowledge_query="local-first context layer",
            )
        )
        receipt_path = self.repo_root / "artifacts" / "context-bundle-receipt.json"
        receipt = emit_context_bundle_receipt(
            root=self.repo_root,
            output_path=receipt_path,
            bundle_payload=bundle,
            plan_path=self.repo_root / "plans" / "demo.toml",
            task_id="context",
        )

        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], "ctxvault.context-bundle-receipt/v1")
        self.assertEqual(stored["bundle_ref"], f"bundle://{bundle['id']}")
        self.assertEqual(stored["plan_ledger_artifact"]["task_id"], "context")
        self.assertEqual(receipt["receipt_path"], str(receipt_path.resolve()))

    def test_emit_audit_receipt_writes_stable_fields(self) -> None:
        claim = json.loads((ROOT / "fixtures" / "evidence" / "claim-record.json").read_text())
        evidence = json.loads((ROOT / "fixtures" / "evidence" / "evidence-link.json").read_text())
        self.vault.capture_claim(claim)
        self.vault.link_evidence(evidence)
        audit = self.vault.run_audit(
            scope_kind="project",
            scope_value="ctxvault",
            subject_ref=claim["subject_ref"],
        )

        receipt_path = self.repo_root / "artifacts" / "audit-receipt.json"
        receipt = emit_audit_receipt(
            root=self.repo_root,
            output_path=receipt_path,
            audit_payload=audit,
            task_id="audit",
        )

        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], "ctxvault.audit-receipt/v1")
        self.assertEqual(stored["audit_ref"], f"audit://{audit['id']}")
        self.assertEqual(stored["verdict"], "supported_by_local_evidence")
        self.assertEqual(stored["plan_ledger_artifact"]["artifact_type"], "ctxvault_audit_receipt")
        self.assertEqual(receipt["receipt_path"], str(receipt_path.resolve()))

    def test_emit_workstream_candidate_receipt_writes_stable_fields(self) -> None:
        candidate = json.loads((ROOT / "fixtures" / "core" / "workstream-candidate.json").read_text())
        self.vault.store_core_object("WorkstreamCandidate", candidate)

        receipt_path = self.repo_root / "artifacts" / "workstream-candidate-receipt.json"
        receipt = emit_workstream_candidate_receipt(
            root=self.repo_root,
            output_path=receipt_path,
            candidate_payload=candidate,
            task_id="promote-workstream",
        )

        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], "ctxvault.workstream-candidate-receipt/v1")
        self.assertEqual(stored["candidate_ref"], f"workstream-candidate://{candidate['id']}")
        self.assertEqual(stored["plan_ledger_artifact"]["artifact_type"], "ctxvault_workstream_candidate_receipt")
        self.assertEqual(stored["plan_ledger_artifact"]["artifact_json"]["artifact_type"], "ctxvault_workstream_candidate_receipt")
        self.assertEqual(receipt["receipt_path"], str(receipt_path.resolve()))

    def test_emit_workstream_receipt_writes_stable_fields(self) -> None:
        workstream = json.loads((ROOT / "fixtures" / "core" / "workstream.json").read_text())
        self.vault.store_core_object("Workstream", workstream)

        receipt_path = self.repo_root / "artifacts" / "workstream-receipt.json"
        receipt = emit_workstream_receipt(
            root=self.repo_root,
            output_path=receipt_path,
            workstream_payload=workstream,
            plan_path=self.repo_root / "plans" / "demo.toml",
            task_id="context-intelligence",
        )

        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], "ctxvault.workstream-receipt/v1")
        self.assertEqual(stored["workstream_ref"], f"workstream://{workstream['id']}")
        self.assertEqual(stored["approval_state"], "approved")
        self.assertEqual(stored["plan_ledger_artifact"]["artifact_type"], "ctxvault_workstream_receipt")
        self.assertIn("--description", stored["plan_ledger_artifact"]["suggested_command"])
        self.assertEqual(receipt["receipt_path"], str(receipt_path.resolve()))

    def test_emit_projection_receipt_writes_stable_fields(self) -> None:
        projection = json.loads((ROOT / "fixtures" / "controls" / "projection-receipt.json").read_text())

        receipt_path = self.repo_root / "artifacts" / "projection-receipt.json"
        receipt = emit_projection_receipt(
            root=self.repo_root,
            output_path=receipt_path,
            projection_payload=projection,
        )

        stored = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(stored["schema_version"], "ctxvault.projection-receipt/v1")
        self.assertEqual(stored["projection_id"], projection["projection_id"])
        self.assertEqual(stored["target_kind"], "harness.agents-md")
        self.assertEqual(stored["plugin_id"], "portable-harness-projection")
        self.assertEqual(stored["plan_ledger_artifact"]["artifact_type"], "ctxvault_projection_receipt")
        self.assertIn("ctxvault_projection_receipt", stored["plan_ledger_artifact"]["suggested_command_template"])
        self.assertEqual(receipt["receipt_path"], str(receipt_path.resolve()))


if __name__ == "__main__":
    unittest.main()
