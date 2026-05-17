# CtxGov v0.6.2: Context Health Doctor

Subtitle: offline context contracts and public-safe OSS evidence receipts.

CtxGov now includes a local Context Health Doctor that shows what AI-facing
context is stale, conflicting, unsupported, or unsafe before it reaches agents.

## Try It

```bash
PYTHONPATH=src python3 -m ctxgov.cli doctor --path /path/to/repo --output .ctxgov/health
```

The default CLI output is compact JSON. Use `--include-report` to print the
embedded report to stdout.

## What It Does

Context Health Doctor scans a chosen local repository, folder, or file and
writes generated CtxGov health artifacts under the chosen output and rollback
paths.

It reports health across four authority layers:

- claim
- context
- memory
- action

It can flag stale version claims, conflicting instructions, duplicated rules,
private/public boundary risk, unsupported claims, missing raw refs,
over-compressed summaries, memory lifecycle gaps, action/publication language
without evidence, and hidden terminal failures.

## Boundaries

This release allows:

- local folder, repository, or file scan
- local report generation
- JSON, Markdown, report receipt, evidence manifest, and backup manifest output
- rollback through local delete paths

This release does not claim:

- security guarantees
- performance or benchmark results
- universal compatibility
- stable protocol status
- scanned source-file modification
- model, provider, browser, cloud, MCP, live runtime, or adapter calls
- auto-remediation
- memory promotion
- raw source snapshot backup

## Why The Result Is Credible

Context Contract SDK provides supporting vocabulary for claim, context, memory,
action, evidence, and rollback fields.

Public-safe OSS evidence receipts show the same claim-boundary discipline on
downstream source checks. They are supporting proof, not separate launch
headlines.
