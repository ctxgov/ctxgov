# CtxGov v0.7.0 - Public-Only Session Continuity Package

Status: public package release notes for v0.7.0.

This release publishes a clean public-only CtxGov source package. The headline
public path is Session Continuity Sidecar, with Memory X-Ray L1 report-shape
evidence as supporting material.

## What Ships In The Public Package

- A minimal installable Python package named `ctxgov`, version `0.7.0`.
- A public CLI limited to:
  - `ctxgov continuity compile`
  - `ctxgov continuity render`
  - `ctxgov continuity apply --mode dry-run|sandbox`
  - `ctxgov memory-xray validate`
- A synthetic session-continuity fixture and local-only demo path.
- Memory X-Ray L1 public-safe report-shape examples.
- A public package check script for local smoke validation.

## Why It Matters

AI agents often continue work from saved traces, summaries, rule files, and
handoffs that may be stale, incomplete, or over-authoritative. This release
shows a narrow local path for turning an explicit saved trace into source-backed
continuity evidence before the next agent session acts on it.

The public claim is intentionally narrow: CtxGov can read a local saved trace,
compile a continuity sidecar, render a reviewable next-session packet, and build
a dry-run or sandbox-only apply result with explicit side-effect boundaries.

## Version Boundary

- Public product/package version for this release: `0.7.0`.
- Historical evidence artifacts are archive material and are not part of the
  v0.7.0 headline or public package narrative.
- Existing schema identifiers with the `ctxvault.*` prefix remain stable legacy
  contract strings and are not branding claims.

## Explicitly Not Claimed

- No public benchmark claim.
- No security, safety, or privacy certification.
- No provider/model compatibility claim.
- No package registry or PyPI publication claim.
- No hosted runtime claim.
- No adoption or community traction claim.
- No stable protocol or stable MGP claim.
- No provider/model call, memory-backend write, external target write, public
  issue/comment, outreach, scheduler, watch daemon, or long-running service.

## Reproduce Locally

After extracting the public-only package, run:

```bash
python3 scripts/run_public_package_checks.py
```

The check is local and deterministic. It validates the public CLI help, compiles
the synthetic trace, renders a Markdown packet, performs a dry-run apply, and
validates the Memory X-Ray L1 examples pack.

## Rollback

If the public copy overclaims or the package contains an unintended surface,
supersede this release pack and publish a corrected package. No provider/model
state, target repository state, memory-backend state, hosted runtime state,
scheduler, or outreach state is created by this package.
