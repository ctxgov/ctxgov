from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_context_injection_m1_golden_path.py"


class ContextInjectionM1GoldenPathTests(unittest.TestCase):
    def run_golden_path(self, root: Path) -> dict:
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_command_emits_source_grounded_outputs_and_projection_receipts(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "m1"
            summary = self.run_golden_path(root)

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["source_gathering"]["project_doc_count"], 2)
            self.assertEqual(summary["source_gathering"]["knowledge_source_count"], 1)
            self.assertEqual(summary["source_gathering"]["session_id"], "sess_m1_context_injection_001")
            self.assertEqual(summary["source_gathering"]["turn_count"], 3)
            self.assertIn("memory://mem_m1_context_injection_approved", summary["context_bundle"]["input_refs"])

            for output_key, target_kind in [
                ("agents_md", "harness.agents-md"),
                ("claude_md", "harness.claude-md"),
                ("workstream_md", "wiki.markdown-workstream"),
            ]:
                output = summary["injected_outputs"][output_key]
                output_path = Path(output["output_path"])
                receipt_path = Path(output["receipt_path"])
                self.assertTrue(output_path.exists())
                self.assertTrue(receipt_path.exists())

                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["schema_version"], "ctxvault.projection-receipt/v1")
                self.assertEqual(receipt["target_kind"], target_kind)
                self.assertEqual(receipt["policy_decision"], "allow")
                self.assertEqual(receipt["output_status"], "written")
                self.assertEqual(receipt["output_sha256"], _sha256(output_path))
                self.assertEqual(receipt["review_state"], "approved")
                self.assertEqual(
                    receipt["source_refs"],
                    [
                        "workstream://ws_m1_context_injection_source_to_injection",
                        "memory://mem_m1_context_injection_approved",
                    ],
                )

            agents_text = Path(summary["injected_outputs"]["agents_md"]["output_path"]).read_text(encoding="utf-8")
            claude_text = Path(summary["injected_outputs"]["claude_md"]["output_path"]).read_text(encoding="utf-8")
            workstream_text = Path(summary["injected_outputs"]["workstream_md"]["output_path"]).read_text(encoding="utf-8")

            for rendered in [agents_text, claude_text, workstream_text]:
                self.assertIn("Context Injection M1 source-to-injection workstream", rendered)
                self.assertIn("session://sess_m1_context_injection_001", rendered)
                self.assertIn("knowledge://", rendered)
                self.assertIn(
                    "Context Injection M1 should inject only reviewed workstream context",
                    rendered,
                )

            self.assertTrue(Path(summary["source_gathering"]["receipt_path"]).exists())
            self.assertTrue(Path(summary["workstream_receipt"]["receipt_path"]).exists())
            self.assertTrue(Path(summary["summary_path"]).exists())

    def test_rejected_and_unreviewed_material_is_not_injected(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "m1"
            summary = self.run_golden_path(root)

            rendered_outputs = "\n".join(
                Path(output["output_path"]).read_text(encoding="utf-8")
                for output in summary["injected_outputs"].values()
            )
            self.assertNotIn("REJECTED_SENTINEL_M1_CONTEXT_INJECTION", rendered_outputs)
            self.assertNotIn("UNREVIEWED_SENTINEL_M1_CONTEXT_INJECTION", rendered_outputs)
            self.assertNotIn("memory-candidate://memc_m1_context_injection_rejected", rendered_outputs)
            self.assertNotIn("memory-candidate://memc_m1_context_injection_unreviewed", rendered_outputs)

            for output in summary["injected_outputs"].values():
                receipt = json.loads(Path(output["receipt_path"]).read_text(encoding="utf-8"))
                self.assertNotIn("memory://mem_m1_context_injection_rejected", receipt["source_refs"])
                self.assertNotIn("memory://mem_m1_context_injection_unreviewed", receipt["source_refs"])
                self.assertNotIn("memory-candidate://memc_m1_context_injection_rejected", receipt["source_refs"])
                self.assertNotIn("memory-candidate://memc_m1_context_injection_unreviewed", receipt["source_refs"])

            rejected_candidate = _stored_payload(
                root,
                "memory_candidate",
                "memc_m1_context_injection_rejected",
            )
            unreviewed_candidate = _stored_payload(
                root,
                "memory_candidate",
                "memc_m1_context_injection_unreviewed",
            )
            self.assertEqual(rejected_candidate["proposal_state"], "rejected")
            self.assertEqual(unreviewed_candidate["proposal_state"], "proposed")
            self.assertFalse((root / ".ctxvault" / "objects" / "memory" / "mem_m1_context_injection_rejected.json").exists())
            self.assertFalse((root / ".ctxvault" / "objects" / "memory" / "mem_m1_context_injection_unreviewed.json").exists())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stored_payload(root: Path, object_kind: str, object_id: str) -> dict:
    path = root / ".ctxvault" / "objects" / object_kind / f"{object_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))["payload"]


if __name__ == "__main__":
    unittest.main()
