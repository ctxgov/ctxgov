# CtxGov

![Public Surface Checks](https://github.com/ctxgov/ctxgov/actions/workflows/public-surface.yml/badge.svg)

Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context
before agents act.

CtxGov is an agent context health and memory-governance project. It treats
README text, AGENTS instructions, terminal transcripts, saved memory summaries,
release notes, and tool receipts as context that can shape the next agent run.
Memory X-Ray turns that context into a report with finding types, evidence
spans, and explicit release boundaries. v0.12.0 records a public fresh-clone
product receipt for the one-command Memory X-Ray preview path.

## 30-Second View

- Problem: agents act from mixed context that may be stale, contradictory,
  unsupported, unsafe, or memory-shaped in misleading ways.
- Product surface: a Memory X-Ray report that points at the context span and
  says what is risky before the agent acts.
- Contract alignment: CtxGov is the ASCR-aligned evidence surface; ASCR is the
  separate framework-neutral Agent State & Context Runtime Contract toolkit
  repo.
- Evidence posture: public-safe report-shape and local release-control
  readiness, not a public benchmark or adoption claim.
- Current product receipt: `release/v0.12.0/` records fresh-clone execution of
  the one-command Memory X-Ray preview path and report SHA. `release/v0.6.13/`
  remains the owner-approved auto-publish research path.

## Run Locally

```bash
python3 scripts/check_public_evidence_release_pack.py
python3 scripts/check_ascr_aligned_release_pack.py
python3 scripts/check_public_surface_hardening.py
python3 scripts/check_publication_intent.py
python3 scripts/check_v012_fresh_clone_product_receipt.py
python3 scripts/run_memory_xray_demo.py
python3 -m unittest tests.test_public_live_links -v
python3 scripts/render_public_memory_xray_preview.py \
  --input release/v0.7.0/memory-xray-l1-public-preview/memory-xray-l1-examples-pack.json \
  --output /tmp/ctxgov-memory-xray-preview.md
```

The public v0.6.13 surface is an auto-publish research and release-integrity
update layered on the v0.6.12 live-link verifier, v0.6.11 hardening release,
v0.6.10 ASCR alignment, and v0.6.9 Memory X-Ray report-shape release. The
v0.12.0 product receipt adds a fresh-clone run of the one-command Memory X-Ray
preview path. The report preview renderer is deterministic public-safe example
rendering only. It is not a Memory X-Ray CLI beta and does not scan arbitrary
target repositories.

Optional network verification after offline checks pass:

```bash
python3 scripts/check_public_live_links.py --release-tag v0.6.13-auto-publish-research
```

## Example Report Shape

```text
finding=unsupported_claim severity=high evidence=README.md
finding=unsafe_instruction severity=high evidence=AGENTS.md
finding=terminal_failure severity=medium evidence=terminal.log
finding=memory_claim_drift severity=medium evidence=memory-summary.md
boundary=no_public_benchmark_claim,no_provider_call,no_target_write
```

## What Memory X-Ray Finds

- `stale_claim`: release or project text no longer matches current receipts.
- `conflicting_instruction`: AI-facing instructions disagree across sources.
- `unsupported_claim`: public copy exceeds available evidence.
- `unsafe_instruction`: context asks for external write, outreach, deploy, or
  provider/model action without an approval gate.
- `memory_claim_drift`: saved memory overstates state, authority, approval, or
  publication status.
- `terminal_failure`: failed or hung terminal output is treated as evidence,
  not as a pass receipt.

## Evidence

- Project homepage: <https://ctxgov.github.io/ctxgov/>
- ASCR toolkit: <https://github.com/ctxgov/ascr>
- v0.6.10 release notes:
  [`release/v0.6.10/RELEASE_NOTES.md`](release/v0.6.10/RELEASE_NOTES.md)
- ASCR-aligned evidence pack:
  [`release/v0.6.10/ascr-aligned-evidence-update/`](release/v0.6.10/ascr-aligned-evidence-update/)
- v0.6.11 release notes:
  [`release/v0.6.11/RELEASE_NOTES.md`](release/v0.6.11/RELEASE_NOTES.md)
- Self-audit public report:
  [`release/v0.6.11/self-audit-public-report/`](release/v0.6.11/self-audit-public-report/)
- v0.6.12 release notes:
  [`release/v0.6.12/RELEASE_NOTES.md`](release/v0.6.12/RELEASE_NOTES.md)
- v0.6.13 release notes:
  [`release/v0.6.13/RELEASE_NOTES.md`](release/v0.6.13/RELEASE_NOTES.md)
- v0.6.13 publication intent:
  [`release/v0.6.13/publication-intent.json`](release/v0.6.13/publication-intent.json)
- v0.12.0 release notes:
  [`release/v0.12.0/RELEASE_NOTES.md`](release/v0.12.0/RELEASE_NOTES.md)
- v0.12.0 fresh-clone product receipt:
  [`release/v0.12.0/fresh-clone-product-receipt.json`](release/v0.12.0/fresh-clone-product-receipt.json)
- v0.6.13 live-link verification asset:
  <https://github.com/ctxgov/ctxgov/releases/download/v0.6.13-auto-publish-research/ctxgov-v0613-live-link-verification.json>
- Self-audit case study:
  [`docs/case-studies/v0.6.9-self-audit.md`](docs/case-studies/v0.6.9-self-audit.md)
- v0.6.9 release notes:
  [`release/v0.6.9/RELEASE_NOTES.md`](release/v0.6.9/RELEASE_NOTES.md)
- Memory X-Ray public evidence pack:
  [`release/v0.6.9/memory-xray-public-evidence-preview/`](release/v0.6.9/memory-xray-public-evidence-preview/)
- L1 public preview:
  [`release/v0.7.0/memory-xray-l1-public-preview/`](release/v0.7.0/memory-xray-l1-public-preview/)
- Memory X-Ray demo report:
  [`docs/memory-xray-demo-report.md`](docs/memory-xray-demo-report.md)
- Try in 5 minutes:
  [`docs/try-in-5-minutes.html`](docs/try-in-5-minutes.html)
- Tiny fixture Memory X-Ray demo:
  [`docs/tiny-fixture-memory-xray-demo.html`](docs/tiny-fixture-memory-xray-demo.html)
- Companion fresh-clone reproducibility eval v0.11.0:
  <https://github.com/ctxgov/agent-context-evals/releases/tag/v0.11.0>
- 5-minute companion local eval path:
  <https://github.com/ctxgov/agent-context-evals/blob/main/docs/5-minute-local-run.md>
- 5-minute feedback request:
  <https://github.com/ctxgov/agent-context-evals/issues/22>

The v0.6.9 evidence pack includes a machine-readable summary, claim lint,
leak scan, 60-second demo script, technical note, reviewer packet, and
publication boundary manifest.

The v0.6.10 evidence pack records the ASCR relationship, ASCR repo verification,
claim lint, leak scan, link check, and publication receipts.

The v0.6.11 evidence pack records a public-safe self-audit of post-publication
context drift and a deterministic preview renderer for the L1 public examples.

The v0.6.12 release adds an optional live-link verifier for public URLs after
offline release-pack checks pass.

The v0.6.13 release records an owner-approved publication intent for the
minimal public release path: CtxGov repo patch, release tag, GitHub release,
and Pages verification only. Its live-link verification asset SHA-256 is
`64e2b8462cbb0c25e89d2f85ec32a665173e9fdda39b5f152d9289d7c59e51f7`.

The v0.12.0 release records a fresh-clone run of
`python3 scripts/run_memory_xray_demo.py`, command output, and the generated
Memory X-Ray report SHA-256. It is product-path reproducibility evidence, not a
benchmark, adoption, security, provider/model compatibility, package, hosted
runtime, live adapter, human reviewer, or CLI beta claim.

The companion `agent-context-evals` v0.11.0 release is linked as local
fresh-clone reproducibility evidence for the v0.10.0 public saved-trace
machine-evidence path, redaction, and hidden-holdout custody evidence, not as a
public benchmark, adoption, security, provider/model compatibility, package,
hosted runtime, live adapter, human reviewer, or CLI beta claim.

The checked-in Memory X-Ray demo report is generated by
`python3 scripts/run_memory_xray_demo.py`. It renders public-safe before/after
examples only; it is not a CLI beta and does not scan arbitrary target
repositories.

## Claim Boundary

Allowed public claims:

- CtxGov provides an agent context health / memory-governance report shape.
- Memory X-Ray public-safe examples show finding types and evidence spans.
- `scripts/run_memory_xray_demo.py` renders the checked-in public-safe
  before/after report.
- `release/v0.12.0/fresh-clone-product-receipt.json` records a fresh-clone
  one-command Memory X-Ray preview run and report SHA.
- Local release-control summaries cover repeat-run stability, no-op handoff
  replay, rollback refs, blocked lanes, and fail-closed negative modes.
- CtxGov v0.6.10 is aligned to ASCR v0.1 contract surfaces.
- CtxGov v0.6.11 renders public-safe Memory X-Ray examples deterministically
  and records a self-audit case study for public-surface drift.
- CtxGov v0.6.12 provides an optional live-link verifier for public release
  URLs after offline checks pass.
- CtxGov v0.6.13 records an owner-approved minimal public release path for
  auto-publish research, with deferred targets explicitly excluded.
- CtxGov v0.12.0 records a public fresh-clone product receipt for the
  one-command Memory X-Ray preview path.

Not claimed:

- No public benchmark claim.
- No security guarantee.
- No provider/model compatibility claim.
- No adoption or downstream production-use claim.
- No package publication claim.
- No hosted runtime claim.
- No live adapter claim.
- No public spec-stability claim.
- No stable ASCR standard claim.
- No memory-backend write.
- No CLI beta claim.
- No package publication claim from `pyproject.toml` version metadata.

This release does not execute provider/model calls, memory-backend writes,
unapproved non-CtxGov target writes, package publication, hosted runtime
changes, or outreach. The public GitHub push, release, metadata update, and
Pages verification are recorded as owner-approved publication actions. v0.6.13
excludes agent-context-evals writes, org profile updates, issue/comment writes,
and LinkedIn/X posting from the approved publication surface.

## Release Status

The public-safe release path is now:

1. v0.6.9 publishes Memory X-Ray as report-shape and local release-control
   evidence.
2. v0.6.10 adds the ASCR sibling-repo relationship and ASCR-aligned evidence
   update.
3. v0.6.11 adds public-surface consistency, self-audit, public-surface CI, and
   deterministic report preview rendering.
4. v0.6.12 adds optional network verification of public release URLs.
5. v0.6.13 records the owner-approved minimal public release path for
   auto-publish research.
6. v0.12.0 records the fresh-clone one-command Memory X-Ray product path and
   report SHA.
7. Public claims remain scoped to report shape, contract alignment, and
   local/public-safe receipts.

Formal benchmark, adoption, provider compatibility, package, live adapter,
security, or spec-stability releases remain blocked until they have independent
review evidence, non-picked real saved traces, downstream design-change signal,
permissioned case-study material, hidden holdout custody, and final public
rollback/claim-lint receipts.

## Repo Map

- `src/ctxgov/` - public package/module path.
- `schemas/` - report and receipt schema material.
- `fixtures/` - public-safe fixtures and local evidence material.
- `release/` - public-safe release packs and release notes.
- `docs/` - project page, provenance, and public-safe case studies.
- `agent-context-evals` - separate companion repo linked from evidence, not
  vendored into this repo.
- ASCR sibling repo - <https://github.com/ctxgov/ascr>.

## License And Governance

[`SECURITY.md`](SECURITY.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) are part
of the public repo hygiene surface. License: Apache-2.0. The license enables
source use and contribution review; it is not a security, benchmark, adoption,
compatibility, package-publication, or support claim.
