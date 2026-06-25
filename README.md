# CtxGov

CtxGov is a local-first research and developer tool for diagnosing and
governing agent context and memory-state influence before an agent acts.

## Current Public Surface

- Public product/package version: `0.9.0`.
- Public evidence artifact: `release/v0.9.0/`.
- Real OSS semantic inventory: `release/v0.9.0/state-of-agent-context/`.
- Historical release packs are archive material, not the current product
  narrative.

## What You Can Run

The v0.9.0 public package supports local governance evaluation CLI surfaces:

```bash
# Run on your own repository. This is read-only and writes no .ctxvault state.
ctxgov change-gate-check --root . --format summary

# Diff two explicit local trees and print a semantic Change Gate report.
ctxgov change-gate-check --baseline-root examples/change-gate-public-preview/baseline --head-root examples/change-gate-public-preview/head --format summary
```

Additional local checks:

```bash
ctxgov continuity compile examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov continuity render examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov continuity apply --mode dry-run examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov memory-xray validate release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json
ctxgov change-gate-federate --base-path examples/federation-public-preview --no-git-required
ctxgov oss-case-study-preview --target-name mem0 --repo-url https://github.com/mem0ai/mem0 --pinned-ref 366945965df43aa7084be98d1b5073b62a20b431 --source-path examples/oss-case-study-public-preview/mem0-source.md
ctxgov oss-efficiency evaluate --manifest release/v0.8.0/oss-efficiency-raw-telemetry-manifest.json
ctxgov governance-replay --trace examples/governance-replay-public-preview/governance-replay-trace.synthetic.json
ctxgov forensics-timeline --fixture release/v0.8.0/forensics-public-preview-fixture.json
ctxgov forensics-trace --fixture release/v0.8.0/forensics-public-preview-fixture.json --finding-id finding-public-authority-001
ctxgov forensics-gaps --fixture release/v0.8.0/forensics-public-preview-fixture.json
```

Other development surfaces are outside this public package boundary and are not
included in the source distribution.

## Input And Output

Input:

- one explicit local saved trace file;
- optional Memory X-Ray JSON report-shape examples.
- explicit local repository paths for Change Gate and Federation;
- an explicit saved local public-source excerpt for OSS Case Study Preview;
- explicit saved raw telemetry for OSS Efficiency methodology receipts;
- pathless State Of Agent Context receipts for selected public OSS repositories;
- an explicit saved local Governance Replay trace;
- explicit local fixture JSON for Forensics preview.

Output:

- a `ctxvault.session-continuity-sidecar/v0` JSON object;
- a human-readable next-session continuity packet;
- a dry-run or sandbox-only apply result;
- a Memory X-Ray validation receipt.
- a read-only semantic Change Gate report;
- a read-only Federation report;
- an OSS case-study decision preview;
- an OSS raw telemetry methodology receipt;
- a pathless real-OSS semantic inventory report;
- a Governance Replay result with bounded coverage counts;
- a Forensics timeline, trace, or gap report.

## Before / After

Before: the next agent session may inherit a long transcript, stale summary, or
ambiguous handoff with unclear source support.

After: CtxGov turns the explicit saved trace into source-backed continuity
evidence with blocked effects, side-effect boundaries, and rollback-by-discard
semantics before the next session uses it.

## Integration Gate

Run the local public package gate:

```bash
python3 scripts/run_public_package_checks.py
```

The gate performs no network calls, provider/model calls, public writes,
schedulers, daemons, or target repository writes. It may create a temporary
local Evidence Core store to verify CAS/SQLite commit and replay behavior.

The inherited `ctxgov continuity apply --mode sandbox` command may write one
local sandbox file. Evidence Core library calls write only explicit local
evidence-store paths chosen by the caller.

## CLI Boundary

Supported public commands:

- `ctxgov continuity compile`
- `ctxgov continuity render`
- `ctxgov continuity apply --mode dry-run|sandbox`
- `ctxgov memory-xray validate`
- `ctxgov change-gate-check`
- `ctxgov change-gate-federate`
- `ctxgov oss-case-study-preview`
- `ctxgov oss-efficiency evaluate|validate`
- `ctxgov governance-replay`
- `ctxgov forensics-timeline`
- `ctxgov forensics-trace`
- `ctxgov forensics-gaps`

No other commands are included in the public package. Real target writes,
network/API calls, publication automation, schedulers, daemons, runtime adapter
execution, and provider/model execution are outside this release.

## Claim Boundary

Not claimed:

- public benchmark result;
- comparative runtime or workflow outcome;
- external uptake or community traction;
- certification or risk assurance;
- model/vendor coverage;
- hosted runtime;
- automated publication pipeline;
- stable protocol or stable MGP;
- stable external Python API;
- autonomous remediation.

The checked-in `ctxvault.*` schema identifiers are stable legacy contract
strings, not a current branding claim.

## License

Apache-2.0. See `LICENSE`.
