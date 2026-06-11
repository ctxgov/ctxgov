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
- Current release: `v0.6.13-auto-publish-research` is a public-safe
  release-integrity / auto-publish research fixture with no wider claim.
- Companion eval: `agent-context-evals` `v0.8.0` is the current public local
  eval-hardening artifact, not a public benchmark.

## Run Locally

```bash
python3 scripts/check_public_evidence_release_pack.py
python3 scripts/verify_release_integrity.py \
  --manifest release/auto-publish-research/2026-06-07/release-integrity-verification-plan.materialized.json \
  --output <tmp-dir>/ctxgov-v0613-release-integrity.json
```

The public v0.6.13 surface is a release-integrity and auto-publish research
fixture. The older v0.6.9 surface remains a report-shape evidence pack. Neither
release publishes a Memory X-Ray CLI beta.

## Activation X-Ray Try-in-5-Minutes

The HN/X/LinkedIn-published milestone after the claim-firewall launch is a
user-operable Activation X-Ray demo:

```bash
git clone https://github.com/ctxgov/ctxgov.git
cd ctxgov
python3 scripts/run_activation_xray_scale_profile_demo.py
```

It checks 24 local scale-profile cases across `local_single_user`,
`team_project`, and `cluster_multi_tenant`, then writes JSON, Markdown, and HTML
reports under `.ctxvault/activation-xray-scale-profile-demo/`.

Single-command local final preflight:

```bash
python3 scripts/check_activation_xray_final_preflight.py
```

This runs the Activation X-Ray go/no-go, release candidate, publish pack, local
repeatability experiment, social payload render, focused unit tests,
`py_compile`, and `git diff --check`. In the full source checkout it also runs
the docs information architecture check and HN skip-live preflight; public slim
checkouts report those absent full-source checks as skipped.

One-command local release-candidate gate:

```bash
python3 scripts/check_activation_xray_next_milestone_release_candidate.py
```

Consolidated owner go/no-go gate:

```bash
python3 scripts/check_activation_xray_publication_go_no_go.py
```

Social copy readiness gate:

```bash
python3 scripts/check_activation_xray_social_copy_ready.py
```

Local repeatability experiment:

```bash
python3 scripts/benchmark_activation_xray_scale_profile_demo.py
```

This repeats the demo locally, records runtime smoke evidence and stable
observation fingerprints, and keeps `public_benchmark_claim_created=false`.
It is publication readiness evidence, not a public benchmark claim.

Render structured HN/X/LinkedIn post payloads without posting:

```bash
python3 scripts/render_activation_xray_social_post_payload.py
```

Render the owner publish packet with final preflight digest, publish commands,
and platform copy:

```bash
python3 scripts/render_activation_xray_owner_publish_packet.py
```

Dry-run the public patch publication flow from the source checkout:

```bash
python3 scripts/publish_activation_xray_public_patch.py --checkout <clean-ctxgov-checkout>
```

Add `--materialize` to copy the bundle into that local checkout and rerun the
target go/no-go gate. Commit and push remain explicit opt-ins via
`--execute-commit` and `--execute-push`. The execute path is covered locally
with a temporary bare git remote, so it can be tested without contacting
GitHub.

The gate also writes the minimal public publication bundle:
`release/activation-xray-scale-profile-demo/2026-06-10/activation-xray-publication-bundle.json`
and `.md`.

To apply that bundle into a clean local public checkout without commit or push:

```bash
python3 scripts/materialize_activation_xray_publication_bundle.py --checkout <clean-ctxgov-checkout>
```

To render the exact publish commands without executing them:

```bash
python3 scripts/render_activation_xray_publish_command_envelope.py
```

After the public patch is pushed and GitHub Pages deploys:

```bash
python3 scripts/check_activation_xray_live_publication.py --live
```

Public page candidate:
<https://ctxgov.github.io/ctxgov/activation-xray-try-in-5-minutes.html>

This is still scoped to local influence-receipt inspection.

Boundary: no public benchmark, savings, compatibility/support, adoption,
endorsement, security, stable-protocol, provider/model, runtime,
memory-backend, package, or outreach claim.

## Local Memory State Influence Boundary Report

The next HN/X/LinkedIn-publishable milestone after Activation X-Ray is a local
audit of user-supplied memory/context/state files:

```bash
git clone https://github.com/ctxgov/ctxgov.git
cd ctxgov
python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/
```

Then point it at your own local memory/context/state file:

```bash
python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md
```

Directory scans are also supported:

```bash
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/
```

For CI or product integration, fail the command when blocked refs are found:

```bash
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --fail-on-blocked
```

To emit only the machine-readable gate for a wrapper or CI step:

```bash
python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked
```

The v0 gate contract is documented at
`schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json`,
with blocked and passing sample outputs at
`release/memory-state-governability-overlay/2026-06-11/integration-gate.example.json`
and
`release/memory-state-governability-overlay/2026-06-11/integration-gate.pass.example.json`.
The full report contract is documented at
`schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json`.
The copyable consumer wrapper example contract is documented at
`schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json`,
with blocked/pass sample outputs at
`release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json`
and
`release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json`.
The product integration quickstart is documented at
`release/memory-state-governability-overlay/2026-06-11/product-integration-quickstart.md`;
it is the handoff index for report generation, the fail-closed gate, wrapper
decisions, schema examples, and the no-raw-content boundary.
This consumer wrapper contract is local and example-scoped.
This is a local tooling contract, not a stable protocol or provider
compatibility claim.

To check the local gate contract, sample output, stdout JSON shape, and
`--fail-on-blocked` exit-code behavior together:

```bash
python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py
```

To check the full report contract, raw-content boundary, and embedded gate
counts together:

```bash
python3 scripts/check_memory_state_influence_boundary_report_contract.py
```

To run a consumer integration smoke test for a product wrapper consuming the
report/gate and making block-vs-allow decisions without raw content:

```bash
python3 scripts/check_memory_state_influence_boundary_consumer_integration.py
```

To check the copyable consumer wrapper output schema, blocked/pass example
drift, decision mapping, and no-raw-content boundary:

```bash
python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py
```

To run a copyable consumer wrapper example that calls the report/gate CLI and
emits a `block` decision for blocked inputs:

```bash
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py
```

To run the same wrapper against a clean inform-only input and see an
`allow_inform_only` decision:

```bash
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
```

To check that the prepared HN/LinkedIn/X release is distinct from the prior
claim-firewall and Activation X-Ray launches:

```bash
python3 scripts/check_memory_state_influence_boundary_release_distinctness.py
```

To smoke-test the BYO path with a temporary repo-external memory-state
directory, blocked/pass gate exit codes, input-relative paths, omitted inputs,
and secret-like redaction:

```bash
python3 scripts/check_memory_state_influence_boundary_byo_smoke.py
```

The blocked-ref gate still writes the JSON, Markdown, and HTML report; it only
changes the process exit code for automation.
The JSON report also includes an `integration_gate` object with
`default_exit_code`, `fail_on_blocked_exit_code`, blocked/omitted/stale/imported
counts, and `raw_content_included=false`, so products can consume the gate
without reconstructing it from multiple report sections.

It reads local files such as `AGENTS.md`, `CLAUDE.md`, `MEMORY.md`, project
notes, MDX context files, JSON/JSONL checkpoint exports, YAML/YML state files,
or TOML state profiles and writes an influence-boundary report. The report
classifies candidate influence refs,
inform-only allowed refs, blocked refs, omitted refs, stale/superseded refs,
imported context refs, and missing policy-grant/final-state/rollback proof.
Findings include structured JSON/TOML/YAML key/value path evidence and review
recommendations while raw file content stays out of the report.
Inputs outside the repository are rendered with input-relative paths such as
`input/CLAUDE.md`, so reports do not default to exposing local absolute paths.
Unsupported or over-limit inputs are counted as omitted; the report keeps a
bounded skipped-input sample instead of copying every skipped path from a large
directory. Malformed JSON/JSONL/TOML state exports are blocked until the state
export is parseable.

The original no-argument command remains available as a built-in sample, but
the publishable path is the user-supplied file/directory audit above.

Render the next LinkedIn/X/HN payload without posting:

```bash
python3 scripts/render_memory_state_governability_overlay_social_payload.py
```

Check that the static HN/LinkedIn/X drafts still match the generated payload:

```bash
python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py
```

Render the owner publish packet with final preflight digest, publish commands,
and platform copy:

```bash
python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py
```

Check that the owner publish packet still matches the bundle digest, command
envelope, social payload, and no-side-effect boundary:

```bash
python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py
```

Check the next publish pack:

```bash
python3 scripts/check_memory_state_influence_boundary_final_preflight.py
python3 scripts/check_memory_state_governability_overlay_publish_pack.py
python3 scripts/check_memory_state_influence_boundary_report_contract.py
python3 scripts/check_memory_state_influence_boundary_consumer_integration.py
python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py
python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml
python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py
python3 scripts/build_memory_state_influence_boundary_publication_bundle.py
python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py
python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py
python3 scripts/render_memory_state_influence_boundary_publish_command_envelope.py
python3 scripts/check_memory_state_influence_boundary_public_checkout_readiness.py --check-live
```

The final preflight includes a clean-checkout materialization smoke test: it
copies the publication bundle into a temporary git checkout and verifies
that no commit, push, live URL check, release, or outreach side effect occurred.
It also smoke-tests the owner public patch publisher in dry-run mode and
verifies that the target checkout remains clean before and after the run.
The release pack also includes a no-push receipt for a fresh public
`ctxgov/ctxgov` checkout.

After the public page is deployed:

```bash
python3 scripts/check_memory_state_influence_boundary_live_publication.py --live
```

To copy the prepared bundle into a clean local public checkout without commit or
push:

```bash
python3 scripts/materialize_memory_state_influence_boundary_publication_bundle.py --checkout <clean-ctxgov-checkout>
```

Dry-run the public patch publication flow from the source checkout:

```bash
python3 scripts/publish_memory_state_influence_boundary_public_patch.py --checkout <clean-ctxgov-checkout>
```

Add `--materialize` to copy the bundle into that local checkout and rerun the
target preflight without commit or push. Commit and push remain explicit opt-ins
via `--execute-commit` and `--execute-push`.

Public page candidate:
<https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html>

Boundary: no provider integration, runtime adapter, compatibility/support,
endorsement, security, benchmark, savings, adoption, stable-protocol, package,
or outreach claim.

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
- Current CtxGov release:
  <https://github.com/ctxgov/ctxgov/releases/tag/v0.6.13-auto-publish-research>
- Activation X-Ray Try-in-5-Minutes:
  <https://ctxgov.github.io/ctxgov/activation-xray-try-in-5-minutes.html>
- Local Memory State Influence Boundary Report candidate:
  <https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html>
- v0.6.13 auto-publish research pack:
  [`release/auto-publish-research/2026-06-07/`](release/auto-publish-research/2026-06-07/)
- v0.6.13 post-publication summary:
  [`release/auto-publish-research/2026-06-07/post-publication-summary.md`](release/auto-publish-research/2026-06-07/post-publication-summary.md)
- Prior v0.6.9 release notes:
  [`release/v0.6.9/RELEASE_NOTES.md`](release/v0.6.9/RELEASE_NOTES.md)
- Prior Memory X-Ray public evidence pack:
  [`release/v0.6.9/memory-xray-public-evidence-preview/`](release/v0.6.9/memory-xray-public-evidence-preview/)
- L1 public preview:
  [`release/v0.7.0/memory-xray-l1-public-preview/`](release/v0.7.0/memory-xray-l1-public-preview/)
- Companion local eval v0.8.0:
  <https://github.com/ctxgov/agent-context-evals/releases/tag/v0.8.0>

The v0.6.13 release includes a live-link verification asset,
`ctxgov-v0613-live-link-verification.json`, with SHA-256
`64e2b8462cbb0c25e89d2f85ec32a665173e9fdda39b5f152d9289d7c59e51f7`.
The v0.6.9 evidence pack remains available for the Memory X-Ray report-shape
evidence summary, claim lint, leak scan, demo script, technical note, reviewer
packet, and publication boundary manifest.

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
