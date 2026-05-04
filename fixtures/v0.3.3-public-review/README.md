# CtxVault v0.3.3 Public Review Corpus

This corpus is for owner-operated public package review before v0.3.3
publication.

The source notes are short CtxVault-authored summaries of public references,
not copied long-form articles. The point is to test deterministic context
selection, privacy preflight, projection receipts, budget boundaries, empty
search boundaries, and decoy handling with auditable public source URLs.

This is a public-package release smoke gate, not a broad retrieval-quality
benchmark. It uses deterministic fixture anchors so the owner can verify the
package, receipts, blocked-selection behavior, and boundary behavior without
flaky ranking expectations. Natural-language retrieval quality should be
evaluated in a separate scorecard.

The reusable suite is defined in `scenarios.json`. Add new local review cases
there, then add or update source notes under `sources/`. The script loads the
manifest at runtime, so scenario coverage can grow without changing the review
runner's core logic.

Run:

```bash
python3 scripts/run_v033_public_review_pack.py --root /tmp/ctxvault-v033-public-review --force
```

Then inspect:

- `/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/owner-review.md`
- `/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/owner-review.html`
- `/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/summary.json`
- `/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/projection.md`
- `/tmp/ctxvault-v033-public-review/artifacts/v0.3.3-public-review/projection-receipt.json`

## Owner Review Protocol

Use this when reviewing the public package without any private CtxVault
context:

1. Run the command above from the extracted public package.
2. Open `owner-review.md` or `owner-review.html` first.
3. Inspect the human report's selected sources before reading the gate result.
4. Confirm that every `forbidden_source_refs` entry is absent from
   `selected_source_refs`.
5. Confirm `blocked_selection.decision` is `block` and
   `blocked_selection.allowed_to_write` is `false`.
6. Open `projection.md` and confirm it is understandable without private
   context.
7. Open `projection-receipt.json` and confirm the selected slice refs match
   the projection summary.
8. Approve publication only if the output explains the handoff path clearly
   enough for a new reviewer.
9. Treat `summary.json` and receipts as evidence backing the human report, not
   as the first reading surface.

The expected behavior now covers multiple scenario classes:

- ready handoff scenarios should select expected public source notes, remain
  within budget, receive privacy `allow`, and write selection receipts;
- CLI/README onboarding, release-note, API/log, license, connector-boundary,
  open-source, privacy, local-search, and secure-release shapes should each
  have at least one deterministic scenario;
- budget-trim scenarios should keep the small relevant source and skip the
  larger noisy source under a tight budget;
- empty-query scenarios should produce zero candidates, no selected slices,
  an empty-selection warning, and an audit receipt instead of fabricating
  context;
- over-budget scenarios should produce an over-budget warning and should not
  mark the handoff ready;
- the synthetic secret source should be withheld and block projection if
  explicitly selected.

## Public References

- NIST Privacy Framework: https://www.nist.gov/privacy-framework
- SQLite FTS5 Extension: https://www.sqlite.org/fts5.html
- SQLite public domain notice: https://sqlite.org/draft/copyright.html
- CISA Secure by Design: https://www.cisa.gov/securebydesign
- NASA Open Source Development: https://www.nasa.gov/nasa-open-source-development/
- SPDX License List: https://spdx.org/licenses/
