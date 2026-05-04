# Context Injection M1 Fixtures

This directory contains the sanitized source inputs for the Context Injection M1
golden path:

- `project-docs/`: project/repo documentation inputs
- `sessions/`: normalized session-history input
- `knowledge/`: local knowledge-source input
- `review/`: deterministic workstream and memory review candidates

Generate the projected outputs and projection receipts with:

```bash
python3 scripts/run_context_injection_m1_golden_path.py --root /tmp/ctxvault-m1-context-injection
```

The command writes:

- `/tmp/ctxvault-m1-context-injection/exports/AGENTS.md`
- `/tmp/ctxvault-m1-context-injection/exports/CLAUDE.md`
- `/tmp/ctxvault-m1-context-injection/exports/workstreams/context-injection-m1.md`
- `/tmp/ctxvault-m1-context-injection/artifacts/projection-receipts/*.json`

Rejected and unreviewed fixture candidates are retained in the vault as
review-state evidence, but they must not appear in projected outputs.
