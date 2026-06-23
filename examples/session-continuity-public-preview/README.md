# Session Continuity Public Preview Synthetic Demo

Status: public-safe synthetic fixture for local v0.7.0 package review.

Run from the repository root:

```bash
ctxgov continuity compile examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov continuity render examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
ctxgov continuity apply --mode dry-run examples/session-continuity-public-preview/saved-goal-trace.synthetic.json
```

Expected behavior:

- reads only the explicit saved trace path;
- prints local JSON or Markdown output;
- writes nothing in dry-run mode;
- writes only under a sandbox directory in sandbox mode;
- performs no provider/model call, memory-backend write, target repository write, package publication, or outreach.
