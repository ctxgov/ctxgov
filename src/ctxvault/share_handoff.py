from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .privacy import scan_privacy_files, scan_privacy_text


SHARE_HANDOFF_SCHEMA_VERSION = 1
_QUEUE_DIRNAME = "ctxvault-share-handoff"
_INBOX_DIRNAME = "inbox"
_ARCHIVE_DIRNAME = "archive"
_ALLOWED_STATUS = {"pending", "consumed", "rejected", "archived"}


def stage_share_handoff(
    *,
    shared_root: Path,
    title: str | None = None,
    text: str | None = None,
    urls: list[str] | None = None,
    attachment_paths: list[str | Path] | None = None,
    source_app: str = "ctxvault",
    source_surface: str = "ios",
    source_format: str = "share_extension_payload",
    capture_method: str = "share_extension",
    imported_via: str = "ctxvault_share_extension",
    notes: str | None = None,
    metadata: dict[str, Any] | None = None,
    handoff_id: str | None = None,
) -> dict[str, Any]:
    normalized_title = str(title or "").strip() or None
    normalized_text = str(text or "").strip() or None
    normalized_urls = _unique_strings(urls or [])
    attachment_entries = _normalize_attachment_entries(shared_root=shared_root, attachment_paths=attachment_paths or [])
    if not normalized_text and not normalized_urls and not attachment_entries:
        raise ValueError("share handoff requires text, urls, or attachment_paths")

    queue_dir = _inbox_dir(shared_root)
    queue_dir.mkdir(parents=True, exist_ok=True)
    effective_handoff_id = handoff_id or _generated_handoff_id()
    created_at = _now_iso()
    payload = {
        "schema_version": SHARE_HANDOFF_SCHEMA_VERSION,
        "handoff_id": effective_handoff_id,
        "status": "pending",
        "created_at": created_at,
        "title": normalized_title,
        "text": normalized_text,
        "urls": normalized_urls,
        "attachments": attachment_entries,
        "source_app": str(source_app).strip() or "ctxvault",
        "source_surface": str(source_surface).strip() or "ios",
        "source_format": str(source_format).strip() or "share_extension_payload",
        "capture_method": str(capture_method).strip() or "share_extension",
        "imported_via": str(imported_via).strip() or "ctxvault_share_extension",
        "notes": str(notes or "").strip() or None,
        "metadata": dict(metadata or {}),
    }
    handoff_path = queue_dir / f"{effective_handoff_id}.json"
    _write_json(handoff_path, payload)
    return {
        "handoff_path": str(handoff_path.resolve()),
        "handoff": _handoff_card({**payload, "handoff_path": str(handoff_path.resolve())}),
        "queue_dir": str(queue_dir.resolve()),
    }


def list_share_handoffs(
    *,
    shared_root: Path,
    limit: int = 50,
    include_archived: bool = False,
) -> dict[str, Any]:
    pending = _load_handoffs_from_dir(_inbox_dir(shared_root))
    archived = _load_handoffs_from_dir(_archive_dir(shared_root)) if include_archived else []
    handoffs = [*pending, *archived]
    handoffs.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("handoff_id") or ""),
        ),
        reverse=True,
    )
    returned = handoffs[:limit]
    return {
        "schema_version": SHARE_HANDOFF_SCHEMA_VERSION,
        "shared_root": str(shared_root.resolve()),
        "summary": {
            "handoff_count": len(handoffs),
            "returned_count": len(returned),
            "pending_count": len(pending),
            "archived_count": len(archived),
        },
        "items": [_handoff_card(item) for item in returned],
    }


def preview_share_handoff(
    *,
    shared_root: Path,
    handoff_path: Path,
    max_findings: int = 25,
    max_bytes: int = 262_144,
) -> dict[str, Any]:
    resolved_path = handoff_path.resolve()
    payload = _load_handoff(resolved_path)
    attachment_paths = _resolved_attachment_paths(shared_root=shared_root, payload=payload)
    text = str(payload.get("text") or "").strip()
    text_preflight = (
        scan_privacy_text(text, source="share_handoff_text", max_findings=max_findings).to_dict()
        if text
        else None
    )
    attachment_preflight = (
        scan_privacy_files(attachment_paths, source="share_handoff_attachment", max_findings=max_findings, max_bytes=max_bytes)
        if attachment_paths
        else None
    )
    decision = _max_decision(
        [
            "allow",
            None if text_preflight is None else str(text_preflight.get("decision") or "allow"),
            None if attachment_preflight is None else str(attachment_preflight.get("decision") or "allow"),
        ]
    )
    highest_severity = _max_severity(
        [
            "none",
            None if text_preflight is None else str(text_preflight.get("highest_severity") or "none"),
            None if attachment_preflight is None else str(attachment_preflight.get("highest_severity") or "none"),
        ]
    )
    return {
        "schema_version": SHARE_HANDOFF_SCHEMA_VERSION,
        "handoff": _handoff_card(payload),
        "resolved_attachment_paths": [str(path) for path in attachment_paths],
        "decision": decision,
        "highest_severity": highest_severity,
        "capture_defaults": compose_share_handoff_capture(
            shared_root=shared_root,
            handoff_path=resolved_path,
        ),
        "text_preflight": text_preflight,
        "attachment_preflight": attachment_preflight,
    }


def mark_share_handoff_consumed(
    *,
    shared_root: Path,
    handoff_path: Path,
    preview_decision: str,
    claim_ref: str,
    candidate_ref: str,
    consumed_by: str | None = None,
    consumption_notes: str | None = None,
) -> dict[str, Any]:
    payload = _load_handoff(handoff_path.resolve())
    if str(payload.get("status") or "pending").strip() != "pending":
        raise ValueError("share handoff is not pending")
    consumed_at = _now_iso()
    updated = {
        **payload,
        "status": "consumed",
        "consumed_at": consumed_at,
        "preview_decision": preview_decision,
        "claim_ref": claim_ref,
        "candidate_ref": candidate_ref,
        "consumed_by": str(consumed_by or "").strip() or None,
        "consumption_notes": str(consumption_notes or "").strip() or None,
    }
    archive_dir = _archive_dir(shared_root)
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived_path = archive_dir / handoff_path.name
    _write_json(archived_path, updated)
    if handoff_path.resolve() != archived_path.resolve() and handoff_path.exists():
        handoff_path.unlink()
    return {
        "handoff_path": str(archived_path.resolve()),
        "handoff": _handoff_card({**updated, "handoff_path": str(archived_path.resolve())}),
    }


def compose_share_handoff_capture(
    *,
    shared_root: Path,
    handoff_path: Path,
) -> dict[str, Any]:
    payload = _load_handoff(handoff_path.resolve())
    urls = _unique_strings(payload.get("urls") or [])
    text = str(payload.get("text") or "").strip() or None
    statement = _statement_from_payload(payload)
    return {
        "statement": statement,
        "capture_text": text,
        "source_refs": [f"share-handoff://{payload['handoff_id']}", *urls],
        "notes": _capture_notes_for_payload(shared_root=shared_root, payload=payload),
        "source_app": str(payload.get("source_app") or "ctxvault").strip() or "ctxvault",
        "source_surface": str(payload.get("source_surface") or "ios").strip() or "ios",
        "source_format": str(payload.get("source_format") or "share_extension_payload").strip() or "share_extension_payload",
        "capture_method": str(payload.get("capture_method") or "share_extension").strip() or "share_extension",
        "imported_via": str(payload.get("imported_via") or "ctxvault_share_extension").strip() or "ctxvault_share_extension",
    }


def _handoff_card(payload: dict[str, Any]) -> dict[str, Any]:
    attachments = list(payload.get("attachments") or [])
    urls = list(payload.get("urls") or [])
    status = str(payload.get("status") or "pending").strip() or "pending"
    return {
        "handoff_id": str(payload.get("handoff_id") or "").strip(),
        "handoff_path": str(payload.get("handoff_path") or "").strip() or None,
        "status": status,
        "created_at": payload.get("created_at"),
        "consumed_at": payload.get("consumed_at"),
        "title": str(payload.get("title") or "").strip() or None,
        "text_preview": _preview_text(str(payload.get("text") or "").strip()),
        "url_count": len(urls),
        "attachment_count": len(attachments),
        "source_app": str(payload.get("source_app") or "").strip() or None,
        "source_surface": str(payload.get("source_surface") or "").strip() or None,
        "source_format": str(payload.get("source_format") or "").strip() or None,
        "capture_method": str(payload.get("capture_method") or "").strip() or None,
        "imported_via": str(payload.get("imported_via") or "").strip() or None,
        "claim_ref": str(payload.get("claim_ref") or "").strip() or None,
        "candidate_ref": str(payload.get("candidate_ref") or "").strip() or None,
        "consumed_by": str(payload.get("consumed_by") or "").strip() or None,
        "actions": ["preview", "consume"] if status == "pending" else [],
    }


def _capture_notes_for_payload(*, shared_root: Path, payload: dict[str, Any]) -> str | None:
    lines = []
    title = str(payload.get("title") or "").strip()
    if title:
        lines.append(f"share_title={title}")
    notes = str(payload.get("notes") or "").strip()
    if notes:
        lines.append(notes)
    for attachment in list(payload.get("attachments") or []):
        filename = str(attachment.get("filename") or "").strip() or "attachment"
        resolved_path = _resolved_attachment_path(shared_root=shared_root, entry=attachment)
        lines.append(f"attachment={filename} path={resolved_path}")
    return "\n".join(lines) if lines else None


def _statement_from_payload(payload: dict[str, Any]) -> str:
    title = str(payload.get("title") or "").strip()
    if title:
        return title
    text = str(payload.get("text") or "").strip()
    if text:
        return _preview_text(text, max_chars=140)
    urls = [str(item).strip() for item in list(payload.get("urls") or []) if str(item).strip()]
    if urls:
        return f"Shared link: {urls[0]}"
    attachments = list(payload.get("attachments") or [])
    if attachments:
        filename = str(attachments[0].get("filename") or attachments[0].get("path") or "attachment").strip()
        return f"Shared attachment: {filename}"
    raise ValueError("share handoff did not contain any capturable material")


def _normalize_attachment_entries(*, shared_root: Path, attachment_paths: list[str | Path]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw_path in attachment_paths:
        raw_text = str(raw_path).strip()
        if not raw_text:
            continue
        path = Path(raw_text).expanduser()
        resolved_path = path.resolve() if path.is_absolute() else (shared_root / path).resolve()
        exists = resolved_path.exists()
        size_bytes = resolved_path.stat().st_size if exists and resolved_path.is_file() else None
        entries.append(
            {
                "path": raw_text,
                "path_kind": "absolute" if path.is_absolute() else "shared_root_relative",
                "filename": resolved_path.name or path.name,
                "exists": exists,
                "size_bytes": size_bytes,
            }
        )
    return entries


def _resolved_attachment_paths(*, shared_root: Path, payload: dict[str, Any]) -> list[Path]:
    return [_resolved_attachment_path(shared_root=shared_root, entry=entry) for entry in list(payload.get("attachments") or [])]


def _resolved_attachment_path(*, shared_root: Path, entry: dict[str, Any]) -> Path:
    raw_path = str(entry.get("path") or "").strip()
    path = Path(raw_path).expanduser()
    return path.resolve() if path.is_absolute() else (shared_root / path).resolve()


def _load_handoff(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid share handoff payload at {path}")
    if int(payload.get("schema_version") or 0) != SHARE_HANDOFF_SCHEMA_VERSION:
        raise ValueError(f"unsupported share handoff schema_version at {path}")
    status = str(payload.get("status") or "pending").strip() or "pending"
    if status not in _ALLOWED_STATUS:
        raise ValueError(f"unsupported share handoff status at {path}: {status}")
    payload["handoff_path"] = str(path.resolve())
    payload["status"] = status
    return payload


def _load_handoffs_from_dir(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    for handoff_path in sorted(path.glob("*.json")):
        items.append(_load_handoff(handoff_path))
    return items


def _queue_root(shared_root: Path) -> Path:
    return shared_root.resolve() / _QUEUE_DIRNAME


def _inbox_dir(shared_root: Path) -> Path:
    return _queue_root(shared_root) / _INBOX_DIRNAME


def _archive_dir(shared_root: Path) -> Path:
    return _queue_root(shared_root) / _ARCHIVE_DIRNAME


def _generated_handoff_id() -> str:
    token = datetime.now(timezone.utc).strftime("%Y%m%dt%H%M%Sz").lower()
    return f"share_{token}_{uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _preview_text(text: str, *, max_chars: int = 120) -> str | None:
    normalized = " ".join(str(text or "").split())
    if not normalized:
        return None
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return normalized[:max_chars]
    return normalized[: max_chars - 3].rstrip() + "..."


def _max_decision(values: list[str | None]) -> str:
    normalized = [value for value in values if value]
    return max(normalized, key=lambda item: {"allow": 0, "redact": 1, "review": 2, "block": 3}.get(item, 0))


def _max_severity(values: list[str | None]) -> str:
    normalized = [value for value in values if value]
    return max(normalized, key=lambda item: {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}.get(item, 0))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    serializable = {key: value for key, value in payload.items() if key != "handoff_path"}
    path.write_text(json.dumps(serializable, indent=2, sort_keys=True) + "\n", encoding="utf-8")
