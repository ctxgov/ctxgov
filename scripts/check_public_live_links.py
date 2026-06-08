#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    required_phrases: tuple[str, ...] = ()


def build_targets(release_tag: str) -> list[Target]:
    release_phrases = (release_tag, "Auto-Publish Research")
    if release_tag == "v0.6.12":
        release_phrases = (release_tag, "Live Link Verifier")
    return [
        Target("ctxgov_pages", "https://ctxgov.github.io/ctxgov/", ("CtxGov", "Reviewer Mode")),
        Target("ctxgov_current_release", f"https://github.com/ctxgov/ctxgov/releases/tag/{release_tag}", release_phrases),
        Target("ctxgov_previous_release", "https://github.com/ctxgov/ctxgov/releases/tag/v0.6.11", ("v0.6.11", "Public Surface Hardening")),
        Target("ascr_repo", "https://github.com/ctxgov/ascr", ("Agent State", "Context")),
        Target("agent_context_evals_release", "https://github.com/ctxgov/agent-context-evals/releases/tag/v0.8.0", ("v0.8.0", "Eval Hardening")),
    ]


def fetch_url(url: str, timeout: float) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "ctxgov-live-link-verifier/0.6.13"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(300_000).decode("utf-8", errors="replace")
        return int(response.status), body


def check_targets(
    targets: list[Target],
    *,
    timeout: float,
    fetcher: Callable[[str, float], tuple[int, str]] = fetch_url,
) -> dict:
    checks = []
    for target in targets:
        issue = None
        status = None
        phrase_results: dict[str, bool] = {}
        try:
            status, body = fetcher(target.url, timeout)
            phrase_results = {phrase: phrase in body for phrase in target.required_phrases}
            if status != 200:
                issue = f"http_status_{status}"
            elif not all(phrase_results.values()):
                missing = [phrase for phrase, found in phrase_results.items() if not found]
                issue = "missing_required_phrase:" + ",".join(missing)
        except Exception as exc:  # pragma: no cover - exercised by caller with real network
            issue = type(exc).__name__ + ":" + str(exc)
        checks.append(
            {
                "name": target.name,
                "url": target.url,
                "http_status": status,
                "required_phrases": phrase_results,
                "status": "pass" if issue is None else "fail",
                "issue": issue,
            }
        )
    return {
        "schema": "ctxgov.public_live_link_verification.v0",
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "target_count": len(checks),
        "checks": checks,
        "claim_boundary": {
            "public_benchmark_claim": False,
            "security_claim": False,
            "provider_model_call": False,
            "adoption_claim": False,
            "package_publication": False,
            "hosted_runtime_change": False,
            "live_adapter_claim": False,
            "cli_beta_claim": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify public CtxGov links after offline release checks pass.")
    parser.add_argument("--release-tag", default="v0.6.13-auto-publish-research")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args(argv)

    report = check_targets(build_targets(args.release_tag), timeout=args.timeout)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
