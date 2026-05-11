# CtxVault v0.5.0 Public Artifact Manifest And Checklist

Status: v0.5.0 public release artifact.

Governed context projection for AI work.

Boundary phrase for publication review: no target repository writes and no provider/model execution.

## Public-Safe Release Artifacts

- `README.md`
- `release/v0.5.0/RELEASE_NOTES.md`
- `release/v0.5.0/v0.5.0-public-evidence-page-draft.md`
- `release/v0.5.0/v0.5.0-public-demo-script-draft.md`
- `release/v0.5.0/v0.5.0-sanitized-demo-packet.md`
- `examples/v0.5.0-governed-context-projection/README.md`
- `examples/v0.5.0-governed-context-projection/projection-preview/receipt.json`

## Required Checks Before Publication

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

The private release wording gate was also run before publication. It is not
shipped in this public artifact set because its explicit local dry-run
identifier checks would disclose maintainer-local evidence names.

Manual review checklist:

- No local absolute user-home paths.
- No private review receipt paths.
- No private receipt dumps.
- No SSH remote URLs.
- No provider/model outputs.
- No public benchmark, leaderboard, reliability, or accuracy claim.
- No adapter, runtime, provider/model, hardware, or cost compatibility claim.
- No automatic optimization claim.
- No stable Memory Governance Protocol, Memory OS, RAG replacement,
  hallucination prevention, or security certification claim.

## Hosted Publication Gate

The v0.5.0 public release artifacts are prepared locally. Hosted publication,
tag creation, push, announcement copy, and a GitHub or Forgejo release page
remain separate actions and should run only from a clean reviewed release
branch with this claim boundary intact.

This public artifact set intentionally excludes private release-readiness
fixtures, private dogfood receipts, specific local dry-run repository
identifiers, specific local dry-run snapshot identifiers, target repository
writes, provider/model outputs, and raw source exports.
