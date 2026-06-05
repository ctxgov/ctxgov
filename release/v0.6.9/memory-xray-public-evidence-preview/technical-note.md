# Technical Note

CtxGov / Memory X-Ray treats agent-facing context as a release-control surface:
README text, AGENTS instructions, saved memory summaries, terminal transcripts,
tool receipts, release notes, and public pages can all shape what an agent does
next.

## Architecture

The public release shape has four layers:

1. Context inputs: local files and sanitized examples that describe what an
   agent would see before acting.
2. Findings: typed issues such as stale claims, conflicting instructions,
   unsupported claims, unsafe operational instructions, memory-risk drift, and
   terminal failure evidence.
3. Evidence spans: each finding points to the context span or receipt that made
   it actionable.
4. Release gates: public copy, evidence packs, and release-control receipts are
   checked for claim boundaries and side-effect boundaries.

## Evidence Gates

The release deliberately separates report-shape evidence from stronger claims.
L1 shows sanitized examples and output shape. L2 adds local release-control
readiness: final ledger summaries, no-op handoff replay, repeat-run stability,
rollback references, blocked lanes, and fail-closed negative cases.

The pack is allowed to say the report shape exists and local release-control
checks passed. It is not allowed to say public benchmark performance, provider
compatibility, security certification, adoption, live adapter availability,
package publication, or public protocol stability.

## Negative Cases

The public-safe negative matrix summarizes ten rejection modes:

- attempted provider/model, memory-backend, or external side effect
- attempted reviewer outreach
- attempted URL, package, or target write side effect
- blocked-lane drift
- ledger digest drift
- public claim drift
- rollback ref loss
- stale no-op handoff replay
- stale release-control history
- target drift

The value is not that these cases prove universal correctness. The value is
that release copy cannot silently drift beyond evidence without a local gate
rejecting it.

## Limits

This release is not a security product release, public benchmark release,
provider compatibility release, package release, hosted runtime release, or
adoption release. It does not include private traces, fixture internals, hidden
holdout custody, independent FP/FN review, permissioned case studies, or live
provider/model execution.

The next higher-confidence release should add independent reviewer notes,
permissioned case-study material, more non-picked real saved traces, downstream
design-change evidence, CLI beta contract if the CLI is in scope, and hidden
holdout custody before making broader claims.
