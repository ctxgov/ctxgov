"""RollbackVerificationResult v1 contract — honest rollback verification.

Per ADR-0019: a rollback result must be VERIFIED / PARTIAL / FAILED /
NOT_VERIFIABLE over a required checks list. Any check that cannot be
verified must block the "rollback fully verified" claim. This is the
cross-backend differentiator versus single-cloud rollback APIs (which
prove the pointer moved but not that caches/sessions/projections are
invalidated).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonicalization import domain_digest

__all__ = [
    "RollbackVerificationResult",
    "RollbackCheck",
    "build_rollback_verification",
    "ROLLBACK_RESULTS",
    "ROLLBACK_CHECK_STATUSES",
    "REQUIRED_CHECK_NAMES",
    "ROLLBACK_VERIFICATION_CONTRACT_VERSION",
    "ROLLBACK_VERIFICATION_DOMAIN",
]

ROLLBACK_VERIFICATION_CONTRACT_VERSION = "ctxgov.rollback-verification/v1"
ROLLBACK_VERIFICATION_DOMAIN = "ctxgov:rollback-verification:v1"

ROLLBACK_RESULTS = frozenset({"VERIFIED", "PARTIAL", "FAILED", "NOT_VERIFIABLE"})
ROLLBACK_CHECK_STATUSES = frozenset({"PASS", "FAIL", "NOT_VERIFIABLE"})

# Required checks per ADR-0019. A rollback may be called VERIFIED only
# when every required check is PASS. Any NOT_VERIFIABLE forces PARTIAL;
# any FAIL forces FAILED.
REQUIRED_CHECK_NAMES = frozenset({
    "current_pointer",
    "old_revision_revoked",
    "retrieval_probe_excludes_old",
    "projection_rebuilt",
    "cache_invalidated",
    "active_sessions_refreshed",
    "regression_eval",
})


@dataclass(frozen=True)
class RollbackCheck:
    name: str
    status: str
    detail: str = ""

    def __post_init__(self) -> None:
        if self.status not in ROLLBACK_CHECK_STATUSES:
            raise ValueError(
                f"check status must be one of {sorted(ROLLBACK_CHECK_STATUSES)}, "
                f"got {self.status!r}"
            )
        if self.name not in REQUIRED_CHECK_NAMES:
            raise ValueError(
                f"check name must be one of {sorted(REQUIRED_CHECK_NAMES)}, "
                f"got {self.name!r}"
            )


@dataclass(frozen=True)
class RollbackVerificationResult:
    """Result of verifying that a rollback took full effect."""

    result: str
    target_state_ref: str
    expected_revision_ref: str
    checks: tuple[RollbackCheck, ...]
    evidence_refs: tuple[str, ...]
    verified_at: str

    def __post_init__(self) -> None:
        if self.result not in ROLLBACK_RESULTS:
            raise ValueError(
                f"result must be one of {sorted(ROLLBACK_RESULTS)}, "
                f"got {self.result!r}"
            )
        # A VERIFIED result requires every required check to be PASS.
        if self.result == "VERIFIED":
            check_names = {c.name for c in self.checks}
            missing = REQUIRED_CHECK_NAMES - check_names
            if missing:
                raise ValueError(
                    f"VERIFIED result is missing required checks: {sorted(missing)}"
                )
            for c in self.checks:
                if c.status != "PASS":
                    raise ValueError(
                        f"VERIFIED result has non-PASS check {c.name!r}: {c.status}"
                    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": ROLLBACK_VERIFICATION_CONTRACT_VERSION,
            "result": self.result,
            "target_state_ref": self.target_state_ref,
            "expected_revision_ref": self.expected_revision_ref,
            "checks": [
                {"name": c.name, "status": c.status, "detail": c.detail}
                for c in self.checks
            ],
            "evidence_refs": list(self.evidence_refs),
            "verified_at": self.verified_at,
            "verification_digest": domain_digest(
                ROLLBACK_VERIFICATION_DOMAIN,
                {
                    "target_state_ref": self.target_state_ref,
                    "expected_revision_ref": self.expected_revision_ref,
                    "result": self.result,
                    "check_results": [
                        {"name": c.name, "status": c.status}
                        for c in self.checks
                    ],
                },
            ),
        }


def build_rollback_verification(
    *,
    target_state_ref: str,
    expected_revision_ref: str,
    checks: list[dict[str, str]],
    evidence_refs: list[str],
    verified_at: str,
) -> RollbackVerificationResult:
    """Build a RollbackVerificationResult, computing the honest result.

    The ``result`` is derived from the checks:
    - Any FAIL → FAILED
    - Else any NOT_VERIFIABLE → NOT_VERIFIABLE (or PARTIAL if all required checks present)
    - Else all required checks PASS → VERIFIED
    - Else PARTIAL (some required checks missing or not verifiable)
    """
    parsed = tuple(
        RollbackCheck(
            name=c["name"],
            status=c["status"],
            detail=c.get("detail", ""),
        )
        for c in checks
    )

    has_fail = any(c.status == "FAIL" for c in parsed)
    not_verifiable = [c for c in parsed if c.status == "NOT_VERIFIABLE"]
    check_names = {c.name for c in parsed}
    missing = REQUIRED_CHECK_NAMES - check_names

    if has_fail:
        result = "FAILED"
    elif not_verifiable or missing:
        result = "PARTIAL"
    elif all(c.status == "PASS" for c in parsed):
        result = "VERIFIED"
    else:
        result = "PARTIAL"

    return RollbackVerificationResult(
        result=result,
        target_state_ref=target_state_ref,
        expected_revision_ref=expected_revision_ref,
        checks=parsed,
        evidence_refs=tuple(evidence_refs),
        verified_at=verified_at,
    )
