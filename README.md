# CtxVault

Status: v0.5.3 public release artifact. Public core and evidence surface.

Governed context projection for AI work.

Know what your AI tools were allowed to see.

CtxVault is the local trust layer for AI work. It helps you decide which
evidence is allowed to influence the next AI work surface, with visible review
decisions, omissions, caveats, and rollback receipts.

Start with a decision preview, not a dashboard:

| Decision | What CtxVault shows first |
| --- | --- |
| Claim | What can be safely stated, and which claims are blocked. |
| Context | What can enter the AI-facing packet, and what was omitted or caveated. |
| Memory | What is blocked from durable reuse until lifecycle and rollback exist. |
| Action | What cannot run or write until side-effect approval exists. |

It is not another agent memory platform, RAG runtime, provider SDK, benchmark
runner, or agent harness. The control point is narrower and more inspectable:

```text
source evidence -> review decision -> portable context packet -> receipt
```

Boundary phrase for publication review: no target repository writes and no provider/model execution.

## Why This Exists

AI tools are getting better at using context, but teams still lack a clean way
to answer:

- Which source evidence was allowed into this AI-facing packet?
- What was omitted, caveated, or blocked?
- Which target surface was previewed?
- How do we roll back or audit the packet later?

CtxVault makes that path explicit. Reviewed evidence becomes a portable packet
for tools like `AGENTS.md`, `CLAUDE.md`, Cursor rules, or a workstream brief.
Receipts keep the source refs, decision state, omitted evidence, blocked refs,
hashes, target-profile dry-runs, and rollback path visible.

Then what: when agent memory, retrieval, docs, generated notes, and local files
start to blur together, CtxVault gives reviewers a receipt for what was allowed
to influence the next AI-facing context packet.

## Start Here

For downstream OSS case-study adoption, start with the public-safe decision
preview path:

```bash
python3 scripts/validate-case-study-templates.py
PYTHONPATH=src python3 -m ctxvault.cli oss-case-study-preview \
  --target-name example \
  --repo-url https://github.com/owner/repo \
  --pinned-ref <commit> \
  --source-path /path/to/local/README.md \
  --output-dir /tmp/ctxvault-case-study
```

The command above reads an explicit local source path and writes only local
CtxVault preview artifacts. Remote README fetch is gated behind
`--allow-network`; it still does not clone, run, install, call a provider/model,
write target files, create issues, or promote memory.

Run the deterministic public checks:

```bash
python3 scripts/check_v050_public_drafts.py
PYTHONPATH=src python3 -m unittest tests.test_v05_pull_context_governance_planning
```

Inspect the public-safe evidence and examples:

- `release/v0.5.3/RELEASE_NOTES.md`
- `release/v0.5.3/experience-evidence-pack.md`
- `release/v0.6.0/public-influence/mem0-public-case-study-deep-dive.md`
- `release/v0.6.0/public-influence/case-study-card.md`
- `examples/v0.5.3-experience-evidence/README.md`
- `docs/mechanism/governed-context-projection.md`
- `docs/mechanism/governed-context-projection.zh.md`

The examples are synthetic and sanitized. They show the evidence -> decision ->
projection -> receipt shape without exposing private local paths, private
receipts, raw OSS source excerpts, target repository writes, provider/model
outputs, or hosted runtime behavior.

## What The Public Core Shows

- Evidence is treated as candidate context until review or policy decisions
  caveat, block, or withhold it.
- Directory projection previews render reviewed material into portable,
  agent-facing files.
- Receipts record source refs, hashes, selected/omitted/blocked material,
  target-profile dry-runs, quality checks, and rollback paths.
- Public-safe evidence is available as aggregate OSS dry-run metrics and
  sanitized examples, not raw private receipts.

## Proof Scene: Public Evidence

The current proof scene is CtxVault dogfood plus three owner-selected local OSS
dry-runs. These are deterministic local dry-runs only. Public evidence is
intentionally aggregate-only:

| Evidence Set | Runs | Candidates | Caveated | Blocked | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| Owner-selected OSS dry-runs | 3 | 121 | 20 | 101 | passed |

Across the three OSS dry-runs, CtxVault produced 121 candidates, caveated 20,
blocked 101, verified manifests, passed target-profile dry-runs, and kept
target writes disabled.

Additional v0.6.0 external OSS governance evaluation work is being prepared as
public evidence surface material. It is not a public benchmark, compatibility
claim, runtime claim, or stable protocol claim.

## Public v0.6.0 Evidence Surface

- Static demo: `docs/index.html`
- mem0 read-only governance case study:
  `release/v0.6.0/public-influence/mem0-public-case-study-deep-dive.md`
- Public extract data:
  `release/v0.6.0/public-influence/mem0-public-case-study-extract.json`

The mem0 case study is a read-only governance evaluation over public metadata
and a sanitized extract. It does not judge mem0 quality, performance,
compatibility, correctness, security, or maintainer endorsement.
It exists to show the governance shape directly: `2056` candidate refs,
`478` selected, `263` caveated, `98` blocked, and `1217` omitted.

## Compatibility Notes

The v0.4.0 public product floor remains available as a deterministic local
trial: CtxVault v0.4.0 is a local, reviewable, receipt-backed AI work context
handoff package. Its baseline keeps the same trust floor:

- no local LLM is required
- no remote LLM is required
- no account, cloud service, provider call, hidden session scan, or runtime
  control is required for the demo path

Run the v0.4.0 one-click context handoff trial:

```bash
python3 scripts/run_v040_context_handoff_trial.py --root /tmp/ctxvault-v040-trial --reset
```

Start with the generated `v0.4.0-first-run-report.md`.

To try the same handoff path on your own local repo without writing back into
that repo:

```bash
python3 scripts/run_v040_real_repo_trial.py --repo /path/to/your/repo --root /tmp/ctxvault-v040-real-repo-trial --reset
```

Repeatability evidence can be regenerated under `/tmp/ctxvault-v040-repeatability`.

v0.4.1 is an experimental, non-normative Projection Governance Kernel design
preview. It is not a stable external API and not runtime behavior.

## Reviewer Path

Inspect the public-safe evidence and demo material:

```bash
python3 scripts/check_v050_public_drafts.py
PYTHONPATH=src python3 -m unittest tests.test_v05_pull_context_governance_planning
```

Then read:

- `release/v0.5.0/RELEASE_NOTES.md`
- `docs/mechanism/governed-context-projection.md`
- `docs/mechanism/governed-context-projection.zh.md`
- `release/v0.5.0/v0.5.0-public-evidence-page-draft.md`
- `release/v0.5.0/v0.5.0-public-demo-script-draft.md`
- `examples/v0.5.0-governed-context-projection/README.md`

The example is synthetic and sanitized. It is meant to show the evidence ->
decision -> projection -> receipt shape without exposing private local paths,
private receipts, or raw OSS source excerpts.

## Claim Boundary

Mechanism notes:

- `docs/mechanism/governed-context-projection.md`
- `docs/mechanism/governed-context-projection.zh.md`
- `release/v0.5.0/mechanism-note-governed-context-projection.md`
- `release/v0.5.0/mechanism-note-governed-context-projection.zh.md`

Allowed wording:

- CtxVault turns reviewed evidence, decisions, caveats, and receipts into
  portable context packets for AI tools, agents, and coding workflows.
- The v0.5.0 proof scene includes CtxVault dogfood plus owner-selected local
  OSS dry-runs.
- The dry-runs perform no hidden scan, no provider/model call, no adapter
  execution, no runtime execution, no memory promotion, and no target writes.

Do not claim:

- benchmark or leaderboard results
- reliability, accuracy, or coding-performance improvement
- adapter, runtime, provider/model, or hardware/cost compatibility
- automatic repository optimization
- stable Memory Governance Protocol
- Memory OS, RAG replacement, hallucination prevention, or security
  certification

## Current Release Status

The latest public release is v0.5.3. It exposes sanitized experience evidence
and aggregate OSS dry-run metrics, not private dogfood receipts, private local
paths, repo-local source excerpts, target repository writes, provider/model
outputs, or hosted runtime evidence.
