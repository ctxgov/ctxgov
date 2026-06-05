# CtxGov v0.6.11 - Public Surface Hardening And Self-Audit

Status: owner-approved public-safe hardening release.

This release tightens CtxGov's public surface after v0.6.10 by fixing remaining
post-publication context drift, adding public-surface CI, publishing a
self-audit case study, and adding a deterministic report preview renderer.

## What Shipped

- README, ROADMAP, v0.6.9 evidence-pack status, and `pyproject.toml` public
  state were aligned to the current public release surface.
- Public-surface CI now checks release-pack shape, claim boundary, public-safe
  leakage checks, and deterministic preview rendering.
- A self-audit case study records public-safe post-publication context drift:
  publication state, repo map, package metadata, and roadmap pointer drift.
- A deterministic public Memory X-Ray preview renderer writes Markdown and JSON
  from the L1 public examples pack.
- The project page now includes a reviewer-mode entrypoint.

## Why It Matters

CtxGov's own public repo provided a useful self-audit target. Stale release
state, old namespace paths, and old version pointers are exactly the kind of
AI-facing context drift that can shape future agent runs incorrectly.

The hardening release turns that drift into evidence without widening claims.

## Reproduce Locally

```bash
python3 scripts/check_public_surface_hardening.py
python3 scripts/render_public_memory_xray_preview.py \
  --input release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json \
  --output /tmp/ctxgov-memory-xray-preview.md
```

## Explicitly Not Claimed

- No public benchmark claim.
- No security guarantee.
- No provider/model compatibility claim.
- No adoption or downstream production-use claim.
- No package publication claim.
- No hosted runtime claim.
- No live adapter claim.
- No public spec-stability claim.
- No stable ASCR standard claim.
- No Memory X-Ray CLI beta claim.

## Rollback

Rollback is to revert the v0.6.11 README/ROADMAP/pyproject/Page patch, remove
`release/v0.6.11/`, remove the public-surface workflow, and keep v0.6.10 as the
current ASCR-aligned public evidence surface.
