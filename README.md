# CtxGov

Agent Context Health Evaluation for AI Workflows.

CtxGov checks AI-facing project context before agent execution. It helps
reviewers find stale claims, conflicting instructions, unsupported release
statements, unsafe action guidance, and hidden failure residue before those
signals shape the next agent run.

Current public posture: local source artifact and public-safe local example
materials. No hosted runtime, provider/model call, target repository write,
public benchmark claim, security guarantee, compatibility matrix, adoption
claim, or stable protocol claim is made by this repository.

## Why This Exists

AI agents increasingly rely on repository files, memory summaries, release
notes, rules files, terminal logs, and handoff packets. When those inputs are
stale, contradictory, unsupported, or action-unsafe, the agent can confidently
execute against bad context.

CtxGov makes that risk inspectable before execution:

| Context hazard | Example failure | CtxGov review target |
| --- | --- | --- |
| Stale claim | README says a feature shipped, but release notes still mark it gated. | Flag the stale claim and point to the conflicting evidence. |
| Conflicting policy | `AGENTS.md` permits writes while governance docs block target writes. | Surface the conflict before an agent acts. |
| Unsupported release claim | Public copy links to a release/tag that does not exist. | Require a release artifact or downgrade the wording. |
| Unsafe action guidance | Docs suggest running deployment or network steps without approval. | Keep side-effect boundaries visible. |
| Hidden failure residue | A terminal log shows tests failed, but handoff text says they passed. | Preserve the failure span in the next review packet. |

## What It Produces

CtxGov public materials currently focus on four artifacts:

- main repo public surface: README, GitHub About copy, release notes, and claim
  boundaries
- Context Health Doctor: a read-only local report over AI-facing repository
  context
- companion evaluation repo:
  `https://github.com/ctxgov/agent-context-evals`
- project, hiring, and outreach packet material under `docs/` and `release/`

The GitHub main package and console command use `ctxgov`. Historical schemas,
fixtures, receipts, and older docs may still contain `ctxvault`; see
`docs/provenance.md` for the boundary.

## Quick Local Check

Run the local Context Health Doctor against a selected repository or folder:

```bash
PYTHONPATH=src python3 -m ctxgov.cli doctor --path /path/to/repo --output .ctxgov/health
```

The command reads user-selected local files and writes derived artifacts under
`.ctxgov/health`. It does not write target repo files, call models or
providers, execute runtimes or adapters, or promote memory.

For a bundled sample repo:

```bash
PYTHONPATH=src python3 -m ctxgov.cli doctor \
  --path fixtures/v0.6.2-context-health-doctor/sample-repo \
  --output /tmp/ctxgov-health \
  --include-report
```

For the companion benchmark skeleton:

```bash
git clone https://github.com/ctxgov/agent-context-evals
cd agent-context-evals
python3 baselines/regex_baseline.py --cases data/cases.jsonl --output reports/regex-baseline-results.jsonl
python3 ctxgov_adapter/run_ctxgov.py --cases data/cases.jsonl --output reports/ctxgov-adapter-results.jsonl
python3 scoring/score_findings.py --labels data/labels.jsonl --predictions reports/ctxgov-adapter-results.jsonl
```

## Public-Safe Evidence

The bundled Context Health Doctor sample shows stale, conflicting, unsupported,
unsafe, and hidden-failure context in a local fixture. It is a report-shape and
workflow example, not a benchmark result.

Inspect:

- `fixtures/v0.6.2-context-health-doctor/sample-repo/`
- `fixtures/v0.6.2-context-health-doctor/example-context-health-report.json`
- `release/v0.6.3/RELEASE_NOTES.md`
- `release/v0.6.3/github-release.md`
- `docs/project-page-and-demo-2026-06-03.md`
- `docs/research-engineering-hiring-packet.md`
- `docs/linkedin-and-outreach-pack-2026-06-03.md`
- `https://github.com/ctxgov/agent-context-evals`

## Claim Boundaries

Allowed wording:

- CtxGov is a local context-health evaluator for AI-agent workflows.
- CtxGov helps reviewers inspect stale, conflicting, unsupported, unsafe, or
  failure-residue context before agent execution.
- Current examples are local, synthetic or sanitized, and release-gated by
  claim boundaries.

Do not claim:

- benchmark or leaderboard results
- security completeness or vulnerability-scanner coverage
- hallucination prevention
- model reliability or coding-performance improvement
- universal provider, framework, memory-backend, or agent-harness compatibility
- automatic remediation, target repository writes, or autonomous execution
- stable Memory Governance Protocol status

## Release Status

The prepared public-surface cleanup release is `v0.6.3`. It is a GitHub source
release draft for clearer CtxGov positioning, release integrity, and local
companion-eval materials. It does not publish a new package or claim a public
benchmark result.

## Provenance

CtxGov was previously developed under the `ctxvault` namespace. Historical
paths, schemas, fixtures, release artifacts, and internal identifiers may still
contain that name when changing them would break provenance. Public positioning
should use CtxGov first and link to `docs/provenance.md` for legacy-name
context.
