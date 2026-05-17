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

from ctxgov.share_handoff import (
    list_share_handoffs,
    mark_share_handoff_consumed,
    preview_share_handoff,
    stage_share_handoff,
)


class ShareHandoffTests(unittest.TestCase):
    def test_stage_list_preview_and_archive_share_handoff(self) -> None:
        with TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            attachment = shared_root / "attachments" / "note.txt"
            attachment.parent.mkdir(parents=True, exist_ok=True)
            attachment.write_text("Keep mobile capture candidate-first.\n", encoding="utf-8")

            staged = stage_share_handoff(
                shared_root=shared_root,
                title="Mobile capture principle",
                text="The phone should stage candidates rather than write durable truth.",
                urls=["https://example.com/mobile"],
                attachment_paths=["attachments/note.txt"],
                source_app="share_extension",
            )
            listed = list_share_handoffs(shared_root=shared_root)
            preview = preview_share_handoff(
                shared_root=shared_root,
                handoff_path=Path(staged["handoff_path"]),
            )
            consumed = mark_share_handoff_consumed(
                shared_root=shared_root,
                handoff_path=Path(staged["handoff_path"]),
                preview_decision=preview["decision"],
                claim_ref="claim://claim_share_handoff_001",
                candidate_ref="memory-candidate://memc_share_handoff_001",
                consumed_by="share_handoff_test",
                consumption_notes="Reviewed in unit test.",
            )
            archived = list_share_handoffs(shared_root=shared_root, include_archived=True)

            self.assertEqual(staged["handoff"]["status"], "pending")
            self.assertEqual(staged["handoff"]["actions"], ["preview", "consume"])
            self.assertEqual(listed["summary"]["pending_count"], 1)
            self.assertEqual(preview["decision"], "allow")
            self.assertEqual(preview["capture_defaults"]["statement"], "Mobile capture principle")
            self.assertEqual(preview["resolved_attachment_paths"], [str(attachment.resolve())])
            self.assertEqual(consumed["handoff"]["status"], "consumed")
            self.assertEqual(consumed["handoff"]["actions"], [])
            self.assertEqual(consumed["handoff"]["claim_ref"], "claim://claim_share_handoff_001")
            self.assertEqual(archived["summary"]["pending_count"], 0)
            self.assertEqual(archived["summary"]["archived_count"], 1)
            archived_payload = json.loads(Path(consumed["handoff_path"]).read_text(encoding="utf-8"))
            self.assertNotIn("handoff_path", archived_payload)
            self.assertEqual(archived_payload["consumed_by"], "share_handoff_test")

    def test_preview_blocks_sensitive_share_handoff(self) -> None:
        with TemporaryDirectory() as tmpdir:
            shared_root = Path(tmpdir)
            attachment = shared_root / "attachments" / "secret.txt"
            attachment.parent.mkdir(parents=True, exist_ok=True)
            attachment.write_text('OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"\n', encoding="utf-8")

            staged = stage_share_handoff(
                shared_root=shared_root,
                text='Contact chris@example.com about OPENAI_API_KEY="sk-1234567890abcdefghijklmnop"',
                attachment_paths=["attachments/secret.txt"],
            )
            preview = preview_share_handoff(
                shared_root=shared_root,
                handoff_path=Path(staged["handoff_path"]),
            )

            self.assertEqual(preview["decision"], "block")
            self.assertEqual(preview["highest_severity"], "critical")
            self.assertEqual(preview["attachment_preflight"]["files"][0]["decision"], "block")


if __name__ == "__main__":
    unittest.main()
