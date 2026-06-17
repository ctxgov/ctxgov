from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault.task_shard_context import (
    build_task_shard_context_budget_public_report,
    render_task_shard_context_budget_public_html,
    render_task_shard_context_budget_public_markdown,
)


DEFAULT_OUTPUT = ROOT / ".ctxvault" / "task-shard-context-budget"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the public-safe Task Shard context budget demo.")
    parser.add_argument("--input", default="examples/task-shard-context-budget/")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    input_path = (ROOT / args.input).resolve() if not Path(args.input).is_absolute() else Path(args.input)
    output_dir = (ROOT / args.output_dir).resolve() if not Path(args.output_dir).is_absolute() else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_task_shard_context_budget_public_report(input_path)
    json_path = output_dir / "task-shard-context-budget-report.json"
    markdown_path = output_dir / "task-shard-context-budget-report.md"
    html_path = output_dir / "task-shard-context-budget-report.html"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_task_shard_context_budget_public_markdown(report), encoding="utf-8")
    html_path.write_text(render_task_shard_context_budget_public_html(report), encoding="utf-8")

    payload = {
        "schema_id": "ctxgov.task-shard-context-budget-demo/v0",
        "status": "pass_task_shard_context_budget_demo",
        "milestone": "Task Shard Context Budget Ledger",
        "raw_content_included": False,
        "output_files": {
            "json": _repo_relative(json_path),
            "markdown": _repo_relative(markdown_path),
            "html": _repo_relative(html_path),
        },
        "report_status": report["status"],
        "report_sha256": report["report_sha256"],
        "side_effect_boundary": report["side_effect_boundary"],
        "claim_boundary": report["claim_boundary"],
        "publication_executed": False,
        "outreach_performed": False,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


if __name__ == "__main__":
    raise SystemExit(main())
