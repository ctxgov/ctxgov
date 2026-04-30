# CtxVault v0.3.2 Injection Composer Plan

Status: private engineering lane.

## No-Approval Execution Scope

These tasks preserve the deterministic local baseline and can be executed
without another release-owner decision:

- source-grouped Context Picker search over existing context slices
- explicit multi-slice selection
- token budget preview
- target-aware privacy preflight
- `ctxvault.context-selection-receipt/v1`
- projection receipts linked to context selection receipts
- local pin, hide, and archive preferences as read-model controls
- CLI, MCP, Surface API, and private workbench service endpoints
- deterministic tests, fixtures, and open-core extraction hygiene

## Approval-Required Scope

These remain blocked until explicitly approved:

- public v0.3.2 GitHub release
- model, embedding, vector, or remote reranking baseline
- remote provider use or external-send behavior
- official Obsidian plugin or live connector claims
- automatic source-material clearing
- physical secure-wipe claims
- graph product claims or canonical graph truth
- new public projection targets

## Recommendation

Ship v0.3.2 first as a private deterministic composer. Do not publish a public
v0.3.2 release until the picker flow has been exercised against real project
workstreams and the owner separately authorizes the public claim set.
