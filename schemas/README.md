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
    ctxvault-task-shard-context-control-fixture-pack-v0.schema.json
    ctxvault-task-shard-context-import-shapes-v0.schema.json
    ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json
    ctxvault-memory-state-influence-boundary-report-v0.schema.json
    ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json
    trace-import-evidence-packet-v0.json
  context-contract-v0.json
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
- `ctxvault-task-shard-context-control-fixture-pack-v0.schema.json`
  - post-v0.7.0 private fixture pack for Task Shard Context Control
  - task shard plans, per-shard context visas, context budget ledgers, shard
    result receipts, merge receipts, replan triggers, benchmark gates, and
    negative fixture contracts
  - schema and fixtures are private evidence only; they execute no workflow,
    create no worktree, call no provider/model, write no target or memory
    backend, and grant no public or stable-MGP claim
- `ctxvault-task-shard-context-import-shapes-v0.schema.json`
  - post-v0.7.0 private saved-trace/import shape fixture for Task Shard
    Context Control
  - Claude Dynamic Workflows, Cline task history, OpenHands condenser traces,
    Aider repo maps, and Plandex context maps are represented as offline import
    contracts only
  - import shapes must include selected source-ref fields, omitted context-ref
    fields, required source recovery, and visible omitted-context contracts
  - schema and fixtures execute no workflow, create no worktree, call no
    provider/model, write no target or memory backend, and grant no public or
    stable-MGP claim
- `ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json`
  - local v0 gate payload emitted by
    `python3 scripts/run_memory_state_influence_boundary_report.py --format gate`
  - blocked refs return `fail_on_blocked_exit_code=2` when
    `--fail-on-blocked` is used, while raw input content remains excluded
  - validate local stdout, schema, blocked/pass sample outputs, and exit-code drift with
    `python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py`
  - local tooling contract only; no provider integration, compatibility,
    security guarantee, benchmark, savings claim, or stable protocol claim
- `ctxvault-memory-state-influence-boundary-report-v0.schema.json`
  - full local v0 report payload emitted by
    `python3 scripts/run_memory_state_influence_boundary_report.py --input <file-or-dir>`
  - covers user-supplied memory/context/state inputs, input-relative paths,
    file hashes, signal refs, decisions, findings, the embedded
    `integration_gate`, claim boundary, and side-effect boundary
  - requires `raw_content_included=false` for scan limits, file reports,
    signal evidence, and the embedded gate
  - validate local stdout, schema shape, raw-content boundary, and embedded
    gate counts with
    `python3 scripts/check_memory_state_influence_boundary_report_contract.py`
  - local tooling contract only; no provider integration, compatibility,
    security guarantee, benchmark, savings claim, or stable protocol claim
- `ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json`
  - local v0 output shape for the copyable consumer wrapper example
  - covers block vs `allow_inform_only` decisions, gate return codes,
    no-raw-content consumption, command shapes, claim boundary, and side-effect
    boundary
  - validate blocked/pass sample outputs and wrapper example drift with
    `python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py`
  - local tooling contract only; no provider integration, compatibility,
    security guarantee, benchmark, savings claim, or stable protocol claim
- `context-contract-v0.json`
  - v0.6.2 Context Contract SDK packet shape
  - source refs, selected/omitted/blocked/stale/conflicting refs, authority
    layers, output schema, merge rule, risk gates, producer, checked time, and
    rollback
  - schema validity is evidence only; readiness and authority checks remain
    separate
- `trace-import-evidence-packet-v0.json`
  - v0.6.2 Bring Your Trace Importers packet wrapper
  - terminal-log, memory-folder, and typed-output inputs normalize into staged
    `EvidencePacket` objects with nested `ContextContract` payloads
  - importer packets are staged evidence only until an explicit promotion
    receipt creates a canonical candidate

## Canonical rules

- New repo-owned assets use `ctxvault` as the canonical project and scope name.
- Historical session paths such as `2026-04-18-context-vault-spec` remain
  unchanged when they refer to the archived research session itself.
- The deterministic core must remain meaningful without any local or remote
  model service.
- Model-assisted capabilities are represented explicitly as adapter profiles
  rather than hidden assumptions in the core schema.

## Current gaps

- The repo now has a no-dependency fixture validation script in
  `scripts/validate_fixtures.py`; runtime validation against the Pydantic models
  still needs the optional `schema` dependency set before it can become part of
  a regular check target.
- More fixtures should be promoted from the knowledge-session examples so the
  corpus covers more edge cases, not just the happy path.
- Additional policy fields may be needed once backup receipts and export gates
  are codified.

## Local validation

Syntax-level checks:

```bash
python3 -m py_compile schemas/python/pydantic_models_v0.py schemas/python/governance_models_v0.py schemas/python/controls_models_v0.py
python3 scripts/validate_fixtures.py
```
