# CtxGov v0.9.0 - Real-Source Governance Evaluation Candidate

Public product/package version for this release candidate: `0.9.0`.

CtxGov v0.9.0 unifies the v0.7.0 Session Continuity path, the v0.8.0
read-only governance evaluation pack, and the v0.9.0 real-source governance
evaluation harness into one public package candidate.

## Included

- Existing v0.7.0 Session Continuity and Memory X-Ray L1 public paths.
- Existing v0.8.0 Change Gate, Federation, OSS Case Study Preview, raw telemetry
  methodology receipts, and fixture-based Forensics preview.
- Read-only semantic Change Gate over local agent-facing surfaces, including
  authority, capability, scope, lifecycle, sensitivity, and surface-presence
  observations.
- Governance Replay over an explicit saved local trace, producing bounded
  six-category coverage counts and raw context-delta telemetry.
- State Of Agent Context report under `release/v0.9.0/state-of-agent-context/`,
  containing pathless receipts for 8 selected public OSS repositories at pinned
  commits.
- Public Evidence Core contracts: JCS canonicalization, Decision v2,
  StateRevision v2, RetrievalManifest, InfluenceEdge, RollbackVerification, and
  reason-code registry.
- Public Evidence Core local storage primitives: CAS blob store, SQLite ledger,
  commit protocol, reconciler, and legacy migration helpers.

## Boundary

- No network call, API call,
  provider/model call, scheduler, daemon, public write, target repository write,
  package-registry publish, issue/PR creation, outreach, runtime execution, or
  adapter execution.
- The inherited `ctxgov continuity apply --mode sandbox` path may write one local
  sandbox file and is not a target repository write.
- Evidence Core is a library surface: it may write CAS blobs and SQLite rows only
  under explicit local evidence-store paths chosen by the caller.
- Governance Replay reports saved local replay observations only. It does not
  assert comparative outcomes, productivity outcomes, public benchmark claim,
  external uptake, platform coverage, deployment readiness, certification
  status, or stable API/protocol claim.
- The State Of Agent Context report is a read-only semantic inventory. It does
  not assert benchmark standing, endorsement, risk-review results, platform
  coverage, external uptake, or deployment readiness.
- Full Runtime Shadow, OEM adapters, repository app integration, OTel import,
  and deep Incident Forensics remain private until separately reviewed.

## Local Check

```bash
python3 scripts/run_public_package_checks.py
```

The check runs only local fixture reads, local tempdir evidence-store writes, and
command smoke tests.
