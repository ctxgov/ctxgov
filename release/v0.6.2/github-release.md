# v0.6.2: Context Health Doctor

Subtitle: offline context contracts and public-safe OSS evidence receipts.

CtxVault now includes a local Context Health Doctor that shows what AI-facing
context is stale, conflicting, unsupported, or unsafe before it reaches agents.

Use it to scan a local repo, folder, or file:

```bash
PYTHONPATH=src python3 -m ctxvault.cli doctor --path /path/to/repo --output .ctxvault/health
```

The doctor writes a claim/context/memory/action health report plus local
receipts under `.ctxvault/health`. The default CLI output is compact JSON; add
`--include-report` when you want the full report in stdout.

This first wave is intentionally narrow:

- scans local files selected by the user
- writes derived health reports and receipts under `.ctxvault/health`
- records rollback delete paths for generated artifacts
- does not write target repo files
- does not call models or providers
- does not execute runtimes or adapters

Context Contract SDK backs the report vocabulary. Public-safe OSS evidence
receipts show the same claim-boundary discipline on downstream source checks.
They are supporting proof, not separate launch headlines.

This release does not claim security guarantees, benchmark performance,
universal compatibility, stable protocol status, or automatic remediation.
