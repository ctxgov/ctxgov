# CtxGov

Status: v0.6.2 public release artifact. Current package-preparation surface:
Context Health Doctor.

Know what your AI tools see.

CtxGov is a local context-governance toolkit for AI work. The v0.6.2 release
focuses on one public path: a local Context Health Doctor that reports stale,
conflicting, unsupported, or unsafe AI-facing context before it reaches agents.

## Context Health Doctor

Scan a local repository, folder, or file and write a claim/context/memory/action
health report:

```bash
PYTHONPATH=src python3 -m ctxgov.cli doctor --path /path/to/repo --output .ctxgov/health
```

The doctor reads local files selected by the user. It writes generated CtxGov
artifacts under the chosen output and rollback paths, including JSON, Markdown,
run receipt, evidence manifest, backup manifest, and index files. It does not
modify scanned source files, call models or providers, execute runtimes or
adapters, fetch the network, or promote memory. Add `--include-report` to print
the full JSON report to stdout.

## Report Layers

| Layer | What the report checks |
| --- | --- |
| Claim | Unsupported public, security, performance, compatibility, endorsement, stable-protocol, or target-write claims. |
| Context | Stale version claims, conflicting instructions, duplicated rules, missing raw refs, and hidden terminal failures. |
| Memory | Memory-like content without source, lifecycle, deletion, or rollback fields. |
| Action | Publication or action language without evidence, approval, and rollback. |

## v0.6.2 Scope

Included in this release:

- `doctor --path` for local Context Health Doctor scans.
- `schemas/json/ctxvault-context-health-report-v0.schema.json`.
- `fixtures/v0.6.2-context-health-doctor/` with sanitized sample and clean
  repos.
- Local receipts with side-effect flags and rollback delete paths.
- Context Contract vocabulary as supporting report structure.
- Public-safe OSS evidence receipts as supporting proof of claim-boundary
  discipline.

Not included or claimed:

- security guarantee
- benchmark, performance, reliability, or coding-improvement claim
- universal compatibility claim
- stable protocol claim
- automatic remediation
- target repository source-file modification
- model, provider, browser, cloud, MCP, live runtime, or adapter execution
- package registry publication
- external outreach

## Verify Locally

```bash
python3 -m pytest tests/test_context_health_doctor.py tests/test_cli.py
```

The focused tests cover schema validation, sample findings, clean-repo allowed
state, generated reports and receipts, rollback paths, missing-path fail-closed
behavior, generated `.ctxgov`/`.ctxvault` exclusion, and legacy `doctor --root`
compatibility.

## Release Artifacts

- `release/v0.6.2/RELEASE_NOTES.md`
- `release/v0.6.2/github-release.md`
- `release/v0.6.2/publication/v062-publication-receipt-2026-05-16.json`
- `src/ctxgov/context_health.py`
- `src/ctxgov/cli.py`
- `tests/test_context_health_doctor.py`
