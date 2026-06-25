"""StateRevision v2 contract — immutable revision with JCS digest.

Per ADR-0003: object identity (StateObject) is separated from revision
(StateRevision). A revision is append-only; the canonical_digest is
computed over the JCS-canonicalized payload with a domain-separation
prefix. The revision_ref is derived deterministically so re-ingesting
identical content is idempotent.

This contract is the type-level foundation for WP-2 (Evidence Core).
The storage layer (CAS + SQLite) is implemented separately.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .canonicalization import canonicalize_bytes, domain_digest

__all__ = [
    "StateRevisionV2",
    "build_state_revision",
    "compute_revision_ref",
    "compute_canonical_digest",
    "STATE_REVISION_DOMAIN",
    "STATE_REVISION_CONTRACT_VERSION",
]

STATE_REVISION_DOMAIN = "ctxgov:state-revision:v2"
STATE_REVISION_CONTRACT_VERSION = "ctxgov.state-revision/v2"

_SIDE_EFFECT_LEVELS = frozenset({
    "read_only",
    "local_write",
    "external_send",
    "deployment_write",
    "destructive",
})

_CONSEQUENCE_CEILINGS = frozenset({
    "requires_human_approval",
    "requires_rollback_plan",
    "requires_sandbox",
    "automatic",
})


@dataclass(frozen=True)
class StateRevisionV2:
    """An immutable revision of a persistent agent state object."""

    state_id: str
    canonical_digest: str
    revision_ref: str
    supersedes_ref: str | None
    payload_ref: str
    writer_ref: str
    approval_required: bool
    capabilities: tuple[str, ...]
    side_effect_level: str
    consequence_ceiling: tuple[str, ...]
    rollback_ref: str | None
    source_refs: tuple[str, ...]
    created_at: str

    def __post_init__(self) -> None:
        if not self.state_id:
            raise ValueError("state_id must be non-empty")
        if self.side_effect_level not in _SIDE_EFFECT_LEVELS:
            raise ValueError(
                f"side_effect_level must be one of {sorted(_SIDE_EFFECT_LEVELS)}, "
                f"got {self.side_effect_level!r}"
            )
        for ceiling in self.consequence_ceiling:
            if ceiling not in _CONSEQUENCE_CEILINGS:
                raise ValueError(
                    f"consequence_ceiling entry must be one of {sorted(_CONSEQUENCE_CEILINGS)}, "
                    f"got {ceiling!r}"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": STATE_REVISION_CONTRACT_VERSION,
            "state_id": self.state_id,
            "revision_ref": self.revision_ref,
            "supersedes": self.supersedes_ref,
            "canonical_digest": self.canonical_digest,
            "payload_ref": self.payload_ref,
            "authority": {
                "writer": self.writer_ref,
                "approval_required": self.approval_required,
            },
            "capabilities": list(self.capabilities),
            "side_effect_level": self.side_effect_level,
            "consequence_ceiling": list(self.consequence_ceiling),
            "rollback_ref": self.rollback_ref,
            "provenance": {"source_refs": list(self.source_refs)},
            "created_at": self.created_at,
        }


def compute_canonical_digest(payload: dict[str, Any]) -> str:
    """Compute the JCS domain-separated canonical digest of a payload."""
    return domain_digest(STATE_REVISION_DOMAIN, payload)


def compute_revision_ref(canonical_digest: str) -> str:
    """Derive the revision_ref from the canonical_digest."""
    if not canonical_digest:
        raise ValueError("canonical_digest must be non-empty")
    return f"urn:ctxgov:revision:{canonical_digest}"


def build_state_revision(
    *,
    state_id: str,
    payload: dict[str, Any],
    payload_ref: str,
    writer_ref: str,
    approval_required: bool,
    capabilities: list[str],
    side_effect_level: str,
    consequence_ceiling: list[str],
    rollback_ref: str | None,
    source_refs: list[str],
    supersedes_ref: str | None,
    created_at: str,
) -> StateRevisionV2:
    """Build a StateRevisionV2 from a payload, computing digests.

    The ``canonical_digest`` is computed over ``payload`` via JCS so that
    identical content always produces the same revision_ref (idempotent
    ingest). ``payload_ref`` is a separate CAS pointer (e.g.
    ``blob://sha256/<digest>``) resolved by the storage layer.
    """
    canonical_digest = compute_canonical_digest(payload)
    revision_ref = compute_revision_ref(canonical_digest)
    return StateRevisionV2(
        state_id=state_id,
        canonical_digest=canonical_digest,
        revision_ref=revision_ref,
        supersedes_ref=supersedes_ref,
        payload_ref=payload_ref,
        writer_ref=writer_ref,
        approval_required=approval_required,
        capabilities=tuple(sorted(capabilities)),
        side_effect_level=side_effect_level,
        consequence_ceiling=tuple(sorted(consequence_ceiling)),
        rollback_ref=rollback_ref,
        source_refs=tuple(source_refs),
        created_at=created_at,
    )
