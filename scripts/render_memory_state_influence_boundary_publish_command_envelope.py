#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from json import JSONDecodeError
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "release" / "memory-state-governability-overlay" / "2026-06-11" / "memory-state-influence-boundary-publication-bundle.json"
BUNDLE_BUILDER = Path("scripts/build_memory_state_influence_boundary_publication_bundle.py")


def render_memory_state_influence_boundary_publish_command_envelope(
    root: Path = ROOT,
    *,
    bundle_path: Path = DEFAULT_BUNDLE,
) -> dict[str, Any]:
    root = Path(root).resolve()
    bundle_path = Path(bundle_path)
    if not bundle_path.is_absolute():
        bundle_path = root / bundle_path

    errors: list[str] = []
    if not bundle_path.exists():
        bundle = _build_bundle(root)
    else:
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except JSONDecodeError:
            bundle = _build_bundle(root)

    if bundle.get("status") != "pass_memory_state_influence_boundary_publication_bundle":
        errors.append(f"publication bundle is not ready: {bundle.get('status')}")

    add_paths = [
        "README.md",
        "docs/index.html",
        "docs/memory-state-influence-boundary-try-in-5-minutes.html",
        "docs/memory-state-governability-overlay-try-in-5-minutes.html",
        "schemas/README.md",
        "schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json",
        "schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json",
        "schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json",
        "examples/memory-state-influence-boundary",
        "fixtures/v0.7.0-mgp-sidecar/memory-xray/memory-state-governability-overlays-20260611.json",
        "release/memory-state-governability-overlay",
        "scripts/build_memory_state_influence_boundary_publication_bundle.py",
        "scripts/materialize_memory_state_influence_boundary_publication_bundle.py",
        "scripts/render_memory_state_influence_boundary_owner_publish_packet.py",
        "scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
        "scripts/render_memory_state_influence_boundary_publish_command_envelope.py",
        "scripts/publish_memory_state_influence_boundary_public_patch.py",
        "scripts/check_memory_state_governability_overlay_publish_pack.py",
        "scripts/check_memory_state_influence_boundary_byo_smoke.py",
        "scripts/check_memory_state_influence_boundary_integration_gate_contract.py",
        "scripts/check_memory_state_influence_boundary_report_contract.py",
        "scripts/check_memory_state_influence_boundary_consumer_integration.py",
        "scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py",
        "scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py",
        "scripts/check_memory_state_influence_boundary_release_distinctness.py",
        "scripts/check_memory_state_influence_boundary_final_preflight.py",
        "scripts/check_memory_state_influence_boundary_public_checkout_readiness.py",
        "scripts/check_memory_state_influence_boundary_live_publication.py",
        "scripts/render_memory_state_governability_overlay_social_payload.py",
        "scripts/check_memory_state_influence_boundary_social_draft_drift.py",
        "scripts/run_memory_state_influence_boundary_report.py",
        "scripts/run_memory_state_governability_overlay_demo.py",
        "tests/test_memory_state_governability_overlay_demo.py",
    ]

    return {
        "schema_id": "ctxvault.memory-state-influence-boundary-publish-command-envelope/v0",
        "status": "pass_memory_state_influence_boundary_publish_command_envelope" if not errors else "fail_memory_state_influence_boundary_publish_command_envelope",
        "milestone": "Local Memory State Influence Boundary Report",
        "public_repo": bundle.get("public_repo", "ctxgov/ctxgov"),
        "publication_bundle_sha256": bundle.get("publication_bundle_sha256"),
        "publication_file_count": bundle.get("publication_file_count"),
        "pre_publish_commands": [
            "python3 scripts/check_memory_state_influence_boundary_final_preflight.py",
            "python3 scripts/check_memory_state_governability_overlay_publish_pack.py",
            "python3 scripts/check_memory_state_influence_boundary_byo_smoke.py",
            "python3 scripts/check_memory_state_influence_boundary_report_contract.py",
            "python3 scripts/check_memory_state_influence_boundary_consumer_integration.py",
            "python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py",
            "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py",
            "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml",
            "python3 scripts/render_memory_state_governability_overlay_social_payload.py",
            "python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py",
            "python3 scripts/build_memory_state_influence_boundary_publication_bundle.py",
            "python3 scripts/check_memory_state_influence_boundary_release_distinctness.py",
            "python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py",
            "python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
            "python3 scripts/render_memory_state_influence_boundary_publish_command_envelope.py",
            "python3 scripts/check_memory_state_influence_boundary_public_checkout_readiness.py --check-live",
            "python3 scripts/publish_memory_state_influence_boundary_public_patch.py --checkout <clean-ctxgov-checkout>",
            "python3 -m unittest tests.test_memory_state_governability_overlay_demo",
            "git diff --check",
            "git status --short",
        ],
        "publish_commands": [
            "git add " + " ".join(add_paths),
            "git commit -m \"Add local memory state influence boundary report\"",
            "git push origin main",
        ],
        "post_publish_commands": [
            "python3 scripts/check_memory_state_influence_boundary_live_publication.py --live",
        ],
        "manual_social_actions": [
            "submit or update the HN follow-up only after the public page is live",
            "post the prepared X thread manually",
            "post the prepared LinkedIn copy manually",
        ],
        "branch_created": False,
        "commit_created": False,
        "push_executed": False,
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }


def _build_bundle(root: Path) -> dict[str, Any]:
    path = root / BUNDLE_BUILDER
    spec = importlib.util.spec_from_file_location("memory_state_publish_envelope_bundle_builder", path)
    if spec is None or spec.loader is None:
        return {"status": "fail_memory_state_influence_boundary_publication_bundle", "errors": [f"unable to load {path}"]}
    module = importlib.util.module_from_spec(spec)
    sys.modules["memory_state_publish_envelope_bundle_builder"] = module
    spec.loader.exec_module(module)
    return module.build_memory_state_influence_boundary_publication_bundle(root)


def render_markdown(envelope: dict[str, Any]) -> str:
    lines = [
        "# Memory State Influence Boundary Publish Command Envelope",
        "",
        "Status: command envelope only. No branch, commit, push, Pages deploy, live check, or outreach has been executed.",
        "",
        f"Milestone: `{envelope['milestone']}`",
        f"Bundle digest: `{envelope.get('publication_bundle_sha256')}`",
        "",
        "Pre-publish commands:",
        "",
        "```sh",
        *envelope["pre_publish_commands"],
        "```",
        "",
        "Publish commands:",
        "",
        "```sh",
        *envelope["publish_commands"],
        "```",
        "",
        "Post-publish commands:",
        "",
        "```sh",
        *envelope["post_publish_commands"],
        "```",
        "",
        "Manual social actions remain manual and unexecuted.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Memory State Influence Boundary public publish command envelope.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()
    envelope = render_memory_state_influence_boundary_publish_command_envelope(args.root, bundle_path=args.bundle)
    if args.output_json:
        output_json = args.output_json if args.output_json.is_absolute() else args.root / args.output_json
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.output_md:
        output_md = args.output_md if args.output_md.is_absolute() else args.root / args.output_md
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(envelope), encoding="utf-8")
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0 if envelope["status"] == "pass_memory_state_influence_boundary_publish_command_envelope" else 1


if __name__ == "__main__":
    raise SystemExit(main())
