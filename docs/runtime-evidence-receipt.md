# Runtime Evidence Receipt

Status: experimental public schema note. This document describes a reviewable
evidence artifact shape; it does not approve runtime execution, provider/model
calls, hosted tracing, compatibility certification, benchmark claims, or stable
protocol status.

## Boundary

A runtime evidence receipt is not the trace truth. It is a narrower claim:
specific source refs were observed, reduced by a named producer and schema
version, with explicit omissions, into a reviewable artifact.

The receipt should let a reviewer answer:

- What was observed?
- What was intentionally not carried?
- What claim is this receipt not making?

## Field Shape

The experimental fixture in
`fixtures/evidence/runtime-evidence-receipt.json` uses these sections:

| Section | Purpose |
| --- | --- |
| `identity` | Receipt id, creation time, producer, producer version, and producer schema version. |
| `source_refs` | Trace, span, tool-call, artifact, output, config, rollback, or other refs plus digests when available. Raw source bodies are not carried. |
| `execution_context` | Runtime or framework version, config fingerprint, seed fingerprint, and environment label. |
| `outcome` | Status, error class, failure stage, observed timestamp, and bounded attribution. |
| `omissions` | Explicit `redacted`, `omitted`, and `unavailable` markers with reasons. |
| `output_state` | Output role, size, digest, and explicit state when provider/model output is redacted, omitted, unavailable, digest-only, or not produced. |
| `rollback` | Rollback ref, reversibility, whether a path is available, and whether rollback was actually observed. |
| `claims_not_made` | Guardrails such as no trace-truth, runtime-ownership, provider-fault, rollback-executed, reliability, compatibility, or benchmark claim. |

## Attribution Rule

Failure attribution should stay at the evidence level. For example:

- Reviewable: `failure_stage` is `tool_argument_validation`.
- Reviewable: `failure_attribution.level` is `stage_only`.
- Too strong without source evidence: `provider_fault`.

The same distinction applies to rollback. Having a rollback path is different
from observing rollback execution. Use `rollback.observed_state` to record the
difference.

## Coherence Invariants

The v0 schema enforces a few cross-field guardrails so a receipt cannot validate
while overclaiming:

- `output_state.state: observed_digest_only` requires both `digest` and
  `size_bytes`.
- `output_state.state: not_produced` requires both `digest` and `size_bytes` to
  be null.
- `rollback.observed_state: executed` requires `observed_at`, `path_available`,
  and `rollback_ref`.
- `rollback.observed_state: path_available_not_executed` requires
  `path_available` and `rollback_ref`, and keeps `observed_at` null.
- `failure_attribution.level: source_supported_component` requires
  `source_ref`.
- A receipt that observed rollback execution cannot also list
  `rollback_executed` in `claims_not_made`.

## Public Output Boundary

If provider or model output is not approved for public examples, the receipt can
still carry an output digest, size, role, and explicit output state. Absence
must not look like nothing existed. Use the same state vocabulary as omission
records: `redacted`, `omitted`, and `unavailable`, plus `observed_digest_only`
and `not_produced`.

## Validation

The schema lives at
`schemas/json/ctxvault-runtime-evidence-receipt-v0.schema.json`.

Run:

```bash
python3 scripts/validate_fixtures.py
PYTHONPATH=src python3 -m pytest tests/test_runtime_evidence_receipt.py -q
```
