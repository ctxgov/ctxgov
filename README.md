# CtxVault

AI work needs a source of truth outside the chat window.

CtxVault is a local context layer for preserving the decisions, constraints,
and working state that AI tools need to carry across sessions and workflows.

M1 starts with a reviewable source-to-context-to-projection loop for
`AGENTS.md`, `CLAUDE.md`, and workstream briefs.

This public repository exposes the deterministic trust floor behind that loop:

- file-backed local objects
- deterministic policy, privacy, and receipt surfaces
- CLI and MCP entry points over the same local core
- review-gated promotion and projection receipts
- public schemas, fixtures, and tests

This repository does not include the private first-party workbench, webapp, or
native wrapper source. Those remain separate product layers.

## Scope

The public core is for users who want to inspect or build on:

- reviewed context organization around workstreams
- context injection into practical working surfaces
- local context storage and rebuildable indexes
- deterministic review-gated promotion flows
- local privacy and policy gates
- stable artifact and receipt surfaces

The public core currently marks these contracts as experimental:

- `src/ctxvault/intelligence.py`
- `Episode`
- `Workstream`
- plugin manifest and projection receipt contracts
- the first local plugin executor paths for context injection targets

Experimental means they are useful and inspectable, but not yet frozen as
long-term public semantics.

## Direction

M1 proves the source-to-review-to-injection loop: gather sources, organize them
around a workstream, review what becomes durable, and inject approved context
into practical working surfaces.

The next track is broader projection and adapter coverage, guided by public
feedback and protected by the same review, policy, and receipt model. Near-term
directions include:

- additional projection targets beyond `AGENTS.md` and `CLAUDE.md`
- harness surface inventory and adapter healthchecks before broad connector
  expansion
- PromptOps and review ergonomics over the same governed local object model
- optional first-party convenience surfaces that do not replace the public core

## Quick Start

Run deterministic checks:

```bash
python3 scripts/run_deterministic_checks.py
```

Run the clean-user core validation flow:

```bash
bash scripts/run_clean_user_core_validation.sh /tmp/ctxvault-clean-verify
```

Emit reviewed context projections:

```bash
PYTHONPATH=src python3 -m ctxvault.cli emit-agents-projection --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema --output-path exports/AGENTS.md --receipt-output-path artifacts/agents-md-receipt.json
PYTHONPATH=src python3 -m ctxvault.cli emit-claude-projection --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema --output-path exports/CLAUDE.md --receipt-output-path artifacts/claude-md-receipt.json
PYTHONPATH=src python3 -m ctxvault.cli emit-wiki-projection --root /tmp/ctxvault-clean-verify --workstream-id ws_20260421_ctxvault_schema --output-path exports/workstream.md --receipt-output-path artifacts/workstream-md-receipt.json
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

## Context Injection M1 Evidence

Run the source-to-injection golden path:

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

## Public Docs

- `docs/public-core-boundary.md`
- `docs/public-release-checklist.md`
- `docs/experimental-contract-evolution-policy.md`
- `docs/workstream-plan-ledger-contract.md`
- `fixtures/README.md`
- `schemas/README.md`

## Feedback

The fastest useful feedback is a concrete first-run report:

- M1 Quick Feedback:
  `.github/ISSUE_TEMPLATE/m1-quick-feedback.yml`
- workflow friction:
  `.github/ISSUE_TEMPLATE/workflow-pain-point.yml`
- trust or privacy concerns:
  `.github/ISSUE_TEMPLATE/trust-or-privacy-concern.yml`
- broader positioning or adapter discussion: GitHub Discussions

## License

Apache-2.0. See `LICENSE`.
