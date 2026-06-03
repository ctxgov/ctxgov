# CtxGov Project Page And Demo Pack

Date: 2026-06-03
Status: GitHub Pages source and companion demo material. Not a hosted runtime,
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
5. Benchmark: separate `ctxgov/agent-context-evals` v0.4 doctor-coverage artifact,
   no public benchmark claim.
6. Links: GitHub, v0.6.4 release, v0.4 results report, technical report,
   demo GIF, hiring packet.
7. Limitations: no security guarantee, no benchmark claim, no compatibility
   claim, no live adapter, no target writes.

## 60-Second Demo Narrative

Screen layout:

- Left: sample AI-facing context from README, release notes, AGENTS.md,
  terminal log, and memory summary.
- Right: context-health report with finding type, evidence span, and claim
  boundary.

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

- [x] Enable GitHub Pages from `main` and `/docs`.
- [x] Open the page in a browser.
- [x] Verify no legacy namespace appears in first viewport.
- [x] Verify GitHub, release, report, benchmark, and demo GIF links resolve.
- [x] Publish companion demo GIF:
  `https://raw.githubusercontent.com/ctxgov/agent-context-evals/main/demo/60-second-demo.gif`
- [x] Run a copy pass for unsupported security/benchmark/compatibility claims.

## Rollback

Disable GitHub Pages or revert `docs/index.html`. No provider/model, target
repo, package, benchmark, or hosted runtime state is created by this page.
