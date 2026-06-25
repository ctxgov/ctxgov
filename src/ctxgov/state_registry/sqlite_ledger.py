"""SQLite revision ledger — append-only revisions + current pointer.

Per ADR-0003/ADR-0004/ADR-0015: stores immutable revision rows, a
mutable current pointer per state object, append-only evidence events,
and an outbox for at-least-once export. Uses WAL mode for local
single-writer concurrency (not network-filesystem safe per §21.2).

The schema is versioned via ``schema_meta``; migrations are append-only
columns + new tables, never destructive ALTER.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "SQLiteLedger",
    "RevisionRecord",
    "ConflictError",
    "SCHEMA_VERSION",
]

SCHEMA_VERSION = 1


class ConflictError(RuntimeError):
    """Raised when an optimistic compare-and-swap fails."""


@dataclass(frozen=True)
class RevisionRecord:
    revision_ref: str
    state_id: str
    canonical_digest: str
    payload_ref: str
    supersedes_ref: str | None
    created_at: str


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS state_objects (
    state_id TEXT PRIMARY KEY,
    tenant TEXT NOT NULL DEFAULT 'default',
    state_type TEXT NOT NULL,
    owner_ref TEXT,
    lifecycle TEXT NOT NULL DEFAULT 'active',
    current_revision_ref TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS state_revisions (
    revision_ref TEXT PRIMARY KEY,
    state_id TEXT NOT NULL REFERENCES state_objects(state_id),
    canonical_digest TEXT NOT NULL,
    payload_ref TEXT NOT NULL,
    supersedes_ref TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE(state_id, canonical_digest)
);

CREATE TABLE IF NOT EXISTS evidence_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_ref TEXT NOT NULL,
    event_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    occurred_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outbox (
    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_ref TEXT NOT NULL,
    destination TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS idempotency_records (
    key TEXT PRIMARY KEY,
    request_digest TEXT NOT NULL,
    result_ref TEXT NOT NULL,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_revisions_state_id
    ON state_revisions(state_id, created_at);
CREATE INDEX IF NOT EXISTS idx_events_source
    ON evidence_events(source_ref, occurred_at);
CREATE INDEX IF NOT EXISTS idx_outbox_pending
    ON outbox(status, next_attempt);
"""


class SQLiteLedger:
    """SQLite-backed revision ledger with optimistic concurrency."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(db_path),
            isolation_level=None,  # manual transaction control
            check_same_thread=False,
        )
        self._configure_pragmas()
        self._initialize_schema()

    def _configure_pragmas(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA journal_mode = WAL")
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("PRAGMA busy_timeout = 5000")
        cur.execute("PRAGMA synchronous = FULL")

    def _initialize_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(_SCHEMA_SQL)
        cur.execute(
            "INSERT OR IGNORE INTO schema_meta(key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )

    # ------------------------------------------------------------------
    # State objects + revisions
    # ------------------------------------------------------------------

    def ensure_state_object(
        self,
        *,
        state_id: str,
        tenant: str,
        state_type: str,
        owner_ref: str | None,
    ) -> None:
        """Insert a state object if it does not already exist."""
        self._conn.execute(
            "INSERT OR IGNORE INTO state_objects"
            " (state_id, tenant, state_type, owner_ref, lifecycle, current_revision_ref, updated_at)"
            " VALUES (?, ?, ?, ?, 'active', NULL, ?)",
            (state_id, tenant, state_type, owner_ref, _now()),
        )

    def get_current_revision_ref(self, state_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT current_revision_ref FROM state_objects WHERE state_id = ?",
            (state_id,),
        ).fetchone()
        return row[0] if row else None

    def append_revision(
        self,
        *,
        revision_ref: str,
        state_id: str,
        canonical_digest: str,
        payload_ref: str,
        supersedes_ref: str | None,
        metadata: dict[str, Any],
        created_at: str,
    ) -> RevisionRecord:
        """Append an immutable revision row. Idempotent on (state_id, digest).

        Returns the stored record. Raises if the revision_ref already
        exists with different content (indicates a hash collision or
        programming error).
        """
        import json

        cur = self._conn.cursor()
        cur.execute(
            "BEGIN IMMEDIATE",
        )
        try:
            cur.execute(
                "INSERT INTO state_revisions"
                " (revision_ref, state_id, canonical_digest, payload_ref,"
                "  supersedes_ref, metadata_json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(state_id, canonical_digest) DO UPDATE SET"
                "  revision_ref = excluded.revision_ref,"
                "  payload_ref = excluded.payload_ref"
                " WHERE state_revisions.canonical_digest = excluded.canonical_digest",
                (
                    revision_ref,
                    state_id,
                    canonical_digest,
                    payload_ref,
                    supersedes_ref,
                    json.dumps(metadata, sort_keys=True),
                    created_at,
                ),
            )
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise

        return RevisionRecord(
            revision_ref=revision_ref,
            state_id=state_id,
            canonical_digest=canonical_digest,
            payload_ref=payload_ref,
            supersedes_ref=supersedes_ref,
            created_at=created_at,
        )

    def commit_revision_transaction(
        self,
        *,
        state_id: str,
        tenant: str,
        state_type: str,
        owner_ref: str | None,
        revision_ref: str,
        canonical_digest: str,
        payload_ref: str,
        supersedes_ref: str | None,
        metadata: dict[str, Any],
        created_at: str,
        expected_revision_ref: str | None,
        event_source_ref: str,
        event_type: str,
        event_data: dict[str, Any],
        event_idempotency_key: str,
        outbox_destination: str,
        outbox_payload: dict[str, Any],
        idempotency_key: str,
        request_digest: str,
    ) -> str | None:
        """Atomically promote a revision and write event/outbox/idempotency rows."""
        import json

        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.execute(
                "INSERT OR IGNORE INTO state_objects"
                " (state_id, tenant, state_type, owner_ref, lifecycle, current_revision_ref, updated_at)"
                " VALUES (?, ?, ?, ?, 'active', NULL, ?)",
                (state_id, tenant, state_type, owner_ref, _now()),
            )
            cur.execute(
                "INSERT INTO state_revisions"
                " (revision_ref, state_id, canonical_digest, payload_ref,"
                "  supersedes_ref, metadata_json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(state_id, canonical_digest) DO UPDATE SET"
                "  revision_ref = excluded.revision_ref,"
                "  payload_ref = excluded.payload_ref"
                " WHERE state_revisions.canonical_digest = excluded.canonical_digest",
                (
                    revision_ref,
                    state_id,
                    canonical_digest,
                    payload_ref,
                    supersedes_ref,
                    json.dumps(metadata, sort_keys=True),
                    created_at,
                ),
            )
            row = cur.execute(
                "SELECT current_revision_ref FROM state_objects WHERE state_id = ?",
                (state_id,),
            ).fetchone()
            previous_revision_ref = row[0] if row else None
            cur.execute(
                "UPDATE state_objects"
                " SET current_revision_ref = ?, updated_at = ?"
                " WHERE state_id = ? AND current_revision_ref IS ?",
                (revision_ref, _now(), state_id, expected_revision_ref),
            )
            if cur.rowcount != 1:
                cur.execute("ROLLBACK")
                raise ConflictError(
                    f"compare-and-swap failed for {state_id}: "
                    f"expected {expected_revision_ref!r}, got {previous_revision_ref!r}"
                )
            existing = cur.execute(
                "SELECT event_id FROM evidence_events WHERE idempotency_key = ?",
                (event_idempotency_key,),
            ).fetchone()
            if existing is None:
                cur.execute(
                    "INSERT INTO evidence_events"
                    " (source_ref, event_type, data_json, idempotency_key, occurred_at, ingested_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        event_source_ref,
                        event_type,
                        json.dumps(event_data, sort_keys=True),
                        event_idempotency_key,
                        created_at,
                        _now(),
                    ),
                )
            cur.execute(
                "INSERT INTO outbox (event_ref, destination, payload_json, next_attempt)"
                " VALUES (?, ?, ?, ?)",
                (revision_ref, outbox_destination, json.dumps(outbox_payload, sort_keys=True), _now()),
            )
            cur.execute(
                "INSERT OR REPLACE INTO idempotency_records"
                " (key, request_digest, result_ref) VALUES (?, ?, ?)",
                (idempotency_key, request_digest, revision_ref),
            )
            cur.execute("COMMIT")
            return previous_revision_ref
        except ConflictError:
            raise
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def compare_and_swap_current(
        self,
        *,
        state_id: str,
        expected_revision_ref: str | None,
        new_revision_ref: str,
    ) -> None:
        """Atomically move the current pointer if it matches ``expected``.

        Raises ConflictError if the current pointer does not match
        ``expected_revision_ref`` (optimistic concurrency failure).
        """
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            cur.execute(
                "UPDATE state_objects"
                " SET current_revision_ref = ?, updated_at = ?"
                " WHERE state_id = ? AND current_revision_ref IS ?",
                (new_revision_ref, _now(), state_id, expected_revision_ref),
            )
            if cur.rowcount != 1:
                cur.execute("ROLLBACK")
                actual = self.get_current_revision_ref(state_id)
                raise ConflictError(
                    f"compare-and-swap failed for {state_id}: "
                    f"expected {expected_revision_ref!r}, got {actual!r}"
                )
            cur.execute("COMMIT")
        except ConflictError:
            raise
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def get_revision(self, revision_ref: str) -> RevisionRecord | None:
        row = self._conn.execute(
            "SELECT revision_ref, state_id, canonical_digest, payload_ref,"
            " supersedes_ref, created_at"
            " FROM state_revisions WHERE revision_ref = ?",
            (revision_ref,),
        ).fetchone()
        if row is None:
            return None
        return RevisionRecord(
            revision_ref=row[0],
            state_id=row[1],
            canonical_digest=row[2],
            payload_ref=row[3],
            supersedes_ref=row[4],
            created_at=row[5],
        )

    def list_revisions(self, state_id: str, *, limit: int = 50) -> list[RevisionRecord]:
        rows = self._conn.execute(
            "SELECT revision_ref, state_id, canonical_digest, payload_ref,"
            " supersedes_ref, created_at"
            " FROM state_revisions WHERE state_id = ?"
            " ORDER BY created_at DESC LIMIT ?",
            (state_id, limit),
        ).fetchall()
        return [
            RevisionRecord(
                revision_ref=r[0],
                state_id=r[1],
                canonical_digest=r[2],
                payload_ref=r[3],
                supersedes_ref=r[4],
                created_at=r[5],
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Evidence events + outbox
    # ------------------------------------------------------------------

    def append_event(
        self,
        *,
        source_ref: str,
        event_type: str,
        data: dict[str, Any],
        idempotency_key: str,
        occurred_at: str,
    ) -> int:
        """Append an evidence event; idempotent on ``idempotency_key``."""
        import json

        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            existing = cur.execute(
                "SELECT event_id FROM evidence_events WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                cur.execute("COMMIT")
                return existing[0]
            cur.execute(
                "INSERT INTO evidence_events"
                " (source_ref, event_type, data_json, idempotency_key, occurred_at, ingested_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (source_ref, event_type, json.dumps(data, sort_keys=True),
                 idempotency_key, occurred_at, _now()),
            )
            event_id = cur.lastrowid
            cur.execute("COMMIT")
            assert event_id is not None
            return event_id
        except Exception:
            cur.execute("ROLLBACK")
            raise

    def enqueue_outbox(
        self,
        *,
        event_ref: str,
        destination: str,
        payload: dict[str, Any],
    ) -> int:
        import json

        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO outbox (event_ref, destination, payload_json, next_attempt)"
            " VALUES (?, ?, ?, ?)",
            (event_ref, destination, json.dumps(payload, sort_keys=True), _now()),
        )
        outbox_id = cur.lastrowid
        assert outbox_id is not None
        return outbox_id

    def pending_outbox(self, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT outbox_id, event_ref, destination, payload_json, attempts"
            " FROM outbox WHERE status = 'pending'"
            " ORDER BY next_attempt LIMIT ?",
            (limit,),
        ).fetchall()
        import json

        return [
            {
                "outbox_id": r[0],
                "event_ref": r[1],
                "destination": r[2],
                "payload": json.loads(r[3]),
                "attempts": r[4],
            }
            for r in rows
        ]

    def mark_outbox_done(self, outbox_id: int) -> None:
        self._conn.execute(
            "UPDATE outbox SET status = 'done' WHERE outbox_id = ?",
            (outbox_id,),
        )

    # ------------------------------------------------------------------
    # Idempotency records
    # ------------------------------------------------------------------

    def record_idempotency(
        self,
        *,
        key: str,
        request_digest: str,
        result_ref: str,
    ) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO idempotency_records"
            " (key, request_digest, result_ref) VALUES (?, ?, ?)",
            (key, request_digest, result_ref),
        )

    def lookup_idempotency(self, key: str) -> str | None:
        record = self.lookup_idempotency_record(key)
        return record[1] if record else None

    def lookup_idempotency_record(self, key: str) -> tuple[str, str] | None:
        row = self._conn.execute(
            "SELECT request_digest, result_ref FROM idempotency_records WHERE key = ?",
            (key,),
        ).fetchone()
        return (row[0], row[1]) if row else None

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._conn.close()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
