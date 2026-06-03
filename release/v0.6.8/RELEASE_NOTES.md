# CtxGov v0.6.8 Release Notes

Date: 2026-06-03
Status: public GitHub source release.

## Summary

CtxGov v0.6.8 aligns the main repo public surface with the companion Agent
Context Evals v0.7.0 release.

This release does not publish a new CtxGov package or runtime. It updates the
public artifact chain so README, GitHub Pages source, positioning, LinkedIn
material, hiring packet, and release-integrity checks point to the current
companion v0.7 trace-shaped local evaluation artifact.

## Companion v0.7.0 Summary

- Release: `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.7.0`
- Report: `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.7-results.md`
- Demo fixture:
  `https://github.com/ctxgov/agent-context-evals/blob/main/demo/reports/v0.7-live-report-fixture.md`

The companion v0.7 artifact includes:

- 96 trace-shaped local cases
- 96 labels
- 72 positive cases
- 24 clean controls
- offline GitHub, CI/log, rules-file, package-registry, transcript, and memory
  adapters
- automated FP/FN, per-finding, span, and hard-negative leakage analysis
- refreshed technical report and static demo fixture

## Local Verification

- `python3 -m unittest tests/test_release_integrity_checker.py`
- `python3 scripts/check_release_integrity.py --root .`
- `python3 -m unittest discover -s tests`
- `git diff --check`

## Claim Boundary

This release does not publish a new package, hosted runtime, public benchmark
result, security guarantee, provider compatibility claim, network adapter
claim, agent-safety claim, or adoption claim.

The companion v0.7.0 metrics are local scaffold/readiness evidence over
synthetic trace-shaped data, not real-world benchmark performance.

## Rollback

If v0.6.8 public links or release metadata are wrong, publish a superseding
release rather than moving the v0.6.8 tag silently. Keep v0.6.7 available as
the previous current-companion wording guard release.
