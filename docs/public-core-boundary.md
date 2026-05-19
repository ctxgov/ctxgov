# CtxVault Public Core Boundary

This repository is the public deterministic core of `ctxvault`.

## What This Repo Includes

- schemas and fixtures
- deterministic storage, policy, privacy, receipt, and versioning modules
- CLI and MCP entry points over the same local core
- tests for deterministic behavior and public contracts

## What Stays Outside This Repo

- optional product surfaces
- maintainer release operations
- non-core planning material
- machine-local state and sample personal data

## Experimental Public Contracts

These public contracts are intentionally marked experimental:

- `src/ctxvault/intelligence.py`
- `Episode`
- `Workstream`
- compiled workstream state read model
- read-only doctor report
- plugin manifest and projection receipt contracts
- the first local plugin executor path
- projection adapter healthchecks
- runtime event receipts
- runtime evidence receipts

They are useful and inspectable today, but still expected to evolve.

## Trust Model

The public trust promise is:

- the deterministic correctness floor stays inspectable
- policy and privacy gates remain visible
- non-core product layers do not replace the source of truth
- optional convenience surfaces can evolve without weakening the public core
- runtime evidence receipts record observed refs, omissions, and bounded
  rollback/output states without claiming runtime ownership or trace truth
