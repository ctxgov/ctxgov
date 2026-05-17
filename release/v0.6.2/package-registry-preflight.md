# v0.6.2 Package Registry Preflight

Status: TestPyPI publication and clean install smoke completed. Official PyPI
publication has not run.
The first TestPyPI workflow attempt is recorded in
`testpypi-publishing-attempt-2026-05-17.json`; it was blocked by missing
TestPyPI trusted-publisher configuration, after the build and metadata checks
passed. That attempt used the now-retired `ctxvault` package name.
The ctxgov TestPyPI publication is recorded in
`testpypi-publishing-success-2026-05-17.json`; it published
`ctxgov==0.6.2.post1` to TestPyPI and clean install smoke passed.

Selected package distribution: `ctxgov`. Selected package version:
`0.6.2.post1`. The GitHub Release and `v0.6.2` tag remain unchanged; the
package registry path uses a package-only post release so the existing GitHub
Release does not need to move again.

This lane prepares CtxGov v0.6.2 for an official `0.6.2.post1` PyPI release.
TestPyPI is preview state only; official install claims remain blocked until
PyPI publication and clean PyPI install smoke pass.

## Latest Execution State

- Public `main` contains the manual trusted-publishing workflow and package
  metadata for `ctxgov==0.6.2.post1`.
- The GitHub package source is `ctxgov/ctxgov`.
- The existing GitHub Release and `v0.6.2` tag were not moved.
- The previous `ctxvault` workflow was manually run against TestPyPI from
  `main`.
- The ctxgov workflow was manually run against TestPyPI from `main`.
- Artifact build, distribution metadata checks, and TestPyPI publication passed.
- Clean TestPyPI install smoke passed for `ctxgov==0.6.2.post1`.
- Official PyPI publication is blocked until the `ctxgov` PyPI organization or
  owner path and the PyPI pending publisher are configured.
- GitHub Release, package tag, and announcement drafts are prepared but not
  published.
- No PyPI upload, package-first announcement, social post, article, maintainer
  outreach, issue, or pull request outreach has been performed.

## No-Approval Work

These actions are local and reversible:

- Add conservative package metadata in `pyproject.toml`.
- Build a local wheel without dependency resolution.
- Install the local wheel into a temporary virtual environment.
- Run `ctxgov doctor` from the installed console script against the v0.6.2
  sample fixture.
- Verify missing-path fail-closed behavior from the installed console script.
- Scan package-facing release artifacts for private planning markers and
  future-plan wording.
- Record package publication as blocked until a registry lane is approved.

## Local Build Command

```bash
python3 -m pip wheel . --no-deps --no-build-isolation -w /private/tmp/ctxgov-v062-package-wheelhouse
```

The command intentionally avoids network dependency resolution. It validates
that the current source tree can produce an installable wheel in the local
environment. It is not a registry upload.

## Registry Options

### Option A: TestPyPI First, Then PyPI

Run the same wheel/install smoke locally, publish to TestPyPI, install from
TestPyPI in a clean environment, then approve a separate PyPI publication.

Pros:

- Exercises registry metadata and install path before the irreversible PyPI
  version is consumed.
- Keeps rollback clear: failed TestPyPI attempts do not consume the official
  PyPI version.
- Matches the project posture of converting uncertainty into auditable gates.

Cons:

- Adds one extra approval and verification step.
- TestPyPI does not perfectly mirror final user discovery on PyPI.

Recommendation: choose this for the first package publication.

### Option B: Direct PyPI Release

Publish `0.6.2.post1` directly to PyPI after local wheel smoke.

Pros:

- Fastest path to a public package.
- Avoids TestPyPI account/project setup if the PyPI project is already ready.

Cons:

- PyPI versions are effectively immutable. A bad upload requires yanking and a
  patch release instead of overwriting.
- Any metadata or README rendering issue becomes public immediately.
- Too much risk for the first package release of this project.

Recommendation: do not choose this for the first package publication.

### Option C: GitHub Packages Only

Publish the Python package to GitHub Packages or keep install instructions tied
to GitHub source.

Pros:

- Keeps package distribution near the source repository.
- Can be acceptable for internal or limited-preview consumers.

Cons:

- Poorer default Python package discovery than PyPI.
- Users may still expect PyPI.
- Does not remove the need for package metadata, install smoke, and rollback
  policy.

Recommendation: use only if the goal is a limited distribution preview.

### Option D: Source-Only Release

Keep v0.6.2 as a GitHub Release with source checkout instructions and do not
publish a package.

Pros:

- Lowest external state and rollback risk.
- Current GitHub Release already supports the documented `PYTHONPATH=src`
  command.

Cons:

- Higher friction for ordinary Python users.
- No registry-level install path.

Recommendation: acceptable if the immediate goal is release credibility rather
than package adoption.

## Publishing Mechanism Options

### Option A: PyPI Trusted Publishing

Use PyPI trusted publishing through a reviewed GitHub Actions workflow after
the TestPyPI lane passes.

Recommendation: best long-term mechanism because it avoids local long-lived
API tokens.

### Option B: Scoped PyPI API Token

Use a project-scoped token with a twine-based upload command.

Recommendation: acceptable only if trusted publishing is not available and the
token handling/rollback receipt is explicit.

### Option C: Username/Password Upload

Do not use this. It is weaker operationally and unnecessary.

## Required Approval Before Publish

Publishing requires explicit approval of:

- registry target
- package name ownership and account access
- publishing mechanism
- whether TestPyPI is mandatory
- PyPI account access or recovery path
- `ctxgov` organization approval state, if publishing under an organization
- final artifact hashes
- rollback policy: yank plus patch release, not overwrite
- exact release/install wording after registry publication
