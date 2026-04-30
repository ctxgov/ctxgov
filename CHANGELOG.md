# Changelog

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
- Published v0.3.2 release notes and injection composer public docs without
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

- Published the first public Context Injection M1 feedback preview.
