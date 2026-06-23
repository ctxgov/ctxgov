from __future__ import annotations

from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
from typing import Any


SESSION_CONTINUITY_SCHEMA_ID = "ctxvault.session-continuity-sidecar/v0"
SOURCE_TRACE_SCHEMA_ID = "ctxvault.session-continuity-saved-goal-trace/v0"
SUPPORTED_TARGETS = {"generic"}
SUPPORTED_APPLY_SURFACES = {"next-session", "claude-md", "agents-md"}
MANAGED_BLOCK_MARKER = "ctxvault:session-continuity"
MANAGED_BLOCK_START = f"<!-- {MANAGED_BLOCK_MARKER}:start -->"
MANAGED_BLOCK_END = f"<!-- {MANAGED_BLOCK_MARKER}:end -->"

ROLE_RE = re.compile(r"^\s*(system|developer|user|assistant|tool|function|observation|command)\s*[:：]\s*(.*)$", re.I)
PATH_RE = re.compile(r"(?:docs|fixtures|schemas|src|tests|scripts|release)/[A-Za-z0-9._/\-]+")
SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{20,}"), "[REDACTED_GOOGLE_KEY]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_ACCESS_KEY]"),
    (re.compile(r"xox[baprs]-[0-9A-Za-z\-]{20,}"), "[REDACTED_SLACK_TOKEN]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+"), "secret=[REDACTED_SECRET]"),
)

SIDE_EFFECT_FALSE_FIELDS = [
    "provider_or_model_call_performed",
    "runtime_or_adapter_executed",
    "target_file_written",
    "memory_backend_written",
    "memory_promotion_performed",
    "provider_memory_written",
    "tool_execution_performed",
    "public_release_created",
    "package_published",
    "outreach_performed",
    "public_claim_created",
]


def compile_session_continuity_sidecar(
    path: Path,
    *,
    target: str = "generic",
    max_injection_items: int = 8,
    checked_at: str | None = None,
) -> dict[str, Any]:
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported continuity target in public package: {target}")
    if max_injection_items < 1:
        raise ValueError("max_injection_items must be at least 1")

    source_path = path.resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"continuity source file does not exist: {source_path}")
    if not source_path.is_file():
        raise ValueError(f"continuity source path is not a file: {source_path}")

    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    raw_bytes = source_path.read_bytes()
    events = _load_events(source_path, raw_bytes)
    if not events:
        raise ValueError("continuity source produced no events")

    assets = _extract_information_assets(events)
    injection_order = assets[:max_injection_items]
    left_searchable = assets[max_injection_items:]

    return {
        "schema_id": SESSION_CONTINUITY_SCHEMA_ID,
        "object_type": "SessionContinuitySidecar",
        "version": "v0.7.0",
        "status": "public_safe_saved_trace_compiler_output",
        "created_at": checked_at,
        "source": {
            "path": str(source_path),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "event_count": len(events),
            "source_schema_id": _source_schema_id(source_path, raw_bytes),
        },
        "information_assets": assets,
        "context_injection_plan": {
            "status": "planned_not_executed",
            "target": target,
            "injection_order": injection_order,
            "left_searchable_only": left_searchable,
            "blocked_items": _blocked_items(),
        },
        "governance_summary": {
            "memory_promotion_allowed": False,
            "context_injection_executed": False,
            "provider_state_mutated": False,
            "public_claim_allowed": False,
        },
        "side_effect_boundary": _false_side_effect_boundary(),
        "rollback": {
            "mode": "discard_or_supersede_output",
            "delete_paths": [],
            "external_state_to_revert": "none",
        },
    }


def render_session_continuity_packet(
    path: Path,
    *,
    target: str = "generic",
    max_injection_items: int = 8,
    checked_at: str | None = None,
) -> str:
    sidecar = compile_session_continuity_sidecar(
        path,
        target=target,
        max_injection_items=max_injection_items,
        checked_at=checked_at,
    )
    return _render_markdown_packet(sidecar)


def apply_session_continuity_packet(
    path: Path,
    *,
    target: str = "generic",
    surface: str = "next-session",
    mode: str = "dry-run",
    sandbox_dir: Path | None = None,
    root: Path | None = None,
    max_injection_items: int = 8,
    checked_at: str | None = None,
) -> dict[str, Any]:
    if surface not in SUPPORTED_APPLY_SURFACES:
        raise ValueError(f"unsupported continuity apply surface: {surface}")
    if mode not in {"dry-run", "sandbox"}:
        raise ValueError(f"unsupported continuity apply mode: {mode}")

    sidecar = compile_session_continuity_sidecar(
        path,
        target=target,
        max_injection_items=max_injection_items,
        checked_at=checked_at,
    )
    sandbox_root = _resolve_sandbox_dir(root=root, sandbox_dir=sandbox_dir)
    target_path = sandbox_root / _surface_filename(surface)
    rendered = _render_surface_content(sidecar, surface)
    existing_content = target_path.read_text(encoding="utf-8") if target_path.exists() else None
    final_content, managed_block = _merge_surface_content(existing_content=existing_content, rendered=rendered)
    wrote_file = False
    if mode == "sandbox":
        sandbox_root.mkdir(parents=True, exist_ok=True)
        target_path.write_text(final_content, encoding="utf-8")
        wrote_file = True

    return {
        "schema_id": "ctxvault.session-continuity-apply-result/v0",
        "operation": "continuity.apply",
        "mode": mode,
        "surface": surface,
        "target": target,
        "status": "sandbox_written" if wrote_file else "dry_run_not_written",
        "source": sidecar["source"],
        "target_path": str(target_path),
        "target_path_is_sandbox": True,
        "content_sha256": hashlib.sha256(final_content.encode("utf-8")).hexdigest(),
        "content_preview": final_content,
        "patch_preview": _patch_preview(target_path, final_content, existing_content),
        "managed_block": managed_block,
        "context_injection_executed": False,
        "side_effect_boundary": _false_side_effect_boundary(target_file_written=wrote_file),
        "rollback": {
            "mode": "delete_sandbox_file" if wrote_file else "discard_dry_run_result",
            "delete_paths": [str(target_path)] if wrote_file else [],
            "external_state_to_revert": "none",
        },
    }


def _load_events(path: Path, raw_bytes: bytes) -> list[dict[str, Any]]:
    text = raw_bytes.decode("utf-8")
    if path.suffix.lower() == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ("events", "messages", "turns"):
                values = payload.get(key)
                if isinstance(values, list):
                    return [_normalize_event(item, index) for index, item in enumerate(values)]
            return [_normalize_event(payload, 0)]
        if isinstance(payload, list):
            return [_normalize_event(item, index) for index, item in enumerate(payload)]
        return [{"role": "source", "content": str(payload), "index": 0}]
    return [_normalize_text_line(line, index) for index, line in enumerate(text.splitlines()) if line.strip()]


def _normalize_event(item: Any, index: int) -> dict[str, Any]:
    if isinstance(item, dict):
        role = str(item.get("role") or item.get("speaker") or item.get("type") or "source")
        content = item.get("content") or item.get("text") or item.get("message") or item.get("summary") or item
        if not isinstance(content, str):
            content = json.dumps(content, sort_keys=True)
        return {"role": role, "content": content, "index": index}
    return {"role": "source", "content": str(item), "index": index}


def _normalize_text_line(line: str, index: int) -> dict[str, Any]:
    match = ROLE_RE.match(line)
    if match:
        return {"role": match.group(1).lower(), "content": match.group(2), "index": index}
    return {"role": "source", "content": line, "index": index}


def _extract_information_assets(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for event in events:
        content = _redact(str(event.get("content") or "")).strip()
        if not content:
            continue
        asset_type = _asset_type(content)
        if asset_type == "background" and len(assets) >= 8:
            continue
        assets.append(
            {
                "asset_id": f"asset_{len(assets) + 1:03d}",
                "asset_type": asset_type,
                "source_event_index": int(event.get("index", len(assets))),
                "source_role": str(event.get("role") or "source"),
                "summary": _compact(content),
                "source_refs": sorted(set(PATH_RE.findall(content))),
            }
        )
    return assets[:48]


def _asset_type(content: str) -> str:
    lowered = content.lower()
    if any(term in lowered for term in ("requirement", "must", "constraint", "guardrail")):
        return "requirement"
    if any(term in lowered for term in ("decision", "decided", "choose", "selected")):
        return "decision"
    if any(term in lowered for term in ("blocked", "blocker", "failed", "error")):
        return "blocker"
    if any(term in lowered for term in ("test", "passed", "receipt", "sha256")):
        return "tool_receipt"
    return "background"


def _compact(content: str, limit: int = 260) -> str:
    normalized = " ".join(content.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3].rstrip() + "..."


def _redact(text: str) -> str:
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _blocked_items() -> list[dict[str, Any]]:
    return [
        {
            "reason": "The public package only prepares reviewable local output.",
            "blocked_effects": ["act", "cache_reuse", "adapter_route", "sampler_bias", "train_or_publish"],
        }
    ]


def _source_schema_id(path: Path, raw_bytes: bytes) -> str:
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            return "unknown-json"
        if isinstance(payload, dict) and isinstance(payload.get("schema_id"), str):
            return payload["schema_id"]
    return SOURCE_TRACE_SCHEMA_ID


def _render_markdown_packet(sidecar: dict[str, Any]) -> str:
    plan = sidecar["context_injection_plan"]
    lines = [
        "# CtxGov Next-Session Continuity Packet",
        "",
        f"Status: {sidecar['status']}.",
        f"Target: `{plan['target']}`",
        f"Source SHA-256: `{sidecar['source']['sha256']}`",
        "",
        "## Injection Order",
    ]
    for item in plan["injection_order"]:
        lines.append(f"- `{item['asset_id']}` `{item['asset_type']}`: {item['summary']}")
    if plan["left_searchable_only"]:
        lines.extend(["", "## Searchable Only"])
        for item in plan["left_searchable_only"]:
            lines.append(f"- `{item['asset_id']}` `{item['asset_type']}`: {item['summary']}")
    lines.extend(["", "## Blocked Effects"])
    for item in plan["blocked_items"]:
        lines.append(f"- {', '.join(item['blocked_effects'])}")
    return "\n".join(lines).rstrip() + "\n"


def _render_surface_content(sidecar: dict[str, Any], surface: str) -> str:
    rendered = _render_markdown_packet(sidecar)
    if surface == "next-session":
        return rendered
    return f"{MANAGED_BLOCK_START}\n{rendered}{MANAGED_BLOCK_END}\n"


def _merge_surface_content(*, existing_content: str | None, rendered: str) -> tuple[str, dict[str, Any]]:
    if existing_content is None:
        return rendered, {"merge_action": "create", "preexisting_content_preserved": True}
    start = existing_content.find(MANAGED_BLOCK_START)
    end = existing_content.find(MANAGED_BLOCK_END)
    if start >= 0 and end >= start:
        end += len(MANAGED_BLOCK_END)
        final = existing_content[:start] + rendered.rstrip() + existing_content[end:]
        return final, {"merge_action": "replace_managed_block", "preexisting_content_preserved": True}
    return existing_content.rstrip() + "\n\n" + rendered, {"merge_action": "append_managed_block", "preexisting_content_preserved": True}


def _resolve_sandbox_dir(*, root: Path | None, sandbox_dir: Path | None) -> Path:
    if sandbox_dir is not None:
        return sandbox_dir.resolve()
    base = root.resolve() if root is not None else Path.cwd().resolve()
    return base / "ctxgov-continuity-sandbox"


def _surface_filename(surface: str) -> str:
    return {"next-session": "next-session.md", "claude-md": "CLAUDE.md", "agents-md": "AGENTS.md"}[surface]


def _patch_preview(target_path: Path, final_content: str, existing_content: str | None) -> str:
    before = [] if existing_content is None else existing_content.splitlines(keepends=True)
    after = final_content.splitlines(keepends=True)
    return "".join(difflib.unified_diff(before, after, fromfile=str(target_path), tofile=str(target_path)))


def _false_side_effect_boundary(*, target_file_written: bool = False) -> dict[str, bool]:
    boundary = {field: False for field in SIDE_EFFECT_FALSE_FIELDS}
    boundary["target_file_written"] = target_file_written
    return boundary
