from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScopeKind(str, Enum):
    GLOBAL = "global"
    USER = "user"
    WORKSPACE = "workspace"
    PROJECT = "project"
    THREAD = "thread"
    TASK = "task"
    TURN = "turn"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ERRORED = "errored"


class EpisodeKind(str, Enum):
    CLARIFY = "clarify"
    PLAN = "plan"
    EXECUTE = "execute"
    DEBUG = "debug"
    REVIEW = "review"
    SUMMARIZE = "summarize"
    DESIGN = "design"
    OTHER = "other"


class TurnRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class WorkstreamStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


class WorkstreamApprovalState(str, Enum):
    APPROVED = "approved"
    SYSTEM_GENERATED = "system_generated"


class PromptStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PromptOwner(str, Enum):
    USER = "user"
    SYSTEM = "system"


class EvalStatus(str, Enum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


class MemoryType(str, Enum):
    PREFERENCE = "preference"
    RULE = "rule"
    WORKFLOW_PATTERN = "workflow_pattern"
    TOOL_HINT = "tool_hint"
    PROJECT_FACT = "project_fact"
    CLAIM = "claim"
    EXEMPLAR = "exemplar"
    ANTI_PATTERN = "anti_pattern"
    TASK_STATE = "task_state"
    USER_PROFILE = "user_profile"
    GLOSSARY_TERM = "glossary_term"


class ProposalState(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    MERGED = "merged"


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"
    RETRACTED = "retracted"


class MemoryApprovalState(str, Enum):
    APPROVED = "approved"
    AUTO_ACCEPTED = "auto_accepted"
    SYSTEM_GENERATED = "system_generated"


class KnowledgeKind(str, Enum):
    TIMELINE = "timeline"
    SYNTHESIS = "synthesis"
    GLOSSARY_ENTRY = "glossary_entry"
    PROJECT_PROFILE = "project_profile"
    ENTITY_SUMMARY = "entity_summary"
    GRAPH_PROJECTION = "graph_projection"


class KnowledgeStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    STALE = "stale"


class EvalTargetType(str, Enum):
    PROMPT_ASSET = "prompt_asset"
    PROMPT_PATCH = "prompt_patch"
    BUNDLE_POLICY = "bundle_policy"
    EXTRACTOR = "extractor"
    CONSOLIDATOR = "consolidator"


class EvalResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"


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


class ContextVaultModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scope(ContextVaultModel):
    kind: ScopeKind
    value: str = Field(min_length=1)


class SessionSignalSummary(ContextVaultModel):
    user_corrections: int = 0
    accepted_outputs: int = 0
    tool_success_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    followup_count: int = 0


class EpisodeQualitySignals(ContextVaultModel):
    user_corrections: int = 0
    assistant_revisions: int = 0
    accepted_outputs: int = 0
    tool_success_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class ContextSectionItem(ContextVaultModel):
    ref: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
    content: str


class ContextBundleSections(ContextVaultModel):
    core_rules: list[ContextSectionItem] = Field(default_factory=list)
    project_context: list[ContextSectionItem] = Field(default_factory=list)
    active_task_state: list[ContextSectionItem] = Field(default_factory=list)
    relevant_memories: list[ContextSectionItem] = Field(default_factory=list)
    relevant_knowledge: list[ContextSectionItem] = Field(default_factory=list)
    recent_conversation: list[ContextSectionItem] = Field(default_factory=list)
    source_pointers: list[str] = Field(default_factory=list)


class Session(ContextVaultModel):
    id: str = Field(pattern=r"^sess_")
    client: str = Field(min_length=1)
    source_app: str | None = Field(default=None, min_length=1)
    source_surface: str | None = Field(default=None, min_length=1)
    source_format: str | None = Field(default=None, min_length=1)
    capture_method: str | None = Field(default=None, min_length=1)
    imported_via: str | None = Field(default=None, min_length=1)
    scope: Scope
    title: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    status: SessionStatus
    task_label: str | None = None
    active_prompt_ids: list[str] = Field(default_factory=list)
    bundle_ids: list[str] = Field(default_factory=list)
    derived_asset_refs: list[str] = Field(default_factory=list)
    signal_summary: SessionSignalSummary = Field(default_factory=SessionSignalSummary)
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool


class Episode(ContextVaultModel):
    id: str = Field(pattern=r"^ep_")
    session_id: str = Field(pattern=r"^sess_")
    kind: EpisodeKind
    goal: str = Field(min_length=1)
    start_turn_index: int = Field(ge=0)
    end_turn_index: int = Field(ge=0)
    start_at: datetime
    end_at: datetime
    input_refs: list[str] = Field(default_factory=list)
    outcome: str | None = None
    quality_signals: EpisodeQualitySignals = Field(default_factory=EpisodeQualitySignals)
    derived_refs: list[str] = Field(default_factory=list)


class Turn(ContextVaultModel):
    id: str = Field(pattern=r"^turn_")
    session_id: str = Field(pattern=r"^sess_")
    index: int = Field(ge=0)
    role: TurnRole
    content: str | dict[str, Any] | list[Any]
    timestamp: datetime
    prompt_asset_id: str | None = None
    context_bundle_id: str | None = None
    tool_call_id: str | None = None
    source_app: str | None = Field(default=None, min_length=1)
    source_surface: str | None = Field(default=None, min_length=1)
    source_format: str | None = Field(default=None, min_length=1)
    capture_method: str | None = Field(default=None, min_length=1)
    imported_via: str | None = Field(default=None, min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    annotations: dict[str, Any] = Field(default_factory=dict)


class Workstream(ContextVaultModel):
    id: str = Field(pattern=r"^ws_")
    scope: Scope
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: WorkstreamStatus
    approval_state: WorkstreamApprovalState
    source_refs: list[str] = Field(default_factory=list)
    session_refs: list[str] = Field(default_factory=list)
    episode_refs: list[str] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    recurring_terms: list[str] = Field(default_factory=list)
    task_labels: list[str] = Field(default_factory=list)
    episode_kind_counts: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    secret_refs: list[str] = Field(default_factory=list)
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    exportable: bool
    created_at: datetime
    updated_at: datetime


class WorkstreamCandidate(ContextVaultModel):
    id: str = Field(pattern=r"^wsc_")
    scope: Scope
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    session_refs: list[str] = Field(default_factory=list)
    episode_refs: list[str] = Field(default_factory=list)
    knowledge_refs: list[str] = Field(default_factory=list)
    recurring_terms: list[str] = Field(default_factory=list)
    task_labels: list[str] = Field(default_factory=list)
    episode_kind_counts: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    proposal_state: ProposalState
    candidate_for: str | None = Field(default=None, pattern=r"^ws_")
    notes: str | None = None
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime


class PromptAsset(ContextVaultModel):
    id: str = Field(pattern=r"^prompt_")
    name: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    scope: Scope
    status: PromptStatus
    instruction: str = Field(min_length=1)
    required_context_types: list[str] = Field(default_factory=list)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    model_preferences: dict[str, Any] = Field(default_factory=dict)
    derived_from: list[str] = Field(default_factory=list)
    owner: PromptOwner
    eval_status: EvalStatus = EvalStatus.UNKNOWN
    known_failure_modes: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    last_promoted_at: datetime | None = None
    quality_metrics: dict[str, Any] = Field(default_factory=dict)
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime
    updated_at: datetime


class PromptRun(ContextVaultModel):
    id: str = Field(pattern=r"^prun_")
    prompt_asset_id: str = Field(pattern=r"^prompt_")
    session_id: str = Field(pattern=r"^sess_")
    episode_id: str | None = None
    bundle_id: str | None = None
    model: str = Field(min_length=1)
    input_refs: list[str] = Field(default_factory=list)
    output_ref: str | None = None
    signals: dict[str, Any] = Field(default_factory=dict)
    feedback: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class PromptPatch(ContextVaultModel):
    id: str = Field(pattern=r"^ppatch_")
    prompt_asset_id: str = Field(pattern=r"^prompt_")
    scope: Scope
    changes: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    proposal_state: ProposalState
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime


class MemoryCandidate(ContextVaultModel):
    id: str = Field(pattern=r"^memc_")
    type: MemoryType
    scope: Scope
    statement: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    proposal_state: ProposalState
    candidate_for: str | None = None
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime


class Memory(ContextVaultModel):
    id: str = Field(pattern=r"^mem_")
    type: MemoryType
    scope: Scope
    status: MemoryStatus
    approval_state: MemoryApprovalState
    statement: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    valid_from: datetime
    valid_to: datetime | None = None
    supersedes: list[str] = Field(default_factory=list)
    retracts: list[str] = Field(default_factory=list)
    retrieval_policy: dict[str, Any] = Field(default_factory=dict)
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeArtifact(ContextVaultModel):
    id: str = Field(pattern=r"^know_")
    kind: KnowledgeKind
    title: str = Field(min_length=1)
    scope: Scope
    body: str | dict[str, Any] | list[Any] | None = None
    source_refs: list[str] = Field(default_factory=list)
    derived_from: list[str] = Field(default_factory=list)
    status: KnowledgeStatus
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime
    updated_at: datetime


class ContextBundle(ContextVaultModel):
    id: str = Field(pattern=r"^bundle_")
    scope: Scope
    task_label: str = Field(min_length=1)
    sections: ContextBundleSections
    input_refs: list[str] = Field(default_factory=list)
    token_budget: int = Field(ge=0)
    token_estimate: int = Field(ge=0)
    assembly_policy: dict[str, Any] = Field(default_factory=dict)
    sensitivity: SensitivityLevel
    redaction_state: RedactionState
    secret_refs: list[str] = Field(default_factory=list)
    exportable: bool
    created_at: datetime


class EvalRun(ContextVaultModel):
    id: str = Field(pattern=r"^eval_")
    target_type: EvalTargetType
    target_id: str = Field(min_length=1)
    dataset_ref: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
    metrics: dict[str, Any] = Field(default_factory=dict)
    result: EvalResult
    notes: str | None = None
    created_at: datetime


MODEL_REGISTRY = {
    "Session": Session,
    "Episode": Episode,
    "Turn": Turn,
    "PromptAsset": PromptAsset,
    "PromptRun": PromptRun,
    "PromptPatch": PromptPatch,
    "MemoryCandidate": MemoryCandidate,
    "Memory": Memory,
    "KnowledgeArtifact": KnowledgeArtifact,
    "ContextBundle": ContextBundle,
    "EvalRun": EvalRun,
}


def model_json_schema_map() -> dict[str, dict[str, Any]]:
    return {name: model.model_json_schema() for name, model in MODEL_REGISTRY.items()}
