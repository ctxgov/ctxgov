# Owner Approval Minimal Matrix

Goal: keep human review focused on decisions that change legal, public,
reputational, or irreversible state. Everything else should be agent-executed
when the public evidence release-pack check passes.

## Approval Principle

Owner approval is required only when an action:

- changes public state
- changes legal/licensing posture
- expands a public claim
- contacts an external person or organization
- writes to a provider/model, memory backend, package registry, or external
  target
- publishes material that could expose private traces, fixture internals, tokens,
  private targets, or unpublished reviewer details

Local preparation, local checks, local copy edits inside the approved boundary,
and local publication dry-runs do not need owner review.

## Single Human Gate

Recommended owner review should be one short approval gate:

1. Approve release scope:
   `agent context health / memory-governance report-shape release`.
2. Approve claim boundary:
   no public benchmark, security, provider/model compatibility, adoption,
   package, hosted runtime, live adapter, public spec-stability, or CLI beta
   claim.
3. Choose license:
   recommendation is Apache-2.0 for patent clarity and enterprise trust; MIT is
   the simpler fallback if maximum casual reuse matters more.
4. Approve public write bundle:
   apply the prepared patch in `ctxgov/ctxgov`, push or open PR, publish GitHub
   release notes, update Pages, and fetch-verify the live page.
5. Decide outreach:
   recommendation is no proactive outreach until the live page and release URL
   are verified; passive reviewer packet may be published as part of the release.

## Requires Owner Approval

| Decision | Why owner approval is required | Recommended default |
| --- | --- | --- |
| License selection | Legal and downstream reuse posture. | Apache-2.0. |
| Public release scope | Defines what the project is allowed to claim. | Report-shape/readiness only. |
| Public write bundle | Push, PR, release, Pages, and public repo metadata change public state. | Approve as one bundled action after checks pass. |
| Any claim expansion | Benchmark, security, provider compatibility, adoption, package, hosted runtime, live adapter, and spec claims raise the evidence bar. | Do not approve for v0.6.9. |
| Publishing demo/GIF/media | Public asset may leak private context or imply unsupported claims. | Publish only sanitized side-by-side demo. |
| Outreach or reviewer contact | External communication creates social and reputational state. | Defer proactive outreach. |
| Package registry or hosted runtime | Creates distribution/runtime expectations. | Defer. |
| Provider/model or memory-backend action | Mutates external/model/backend state. | Block. |

## Does Not Require Owner Approval

| Action | Why it does not need owner review |
| --- | --- |
| Local README/homepage/release-note copy edits | No public state changes if kept local and inside approved boundary. |
| Local evidence-pack edits | Public-safe structure and boundary are enforced by checks. |
| Local claim lint, leak scan, link check, and unit tests | Verification only; no external side effect. |
| Local static page preview | No public state change. |
| Local demo draft using sanitized sample context | Draft asset only; publish still uses the public write bundle. |
| Applying the prepared patch to a local clean public checkout without push | Preparation only; public state changes only at PR/push/release time. |
| Mechanical GitHub release body assembly from approved `github-release.md` | No judgment needed if content is unchanged; publishing still needs the bundle approval. |
| Metadata copy from `docs/public-repo-metadata.md` | No separate content approval if included in the public write bundle. |

## Agent Stop Conditions

The agent must stop and ask the owner if any of these occur:

- `scripts/check_public_evidence_release_pack.py` fails
- a new public claim category is introduced
- a private path, private trace, raw fixture detail, token, or private target may
  be exposed
- a license must be chosen or changed
- a public GitHub/Pages/release/package/metadata write is about to happen
- outreach, reviewer contact, or announcement is about to happen
- provider/model, memory-backend, external target, package registry, or hosted
  runtime state would be touched

## Minimal Approval Text

The owner can approve the full public-safe release with one message:

`Approve v0.6.9 public-safe release scope; use Apache-2.0; apply the prepared patch to ctxgov/ctxgov; publish GitHub release and Pages after checks pass; no proactive outreach.`

If the owner wants MIT instead:

`Approve v0.6.9 public-safe release scope; use MIT; apply the prepared patch to ctxgov/ctxgov; publish GitHub release and Pages after checks pass; no proactive outreach.`
