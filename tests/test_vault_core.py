from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.core import ContextBuildRequest, ContextItemInput, CtxVault
from ctxvault.ingest import import_transcript_path
from ctxvault.layout import default_layout


class VaultCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = TemporaryDirectory()
        self.repo_root = Path(self._tmpdir.name)
        self.vault = CtxVault(default_layout(self.repo_root))
        self.fixture_root = ROOT / "fixtures" / "core"

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _fixture(self, name: str) -> dict:
        return json.loads((self.fixture_root / name).read_text())

    def test_store_core_object_writes_envelope_and_projection(self) -> None:
        envelope = self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        stored_path = self.repo_root / ".ctxvault" / "objects" / "prompt_asset" / "prompt_schema_designer_v1.json"

        self.assertTrue(stored_path.exists())
        stored_payload = json.loads(stored_path.read_text())
        self.assertEqual(stored_payload["object_id"], "prompt_schema_designer_v1")
        self.assertEqual(stored_payload["content_sha256"], envelope.content_sha256)

        connection = sqlite3.connect(self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3")
        row = connection.execute(
            "SELECT object_kind, storage_ref FROM object_index WHERE object_id = ?",
            ("prompt_schema_designer_v1",),
        ).fetchone()
        prompt_row = connection.execute(
            "SELECT instruction FROM prompt_assets WHERE object_id = ?",
            ("prompt_schema_designer_v1",),
        ).fetchone()
        connection.close()

        self.assertEqual(row, ("prompt_asset", "vault://objects/prompt_asset/prompt_schema_designer_v1.json"))
        self.assertIn("explicit object types", prompt_row[0])

    def test_prompt_memory_and_context_primitives_run_over_sqlite_projection(self) -> None:
        self.vault.store_core_object("PromptAsset", self._fixture("prompt-asset.json"))
        self.vault.store_core_object("Memory", self._fixture("memory.json"))
        self.vault.store_core_object("KnowledgeArtifact", self._fixture("knowledge-artifact.json"))

        resolved = self.vault.resolve_prompt("prompt_schema_designer_v1")
        prompts = self.vault.list_prompts(scope=("project", "ctxvault"), limit=3)
        memories = self.vault.search_memories("local LLM", scope=("project", "ctxvault"), limit=3)

        self.assertEqual(resolved.object_id, "prompt_schema_designer_v1")
        self.assertEqual(prompts[0].object_id, "prompt_schema_designer_v1")
        self.assertEqual(memories[0].object_id, "mem_20260419_ctxvault_rule_001")

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="continue schema work",
                prompt_id="prompt_schema_designer_v1",
                memory_query="local LLM",
                knowledge_query="local-first context layer",
            )
        )

        self.assertEqual(bundle["scope"]["value"], "ctxvault")
        self.assertTrue(any(item["ref"] == "memory://mem_20260419_ctxvault_rule_001" for item in bundle["sections"]["core_rules"]))
        self.assertTrue(any(item["ref"] == "knowledge://know_proj_ctxvault_profile_v1" for item in bundle["sections"]["project_context"]))
        self.assertIn("vault://objects/prompt_asset/prompt_schema_designer_v1.json", bundle["sections"]["source_pointers"])

        bundle_path = self.repo_root / ".ctxvault" / "objects" / "context_bundle" / f"{bundle['id']}.json"
        self.assertTrue(bundle_path.exists())

    def test_build_context_hydrates_recent_conversation_from_stored_turns(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "demo.json"
        transcript_path.parent.mkdir(parents=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_demo",
                    "title": "Demo Transcript",
                    "turns": [
                        {
                            "id": "turn_demo_001",
                            "role": "user",
                            "content": "How should ctxvault ingest local knowledge?",
                            "created_at": "2026-04-20T10:00:00+00:00",
                        },
                        {
                            "id": "turn_demo_002",
                            "role": "assistant",
                            "content": "Use deterministic typed imports first.",
                            "created_at": "2026-04-20T10:00:10+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        import_transcript_path(
            self.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="continue schema work",
                max_recent_turns=4,
            )
        )

        self.assertEqual(
            bundle["sections"]["recent_conversation"],
            [
                {"ref": "turn://turn_demo_001", "content": "user: How should ctxvault ingest local knowledge?"},
                {"ref": "turn://turn_demo_002", "content": "assistant: Use deterministic typed imports first."},
            ],
        )
        self.assertIn("turn://turn_demo_002", bundle["input_refs"])

    def test_build_context_prefers_explicit_recent_conversation_inputs(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "demo.json"
        transcript_path.parent.mkdir(parents=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_demo",
                    "title": "Demo Transcript",
                    "turns": [
                        {"id": "turn_demo_001", "role": "user", "content": "vault internals"},
                        {"id": "turn_demo_002", "role": "assistant", "content": "deterministic imports"},
                    ],
                }
            ),
            encoding="utf-8",
        )

        import_transcript_path(
            self.vault,
            transcript_path,
            scope_kind="project",
            scope_value="ctxvault",
        )

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="continue schema work",
                recent_conversation=(ContextItemInput(ref="turn://manual", content="user: live scratch note"),),
            )
        )

        self.assertEqual(
            bundle["sections"]["recent_conversation"],
            [{"ref": "turn://manual", "content": "user: live scratch note"}],
        )

    def test_build_context_uses_latest_session_for_recent_conversation(self) -> None:
        transcript_a = self.repo_root / "transcripts" / "older.json"
        transcript_a.parent.mkdir(parents=True, exist_ok=True)
        transcript_a.write_text(
            json.dumps(
                {
                    "id": "sess_older",
                    "title": "Older Transcript",
                    "turns": [
                        {
                            "id": "turn_old_001",
                            "role": "user",
                            "content": "older question",
                            "created_at": "2026-04-20T09:00:00+00:00",
                        },
                        {
                            "id": "turn_old_002",
                            "role": "assistant",
                            "content": "older answer",
                            "created_at": "2026-04-20T09:00:10+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        transcript_b = self.repo_root / "transcripts" / "latest.json"
        transcript_b.write_text(
            json.dumps(
                {
                    "id": "sess_latest",
                    "title": "Latest Transcript",
                    "turns": [
                        {
                            "id": "turn_new_001",
                            "role": "user",
                            "content": "latest question",
                            "created_at": "2026-04-20T10:00:00+00:00",
                        },
                        {
                            "id": "turn_new_002",
                            "role": "assistant",
                            "content": "latest answer",
                            "created_at": "2026-04-20T10:00:10+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        import_transcript_path(
            self.vault,
            transcript_a,
            scope_kind="project",
            scope_value="ctxvault",
        )
        import_transcript_path(
            self.vault,
            transcript_b,
            scope_kind="project",
            scope_value="ctxvault",
        )

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="continue schema work",
                max_recent_turns=4,
            )
        )

        self.assertEqual(
            bundle["sections"]["recent_conversation"],
            [
                {"ref": "turn://turn_new_001", "content": "user: latest question"},
                {"ref": "turn://turn_new_002", "content": "assistant: latest answer"},
            ],
        )

    def test_build_context_supports_explicit_session_selection(self) -> None:
        transcript_a = self.repo_root / "transcripts" / "older.json"
        transcript_a.parent.mkdir(parents=True, exist_ok=True)
        transcript_a.write_text(
            json.dumps(
                {
                    "id": "sess_older",
                    "title": "Older Transcript",
                    "turns": [
                        {
                            "id": "turn_old_001",
                            "role": "user",
                            "content": "older question",
                            "created_at": "2026-04-20T09:00:00+00:00",
                        },
                        {
                            "id": "turn_old_002",
                            "role": "assistant",
                            "content": "older answer",
                            "created_at": "2026-04-20T09:00:10+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        transcript_b = self.repo_root / "transcripts" / "latest.json"
        transcript_b.write_text(
            json.dumps(
                {
                    "id": "sess_latest",
                    "title": "Latest Transcript",
                    "turns": [
                        {
                            "id": "turn_new_001",
                            "role": "user",
                            "content": "latest question",
                            "created_at": "2026-04-20T10:00:00+00:00",
                        },
                        {
                            "id": "turn_new_002",
                            "role": "assistant",
                            "content": "latest answer",
                            "created_at": "2026-04-20T10:00:10+00:00",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        import_transcript_path(
            self.vault,
            transcript_a,
            scope_kind="project",
            scope_value="ctxvault",
        )
        import_transcript_path(
            self.vault,
            transcript_b,
            scope_kind="project",
            scope_value="ctxvault",
        )

        bundle = self.vault.build_context(
            ContextBuildRequest(
                scope_kind="project",
                scope_value="ctxvault",
                task_label="continue schema work",
                session_id="sess_older",
                max_recent_turns=4,
            )
        )

        self.assertEqual(
            bundle["sections"]["recent_conversation"],
            [
                {"ref": "turn://turn_old_001", "content": "user: older question"},
                {"ref": "turn://turn_old_002", "content": "assistant: older answer"},
            ],
        )
        self.assertEqual(bundle["assembly_policy"]["session_id"], "sess_older")

    def test_build_context_rejects_unknown_session_selection(self) -> None:
        with self.assertRaisesRegex(ValueError, "did not contain stored turns"):
            self.vault.build_context(
                ContextBuildRequest(
                    scope_kind="project",
                    scope_value="ctxvault",
                    task_label="continue schema work",
                    session_id="sess_missing",
                )
            )

    def test_list_and_search_sessions_return_recent_matches_with_turn_counts(self) -> None:
        transcript_a = self.repo_root / "transcripts" / "older.json"
        transcript_a.parent.mkdir(parents=True, exist_ok=True)
        transcript_a.write_text(
            json.dumps(
                {
                    "id": "sess_older",
                    "title": "Older Transcript",
                    "task_label": "Review older design",
                    "turns": [
                        {"id": "turn_old_001", "role": "user", "content": "older question"},
                        {"id": "turn_old_002", "role": "assistant", "content": "older answer"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        transcript_b = self.repo_root / "transcripts" / "latest.json"
        transcript_b.write_text(
            json.dumps(
                {
                    "id": "sess_latest",
                    "title": "Latest Transcript",
                    "source_app": "chatgpt",
                    "source_surface": "ios",
                    "source_format": "chatgpt_export",
                    "capture_method": "zip_import",
                    "task_label": "Design local app",
                    "turns": [
                        {"id": "turn_new_001", "role": "user", "content": "latest question"},
                        {"id": "turn_new_002", "role": "assistant", "content": "latest answer"},
                        {"id": "turn_new_003", "role": "user", "content": "follow up"},
                    ],
                }
            ),
            encoding="utf-8",
        )

        import_transcript_path(self.vault, transcript_a, scope_kind="project", scope_value="ctxvault")
        import_transcript_path(self.vault, transcript_b, scope_kind="project", scope_value="ctxvault")

        listed = self.vault.list_sessions(scope=("project", "ctxvault"), limit=10)
        searched = self.vault.search_sessions("design chatgpt zip_import", scope=("project", "ctxvault"), limit=10)

        self.assertEqual([hit.object_id for hit in listed[:2]], ["sess_latest", "sess_older"])
        self.assertEqual(searched[0].object_id, "sess_latest")
        self.assertEqual(searched[0].payload["turn_count"], 3)
        self.assertEqual(searched[0].payload["source_app"], "chatgpt")
        self.assertEqual(searched[0].payload["source_surface"], "ios")
        self.assertEqual(searched[0].payload["source_format"], "chatgpt_export")
        self.assertEqual(searched[0].payload["capture_method"], "zip_import")

    def test_search_sessions_backfills_source_provenance_for_legacy_projection_rows(self) -> None:
        transcript_path = self.repo_root / "transcripts" / "legacy.json"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(
            json.dumps(
                {
                    "id": "sess_legacy",
                    "title": "Legacy Transcript",
                    "source_app": "chatgpt",
                    "source_surface": "ios",
                    "source_format": "chatgpt_export",
                    "capture_method": "share_sheet",
                    "task_label": "Review mobile companion",
                    "turns": [
                        {"id": "turn_legacy_001", "role": "user", "content": "review mobile capture"},
                        {"id": "turn_legacy_002", "role": "assistant", "content": "keep the phone as a companion surface"},
                    ],
                }
            ),
            encoding="utf-8",
        )

        import_transcript_path(self.vault, transcript_path, scope_kind="project", scope_value="ctxvault")

        sqlite_path = self.repo_root / ".ctxvault" / "indexes" / "ctxvault.sqlite3"
        with closing(sqlite3.connect(sqlite_path)) as connection:
            connection.executescript(
                """
                ALTER TABLE sessions RENAME TO sessions_v1;
                CREATE TABLE sessions (
                  object_id TEXT PRIMARY KEY,
                  semantic_ref TEXT NOT NULL,
                  storage_ref TEXT NOT NULL,
                  storage_path TEXT NOT NULL,
                  scope_kind TEXT,
                  scope_value TEXT,
                  client TEXT NOT NULL,
                  title TEXT NOT NULL,
                  task_label TEXT NOT NULL,
                  status TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  ended_at TEXT,
                  turn_count INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO sessions (
                  object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
                  client, title, task_label, status, started_at, ended_at, turn_count
                )
                SELECT
                  object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
                  client, title, task_label, status, started_at, ended_at, turn_count
                FROM sessions_v1;
                DROP TABLE sessions_v1;
                """
            )
            columns = {row[1] for row in connection.execute('PRAGMA table_info("sessions")').fetchall()}
            self.assertNotIn("source_app", columns)
            self.assertNotIn("source_surface", columns)
            self.assertNotIn("source_format", columns)
            self.assertNotIn("capture_method", columns)

        searched = self.vault.search_sessions("chatgpt ios share_sheet", scope=("project", "ctxvault"), limit=10)

        self.assertEqual(searched[0].object_id, "sess_legacy")
        self.assertEqual(searched[0].payload["source_app"], "chatgpt")
        self.assertEqual(searched[0].payload["source_surface"], "ios")
        self.assertEqual(searched[0].payload["source_format"], "chatgpt_export")
        self.assertEqual(searched[0].payload["capture_method"], "share_sheet")

        with closing(sqlite3.connect(sqlite_path)) as connection:
            row = connection.execute(
                "SELECT source_app, source_surface, source_format, capture_method FROM sessions WHERE object_id = ?",
                ("sess_legacy",),
            ).fetchone()

        self.assertEqual(row, ("chatgpt", "ios", "chatgpt_export", "share_sheet"))


if __name__ == "__main__":
    unittest.main()
