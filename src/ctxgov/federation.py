from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .change_analysis import scan_repository_surfaces


FEDERATION_REPORT_SCHEMA_ID = "ctxvault.public-federation-report/v0"


def federate_auto_discover(
    base_path: Path,
    *,
    max_depth: int = 1,
    require_git: bool = True,
    extra_repos: list[Path] | None = None,
    max_repos: int = 16,
    max_files: int = 64,
    max_bytes_per_file: int = 262144,
) -> dict[str, Any]:
    repos = discover_repos(base_path, max_depth=max_depth, require_git=require_git, max_repos=max_repos)
    for repo in extra_repos or []:
        resolved = repo.resolve()
        if resolved not in repos:
            repos.append(resolved)
    return federate(repos[:max_repos], max_repos=max_repos, max_files=max_files, max_bytes_per_file=max_bytes_per_file)


def federate(
    repos: list[Path],
    *,
    max_repos: int = 16,
    max_files: int = 64,
    max_bytes_per_file: int = 262144,
) -> dict[str, Any]:
    if not repos:
        raise ValueError("public federation requires explicit repositories or an explicit base path")
    if len(repos) > max_repos:
        raise ValueError(f"too many repositories: {len(repos)} > {max_repos}")
    results = []
    for repo in repos:
        root = repo.resolve()
        try:
            inventory = scan_repository_surfaces(root, max_files=max_files, max_bytes_per_file=max_bytes_per_file)
            status = "ok" if inventory["surface_count"] else "no_surfaces"
            error = None
        except Exception as exc:
            inventory = None
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
        results.append({"repo_name": root.name, "repo_path": str(root), "status": status, "error": error, "inventory": inventory})
    return {
        "schema_id": FEDERATION_REPORT_SCHEMA_ID,
        "created_at": _utc_now(),
        "repo_count": len(results),
        "ok_count": sum(1 for item in results if item["status"] == "ok"),
        "results": results,
        "limits": {"max_repos": max_repos, "max_files": max_files, "max_bytes_per_file": max_bytes_per_file},
        "side_effect_boundary": _side_effect_boundary(),
    }


def discover_repos(base_path: Path, *, max_depth: int = 1, require_git: bool = True, max_repos: int = 16) -> list[Path]:
    base = base_path.resolve()
    if not base.exists() or not base.is_dir():
        raise FileNotFoundError(f"base path does not exist or is not a directory: {base}")
    repos: list[Path] = []
    for candidate in sorted(base.iterdir()):
        if len(repos) >= max_repos:
            break
        if candidate.is_symlink() or not candidate.is_dir() or candidate.name.startswith("."):
            continue
        if require_git and not (candidate / ".git").exists():
            continue
        if any((candidate / name).exists() for name in ("AGENTS.md", "CLAUDE.md", "README.md", "SKILL.md", "mcp.json")):
            repos.append(candidate.resolve())
        if max_depth > 1:
            for nested in sorted(candidate.iterdir()):
                if len(repos) >= max_repos:
                    break
                if nested.is_symlink() or not nested.is_dir() or nested.name.startswith("."):
                    continue
                if require_git and not (nested / ".git").exists():
                    continue
                if any((nested / name).exists() for name in ("AGENTS.md", "CLAUDE.md", "README.md", "SKILL.md", "mcp.json")):
                    repos.append(nested.resolve())
    return repos


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_access_performed": False,
        "provider_or_model_call_performed": False,
        "runtime_or_adapter_executed": False,
        "target_file_written": False,
        "public_write_performed": False,
        "scheduler_or_daemon_started": False,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
