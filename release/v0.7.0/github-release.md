# CtxGov v0.7.0 - Public-Only Session Continuity Package

This release publishes a clean public-only CtxGov package focused on Session
Continuity Sidecar, with Memory X-Ray L1 report-shape examples as supporting
evidence.

## Included

- Minimal public CLI: `continuity compile`, `continuity render`, `continuity apply --mode dry-run|sandbox`, and `memory-xray validate`.
- Synthetic public-safe session-continuity fixture.
- Memory X-Ray L1 public-safe example pack.
- Local public package smoke checks.

## Not Included

- Non-public development artifacts and local session exports.
- App bundles, publication automation, real target writes, external state mutation flows, provider/model calls, schedulers, watch daemons, or long-running services.
- Public benchmark, adoption, security, provider compatibility, hosted runtime, PyPI, or stable protocol claims.

## Local Check

```bash
python3 scripts/run_public_package_checks.py
```

## Claim Boundary

This release is a local-first research and developer tooling preview. It shows
deterministic report and continuity shapes, not production adoption, security
certification, provider compatibility, or autonomous remediation.
