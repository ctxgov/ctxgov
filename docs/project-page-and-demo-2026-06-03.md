# CtxGov Project Page And Demo Pack

Date: 2026-06-05
Status: public-safe project-page and demo material prepared locally for
owner-approved publication, then published and live-verified on 2026-06-05.
This is not a hosted-runtime release, public benchmark claim, security claim,
provider compatibility claim, package claim, or adoption claim.

## Project Page

Source:

- `docs/index.html`

Public URL:

- `https://ctxgov.github.io/ctxgov/`

Current local public-surface target:

- `v0.6.9` Memory X-Ray public evidence preview
- `release/v0.6.9/RELEASE_NOTES.md`
- `release/v0.6.9/memory-xray-public-evidence-preview/`
- GitHub release: `https://github.com/ctxgov/ctxgov/releases/tag/v0.6.9`
- Final public tag/target is verified by GitHub release state.

First-viewport message:

`CtxGov`

Supporting copy:

`Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context before agents act.`

Primary calls to action:

- Run locally
- Read evidence
- Review limits

## Page Structure

1. Hero: CtxGov as agent context health / memory-governance report shape.
2. Demo: before/after context health report covering README drift, AGENTS
   unsafe write instruction, terminal failure, and memory-claim drift.
3. Run locally: public evidence-pack checker.
4. Evidence: L1 public preview, L2 release-control summary, companion local
   eval v0.7.0.
5. Findings: stale/conflicting context, unsupported claims, unsafe
   instructions.
6. Limits: explicit allowed public claims and explicit not-claimed surface.

## 60-Second Demo Narrative

Screen layout:

- Left: sample AI-facing context from README, AGENTS.md, terminal log, and
  saved memory summary.
- Right: CtxGov / Memory X-Ray report with finding type, evidence span,
  severity, and boundary.

Script:

1. Show the agent's input context.
2. Highlight the unsupported public release claim.
3. Highlight the external-write instruction that requires owner approval.
4. Highlight the hung terminal command as failure evidence.
5. Highlight saved memory that overstates publication state.
6. Show CtxGov findings with evidence spans.
7. End on the claim boundary: 0 public benchmark claims, 0 provider/model
   calls, 0 memory-backend writes, 0 external target writes.

Acceptance:

- viewer understands the project in 10 seconds
- demo shows finding categories, not abstract marketing copy
- evidence and limits are visible in the first scroll path
- page says Evidence / Local Eval, not Benchmark
- limitations are visible before the footer

## Publication Checklist

- [x] Prepare public-safe homepage source in `docs/index.html`.
- [x] Use `https://ctxgov.github.io/ctxgov/` as the public URL target.
- [x] Remove legacy namespace from first-viewport copy.
- [x] Replace Benchmark section with Evidence / Local Eval framing.
- [x] Link to L1 public preview, v0.6.9 evidence pack, and companion local eval
  v0.7.0.
- [x] Apply this patch in a clean public `ctxgov/ctxgov` repo checkout.
- [x] Run claim lint, leak scan, release-pack check, and link check on the
  public checkout.
- [x] Obtain owner approval for public write, GitHub release, and Pages update.
- [x] Push to the public repo.
- [x] Publish GitHub release `v0.6.9`.
- [x] Fetch the live Pages URL and verify updated copy.
- [ ] Capture a GIF from the hero demo panel or replace this pack with an
  approved video/GIF asset.

## Rollback

Rollback is to revert public commit `6acad2339a2e754dab8361a4734f688fada99fb0`,
delete or supersede release `v0.6.9`, and keep `v0.6.8` as the fallback public
surface. This pack does not create provider/model state, memory-backend state,
external target writes, package state, benchmark state, hosted runtime state, or
outreach.
