#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
PACK_REL = Path("release/memory-state-governability-overlay/2026-06-11")
DEFAULT_OUTPUT_JSON = PACK_REL / "memory-state-governability-overlay-social-payload.json"
DEFAULT_OUTPUT_MD = PACK_REL / "memory-state-governability-overlay-social-payload.md"
PUBLIC_PAGE = "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html"
DEMO_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/"
BYO_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md"
BYO_DIR_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/"
GATE_COMMAND = "python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked"
GATE_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py"
REPORT_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_report_contract.py"
CONSUMER_INTEGRATION_COMMAND = "python3 scripts/check_memory_state_influence_boundary_consumer_integration.py"
CONSUMER_WRAPPER_CONTRACT_COMMAND = "python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py"
CONSUMER_WRAPPER_COMMAND = "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py"
CONSUMER_WRAPPER_PASS_COMMAND = "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml"
BYO_SMOKE_COMMAND = "python3 scripts/check_memory_state_influence_boundary_byo_smoke.py"
HN_TITLE = "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report"


CLAIM_BOUNDARY = {
    "public_savings_claim_created": False,
    "public_benchmark_claim_created": False,
    "public_adoption_claim_created": False,
    "public_compatibility_claim_created": False,
    "public_support_claim_created": False,
    "public_security_claim_created": False,
    "public_endorsement_claim_created": False,
    "stable_protocol_claim_created": False,
}
SIDE_EFFECT_BOUNDARY = {
    "network_access_performed": False,
    "provider_or_model_call_performed": False,
    "external_runtime_or_adapter_executed": False,
    "memory_backend_written": False,
    "target_file_written": False,
    "sarif_uploaded": False,
    "public_release_created": False,
    "outreach_performed": False,
}


LINKEDIN_BODY = """The next CtxGov milestone after Activation X-Ray is a local influence-boundary
report for AI memory/context/state files.

The difference from the last release is user input:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/
```

Then point it at your own local file or directory:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md
```

or:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/
```

It reads local files such as AGENTS.md, CLAUDE.md, MEMORY.md, project notes,
MDX context files, JSON/JSONL checkpoint exports, YAML/YML state files, or
TOML state profiles and writes an influence-boundary report:

- candidate memory/context/state refs
- refs allowed only as inform-only context
- refs blocked until review or policy grant
- stale/superseded refs
- imported context refs
- missing policy grant, final-state assertion, rollback, and deletion proof

The report includes hashes, paths, line refs, structured JSON/TOML/YAML
key/value path refs, signal ids, and review recommendations. It does not
include raw file content.
Repo-external inputs are rendered with input-relative paths rather than local
absolute paths.
For product integration, the JSON includes an integration_gate object with
default_exit_code, fail_on_blocked_exit_code, blocked/omitted/stale/imported
counts, and raw_content_included=false.
The full report contract is documented at
schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json.
Wrappers can also request only that gate:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked
```

There is also a no-dependency local contract check:

```sh
python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py
```

And a full report contract check:

```sh
python3 scripts/check_memory_state_influence_boundary_report_contract.py
```

And a consumer integration smoke check that simulates a wrapper consuming the
report/gate and making block vs allow-inform-only decisions:

```sh
python3 scripts/check_memory_state_influence_boundary_consumer_integration.py
```

And a consumer wrapper contract check that validates the wrapper output schema,
blocked/pass example drift, decision mapping, and no-raw-content boundary:

```sh
python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py
```

The copyable wrapper example exposes the product-integration shape directly.
The default sample returns `block` when refs are blocked:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py
```

The clean sample returns `allow_inform_only` without reading raw file content:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
```

And a BYO smoke check that creates repo-external local inputs and verifies
blocked/pass gate behavior, input-relative paths, omitted unsupported files,
and secret-like redaction:

```sh
python3 scripts/check_memory_state_influence_boundary_byo_smoke.py
```

The built-in sample remains available, but the publishable step is now local
audit of user-supplied memory/context/state files.

Public page candidate:
https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html

Boundary: this is not a provider integration, adapter release, compatibility
matrix, support claim, endorsement, security guarantee, benchmark, savings
claim, adoption claim, or stable protocol.

The narrow claim is simpler:

Before AI memory influences behavior, teams need a local report that says which
state is allowed, blocked, omitted, stale, or unsupported.
"""


X_TWEETS = [
    """1/ Next CtxGov milestone:

Drop in AI memory files. Get an influence-boundary report.

`python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/`

Swap in your own CLAUDE.md, notes, JSON/JSONL, YAML, TOML, or MDX file.""",
    """2/ The report classifies local refs:

candidate influence
inform-only allowed
blocked until review/grant
omitted
stale/superseded
imported context

No raw file content is included.""",
    """3/ This is not a provider integration.

No compatibility matrix.
No benchmark.
No savings claim.
No security guarantee.
No stable protocol claim.

It is a local audit before memory/context becomes operational state.""",
    """4/ Product wrapper shape is included:

blocked refs -> block
clean refs -> allow_inform_only

It consumes report/gate JSON without reading raw file content.""",
    """5/ Public page candidate:

https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html

Question: what proof should exist before local AI memory is allowed to influence behavior?""",
]


def render_memory_state_governability_overlay_social_payload(
    root: Path = ROOT,
    *,
    output_json: Path | None = None,
    output_md: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    errors: list[str] = []
    if DEMO_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing demo command")
    if BYO_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing bring-your-own file command")
    if BYO_DIR_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing bring-your-own directory command")
    if GATE_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing gate-only integration command")
    if GATE_CONTRACT_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing integration gate contract check command")
    if REPORT_CONTRACT_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing full report contract check command")
    if CONSUMER_INTEGRATION_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing consumer integration check command")
    if CONSUMER_WRAPPER_CONTRACT_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing consumer wrapper contract check command")
    if CONSUMER_WRAPPER_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing consumer wrapper command")
    if CONSUMER_WRAPPER_PASS_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing consumer wrapper pass command")
    if BYO_SMOKE_COMMAND not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing BYO smoke command")
    if PUBLIC_PAGE not in LINKEDIN_BODY:
        errors.append("LinkedIn body missing public page")
    for index, tweet in enumerate(X_TWEETS, start=1):
        if len(tweet) > 280:
            errors.append(f"tweet {index} exceeds 280 characters")
    if any(bool(value) for value in CLAIM_BOUNDARY.values()):
        errors.append("claim boundary contains true values")
    if any(bool(value) for value in SIDE_EFFECT_BOUNDARY.values()):
        errors.append("side-effect boundary contains true values")

    payload = {
        "schema_id": "ctxvault.memory-state-governability-overlay-social-payload/v0",
        "status": "pass_memory_state_governability_overlay_social_payload" if not errors else "fail_memory_state_governability_overlay_social_payload",
        "milestone": "Local Memory State Influence Boundary Report",
        "public_page": PUBLIC_PAGE,
        "demo_command": DEMO_COMMAND,
        "bring_your_own_command": BYO_COMMAND,
        "gate_command": GATE_COMMAND,
        "gate_contract_command": GATE_CONTRACT_COMMAND,
        "report_contract_command": REPORT_CONTRACT_COMMAND,
        "consumer_integration_command": CONSUMER_INTEGRATION_COMMAND,
        "consumer_wrapper_contract_command": CONSUMER_WRAPPER_CONTRACT_COMMAND,
        "consumer_wrapper_command": CONSUMER_WRAPPER_COMMAND,
        "consumer_wrapper_pass_command": CONSUMER_WRAPPER_PASS_COMMAND,
        "byo_smoke_command": BYO_SMOKE_COMMAND,
        "hn": {
            "submission_type": "url",
            "title": HN_TITLE,
            "url": PUBLIC_PAGE,
            "text": "",
        },
        "linkedin": {
            "body": LINKEDIN_BODY.rstrip(),
            "character_count": len(LINKEDIN_BODY.rstrip()),
        },
        "x": {
            "tweet_count": len(X_TWEETS),
            "max_tweet_chars": 280,
            "tweet_character_counts": [len(tweet) for tweet in X_TWEETS],
            "tweets": X_TWEETS,
        },
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "side_effect_boundary": dict(SIDE_EFFECT_BOUNDARY),
        "manual_review_required": "owner_manual_platform_submit_only",
        "publication_executed": False,
        "outreach_performed": False,
        "errors": errors,
    }
    json_path = _resolve(root, output_json or DEFAULT_OUTPUT_JSON)
    md_path = _resolve(root, output_md or DEFAULT_OUTPUT_MD)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    _write_text_atomic(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_text_atomic(md_path, _render_markdown(payload))
    payload["payload_outputs"] = {
        "json": _display_path(json_path, root),
        "markdown": _display_path(md_path, root),
    }
    _write_text_atomic(json_path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Memory State Governability Overlay Social Payload",
        "",
        "Status: local payload only. No HN, X, LinkedIn, or other outreach action has been executed.",
        "",
        f"Milestone: `{payload['milestone']}`",
        f"Status: `{payload['status']}`",
        "",
        "## HN URL Submission",
        "",
        "```text",
        f"title: {payload['hn']['title']}",
        f"url: {payload['hn']['url']}",
        "text: empty",
        "```",
        "",
        "## LinkedIn",
        "",
        payload["linkedin"]["body"],
        "",
        "## X Thread",
        "",
    ]
    for tweet in payload["x"]["tweets"]:
        lines.extend(["```text", tweet, "```", ""])
    lines.append("Manual platform submission remains manual and unexecuted.")
    return "\n".join(lines) + "\n"


def _resolve(root: Path, path: Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else root / path


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render Memory State Governability Overlay HN/X/LinkedIn payloads.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-md", type=Path)
    args = parser.parse_args()
    payload = render_memory_state_governability_overlay_social_payload(
        args.root,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["status"] == "pass_memory_state_governability_overlay_social_payload" else 1


if __name__ == "__main__":
    raise SystemExit(main())
