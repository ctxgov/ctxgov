# Contributing To CtxVault

CtxVault is governed context projection for AI work. Contributions are welcome
when they keep the project inspectable, local-first, and receipt-backed.

## Good First Contributions

- Improve public examples without adding private paths or raw OSS excerpts.
- Add tests that make selected, omitted, caveated, blocked, or rollback state
  easier to audit.
- Improve docs that explain how reviewed evidence becomes a portable context
  packet.
- Add issue reproductions for confusing first-run or reviewer paths.
- Propose target-profile dry-runs for AI-facing files such as `AGENTS.md`,
  `CLAUDE.md`, Cursor rules, or workstream briefs.

## Boundaries

Do not submit changes that require a model key, provider call, hosted runtime,
target repository write, benchmark claim, adapter compatibility claim, hardware
or cost claim, or stable protocol claim unless a maintainer has opened an
explicit approved lane for that work.

Public examples must stay sanitized. They should not include private local
paths, credentials, raw secrets, unpublished private receipts, or raw excerpts
from third-party repositories.

## Development

Run focused tests for the area you changed. For public release surface changes,
run:

```bash
python3 scripts/validate_fixtures.py
python3 scripts/check_v050_public_drafts.py
PYTHONPATH=src python3 -m unittest tests.test_v05_pull_context_governance_planning
```

Use small pull requests. Lead with the receipt, fixture, test, or public example
that proves the change is reviewable.

## Issue Labels

Useful first labels for maintainers:

- `good first issue`: small docs, examples, or focused tests.
- `help wanted`: bounded work with an existing receipt or issue.
- `public-surface`: README, examples, release notes, or demo surface.
- `governance`: receipts, claim boundaries, rollback, or review state.
- `needs-owner-approval`: work that could publish, write targets, run providers,
  run adapters, or change public claims.
