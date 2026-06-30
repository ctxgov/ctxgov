# CtxGov v0.10.0

Your coding agent is reading more instructions than you think.

This release adds `CtxGov Conflict Map`, a local read-only preflight for agent
context collisions.

```bash
ctxgov context-conflicts --root . --format summary
```

Use it to review which AGENTS.md, CLAUDE.md, Copilot instructions, README docs,
and MCP boundaries appear to collide before the next agent run.

## What Ships

- Conflict Map CLI: `ctxgov context-conflicts`.
- Conflict Edition report: `release/v0.10.0/state-of-agent-context-conflicts/`.
- Source/evidence tiering for instruction/config vs README/docs evidence.
- Deterministic adjudication artifacts: `ADJUDICATION.md` and
  `adjudication-sample.json`.
- Existing local public surfaces from v0.7.0 through v0.9.0 remain available.

## Boundary

Findings are review-needed declared instruction-collision signals. They are not
security findings, benchmark results, runtime precedence truth, project-quality
rankings, compatibility results, endorsements, production-readiness claims, or
autonomous remediation.

No provider/model calls, network calls by the report builder, target writes,
schedulers, daemons, package publication automation, or outreach are included in
the package behavior.
