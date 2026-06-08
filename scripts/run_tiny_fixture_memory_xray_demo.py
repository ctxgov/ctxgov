#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "memory_xray_tiny_repo"
OUTPUT_HTML = ROOT / "docs" / "tiny-fixture-memory-xray-demo.html"
OUTPUT_JSON = ROOT / "docs" / "tiny-fixture-memory-xray-demo.json"


CASES = [
    {
        "file": "README.md",
        "finding": "unsupported_claim",
        "severity": "high",
        "evidence": "bad context: Public benchmark complete. Formal release ready.",
        "note": "Release and benchmark language exceeds the public evidence boundary.",
    },
    {
        "file": "AGENTS.md",
        "finding": "unsafe_instruction",
        "severity": "high",
        "evidence": "Push release artifacts and update target repo after the report is generated.",
        "note": "External writes require explicit owner approval.",
    },
    {
        "file": "terminal.log",
        "finding": "terminal_failure",
        "severity": "medium",
        "evidence": "no output for 4 minutes\nprocess killed by operator",
        "note": "A hung or killed command is evidence, not a pass receipt.",
    },
    {
        "file": "memory-summary.md",
        "finding": "memory_claim_drift",
        "severity": "medium",
        "evidence": "Owner approval and public publish already happened.",
        "note": "Saved memory overstates publication state.",
    },
]


def load_fixture() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        path = FIXTURE / case["file"]
        text = path.read_text(encoding="utf-8")
        rows.append({**case, "content": text})
    return rows


def build_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "ctxgov.tiny_fixture_memory_xray_demo.v0",
        "fixture": "fixtures/memory_xray_tiny_repo",
        "claim_boundary": {
            "public_benchmark_claim_allowed": False,
            "security_claim_allowed": False,
            "provider_model_call_allowed": False,
            "adoption_claim_allowed": False,
            "arbitrary_repo_scan_claim_allowed": False,
        },
        "file_inputs": [
            {"file": row["file"], "content": row["content"]}
            for row in rows
        ],
        "findings": [
            {
                "file": row["file"],
                "finding": row["finding"],
                "severity": row["severity"],
                "evidence": row["evidence"],
                "note": row["note"],
            }
            for row in rows
        ],
    }


def render_html(report: dict[str, Any]) -> str:
    input_cards = []
    for item in report["file_inputs"]:
        input_cards.append(
            f"""
            <article class=\"card input-card\">
              <h3>{html.escape(item["file"])}</h3>
              <pre>{html.escape(item["content"])}</pre>
            </article>"""
        )
    finding_cards = []
    for finding in report["findings"]:
        finding_cards.append(
            f"""
            <article class=\"card finding-card\">
              <p class=\"kicker\">{html.escape(finding["file"])}</p>
              <h3>{html.escape(finding["finding"])}</h3>
              <p><strong>Severity</strong> {html.escape(finding["severity"])}</p>
              <p><strong>Evidence</strong> {html.escape(finding["evidence"])}</p>
              <p>{html.escape(finding["note"])}</p>
            </article>"""
        )
    page = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Tiny fixture Memory X-Ray demo</title>
    <meta property=\"og:title\" content=\"Tiny fixture Memory X-Ray demo\" />
    <meta property=\"og:image\" content=\"https://ctxgov.github.io/ctxgov/og.png\" />
    <meta name=\"twitter:card\" content=\"summary_large_image\" />
    <meta name=\"twitter:image\" content=\"https://ctxgov.github.io/ctxgov/og.png\" />
    <style>
      :root {{ --bg: #f7f8fb; --panel: #ffffff; --ink: #18202f; --muted: #5d697a; --line: #d8dde6; --teal: #0b7f77; --red: #b42318; }}
      * {{ box-sizing: border-box; }}
      body {{ margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.55 system-ui, sans-serif; }}
      main {{ max-width: 1120px; margin: 0 auto; padding: 36px 24px 54px; }}
      .eyebrow, .kicker {{ color: var(--teal); font-weight: 800; }}
      h1 {{ margin: 0; font-size: 44px; line-height: 1.05; }}
      .lede {{ max-width: 760px; color: var(--muted); font-size: 18px; }}
      .columns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; align-items: start; }}
      .stack {{ display: grid; gap: 12px; }}
      .card {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel); padding: 16px; }}
      .finding-card {{ border-left: 4px solid var(--red); }}
      pre {{ white-space: pre-wrap; margin: 0; color: var(--muted); font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
      .boundary {{ margin-top: 18px; color: var(--muted); }}
      @media (max-width: 820px) {{ .columns {{ grid-template-columns: 1fr; }} h1 {{ font-size: 34px; }} }}
    </style>
  </head>
  <body>
    <main>
      <p class=\"eyebrow\">Fixture-only product shape</p>
      <h1>Tiny fixture repo demo</h1>
      <p class=\"lede\">
        A fixed public-safe fixture shows File input to Memory X-Ray report.
        This is not an arbitrary repo scanner and does not read external targets.
      </p>
      <div class=\"columns\">
        <section>
          <h2>File input</h2>
          <div class=\"stack\">{''.join(input_cards)}</div>
        </section>
        <section>
          <h2>Memory X-Ray report</h2>
          <div class=\"stack\">{''.join(finding_cards)}</div>
        </section>
      </div>
      <p class=\"boundary\">
        Boundary: No public benchmark claim. No provider/model call. No adoption claim.
        This is a fixture-only report-shape demo, not an arbitrary repo scanner.
      </p>
    </main>
  </body>
</html>
"""
    return "\n".join(line.rstrip() for line in page.splitlines()) + "\n"


def main() -> int:
    rows = load_fixture()
    report = build_report(rows)
    OUTPUT_HTML.write_text(render_html(report), encoding="utf-8")
    OUTPUT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"html": str(OUTPUT_HTML), "json": str(OUTPUT_JSON), "finding_count": len(report["findings"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
