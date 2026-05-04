# CtxVault Public Release Checklist

This checklist describes the public release expectations for the v0.3.5
first-run UX boundary patch over the v0.3.4 deterministic context extraction
and quality-receipt milestone.

## Release Gates

- Context Injection M1 remains complete and demonstrable as a historical
  source-to-context-to-projection milestone
- the v0.3.3 public review pack passes from public-source fixtures and writes
  inspectable summary, projection, and receipt artifacts
- public schemas, fixtures, CLI, and MCP surfaces are present
- deterministic tests pass in the extracted tree
- experimental contracts are labeled clearly
- the public README leads with safe context handoff, receipts, and the local
  source-of-truth hook
- v0.3.5 wording keeps private Workbench UX outside the public core and does
  not claim runtime control
- policy, privacy, and receipt surfaces remain inspectable
- projected outputs have projection receipts
- projection adapter healthchecks are read-only and clearly experimental
- compiled workstream state remains a read model, not canonical truth
- `doctor` remains read-only
- Markdown-vault import remains a bridge, not canonical storage
- local backup wording is limited to optional local snapshot/replica durability
- agent harness, LLM API gateway, automatic memory, and agent-quality claims
  remain out of scope unless backed by explicit public contracts, fixtures,
  receipts, and owner approval

## Public-Core Checklist

1. Package the v0.3.5 deterministic public core as the public
   `ctxvault` repository.
2. Keep optional product surfaces outside this repository.
3. Ship Apache-2.0 licensing with the public repo.
4. Keep public docs limited to deterministic contracts, the M1 projection path,
   v0.3 compiled-context evidence, and sanitized boundary notes.
5. Label `intelligence.py`, `Episode`, `Workstream`, plugin or projection
   contracts, compiled state, doctor, healthchecks, runtime receipts, and the
   first local executor paths as experimental.

## Optional Product Surfaces

Any optional product surface should remain a distribution or UX layer over the
same deterministic local core instead of a hidden source of truth.
