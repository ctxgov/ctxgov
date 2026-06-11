# CtxGov v0.6.13 Post-Publication Summary

Status: published and verified.

Owner-approved minimal public targets executed:

- `ctxgov_public_repo_patch`
- `ctxgov_release_tag`
- `ctxgov_github_release`
- `ctxgov_pages`

Executed evidence:

- Commit: `88f0ed28ce4ad26091c37ef6e77bde388871413b`
- Release: <https://github.com/ctxgov/ctxgov/releases/tag/v0.6.13-auto-publish-research>
- Pages: <https://ctxgov.github.io/ctxgov/>
- Live verification asset:
  <https://github.com/ctxgov/ctxgov/releases/download/v0.6.13-auto-publish-research/ctxgov-v0613-live-link-verification.json>
- Live verification asset SHA-256:
  `64e2b8462cbb0c25e89d2f85ec32a665173e9fdda39b5f152d9289d7c59e51f7`
- Public Surface Checks:
  <https://github.com/ctxgov/ctxgov/actions/runs/27111657410>
- Pages deployment:
  <https://github.com/ctxgov/ctxgov/actions/runs/27111657101>

Not executed:

- `agent_context_evals_public_repo_patch`
- `org_profile_update`
- `github_issue_or_comment`
- `linkedin_x_manual_post`
- provider/model call
- memory/backend write
- package publication
- hosted runtime change
- live adapter enablement
- outreach

Claim boundary remains public-safe report-shape, release-integrity, and
auto-publish research only. This is not a benchmark, security, provider,
adoption, package, hosted-runtime, live-adapter, stable-spec, or CLI-beta
release.

Rollback path:

1. Revert commit `88f0ed28ce4ad26091c37ef6e77bde388871413b` on public main.
2. Delete tag `v0.6.13-auto-publish-research`.
3. Delete GitHub release `v0.6.13-auto-publish-research` and its live-link
   asset.
4. Let Pages return to the previous main-branch content
   `f8c9f648381390dfe93389e0f3e9493a9cd4f2b0`.
