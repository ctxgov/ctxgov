# CtxGov Release Boundary

This repository does not publish future plans. Public documentation should
describe current shipped artifacts, current release boundaries, and explicit
non-claims.

For the current public surface, start with:

- `README.md`
- `release/v0.6.2/RELEASE_NOTES.md`
- `release/v0.6.2/github-release.md`
- `release/v0.6.2/publication/v062-publication-receipt-2026-05-16.json`

Public copy must avoid:

- private planning document names or summaries
- private repository paths or local machine paths
- roadmap promises
- promotional adoption claims
- package publication claims unless a package receipt exists
- external outreach claims unless an outreach receipt exists
- benchmark, security, reliability, compatibility, stable-protocol, or
  automatic-remediation claims

The v0.6.2 claim boundary is Context Health Doctor: a local scan that writes
generated CtxGov health artifacts and rollback receipts without modifying
scanned source files, calling models or providers, executing runtimes, fetching
the network, or promoting memory.
