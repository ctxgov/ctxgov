# State Of Agent Context: Conflict Edition

Which instruction wins when AGENTS.md, CLAUDE.md, README, and MCP disagree?

This report is a read-only declared-conflict map over selected public OSS
repositories at pinned commits. It records local observations about
agent-facing context surfaces; it is not a benchmark, security review,
runtime precedence result, compatibility result, endorsement, or
production-readiness claim.

- Report ID: `soc_conflict_6098a3b8c7176f99`
- Checked at: `2026-06-29T00:00:00Z`
- Project count: `20`
- Total surfaces: `1496`
- Total findings: `93`
- Source tiers: `instruction_or_config`:118, `other_context`:100, `readme_or_docs`:1278
- Evidence tiers: `instruction_config_only`:13, `mixed_instruction_config_and_readme_docs`:59, `mixed_with_readme_docs`:2, `other_context_only`:1, `readme_docs_only`:18
- Adjudication sample: `12` findings in `adjudication-sample.json` and `ADJUDICATION.md`
- Runtime boundary: no provider/model calls, no API calls, no network calls by the report builder, no target writes, no package publication.

| Project | Pinned Ref | Surfaces | High-Authority Surfaces | Findings | Precedence Declared | Finding Types |
| --- | --- | ---: | ---: | ---: | --- | --- |
| mem0 | `31cec11a7908` | 72 | 6 | 7 | yes | `approval_conflict`:1, `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| cline | `4175677e712e` | 72 | 22 | 7 | yes | `approval_conflict`:1, `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| langgraph | `d2f97191abc4` | 15 | 2 | 4 | no | `execution_conflict`:1, `precedence_missing`:1, `scope_conflict`:1, `target_write_conflict`:1 |
| graphiti | `b59d4ba01118` | 13 | 3 | 3 | yes | `network_conflict`:1, `scope_conflict`:1, `target_write_conflict`:1 |
| smolagents | `526069c1ead9` | 7 | 1 | 3 | no | `execution_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| continue | `d0a3c0b626b5` | 31 | 1 | 4 | yes | `approval_conflict`:1, `execution_conflict`:1, `network_conflict`:1, `target_write_conflict`:1 |
| aider | `5dc9490bb35f` | 5 | 0 | 1 | no | `approval_conflict`:1 |
| autogen | `027ecf0a379b` | 51 | 1 | 4 | yes | `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `sensitivity_boundary_conflict`:1 |
| crewai | `4379c4580479` | 95 | 2 | 6 | yes | `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| openhands | `b897ce421df0` | 32 | 1 | 4 | no | `network_conflict`:1, `publish_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| browser-use | `2454d3e25517` | 25 | 2 | 5 | yes | `execution_conflict`:1, `network_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| llama-index | `5891d5f4f3e9` | 685 | 0 | 5 | yes | `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| langchain | `1e35d8f7a988` | 28 | 3 | 2 | yes | `network_conflict`:1, `publish_conflict`:1 |
| mcp-servers | `b2a94a21a53f` | 11 | 3 | 4 | no | `execution_conflict`:1, `precedence_missing`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| openai-agents-python | `fea17ef5423f` | 51 | 2 | 6 | yes | `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| gemini-cli | `ae0a3aa7b928` | 40 | 8 | 6 | yes | `approval_conflict`:1, `execution_conflict`:1, `network_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| roo-code | `b867ec914575` | 64 | 37 | 6 | yes | `approval_conflict`:1, `execution_conflict`:1, `network_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| goose | `2cc1140dc1e8` | 36 | 10 | 5 | yes | `execution_conflict`:1, `network_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| opencode | `7077c70d6044` | 44 | 14 | 6 | yes | `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `scope_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |
| semantic-kernel | `dfc522722735` | 119 | 0 | 5 | yes | `execution_conflict`:1, `network_conflict`:1, `publish_conflict`:1, `sensitivity_boundary_conflict`:1, `target_write_conflict`:1 |

## Methodology And Limitations

CtxGov scans local checked-out source trees at pinned refs using declared-text
heuristics. It classifies detected surfaces into instruction/config,
README/docs, and other-context tiers before aggregating review-needed
instruction-collision signals.

README/docs evidence is lower-authority than explicit agent instruction
or config surfaces. A finding that includes README/docs text should be
treated as a caveated review prompt, not proof of active agent policy.

The fixed adjudication sample is deterministic and pathless. It separates
`accepted`, `needs_refinement`, and `false_positive` outcomes so external
messaging can avoid using lower-confidence rows as headline claims.

## Claim Boundary

Findings mean review-needed declared instruction conflicts. They do not
claim actual agent runtime behavior, hidden provider precedence, security
impact, or project quality.

## Reproduce

Use local clones at the listed pinned refs, then run:

```bash
ctxgov context-conflicts --root /path/to/local/repo --format summary
```

The checked-in per-project receipts omit local filesystem paths and raw source content.
