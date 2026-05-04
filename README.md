# CtxVault

AI work needs a source of truth outside the chat window.

CtxVault is a local-first context layer for AI work. It preserves the
decisions, constraints, and working state that should survive across chats,
agents, editors, and command-line sessions.

v0.3.3 is the safe context handoff hardening milestone. It makes the
deterministic selector easier to run, inspect, and approve before context
reaches AI tools:

`local sources -> context slices -> context-prepare -> privacy preflight -> context-project -> projection receipts`

The baseline is intentionally constrained: no model call, no embedding service,
no vector database, no remote provider. The value is that the operator can see
which local context was selected, why it was allowed, how large it is, and
which projection receipt links it to an AI work surface.

The roadmap treats this as AI work quality infrastructure: specs define what
"done" means, context receipts explain what was selected or blocked, and trace
or runtime receipts can later inspect how AI work happened. v0.3.3 proves only
the deterministic safe handoff part of that system.

This public repository exposes the deterministic trust floor behind that
source-to-context-to-projection loop:

- local file-backed objects and rebuildable indexes
- CLI and MCP entry points over the same deterministic core
- review-gated promotion and projection receipts
- experimental compiled workstream state with source refs
- deterministic context slicing and local context search
- source-grouped context selection with token budget previews
- selected-slice privacy preflight before projection
- projection receipts linked to context-selection receipts
- owner-operated public review pack with reusable public-source scenarios,
  boundary checks, and a synthetic blocked-selection check
- read-only doctor diagnostics and projection healthchecks
- Markdown-vault import as source material
- review-gated logical purge for derived slice, search, preview, and selected
  projection data
- public schemas, fixtures, and deterministic tests

## Official Project

This repository is the maintainer-controlled public core for `ctxvault`.

Official releases, schemas, fixtures, and compatibility checks are published
only through maintainer-controlled CtxVault channels. Forks and integrations
are welcome under the Apache-2.0 core license, but unofficial builds should use
distinct names and should not imply maintainer endorsement.

This repository contains the public deterministic core. Optional product
surfaces and maintainer release operations remain outside this repo.

## What To Inspect First

If you are evaluating the project, start with:

- the Quick Start below for a clean deterministic run;
- `spaces/huggingface/v032-deterministic-demo/` for the toy-source demo;
- `scripts/run_v032_deterministic_demo.py` for the offline demo loop;
- `scripts/inspect_v032_demo_receipts.py` for receipt-chain inspection;
- `scripts/run_v032_selection_scorecard.py` for lightweight selection quality
  and safety checks;
- `scripts/run_v033_public_review_pack.py` for owner-operated public package
  review before publication.

## Scope

The public core is for developers who want to inspect or build on:

- reviewed context organization around workstreams
- context projection into practical AI working surfaces
- local context storage and rebuildable indexes
- deterministic review-gated promotion flows
- local privacy and policy gates
- artifact and receipt surfaces
- early source-of-truth and evidence semantics for future AI work quality
  contracts
- compiled current workstream state with source refs
- local context slice rebuild, search, and selected-slice preflight
- explicit logical purge of derived data without a secure-wipe claim
- Markdown-vault import as source material
- read-only projection adapter healthchecks
- optional local snapshot/replica backup writes

The public core currently marks these contracts as experimental:

- `src/ctxvault/intelligence.py`
- `Episode`
- `Workstream`
- compiled workstream state read model
- `doctor` report
- plugin manifest and projection receipt contracts
- the first local plugin executor paths for reviewed context projection targets
- projection adapter healthchecks
- runtime event receipts
- context selection receipts

Experimental means useful and inspectable, but not yet frozen as long-term
public semantics.

## v0.3.3 Safe Context Handoff

v0.3.3 is a hardening release over the v0.3.2 composer. It does not add model,
embedding, vector, remote provider, official plugin, live connector, or public
Workbench dependencies. It makes the public path easier to verify:

- run the public review pack from reusable public-source scenario fixtures
- prepare exact local slices with `context-prepare`
- inspect `selection_status`, `handoff_ready`, budget state, warnings, blocked
  reasons, and receipt paths
- project approved selected slices with `context-project`
- verify the projection receipt and linked context-selection receipt
- confirm the synthetic secret fixture is withheld and blocks projection when
  explicitly selected

## v0.3.2 Context Selection Composer

v0.3.2 is a fast-follow release after v0.3.1. It does not add model,
embedding, vector, remote provider, official plugin, or live connector
dependencies. It adds the deterministic step that should happen before context
is projected into an AI work surface: choose exact local slices, inspect the
budget, run privacy preflight, and keep the receipt chain.

- source-grouped local context candidate composition
- explicit multi-slice selection
- token budget preview
- target-aware privacy preflight for selected slices
- `ctxvault.context-selection-receipt/v1`
- projection receipts linked to context selection receipts
- local pin, hide, and archive preferences for slice suggestions
- CLI and MCP tools over the same deterministic core

## v0.3.1 Local Safety And Context Slicing

v0.3.1 keeps the v0.3 source-to-context-to-projection path and adds the local
safety substrate needed for safer context selection:

- import project docs, sessions, and Markdown notes
- organize them around reviewed `Workstream` state
- compile current truth, open questions, decisions, warnings, and source refs
- rebuild deterministic local context slices from governed sources
- search slices locally without model, embedding, remote service, or hosted API
- run privacy preflight before selected slices are projected
- project that state into `AGENTS.md`, `CLAUDE.md`, and a workstream brief
- inspect projection receipts, privacy preflight receipts, logical purge
  receipts, tombstones, and read-only diagnostics

This is the same source-to-context-to-projection loop from M1, now made denser
with compiled current state and explicit health visibility.

CtxVault remains a local context layer for AI work, not a single-harness memory
plugin. ChatGPT, Claude.ai, DeepSeek, local Ollama-style UIs, Claude Code,
Codex, Cursor, shell traces, project notes, and rules files can all be source
or target surfaces over time. Current named-source support is explicit:
normalized transcript import where stable, and experimental adapters only where
marked as such.

## Quick Start

Run deterministic checks:

```bash
python3 scripts/run_deterministic_checks.py
```

Run the v0.3.3 public package review pack:

```bash
python3 scripts/run_v033_public_review_pack.py --root /tmp/ctxvault-v033-public-review --force
```

Start with the generated human report:

```text
/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/owner-review.md
/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/owner-review.html
```

Run the clean-user core validation flow:

```bash
bash scripts/run_clean_user_core_validation.sh /tmp/ctxvault-clean-verify
```

Run the v0.3.2 deterministic demo:

```bash
python3 scripts/run_v032_deterministic_demo.py --root /tmp/ctxvault-v032-demo
python3 scripts/inspect_v032_demo_receipts.py --root /tmp/ctxvault-v032-demo
python3 scripts/run_v032_selection_scorecard.py --root /tmp/ctxvault-v032-scorecard
```

Emit reviewed context projections:

```bash
PYTHONPATH=src python3 -m ctxvault.cli emit-agents-projection --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema --output-path exports/AGENTS.md --receipt-output-path artifacts/agents-md-receipt.json
PYTHONPATH=src python3 -m ctxvault.cli emit-claude-projection --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema --output-path exports/CLAUDE.md --receipt-output-path artifacts/claude-md-receipt.json
PYTHONPATH=src python3 -m ctxvault.cli emit-wiki-projection --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema --output-path exports/workstream.md --receipt-output-path artifacts/workstream-md-receipt.json
```

Build compiled workstream state:

```bash
PYTHONPATH=src python3 -m ctxvault.cli compiled-workstream-state --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema
```

Import a Markdown vault as source material:

```bash
PYTHONPATH=src python3 -m ctxvault.cli markdown-vault-import --root /tmp/ctxvault-clean-verify --vault-path /path/to/notes --scope-kind project --scope-value ctxvault
```

Run read-only diagnostics:

```bash
PYTHONPATH=src python3 -m ctxvault.cli doctor --root /tmp/ctxvault-clean-verify
```

Rebuild and search deterministic local context slices:

```bash
PYTHONPATH=src python3 -m ctxvault.cli context-slice-rebuild --root /tmp/ctxvault-clean-verify
PYTHONPATH=src python3 -m ctxvault.cli context-search --root /tmp/ctxvault-clean-verify --query "projection receipts"
```

Run selected-slice privacy preflight before projecting a slice into a target:

```bash
PYTHONPATH=src python3 -m ctxvault.cli context-selection-preflight --root /tmp/ctxvault-clean-verify --slice-ref SLICE_REF --target-kind agents-md --write-receipt
```

Compose selected local slices with a budget preview and a selection receipt:

```bash
PYTHONPATH=src python3 -m ctxvault.cli context-selection-compose --root /tmp/ctxvault-clean-verify --query "projection receipts" --target-kind harness.agents-md --slice-ref SLICE_REF --token-budget 1200 --write-receipt
```

Prepare and project a safe context handoff:

```bash
PYTHONPATH=src python3 -m ctxvault.cli context-prepare --root /tmp/ctxvault-clean-verify --query "projection receipts" --target-kind harness.agents-md --token-budget 1200 --write-receipt
PYTHONPATH=src python3 -m ctxvault.cli context-project --root /tmp/ctxvault-clean-verify --target workstream-brief --workstream-id ws_20260421_ctxvault_schema --slice-ref SLICE_REF --output-path exports/workstream.md --receipt-output-path artifacts/workstream-md-receipt.json
```

Pin, hide, or archive local slice suggestions:

```bash
PYTHONPATH=src python3 -m ctxvault.cli context-slice-preference-set --root /tmp/ctxvault-clean-verify --slice-ref SLICE_REF --action pin --target-kind harness.agents-md
```

Plan a review-gated logical purge of derived data:

```bash
PYTHONPATH=src python3 -m ctxvault.cli logical-purge-plan --root /tmp/ctxvault-clean-verify --slice-ref SLICE_REF --include-projections
```

Run read-only projection adapter healthchecks:

```bash
PYTHONPATH=src python3 -m ctxvault.cli adapter-healthcheck --root /tmp/ctxvault-clean-verify --target-kind agents-md --target-path exports/AGENTS.md
PYTHONPATH=src python3 -m ctxvault.cli adapter-healthcheck --root /tmp/ctxvault-clean-verify --target-kind claude-md --target-path exports/CLAUDE.md
PYTHONPATH=src python3 -m ctxvault.cli adapter-healthcheck --root /tmp/ctxvault-clean-verify --target-kind workstream-brief --target-path exports/workstream.md
```

Write an optional local snapshot/replica backup to an explicit local target:

```bash
PYTHONPATH=src python3 -m ctxvault.cli local-backup-write --root /tmp/ctxvault-clean-verify --target file:///tmp/ctxvault-clean-verify-backup --label "local backup rehearsal" --device-id local-target
```

Inspect the default runtime layout:

```bash
PYTHONPATH=src python3 -m ctxvault.cli print-layout
```

Initialize a local vault:

```bash
PYTHONPATH=src python3 -m ctxvault.cli init-vault
```

Run the stdio MCP transport:

```bash
PYTHONPATH=src python3 -m ctxvault.cli serve-mcp
```

## M1 Projection Evidence

Run the source-to-projection golden path:

```bash
python3 scripts/run_context_injection_m1_golden_path.py --root /tmp/ctxvault-m1-context-injection
```

The checked-in M1 fixture evidence is in:

- `fixtures/context-injection-m1/projections/AGENTS.md`
- `fixtures/context-injection-m1/projections/CLAUDE.md`
- `fixtures/context-injection-m1/projections/workstream-brief.md`
- `fixtures/context-injection-m1/projections/agents-md-receipt.json`
- `fixtures/context-injection-m1/projections/claude-md-receipt.json`
- `fixtures/context-injection-m1/projections/workstream-brief-receipt.json`
- `fixtures/m1-context-injection/README.md`

## v0.3.3 Evidence

The v0.3.3 safe handoff path, v0.3.2 context-selection composer, v0.3.1 local
safety, and compiled context projection evidence is described in:

- `docs/v0.3-compiled-context.md`
- `docs/v0.3.3-release-notes.md`
- `fixtures/v0.3.3-public-review/README.md`
- `docs/v0.3.2-release-notes.md`
- `docs/v0.3.2-injection-composer/implementation-plan.md`
- `docs/v0.3.2-injection-composer/experimental-schemas/ctxvault-context-selection-receipt-v1.schema.json`
- `docs/v0.3.1-release-notes.md`
- `docs/v0.3.1-local-safety/approved-boundary-decisions.md`
- `docs/v0.3.1-local-safety/hardening-status.md`
- `docs/v0.3-release-notes.md`
- `docs/v0.2-m2-developer-framework.md`
- `docs/v0.2-m2-compatibility-evidence.md`
- `docs/v0.2-m2-release-notes.md`

The local backup write path is optional local durability. It creates a governed
snapshot, copies the snapshot manifest, restore bundle, and sync manifest into
an explicit local target, and verifies the target as a replica before reporting
success. It does not make a hosted service the source of truth and does not
replace a separate offsite backup strategy.

## Public Docs

- `docs/public-core-boundary.md`
- `docs/public-release-checklist.md`
- `docs/experimental-contract-evolution-policy.md`
- `docs/workstream-plan-ledger-contract.md`
- `docs/v0.3-compiled-context.md`
- `docs/v0.3.3-release-notes.md`
- `docs/v0.3.2-release-notes.md`
- `docs/v0.3.2-injection-composer/implementation-plan.md`
- `docs/v0.3.1-release-notes.md`
- `docs/v0.3.1-local-safety/approved-boundary-decisions.md`
- `docs/v0.3.1-local-safety/hardening-status.md`
- `docs/v0.3-release-notes.md`
- `docs/v0.2-m2-developer-framework.md`
- `docs/v0.2-m2-compatibility-evidence.md`
- `docs/v0.2-m2-release-notes.md`
- `fixtures/v0.3.3-public-review/README.md`
- `fixtures/README.md`
- `schemas/README.md`
- `CHANGELOG.md`
- `TRADEMARK.md`

## Feedback

The most useful feedback is concrete: what you ran, what confused you, and
which receipt, slice, projection, or workflow step was hard to trust.

- v0.3 Compiled Context feedback:
  `.github/ISSUE_TEMPLATE/workflow-pain-point.yml`
- v0.3.1 local safety, privacy, or purge feedback:
  `.github/ISSUE_TEMPLATE/trust-or-privacy-concern.yml`
- v0.3.2 context-selection composer feedback:
  `.github/ISSUE_TEMPLATE/workflow-pain-point.yml`
- v0.3.3 safe context handoff feedback:
  `.github/ISSUE_TEMPLATE/workflow-pain-point.yml`
- v0.2/M2 Developer Framework Feedback:
  `.github/ISSUE_TEMPLATE/v0.2-m2-feedback.yml`
- M1 Quick Feedback:
  `.github/ISSUE_TEMPLATE/m1-quick-feedback.yml`
- workflow friction:
  `.github/ISSUE_TEMPLATE/workflow-pain-point.yml`
- trust or privacy concerns:
  `.github/ISSUE_TEMPLATE/trust-or-privacy-concern.yml`
- broader positioning or adapter discussion: GitHub Discussions

## License

Apache-2.0. See `LICENSE`.

Trademark and official-project usage guidelines are in `TRADEMARK.md`.
