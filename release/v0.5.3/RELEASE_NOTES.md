# CtxVault v0.5.3 Release Notes

Status: v0.5.3 public release artifact.

Governed context projection for AI work.

Boundary phrase for publication review: no target repository writes and no provider/model execution.

## Headline

CtxVault v0.5.3 publishes the Experience Evidence Pack.

The release focuses on one product question: can a reviewer inspect what
context is selected, caveated, blocked, omitted, and rollbackable before it
becomes agent-visible?

## What Is New

- Public sanitized Experience Evidence Pack:
  `examples/v0.5.3-experience-evidence/`.
- Redacted receipt-viewer example with selected, omitted, blocked, warning,
  side-effect, and rollback fields.
- Future Context Review example with risk-ranked queue items and visible
  source-support uncertainty.
- Static Hugging Face Space source under
  `spaces/huggingface/v053-experience-evidence-static/`.
- Public release copy for explaining CtxVault as context inspection before AI
  work surfaces consume project context.
- v0.5.4 OSS evaluation readiness plan and read-only harness constraints.

## Evidence Boundary

The v0.5.3 examples are synthetic and sanitized. They do not include private
paths, raw private receipts, raw source excerpts, provider/model outputs,
target repository writes, or benchmark evidence.

The static Hugging Face Space source is a comprehension surface. It has no user
uploads, no network calls, no credentials, no provider/model execution, no
target writes, and no persistence.

## How To Review

```bash
python3 scripts/check_v050_public_drafts.py
python3 scripts/check_v053_public_release_artifacts.py --root .
PYTHONPATH=src python3 -m unittest discover -s tests
```

Then inspect:

- `examples/v0.5.3-experience-evidence/README.md`
- `examples/v0.5.3-experience-evidence/receipt-viewer/receipt-inspection.json`
- `examples/v0.5.3-experience-evidence/future-context-review/future-context-review-queue.json`
- `release/v0.5.3/experience-evidence-pack.md`
- `spaces/huggingface/v053-experience-evidence-static/`

## Not Included

- No public benchmark or leaderboard result.
- No public reliability, accuracy, or coding-performance improvement claim.
- No adapter, runtime, provider/model, or hardware/cost compatibility claim.
- No automatic repository optimization claim.
- No stable Memory Governance Protocol claim.
- No Memory OS, RAG replacement, hallucination prevention, or security
  certification claim.
- No live hosted runtime.
- No target repository writes.
- No provider/model execution.

## Rollback

Rollback is bounded to public release surfaces: delete or supersede the
v0.5.3 GitHub release, delete the `v0.5.3` tag, delete the
`release-v0.5.3` branch if needed, and publish a superseding receipt. The
release does not create provider/model, target-write, projection-write, memory,
or hosted-runtime state.
