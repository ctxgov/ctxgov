# CtxGov v0.6.6 Release Notes

Status: prepared GitHub source release draft for companion v0.6 alignment. This
file alone does not publish the release.

CtxGov v0.6.6 keeps the main repo public surface aligned with the companion
Agent Context Health Eval v0.6.0 release.

## Updated

- Public README, project page, LinkedIn/outreach pack, hiring packet, and
  positioning docs now point to companion `v0.6.0` and
  `reports/v0.6-results.md` as the current evaluation artifact.
- Local release-integrity checker now expects:
  - CtxGov release: `v0.6.6`
  - companion release: `v0.6.0`
  - companion report: `reports/v0.6-results.md`
- Public page copy includes v0.6 adversarial hard negatives and span
  diagnostics.

## Companion v0.6.0 Summary

Related companion artifact:

- Release: `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.6.0`
- Results report:
  `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.6-results.md`
- Project page: `https://ctxgov.github.io/ctxgov/`

Observed local hard-negative run on 2026-06-03:

| Evaluator / Split | Cases | Expected positives | Predicted positives | False positives |
| --- | ---: | ---: | ---: | ---: |
| regex baseline / v0.6 adversarial hard negatives | 60 | 0 | 0 | 0 |
| CtxGov doctor adapter / v0.6 adversarial hard negatives | 60 | 0 | 0 | 0 |

## Verification

Run before publishing the release:

```bash
python3 -m unittest tests.test_release_integrity_checker
python3 scripts/check_release_integrity.py --root .
python3 -m unittest discover -s tests
```

## Claim Boundary

This release updates public links and release-integrity expectations. It does
not claim a public benchmark result, security guarantee, provider compatibility
claim, agent-safety claim, package publication, hosted runtime, or adoption
evidence. The companion v0.6.0 data is local adversarial hard-negative scaffold
data, not independently adjudicated trace data.

## Rollback

Delete or supersede the `v0.6.6` GitHub release draft, remove the tag if one was
created, and link readers back to `v0.6.5` plus this release note as an
unpublished draft.
