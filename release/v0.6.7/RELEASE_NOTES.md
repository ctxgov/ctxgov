# CtxGov v0.6.7 Release Notes

Date: 2026-06-03
Status: public GitHub source release.

## Summary

CtxGov v0.6.7 keeps the public release tag aligned with the current main repo
public surface after the companion eval v0.6.0 wording guard.

This release supersedes v0.6.6 as the current main repo release. It does not
replace v0.6.6 history. The reason for the new tag is narrow: v0.6.6 aligned
the main repo with companion eval v0.6.0, then a completion audit found one
README line still describing the companion repo as a v0.5 packet. v0.6.7
includes the corrected wording and the local release-integrity guard that
prevents that drift from returning.

## Changes

- Updates README current-artifact wording from a v0.5 companion packet to the
  current v0.6 local eval packet.
- Adds a release-integrity check for stale current-companion v0.5 wording in
  public-surface files.
- Updates README, GitHub Pages source, positioning, LinkedIn/outreach, hiring
  packet, and project-page material to treat CtxGov v0.6.7 as the current main
  repo release.
- Keeps the companion eval artifact pinned to:
  - release: `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.6.0`
  - report: `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.6-results.md`

## Local Verification

- `python3 -m unittest tests/test_release_integrity_checker.py`
- `python3 scripts/check_release_integrity.py --root .`
- `python3 -m unittest discover -s tests`
- `git diff --check`

## Claim Boundary

This release does not publish a new package, hosted runtime, public benchmark
result, security guarantee, provider compatibility claim, agent-safety claim,
or adoption claim.

## Rollback

If v0.6.7 public links or release metadata are wrong, publish a superseding
release rather than moving the v0.6.7 tag silently. Keep v0.6.6 available as
the previous companion-alignment release.
