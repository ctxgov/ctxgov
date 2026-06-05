# 60-Second Demo Script

Goal: make the value obvious without relying on benchmark or adoption claims.

## Frame

CtxGov finds risky AI-facing context before the next agent run uses it.

## Shot List

0-5s: Show the problem.

- Left panel: `README.md` says a release is complete.
- Left panel: `AGENTS.md` contains an unsafe deployment instruction.
- Left panel: terminal transcript shows a command hung and was killed.
- Left panel: saved memory summary says public approval already happened.

5-35s: Run the report.

```bash
python3 scripts/check_public_evidence_release_pack.py
```

35-50s: Show the report-shape preview.

- `stale_claim`: release copy contradicts current receipts.
- `unsafe_instruction`: deploy/write instruction lacks owner approval.
- `unsupported_claim`: benchmark/adoption/spec language lacks public evidence.
- `memory_claim_drift`: saved memory overstates publication state.
- `terminal_failure`: hung command is evidence, not a pass receipt.

50-60s: Show the boundary.

- 0 public benchmark claims.
- 0 provider/model calls.
- 0 memory-backend writes.
- 0 external target writes.
- 0 public CLI beta claims.
- Evidence spans and rollback path are visible.

## Copy

Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context
before agents act.

## Production Notes

- Use a side-by-side before/after layout.
- Do not show private trace contents, private fixture internals, tokens, private
  targets, or unpublished reviewer details.
- End on the evidence-pack link, not on an overbroad performance claim.
