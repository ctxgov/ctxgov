# CtxVault Public Core Boundary

This repository is the public deterministic core of `ctxvault`.

## What This Repo Includes

- schemas and fixtures
- deterministic storage, policy, privacy, receipt, and versioning modules
- CLI and MCP entry points over the same local core
- tests for deterministic behavior and public contracts

## What Stays Outside This Repo

- the first-party workbench and web UI
- native wrapper source, signing, notarization, and update channels
- private product strategy and competitive reasoning
- machine-local state and sample personal data

## Experimental Public Contracts

These public contracts are intentionally marked experimental:

- `src/ctxvault/intelligence.py`
- `Episode`
- `Workstream`
- plugin manifest and projection receipt contracts
- the first local plugin executor path
- projection adapter healthchecks
- runtime event receipts

They are useful and inspectable today, but still expected to evolve.

## Trust Model

The public trust promise is:

- the deterministic correctness floor stays inspectable
- policy and privacy gates remain visible
- private product layers do not replace the source of truth
- first-party convenience surfaces can evolve without weakening the public core
