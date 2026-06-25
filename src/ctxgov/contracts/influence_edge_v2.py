"""InfluenceEdge v2 contract — four-field evidence semantics.

Per ADR-0017: every influence edge separates four independent fields:
evidence_class (source type), sensor_integrity (trustworthiness),
correlation_method (strength of link), calibrated_score (confidence).
Weak correlation methods may never promote an edge to OBSERVED; observed
does not imply sensor trustworthiness or causation; calibrated_score may
not default to 1.0.

This contract is the type-level foundation for WP-5 (Incident Forensics
influence graph). The graph traversal layer is implemented separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonicalization import domain_digest

__all__ = [
    "InfluenceEdgeV2",
    "build_influence_edge",
    "EVIDENCE_CLASSES",
    "SENSOR_INTEGRITY_LEVELS",
    "CORRELATION_METHODS",
    "INFLUENCE_EDGE_CONTRACT_VERSION",
    "INFLUENCE_EDGE_DOMAIN",
]

INFLUENCE_EDGE_CONTRACT_VERSION = "ctxgov.influence-edge/v2"
INFLUENCE_EDGE_DOMAIN = "ctxgov:influence-edge:v2"

EVIDENCE_CLASSES = frozenset({"OBSERVED", "ASSERTED", "INFERRED"})
SENSOR_INTEGRITY_LEVELS = frozenset({
    "VERIFIED",
    "UNVERIFIED",
    "COMPROMISED",
    "UNKNOWN",
})
# Ordered strong-to-weak; weak methods may not promote an edge to OBSERVED.
CORRELATION_METHODS = frozenset({
    "EXACT_ID",
    "EXPLICIT_LINK",
    "TRACE_LINK",
    "TIME_SCOPE",
    "CONTENT_FINGERPRINT",
})
_WEAK_METHODS = frozenset({"TIME_SCOPE", "CONTENT_FINGERPRINT"})


@dataclass(frozen=True)
class InfluenceEdgeV2:
    """A single edge in the influence graph with honest evidence semantics."""

    from_ref: str
    relation: str
    to_ref: str
    evidence_class: str
    sensor_integrity: str
    correlation_method: str
    calibrated_score: float | None
    evidence_refs: tuple[str, ...]
    telemetry_gaps: tuple[str, ...]
    observed_at: str
    ingested_at: str

    def __post_init__(self) -> None:
        if self.evidence_class not in EVIDENCE_CLASSES:
            raise ValueError(
                f"evidence_class must be one of {sorted(EVIDENCE_CLASSES)}, "
                f"got {self.evidence_class!r}"
            )
        if self.sensor_integrity not in SENSOR_INTEGRITY_LEVELS:
            raise ValueError(
                f"sensor_integrity must be one of "
                f"{sorted(SENSOR_INTEGRITY_LEVELS)}, "
                f"got {self.sensor_integrity!r}"
            )
        if self.correlation_method not in CORRELATION_METHODS:
            raise ValueError(
                f"correlation_method must be one of "
                f"{sorted(CORRELATION_METHODS)}, "
                f"got {self.correlation_method!r}"
            )
        # Weak correlation methods may not claim OBSERVED evidence class.
        if self.correlation_method in _WEAK_METHODS and self.evidence_class == "OBSERVED":
            raise ValueError(
                f"correlation_method {self.correlation_method!r} is too weak "
                f"to support evidence_class OBSERVED; use INFERRED"
            )
        # calibrated_score may not default to 1.0 (ADR-0017 v1.1 bug fix).
        if self.calibrated_score is not None:
            if not (0.0 <= self.calibrated_score <= 1.0):
                raise ValueError(
                    f"calibrated_score must be in [0.0, 1.0], "
                    f"got {self.calibrated_score}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": INFLUENCE_EDGE_CONTRACT_VERSION,
            "from_ref": self.from_ref,
            "relation": self.relation,
            "to_ref": self.to_ref,
            "evidence_class": self.evidence_class,
            "sensor_integrity": self.sensor_integrity,
            "correlation_method": self.correlation_method,
            "calibrated_score": self.calibrated_score,
            "evidence_refs": list(self.evidence_refs),
            "telemetry_gaps": list(self.telemetry_gaps),
            "observed_at": self.observed_at,
            "ingested_at": self.ingested_at,
            "edge_digest": domain_digest(
                INFLUENCE_EDGE_DOMAIN,
                {
                    "from_ref": self.from_ref,
                    "relation": self.relation,
                    "to_ref": self.to_ref,
                    "evidence_class": self.evidence_class,
                    "correlation_method": self.correlation_method,
                },
            ),
        }


def build_influence_edge(
    *,
    from_ref: str,
    relation: str,
    to_ref: str,
    evidence_class: str,
    sensor_integrity: str,
    correlation_method: str,
    calibrated_score: float | None,
    evidence_refs: list[str],
    telemetry_gaps: list[str],
    observed_at: str,
    ingested_at: str,
) -> InfluenceEdgeV2:
    """Build an InfluenceEdgeV2, enforcing ADR-0017 semantics."""
    return InfluenceEdgeV2(
        from_ref=from_ref,
        relation=relation,
        to_ref=to_ref,
        evidence_class=evidence_class,
        sensor_integrity=sensor_integrity,
        correlation_method=correlation_method,
        calibrated_score=calibrated_score,
        evidence_refs=tuple(evidence_refs),
        telemetry_gaps=tuple(telemetry_gaps),
        observed_at=observed_at,
        ingested_at=ingested_at,
    )
