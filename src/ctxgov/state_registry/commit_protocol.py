"""Local Commit Protocol — the 5-stage crash-safe revision commit.

Per ADR-0015 §21.1:

  1. Prepare     — JCS-canonicalize payload; compute domain-separated
                   digest; derive revision_ref.
  2. Durable CAS — store payload bytes at ``blobs/sha256/<digest>`` via
                   temp-write → fsync → atomic rename. Idempotent.
  3. DB txn      — ``BEGIN IMMEDIATE``; INSERT revision row;
                   compare-and-swap UPDATE current pointer; INSERT
                   evidence event; INSERT outbox row; COMMIT.
                   ``expected_revision_ref`` mismatch → CONFLICT.
  4. Publish     — outbox worker emits export events at-least-once.
                   Consumers dedupe via ``source + id`` + idempotency key.
  5. Reconcile   — periodic scan for missing/orphan blobs, dangling
                   pointers, stuck outbox. (Phase 3.5)

Crash invariants (see ADR-0015 §7):
  - A successful commit means the current pointer references an
    existing, digest-verified revision.
  - A crash before the DB COMMIT leaves an orphan blob (acceptable;
    reconciler GCs it).
  - A crash after the DB COMMIT is durable: WAL + ``synchronous=FULL``
    guarantees the revision row + current pointer + event + outbox row
    are atomic.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..contracts.canonicalization import canonicalize_bytes, domain_digest
from ..contracts.state_revision_v2 import (
    STATE_REVISION_DOMAIN,
    compute_canonical_digest,
    compute_revision_ref,
)
from .blob_store import BlobStore
from .sqlite_ledger import ConflictError, SQLiteLedger

__all__ = [
    "CommitProtocol",
    "CommitResult",
    "CommitConflict",
]


class CommitConflict(ConflictError):
    """Raised when the compare-and-swap current-pointer check fails."""


@dataclass(frozen=True)
class CommitResult:
    """The outcome of a successful commit."""

    revision_ref: str
    canonical_digest: str
    payload_ref: str
    state_id: str
    previous_revision_ref: str | None
    created_at: str


class CommitProtocol:
    """Orchestrates the 5-stage Local Commit Protocol.

    The protocol is the ONLY way to promote a new current revision.
    Direct writes to BlobStore or SQLiteLedger bypass crash safety and
    must not be used from application code.
    """

    def __init__(self, blobs: BlobStore, ledger: SQLiteLedger) -> None:
        self._blobs = blobs
        self._ledger = ledger

    def commit(
        self,
        *,
        state_id: str,
        tenant: str,
        state_type: str,
        owner_ref: str | None,
        payload: dict[str, Any],
        expected_revision_ref: str | None,
        writer_ref: str,
        idempotency_key: str,
    ) -> CommitResult:
        """Commit a new revision under the 5-stage protocol.

        ``expected_revision_ref`` is the optimistic-concurrency guard:
        pass the revision_ref you believe is currently active, or
        ``None`` if this is the first revision for this state object.
        Raises CommitConflict if the assumption is wrong.

        The call is idempotent on ``idempotency_key``: repeating the
        same commit returns the original result without creating a
        duplicate revision or side effect.
        """
        # ------------------------------------------------------------------
        # Stage 1: Prepare — canonicalize + compute digests.
        # ------------------------------------------------------------------
        canonical_digest = compute_canonical_digest(payload)
        revision_ref = compute_revision_ref(canonical_digest)
        canonical_bytes = canonicalize_bytes(payload)

        # The CAS payload is the JCS-canonical payload; payload_ref is a
        # stable ``blob://sha256/<digest>`` URI resolved by BlobStore.
        payload_digest = hashlib.sha256(canonical_bytes).hexdigest()
        payload_ref = f"blob://sha256/{payload_digest}"
        created_at = _now()
        request_digest = _request_digest(
            state_id=state_id,
            tenant=tenant,
            state_type=state_type,
            owner_ref=owner_ref,
            canonical_digest=canonical_digest,
            expected_revision_ref=expected_revision_ref,
            writer_ref=writer_ref,
        )

        # Idempotency short-circuit after the request digest is known. Reusing
        # a key for different semantic input is a caller error and must not
        # silently return a previous result.
        existing = self._ledger.lookup_idempotency_record(idempotency_key)
        if existing is not None:
            existing_request_digest, existing_revision_ref = existing
            if existing_request_digest != request_digest:
                raise ValueError("idempotency key already used for a different request")
            return self._result_from_existing(existing_revision_ref, state_id)

        # ------------------------------------------------------------------
        # Stage 2: Durable CAS — write the blob (idempotent).
        # ------------------------------------------------------------------
        self._blobs.store_bytes(canonical_bytes)

        # ------------------------------------------------------------------
        # Stage 3: DB transaction — revision + current + event + outbox.
        # ------------------------------------------------------------------
        try:
            previous = self._ledger.commit_revision_transaction(
                state_id=state_id,
                tenant=tenant,
                state_type=state_type,
                owner_ref=owner_ref,
                revision_ref=revision_ref,
                canonical_digest=canonical_digest,
                payload_ref=payload_ref,
                supersedes_ref=expected_revision_ref,
                metadata={"writer_ref": writer_ref},
                created_at=created_at,
                expected_revision_ref=expected_revision_ref,
                event_source_ref=f"state://{state_id}",
                event_type="state.revision.promoted",
                event_data={
                    "revision_ref": revision_ref,
                    "supersedes": expected_revision_ref,
                    "writer_ref": writer_ref,
                },
                event_idempotency_key=f"promote:{idempotency_key}",
                outbox_destination="default",
                outbox_payload={
                    "event_type": "state.revision.promoted",
                    "state_id": state_id,
                    "revision_ref": revision_ref,
                },
                idempotency_key=idempotency_key,
                request_digest=request_digest,
            )
        except ConflictError as exc:
            raise CommitConflict(str(exc)) from exc

        result = CommitResult(
            revision_ref=revision_ref,
            canonical_digest=canonical_digest,
            payload_ref=payload_ref,
            state_id=state_id,
            previous_revision_ref=previous,
            created_at=created_at,
        )

        return result

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def read_payload(self, revision_ref: str) -> dict[str, Any]:
        """Return the canonical payload for ``revision_ref``.

        Raises KeyError if the revision is unknown.
        """
        import json

        record = self._ledger.get_revision(revision_ref)
        if record is None:
            raise KeyError(f"unknown revision: {revision_ref}")
        # payload_ref is blob://sha256/<digest>
        digest = record.payload_ref.rsplit("/", 1)[-1]
        raw = self._blobs.read_bytes(digest)
        return json.loads(raw.decode("utf-8"))

    def _result_from_existing(self, revision_ref: str, state_id: str) -> CommitResult:
        record = self._ledger.get_revision(revision_ref)
        if record is None:
            raise KeyError(
                f"idempotency lookup returned {revision_ref!r} but revision missing"
            )
        return CommitResult(
            revision_ref=record.revision_ref,
            canonical_digest=record.canonical_digest,
            payload_ref=record.payload_ref,
            state_id=record.state_id,
            previous_revision_ref=record.supersedes_ref,
            created_at=record.created_at,
        )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _request_digest(
    *,
    state_id: str,
    tenant: str,
    state_type: str,
    owner_ref: str | None,
    canonical_digest: str,
    expected_revision_ref: str | None,
    writer_ref: str,
) -> str:
    payload = {
        "state_id": state_id,
        "tenant": tenant,
        "state_type": state_type,
        "owner_ref": owner_ref,
        "canonical_digest": canonical_digest,
        "expected_revision_ref": expected_revision_ref,
        "writer_ref": writer_ref,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
