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


class OperationKind(str, Enum):
    MEMORY_PROMOTION = "memory_promotion"
    PROMPT_PATCH_PROMOTION = "prompt_patch_promotion"
    WORKSTREAM_PROMOTION = "workstream_promotion"
    KNOWLEDGE_EXPORT = "knowledge_export"
    CONTEXT_EXPORT = "context_export"
    INDEX_REBUILD = "index_rebuild"
    DESTRUCTIVE_REDACTION = "destructive_redaction"
    REDACTION_REVERSAL = "redaction_reversal"


class BackupStatus(str, Enum):
    OK = "ok"
    STALE = "stale"
    MISSING = "missing"
    FAILED = "failed"


class BackupMode(str, Enum):
    PREFLIGHT = "preflight"
    SCHEDULED = "scheduled"
    MANUAL = "manual"
    MIGRATION_GUARD = "migration_guard"


class FailureAction(str, Enum):
    BLOCK = "block"
    ESCALATE = "escalate"
    ROLLBACK_REQUIRED = "rollback_required"


class ExportAction(str, Enum):
    ALLOW = "allow"
    REDACT = "redact"
    REVIEW = "review"
    BLOCK = "block"


class ProjectionKind(str, Enum):
    HARNESS = "harness"
    HUMAN_READABLE = "human-readable"
    FIRST_PARTY_SURFACE = "first-party-surface"


class MergePolicy(str, Enum):
    REPLACE = "replace"
    MERGE = "merge"
    APPEND = "append"
    SKIP = "skip"


class ProjectionOutputStatus(str, Enum):
    WRITTEN = "written"
    UPDATED = "updated"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class ProjectionReviewState(str, Enum):
    GENERATED = "generated"
    PENDING_RECONCILIATION = "pending-reconciliation"
    REVIEWED = "reviewed"


class RollbackTriggerKind(str, Enum):
    BACKUP_RECEIPT_MISSING = "backup_receipt_missing"
    BACKUP_RECEIPT_STALE = "backup_receipt_stale"
    REDACTION_POLICY_VIOLATION = "redaction_policy_violation"
    EXPORT_POLICY_VIOLATION = "export_policy_violation"
    PROJECTION_CORRUPTION = "projection_corruption"
    SCHEMA_MIGRATION_FAILURE = "schema_migration_failure"
    DESTRUCTIVE_REDACTION_WITHOUT_BACKUP = "destructive_redaction_without_backup"
    DURABLE_WRITE_VALIDATION_FAILURE = "durable_write_validation_failure"


class RollbackSeverity(str, Enum):
    WARNING = "warning"
    ROLLBACK_RECOMMENDED = "rollback_recommended"
    ROLLBACK_REQUIRED = "rollback_required"


class RollbackAction(str, Enum):
    PAUSE_WRITES = "pause_writes"
    RESTORE_LAST_VALID_BACKUP = "restore_last_valid_backup"
    REBUILD_PROJECTION = "rebuild_projection"
    REQUIRE_HUMAN_REVIEW = "require_human_review"


class RollbackState(str, Enum):
    DECLARED = "declared"
    VALIDATED = "validated"
    EXECUTED = "executed"
    DISMISSED = "dismissed"


class CtxVaultControlsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scope(CtxVaultControlsModel):
    kind: ScopeKind
    value: str = Field(min_length=1)


class OperationRule(CtxVaultControlsModel):
    operation: OperationKind
    requires_backup: bool
    max_backup_age_hours: int | None = Field(default=None, ge=1)
    require_human_review: bool
    applies_to_sensitivity: list[SensitivityLevel] = Field(default_factory=list)
    on_failure: FailureAction


class ExportRule(CtxVaultControlsModel):
    sensitivities: list[SensitivityLevel] = Field(default_factory=list)
    action: ExportAction
    redact_secret_refs: bool
    require_human_review: bool


class BackupCheckReceipt(CtxVaultControlsModel):
    id: str = Field(pattern=r"^backup_")
    scope: Scope
    checked_at: datetime
    status: BackupStatus
    mode: BackupMode
    protected_refs: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    recovery_point_at: datetime | None = None
    restore_tested: bool
    max_age_hours: int = Field(ge=1)
    notes: str | None = None


class ProtectionPolicy(CtxVaultControlsModel):
    id: str = Field(pattern=r"^policy_")
    scope: Scope
    name: str = Field(min_length=1)
    operation_rules: list[OperationRule] = Field(default_factory=list)
    export_rules: list[ExportRule] = Field(default_factory=list)
    rollback_triggers: list[RollbackTriggerKind] = Field(default_factory=list)
    secret_ref_schemes: list[str] = Field(default_factory=list)
    notes: str | None = None
    updated_at: datetime


class RollbackDecision(CtxVaultControlsModel):
    id: str = Field(pattern=r"^rollback_")
    triggered_at: datetime
    trigger: RollbackTriggerKind
    severity: RollbackSeverity
    affected_refs: list[str] = Field(default_factory=list)
    backup_receipt_ref: str | None = Field(default=None, pattern=r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
    action: RollbackAction
    state: RollbackState
    notes: str | None = None


class ProjectionReceipt(CtxVaultControlsModel):
    schema_version: str = Field(default="ctxvault.projection-receipt/v1", pattern=r"^ctxvault\.projection-receipt/v1$")
    receipt_id: str = Field(pattern=r"^projection_")
    created_at: datetime
    projection_id: str = Field(min_length=1)
    projection_kind: ProjectionKind
    target_kind: str = Field(min_length=1)
    target_path: str = Field(min_length=1)
    source_refs: list[str] = Field(default_factory=list)
    source_object_kinds: list[str] = Field(default_factory=list)
    scope: Scope
    plugin_id: str = Field(min_length=1)
    plugin_version: str = Field(min_length=1)
    render_policy: str = Field(min_length=1)
    merge_policy: MergePolicy
    output_sha256: str = Field(min_length=1)
    output_bytes: int = Field(ge=0)
    output_status: ProjectionOutputStatus
    policy_decision: ExportAction
    review_state: ProjectionReviewState
    warnings: list[str] = Field(default_factory=list)


MODEL_REGISTRY = {
    "BackupCheckReceipt": BackupCheckReceipt,
    "ProtectionPolicy": ProtectionPolicy,
    "RollbackDecision": RollbackDecision,
    "ProjectionReceipt": ProjectionReceipt,
}


def model_json_schema_map() -> dict[str, dict]:
    return {name: model.model_json_schema() for name, model in MODEL_REGISTRY.items()}
