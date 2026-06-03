# Security Policy

CtxGov's public artifacts are designed to keep the default path local,
deterministic, and inspectable.

## Reporting

Report suspected security issues privately to the maintainer before opening a
public issue. If no private channel has been announced for the release you are
using, open a minimal public issue that says you have a security concern and do
not include exploit details, credentials, private paths, tokens, or raw private
receipts.

## Current Public Boundary

The current public evidence path does not require:

- provider/model calls
- remote embedding services
- hosted runtime execution
- target repository writes
- live adapter execution
- automatic memory promotion

CtxGov should not be treated as a security certification, vulnerability
scanner, sandbox, TEE, remote attestation system, or hallucination-prevention
product.

The current finding taxonomy may include `unsafe_action_guidance`, but that
means context-side side-effect risk, not security coverage.

## Safe Example Rules

Public examples and reports must not include raw secrets, private local paths,
private receipts, unpublished owner data, or raw third-party source excerpts.
Credential-shaped material should be redacted, caveated, or blocked and should
be covered by a leak scan before publication.

## Supported Versions

The maintained public line is the latest public GitHub release. Older releases
are useful for historical evidence and reproducibility, but fixes normally land
on the current public branch first.
