# CtxVault Schemas

This directory is the canonical schema home for `ctxvault`.

It promotes the earlier research-session schema work into repo-owned assets that
future implementation and validation can evolve without rewriting the historical
knowledge archive.

## Layout

```text
schemas/
  README.md
  json/
    ctxvault-core-v0.schema.json
    ctxvault-governance-v0.schema.json
    ctxvault-controls-v0.schema.json
    ctxvault-projection-governance-kernel-v041.schema.json
    ctxvault-runtime-evidence-receipt-v0.schema.json
  python/
    pydantic_models_v0.py
    governance_models_v0.py
    controls_models_v0.py
```

## Schema families

- `ctxvault-core-v0.schema.json`
  - deterministic core objects
  - sessions, episodes, turns, workstreams, prompts, memories, knowledge
    artifacts, context bundles, and eval runs
- `ctxvault-governance-v0.schema.json`
  - governance and adapter objects
  - claim records, evidence links, audit runs, adapter capability profiles, and
    plugin manifests
- `ctxvault-controls-v0.schema.json`
  - operational control objects
  - backup receipts, protection policy rules, rollback decisions, and
    projection receipts
- `ctxvault-projection-governance-kernel-v041.schema.json`
  - v0.4.1 schema explanation objects
  - source evidence, candidate context, review decisions, projections, handoff
    packet references, and receipt states for reviewed context handoff
- `ctxvault-runtime-evidence-receipt-v0.schema.json`
  - experimental runtime evidence receipt shape
  - observed source refs, execution context, bounded outcome attribution,
    explicit redacted/omitted/unavailable output states, rollback observation
    state, and claims the receipt does not make

## Canonical rules

- New repo-owned assets use `ctxvault` as the canonical project and scope name.
- Historical session paths such as `2026-04-18-context-vault-spec` remain
  unchanged when they refer to the archived research session itself.
- The deterministic core must remain meaningful without any local or remote
  model service.
- Model-assisted capabilities are represented explicitly as adapter profiles
  rather than hidden assumptions in the core schema.
- Runtime evidence receipts are review artifacts, not trace truth or runtime
  ownership claims.

## Current gaps

- The repo now has a no-dependency fixture validation script in
  `scripts/validate_fixtures.py`; runtime validation against the Pydantic models
  still needs the optional `schema` dependency set before it can become part of
  a regular check target.
- More fixtures should be promoted from the knowledge-session examples so the
  corpus covers more edge cases, not just the happy path.
- Additional policy fields may be needed once backup receipts and export gates
  are codified.
- The runtime evidence receipt is experimental and should not be treated as a
  stable protocol, compatibility certification, benchmark result, or provider
  fault claim.

## Local validation

Syntax-level checks:

```bash
python3 -m py_compile schemas/python/pydantic_models_v0.py schemas/python/governance_models_v0.py schemas/python/controls_models_v0.py
python3 scripts/validate_fixtures.py
```
