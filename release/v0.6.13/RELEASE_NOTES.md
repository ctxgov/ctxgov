# CtxGov v0.6.13 - Auto-Publish Research

CtxGov v0.6.13 records an owner-approved, minimal public release path for
auto-publish research. It narrows the public write surface to the CtxGov repo,
release tag, GitHub release, and Pages verification.

## What Shipped

- `release/v0.6.13/publication-intent.json`
- `scripts/check_publication_intent.py`
- `tests/test_publication_intent.py`
- README, project-page, metadata, and CI updates for the v0.6.13 release path.
- Release-tag-aware live-link verification for v0.6.13 and v0.6.12.

## Owner-Approved Scope

Included public targets:

- `ctxgov_public_repo_patch`
- `ctxgov_release_tag`
- `ctxgov_github_release`
- `ctxgov_pages`

Excluded public targets:

- `agent_context_evals_public_repo_patch`
- `org_profile_update`
- `github_issue_or_comment`
- `linkedin_x_manual_post`

## Evidence

- Owner-visible digest:
  `cfb94da58cdf0dbe439cc393952b084f939e4409823f410ce57b068936ea053b`
- Owner packet v5 digest:
  `d4c0ff8f5a6e64e687c5c4ce865052196ac739e8ba1196d3304c7a8ba31ad584`
- Claim boundary: no public benchmark, security, provider/model,
  adoption, package, hosted runtime, live adapter, stable spec, or CLI beta
  claim.

## Reproduce Locally

Offline checks:

```bash
python3 scripts/check_publication_intent.py
python3 scripts/check_public_surface_hardening.py
python3 -m unittest tests.test_publication_intent tests.test_public_live_links -v
```

Optional network check after release publication:

```bash
python3 scripts/check_public_live_links.py \
  --release-tag v0.6.13-auto-publish-research
```

## Boundary

- No public benchmark claim.
- No security guarantee.
- No provider/model call.
- No adoption claim.
- No package publication claim.
- No hosted runtime or live adapter claim.
- No CLI beta claim.
- No stable public spec claim.

This release does not publish packages, call providers, write memory backends,
update companion repos, post to social platforms, or create issue comments. It
only records and executes the owner-approved public release path for this repo.

## Rollback

Rollback is to revert the v0.6.13 public repo patch, delete the
`v0.6.13-auto-publish-research` tag, delete the GitHub release, and let GitHub
Pages return to the previous main-branch content.
