"""Decision v2 contract — three-axis decision model with replay support.

axes: Effect × Evaluation × Enforcement
- Effect: what the policy says should happen (ALLOW, REVIEW, DENY, etc.)
- Evaluation: whether the evaluation was complete (COMPLETE, DEGRADED, etc.)
- Enforcement: whether the decision was actually enforced (NOT_APPLIED, APPLIED, etc.)

Every decision carries policy bundle digest, input digest, and evaluator
version so the same result can be replayed and verified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from .canonicalization import domain_digest
from .reason_codes import (
    DECISION_CONTRACT_VERSION,
    obligations_for_findings,
    reason_code_for_finding_type,
    REASON_CODES,
    ReasonCode,
)


_EFFECTS = frozenset({"ALLOW", "ALLOW_WITH_OBLIGATIONS", "REVIEW", "QUARANTINE", "DENY"})
_EVALUATION_STATUSES = frozenset({"COMPLETE", "DEGRADED", "INDETERMINATE", "ERROR"})
_ENFORCEMENT_RESULTS = frozenset({"NOT_APPLIED", "APPLIED", "BYPASSED", "FAILED"})


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _digest_input(*parts: str) -> str:
    seed = b"ctxgov:decision:v2\0" + _canonical_json(list(parts)).encode("utf-8")
    return hashlib.sha256(seed).hexdigest()


def _jcs_digest(decision: "DecisionV2") -> str:
    """JCS (RFC 8785) domain-separated digest for cross-language replay.

    Unlike the legacy ``deterministic_digest`` (which uses
    ``ensure_ascii=True`` JSON), this digest is stable across language
    runtimes per ADR-0010. Both fields are emitted during the migration
    window; new code SHOULD prefer ``jcs_digest``.
    """
    payload = {
        "effect": decision.effect,
        "evaluation_status": decision.evaluation_status,
        "enforcement_result": decision.enforcement_result,
        "reason_codes": sorted(decision.reason_codes),
        "input_digest": decision.input_digest,
        "policy_bundle_digest": decision.policy_bundle_digest,
        "evaluator_version": decision.evaluator_version,
    }
    return domain_digest("ctxgov:decision:v2", payload)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class DecisionV2:
    decision_id: str
    effect: str
    evaluation_status: str
    enforcement_result: str
    reason_codes: list[str]
    obligations: list[str]
    policy_bundle_id: str
    policy_bundle_revision: str
    policy_bundle_digest: str
    input_digest: str
    evaluator_version: str
    evidence_refs: list[str]
    valid_until: str | None
    findings: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.effect not in _EFFECTS:
            raise ValueError(f"effect must be one of {sorted(_EFFECTS)}, got {self.effect!r}")
        if self.evaluation_status not in _EVALUATION_STATUSES:
            raise ValueError(f"evaluation_status must be one of {sorted(_EVALUATION_STATUSES)}, got {self.evaluation_status!r}")
        if self.enforcement_result not in _ENFORCEMENT_RESULTS:
            raise ValueError(f"enforcement_result must be one of {sorted(_ENFORCEMENT_RESULTS)}, got {self.enforcement_result!r}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": DECISION_CONTRACT_VERSION,
            "decision_id": self.decision_id,
            "effect": self.effect,
            "evaluation": {
                "status": self.evaluation_status,
                "completed_checks": ["semantic_diff", "policy"],
                "missing_evidence": [],
                "errors": [],
                "retryable": self.evaluation_status in {"DEGRADED", "ERROR"},
            },
            "enforcement": {
                "mode": "SHADOW" if self.enforcement_result == "NOT_APPLIED" else "DIRECT",
                "result": self.enforcement_result,
                "bypass_ref": None,
            },
            "reason_codes": self.reason_codes,
            "obligations": self.obligations,
            "policy_bundle": {
                "id": self.policy_bundle_id,
                "revision": self.policy_bundle_revision,
                "digest": self.policy_bundle_digest,
                "entrypoint": "ctxgov/decision",
            },
            "input_digest": self.input_digest,
            "evaluator": {
                "version": self.evaluator_version,
                "config_digest": hashlib.sha256(
                    _canonical_json({"evaluator_version": self.evaluator_version}).encode()
                ).hexdigest(),
            },
            "evidence_refs": self.evidence_refs,
            "valid_until": self.valid_until,
            "findings": self.findings,
            "created_at": self.created_at,
            "deterministic_digest": _digest_input(
                self.input_digest,
                self.policy_bundle_digest,
                self.evaluator_version,
                _canonical_json(sorted(self.reason_codes)),
            ),
            "jcs_digest": _jcs_digest(self),
        }


def build_decision_v2(
    report: dict[str, Any],
    *,
    policy_bundle_id: str = "ctxgov-local",
    policy_bundle_revision: str = "local:0",
    policy_bundle_digest: str = "",
    evaluator_version: str = "ctxgov-core/0.6.13",
    enforcement_result: str = "NOT_APPLIED",
    valid_until: str | None = None,
) -> DecisionV2:
    findings = report.get("findings", [])
    finding_count = len(findings)
    severities = [str(f.get("severity", "low")) for f in findings]

    if any(s in {"critical", "high"} for s in severities):
        effect = "REVIEW"
    elif any(s == "medium" for s in severities):
        effect = "REVIEW"
    elif finding_count == 0:
        effect = "ALLOW"
    else:
        effect = "REVIEW"

    has_critical_or_high = any(s in {"critical", "high"} for s in severities)
    if has_critical_or_high:
        evaluation_status = "COMPLETE" if all(s != "info" for s in severities) else "DEGRADED"
    else:
        evaluation_status = "COMPLETE"

    reason_codes_list = list({
        reason_code_for_finding_type(str(f.get("finding_type", "")))
        for f in findings
    })
    if not reason_codes_list:
        reason_codes_list.append("SEMANTIC_RISK_UNCERTAIN")

    obligations = obligations_for_findings(findings)

    input_data: list[dict[str, str]] = [
        {"source_ref": str(f.get("source_ref", "")), "finding_type": str(f.get("finding_type", ""))}
        for f in findings
    ]
    input_digest = _digest_input(_canonical_json(input_data))

    evidence_refs = [str(f.get("finding_id", "")) for f in findings]

    created_at = _utc_now()
    decision_id = f"decision_{hashlib.sha256(f'{input_digest}:{policy_bundle_digest}:{evaluator_version}:{created_at}'.encode()).hexdigest()[:16]}"

    return DecisionV2(
        decision_id=decision_id,
        effect=effect,
        evaluation_status=evaluation_status,
        enforcement_result=enforcement_result,
        reason_codes=reason_codes_list,
        obligations=obligations,
        policy_bundle_id=policy_bundle_id,
        policy_bundle_revision=policy_bundle_revision,
        policy_bundle_digest=policy_bundle_digest,
        input_digest=input_digest,
        evaluator_version=evaluator_version,
        evidence_refs=evidence_refs,
        valid_until=valid_until,
        findings=findings,
        created_at=created_at,
    )
