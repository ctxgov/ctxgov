# CtxGov v0.9.0 State Of Agent Context

This report is a read-only semantic inventory over selected public OSS
repositories at pinned commits. It records local observations about
agent-facing context surfaces; it is not a benchmark, security review,
compatibility result, endorsement, or production-readiness claim.

- Report ID: `soc_3464617b59c82591`
- Checked at: `2026-06-24T00:00:00Z`
- Project count: `8`
- Runtime boundary: no provider/model calls, no API calls, no target writes, no package publication.

| Project | Pinned Ref | Surfaces | Surface Kinds | Highest Authority | Capabilities | Scopes | Sensitivity |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| mem0 | `1678e682ee70` | 72 | `agent_instruction`:1, `claude_instruction`:1, `mcp_config`:4, `readme`:25, `skill`:41 | `override` | `delete`, `deploy`, `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `system`, `user` | `internal`:48, `public`:16, `sensitive`:8 |
| cline | `864419d8b0c2` | 70 | `agent_instruction`:2, `claude_instruction`:1, `cline_rule`:13, `github_copilot_instruction`:1, `mcp_config`:3, `readme`:46, `skill`:4 | `override` | `delete`, `deploy`, `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `session`, `system`, `user`, `workspace` | `internal`:53, `public`:14, `sensitive`:3 |
| langgraph | `8c9d59c84245` | 15 | `agent_instruction`:1, `claude_instruction`:1, `readme`:13 | `review_required` | `delete`, `deploy`, `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `user` | `internal`:4, `public`:11 |
| graphiti | `413b9b2e140e` | 13 | `agent_instruction`:1, `claude_instruction`:1, `mcp_config`:1, `readme`:10 | `override` | `delete`, `deploy`, `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `system`, `user` | `internal`:9, `public`:4 |
| smolagents | `526069c1ead9` | 7 | `agent_instruction`:1, `readme`:6 | `block` | `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `user` | `internal`:4, `public`:2, `restricted`:1 |
| continue | `d0a3c0b626b5` | 31 | `agent_instruction`:1, `readme`:28, `skill`:2 | `override` | `delete`, `deploy`, `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `system`, `user` | `internal`:27, `public`:4 |
| aider | `5dc9490bb35f` | 5 | `readme`:5 | `block` | `inform`, `network`, `read`, `write` | `project` | `internal`:2, `public`:3 |
| autogen | `027ecf0a379b` | 51 | `github_copilot_instruction`:1, `readme`:50 | `override` | `delete`, `deploy`, `execute`, `inform`, `network`, `publish`, `read`, `write` | `project`, `system`, `user` | `internal`:34, `public`:14, `restricted`:1, `sensitive`:2 |

## Reproduce

Use local clones at the listed pinned refs, then run:

```bash
ctxgov change-gate-check --root /path/to/local/repo --format summary
```

The checked-in per-project receipts omit local filesystem paths and raw source content.
