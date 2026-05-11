# Changelog

## v0.5.0 - 2026-05-11

- Added public release artifacts for governed context projection for AI work.
- Added aggregate-only OSS dry-run evidence and a sanitized example under
  `examples/v0.5.0-governed-context-projection/`.
- Added a release wording gate for local path leaks and overclaim boundaries;
  the gate was run before publication and is not shipped with local dry-run
  identifiers.
- Preserved the no-target-write, no-provider/model-execution, no-runtime,
  no-adapter, no-benchmark, no-hardware/cost, no-security-certification, and
  no-stable-MGP claim boundaries.

## v0.4.1 - 2026-05-08

- Added the experimental, non-normative Projection Governance Kernel design
  preview.
- Added the v0.4.1 object-model schema, example projection and receipt
  fixtures, approval matrix, projection-rights explanation, and focused tests.
- Preserved the no-runtime-control, no-stable-external-API, no-external-adapter,
  no-provider-execution, no-public-beta, and no-hallucination-prevention
  boundaries.

## v0.4.0 - 2026-05-06

- Packaged the local trust-and-handoff path as the v0.4.0 Day 0 release.
- Added the static Receipt/Trust Gallery under
  `release/v0.4.0/receipt-trust-gallery/`.
- Updated public package metadata to v0.4.0.
- Preserved the no-model, no-vector, no-hidden-session-scan,
  no-runtime-control, and no-public-Workbench-beta boundaries.

## v0.3.5 - 2026-05-05

- Recorded the v0.3.5 first-run UX boundary around the private Workbench
  extract/inject patch.
- Updated public package metadata to v0.3.5 while keeping the public core on
  the deterministic CLI/MCP context extraction and receipt path.
- Clarified that Workbench target profiles do not imply runtime takeover,
  session attach, runtime inventory, or an agent session manager.
- Preserved the public no-Workbench, no-model, no-vector, no-live-connector,
  and no-runtime-control boundaries.

## v0.3.4 - 2026-05-04

- Added `context-extract` and MCP `context.extract` for deterministic local
  source extraction, source fingerprinting, idempotency keys, slice rebuild,
  context prepare, and optional gated projection.
- Added `context-extract --dry-run` for planned-import previews without writing
  governed objects.
- Added `receipt-inspect --latest --summary` and MCP `receipt.inspect`
  `summary_text` for human-readable receipt-chain inspection.
- Added deterministic context quality, density, retrieval gain, search trace,
  source conflict, source retention, and prompt patch density checks.
- Added read-only doctor checks for stale extraction source fingerprints,
  missing selection receipts, stale projection selection links, and blocked
  extraction runs.
- Added static source-shape fixtures and v0.3.4 stability/quality scorecards.
- Preserved the deterministic baseline without adding model, vector, remote
  provider, official connector, public Workbench, app-surface, or quality-uplift
  claims.

## v0.3.3 - 2026-05-04

- Added owner-operated public review pack for v0.3.3 package approval using
  reusable public-source scenarios, boundary checks, and a synthetic
  blocked-selection check.
- Added `scripts/run_v033_public_review_pack.py` and deterministic test
  coverage for review summary, ready/empty/over-budget behavior, privacy
  block, projection output, and receipt linkage.
- Updated public README, release notes, changelog, and package metadata to
  position v0.3.3 as safe context handoff hardening.
- Preserved the deterministic baseline without adding model, vector, remote
  provider, official connector, public Workbench, or app-surface claims.

## v0.3.2 - 2026-05-01

- Added deterministic source-grouped context selection composer over existing
  local context slices.
- Added `ctxvault.context-selection-receipt/v1` schema and fixture.
- Added token budget preview and target-aware privacy preflight during
  selection composition.
- Linked projection receipts to the context selection receipt that produced
  the selected slice set.
- Added local pin, hide, archive, and clear preferences for slice suggestions.
- Added CLI and MCP surfaces for context selection compose and slice
  preferences.
- Published v0.3.2 release notes and context-selection public docs without
  adding model, vector, remote provider, official plugin, or live connector
  promises.

## v0.3.1 - 2026-04-30

- Added deterministic local context slices over governed sources.
- Added local context search, selected-slice privacy preflight, and preflight
  receipts.
- Added selected-slice projection receipt metadata and pre-projection blocking
  for withheld or unsafe selections.
- Added review-gated logical purge for derived slice/search/preview/embedding
  and selected projection data, with no physical secure-wipe claim.
- Added doctor diagnostics for slice-index health and projection slice refs.
- Published v0.3.1 schemas, fixtures, release notes, and public safety
  boundary notes.

## v0.3.0 - 2026-04-30

- Added compiled workstream state as an experimental read model.
- Added compiled state projection into `AGENTS.md`, `CLAUDE.md`, and workstream
  briefs with receipts.
- Added read-only doctor diagnostics and Markdown-vault import bridge.

## v0.2.0 - 2026-04-30

- Added projection adapter healthchecks, runtime receipts, and optional local
  snapshot/replica backup writes.

## v0.1.0 - 2026-04-27

- Published the first public M1 source-to-context-to-projection feedback
  preview.
