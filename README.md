# CtxGov

Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context
before agents act.

CtxGov is an agent context health and memory-governance project. It treats
README text, AGENTS instructions, terminal transcripts, saved memory summaries,
release notes, and tool receipts as context that can shape the next agent run.
Memory X-Ray turns that context into a report with finding types, evidence
spans, and explicit release boundaries. v0.6.10 aligns that report shape to
ASCR: Agent State & Context Runtime Contract.

## 30-Second View

- Problem: agents act from mixed context that may be stale, contradictory,
  unsupported, unsafe, or memory-shaped in misleading ways.
- Product surface: a Memory X-Ray report that points at the context span and
  says what is risky before the agent acts.
- Contract alignment: CtxGov is the ASCR-aligned evidence surface; ASCR is the
  separate framework-neutral contract/toolkit repo.
- Evidence posture: public-safe report-shape and local release-control
  readiness, not a public benchmark or adoption claim.
- Current release pack: `release/v0.6.10/` records the ASCR-aligned evidence
  update. `release/v0.6.9/` remains the Memory X-Ray public evidence release.

## Run Locally

```bash
python3 scripts/check_public_evidence_release_pack.py
python3 scripts/check_ascr_aligned_release_pack.py
```

The public v0.6.10 surface is an ASCR-aligned evidence update layered on the
v0.6.9 Memory X-Ray report-shape release. It does not publish a Memory X-Ray
CLI beta.

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
- v0.6.9 release notes:
  [`release/v0.6.9/RELEASE_NOTES.md`](release/v0.6.9/RELEASE_NOTES.md)
- Memory X-Ray public evidence pack:
  [`release/v0.6.9/memory-xray-public-evidence-preview/`](release/v0.6.9/memory-xray-public-evidence-preview/)
- L1 public preview:
  [`release/v0.7.0/memory-xray-l1-public-preview/`](release/v0.7.0/memory-xray-l1-public-preview/)
- Companion local eval v0.7.0:
  <https://github.com/ctxgov/agent-context-evals/releases/tag/v0.7.0>

The v0.6.9 evidence pack includes a machine-readable summary, claim lint,
leak scan, 60-second demo script, technical note, reviewer packet, and
publication boundary manifest.

The v0.6.10 evidence pack records the ASCR relationship, ASCR repo verification,
claim lint, leak scan, link check, and publication receipts.

## Claim Boundary

Allowed public claims:

- CtxGov provides an agent context health / memory-governance report shape.
- Memory X-Ray public-safe examples show finding types and evidence spans.
- Local release-control summaries cover repeat-run stability, no-op handoff
  replay, rollback refs, blocked lanes, and fail-closed negative modes.
- CtxGov v0.6.10 is aligned to ASCR v0.1 contract surfaces.

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

This release does not execute provider/model calls, memory-backend writes,
external target writes, package publication, hosted runtime changes, or
outreach. The public GitHub push, release, metadata update, and Pages
verification are recorded as owner-approved publication actions.

## Release Status

The public-safe release path is now:

1. v0.6.9 publishes Memory X-Ray as report-shape and local release-control
   evidence.
2. v0.6.10 adds the ASCR sibling-repo relationship and ASCR-aligned evidence
   update.
3. Public claims remain scoped to report shape, contract alignment, and
   local/public-safe receipts.

Formal benchmark, adoption, provider compatibility, package, live adapter,
security, or spec-stability releases remain blocked until they have independent
review evidence, non-picked real saved traces, downstream design-change signal,
permissioned case-study material, hidden holdout custody, and final public
rollback/claim-lint receipts.

## Repo Map

- `src/ctxvault/` - CLI and local report-generation code.
- `schemas/json/` - JSON schemas for reports and receipts.
- `fixtures/` - local fixtures and private-sidecar evidence.
- `release/` - public-safe release packs and release notes.
- `docs/` - project page and release planning documents.
- `companion/agent-context-evals/` - companion local-eval artifact.
- ASCR sibling repo - <https://github.com/ctxgov/ascr>.

## License And Governance

[`SECURITY.md`](SECURITY.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) are part
of the public repo hygiene surface. CtxGov uses Apache-2.0. OpenSSF/GitHub
hygiene is treated as trust posture, not as a security certification.
