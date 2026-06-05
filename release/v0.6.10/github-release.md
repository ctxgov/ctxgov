# CtxGov v0.6.10 - ASCR-Aligned Evidence Update

CtxGov now has a clean public relationship to ASCR: Agent State & Context
Runtime Contract.

The release is intentionally scoped. CtxGov is the agent context health and
memory-governance report-shape surface. ASCR is the separate
framework-neutral contract/toolkit repo.

ASCR: https://github.com/ctxgov/ascr

## What shipped

- Public ASCR sibling repo link and relationship copy.
- v0.6.10 ASCR-aligned evidence pack.
- README and project page updates.
- Local checker: `python3 scripts/check_ascr_aligned_release_pack.py`.

## Evidence

- ASCR repo: `https://github.com/ctxgov/ascr`
- v0.6.10 evidence pack:
  `release/v0.6.10/ascr-aligned-evidence-update/`
- v0.6.9 Memory X-Ray evidence:
  `release/v0.6.9/memory-xray-public-evidence-preview/`

## Reproduce

```bash
python3 scripts/check_ascr_aligned_release_pack.py
```

## Not claimed

No public benchmark claim. No security guarantee. No provider/model
compatibility claim. No adoption claim. No package publication claim. No hosted
runtime claim. No live adapter claim. No public spec-stability claim. No stable
ASCR standard claim. No CtxGov CLI beta claim.

No provider/model call, memory-backend write, external target write, package
publication, hosted runtime change, or outreach is part of this release.

## Rollback

Revert the v0.6.10 README/homepage patch and remove `release/v0.6.10/`. Keep
v0.6.9 as the public evidence surface.
