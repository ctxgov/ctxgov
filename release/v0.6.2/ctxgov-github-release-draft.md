# v0.6.2.post1: Context Health Doctor

Status: blocked draft. Do not publish this GitHub Release until an official
PyPI publication receipt and clean PyPI install smoke exist.

CtxGov v0.6.2.post1 packages Context Health Doctor, a local scan that reports
stale, conflicting, unsupported, or unsafe AI-facing context across claim,
context, memory, and action layers before it reaches agents.

Planned install path after official PyPI verification:

```bash
python -m pip install ctxgov==0.6.2.post1
ctxgov doctor --path /path/to/repo --output .ctxgov/health
```

The doctor reads local files selected by the user and writes generated reports,
receipts, evidence manifests, backup manifests, and rollback delete paths under
the chosen output and rollback paths. It does not modify scanned source files,
call models or providers, fetch the network, execute runtimes or adapters, or
promote memory.

This release does not claim security guarantees, benchmark results, performance
improvements, universal compatibility, stable protocol status, automatic
remediation, or maintainer endorsement.

Context Contract vocabulary and public-safe OSS evidence receipts are included
as supporting proof of claim-boundary discipline. They are not separate launch
headlines.

Publication gate:

- TestPyPI publication and install smoke: passed.
- Official PyPI publication: blocked until PyPI organization/project publisher
  configuration and owner approval.
- External announcement: blocked until official PyPI install smoke passes.
- Maintainer outreach: blocked for v0.6.2.
