# Public Checkout Readiness Receipt

Status: local verification receipt only. No branch, commit, push, pull request,
tag, release, GitHub Pages deployment, live URL pass, HN submission, X post, or
LinkedIn post has been executed.

Milestone: `Local Memory State Influence Boundary Report`

Verified public repository: `ctxgov/ctxgov`

Verified public checkout base: `3a87b69`

Publication bundle digest: recorded in
`memory-state-influence-boundary-publication-bundle.json`.

## Verification Performed

The prepared publication bundle was materialized into a fresh public
`ctxgov/ctxgov` checkout with:

```sh
python3 scripts/materialize_memory_state_influence_boundary_publication_bundle.py --checkout <clean-ctxgov-checkout>
```

Observed materialization result:

- status:
  `pass_memory_state_influence_boundary_publication_bundle_materialized`
- copied files: matched `publication_file_count` in the bundle JSON
- copied file count observed in the latest readiness run: `52`
- product integration quickstart copied: `true`
- checkout was clean before materialization: `true`
- branch created: `false`
- commit created: `false`
- push executed: `false`
- pull request created: `false`
- tag created: `false`
- release created: `false`
- GitHub Pages deployed: `false`
- live URL checked by the readiness wrapper: `true`
- live URL status: `HTTP 404 Not Found`
- outreach performed: `false`

Then the materialized public checkout passed:

```sh
python3 scripts/check_memory_state_influence_boundary_final_preflight.py
```

Observed final preflight result:

- status: `pass_memory_state_influence_boundary_final_preflight`
- go/no-go: `go_local_ready_external_publish_pending`
- sample input files: `9`
- blocked refs in sample: `4`
- stale/superseded refs in sample: `2`
- publication files: matched `publication_file_count` in the bundle JSON
- materialized copied files: matched `publication_file_count` in the bundle JSON
- owner publisher dry-run smoke: `pass`
- full report contract: `pass`
- consumer integration smoke: `pass`
- consumer wrapper contract: `pass`
- consumer wrapper blocked decision: `block`
- consumer wrapper passing decision: `allow_inform_only`
- release distinctness warnings: `0`
- social draft drift: `pass`
- owner publish packet contract: `pass`
- owner publisher dry-run target checkout before/after line count: `0` / `0`
- owner publisher dry-run write/commit/push/publication/outreach: `false`
- issue count: `0`

The public checkout did not include the full-source docs information
architecture checker, so that optional full-source check was reported as
`skipped_missing_optional_full_source_check` in the public checkout. The full
source checkout still runs the docs information architecture gate.

## External Actions Still Required

- Commit and push the prepared public repo patch.
- Wait for GitHub Pages deployment.
- Clear the current live-page blocker:
  `https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html`
  still returns `HTTP 404 Not Found` before publication.
- Run:

```sh
python3 scripts/check_memory_state_influence_boundary_live_publication.py --live
```

- Manually post selected HN/X/LinkedIn copy only after the live URL passes.

## Claim Boundary

This receipt does not create a provider integration, runtime adapter,
compatibility/support claim, endorsement, security guarantee, benchmark,
savings claim, adoption claim, stable protocol claim, package publication,
public release, or outreach claim.
