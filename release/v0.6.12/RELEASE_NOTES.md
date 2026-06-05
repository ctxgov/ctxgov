# CtxGov v0.6.12 - Live Link Verifier

CtxGov v0.6.12 adds an optional network-enabled public live-link verifier.

## What Shipped

- `scripts/check_public_live_links.py`
- `tests/test_public_live_links.py`
- README and project-page updates for the v0.6.12 release-integrity path.

## Reproduce Locally

Offline checks:

```bash
python3 scripts/check_public_surface_hardening.py
python3 -m unittest tests.test_public_live_links -v
```

Optional network check after release publication:

```bash
python3 scripts/check_public_live_links.py \
  --release-tag v0.6.12 \
  --json-output release/v0.6.12/live-link-verification.json
```

## Boundary

- No public benchmark claim.
- No security guarantee.
- No provider/model call.
- No adoption claim.
- No package publication claim.
- No hosted runtime or live adapter claim.
- No CLI beta claim.

The verifier fetches public URLs only when run explicitly. It does not call a
provider, write a memory backend, publish a package, mutate an external target,
or perform outreach.
