# CtxGov Public Positioning

Date: 2026-06-03
Status: public copy source for the CtxGov surface. This document does not grant
package migration, benchmark, compatibility, security, provider-call,
target-write, or stable-protocol authority.

## Core Position

CtxGov is:

- Agent Context Health Evaluation for AI Workflows
- a local, reviewable evaluator for AI-facing context before agent execution
- a way to catch stale, conflicting, unsupported, unsafe, or hidden-failure
  context before it shapes an agent run
- a research-engineering artifact that can become a benchmark companion, not an
  agent runtime or memory backend

Short hook:

`Agents fail on bad context. CtxGov checks the context first.`

Developer-facing line:

`CtxGov evaluates AI-facing repo and workflow context before agent execution, with evidence spans, finding types, and explicit claim boundaries.`

## Problem Statement

AI agents do not only read prompts. They consume repository docs, rules files,
release notes, memory summaries, saved traces, terminal logs, issue comments,
and handoff packets. Those inputs often disagree.

The public problem should be framed in this order:

1. agents act on AI-facing context assembled from many stale or partial sources
2. bad context produces bad behavior before the model has a chance to reason
3. teams lack a small evaluator that points to the exact evidence span
4. CtxGov makes that context-health review explicit and reproducible

## Failure Taxonomy

Use these public finding families:

| Finding type | Reader meaning | Public claim boundary |
| --- | --- | --- |
| `stale_claim` | A current-facing claim is contradicted by fresher evidence. | Not a truth oracle. It points to evidence drift. |
| `conflicting_policy` | Two AI-facing instructions authorize incompatible behavior. | Not a policy engine. It flags conflict for review. |
| `unsupported_release_claim` | Copy points to a release, tag, package, or benchmark that is not backed by an artifact. | Not a package registry guarantee. |
| `unsafe_action_guidance` | Context encourages side effects without approval, rollback, or authority. | Not a sandbox or security product. |
| `hidden_terminal_failure` | Logs or receipts show failure while handoff copy says pass or ready. | Not a CI service. It preserves failure evidence. |
| `clean` | No expected finding in the labeled case. | Synthetic clean cases are controls, not broad safety evidence. |

## Differentiation

CtxGov should not be positioned as:

- an agent harness
- a memory backend
- a RAG framework
- a provider SDK
- a security scanner
- a universal benchmark
- an automatic remediation agent

The differentiator is narrower:

`Before the agent runs, inspect whether the context it is about to trust is stale, conflicting, unsupported, unsafe, or hiding failures.`

## Release Ladder Language

Use:

- `local source artifact`
- `L1 public-safe report-shape example`
- `companion eval review-ready artifact`
- `synthetic labeled cases`
- `deterministic scorer`
- `claim boundaries`

Avoid until evidence exists:

- `state of the art`
- `security-grade`
- `prevents hallucinations`
- `proves agent safety`
- `universal benchmark`
- `supports all providers`
- `production-ready autonomous remediation`

## LinkedIn Headline

`Research Engineer | AI Agent Evaluation, Context Health, and Evals Infrastructure | Building CtxGov`

## LinkedIn About Draft

I build evaluation infrastructure for AI-agent workflows.

My current project is CtxGov, a local context-health evaluator for AI-facing
project and workflow context. The goal is simple: before an agent runs, check
whether the context it is about to trust is stale, conflicting, unsupported,
unsafe, or hiding a failed command.

Current artifacts include the CtxGov repo, a Context Health Doctor sample, a
v0.6.3 public-surface release, a v0.6.4 doctor-coverage release, a v0.6.5
release-integrity and multi-label eval readiness release, a v0.6.6 companion
alignment release, a v0.6.7 current-companion wording guard release, and a
companion Agent Context Health Eval v0.6 artifact with
160 deterministic mutation cases, 206 labels, 60 adversarial hard negatives,
multi-label scoring, span diagnostics, deterministic baselines, a native CtxGov
doctor adapter run, an offline LLM-judge harness, a demo GIF, a review packet,
and a technical-report draft.

I am focused on research engineering roles around evals, model behavior,
agent reliability, and AI safety evaluation. I care about reproducible
evidence, clear limitations, and artifacts that hiring managers and researchers
can inspect directly.

## Publication Boundary

Every public artifact must keep these constraints visible:

- no provider/model call
- no target repository write
- no live adapter or hosted runtime claim
- no security guarantee
- no benchmark-performance claim until independent review and adjudication are
  published
- no adoption claim until a downstream issue, PR, design doc, or maintainer
  thread cites the artifact with permission
- no stable protocol claim

## Rollback

If public copy drifts into unsupported claims, supersede this document and the
affected release/page/post. Keep archived wording only when needed for
provenance, and route it through `docs/provenance.md`.
