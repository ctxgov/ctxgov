# Memory State Influence Boundary Example

This directory is a synthetic local input sample for:

```sh
python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/
```

It is designed to exercise the local input audit path without provider calls,
runtime adapters, backend writes, target writes, package publication, or
outreach.

The files are examples only. They are not provider exports, compatibility
fixtures, benchmark cases, adoption evidence, or security guarantees.

The sample includes Markdown, MDX, JSON, JSONL, YAML, and TOML inputs so the
default fresh-checkout command exercises the supported local state file
families.

The product integration quickstart for consuming the report/gate from another
tool is documented at
`release/memory-state-governability-overlay/2026-06-11/product-integration-quickstart.md`.

To see how a product wrapper can consume the report/gate output and make a
local block decision without reading raw file content:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/
```

To run the same wrapper against a clean inform-only input and see an
`allow_inform_only` decision:

```sh
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
```
