from __future__ import annotations

from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
from typing import Any
from urllib.parse import unquote, urlparse

from .backup import collect_workspace_files
from .core import CtxVault
from .layout import VaultLayout


SNAPSHOT_SCHEMA_VERSION = "ctxvault.snapshot-manifest/v1"
OPERATION_LOG_SCHEMA_VERSION = "ctxvault.operation-log/v1"
MUTATION_LEDGER_SCHEMA_VERSION = "ctxvault.mutation-ledger/v1"
SYNC_RECEIPT_SCHEMA_VERSION = "ctxvault.sync-receipt/v1"
SYNC_MANIFEST_SCHEMA_VERSION = "ctxvault.sync-manifest/v1"
SYNC_COPY_RECEIPT_SCHEMA_VERSION = "ctxvault.sync-copy-receipt/v1"
REPLICA_VERIFY_SCHEMA_VERSION = "ctxvault.replica-verify/v1"
REPLICA_TRUST_EVAL_SCHEMA_VERSION = "ctxvault.replica-trust-eval/v1"
REPLICA_TRUST_REGISTRY_SCHEMA_VERSION = "ctxvault.replica-trust-registry/v1"
PAIRING_OFFER_SCHEMA_VERSION = "ctxvault.replica-pairing-offer/v1"
SNAPSHOT_PROVENANCE_SCHEMA_VERSION = "ctxvault.snapshot-provenance/v1"
REPLICA_IMPORT_RECEIPT_SCHEMA_VERSION = "ctxvault.replica-import-receipt/v1"
REPLICA_APPLY_RECEIPT_SCHEMA_VERSION = "ctxvault.replica-apply-receipt/v1"
RESTORE_RECEIPT_SCHEMA_VERSION = "ctxvault.restore-receipt/v1"
SYNC_CONFLICT_MARKER_SCHEMA_VERSION = "ctxvault.sync-conflict-marker/v1"


def create_snapshot(
    *,
    root: Path,
    layout: VaultLayout,
    scope_kind: str,
    scope_value: str,
    label: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    snapshot_dir = layout.exports_dir / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    created_at_dt = datetime.now(timezone.utc)
    created_at = created_at_dt.isoformat()
    timestamp_token = created_at_dt.strftime("%Y%m%dT%H%M%S%fZ")

    workspace_files = collect_workspace_files(root, excluded_prefixes=(layout.exports_dir,))
    workspace_entries = [_file_entry(root, path) for path in workspace_files]
    vault_object_paths = _collect_vault_paths(layout.objects_dir)
    review_paths = _collect_vault_paths(layout.reviews_dir)
    vault_object_entries = [_file_entry(root, path) for path in vault_object_paths]
    review_entries = [_file_entry(root, path) for path in review_paths]
    restore_bundle_dir = layout.exports_dir / "snapshot-bundles"
    restore_bundle_dir.mkdir(parents=True, exist_ok=True)
    restore_bundle_path = restore_bundle_dir / f"{timestamp_token.lower()}.tar.gz"
    restore_bundle_paths = [*workspace_files, *vault_object_paths, *review_paths]
    _write_archive(root, restore_bundle_paths, restore_bundle_path)
    restore_bundle_sha256 = _sha256_file(restore_bundle_path)

    workspace_digest = _entries_digest(workspace_entries)
    vault_digest = _entries_digest([*vault_object_entries, *review_entries])
    combined_digest = _entries_digest(
        [
            {"path": "workspace", "sha256": workspace_digest, "size_bytes": len(workspace_entries)},
            {"path": "vault", "sha256": vault_digest, "size_bytes": len(vault_object_entries) + len(review_entries)},
        ]
    )
    snapshot_id = f"snap_{timestamp_token.lower()}_{combined_digest[:8]}"
    manifest_path = snapshot_dir / f"{snapshot_id}.json"
    parent_snapshot_id = _latest_snapshot_id(snapshot_dir)

    manifest = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "root": str(root),
        "scope": {"kind": scope_kind, "value": scope_value},
        "label": label,
        "parent_snapshot_id": parent_snapshot_id,
        "summary": {
            "workspace": {
                "file_count": len(workspace_entries),
                "total_bytes": sum(int(entry["size_bytes"]) for entry in workspace_entries),
                "digest": workspace_digest,
            },
            "vault": {
                "object_file_count": len(vault_object_entries),
                "review_file_count": len(review_entries),
                "total_bytes": sum(int(entry["size_bytes"]) for entry in [*vault_object_entries, *review_entries]),
                "digest": vault_digest,
            },
            "combined_digest": combined_digest,
        },
        "workspace_files": workspace_entries,
        "vault_files": {
            "objects": vault_object_entries,
            "reviews": review_entries,
        },
        "restore_bundle": {
            "path": str(restore_bundle_path.resolve()),
            "sha256": restore_bundle_sha256,
            "file_count": len(restore_bundle_paths),
        },
        "rebuildable_indexes": [
            _display_path(root, layout.sqlite_path),
        ],
    }
    _write_json(manifest_path, manifest)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": created_at,
        "operation": "snapshot.create",
        "snapshot_id": snapshot_id,
        "manifest_path": str(manifest_path),
        "scope": {"kind": scope_kind, "value": scope_value},
        "label": label,
        "parent_snapshot_id": parent_snapshot_id,
        "combined_digest": combined_digest,
        "restore_bundle_path": str(restore_bundle_path.resolve()),
        "restore_bundle_sha256": restore_bundle_sha256,
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "snapshot_id": snapshot_id,
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "restore_bundle_path": str(restore_bundle_path.resolve()),
        "restore_bundle_sha256": restore_bundle_sha256,
        "operation_log_path": str(operation_log_path),
        "operation": operation,
    }


def record_mutation(
    *,
    layout: VaultLayout,
    mutation_kind: str,
    object_ref: str,
    actor: str | None = None,
    decision: str | None = None,
    scope: dict[str, Any] | None = None,
    related_refs: list[str] | None = None,
    notes: str | None = None,
    status: str = "recorded",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_mutation_kind = mutation_kind.strip()
    normalized_object_ref = object_ref.strip()
    if not normalized_mutation_kind:
        raise ValueError("mutation_kind must not be empty")
    if not normalized_object_ref:
        raise ValueError("object_ref must not be empty")

    mutation_path = layout.exports_dir / "mutation-ledger.jsonl"
    mutation_path.parent.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    recorded_at_dt = datetime.now(timezone.utc)
    recorded_at = recorded_at_dt.isoformat()
    timestamp_token = recorded_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    mutation_id = f"mutation_{timestamp_token}_{_slug_token(normalized_mutation_kind)[:24]}"
    entry = {
        "schema_version": MUTATION_LEDGER_SCHEMA_VERSION,
        "id": mutation_id,
        "recorded_at": recorded_at,
        "mutation_kind": normalized_mutation_kind,
        "object_ref": normalized_object_ref,
        "actor": actor,
        "decision": decision,
        "scope": dict(scope or {}),
        "related_refs": [str(item).strip() for item in list(related_refs or []) if str(item).strip()],
        "notes": notes,
        "status": status,
        "details": dict(details or {}),
    }
    _append_jsonl(mutation_path, entry)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": recorded_at,
        "operation": "mutation.record",
        "mutation_id": mutation_id,
        "mutation_kind": normalized_mutation_kind,
        "object_ref": normalized_object_ref,
    }
    _append_jsonl(operation_log_path, operation)
    return {
        "mutation_ledger_path": str(mutation_path.resolve()),
        "entry": entry,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def list_mutations(
    *,
    layout: VaultLayout,
    limit: int = 50,
    mutation_kind: str | None = None,
) -> dict[str, Any]:
    mutation_path = layout.exports_dir / "mutation-ledger.jsonl"
    if not mutation_path.exists():
        return {
            "schema_version": MUTATION_LEDGER_SCHEMA_VERSION,
            "mutation_ledger_path": str(mutation_path.resolve()),
            "summary": {"entry_count": 0, "returned_count": 0},
            "entries": [],
        }
    normalized_kind = str(mutation_kind or "").strip() or None
    entries: list[dict[str, Any]] = []
    for raw in mutation_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            continue
        if normalized_kind is not None and str(payload.get("mutation_kind") or "").strip() != normalized_kind:
            continue
        entries.append(payload)
    entries.sort(key=lambda item: (str(item.get("recorded_at") or ""), str(item.get("id") or "")), reverse=True)
    returned = entries[:limit]
    return {
        "schema_version": MUTATION_LEDGER_SCHEMA_VERSION,
        "mutation_ledger_path": str(mutation_path.resolve()),
        "summary": {
            "entry_count": len(entries),
            "returned_count": len(returned),
            "mutation_kind": normalized_kind,
        },
        "entries": returned,
    }


def list_snapshots(*, layout: VaultLayout, limit: int = 20) -> list[dict[str, Any]]:
    snapshot_dir = layout.exports_dir / "snapshots"
    if not snapshot_dir.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(snapshot_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        snapshots.append(
            {
                "snapshot_id": str(payload.get("snapshot_id") or path.stem),
                "created_at": str(payload.get("created_at") or ""),
                "label": payload.get("label"),
                "parent_snapshot_id": payload.get("parent_snapshot_id"),
                "scope": payload.get("scope") or {},
                "manifest_path": str(path.resolve()),
                "combined_digest": str(((payload.get("summary") or {}).get("combined_digest")) or ""),
                "workspace_file_count": int((((payload.get("summary") or {}).get("workspace") or {}).get("file_count")) or 0),
                "vault_file_count": int((((payload.get("summary") or {}).get("vault") or {}).get("object_file_count")) or 0)
                + int((((payload.get("summary") or {}).get("vault") or {}).get("review_file_count")) or 0),
                "restore_bundle_path": str((((payload.get("restore_bundle") or {}).get("path")) or "")),
                "restore_bundle_available": bool((((payload.get("restore_bundle") or {}).get("path")) or "")),
            }
        )
    snapshots.sort(key=lambda item: (item["created_at"], item["snapshot_id"]), reverse=True)
    return snapshots[:limit]


def diff_snapshots(
    *,
    layout: VaultLayout,
    base_snapshot_id: str,
    head_snapshot_id: str,
) -> dict[str, Any]:
    base_path = _snapshot_manifest_path(layout, base_snapshot_id)
    head_path = _snapshot_manifest_path(layout, head_snapshot_id)
    base_manifest = _load_json(base_path)
    head_manifest = _load_json(head_path)

    workspace_diff = _diff_entry_sets(
        _entry_map(list(base_manifest.get("workspace_files") or [])),
        _entry_map(list(head_manifest.get("workspace_files") or [])),
    )
    base_vault = base_manifest.get("vault_files") if isinstance(base_manifest.get("vault_files"), dict) else {}
    head_vault = head_manifest.get("vault_files") if isinstance(head_manifest.get("vault_files"), dict) else {}
    object_diff = _diff_entry_sets(
        _entry_map(list(base_vault.get("objects") or [])),
        _entry_map(list(head_vault.get("objects") or [])),
    )
    review_diff = _diff_entry_sets(
        _entry_map(list(base_vault.get("reviews") or [])),
        _entry_map(list(head_vault.get("reviews") or [])),
    )

    vault_summary = _merge_diff_summaries(object_diff["summary"], review_diff["summary"])
    combined_summary = _merge_diff_summaries(workspace_diff["summary"], vault_summary)

    return {
        "base_snapshot_id": str(base_manifest.get("snapshot_id") or base_snapshot_id),
        "head_snapshot_id": str(head_manifest.get("snapshot_id") or head_snapshot_id),
        "base_manifest_path": str(base_path.resolve()),
        "head_manifest_path": str(head_path.resolve()),
        "summary": {
            "workspace": workspace_diff["summary"],
            "vault": vault_summary,
            "combined": combined_summary,
        },
        "changes": {
            "workspace": workspace_diff["changes"],
            "vault_objects": object_diff["changes"],
            "vault_reviews": review_diff["changes"],
        },
    }


def emit_sync_receipt(
    *,
    layout: VaultLayout,
    snapshot_id: str,
    target: str,
    transport: str,
    device_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    snapshot_dir = layout.exports_dir / "snapshots"
    receipt_dir = layout.exports_dir / "sync-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_path = _snapshot_manifest_path(layout, snapshot_id)
    manifest = _load_json(manifest_path)
    created_at_dt = datetime.now(timezone.utc)
    created_at = created_at_dt.isoformat()
    timestamp_token = created_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    receipt_id = f"sync_{timestamp_token}_{snapshot_id[-8:]}"
    receipt_path = receipt_dir / f"{receipt_id}.json"

    receipt = {
        "schema_version": SYNC_RECEIPT_SCHEMA_VERSION,
        "id": receipt_id,
        "created_at": created_at,
        "snapshot_id": str(manifest.get("snapshot_id") or snapshot_id),
        "snapshot_manifest_path": str(manifest_path.resolve()),
        "scope": manifest.get("scope") or {},
        "target": target,
        "transport": transport,
        "device_id": device_id,
        "combined_digest": str(((manifest.get("summary") or {}).get("combined_digest")) or ""),
        "status": "recorded",
        "notes": notes,
    }
    _write_json(receipt_path, receipt)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": created_at,
        "operation": "snapshot.sync",
        "snapshot_id": receipt["snapshot_id"],
        "receipt_id": receipt_id,
        "receipt_path": str(receipt_path.resolve()),
        "target": target,
        "transport": transport,
        "device_id": device_id,
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "receipt_path": str(receipt_path.resolve()),
        "receipt": receipt,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def emit_sync_manifest(
    *,
    layout: VaultLayout,
    target: str,
    transport: str,
    device_id: str | None = None,
    snapshot_id: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    snapshots = list_snapshots(layout=layout, limit=10000)
    effective_snapshot_id = snapshot_id or _current_local_snapshot_id(layout) or (snapshots[0]["snapshot_id"] if snapshots else None)
    if not effective_snapshot_id:
        raise ValueError("cannot emit a sync manifest without at least one local snapshot")

    manifest_path = _snapshot_manifest_path(layout, effective_snapshot_id)
    manifest = _load_json(manifest_path)
    restore_bundle = manifest.get("restore_bundle") if isinstance(manifest.get("restore_bundle"), dict) else {}
    restore_bundle_path = _restore_bundle_path(layout.repo_root, restore_bundle)
    if restore_bundle_path is None:
        raise ValueError(f"snapshot {effective_snapshot_id} does not include a restore bundle")

    sync_manifest_dir = layout.exports_dir / "sync-manifests"
    sync_manifest_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    created_at_dt = datetime.now(timezone.utc)
    created_at = created_at_dt.isoformat()
    timestamp_token = created_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    sync_manifest_id = f"sync_manifest_{timestamp_token}_{effective_snapshot_id[-8:]}"
    sync_manifest_path = sync_manifest_dir / f"{sync_manifest_id}.json"

    artifact_paths = [
        str(manifest_path.resolve()),
        str(restore_bundle_path.resolve()),
    ]
    sync_manifest = {
        "schema_version": SYNC_MANIFEST_SCHEMA_VERSION,
        "id": sync_manifest_id,
        "created_at": created_at,
        "snapshot_id": str(manifest.get("snapshot_id") or effective_snapshot_id),
        "snapshot_manifest_path": str(manifest_path.resolve()),
        "restore_bundle_path": str(restore_bundle_path.resolve()),
        "scope": manifest.get("scope") or {},
        "target": target,
        "transport": transport,
        "device_id": device_id,
        "endpoint_key": _sync_endpoint_from_values(device_id=device_id, target=target),
        "summary": {
            "artifact_count": len(artifact_paths),
            "workspace_file_count": int((((manifest.get("summary") or {}).get("workspace") or {}).get("file_count")) or 0),
            "vault_file_count": int((((manifest.get("summary") or {}).get("vault") or {}).get("object_file_count")) or 0)
            + int((((manifest.get("summary") or {}).get("vault") or {}).get("review_file_count")) or 0),
        },
        "artifact_paths": artifact_paths,
        "notes": notes,
    }
    _write_json(sync_manifest_path, sync_manifest)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": created_at,
        "operation": "snapshot.sync-manifest",
        "snapshot_id": sync_manifest["snapshot_id"],
        "sync_manifest_id": sync_manifest_id,
        "sync_manifest_path": str(sync_manifest_path.resolve()),
        "target": target,
        "transport": transport,
        "device_id": device_id,
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "sync_manifest_path": str(sync_manifest_path.resolve()),
        "sync_manifest": sync_manifest,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def apply_sync_manifest(
    *,
    layout: VaultLayout,
    sync_manifest_path: Path,
) -> dict[str, Any]:
    sync_manifest_path = sync_manifest_path.resolve()
    sync_manifest = _load_json(sync_manifest_path)
    target_root = _local_target_root(str(sync_manifest.get("target") or ""))
    target_root.mkdir(parents=True, exist_ok=True)

    copied_paths: list[str] = []
    skipped_paths: list[str] = []
    for artifact_path in _sync_manifest_artifact_paths(sync_manifest, sync_manifest_path):
        destination = _sync_copy_destination(target_root, artifact_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and _sha256_file(destination) == _sha256_file(artifact_path):
            skipped_paths.append(str(destination.resolve()))
            continue
        destination.write_bytes(artifact_path.read_bytes())
        copied_paths.append(str(destination.resolve()))

    receipt_dir = layout.exports_dir / "sync-copy-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    copied_at_dt = datetime.now(timezone.utc)
    copied_at = copied_at_dt.isoformat()
    timestamp_token = copied_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    receipt_id = f"sync_copy_{timestamp_token}_{str(sync_manifest.get('snapshot_id') or '')[-8:]}"
    receipt_path = receipt_dir / f"{receipt_id}.json"

    receipt = {
        "schema_version": SYNC_COPY_RECEIPT_SCHEMA_VERSION,
        "id": receipt_id,
        "copied_at": copied_at,
        "sync_manifest_id": str(sync_manifest.get("id") or sync_manifest_path.stem),
        "sync_manifest_path": str(sync_manifest_path),
        "snapshot_id": str(sync_manifest.get("snapshot_id") or ""),
        "target_root": str(target_root.resolve()),
        "copied_paths": copied_paths,
        "skipped_paths": skipped_paths,
        "status": "copied",
    }
    _write_json(receipt_path, receipt)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": copied_at,
        "operation": "snapshot.sync-copy",
        "snapshot_id": receipt["snapshot_id"],
        "sync_manifest_id": receipt["sync_manifest_id"],
        "receipt_id": receipt_id,
        "receipt_path": str(receipt_path.resolve()),
        "target_root": str(target_root.resolve()),
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "receipt_path": str(receipt_path.resolve()),
        "receipt": receipt,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def verify_replica(
    *,
    replica_root: Path,
    snapshot_id: str | None = None,
    sync_manifest_path: Path | None = None,
) -> dict[str, Any]:
    replica_root = replica_root.resolve()
    selected_sync_manifest_path = _select_replica_sync_manifest_path(replica_root, sync_manifest_path)
    sync_manifest = _load_json(selected_sync_manifest_path) if selected_sync_manifest_path is not None else None

    effective_snapshot_id = snapshot_id or (str(sync_manifest.get("snapshot_id") or "").strip() if sync_manifest else "")
    if not effective_snapshot_id:
        effective_snapshot_id = _latest_replica_snapshot_id(replica_root) or ""
    if not effective_snapshot_id:
        raise ValueError("cannot verify replica without a snapshot id or replica snapshot manifest")

    snapshot_manifest_path = replica_root / "snapshots" / f"{effective_snapshot_id}.json"
    checks = {
        "snapshot_manifest_exists": snapshot_manifest_path.exists(),
        "sync_manifest_exists": selected_sync_manifest_path is not None and selected_sync_manifest_path.exists(),
        "sync_manifest_snapshot_matches": True,
        "restore_bundle_exists": False,
        "restore_bundle_sha256_matches": False,
        "sync_artifacts_complete": True,
    }
    missing_paths: list[str] = []
    mismatches: list[str] = []

    if not snapshot_manifest_path.exists():
        missing_paths.append(str(snapshot_manifest_path.resolve()))
        return {
            "schema_version": REPLICA_VERIFY_SCHEMA_VERSION,
            "status": "invalid",
            "replica_root": str(replica_root),
            "snapshot_id": effective_snapshot_id,
            "snapshot_manifest_path": str(snapshot_manifest_path.resolve()),
            "sync_manifest_path": str(selected_sync_manifest_path.resolve()) if selected_sync_manifest_path is not None else None,
            "restore_bundle_path": None,
            "checks": checks,
            "missing_paths": missing_paths,
            "mismatches": mismatches,
        }

    snapshot_manifest = _load_json(snapshot_manifest_path)
    if sync_manifest is not None and str(sync_manifest.get("snapshot_id") or "") != effective_snapshot_id:
        checks["sync_manifest_snapshot_matches"] = False
        mismatches.append("sync_manifest.snapshot_id")

    restore_bundle_path = _replica_restore_bundle_path(replica_root, snapshot_manifest)
    checks["restore_bundle_exists"] = restore_bundle_path.exists()
    if not restore_bundle_path.exists():
        missing_paths.append(str(restore_bundle_path.resolve()))
    else:
        expected_bundle_sha = str((((snapshot_manifest.get("restore_bundle") or {}).get("sha256")) or "")).strip()
        actual_bundle_sha = _sha256_file(restore_bundle_path)
        checks["restore_bundle_sha256_matches"] = bool(expected_bundle_sha) and actual_bundle_sha == expected_bundle_sha
        if not checks["restore_bundle_sha256_matches"]:
            mismatches.append("restore_bundle.sha256")

    artifact_paths: list[str] = []
    if sync_manifest is not None:
        for artifact_path in _sync_manifest_artifact_paths(sync_manifest, selected_sync_manifest_path):
            expected_path = _sync_copy_destination(replica_root, artifact_path)
            artifact_paths.append(str(expected_path.resolve()))
            if not expected_path.exists():
                checks["sync_artifacts_complete"] = False
                missing_paths.append(str(expected_path.resolve()))
    else:
        artifact_paths = [
            str(snapshot_manifest_path.resolve()),
            str(restore_bundle_path.resolve()),
        ]

    status = "verified" if not missing_paths and not mismatches else "invalid"
    return {
        "schema_version": REPLICA_VERIFY_SCHEMA_VERSION,
        "status": status,
        "replica_root": str(replica_root),
        "snapshot_id": effective_snapshot_id,
        "snapshot_manifest_path": str(snapshot_manifest_path.resolve()),
        "sync_manifest_path": str(selected_sync_manifest_path.resolve()) if selected_sync_manifest_path is not None else None,
        "restore_bundle_path": str(restore_bundle_path.resolve()),
        "checks": checks,
        "artifact_paths": artifact_paths,
        "missing_paths": missing_paths,
        "mismatches": mismatches,
    }


def evaluate_replica_trust(
    *,
    replica_root: Path,
    snapshot_id: str | None = None,
    sync_manifest_path: Path | None = None,
    trust_policy: dict[str, Any] | None = None,
    trust_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verification = verify_replica(
        replica_root=replica_root,
        snapshot_id=snapshot_id,
        sync_manifest_path=sync_manifest_path,
    )
    policy = trust_policy or {}
    default_decision = _trust_default_decision(policy)
    require_sync_manifest = bool(policy.get("require_sync_manifest", True))
    trusted_device_ids = {str(item).strip() for item in list(policy.get("trusted_device_ids") or []) if str(item).strip()}
    blocked_device_ids = {str(item).strip() for item in list(policy.get("blocked_device_ids") or []) if str(item).strip()}
    allowed_transports = {str(item).strip() for item in list(policy.get("allowed_transports") or []) if str(item).strip()}
    max_snapshot_age_hours = int(policy["max_snapshot_age_hours"]) if "max_snapshot_age_hours" in policy else None

    reasons: list[str] = []
    decision = "allow"
    sync_manifest_payload = (
        _load_json(Path(str(verification["sync_manifest_path"])))
        if verification.get("sync_manifest_path")
        else None
    )
    snapshot_manifest_payload = _load_json(Path(str(verification["snapshot_manifest_path"])))
    registry_entry = None if sync_manifest_payload is None else _replica_trust_registry_entry(
        trust_registry,
        str(sync_manifest_payload.get("device_id") or "").strip(),
    )

    if verification["status"] != "verified":
        return {
            "schema_version": REPLICA_TRUST_EVAL_SCHEMA_VERSION,
            "decision": "block",
            "requires_human_review": False,
            "replica_root": verification["replica_root"],
            "snapshot_id": verification["snapshot_id"],
            "sync_manifest_path": verification.get("sync_manifest_path"),
            "device_id": None if sync_manifest_payload is None else sync_manifest_payload.get("device_id"),
            "transport": None if sync_manifest_payload is None else sync_manifest_payload.get("transport"),
            "endpoint_key": None if sync_manifest_payload is None else sync_manifest_payload.get("endpoint_key"),
            "verification_status": verification["status"],
            "matched_policy": policy,
            "matched_registry_entry": registry_entry,
            "reasons": ["replica verification failed"] + list(verification.get("missing_paths") or []) + list(verification.get("mismatches") or []),
        }

    if sync_manifest_payload is None:
        if require_sync_manifest:
            decision = _stronger_decision(decision, "block")
            reasons.append("trust policy requires a sync manifest")
        else:
            reasons.append("sync manifest not required by trust policy")
    else:
        device_id = str(sync_manifest_payload.get("device_id") or "").strip()
        transport = str(sync_manifest_payload.get("transport") or "").strip()
        endpoint_key = str(sync_manifest_payload.get("endpoint_key") or "").strip()
        trusted_by_registry = False

        if device_id in blocked_device_ids:
            decision = _stronger_decision(decision, "block")
            reasons.append(f"device {device_id} is explicitly blocked")
        elif registry_entry is not None:
            registry_state = str(registry_entry.get("trust_state") or "").strip()
            if registry_state == "block":
                decision = _stronger_decision(decision, "block")
                reasons.append(f"device {device_id} is blocked by local trust registry")
            elif registry_state == "review":
                decision = _stronger_decision(decision, "review")
                reasons.append(f"device {device_id} requires review by local trust registry")
            elif registry_state == "allow":
                trusted_by_registry = True
                reasons.append(f"device {device_id} is trusted by local trust registry")
        if trusted_device_ids and not trusted_by_registry and device_id not in blocked_device_ids and registry_entry is None:
            if device_id in trusted_device_ids:
                reasons.append(f"device {device_id} is trusted")
            else:
                decision = _stronger_decision(decision, default_decision)
                reasons.append("device is not in trusted_device_ids")
        elif not trusted_device_ids and registry_entry is None:
            reasons.append("no trusted_device_ids policy configured")

        if allowed_transports:
            if transport in allowed_transports:
                reasons.append(f"transport {transport} is allowed")
            else:
                decision = _stronger_decision(decision, default_decision if default_decision != "allow" else "review")
                reasons.append(f"transport {transport or 'unknown'} is not in allowed_transports")
        else:
            reasons.append("no allowed_transports policy configured")

        registry_transports = {
            str(item).strip()
            for item in list((registry_entry or {}).get("allowed_transports") or [])
            if str(item).strip()
        }
        if registry_transports:
            if transport in registry_transports:
                reasons.append(f"transport {transport} is allowed by local trust registry")
            else:
                decision = _stronger_decision(decision, "review")
                reasons.append(f"transport {transport or 'unknown'} is not allowed by local trust registry")

        if not endpoint_key:
            decision = _stronger_decision(decision, default_decision if default_decision != "allow" else "review")
            reasons.append("sync manifest does not include an endpoint key")

    if max_snapshot_age_hours is not None:
        snapshot_created_at = _parse_timestamp(str(snapshot_manifest_payload.get("created_at") or ""))
        age_hours = (datetime.now(timezone.utc) - snapshot_created_at).total_seconds() / 3600.0
        if age_hours > max_snapshot_age_hours:
            decision = _stronger_decision(decision, default_decision if default_decision != "allow" else "review")
            reasons.append(f"snapshot is older than {max_snapshot_age_hours} hour(s)")
        else:
            reasons.append("snapshot age is within trust policy limits")

    if not reasons:
        reasons.append("replica trust policy passed")

    return {
        "schema_version": REPLICA_TRUST_EVAL_SCHEMA_VERSION,
        "decision": decision,
        "requires_human_review": decision == "review",
        "replica_root": verification["replica_root"],
        "snapshot_id": verification["snapshot_id"],
        "sync_manifest_path": verification.get("sync_manifest_path"),
        "device_id": None if sync_manifest_payload is None else sync_manifest_payload.get("device_id"),
        "transport": None if sync_manifest_payload is None else sync_manifest_payload.get("transport"),
        "endpoint_key": None if sync_manifest_payload is None else sync_manifest_payload.get("endpoint_key"),
        "verification_status": verification["status"],
        "matched_policy": policy,
        "matched_registry_entry": registry_entry,
        "reasons": reasons,
    }


def import_replica(
    *,
    layout: VaultLayout,
    replica_root: Path,
    snapshot_id: str | None = None,
    sync_manifest_path: Path | None = None,
    trust_policy: dict[str, Any] | None = None,
    trust_registry: dict[str, Any] | None = None,
    reviewed_by: str | None = None,
) -> dict[str, Any]:
    verification = verify_replica(
        replica_root=replica_root,
        snapshot_id=snapshot_id,
        sync_manifest_path=sync_manifest_path,
    )
    if verification["status"] != "verified":
        raise ValueError("replica import requires a verified replica")
    trust_report = evaluate_replica_trust(
        replica_root=replica_root,
        snapshot_id=snapshot_id,
        sync_manifest_path=sync_manifest_path,
        trust_policy=trust_policy,
        trust_registry=trust_registry,
    )
    if trust_report["decision"] == "block":
        raise ValueError("replica trust policy blocked import")
    if trust_report["decision"] == "review" and not reviewed_by:
        raise ValueError("replica import requires reviewed_by under the trust policy")

    source_snapshot_manifest_path = Path(str(verification["snapshot_manifest_path"]))
    source_restore_bundle_path = Path(str(verification["restore_bundle_path"]))
    source_sync_manifest_path = (
        Path(str(verification["sync_manifest_path"])) if verification.get("sync_manifest_path") else None
    )

    destination_snapshot_dir = layout.exports_dir / "snapshots"
    destination_bundle_dir = layout.exports_dir / "snapshot-bundles"
    destination_sync_manifest_dir = layout.exports_dir / "imported-sync-manifests"
    destination_snapshot_dir.mkdir(parents=True, exist_ok=True)
    destination_bundle_dir.mkdir(parents=True, exist_ok=True)
    destination_sync_manifest_dir.mkdir(parents=True, exist_ok=True)

    destination_bundle_path = destination_bundle_dir / source_restore_bundle_path.name
    bundle_action = _copy_file_if_needed(source_restore_bundle_path, destination_bundle_path)

    source_manifest = _load_json(source_snapshot_manifest_path)
    imported_manifest = dict(source_manifest)
    restore_bundle = dict(imported_manifest.get("restore_bundle") or {})
    restore_bundle["path"] = str(destination_bundle_path.resolve())
    imported_manifest["restore_bundle"] = restore_bundle
    imported_manifest["replica_source"] = {
        "replica_root": str(Path(str(verification["replica_root"])).resolve()),
        "snapshot_manifest_path": str(source_snapshot_manifest_path.resolve()),
        "sync_manifest_path": str(source_sync_manifest_path.resolve()) if source_sync_manifest_path is not None else None,
    }

    destination_snapshot_manifest_path = destination_snapshot_dir / source_snapshot_manifest_path.name
    if destination_snapshot_manifest_path.exists():
        existing_manifest = _load_json(destination_snapshot_manifest_path)
        if _equivalent_snapshot_manifest(existing_manifest, imported_manifest):
            snapshot_action = "skipped"
        else:
            raise ValueError(f"destination conflict for {destination_snapshot_manifest_path}")
    else:
        snapshot_action = _write_json_if_needed(destination_snapshot_manifest_path, imported_manifest)

    imported_sync_manifest_path: Path | None = None
    sync_manifest_action: str | None = None
    if source_sync_manifest_path is not None:
        imported_sync_manifest_path = destination_sync_manifest_dir / source_sync_manifest_path.name
        sync_manifest_action = _copy_file_if_needed(source_sync_manifest_path, imported_sync_manifest_path)

    receipt_dir = layout.exports_dir / "replica-import-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    imported_at_dt = datetime.now(timezone.utc)
    imported_at = imported_at_dt.isoformat()
    timestamp_token = imported_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    receipt_id = f"replica_import_{timestamp_token}_{str(verification['snapshot_id'])[-8:]}"
    receipt_path = receipt_dir / f"{receipt_id}.json"

    receipt = {
        "schema_version": REPLICA_IMPORT_RECEIPT_SCHEMA_VERSION,
        "id": receipt_id,
        "imported_at": imported_at,
        "snapshot_id": verification["snapshot_id"],
        "replica_root": verification["replica_root"],
        "source_snapshot_manifest_path": str(source_snapshot_manifest_path.resolve()),
        "source_restore_bundle_path": str(source_restore_bundle_path.resolve()),
        "source_sync_manifest_path": str(source_sync_manifest_path.resolve()) if source_sync_manifest_path is not None else None,
        "imported_snapshot_manifest_path": str(destination_snapshot_manifest_path.resolve()),
        "imported_restore_bundle_path": str(destination_bundle_path.resolve()),
        "imported_sync_manifest_path": str(imported_sync_manifest_path.resolve()) if imported_sync_manifest_path is not None else None,
        "actions": {
            "snapshot_manifest": snapshot_action,
            "restore_bundle": bundle_action,
            "sync_manifest": sync_manifest_action,
        },
        "verification_status": verification["status"],
        "trust_decision": trust_report["decision"],
        "trust_reasons": trust_report["reasons"],
        "reviewed_by": reviewed_by,
        "status": "imported",
    }
    _write_json(receipt_path, receipt)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": imported_at,
        "operation": "replica.import",
        "snapshot_id": verification["snapshot_id"],
        "receipt_id": receipt_id,
        "receipt_path": str(receipt_path.resolve()),
        "replica_root": verification["replica_root"],
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "receipt_path": str(receipt_path.resolve()),
        "receipt": receipt,
        "verification": verification,
        "trust_report": trust_report,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def apply_replica(
    *,
    root: Path,
    layout: VaultLayout,
    replica_root: Path,
    snapshot_id: str | None = None,
    sync_manifest_path: Path | None = None,
    include_workspace: bool = True,
    include_vault: bool = True,
    allow_deletes: bool = False,
    reviewed_by: str | None = None,
    refresh_indexes: bool = True,
    trust_policy: dict[str, Any] | None = None,
    trust_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verification = verify_replica(
        replica_root=replica_root,
        snapshot_id=snapshot_id,
        sync_manifest_path=sync_manifest_path,
    )
    conflict_marker = None
    current_local_snapshot_id = _current_local_snapshot_id(layout)
    if current_local_snapshot_id and current_local_snapshot_id != str(verification["snapshot_id"]):
        conflict_marker = _write_sync_conflict_marker(
            layout=layout,
            local_snapshot_id=current_local_snapshot_id,
            incoming_snapshot_id=str(verification["snapshot_id"]),
            replica_root=Path(str(verification["replica_root"])),
            sync_manifest_path=(
                Path(str(verification["sync_manifest_path"]))
                if verification.get("sync_manifest_path")
                else None
            ),
            reviewed_by=reviewed_by,
            reason="incoming replica snapshot differs from current local snapshot",
        )
        if not reviewed_by:
            raise ValueError("replica apply requires reviewed_by when incoming snapshot differs from current local snapshot")

    imported = import_replica(
        layout=layout,
        replica_root=replica_root,
        snapshot_id=snapshot_id,
        sync_manifest_path=sync_manifest_path,
        trust_policy=trust_policy,
        trust_registry=trust_registry,
        reviewed_by=reviewed_by,
    )
    effective_snapshot_id = str(imported["receipt"]["snapshot_id"])
    restored = apply_restore(
        root=root,
        layout=layout,
        snapshot_id=effective_snapshot_id,
        include_workspace=include_workspace,
        include_vault=include_vault,
        allow_deletes=allow_deletes,
        reviewed_by=reviewed_by,
        refresh_indexes=refresh_indexes,
    )

    receipt_dir = layout.exports_dir / "replica-apply-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    applied_at_dt = datetime.now(timezone.utc)
    applied_at = applied_at_dt.isoformat()
    timestamp_token = applied_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    receipt_id = f"replica_apply_{timestamp_token}_{effective_snapshot_id[-8:]}"
    receipt_path = receipt_dir / f"{receipt_id}.json"

    receipt = {
        "schema_version": REPLICA_APPLY_RECEIPT_SCHEMA_VERSION,
        "id": receipt_id,
        "applied_at": applied_at,
        "snapshot_id": effective_snapshot_id,
        "replica_root": str(Path(str(imported["receipt"]["replica_root"])).resolve()),
        "include_workspace": include_workspace,
        "include_vault": include_vault,
        "allow_deletes": allow_deletes,
        "reviewed_by": reviewed_by,
        "refresh_indexes": bool(include_vault and refresh_indexes),
        "verification_status": imported["verification"]["status"],
        "trust_decision": imported["trust_report"]["decision"],
        "import_receipt_path": imported["receipt_path"],
        "restore_receipt_path": restored["receipt_path"],
        "conflict_marker_path": None if conflict_marker is None else conflict_marker["conflict_marker_path"],
        "summary": restored["receipt"]["summary"],
        "status": "applied",
    }
    _write_json(receipt_path, receipt)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": applied_at,
        "operation": "replica.apply",
        "snapshot_id": effective_snapshot_id,
        "receipt_id": receipt_id,
        "receipt_path": str(receipt_path.resolve()),
        "replica_root": str(Path(str(imported["receipt"]["replica_root"])).resolve()),
        "include_workspace": include_workspace,
        "include_vault": include_vault,
        "allow_deletes": allow_deletes,
        "reviewed_by": reviewed_by,
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "receipt_path": str(receipt_path.resolve()),
        "receipt": receipt,
        "imported": imported,
        "restored": restored,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def apply_restore(
    *,
    root: Path,
    layout: VaultLayout,
    snapshot_id: str,
    include_workspace: bool = True,
    include_vault: bool = True,
    allow_deletes: bool = False,
    reviewed_by: str | None = None,
    refresh_indexes: bool = True,
) -> dict[str, Any]:
    plan = plan_restore(
        root=root,
        layout=layout,
        snapshot_id=snapshot_id,
        include_workspace=include_workspace,
        include_vault=include_vault,
    )
    if plan["requires_review"]:
        if not allow_deletes:
            raise ValueError("restore apply requires allow_deletes when the plan includes delete actions")
        if not reviewed_by:
            raise ValueError("restore apply with delete actions requires reviewed_by")

    manifest_path = _snapshot_manifest_path(layout, snapshot_id)
    manifest = _load_json(manifest_path)
    restore_bundle = manifest.get("restore_bundle") if isinstance(manifest.get("restore_bundle"), dict) else {}
    restore_bundle_path = _restore_bundle_path(root, restore_bundle)
    combined_summary = plan["summary"]["combined"]
    if combined_summary["write"] > 0 and restore_bundle_path is None:
        raise ValueError(f"snapshot {snapshot_id} does not include a restore bundle")

    if restore_bundle_path is not None:
        missing = _missing_bundle_paths(plan, restore_bundle_path)
        if missing:
            raise ValueError(f"restore bundle for snapshot {snapshot_id} is missing {len(missing)} file(s)")

    written_paths = _apply_restore_writes(root, plan, restore_bundle_path)
    deleted_paths = _apply_restore_deletes(root, plan) if allow_deletes else []

    index_refresh: dict[str, Any] | None = None
    if include_vault and refresh_indexes:
        index_refresh = CtxVault(layout).rebuild_indexes()

    receipt_dir = layout.exports_dir / "restore-receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    applied_at_dt = datetime.now(timezone.utc)
    applied_at = applied_at_dt.isoformat()
    timestamp_token = applied_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    receipt_id = f"restore_{timestamp_token}_{snapshot_id[-8:]}"
    receipt_path = receipt_dir / f"{receipt_id}.json"

    receipt = {
        "schema_version": RESTORE_RECEIPT_SCHEMA_VERSION,
        "id": receipt_id,
        "applied_at": applied_at,
        "snapshot_id": str(manifest.get("snapshot_id") or snapshot_id),
        "snapshot_manifest_path": str(manifest_path.resolve()),
        "restore_bundle_path": str(restore_bundle_path.resolve()) if restore_bundle_path is not None else None,
        "scope": manifest.get("scope") or {},
        "include_workspace": include_workspace,
        "include_vault": include_vault,
        "allow_deletes": allow_deletes,
        "reviewed_by": reviewed_by,
        "refresh_indexes": bool(include_vault and refresh_indexes),
        "summary": plan["summary"],
        "written_paths": written_paths,
        "deleted_paths": deleted_paths,
        "requires_review": plan["requires_review"],
        "status": "applied",
        "index_refresh": index_refresh,
    }
    _write_json(receipt_path, receipt)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": applied_at,
        "operation": "snapshot.restore",
        "snapshot_id": receipt["snapshot_id"],
        "receipt_id": receipt_id,
        "receipt_path": str(receipt_path.resolve()),
        "include_workspace": include_workspace,
        "include_vault": include_vault,
        "allow_deletes": allow_deletes,
        "reviewed_by": reviewed_by,
    }
    _append_jsonl(operation_log_path, operation)

    return {
        "receipt_path": str(receipt_path.resolve()),
        "receipt": receipt,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
        "plan": plan,
        "index_refresh": index_refresh,
    }


def sync_status(*, layout: VaultLayout, limit: int = 50) -> dict[str, Any]:
    snapshots = list_snapshots(layout=layout, limit=10000)
    latest_snapshot = snapshots[0] if snapshots else None
    snapshot_rank = {item["snapshot_id"]: index for index, item in enumerate(snapshots)}
    current_local_snapshot_id = _current_local_snapshot_id(layout) or (latest_snapshot["snapshot_id"] if latest_snapshot else None)
    current_local_snapshot = next(
        (item for item in snapshots if item["snapshot_id"] == current_local_snapshot_id),
        latest_snapshot,
    )
    receipt_items = _list_sync_receipts(layout=layout, limit=limit)

    latest_by_endpoint: dict[str, dict[str, Any]] = {}
    for receipt in receipt_items:
        endpoint_key = _sync_endpoint_key(receipt)
        if endpoint_key not in latest_by_endpoint:
            latest_by_endpoint[endpoint_key] = receipt

    targets: list[dict[str, Any]] = []
    for endpoint_key, receipt in sorted(
        latest_by_endpoint.items(),
        key=lambda item: (
            str(item[1].get("created_at") or ""),
            str(item[1].get("id") or ""),
            item[0],
        ),
        reverse=True,
    ):
        receipt_snapshot_id = str(receipt.get("snapshot_id") or "")
        receipt_rank = snapshot_rank.get(receipt_snapshot_id)
        current_rank = snapshot_rank.get(current_local_snapshot["snapshot_id"]) if current_local_snapshot is not None else None
        if latest_snapshot is None:
            state = "no_local_snapshots"
            snapshot_lag = None
            pending_snapshot_ids: list[str] = []
        elif current_local_snapshot is not None and receipt_snapshot_id == current_local_snapshot["snapshot_id"]:
            state = "in_sync"
            snapshot_lag = 0
            pending_snapshot_ids = []
        elif receipt_rank is None or current_rank is None:
            state = "snapshot_missing"
            snapshot_lag = None
            pending_snapshot_ids = []
        elif receipt_rank > current_rank:
            state = "behind"
            snapshot_lag = receipt_rank - current_rank
            pending_snapshot_ids = [item["snapshot_id"] for item in snapshots[current_rank:receipt_rank]]
        elif receipt_rank < current_rank:
            state = "ahead_of_local_state"
            snapshot_lag = current_rank - receipt_rank
            pending_snapshot_ids = []
        else:
            state = "snapshot_missing"
            snapshot_lag = None
            pending_snapshot_ids = []
        targets.append(
            {
                "endpoint_key": endpoint_key,
                "device_id": receipt.get("device_id"),
                "target": receipt.get("target"),
                "transport": receipt.get("transport"),
                "latest_sync_at": receipt.get("created_at"),
                "snapshot_id": receipt_snapshot_id,
                "combined_digest": receipt.get("combined_digest"),
                "state": state,
                "snapshot_lag": snapshot_lag,
                "pending_snapshot_ids": pending_snapshot_ids,
                "receipt_path": receipt.get("receipt_path"),
            }
        )

    out_of_date = [target for target in targets if target["state"] not in {"in_sync", "no_local_snapshots"}]
    return {
        "latest_local_snapshot": latest_snapshot,
        "current_local_snapshot": current_local_snapshot,
        "summary": {
            "target_count": len(targets),
            "out_of_date_target_count": len(out_of_date),
            "receipt_count": len(receipt_items),
        },
        "targets": targets,
    }


def list_transport_events(*, layout: VaultLayout, limit: int = 20) -> dict[str, Any]:
    events = [
        operation
        for operation in _list_operations(layout)
        if str(operation.get("operation") or "").startswith(("snapshot.", "replica.", "sync.", "mutation."))
    ]
    events.sort(
        key=lambda item: (
            str(item.get("timestamp") or ""),
            str(item.get("receipt_id") or item.get("snapshot_id") or item.get("mutation_id") or ""),
        ),
        reverse=True,
    )
    returned = events[:limit]
    return {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "summary": {
            "event_count": len(events),
            "returned_count": len(returned),
        },
        "events": returned,
    }


def list_replica_trust_devices(*, layout: VaultLayout) -> dict[str, Any]:
    registry = _load_replica_trust_registry(layout)
    devices = [
        dict(entry)
        for entry in sorted(
            (registry.get("devices") or {}).values(),
            key=lambda item: (str(item.get("device_id") or ""), str(item.get("updated_at") or "")),
        )
    ]
    return {
        "schema_version": REPLICA_TRUST_REGISTRY_SCHEMA_VERSION,
        "registry_path": str(_replica_trust_registry_path(layout).resolve()),
        "updated_at": registry.get("updated_at"),
        "device_count": len(devices),
        "devices": devices,
    }


def emit_pairing_offer(
    *,
    layout: VaultLayout,
    device_id: str,
    label: str | None = None,
    notes: str | None = None,
    allowed_transports: list[str] | None = None,
    pairing_id: str | None = None,
    expires_in_hours: int = 24,
) -> dict[str, Any]:
    normalized_device_id = device_id.strip()
    if not normalized_device_id:
        raise ValueError("device_id must not be empty")
    if expires_in_hours < 1:
        raise ValueError("expires_in_hours must be at least 1")

    pairing_dir = layout.exports_dir / "pairing-offers"
    pairing_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    created_at_dt = datetime.now(timezone.utc)
    created_at = created_at_dt.isoformat()
    expires_at = (created_at_dt + timedelta(hours=expires_in_hours)).isoformat()
    timestamp_token = created_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    effective_pairing_id = pairing_id or f"pairing_{timestamp_token}_{_slug_token(normalized_device_id)[:16]}"
    offer_path = pairing_dir / f"{effective_pairing_id}.json"
    offer = {
        "schema_version": PAIRING_OFFER_SCHEMA_VERSION,
        "pairing_id": effective_pairing_id,
        "created_at": created_at,
        "expires_at": expires_at,
        "device_id": normalized_device_id,
        "label": label,
        "notes": notes,
        "allowed_transports": sorted(
            {
                str(item).strip()
                for item in list(allowed_transports or [])
                if str(item).strip()
            }
        ),
        "status": "open",
    }
    _write_json(offer_path, offer)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": created_at,
        "operation": "replica.pairing-offer",
        "pairing_id": effective_pairing_id,
        "device_id": normalized_device_id,
        "offer_path": str(offer_path.resolve()),
    }
    _append_jsonl(operation_log_path, operation)
    return {
        "pairing_offer_path": str(offer_path.resolve()),
        "pairing_offer": offer,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def list_pairing_offers(
    *,
    layout: VaultLayout,
    limit: int = 50,
    include_expired: bool = False,
) -> dict[str, Any]:
    pairing_dir = layout.exports_dir / "pairing-offers"
    if not pairing_dir.exists():
        return {
            "schema_version": PAIRING_OFFER_SCHEMA_VERSION,
            "pairing_offer_dir": str(pairing_dir.resolve()),
            "summary": {"offer_count": 0, "returned_count": 0},
            "offers": [],
        }
    now = datetime.now(timezone.utc)
    offers: list[dict[str, Any]] = []
    for path in sorted(pairing_dir.glob("*.json")):
        payload = _load_json(path)
        expires_at = _parse_timestamp(str(payload.get("expires_at") or ""))
        is_expired = expires_at < now
        if is_expired and not include_expired:
            continue
        offers.append(
            {
                **payload,
                "pairing_offer_path": str(path.resolve()),
                "is_expired": is_expired,
            }
        )
    offers.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("pairing_id") or "")), reverse=True)
    returned = offers[:limit]
    return {
        "schema_version": PAIRING_OFFER_SCHEMA_VERSION,
        "pairing_offer_dir": str(pairing_dir.resolve()),
        "summary": {"offer_count": len(offers), "returned_count": len(returned)},
        "offers": returned,
    }


def accept_pairing_offer(
    *,
    layout: VaultLayout,
    pairing_offer_path: Path,
    trust_state: str = "allow",
    reviewed_by: str,
    label: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    normalized_reviewer = reviewed_by.strip()
    if not normalized_reviewer:
        raise ValueError("reviewed_by must not be empty")
    offer_path = pairing_offer_path.resolve()
    offer = _load_json(offer_path)
    if str(offer.get("schema_version") or "") != PAIRING_OFFER_SCHEMA_VERSION:
        raise ValueError(f"unsupported pairing offer schema_version: {offer.get('schema_version')}")
    expires_at = _parse_timestamp(str(offer.get("expires_at") or ""))
    if expires_at < datetime.now(timezone.utc):
        raise ValueError("pairing offer has expired")
    accepted_at = datetime.now(timezone.utc).isoformat()

    trust_result = set_replica_device_trust(
        layout=layout,
        device_id=str(offer.get("device_id") or ""),
        trust_state=trust_state,
        label=label if label is not None else offer.get("label"),
        notes=notes if notes is not None else offer.get("notes"),
        allowed_transports=[
            str(item).strip()
            for item in list(offer.get("allowed_transports") or [])
            if str(item).strip()
        ],
    )
    updated_offer = {
        **offer,
        "status": "accepted",
        "accepted_at": accepted_at,
        "accepted_by": normalized_reviewer,
        "accepted_trust_state": trust_state,
    }
    _write_json(offer_path, updated_offer)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)
    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": accepted_at,
        "operation": "replica.pairing-accept",
        "pairing_id": str(offer.get("pairing_id") or offer_path.stem),
        "device_id": str(offer.get("device_id") or ""),
        "offer_path": str(offer_path.resolve()),
        "trust_state": trust_state,
        "reviewed_by": normalized_reviewer,
    }
    _append_jsonl(operation_log_path, operation)
    return {
        "pairing_offer_path": str(offer_path.resolve()),
        "pairing_offer": updated_offer,
        "trust_result": trust_result,
        "accepted_by": normalized_reviewer,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def load_replica_trust_registry(*, layout: VaultLayout) -> dict[str, Any]:
    return _load_replica_trust_registry(layout)


def set_replica_device_trust(
    *,
    layout: VaultLayout,
    device_id: str,
    trust_state: str,
    label: str | None = None,
    notes: str | None = None,
    allowed_transports: list[str] | None = None,
) -> dict[str, Any]:
    normalized_device_id = device_id.strip()
    if not normalized_device_id:
        raise ValueError("device_id must not be empty")
    if trust_state not in {"allow", "review", "block"}:
        raise ValueError(f"unsupported trust_state: {trust_state}")

    registry = _load_replica_trust_registry(layout)
    devices = dict(registry.get("devices") or {})
    updated_at = datetime.now(timezone.utc).isoformat()
    entry = {
        "device_id": normalized_device_id,
        "trust_state": trust_state,
        "label": label,
        "notes": notes,
        "allowed_transports": sorted(
            {
                str(item).strip()
                for item in list(allowed_transports or [])
                if str(item).strip()
            }
        ),
        "updated_at": updated_at,
    }
    devices[normalized_device_id] = entry
    registry_payload = {
        "schema_version": REPLICA_TRUST_REGISTRY_SCHEMA_VERSION,
        "updated_at": updated_at,
        "devices": devices,
    }
    registry_path = _replica_trust_registry_path(layout)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(registry_path, registry_payload)

    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)
    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": updated_at,
        "operation": "replica.trust-set",
        "device_id": normalized_device_id,
        "trust_state": trust_state,
        "registry_path": str(registry_path.resolve()),
    }
    _append_jsonl(operation_log_path, operation)
    return {
        "registry_path": str(registry_path.resolve()),
        "entry": entry,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def snapshot_lineage(
    *,
    layout: VaultLayout,
    snapshot_id: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("snapshot lineage limit must be at least 1")

    matched = []
    for operation in _list_operations(layout):
        current_snapshot_id = str(operation.get("snapshot_id") or "").strip()
        if snapshot_id and current_snapshot_id != snapshot_id:
            continue
        matched.append(operation)

    events = matched[-limit:]
    counts_by_operation: dict[str, int] = {}
    for event in matched:
        operation_name = str(event.get("operation") or "").strip() or "unknown"
        counts_by_operation[operation_name] = counts_by_operation.get(operation_name, 0) + 1

    return {
        "snapshot_id": snapshot_id,
        "summary": {
            "matched_event_count": len(matched),
            "returned_event_count": len(events),
            "operation_count_by_type": counts_by_operation,
        },
        "events": events,
    }


def list_sync_conflicts(
    *,
    layout: VaultLayout,
    limit: int = 50,
    status: str | None = None,
) -> dict[str, Any]:
    conflict_dir = layout.exports_dir / "sync-conflicts"
    if not conflict_dir.exists():
        return {
            "schema_version": SYNC_CONFLICT_MARKER_SCHEMA_VERSION,
            "conflict_dir": str(conflict_dir.resolve()),
            "summary": {"conflict_count": 0, "returned_count": 0, "status": status},
            "conflicts": [],
        }
    normalized_status = str(status or "").strip() or None
    conflicts: list[dict[str, Any]] = []
    for path in sorted(conflict_dir.glob("*.json")):
        payload = _load_json(path)
        if normalized_status is not None and str(payload.get("status") or "").strip() != normalized_status:
            continue
        conflicts.append({**payload, "conflict_marker_path": str(path.resolve())})
    conflicts.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    returned = conflicts[:limit]
    return {
        "schema_version": SYNC_CONFLICT_MARKER_SCHEMA_VERSION,
        "conflict_dir": str(conflict_dir.resolve()),
        "summary": {"conflict_count": len(conflicts), "returned_count": len(returned), "status": normalized_status},
        "conflicts": returned,
    }


def review_sync_conflict(
    *,
    layout: VaultLayout,
    conflict_marker_path: Path,
    reviewed_by: str,
    resolution: str,
    notes: str | None = None,
) -> dict[str, Any]:
    normalized_reviewer = reviewed_by.strip()
    if not normalized_reviewer:
        raise ValueError("reviewed_by must not be empty")
    normalized_resolution = resolution.strip()
    if normalized_resolution not in {"kept_local", "accepted_remote", "needs_followup"}:
        raise ValueError(f"unsupported sync conflict resolution: {resolution}")

    marker_path = conflict_marker_path.resolve()
    payload = _load_json(marker_path)
    if str(payload.get("schema_version") or "") != SYNC_CONFLICT_MARKER_SCHEMA_VERSION:
        raise ValueError(f"unsupported sync conflict schema_version: {payload.get('schema_version')}")

    reviewed_at = datetime.now(timezone.utc).isoformat()
    updated = {
        **payload,
        "status": "reviewed",
        "reviewed_by": normalized_reviewer,
        "reviewed_at": reviewed_at,
        "resolution": normalized_resolution,
        "review_notes": notes,
    }
    _write_json(marker_path, updated)

    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)
    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": reviewed_at,
        "operation": "sync.conflict-review",
        "conflict_id": str(updated.get("id") or marker_path.stem),
        "resolution": normalized_resolution,
        "reviewed_by": normalized_reviewer,
        "conflict_marker_path": str(marker_path.resolve()),
    }
    _append_jsonl(operation_log_path, operation)
    return {
        "conflict_marker_path": str(marker_path.resolve()),
        "conflict_marker": updated,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def snapshot_provenance(
    *,
    layout: VaultLayout,
    snapshot_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    manifest_path = _snapshot_manifest_path(layout, snapshot_id)
    manifest = _load_json(manifest_path)
    replica_source_payload = manifest.get("replica_source") if isinstance(manifest.get("replica_source"), dict) else {}
    source_snapshot_manifest = _load_optional_json_path(replica_source_payload.get("snapshot_manifest_path"))
    source_sync_manifest = _load_optional_json_path(replica_source_payload.get("sync_manifest_path"))

    source_device_id = None if source_sync_manifest is None else str(source_sync_manifest.get("device_id") or "").strip() or None
    trust_registry = _load_replica_trust_registry(layout)
    trust_registry_entry = _replica_trust_registry_entry(trust_registry, source_device_id or "")
    local_restore_bundle = manifest.get("restore_bundle") if isinstance(manifest.get("restore_bundle"), dict) else {}

    return {
        "schema_version": SNAPSHOT_PROVENANCE_SCHEMA_VERSION,
        "snapshot_id": str(manifest.get("snapshot_id") or snapshot_id),
        "manifest_path": str(manifest_path.resolve()),
        "created_at": manifest.get("created_at"),
        "scope": manifest.get("scope") or {},
        "label": manifest.get("label"),
        "parent_snapshot_id": manifest.get("parent_snapshot_id"),
        "combined_digest": str((((manifest.get("summary") or {}).get("combined_digest")) or "")),
        "restore_bundle_path": str(local_restore_bundle.get("path") or ""),
        "is_imported_replica": bool(replica_source_payload),
        "replica_source": None
        if not replica_source_payload
        else {
            "replica_root": replica_source_payload.get("replica_root"),
            "snapshot_manifest_path": replica_source_payload.get("snapshot_manifest_path"),
            "snapshot_manifest_exists": source_snapshot_manifest is not None,
            "source_snapshot_id": None if source_snapshot_manifest is None else source_snapshot_manifest.get("snapshot_id"),
            "source_snapshot_created_at": None if source_snapshot_manifest is None else source_snapshot_manifest.get("created_at"),
            "source_scope": {} if source_snapshot_manifest is None else (source_snapshot_manifest.get("scope") or {}),
            "sync_manifest_path": replica_source_payload.get("sync_manifest_path"),
            "sync_manifest_exists": source_sync_manifest is not None,
            "device_id": source_device_id,
            "transport": None if source_sync_manifest is None else source_sync_manifest.get("transport"),
            "target": None if source_sync_manifest is None else source_sync_manifest.get("target"),
            "endpoint_key": None if source_sync_manifest is None else source_sync_manifest.get("endpoint_key"),
        },
        "trust_registry_entry": trust_registry_entry,
        "lineage": snapshot_lineage(layout=layout, snapshot_id=snapshot_id, limit=limit),
    }


def plan_restore(
    *,
    root: Path,
    layout: VaultLayout,
    snapshot_id: str,
    include_workspace: bool = True,
    include_vault: bool = True,
) -> dict[str, Any]:
    if not include_workspace and not include_vault:
        raise ValueError("restore plan must include workspace, vault, or both")

    root = root.resolve()
    manifest_path = _snapshot_manifest_path(layout, snapshot_id)
    manifest = _load_json(manifest_path)

    workspace_current = _entry_map(
        [_file_entry(root, path) for path in collect_workspace_files(root, excluded_prefixes=(layout.exports_dir,))]
    )
    vault_current_objects = _entry_map([_file_entry(root, path) for path in _collect_vault_paths(layout.objects_dir)])
    vault_current_reviews = _entry_map([_file_entry(root, path) for path in _collect_vault_paths(layout.reviews_dir)])

    workspace_target = _entry_map(list(manifest.get("workspace_files") or []))
    vault_target = manifest.get("vault_files") if isinstance(manifest.get("vault_files"), dict) else {}
    vault_target_objects = _entry_map(list(vault_target.get("objects") or []))
    vault_target_reviews = _entry_map(list(vault_target.get("reviews") or []))

    workspace_plan = _restore_section_plan(workspace_target, workspace_current) if include_workspace else _empty_restore_plan()
    object_plan = _restore_section_plan(vault_target_objects, vault_current_objects) if include_vault else _empty_restore_plan()
    review_plan = _restore_section_plan(vault_target_reviews, vault_current_reviews) if include_vault else _empty_restore_plan()
    vault_plan = _merge_restore_plans(object_plan, review_plan)
    combined_plan = _merge_restore_plans(workspace_plan, vault_plan)

    warnings: list[str] = []
    indexes = [str(path) for path in manifest.get("rebuildable_indexes", []) if str(path).strip()]
    if include_vault and indexes:
        warnings.append("SQLite and other rebuildable indexes should be refreshed after applying this restore plan.")

    return {
        "snapshot_id": str(manifest.get("snapshot_id") or snapshot_id),
        "manifest_path": str(manifest_path.resolve()),
        "scope": manifest.get("scope") or {},
        "include_workspace": include_workspace,
        "include_vault": include_vault,
        "restore_bundle_available": bool((((manifest.get("restore_bundle") or {}).get("path")) or "")),
        "restore_bundle_path": str((((manifest.get("restore_bundle") or {}).get("path")) or "")),
        "summary": {
            "workspace": workspace_plan["summary"],
            "vault": vault_plan["summary"],
            "combined": combined_plan["summary"],
        },
        "actions": {
            "workspace": workspace_plan["actions"],
            "vault_objects": object_plan["actions"],
            "vault_reviews": review_plan["actions"],
        },
        "requires_review": combined_plan["summary"]["delete"] > 0,
        "rebuildable_indexes": indexes,
        "warnings": warnings,
    }


def _collect_vault_paths(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return [path.resolve() for path in sorted(base_dir.rglob("*.json")) if path.is_file()]


def _latest_snapshot_id(snapshot_dir: Path) -> str | None:
    snapshots = sorted(snapshot_dir.glob("*.json"))
    if not snapshots:
        return None
    latest = json.loads(snapshots[-1].read_text(encoding="utf-8"))
    snapshot_id = str(latest.get("snapshot_id") or "").strip()
    return snapshot_id or None


def _snapshot_manifest_path(layout: VaultLayout, snapshot_id: str) -> Path:
    snapshot_dir = layout.exports_dir / "snapshots"
    candidate = snapshot_dir / f"{snapshot_id}.json"
    if not candidate.exists():
        raise KeyError(f"unknown snapshot {snapshot_id}")
    return candidate


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected object payload in {path}")
    return payload


def _load_optional_json_path(raw_path: Any) -> dict[str, Any] | None:
    path_text = str(raw_path or "").strip()
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = path.expanduser()
    if not path.exists():
        return None
    return _load_json(path.resolve())


def _restore_bundle_path(root: Path, restore_bundle: dict[str, Any]) -> Path | None:
    raw_path = str(restore_bundle.get("path") or "").strip()
    if not raw_path:
        return None
    bundle_path = Path(raw_path)
    return bundle_path if bundle_path.is_absolute() else (root / bundle_path).resolve()


def _missing_bundle_paths(plan: dict[str, Any], bundle_path: Path) -> list[str]:
    required = _restore_write_paths(plan)
    if not required:
        return []
    with tarfile.open(bundle_path, mode="r:gz") as tar_handle:
        available = {member.name for member in tar_handle.getmembers() if member.isfile()}
    return [path for path in required if path not in available]


def _apply_restore_writes(root: Path, plan: dict[str, Any], bundle_path: Path | None) -> list[str]:
    required = _restore_write_paths(plan)
    if not required:
        return []
    if bundle_path is None:
        raise ValueError("restore bundle is required when the restore plan includes write actions")
    written: list[str] = []
    with tarfile.open(bundle_path, mode="r:gz") as tar_handle:
        for path in required:
            member = tar_handle.getmember(path)
            extracted = tar_handle.extractfile(member)
            if extracted is None:
                raise ValueError(f"restore bundle entry {path} has no readable content")
            destination = (root / path).resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(extracted.read())
            written.append(path)
    return written


def _apply_restore_deletes(root: Path, plan: dict[str, Any]) -> list[str]:
    deleted: list[str] = []
    for section in ("workspace", "vault_objects", "vault_reviews"):
        actions = ((plan.get("actions") or {}).get(section) or {}).get("delete", [])
        for item in actions:
            path = str(item.get("path") or "").strip()
            if not path:
                continue
            destination = (root / path).resolve()
            if destination.exists():
                destination.unlink()
            deleted.append(path)
    return deleted


def _restore_write_paths(plan: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for section in ("workspace", "vault_objects", "vault_reviews"):
        actions = ((plan.get("actions") or {}).get(section) or {}).get("write", [])
        for item in actions:
            path = str(item.get("path") or "").strip()
            if path:
                paths.append(path)
    return paths


def _list_sync_receipts(*, layout: VaultLayout, limit: int) -> list[dict[str, Any]]:
    receipt_dir = layout.exports_dir / "sync-receipts"
    if not receipt_dir.exists():
        return []
    receipts: list[dict[str, Any]] = []
    for path in sorted(receipt_dir.glob("*.json")):
        payload = _load_json(path)
        payload["receipt_path"] = str(path.resolve())
        receipts.append(payload)
    receipts.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("id") or "")), reverse=True)
    return receipts[:limit]


def _sync_endpoint_key(receipt: dict[str, Any]) -> str:
    return _sync_endpoint_from_values(
        device_id=str(receipt.get("device_id") or "").strip() or None,
        target=str(receipt.get("target") or "").strip() or None,
        fallback=str(receipt.get("id") or "").strip() or None,
    )


def _sync_endpoint_from_values(
    *,
    device_id: str | None,
    target: str | None,
    fallback: str | None = None,
) -> str:
    if device_id:
        return device_id
    if target:
        return target
    return fallback or ""


def _current_local_snapshot_id(layout: VaultLayout) -> str | None:
    for payload in reversed(_list_operations(layout)):
        operation = str(payload.get("operation") or "")
        if operation in {"snapshot.create", "snapshot.restore"}:
            snapshot_id = str(payload.get("snapshot_id") or "").strip()
            if snapshot_id:
                return snapshot_id
    return None


def _list_operations(layout: VaultLayout) -> list[dict[str, Any]]:
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    if not operation_log_path.exists():
        return []
    operations: list[dict[str, Any]] = []
    for raw in operation_log_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        payload = json.loads(raw)
        if isinstance(payload, dict):
            operations.append(payload)
    return operations


def _replica_trust_registry_path(layout: VaultLayout) -> Path:
    return layout.vault_root / "replica-trust-registry.json"


def _load_replica_trust_registry(layout: VaultLayout) -> dict[str, Any]:
    path = _replica_trust_registry_path(layout)
    if not path.exists():
        return {
            "schema_version": REPLICA_TRUST_REGISTRY_SCHEMA_VERSION,
            "updated_at": None,
            "devices": {},
        }
    payload = _load_json(path)
    devices_payload = payload.get("devices") if isinstance(payload.get("devices"), dict) else {}
    devices: dict[str, dict[str, Any]] = {}
    for raw_device_id, raw_entry in devices_payload.items():
        device_id = str(raw_device_id or "").strip()
        if not device_id or not isinstance(raw_entry, dict):
            continue
        devices[device_id] = {
            "device_id": device_id,
            "trust_state": str(raw_entry.get("trust_state") or "review").strip() or "review",
            "label": raw_entry.get("label"),
            "notes": raw_entry.get("notes"),
            "allowed_transports": [
                str(item).strip()
                for item in list(raw_entry.get("allowed_transports") or [])
                if str(item).strip()
            ],
            "updated_at": raw_entry.get("updated_at"),
        }
    return {
        "schema_version": REPLICA_TRUST_REGISTRY_SCHEMA_VERSION,
        "updated_at": payload.get("updated_at"),
        "devices": devices,
    }


def _replica_trust_registry_entry(trust_registry: dict[str, Any] | None, device_id: str) -> dict[str, Any] | None:
    normalized_device_id = device_id.strip()
    if not normalized_device_id or not isinstance(trust_registry, dict):
        return None
    devices = trust_registry.get("devices")
    if not isinstance(devices, dict):
        return None
    entry = devices.get(normalized_device_id)
    return dict(entry) if isinstance(entry, dict) else None


def _select_replica_sync_manifest_path(replica_root: Path, sync_manifest_path: Path | None) -> Path | None:
    if sync_manifest_path is not None:
        candidate = sync_manifest_path if sync_manifest_path.is_absolute() else (replica_root / sync_manifest_path)
        return candidate.resolve()
    sync_manifest_dir = replica_root / "sync-manifests"
    candidates = sorted(sync_manifest_dir.glob("*.json"))
    return candidates[-1].resolve() if candidates else None


def _latest_replica_snapshot_id(replica_root: Path) -> str | None:
    snapshot_dir = replica_root / "snapshots"
    candidates = sorted(snapshot_dir.glob("*.json"))
    if not candidates:
        return None
    payload = _load_json(candidates[-1])
    snapshot_id = str(payload.get("snapshot_id") or "").strip()
    return snapshot_id or None


def _replica_restore_bundle_path(replica_root: Path, snapshot_manifest: dict[str, Any]) -> Path:
    restore_bundle = snapshot_manifest.get("restore_bundle") if isinstance(snapshot_manifest.get("restore_bundle"), dict) else {}
    bundle_name = Path(str(restore_bundle.get("path") or "")).name
    if not bundle_name:
        raise ValueError("replica snapshot manifest does not include a restore bundle path")
    return (replica_root / "snapshot-bundles" / bundle_name).resolve()


def _sync_manifest_artifact_paths(sync_manifest: dict[str, Any], sync_manifest_path: Path) -> list[Path]:
    paths = [Path(str(raw)).resolve() for raw in list(sync_manifest.get("artifact_paths") or []) if str(raw).strip()]
    paths.append(sync_manifest_path.resolve())
    unique: dict[str, Path] = {}
    for path in paths:
        unique[str(path)] = path
    return list(unique.values())


def _local_target_root(target: str) -> Path:
    target = target.strip()
    if not target:
        raise ValueError("sync manifest target must not be empty")
    if target.startswith("file://"):
        parsed = urlparse(target)
        return Path(unquote(parsed.path)).resolve()
    parsed = urlparse(target)
    if parsed.scheme and parsed.scheme != "file":
        raise ValueError(f"unsupported sync target scheme: {parsed.scheme}")
    return Path(target).expanduser().resolve()


def _sync_copy_destination(target_root: Path, artifact_path: Path) -> Path:
    parent_name = artifact_path.parent.name
    if parent_name == "snapshots":
        return target_root / "snapshots" / artifact_path.name
    if parent_name == "snapshot-bundles":
        return target_root / "snapshot-bundles" / artifact_path.name
    if parent_name == "sync-manifests":
        return target_root / "sync-manifests" / artifact_path.name
    return target_root / "artifacts" / artifact_path.name


def _copy_file_if_needed(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if _sha256_file(destination) == _sha256_file(source):
            return "skipped"
        raise ValueError(f"destination conflict for {destination}")
    destination.write_bytes(source.read_bytes())
    return "copied"


def _write_json_if_needed(path: Path, payload: dict[str, Any]) -> str:
    rendered = json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == rendered:
            return "skipped"
        raise ValueError(f"destination conflict for {path}")
    path.write_text(rendered, encoding="utf-8")
    return "written"


def _equivalent_snapshot_manifest(existing: dict[str, Any], imported: dict[str, Any]) -> bool:
    existing_snapshot_id = str(existing.get("snapshot_id") or "").strip()
    imported_snapshot_id = str(imported.get("snapshot_id") or "").strip()
    if not existing_snapshot_id or existing_snapshot_id != imported_snapshot_id:
        return False
    existing_digest = str((((existing.get("summary") or {}).get("combined_digest")) or "")).strip()
    imported_digest = str((((imported.get("summary") or {}).get("combined_digest")) or "")).strip()
    if existing_digest != imported_digest:
        return False
    existing_bundle_sha = str((((existing.get("restore_bundle") or {}).get("sha256")) or "")).strip()
    imported_bundle_sha = str((((imported.get("restore_bundle") or {}).get("sha256")) or "")).strip()
    return bool(existing_bundle_sha) and existing_bundle_sha == imported_bundle_sha


def _write_sync_conflict_marker(
    *,
    layout: VaultLayout,
    local_snapshot_id: str,
    incoming_snapshot_id: str,
    replica_root: Path,
    sync_manifest_path: Path | None,
    reviewed_by: str | None,
    reason: str,
) -> dict[str, Any]:
    conflict_dir = layout.exports_dir / "sync-conflicts"
    conflict_dir.mkdir(parents=True, exist_ok=True)
    operation_log_path = layout.exports_dir / "operation-log.jsonl"
    operation_log_path.parent.mkdir(parents=True, exist_ok=True)

    created_at_dt = datetime.now(timezone.utc)
    created_at = created_at_dt.isoformat()
    timestamp_token = created_at_dt.strftime("%Y%m%dT%H%M%S%fZ").lower()
    conflict_id = f"sync_conflict_{timestamp_token}_{incoming_snapshot_id[-8:]}"
    conflict_path = conflict_dir / f"{conflict_id}.json"
    payload = {
        "schema_version": SYNC_CONFLICT_MARKER_SCHEMA_VERSION,
        "id": conflict_id,
        "created_at": created_at,
        "status": "reviewed" if reviewed_by else "open",
        "requires_review": True,
        "reviewed_by": reviewed_by,
        "reason": reason,
        "local_snapshot_id": local_snapshot_id,
        "incoming_snapshot_id": incoming_snapshot_id,
        "replica_root": str(replica_root.resolve()),
        "sync_manifest_path": None if sync_manifest_path is None else str(sync_manifest_path.resolve()),
    }
    _write_json(conflict_path, payload)

    operation = {
        "schema_version": OPERATION_LOG_SCHEMA_VERSION,
        "timestamp": created_at,
        "operation": "sync.conflict-marker",
        "conflict_id": conflict_id,
        "local_snapshot_id": local_snapshot_id,
        "incoming_snapshot_id": incoming_snapshot_id,
        "reviewed_by": reviewed_by,
    }
    _append_jsonl(operation_log_path, operation)
    return {
        "conflict_marker_path": str(conflict_path.resolve()),
        "conflict_marker": payload,
        "operation_log_path": str(operation_log_path.resolve()),
        "operation": operation,
    }


def _trust_default_decision(policy: dict[str, Any]) -> str:
    decision = str(policy.get("default_decision", "review")).strip() or "review"
    if decision not in {"allow", "review", "block"}:
        raise ValueError(f"unsupported trust policy default_decision: {decision}")
    return decision


def _stronger_decision(left: str, right: str) -> str:
    order = {"allow": 0, "review": 1, "block": 2}
    return left if order[left] >= order[right] else right


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if not normalized:
        raise ValueError("missing timestamp")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


def _restore_section_plan(
    target_entries: dict[str, dict[str, Any]],
    current_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    write_actions: list[dict[str, Any]] = []
    delete_actions: list[dict[str, Any]] = []
    unchanged = 0

    for path in sorted(target_entries):
        target = target_entries[path]
        current = current_entries.get(path)
        if current is not None and _entries_match(current, target):
            unchanged += 1
            continue
        write_actions.append(
            {
                "path": path,
                "target": target,
                "current": current,
                "reason": "missing" if current is None else "content_mismatch",
            }
        )

    for path in sorted(set(current_entries) - set(target_entries)):
        delete_actions.append(
            {
                "path": path,
                "current": current_entries[path],
                "reason": "not_in_snapshot",
            }
        )

    return {
        "summary": {
            "write": len(write_actions),
            "delete": len(delete_actions),
            "unchanged": unchanged,
        },
        "actions": {
            "write": write_actions,
            "delete": delete_actions,
        },
    }


def _empty_restore_plan() -> dict[str, Any]:
    return {
        "summary": {"write": 0, "delete": 0, "unchanged": 0},
        "actions": {"write": [], "delete": []},
    }


def _merge_restore_plans(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": {
            "write": int((left.get("summary") or {}).get("write", 0)) + int((right.get("summary") or {}).get("write", 0)),
            "delete": int((left.get("summary") or {}).get("delete", 0)) + int((right.get("summary") or {}).get("delete", 0)),
            "unchanged": int((left.get("summary") or {}).get("unchanged", 0)) + int((right.get("summary") or {}).get("unchanged", 0)),
        },
        "actions": {
            "write": list((left.get("actions") or {}).get("write", [])) + list((right.get("actions") or {}).get("write", [])),
            "delete": list((left.get("actions") or {}).get("delete", [])) + list((right.get("actions") or {}).get("delete", [])),
        },
    }


def _entries_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        str(left.get("sha256") or "") == str(right.get("sha256") or "")
        and int(left.get("size_bytes", 0) or 0) == int(right.get("size_bytes", 0) or 0)
    )


def _file_entry(root: Path, path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    return {
        "path": _display_path(root, resolved),
        "size_bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }


def _display_path(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(resolved)


def _entry_map(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for entry in entries:
        entry_path = str(entry.get("path") or "").strip()
        if entry_path:
            mapped[entry_path] = dict(entry)
    return mapped


def _diff_entry_sets(
    base_entries: dict[str, dict[str, Any]],
    head_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    added_paths = sorted(set(head_entries) - set(base_entries))
    deleted_paths = sorted(set(base_entries) - set(head_entries))
    shared_paths = sorted(set(base_entries) & set(head_entries))

    modified: list[dict[str, Any]] = []
    unchanged = 0
    for path in shared_paths:
        base_entry = base_entries[path]
        head_entry = head_entries[path]
        if (
            str(base_entry.get("sha256")) == str(head_entry.get("sha256"))
            and int(base_entry.get("size_bytes", 0)) == int(head_entry.get("size_bytes", 0))
        ):
            unchanged += 1
            continue
        modified.append(
            {
                "path": path,
                "base": base_entry,
                "head": head_entry,
            }
        )

    summary = {
        "added": len(added_paths),
        "modified": len(modified),
        "deleted": len(deleted_paths),
        "unchanged": unchanged,
    }
    return {
        "summary": summary,
        "changes": {
            "added": [head_entries[path] for path in added_paths],
            "modified": modified,
            "deleted": [base_entries[path] for path in deleted_paths],
        },
    }


def _merge_diff_summaries(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {
        "added": int(left.get("added", 0)) + int(right.get("added", 0)),
        "modified": int(left.get("modified", 0)) + int(right.get("modified", 0)),
        "deleted": int(left.get("deleted", 0)) + int(right.get("deleted", 0)),
        "unchanged": int(left.get("unchanged", 0)) + int(right.get("unchanged", 0)),
    }


def _entries_digest(entries: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(str(entry["path"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(entry["sha256"]).encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(entry["size_bytes"]).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_archive(root: Path, paths: list[Path], archive_path: Path) -> None:
    with archive_path.open("wb") as raw_handle:
        with gzip.GzipFile(fileobj=raw_handle, mode="wb", mtime=0) as gzip_handle:
            with tarfile.open(fileobj=gzip_handle, mode="w") as tar_handle:
                for path in paths:
                    tar_handle.add(
                        path,
                        arcname=str(path.relative_to(root)),
                        filter=_normalize_tarinfo,
                    )


def _normalize_tarinfo(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    return info


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")


def _slug_token(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "_" for char in value).strip("_") or "entry"
