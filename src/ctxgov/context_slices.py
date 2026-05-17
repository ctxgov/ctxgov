from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Any, Iterable

from .privacy import PrivacyFinding, scan_privacy_text


CONTEXT_SLICE_SCHEMA_ID = "ctxvault.context-slice/v1"
MAX_INDEX_BODY_BYTES = 8 * 1024
TARGET_MIN_WORDS = 80
TARGET_MAX_WORDS = 250
HARD_WARNING_WORDS = 500

SENSITIVITY_RANK = {
    "public": 0,
    "internal": 1,
    "sensitive": 2,
    "restricted": 3,
}


@dataclass(frozen=True)
class ContextSlice:
    slice_id: str
    slice_ref: str
    source_ref: str
    source_object_kind: str
    scope_kind: str | None
    scope_value: str | None
    workstream_ref: str | None
    slice_kind: str
    title: str
    heading_path: str | None
    line_start: int | None
    line_end: int | None
    byte_start: int | None
    byte_end: int | None
    content_sha256: str
    redacted_sha256: str | None
    privacy_class: str
    sensitivity: str
    redaction_state: str
    token_estimate: int
    updated_at: str
    redacted_preview: str
    source_content_sha256: str
    index_title: str
    index_body_redacted: str
    ranking_boost: float

    def to_contract(self) -> dict[str, Any]:
        return {
            "schema_id": CONTEXT_SLICE_SCHEMA_ID,
            "slice_id": self.slice_id,
            "slice_ref": self.slice_ref,
            "source_ref": self.source_ref,
            "source_object_kind": self.source_object_kind,
            "scope_kind": self.scope_kind,
            "scope_value": self.scope_value,
            "workstream_ref": self.workstream_ref,
            "slice_kind": self.slice_kind,
            "title": self.title,
            "heading_path": self.heading_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "byte_start": self.byte_start,
            "byte_end": self.byte_end,
            "content_sha256": self.content_sha256,
            "redacted_sha256": self.redacted_sha256,
            "privacy_class": self.privacy_class,
            "sensitivity": self.sensitivity,
            "redaction_state": self.redaction_state,
            "token_estimate": self.token_estimate,
            "updated_at": self.updated_at,
            "redacted_preview": self.redacted_preview,
            "source_content_sha256": self.source_content_sha256,
            "ranking_boost": self.ranking_boost,
        }


@dataclass(frozen=True)
class _MarkdownBlock:
    slice_kind: str
    text: str
    heading_path: tuple[str, ...]
    line_start: int
    line_end: int
    byte_start: int
    byte_end: int


def build_markdown_context_slices(
    *,
    source_kind: str,
    source_id: str,
    source_ref: str,
    source_object_kind: str,
    title: str,
    body_text: str,
    scope_kind: str | None,
    scope_value: str | None,
    workstream_ref: str | None,
    updated_at: str | None,
    sensitivity: str = "internal",
) -> list[ContextSlice]:
    source_sha = _sha256(body_text)
    blocks = _merge_small_paragraphs(_parse_markdown_blocks(body_text))
    counts: dict[tuple[str, tuple[str, ...], str], int] = {}
    slices: list[ContextSlice] = []
    for block in blocks:
        if not block.text.strip():
            continue
        duplicate_key = (block.slice_kind, block.heading_path, _sha256(block.text.strip()))
        counts[duplicate_key] = counts.get(duplicate_key, 0) + 1
        slices.append(
            _slice_from_text(
                source_kind=source_kind,
                source_id=source_id,
                source_ref=source_ref,
                source_object_kind=source_object_kind,
                scope_kind=scope_kind,
                scope_value=scope_value,
                workstream_ref=workstream_ref,
                slice_kind=block.slice_kind,
                title=_slice_title(title, block.heading_path, block.slice_kind),
                heading_path=" > ".join(block.heading_path) if block.heading_path else None,
                text=block.text,
                line_start=block.line_start,
                line_end=block.line_end,
                byte_start=block.byte_start,
                byte_end=block.byte_end,
                updated_at=updated_at,
                source_content_sha256=source_sha,
                sensitivity=sensitivity,
                ranking_boost=0.0,
                duplicate_ordinal=counts[duplicate_key],
            )
        )
    return slices


def build_turn_context_slice(
    *,
    turn_payload: dict[str, Any],
    updated_at: str | None = None,
) -> ContextSlice:
    turn_id = str(turn_payload["id"])
    role = str(turn_payload.get("role") or "unknown").strip() or "unknown"
    ordinal = int(turn_payload.get("ordinal") or 0)
    text = str(turn_payload.get("content") or "").strip()
    title = f"{role} turn {ordinal}" if ordinal else f"{role} turn"
    scope = turn_payload.get("scope") if isinstance(turn_payload.get("scope"), dict) else {}
    return _slice_from_text(
        source_kind="turn",
        source_id=turn_id,
        source_ref=f"turn://{turn_id}",
        source_object_kind="turn",
        scope_kind=str(scope.get("kind")) if scope.get("kind") is not None else None,
        scope_value=str(scope.get("value")) if scope.get("value") is not None else None,
        workstream_ref=None,
        slice_kind="session_turn",
        title=title,
        heading_path=None,
        text=f"{role}: {text}" if text else role,
        line_start=None,
        line_end=None,
        byte_start=None,
        byte_end=None,
        updated_at=updated_at or str(turn_payload.get("created_at") or ""),
        source_content_sha256=_sha256(text),
        sensitivity=str(turn_payload.get("sensitivity") or "internal"),
        ranking_boost=0.1,
    )


def build_episode_context_slice(
    *,
    episode_payload: dict[str, Any],
    updated_at: str | None = None,
) -> ContextSlice:
    episode_id = str(episode_payload["id"])
    scope = episode_payload.get("scope") if isinstance(episode_payload.get("scope"), dict) else {}
    text_parts = [
        str(episode_payload.get("title") or "").strip(),
        str(episode_payload.get("summary") or "").strip(),
        str(episode_payload.get("outcome") or "").strip(),
        " ".join(str(item).strip() for item in episode_payload.get("key_points", []) if str(item).strip()),
    ]
    text = "\n".join(part for part in text_parts if part)
    return _slice_from_text(
        source_kind="episode",
        source_id=episode_id,
        source_ref=f"episode://{episode_id}",
        source_object_kind="episode",
        scope_kind=str(scope.get("kind")) if scope.get("kind") is not None else None,
        scope_value=str(scope.get("value")) if scope.get("value") is not None else None,
        workstream_ref=None,
        slice_kind="session_episode",
        title=str(episode_payload.get("title") or episode_id),
        heading_path=None,
        text=text or episode_id,
        line_start=None,
        line_end=None,
        byte_start=None,
        byte_end=None,
        updated_at=updated_at or str(episode_payload.get("updated_at") or episode_payload.get("created_at") or ""),
        source_content_sha256=_sha256(text),
        sensitivity=str(episode_payload.get("sensitivity") or "internal"),
        ranking_boost=0.2,
    )


def build_compiled_state_context_slices(
    *,
    state_payload: dict[str, Any],
    scope_kind: str | None,
    scope_value: str | None,
) -> list[ContextSlice]:
    state_id = str(state_payload["state_id"])
    source_ref = f"compiled-state://{state_id}"
    workstream_ref = str(state_payload.get("workstream_ref") or "")
    generated_at = str(state_payload.get("generated_at") or "")
    source_sha = _sha256(_stable_text(state_payload))
    current_truth = state_payload.get("current_truth") if isinstance(state_payload.get("current_truth"), dict) else {}
    rows: list[tuple[str, str, str, float]] = []

    summary = current_truth.get("summary") if isinstance(current_truth.get("summary"), dict) else {}
    if str(summary.get("text") or "").strip():
        rows.append(("compiled_state_summary", "Compiled summary", str(summary["text"]).strip(), 1.0))

    for field, slice_kind, title, boost in [
        ("active_decisions", "workstream_decision", "Active decision", 1.4),
        ("active_constraints", "workstream_constraint", "Active constraint", 1.3),
        ("open_questions", "workstream_open_question", "Open question", 1.2),
        ("next_actions", "workstream_open_question", "Next action", 1.1),
    ]:
        for item in current_truth.get(field) or []:
            text = str(item.get("text") if isinstance(item, dict) else item).strip()
            if text:
                rows.append((slice_kind, title, text, boost))

    return [
        _slice_from_text(
            source_kind="compiled-state",
            source_id=state_id,
            source_ref=source_ref,
            source_object_kind="compiled_workstream_state",
            scope_kind=scope_kind,
            scope_value=scope_value,
            workstream_ref=workstream_ref or None,
            slice_kind=slice_kind,
            title=title,
            heading_path=None,
            text=text,
            line_start=None,
            line_end=None,
            byte_start=None,
            byte_end=None,
            updated_at=generated_at,
            source_content_sha256=source_sha,
            sensitivity="internal",
            ranking_boost=boost,
        )
        for slice_kind, title, text, boost in rows
    ]


def privacy_sort_key(privacy_class: str) -> int:
    return {
        "searchable_plain": 0,
        "searchable_redacted": 1,
        "metadata_only": 2,
        "withheld": 3,
    }.get(privacy_class, 4)


def redacted_text_for_findings(text: str, findings: Iterable[PrivacyFinding]) -> str:
    ordered = sorted(findings, key=lambda finding: (finding.start, finding.end))
    result: list[str] = []
    cursor = 0
    for finding in ordered:
        start = max(cursor, finding.start)
        end = max(start, finding.end)
        result.append(text[cursor:start])
        result.append(f"[REDACTED:{finding.category}]")
        cursor = end
    result.append(text[cursor:])
    return "".join(result)


def _parse_markdown_blocks(text: str) -> list[_MarkdownBlock]:
    lines = text.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in lines:
        offsets.append(cursor)
        cursor += len(line.encode("utf-8"))

    blocks: list[_MarkdownBlock] = []
    heading_stack: list[str] = []
    paragraph_lines: list[tuple[int, str]] = []
    code_lines: list[tuple[int, str]] = []
    list_lines: list[tuple[int, str]] = []
    in_code = False
    code_fence = ""

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if not paragraph_lines:
            return
        blocks.append(_block_from_lines("markdown_paragraph", paragraph_lines, heading_stack, offsets))
        paragraph_lines = []

    def flush_list() -> None:
        nonlocal list_lines
        if not list_lines:
            return
        blocks.append(_block_from_lines("markdown_list_block", list_lines, heading_stack, offsets))
        list_lines = []

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\r\n")
        stripped = line.strip()

        if in_code:
            code_lines.append((line_number, raw_line))
            if stripped.startswith(code_fence):
                blocks.append(_block_from_lines("markdown_code_block", code_lines, heading_stack, offsets))
                code_lines = []
                in_code = False
                code_fence = ""
            continue

        fence_match = re.match(r"^(```+|~~~+)", stripped)
        if fence_match:
            flush_paragraph()
            flush_list()
            in_code = True
            code_fence = fence_match.group(1)
            code_lines = [(line_number, raw_line)]
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            heading = heading_match.group(2).strip()
            heading_stack = heading_stack[: max(0, level - 1)]
            heading_stack.append(heading)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        if re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line):
            flush_paragraph()
            list_lines.append((line_number, raw_line))
            continue

        if list_lines and (line.startswith(" ") or line.startswith("\t")):
            list_lines.append((line_number, raw_line))
            continue

        flush_list()
        paragraph_lines.append((line_number, raw_line))

    if in_code and code_lines:
        blocks.append(_block_from_lines("markdown_code_block", code_lines, heading_stack, offsets))
    flush_paragraph()
    flush_list()
    return blocks


def _block_from_lines(
    slice_kind: str,
    numbered_lines: list[tuple[int, str]],
    heading_stack: list[str],
    offsets: list[int],
) -> _MarkdownBlock:
    line_start = numbered_lines[0][0]
    line_end = numbered_lines[-1][0]
    byte_start = offsets[line_start - 1]
    byte_end = offsets[line_end - 1] + len(numbered_lines[-1][1].encode("utf-8"))
    text = "".join(raw for _, raw in numbered_lines).strip()
    return _MarkdownBlock(
        slice_kind=slice_kind,
        text=text,
        heading_path=tuple(heading_stack),
        line_start=line_start,
        line_end=line_end,
        byte_start=byte_start,
        byte_end=byte_end,
    )


def _merge_small_paragraphs(blocks: list[_MarkdownBlock]) -> list[_MarkdownBlock]:
    merged: list[_MarkdownBlock] = []
    pending: _MarkdownBlock | None = None
    for block in blocks:
        if block.slice_kind != "markdown_paragraph":
            if pending is not None:
                merged.append(pending)
                pending = None
            merged.append(block)
            continue
        if pending is None:
            pending = block
            continue
        combined_text = f"{pending.text}\n\n{block.text}"
        if (
            pending.heading_path == block.heading_path
            and _word_count(pending.text) < TARGET_MIN_WORDS
            and _word_count(combined_text) <= TARGET_MAX_WORDS
        ):
            pending = _MarkdownBlock(
                slice_kind="markdown_paragraph",
                text=combined_text,
                heading_path=pending.heading_path,
                line_start=pending.line_start,
                line_end=block.line_end,
                byte_start=pending.byte_start,
                byte_end=block.byte_end,
            )
        else:
            merged.append(pending)
            pending = block
    if pending is not None:
        merged.append(pending)
    return merged


def _slice_from_text(
    *,
    source_kind: str,
    source_id: str,
    source_ref: str,
    source_object_kind: str,
    scope_kind: str | None,
    scope_value: str | None,
    workstream_ref: str | None,
    slice_kind: str,
    title: str,
    heading_path: str | None,
    text: str,
    line_start: int | None,
    line_end: int | None,
    byte_start: int | None,
    byte_end: int | None,
    updated_at: str | None,
    source_content_sha256: str,
    sensitivity: str,
    ranking_boost: float,
    duplicate_ordinal: int = 1,
) -> ContextSlice:
    normalized_text = text.strip()
    content_sha = _sha256(normalized_text)
    scan = scan_privacy_text(normalized_text, source=source_ref, max_findings=100)
    findings = list(scan.findings)
    privacy_class = _privacy_class(findings, scan.decision)
    redacted_preview = redacted_text_for_findings(normalized_text, findings) if findings else normalized_text
    redacted_preview = _trim_preview(redacted_preview)
    redaction_state = _redaction_state(privacy_class, bool(findings))
    effective_sensitivity = _max_sensitivity(sensitivity, _sensitivity_for_findings(findings))

    if privacy_class == "withheld":
        index_title = ""
        index_body = ""
        preview = ""
    elif privacy_class == "metadata_only":
        index_title = title
        index_body = ""
        preview = ""
    elif privacy_class == "searchable_redacted":
        index_title = title
        index_body = _limit_index_body(redacted_preview)
        preview = redacted_preview
    else:
        index_title = title
        index_body = _limit_index_body(normalized_text)
        preview = redacted_preview

    ref_hash = content_sha[:12]
    stable_ordinal = _stable_content_ordinal(source_ref, slice_kind, heading_path, content_sha, duplicate_ordinal)
    slice_ref = f"slice://{source_kind}/{source_id}#{slice_kind}/{stable_ordinal}-{ref_hash}"
    slice_id = _sha256("|".join([source_ref, slice_kind, heading_path or "", content_sha, str(duplicate_ordinal)]))[:24]
    redacted_sha = _sha256(preview) if preview else None
    token_estimate = _estimate_tokens([normalized_text])
    if _word_count(normalized_text) > HARD_WARNING_WORDS:
        token_estimate = max(token_estimate, _estimate_tokens([normalized_text[:MAX_INDEX_BODY_BYTES]]))

    return ContextSlice(
        slice_id=slice_id,
        slice_ref=slice_ref,
        source_ref=source_ref,
        source_object_kind=source_object_kind,
        scope_kind=scope_kind,
        scope_value=scope_value,
        workstream_ref=workstream_ref,
        slice_kind=slice_kind,
        title=title,
        heading_path=heading_path,
        line_start=line_start,
        line_end=line_end,
        byte_start=byte_start,
        byte_end=byte_end,
        content_sha256=content_sha,
        redacted_sha256=redacted_sha,
        privacy_class=privacy_class,
        sensitivity=effective_sensitivity,
        redaction_state=redaction_state,
        token_estimate=token_estimate,
        updated_at=updated_at or _utc_now(),
        redacted_preview=preview,
        source_content_sha256=source_content_sha256,
        index_title=index_title,
        index_body_redacted=index_body,
        ranking_boost=ranking_boost,
    )


def _privacy_class(findings: list[PrivacyFinding], decision: str) -> str:
    categories = {finding.category for finding in findings}
    severities = {finding.severity for finding in findings}
    if "credential_secret" in categories and "critical" in severities:
        return "withheld"
    if decision == "block":
        return "metadata_only"
    if decision in {"review", "redact"}:
        return "searchable_redacted"
    return "searchable_plain"


def _redaction_state(privacy_class: str, has_findings: bool) -> str:
    if privacy_class == "withheld":
        return "withheld"
    if privacy_class == "metadata_only":
        return "fully_redacted"
    if has_findings:
        return "partial"
    return "none"


def _sensitivity_for_findings(findings: list[PrivacyFinding]) -> str:
    if any(finding.severity in {"critical", "high"} for finding in findings):
        return "restricted"
    if any(finding.severity == "medium" for finding in findings):
        return "sensitive"
    if any(finding.severity == "low" for finding in findings):
        return "internal"
    return "public"


def _max_sensitivity(left: str, right: str) -> str:
    left_rank = SENSITIVITY_RANK.get(left, 1)
    right_rank = SENSITIVITY_RANK.get(right, 1)
    return left if left_rank >= right_rank else right


def _slice_title(title: str, heading_path: tuple[str, ...], slice_kind: str) -> str:
    heading = " > ".join(heading_path)
    base = heading or title or "Untitled source"
    suffix = {
        "markdown_code_block": "code",
        "markdown_list_block": "list",
        "markdown_paragraph": "paragraph",
    }.get(slice_kind, slice_kind)
    return f"{base} ({suffix})"


def _stable_content_ordinal(
    source_ref: str,
    slice_kind: str,
    heading_path: str | None,
    content_sha: str,
    duplicate_ordinal: int,
) -> int:
    seed = _sha256("|".join([source_ref, slice_kind, heading_path or "", content_sha, str(duplicate_ordinal)]))
    return int(seed[:6], 16) % 900000 + 100000


def _limit_index_body(text: str) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= MAX_INDEX_BODY_BYTES:
        return text
    return encoded[:MAX_INDEX_BODY_BYTES].decode("utf-8", errors="ignore")


def _trim_preview(text: str) -> str:
    compact = text.strip()
    if len(compact.encode("utf-8")) <= MAX_INDEX_BODY_BYTES:
        return compact
    return _limit_index_body(compact).rstrip() + "\n[TRUNCATED]"


def _estimate_tokens(parts: Iterable[str]) -> int:
    total_chars = sum(len(part) for part in parts if part)
    return max(1, total_chars // 4) if total_chars else 0


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text))


def _stable_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_stable_text(value[key])}" for key in sorted(value))
    if isinstance(value, list):
        return "\n".join(_stable_text(item) for item in value)
    return str(value)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
