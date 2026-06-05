# CtxGov Public Repo Metadata

Date: 2026-06-05
Status: public-surface metadata source. This file is not a release receipt,
benchmark result, security claim, package migration receipt, or compatibility
matrix.

## Repository Identity

Canonical public project name:

`CtxGov`

Recommended canonical public repository:

`ctxgov/ctxgov`

Current legacy compatibility namespace:

`ctxvault`

Use `docs/provenance.md` when archived paths, old release artifacts, package
names, CLI commands, schema ids, or immutable receipts still contain the legacy
namespace.

## GitHub Description

Preferred:

`Agent context health and ASCR-aligned memory governance for stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context.`

Shorter fallback:

`Find bad AI-facing context before agents act.`

## GitHub About

Preferred:

`CtxGov checks AI-facing project context for stale claims, conflicting instructions, unsupported release statements, unsafe action guidance, hidden failure residue, and memory-risk drift before agent execution.`

Shorter fallback:

`Agent context health / memory governance before agents act.`

## Homepage

Preferred:

`https://ctxgov.github.io/ctxgov/`

Use the repo URL only as a fallback. The homepage must not point at a package,
wrapper, or demo that implies provider calls, target writes, public benchmark
claims, package availability, hosted runtime, or provider compatibility.

## Topics

First wave:

- `llm-evaluation`
- `agent-evaluation`
- `context-engineering`
- `ai-agents`
- `llmops`
- `model-behavior`
- `local-eval`
- `developer-tools`
- `python`
- `local-first`
- `ascr`
- `memory-governance`

Second wave only after formal public evidence supports broader claims:

- `benchmark`
- `benchmarking`
- `evals`

Avoid early:

- `security`
- `vulnerability-scanner`
- `memory-os`
- `vector-database`
- `chatbot`
- `agi`

Those topics either overstate the current artifact or attract the wrong review
standard.

## Social Summary

Use:

`CtxGov finds stale, conflicting, unsupported, unsafe, and memory-risky AI-facing context before it shapes the next agent run.`

## Litmus Test

The repo header is correct if a new reader can infer all of this in 10 seconds:

- this is about AI-agent context health
- ASCR is a linked sibling contract/toolkit, not a stable-standard claim
- the artifact is local and reviewable
- the project is evaluation-oriented, not another agent runtime
- no public benchmark, security, compatibility, or autonomous-execution claim is
  being made
- the legacy namespace is provenance, not the public brand
