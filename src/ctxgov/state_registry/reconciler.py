"""Reconciler — detect missing/orphan blobs and dangling pointers.

Per ADR-0015 §21.1 stage 5: the reconciler runs at startup and
periodically to detect and repair the three classes of post-crash
inconsistency that cross-media storage can introduce:

  - **missing blob** (HIGH severity): a revision row references a
    ``payload_ref`` whose blob is not on disk. Indicates a CAS write
    failure or filesystem corruption.
  - **orphan blob**: a blob exists on disk but no revision row
    references it. Benign — produced when a commit crashes after CAS
    but before the DB transaction commits. Reclaimed after a grace
    period.
  - **dangling pointer**: a ``state_objects.current_revision_ref``
    points to a revision row that does not exist. Indicates a DB
    inconsistency or partial migration. High severity.
  - **stuck outbox**: an outbox row remains ``pending`` past a
    deadline. Surfaces adapter/destination failures.

The reconciler does NOT auto-repair missing-blob or dangling-pointer
conditions; those require human review. It only quarantines them and
surfaces a receipt. Orphan blobs are GC'd after ``orphan_grace_seconds``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .blob_store import BlobStore
from .sqlite_ledger import SQLiteLedger

__all__ = [
    "Reconciler",
    "ReconciliationReport",
    "MissingBlob",
    "OrphanBlob",
    "DanglingPointer",
    "StuckOutbox",
]


@dataclass(frozen=True)
class MissingBlob:
    revision_ref: str
    state_id: str
    payload_ref: str


@dataclass(frozen=True)
class OrphanBlob:
    digest: str
    path: str


@dataclass(frozen=True)
class DanglingPointer:
    state_id: str
    current_revision_ref: str


@dataclass(frozen=True)
class StuckOutbox:
    outbox_id: int
    event_ref: str
    destination: str
    attempts: int


@dataclass(frozen=True)
class ReconciliationReport:
    missing_blobs: tuple[MissingBlob, ...]
    orphan_blobs: tuple[OrphanBlob, ...]
    dangling_pointers: tuple[DanglingPointer, ...]
    stuck_outbox: tuple[StuckOutbox, ...]
    status: str  # "clean" if no issues, else "issues_found"
    reconciled_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reconciled_at": self.reconciled_at,
            "missing_blob_count": len(self.missing_blobs),
            "orphan_blob_count": len(self.orphan_blobs),
            "dangling_pointer_count": len(self.dangling_pointers),
            "stuck_outbox_count": len(self.stuck_outbox),
            "missing_blobs": [
                {"revision_ref": m.revision_ref, "state_id": m.state_id, "payload_ref": m.payload_ref}
                for m in self.missing_blobs
            ],
            "orphan_blobs": [
                {"digest": o.digest, "path": o.path}
                for o in self.orphan_blobs
            ],
            "dangling_pointers": [
                {"state_id": d.state_id, "current_revision_ref": d.current_revision_ref}
                for d in self.dangling_pointers
            ],
            "stuck_outbox": [
                {"outbox_id": s.outbox_id, "event_ref": s.event_ref, "attempts": s.attempts}
                for s in self.stuck_outbox
            ],
        }


class Reconciler:
    """Detect cross-media inconsistencies and reclaim orphan blobs."""

    def __init__(
        self,
        blobs: BlobStore,
        ledger: SQLiteLedger,
        *,
        orphan_grace_seconds: int = 86400,
    ) -> None:
        self._blobs = blobs
        self._ledger = ledger
        self._orphan_grace = orphan_grace_seconds

    def scan(self) -> ReconciliationReport:
        """Run a full reconciliation scan without modifying state."""
        missing = self._find_missing_blobs()
        orphans = self._find_orphan_blobs()
        dangling = self._find_dangling_pointers()
        stuck = self._find_stuck_outbox()
        status = "clean" if not (missing or dangling) else "issues_found"
        return ReconciliationReport(
            missing_blobs=missing,
            orphan_blobs=orphans,
            dangling_pointers=dangling,
            stuck_outbox=stuck,
            status=status,
            reconciled_at=_now(),
        )

    def reclaim_orphans(self) -> int:
        """Delete orphan blobs older than the grace period. Returns count.

        This is the ONLY destructive operation the reconciler performs
        automatically. Missing-blob and dangling-pointer conditions are
        reported but NOT auto-repaired.
        """
        report = self.scan()
        now = time.time()
        reclaimed = 0
        for orphan in report.orphan_blobs:
            blob_path = self._blobs._root / "sha256" / orphan.digest[:2] / orphan.digest
            try:
                mtime = blob_path.stat().st_mtime
            except OSError:
                continue
            if now - mtime >= self._orphan_grace:
                try:
                    blob_path.unlink()
                    reclaimed += 1
                except OSError:
                    pass
        return reclaimed

    # ------------------------------------------------------------------
    # Internal scans
    # ------------------------------------------------------------------

    def _find_missing_blobs(self) -> tuple[MissingBlob, ...]:
        rows = self._ledger._conn.execute(
            "SELECT revision_ref, state_id, payload_ref FROM state_revisions"
        ).fetchall()
        issues: list[MissingBlob] = []
        for row in rows:
            revision_ref, state_id, payload_ref = row
            digest = payload_ref.rsplit("/", 1)[-1]
            if not self._blobs.exists(digest):
                issues.append(
                    MissingBlob(
                        revision_ref=revision_ref,
                        state_id=state_id,
                        payload_ref=payload_ref,
                    )
                )
        return tuple(issues)

    def _find_orphan_blobs(self) -> tuple[OrphanBlob, ...]:
        known_digests: set[str] = set()
        rows = self._ledger._conn.execute(
            "SELECT payload_ref FROM state_revisions"
        ).fetchall()
        for row in rows:
            payload_ref = row[0]
            digest = payload_ref.rsplit("/", 1)[-1]
            known_digests.add(digest)

        orphans: list[OrphanBlob] = []
        for digest in self._blobs.iter_digests():
            if digest not in known_digests:
                blob_path = self._blobs._blob_path(digest)
                orphans.append(OrphanBlob(digest=digest, path=str(blob_path)))
        return tuple(orphans)

    def _find_dangling_pointers(self) -> tuple[DanglingPointer, ...]:
        rows = self._ledger._conn.execute(
            "SELECT so.state_id, so.current_revision_ref"
            " FROM state_objects so"
            " LEFT JOIN state_revisions sr ON so.current_revision_ref = sr.revision_ref"
            " WHERE so.current_revision_ref IS NOT NULL AND sr.revision_ref IS NULL"
        ).fetchall()
        return tuple(
            DanglingPointer(state_id=row[0], current_revision_ref=row[1])
            for row in rows
        )

    def _find_stuck_outbox(self) -> tuple[StuckOutbox, ...]:
        rows = self._ledger._conn.execute(
            "SELECT outbox_id, event_ref, destination, attempts"
            " FROM outbox WHERE status = 'pending' AND attempts >= 5"
        ).fetchall()
        return tuple(
            StuckOutbox(
                outbox_id=row[0],
                event_ref=row[1],
                destination=row[2],
                attempts=row[3],
            )
            for row in rows
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
