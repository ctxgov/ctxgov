# Provenance

Date: 2026-06-03

CtxGov was previously developed under the internal and legacy namespace
`ctxvault`.

Public positioning now uses `CtxGov`. Historical paths, schema ids, package
names, CLI commands, fixtures, receipts, release artifacts, and old GitHub URLs
may still contain `ctxvault` when changing them would break provenance or when a
dedicated migration receipt has not yet updated compatibility surfaces.

Current rule for the GitHub public repo:

- Public brand: `CtxGov`
- Recommended public repository: `ctxgov/ctxgov`
- Public package and console command: `ctxgov`
- Public module path: `ctxgov`
- Historical/provenance namespace: `ctxvault`
- Historical generated state may still include `.ctxvault`

The README and public metadata should lead with CtxGov. Legacy names should be
explained here or in migration notes, not in the first public hook.

This file does not create a schema namespace migration, historical fixture
migration, public release, or compatibility claim.
