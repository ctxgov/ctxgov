from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov.core import ContextBuildRequest, CtxVault
from ctxgov.ingest import import_conversation_path, import_knowledge_path, import_prompt_path, import_transcript_path
from ctxgov.layout import default_layout


class IngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_import_knowledge_path_ingests_documents_and_infers_project_profile(self) -> None:
        docs_root = self.repo_root / "knowledge-source"
        docs_root.mkdir()
        (docs_root / "README.md").write_text("# Trial Notes\n\nCtxVault keeps local knowledge grounded.\n", encoding="utf-8")
        (docs_root / "raw").mkdir()
        (docs_root / "raw" / "ignored.json").write_text("{}", encoding="utf-8")

        canonical_root = self.repo_root / "canonical" / "projects"
        canonical_root.mkdir(parents=True)
        (canonical_root / "ctxvault.json").write_text(
            json.dumps(
                {
                    "kind": "canonical_project",
                    "title": "ctxvault",
                    "current_summary": "Local-first context layer with deterministic retrieval.",
                    "claims": ["CtxVault keeps durable local evidence."],
                }
            ),
            encoding="utf-8",
        )

        receipts = import_knowledge_path(
            self.vault,
            self.repo_root,
            scope_kind="project",
            scope_value="ctxvault",
            recursive=True,
        )

        self.assertEqual(len(receipts), 2)
        profile_hits = self.vault.search_knowledge("deterministic retrieval", scope=("project", "ctxvault"), limit=5)
        self.assertTrue(any(hit.payload["kind"] == "project_profile" for hit in profile_hits))

        note_hits = self.vault.search_knowledge("grounded", scope=("project", "ctxvault"), limit=5)
        self.assertTrue(any("local knowledge grounded" in hit.payload["body"] for hit in note_hits))

    def test_build_context_keeps_project_profile_even_when_query_matches_other_docs(self) -> None:
        knowledge_root = self.repo_root / "knowledge"
        knowledge_root.mkdir()
        (knowledge_root / "research.md").write_text(
            "# Research\n\nMCP and local memory architecture are central to ctxvault.\n",
            encoding="utf-8",
        )

        canonical_root = self.repo_root / "canonical" / "projects"
        canonical_root.mkdir(parents=True)
        (canonical_root / "ctxvault.json").write_text(
            json.dumps(
                {
                    "kind": "canonical_project",
                    "title": "ctxvault",
                    "current_summary": "Local-first context layer with deterministic retrieval.",
                    "claims": ["Project profile should remain visible in context bundles."],
                }
            ),
            encoding="utf-8",
        )

        import_knowledge_path(self.vault, knowledge_root, scope_kind="project", scope_value="ctxvault", recursive=True)
        import_knowledge_path(self.vault, canonical_root, scope_kind="project", scope_value="ctxvault", recursive=True)

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="Plan local app",
                knowledge_query="MCP local memory architecture",
            )
        )

        self.assertTrue(
            any("Local-first context layer with deterministic retrieval." in item["content"] for item in bundle["sections"]["project_context"])
        )

    def test_import_prompt_path_supports_text_file_prompts(self) -> None:
        prompt_path = self.repo_root / "prompts" / "schema-designer.md"
        prompt_path.parent.mkdir(parents=True)
        prompt_path.write_text(
            "---\n"
            "id: schema-designer-v2\n"
            "skill: schema_design\n"
            "---\n\n"
            "# SYSTEM\n\n"
            "Write an explicit object model with storage and governance notes.\n",
            encoding="utf-8",
        )

        receipt = import_prompt_path(
            self.vault,
            prompt_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        resolved = self.vault.resolve_prompt(receipt.object_id)
        self.assertEqual(resolved.object_id, "schema-designer-v2")
        self.assertIn("explicit object model", resolved.instruction)
        self.assertFalse(resolved.instruction.startswith("---"))
        self.assertEqual(resolved.payload["intent"], "schema_design")
        self.assertEqual(resolved.payload["name"], "Schema Designer V2")

    def test_import_transcript_path_writes_session_and_turns(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "demo.json"
        transcript_path.parent.mkdir(parents=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_demo",
                    "title": "Demo Transcript",
                    "task_label": "Review ctxvault architecture",
                    "turns": [
                        {"id": "turn_demo_001", "role": "user", "content": "How should ctxvault ingest local knowledge?"},
                        {"role": "assistant", "content": "Use deterministic typed imports first."},
                    ],
                }
            ),
            encoding="utf-8",
        )

        receipt = import_transcript_path(
            self.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(receipt.session.object_id, "sess_demo")
        self.assertEqual(len(receipt.turns), 2)

        session_payload = json.loads(
            (self.repo_root / ".ctxvault" / "objects" / "session" / "sess_demo.json").read_text(encoding="utf-8")
        )["payload"]
        turn_payload = json.loads(
            (self.repo_root / ".ctxvault" / "objects" / "turn" / "turn_demo_001.json").read_text(encoding="utf-8")
        )["payload"]

        self.assertEqual(session_payload["client"], "local_import")
        self.assertEqual(session_payload["source_app"], "unknown")
        self.assertEqual(session_payload["source_surface"], "local")
        self.assertEqual(session_payload["source_format"], "normalized_transcript")
        self.assertEqual(session_payload["capture_method"], "file_import")
        self.assertEqual(session_payload["imported_via"], "ctxvault_import")
        self.assertEqual(turn_payload["source_app"], "unknown")
        self.assertEqual(turn_payload["source_surface"], "local")
        self.assertEqual(turn_payload["source_format"], "normalized_transcript")
        self.assertEqual(turn_payload["capture_method"], "file_import")
        self.assertEqual(turn_payload["imported_via"], "ctxvault_import")

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        rows = connection.execute(
            "SELECT object_kind, object_id FROM object_index WHERE object_id IN (?, ?, ?)",
            ("sess_demo", "turn_demo_001", "sess_demo_turn_0002"),
        ).fetchall()
        connection.close()

        self.assertEqual(
            sorted(rows),
            [
                ("session", "sess_demo"),
                ("turn", "sess_demo_turn_0002"),
                ("turn", "turn_demo_001"),
            ],
        )

    def test_import_conversation_path_supports_chatgpt_export_and_picks_latest_branch(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "chatgpt-export.json"
        transcript_path.parent.mkdir(parents=True)
        transcript_path.write_text(
            json.dumps(
                [
                    {
                        "title": "Async Help",
                        "create_time": 1710000000.0,
                        "update_time": 1710000500.0,
                        "mapping": {
                            "root": {"id": "root", "parent": None, "children": ["user1"], "message": None},
                            "user1": {
                                "id": "user1",
                                "parent": "root",
                                "children": ["assistant1"],
                                "message": {
                                    "id": "user1",
                                    "author": {"role": "user"},
                                    "create_time": 1710000010.0,
                                    "content": {"content_type": "text", "parts": ["Explain async await"]},
                                },
                            },
                            "assistant1": {
                                "id": "assistant1",
                                "parent": "user1",
                                "children": ["old_branch", "new_branch"],
                                "message": {
                                    "id": "assistant1",
                                    "author": {"role": "assistant"},
                                    "create_time": 1710000020.0,
                                    "content": {"content_type": "text", "parts": ["Coroutines suspend and resume."]},
                                },
                            },
                            "old_branch": {
                                "id": "old_branch",
                                "parent": "assistant1",
                                "children": [],
                                "message": {
                                    "id": "old_branch",
                                    "author": {"role": "user"},
                                    "create_time": 1710000100.0,
                                    "content": {"content_type": "text", "parts": ["Show event loop details"]},
                                },
                            },
                            "new_branch": {
                                "id": "new_branch",
                                "parent": "assistant1",
                                "children": [],
                                "message": {
                                    "id": "new_branch",
                                    "author": {"role": "user"},
                                    "create_time": 1710000400.0,
                                    "content": {"content_type": "text", "parts": ["Show asyncio.gather"]},
                                },
                            },
                        },
                    }
                ]
            ),
            encoding="utf-8",
        )

        receipts = import_conversation_path(
            self.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(len(receipts), 1)
        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        rows = connection.execute(
            "SELECT storage_path FROM object_index WHERE object_kind = 'turn' ORDER BY object_id ASC"
        ).fetchall()
        connection.close()

        payloads = [json.loads(Path(row[0]).read_text(encoding="utf-8"))["payload"] for row in rows]
        self.assertEqual([payload["id"] for payload in payloads], ["assistant1", "new_branch", "user1"])
        self.assertTrue(any(payload["content"] == "Show asyncio.gather" for payload in payloads))
        self.assertFalse(any(payload["content"] == "Show event loop details" for payload in payloads))

    def test_import_conversation_path_supports_claude_and_gemini_exports(self) -> None:
        claude_path = self.repo_root / "transcripts" / "claude-export.json"
        claude_path.parent.mkdir(parents=True, exist_ok=True)
        claude_path.write_text(
            json.dumps(
                [
                    {
                        "uuid": "conv_001",
                        "name": "Claude Demo",
                        "created_at": "2026-03-01T10:00:00.000000Z",
                        "updated_at": "2026-03-01T10:05:00.000000Z",
                        "chat_messages": [
                            {
                                "uuid": "claude_msg_001",
                                "sender": "human",
                                "text": "Explain quantum computing",
                                "created_at": "2026-03-01T10:00:10.000000Z",
                            },
                            {
                                "uuid": "claude_msg_002",
                                "sender": "assistant",
                                "content": [{"type": "text", "text": "Quantum computing uses qubits."}],
                                "created_at": "2026-03-01T10:00:30.000000Z",
                            },
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )
        gemini_path = self.repo_root / "transcripts" / "gemini-session.json"
        gemini_path.write_text(
            json.dumps(
                {
                    "sessionId": "gemini_sess_001",
                    "projectHash": "proj_hash",
                    "startTime": "2026-03-10T14:23:00.000Z",
                    "lastUpdated": "2026-03-10T14:45:00.000Z",
                    "messages": [
                        {
                            "id": "gemini_msg_001",
                            "type": "user",
                            "content": "fix login.py",
                            "timestamp": "2026-03-10T14:23:01.000Z",
                        },
                        {
                            "id": "gemini_msg_002",
                            "type": "gemini",
                            "content": [{"text": "I will update the token validation logic."}],
                            "timestamp": "2026-03-10T14:23:05.000Z",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        claude_receipts = import_conversation_path(
            self.vault,
            claude_path,
            scope_kind="project",
            scope_value="ctxvault",
        )
        gemini_receipts = import_conversation_path(
            self.vault,
            gemini_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(len(claude_receipts), 1)
        self.assertEqual(len(gemini_receipts), 1)
        self.assertEqual(claude_receipts[0].session.object_id, "conv_001")
        self.assertEqual(gemini_receipts[0].session.object_id, "gemini_sess_001")

        claude_session = json.loads(
            (self.repo_root / ".ctxvault" / "objects" / "session" / "conv_001.json").read_text(encoding="utf-8")
        )["payload"]
        gemini_session = json.loads(
            (self.repo_root / ".ctxvault" / "objects" / "session" / "gemini_sess_001.json").read_text(encoding="utf-8")
        )["payload"]

        self.assertEqual(claude_session["source_app"], "claude")
        self.assertEqual(claude_session["source_surface"], "export")
        self.assertEqual(claude_session["source_format"], "claude_export")
        self.assertEqual(claude_session["capture_method"], "file_import")
        self.assertEqual(claude_session["imported_via"], "ctxvault_import")
        self.assertEqual(gemini_session["source_app"], "gemini")
        self.assertEqual(gemini_session["source_surface"], "export")
        self.assertEqual(gemini_session["source_format"], "gemini_export")
        self.assertEqual(gemini_session["capture_method"], "file_import")
        self.assertEqual(gemini_session["imported_via"], "ctxvault_import")

    def test_import_conversation_path_supports_deepseek_and_ollama_experimental_adapters(self) -> None:
        deepseek_path = self.repo_root / "transcripts" / "deepseek-export.json"
        deepseek_path.parent.mkdir(parents=True, exist_ok=True)
        deepseek_path.write_text(
            json.dumps(
                {
                    "source_app": "deepseek",
                    "conversation_id": "deepseek_conv_001",
                    "title": "DeepSeek Demo",
                    "created_at": "2026-04-28T10:00:00+08:00",
                    "updated_at": "2026-04-28T10:05:00+08:00",
                    "messages": [
                        {
                            "id": "deepseek_msg_001",
                            "role": "user",
                            "content": "How should v0.2 describe named source coverage?",
                            "created_at": "2026-04-28T10:00:20+08:00",
                        },
                        {
                            "id": "deepseek_msg_002",
                            "role": "assistant",
                            "content": {"text": "Use normalized fallback unless an experimental adapter matches the source shape."},
                            "created_at": "2026-04-28T10:01:10+08:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        ollama_path = self.repo_root / "transcripts" / "ollama-ui-export.json"
        ollama_path.write_text(
            json.dumps(
                {
                    "source_app": "ollama",
                    "id": "ollama_chat_001",
                    "chat": {
                        "title": "Ollama UI Demo",
                        "history": {
                            "messages": [
                                {
                                    "id": "ollama_msg_001",
                                    "role": "user",
                                    "content": "Can a local UI transcript become a workstream candidate?",
                                    "timestamp": "2026-04-28T10:10:00+08:00",
                                },
                                {
                                    "id": "ollama_msg_002",
                                    "role": "assistant",
                                    "content": [{"text": "Yes, after source-shape gated normalization and review candidate creation."}],
                                    "timestamp": "2026-04-28T10:11:00+08:00",
                                },
                            ]
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        deepseek_receipts = import_conversation_path(
            self.vault,
            deepseek_path,
            scope_kind="project",
            scope_value="ctxvault",
        )
        ollama_receipts = import_conversation_path(
            self.vault,
            ollama_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(deepseek_receipts[0].session.object_id, "deepseek_conv_001")
        self.assertEqual(ollama_receipts[0].session.object_id, "ollama_chat_001")
        self.assertEqual(deepseek_receipts[0].source_connector.connector_id, "connector.deepseek.experimental")
        self.assertEqual(ollama_receipts[0].source_connector.connector_id, "connector.ollama-ui.experimental")
        self.assertIn("experimental", deepseek_receipts[0].source_connector.warnings[0])
        self.assertIn("experimental", ollama_receipts[0].source_connector.warnings[0])

        deepseek_session = json.loads(
            (self.repo_root / ".ctxvault" / "objects" / "session" / "deepseek_conv_001.json").read_text(encoding="utf-8")
        )["payload"]
        ollama_session = json.loads(
            (self.repo_root / ".ctxvault" / "objects" / "session" / "ollama_chat_001.json").read_text(encoding="utf-8")
        )["payload"]

        self.assertEqual(deepseek_session["source_app"], "deepseek")
        self.assertEqual(deepseek_session["source_format"], "deepseek_messages_export")
        self.assertEqual(ollama_session["source_app"], "ollama")
        self.assertEqual(ollama_session["source_surface"], "local_ui_export")
        self.assertEqual(ollama_session["source_format"], "ollama_ui_messages_export")

    def test_import_conversation_path_supports_claude_export_zip(self) -> None:
        archive_path = self.repo_root / "transcripts" / "claude-export.zip"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        claude_export = [
            {
                "uuid": "conv_001",
                "name": "Claude Demo",
                "created_at": "2026-03-01T10:00:00.000000Z",
                "updated_at": "2026-03-01T10:05:00.000000Z",
                "chat_messages": [
                    {
                        "uuid": "claude_msg_001",
                        "sender": "human",
                        "text": "Explain quantum computing",
                        "created_at": "2026-03-01T10:00:10.000000Z",
                    },
                    {
                        "uuid": "claude_msg_002",
                        "sender": "assistant",
                        "content": [{"type": "text", "text": "Quantum computing uses qubits."}],
                        "created_at": "2026-03-01T10:00:30.000000Z",
                    },
                ],
            }
        ]
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("conversations.json", json.dumps(claude_export))

        receipts = import_conversation_path(
            self.vault,
            archive_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].session.object_id, "conv_001")
        self.assertEqual(receipts[0].session.source_path, archive_path.resolve())

    def test_import_conversation_path_supports_export_directory(self) -> None:
        export_root = self.repo_root / "transcripts" / "claude-export"
        export_root.mkdir(parents=True, exist_ok=True)
        (export_root / "nested").mkdir()
        (export_root / "nested" / "conversations.json").write_text(
            json.dumps(
                [
                    {
                        "uuid": "conv_001",
                        "name": "Claude Demo",
                        "created_at": "2026-03-01T10:00:00.000000Z",
                        "updated_at": "2026-03-01T10:05:00.000000Z",
                        "chat_messages": [
                            {
                                "uuid": "claude_msg_001",
                                "sender": "human",
                                "text": "Explain quantum computing",
                                "created_at": "2026-03-01T10:00:10.000000Z",
                            },
                            {
                                "uuid": "claude_msg_002",
                                "sender": "assistant",
                                "content": [{"type": "text", "text": "Quantum computing uses qubits."}],
                                "created_at": "2026-03-01T10:00:30.000000Z",
                            },
                        ],
                    }
                ]
            ),
            encoding="utf-8",
        )

        receipts = import_conversation_path(
            self.vault,
            export_root,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].session.object_id, "conv_001")
        self.assertEqual(receipts[0].session.source_path, (export_root / "nested" / "conversations.json").resolve())

    def test_import_conversation_path_skips_empty_claude_entries_in_export_arrays(self) -> None:
        claude_path = self.repo_root / "transcripts" / "claude-export.json"
        claude_path.parent.mkdir(parents=True, exist_ok=True)
        claude_path.write_text(
            json.dumps(
                [
                    {
                        "uuid": "conv_empty",
                        "name": "Empty Claude Conversation",
                        "chat_messages": [],
                    },
                    {
                        "uuid": "conv_001",
                        "name": "Claude Demo",
                        "created_at": "2026-03-01T10:00:00.000000Z",
                        "updated_at": "2026-03-01T10:05:00.000000Z",
                        "chat_messages": [
                            {
                                "uuid": "claude_msg_001",
                                "sender": "human",
                                "text": "Explain quantum computing",
                                "created_at": "2026-03-01T10:00:10.000000Z",
                            },
                            {
                                "uuid": "claude_msg_002",
                                "sender": "assistant",
                                "content": [{"type": "text", "text": "Quantum computing uses qubits."}],
                                "created_at": "2026-03-01T10:00:30.000000Z",
                            },
                        ],
                    },
                ]
            ),
            encoding="utf-8",
        )

        receipts = import_conversation_path(
            self.vault,
            claude_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0].session.object_id, "conv_001")

    def test_import_conversation_path_rejects_export_arrays_without_importable_conversations(self) -> None:
        claude_path = self.repo_root / "transcripts" / "claude-export-empty.json"
        claude_path.parent.mkdir(parents=True, exist_ok=True)
        claude_path.write_text(
            json.dumps(
                [
                    {
                        "uuid": "conv_empty",
                        "name": "Empty Claude Conversation",
                        "chat_messages": [],
                    }
                ]
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "did not contain any importable conversations"):
            import_conversation_path(
                self.vault,
                claude_path,
                scope_kind="project",
                scope_value="ctxvault",
            )


if __name__ == "__main__":
    unittest.main()
