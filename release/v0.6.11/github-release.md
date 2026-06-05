# CtxGov v0.6.11 - Public Surface Hardening And Self-Audit

CtxGov v0.6.11 tightens the public surface after v0.6.10.

## What shipped

- Public-surface consistency fixes for README, ROADMAP, v0.6.9 evidence pack
  status, and `pyproject.toml`.
- Public-surface CI for release-pack, claim-boundary, leakage, and preview
  rendering checks.
- A public-safe self-audit case study for post-publication context drift.
- A deterministic Memory X-Ray public-example preview renderer.
- Reviewer-mode project-page guidance.

## Reproduce

```bash
python3 scripts/check_public_surface_hardening.py
python3 scripts/render_public_memory_xray_preview.py \
  --input release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json \
  --output /tmp/ctxgov-memory-xray-preview.md
```

## Not claimed

No public benchmark claim. No security guarantee. No provider/model
compatibility claim. No adoption claim. No package publication claim. No hosted
runtime claim. No live adapter claim. No public spec-stability claim. No stable
ASCR standard claim. No Memory X-Ray CLI beta claim.

No provider/model call, memory-backend write, external target write, package
publication, hosted runtime change, or outreach is part of this release.
