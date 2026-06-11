# Local Memory State Influence Boundary Report Publish Pack

Status: local publish pack prepared; `publication_executed=false`;
`outreach_performed=false`.

## Milestone

The next publishable milestone after Activation X-Ray Try-in-5-Minutes is
**Local Memory State Influence Boundary Report**.

The user-operable command is:

```sh
git clone https://github.com/ctxgov/ctxgov.git
cd ctxgov
python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/
```

Then point it at your own local memory/context/state file:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md
```

Directory input is also supported for bounded local scans:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/
```

For CI or product integration, use the optional blocked-ref gate:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --fail-on-blocked
```

To emit only the machine-readable gate for a wrapper or CI step:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked
```

The v0 gate contract is documented at
`schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json`,
with blocked and passing sample outputs at
`release/memory-state-governability-overlay/2026-06-11/integration-gate.example.json`
and
`release/memory-state-governability-overlay/2026-06-11/integration-gate.pass.example.json`.
The full report contract is documented at
`schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json`.
The copyable consumer wrapper example contract is documented at
`schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json`,
with blocked/pass sample outputs at
`release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json`
and
`release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json`.
The product integration quickstart is documented at
`release/memory-state-governability-overlay/2026-06-11/product-integration-quickstart.md`;
it is the handoff index for report generation, the fail-closed gate, wrapper
decisions, schema examples, and the no-raw-content boundary.
This consumer wrapper contract is local and example-scoped.
This is a local tooling contract, not a stable protocol or provider
compatibility claim.

To check the local gate contract, sample output, stdout JSON shape, and
`--fail-on-blocked` exit-code behavior together:

```sh
python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py
```

To check the full report contract, raw-content boundary, and embedded gate
counts together:

```sh
python3 scripts/check_memory_state_influence_boundary_report_contract.py
```

To run a consumer integration smoke test for a product wrapper consuming the
report/gate and making block-vs-allow decisions without raw content:

```sh
python3 scripts/check_memory_state_influence_boundary_consumer_integration.py
```

To check the copyable consumer wrapper output schema, blocked/pass example
drift, decision mapping, and no-raw-content boundary:

```sh
python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py
```

To run a copyable consumer wrapper example that calls the report/gate CLI and
emits a `block` decision for blocked inputs:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py
```

To run the same wrapper against a clean inform-only input and see an
`allow_inform_only` decision:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
```

To check that the prepared HN/LinkedIn/X release is distinct from the prior
claim-firewall and Activation X-Ray launches:

```sh
python3 scripts/check_memory_state_influence_boundary_release_distinctness.py
```

To smoke-test the BYO path with a temporary repo-external memory-state
directory, blocked/pass gate exit codes, input-relative paths, omitted inputs,
and secret-like redaction:

```sh
python3 scripts/check_memory_state_influence_boundary_byo_smoke.py
```

The JSON report includes an `integration_gate` object with
`default_exit_code`, `fail_on_blocked_exit_code`, blocked/omitted/stale/imported
counts, and `raw_content_included=false`.

It reads user-supplied local memory/context/state files and writes:

- `.ctxvault/memory-state-governability-overlay/influence-boundary-report.json`
- `.ctxvault/memory-state-governability-overlay/influence-boundary-report.md`
- `.ctxvault/memory-state-governability-overlay/influence-boundary-report.html`

Unsupported or over-limit inputs are counted as omitted. The report keeps a
bounded skipped-input sample rather than copying every skipped path from a large
directory. Malformed JSON/JSONL/TOML state exports are blocked until the state
export is parseable.

The original no-argument command remains available as a built-in sample, but
the publishable path is the user-supplied file/directory audit above.

Public page candidate after publication:

`https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html`

## What Users Can Test

- A local audit over user-supplied `CLAUDE.md`, `AGENTS.md`, `MEMORY.md`,
  project notes, MDX context files, JSON/JSONL checkpoint exports,
  YAML/YML state files, or TOML state profiles.
- A bounded directory scan that classifies candidate memory/context/state refs,
  inform-only allowed refs, blocked refs, omitted refs, stale/superseded refs,
  imported context refs, and missing proof.
- A report that includes paths, line refs, structured JSON/TOML/YAML key/value path
  refs, hashes, signal ids, and decisions plus review recommendations while
  excluding raw file content.
- Input-relative path rendering for repo-external files and directories, so
  local absolute paths are not emitted by default.
- The optional `--fail-on-blocked` gate for CI or product integration, where
  blocked refs make the command exit non-zero while still writing the report.
- `--format gate` for wrappers that only need the machine-readable
  `integration_gate` payload.
- A full report JSON Schema and local contract checker for product integration
  tests that consume the full influence-boundary report.
- A consumer integration smoke checker that consumes the full report and
  `integration_gate` payload, then proves blocked inputs become `block` and
  clean inform-only inputs become `allow_inform_only`.
- A consumer wrapper example JSON Schema, blocked/pass sample outputs, and
  local contract checker for products copying the wrapper shape directly.
- A v0 gate JSON Schema and sample output for local wrapper tests.
- A local contract checker for schema, sample-output, stdout, and exit-code
  drift.
- A BYO smoke checker that creates repo-external local inputs and verifies
  blocked/pass gate behavior, input-relative paths, omitted unsupported files,
  and secret-like redaction.
- A machine-readable `integration_gate` object for product integration without
  reconstructing gate state from multiple report sections.
- The mapping from visible local state to required governance proof: source
  refs, selected/omitted/blocked refs, stale or superseded refs, authority
  ceiling, policy grant, final-state assertion, rollback, deletion propagation,
  and side-effect boundary.
- The claim boundary that blocks compatibility, support, endorsement,
  adoption, security, benchmark, savings, and stable-protocol claims.

## Positioning

This is not a provider integration, provider support announcement, adapter
release, compatibility matrix, benchmark, or endorsement claim.

The public-safe message is:

> CtxGov can now audit user-supplied local memory/context/state files and report
> which refs are inform-only, blocked, omitted, stale, imported, or unsupported
> before they are allowed to influence behavior.

## Local Gates

Run:

```sh
python3 scripts/check_memory_state_influence_boundary_final_preflight.py
python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --fail-on-blocked
python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/
python3 scripts/check_memory_state_influence_boundary_byo_smoke.py
python3 scripts/check_memory_state_influence_boundary_report_contract.py
python3 scripts/check_memory_state_influence_boundary_consumer_integration.py
python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
python3 scripts/run_memory_state_governability_overlay_demo.py
python3 scripts/render_memory_state_governability_overlay_social_payload.py
python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py
python3 scripts/check_memory_state_governability_overlay_publish_pack.py
python3 scripts/build_memory_state_influence_boundary_publication_bundle.py
python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py
python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py
python3 scripts/render_memory_state_influence_boundary_publish_command_envelope.py
python3 scripts/check_memory_state_influence_boundary_public_checkout_readiness.py --check-live
```

Expected: all pass while public benchmark, savings, compatibility, adoption,
support, security, endorsement, provider integration, runtime adapter, SARIF
upload, and stable-protocol claims remain blocked.

The final preflight also materializes the publication bundle into a temporary
clean git checkout and verifies that all listed publication files copy without
commit, push, release, live URL check, or outreach side effects.
It also smoke-tests the owner public patch publisher in dry-run mode and
verifies that no target checkout write, commit, push, public release, or
outreach occurs.

This release pack also includes
`public-checkout-readiness-receipt.md`, which records a no-push smoke test
against a fresh public `ctxgov/ctxgov` checkout.

The owner publish packet is rendered by:

```sh
python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py
```

The owner publish packet contract is checked by:

```sh
python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py
```

After a public page deploy, run the live URL check before manual platform
posting:

```sh
python3 scripts/check_memory_state_influence_boundary_live_publication.py --live
```

To apply the prepared file bundle into a clean local public checkout without
commit or push:

```sh
python3 scripts/materialize_memory_state_influence_boundary_publication_bundle.py --checkout <clean-ctxgov-checkout>
```

To dry-run the owner publication flow without writing the target checkout:

```sh
python3 scripts/publish_memory_state_influence_boundary_public_patch.py --checkout <clean-ctxgov-checkout>
```

Add `--materialize` to copy the bundle and rerun target preflight without commit
or push. Commit and push require explicit `--execute-commit` and
`--execute-push` flags.
