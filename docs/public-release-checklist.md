# CtxVault Public Release Checklist

This checklist describes the public release expectations for the v0.2/M2
developer-framework milestone.

## Release Gates

- Context Injection M1 remains complete and demonstrable
- public schemas, fixtures, CLI, and MCP surfaces are present
- deterministic tests pass in the extracted tree
- experimental contracts are labeled clearly
- the public README leads with the local source-of-truth hook, the M1
  source-to-context-to-projection loop, and the v0.2 developer-framework
  direction
- policy, privacy, and receipt surfaces remain inspectable
- injected outputs have projection receipts
- projection adapter healthchecks are read-only and clearly experimental
- local backup wording is limited to optional local snapshot/replica durability

## Public-Core Checklist

1. Package the v0.2 developer-framework public core as the public `ctxvault`
   repository.
2. Keep first-party wrapper and workbench sources outside this repository.
3. Ship Apache-2.0 licensing with the public repo.
4. Keep public docs limited to deterministic contracts, the M1 injection path,
   experimental v0.2 developer-framework evidence, and sanitized boundary notes.
5. Label `intelligence.py`, `Episode`, `Workstream`, plugin or projection
   contracts, healthchecks, runtime receipts, and the first local executor
   paths as experimental.

## Wrapper Relationship

If a signed thin native wrapper ships alongside this repo, it must pass the
private notarization launch gate and should remain a distribution and UX layer
over the same deterministic local core instead of a hidden source of truth.
