from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

CHANGE_GATE_REPORT_SCHEMA_ID = "ctxvault.change-gate-report/v0"

SURFACE_GLOB_PATTERNS = {
    "agent_instruction": ["AGENTS.md", "AGENTS"],
    "claude_instruction": ["CLAUDE.md", "CLAUDE"],
    "gemini_instruction": ["GEMINI.md", "GEMINI"],
    "readme": ["README.md", "README"],
    "skill": ["SKILL.md", "SKILL"],
    "cursor_rule": [".cursorrules"],
    "mcp_config": [".mcp.json", "mcp.json"],
}

EXCLUDED_DIR_NAMES = frozenset({
    ".ctxvault",
    ".git",
    ".github",
    ".knowledge-drafts",
    ".staging",
    ".worktrees",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".cursor",
    ".vscode",
    ".idea",
    "artifacts",
    "output",
})

DEFAULT_MAX_FILE_BYTES = 512 * 1024

CHANGE_FINDING_TYPES = frozenset({
    "authority_escalation",
    "authority_shift",
    "capability_expansion",
    "scope_expansion",
    "lifecycle_change",
    "evidence_provenance_drop",
    "sensitivity_increase",
    "surface_added",
    "surface_removed",
    "structural_shift",
})

SEVERITY_LEVELS = {"info", "low", "medium", "high", "critical"}

AUTHORITY_KEYWORDS = {
    "can": "read_only",
    "may": "read_only",
    "must": "review_required",
    "must not": "deny",
    "allow": "allow",
    "deny": "deny",
    "block": "block",
    "override": "override",
    "review": "review_required",
    "approve": "review_required",
    "approval": "review_required",
    "requires human review": "review_required",
    "requires approval": "review_required",
}

CAPABILITY_KEYWORDS = {
    "write": "write",
    "delete": "delete",
    "deploy": "deploy",
    "execute": "execute",
    "read": "read",
    "scan": "read",
    "inform": "inform",
    "suggest": "inform",
    "warn": "inform",
    "observe": "read",
    "query": "read",
    "ingest": "write",
    "import": "write",
    "project": "write",
    "projection": "write",
    "promote": "write",
    "promotion": "write",
    "publish": "publish",
    "side effect": "write",
    "side-effect": "write",
    "network": "network",
    "http": "network",
    "api": "network",
    "no network": "no_network",
    "never network": "no_network",
}

SCOPE_KEYWORDS = {
    "project": "project",
    "repo": "project",
    "repository": "project",
    "user": "user",
    "system": "system",
    "machine": "system",
    "global": "system",
    "tenant": "tenant",
    "workspace": "workspace",
    "session": "session",
    "cross-session": "tenant",
}


@dataclass(frozen=True)
class SurfaceFile:
    surface_kind: str
    path: Path
    relative_path: str
    source_ref: str
    text: str
    sha256: str
    size_bytes: int


@dataclass
class ParsedSurface:
    surface_kind: str
    source_ref: str
    sha256: str
    authority: dict[str, Any]
    capabilities: list[str]
    scope: dict[str, Any]
    lifecycle: dict[str, Any]
    sensitivity: str
    allowed_effects: list[str]


@dataclass(frozen=True)
class SemanticFinding:
    finding_id: str
    source_ref: str
    finding_type: str
    severity: str
    reason: str
    baseline_state: dict[str, Any]
    head_state: dict[str, Any]
    rollback_ref: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "source_ref": self.source_ref,
            "finding_type": self.finding_type,
            "severity": self.severity,
            "reason": self.reason,
            "baseline_state": self.baseline_state,
            "head_state": self.head_state,
            "rollback_ref": self.rollback_ref,
        }


def discover_surfaces(root: Path, *, max_file_bytes: int = DEFAULT_MAX_FILE_BYTES, strict_text: bool = False) -> list[SurfaceFile]:
    root = root.resolve()
    surfaces: list[SurfaceFile] = []

    for path in sorted(root.rglob("*")):
        surface_kind = _classify_surface(path)
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in relative_parts) and not _allowed_excluded_surface(surface_kind, relative_parts):
            continue
        content_path = path
        if path.is_symlink():
            if surface_kind is None:
                continue
            try:
                content_path = path.resolve(strict=True)
                content_relative_parts = content_path.relative_to(root).parts
            except (OSError, ValueError) as exc:
                if strict_text:
                    raise ValueError(
                        f"symlink surface target escapes strict dual-tree root: {path.relative_to(root)}"
                    ) from exc
                continue
            if any(part in EXCLUDED_DIR_NAMES for part in content_relative_parts) and not _allowed_excluded_surface(surface_kind, content_relative_parts):
                if strict_text:
                    raise ValueError(
                        f"symlink surface target points to excluded directory: {path.relative_to(root)}"
                    )
                continue
        if not content_path.is_file():
            continue
        if surface_kind is None:
            continue
        try:
            size = content_path.stat().st_size
        except OSError:
            if strict_text:
                raise ValueError(f"surface metadata cannot be read in strict dual-tree mode: {path.relative_to(root)}")
            continue
        if strict_text and size > max_file_bytes:
            raise ValueError(f"surface exceeds max_file_bytes={max_file_bytes}: {path.relative_to(root)}")
        try:
            sha256 = _sha256_file(content_path)
        except OSError as exc:
            if strict_text:
                raise ValueError(f"surface cannot be read in strict dual-tree mode: {path.relative_to(root)}") from exc
            continue
        if size > max_file_bytes:
            text = ""
        else:
            try:
                text = content_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                if strict_text:
                    raise ValueError(f"surface is not readable UTF-8 in strict dual-tree mode: {path.relative_to(root)}")
                text = ""
        surfaces.append(
            SurfaceFile(
                surface_kind=surface_kind,
                path=path,
                relative_path=str(path.relative_to(root)),
                source_ref=f"file://{path.relative_to(root)}",
                text=text,
                sha256=sha256,
                size_bytes=size,
            )
        )

    surfaces.sort(key=lambda s: (s.surface_kind, s.source_ref.lower()))
    return surfaces


def parse_surface(surface: SurfaceFile) -> ParsedSurface:
    return ParsedSurface(
        surface_kind=surface.surface_kind,
        source_ref=surface.source_ref,
        sha256=surface.sha256,
        authority=_parse_authority(surface),
        capabilities=_parse_capabilities(surface),
        scope=_parse_scope(surface),
        lifecycle=_parse_lifecycle(surface),
        sensitivity=_parse_sensitivity(surface),
        allowed_effects=_parse_allowed_effects(surface),
    )


def parse_surfaces(surfaces: Iterable[SurfaceFile]) -> dict[str, ParsedSurface]:
    return {s.source_ref: parse_surface(s) for s in surfaces}


def semantic_diff(
    baseline: dict[str, ParsedSurface],
    head: dict[str, ParsedSurface],
    *,
    baseline_snapshot_id: str = "",
    head_snapshot_id: str = "",
) -> list[SemanticFinding]:
    findings: list[SemanticFinding] = []
    all_refs = sorted(set(baseline) | set(head))

    for idx, source_ref in enumerate(all_refs, start=1):
        b = baseline.get(source_ref)
        h = head.get(source_ref)
        if b is None and h is not None:
            findings.append(
                SemanticFinding(
                    finding_id=f"chg_{idx:04d}_surface_added",
                    source_ref=h.source_ref,
                    finding_type="surface_added",
                    severity=_surface_added_severity(h),
                    reason=_surface_added_reason(h),
                    baseline_state={},
                    head_state=_parsed_to_dict(h),
                    rollback_ref=f"delete://{h.source_ref}",
                )
            )
            continue
        if b is not None and h is None:
            findings.append(
                SemanticFinding(
                    finding_id=f"chg_{idx:04d}_surface_removed",
                    source_ref=b.source_ref,
                    finding_type="surface_removed",
                    severity="medium",
                    reason=f"Surface {_safe_display_name(source_ref)} was removed from the workspace.",
                    baseline_state=_parsed_to_dict(b),
                    head_state={},
                    rollback_ref=f"restore://{b.source_ref}",
                )
            )
            continue
        if b is not None and h is not None:
            findings.extend(_diff_authority(source_ref, b, h))
            findings.extend(_diff_capabilities(source_ref, b, h))
            findings.extend(_diff_scope(source_ref, b, h))
            findings.extend(_diff_lifecycle(source_ref, b, h))
            findings.extend(_diff_sensitivity(source_ref, b, h))

    for i, f in enumerate(findings, start=1):
        findings[i - 1] = SemanticFinding(
            finding_id=f"chg_{i:04d}_{f.finding_type}",
            source_ref=f.source_ref,
            finding_type=f.finding_type,
            severity=f.severity,
            reason=f.reason,
            baseline_state=f.baseline_state,
            head_state=f.head_state,
            rollback_ref=f"delete://change-gate-report",
        )

    return findings


def change_gate_decision(findings: list[SemanticFinding]) -> dict[str, Any]:
    blocked = [f for f in findings if f.severity in {"critical", "high"}]
    caveated = [f for f in findings if f.severity in {"medium"}]
    allowed = [f for f in findings if f.severity in {"low", "info"}]

    if blocked:
        top = "blocked"
        reason = f"{len(blocked)} high-severity semantic change(s) require review."
    elif caveated:
        top = "caveated"
        reason = f"{len(caveated)} medium-severity semantic change(s) require caveats."
    else:
        top = "allowed"
        reason = "No high/medium-severity semantic changes found."

    return {
        "schema_id": "ctxvault.change-gate-decision/v0",
        "top_decision": top,
        "finding_count": len(findings),
        "blocked_count": len(blocked),
        "caveated_count": len(caveated),
        "allowed_count": len(allowed),
        "reason": reason,
        "findings": [f.to_dict() for f in findings],
    }


def build_change_gate_report(
    baseline: dict[str, ParsedSurface],
    head: dict[str, ParsedSurface],
    *,
    root: Path,
    baseline_snapshot_id: str = "",
    head_snapshot_id: str = "",
) -> dict[str, Any]:
    root = root.resolve()
    findings = semantic_diff(
        baseline,
        head,
        baseline_snapshot_id=baseline_snapshot_id,
        head_snapshot_id=head_snapshot_id,
    )
    decision = change_gate_decision(findings)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    report_id = _report_id(root, baseline, head, generated_at)

    return {
        "schema_id": CHANGE_GATE_REPORT_SCHEMA_ID,
        "report_id": report_id,
        "generated_at": generated_at,
        "root": str(root),
        "baseline_snapshot_id": baseline_snapshot_id,
        "head_snapshot_id": head_snapshot_id,
        "baseline_surface_count": len(baseline),
        "head_surface_count": len(head),
        "decision": decision["top_decision"],
        "finding_count": decision["finding_count"],
        "blocked_count": decision["blocked_count"],
        "caveated_count": decision["caveated_count"],
        "allowed_count": decision["allowed_count"],
        "reason": decision["reason"],
        "findings": decision["findings"],
    }

CHANGE_GATE_INVENTORY_SCHEMA_ID = "ctxvault.public-change-gate-inventory/v0"


def build_change_gate_report_for_roots(
    *,
    root: Path,
    baseline_root: Path | None = None,
    head_root: Path | None = None,
    max_files: int = 64,
    max_bytes_per_file: int = DEFAULT_MAX_FILE_BYTES,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Build a read-only semantic inventory or diff for explicit source trees."""
    if (baseline_root is None) ^ (head_root is None):
        raise ValueError("baseline_root and head_root must be provided together")

    root = root.resolve()
    baseline = (baseline_root or root).resolve()
    head = (head_root or root).resolve()
    _require_existing_directory(root, "root")
    _require_existing_directory(baseline, "baseline_root")
    _require_existing_directory(head, "head_root")
    if baseline_root is not None and head_root is not None:
        _require_contained(root, baseline, "baseline_root")
        _require_contained(root, head, "head_root")

    baseline_surfaces = discover_surfaces(baseline, max_file_bytes=max_bytes_per_file, strict_text=baseline_root is not None)[:max_files]
    head_surfaces = discover_surfaces(head, max_file_bytes=max_bytes_per_file, strict_text=head_root is not None)[:max_files]
    _reject_oversized_surfaces(baseline_surfaces, max_bytes_per_file, "baseline_root")
    _reject_oversized_surfaces(head_surfaces, max_bytes_per_file, "head_root")
    baseline_parsed = parse_surfaces(baseline_surfaces)
    head_parsed = parse_surfaces(head_surfaces)

    report = build_change_gate_report(
        baseline_parsed,
        head_parsed,
        root=root,
        baseline_snapshot_id="real-source-baseline" if baseline_root else "single-tree-baseline",
        head_snapshot_id="real-source-head" if head_root else "single-tree-head",
    )
    report.update(
        {
            "input_mode": "real-source-dual-tree" if baseline_root else "single-tree-inventory",
            "baseline_root": str(baseline),
            "head_root": str(head),
            "source_manifest": {
                "baseline": _surface_manifest(baseline_surfaces),
                "head": _surface_manifest(head_surfaces),
            },
            "baseline_inventory": scan_repository_surfaces(baseline, max_files=max_files, max_bytes_per_file=max_bytes_per_file, checked_at=checked_at),
            "head_inventory": scan_repository_surfaces(head, max_files=max_files, max_bytes_per_file=max_bytes_per_file, checked_at=checked_at),
            "limits": {"max_files": max_files, "max_bytes_per_file": max_bytes_per_file},
            "side_effect_boundary": _read_only_side_effect_boundary(),
            "claim_boundary": _bounded_claim_boundary(),
        }
    )
    return report


def scan_repository_surfaces(
    root: Path,
    *,
    max_files: int = 64,
    max_bytes_per_file: int = DEFAULT_MAX_FILE_BYTES,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = root.resolve()
    _require_existing_directory(resolved, "root")
    surfaces = discover_surfaces(resolved, max_file_bytes=max_bytes_per_file)[:max_files]
    parsed = [parse_surface(surface) for surface in surfaces]
    return {
        "schema_id": CHANGE_GATE_INVENTORY_SCHEMA_ID,
        "created_at": checked_at or _utc_now(),
        "root": str(resolved),
        "surface_count": len(parsed),
        "surfaces": [_parsed_to_dict(surface) for surface in parsed],
        "limits": {"max_files": max_files, "max_bytes_per_file": max_bytes_per_file},
        "side_effect_boundary": _read_only_side_effect_boundary(),
    }


def render_change_gate_report_summary(report: dict[str, Any]) -> str:
    return _render_markdown(report)

def _utc_now() -> str:
    from datetime import datetime, timezone as tz
    return datetime.now(tz.utc).replace(microsecond=0).isoformat()

def _require_existing_directory(path: Path, label: str) -> None:
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"{label} does not exist or is not a directory: {path}")


def _require_contained(root: Path, path: Path, label: str) -> None:
    if path != root and not path.is_relative_to(root):
        raise ValueError(f"{label} must be inside root for strict dual-tree mode: {path}")


def _reject_oversized_surfaces(surfaces: list[SurfaceFile], max_file_bytes: int, label: str) -> None:
    oversized = [surface for surface in surfaces if surface.size_bytes > max_file_bytes]
    if oversized:
        refs = ", ".join(surface.source_ref for surface in oversized[:5])
        raise ValueError(f"{label} contains surface(s) exceeding max_file_bytes={max_file_bytes}: {refs}")


def _surface_manifest(surfaces: list[SurfaceFile]) -> dict[str, Any]:
    items = [
        {
            "surface_kind": surface.surface_kind,
            "source_ref": surface.source_ref,
            "sha256": surface.sha256,
            "size_bytes": surface.size_bytes,
        }
        for surface in surfaces
    ]
    return {
        "surface_count": len(items),
        "digest": hashlib.sha256(json.dumps(items, ensure_ascii=True, sort_keys=True).encode()).hexdigest(),
        "items": items,
    }


def _read_only_side_effect_boundary() -> dict[str, bool]:
    return {
        "network_call_performed": False,
        "provider_model_call_performed": False,
        "api_call_performed": False,
        "scheduler_or_daemon_started": False,
        "target_file_written": False,
        "hidden_state_written": False,
        "public_repo_written": False,
        "package_published": False,
    }


def _bounded_claim_boundary() -> dict[str, bool]:
    return {
        "public_claim_created": False,
        "comparative_outcome_claim_created": False,
        "external_use_claim_created": False,
        "readiness_or_certification_claim_created": False,
        "universal_fit_claim_created": False,
        "result_authority_claim_created": False,
        "protocol_guarantee_claim_created": False,
    }

def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Change Gate Report",
        "",
        f"- Report: `{report['report_id']}`",
        f"- Baseline surfaces: `{report['baseline_surface_count']}`",
        f"- Head surfaces: `{report['head_surface_count']}`",
        f"- Decision: `{report['decision']}`",
        f"- Findings: `{report['finding_count']}`",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No semantic changes detected.")
    for f in report["findings"]:
        lines.extend([
            f"### {f['finding_id']}",
            "",
            f"- Source: `{f['source_ref']}`",
            f"- Type: `{f['finding_type']}`",
            f"- Severity: `{f['severity']}`",
            f"- Reason: {f['reason']}",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"

def _classify_surface(path: Path) -> str | None:
    name = path.name
    parts = set(path.parts)
    suffix = path.suffix.lower()
    if name == "copilot-instructions.md" and ".github" in parts:
        return "github_copilot_instruction"
    if ".cursor" in parts and "rules" in parts and suffix in {".md", ".mdc", ".txt"}:
        return "cursor_rule"
    if ".clinerules" in parts and suffix in {".md", ".txt"}:
        return "cline_rule"
    for kind, patterns in SURFACE_GLOB_PATTERNS.items():
        if name in patterns:
            return kind
    if path.suffix.lower() == ".json":
        if "mcp" in name.lower():
            return "mcp_config"
    return None


def _allowed_excluded_surface(surface_kind: str | None, relative_parts: tuple[str, ...]) -> bool:
    if surface_kind == "github_copilot_instruction" and ".github" in relative_parts:
        return True
    if surface_kind == "cursor_rule" and ".cursor" in relative_parts:
        return True
    return False


def _parse_authority(surface: SurfaceFile) -> dict[str, Any]:
    text = surface.text.lower() if surface.text else ""
    result: dict[str, Any] = {
        "has_explicit_owner": False,
        "has_approval_gate": False,
        "highest_effect": "inform",
        "override_priority": None,
    }
    if not text:
        return result

    owner_match = re.search(r"\b(owner|author|maintainer)\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    result["has_explicit_owner"] = bool(owner_match)
    if owner_match:
        result["owner_ref"] = owner_match.group(2)

    if re.search(r"\b(approval|human review|requires review|review required)\b", text, re.IGNORECASE):
        result["has_approval_gate"] = True

    effects = [v for k, v in AUTHORITY_KEYWORDS.items() if k in text]
    if effects:
        if "override" in effects:
            result["highest_effect"] = "override"
            result["override_priority"] = "high"
        elif "deny" in effects or "block" in effects:
            result["highest_effect"] = "block"
        elif "review_required" in effects:
            result["highest_effect"] = "review_required"
        elif "allow" in effects:
            result["highest_effect"] = "allow"
        elif "write" in effects:
            result["highest_effect"] = "write"
        elif "read_only" in effects:
            result["highest_effect"] = "read_only"

    return result


def _parse_capabilities(surface: SurfaceFile) -> list[str]:
    text = surface.text.lower() if surface.text else ""
    if not text:
        return []
    found: set[str] = set()
    for keyword, capability in CAPABILITY_KEYWORDS.items():
        if keyword in text:
            if capability == "no_network":
                found.discard("network")
            else:
                found.add(capability)
    return sorted(found)


def _parse_scope(surface: SurfaceFile) -> dict[str, Any]:
    text = surface.text.lower() if surface.text else ""
    result: dict[str, Any] = {"scope_kind": "project", "scope_boundaries": []}
    if not text:
        return result

    for keyword, scope in SCOPE_KEYWORDS.items():
        if keyword in text:
            result["scope_kind"] = scope
            break

    if re.search(r"\b(scoped|limited|bound)\s+to\b", text):
        result["scope_boundaries"].append("explicitly_scoped")

    scope_match = re.findall(r"\b(scope|applies[_-]?to|scoped[_-]?to)\s*[:=]\s*(\S+)", text, re.IGNORECASE)
    for _, val in scope_match:
        result["scope_boundaries"].append(val.lower())

    if re.search(r"\b(all|any|every)\s+(agent|tool|repo|project)\b", text):
        result["scope_boundaries"].append("universal")
        result["scope_kind"] = "system"

    return result


def _parse_lifecycle(surface: SurfaceFile) -> dict[str, Any]:
    text = surface.text.lower() if surface.text else ""
    result: dict[str, Any] = {"has_expiry": False, "is_revokable": False, "lifecycle_state": "unknown"}
    if not text:
        return result

    if re.search(r"\b(active|candidate|quarantined|revoked|archived|expired)\b", text, re.IGNORECASE):
        result["lifecycle_state"] = "declared"

    if re.search(r"\b(expires|expiry|ttl|retention|retain|valid_until)\b", text, re.IGNORECASE):
        result["has_expiry"] = True

    if re.search(r"\b(revoke|revocable|rollback|undo|revert)\b", text, re.IGNORECASE):
        result["is_revokable"] = True

    return result


def _parse_sensitivity(surface: SurfaceFile) -> str:
    text = surface.text.lower() if surface.text else ""
    if not text:
        return "internal"
    if re.search(r"\b(restricted|confidential)\b", text):
        return "restricted"
    if re.search(r"\bsensitive\b", text):
        return "sensitive"
    if re.search(r"\b(public|open)\b", text):
        return "public"
    return "internal"


def _parse_allowed_effects(surface: SurfaceFile) -> list[str]:
    text = surface.text.lower() if surface.text else ""
    effects: list[str] = []
    if not text:
        return effects
    effect_pattern = re.compile(r"\ballowed\s+(?:effects?|actions?)\s*[:=]\s*(.+?)(?:\n|$)", re.IGNORECASE)
    for m in effect_pattern.finditer(text):
        parts = re.split(r"[,;]", m.group(1))
        effects.extend(p.strip() for p in parts if p.strip())
    return sorted(set(effects))


_SURFACE_EFFECT_ORDER = {
    "inform": 0,
    "suggest": 1,
    "read_only": 2,
    "allow": 3,
    "write": 4,
    "warn": 5,
    "review_required": 5,
    "block": 6,
    "deny": 6,
    "override": 7,
}

_SCOPE_ORDER = {
    "session": 0,
    "project": 1,
    "workspace": 2,
    "user": 3,
    "system": 4,
    "tenant": 5,
}

_CAPABILITY_ORDER = {
    "read": 0,
    "inform": 1,
    "no_network": 2,
    "network": 3,
    "write": 4,
    "execute": 5,
    "delete": 6,
    "deploy": 7,
    "publish": 8,
}


def _diff_authority(source_ref: str, b: ParsedSurface, h: ParsedSurface) -> list[SemanticFinding]:
    findings: list[SemanticFinding] = []
    b_effect = _SURFACE_EFFECT_ORDER.get(b.authority.get("highest_effect", "inform"), -1)
    h_effect = _SURFACE_EFFECT_ORDER.get(h.authority.get("highest_effect", "inform"), -1)
    b_approval = b.authority.get("has_approval_gate", False)
    h_approval = h.authority.get("has_approval_gate", False)

    if h_effect > b_effect:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="authority_escalation",
            severity="high",
            reason=f"Authority escalated from '{b.authority.get('highest_effect')}' to '{h.authority.get('highest_effect')}'.",
            baseline_state={"authority": b.authority},
            head_state={"authority": h.authority},
            rollback_ref="",
        ))
    elif b_approval and not h_approval:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="authority_shift",
            severity="high",
            reason="Approval gate was removed from the surface.",
            baseline_state={"authority": b.authority},
            head_state={"authority": h.authority},
            rollback_ref="",
        ))
    elif h_effect != b_effect:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="authority_shift",
            severity="medium" if h_effect < b_effect else "high",
            reason=f"Authority changed from '{b.authority.get('highest_effect')}' to '{h.authority.get('highest_effect')}'.",
            baseline_state={"authority": b.authority},
            head_state={"authority": h.authority},
            rollback_ref="",
        ))

    b_override = b.authority.get("override_priority")
    h_override = h.authority.get("override_priority")
    if h_override and not b_override:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="authority_escalation",
            severity="high",
            reason="Surface gained override priority.",
            baseline_state={"override_priority": b_override},
            head_state={"override_priority": h_override},
            rollback_ref="",
        ))

    return findings


def _diff_capabilities(source_ref: str, b: ParsedSurface, h: ParsedSurface) -> list[SemanticFinding]:
    findings: list[SemanticFinding] = []
    b_caps = set(b.capabilities)
    h_caps = set(h.capabilities)
    added = h_caps - b_caps

    for cap in sorted(added):
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="capability_expansion",
            severity=_capability_severity(cap),
            reason=f"New capability declared: '{cap}'.",
            baseline_state={"capabilities": sorted(b_caps)},
            head_state={"capabilities": sorted(h_caps)},
            rollback_ref="",
        ))
    return findings


def _diff_scope(source_ref: str, b: ParsedSurface, h: ParsedSurface) -> list[SemanticFinding]:
    findings: list[SemanticFinding] = []
    b_kind = b.scope.get("scope_kind", "project")
    h_kind = h.scope.get("scope_kind", "project")
    b_rank = _SCOPE_ORDER.get(b_kind, 0)
    h_rank = _SCOPE_ORDER.get(h_kind, 0)

    if h_rank > b_rank:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="scope_expansion",
            severity="high",
            reason=f"Scope expanded from '{b_kind}' to '{h_kind}'.",
            baseline_state={"scope": b.scope},
            head_state={"scope": h.scope},
            rollback_ref="",
        ))

    b_boundaries = set(b.scope.get("scope_boundaries", []))
    h_boundaries = set(h.scope.get("scope_boundaries", []))
    if "universal" in h_boundaries and "universal" not in b_boundaries:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="scope_expansion",
            severity="critical",
            reason="Scope boundary removed; surface now applies universally.",
            baseline_state={"scope": b.scope},
            head_state={"scope": h.scope},
            rollback_ref="",
        ))

    return findings


def _diff_lifecycle(source_ref: str, b: ParsedSurface, h: ParsedSurface) -> list[SemanticFinding]:
    findings: list[SemanticFinding] = []
    b_expiry = b.lifecycle.get("has_expiry", False)
    h_expiry = h.lifecycle.get("has_expiry", False)
    b_revokable = b.lifecycle.get("is_revokable", False)
    h_revokable = h.lifecycle.get("is_revokable", False)

    if b_expiry and not h_expiry:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="lifecycle_change",
            severity="medium",
            reason="Expiry or TTL was removed from the surface.",
            baseline_state={"lifecycle": b.lifecycle},
            head_state={"lifecycle": h.lifecycle},
            rollback_ref="",
        ))
    if b_revokable and not h_revokable:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="lifecycle_change",
            severity="medium",
            reason="Revokability was removed from the surface.",
            baseline_state={"lifecycle": b.lifecycle},
            head_state={"lifecycle": h.lifecycle},
            rollback_ref="",
        ))

    return findings


def _diff_sensitivity(source_ref: str, b: ParsedSurface, h: ParsedSurface) -> list[SemanticFinding]:
    findings: list[SemanticFinding] = []
    sensitivity_order = {"public": 0, "internal": 1, "sensitive": 2, "restricted": 3}
    b_rank = sensitivity_order.get(b.sensitivity, 1)
    h_rank = sensitivity_order.get(h.sensitivity, 1)
    if h_rank > b_rank:
        findings.append(SemanticFinding(
            finding_id="",
            source_ref=source_ref,
            finding_type="sensitivity_increase",
            severity="medium",
            reason=f"Sensitivity increased from '{b.sensitivity}' to '{h.sensitivity}'.",
            baseline_state={"sensitivity": b.sensitivity},
            head_state={"sensitivity": h.sensitivity},
            rollback_ref="",
        ))
    return findings


def _surface_added_severity(h: ParsedSurface) -> str:
    if h.authority.get("highest_effect") in {"override", "block", "deny"}:
        return "high"
    if h.authority.get("highest_effect") in {"write", "review_required"}:
        return "medium"
    return "low"


def _surface_added_reason(h: ParsedSurface) -> str:
    return (
        f"New surface '{h.surface_kind}' added at {h.source_ref} "
        f"with authority level '{h.authority.get('highest_effect', 'unknown')}'."
    )


def _capability_severity(cap: str) -> str:
    if cap in {"deploy", "publish", "delete", "execute"}:
        return "critical"
    if cap in {"write", "network"}:
        return "high"
    return "medium"


def _safe_display_name(source_ref: str) -> str:
    parts = source_ref.split("/")
    return parts[-1] if parts else source_ref


def _parsed_to_dict(p: ParsedSurface) -> dict[str, Any]:
    return {
        "surface_kind": p.surface_kind,
        "source_ref": p.source_ref,
        "sha256": p.sha256,
        "authority": p.authority,
        "capabilities": p.capabilities,
        "scope": p.scope,
        "lifecycle": p.lifecycle,
        "sensitivity": p.sensitivity,
        "allowed_effects": p.allowed_effects,
    }


def _report_id(root: Path, baseline: dict, head: dict, generated_at: str) -> str:
    b_count = len(baseline)
    h_count = len(head)
    b_digest = _dicts_digest({ref: p.sha256 for ref, p in baseline.items()})
    h_digest = _dicts_digest({ref: p.sha256 for ref, p in head.items()})
    entropy = os.urandom(8).hex()
    token = hashlib.sha256(
        f"{root}:{b_count}:{h_count}:{b_digest}:{h_digest}:{generated_at}:{entropy}".encode()
    ).hexdigest()[:12]
    return f"cg_{token}"


def _dicts_digest(mapping: dict[str, str]) -> str:
    return hashlib.sha256(
        json.dumps(mapping, ensure_ascii=True, sort_keys=True).encode()
    ).hexdigest()[:12]


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
