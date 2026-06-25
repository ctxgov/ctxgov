# CtxGov v0.9.0 - Real-Source Governance Evaluation Candidate

This release candidate publishes a public-only CtxGov package for local
governance evaluation over explicit saved traces, local files, local
repositories, and public-safe evidence fixtures.

## Included

- `ctxgov continuity compile|render|apply`
- `ctxgov memory-xray validate`
- `ctxgov change-gate-check` with read-only semantic findings and summary output
- `ctxgov change-gate-federate`
- `ctxgov oss-case-study-preview`
- `ctxgov oss-efficiency evaluate|validate`
- `ctxgov governance-replay`
- `ctxgov forensics-timeline`
- `ctxgov forensics-trace`
- `ctxgov forensics-gaps`
- Public Evidence Core contracts and explicit local evidence-store primitives
- `release/v0.9.0/state-of-agent-context/` pathless semantic inventory receipts
  for 8 selected public OSS repositories at pinned commits

## Not Included

- Network/API calls, provider/model calls, schedulers, daemons, runtime adapters,
  target repository writes, public writes, package-registry publishing,
  issue/PR creation, outreach, publication automation, or hosted runtime.
- Speedup, productivity, adoption, public benchmark, provider compatibility,
  production readiness, security certification, stable API/protocol, or
  autonomous remediation claims.

## Local Check

```bash
python3 scripts/run_public_package_checks.py
```

## Claim Boundary

Governance Replay and Evidence Core outputs are bounded local receipts. They do
not generalize to other projects, users, models, providers, or workflows.

The State Of Agent Context report is a selected real-OSS semantic inventory, not
a benchmark, endorsement, security review, compatibility result, adoption claim,
or production-readiness claim.
