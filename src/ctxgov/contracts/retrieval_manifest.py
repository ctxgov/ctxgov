"""RetrievalManifest v1 contract — honest candidate-universe visibility.

Per ADR-0018: a RetrievalManifest must declare whether the adapter
observed the COMPLETE candidate universe, only a PARTIAL slice, or
could not determine coverage (UNKNOWN). The ``omitted`` list only
covers observed candidates; absence from ``omitted`` when status is
PARTIAL or UNKNOWN does not mean the system saw and rejected the item.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonicalization import domain_digest

__all__ = [
    "RetrievalManifest",
    "SelectedRef",
    "OmittedRef",
    "build_retrieval_manifest",
    "RETRIEVAL_MANIFEST_CONTRACT_VERSION",
    "RETRIEVAL_MANIFEST_DOMAIN",
]

RETRIEVAL_MANIFEST_CONTRACT_VERSION = "ctxgov.retrieval-manifest/v1"
RETRIEVAL_MANIFEST_DOMAIN = "ctxgov:retrieval-manifest:v1"

_CANDIDATE_UNIVERSE_STATUSES = frozenset({"COMPLETE", "PARTIAL", "UNKNOWN"})
_OMIT_REASONS = frozenset({
    "BELOW_BACKEND_THRESHOLD",
    "FILTERED_BY_SCOPE",
    "FILTERED_BY_PRINCIPAL",
    "REVOKED",
    "QUARANTINED",
    "STALE",
    "CONTRADICTED",
    "OTHER",
})


@dataclass(frozen=True)
class SelectedRef:
    revision_ref: str
    rank: int | None
    score: float | None


@dataclass(frozen=True)
class OmittedRef:
    revision_ref: str
    reason: str


@dataclass(frozen=True)
class RetrievalManifest:
    """A retrieval result set with explicit candidate-universe visibility."""

    query_ref: str
    backend_ref: str
    candidate_universe_status: str
    selected: tuple[SelectedRef, ...]
    omitted: tuple[OmittedRef, ...]
    unknown_candidate_count: int | None
    backend_receipt_ref: str
    observed_at: str

    def __post_init__(self) -> None:
        if self.candidate_universe_status not in _CANDIDATE_UNIVERSE_STATUSES:
            raise ValueError(
                f"candidate_universe_status must be one of "
                f"{sorted(_CANDIDATE_UNIVERSE_STATUSES)}, "
                f"got {self.candidate_universe_status!r}"
            )
        for ref in self.omitted:
            if ref.reason not in _OMIT_REASONS:
                raise ValueError(
                    f"omit reason must be one of {sorted(_OMIT_REASONS)}, "
                    f"got {ref.reason!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": RETRIEVAL_MANIFEST_CONTRACT_VERSION,
            "query_ref": self.query_ref,
            "backend_ref": self.backend_ref,
            "candidate_universe_status": self.candidate_universe_status,
            "selected": [
                {
                    "revision_ref": s.revision_ref,
                    "rank": s.rank,
                    "score": s.score,
                }
                for s in self.selected
            ],
            "omitted": [
                {"revision_ref": o.revision_ref, "reason": o.reason}
                for o in self.omitted
            ],
            "unknown_candidate_count": self.unknown_candidate_count,
            "backend_receipt_ref": self.backend_receipt_ref,
            "observed_at": self.observed_at,
            "manifest_digest": domain_digest(
                RETRIEVAL_MANIFEST_DOMAIN,
                {
                    "query_ref": self.query_ref,
                    "backend_ref": self.backend_ref,
                    "candidate_universe_status": self.candidate_universe_status,
                    "selected_revision_refs": [s.revision_ref for s in self.selected],
                    "omitted_revision_refs": [o.revision_ref for o in self.omitted],
                },
            ),
        }


def build_retrieval_manifest(
    *,
    query_ref: str,
    backend_ref: str,
    candidate_universe_status: str,
    selected: list[dict[str, Any]],
    omitted: list[dict[str, Any]],
    unknown_candidate_count: int | None,
    backend_receipt_ref: str,
    observed_at: str,
) -> RetrievalManifest:
    """Build a RetrievalManifest from raw dicts, validating enums."""
    sel = tuple(
        SelectedRef(
            revision_ref=s["revision_ref"],
            rank=s.get("rank"),
            score=s.get("score"),
        )
        for s in selected
    )
    om = tuple(
        OmittedRef(revision_ref=o["revision_ref"], reason=o["reason"])
        for o in omitted
    )
    return RetrievalManifest(
        query_ref=query_ref,
        backend_ref=backend_ref,
        candidate_universe_status=candidate_universe_status,
        selected=sel,
        omitted=om,
        unknown_candidate_count=unknown_candidate_count,
        backend_receipt_ref=backend_receipt_ref,
        observed_at=observed_at,
    )
