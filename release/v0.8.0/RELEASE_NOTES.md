# CtxGov v0.8.0 - Read-Only Governance Evaluation Pack

Public product/package version for this release: `0.8.0`.

CtxGov v0.8.0 expands the public package from session-continuity report shapes
to a read-only governance evaluation pack for local projects and saved public
OSS evidence.

## Included

- Change Gate surface inspection for explicit local repositories.
- Federation over explicit local repository paths or an explicit base path.
- OSS Case Study Preview over an explicit saved local public-source excerpt.
- OSS Efficiency raw telemetry methodology receipts using saved local telemetry.
- Forensics read-only preview over explicit local fixtures.
- The v0.7.0 Session Continuity and Memory X-Ray L1 public paths remain in the
  package.

## Boundary

- No network call, API call, provider/model call, scheduler, daemon, public
  write, target repository write, package-registry publish, issue/PR creation,
  outreach, runtime execution, or adapter execution is performed.
- The only local file-write exception is the inherited v0.7.0
  `ctxgov continuity apply --mode sandbox` path, which writes only to a sandbox
  file and is not a target repository write.
- OSS Efficiency artifacts publish raw saved-run measurements and methodology
  receipts only. They are not a speedup claim, productivity claim, adoption
  claim, public benchmark claim, provider compatibility claim, production
  readiness claim, or stable protocol claim.
- No derived delta or aggregate comparison conclusion is published.
- No adoption claim is made.
- OSS Case Study Preview is source-descriptive only. It does not claim maintainer
  endorsement, compatibility, security validation, runtime validation, or target
  project quality.
- Forensics is a read-only preview over existing local fixtures. If no fixture is
  provided, it does not create a receipt store.

## Local Check

```bash
python3 scripts/run_public_package_checks.py
```

The check runs only local fixture reads and command smoke tests.
