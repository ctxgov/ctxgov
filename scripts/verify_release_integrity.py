#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import urllib.request


SCHEMA_ID = "ctxgov.release-integrity-verification-receipt/v0"
FIELDS = ("tag_target", "release_notes_sha256", "pages_url", "rollback_target")


def main() -> int:
    args = build_parser().parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    receipt = verify_integrity(manifest, live_fetch=args.live_fetch, allow_live_fetch=args.allow_live_fetch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify release integrity values after owner-approved publication.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-fetch", action="store_true", help="Request post-approval live fetch verification.")
    parser.add_argument("--allow-live-fetch", action="store_true", help="Explicitly allow network fetch after owner-approved publication.")
    return parser


def verify_integrity(manifest: dict[str, Any], live_fetch: bool = False, allow_live_fetch: bool = False) -> dict[str, Any]:
    expected = manifest.get("expected", {})
    observed = manifest.get("observed", {})
    checks = []
    for field in FIELDS:
        expected_value = expected.get(field)
        observed_value = observed.get(field)
        checks.append(
            {
                "field": field,
                "status": "pass" if expected_value == observed_value else "fail",
                "expected": expected_value,
                "observed": observed_value,
            }
        )
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    post_approval_live_fetch: dict[str, Any] = {
        "required_after_owner_approved_publication": True,
        "requested": live_fetch,
        "approval_required": live_fetch and not allow_live_fetch,
        "executed": False,
        "result": "not_requested" if not live_fetch else "approval_required_not_executed",
    }
    remote_fetch_executed = False
    if live_fetch and not allow_live_fetch:
        status = "blocked_approval_required"
    elif live_fetch and allow_live_fetch:
        post_approval_live_fetch = fetch_live_pages(expected.get("pages_url") or observed.get("pages_url"))
        remote_fetch_executed = post_approval_live_fetch["executed"]
        if post_approval_live_fetch["status"] != "pass":
            status = "fail"
    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "candidate_version": manifest.get("candidate_version"),
        "checks": checks,
        "post_approval_live_fetch": post_approval_live_fetch,
        "public_write_executed": False,
        "remote_fetch_executed": remote_fetch_executed,
        "note": "This verifier compares supplied owner-approved values by default. Live fetch requires explicit owner-approved allowance.",
    }


def fetch_live_pages(url: str | None) -> dict[str, Any]:
    if not url:
        return {
            "status": "fail",
            "required_after_owner_approved_publication": True,
            "requested": True,
            "approval_required": False,
            "executed": False,
            "result": "missing_pages_url",
        }
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "ctxgov-release-integrity-verifier"})
        with urllib.request.urlopen(request, timeout=15) as response:
            status_code = response.status
    except Exception as exc:  # pragma: no cover - only used after explicit live approval.
        return {
            "status": "fail",
            "required_after_owner_approved_publication": True,
            "requested": True,
            "approval_required": False,
            "executed": True,
            "url": url,
            "result": "fetch_failed",
            "error": str(exc),
        }
    return {
        "status": "pass" if 200 <= status_code < 400 else "fail",
        "required_after_owner_approved_publication": True,
        "requested": True,
        "approval_required": False,
        "executed": True,
        "url": url,
        "http_status": status_code,
        "result": "fetched",
    }


if __name__ == "__main__":
    raise SystemExit(main())
