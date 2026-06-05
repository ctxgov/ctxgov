# CtxGov v0.6.9 - Memory X-Ray Public Evidence Release Preview

CtxGov now presents Memory X-Ray as an agent context health and
memory-governance report-shape release.

The public claim is intentionally narrow: find stale, conflicting, unsupported,
unsafe, and memory-risky AI-facing context before agents act. This is not a
benchmark release, security product release, provider compatibility release, or
adoption claim.

## What shipped

- Refreshed public homepage and README.
- Public-safe Memory X-Ray evidence pack.
- L1 report-shape preview links.
- L2 release-control summary, repeat-run/no-op replay summary, and negative
  rejection modes.
- Claim-lint and leak-scan receipts.
- 60-second demo script, technical note, and reviewer packet.

## Evidence

- L1 public preview: `release/v0.7.0/memory-xray-l1-public-preview/`
- v0.6.9 evidence pack:
  `release/v0.6.9/memory-xray-public-evidence-preview/`
- Companion local eval release:
  `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.7.0`

## Reproduce

```bash
python3 scripts/check_public_evidence_release_pack.py
```

The Memory X-Ray CLI is not part of the public v0.6.9 scope.

## Not claimed

No public benchmark claim. No security guarantee. No provider/model
compatibility claim. No package publication claim. No hosted runtime claim. No
adoption claim. No live adapter claim. No public spec-stability claim. No CLI
beta claim.

No provider/model call, memory-backend write, external target write, package
publication, hosted runtime change, or outreach is part of this release.

The public GitHub push, release, metadata update, and Pages verification are
owner-approved publication actions for this public-safe scope.

## Rollback

Revert the homepage/README patch and remove `release/v0.6.9/`. Keep `v0.6.8`
as the public release surface until owner-approved publication completes.
