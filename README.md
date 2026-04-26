# CtxVault

`ctxvault` is an inspectable deterministic local context core for AI work.

This public repository exposes the correctness floor:

- file-backed local objects
- deterministic policy, privacy, and receipt surfaces
- CLI and MCP entry points over the same local core
- public schemas, fixtures, and tests

This repository does not include the private first-party workbench, webapp, or
native wrapper source. Those remain separate product layers.

## Scope

The public core is for users who want to inspect or build on:

- local context storage and rebuildable indexes
- deterministic review-gated promotion flows
- local privacy and policy gates
- stable artifact and receipt surfaces

The public core currently marks these contracts as experimental:

- `src/ctxvault/intelligence.py`
- `Episode`
- `Workstream`
- plugin manifest and projection receipt contracts
- the first local plugin executor path

Experimental means they are useful and inspectable, but not yet frozen as
long-term public semantics.

## Quick Start

Run deterministic checks:

```bash
python3 scripts/run_deterministic_checks.py
```

Run the clean-user core validation flow:

```bash
bash scripts/run_clean_user_core_validation.sh /tmp/ctxvault-clean-verify
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

## Public Docs

- `docs/p0-scope.md`
- `docs/backup-policy-contract.md`
- `docs/public-core-boundary.md`
- `docs/public-release-checklist.md`
- `docs/experimental-contract-evolution-policy.md`
- `docs/workstream-lifecycle.md`
- `docs/workstream-plan-ledger-contract.md`
- `fixtures/README.md`
- `schemas/README.md`

## License

Apache-2.0. See `LICENSE`.
