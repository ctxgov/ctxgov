# LinkedIn And Outreach Pack

Date: 2026-06-03
Status: draft material with public v0.6.3 and companion v0.3.0 links verified.

## LinkedIn Headline

`Research Engineer | AI Agent Evaluation, Context Health, and Evals Infrastructure | Building CtxGov`

## LinkedIn About

I build evaluation infrastructure for AI-agent workflows.

My current project is CtxGov, a local context-health evaluator for AI-facing
project and workflow context. Before an agent runs, CtxGov checks whether the
context it is about to trust is stale, conflicting, unsupported, unsafe, or
hiding a failed command.

Current artifacts include the CtxGov repo, a Context Health Doctor sample, a
v0.6.3 public-surface cleanup release, and a companion Agent Context Health
Eval v0.3 artifact with 50 trace-pattern labeled cases, 12 hidden-holdout
public case texts, 12 review-intake cases, deterministic scoring, baselines,
adapter contracts, an offline LLM-judge harness, a demo GIF, a review packet,
and a technical-report draft.

I am focused on research engineering roles around evals, model behavior, agent
reliability, and AI safety evaluation. I care about reproducible evidence,
clear limitations, and artifacts that a research engineer or hiring manager can
inspect directly.

## Technical Post 1

Title:

`Agents fail on bad context`

Draft:

AI agents do not only read prompts.

They read README files, release notes, rules files, memory summaries, terminal
logs, issue comments, and handoff packets. Those files often disagree.

One file says a release is ready. Another says external publish approval is
pending. A handoff says tests pass. A terminal log says they failed. An
AGENTS.md file suggests a deploy step that the governance doc still blocks.

That is the gap I am working on with CtxGov: Agent Context Health Evaluation
for AI Workflows.

The first artifact checks AI-facing context for five failure families:

- stale claims
- conflicting policy
- unsupported release claims
- unsafe action guidance
- hidden terminal failures

The key design choice is evidence spans. A finding is not useful unless it
points to the exact text that would mislead the next agent run.

Current materials include the CtxGov repo, a v0.6.3 public-surface release, a
50-case companion eval scaffold, a regex baseline, a real CtxGov doctor adapter
result, an offline LLM-judge harness, a demo GIF, a review packet, a scorer,
and a technical-report draft.

Limitations are explicit: this is not a security guarantee, not a universal
benchmark, not a provider compatibility claim, and not an auto-remediation
agent.

The goal is narrower:

Before the agent runs, check whether the context is healthy enough to trust.

Links:

- CtxGov repo: `https://github.com/ctxgov/ctxgov`
- Release: `https://github.com/ctxgov/ctxgov/releases/tag/v0.6.3`
- Project page: `https://ctxgov.github.io/ctxgov/`
- Technical report: `https://github.com/ctxgov/agent-context-evals/blob/main/reports/technical-report.md`
- Readiness report: `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.3-readiness.md`
- Demo GIF: `https://raw.githubusercontent.com/ctxgov/agent-context-evals/main/demo/60-second-demo.gif`
- Companion release: `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.3.0`

## Targeted Outreach Message

Subject:

`Agent context-health eval artifact`

Message:

Hi <name>,

I am building CtxGov, a small evaluation artifact for AI-agent context health.
It checks repo/workflow context for stale, conflicting, unsupported, unsafe, and
hidden-failure spans before an agent acts on it.

The current materials are repo-first: public-surface release, 50-case v0.2
trace-pattern scaffold, 12 hidden-holdout public case texts, 12 v0.3
review-intake cases, regex baseline, scorer, offline LLM-judge harness, demo
GIF, CtxGov heuristic and doctor adapter modes, and technical report draft.
The limitations are explicit: no security guarantee, no universal benchmark
claim, and no provider compatibility claim.

I would value feedback from an evals/research-engineering perspective,
especially on the taxonomy and whether the benchmark schema would be useful for
agent workflow evaluation.

Links:

- Repo: <repo link>
- Project page: <page link>
- Report: <report link>

Thanks,
Chris

## Weekly Cadence

Monday:

- publish one artifact-backed technical post

Tuesday to Wednesday:

- send 5 to 10 targeted messages to evals/research-engineering people

Thursday:

- update repo, demo, report, or benchmark based on feedback

Friday:

- review metrics and choose next artifact

## Outreach Tracker Columns

Use this table in a spreadsheet or Notion:

| Date | Name | Role | Company/Lab | Artifact Sent | Channel | Status | Reply | Follow-Up Date | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06-03 | Example | Research Engineer | Example Lab | Repo + report | LinkedIn | Draft |  | 2026-06-10 | Replace before use. |

## Featured Section

Monthly rotation:

- CtxGov repo
- Agent Context Evals companion repo
- technical report
- 60-second demo
- release notes
- hiring packet
