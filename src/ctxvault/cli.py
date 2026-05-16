from __future__ import annotations

import argparse
from importlib import import_module
from importlib.util import find_spec
import json
from pathlib import Path
import sys
from typing import Callable

from .checks import main as run_checks_main
from .config import load_config
from .core import ContextBuildRequest, CtxVault
from .ingest import import_conversation_path, import_knowledge_path, import_prompt_path, import_transcript_path
from .layout import default_layout
from .mcp_stdio import serve_stdio
from .oss_case_study import build_oss_case_study_preview
from .policy import CtxVaultPolicy
from .surface import CtxVaultSurface


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def bundled_fixtures_root() -> Path:
    return project_root() / "fixtures"


def resolve_fixture_path(root: Path, *relative_parts: str) -> Path:
    local_path = root / "fixtures" / Path(*relative_parts)
    if local_path.exists():
        return local_path
    return bundled_fixtures_root().joinpath(*relative_parts)


def workbench_module_name() -> str:
    if __package__:
        return f"{__package__}.workbench"
    return "ctxvault.workbench"


def has_workbench_surface() -> bool:
    return find_spec(workbench_module_name()) is not None


def load_workbench_server() -> Callable[..., int]:
    try:
        module = import_module(".workbench", __package__ or "ctxvault")
    except ModuleNotFoundError as exc:
        if exc.name in {workbench_module_name(), "ctxvault.workbench"}:
            raise RuntimeError("workbench surface is not available in this build") from exc
        raise
    server = getattr(module, "serve_workbench", None)
    if not callable(server):
        raise RuntimeError("workbench surface is not available in this build")
    return server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ctxvault")
    subcommands = parser.add_subparsers(dest="command", required=True)

    print_layout = subcommands.add_parser("print-layout", help="Print the default runtime layout")
    print_layout.add_argument("--root", type=Path, default=project_root())

    config_show = subcommands.add_parser("show-config", help="Load and print a config file")
    config_show.add_argument(
        "--config",
        type=Path,
        default=project_root() / "config" / "ctxvault.example.toml",
    )

    init_vault = subcommands.add_parser("init-vault", help="Create the deterministic vault layout and SQLite projections")
    init_vault.add_argument("--root", type=Path, default=project_root())

    seed_fixtures = subcommands.add_parser("seed-fixtures", help="Import the canonical core fixtures into the local vault")
    seed_fixtures.add_argument("--root", type=Path, default=project_root())

    build_context = subcommands.add_parser("build-context", help="Build a deterministic context bundle from stored objects")
    build_context.add_argument("--root", type=Path, default=project_root())
    build_context.add_argument("--scope-kind", default="project")
    build_context.add_argument("--scope-value", default="ctxvault")
    build_context.add_argument("--task-label", required=True)
    build_context.add_argument("--prompt-id")
    build_context.add_argument("--session-id")
    build_context.add_argument("--memory-query", default="")
    build_context.add_argument("--knowledge-query", default="")
    build_context.add_argument("--max-memories", type=int, default=5)
    build_context.add_argument("--max-knowledge", type=int, default=4)
    build_context.add_argument("--max-recent-turns", type=int, default=6)
    build_context.add_argument("--token-budget", type=int, default=12000)
    build_context.add_argument("--write-receipt", type=Path)
    build_context.add_argument("--plan-path", type=Path)
    build_context.add_argument("--task-id")

    seed_evidence = subcommands.add_parser("seed-evidence-fixtures", help="Import the canonical claim and evidence fixtures into the local vault")
    seed_evidence.add_argument("--root", type=Path, default=project_root())

    trace_record = subcommands.add_parser("trace-record", help="Store a core object through the named trace surface")
    trace_record.add_argument("--root", type=Path, default=project_root())
    trace_record.add_argument("--model-name", required=True)
    trace_record.add_argument("--json-path", type=Path, required=True)

    prompt_resolve = subcommands.add_parser("prompt-resolve", help="Resolve a prompt asset through the named surface")
    prompt_resolve.add_argument("--root", type=Path, default=project_root())
    prompt_resolve.add_argument("--prompt-id", required=True)

    session_list = subcommands.add_parser("session-list", help="List imported sessions through the deterministic surface")
    session_list.add_argument("--root", type=Path, default=project_root())
    session_list.add_argument("--scope-kind")
    session_list.add_argument("--scope-value")
    session_list.add_argument("--limit", type=int, default=20)

    session_search = subcommands.add_parser("session-search", help="Search imported sessions through the deterministic surface")
    session_search.add_argument("--root", type=Path, default=project_root())
    session_search.add_argument("--query", required=True)
    session_search.add_argument("--scope-kind")
    session_search.add_argument("--scope-value")
    session_search.add_argument("--limit", type=int, default=20)

    session_related = subcommands.add_parser("session-related", help="Find deterministic related sessions for one anchor session")
    session_related.add_argument("--root", type=Path, default=project_root())
    session_related.add_argument("--session-id", required=True)
    session_related.add_argument("--limit", type=int, default=5)

    session_aggregate_preview = subcommands.add_parser("session-aggregate-preview", help="Build a read-only aggregate preview over one session and its related sessions")
    session_aggregate_preview.add_argument("--root", type=Path, default=project_root())
    session_aggregate_preview.add_argument("--session-id", required=True)
    session_aggregate_preview.add_argument("--limit", type=int, default=5)

    workstream_list = subcommands.add_parser("workstream-list", help="List durable workstreams")
    workstream_list.add_argument("--root", type=Path, default=project_root())
    workstream_list.add_argument("--scope-kind")
    workstream_list.add_argument("--scope-value")
    workstream_list.add_argument("--status")
    workstream_list.add_argument("--limit", type=int, default=20)

    workstream_preview = subcommands.add_parser("workstream-preview", help="Build a read-only workstream preview from one anchor session")
    workstream_preview.add_argument("--root", type=Path, default=project_root())
    workstream_preview.add_argument("--session-id", required=True)
    workstream_preview.add_argument("--limit", type=int, default=5)

    workstream_intelligence = subcommands.add_parser(
        "workstream-intelligence",
        help="Build a read-only workstream intelligence report over distilled workstream assets",
    )
    workstream_intelligence.add_argument("--root", type=Path, default=project_root())
    workstream_intelligence.add_argument("--workstream-id", required=True)
    workstream_intelligence.add_argument("--limit", type=int, default=6)

    compiled_workstream_state = subcommands.add_parser(
        "compiled-workstream-state",
        help="Build the experimental compiled workstream state read model",
    )
    compiled_workstream_state.add_argument("--root", type=Path, default=project_root())
    compiled_workstream_state.add_argument("--workstream-id", required=True)
    compiled_workstream_state.add_argument("--limit", type=int, default=6)

    workstream_candidate_create = subcommands.add_parser("workstream-candidate-create", help="Create a durable workstream candidate from a workstream preview")
    workstream_candidate_create.add_argument("--root", type=Path, default=project_root())
    workstream_candidate_create.add_argument("--session-id", required=True)
    workstream_candidate_create.add_argument("--limit", type=int, default=5)
    workstream_candidate_create.add_argument("--candidate-id")
    workstream_candidate_create.add_argument("--candidate-for")
    workstream_candidate_create.add_argument("--title")
    workstream_candidate_create.add_argument("--summary")
    workstream_candidate_create.add_argument("--rationale")
    workstream_candidate_create.add_argument("--notes")

    workstream_candidate_list = subcommands.add_parser("workstream-candidate-list", help="List proposed or resolved workstream candidates")
    workstream_candidate_list.add_argument("--root", type=Path, default=project_root())
    workstream_candidate_list.add_argument("--scope-kind")
    workstream_candidate_list.add_argument("--scope-value")
    workstream_candidate_list.add_argument("--proposal-state")
    workstream_candidate_list.add_argument("--limit", type=int, default=20)

    review_workstream_candidate = subcommands.add_parser("review-workstream-candidate", help="Approve or reject a proposed workstream candidate")
    review_workstream_candidate.add_argument("--root", type=Path, default=project_root())
    review_workstream_candidate.add_argument("--candidate-id", required=True)
    review_workstream_candidate.add_argument("--decision", required=True, choices=["approved", "rejected"])
    review_workstream_candidate.add_argument("--reviewer", default="human_review")
    review_workstream_candidate.add_argument("--notes")
    review_workstream_candidate.add_argument("--workstream-id")
    review_workstream_candidate.add_argument("--policy-json-path", type=Path)
    review_workstream_candidate.add_argument("--backup-json-path", type=Path)

    emit_workstream_receipt = subcommands.add_parser("emit-workstream-receipt", help="Write a stable workstream receipt for plan-ledger artifact registration")
    emit_workstream_receipt.add_argument("--root", type=Path, default=project_root())
    emit_workstream_receipt.add_argument("--workstream-id", required=True)
    emit_workstream_receipt.add_argument("--output-path", type=Path, required=True)
    emit_workstream_receipt.add_argument("--plan-path", type=Path)
    emit_workstream_receipt.add_argument("--task-id")

    emit_workstream_candidate_receipt = subcommands.add_parser("emit-workstream-candidate-receipt", help="Write a stable workstream candidate receipt for plan-ledger artifact registration")
    emit_workstream_candidate_receipt.add_argument("--root", type=Path, default=project_root())
    emit_workstream_candidate_receipt.add_argument("--candidate-id", required=True)
    emit_workstream_candidate_receipt.add_argument("--output-path", type=Path, required=True)
    emit_workstream_candidate_receipt.add_argument("--plan-path", type=Path)
    emit_workstream_candidate_receipt.add_argument("--task-id")

    episode_list = subcommands.add_parser("episode-list", help="List derived episodes from stored sessions")
    episode_list.add_argument("--root", type=Path, default=project_root())
    episode_list.add_argument("--scope-kind")
    episode_list.add_argument("--scope-value")
    episode_list.add_argument("--session-id")
    episode_list.add_argument("--limit", type=int, default=20)

    derive_episodes = subcommands.add_parser("derive-episodes", help="Derive deterministic episodes from an imported session")
    derive_episodes.add_argument("--root", type=Path, default=project_root())
    derive_episodes.add_argument("--session-id", required=True)

    synthesize_episode = subcommands.add_parser("synthesize-episode", help="Compile an episode into a synthesis knowledge artifact")
    synthesize_episode.add_argument("--root", type=Path, default=project_root())
    synthesize_episode.add_argument("--episode-id", required=True)
    synthesize_episode.add_argument("--knowledge-id")
    synthesize_episode.add_argument("--title")

    export_knowledge_note = subcommands.add_parser("export-knowledge-note", help="Export a knowledge artifact as a local wiki note candidate")
    export_knowledge_note.add_argument("--root", type=Path, default=project_root())
    export_knowledge_note.add_argument("--knowledge-id", required=True)
    export_knowledge_note.add_argument("--output-path", type=Path, required=True)
    export_knowledge_note.add_argument("--canonical-target", default="project:ctxvault")
    export_knowledge_note.add_argument("--privacy")
    export_knowledge_note.add_argument("--status", default="draft")
    export_knowledge_note.add_argument("--note-id")
    export_knowledge_note.add_argument("--title")

    memory_search = subcommands.add_parser("memory-search", help="Search memories through the named surface")
    memory_search.add_argument("--root", type=Path, default=project_root())
    memory_search.add_argument("--query", required=True)
    memory_search.add_argument("--scope-kind")
    memory_search.add_argument("--scope-value")
    memory_search.add_argument("--limit", type=int, default=5)
    memory_search.add_argument("--pinned-only", action="store_true")

    memory_candidate_list = subcommands.add_parser("memory-candidate-list", help="List proposed or resolved memory candidates")
    memory_candidate_list.add_argument("--root", type=Path, default=project_root())
    memory_candidate_list.add_argument("--scope-kind")
    memory_candidate_list.add_argument("--scope-value")
    memory_candidate_list.add_argument("--proposal-state")
    memory_candidate_list.add_argument("--limit", type=int, default=20)

    review_memory_candidate = subcommands.add_parser("review-memory-candidate", help="Approve or reject a proposed memory candidate")
    review_memory_candidate.add_argument("--root", type=Path, default=project_root())
    review_memory_candidate.add_argument("--candidate-id", required=True)
    review_memory_candidate.add_argument("--decision", required=True, choices=["approved", "rejected"])
    review_memory_candidate.add_argument("--reviewer", default="human_review")
    review_memory_candidate.add_argument("--notes")
    review_memory_candidate.add_argument("--memory-id")
    review_memory_candidate.add_argument("--policy-json-path", type=Path)
    review_memory_candidate.add_argument("--backup-json-path", type=Path)

    prompt_patch_list = subcommands.add_parser("prompt-patch-list", help="List proposed or resolved prompt patches")
    prompt_patch_list.add_argument("--root", type=Path, default=project_root())
    prompt_patch_list.add_argument("--scope-kind")
    prompt_patch_list.add_argument("--scope-value")
    prompt_patch_list.add_argument("--proposal-state")
    prompt_patch_list.add_argument("--prompt-asset-id")
    prompt_patch_list.add_argument("--limit", type=int, default=20)

    prompt_patch_density_check = subcommands.add_parser(
        "prompt-patch-density-check",
        help="Run a deterministic density check against a prompt patch preview without mutating the active prompt",
    )
    prompt_patch_density_check.add_argument("--root", type=Path, default=project_root())
    prompt_patch_density_check.add_argument("--patch-id", required=True)

    review_prompt_patch = subcommands.add_parser("review-prompt-patch", help="Approve or reject a proposed prompt patch")
    review_prompt_patch.add_argument("--root", type=Path, default=project_root())
    review_prompt_patch.add_argument("--patch-id", required=True)
    review_prompt_patch.add_argument("--decision", required=True, choices=["approved", "rejected"])
    review_prompt_patch.add_argument("--reviewer", default="human_review")
    review_prompt_patch.add_argument("--notes")
    review_prompt_patch.add_argument("--policy-json-path", type=Path)
    review_prompt_patch.add_argument("--backup-json-path", type=Path)

    prompt_eval_run = subcommands.add_parser("prompt-eval-run", help="Run deterministic assertions against a prompt asset or prompt patch")
    prompt_eval_run.add_argument("--root", type=Path, default=project_root())
    prompt_eval_run.add_argument("--target-type", required=True, choices=["prompt_asset", "prompt_patch"])
    prompt_eval_run.add_argument("--target-id", required=True)
    prompt_eval_run.add_argument("--dataset-ref", default="eval://manual/prompt-assertions")
    prompt_eval_run.add_argument("--assert-contains", action="append", default=[])
    prompt_eval_run.add_argument("--assert-not-contains", action="append", default=[])
    prompt_eval_run.add_argument("--notes")

    privacy_scan = subcommands.add_parser("privacy-scan", help="Run a deterministic privacy preflight over text")
    privacy_scan.add_argument("--root", type=Path, default=project_root())
    privacy_scan_group = privacy_scan.add_mutually_exclusive_group(required=True)
    privacy_scan_group.add_argument("--text")
    privacy_scan_group.add_argument("--text-path", type=Path)
    privacy_scan.add_argument("--source", default="inline")
    privacy_scan.add_argument("--max-findings", type=int, default=25)

    privacy_scan_files = subcommands.add_parser("privacy-scan-files", help="Run a deterministic privacy preflight over one or more local files")
    privacy_scan_files.add_argument("--root", type=Path, default=project_root())
    privacy_scan_files.add_argument("--file-path", type=Path, action="append", required=True)
    privacy_scan_files.add_argument("--source", default="attachment")
    privacy_scan_files.add_argument("--max-findings", type=int, default=25)
    privacy_scan_files.add_argument("--max-bytes", type=int, default=262144)

    share_handoff_stage = subcommands.add_parser("share-handoff-stage", help="Stage a share-extension or App Group ingress payload into the governed handoff queue")
    share_handoff_stage.add_argument("--root", type=Path, default=project_root())
    share_handoff_stage.add_argument("--shared-root", type=Path)
    share_handoff_text_group = share_handoff_stage.add_mutually_exclusive_group()
    share_handoff_text_group.add_argument("--text")
    share_handoff_text_group.add_argument("--text-path", type=Path)
    share_handoff_stage.add_argument("--title")
    share_handoff_stage.add_argument("--url", action="append", default=[])
    share_handoff_stage.add_argument("--attachment-path", action="append", default=[])
    share_handoff_stage.add_argument("--source-app", default="ctxvault")
    share_handoff_stage.add_argument("--source-surface", default="ios")
    share_handoff_stage.add_argument("--source-format", default="share_extension_payload")
    share_handoff_stage.add_argument("--capture-method", default="share_extension")
    share_handoff_stage.add_argument("--imported-via", default="ctxvault_share_extension")
    share_handoff_stage.add_argument("--notes")
    share_handoff_stage.add_argument("--metadata-json-path", type=Path)
    share_handoff_stage.add_argument("--handoff-id")

    share_handoff_list = subcommands.add_parser("share-handoff-list", help="List pending or archived share handoff queue items")
    share_handoff_list.add_argument("--root", type=Path, default=project_root())
    share_handoff_list.add_argument("--shared-root", type=Path)
    share_handoff_list.add_argument("--limit", type=int, default=50)
    share_handoff_list.add_argument("--include-archived", action="store_true")

    share_handoff_preview = subcommands.add_parser("share-handoff-preview", help="Preview one share handoff and run deterministic privacy checks over its text and attachments")
    share_handoff_preview.add_argument("--root", type=Path, default=project_root())
    share_handoff_preview.add_argument("--shared-root", type=Path)
    share_handoff_preview.add_argument("--handoff-path", type=Path, required=True)
    share_handoff_preview.add_argument("--max-findings", type=int, default=25)
    share_handoff_preview.add_argument("--max-bytes", type=int, default=262144)

    share_handoff_consume = subcommands.add_parser("share-handoff-consume", help="Consume one share handoff into governed evidence and a MemoryCandidate")
    share_handoff_consume.add_argument("--root", type=Path, default=project_root())
    share_handoff_consume.add_argument("--shared-root", type=Path)
    share_handoff_consume.add_argument("--handoff-path", type=Path, required=True)
    share_handoff_consume.add_argument("--why-it-matters", required=True)
    share_handoff_consume.add_argument("--statement")
    share_handoff_consume.add_argument("--scope-kind", default="project")
    share_handoff_consume.add_argument("--scope-value", default="ctxvault")
    share_handoff_consume.add_argument("--candidate-type", default="workflow_pattern")
    share_handoff_consume.add_argument("--confidence", type=float, default=0.8)
    share_handoff_consume.add_argument("--candidate-for")
    share_handoff_consume.add_argument("--sensitivity", default="internal")
    share_handoff_consume.add_argument("--redaction-state", default="none")
    share_handoff_consume.add_argument("--exportable", choices=["true", "false"], default="true")
    share_handoff_consume.add_argument("--notes")
    share_handoff_consume.add_argument("--reviewed-by", default="share_handoff_consume")
    share_handoff_consume.add_argument("--allow-blocked", action="store_true")
    share_handoff_consume.add_argument("--max-findings", type=int, default=25)
    share_handoff_consume.add_argument("--max-bytes", type=int, default=262144)

    knowledge_search = subcommands.add_parser("knowledge-search", help="Search imported knowledge artifacts through the deterministic surface")
    knowledge_search.add_argument("--root", type=Path, default=project_root())
    knowledge_search.add_argument("--query", required=True)
    knowledge_search.add_argument("--scope-kind")
    knowledge_search.add_argument("--scope-value")
    knowledge_search.add_argument("--limit", type=int, default=5)

    context_slice_rebuild = subcommands.add_parser("context-slice-rebuild", help="Rebuild deterministic local context slice indexes")
    context_slice_rebuild.add_argument("--root", type=Path, default=project_root())

    context_search = subcommands.add_parser("context-search", help="Search deterministic local context slices")
    context_search.add_argument("--root", type=Path, default=project_root())
    context_search.add_argument("--query", required=True)
    context_search.add_argument("--scope-kind")
    context_search.add_argument("--scope-value")
    context_search.add_argument("--workstream-ref")
    context_search.add_argument("--limit", type=int, default=10)
    context_search.add_argument("--include-blocked", action="store_true")

    context_selection_preflight = subcommands.add_parser(
        "context-selection-preflight",
        help="Run privacy preflight over selected context slice refs",
    )
    context_selection_preflight.add_argument("--root", type=Path, default=project_root())
    context_selection_preflight.add_argument("--slice-ref", action="append", required=True)
    context_selection_preflight.add_argument("--target-kind", required=True)
    context_selection_preflight.add_argument("--query")
    context_selection_preflight.add_argument("--workstream-ref")
    context_selection_preflight.add_argument("--write-receipt", action="store_true")

    context_selection_compose = subcommands.add_parser(
        "context-selection-compose",
        help="Compose source-grouped context slice candidates and optionally write a context-selection receipt",
    )
    context_selection_compose.add_argument("--root", type=Path, default=project_root())
    context_selection_compose.add_argument("--query", default="")
    context_selection_compose.add_argument("--target-kind", required=True)
    context_selection_compose.add_argument("--scope-kind")
    context_selection_compose.add_argument("--scope-value")
    context_selection_compose.add_argument("--workstream-ref")
    context_selection_compose.add_argument("--slice-ref", action="append", default=[])
    context_selection_compose.add_argument("--candidate-slice-ref", action="append", default=[])
    context_selection_compose.add_argument("--required-slice-ref", action="append", default=[])
    context_selection_compose.add_argument("--limit", type=int, default=10)
    context_selection_compose.add_argument("--token-budget", type=int, default=4000)
    context_selection_compose.add_argument("--include-blocked", action="store_true")
    context_selection_compose.add_argument("--write-receipt", action="store_true")

    context_prepare = subcommands.add_parser(
        "context-prepare",
        help="Prepare a safe local context handoff with selection, privacy preflight, and receipts",
    )
    context_prepare.add_argument("--root", type=Path, default=project_root())
    context_prepare.add_argument("--query", required=True)
    context_prepare.add_argument("--target-kind", default="harness.agents-md")
    context_prepare.add_argument("--scope-kind", default="project")
    context_prepare.add_argument("--scope-value", default="ctxvault")
    context_prepare.add_argument("--workstream-ref")
    context_prepare.add_argument("--slice-ref", action="append", default=[])
    context_prepare.add_argument("--required-slice-ref", action="append", default=[])
    context_prepare.add_argument("--limit", type=int, default=10)
    context_prepare.add_argument("--token-budget", type=int, default=4000)
    context_prepare.add_argument("--include-blocked", action="store_true")
    context_prepare.add_argument("--rebuild", action=argparse.BooleanOptionalAction, default=True)
    context_prepare.add_argument("--write-receipt", action=argparse.BooleanOptionalAction, default=True)

    context_project = subcommands.add_parser(
        "context-project",
        help="Project selected reviewed context into a local work surface with a projection receipt",
    )
    context_project.add_argument("--root", type=Path, default=project_root())
    context_project.add_argument("--target", required=True, choices=("agents-md", "claude-md", "workstream-brief"))
    context_project.add_argument("--workstream-id", required=True)
    context_project.add_argument("--output-path", type=Path)
    context_project.add_argument("--receipt-output-path", type=Path)
    context_project.add_argument("--memory-limit", type=int, default=5)
    context_project.add_argument("--slice-ref", action="append", default=[])

    context_extract = subcommands.add_parser(
        "context-extract",
        help="Import local sources, rebuild slices, optionally prepare and project context with receipts",
    )
    context_extract.add_argument("--root", type=Path, default=project_root())
    context_extract.add_argument("--source-path", type=Path, action="append", required=True)
    context_extract.add_argument("--source-kind", default="auto", choices=("auto", "knowledge", "markdown-vault", "transcript", "prompt"))
    context_extract.add_argument("--scope-kind", default="project")
    context_extract.add_argument("--scope-value", default="ctxvault")
    context_extract.add_argument("--recursive", action="store_true")
    context_extract.add_argument("--kind")
    context_extract.add_argument("--title")
    context_extract.add_argument("--prompt-id")
    context_extract.add_argument("--prompt-name")
    context_extract.add_argument("--prompt-intent", default="general")
    context_extract.add_argument("--prompt-owner", default="local_import")
    context_extract.add_argument("--prompt-required-context-type", action="append", default=[])
    context_extract.add_argument("--transcript-session-id")
    context_extract.add_argument("--transcript-title")
    context_extract.add_argument("--transcript-task-label")
    context_extract.add_argument("--transcript-client", default="local_import")
    context_extract.add_argument("--prepare-query")
    context_extract.add_argument("--target-kind", default="harness.agents-md")
    context_extract.add_argument("--workstream-ref")
    context_extract.add_argument("--slice-ref", action="append", default=[])
    context_extract.add_argument("--required-slice-ref", action="append", default=[])
    context_extract.add_argument("--limit", type=int, default=10)
    context_extract.add_argument("--token-budget", type=int, default=4000)
    context_extract.add_argument("--include-blocked", action="store_true")
    context_extract.add_argument("--project-target", action="append", default=[])
    context_extract.add_argument("--workstream-id")
    context_extract.add_argument("--dry-run", action="store_true")
    context_extract.add_argument("--write-receipt", action=argparse.BooleanOptionalAction, default=True)

    oss_case_study_preview = subcommands.add_parser(
        "oss-case-study-preview",
        help="Create a governed read-only OSS case-study decision preview",
    )
    oss_case_study_preview.add_argument("--root", type=Path, default=project_root())
    oss_case_study_preview.add_argument("--target-name", required=True)
    oss_case_study_preview.add_argument("--repo-url")
    oss_case_study_preview.add_argument("--pinned-ref", required=True)
    oss_case_study_preview.add_argument("--source-path", type=Path)
    oss_case_study_preview.add_argument("--output-dir", type=Path)
    oss_case_study_preview.add_argument("--checked-at-utc")
    oss_case_study_preview.add_argument("--license", default="unknown")
    oss_case_study_preview.add_argument("--allow-network", action="store_true")
    oss_case_study_preview.add_argument("--max-source-bytes", type=int, default=262144)

    receipt_inspect = subcommands.add_parser(
        "receipt-inspect",
        help="Inspect a local receipt chain for extraction, selection, privacy, quality, and projection receipts",
    )
    receipt_inspect.add_argument("--root", type=Path, default=project_root())
    receipt_inspect.add_argument("--receipt-path", type=Path)
    receipt_inspect.add_argument("--receipt-ref")
    receipt_inspect.add_argument("--latest", action="store_true", help="Inspect the newest local receipt")
    receipt_inspect.add_argument("--include-payload", action="store_true")
    receipt_inspect.add_argument("--summary", action="store_true", help="Print a human-readable summary instead of JSON")

    context_slice_preference_set = subcommands.add_parser(
        "context-slice-preference-set",
        help="Pin, hide, archive, or clear one local context slice preference",
    )
    context_slice_preference_set.add_argument("--root", type=Path, default=project_root())
    context_slice_preference_set.add_argument("--slice-ref", required=True)
    context_slice_preference_set.add_argument("--action", required=True, choices=("pin", "hide", "archive", "clear"))
    context_slice_preference_set.add_argument("--target-kind")
    context_slice_preference_set.add_argument("--scope-kind")
    context_slice_preference_set.add_argument("--scope-value")
    context_slice_preference_set.add_argument("--note")

    context_slice_preference_list = subcommands.add_parser(
        "context-slice-preference-list",
        help="List local context slice preferences",
    )
    context_slice_preference_list.add_argument("--root", type=Path, default=project_root())
    context_slice_preference_list.add_argument("--target-kind")
    context_slice_preference_list.add_argument("--scope-kind")
    context_slice_preference_list.add_argument("--scope-value")

    logical_purge_plan = subcommands.add_parser(
        "logical-purge-plan",
        help="Plan a logical purge of derived privacy-sensitive context data",
    )
    logical_purge_plan.add_argument("--root", type=Path, default=project_root())
    logical_purge_plan.add_argument("--source-ref", action="append")
    logical_purge_plan.add_argument("--slice-ref", action="append")
    logical_purge_plan.add_argument("--include-projections", action="store_true")

    logical_purge_apply = subcommands.add_parser(
        "logical-purge-apply",
        help="Apply a reviewed logical purge of derived context data",
    )
    logical_purge_apply.add_argument("--root", type=Path, default=project_root())
    logical_purge_apply.add_argument("--source-ref", action="append")
    logical_purge_apply.add_argument("--slice-ref", action="append")
    logical_purge_apply.add_argument("--include-projections", action="store_true")
    logical_purge_apply.add_argument("--reviewer", required=True)
    logical_purge_apply.add_argument("--notes")
    logical_purge_apply.add_argument("--policy-json-path", type=Path)
    logical_purge_apply.add_argument("--backup-json-path", type=Path)
    logical_purge_apply.add_argument("--confirm", action="store_true")

    ingest_knowledge = subcommands.add_parser("ingest-knowledge", help="Import local documents as deterministic knowledge artifacts")
    ingest_knowledge.add_argument("--root", type=Path, default=project_root())
    ingest_knowledge.add_argument("--path", type=Path, required=True)
    ingest_knowledge.add_argument("--scope-kind", default="project")
    ingest_knowledge.add_argument("--scope-value", default="ctxvault")
    ingest_knowledge.add_argument("--recursive", action="store_true")
    ingest_knowledge.add_argument("--kind")
    ingest_knowledge.add_argument("--title")

    markdown_vault_import = subcommands.add_parser(
        "markdown-vault-import",
        help="Import a local Markdown vault through the import/export bridge",
    )
    markdown_vault_import.add_argument("--root", type=Path, default=project_root())
    markdown_vault_import.add_argument("--vault-path", type=Path, required=True)
    markdown_vault_import.add_argument("--scope-kind", default="project")
    markdown_vault_import.add_argument("--scope-value", default="ctxvault")
    markdown_vault_import.add_argument("--recursive", action=argparse.BooleanOptionalAction, default=True)
    markdown_vault_import.add_argument("--kind")

    ingest_prompt = subcommands.add_parser("ingest-prompt", help="Import a local file as a prompt asset")
    ingest_prompt.add_argument("--root", type=Path, default=project_root())
    ingest_prompt.add_argument("--path", type=Path, required=True)
    ingest_prompt.add_argument("--scope-kind", default="project")
    ingest_prompt.add_argument("--scope-value", default="ctxvault")
    ingest_prompt.add_argument("--prompt-id")
    ingest_prompt.add_argument("--name")
    ingest_prompt.add_argument("--intent", default="general")
    ingest_prompt.add_argument("--owner", default="local_import")
    ingest_prompt.add_argument("--required-context-type", action="append", default=[])

    ingest_transcript = subcommands.add_parser(
        "ingest-transcript",
        help="Import transcript JSON, an export directory, or a zip archive as Session and Turn objects",
    )
    ingest_transcript.add_argument("--root", type=Path, default=project_root())
    ingest_transcript.add_argument("--path", type=Path, required=True)
    ingest_transcript.add_argument("--scope-kind", default="project")
    ingest_transcript.add_argument("--scope-value", default="ctxvault")
    ingest_transcript.add_argument("--session-id")
    ingest_transcript.add_argument("--title")
    ingest_transcript.add_argument("--task-label")
    ingest_transcript.add_argument("--client", default="local_import")

    run_audit = subcommands.add_parser("run-audit", help="Run a deterministic local-evidence audit")
    run_audit.add_argument("--root", type=Path, default=project_root())
    run_audit.add_argument("--scope-kind", default="project")
    run_audit.add_argument("--scope-value", default="ctxvault")
    run_audit.add_argument("--subject-ref", required=True)
    run_audit.add_argument("--claim-ref", action="append", default=[])
    run_audit.add_argument("--audit-id")
    run_audit.add_argument("--notes")
    run_audit.add_argument("--write-receipt", type=Path)
    run_audit.add_argument("--plan-path", type=Path)
    run_audit.add_argument("--task-id")

    review_audit = subcommands.add_parser("review-audit", help="Record a human review decision for an audit run")
    review_audit.add_argument("--root", type=Path, default=project_root())
    review_audit.add_argument("--audit-id", required=True)
    review_audit.add_argument("--decision", required=True, choices=["open", "approved", "rejected", "escalated"])
    review_audit.add_argument(
        "--verdict",
        choices=[
            "supported_by_local_evidence",
            "contradicted_by_local_evidence",
            "insufficient_local_evidence",
            "needs_human_review",
        ],
    )
    review_audit.add_argument("--notes")

    policy_check = subcommands.add_parser("policy-check", help="Evaluate a deterministic operation gate against the protection policy")
    policy_check.add_argument("--root", type=Path, default=project_root())
    policy_check.add_argument("--policy-json-path", type=Path)
    policy_check.add_argument("--backup-json-path", type=Path)
    policy_check.add_argument("--operation", required=True)
    policy_check.add_argument("--sensitivity", required=True)

    export_check = subcommands.add_parser("export-check", help="Evaluate a deterministic export gate against the protection policy")
    export_check.add_argument("--root", type=Path, default=project_root())
    export_check.add_argument("--policy-json-path", type=Path)
    export_check.add_argument("--sensitivity", required=True)
    export_check.add_argument("--exportable", choices=["true", "false"], required=True)
    export_check.add_argument("--redaction-state", default="none")
    export_check.add_argument("--secret-ref", action="append", default=[])

    e2e_smoke = subcommands.add_parser("e2e-smoke", help="Run a deterministic end-to-end smoke path over fixtures and policy gates")
    e2e_smoke.add_argument("--root", type=Path, default=project_root())
    e2e_smoke.add_argument("--policy-json-path", type=Path)
    e2e_smoke.add_argument("--backup-json-path", type=Path)

    adapter_status = subcommands.add_parser("adapter-status", help="List target-side harness adapter profiles in deterministic priority order")
    adapter_status.add_argument("--root", type=Path, default=project_root())
    adapter_status.add_argument("--profile-json-path", type=Path)

    adapter_resolve = subcommands.add_parser("adapter-resolve", help="Resolve a projection target against the adapter registry")
    adapter_resolve.add_argument("--root", type=Path, default=project_root())
    adapter_resolve.add_argument("--profile-json-path", type=Path)
    adapter_resolve.add_argument("--capability", required=True)

    adapter_healthcheck = subcommands.add_parser("adapter-healthcheck", help="Run a read-only projection adapter healthcheck")
    adapter_healthcheck.add_argument("--root", type=Path, default=project_root())
    adapter_healthcheck.add_argument(
        "--target-kind",
        default="agents-md",
        choices=[
            "agents-md",
            "harness.agents-md",
            "claude-md",
            "harness.claude-md",
            "workstream-brief",
            "human-readable-brief",
            "wiki.markdown-workstream",
        ],
    )
    adapter_healthcheck.add_argument("--target-path", type=Path)

    plugin_status = subcommands.add_parser("plugin-status", help="List plugin manifests in deterministic priority order")
    plugin_status.add_argument("--root", type=Path, default=project_root())
    plugin_status.add_argument("--plugin-json-path", type=Path)

    plugin_resolve = subcommands.add_parser("plugin-resolve", help="Resolve a capability against the plugin registry")
    plugin_resolve.add_argument("--root", type=Path, default=project_root())
    plugin_resolve.add_argument("--plugin-json-path", type=Path)
    plugin_resolve.add_argument("--capability", required=True)

    plugin_execute = subcommands.add_parser("plugin-execute", help="Execute one plugin capability through the local plugin dispatcher")
    plugin_execute.add_argument("--root", type=Path, default=project_root())
    plugin_execute.add_argument("--plugin-json-path", type=Path)
    plugin_execute.add_argument("--capability", required=True)
    plugin_execute.add_argument("--arguments-json-path", type=Path, required=True)

    emit_agents_projection = subcommands.add_parser("emit-agents-projection", help="Render an AGENTS.md projection and emit a projection receipt")
    emit_agents_projection.add_argument("--root", type=Path, default=project_root())
    emit_agents_projection.add_argument("--workstream-id", required=True)
    emit_agents_projection.add_argument("--output-path", type=Path, required=True)
    emit_agents_projection.add_argument("--receipt-output-path", type=Path, required=True)
    emit_agents_projection.add_argument("--memory-limit", type=int, default=5)
    emit_agents_projection.add_argument("--slice-ref", action="append", default=[])

    emit_claude_projection = subcommands.add_parser("emit-claude-projection", help="Render a CLAUDE.md projection and emit a projection receipt")
    emit_claude_projection.add_argument("--root", type=Path, default=project_root())
    emit_claude_projection.add_argument("--workstream-id", required=True)
    emit_claude_projection.add_argument("--output-path", type=Path, required=True)
    emit_claude_projection.add_argument("--receipt-output-path", type=Path, required=True)
    emit_claude_projection.add_argument("--memory-limit", type=int, default=5)
    emit_claude_projection.add_argument("--slice-ref", action="append", default=[])

    emit_wiki_projection = subcommands.add_parser("emit-wiki-projection", help="Render a workstream wiki markdown projection and emit a projection receipt")
    emit_wiki_projection.add_argument("--root", type=Path, default=project_root())
    emit_wiki_projection.add_argument("--workstream-id", required=True)
    emit_wiki_projection.add_argument("--output-path", type=Path, required=True)
    emit_wiki_projection.add_argument("--receipt-output-path", type=Path, required=True)
    emit_wiki_projection.add_argument("--memory-limit", type=int, default=5)
    emit_wiki_projection.add_argument("--slice-ref", action="append", default=[])

    emit_backup = subcommands.add_parser("emit-backup-receipt", help="Capture a deterministic workspace backup bundle and write a receipt")
    emit_backup.add_argument("--root", type=Path, default=project_root())
    emit_backup.add_argument("--output", type=Path, required=True)
    emit_backup.add_argument("--format", choices=["ctxvault", "plan-ledger"], default="ctxvault")
    emit_backup.add_argument("--scope-kind", default="project")
    emit_backup.add_argument("--scope-value", default="ctxvault")
    emit_backup.add_argument("--plan-id")
    emit_backup.add_argument("--target")
    emit_backup.add_argument("--max-age-hours", type=int, default=24)
    emit_backup.add_argument("--restore-tested", action="store_true")
    emit_backup.add_argument("--notes")

    snapshot_create = subcommands.add_parser("snapshot-create", help="Write a local snapshot manifest and append an operation-log entry")
    snapshot_create.add_argument("--root", type=Path, default=project_root())
    snapshot_create.add_argument("--scope-kind", default="project")
    snapshot_create.add_argument("--scope-value", default="ctxvault")
    snapshot_create.add_argument("--label")

    snapshot_list = subcommands.add_parser("snapshot-list", help="List local snapshot manifests in reverse chronological order")
    snapshot_list.add_argument("--root", type=Path, default=project_root())
    snapshot_list.add_argument("--limit", type=int, default=20)

    snapshot_diff = subcommands.add_parser("snapshot-diff", help="Compare two local snapshot manifests")
    snapshot_diff.add_argument("--root", type=Path, default=project_root())
    snapshot_diff.add_argument("--base-snapshot-id", required=True)
    snapshot_diff.add_argument("--head-snapshot-id", required=True)

    snapshot_lineage = subcommands.add_parser("snapshot-lineage", help="Show the operation-log lineage for one snapshot or all local snapshots")
    snapshot_lineage.add_argument("--root", type=Path, default=project_root())
    snapshot_lineage.add_argument("--snapshot-id")
    snapshot_lineage.add_argument("--limit", type=int, default=100)

    mutation_list = subcommands.add_parser("mutation-list", help="List high-value governed mutation records")
    mutation_list.add_argument("--root", type=Path, default=project_root())
    mutation_list.add_argument("--limit", type=int, default=50)
    mutation_list.add_argument("--mutation-kind")

    transport_dashboard = subcommands.add_parser("transport-dashboard", help="Summarize sync, trust, pairing, conflicts, and governed mutations")
    transport_dashboard.add_argument("--root", type=Path, default=project_root())
    transport_dashboard.add_argument("--sync-limit", type=int, default=20)
    transport_dashboard.add_argument("--mutation-limit", type=int, default=10)
    transport_dashboard.add_argument("--pairing-limit", type=int, default=10)
    transport_dashboard.add_argument("--conflict-limit", type=int, default=10)
    transport_dashboard.add_argument("--include-expired-pairings", action="store_true")

    companion_sync_feed = subcommands.add_parser("companion-sync-feed", help="Render a mobile-safe sync feed over transport, pairing, trust, and conflict state")
    companion_sync_feed.add_argument("--root", type=Path, default=project_root())
    companion_sync_feed.add_argument("--activity-limit", type=int, default=12)
    companion_sync_feed.add_argument("--target-limit", type=int, default=6)
    companion_sync_feed.add_argument("--pairing-limit", type=int, default=6)
    companion_sync_feed.add_argument("--conflict-limit", type=int, default=6)

    snapshot_provenance = subcommands.add_parser("snapshot-provenance", help="Show local provenance for one snapshot, including replica source metadata when available")
    snapshot_provenance.add_argument("--root", type=Path, default=project_root())
    snapshot_provenance.add_argument("--snapshot-id", required=True)
    snapshot_provenance.add_argument("--limit", type=int, default=100)

    snapshot_restore_plan = subcommands.add_parser("snapshot-restore-plan", help="Create a dry-run restore plan from the current state back to a local snapshot")
    snapshot_restore_plan.add_argument("--root", type=Path, default=project_root())
    snapshot_restore_plan.add_argument("--snapshot-id", required=True)
    snapshot_restore_plan.add_argument("--workspace-only", action="store_true")
    snapshot_restore_plan.add_argument("--vault-only", action="store_true")

    snapshot_restore_apply = subcommands.add_parser("snapshot-restore-apply", help="Apply a local snapshot restore bundle with explicit delete review gating")
    snapshot_restore_apply.add_argument("--root", type=Path, default=project_root())
    snapshot_restore_apply.add_argument("--snapshot-id", required=True)
    snapshot_restore_apply.add_argument("--workspace-only", action="store_true")
    snapshot_restore_apply.add_argument("--vault-only", action="store_true")
    snapshot_restore_apply.add_argument("--allow-deletes", action="store_true")
    snapshot_restore_apply.add_argument("--reviewed-by")
    snapshot_restore_apply.add_argument("--no-refresh-indexes", action="store_true")

    emit_sync_receipt = subcommands.add_parser("emit-sync-receipt", help="Record that a snapshot was copied or synced to another local target")
    emit_sync_receipt.add_argument("--root", type=Path, default=project_root())
    emit_sync_receipt.add_argument("--snapshot-id", required=True)
    emit_sync_receipt.add_argument("--target", required=True)
    emit_sync_receipt.add_argument("--transport", default="local_copy")
    emit_sync_receipt.add_argument("--device-id")
    emit_sync_receipt.add_argument("--notes")

    emit_sync_manifest = subcommands.add_parser("emit-sync-manifest", help="Write a sync manifest for the current effective local snapshot")
    emit_sync_manifest.add_argument("--root", type=Path, default=project_root())
    emit_sync_manifest.add_argument("--target", required=True)
    emit_sync_manifest.add_argument("--transport", default="local_copy")
    emit_sync_manifest.add_argument("--device-id")
    emit_sync_manifest.add_argument("--snapshot-id")
    emit_sync_manifest.add_argument("--notes")

    apply_sync_manifest = subcommands.add_parser("apply-sync-manifest", help="Copy the artifacts referenced by a sync manifest into its local target directory")
    apply_sync_manifest.add_argument("--root", type=Path, default=project_root())
    apply_sync_manifest.add_argument("--sync-manifest-path", type=Path, required=True)

    local_backup_write = subcommands.add_parser("local-backup-write", help="Create a snapshot, copy it to a local backup target, and verify the replica")
    local_backup_write.add_argument("--root", type=Path, default=project_root())
    local_backup_write.add_argument("--target", required=True)
    local_backup_write.add_argument("--scope-kind", default="project")
    local_backup_write.add_argument("--scope-value", default="ctxvault")
    local_backup_write.add_argument("--label")
    local_backup_write.add_argument("--transport", default="local_copy")
    local_backup_write.add_argument("--device-id")
    local_backup_write.add_argument("--notes")

    replica_verify = subcommands.add_parser("replica-verify", help="Verify a copied local replica target contains a complete snapshot and restore bundle")
    replica_verify.add_argument("--root", type=Path, default=project_root())
    replica_verify.add_argument("--replica-root", type=Path, required=True)
    replica_verify.add_argument("--snapshot-id")
    replica_verify.add_argument("--sync-manifest-path", type=Path)

    replica_import = subcommands.add_parser("replica-import", help="Import a verified local replica snapshot into the current workspace exports")
    replica_import.add_argument("--root", type=Path, default=project_root())
    replica_import.add_argument("--replica-root", type=Path, required=True)
    replica_import.add_argument("--snapshot-id")
    replica_import.add_argument("--sync-manifest-path", type=Path)
    replica_import.add_argument("--trust-policy-json-path", type=Path)
    replica_import.add_argument("--reviewed-by")

    replica_apply = subcommands.add_parser("replica-apply", help="Verify, import, and apply a local replica snapshot into the current workspace")
    replica_apply.add_argument("--root", type=Path, default=project_root())
    replica_apply.add_argument("--replica-root", type=Path, required=True)
    replica_apply.add_argument("--snapshot-id")
    replica_apply.add_argument("--sync-manifest-path", type=Path)
    replica_apply.add_argument("--trust-policy-json-path", type=Path)
    replica_apply.add_argument("--workspace-only", action="store_true")
    replica_apply.add_argument("--vault-only", action="store_true")
    replica_apply.add_argument("--allow-deletes", action="store_true")
    replica_apply.add_argument("--reviewed-by")
    replica_apply.add_argument("--no-refresh-indexes", action="store_true")

    replica_trust_evaluate = subcommands.add_parser("replica-trust-evaluate", help="Evaluate receiver-side trust policy for a copied local replica")
    replica_trust_evaluate.add_argument("--root", type=Path, default=project_root())
    replica_trust_evaluate.add_argument("--replica-root", type=Path, required=True)
    replica_trust_evaluate.add_argument("--snapshot-id")
    replica_trust_evaluate.add_argument("--sync-manifest-path", type=Path)
    replica_trust_evaluate.add_argument("--trust-policy-json-path", type=Path)

    replica_trust_list = subcommands.add_parser("replica-trust-list", help="List persisted receiver-side device trust entries")
    replica_trust_list.add_argument("--root", type=Path, default=project_root())

    replica_trust_set = subcommands.add_parser("replica-trust-set", help="Persist or update one receiver-side device trust entry")
    replica_trust_set.add_argument("--root", type=Path, default=project_root())
    replica_trust_set.add_argument("--device-id", required=True)
    replica_trust_set.add_argument("--trust-state", required=True, choices=["allow", "review", "block"])
    replica_trust_set.add_argument("--label")
    replica_trust_set.add_argument("--notes")
    replica_trust_set.add_argument("--allowed-transport", action="append", default=[])

    replica_pairing_offer = subcommands.add_parser("replica-pairing-offer", help="Emit an explicit device pairing offer for later trust acceptance")
    replica_pairing_offer.add_argument("--root", type=Path, default=project_root())
    replica_pairing_offer.add_argument("--device-id", required=True)
    replica_pairing_offer.add_argument("--label")
    replica_pairing_offer.add_argument("--notes")
    replica_pairing_offer.add_argument("--allowed-transport", action="append", default=[])
    replica_pairing_offer.add_argument("--pairing-id")
    replica_pairing_offer.add_argument("--expires-in-hours", type=int, default=24)

    replica_pairing_list = subcommands.add_parser("replica-pairing-list", help="List stored pairing offers")
    replica_pairing_list.add_argument("--root", type=Path, default=project_root())
    replica_pairing_list.add_argument("--limit", type=int, default=50)
    replica_pairing_list.add_argument("--include-expired", action="store_true")

    replica_pairing_accept = subcommands.add_parser("replica-pairing-accept", help="Accept one pairing offer into the local trust registry")
    replica_pairing_accept.add_argument("--root", type=Path, default=project_root())
    replica_pairing_accept.add_argument("--pairing-offer-path", type=Path, required=True)
    replica_pairing_accept.add_argument("--trust-state", default="allow", choices=["allow", "review", "block"])
    replica_pairing_accept.add_argument("--reviewed-by", required=True)
    replica_pairing_accept.add_argument("--label")
    replica_pairing_accept.add_argument("--notes")

    sync_status = subcommands.add_parser("sync-status", help="Summarize the latest sync receipt per local target or device")
    sync_status.add_argument("--root", type=Path, default=project_root())
    sync_status.add_argument("--limit", type=int, default=50)

    sync_conflict_list = subcommands.add_parser("sync-conflict-list", help="List explicit sync conflict markers that require or record human review")
    sync_conflict_list.add_argument("--root", type=Path, default=project_root())
    sync_conflict_list.add_argument("--limit", type=int, default=50)
    sync_conflict_list.add_argument("--status")

    doctor = subcommands.add_parser("doctor", help="Run read-only local diagnostics")
    doctor.add_argument("--root", type=Path, default=project_root())

    serve_mcp = subcommands.add_parser("serve-mcp", help="Run the stdio MCP transport over the named deterministic surface")
    serve_mcp.add_argument("--root", type=Path, default=project_root())
    serve_mcp.add_argument("--policy-json-path", type=Path)
    serve_mcp.add_argument("--backup-json-path", type=Path)
    serve_mcp.add_argument("--profile-json-path", type=Path)
    serve_mcp.add_argument("--plugin-json-path", type=Path)

    if has_workbench_surface():
        workbench = subcommands.add_parser("workbench", help="Run the local HTTP workbench over the deterministic surface")
        workbench.add_argument("--root", type=Path, default=project_root())
        workbench.add_argument("--host", default="127.0.0.1")
        workbench.add_argument("--port", type=int, default=8765)

    subcommands.add_parser("check", help="Run deterministic scaffold checks")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    def default_policy_path(root: Path) -> Path:
        return resolve_fixture_path(root, "controls", "protection-policy.json")

    def default_backup_path(root: Path) -> Path:
        return resolve_fixture_path(root, "controls", "backup-check-receipt.json")

    def default_adapter_profile_path(root: Path) -> Path:
        return resolve_fixture_path(root, "evidence", "adapter-capability-profile.json")

    def default_plugin_manifest_path(root: Path) -> Path:
        return resolve_fixture_path(root, "evidence", "plugin-manifest.json")

    def load_stored_payload(root: Path, object_kind: str, object_id: str) -> dict:
        path = default_layout(root).objects_dir / object_kind / f"{object_id}.json"
        envelope = json.loads(path.read_text(encoding="utf-8"))
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"stored payload for {object_kind} {object_id} is invalid")
        return payload

    try:
        if args.command == "print-layout":
            layout = default_layout(args.root.resolve())
            print(json.dumps(layout.as_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "show-config":
            config = load_config(args.config.resolve())
            print(json.dumps(config, default=lambda value: value.__dict__, indent=2, sort_keys=True))
            return 0

        if args.command == "init-vault":
            vault = CtxVault(default_layout(args.root.resolve()))
            layout = vault.initialize()
            print(json.dumps(layout.as_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "seed-fixtures":
            root = args.root.resolve()
            vault = CtxVault(default_layout(root))
            envelopes = vault.import_core_fixtures(resolve_fixture_path(root, "core"))
            print(
                json.dumps(
                    [
                        {
                            "object_id": envelope.object_id,
                            "object_kind": envelope.object_kind,
                            "storage_ref": envelope.storage_ref,
                        }
                        for envelope in envelopes
                    ],
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "trace-record":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            payload = json.loads(args.json_path.resolve().read_text())
            result = surface.trace_record(args.model_name, payload)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "prompt-resolve":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.prompt_resolve(args.prompt_id)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "session-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.session_list(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "session-search":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.session_search(
                args.query,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "session-related":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.session_related(
                args.session_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "session-aggregate-preview":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.session_aggregate_preview(
                args.session_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "workstream-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.workstream_list(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                status=args.status,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "workstream-preview":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.workstream_preview(
                args.session_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "workstream-intelligence":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.workstream_intelligence(
                args.workstream_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "compiled-workstream-state":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.compiled_workstream_state(
                args.workstream_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "workstream-candidate-create":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.workstream_candidate_create(
                args.session_id,
                limit=args.limit,
                candidate_id=args.candidate_id,
                candidate_for=args.candidate_for,
                title=args.title,
                summary=args.summary,
                rationale=args.rationale,
                notes=args.notes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "workstream-candidate-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.workstream_candidate_list(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                proposal_state=args.proposal_state,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "review-workstream-candidate":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            policy_payload = None
            backup_payload = None
            if args.decision == "approved":
                policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(project_root())
                backup_path = args.backup_json_path.resolve() if args.backup_json_path else default_backup_path(project_root())
                if not policy_path.exists():
                    raise ValueError(f"missing policy payload at {policy_path}")
                if not backup_path.exists():
                    raise ValueError(f"missing backup receipt at {backup_path}")
                policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
                backup_payload = CtxVaultPolicy.load_backup_receipt(backup_path, refresh_timestamps=args.backup_json_path is None)

            result = surface.workstream_candidate_review(
                args.candidate_id,
                decision=args.decision,
                reviewer=args.reviewer,
                notes=args.notes,
                workstream_id=args.workstream_id,
                policy_payload=policy_payload,
                backup_receipt=backup_payload,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-workstream-receipt":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            workstream = load_stored_payload(root, "workstream", args.workstream_id)
            output_path = args.output_path if args.output_path.is_absolute() else root / args.output_path
            result = surface.workstream_receipt_emit(
                workstream,
                output_path=output_path.resolve(),
                plan_path=args.plan_path.resolve() if args.plan_path is not None else None,
                task_id=args.task_id,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-workstream-candidate-receipt":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            candidate = load_stored_payload(root, "workstream_candidate", args.candidate_id)
            output_path = args.output_path if args.output_path.is_absolute() else root / args.output_path
            result = surface.workstream_candidate_receipt_emit(
                candidate,
                output_path=output_path.resolve(),
                plan_path=args.plan_path.resolve() if args.plan_path is not None else None,
                task_id=args.task_id,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "episode-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.episode_list(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                session_id=args.session_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "derive-episodes":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.episode_derive(args.session_id)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "synthesize-episode":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.episode_synthesize(
                args.episode_id,
                knowledge_id=args.knowledge_id,
                title=args.title,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "export-knowledge-note":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            output_path = args.output_path if args.output_path.is_absolute() else root / args.output_path
            result = surface.knowledge_export_note(
                args.knowledge_id,
                output_path=output_path.resolve(),
                canonical_target=args.canonical_target,
                privacy=args.privacy,
                status=args.status,
                note_id=args.note_id,
                title=args.title,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "memory-search":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.memory_search(
                args.query,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                limit=args.limit,
                pinned_only=args.pinned_only,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "memory-candidate-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.memory_candidate_list(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                proposal_state=args.proposal_state,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "review-memory-candidate":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            policy_payload = None
            backup_payload = None
            if args.decision == "approved":
                policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(project_root())
                backup_path = args.backup_json_path.resolve() if args.backup_json_path else default_backup_path(project_root())
                if not policy_path.exists():
                    raise ValueError(f"missing policy payload at {policy_path}")
                if not backup_path.exists():
                    raise ValueError(f"missing backup receipt at {backup_path}")
                policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
                backup_payload = CtxVaultPolicy.load_backup_receipt(backup_path, refresh_timestamps=args.backup_json_path is None)

            result = surface.memory_candidate_review(
                args.candidate_id,
                decision=args.decision,
                reviewer=args.reviewer,
                notes=args.notes,
                memory_id=args.memory_id,
                policy_payload=policy_payload,
                backup_receipt=backup_payload,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "prompt-patch-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.prompt_patch_list(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                proposal_state=args.proposal_state,
                prompt_asset_id=args.prompt_asset_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "prompt-patch-density-check":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.prompt_patch_density_check(args.patch_id)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "review-prompt-patch":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            policy_payload = None
            backup_payload = None
            if args.decision == "approved":
                policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(project_root())
                backup_path = args.backup_json_path.resolve() if args.backup_json_path else default_backup_path(project_root())
                if not policy_path.exists():
                    raise ValueError(f"missing policy payload at {policy_path}")
                if not backup_path.exists():
                    raise ValueError(f"missing backup receipt at {backup_path}")
                policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
                backup_payload = CtxVaultPolicy.load_backup_receipt(backup_path, refresh_timestamps=args.backup_json_path is None)

            result = surface.prompt_patch_review(
                args.patch_id,
                decision=args.decision,
                reviewer=args.reviewer,
                notes=args.notes,
                policy_payload=policy_payload,
                backup_receipt=backup_payload,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "prompt-eval-run":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.prompt_eval_run(
                args.target_type,
                args.target_id,
                dataset_ref=args.dataset_ref,
                assert_contains=args.assert_contains,
                assert_not_contains=args.assert_not_contains,
                notes=args.notes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "privacy-scan":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            text = args.text if args.text is not None else args.text_path.resolve().read_text(encoding="utf-8")
            result = surface.privacy_scan(
                text,
                source=args.source,
                max_findings=args.max_findings,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "privacy-scan-files":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.privacy_scan_files(
                [path.resolve() for path in args.file_path],
                source=args.source,
                max_findings=args.max_findings,
                max_bytes=args.max_bytes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "share-handoff-stage":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            text = args.text if args.text is not None else (
                args.text_path.resolve().read_text(encoding="utf-8") if args.text_path is not None else None
            )
            metadata = json.loads(args.metadata_json_path.resolve().read_text(encoding="utf-8")) if args.metadata_json_path else None
            if metadata is not None and not isinstance(metadata, dict):
                raise ValueError("share handoff metadata must be a JSON object")
            result = surface.companion_share_handoff_stage(
                shared_root=args.shared_root,
                title=args.title,
                text=text,
                urls=args.url or None,
                attachment_paths=[str(path) for path in args.attachment_path] or None,
                source_app=args.source_app,
                source_surface=args.source_surface,
                source_format=args.source_format,
                capture_method=args.capture_method,
                imported_via=args.imported_via,
                notes=args.notes,
                metadata=metadata,
                handoff_id=args.handoff_id,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "share-handoff-list":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.companion_share_handoff_list(
                shared_root=args.shared_root,
                limit=args.limit,
                include_archived=bool(args.include_archived),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "share-handoff-preview":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.companion_share_handoff_preview(
                handoff_path=args.handoff_path,
                shared_root=args.shared_root,
                max_findings=args.max_findings,
                max_bytes=args.max_bytes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "share-handoff-consume":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.companion_share_handoff_consume(
                handoff_path=args.handoff_path,
                why_it_matters=args.why_it_matters,
                shared_root=args.shared_root,
                statement=args.statement,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                candidate_type=args.candidate_type,
                confidence=args.confidence,
                candidate_for=args.candidate_for,
                sensitivity=args.sensitivity,
                redaction_state=args.redaction_state,
                exportable=args.exportable == "true",
                notes=args.notes,
                reviewed_by=args.reviewed_by,
                allow_blocked=bool(args.allow_blocked),
                max_findings=args.max_findings,
                max_bytes=args.max_bytes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "knowledge-search":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.knowledge_search(
                args.query,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-slice-rebuild":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_slice_rebuild()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-search":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_search(
                args.query,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                workstream_ref=args.workstream_ref,
                limit=args.limit,
                include_blocked=args.include_blocked,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-selection-preflight":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_selection_preflight(
                args.slice_ref,
                target_kind=args.target_kind,
                query=args.query,
                workstream_ref=args.workstream_ref,
                write_receipt=args.write_receipt,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-selection-compose":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_selection_compose(
                args.query,
                target_kind=args.target_kind,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                workstream_ref=args.workstream_ref,
                selected_slice_refs=args.slice_ref,
                candidate_slice_refs=args.candidate_slice_ref,
                required_slice_refs=args.required_slice_ref,
                limit=args.limit,
                token_budget=args.token_budget,
                include_blocked=args.include_blocked,
                write_receipt=args.write_receipt,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-prepare":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_prepare(
                args.query,
                target_kind=args.target_kind,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                workstream_ref=args.workstream_ref,
                selected_slice_refs=args.slice_ref,
                required_slice_refs=args.required_slice_ref,
                limit=args.limit,
                token_budget=args.token_budget,
                include_blocked=args.include_blocked,
                rebuild=args.rebuild,
                write_receipt=args.write_receipt,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-project":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            output_path = None
            if args.output_path is not None:
                output_path = args.output_path.resolve() if args.output_path.is_absolute() else (root / args.output_path).resolve()
            receipt_output_path = None
            if args.receipt_output_path is not None:
                receipt_output_path = (
                    args.receipt_output_path.resolve()
                    if args.receipt_output_path.is_absolute()
                    else (root / args.receipt_output_path).resolve()
                )
            result = surface.context_project(
                target=args.target,
                workstream_id=args.workstream_id,
                output_path=output_path,
                receipt_output_path=receipt_output_path,
                memory_limit=args.memory_limit,
                selected_slice_refs=args.slice_ref,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-extract":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_extract(
                source_paths=[path.resolve() for path in args.source_path],
                source_kind=args.source_kind,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                recursive=args.recursive,
                kind=args.kind,
                title=args.title,
                prompt_id=args.prompt_id,
                prompt_name=args.prompt_name,
                prompt_intent=args.prompt_intent,
                prompt_owner=args.prompt_owner,
                prompt_required_context_types=args.prompt_required_context_type,
                transcript_session_id=args.transcript_session_id,
                transcript_title=args.transcript_title,
                transcript_task_label=args.transcript_task_label,
                transcript_client=args.transcript_client,
                prepare_query=args.prepare_query,
                target_kind=args.target_kind,
                workstream_ref=args.workstream_ref,
                selected_slice_refs=args.slice_ref,
                required_slice_refs=args.required_slice_ref,
                limit=args.limit,
                token_budget=args.token_budget,
                include_blocked=args.include_blocked,
                project_targets=args.project_target,
                workstream_id=args.workstream_id,
                dry_run=args.dry_run,
                write_receipt=args.write_receipt,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "oss-case-study-preview":
            root = args.root.resolve()
            output_dir = None
            if args.output_dir is not None:
                output_dir = args.output_dir if args.output_dir.is_absolute() else root / args.output_dir
            source_path = None
            if args.source_path is not None:
                source_path = args.source_path if args.source_path.is_absolute() else root / args.source_path
            result = build_oss_case_study_preview(
                root=root,
                target_name=args.target_name,
                repo_url=args.repo_url,
                pinned_ref=args.pinned_ref,
                source_path=source_path,
                output_dir=output_dir,
                checked_at_utc=args.checked_at_utc,
                license_name=args.license,
                allow_network=args.allow_network,
                max_source_bytes=args.max_source_bytes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1 if result.get("status") == "blocked_network_not_approved" else 0

        if args.command == "receipt-inspect":
            root = args.root.resolve()
            receipt_path = None
            if args.receipt_path is not None:
                receipt_path = args.receipt_path.resolve() if args.receipt_path.is_absolute() else (root / args.receipt_path).resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.receipt_inspect(
                receipt_path=receipt_path,
                receipt_ref=args.receipt_ref,
                latest=args.latest,
                include_payload=args.include_payload,
            )
            if args.summary:
                print(result["summary_text"])
            else:
                print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-slice-preference-set":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_slice_preference_set(
                slice_ref=args.slice_ref,
                action=args.action,
                target_kind=args.target_kind,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                note=args.note,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "context-slice-preference-list":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.context_slice_preference_list(
                target_kind=args.target_kind,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "logical-purge-plan":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            result = surface.logical_purge_plan(
                source_refs=args.source_ref,
                slice_refs=args.slice_ref,
                include_projections=args.include_projections,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "logical-purge-apply":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(project_root())
            backup_path = args.backup_json_path.resolve() if args.backup_json_path else default_backup_path(project_root())
            if not policy_path.exists():
                raise ValueError(f"missing policy payload at {policy_path}")
            if not backup_path.exists():
                raise ValueError(f"missing backup receipt at {backup_path}")
            policy_payload = json.loads(policy_path.read_text(encoding="utf-8"))
            backup_payload = CtxVaultPolicy.load_backup_receipt(
                backup_path,
                refresh_timestamps=args.backup_json_path is None,
            )
            result = surface.logical_purge_apply(
                source_refs=args.source_ref,
                slice_refs=args.slice_ref,
                include_projections=args.include_projections,
                reviewer=args.reviewer,
                notes=args.notes,
                policy_payload=policy_payload,
                backup_receipt=backup_payload,
                confirm=args.confirm,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "ingest-knowledge":
            vault = CtxVault(default_layout(args.root.resolve()))
            receipts = import_knowledge_path(
                vault,
                args.path.resolve(),
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                recursive=args.recursive,
                kind=args.kind,
                title=args.title,
            )
            print(json.dumps([receipt.to_dict() for receipt in receipts], indent=2, sort_keys=True))
            return 0

        if args.command == "markdown-vault-import":
            vault = CtxVault(default_layout(args.root.resolve()))
            receipts = import_knowledge_path(
                vault,
                args.vault_path.resolve(),
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                recursive=args.recursive,
                kind=args.kind,
                extensions=(".markdown", ".md"),
            )
            print(json.dumps([receipt.to_dict() for receipt in receipts], indent=2, sort_keys=True))
            return 0

        if args.command == "ingest-prompt":
            vault = CtxVault(default_layout(args.root.resolve()))
            receipt = import_prompt_path(
                vault,
                args.path.resolve(),
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                prompt_id=args.prompt_id,
                name=args.name,
                intent=args.intent,
                owner=args.owner,
                required_context_types=args.required_context_type,
            )
            print(json.dumps(receipt.to_dict(), indent=2, sort_keys=True))
            return 0

        if args.command == "ingest-transcript":
            vault = CtxVault(default_layout(args.root.resolve()))
            receipts = import_conversation_path(
                vault,
                args.path.resolve(),
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                session_id=args.session_id,
                title=args.title,
                task_label=args.task_label,
                client=args.client,
                imported_via="ctxvault_cli",
            )
            if len(receipts) == 1:
                payload = receipts[0].to_dict()
            else:
                payload = [receipt.to_dict() for receipt in receipts]
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        if args.command == "build-context":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            bundle = surface.vault.build_context(
                ContextBuildRequest(
                    scope_kind=args.scope_kind,
                    scope_value=args.scope_value,
                    task_label=args.task_label,
                    prompt_id=args.prompt_id,
                    session_id=args.session_id,
                    memory_query=args.memory_query,
                    knowledge_query=args.knowledge_query,
                    max_memories=args.max_memories,
                    max_knowledge=args.max_knowledge,
                    max_recent_turns=args.max_recent_turns,
                    token_budget=args.token_budget,
                )
            )
            payload: dict[str, object] = {"bundle": bundle}
            if args.write_receipt is not None:
                receipt = surface.context_receipt_emit(
                    bundle,
                    output_path=args.write_receipt.resolve(),
                    plan_path=args.plan_path.resolve() if args.plan_path is not None else None,
                    task_id=args.task_id,
                )
                payload["receipt"] = receipt["receipt"]
                payload["receipt_path"] = receipt["receipt_path"]
            print(json.dumps(payload if args.write_receipt is not None else bundle, indent=2, sort_keys=True))
            return 0

        if args.command == "seed-evidence-fixtures":
            root = args.root.resolve()
            vault = CtxVault(default_layout(root))
            envelopes = [
                vault.import_governance_fixture(resolve_fixture_path(root, "evidence", "claim-record.json"), "ClaimRecord"),
                vault.import_governance_fixture(resolve_fixture_path(root, "evidence", "evidence-link.json"), "EvidenceLink"),
            ]
            print(
                json.dumps(
                    [
                        {
                            "object_id": envelope.object_id,
                            "object_kind": envelope.object_kind,
                            "storage_ref": envelope.storage_ref,
                        }
                        for envelope in envelopes
                    ],
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "run-audit":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            audit = surface.audit_run(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                subject_ref=args.subject_ref,
                claim_refs=args.claim_ref or None,
                audit_id=args.audit_id,
                notes=args.notes,
            )
            payload = audit
            if args.write_receipt is not None:
                receipt = surface.audit_receipt_emit(
                    audit,
                    output_path=args.write_receipt.resolve(),
                    plan_path=args.plan_path.resolve() if args.plan_path is not None else None,
                    task_id=args.task_id,
                )
                payload = {
                    "audit": audit,
                    "receipt": receipt["receipt"],
                    "receipt_path": receipt["receipt_path"],
                }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        if args.command == "review-audit":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            audit = surface.audit_review(
                args.audit_id,
                decision=args.decision,
                notes=args.notes,
                override_verdict=args.verdict,
            )
            print(json.dumps(audit, indent=2, sort_keys=True))
            return 0

        if args.command == "policy-check":
            root = args.root.resolve()
            policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(root)
            backup_path = args.backup_json_path.resolve() if args.backup_json_path else default_backup_path(root)
            policy_payload = json.loads(policy_path.read_text())
            backup_payload = (
                CtxVaultPolicy.load_backup_receipt(backup_path, refresh_timestamps=args.backup_json_path is None)
                if backup_path.exists()
                else None
            )
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            decision = surface.policy_check(
                policy_payload=policy_payload,
                operation=args.operation,
                sensitivity=args.sensitivity,
                backup_receipt=backup_payload,
            )
            print(json.dumps(decision, indent=2, sort_keys=True))
            return 0

        if args.command == "export-check":
            root = args.root.resolve()
            policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(root)
            policy_payload = json.loads(policy_path.read_text())
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            decision = surface.export_check(
                policy_payload=policy_payload,
                sensitivity=args.sensitivity,
                exportable=args.exportable == "true",
                redaction_state=args.redaction_state,
                secret_refs=args.secret_ref,
            )
            print(json.dumps(decision, indent=2, sort_keys=True))
            return 0

        if args.command == "e2e-smoke":
            root = args.root.resolve()
            policy_path = args.policy_json_path.resolve() if args.policy_json_path else default_policy_path(root)
            backup_path = args.backup_json_path.resolve() if args.backup_json_path else default_backup_path(root)
            policy_payload = json.loads(policy_path.read_text())
            backup_payload = (
                CtxVaultPolicy.load_backup_receipt(backup_path, refresh_timestamps=args.backup_json_path is None)
                if backup_path.exists()
                else None
            )
            surface = CtxVaultSurface(CtxVault(default_layout(root)))

            core_envelopes = surface.vault.import_core_fixtures(resolve_fixture_path(root, "core"))
            claim_envelope = surface.vault.import_governance_fixture(
                resolve_fixture_path(root, "evidence", "claim-record.json"),
                "ClaimRecord",
            )
            evidence_envelope = surface.vault.import_governance_fixture(
                resolve_fixture_path(root, "evidence", "evidence-link.json"),
                "EvidenceLink",
            )

            bundle = surface.context_build(
                {
                    "scope_kind": "project",
                    "scope_value": "ctxvault",
                    "task_label": "deterministic e2e smoke",
                    "prompt_id": "prompt_schema_designer_v1",
                    "memory_query": "local LLM",
                    "knowledge_query": "local-first context layer",
                }
            )
            audit = surface.audit_run(
                scope_kind="project",
                scope_value="ctxvault",
                subject_ref="turn://sess_20260419_ctxvault_001/8",
            )
            operation_gate = surface.policy_check(
                policy_payload=policy_payload,
                operation="memory_promotion",
                sensitivity="internal",
                backup_receipt=backup_payload,
            )
            export_gate = surface.export_check(
                policy_payload=policy_payload,
                sensitivity=bundle["sensitivity"],
                exportable=bool(bundle["exportable"]),
                redaction_state=str(bundle["redaction_state"]),
                secret_refs=list(bundle.get("secret_refs", [])),
            )

            print(
                json.dumps(
                    {
                        "seeded_core_objects": [envelope.object_id for envelope in core_envelopes],
                        "seeded_claim_id": claim_envelope.object_id,
                        "seeded_evidence_id": evidence_envelope.object_id,
                        "bundle_id": bundle["id"],
                        "audit_id": audit["id"],
                        "operation_gate": operation_gate,
                        "export_gate": export_gate,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "adapter-status":
            root = args.root.resolve()
            profile_path = args.profile_json_path.resolve() if args.profile_json_path else default_adapter_profile_path(root)
            profiles_payload = json.loads(profile_path.read_text())
            profiles = profiles_payload if isinstance(profiles_payload, list) else [profiles_payload]
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            print(json.dumps(surface.adapter_status(profiles), indent=2, sort_keys=True))
            return 0

        if args.command == "adapter-resolve":
            root = args.root.resolve()
            profile_path = args.profile_json_path.resolve() if args.profile_json_path else default_adapter_profile_path(root)
            profiles_payload = json.loads(profile_path.read_text())
            profiles = profiles_payload if isinstance(profiles_payload, list) else [profiles_payload]
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            print(json.dumps(surface.adapter_resolve(profiles, args.capability), indent=2, sort_keys=True))
            return 0

        if args.command == "adapter-healthcheck":
            root = args.root.resolve()
            target_path = None
            if args.target_path is not None:
                target_path = args.target_path.resolve() if args.target_path.is_absolute() else (root / args.target_path).resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            print(
                json.dumps(
                    surface.adapter_healthcheck(target_kind=args.target_kind, target_path=target_path),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0

        if args.command == "plugin-status":
            root = args.root.resolve()
            plugin_path = args.plugin_json_path.resolve() if args.plugin_json_path else default_plugin_manifest_path(root)
            manifests_payload = json.loads(plugin_path.read_text())
            manifests = manifests_payload if isinstance(manifests_payload, list) else [manifests_payload]
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            print(json.dumps(surface.plugin_status(manifests), indent=2, sort_keys=True))
            return 0

        if args.command == "plugin-resolve":
            root = args.root.resolve()
            plugin_path = args.plugin_json_path.resolve() if args.plugin_json_path else default_plugin_manifest_path(root)
            manifests_payload = json.loads(plugin_path.read_text())
            manifests = manifests_payload if isinstance(manifests_payload, list) else [manifests_payload]
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            print(json.dumps(surface.plugin_resolve(manifests, args.capability), indent=2, sort_keys=True))
            return 0

        if args.command == "plugin-execute":
            root = args.root.resolve()
            plugin_path = args.plugin_json_path.resolve() if args.plugin_json_path else default_plugin_manifest_path(root)
            manifests_payload = json.loads(plugin_path.read_text())
            manifests = manifests_payload if isinstance(manifests_payload, list) else [manifests_payload]
            arguments_path = args.arguments_json_path.resolve()
            arguments = json.loads(arguments_path.read_text())
            if not isinstance(arguments, dict):
                raise ValueError("plugin execute arguments must be a JSON object")
            for field in ("output_path", "receipt_output_path"):
                if field in arguments:
                    raw_path = Path(str(arguments[field]))
                    arguments[field] = str(raw_path if raw_path.is_absolute() else (root / raw_path).resolve())
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            print(json.dumps(surface.plugin_execute(manifests, args.capability, arguments), indent=2, sort_keys=True))
            return 0

        if args.command == "emit-agents-projection":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.harness_agents_md_emit(
                workstream_id=args.workstream_id,
                output_path=args.output_path.resolve() if args.output_path.is_absolute() else (root / args.output_path).resolve(),
                receipt_output_path=(
                    args.receipt_output_path.resolve()
                    if args.receipt_output_path.is_absolute()
                    else (root / args.receipt_output_path).resolve()
                ),
                memory_limit=args.memory_limit,
                selected_slice_refs=args.slice_ref,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-claude-projection":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.harness_claude_md_emit(
                workstream_id=args.workstream_id,
                output_path=args.output_path.resolve() if args.output_path.is_absolute() else (root / args.output_path).resolve(),
                receipt_output_path=(
                    args.receipt_output_path.resolve()
                    if args.receipt_output_path.is_absolute()
                    else (root / args.receipt_output_path).resolve()
                ),
                memory_limit=args.memory_limit,
                selected_slice_refs=args.slice_ref,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-wiki-projection":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.wiki_workstream_markdown_emit(
                workstream_id=args.workstream_id,
                output_path=args.output_path.resolve() if args.output_path.is_absolute() else (root / args.output_path).resolve(),
                receipt_output_path=(
                    args.receipt_output_path.resolve()
                    if args.receipt_output_path.is_absolute()
                    else (root / args.receipt_output_path).resolve()
                ),
                memory_limit=args.memory_limit,
                selected_slice_refs=args.slice_ref,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-backup-receipt":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.backup_emit(
                root=root,
                output_path=args.output.resolve(),
                receipt_format=args.format,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                max_age_hours=args.max_age_hours,
                restore_tested=args.restore_tested,
                notes=args.notes,
                plan_id=args.plan_id,
                target=args.target,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-create":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_create(
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                label=args.label,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-list":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_list(limit=args.limit)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-diff":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_diff(
                base_snapshot_id=args.base_snapshot_id,
                head_snapshot_id=args.head_snapshot_id,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-lineage":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_lineage(
                snapshot_id=args.snapshot_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "mutation-list":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.mutation_list(
                limit=args.limit,
                mutation_kind=args.mutation_kind,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "transport-dashboard":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.transport_dashboard(
                sync_limit=args.sync_limit,
                mutation_limit=args.mutation_limit,
                pairing_limit=args.pairing_limit,
                conflict_limit=args.conflict_limit,
                include_expired_pairings=bool(args.include_expired_pairings),
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "companion-sync-feed":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.companion_sync_feed(
                activity_limit=args.activity_limit,
                target_limit=args.target_limit,
                pairing_limit=args.pairing_limit,
                conflict_limit=args.conflict_limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-provenance":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_provenance(
                snapshot_id=args.snapshot_id,
                limit=args.limit,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-restore-plan":
            if args.workspace_only and args.vault_only:
                raise ValueError("snapshot restore plan cannot be both workspace-only and vault-only")
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_restore_plan(
                snapshot_id=args.snapshot_id,
                include_workspace=not args.vault_only,
                include_vault=not args.workspace_only,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "snapshot-restore-apply":
            if args.workspace_only and args.vault_only:
                raise ValueError("snapshot restore apply cannot be both workspace-only and vault-only")
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.snapshot_restore_apply(
                snapshot_id=args.snapshot_id,
                include_workspace=not args.vault_only,
                include_vault=not args.workspace_only,
                allow_deletes=args.allow_deletes,
                reviewed_by=args.reviewed_by,
                refresh_indexes=not args.no_refresh_indexes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-sync-receipt":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.sync_receipt_emit(
                snapshot_id=args.snapshot_id,
                target=args.target,
                transport=args.transport,
                device_id=args.device_id,
                notes=args.notes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "emit-sync-manifest":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.sync_manifest_emit(
                target=args.target,
                transport=args.transport,
                device_id=args.device_id,
                snapshot_id=args.snapshot_id,
                notes=args.notes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "apply-sync-manifest":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            sync_manifest_path = args.sync_manifest_path.resolve() if args.sync_manifest_path.is_absolute() else (root / args.sync_manifest_path).resolve()
            result = surface.sync_manifest_apply(sync_manifest_path=sync_manifest_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "local-backup-write":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.local_backup_write(
                target=args.target,
                scope_kind=args.scope_kind,
                scope_value=args.scope_value,
                label=args.label,
                transport=args.transport,
                device_id=args.device_id,
                notes=args.notes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-verify":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.replica_verify(
                replica_root=args.replica_root.resolve(),
                snapshot_id=args.snapshot_id,
                sync_manifest_path=args.sync_manifest_path.resolve() if args.sync_manifest_path else None,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-import":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            trust_policy = json.loads(args.trust_policy_json_path.read_text(encoding="utf-8")) if args.trust_policy_json_path else None
            result = surface.replica_import(
                replica_root=args.replica_root.resolve(),
                snapshot_id=args.snapshot_id,
                sync_manifest_path=args.sync_manifest_path.resolve() if args.sync_manifest_path else None,
                trust_policy=trust_policy,
                reviewed_by=args.reviewed_by,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-apply":
            if args.workspace_only and args.vault_only:
                raise ValueError("replica apply cannot be both workspace-only and vault-only")
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            trust_policy = json.loads(args.trust_policy_json_path.read_text(encoding="utf-8")) if args.trust_policy_json_path else None
            result = surface.replica_apply(
                replica_root=args.replica_root.resolve(),
                snapshot_id=args.snapshot_id,
                sync_manifest_path=args.sync_manifest_path.resolve() if args.sync_manifest_path else None,
                include_workspace=not args.vault_only,
                include_vault=not args.workspace_only,
                allow_deletes=args.allow_deletes,
                reviewed_by=args.reviewed_by,
                refresh_indexes=not args.no_refresh_indexes,
                trust_policy=trust_policy,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-trust-evaluate":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            trust_policy = json.loads(args.trust_policy_json_path.read_text(encoding="utf-8")) if args.trust_policy_json_path else None
            result = surface.replica_trust_evaluate(
                replica_root=args.replica_root.resolve(),
                snapshot_id=args.snapshot_id,
                sync_manifest_path=args.sync_manifest_path.resolve() if args.sync_manifest_path else None,
                trust_policy=trust_policy,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-trust-list":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.replica_trust_list()
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-trust-set":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.replica_trust_set(
                device_id=args.device_id,
                trust_state=args.trust_state,
                label=args.label,
                notes=args.notes,
                allowed_transports=args.allowed_transport,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-pairing-offer":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.replica_pairing_offer_emit(
                device_id=args.device_id,
                label=args.label,
                notes=args.notes,
                allowed_transports=args.allowed_transport,
                pairing_id=args.pairing_id,
                expires_in_hours=args.expires_in_hours,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-pairing-list":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.replica_pairing_offer_list(
                limit=args.limit,
                include_expired=args.include_expired,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "replica-pairing-accept":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.replica_pairing_offer_accept(
                pairing_offer_path=args.pairing_offer_path.resolve()
                if args.pairing_offer_path.is_absolute()
                else (root / args.pairing_offer_path).resolve(),
                trust_state=args.trust_state,
                reviewed_by=args.reviewed_by,
                label=args.label,
                notes=args.notes,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "sync-status":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.sync_status(limit=args.limit)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "sync-conflict-list":
            root = args.root.resolve()
            surface = CtxVaultSurface(CtxVault(default_layout(root)))
            result = surface.sync_conflict_list(limit=args.limit, status=args.status)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "doctor":
            surface = CtxVaultSurface(CtxVault(default_layout(args.root.resolve())))
            print(json.dumps(surface.doctor_report(), indent=2, sort_keys=True))
            return 0

        if args.command == "serve-mcp":
            root = args.root.resolve()
            return serve_stdio(
                root=root,
                policy_path=args.policy_json_path.resolve() if args.policy_json_path else None,
                backup_path=args.backup_json_path.resolve() if args.backup_json_path else None,
                profile_path=args.profile_json_path.resolve() if args.profile_json_path else None,
                plugin_path=args.plugin_json_path.resolve() if args.plugin_json_path else None,
            )

        if args.command == "workbench":
            return load_workbench_server()(root=args.root.resolve(), host=args.host, port=args.port)

        if args.command == "check":
            return run_checks_main()
    except (KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
