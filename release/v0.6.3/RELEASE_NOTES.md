# CtxGov v0.6.3 Release Notes

Status: prepared GitHub source release draft for public-surface cleanup. This
release has not been published by this file alone.

## Summary

CtxGov v0.6.3 is a public-surface integrity release. It normalizes the public
artifact around Agent Context Health Evaluation for AI Workflows and prepares
local materials for a companion evaluation artifact.

## Changed

- Repositioned the README around CtxGov and agent context health evaluation.
- Added `docs/provenance.md` to isolate the legacy `ctxvault` namespace.
- Updated public repo metadata, GitHub launch checklist, and public positioning
  copy for CtxGov.
- Prepared the companion benchmark skeleton for
  `https://github.com/ctxgov/agent-context-evals`.
- Added project page, demo, LinkedIn, outreach, curated issue, and hiring packet
  materials.
- Added this GitHub release draft and a release-readiness checklist.

## Validation Targets

Run before publishing the release:

```bash
python3 -m unittest tests.test_context_health_doctor tests.test_v062_testpypi_success_and_release_drafts
PYTHONPATH=src python3 -m ctxgov.cli doctor --path fixtures/v0.6.2-context-health-doctor/sample-repo --output /tmp/ctxgov-health --include-report
git clone https://github.com/ctxgov/agent-context-evals
cd agent-context-evals
python3 baselines/regex_baseline.py --cases data/cases.jsonl --output reports/regex-baseline-results.jsonl
python3 ctxgov_adapter/run_ctxgov.py --cases data/cases.jsonl --output reports/ctxgov-adapter-results.jsonl
python3 scoring/score_findings.py --labels data/labels.jsonl --predictions reports/ctxgov-adapter-results.jsonl
```

Run broader tests only from a clean worktree because unrelated code changes can
affect local results.

## Non-Goals

This release does not:

- publish a package
- migrate historical schema, fixture, receipt, or generated-state names
- claim a public benchmark result
- claim security guarantees
- claim provider, framework, memory-backend, or agent-harness compatibility
- call providers or models
- write target repositories
- publish a live adapter, hosted runtime, or autonomous remediation workflow
- claim stable Memory Governance Protocol status

## Rollback

Delete or supersede the `v0.6.3` GitHub release draft, remove the tag if one was
created, restore the previous README/About copy, and keep `docs/provenance.md`
as the legacy namespace record. No package, provider/model, target repo, memory
backend, or hosted runtime state is created by this source-release draft.
