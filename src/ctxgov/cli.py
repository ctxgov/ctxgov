from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .memory_xray import validate_memory_xray_file
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
        description="CtxGov v0.7.0 public CLI: local session-continuity and Memory X-Ray validation only.",
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

    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
