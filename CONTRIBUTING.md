# Contributing To CtxGov

CtxGov is Agent Context Health Evaluation for AI Workflows. Contributions are
welcome when they keep the project local, inspectable, evidence-backed, and
careful about claim boundaries.

## Good First Contributions

- Improve labeled context-hazard cases without adding private paths or raw OSS
  excerpts.
- Add deterministic scoring tests for stale, conflicting, unsupported, unsafe,
  or hidden-failure context.
- Improve docs that explain how evidence spans map to finding types.
- Add public-safe examples that make claim boundaries clearer.
- Propose benchmark cases in `https://github.com/ctxgov/agent-context-evals`.

## Boundaries

Do not submit changes that require a model key, provider call, hosted runtime,
target repository write, public benchmark claim, provider/framework
compatibility claim, hardware or cost claim, security guarantee, or stable
protocol claim unless a maintainer has opened an explicit approved lane for that
work.

Public examples must stay sanitized. They should not include private local
paths, credentials, raw secrets, unpublished private receipts, or raw excerpts
from third-party repositories.

The GitHub public package and CLI use `ctxgov`. Historical schemas, fixtures,
receipts, and older docs may still use the legacy `ctxvault` namespace. See
`docs/provenance.md` before proposing schema, fixture, or compatibility
migration work.

## Development

Run focused tests for the area you changed. For public release surface changes,
run:

```bash
python3 -m unittest tests.test_context_health_doctor tests.test_v062_testpypi_success_and_release_drafts
PYTHONPATH=src python3 -m ctxgov.cli doctor --path fixtures/v0.6.2-context-health-doctor/sample-repo --output /tmp/ctxgov-health --include-report
```

For companion benchmark material, run:

```bash
git clone https://github.com/ctxgov/agent-context-evals
cd agent-context-evals
python3 baselines/regex_baseline.py --cases data/cases.jsonl --output reports/regex-baseline-results.jsonl
python3 ctxgov_adapter/run_ctxgov.py --cases data/cases.jsonl --output reports/ctxgov-adapter-results.jsonl
python3 scoring/score_findings.py --labels data/labels.jsonl --predictions reports/ctxgov-adapter-results.jsonl
```

Use small pull requests. Lead with the data, scorer, fixture, receipt, test, or
public example that proves the change is reviewable.

## Issue Labels

Useful first labels for maintainers:

- `good first issue`: small docs, examples, cases, or focused tests.
- `help wanted`: bounded work with an existing issue or schema.
- `public-surface`: README, examples, release notes, demo, or project page.
- `eval`: datasets, labels, scoring, baselines, or result analysis.
- `governance`: receipts, claim boundaries, rollback, or review state.
- `needs-owner-approval`: work that could publish, write targets, run
  providers, run adapters, or change public claims.
