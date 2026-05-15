# mem0 Public Case Study Deep Dive

Status: public owner-approved data extract.

## Positioning

CtxVault's core positioning was already governed context projection and
receipt-backed AI work context. The current task is distribution: make that
definition visible in the first public screen, evidence pack, case study, demo,
and article so it is not mistaken for generic persistent memory or RAG.

## Source-Fact Recheck

Checked at `2026-05-15T11:57:53Z` against primary GitHub sources.

- Repo: `mem0ai/mem0`
- Public URL: `https://github.com/mem0ai/mem0`
- GitHub description: `Universal memory layer for AI Agents`
- License: `Apache-2.0`
- Default branch: `main`
- Stars: `55780`
- Forks: `6345`
- Pinned commit:
  `70bc9e51d57fe005d02b7b6d81b56476bade3cb3`
- Pinned commit URL:
  `https://github.com/mem0ai/mem0/commit/70bc9e51d57fe005d02b7b6d81b56476bade3cb3`

The source-fact recheck describes current public repository metadata and the
pinned evaluation commit. It does not claim endorsement, compatibility,
performance, correctness, or security. It does not certify mem0 behavior.

## Read-Only Governance Metrics

- Candidate context count: `2056`
- Surfaced candidate count: `839`
- Selected count: `478`
- Caveated count: `263`
- Blocked count: `98`
- Omitted count: `1217`
- Unsupported count: `93`
- Evidence precision: `0.570`
- Omitted raw visibility: `0.025`
- Omitted sample-cap compliance: `1.000`
- Projection portability: `1.000`
- CtxVault evaluation rollback confidence: `1.000`

## Omitted Evidence Analysis

The source receipt records 30 omitted samples and a total omitted count of
`1217`. It does not expose the full omitted-ref list. Therefore the honest
public candidate claim is sample distribution, not full distribution.

Omitted sample distribution:

- `other`: `10`
- `skill_like_procedure`: `20`

This is enough to show that omitted refs are visible up to the receipt sample
cap. It is not enough to claim full omitted-distribution coverage.

## Credential Boundary

Credential-shaped public path refs are handled as path-only evidence:

- `docs/images/platform/api-key.png`: blocked as a credential-shaped path marker.
- `examples/mem0-demo/.env.example`: caveated as public but requiring scope or
  generated-artifact caveat.

No raw secret values are included in the public candidate extract.

## Claim Lint

Allowed:

- read-only governance evaluation
- aggregate counts and path-only public refs
- selected, caveated, blocked, omitted, unsupported, side-effect, and rollback
  evidence
- publication gates and limitations

Not allowed:

- benchmark or leaderboard result
- target project quality, performance, correctness, compatibility, or security
  judgment
- provider/model execution
- runtime or adapter compatibility
- target write support
- stable protocol or stable MGP
- endorsement by mem0 maintainers

## Public Extract Decision

Do not publish the raw source receipt as-is. It contains local output, private
temporary target, and local rollback paths.

The sanitized public data extract is approved for public OSS release because it
contains only aggregate metrics, primary-source public facts, path-only public
refs, claim boundaries, and leak-scan status.

Publication target: GitHub public repository `ctxvault/ctxvault`, branch `main`.
Rollback path: revert the publication commit or restore the previous `main`
commit recorded in the publication receipt.
