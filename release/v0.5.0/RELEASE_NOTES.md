# CtxVault v0.5.0 Release Notes

Status: v0.5.0 public release artifact.

Governed context projection for AI work.

Boundary phrase for publication review: no target repository writes and no provider/model execution.

## Headline

CtxVault v0.5.0 prepares governed context projection for AI work.

Reviewed evidence, decisions, caveats, and receipts can be rendered into
portable context packets for AI tools, agents, and coding workflows.

## What Is New

- Public-safe evidence page for the v0.5.0 proof scene.
- Static demo script for walking through evidence, caveats, blocked material,
  manifests, and receipts.
- Sanitized example bundle showing evidence -> decision -> projection ->
  receipt without private local paths or raw source exports.
- Release wording gate for local path leaks and common overclaims, run before
  publication.
- Public artifact manifest for release-following review.

## Evidence Summary

The v0.5.0 release is backed by one private dogfood path and three
owner-selected OSS dry-runs. Public evidence is intentionally aggregate-only:

| Evidence Set | Runs | Candidates | Caveated | Blocked | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Owner-selected OSS dry-runs | 3 | 121 | 20 | 101 | passed |

These runs are deterministic local dry-runs only. They are not benchmark,
leaderboard, reliability, runtime, adapter, provider/model, hardware, cost, or
automatic optimization evidence.

## How To Review

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Then inspect:

- `README.md`
- `release/v0.5.0/v0.5.0-public-evidence-page-draft.md`
- `release/v0.5.0/v0.5.0-public-demo-script-draft.md`
- `examples/v0.5.0-governed-context-projection/README.md`

## Not Included

- No public benchmark or leaderboard result.
- No public reliability, accuracy, or coding-performance improvement claim.
- No adapter, runtime, provider/model, or hardware/cost compatibility claim.
- No automatic repository optimization claim.
- No stable Memory Governance Protocol claim.
- No Memory OS, RAG replacement, hallucination prevention, or security
  certification claim.

## Publication Status

These public release artifacts are published from a clean release branch. The
release does not include private dogfood receipts, private local paths,
repo-local source excerpts, target repository writes, provider/model outputs,
or hosted runtime evidence.
