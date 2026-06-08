#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INTENT = ROOT / "release" / "v0.6.13" / "publication-intent.json"

REQUIRED_INCLUDED = {
    "ctxgov_public_repo_patch",
    "ctxgov_release_tag",
    "ctxgov_github_release",
    "ctxgov_pages",
}

REQUIRED_EXCLUDED = {
    "agent_context_evals_public_repo_patch",
    "org_profile_update",
    "github_issue_or_comment",
    "linkedin_x_manual_post",
}

FORBIDDEN_INCLUDED = REQUIRED_EXCLUDED | {
    "package_publication",
    "provider_model_call",
    "memory_backend_write",
    "hosted_runtime_change",
    "live_adapter_enablement",
}

FORBIDDEN_CLAIMS = {
    "public_benchmark_claim",
    "security_claim",
    "provider_model_call",
    "provider_model_compatibility_claim",
    "adoption_claim",
    "package_publication",
    "hosted_runtime_change",
    "live_adapter_claim",
    "stable_public_spec_claim",
    "cli_beta_claim",
    "memory_backend_write",
    "social_outreach",
    "companion_repo_write",
    "issue_or_comment_write",
}


def validate_publication_intent(intent: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if intent.get("schema") != "ctxgov.publication_intent.v0":
        issues.append(_issue("schema", "unexpected publication intent schema"))
    if intent.get("release") != "v0.6.13":
        issues.append(_issue("release", "release must be v0.6.13"))
    if intent.get("release_tag") != "v0.6.13-auto-publish-research":
        issues.append(_issue("release_tag", "unexpected release tag"))
    if intent.get("status") != "owner_approved_publication_intent":
        issues.append(_issue("status", "intent must record owner-approved publication intent"))

    for field in ("owner_visible_digest_sha256", "owner_packet_v5_digest_sha256"):
        digest = intent.get(field, "")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            issues.append(_issue(field, "digest must be a 64-character lowercase sha256 hex string"))

    included = set(intent.get("included_targets", []))
    excluded = set(intent.get("excluded_targets", []))
    if included != REQUIRED_INCLUDED:
        issues.append(_issue("included_targets", "included targets must match the minimal public release set"))
    if excluded != REQUIRED_EXCLUDED:
        issues.append(_issue("excluded_targets", "excluded targets must match deferred public-write targets"))
    for target in sorted(included & FORBIDDEN_INCLUDED):
        issues.append(_issue("forbidden_included_target", target))

    claim_boundary = intent.get("claim_boundary", {})
    for claim in sorted(FORBIDDEN_CLAIMS):
        if claim_boundary.get(claim) is not False:
            issues.append(_issue("claim_boundary", f"{claim} must be false"))

    policy = intent.get("execution_policy", {})
    for field in (
        "execution_allowed",
        "requires_clean_public_checkout",
        "requires_matching_owner_digest",
        "requires_offline_checks_before_public_write",
        "requires_live_fetch_after_publication",
    ):
        if policy.get(field) is not True:
            issues.append(_issue("execution_policy", f"{field} must be true"))
    if policy.get("execution_performed_by_this_file") is not False:
        issues.append(_issue("execution_policy", "intent file must not claim execution by itself"))

    rollback = intent.get("rollback_targets", {})
    for key in ("repo_patch", "release_tag", "github_release", "pages"):
        if not isinstance(rollback.get(key), str) or not rollback[key].strip():
            issues.append(_issue("rollback_targets", f"{key} must be described"))
    return issues


def main() -> int:
    try:
        intent = json.loads(INTENT.read_text(encoding="utf-8"))
    except Exception as exc:
        report = _report([_issue("load", str(exc))])
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    issues = validate_publication_intent(intent)
    report = _report(issues)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


def _issue(kind: str, detail: str) -> dict[str, str]:
    return {"kind": kind, "detail": detail}


def _report(issues: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "schema": "ctxgov.publication_intent_check.v0",
        "release": "v0.6.13",
        "status": "pass" if not issues else "fail",
        "issue_count": len(issues),
        "issues": issues,
    }


if __name__ == "__main__":
    raise SystemExit(main())
