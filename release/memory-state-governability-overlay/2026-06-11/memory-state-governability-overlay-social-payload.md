# Memory State Governability Overlay Social Payload

Status: local payload only. No HN, X, LinkedIn, or other outreach action has been executed.

Milestone: `Local Memory State Influence Boundary Report`
Status: `pass_memory_state_governability_overlay_social_payload`

## HN URL Submission

```text
title: Show HN: CtxGov - drop in AI memory files, get an influence-boundary report
url: https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html
text: empty
```

## LinkedIn

The next CtxGov milestone after Activation X-Ray is a local influence-boundary
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

## X Thread

```text
1/ Next CtxGov milestone:

Drop in AI memory files. Get an influence-boundary report.

`python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/`

Swap in your own CLAUDE.md, notes, JSON/JSONL, YAML, TOML, or MDX file.
```

```text
2/ The report classifies local refs:

candidate influence
inform-only allowed
blocked until review/grant
omitted
stale/superseded
imported context

No raw file content is included.
```

```text
3/ This is not a provider integration.

No compatibility matrix.
No benchmark.
No savings claim.
No security guarantee.
No stable protocol claim.

It is a local audit before memory/context becomes operational state.
```

```text
4/ Product wrapper shape is included:

blocked refs -> block
clean refs -> allow_inform_only

It consumes report/gate JSON without reading raw file content.
```

```text
5/ Public page candidate:

https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html

Question: what proof should exist before local AI memory is allowed to influence behavior?
```

Manual platform submission remains manual and unexecuted.
