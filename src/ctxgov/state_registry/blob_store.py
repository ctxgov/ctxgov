"""Content-addressed blob store (CAS) for revision payloads.

Per ADR-0015: blobs live at ``blobs/sha256/<digest>`` and are written
via temp-file → fsync → atomic rename → parent-dir fsync. Writing the
same content twice is idempotent. The CAS layer is deliberately simple:
it stores bytes keyed by sha256 digest and knows nothing about the
domain model.

Crash safety contract:
  - If ``store_bytes`` returns successfully, the blob is durable on
    disk (fsync'd).
  - A crash before rename leaves an orphan temp file (never a corrupt
    blob). The reconciler (Phase 3.5) reclaims orphans.
  - A crash after rename but before parent-dir fsync may leave the
    entry unlinked after a crash; the reconciler detects this.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "BlobStore",
    "StoredBlob",
    "MissingBlobError",
    "digest_bytes",
]

_HEX = "0123456789abcdef"


class MissingBlobError(KeyError):
    """Raised when a requested blob digest is not present."""


@dataclass(frozen=True)
class StoredBlob:
    digest: str
    path: Path
    size: int


def digest_bytes(payload: bytes) -> str:
    """Return the hex sha256 digest of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


class BlobStore:
    """Content-addressed blob store backed by a filesystem directory.

    The directory layout is ``blobs/sha256/<first2>/<digest>`` to avoid
    single directories with millions of entries.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._tmp_dir = root / "_tmp"
        self._root.mkdir(parents=True, exist_ok=True)
        self._tmp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Write path
    # ------------------------------------------------------------------

    def store_bytes(self, payload: bytes) -> StoredBlob:
        """Store ``payload`` and return a StoredBlob.

        Idempotent: storing identical bytes returns the same digest and
        is a no-op if the blob already exists on disk.
        """
        digest = digest_bytes(payload)
        blob_path = self._blob_path(digest)

        if blob_path.exists():
            # Already stored; verify size matches to detect partial writes.
            size = blob_path.stat().st_size
            if size == len(payload):
                return StoredBlob(digest=digest, path=blob_path, size=size)
            # Partial / corrupt file — remove and rewrite.
            blob_path.unlink()

        # Write to temp file in the same directory tree, then atomic rename.
        prefix = _validate_digest_prefix(digest)
        fd, tmp_name = tempfile.mkstemp(prefix=prefix, dir=self._tmp_dir)
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            # Ensure the shard directory exists before rename.
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp_path, blob_path)
            _fsync_dir(blob_path.parent)
        except Exception:
            # Best-effort cleanup of the temp file on any failure.
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise

        return StoredBlob(digest=digest, path=blob_path, size=len(payload))

    # ------------------------------------------------------------------
    # Read path
    # ------------------------------------------------------------------

    def read_bytes(self, digest: str) -> bytes:
        """Return the raw bytes for ``digest`` or raise MissingBlobError."""
        _validate_digest(digest)
        blob_path = self._blob_path(digest)
        if not blob_path.exists():
            raise MissingBlobError(digest)
        return blob_path.read_bytes()

    def exists(self, digest: str) -> bool:
        """Return True if the blob is present on disk."""
        _validate_digest(digest)
        return self._blob_path(digest).exists()

    def stat(self, digest: str) -> StoredBlob:
        """Return StoredBlob metadata without reading the payload."""
        _validate_digest(digest)
        blob_path = self._blob_path(digest)
        if not blob_path.exists():
            raise MissingBlobError(digest)
        return StoredBlob(digest=digest, path=blob_path, size=blob_path.stat().st_size)

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def iter_digests(self):
        """Yield every digest currently stored."""
        shard_root = self._root / "sha256"
        if not shard_root.exists():
            return
        for shard in sorted(shard_root.iterdir()):
            if not shard.is_dir():
                continue
            for blob in sorted(shard.iterdir()):
                if blob.is_file() and _is_valid_digest(blob.name):
                    yield blob.name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _blob_path(self, digest: str) -> Path:
        return self._root / "sha256" / digest[:2] / digest


def _validate_digest(digest: str) -> None:
    if not _is_valid_digest(digest):
        raise ValueError(f"invalid sha256 digest: {digest!r}")


def _is_valid_digest(text: str) -> bool:
    if len(text) != 64:
        return False
    return all(c in _HEX for c in text)


def _validate_digest_prefix(digest: str) -> str:
    _validate_digest(digest)
    return digest[:8]


def _fsync_dir(directory: Path) -> None:
    """Best-effort fsync of ``directory`` for rename durability.

    On platforms or filesystems where directory fsync is not supported
    (e.g. some network filesystems per ADR-0015/§21.2), this is a
    no-op. WAL + SQLite is the source of truth for current-pointer
    integrity; CAS durability is a best-effort optimization.
    """
    try:
        fd = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass
