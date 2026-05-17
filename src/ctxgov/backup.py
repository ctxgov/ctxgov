from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
from typing import Any


PLAN_LEDGER_BACKUP_RECEIPT_SCHEMA_VERSION = "plan-ledger.backup-receipt/v1"
DEFAULT_MAX_AGE_HOURS = 24
DEFAULT_RECEIPT_MODE = "preflight"
DEFAULT_WORKSPACE_PATHS = (
    "README.md",
    "module.yaml",
    "pyproject.toml",
    "config",
    "docs",
    "fixtures",
    "schemas",
    "scripts",
    "src",
    "tests",
)


def emit_backup_bundle(
    *,
    root: Path,
    output_path: Path,
    receipt_format: str,
    scope_kind: str,
    scope_value: str,
    max_age_hours: int,
    restore_tested: bool,
    notes: str | None,
    plan_id: str | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    output_path = output_path.resolve()
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    checked_at_dt = datetime.now(timezone.utc)
    checked_at = _isoformat(checked_at_dt)
    timestamp_token = checked_at_dt.strftime("%Y%m%dT%H%M%SZ")
    archive_path = output_dir / f"ctxvault-backup-{timestamp_token}.tar.gz"
    manifest_path = output_dir / f"ctxvault-backup-{timestamp_token}.manifest.json"
    ctxvault_receipt_path = (
        output_path
        if receipt_format == "ctxvault"
        else output_dir / f"ctxvault-backup-{timestamp_token}.receipt.json"
    )

    excluded_prefixes = (output_dir,) if _is_relative_to(output_dir, root) else ()
    workspace_files = collect_workspace_files(root, excluded_prefixes=excluded_prefixes)
    if not workspace_files:
        raise ValueError("no workspace files available for backup receipt emission")

    _write_archive(root, workspace_files, archive_path)
    archive_sha256 = _sha256_file(archive_path)

    manifest_entries = [_manifest_entry(root, path) for path in workspace_files]
    manifest_sha256 = _manifest_sha256(manifest_entries)
    total_bytes = sum(int(entry["size_bytes"]) for entry in manifest_entries)
    manifest_payload = {
        "generated_at": checked_at,
        "workspace_root": str(root),
        "scope": {"kind": scope_kind, "value": scope_value},
        "archive": {
            "path": str(archive_path),
            "sha256": archive_sha256,
        },
        "summary": {
            "file_count": len(manifest_entries),
            "total_bytes": total_bytes,
            "manifest_sha256": manifest_sha256,
        },
        "files": manifest_entries,
    }
    _write_json(manifest_path, manifest_payload)

    artifact_refs = [
        archive_path.as_uri(),
        manifest_path.as_uri(),
        f"manifest://ctxvault/{manifest_sha256}",
        f"sha256://archive/{archive_sha256}",
    ]
    protected_refs = [path.as_uri() for path in workspace_files]
    ctxvault_receipt = {
        "id": f"backup_{timestamp_token.lower()}_ctxvault_preflight",
        "scope": {"kind": scope_kind, "value": scope_value},
        "checked_at": checked_at,
        "status": "ok",
        "mode": DEFAULT_RECEIPT_MODE,
        "protected_refs": protected_refs,
        "artifact_refs": artifact_refs,
        "recovery_point_at": checked_at,
        "restore_tested": restore_tested,
        "max_age_hours": max_age_hours,
        "notes": notes
        or (
            f"Deterministic preflight archive covering {len(manifest_entries)} "
            f"workspace file(s) and {total_bytes} byte(s)."
        ),
    }
    _write_json(ctxvault_receipt_path, ctxvault_receipt)

    receipt_payload: dict[str, Any]
    if receipt_format == "plan-ledger":
        if not plan_id:
            raise ValueError("plan_id is required when receipt_format is plan-ledger")
        if not target:
            raise ValueError("target is required when receipt_format is plan-ledger")
        receipt_payload = {
            "schema_version": PLAN_LEDGER_BACKUP_RECEIPT_SCHEMA_VERSION,
            "checked_at": checked_at,
            "plan_id": plan_id,
            "target": target,
            "path": str(output_path),
            "status": "fresh",
            "recoverable": True,
            "notes": (
                f"Deterministic workspace snapshot with archive {archive_path.name} "
                f"and manifest {manifest_path.name}."
            ),
        }
        _write_json(output_path, receipt_payload)
    elif receipt_format == "ctxvault":
        receipt_payload = ctxvault_receipt
    else:
        raise ValueError(f"unsupported receipt_format: {receipt_format}")

    return {
        "receipt_format": receipt_format,
        "receipt_path": str(output_path),
        "receipt": receipt_payload,
        "ctxvault_receipt_path": str(ctxvault_receipt_path),
        "ctxvault_receipt": ctxvault_receipt,
        "archive_path": str(archive_path),
        "archive_sha256": archive_sha256,
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha256,
        "file_count": len(manifest_entries),
        "total_bytes": total_bytes,
    }


def collect_workspace_files(root: Path, *, excluded_prefixes: tuple[Path, ...] = ()) -> list[Path]:
    prefixes = tuple(prefix.resolve() for prefix in excluded_prefixes)
    git_paths = _git_workspace_files(root)
    if git_paths:
        return _filter_workspace_files(git_paths, prefixes)
    fallback_paths = _fallback_workspace_files(root)
    return _filter_workspace_files(fallback_paths, prefixes)


def _git_workspace_files(root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    candidates = []
    for raw in completed.stdout.splitlines():
        if not raw.strip():
            continue
        candidate = (root / raw).resolve()
        if candidate.is_file():
            candidates.append(candidate)
    return candidates


def _fallback_workspace_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for raw in DEFAULT_WORKSPACE_PATHS:
        candidate = (root / raw).resolve()
        if candidate.is_file():
            candidates.append(candidate)
            continue
        if candidate.is_dir():
            candidates.extend(path.resolve() for path in sorted(candidate.rglob("*")) if path.is_file())
    return candidates


def _filter_workspace_files(paths: list[Path], prefixes: tuple[Path, ...]) -> list[Path]:
    unique: dict[str, Path] = {}
    for path in paths:
        resolved = path.resolve()
        if any(_is_relative_to(resolved, prefix) for prefix in prefixes):
            continue
        unique[str(resolved)] = resolved
    return sorted(unique.values(), key=lambda path: str(path))


def _manifest_entry(root: Path, path: Path) -> dict[str, Any]:
    relative_path = str(path.relative_to(root))
    return {
        "path": relative_path,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _manifest_sha256(entries: list[dict[str, Any]]) -> str:
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


def _write_archive(root: Path, workspace_files: list[Path], archive_path: Path) -> None:
    with archive_path.open("wb") as raw_handle:
        with gzip.GzipFile(fileobj=raw_handle, mode="wb", mtime=0) as gzip_handle:
            with tarfile.open(fileobj=gzip_handle, mode="w") as tar_handle:
                for path in workspace_files:
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _isoformat(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False
