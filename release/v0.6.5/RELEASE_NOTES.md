# CtxGov v0.6.5 Release Notes

Status: prepared GitHub source release draft for local release-integrity and
multi-label evaluation readiness. This file alone does not publish the release.

CtxGov v0.6.5 tightens the public artifact loop between the main repo and the
companion Agent Context Health Eval v0.5 artifact.

## Added

- Local release-integrity checker for current public surface links, release
  pointers, project page references, public claim boundaries, and private-marker
  guardrails:

```bash
python3 scripts/check_release_integrity.py --root .
```

- Context Health Doctor coverage for v0.5 mutation and multi-label evaluation
  patterns:
  - release link 404 and release-link-not-found paraphrases
  - Memory X-Ray L1 source coverage, rollback, consequence ceiling, and
    model-state surface paraphrases
  - Task Shard schema conflict, unapproved side effect, and missing rollback
    paraphrases
  - hidden terminal failure phrasing with `handoff says green` and
    `exit code 1`
  - stale ready claims contradicted by pending approval gates
- Narrower action guidance detection so neutral release audit text is not
  treated as unsafe action guidance.

## Companion Eval v0.5

Related companion artifact:

- Release: `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.5.0`
- Results report:
  `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.5-results.md`
- Project page: `https://ctxgov.github.io/ctxgov/`

Observed local scaffold run on 2026-06-03:

| Evaluator | Cases | Labels | Precision | Recall | F1 | Evidence token-F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| regex baseline / v0.5 mutation multi-label scaffold | 160 | 206 | 1.0000 | 0.6205 | 0.7658 | 1.0000 |
| CtxGov doctor adapter / v0.5 mutation multi-label scaffold | 160 | 206 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

## Verification

Run before publishing the release:

```bash
python3 -m unittest tests.test_context_health_doctor
python3 -m unittest tests.test_release_integrity_checker
python3 scripts/check_release_integrity.py --root .
PYTHONPATH=src python3 -m ctxgov.cli doctor --path fixtures/v0.6.2-context-health-doctor/sample-repo --output /tmp/ctxgov-health --include-report
```

Companion eval verification:

```bash
cd agent-context-evals
python3 scripts/generate_v05_mutation_data.py
python3 baselines/regex_baseline.py --cases data/v0.5/mutation_cases.jsonl --output reports/v0.5-regex-baseline-results.jsonl --multi-label
python3 ctxgov_adapter/run_ctxgov.py --cases data/v0.5/mutation_cases.jsonl --output reports/v0.5-ctxgov-doctor-results.jsonl --mode doctor --projection none --ctxgov-root /path/to/ctxgov
python3 scoring/score_multilabel.py --labels data/v0.5/mutation_labels.jsonl --predictions reports/v0.5-regex-baseline-results.jsonl
python3 scoring/score_multilabel.py --labels data/v0.5/mutation_labels.jsonl --predictions reports/v0.5-ctxgov-doctor-results.jsonl
```

## Claim Boundary

This release improves local doctor coverage, public-surface checking, and
adapter readiness. It does not claim a public benchmark result, security
guarantee, provider compatibility claim, agent-safety claim, package
publication, hosted runtime, or adoption evidence. The v0.5 eval data is a
deterministic local mutation scaffold, not independently adjudicated trace data.

## Rollback

Delete or supersede the `v0.6.5` GitHub release draft, remove the tag if one was
created, and link readers back to `v0.6.4` plus this release note as an
unpublished draft. No target repository write, provider/model call, package
registry, memory backend, or hosted runtime state is created by this source
release draft.
