# ASCR-Aligned Evidence Update

This pack records the public-safe v0.6.10 relationship between CtxGov and ASCR.

ASCR means Agent State & Context Runtime Contract. The public ASCR repo is:
<https://github.com/ctxgov/ascr>

CtxGov remains an agent context health and memory-governance report-shape
surface. ASCR is the separate contract/toolkit repo.

## Included Receipts

- `ascr-alignment-summary.json` - relationship, surfaces, and boundaries.
- `claim-lint.json` - public claim-boundary receipt.
- `leak-scan.json` - public leak-scan receipt.
- `link-check.json` - local and live-link receipt.
- `publication-readiness.json` - owner approval and public-write scope.
- `publication-execution-receipt.json` - publication and verification receipt.
- `manifest.json` - release-pack asset inventory.

## ASCR v0.1 Surfaces Referenced

- `ascr.run_event.v0.1`
- `ascr.context_manifest.v0.1`
- `ascr.memory_record.v0.1`
- `ascr.artifact_manifest.v0.1`
- `ascr.capability_manifest.v0.1`
- `ascr.approval_event.v0.1`
- `ascr.eval_case.v0.1`

## Reproduce

From the repository root:

```bash
python3 scripts/check_ascr_aligned_release_pack.py
```

## Boundary

This pack does not publish private traces or fixture internals. It does not
claim public benchmark results, security guarantees, provider/model
compatibility, external adoption, package publication, hosted runtime, live
adapters, public spec stability, stable ASCR standard status, or a CtxGov CLI
beta.
