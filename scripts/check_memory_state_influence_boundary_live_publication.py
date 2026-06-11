#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PAGE = Path("docs/memory-state-influence-boundary-try-in-5-minutes.html")
PUBLIC_URL = "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html"
REQUIRED_PHRASES = [
    "Local Memory State Influence Boundary Report",
    "python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/",
    "python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md",
    "python3 scripts/check_memory_state_influence_boundary_final_preflight.py",
    "not a provider integration",
    "compatibility matrix",
    "benchmark",
]


def check_memory_state_influence_boundary_live_publication(
    root: Path = ROOT,
    *,
    live: bool = False,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    local_page = root / PUBLIC_PAGE
    local_status: dict[str, Any] = {"exists": local_page.exists(), "missing_phrases": []}
    if local_page.exists():
        text = local_page.read_text(encoding="utf-8")
        local_status["missing_phrases"] = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
        for phrase in local_status["missing_phrases"]:
            errors.append(f"local page missing phrase: {phrase}")
    else:
        errors.append(f"missing local page: {PUBLIC_PAGE}")

    live_status: dict[str, Any] = {
        "checked": live,
        "url": PUBLIC_URL,
        "http_status": None,
        "missing_phrases": [],
        "error": None,
    }
    if live:
        try:
            with urlopen(PUBLIC_URL, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                live_status["http_status"] = response.status
        except HTTPError as exc:
            live_status["http_status"] = exc.code
            live_status["error"] = str(exc)
            errors.append(f"live fetch failed: {exc}")
            exc.close()
        except (OSError, URLError) as exc:
            live_status["error"] = str(exc)
            errors.append(f"live fetch failed: {exc}")
        else:
            if live_status["http_status"] != 200:
                errors.append(f"live fetch returned HTTP {live_status['http_status']}")
            live_status["missing_phrases"] = [phrase for phrase in REQUIRED_PHRASES if phrase not in body]
            for phrase in live_status["missing_phrases"]:
                errors.append(f"live page missing phrase: {phrase}")

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-live-publication-check/v0",
        "status": "pass_memory_state_influence_boundary_live_publication_check" if not errors else "fail_memory_state_influence_boundary_live_publication_check",
        "public_page": PUBLIC_URL,
        "local_page": str(PUBLIC_PAGE),
        "live_fetch_performed": live,
        "local_status": local_status,
        "live_status": live_status,
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the Memory State Influence Boundary public Pages surface.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    args = parser.parse_args()
    result = check_memory_state_influence_boundary_live_publication(
        args.root,
        live=args.live,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "pass_memory_state_influence_boundary_live_publication_check" else 1


if __name__ == "__main__":
    raise SystemExit(main())
