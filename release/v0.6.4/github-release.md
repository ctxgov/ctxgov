# GitHub Release Draft: CtxGov v0.6.4

Tag:
`v0.6.4`

Title:
`CtxGov v0.6.4: Native Context Health Doctor Coverage`

Body:

CtxGov v0.6.4 adds native Context Health Doctor coverage for the companion
Agent Context Health Eval v0.4 artifact.

Highlights:

- release integrity findings: `release_link_404`,
  `package_registry_unverified`, `release_artifact_missing`
- Memory X-Ray L1 findings: source coverage, rollback, consequence ceiling,
  and model-state surface
- Task Shard findings: schema conflict, unapproved side effect, missing
  rollback
- exact evidence spans in doctor findings and evidence manifests
- companion v0.4 doctor adapter run: precision/recall/F1/evidence token-F1 of
  1.0000 on the public trace-pattern scaffold

This is a GitHub source release. It does not publish a new package, hosted
runtime, benchmark claim, security guarantee, provider compatibility claim, or
agent-safety claim. The companion v0.4 result is a scaffold readiness signal on
public trace-pattern and synthetic hard-negative data; independent reviewer
labels and adjudication remain pending.

Related:

- Companion eval repo: `https://github.com/ctxgov/agent-context-evals`
- Companion v0.4 report:
  `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.4-results.md`
