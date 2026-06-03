# CtxGov v0.6.4 Release Notes

Status: prepared GitHub source release draft for Context Health Doctor coverage.
This release has not been published by this file alone.

CtxGov v0.6.4 is a doctor coverage release. It adds native context-health
finding types and exact evidence spans needed by the companion Agent Context
Health Eval v0.4 artifact.

## Added

- Native release integrity findings:
  - `release_link_404`
  - `package_registry_unverified`
  - `release_artifact_missing`
- Native Memory X-Ray L1 findings:
  - `memory_missing_source_coverage`
  - `memory_missing_rollback`
  - `memory_unbounded_consequence`
  - `memory_missing_model_state_surface`
- Native Task Shard context-control findings:
  - `task_shard_schema_conflict`
  - `task_shard_unapproved_side_effect`
  - `task_shard_missing_rollback`
- Exact `evidence_span` values in Context Health Doctor findings and evidence
  manifests.
- Stale-context detection for `pending approval contradicts ready claim`.

## Verification

Run before publishing the release:

```bash
python3 -m unittest tests.test_context_health_doctor
python3 -m unittest tests.test_surface tests.test_v062_public_surface_cleanup tests.test_v062_testpypi_success_and_release_drafts
python3 scripts/check_release_integrity.py --root .
PYTHONPATH=src python3 -m ctxgov.cli doctor --path fixtures/v0.6.2-context-health-doctor/sample-repo --output /tmp/ctxgov-health --include-report
```

Companion eval verification:

```bash
cd agent-context-evals
python3 ctxgov_adapter/run_ctxgov.py --cases data/v0.2/trace_pattern_cases.jsonl --output reports/v0.4-ctxgov-doctor-results.jsonl --mode doctor --ctxgov-root /path/to/ctxgov
python3 scoring/score_findings.py --labels data/v0.2/trace_pattern_labels.jsonl --predictions reports/v0.4-ctxgov-doctor-results.jsonl
```

Observed companion v0.4 scaffold result with this doctor coverage:

- precision: 1.0000
- recall: 1.0000
- F1: 1.0000
- mean evidence token-F1: 1.0000

## Claim Boundary

This release improves local doctor coverage and adapter readiness. It does not
claim a public benchmark result, security guarantee, provider compatibility,
agent safety, package publication, hosted runtime, or adoption evidence. The
v0.4 eval data remains public trace-pattern and synthetic hard-negative
material pending independent review and adjudication.

## Rollback

Delete or supersede the `v0.6.4` GitHub release draft, remove the tag if one was
created, and link readers back to `v0.6.3` plus this release note as an
unpublished draft. No target repository write, provider/model call, package
registry, memory backend, or hosted runtime state is created by this source
release draft.
