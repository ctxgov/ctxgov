# Memory X-Ray Public Evidence Preview

Status: public-safe local release pack, prepared for owner-approved publication.

This pack shows the shape of a CtxGov / Memory X-Ray public evidence release
without exposing private traces or implying unsupported claims. It is scoped to
agent context health and memory-governance report shape.

## Public Claim

Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context
before agents act.

## Included

- `evidence-summary.json` - machine-readable public-safe release summary.
- `claim-lint.json` - public-safe claim-boundary receipt.
- `leak-scan.json` - public-safe leak-scan receipt.
- `link-check.json` - local link-check receipt with remote fetch pending.
- `publication-readiness.json` - owner-approval and public-publish boundary.
- `owner-approval-minimal-matrix.md` - the minimal human-review gate and
  agent-stop conditions.
- `60-second-demo-script.md` - short demo plan for video or GIF capture.
- `technical-note.md` - architecture, evidence gates, negative cases, and
  limitations.
- `reviewer-packet.md` - focused questions for external reviewers.
- `manifest.json` - asset inventory and publication boundary.

## Evidence Shape

The release pack links four evidence layers:

1. L1 public preview: sanitized report examples and readiness receipts.
2. L2 release-control summary: local gates over release ledger and handoff
   readiness.
3. Repeat-run/no-op replay: checks that local release-control summaries remain
   stable across repeat runs and no-op handoff replay.
4. Negative matrix: fail-closed rejection modes for stale refs, digest drift,
   rollback loss, blocked-lane drift, public claim drift, target drift, and
   attempted side effects.

## Reproduction Commands

```bash
python3 scripts/check_public_evidence_release_pack.py
```

The Memory X-Ray CLI is not published as a public beta in v0.6.9. The L2
release-control commands remain summarized as public-safe evidence only.

## Boundary

No public benchmark claim. No security guarantee. No provider/model
compatibility claim. No adoption claim. No package publication claim. No hosted
runtime claim. No live adapter claim. No public spec-stability claim. No CLI
beta claim.

This pack does not execute provider/model calls, memory-backend writes, external
target writes, package publication, hosted runtime changes, or outreach. The
public GitHub push, release, metadata update, and Pages verification are
owner-approved publication actions for this public-safe scope.
