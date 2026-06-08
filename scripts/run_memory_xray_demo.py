#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "release" / "v0.7.0" / "memory-xray-l1-public-preview" / "memory-xray-l1-examples-pack.json"
DEFAULT_OUTPUT = ROOT / "docs" / "memory-xray-demo-report.md"

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
        description="Run the deterministic public-safe Memory X-Ray demo."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def load_pack(path: Path) -> dict[str, Any]:
    pack = json.loads(path.read_text(encoding="utf-8"))
    examples = pack.get("examples")
    if not isinstance(examples, list) or not examples:
        raise ValueError("input pack must contain a non-empty examples list")
    return pack


def build_demo(pack: dict[str, Any], source_path: Path) -> dict[str, Any]:
    examples = sorted(pack["examples"], key=lambda item: str(item.get("example_id", "")))
    before = []
    findings = []
    for example in examples:
        coverage = example.get("source_coverage", {})
        evidence = example.get("source_rollback_consequence_evidence", {})
        before.append(
            {
                "source": example.get("private_source_ref", "redacted_public_safe_trace"),
                "context_span": example.get("label"),
                "risk_hint": example.get("example_kind"),
            }
        )
        findings.append(
            {
                "finding_id": example.get("example_id"),
                "finding_family": example.get("example_kind"),
                "severity": example.get("risk_band"),
                "risk_score": example.get("risk_score"),
                "evidence_span": example.get("label"),
                "consequence_ceiling": example.get("consequence_ceiling"),
                "source_refs": {
                    "selected": coverage.get("selected_ref_count"),
                    "omitted": coverage.get("omitted_ref_count"),
                    "missing": coverage.get("missing_ref_count"),
                    "contradicted": coverage.get("contradicted_ref_count"),
                },
                "rollback_evidence_present": evidence.get("rollback_evidence_present"),
                "blocked_effects": sorted(example.get("blocked_effects", [])),
            }
        )
    return {
        "schema": "ctxgov.public_memory_xray_demo.v0",
        "source": str(source_path.relative_to(ROOT)),
        "example_count": len(examples),
        "claim_boundary": BOUNDARY,
        "before": before,
        "after": {
            "report_surface": "Memory X-Ray public-safe demo report",
            "findings": findings,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Memory X-Ray Demo Report",
        "",
        "This is a deterministic public-safe before/after demo. It renders the",
        "checked-in L1 examples pack and does not scan arbitrary target repositories.",
        "It is not a Memory X-Ray CLI beta.",
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
        "## Before",
        "",
    ]
    for item in report["before"]:
        lines.extend(
            [
                f"### {item['risk_hint']}",
                "",
                f"- source: `{item['source']}`",
                f"- context span: {item['context_span']}",
                "",
            ]
        )
    lines.extend(["## After", ""])
    for finding in report["after"]["findings"]:
        refs = finding["source_refs"]
        lines.extend(
            [
                f"### {finding['finding_id']}",
                "",
                f"- family: `{finding['finding_family']}`",
                f"- severity: `{finding['severity']}`",
                f"- risk_score: `{finding['risk_score']}`",
                f"- evidence_span: {finding['evidence_span']}",
                f"- consequence_ceiling: `{finding['consequence_ceiling']}`",
                f"- source_refs: selected={refs['selected']} omitted={refs['omitted']} missing={refs['missing']} contradicted={refs['contradicted']}",
                f"- rollback_evidence_present: `{str(finding['rollback_evidence_present']).lower()}`",
                f"- blocked_effects: `{', '.join(finding['blocked_effects'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Reproduce",
            "",
            "```bash",
            "python3 scripts/run_memory_xray_demo.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_html(markdown: str) -> str:
    escaped = html.escape(markdown)
    return f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Memory X-Ray Demo Report</title>
    <style>
      body {{ margin: 0; padding: 32px; background: #f7f8fb; color: #18202f; font: 16px/1.55 system-ui, sans-serif; }}
      main {{ max-width: 920px; margin: 0 auto; }}
      pre {{ white-space: pre-wrap; background: #fff; border: 1px solid #d8dde6; border-radius: 8px; padding: 20px; overflow-x: auto; }}
    </style>
  </head>
  <body>
    <main>
      <pre>{escaped}</pre>
    </main>
  </body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = args.input if args.input.is_absolute() else ROOT / args.input
    output_path = args.output if args.output.is_absolute() else ROOT / args.output
    pack = load_pack(input_path)
    report = build_demo(pack, input_path)
    markdown = render_markdown(report)
    json_path = output_path.with_suffix(".json")
    html_path = output_path.with_suffix(".html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    html_path.write_text(render_html(markdown), encoding="utf-8")
    print(
        json.dumps(
            {
                "markdown": str(output_path),
                "json": str(json_path),
                "html": str(html_path),
                "example_count": report["example_count"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
