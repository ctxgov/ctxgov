# CtxGov v0.12.0

Status: public fresh-clone product receipt release. No public benchmark claim.

## What Shipped

- Fresh-clone product receipt:
  `release/v0.12.0/fresh-clone-product-receipt.json`.
- One-command Memory X-Ray product path:
  `python3 scripts/run_memory_xray_demo.py`.
- Readable Memory X-Ray report UI:
  `docs/memory-xray-demo-report.html`.
- 5-minute local path:
  `docs/try-in-5-minutes.html`.
- CI-safe v0.12 receipt gate:
  `scripts/check_v012_fresh_clone_product_receipt.py`.

## Reproduce

```bash
python3 scripts/check_v012_fresh_clone_product_receipt.py
python3 scripts/run_memory_xray_demo.py
python3 -m unittest tests.test_v012_fresh_clone_product_receipt -v
```

To regenerate the receipt, run the explicit release-operation path. It uses
network access to clone the public repository into a temporary directory:

```bash
python3 scripts/run_v012_fresh_clone_product_receipt.py --ref main
```

The receipt records a fresh clone of the public CtxGov repository, runs the
one-command Memory X-Ray demo, records command output, and records the generated
report SHA-256.

## Boundary

- No public benchmark claim.
- No security claim.
- No provider/model call.
- No adoption claim.
- No human reviewer claim.
- No package publication claim.
- No hosted runtime claim.
- No live adapter claim.
- No stable protocol claim.

This release publishes a product-path receipt and readable report surface only.
It does not execute provider/model calls, memory-backend writes, package
publication, hosted runtime changes, target writes, reviewer outreach, adoption
measurement, or public benchmark reporting.
