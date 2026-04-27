# CtxVault Public Release Checklist

This checklist describes the first public release expectations for `ctxvault`.

## Release Gates

- Context Injection M1 is complete and demonstrable
- public schemas, fixtures, CLI, and MCP surfaces are present
- deterministic tests pass in the extracted tree
- experimental contracts are labeled clearly
- the public README leads with the local source-of-truth hook and M1
  source-to-context-to-projection loop
- policy, privacy, and receipt surfaces remain inspectable
- injected outputs have projection receipts

## Public-Core Checklist

1. Package the Context Injection M1 public core as the public `ctxvault`
   repository.
2. Keep first-party wrapper and workbench sources outside this repository.
3. Ship Apache-2.0 licensing with the public repo.
4. Keep public docs limited to deterministic contracts, the M1 injection path,
   and sanitized boundary notes.
5. Label `intelligence.py`, `Episode`, `Workstream`, plugin or projection
   contracts, and the first local executor paths as experimental.

## Wrapper Relationship

If a signed thin native wrapper ships alongside this repo, it must pass the
private notarization launch gate and should remain a distribution and UX layer
over the same deterministic local core instead of a hidden source of truth.
