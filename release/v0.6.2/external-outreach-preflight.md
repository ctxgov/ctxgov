# v0.6.2 External Outreach Preflight

Status: draft and approval matrix only. No external outreach has been
performed.

The outreach lane is separate from the package lane. It should not begin until
the intended user path is clear: GitHub source checkout only, TestPyPI preview,
or official PyPI install.

## No-Approval Work

These actions are local and reversible:

- Define outreach channels and approval requirements.
- Draft exact copy that stays inside the v0.6.2 Context Health Doctor boundary.
- Define a response policy for package, security, compatibility, benchmark,
  stable-protocol, and roadmap questions.
- Keep maintainer outreach blocked unless separately approved.
- Keep social posts blocked unless channel, account, copy, and rollback are
  approved.

## Channel Options

### Option A: GitHub Release Only

Use the existing GitHub Release as the only public announcement surface.

Pros:

- Already published and verified.
- Lowest risk of over-claiming or creating unsupported expectations.
- No new channel/account rollback problem.

Cons:

- Limited reach.
- Users may not discover the release without package or social distribution.

Recommendation: current default until package preflight is approved.

### Option B: Package-First Announcement

Publish package artifacts first, verify clean install, then announce with an
install command and the GitHub Release link.

Pros:

- Gives users a concrete path after they see the announcement.
- Reduces support friction.
- Makes the claim easier to test: install, run doctor, inspect report.

Cons:

- Depends on package registry approval and successful package smoke.
- Requires package rollback policy before outreach.

Recommendation: best next public outreach sequence after TestPyPI/PyPI
decisions are made.

### Option C: Technical Article

Publish a short technical note explaining Context Health Doctor and the claim,
context, memory, action authority layers.

Pros:

- Fits the project better than promotional copy.
- Can explain why schema-valid is not authority-valid.

Cons:

- Easy to drift into roadmap language if not tightly reviewed.
- Needs exact copy approval and correction/rollback plan.

Recommendation: good second wave after package/install path is clear.

### Option D: Social Post

Post a short announcement to a selected social channel.

Pros:

- Fast reach.
- Can point directly to the GitHub Release.

Cons:

- Highest risk of compressed over-claiming.
- Edits/deletions may not fully remove cached or quoted claims.

Recommendation: defer until package path and exact copy are approved.

### Option E: Maintainer Outreach

Contact maintainers of downstream OSS projects or projects mentioned in case
study material.

Pros:

- Could produce concrete feedback.

Cons:

- Easy to imply evaluation, endorsement, compatibility, or maintainer
  relationship.
- Requires per-target copy and response policy.

Recommendation: do not do this for v0.6.2. Treat it as a later dedicated lane.

## Draft Copy

Short GitHub/package announcement draft:

> CtxVault v0.6.2 adds Context Health Doctor: a local scan that reports stale,
> conflicting, unsupported, or unsafe AI-facing context across claim, context,
> memory, and action layers before it reaches agents. It writes generated
> reports and rollback receipts under the chosen output path. It does not
> modify scanned source files, call models/providers, fetch the network, or run
> adapters.

Technical article headline draft:

> Context Health Doctor: checking AI-facing context before agents consume it

Technical article summary draft:

> v0.6.2 focuses on a local report path for context authority. The report
> separates claim, context, memory, and action findings, records evidence refs,
> and keeps rollback delete paths visible for generated artifacts.

## Response Policy

If asked about security:

- Say it is not a security scanner or security guarantee.
- Point to local context-health findings and explicit non-claims.

If asked about benchmarks or performance:

- Say no benchmark, leaderboard, or performance improvement is claimed.

If asked about compatibility:

- Say v0.6.2 has local Python tests and a local CLI path; it does not claim
  universal runtime/provider/tool compatibility.

If asked about package install:

- Answer only with the approved package path. If no package registry release is
  approved, use the GitHub source checkout command from the release.

If asked about roadmap:

- Avoid future promises. Discuss only current release artifacts and explicit
  non-claims.

## Required Approval Before Outreach

Outreach requires explicit approval of:

- channel and account
- exact copy
- links
- whether package install can be mentioned
- response policy
- rollback/correction action
- whether maintainer outreach is allowed at all

