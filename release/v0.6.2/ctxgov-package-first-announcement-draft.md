# CtxGov Package-First Announcement Draft

Status: blocked draft. Do not post externally until official PyPI publication
and clean PyPI install smoke are recorded.

Draft copy:

> CtxGov v0.6.2.post1 adds Context Health Doctor: a local scan that reports
> stale, conflicting, unsupported, or unsafe AI-facing context across claim,
> context, memory, and action layers before it reaches agents.
>
> After official PyPI verification:
>
> `python -m pip install ctxgov==0.6.2.post1`
>
> `ctxgov doctor --path /path/to/repo --output .ctxgov/health`
>
> The doctor writes generated reports and rollback receipts under the chosen
> output paths. It does not modify scanned source files, call models/providers,
> fetch the network, run adapters, or promote memory.

Allowed links after publication:

- GitHub repository: `https://github.com/ctxgov/ctxgov`
- GitHub Release: `https://github.com/ctxgov/ctxgov/releases/tag/v0.6.2.post1`
- PyPI project: `https://pypi.org/project/ctxgov/`

Do not include:

- security guarantee
- benchmark or performance claim
- universal compatibility claim
- stable protocol claim
- automatic remediation claim
- maintainer endorsement
- downstream OSS evaluation claim
- roadmap promise

Response policy:

- If asked about security, say this is not a security scanner or guarantee.
- If asked about benchmarks, say no benchmark or performance result is claimed.
- If asked about compatibility, say v0.6.2.post1 provides a local Python CLI
  path and does not claim universal provider/runtime/tool compatibility.
- If asked about roadmap, discuss only current release artifacts and explicit
  non-claims.
- If asked about maintainers of other projects, say no maintainer outreach or
  endorsement is part of v0.6.2.
