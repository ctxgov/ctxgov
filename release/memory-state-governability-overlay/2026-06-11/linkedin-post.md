# LinkedIn Post

Status: local draft only. No LinkedIn post has been executed.

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
