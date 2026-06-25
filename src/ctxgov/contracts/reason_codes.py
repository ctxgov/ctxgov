"""Reason code registry for CtxGov Decision v2.

Each reason code maps to:
- A semanic boundary it protects (authority, capability, scope, evidence, lifecycle)
- Default severity (informational → enforcement escalates)
- Default obligation (what action to recommend)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DECISION_CONTRACT_VERSION = "ctxgov.decision/v2"


@dataclass(frozen=True)
class ReasonCode:
    code: str
    boundary: str
    description: str
    default_obligations: list[str]


REASON_CODES: dict[str, ReasonCode] = {
    "CAPABILITY_ESCALATION": ReasonCode(
        code="CAPABILITY_ESCALATION",
        boundary="capability",
        description="Capability expanded from read/plan to write/deploy/delete/payment.",
        default_obligations=["require_human_approval", "attach_rollback_plan"],
    ),
    "SCOPE_EXPANSION": ReasonCode(
        code="SCOPE_EXPANSION",
        boundary="scope",
        description="Scope expanded (project→user, user→system, project→tenant) or inherited scope widened.",
        default_obligations=["require_owner_approval"],
    ),
    "MISSING_APPROVAL": ReasonCode(
        code="MISSING_APPROVAL",
        boundary="authority",
        description="High-risk mutation lacks an approval gate or review decision.",
        default_obligations=["require_human_approval", "attach_rollback_plan"],
    ),
    "MISSING_SOURCE_COVERAGE": ReasonCode(
        code="MISSING_SOURCE_COVERAGE",
        boundary="evidence",
        description="Source reference coverage is below policy threshold.",
        default_obligations=["quarantine_until_sources_provided"],
    ),
    "MISSING_ROLLBACK": ReasonCode(
        code="MISSING_ROLLBACK",
        boundary="lifecycle",
        description="High-risk revision has no rollback path or verification plan.",
        default_obligations=["attach_rollback_plan", "require_human_approval"],
    ),
    "REVOKED_REVISION_SELECTED": ReasonCode(
        code="REVOKED_REVISION_SELECTED",
        boundary="lifecycle",
        description="A revoked or quarantined revision was selected for retrieval or context assembly.",
        default_obligations=["deny", "invalidate_cache"],
    ),
    "POLICY_BUNDLE_STALE": ReasonCode(
        code="POLICY_BUNDLE_STALE",
        boundary="policy",
        description="Policy decision point has only an expired or stale policy bundle available.",
        default_obligations=["degrade_decision", "emit_degraded_receipt"],
    ),
    "SEMANTIC_RISK_UNCERTAIN": ReasonCode(
        code="SEMANTIC_RISK_UNCERTAIN",
        boundary="evidence",
        description="Semantic detector found a signal but confidence or evidence is insufficient for a hard decision.",
        default_obligations=["review", "do_not_deny"],
    ),
    "AUTHORITY_ESCALATION": ReasonCode(
        code="AUTHORITY_ESCALATION",
        boundary="authority",
        description="Surface authority escalated (read_only→write, write→block, none→override).",
        default_obligations=["require_human_approval"],
    ),
    "AUTHORITY_SHIFT": ReasonCode(
        code="AUTHORITY_SHIFT",
        boundary="authority",
        description="Surface authority shifted (approval gate removed, effect downgraded).",
        default_obligations=["review"],
    ),
    "LIFECYCLE_CHANGE": ReasonCode(
        code="LIFECYCLE_CHANGE",
        boundary="lifecycle",
        description="Surface lifecycle changed (expiry removed, revokability removed, state shifted).",
        default_obligations=["review"],
    ),
    "SENSITIVITY_INCREASE": ReasonCode(
        code="SENSITIVITY_INCREASE",
        boundary="evidence",
        description="Surface sensitivity classification increased.",
        default_obligations=["review"],
    ),
    "SURFACE_ADDED": ReasonCode(
        code="SURFACE_ADDED",
        boundary="structure",
        description="A new agent surface was added to the workspace.",
        default_obligations=["review"],
    ),
    "SURFACE_REMOVED": ReasonCode(
        code="SURFACE_REMOVED",
        boundary="structure",
        description="An agent surface was removed from the workspace.",
        default_obligations=["review"],
    ),
}


def reason_code_for_finding_type(finding_type: str) -> str:
    mapping: dict[str, str] = {
        "authority_escalation": "AUTHORITY_ESCALATION",
        "authority_shift": "AUTHORITY_SHIFT",
        "capability_expansion": "CAPABILITY_ESCALATION",
        "scope_expansion": "SCOPE_EXPANSION",
        "lifecycle_change": "LIFECYCLE_CHANGE",
        "sensitivity_increase": "SENSITIVITY_INCREASE",
        "surface_added": "SURFACE_ADDED",
        "surface_removed": "SURFACE_REMOVED",
        "evidence_provenance_drop": "MISSING_SOURCE_COVERAGE",
        "structural_shift": "SEMANTIC_RISK_UNCERTAIN",
    }
    return mapping.get(finding_type, "SEMANTIC_RISK_UNCERTAIN")


def obligations_for_findings(findings: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    obligations: list[str] = []
    for finding in findings:
        ft = str(finding.get("finding_type", ""))
        rc_code = reason_code_for_finding_type(ft)
        rc = REASON_CODES.get(rc_code)
        if rc:
            for obl in rc.default_obligations:
                if obl not in seen:
                    seen.add(obl)
                    obligations.append(obl)
    if not obligations:
        obligations.append("review")
    return obligations
