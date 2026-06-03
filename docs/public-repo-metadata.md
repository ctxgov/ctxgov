# CtxGov Public Repo Metadata

Date: 2026-06-03
Status: public-surface metadata source. This file is not a release receipt,
benchmark result, security claim, package migration receipt, or compatibility
matrix.

## Repository Identity

Canonical public project name:

`CtxGov`

Recommended canonical public repository:

`ctxgov/ctxgov`

Historical/provenance namespace:

`ctxvault`

Use `docs/provenance.md` when archived paths, old release artifacts, schema
ids, immutable receipts, or older docs still contain the legacy namespace.

## GitHub Description

Preferred:

`Context-health evaluator for AI agents: stale, conflicting, unsupported, and unsafe AI-facing context.`

Shorter fallback:

`Agent context-health evaluation before AI workflow execution.`

## GitHub About

Preferred:

`CtxGov checks AI-facing project context for stale claims, conflicting instructions, unsupported release statements, unsafe action guidance, and hidden failure residue before agent execution.`

Shorter fallback:

`Agent Context Health Evaluation for AI Workflows.`

## Homepage

Preferred:

`https://ctxgov.github.io/ctxgov/`

Use the repo URL only until GitHub Pages or another project page is live. The
homepage must not point at a package, wrapper, or demo that implies provider
calls, target writes, or benchmark claims.

## Topics

First wave:

- `llm-evaluation`
- `agent-evaluation`
- `context-engineering`
- `ai-agents`
- `llmops`
- `model-behavior`
- `evaluation`
- `developer-tools`
- `python`
- `local-first`

Second wave after the companion benchmark is public:

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

`CtxGov evaluates AI-facing context before agent execution, so reviewers can catch stale, conflicting, unsupported, unsafe, or hidden-failure context before it shapes the next run.`

## Litmus Test

The repo header is correct if a new reader can infer all of this in 10 seconds:

- this is about AI-agent context health
- the artifact is local and reviewable
- the project is evaluation-oriented, not another agent runtime
- no public benchmark, security, compatibility, or autonomous-execution claim is
  being made
- the legacy namespace is provenance, not the public brand
