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

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.policy import CtxVaultPolicy
from ctxvault.surface import CtxVaultSurface


class EndToEndSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.surface = CtxVaultSurface(CtxVault(default_layout(self.repo_root)))
        self.policy = json.loads((ROOT / "fixtures" / "controls" / "protection-policy.json").read_text())
        self.backup = CtxVaultPolicy.freshen_backup_receipt(
            json.loads((ROOT / "fixtures" / "controls" / "backup-check-receipt.json").read_text())
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_deterministic_end_to_end_flow(self) -> None:
        for fixture_name, model_name in [
            ("prompt-asset.json", "PromptAsset"),
            ("memory.json", "Memory"),
            ("knowledge-artifact.json", "KnowledgeArtifact"),
        ]:
            payload = json.loads((ROOT / "fixtures" / "core" / fixture_name).read_text())
            self.surface.trace_record(model_name, payload)

        claim = json.loads((ROOT / "fixtures" / "evidence" / "claim-record.json").read_text())
        evidence = json.loads((ROOT / "fixtures" / "evidence" / "evidence-link.json").read_text())
        self.surface.vault.capture_claim(claim)
        self.surface.vault.link_evidence(evidence)

        bundle = self.surface.context_build(
            {
                "scope_kind": "project",
                "scope_value": "ctxvault",
                "task_label": "deterministic e2e smoke",
                "prompt_id": "prompt_schema_designer_v1",
                "memory_query": "local LLM",
                "knowledge_query": "local-first context layer",
            }
        )
        audit = self.surface.audit_run(
            scope_kind="project",
            scope_value="ctxvault",
            subject_ref=claim["subject_ref"],
        )
        operation_gate = self.surface.policy_check(
            policy_payload=self.policy,
            operation="memory_promotion",
            sensitivity="internal",
            backup_receipt=self.backup,
        )
        export_gate = self.surface.export_check(
            policy_payload=self.policy,
            sensitivity=bundle["sensitivity"],
            exportable=bundle["exportable"],
            redaction_state=bundle["redaction_state"],
            secret_refs=bundle["secret_refs"],
        )

        self.assertEqual(audit["verdict"], "supported_by_local_evidence")
        self.assertEqual(operation_gate["decision"], "review_required")
        self.assertEqual(export_gate["decision"], "allow")
        self.assertTrue(bundle["id"].startswith("bundle_"))


if __name__ == "__main__":
    unittest.main()
