# CtxGov

Find stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context
before agents act.

CtxGov is an agent context health and memory-governance project. It treats
README text, AGENTS instructions, terminal transcripts, saved memory summaries,
release notes, and tool receipts as context that can shape the next agent run.
Memory X-Ray turns that context into a report with finding types, evidence
spans, and explicit release boundaries.

## 30-Second View

- Problem: agents act from mixed context that may be stale, contradictory,
  unsupported, unsafe, or memory-shaped in misleading ways.
- Product surface: a Memory X-Ray report that points at the context span and
  says what is risky before the agent acts.
- Evidence posture: public-safe report-shape and local release-control
  readiness, not a public benchmark or adoption claim.
- Current release pack: `release/v0.6.9/` is prepared as a public evidence
  preview pending owner-approved publication.

## Run Locally

```bash
python3 scripts/check_public_evidence_release_pack.py
```

The public v0.6.9 surface is a release-pack and report-shape preview. It does
not publish a Memory X-Ray CLI beta.

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

## Claim Boundary

Allowed public claims:

- CtxGov provides an agent context health / memory-governance report shape.
- Memory X-Ray public-safe examples show finding types and evidence spans.
- Local release-control summaries cover repeat-run stability, no-op handoff
  replay, rollback refs, blocked lanes, and fail-closed negative modes.

Not claimed:

- No public benchmark claim.
- No security guarantee.
- No provider/model compatibility claim.
- No adoption or downstream production-use claim.
- No package publication claim.
- No hosted runtime claim.
- No live adapter claim.
- No public spec-stability claim.
- No memory-backend write.
- No CLI beta claim.

This release does not execute provider/model calls, memory-backend writes,
external target writes, package publication, hosted runtime changes, or
outreach. The public GitHub push, release, metadata update, and Pages
verification are recorded as owner-approved publication actions.

## Release Status

The public-safe release path is:

1. Keep the public narrative scoped to report shape and local readiness.
2. Publish sanitized evidence only; do not publish private traces or fixture
   internals.
3. Run claim lint, leak scan, link checks, release-pack checks, and Pages fetch
   verification.
4. Publish only after owner approval in a clean public `ctxgov/ctxgov` repo
   patch.

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

## License And Governance

[`SECURITY.md`](SECURITY.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) are part
of the public repo hygiene surface. License selection remains an owner decision
before public release. OpenSSF/GitHub hygiene is treated as trust posture, not
as a security certification.
