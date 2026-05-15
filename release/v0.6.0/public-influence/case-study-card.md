# CtxVault mem0 Case Study Card

Status: public evidence surface.

## One-Line Story

CtxVault shows why an AI tool was allowed to see some context and not the rest.

## Case

- Subject: `mem0ai/mem0`
- Evaluation type: read-only governance evaluation
- Target writes: `false`
- Provider/model calls: `false`
- Runtime/adapter execution: `false`
- Benchmark claim: `false`

## Numbers

| Metric | Value |
| --- | ---: |
| Candidate refs | 2056 |
| Surfaced refs | 839 |
| Selected refs | 478 |
| Caveated refs | 263 |
| Blocked refs | 98 |
| Omitted refs | 1217 |
| Evidence precision | 0.570 |
| Projection portability | 1.000 |

## Message

Memory systems optimize recall. CtxVault governs influence.

The important question is not only what the AI tool remembers. It is what the
operator allowed into the next AI-facing packet, what was omitted, what was
blocked, and how that choice can be audited or rolled back.

Then what: when context gets messy, CtxVault gives reviewers a receipt instead
of a hunch. The public mem0 case shows the governance shape directly: `2056`
candidate refs became `478` selected refs, with `263` caveated, `98` blocked,
and `1217` omitted.

## Link

`https://github.com/ctxvault/ctxvault/tree/main/release/v0.6.0/public-influence`
