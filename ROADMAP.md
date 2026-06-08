# CtxGov Release Boundary

This repository does not publish future plans. Public documentation should
describe current shipped artifacts, current release boundaries, and explicit
non-claims.

For the current public surface, start with:

- `README.md`
- `release/v0.6.13/RELEASE_NOTES.md`
- `release/v0.6.13/publication-intent.json`
- `release/v0.6.12/RELEASE_NOTES.md`
- `release/v0.6.11/RELEASE_NOTES.md`
- `release/v0.6.11/github-release.md`
- `release/v0.6.11/self-audit-public-report/`
- `release/v0.6.10/ascr-aligned-evidence-update/`
- `release/v0.6.9/memory-xray-public-evidence-preview/`

Public copy must avoid:

- private planning document names or summaries
- private repository paths or local machine paths
- roadmap promises
- promotional adoption claims
- package publication claims unless a package receipt exists
- external outreach claims unless an outreach receipt exists
- benchmark, security, reliability, compatibility, stable-protocol, or
  automatic-remediation claims

The current claim boundary is agent context health / memory governance report
shape plus ASCR-aligned evidence. v0.6.13 records the owner-approved minimal
public release path for auto-publish research. v0.6.12 adds optional live-link
verification. v0.6.11 adds public-surface hardening, self-audit,
public-surface CI, and deterministic public-example preview rendering without
modifying scanned source files, calling models or providers, executing
runtimes, publishing packages, or promoting memory.
