# CtxGov v0.6.10 - ASCR-Aligned Evidence Update

Status: owner-approved public-safe ASCR alignment update.

This release links CtxGov / Memory X-Ray to the new sibling ASCR project:
Agent State & Context Runtime Contract.

CtxGov remains the public evidence and report-shape surface. ASCR is the
separate framework-neutral contract/toolkit repository for agent event logs,
context manifests, memory records, artifact manifests, capability manifests,
approval events, and trace-linked eval cases.

ASCR repo: <https://github.com/ctxgov/ascr>

## What Shipped

- A new public ASCR sibling repo with v0.1 schemas, public-safe samples,
  a standard-library validator, tests, and a clean boundary document.
- CtxGov README and project homepage updates that explain the relationship:
  CtxGov is ASCR-aligned evidence; ASCR is the separate contract/toolkit.
- A v0.6.10 ASCR-aligned evidence pack with alignment summary, claim lint,
  leak scan, link check, publication readiness, and execution receipts.
- A local release-pack checker:
  `python3 scripts/check_ascr_aligned_release_pack.py`.

## Why It Matters

The highest-leverage public move is not another agent framework. It is a clean
contract boundary for the state an agent acts from: events, compiled context,
memory provenance, artifact versions, capabilities, approvals, and eval cases.

This update makes that boundary visible while keeping claims narrow. CtxGov
shows how an agent context health report can align to ASCR-shaped runtime
artifacts. It does not claim that ASCR is a stable standard, externally adopted,
provider-compatible, or production-certified.

## Evidence

- ASCR public repo: <https://github.com/ctxgov/ascr>
- v0.6.10 evidence pack:
  `release/v0.6.10/ascr-aligned-evidence-update/`
- v0.6.9 Memory X-Ray public evidence release:
  `release/v0.6.9/memory-xray-public-evidence-preview/`
- Companion local eval artifact:
  <https://github.com/ctxgov/agent-context-evals/releases/tag/v0.7.0>

## Reproduce Locally

From the repository root:

```bash
python3 scripts/check_ascr_aligned_release_pack.py
```

This check validates local release structure, ASCR link posture, claim boundary,
local links, and publication receipts. It does not call providers, write memory
backends, publish packages, run outreach, or write external targets.

## Explicitly Not Claimed

- No public benchmark claim.
- No security guarantee.
- No provider/model compatibility claim.
- No adoption or downstream production-use claim.
- No package publication claim.
- No hosted runtime claim.
- No live adapter claim.
- No public spec-stability claim.
- No stable ASCR standard claim.
- No CtxGov CLI beta claim.

## Rollback And Provenance

Rollback is to revert the v0.6.10 README/homepage patch, remove
`release/v0.6.10/`, and keep v0.6.9 as the public evidence surface. The ASCR
repo remains a separate sibling project and does not require private CtxGov
state to be understood or validated.
