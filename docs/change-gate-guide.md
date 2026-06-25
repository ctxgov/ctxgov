# Change Gate Public Guide

The public Change Gate command reads explicit local agent-facing files and prints
a semantic review artifact. It is read-only: no target write, `.ctxvault` write,
network/API call, provider/model call, scheduler, daemon, or policy enforcement.

Run on one repository:

```bash
ctxgov change-gate-check --root . --format summary
```

Diff two explicit local trees:

```bash
ctxgov change-gate-check --baseline-root examples/change-gate-public-preview/baseline --head-root examples/change-gate-public-preview/head --format summary
```

The semantic categories are authority, capability, scope, lifecycle,
sensitivity, and structural surface presence. The report is evidence for human
review, not an autonomous security or production-readiness decision.
