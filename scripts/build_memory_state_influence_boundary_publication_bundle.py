#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
PACK_REL = Path("release/memory-state-governability-overlay/2026-06-11")
DEFAULT_OUTPUT_JSON = PACK_REL / "memory-state-influence-boundary-publication-bundle.json"
DEFAULT_OUTPUT_MD = PACK_REL / "memory-state-influence-boundary-publication-bundle.md"
READINESS_RECEIPT = "release/memory-state-governability-overlay/2026-06-11/public-checkout-readiness-receipt.md"

DEMO_SCRIPT = Path("scripts/run_memory_state_governability_overlay_demo.py")
PACK_CHECK_SCRIPT = Path("scripts/check_memory_state_governability_overlay_publish_pack.py")
READINESS_TEMP_PREFIX_MARKER = "ctxgov-public" + "-readiness-"
SAMPLE_INPUT_DIR = "examples/memory-state-influence-boundary"
INFLUENCE_BOUNDARY_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py"

PUBLICATION_STATIC_FILES = [
    "README.md",
    "docs/index.html",
    "docs/memory-state-influence-boundary-try-in-5-minutes.html",
    "docs/memory-state-governability-overlay-try-in-5-minutes.html",
    "schemas/README.md",
    "schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json",
    "schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json",
    "schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json",
    "examples/memory-state-influence-boundary/README.md",
    "examples/memory-state-influence-boundary/CLAUDE.md",
    "examples/memory-state-influence-boundary/AGENTS.md",
    "examples/memory-state-influence-boundary/project-notes.md",
    "examples/memory-state-influence-boundary/context-note.mdx",
    "examples/memory-state-influence-boundary/checkpoint.json",
    "examples/memory-state-influence-boundary/memory-store.jsonl",
    "examples/memory-state-influence-boundary/state-profile.yaml",
    "examples/memory-state-influence-boundary/state-policy.toml",
    "fixtures/v0.7.0-mgp-sidecar/memory-xray/memory-state-governability-overlays-20260611.json",
    "release/memory-state-governability-overlay/2026-06-11/README.md",
    "release/memory-state-governability-overlay/2026-06-11/product-integration-quickstart.md",
    "release/memory-state-governability-overlay/2026-06-11/integration-gate.example.json",
    "release/memory-state-governability-overlay/2026-06-11/integration-gate.pass.example.json",
    "release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json",
    "release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json",
    READINESS_RECEIPT,
    "release/memory-state-governability-overlay/2026-06-11/hn-post.md",
    "release/memory-state-governability-overlay/2026-06-11/linkedin-post.md",
    "release/memory-state-governability-overlay/2026-06-11/x-thread.md",
    "release/memory-state-governability-overlay/2026-06-11/memory-state-governability-overlay-social-payload.json",
    "release/memory-state-governability-overlay/2026-06-11/memory-state-governability-overlay-social-payload.md",
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

PRIVATE_MARKERS = [
    "/" + "Users" + "/" + "chris",
    "/" + "Users" + "/",
    "/" + "private" + "/",
    "/" + "var" + "/" + "folders" + "/",
    "/" + "tmp" + "/" + "ctxgov-",
    READINESS_TEMP_PREFIX_MARKER,
    "chrisho" + "hoho",
    "ctxvault-" + "incubation",
    "Forgejo" + "-only",
]


def build_memory_state_influence_boundary_publication_bundle(
    root: Path = ROOT,
    *,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    demo_module = _load_script(root, DEMO_SCRIPT, "memory_state_publication_demo")
    pack_module = _load_script(root, PACK_CHECK_SCRIPT, "memory_state_publication_pack")

    sample_report = demo_module.build_memory_state_influence_boundary_report(
        root,
        input_path=Path("examples/memory-state-influence-boundary"),
    )
    pack = pack_module.check_memory_state_governability_overlay_publish_pack(
        root,
        include_owner_packet_contract=False,
    )

    errors: list[str] = []
    file_digests: dict[str, dict[str, Any]] = {}
    private_marker_hits: dict[str, list[str]] = {}
    publication_files = list(dict.fromkeys(PUBLICATION_STATIC_FILES))

    for rel in publication_files:
        path = root / rel
        if not path.exists():
            errors.append(f"missing publication file {rel}")
            continue
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        hits = _private_marker_hits(rel, text)
        if hits:
            private_marker_hits[rel] = hits
            errors.append(f"publication file {rel} contains private marker(s): {', '.join(hits)}")
        file_digests[rel] = {"bytes": len(data), "sha256": _sha256_bytes(data)}

    _check_readiness_receipt_counts(
        root / READINESS_RECEIPT,
        publication_file_count=len(publication_files),
        sample_input_file_count=sample_report.get("input_file_count"),
        errors=errors,
    )

    if sample_report.get("status") != "pass_memory_state_influence_boundary_report":
        errors.append("sample input report failed")
    if sample_report.get("input_file_count", 0) < 9:
        errors.append("sample input report must scan the sample directory")
    if not sample_report.get("influence_boundary", {}).get("blocked_refs"):
        errors.append("sample input report must include blocked refs")
    if pack.get("status") != "pass_memory_state_governability_overlay_publish_pack":
        errors.append("publish pack failed")
    if any(bool(value) for value in sample_report.get("claim_boundary", {}).values()):
        errors.append("sample report claim boundary contains true values")
    if any(bool(value) for value in sample_report.get("side_effect_boundary", {}).values()):
        errors.append("sample report side-effect boundary contains true values")

    digest_payload = {
        "publication_files": file_digests,
        "sample_status": sample_report.get("status"),
        "pack_status": pack.get("status"),
        "sample_input_file_count": sample_report.get("input_file_count"),
        "sample_blocked_ref_count": len(sample_report.get("influence_boundary", {}).get("blocked_refs", [])),
        "claim_boundary": sample_report.get("claim_boundary", {}),
        "side_effect_boundary": sample_report.get("side_effect_boundary", {}),
    }
    bundle = {
        "schema_id": "ctxvault.memory-state-influence-boundary-publication-bundle/v0",
        "status": "pass_memory_state_influence_boundary_publication_bundle" if not errors else "fail_memory_state_influence_boundary_publication_bundle",
        "milestone": "Local Memory State Influence Boundary Report",
        "public_repo": "ctxgov/ctxgov",
        "public_page": "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
        "publication_files": publication_files,
        "publication_file_count": len(publication_files),
        "file_digests": file_digests,
        "publication_bundle_sha256": _sha256_json(digest_payload),
        "sample_report_status": sample_report.get("status"),
        "sample_input_file_count": sample_report.get("input_file_count"),
        "sample_blocked_ref_count": len(sample_report.get("influence_boundary", {}).get("blocked_refs", [])),
        "sample_stale_ref_count": len(sample_report.get("influence_boundary", {}).get("stale_or_superseded_refs", [])),
        "final_preflight_status": "checked_by_outer_preflight",
        "publish_pack_status": pack.get("status"),
        "fresh_checkout_commands": [
            "git clone https://github.com/ctxgov/ctxgov.git",
            "cd ctxgov",
            f"{INFLUENCE_BOUNDARY_COMMAND} --input {SAMPLE_INPUT_DIR}",
        ],
        "bring_your_own_commands": [
            f"{INFLUENCE_BOUNDARY_COMMAND} --input ./CLAUDE.md",
            f"{INFLUENCE_BOUNDARY_COMMAND} --input ./memory-state/",
        ],
        "demo_output_files": sample_report.get("output_files", {}),
        "claim_boundary": sample_report.get("claim_boundary", {}),
        "side_effect_boundary": sample_report.get("side_effect_boundary", {}),
        "private_marker_hits": private_marker_hits,
        "manual_review_required": "minimal_owner_publish_action_only",
        "required_external_actions": [
            "copy the listed publication files into a clean ctxgov/ctxgov checkout",
            "or run python3 scripts/materialize_memory_state_influence_boundary_publication_bundle.py --checkout <clean-checkout>",
            "run python3 scripts/check_memory_state_influence_boundary_final_preflight.py in that checkout",
            "review python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py output",
            "run python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
            "review python3 scripts/render_memory_state_influence_boundary_publish_command_envelope.py output",
            "commit and push the public repo patch",
            "wait for GitHub Pages to deploy and run python3 scripts/check_memory_state_influence_boundary_live_publication.py --live",
            "manually post the selected HN/X/LinkedIn copy",
        ],
        "branch_created": False,
        "commit_created": False,
        "push_executed": False,
        "pull_request_created": False,
        "tag_created": False,
        "release_created": False,
        "github_pages_deployed": False,
        "live_url_checked": False,
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }

    json_path = _resolve_output(root, output_json or DEFAULT_OUTPUT_JSON)
    md_path = _resolve_output(root, output_md or DEFAULT_OUTPUT_MD)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(json_path, json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    _write_text_atomic(md_path, _render_markdown(bundle))
    bundle["bundle_outputs"] = {
        "json": _display_path(json_path, root),
        "markdown": _display_path(md_path, root),
    }
    _write_text_atomic(json_path, json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    return bundle


def _load_script(root: Path, rel_path: Path, module_name: str) -> Any:
    path = root / rel_path
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _private_marker_hits(rel_path: str, text: str) -> list[str]:
    hits = [marker for marker in PRIVATE_MARKERS if marker in text]
    if rel_path == "scripts/check_memory_state_influence_boundary_public_checkout_readiness.py":
        hits = [marker for marker in hits if marker != READINESS_TEMP_PREFIX_MARKER]
    return hits


def _check_readiness_receipt_counts(
    receipt_path: Path,
    *,
    publication_file_count: int,
    sample_input_file_count: Any,
    errors: list[str],
) -> None:
    if not receipt_path.exists():
        errors.append(f"missing public checkout readiness receipt: {_display_path(receipt_path, ROOT)}")
        return
    text = receipt_path.read_text(encoding="utf-8")
    expected_phrases = [
        f"copied file count observed in the latest readiness run: `{publication_file_count}`",
        f"sample input files: `{sample_input_file_count}`",
        "product integration quickstart copied: `true`",
        "consumer wrapper contract: `pass`",
        "consumer wrapper blocked decision: `block`",
        "consumer wrapper passing decision: `allow_inform_only`",
        "release distinctness warnings: `0`",
        "social draft drift: `pass`",
        "owner publish packet contract: `pass`",
    ]
    for phrase in expected_phrases:
        if phrase not in text:
            errors.append(f"public checkout readiness receipt has stale count or missing phrase: {phrase}")


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _resolve_output(root: Path, output: Path) -> Path:
    output = Path(output)
    return output if output.is_absolute() else root / output


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _render_markdown(bundle: dict[str, Any]) -> str:
    lines = [
        "# Memory State Influence Boundary Publication Bundle",
        "",
        "Status: local bundle only. No branch, commit, push, PR, tag, release, Pages deploy, live URL check, or outreach has been executed.",
        "",
        f"Milestone: `{bundle['milestone']}`",
        f"Status: `{bundle['status']}`",
        f"Bundle digest: `{bundle['publication_bundle_sha256']}`",
        f"Public page: {bundle['public_page']}",
        "",
        "Fresh checkout command:",
        "",
        "```sh",
        *bundle["fresh_checkout_commands"],
        "```",
        "",
        "Publication files:",
        "",
    ]
    lines.extend(f"- `{rel}`" for rel in bundle["publication_files"])
    lines.extend(
        [
            "",
            "Required external actions remain manual and unexecuted.",
            "",
            "Blocked claims remain false: benchmark, savings, adoption, compatibility/support, endorsement, security, and stable protocol.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the local Memory State Influence Boundary publication bundle.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args()
    bundle = build_memory_state_influence_boundary_publication_bundle(
        args.root,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    print(json.dumps(bundle, indent=2, sort_keys=True))
    return 0 if bundle["status"] == "pass_memory_state_influence_boundary_publication_bundle" else 1


if __name__ == "__main__":
    raise SystemExit(main())
