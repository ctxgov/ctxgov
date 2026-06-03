# GitHub Release Draft: CtxGov v0.6.5

Tag:
`v0.6.5`

Title:
`CtxGov v0.6.5: Release Integrity and Multi-Label Eval Readiness`

Body:

CtxGov v0.6.5 tightens the local public-artifact and evaluation loop for Agent
Context Health work.

Highlights:

- adds `scripts/check_release_integrity.py` for local public-surface link and
  claim-boundary checks
- expands Context Health Doctor detection for release integrity, Memory X-Ray
  L1, Task Shard, stale approval, and hidden terminal failure paraphrases
- narrows unsafe-action detection so neutral release audit text does not become
  an action finding
- supports the companion v0.5 mutation and multi-label scaffold

Observed local v0.5 scaffold run:

- regex baseline: precision 1.0000, recall 0.6205, F1 0.7658
- CtxGov doctor adapter: precision 1.0000, recall 1.0000, F1 1.0000
- cases: 160
- labels: 206
- clean controls: 40

This is a GitHub source release. It does not publish a new package, hosted
runtime, public benchmark result, security guarantee, provider compatibility
claim, or agent-safety claim. The companion v0.5 result is a deterministic
local mutation-scaffold readiness signal, not independently adjudicated
benchmark evidence.

Related:

- Companion eval repo: `https://github.com/ctxgov/agent-context-evals`
- Companion v0.5 release:
  `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.5.0`
- Companion v0.5 results report:
  `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.5-results.md`
- Project page: `https://ctxgov.github.io/ctxgov/`
