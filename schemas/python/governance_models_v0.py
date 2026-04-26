from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ScopeKind(str, Enum):
    GLOBAL = "global"
    USER = "user"
    WORKSPACE = "workspace"
    PROJECT = "project"
    THREAD = "thread"
    TASK = "task"
    TURN = "turn"


class SensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class RedactionState(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    FULLY_REDACTED = "fully_redacted"
    WITHHELD = "withheld"


class ClaimStatus(str, Enum):
    RECORDED = "recorded"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    RETRACTED = "retracted"


class EvidenceRelation(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    CONTEXT_ONLY = "context_only"


class EvidenceVerdict(str, Enum):
    SUPPORTED = "supported_by_local_evidence"
    CONTRADICTED = "contradicted_by_local_evidence"
    INSUFFICIENT = "insufficient_local_evidence"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class AuditMethod(str, Enum):
    DETERMINISTIC_LOCAL_EVIDENCE = "deterministic_local_evidence"
    HUMAN_REVIEW = "human_review"
    MODEL_ASSISTED = "model_assisted"


class ReviewState(str, Enum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class AdapterMode(str, Enum):
    DISABLED = "disabled"
    LOCAL = "local"
    REMOTE = "remote"


class PluginKind(str, Enum):
    ANALYZER = "analyzer"
    TRANSFORMER = "transformer"
    PROJECTION = "projection"
    INGEST = "ingest"
    ACTION = "action"


class PluginRuntime(str, Enum):
    DETERMINISTIC_LOCAL = "deterministic-local"
    LOCAL_MODEL = "local-model"
    EXTERNAL_TOOL = "external-tool"


class PluginSideEffectLevel(str, Enum):
    NONE = "none"
    LOCAL_FILES = "local-files"
    GOVERNED_CANDIDATES = "governed-candidates"
    EXTERNAL_ACTION = "external-action"


class PluginFallbackPolicy(str, Enum):
    FAIL_CLOSED = "fail-closed"
    DETERMINISTIC_ONLY = "deterministic-only"
    SKIP_WITH_RECEIPT = "skip-with-receipt"
    HUMAN_REVIEW_ONLY = "human-review-only"


class SurfaceName(str, Enum):
    CLI = "cli"
    MCP = "mcp"
    WORKBENCH = "workbench"
    NATIVE_WRAPPER = "native-wrapper"


class AdapterHealth(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"


class FallbackPolicy(str, Enum):
    FAIL_CLOSED = "fail_closed"
    DETERMINISTIC_ONLY = "deterministic_only"
    HUMAN_REVIEW_ONLY = "human_review_only"


class CtxVaultGovernanceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scope(CtxVaultGovernanceModel):
    kind: ScopeKind
    value: str = Field(min_length=1)


class ClaimRecord(CtxVaultGovernanceModel):
    id: str = Field(pattern=r"^claim_")
    scope: Scope
    subject_ref: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
    claim_text: str = Field(min_length=1)
    status: ClaimStatus
    source_refs: list[str] = Field(default_factory=list)
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceLink(CtxVaultGovernanceModel):
    id: str = Field(pattern=r"^evid_")
    claim_id: str = Field(pattern=r"^claim_")
    evidence_ref: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
    relation: EvidenceRelation
    excerpt: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime


class AuditRun(CtxVaultGovernanceModel):
    id: str = Field(pattern=r"^audit_")
    scope: Scope
    subject_ref: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
    claim_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    verdict: EvidenceVerdict
    method: AuditMethod
    review_state: ReviewState = ReviewState.OPEN
    notes: str | None = None
    created_at: datetime


class AdapterCapabilityProfile(CtxVaultGovernanceModel):
    id: str = Field(pattern=r"^adapter_")
    mode: AdapterMode
    harness_name: str = Field(min_length=1)
    supported_projection_types: list[str] = Field(default_factory=list)
    required_files: list[str] = Field(default_factory=list)
    optional_files: list[str] = Field(default_factory=list)
    hook_support: list[str] = Field(default_factory=list)
    health_state: AdapterHealth = AdapterHealth.UNKNOWN
    fallback_policy: FallbackPolicy = FallbackPolicy.DETERMINISTIC_ONLY
    last_checked_at: datetime | None = None
    updated_at: datetime


class PluginManifest(CtxVaultGovernanceModel):
    schema_version: str = Field(default="ctxvault.plugin-manifest/v1", pattern=r"^ctxvault\.plugin-manifest/v1$")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    version: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    kind: PluginKind
    capabilities: list[str] = Field(default_factory=list)
    runtime: PluginRuntime
    accepted_inputs: list[str] = Field(default_factory=list)
    produced_outputs: list[str] = Field(default_factory=list)
    side_effect_level: PluginSideEffectLevel
    requires_review: bool
    requires_network: bool
    fallback_policy: PluginFallbackPolicy
    supported_surfaces: list[SurfaceName] = Field(default_factory=list)
    healthcheck: str = Field(min_length=1)


MODEL_REGISTRY = {
    "ClaimRecord": ClaimRecord,
    "EvidenceLink": EvidenceLink,
    "AuditRun": AuditRun,
    "AdapterCapabilityProfile": AdapterCapabilityProfile,
    "PluginManifest": PluginManifest,
}


def model_json_schema_map() -> dict[str, dict]:
    return {name: model.model_json_schema() for name, model in MODEL_REGISTRY.items()}
