"""State Registry — persistent agent state with immutable revisions.

This package implements the Evidence Core storage layer (WP-2) per
ADR-0003/ADR-0015: content-addressed blobs + SQLite revision ledger +
Local Commit Protocol. It coexists with the legacy ``objects/`` JSON
store; new writes go through the commit protocol while old files are
read via the legacy adapter until migrated.
"""

from .blob_store import BlobStore, StoredBlob
from .sqlite_ledger import SQLiteLedger, RevisionRecord
from .commit_protocol import CommitProtocol, CommitResult, CommitConflict

__all__ = [
    "BlobStore",
    "StoredBlob",
    "SQLiteLedger",
    "RevisionRecord",
    "CommitProtocol",
    "CommitResult",
    "CommitConflict",
]
