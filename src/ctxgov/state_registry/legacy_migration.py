from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..contracts.canonicalization import canonicalize_bytes
from .commit_protocol import CommitProtocol

__all__ = [
    "MigrationReport",
    "run_legacy_migration",
    "MIGRATION_WRITER_REF",
    "MIGRATION_TENANT",
]

MIGRATION_WRITER_REF = "migration://legacy/v1"
MIGRATION_TENANT = "legacy"


@dataclass(frozen=True)
class MigrationReport:
    total_count: int
    migrated_count: int
    quarantined_count: int
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_count": self.total_count,
            "migrated_count": self.migrated_count,
            "quarantined_count": self.quarantined_count,
            "errors": list(self.errors),
        }


def run_legacy_migration(
    legacy_objects_dir: Path,
    protocol: CommitProtocol,
    *,
    tenant: str = MIGRATION_TENANT,
    writer_ref: str = MIGRATION_WRITER_REF,
) -> MigrationReport:
    if not legacy_objects_dir.is_dir():
        raise NotADirectoryError(
            f"legacy_objects_dir does not exist: {legacy_objects_dir}"
        )

    total = 0
    migrated = 0
    quarantined = 0
    errors: list[dict[str, Any]] = []

    for kind_dir in sorted(legacy_objects_dir.iterdir()):
        if not kind_dir.is_dir():
            continue
        kind = kind_dir.name
        for json_file in sorted(kind_dir.glob("*.json")):
            total += 1
            file_id = json_file.stem
            legacy_storage_ref = f"vault://objects/{kind}/{json_file.name}"

            try:
                raw_bytes = json_file.read_bytes()
                payload: dict[str, Any] = json.loads(raw_bytes)
            except (json.JSONDecodeError, OSError) as exc:
                quarantined += 1
                errors.append({
                    "file": str(json_file),
                    "stage": "read",
                    "error": str(exc),
                })
                _quarantine_file(json_file)
                continue

            raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()

            try:
                canonicalize_bytes(payload)
            except Exception as exc:
                quarantined += 1
                errors.append({
                    "file": str(json_file),
                    "stage": "canonicalize",
                    "error": str(exc),
                })
                _quarantine_file(json_file)
                continue

            state_id = f"state://legacy/{kind}/{file_id}"
            idempotency_key = f"legacy-migrate:{raw_sha256}"

            migrated_payload: dict[str, Any] = {
                "_legacy": {
                    "storage_ref": legacy_storage_ref,
                    "sha256": raw_sha256,
                },
                "data": payload,
            }

            try:
                protocol.commit(
                    state_id=state_id,
                    tenant=tenant,
                    state_type=kind,
                    owner_ref=None,
                    payload=migrated_payload,
                    expected_revision_ref=None,
                    writer_ref=writer_ref,
                    idempotency_key=idempotency_key,
                )
            except Exception as exc:
                quarantined += 1
                errors.append({
                    "file": str(json_file),
                    "stage": "commit",
                    "error": str(exc),
                })
                _quarantine_file(json_file)
                continue

            migrated += 1

    return MigrationReport(
        total_count=total,
        migrated_count=migrated,
        quarantined_count=quarantined,
        errors=errors,
    )


def _quarantine_file(path: Path) -> None:
    quarantine_dir = path.parent / ".quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / path.name
    path.rename(dest)
