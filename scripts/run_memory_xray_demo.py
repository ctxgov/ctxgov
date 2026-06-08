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


def _badge_class(severity: str | None) -> str:
    if severity == "high":
        return "badge high"
    if severity == "medium":
        return "badge medium"
    return "badge"


def render_html(report: dict[str, Any]) -> str:
    before_cards = []
    for item in report["before"]:
        before_cards.append(
            f"""
            <article class=\"context-card\">
              <p class=\"card-kicker\">{html.escape(str(item["risk_hint"]))}</p>
              <h2>{html.escape(str(item["context_span"]))}</h2>
              <p><span>Source</span>{html.escape(str(item["source"]))}</p>
            </article>"""
        )

    finding_cards = []
    for finding in report["after"]["findings"]:
        refs = finding["source_refs"]
        blocked = ", ".join(finding["blocked_effects"])
        finding_cards.append(
            f"""
            <article class=\"finding-card\">
              <div class=\"finding-head\">
                <p class=\"card-kicker\">{html.escape(str(finding["finding_family"]))}</p>
                <span class=\"{_badge_class(finding.get("severity"))}\">{html.escape(str(finding["severity"]))}</span>
              </div>
              <h2>{html.escape(str(finding["finding_id"]))}</h2>
              <dl>
                <div><dt>Evidence span</dt><dd>{html.escape(str(finding["evidence_span"]))}</dd></div>
                <div><dt>Risk score</dt><dd>{html.escape(str(finding["risk_score"]))}</dd></div>
                <div><dt>Consequence ceiling</dt><dd>{html.escape(str(finding["consequence_ceiling"]))}</dd></div>
                <div><dt>Source refs</dt><dd>selected={refs["selected"]} omitted={refs["omitted"]} missing={refs["missing"]} contradicted={refs["contradicted"]}</dd></div>
                <div><dt>Rollback evidence</dt><dd>{html.escape(str(finding["rollback_evidence_present"]).lower())}</dd></div>
                <div><dt>Blocked effects</dt><dd>{html.escape(blocked)}</dd></div>
              </dl>
            </article>"""
        )

    html_doc = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Memory X-Ray Demo Report</title>
    <style>
      :root {{
        --bg: #f7f8fb;
        --panel: #ffffff;
        --ink: #18202f;
        --muted: #5d697a;
        --line: #d8dde6;
        --teal: #0b7f77;
        --blue: #2458d3;
        --amber: #9a5b00;
        --red: #b42318;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font: 16px/1.55 system-ui, -apple-system, BlinkMacSystemFont, \"Segoe UI\", sans-serif;
      }}
      a {{ color: var(--blue); text-decoration: none; }}
      a:hover {{ text-decoration: underline; }}
      .report-shell {{ max-width: 1160px; margin: 0 auto; padding: 36px 24px 54px; }}
      .topbar {{ display: flex; justify-content: space-between; gap: 16px; margin-bottom: 34px; }}
      .eyebrow {{ margin: 0 0 10px; color: var(--teal); font-weight: 700; }}
      h1 {{ margin: 0; max-width: 760px; font-size: 48px; line-height: 1.02; }}
      .lede {{ max-width: 760px; color: var(--muted); font-size: 19px; }}
      .boundary {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin: 24px 0 36px;
      }}
      .boundary span {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
        padding: 10px 12px;
        color: var(--muted);
        font-size: 14px;
      }}
      .columns {{ display: grid; grid-template-columns: 0.9fr 1.1fr; gap: 18px; align-items: start; }}
      .panel-title {{ margin: 0 0 12px; font-size: 24px; }}
      .stack {{ display: grid; gap: 12px; }}
      .context-card,
      .finding-card {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
        padding: 16px;
      }}
      .card-kicker {{ margin: 0 0 8px; color: var(--teal); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .context-card h2,
      .finding-card h2 {{ margin: 0 0 12px; font-size: 18px; line-height: 1.25; }}
      .context-card p {{ margin: 0; color: var(--muted); }}
      .context-card p span {{ display: block; color: var(--ink); font-weight: 700; }}
      .finding-head {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; }}
      .badge {{ border: 1px solid var(--line); border-radius: 999px; padding: 3px 9px; color: var(--muted); font-size: 12px; font-weight: 800; }}
      .badge.medium {{ border-color: #e3b341; color: var(--amber); }}
      .badge.high {{ border-color: #e08478; color: var(--red); }}
      dl {{ display: grid; gap: 8px; margin: 0; }}
      dl div {{ display: grid; grid-template-columns: 150px 1fr; gap: 12px; }}
      dt {{ color: var(--muted); }}
      dd {{ margin: 0; }}
      code {{ background: #edf1f7; border-radius: 6px; padding: 2px 5px; }}
      .reproduce {{ margin-top: 28px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); padding: 16px; }}
      @media (max-width: 860px) {{
        .topbar,
        .columns,
        .boundary {{ grid-template-columns: 1fr; display: grid; }}
        h1 {{ font-size: 36px; }}
        dl div {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main class=\"report-shell\">
      <div class=\"topbar\">
        <div>
          <p class=\"eyebrow\">Public-safe Memory X-Ray preview</p>
          <h1>Memory X-Ray Demo Report</h1>
          <p class=\"lede\">
            A deterministic before/after report generated from checked-in L1
            examples. It shows the report shape and evidence spans without
            scanning arbitrary target repositories.
          </p>
        </div>
        <p><a href=\"try-in-5-minutes.html\">Try in 5 minutes</a></p>
      </div>
      <div class=\"boundary\" aria-label=\"Claim boundary\">
        <span>No public benchmark claim</span>
        <span>No security guarantee</span>
        <span>No provider/model call</span>
        <span>No memory-backend write</span>
        <span>No external target write</span>
        <span>No arbitrary repo scan</span>
      </div>
      <div class=\"columns\">
        <section>
          <h2 class=\"panel-title\">Before Context</h2>
          <div class=\"stack\">
            {''.join(before_cards)}
          </div>
        </section>
        <section>
          <h2 class=\"panel-title\">After Report</h2>
          <div class=\"stack\">
            {''.join(finding_cards)}
          </div>
        </section>
      </div>
      <section class=\"reproduce\">
        <h2>Reproduce</h2>
        <p>Run <code>python3 scripts/run_memory_xray_demo.py</code> from a fresh clone.</p>
      </section>
    </main>
  </body>
</html>
"""
    return "\n".join(line.rstrip() for line in html_doc.splitlines()) + "\n"


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
    html_path.write_text(render_html(report), encoding="utf-8")
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
