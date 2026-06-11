# Product Integration Quickstart

Status: local example contract only. No provider integration, stable protocol,
compatibility/support claim, security guarantee, benchmark, package
publication, public release, or outreach has been executed.

This quickstart is the handoff for products that want to consume the local
Memory State Influence Boundary output. It wires user-supplied
memory/context/state files into a report, a CI-friendly gate, and a copyable
wrapper decision without consuming raw file content.

## 1. Generate A Local Report

Start with the included sample:

```sh
git clone https://github.com/ctxgov/ctxgov.git
cd ctxgov
python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/
```

Then point the command at your own local memory/context/state file or
directory:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/
```

The command writes:

- `.ctxvault/memory-state-governability-overlay/influence-boundary-report.json`
- `.ctxvault/memory-state-governability-overlay/influence-boundary-report.md`
- `.ctxvault/memory-state-governability-overlay/influence-boundary-report.html`

Supported local input families include Markdown, MDX, text, JSON, JSONL, YAML,
YML, and TOML state files.

## 2. Add The Gate

For CI or a product wrapper, emit only the machine-readable gate and fail
closed when blocked refs are present:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked
```

Gate behavior:

- blocked input returns `fail_on_blocked_exit_code=2`
- clean inform-only input returns `fail_on_blocked_exit_code=0`
- `raw_content_included=false`
- repo-external input paths are rendered as `input/...`

The gate contract lives at:

- `schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json`
- `release/memory-state-governability-overlay/2026-06-11/integration-gate.example.json`
- `release/memory-state-governability-overlay/2026-06-11/integration-gate.pass.example.json`

Verify it with:

```sh
python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py
```

## 3. Consume It From A Product Wrapper

The copyable wrapper example runs the report/gate CLI and maps the result to a
product-facing decision without reading raw input content:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py
```

Expected blocked decision:

- `decision.decision=block`
- `reason=blocked_refs_present`
- `gate_returncode=2`
- `consumed_raw_content=false`
- `raw_content_included=false`

Run the same wrapper against a clean inform-only input:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
```

Expected passing decision:

- `decision.decision=allow_inform_only`
- `reason=gate_passed_no_blocked_refs`
- `gate_returncode=0`
- `consumed_raw_content=false`
- `raw_content_included=false`

The wrapper output contract lives at:

- `schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json`
- `release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json`
- `release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json`

Verify it with:

```sh
python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py
```

## 4. Validate The Full Report Contract

The full report contract lives at:

- `schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json`

Verify the schema, raw-content boundary, and embedded gate counts with:

```sh
python3 scripts/check_memory_state_influence_boundary_report_contract.py
```

Run the higher-level consumer integration smoke test with:

```sh
python3 scripts/check_memory_state_influence_boundary_consumer_integration.py
```

## Integration Boundary

This is intentionally a local v0 tooling contract. It is suitable for testing a
product wrapper that needs block-vs-allow decisions around local AI
memory/context/state files. It is not a provider API, runtime adapter, and is
not a stable protocol, compatibility matrix, security guarantee, benchmark,
adoption claim, or support commitment.
