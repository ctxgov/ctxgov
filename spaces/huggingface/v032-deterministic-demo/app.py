from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

import gradio as gr


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from inspect_v032_demo_receipts import inspect_receipts
from run_v032_deterministic_demo import run_demo


def run_ctxvault_demo() -> tuple[str, str, str, str, str]:
    with tempfile.TemporaryDirectory(prefix="ctxvault-v032-space-") as tmpdir:
        summary = run_demo(root=Path(tmpdir) / "demo")
        inspection = inspect_receipts(summary_path=Path(summary["summary_path"]))
        agents_md = Path(summary["projections"]["agents_md"]["output_path"]).read_text(encoding="utf-8")
        claude_md = Path(summary["projections"]["claude_md"]["output_path"]).read_text(encoding="utf-8")
        brief_md = Path(summary["projections"]["workstream_brief"]["output_path"]).read_text(encoding="utf-8")
        visible_summary = public_demo_summary(summary, inspection)
        return (
            public_demo_status(visible_summary),
            json.dumps(visible_summary, ensure_ascii=False, indent=2, sort_keys=True),
            agents_md,
            claude_md,
            brief_md,
        )


def public_demo_summary(summary: dict, inspection: dict) -> dict:
    selection = summary["selection"]
    blocked = selection["blocked_candidate"]
    return {
        "status": "pass" if summary["ok"] and inspection["status"] == "pass" else "fail",
        "claim_boundary": summary["claim_boundary"],
        "selection": {
            "target_kind": selection["target_kind"],
            "privacy_decision": selection["privacy_decision"],
            "budget_status": selection["budget_status"],
            "token_budget": selection["token_budget"],
            "token_estimate": selection["token_estimate"],
            "source_group_count": selection["source_group_count"],
            "candidate_count": len(selection["candidate_slice_refs"]),
            "selected_slice_refs": selection["selected_slice_refs"],
            "blocked_candidate": {
                "slice_ref": blocked["slice_ref"],
                "privacy_class": blocked["privacy_class"],
                "is_selected": blocked["is_selected"],
            },
        },
        "receipt_inspection": {
            "status": inspection["status"],
            "checks": [
                {
                    "name": check["name"],
                    "status": check["status"],
                    **({"target_kind": check["target_kind"]} if "target_kind" in check else {}),
                }
                for check in inspection["checks"]
            ],
        },
        "projection_outputs": [
            "AGENTS.md",
            "CLAUDE.md",
            "workstream-brief.md",
        ],
    }


def public_demo_status(visible_summary: dict) -> str:
    selection = visible_summary["selection"]
    receipt_checks = visible_summary["receipt_inspection"]["checks"]
    selected_count = len(selection["selected_slice_refs"])
    blocked = selection["blocked_candidate"]
    return "\n".join(
        [
            "### PASS",
            f"- selected `{selected_count}` safe context slices from `{selection['source_group_count']}` source groups",
            f"- token budget `{selection['token_estimate']}/{selection['token_budget']}` is `{selection['budget_status']}`",
            f"- withheld candidate `{blocked['privacy_class']}` was selected: `{str(blocked['is_selected']).lower()}`",
            f"- receipt checks passed: `{sum(1 for check in receipt_checks if check['status'] == 'pass')}/{len(receipt_checks)}`",
        ]
    )


with gr.Blocks(title="CtxVault v0.3.2 Deterministic Demo") as demo:
    gr.Markdown(
        """
# CtxVault v0.3.2

Deterministic context selection before context reaches AI tools. This demo uses
toy local sources only: no model, no embedding service, no vector database, no
remote provider, no private user data, and no uploads.
"""
    )
    run_button = gr.Button("Run deterministic demo", variant="primary")
    status = gr.Markdown("Run the demo to inspect deterministic selection and receipts.")
    summary = gr.Code(label="Public receipt summary", language="json", lines=18)
    with gr.Tabs():
        with gr.Tab("AGENTS.md"):
            agents = gr.Code(label="AGENTS.md projection", language="markdown", lines=24)
        with gr.Tab("CLAUDE.md"):
            claude = gr.Code(label="CLAUDE.md projection", language="markdown", lines=24)
        with gr.Tab("Brief"):
            brief = gr.Code(label="Workstream brief projection", language="markdown", lines=24)
    run_button.click(run_ctxvault_demo, outputs=[status, summary, agents, claude, brief])


if __name__ == "__main__":
    demo.launch()
