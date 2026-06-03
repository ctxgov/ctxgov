# CtxGov GitHub Repo Launch Checklist

Date: 2026-06-03
Status: public repo setup checklist. GitHub-side changes still require repo
admin or maintainer permissions.

## Done Condition

The GitHub public surface is launch-ready when:

- repository name and About surface consistently say CtxGov
- README first screen explains Agent Context Health Evaluation
- release URL for `v0.6.3` works
- GitHub Pages or project page URL works
- topics match AI evaluation and context engineering
- issue templates and curated starter issues are ready
- no public copy claims security guarantees, benchmark performance, universal
  compatibility, or autonomous remediation

## Repository Basics

Target public repo:

`ctxgov/ctxgov`

If the current public repo still lives at a legacy namespace, update the About
surface first and use `docs/provenance.md` until repository/package migration is
approved and executed.

## Description, Website, Topics

Use `docs/public-repo-metadata.md` as source of truth.

Description:

`Context-health evaluator for AI agents: stale, conflicting, unsupported, and unsafe AI-facing context.`

Website:

`https://ctxgov.github.io/ctxgov/`

Topics:

- `llm-evaluation`
- `agent-evaluation`
- `context-engineering`
- `ai-agents`
- `llmops`
- `model-behavior`
- `evaluation`
- `developer-tools`
- `python`
- `local-first`

Do not add `security` unless a future release explicitly scopes and verifies a
security-review artifact.

## README Check

The first screen must answer:

- What is CtxGov? Agent Context Health Evaluation for AI Workflows.
- What problem does it solve? Bad AI-facing context causes bad agent behavior.
- What hazards does it inspect? Stale, conflicting, unsupported, unsafe, and
  hidden-failure context.
- What are the claim boundaries? No security, benchmark, compatibility,
  provider-call, target-write, or autonomous-remediation claim.
- Where does legacy naming live? `docs/provenance.md`, not the top-level hook.

## Release Check

Prepare `v0.6.3` as a GitHub source release:

- `release/v0.6.3/RELEASE_NOTES.md`
- `release/v0.6.3/github-release.md`
- `release/v0.6.3/release-readiness-checklist.md`

The release body must say that package and CLI migration are not part of this
release unless a separate migration receipt exists.

## GitHub Pages Check

Use `docs/index.html` as the project page source.

Acceptance:

- hero says `Agent Context Health Evaluation for AI Workflows`
- page links to GitHub, report materials, release notes, and benchmark staging
- limitations are visible without scrolling to the footer only
- page does not claim security, benchmark, compatibility, or live demo status

## Curated Starter Issues

Prepare these issue titles before launch:

- `[eval] Define labeled case schema for Agent Context Health Eval`
- `[eval] Add 50 synthetic context-hazard cases`
- `[eval] Implement finding-type precision/recall scorer`
- `[baseline] Add regex baseline`
- `[docs] Publish failure taxonomy`
- `[demo] Add 60-second demo GIF`
- `[release] Prepare v0.6.3 canonical GitHub release`
- `[outreach] Track reviewer/HM feedback loops`

Issue bodies are staged in `docs/curated-github-issues-2026-06-03.md`.

## Manual GitHub Verification

After publication, manually verify:

- `https://github.com/ctxgov/ctxgov` loads
- About description matches this checklist
- website link is not 404
- topics are visible
- release URL for `v0.6.3` loads
- README first screen does not show the legacy namespace
- issue templates load
- curated issues are visible and scoped

## Rollback

If public copy overclaims or the release URL is broken, delete or supersede the
release draft, remove the website link, revert README/About copy to the last
verified state, and publish a correction note. No package, provider, backend,
target repo, or memory state is created by this checklist.
