# CtxGov Project Page And Demo Pack

Date: 2026-06-03
Status: local project-page and demo material. Not a published site, hosted demo,
benchmark claim, security claim, or adoption claim.

## Project Page

Source:

- `docs/index.html`

Recommended URL after GitHub Pages setup:

- `https://ctxgov.github.io/ctxgov/`

First-viewport message:

`Agent Context Health Evaluation for AI Workflows`

Supporting copy:

`Agents fail on bad context. CtxGov checks AI-facing repo and workflow context for stale claims, conflicting instructions, unsupported releases, unsafe action guidance, and hidden terminal failures before execution.`

## Page Structure

1. Hero: Agent Context Health Evaluation for AI Workflows.
2. Problem: agents consume stale or conflicting repo/workflow context.
3. Demo: before/after context-health report.
4. Taxonomy: stale, conflicting, unsupported, unsafe, hidden terminal failure.
5. Benchmark: separate `ctxgov/agent-context-evals` v0.2 scaffold, no public benchmark claim.
6. Links: GitHub, release draft, benchmark report, technical report, hiring
   packet.
7. Limitations: no security guarantee, no benchmark claim, no compatibility
   claim, no live adapter, no target writes.

## 60-Second Demo Narrative

Screen layout:

- Left: sample AI-facing context from README, release notes, AGENTS.md, and
  terminal log.
- Right: CtxGov report with finding type, evidence span, severity, and next
  action.

Script:

1. Show the agent's input context.
2. Highlight the stale release claim.
3. Highlight the conflicting deploy instruction.
4. Highlight the failed terminal test.
5. Show CtxGov findings with evidence spans.
6. End on the claim boundary: review before execution, no auto-remediation
   claim.

Acceptance:

- viewer understands the project in 10 seconds
- demo shows actual finding categories, not abstract marketing copy
- release/report/benchmark links are visible
- limitations are visible before the footer

## Publication Checklist

- [ ] Enable GitHub Pages from `main` and `/docs`.
- [ ] Open the page in a browser.
- [ ] Verify no legacy namespace appears in first viewport.
- [ ] Verify GitHub, release, report, and benchmark links resolve.
- [ ] Capture a GIF from the hero demo panel or replace this pack with a live
  demo link.
- [ ] Run a copy pass for unsupported security/benchmark/compatibility claims.

## Rollback

Disable GitHub Pages or revert `docs/index.html`. No provider/model, target
repo, package, benchmark, or hosted runtime state is created by this page.
