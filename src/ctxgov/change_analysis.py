from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any


CHANGE_GATE_REPORT_SCHEMA_ID = "ctxvault.public-change-gate-report/v0"
CHANGE_GATE_INVENTORY_SCHEMA_ID = "ctxvault.public-change-gate-inventory/v0"
SURFACE_NAMES = {"AGENTS.md", "AGENTS", "CLAUDE.md", "CLAUDE", "README.md", "SKILL.md", "mcp.json"}
SKIP_DIRS = {".git", ".ctxvault", ".venv", ".pytest_cache", "__pycache__", "build", "dist"}


def build_change_gate_report_for_roots(
    *,
    root: Path,
    baseline_root: Path | None = None,
    head_root: Path | None = None,
    max_files: int = 64,
    max_bytes_per_file: int = 262144,
    checked_at: str | None = None,
) -> dict[str, Any]:
    base = (baseline_root or root).resolve()
    head = (head_root or root).resolve()
    baseline = scan_repository_surfaces(base, max_files=max_files, max_bytes_per_file=max_bytes_per_file, checked_at=checked_at)
    current = scan_repository_surfaces(head, max_files=max_files, max_bytes_per_file=max_bytes_per_file, checked_at=checked_at)
    findings = _diff_surfaces(baseline["surfaces"], current["surfaces"])
    return {
        "schema_id": CHANGE_GATE_REPORT_SCHEMA_ID,
        "created_at": checked_at or _utc_now(),
        "mode": "two_tree_diff" if baseline_root or head_root else "single_tree_inventory",
        "baseline_root": str(base),
        "head_root": str(head),
        "finding_count": len(findings),
        "findings": findings,
        "baseline_inventory": baseline,
        "head_inventory": current,
        "side_effect_boundary": _side_effect_boundary(),
        "claim_boundary": _claim_boundary(),
    }


def scan_repository_surfaces(
    root: Path,
    *,
    max_files: int = 64,
    max_bytes_per_file: int = 262144,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = root.resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"repository root does not exist or is not a directory: {resolved}")
    surfaces = []
    for path in _iter_surface_files(resolved, max_files=max_files):
        raw = path.read_bytes()
        truncated = len(raw) > max_bytes_per_file
        raw = raw[:max_bytes_per_file]
        text = raw.decode("utf-8", "replace")
        rel = path.relative_to(resolved).as_posix()
        surfaces.append(
            {
                "path": rel,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "line_count": len(text.splitlines()),
                "truncated": truncated,
                "authority_terms": _count_terms(text, ("must", "required", "approval", "authority", "policy")),
                "capability_terms": _count_terms(text, ("tool", "network", "write", "execute", "provider", "api")),
            }
        )
    return {
        "schema_id": CHANGE_GATE_INVENTORY_SCHEMA_ID,
        "created_at": checked_at or _utc_now(),
        "root": str(resolved),
        "surface_count": len(surfaces),
        "surfaces": surfaces,
        "limits": {"max_files": max_files, "max_bytes_per_file": max_bytes_per_file},
        "side_effect_boundary": _side_effect_boundary(),
    }


def _iter_surface_files(root: Path, *, max_files: int) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if len(files) >= max_files:
            break
        if path.is_symlink() or not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.name in SURFACE_NAMES:
            files.append(path)
    return files


def _diff_surfaces(baseline: list[dict[str, Any]], head: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_by_path = {item["path"]: item for item in baseline}
    head_by_path = {item["path"]: item for item in head}
    findings: list[dict[str, Any]] = []
    for path in sorted(set(base_by_path) | set(head_by_path)):
        base = base_by_path.get(path)
        current = head_by_path.get(path)
        if base is None:
            findings.append(_finding(path, "surface_added", "medium", "Agent-facing surface was added."))
        elif current is None:
            findings.append(_finding(path, "surface_removed", "low", "Agent-facing surface was removed."))
        elif base.get("sha256") != current.get("sha256"):
            severity = "medium" if current.get("authority_terms", 0) >= base.get("authority_terms", 0) else "low"
            findings.append(_finding(path, "surface_modified", severity, "Agent-facing surface content changed."))
    return findings


def _finding(path: str, finding_type: str, severity: str, reason: str) -> dict[str, Any]:
    finding_id = hashlib.sha256(f"{path}:{finding_type}:{reason}".encode("utf-8")).hexdigest()[:16]
    return {"finding_id": f"finding-{finding_id}", "finding_type": finding_type, "severity": severity, "source_ref": path, "reason": reason}


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_access_performed": False,
        "provider_or_model_call_performed": False,
        "runtime_or_adapter_executed": False,
        "target_file_written": False,
        "public_write_performed": False,
        "scheduler_or_daemon_started": False,
    }


def _claim_boundary() -> dict[str, bool]:
    return {
        "public_efficiency_claim_created": False,
        "public_benchmark_claim_created": False,
        "public_adoption_claim_created": False,
        "provider_compatibility_claim_created": False,
        "stable_protocol_claim_created": False,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
