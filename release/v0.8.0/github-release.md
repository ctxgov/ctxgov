# CtxGov v0.8.0 - Read-Only Governance Evaluation Pack

This release publishes a public-only CtxGov package for read-only governance
evaluation over explicit local files, local repositories, and saved public-safe
evidence.

## Included

- `ctxgov change-gate-check`
- `ctxgov change-gate-federate`
- `ctxgov oss-case-study-preview`
- `ctxgov oss-efficiency evaluate|validate`
- `ctxgov forensics-timeline`
- `ctxgov forensics-trace`
- `ctxgov forensics-gaps`
- Existing v0.7.0 public Session Continuity and Memory X-Ray L1 paths

## Not Included

- Network/API calls, provider/model calls, schedulers, daemons, runtime adapters,
  target repository writes, public writes, package-registry publishing,
  issue/PR creation, outreach, or publication automation.
- The inherited `ctxgov continuity apply --mode sandbox` local sandbox write is
  the only file-write exception and is not a target repository write.
- Speedup, productivity, adoption, public benchmark, provider compatibility,
  production readiness, security certification, hosted runtime, PyPI, stable
  protocol, or autonomous remediation claims.

## Local Check

```bash
python3 scripts/run_public_package_checks.py
```

## Claim Boundary

OSS Efficiency numbers in this release are raw saved-run measurements and
methodology receipt data only. They describe specific local observations and do
not generalize to other projects, users, models, providers, or workflows. No
derived delta or aggregate comparison conclusion is published.
