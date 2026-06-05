# CtxGov GitHub Repo Launch Checklist

Date: 2026-06-05
Status: public repo setup checklist. GitHub-side changes still require repo
admin or maintainer permissions.

## Done Condition

The GitHub public surface is launch-ready when:

- repository name and About surface consistently say CtxGov
- README first screen explains agent context health / memory governance
- release URL for `v0.6.9` works after owner-approved publication
- GitHub Pages or project page URL works
- topics match AI evaluation and context engineering
- LICENSE choice is confirmed by the owner
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

`Agent context health for stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context.`

Website:

`https://ctxgov.github.io/ctxgov/`

Topics:

- `llm-evaluation`
- `agent-evaluation`
- `context-engineering`
- `ai-agents`
- `llmops`
- `model-behavior`
- `local-eval`
- `developer-tools`
- `python`
- `local-first`

Do not add `security` unless a future release explicitly scopes and verifies a
security-review artifact.

## README Check

The first screen must answer:

- What is CtxGov? Agent context health / memory governance before agents act.
- What problem does it solve? Bad AI-facing context causes bad agent behavior.
- What hazards does it inspect? Stale, conflicting, unsupported, unsafe,
  memory-risky, and hidden-failure context.
- What are the claim boundaries? No security, benchmark, compatibility,
  provider-call, memory-backend-write, target-write, package, hosted-runtime,
  adoption, or autonomous-remediation claim.
- Where does legacy naming live? `docs/provenance.md`, not the top-level hook.

## Release Check

Prepare `v0.6.9` as a GitHub source release only after owner approval:

- `release/v0.6.9/RELEASE_NOTES.md`
- `release/v0.6.9/github-release.md`
- `release/v0.6.9/memory-xray-public-evidence-preview/`

Use
`release/v0.6.9/memory-xray-public-evidence-preview/owner-approval-minimal-matrix.md`
to keep review to a single bundled human gate: scope, claim boundary, license,
public write bundle, and outreach posture.

The release body must include these boundaries unless a separate owner-approved
receipt exists:

- No package publication claim.
- No hosted runtime claim.
- No provider/model compatibility claim.
- No public benchmark claim.
- No security guarantee.
- No adoption claim.
- No public spec-stability claim.
- No CLI beta migration claim.

## GitHub Pages Check

Use `docs/index.html` as the project page source.

Acceptance:

- hero says `CtxGov`
- first viewport says `Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context before agents act.`
- page links to GitHub, L1 preview, v0.6.9 evidence pack, release notes, and
  companion local eval v0.7.0
- page uses Evidence / Local Eval framing instead of Benchmark framing
- limitations are visible without scrolling to the footer only
- page does not claim security, benchmark, compatibility, package, hosted
  runtime, adoption, or live demo status

## Curated Starter Issues

Prepare these issue titles before launch:

- `[eval] Define labeled case schema for Agent Context Health Eval`
- `[eval] Add 50 synthetic context-hazard cases`
- `[eval] Implement finding-type precision/recall scorer`
- `[baseline] Add regex baseline`
- `[docs] Publish failure taxonomy`
- `[demo] Add 60-second demo GIF`
- `[release] Prepare v0.6.9 public evidence release`
- `[outreach] Track reviewer/HM feedback loops`

Issue bodies are staged in `docs/curated-github-issues-2026-06-03.md`.

## Manual GitHub Verification

After publication, manually verify:

- `https://github.com/ctxgov/ctxgov` loads
- About description matches this checklist
- website link is not 404
- topics are visible
- release URL for `v0.6.9` loads after publication
- live Pages fetch shows the updated `CtxGov` first viewport
- README first screen does not show the legacy namespace
- issue templates load
- curated issues are visible and scoped
- `python3 scripts/check_public_evidence_release_pack.py` passes in the public
  checkout

## Rollback

If public copy overclaims or the release URL is broken, delete or supersede the
release draft, remove the website link, revert README/About copy to the last
verified state, and publish a correction note. No package, provider, backend,
target repo, or memory state is created by this checklist.
