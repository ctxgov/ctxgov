# CtxGov 60-Second Demo Script

Status: local capture script. This is not a hosted demo, benchmark result,
security claim, provider compatibility claim, or public release proof.

## Frame 1: Bad Context Enters The Agent

Show a small sample repo with these files side by side:

- `README.md`: "v0.6.3 is released and safe to publish."
- `release-notes.md`: "External deploy and public benchmark remain pending."
- `AGENTS.md`: "Run the deploy script after tests pass."
- `terminal.log`: "FAILED test_release_url_not_404"

Voiceover:

`Agents often inherit context from docs, rules files, release notes, and logs. If those files disagree, the agent starts from a bad premise.`

## Frame 2: CtxGov Reads AI-Facing Context

Show the report starting with:

- case id
- files inspected
- side-effect boundary
- claim boundary

Voiceover:

`CtxGov evaluates the context before execution. It does not run the agent, call a model, deploy, or write the target repo.`

## Frame 3: Findings

Show a table:

| Finding | Evidence Span | Next Action |
| --- | --- | --- |
| `stale_claim` | `v0.6.3 is released and safe to publish` | Downgrade until release URL exists. |
| `conflicting_policy` | `External deploy ... remain pending` vs `Run the deploy script` | Block deploy guidance. |
| `unsupported_release_claim` | `test_release_url_not_404` | Create release or remove link. |
| `hidden_terminal_failure` | `FAILED test_release_url_not_404` | Preserve failure in handoff. |

Voiceover:

`Each finding points to an evidence span, not a vague warning.`

## Frame 4: Safe End State

Show corrected handoff:

- release copy says "prepared draft" instead of "released"
- deploy instruction is blocked pending approval
- terminal failure is visible
- release checklist remains open

Voiceover:

`The goal is not automatic remediation. The goal is to stop bad context before it becomes agent behavior.`

## Capture Notes

- Keep total runtime under 60 seconds.
- Use the demo panel in `docs/index.html` as the initial visual.
- Use 1440x900 or 1280x720.
- End on the limitation line:
  `No security guarantee. No public benchmark claim. No provider/model call. No target write.`
