# CtxGov v0.10.0 Release Notes

Your coding agent is reading more instructions than you think.

v0.10.0 makes `CtxGov Conflict Map` the primary public product point: a local,
read-only preflight for declared agent-context collisions before the next agent
run.

## What Is New

- `ctxgov context-conflicts --root . --format summary` maps declared
  instruction-collision signals across local agent-context surfaces.
- Conflict Map separates high-authority instruction/config evidence from
  lower-authority README/docs evidence.
- `release/v0.10.0/state-of-agent-context-conflicts/` publishes the Conflict
  Edition report, pathless per-project receipts, `manifest.json`,
  `ADJUDICATION.md`, and `adjudication-sample.json`.
- Public extraction now treats v0.10.0 as the current package version and keeps
  v0.7.0, v0.8.0, and v0.9.0 artifacts as supporting history.

## Main Question

Which instruction wins when AGENTS.md, CLAUDE.md, Copilot instructions, README
docs, and MCP boundaries disagree?

## Evidence Pack

- 20 selected public OSS repositories at pinned commits.
- 1,496 detected agent-context surfaces.
- 93 review-needed declared-conflict findings.
- 13 findings from instruction/config-only evidence.
- 80 findings that include README/docs or other-context evidence and must stay
  caveated.
- 12 deterministic adjudication samples: 2 accepted and 10 needs-refinement at
  candidate generation time.

These numbers are report evidence, not a benchmark, project-quality ranking,
security review, runtime precedence result, compatibility result, endorsement,
or production-readiness claim.

Findings are review prompts; they are not runtime precedence truth.

## Try It Locally

```bash
ctxgov context-conflicts --root . --format summary
```

The command reads local files and prints a review artifact. It does not call a
provider, call a model, fetch the network, execute a target repo, write target
files, start a scheduler, start a daemon, publish packages, or mutate external
state.

## Also Included

- Read-only semantic Change Gate.
- Session Continuity public preview commands.
- Memory X-Ray public example validation.
- Federation over explicit local repository paths.
- OSS Case Study Preview over saved local source excerpts.
- OSS raw telemetry methodology receipts without efficiency claims.
- Governance Replay over saved local traces.
- Fixture-based Forensics preview.
- Public Evidence Core contracts and explicit local evidence-store primitives.

## Claim Boundary

Allowed wording:

- review-needed declared instruction-collision signal;
- source/evidence-tiered local conflict map;
- read-only local preflight;
- pathless public OSS receipts at pinned commits.

Not claimed:

- security finding;
- benchmark result;
- runtime precedence truth;
- model/provider behavior;
- project quality ranking;
- compatibility result;
- production readiness;
- maintainer endorsement;
- autonomous remediation.
