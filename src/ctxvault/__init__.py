"""CtxVault deterministic scaffold."""

from .adapters import AdapterRegistry
from .backup import emit_backup_bundle
from .config import CtxVaultConfig, load_config
from .core import ContextBuildRequest, ContextItemInput, CtxVault
from .ingest import ImportReceipt, TranscriptImportReceipt, import_conversation_path, import_knowledge_path, import_prompt_path, import_transcript_path
from .intelligence import build_episode_synthesis_payload, derive_episode_payloads, render_manual_note
from .layout import VaultLayout, default_layout
from .mcp_stdio import CtxVaultMcpServer
from .policy import CtxVaultPolicy
from .plugins import LocalPluginExecutorRegistry, PluginRegistry, PluginRegistryError
from .privacy import PrivacyFinding, PrivacyScanReport, scan_privacy_text
from .projections import emit_agents_md_projection, render_agents_md
from .receipts import emit_audit_receipt, emit_context_bundle_receipt, emit_projection_receipt, emit_workstream_candidate_receipt, emit_workstream_receipt
from .surface import CtxVaultSurface
from .versioning import apply_replica, apply_restore, apply_sync_manifest, create_snapshot, diff_snapshots, emit_sync_manifest, emit_sync_receipt, evaluate_replica_trust, import_replica, list_replica_trust_devices, list_snapshots, load_replica_trust_registry, plan_restore, set_replica_device_trust, snapshot_lineage, snapshot_provenance, sync_status, verify_replica

try:
    from .projection_lifecycle import canonical_projection_path, default_context_assembly_decisions, scan_projection_lifecycle
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in extracted public-core builds
    if exc.name not in {"ctxvault.projection_lifecycle", f"{__name__}.projection_lifecycle"}:
        raise
    canonical_projection_path = None
    default_context_assembly_decisions = None
    scan_projection_lifecycle = None

try:
    from .workbench import CtxVaultWorkbenchService, serve_workbench
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in extracted public-core builds
    if exc.name not in {"ctxvault.workbench", f"{__name__}.workbench"}:
        raise
    CtxVaultWorkbenchService = None
    serve_workbench = None

__all__ = [
    "AdapterRegistry",
    "build_episode_synthesis_payload",
    "CtxVaultConfig",
    "CtxVaultMcpServer",
    "ContextBuildRequest",
    "ContextItemInput",
    "CtxVault",
    "CtxVaultPolicy",
    "CtxVaultSurface",
    "ImportReceipt",
    "LocalPluginExecutorRegistry",
    "PluginRegistry",
    "PluginRegistryError",
    "PrivacyFinding",
    "PrivacyScanReport",
    "TranscriptImportReceipt",
    "VaultLayout",
    "default_layout",
    "create_snapshot",
    "diff_snapshots",
    "emit_sync_manifest",
    "emit_sync_receipt",
    "list_snapshots",
    "list_replica_trust_devices",
    "load_replica_trust_registry",
    "apply_restore",
    "apply_sync_manifest",
    "apply_replica",
    "evaluate_replica_trust",
    "verify_replica",
    "import_replica",
    "plan_restore",
    "set_replica_device_trust",
    "snapshot_lineage",
    "snapshot_provenance",
    "sync_status",
    "derive_episode_payloads",
    "emit_backup_bundle",
    "emit_audit_receipt",
    "emit_agents_md_projection",
    "emit_context_bundle_receipt",
    "emit_projection_receipt",
    "emit_workstream_candidate_receipt",
    "emit_workstream_receipt",
    "import_conversation_path",
    "import_knowledge_path",
    "import_prompt_path",
    "import_transcript_path",
    "load_config",
    "render_agents_md",
    "render_manual_note",
    "scan_privacy_text",
]

if canonical_projection_path is not None and default_context_assembly_decisions is not None and scan_projection_lifecycle is not None:
    __all__.extend(["canonical_projection_path", "default_context_assembly_decisions", "scan_projection_lifecycle"])

if CtxVaultWorkbenchService is not None and serve_workbench is not None:
    __all__.extend(["CtxVaultWorkbenchService", "serve_workbench"])
