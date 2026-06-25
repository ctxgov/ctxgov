"""CtxGov contracts package — versioned, replay-verifiable data contracts."""

from .canonicalization import canonicalize, canonicalize_bytes, domain_digest

CONTRACT_VERSIONS = {
    "decision": "ctxgov.decision/v2",
    "state_revision": "ctxgov.state-revision/v2",
    "retrieval_manifest": "ctxgov.retrieval-manifest/v1",
    "influence_edge": "ctxgov.influence-edge/v2",
    "rollback_verification": "ctxgov.rollback-verification/v1",
}

__all__ = [
    "CONTRACT_VERSIONS",
    "canonicalize",
    "canonicalize_bytes",
    "domain_digest",
]
