from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .change_analysis import build_change_gate_report_for_roots, render_change_gate_report_summary
from .federation import federate, federate_auto_discover
from .forensics import build_forensic_timeline, identify_evidence_gaps, trace_evidence_path
from .governance_eval import build_governance_replay_receipts
from .memory_xray import validate_memory_xray_file
from .oss_case_study import build_oss_case_study_preview
from .oss_efficiency import evaluate_oss_efficiency_manifest, validate_oss_efficiency_receipt_file
from .session_continuity import (
    SUPPORTED_TARGETS,
    apply_session_continuity_packet,
    compile_session_continuity_sidecar,
    render_session_continuity_packet,
)


def _json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctxgov",
        description="CtxGov v0.9.0 public CLI: local governance evaluation and session-continuity commands.",
    )
    parser.add_argument("--version", action="version", version=f"ctxgov {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)

    continuity = subcommands.add_parser("continuity", help="Local session-continuity commands")
    continuity_subcommands = continuity.add_subparsers(dest="continuity_command", required=True)

    def add_continuity_common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--target", choices=sorted(SUPPORTED_TARGETS), default="generic")
        command.add_argument("--max-injection-items", type=int, default=8)
        command.add_argument("--checked-at")
        command.add_argument("path", type=Path)

    compile_cmd = continuity_subcommands.add_parser("compile", help="Print a local continuity sidecar JSON object")
    add_continuity_common(compile_cmd)

    render_cmd = continuity_subcommands.add_parser("render", help="Print a Markdown next-session packet")
    add_continuity_common(render_cmd)

    apply_cmd = continuity_subcommands.add_parser("apply", help="Build a dry-run or sandbox-only apply result")
    apply_cmd.add_argument("--target", choices=sorted(SUPPORTED_TARGETS), default="generic")
    apply_cmd.add_argument("--surface", choices=("next-session", "claude-md", "agents-md"), default="next-session")
    apply_cmd.add_argument("--mode", choices=("dry-run", "sandbox"), default="dry-run")
    apply_cmd.add_argument("--sandbox-dir", type=Path)
    apply_cmd.add_argument("--root", type=Path, default=Path.cwd())
    apply_cmd.add_argument("--max-injection-items", type=int, default=8)
    apply_cmd.add_argument("--checked-at")
    apply_cmd.add_argument("path", type=Path)

    memory_xray = subcommands.add_parser("memory-xray", help="Memory X-Ray report-shape validation")
    memory_xray_subcommands = memory_xray.add_subparsers(dest="memory_xray_command", required=True)
    validate_cmd = memory_xray_subcommands.add_parser("validate", help="Validate one Memory X-Ray JSON report")
    validate_cmd.add_argument("path", type=Path)

    change_gate = subcommands.add_parser("change-gate-check", help="Read local agent surfaces and print a read-only Change Gate report")
    change_gate.add_argument("--root", type=Path, default=Path("."))
    change_gate.add_argument("--baseline-root", type=Path)
    change_gate.add_argument("--head-root", type=Path)
    change_gate.add_argument("--max-files", type=int, default=64)
    change_gate.add_argument("--max-bytes-per-file", type=int, default=262144)
    change_gate.add_argument("--format", choices=("json", "summary"), default="json")

    federation = subcommands.add_parser("change-gate-federate", help="Run read-only Change Gate inventory over explicit local repositories")
    federation.add_argument("--base-path", type=Path)
    federation.add_argument("--repos", nargs="*", type=Path)
    federation.add_argument("--max-depth", type=int, default=1)
    federation.add_argument("--max-repos", type=int, default=16)
    federation.add_argument("--max-files", type=int, default=64)
    federation.add_argument("--max-bytes-per-file", type=int, default=262144)
    federation.add_argument("--no-git-required", action="store_true")

    case_study = subcommands.add_parser("oss-case-study-preview", help="Build a source-descriptive read-only OSS case-study preview from a saved local source file")
    case_study.add_argument("--target-name", required=True)
    case_study.add_argument("--repo-url")
    case_study.add_argument("--pinned-ref", required=True)
    case_study.add_argument("--source-path", type=Path, required=True)
    case_study.add_argument("--license", default="unknown")
    case_study.add_argument("--checked-at-utc")
    case_study.add_argument("--max-source-bytes", type=int, default=262144)

    oss_efficiency = subcommands.add_parser("oss-efficiency", help="Evaluate or validate saved raw OSS telemetry methodology receipts")
    oss_efficiency_subcommands = oss_efficiency.add_subparsers(dest="oss_efficiency_command", required=True)
    oss_eval = oss_efficiency_subcommands.add_parser("evaluate", help="Print a raw telemetry methodology receipt from saved local measurement data")
    oss_eval.add_argument("--manifest", type=Path, default=Path("release/v0.8.0/oss-efficiency-raw-telemetry-manifest.json"))
    oss_eval.add_argument("--telemetry", action="append", type=Path, default=[])
    oss_eval.add_argument("--checked-at")
    oss_validate = oss_efficiency_subcommands.add_parser("validate", help="Validate one raw telemetry methodology receipt")
    oss_validate.add_argument("path", type=Path)

    governance_replay = subcommands.add_parser("governance-replay", help="Replay a saved local governance trace without model/provider calls")
    governance_replay.add_argument("--trace", type=Path, required=True)
    governance_replay.add_argument("--checked-at")

    forensics_timeline = subcommands.add_parser("forensics-timeline", help="Print a read-only timeline from an explicit fixture")
    forensics_timeline.add_argument("--fixture", type=Path, default=Path("release/v0.8.0/forensics-public-preview-fixture.json"))
    forensics_timeline.add_argument("--limit", type=int, default=100)
    forensics_trace = subcommands.add_parser("forensics-trace", help="Trace one finding from an explicit fixture")
    forensics_trace.add_argument("--fixture", type=Path, default=Path("release/v0.8.0/forensics-public-preview-fixture.json"))
    forensics_trace.add_argument("--finding-id", required=True)
    forensics_gaps = subcommands.add_parser("forensics-gaps", help="Identify fixture-level evidence gaps without creating local stores")
    forensics_gaps.add_argument("--fixture", type=Path, default=Path("release/v0.8.0/forensics-public-preview-fixture.json"))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "continuity":
        if args.continuity_command == "compile":
            _json(
                compile_session_continuity_sidecar(
                    args.path,
                    target=args.target,
                    max_injection_items=args.max_injection_items,
                    checked_at=args.checked_at,
                )
            )
            return 0
        if args.continuity_command == "render":
            print(
                render_session_continuity_packet(
                    args.path,
                    target=args.target,
                    max_injection_items=args.max_injection_items,
                    checked_at=args.checked_at,
                )
            )
            return 0
        if args.continuity_command == "apply":
            _json(
                apply_session_continuity_packet(
                    args.path,
                    target=args.target,
                    surface=args.surface,
                    mode=args.mode,
                    sandbox_dir=args.sandbox_dir,
                    root=args.root,
                    max_injection_items=args.max_injection_items,
                    checked_at=args.checked_at,
                )
            )
            return 0

    if args.command == "memory-xray" and args.memory_xray_command == "validate":
        result = validate_memory_xray_file(args.path)
        _json(result)
        return 0 if result.get("valid") else 1

    if args.command == "change-gate-check":
        if (args.baseline_root is None) ^ (args.head_root is None):
            print("error: --baseline-root and --head-root must be provided together", file=sys.stderr)
            return 2
        report = build_change_gate_report_for_roots(
            root=args.root,
            baseline_root=args.baseline_root,
            head_root=args.head_root,
            max_files=args.max_files,
            max_bytes_per_file=args.max_bytes_per_file,
        )
        if args.format == "summary":
            print(render_change_gate_report_summary(report))
        else:
            _json(report)
        return 0

    if args.command == "change-gate-federate":
        repos = [path for path in args.repos or []]
        if args.base_path is None and not repos:
            print("error: provide --base-path or --repos; the public CLI does not scan parent directories by default", file=sys.stderr)
            return 2
        if args.base_path is not None:
            report = federate_auto_discover(
                args.base_path,
                max_depth=args.max_depth,
                require_git=not args.no_git_required,
                extra_repos=repos,
                max_repos=args.max_repos,
                max_files=args.max_files,
                max_bytes_per_file=args.max_bytes_per_file,
            )
        else:
            report = federate(
                repos,
                max_repos=args.max_repos,
                max_files=args.max_files,
                max_bytes_per_file=args.max_bytes_per_file,
            )
        _json(report)
        return 0

    if args.command == "oss-case-study-preview":
        _json(
            build_oss_case_study_preview(
                target_name=args.target_name,
                source_path=args.source_path,
                repo_url=args.repo_url,
                pinned_ref=args.pinned_ref,
                license_name=args.license,
                checked_at=args.checked_at_utc,
                max_source_bytes=args.max_source_bytes,
            )
        )
        return 0

    if args.command == "oss-efficiency":
        if args.oss_efficiency_command == "evaluate":
            _json(evaluate_oss_efficiency_manifest(args.manifest, telemetry_paths=args.telemetry, checked_at=args.checked_at))
            return 0
        if args.oss_efficiency_command == "validate":
            result = validate_oss_efficiency_receipt_file(args.path)
            _json(result)
            return 0 if result.get("valid") else 1

    if args.command == "governance-replay":
        _json(build_governance_replay_receipts(args.trace, checked_at=args.checked_at))
        return 0

    if args.command == "forensics-timeline":
        _json(build_forensic_timeline(args.fixture, limit=args.limit))
        return 0
    if args.command == "forensics-trace":
        _json(trace_evidence_path(args.fixture, args.finding_id))
        return 0
    if args.command == "forensics-gaps":
        _json(identify_evidence_gaps(args.fixture))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
