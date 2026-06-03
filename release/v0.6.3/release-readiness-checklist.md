# CtxGov v0.6.3 Release Readiness Checklist

Date: 2026-06-03
Status: local release checklist for a future GitHub source release.

## Local Materials

- [x] README first screen leads with CtxGov.
- [x] Public metadata file defines description, About, website, and topics.
- [x] Provenance file explains legacy `ctxvault` namespace.
- [x] GitHub release draft exists.
- [x] Release notes exist.
- [x] Project page and demo material exists.
- [x] Companion benchmark skeleton is ready for separate repo publication.
- [x] Technical report draft exists.
- [x] Hiring, LinkedIn, outreach, and curated issue materials exist.

## Manual GitHub Steps

- [ ] Create or confirm public repo `ctxgov/ctxgov`.
- [ ] Update GitHub About description.
- [ ] Add website URL.
- [ ] Add topics from `docs/public-repo-metadata.md`.
- [ ] Create tag `v0.6.3`.
- [ ] Publish the GitHub release using `release/v0.6.3/github-release.md`.
- [ ] Verify the release URL is not 404.
- [ ] Verify README rendering in GitHub.
- [ ] Verify GitHub Pages URL if enabled.

## Verification Commands

Run from the repository root:

```bash
python3 -m unittest tests.test_context_health_doctor tests.test_v062_testpypi_success_and_release_drafts
PYTHONPATH=src python3 -m ctxgov.cli doctor --path fixtures/v0.6.2-context-health-doctor/sample-repo --output /tmp/ctxgov-health --include-report
rg -n "CtxVault|ctxvault/ctxvault|github.com/ctxvault|python3 -m ctxvault|memory-xray|release/v0.7.0" README.md docs/public-repo-metadata.md docs/public-positioning.md docs/public-github-repo-launch-checklist.md docs/index.html
```

Run from the companion staging directory:

```bash
git clone https://github.com/ctxgov/agent-context-evals
cd agent-context-evals
python3 baselines/regex_baseline.py --cases data/cases.jsonl --output reports/regex-baseline-results.jsonl
python3 ctxgov_adapter/run_ctxgov.py --cases data/cases.jsonl --output reports/ctxgov-adapter-results.jsonl
python3 scoring/score_findings.py --labels data/labels.jsonl --predictions reports/ctxgov-adapter-results.jsonl
```

Expected grep result: no public-surface legacy namespace hits in those files
except explicit provenance or compatibility discussion.

## Publication Boundary

Do not publish if release copy claims:

- security guarantees
- public benchmark performance
- provider/framework/memory-backend compatibility
- target repository writes
- provider/model execution
- automatic remediation
- stable protocol status

## Rollback

Delete or supersede the GitHub release, delete the tag if created, restore the
previous README and About copy, and keep all local material as draft evidence.
