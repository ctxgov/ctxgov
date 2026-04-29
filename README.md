# CtxVault

AI work needs a source of truth outside the chat window.

CtxVault is a local context layer for preserving the decisions, constraints,
and working state that AI tools need to carry across sessions and workflows.

v0.2 is a developer-framework milestone. It keeps the reviewed
source-to-context-to-projection loop from M1 and adds read-only projection
adapter healthchecks, runtime receipt evidence, review ergonomics, and optional
local snapshot/replica backup writes.

This public repository exposes the deterministic trust floor behind that loop:

- file-backed local objects
- deterministic policy, privacy, and receipt surfaces
- CLI and MCP entry points over the same local core
- review-gated promotion and projection receipts
- experimental projection healthchecks and runtime receipts
- public schemas, fixtures, and deterministic tests

## Official Project

This repository is the maintainer-controlled public core for `ctxvault`.

Official releases, schemas, fixtures, compatibility checks, and any signed or
notarized app artifacts, if provided, are published only through
maintainer-controlled CtxVault channels. Forks and integrations are welcome
under the Apache-2.0 core license, but unofficial builds should use distinct
names and should not imply maintainer endorsement.

This repository does not include the private first-party workbench, webapp,
native wrapper source, signing operations, notarization operations, release
operations, or brand assets. Those remain separate product layers.

## Scope

The public core is for users who want to inspect or build on:

- reviewed context organization around workstreams
- context injection into practical working surfaces
- local context storage and rebuildable indexes
- deterministic review-gated promotion flows
- local privacy and policy gates
- artifact and receipt surfaces
- read-only projection adapter healthchecks
- optional local snapshot/replica backup writes

The public core currently marks these contracts as experimental:

- `src/ctxvault/intelligence.py`
- `Episode`
- `Workstream`
- plugin manifest and projection receipt contracts
- the first local plugin executor paths for context injection targets
- projection adapter healthchecks
- runtime event receipts

Experimental means they are useful and inspectable, but not yet frozen as
long-term public semantics.

## v0.2 Developer Framework

v0.2 focuses on making the local context core easier to inspect and integrate
with real AI work surfaces:

- projection adapter healthchecks for `AGENTS.md`, `CLAUDE.md`, and workstream
  briefs
- runtime receipt evidence attached to healthcheck output
- governed review flows that keep ranking advisory
- optional local backup writes from a governed snapshot into an explicit local
  file target

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

## v0.2 Evidence

The v0.2 developer-framework evidence is described in:

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
- `docs/v0.2-m2-developer-framework.md`
- `docs/v0.2-m2-compatibility-evidence.md`
- `docs/v0.2-m2-release-notes.md`
- `fixtures/README.md`
- `schemas/README.md`
- `TRADEMARK.md`

## Feedback

The fastest useful feedback is a concrete first-run report:

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
