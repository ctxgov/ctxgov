# CtxGov

CtxGov is a local-first research and developer tool for diagnosing and
governing agent context and memory-state influence before an agent acts.

## Current Public Surface

- Public product/package version: `0.7.0`.
- Public evidence artifact: `release/v0.7.0/`.
- Historical release packs are archive material, not the current product
  narrative.

## What You Can Run

The v0.7.0 public package supports a narrow CLI surface:

```bash
ctxgov continuity compile examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov continuity render examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov continuity apply --mode dry-run examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov memory-xray validate release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json
```

Other development surfaces are outside this public package boundary and are not
included in the source distribution.

## Input And Output

Input:

- one explicit local saved trace file;
- optional Memory X-Ray JSON report-shape examples.

Output:

- a `ctxvault.session-continuity-sidecar/v0` JSON object;
- a human-readable next-session continuity packet;
- a dry-run or sandbox-only apply result;
- a Memory X-Ray validation receipt.

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
schedulers, daemons, or target repository writes.

## CLI Boundary

Supported public commands:

- `ctxgov continuity compile`
- `ctxgov continuity render`
- `ctxgov continuity apply --mode dry-run|sandbox`
- `ctxgov memory-xray validate`

No other commands are included in the public package. Real target writes,
publication automation, schedulers, daemons, and provider/model execution are
outside this release.

## Claim Boundary

Not claimed:

- public benchmark result;
- adoption or community traction;
- security, safety, or privacy certification;
- provider/model compatibility;
- hosted runtime;
- PyPI/package-registry publication;
- stable protocol or stable MGP;
- autonomous remediation.

The checked-in `ctxvault.*` schema identifiers are stable legacy contract
strings, not a current branding claim.

## License

Apache-2.0. See `LICENSE`.
