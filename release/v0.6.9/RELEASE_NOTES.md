# CtxGov v0.6.9 - Memory X-Ray Public Evidence Release Preview

Status: prepared locally for owner-approved publication.

This release is a public-safe report-shape and readiness release for CtxGov /
Memory X-Ray. It is designed to show the product surface, evidence discipline,
and release-control boundary without publishing private traces, benchmark claims,
provider compatibility claims, adoption claims, or security-product claims.

## What Shipped

- A refreshed public project homepage focused on agent context health:
  stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context.
- A README rewritten as a public portal: problem, one-command local run,
  sample output shape, evidence links, and explicit claim boundaries.
- A Memory X-Ray public evidence pack with L1 report-shape preview, L2
  release-control summary, repeat-run/no-op replay summary, negative-matrix
  rejection modes, claim lint, leak scan, and reproduction guidance.
- A 60-second demo script suitable for a short video or GIF.
- A reviewer packet with focused external-review questions.
- A concise technical note covering architecture, evidence gates, negative
  cases, and limits.

## Why It Matters

AI agents increasingly act from a mixed pile of README text, AGENTS files,
terminal output, saved memory summaries, release notes, and tool receipts. The
failure mode is not just "bad prompt text"; it is stale context, contradictory
context, unsupported release claims, unsafe operational instructions, and
memory-shaped drift that looks authoritative in the next run.

CtxGov positions this release around a narrower claim: it can produce an
agent-context health report with evidence spans, finding types, and explicit
release boundaries before an agent acts.

## Evidence Supporting This Release

- L1 public preview: sanitized report-shape examples and local readiness
  receipts are available under
  `release/v0.7.0/memory-xray-l1-public-preview/`.
- L2 release-control summary: local release-control gates cover final ledger
  state, no-op handoff indexing, repeat-run history, handoff replay, and
  fail-closed negatives.
- Negative-matrix coverage: public-safe summaries include stale release-control
  refs, ledger digest drift, rollback ref loss, blocked-lane drift, public claim
  drift, target drift, and attempted side effects.
- Companion eval: the public companion repo remains scoped as a local eval
  artifact, not a public benchmark claim.

## Reproduce Locally

From the repository root:

```bash
python3 scripts/check_public_evidence_release_pack.py
```

The public v0.6.9 surface is a release-pack and report-shape preview. The
private L2 commands used to generate the summarized evidence are not published
as a public CLI beta in this release.

## Explicitly Not Claimed

- No public benchmark claim.
- No security certification or guarantee.
- No provider/model compatibility claim.
- No package publication claim.
- No hosted runtime claim.
- No adoption or downstream production-use claim.
- No live adapter claim.
- No public spec-stability claim.
- No CLI beta claim.
- No provider/model call, memory-backend write, external target write, package
  publication, hosted runtime change, or outreach is part of this release.
- The public GitHub push, release, metadata update, and Pages verification are
  owner-approved publication actions for this public-safe scope.

## Formal Release Gaps

A stronger formal public release remains blocked until the project has
owner-approved evidence for independent reviewer FP/FN notes, more non-picked
real saved traces, downstream design-change signal, permissioned case study,
CLI beta contract if CLI enters scope, hidden holdout custody, and public-safe
rollback/claim-lint receipts tied to the final public artifact.

## Rollback And Provenance

This release pack is file-local. Rollback is to remove `release/v0.6.9/`, revert
the public homepage/README changes, and keep `v0.6.8` as the public release
surface. Publication requires a clean public `ctxgov/ctxgov` repo patch and
owner approval before push, release, or Pages update.
