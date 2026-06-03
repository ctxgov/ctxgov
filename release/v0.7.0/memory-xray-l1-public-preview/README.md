# Memory X-Ray Report L1 Public-Safe Example

Status: L1 public-safe report-shape example. This is not a product release, public benchmark, provider compatibility matrix, live adapter, adoption claim, or stable protocol claim.

Memory X-Ray Report shows the shape of a source-backed, rollbackable, consequence-bounded memory-mutation review.

## What This Shows

- A memory candidate should point to selected source refs.
- Omitted, missing, and contradicted refs should stay visible.
- A consequence ceiling should limit what future behavior the memory can affect.
- A rollback template should exist before a memory becomes durable authority.
- A model-state surface passport should say which kind of state the report inspected.

## Example Pack

- `memory-xray-l1-examples-pack.json` contains provider-neutral sanitized examples.
- examples: 5
- source/rollback/consequence shapes ready: 5/5
- private paths redacted: True
- provider names redacted: True

## How To Read A Row

Each sanitized row has:

- `source_coverage`: counts for selected, omitted, missing, and contradicted refs.
- `consequence_ceiling`: the maximum allowed downstream effect class.
- `blocked_effects`: behavior changes that remain blocked.
- `rollback_template`: how to discard or supersede the candidate report.
- `mgp_receipt_shape`: the object types a fuller private report would contain.

## Not Claimed

Do not read this pack as:

- a public benchmark result
- a productivity improvement claim
- adoption proof
- support for a named provider or framework
- a live adapter
- a safety or security guarantee
- a stable protocol claim

## Missing For A Full Product Release

These are intentionally not required for this L1 report-shape preview, but they are required before stronger releases:

- L2 case study: permission, source freshness, downstream citation or maintainer feedback, claim lint, rollback.
- L3 public CLI beta: stable schema, deterministic validation, failure-mode docs, no backend/provider writes.
- L4 public benchmark: real telemetry, hidden holdout, negative cases, reproducible methodology, equal-or-better quality gates.
- L5 stable protocol: multiple downstream uses, migration/versioning, compatibility policy, public spec review, rollback strategy.

## Rollback

Delete or supersede this directory. No provider state, memory backend, package, public benchmark, public adoption claim, or live adapter is created by this preview.
