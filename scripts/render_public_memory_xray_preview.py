#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BOUNDARY = {
    "public_benchmark_claim": False,
    "security_guarantee": False,
    "provider_model_call": False,
    "memory_backend_write": False,
    "external_target_write": False,
    "arbitrary_repo_scan": False,
    "memory_xray_cli_beta_claim": False,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a deterministic public-safe Memory X-Ray preview from the L1 examples pack."
    )
    parser.add_argument("--input", required=True, type=Path, help="Public L1 examples JSON pack")
    parser.add_argument("--output", required=True, type=Path, help="Markdown output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    pack = _load_pack(args.input)
    report = _build_report(pack, args.input)
    markdown = _render_markdown(report)

    markdown_path = args.output
    json_path = markdown_path.with_suffix(".json")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({"markdown": str(markdown_path), "json": str(json_path), "example_count": report["example_count"]}, sort_keys=True))
    return 0


def _load_pack(path: Path) -> dict[str, Any]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(pack, dict):
        raise ValueError("input pack must be a JSON object")
    examples = pack.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("input pack must contain a non-empty examples list")
    return pack


def _build_report(pack: dict[str, Any], source_path: Path) -> dict[str, Any]:
    examples = sorted(pack["examples"], key=lambda item: str(item.get("example_id", "")))
    findings = []
    for example in examples:
        evidence = example.get("source_rollback_consequence_evidence", {})
        coverage = example.get("source_coverage", {})
        findings.append(
            {
                "finding_id": example.get("example_id"),
                "finding_family": example.get("example_kind"),
                "label": example.get("label"),
                "severity": example.get("risk_band"),
                "risk_score": example.get("risk_score"),
                "consequence_ceiling": example.get("consequence_ceiling"),
                "selected_ref_count": coverage.get("selected_ref_count"),
                "omitted_ref_count": coverage.get("omitted_ref_count"),
                "missing_ref_count": coverage.get("missing_ref_count"),
                "contradicted_ref_count": coverage.get("contradicted_ref_count"),
                "blocked_effects": sorted(example.get("blocked_effects", [])),
                "source_evidence_present": evidence.get("source_evidence_present"),
                "rollback_evidence_present": evidence.get("rollback_evidence_present"),
                "consequence_evidence_present": evidence.get("consequence_evidence_present"),
            }
        )
    return {
        "schema": "ctxgov.public_memory_xray_preview.v0",
        "source": str(source_path),
        "example_count": len(findings),
        "claim_boundary": BOUNDARY,
        "findings": findings,
    }


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# CtxGov Public Memory X-Ray Preview",
        "",
        "This deterministic preview renders public-safe L1 examples only.",
        "It is not a Memory X-Ray CLI beta and does not scan arbitrary target repositories.",
        "",
        "## Claim Boundary",
        "",
        "- No public benchmark claim.",
        "- No security guarantee.",
        "- No provider/model call.",
        "- No memory-backend write.",
        "- No external target write.",
        "- No arbitrary repo scan.",
        "",
        "## Findings",
        "",
    ]
    for finding in report["findings"]:
        lines.extend(
            [
                f"### {finding['finding_id']}",
                "",
                f"- family: `{finding['finding_family']}`",
                f"- severity: `{finding['severity']}`",
                f"- risk_score: `{finding['risk_score']}`",
                f"- evidence: {finding['label']}",
                f"- consequence_ceiling: `{finding['consequence_ceiling']}`",
                f"- source_refs: selected={finding['selected_ref_count']} omitted={finding['omitted_ref_count']} missing={finding['missing_ref_count']} contradicted={finding['contradicted_ref_count']}",
                f"- blocked_effects: `{', '.join(finding['blocked_effects'])}`",
                "",
            ]
        )
    lines.append("## Reproduce")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 scripts/render_public_memory_xray_preview.py --input release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json --output /tmp/ctxgov-memory-xray-preview.md")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
