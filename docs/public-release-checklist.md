# CtxVault Public Release Checklist

This checklist describes the public-core release expectations for `ctxvault`.

## Release Gates

- public schemas, fixtures, CLI, and MCP surfaces are present
- deterministic tests pass in the extracted tree
- experimental contracts are labeled clearly
- the public README matches the actual public scope
- policy, privacy, and receipt surfaces remain inspectable

## Public-Core Checklist

1. Package the deterministic core as the public `ctxvault` repository.
2. Keep first-party wrapper and workbench sources outside this repository.
3. Ship Apache-2.0 licensing with the public repo.
4. Keep public docs limited to deterministic contracts and sanitized boundary
   notes.
5. Label `intelligence.py`, `Episode`, `Workstream`, plugin or projection
   contracts, and the first local executor path as experimental.

## Wrapper Relationship

If a signed thin native wrapper ships alongside this repo, it should remain a
distribution and UX layer over the same deterministic local core instead of a
hidden source of truth.
