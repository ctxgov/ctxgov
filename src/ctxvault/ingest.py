from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable
import zipfile

from .core import CtxVault


SOURCE_CONNECTOR_RECEIPT_SCHEMA_VERSION = "ctxvault.source-connector-receipt/v1"
SUPPORTED_KNOWLEDGE_EXTENSIONS = {".json", ".md", ".txt"}
CONVERSATION_EXPORT_FILE_NAMES = {"conversations.json", "conversation.json", "messages.json"}
SKIP_DIR_NAMES = {".ctxvault", ".git", "__pycache__", "raw"}
SKIP_FILE_NAMES = {"search-meta.json"}


@dataclass(frozen=True)
class ImportReceipt:
    source_path: Path
    object_id: str
    model_name: str
    object_kind: str

    def to_dict(self) -> dict[str, str]:
        return {
            "source_path": str(self.source_path),
            "object_id": self.object_id,
            "model_name": self.model_name,
            "object_kind": self.object_kind,
        }


@dataclass(frozen=True)
class SourceConnectorReceipt:
    receipt_id: str
    connector_id: str
    source_app: str
    source_surface: str
    source_format: str
    capture_method: str
    imported_via: str
    source_ref: str
    imported_at: str
    scope: dict[str, str]
    object_refs: tuple[str, ...]
    turn_count: int
    normalization: dict[str, Any]
    warnings: tuple[str, ...]
    review_state: str = "not_required"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": SOURCE_CONNECTOR_RECEIPT_SCHEMA_VERSION,
            "receipt_id": self.receipt_id,
            "connector_id": self.connector_id,
            "source_app": self.source_app,
            "source_surface": self.source_surface,
            "source_format": self.source_format,
            "capture_method": self.capture_method,
            "imported_via": self.imported_via,
            "source_ref": self.source_ref,
            "imported_at": self.imported_at,
            "scope": dict(self.scope),
            "object_refs": list(self.object_refs),
            "turn_count": self.turn_count,
            "normalization": dict(self.normalization),
            "warnings": list(self.warnings),
            "review_state": self.review_state,
        }


@dataclass(frozen=True)
class TranscriptImportReceipt:
    session: ImportReceipt
    turns: tuple[ImportReceipt, ...]
    source_connector: SourceConnectorReceipt

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session.to_dict(),
            "turns": [turn.to_dict() for turn in self.turns],
            "source_connector_receipt": self.source_connector.to_dict(),
        }


def import_conversation_path(
    vault: CtxVault,
    source_path: Path,
    *,
    scope_kind: str,
    scope_value: str,
    session_id: str | None = None,
    title: str | None = None,
    task_label: str | None = None,
    client: str = "local_import",
    imported_via: str = "ctxvault_import",
) -> list[TranscriptImportReceipt]:
    requested_source_path = source_path.resolve()
    path, payload = _load_conversation_source(requested_source_path)
    transcripts = _conversation_payloads_from_source(path, payload, client=client)
    if not transcripts:
        raise ValueError("conversation payload did not contain any importable conversations")
    if len(transcripts) > 1 and any(value is not None for value in (session_id, title, task_label)):
        raise ValueError("session_id, title, and task_label overrides require a single conversation payload")

    return [
        _store_transcript_payload(
            vault,
            path,
            transcript_payload,
            scope_kind=scope_kind,
            scope_value=scope_value,
            session_id=session_id,
            title=title,
            task_label=task_label,
            requested_source_path=requested_source_path,
            client=client,
            imported_via=imported_via,
        )
        for transcript_payload in transcripts
    ]


def import_knowledge_path(
    vault: CtxVault,
    source_path: Path,
    *,
    scope_kind: str,
    scope_value: str,
    recursive: bool = False,
    kind: str | None = None,
    title: str | None = None,
) -> list[ImportReceipt]:
    resolved = source_path.resolve()
    sources = [resolved] if resolved.is_file() else list(_iter_knowledge_sources(resolved, recursive=recursive))
    receipts: list[ImportReceipt] = []
    for path in sources:
        payload = build_knowledge_payload(
            path,
            scope_kind=scope_kind,
            scope_value=scope_value,
            kind=kind,
            title=title,
        )
        envelope = vault.store_core_object("KnowledgeArtifact", payload)
        receipts.append(
            ImportReceipt(
                source_path=path,
                object_id=envelope.object_id,
                model_name="KnowledgeArtifact",
                object_kind=envelope.object_kind,
            )
        )
    return receipts


def import_prompt_path(
    vault: CtxVault,
    source_path: Path,
    *,
    scope_kind: str,
    scope_value: str,
    prompt_id: str | None = None,
    name: str | None = None,
    intent: str = "general",
    owner: str = "local_import",
    required_context_types: Iterable[str] = (),
) -> ImportReceipt:
    path = source_path.resolve()
    payload = build_prompt_payload(
        path,
        scope_kind=scope_kind,
        scope_value=scope_value,
        prompt_id=prompt_id,
        name=name,
        intent=intent,
        owner=owner,
        required_context_types=list(required_context_types),
    )
    envelope = vault.store_core_object("PromptAsset", payload)
    return ImportReceipt(
        source_path=path,
        object_id=envelope.object_id,
        model_name="PromptAsset",
        object_kind=envelope.object_kind,
    )


def import_transcript_path(
    vault: CtxVault,
    source_path: Path,
    *,
    scope_kind: str,
    scope_value: str,
    session_id: str | None = None,
    title: str | None = None,
    task_label: str | None = None,
    client: str = "local_import",
    imported_via: str = "ctxvault_import",
) -> TranscriptImportReceipt:
    requested_source_path = source_path.resolve()
    path, payload = _load_conversation_source(requested_source_path)
    if not isinstance(payload, dict):
        raise ValueError("transcript payload must be a JSON object")
    return _store_transcript_payload(
        vault,
        path,
        payload,
        scope_kind=scope_kind,
        scope_value=scope_value,
        session_id=session_id,
        title=title,
        task_label=task_label,
        requested_source_path=requested_source_path,
        client=client,
        imported_via=imported_via,
    )


def _load_conversation_source(source_path: Path) -> tuple[Path, Any]:
    path = source_path.resolve()
    if path.is_dir():
        payload_path = _find_conversation_payload_path(path)
        return payload_path, json.loads(payload_path.read_text(encoding="utf-8"))
    if path.suffix.lower() == ".zip":
        return path, _load_conversation_payload_from_zip(path)
    return path, json.loads(path.read_text(encoding="utf-8"))


def _find_conversation_payload_path(root: Path) -> Path:
    if not root.exists():
        raise FileNotFoundError(root)

    candidates = [
        path
        for path in sorted(root.rglob("*.json"))
        if path.is_file() and not _should_skip_archive_member(path.relative_to(root).parts)
    ]
    recognized = [path for path in candidates if path.name.lower() in CONVERSATION_EXPORT_FILE_NAMES]
    if recognized:
        return _best_conversation_payload_path(root, recognized)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"conversation directory {root} did not contain any JSON files")
    raise ValueError(
        f"conversation directory {root} contained multiple JSON files; expected one of {sorted(CONVERSATION_EXPORT_FILE_NAMES)}"
    )


def _best_conversation_payload_path(root: Path, candidates: list[Path]) -> Path:
    return min(candidates, key=lambda path: (len(path.relative_to(root).parts), str(path.relative_to(root))))


def _load_conversation_payload_from_zip(path: Path) -> Any:
    try:
        with zipfile.ZipFile(path) as archive:
            member_name = _select_conversation_archive_member(archive.namelist())
            with archive.open(member_name) as handle:
                return json.loads(handle.read().decode("utf-8-sig"))
    except zipfile.BadZipFile as exc:
        raise ValueError(f"conversation archive {path} is not a valid zip file") from exc


def _select_conversation_archive_member(member_names: Iterable[str]) -> str:
    candidates = [
        name
        for name in sorted(member_names)
        if name.lower().endswith(".json")
        and not name.endswith("/")
        and not _should_skip_archive_member(Path(name).parts)
    ]
    recognized = [name for name in candidates if Path(name).name.lower() in CONVERSATION_EXPORT_FILE_NAMES]
    if recognized:
        return _best_archive_member_name(recognized)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError("conversation archive did not contain any JSON files")
    raise ValueError(
        f"conversation archive contained multiple JSON files; expected one of {sorted(CONVERSATION_EXPORT_FILE_NAMES)}"
    )


def _best_archive_member_name(candidates: list[str]) -> str:
    return min(candidates, key=lambda name: (len(Path(name).parts), name))


def _should_skip_archive_member(parts: Iterable[str]) -> bool:
    normalized = tuple(parts)
    return "__MACOSX" in normalized or any(part.startswith("._") for part in normalized)


def _store_transcript_payload(
    vault: CtxVault,
    source_path: Path,
    payload: dict[str, Any],
    *,
    scope_kind: str,
    scope_value: str,
    session_id: str | None = None,
    title: str | None = None,
    task_label: str | None = None,
    requested_source_path: Path | None = None,
    client: str = "local_import",
    imported_via: str = "ctxvault_import",
) -> TranscriptImportReceipt:
    turns_payload = payload.get("turns")
    if not isinstance(turns_payload, list) or not turns_payload:
        raise ValueError("transcript payload must include a non-empty turns array")

    started_at = _timestamp_from_value(payload.get("started_at")) or _timestamp_from_path(source_path)
    session_object_id = session_id or _string_value(payload.get("id")) or _stable_id("sess", source_path)
    session_title = title or _string_value(payload.get("title")) or _headline_title(source_path) or _humanize_slug(source_path.stem)
    resolved_task_label = task_label or _string_value(payload.get("task_label")) or session_title
    effective_source_path = requested_source_path or source_path
    session_client = _string_value(payload.get("client")) or client
    session_source_app = _string_value(payload.get("source_app")) or _default_source_app(session_client, "unknown")
    session_source_surface = _string_value(payload.get("source_surface")) or "local"
    session_source_format = _string_value(payload.get("source_format")) or "normalized_transcript"
    session_capture_method = _string_value(payload.get("capture_method")) or _capture_method_from_source_path(
        effective_source_path
    )
    session_imported_via = _string_value(payload.get("imported_via")) or imported_via
    session_payload = {
        "id": session_object_id,
        "client": session_client,
        "source_app": session_source_app,
        "source_surface": session_source_surface,
        "source_format": session_source_format,
        "capture_method": session_capture_method,
        "imported_via": session_imported_via,
        "scope": {"kind": scope_kind, "value": scope_value},
        "title": session_title,
        "started_at": started_at,
        "ended_at": _timestamp_from_value(payload.get("ended_at")),
        "status": _string_value(payload.get("status")) or "active",
        "task_label": resolved_task_label,
        "turn_count": len(turns_payload),
        "active_prompt_ids": _string_list(payload.get("active_prompt_ids")),
        "bundle_ids": _string_list(payload.get("bundle_ids")),
        "derived_asset_refs": _string_list(payload.get("derived_asset_refs")),
        "signal_summary": {
            "user_corrections": 0,
            "accepted_outputs": 0,
            "tool_success_rate": 1.0,
            "followup_count": max(0, len(turns_payload) - 1),
        },
        "sensitivity": _string_value(payload.get("sensitivity")) or "internal",
        "redaction_state": _string_value(payload.get("redaction_state")) or "none",
        "secret_refs": _string_list(payload.get("secret_refs")),
        "exportable": bool(payload.get("exportable", True)),
    }
    session_envelope = vault.store_core_object("Session", session_payload)

    turn_receipts: list[ImportReceipt] = []
    for index, item in enumerate(turns_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError("each transcript turn must be an object")
        content = _string_value(item.get("content")) or _string_value(item.get("text"))
        if not content:
            raise ValueError(f"transcript turn {index} must include content")
        turn_id = _string_value(item.get("id")) or f"{session_object_id}_turn_{index:04d}"
        turn_payload = {
            "id": turn_id,
            "session_id": session_object_id,
            "source_app": _string_value(item.get("source_app")) or session_source_app,
            "source_surface": _string_value(item.get("source_surface")) or session_source_surface,
            "source_format": _string_value(item.get("source_format")) or session_source_format,
            "capture_method": _string_value(item.get("capture_method")) or session_capture_method,
            "imported_via": _string_value(item.get("imported_via")) or session_imported_via,
            "scope": {"kind": scope_kind, "value": scope_value},
            "role": _string_value(item.get("role")) or _string_value(item.get("speaker")) or "unknown",
            "content": content,
            "ordinal": index,
            "status": _string_value(item.get("status")) or "recorded",
            "created_at": _timestamp_from_value(item.get("created_at")) or started_at,
            "source_refs": [f"file://{source_path}"],
            "sensitivity": _string_value(item.get("sensitivity")) or session_payload["sensitivity"],
            "redaction_state": _string_value(item.get("redaction_state")) or session_payload["redaction_state"],
            "secret_refs": _string_list(item.get("secret_refs")),
            "exportable": bool(item.get("exportable", session_payload["exportable"])),
        }
        turn_envelope = vault.store_core_object("Turn", turn_payload)
        turn_receipts.append(
            ImportReceipt(
                source_path=source_path,
                object_id=turn_envelope.object_id,
                model_name="Turn",
                object_kind=turn_envelope.object_kind,
            )
        )

    session_receipt = ImportReceipt(
        source_path=source_path,
        object_id=session_envelope.object_id,
        model_name="Session",
        object_kind=session_envelope.object_kind,
    )
    source_connector = _build_source_connector_receipt(
        source_path=source_path,
        session_payload=session_payload,
        session_ref=f"session://{session_envelope.object_id}",
        turn_refs=tuple(f"turn://{receipt.object_id}" for receipt in turn_receipts),
    )

    return TranscriptImportReceipt(
        session=session_receipt,
        turns=tuple(turn_receipts),
        source_connector=source_connector,
    )


def _conversation_payloads_from_source(path: Path, payload: Any, *, client: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [_normalized_conversation_payload(path, payload, client=client)]

    if isinstance(payload, list):
        conversations: list[dict[str, Any]] = []
        for index, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"conversation entry {index} must be an object")
            normalized = _normalized_conversation_payload(
                path,
                item,
                client=client,
                ordinal=index,
                skip_empty=True,
            )
            if normalized is not None:
                conversations.append(normalized)
        return conversations

    raise ValueError("conversation payload must be a JSON object or array")


def _normalized_conversation_payload(
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None = None,
    skip_empty: bool = False,
) -> dict[str, Any] | None:
    if _is_normalized_transcript(payload):
        return payload

    if isinstance(payload.get("chat_messages"), list):
        if skip_empty and not payload["chat_messages"]:
            return None
        return _normalize_export_conversation(
            _normalize_claude_conversation,
            path,
            payload,
            client=client,
            ordinal=ordinal,
            skip_empty=skip_empty,
        )

    if isinstance(payload.get("mapping"), dict):
        return _normalize_export_conversation(
            _normalize_chatgpt_conversation,
            path,
            payload,
            client=client,
            ordinal=ordinal,
            skip_empty=skip_empty,
        )

    if _is_deepseek_messages_export(path, payload, client):
        return _normalize_export_conversation(
            _normalize_deepseek_conversation,
            path,
            payload,
            client=client,
            ordinal=ordinal,
            skip_empty=skip_empty,
        )

    if _is_ollama_ui_messages_export(path, payload, client):
        return _normalize_export_conversation(
            _normalize_ollama_ui_conversation,
            path,
            payload,
            client=client,
            ordinal=ordinal,
            skip_empty=skip_empty,
        )

    if isinstance(payload.get("messages"), list):
        if skip_empty and not payload["messages"]:
            return None
        return _normalize_export_conversation(
            _normalize_gemini_conversation,
            path,
            payload,
            client=client,
            ordinal=ordinal,
            skip_empty=skip_empty,
        )

    message = "unsupported conversation payload shape" if ordinal is None else f"conversation entry {ordinal} uses an unsupported payload shape"
    raise ValueError(message)


def _normalize_export_conversation(
    normalizer: Any,
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None,
    skip_empty: bool,
) -> dict[str, Any] | None:
    try:
        return normalizer(path, payload, client=client, ordinal=ordinal)
    except ValueError as exc:
        if skip_empty and _is_empty_conversation_error(str(exc)):
            return None
        raise


def _is_empty_conversation_error(message: str) -> bool:
    return "did not contain any importable messages" in message


def _normalize_chatgpt_conversation(
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None = None,
) -> dict[str, Any]:
    title = _string_value(payload.get("title")) or _humanize_slug(path.stem)
    session_object_id = _string_value(payload.get("conversation_id")) or _string_value(payload.get("id")) or _stable_child_id(path, "chatgpt", ordinal)
    turns = []
    for index, message in enumerate(_chatgpt_branch_messages(payload.get("mapping")), start=1):
        content = _chatgpt_content_text(message.get("content"))
        if not content:
            continue
        turns.append(
            {
                "id": _string_value(message.get("id")) or f"{session_object_id}_turn_{index:04d}",
                "role": _normalize_role(_deep_string(message, "author", "role") or "unknown"),
                "content": content,
                "status": "recorded",
                "created_at": _timestamp_from_value(message.get("create_time")),
            }
        )
    if not turns:
        raise ValueError("chatgpt export did not contain any importable messages")
    return {
        "id": session_object_id,
        "client": _resolved_client_name(client, "chatgpt_export"),
        "source_app": _default_source_app(client, "chatgpt"),
        "source_surface": "export",
        "source_format": "chatgpt_export",
        "title": title,
        "started_at": _timestamp_from_value(payload.get("create_time")) or turns[0].get("created_at") or _timestamp_from_path(path),
        "ended_at": _timestamp_from_value(payload.get("update_time")) or turns[-1].get("created_at"),
        "status": "active",
        "task_label": title,
        "turns": turns,
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
    }


def _normalize_claude_conversation(
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None = None,
) -> dict[str, Any]:
    messages = payload.get("chat_messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("claude export must include a non-empty chat_messages array")
    title = _string_value(payload.get("name")) or _humanize_slug(path.stem)
    session_object_id = _string_value(payload.get("uuid")) or _stable_child_id(path, "claude", ordinal)
    turns = []
    for index, item in enumerate(messages, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"claude message {index} must be an object")
        content = _string_value(item.get("text")) or _rich_text_to_string(item.get("content"))
        if not content:
            continue
        turns.append(
            {
                "id": _string_value(item.get("uuid")) or f"{session_object_id}_turn_{index:04d}",
                "role": _normalize_role(_string_value(item.get("sender")) or "unknown"),
                "content": content,
                "status": "recorded",
                "created_at": _timestamp_from_value(item.get("created_at")) or _timestamp_from_value(item.get("updated_at")),
            }
        )
    if not turns:
        raise ValueError("claude export did not contain any importable messages")
    return {
        "id": session_object_id,
        "client": _resolved_client_name(client, "claude_export"),
        "source_app": _default_source_app(client, "claude"),
        "source_surface": "export",
        "source_format": "claude_export",
        "title": title,
        "started_at": _timestamp_from_value(payload.get("created_at")) or turns[0].get("created_at") or _timestamp_from_path(path),
        "ended_at": _timestamp_from_value(payload.get("updated_at")) or turns[-1].get("created_at"),
        "status": "active",
        "task_label": title,
        "turns": turns,
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
    }


def _normalize_deepseek_conversation(
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None = None,
) -> dict[str, Any]:
    messages = _source_hinted_messages(payload)
    if not messages:
        raise ValueError("deepseek export did not contain any importable messages")
    session_object_id = (
        _string_value(payload.get("conversation_id"))
        or _string_value(payload.get("chat_id"))
        or _string_value(payload.get("id"))
        or _stable_child_id(path, "deepseek", ordinal)
    )
    title = _conversation_title(payload, path)
    turns = _normalize_role_content_turns(messages, session_object_id=session_object_id, source_name="deepseek")
    if not turns:
        raise ValueError("deepseek export did not contain any importable messages")
    return {
        "id": session_object_id,
        "client": _resolved_client_name(client, "deepseek_export"),
        "source_app": "deepseek",
        "source_surface": _string_value(payload.get("source_surface")) or "export",
        "source_format": "deepseek_messages_export",
        "capture_method": "file_import",
        "title": title,
        "started_at": _first_timestamp(payload, ["created_at", "create_time", "start_time"]) or turns[0].get("created_at") or _timestamp_from_path(path),
        "ended_at": _first_timestamp(payload, ["updated_at", "update_time", "end_time"]) or turns[-1].get("created_at"),
        "status": "active",
        "task_label": title,
        "turns": turns,
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
    }


def _normalize_ollama_ui_conversation(
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None = None,
) -> dict[str, Any]:
    messages = _source_hinted_messages(payload)
    if not messages:
        raise ValueError("ollama ui export did not contain any importable messages")
    session_object_id = (
        _string_value(payload.get("conversation_id"))
        or _string_value(payload.get("chat_id"))
        or _string_value(payload.get("id"))
        or _stable_child_id(path, "ollama", ordinal)
    )
    title = _conversation_title(payload, path)
    turns = _normalize_role_content_turns(messages, session_object_id=session_object_id, source_name="ollama")
    if not turns:
        raise ValueError("ollama ui export did not contain any importable messages")
    return {
        "id": session_object_id,
        "client": _resolved_client_name(client, "ollama_ui_export"),
        "source_app": "ollama",
        "source_surface": _string_value(payload.get("source_surface")) or "local_ui_export",
        "source_format": "ollama_ui_messages_export",
        "capture_method": "file_import",
        "title": title,
        "started_at": _first_timestamp(payload, ["created_at", "create_time", "start_time"]) or turns[0].get("created_at") or _timestamp_from_path(path),
        "ended_at": _first_timestamp(payload, ["updated_at", "update_time", "end_time"]) or turns[-1].get("created_at"),
        "status": "active",
        "task_label": title,
        "turns": turns,
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
    }


def _normalize_gemini_conversation(
    path: Path,
    payload: dict[str, Any],
    *,
    client: str,
    ordinal: int | None = None,
) -> dict[str, Any]:
    messages = payload.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages payload must include a non-empty messages array")
    session_object_id = _string_value(payload.get("sessionId")) or _string_value(payload.get("id")) or _stable_child_id(path, "gemini", ordinal)
    title = _string_value(payload.get("title")) or _string_value(payload.get("projectHash")) or _humanize_slug(path.stem)
    turns = []
    for index, item in enumerate(messages, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"message {index} must be an object")
        content = _string_value(item.get("content")) or _rich_text_to_string(item.get("content"))
        if not content:
            continue
        turns.append(
            {
                "id": _string_value(item.get("id")) or f"{session_object_id}_turn_{index:04d}",
                "role": _normalize_role(_string_value(item.get("type")) or "unknown"),
                "content": content,
                "status": "recorded",
                "created_at": _timestamp_from_value(item.get("timestamp")),
            }
        )
    if not turns:
        raise ValueError("messages payload did not contain any importable messages")
    return {
        "id": session_object_id,
        "client": _resolved_client_name(client, "gemini_session"),
        "source_app": _default_source_app(client, "gemini"),
        "source_surface": "export",
        "source_format": "gemini_export",
        "title": title,
        "started_at": _timestamp_from_value(payload.get("startTime")) or turns[0].get("created_at") or _timestamp_from_path(path),
        "ended_at": _timestamp_from_value(payload.get("lastUpdated")) or turns[-1].get("created_at"),
        "status": "active",
        "task_label": title,
        "turns": turns,
        "sensitivity": "internal",
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
    }


def build_knowledge_payload(
    source_path: Path,
    *,
    scope_kind: str,
    scope_value: str,
    kind: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    path = source_path.resolve()
    inferred_kind = kind or _infer_knowledge_kind(path)
    if inferred_kind is None:
        raise ValueError(f"unsupported knowledge source {path}")

    payload_value = _load_source_payload(path)
    body = _body_from_source(path, payload_value)
    timestamp = _timestamp_from_path(path)
    derived_from = _derived_refs_from_source(path)
    return {
        "id": _stable_id("know", path),
        "kind": inferred_kind,
        "title": title or _title_from_source(path, payload_value),
        "scope": {
            "kind": scope_kind,
            "value": scope_value,
        },
        "body": body,
        "source_refs": [f"file://{path}", *derived_from],
        "derived_from": derived_from,
        "status": "active",
        "sensitivity": _infer_sensitivity(path),
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def build_prompt_payload(
    source_path: Path,
    *,
    scope_kind: str,
    scope_value: str,
    prompt_id: str | None = None,
    name: str | None = None,
    intent: str = "general",
    owner: str = "local_import",
    required_context_types: list[str] | None = None,
) -> dict[str, Any]:
    path = source_path.resolve()
    payload = _load_source_payload(path)
    if isinstance(payload, dict):
        return _normalize_prompt_payload(
            payload,
            source_path=path,
            scope_kind=scope_kind,
            scope_value=scope_value,
            prompt_id=prompt_id,
            name=name,
            intent=intent,
            owner=owner,
            required_context_types=required_context_types or [],
        )

    frontmatter, instruction_text = _parse_markdown_frontmatter(str(payload)) if path.suffix.lower() == ".md" else ({}, str(payload).strip())
    timestamp = _timestamp_from_path(path)
    frontmatter_id = _string_value(frontmatter.get("id"))
    frontmatter_title = _string_value(frontmatter.get("title"))
    frontmatter_intent = _string_value(frontmatter.get("skill")) or _string_value(frontmatter.get("category"))
    return {
        "id": prompt_id or frontmatter_id or _stable_id("prompt", path),
        "name": name or frontmatter_title or _humanize_slug(frontmatter_id or path.stem),
        "intent": intent if intent != "general" else (frontmatter_intent or intent),
        "scope": {"kind": scope_kind, "value": scope_value},
        "status": "active",
        "instruction": instruction_text,
        "required_context_types": list(required_context_types or []),
        "output_contract": {"format": "markdown", "sections": []},
        "model_preferences": {},
        "derived_from": [f"file://{path}"],
        "owner": owner,
        "eval_status": "unvalidated",
        "known_failure_modes": [],
        "anti_patterns": [],
        "last_promoted_at": None,
        "quality_metrics": {},
        "sensitivity": _infer_sensitivity(path),
        "redaction_state": "none",
        "secret_refs": [],
        "exportable": True,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _normalize_prompt_payload(
    payload: dict[str, Any],
    *,
    source_path: Path,
    scope_kind: str,
    scope_value: str,
    prompt_id: str | None,
    name: str | None,
    intent: str,
    owner: str,
    required_context_types: list[str],
) -> dict[str, Any]:
    timestamp = _timestamp_from_path(source_path)
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    normalized = dict(payload)
    normalized["id"] = prompt_id or _string_value(payload.get("id")) or _stable_id("prompt", source_path)
    normalized["name"] = name or _string_value(payload.get("name")) or _title_from_source(source_path, payload)
    normalized["intent"] = _string_value(payload.get("intent")) or intent
    normalized["scope"] = {
        "kind": _string_value(scope.get("kind")) or scope_kind,
        "value": _string_value(scope.get("value")) or scope_value,
    }
    normalized["status"] = _string_value(payload.get("status")) or "active"
    instruction = _string_value(payload.get("instruction"))
    if not instruction:
        raise ValueError(f"prompt payload at {source_path} must include instruction")
    normalized["instruction"] = instruction
    normalized["required_context_types"] = _string_list(payload.get("required_context_types")) or required_context_types
    normalized["output_contract"] = payload.get("output_contract") if isinstance(payload.get("output_contract"), dict) else {"format": "markdown", "sections": []}
    normalized["model_preferences"] = payload.get("model_preferences") if isinstance(payload.get("model_preferences"), dict) else {}
    normalized["derived_from"] = _string_list(payload.get("derived_from")) or [f"file://{source_path}"]
    normalized["owner"] = _string_value(payload.get("owner")) or owner
    normalized["eval_status"] = _string_value(payload.get("eval_status")) or "unvalidated"
    normalized["known_failure_modes"] = _string_list(payload.get("known_failure_modes"))
    normalized["anti_patterns"] = _string_list(payload.get("anti_patterns"))
    normalized["last_promoted_at"] = payload.get("last_promoted_at")
    normalized["quality_metrics"] = payload.get("quality_metrics") if isinstance(payload.get("quality_metrics"), dict) else {}
    normalized["sensitivity"] = _string_value(payload.get("sensitivity")) or _infer_sensitivity(source_path)
    normalized["redaction_state"] = _string_value(payload.get("redaction_state")) or "none"
    normalized["secret_refs"] = _string_list(payload.get("secret_refs"))
    normalized["exportable"] = bool(payload.get("exportable", True))
    normalized["created_at"] = _timestamp_from_value(payload.get("created_at")) or timestamp
    normalized["updated_at"] = _timestamp_from_value(payload.get("updated_at")) or timestamp
    return normalized


def _iter_knowledge_sources(root: Path, *, recursive: bool) -> Iterable[Path]:
    if not root.exists():
        raise FileNotFoundError(root)
    iterator = root.rglob("*") if recursive else root.glob("*")
    for path in sorted(iterator):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if path.name in SKIP_FILE_NAMES:
            continue
        if path.suffix.lower() not in SUPPORTED_KNOWLEDGE_EXTENSIONS:
            continue
        if _infer_knowledge_kind(path) is None:
            continue
        yield path


def _load_source_payload(path: Path) -> Any:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return path.read_text(encoding="utf-8")


def _body_from_source(path: Path, payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        if _is_canonical_project(payload, path):
            lines: list[str] = []
            title = _string_value(payload.get("title")) or _humanize_slug(path.stem)
            lines.append(title)
            summary = _string_value(payload.get("current_summary"))
            if summary:
                lines.append(summary)
            claims = payload.get("claims")
            if isinstance(claims, list) and claims:
                lines.append("Claims:\n" + "\n".join(f"- {value}" for value in claims if isinstance(value, str)))
            return "\n\n".join(lines)
        return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
    if isinstance(payload, list):
        return json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
    return str(payload)


def _title_from_source(path: Path, payload: Any) -> str:
    if isinstance(payload, dict):
        title = _string_value(payload.get("title")) or _string_value(payload.get("name"))
        if title:
            return title
    headline = _headline_title(path)
    if headline:
        return headline
    return _humanize_slug(path.stem)


def _parse_markdown_frontmatter(text: str) -> tuple[dict[str, str], str]:
    stripped = text.strip()
    if not stripped.startswith("---\n"):
        return {}, stripped

    lines = stripped.splitlines()
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, stripped

    metadata: dict[str, str] = {}
    for line in lines[1:end_index]:
        key, separator, value = line.partition(":")
        if not separator:
            continue
        normalized_key = key.strip()
        normalized_value = value.strip()
        if normalized_key and normalized_value:
            metadata[normalized_key] = normalized_value
    body = "\n".join(lines[end_index + 1 :]).strip()
    return metadata, body


def _headline_title(path: Path) -> str | None:
    if path.suffix.lower() not in {".md", ".txt"}:
        return None
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        return None
    return None


def _infer_knowledge_kind(path: Path) -> str | None:
    lower_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if name in SKIP_FILE_NAMES:
        return None
    if "raw" in lower_parts:
        return None
    if "canonical" in lower_parts and "projects" in lower_parts and path.suffix.lower() == ".json":
        return "project_profile"
    if "webfetch" in lower_parts and name == "readme.md":
        return "research_archive"
    if "webfetch" in lower_parts and name.startswith("source-"):
        return "research_note"
    if "sessions" in lower_parts and name == "readme.md":
        return "session_handoff"
    if name == "decisions.md":
        return "decision_log"
    if name == "cortex-facts.md":
        return "facts_log"
    if name.endswith(".json"):
        return "structured_note"
    if "docs" in lower_parts or "design" in name or "spec" in name:
        return "design_note"
    if path.suffix.lower() in {".md", ".txt"}:
        return "note"
    return None


def _derived_refs_from_source(path: Path) -> list[str]:
    refs: list[str] = []
    if path.name.lower() == "readme.md" and "webfetch" in {part.lower() for part in path.parts}:
        manifest = path.with_name("manifest.toml")
        if manifest.exists():
            refs.append(f"file://{manifest.resolve()}")
    return refs


def _infer_sensitivity(path: Path) -> str:
    lower = str(path).lower()
    if "/webfetch/" in lower:
        return "public"
    return "internal"


def _is_canonical_project(payload: dict[str, Any], path: Path) -> bool:
    kind = _string_value(payload.get("kind"))
    return kind == "canonical_project" or "canonical" in {part.lower() for part in path.parts}


def _is_normalized_transcript(payload: dict[str, Any]) -> bool:
    turns = payload.get("turns")
    return isinstance(turns, list) and bool(turns)


def _is_deepseek_messages_export(path: Path, payload: dict[str, Any], client: str) -> bool:
    return "deepseek" in _source_hint(path, payload, client) and bool(_source_hinted_messages(payload))


def _is_ollama_ui_messages_export(path: Path, payload: dict[str, Any], client: str) -> bool:
    hint = _source_hint(path, payload, client)
    return any(marker in hint for marker in ("ollama", "open-webui", "openwebui")) and bool(_source_hinted_messages(payload))


def _source_hint(path: Path, payload: dict[str, Any], client: str) -> str:
    values = [
        client,
        path.name,
        _string_value(payload.get("source_app")) or "",
        _string_value(payload.get("source_surface")) or "",
        _string_value(payload.get("source_format")) or "",
        _string_value(payload.get("provider")) or "",
        _string_value(payload.get("model")) or "",
    ]
    return " ".join(value.lower() for value in values if value)


def _source_hinted_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for container in (
        payload.get("messages"),
        _deep_value(payload, "chat", "messages"),
        _deep_value(payload, "chat", "history", "messages"),
        _deep_value(payload, "conversation", "messages"),
        _deep_value(payload, "history", "messages"),
    ):
        if isinstance(container, list):
            return [item for item in container if isinstance(item, dict)]
    return []


def _normalize_role_content_turns(
    messages: list[dict[str, Any]],
    *,
    session_object_id: str,
    source_name: str,
) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for index, item in enumerate(messages, start=1):
        content = _message_content_text(item)
        if not content:
            continue
        turns.append(
            {
                "id": _string_value(item.get("id")) or _string_value(item.get("message_id")) or _string_value(item.get("uuid")) or f"{session_object_id}_turn_{index:04d}",
                "role": _normalize_role(_string_value(item.get("role")) or _string_value(item.get("speaker")) or _string_value(item.get("type")) or "unknown"),
                "content": content,
                "status": "recorded",
                "created_at": _first_timestamp(item, ["created_at", "createdAt", "timestamp", "time", "date"]),
                "source_app": source_name,
            }
        )
    return turns


def _message_content_text(item: dict[str, Any]) -> str | None:
    content = item.get("content")
    if isinstance(content, dict):
        return _string_value(content.get("text")) or _string_value(content.get("content")) or _rich_text_to_string([content])
    return _string_value(content) or _rich_text_to_string(content) or _string_value(item.get("text"))


def _conversation_title(payload: dict[str, Any], path: Path) -> str:
    return (
        _string_value(payload.get("title"))
        or _string_value(payload.get("name"))
        or _deep_string(payload, "chat", "title")
        or _deep_string(payload, "conversation", "title")
        or _humanize_slug(path.stem)
    )


def _first_timestamp(payload: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        timestamp = _timestamp_from_value(payload.get(key))
        if timestamp:
            return timestamp
    return None


def _deep_value(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _build_source_connector_receipt(
    *,
    source_path: Path,
    session_payload: dict[str, Any],
    session_ref: str,
    turn_refs: tuple[str, ...],
) -> SourceConnectorReceipt:
    source_app = str(session_payload.get("source_app") or "unknown")
    source_format = str(session_payload.get("source_format") or "unknown")
    return SourceConnectorReceipt(
        receipt_id=_source_connector_receipt_id(str(session_payload.get("id") or "session"), source_path),
        connector_id=_connector_id(source_app, source_format),
        source_app=source_app,
        source_surface=str(session_payload.get("source_surface") or "local"),
        source_format=source_format,
        capture_method=str(session_payload.get("capture_method") or "file_import"),
        imported_via=str(session_payload.get("imported_via") or "ctxvault_import"),
        source_ref=f"file://{source_path}",
        imported_at=_timestamp_from_value(session_payload.get("started_at")) or _timestamp_from_path(source_path),
        scope={
            "kind": str((session_payload.get("scope") or {}).get("kind") or "project"),
            "value": str((session_payload.get("scope") or {}).get("value") or "ctxvault"),
        },
        object_refs=(session_ref, *turn_refs),
        turn_count=len(turn_refs),
        normalization={
            "status": "normalized",
            "input_shape": source_format,
            "output_shape": "ctxvault.normalized-transcript",
            "lossiness": _connector_lossiness(source_app, source_format),
        },
        warnings=tuple(_connector_warnings(source_app, source_format)),
    )


def _source_connector_receipt_id(session_id: str, source_path: Path) -> str:
    slug = _slugify(session_id) or "session"
    digest = hashlib.sha256(str(source_path.resolve()).encode("utf-8")).hexdigest()[:10]
    return f"screc_{slug}_{digest}"


def _connector_id(source_app: str, source_format: str) -> str:
    if source_app == "deepseek" and source_format == "deepseek_messages_export":
        return "connector.deepseek.experimental"
    if source_app == "ollama" and source_format == "ollama_ui_messages_export":
        return "connector.ollama-ui.experimental"
    if source_format == "normalized_transcript":
        return "connector.normalized-transcript"
    return f"connector.{_slugify(source_app) or 'unknown'}"


def _connector_lossiness(source_app: str, source_format: str) -> list[str]:
    if source_app in {"deepseek", "ollama"} and source_format != "normalized_transcript":
        return ["private experimental adapter preserves role, content, message ids, and timestamps but not all native UI metadata"]
    if source_format == "normalized_transcript":
        return ["native product metadata is not preserved unless mapped into explicit source fields"]
    return ["native product metadata may be reduced to the canonical transcript fields"]


def _connector_warnings(source_app: str, source_format: str) -> list[str]:
    if source_app in {"deepseek", "ollama"} and source_format != "normalized_transcript":
        return [f"{source_app} adapter is private experimental and source-shape gated"]
    if source_app in {"deepseek", "ollama"}:
        return [f"{source_app} coverage uses normalized transcript fallback unless a native adapter matches the source shape"]
    return []


def _stable_id(prefix: str, path: Path) -> str:
    slug = _slugify(path.stem) or prefix
    digest = hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{slug}_{digest}"


def _stable_child_id(path: Path, prefix: str, ordinal: int | None) -> str:
    child = path if ordinal is None else path.with_name(f"{path.stem}_{ordinal}")
    return _stable_id(prefix, child)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _humanize_slug(value: str) -> str:
    pieces = [piece for piece in re.split(r"[_-]+", value) if piece]
    if not pieces:
        return value
    return " ".join(piece.capitalize() for piece in pieces)


def _timestamp_from_path(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).replace(microsecond=0).isoformat()


def _timestamp_from_value(value: Any) -> str | None:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(microsecond=0).isoformat()
    if isinstance(value, str) and value.strip():
        normalized = value.strip()
        try:
            return datetime.fromisoformat(normalized.replace("Z", "+00:00")).isoformat()
        except ValueError:
            return normalized
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _deep_string(payload: dict[str, Any], *path: str) -> str | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return _string_value(current)


def _rich_text_to_string(value: Any) -> str | None:
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                text = _string_value(item)
            elif isinstance(item, dict):
                text = _string_value(item.get("text")) or _string_value(item.get("thinking")) or _string_value(item.get("content"))
            else:
                text = _string_value(item)
            if text:
                parts.append(text)
        return "\n\n".join(parts) if parts else None
    return _string_value(value)


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized in {"human", "user"}:
        return "user"
    if normalized in {"assistant", "gemini", "model"}:
        return "assistant"
    if normalized == "system":
        return "system"
    return normalized or "unknown"


def _resolved_client_name(client: str, default_name: str) -> str:
    return default_name if client == "local_import" else client


def _default_source_app(client: str, default_name: str) -> str:
    resolved = _string_value(client)
    if resolved and resolved != "local_import":
        return resolved
    return default_name


def _capture_method_from_source_path(path: Path) -> str:
    if path.is_dir():
        return "directory_import"
    if path.suffix.lower() == ".zip":
        return "zip_import"
    return "file_import"


def _chatgpt_branch_messages(mapping: Any) -> list[dict[str, Any]]:
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("chatgpt export must include a non-empty mapping object")
    nodes = {key: value for key, value in mapping.items() if isinstance(value, dict)}
    leaf_paths: list[list[dict[str, Any]]] = []
    for node in nodes.values():
        children = node.get("children")
        if isinstance(children, list) and children:
            continue
        path_nodes: list[dict[str, Any]] = []
        current = node
        while isinstance(current, dict):
            path_nodes.append(current)
            parent_id = _string_value(current.get("parent"))
            if not parent_id:
                break
            current = nodes.get(parent_id)
        leaf_paths.append(list(reversed(path_nodes)))

    if not leaf_paths:
        leaf_paths = [list(nodes.values())]

    best_path = max(
        leaf_paths,
        key=lambda path_nodes: (
            _sort_timestamp_value(_deep_message_value(path_nodes[-1], "create_time")),
            len(path_nodes),
        ),
    )
    messages = []
    for node in best_path:
        message = node.get("message")
        if isinstance(message, dict):
            messages.append(message)
    if messages:
        return messages
    raise ValueError("chatgpt export did not contain any importable messages")


def _deep_message_value(node: dict[str, Any], key: str) -> Any:
    message = node.get("message")
    if isinstance(message, dict):
        return message.get(key)
    return None


def _sort_timestamp_value(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _chatgpt_content_text(content: Any) -> str | None:
    if not isinstance(content, dict):
        return _string_value(content)
    parts = content.get("parts")
    if isinstance(parts, list):
        text_parts = [text for item in parts if (text := _rich_text_to_string(item))]
        if text_parts:
            return "\n\n".join(text_parts)
    return _string_value(content.get("text")) or _string_value(content.get("content_type"))
