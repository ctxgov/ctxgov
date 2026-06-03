# Research Engineering Hiring Packet

Date: 2026-06-03
Status: public packet for personal outreach and LinkedIn Featured. Links were
updated after the companion v0.5.0 release.

## Target Roles

- Research Engineer, Evals
- Model Evaluation Engineer
- AI Safety Evaluation Engineer
- Agent Evaluation Engineer
- LLM Evaluation Infrastructure Engineer

## Positioning

I build evaluation infrastructure for AI-agent workflows. My current project is
CtxGov, a local context-health evaluator that checks AI-facing repo and workflow
context before agent execution.

The core question:

`Can we catch stale, conflicting, unsupported, unsafe, or hidden-failure context before an agent acts on it?`

## Artifacts

| Artifact | Status | Link |
| --- | --- | --- |
| CtxGov main repo | Public | `https://github.com/ctxgov/ctxgov` |
| v0.6.3 release | Published | `https://github.com/ctxgov/ctxgov/releases/tag/v0.6.3` |
| v0.6.4 doctor coverage release | Published | `https://github.com/ctxgov/ctxgov/releases/tag/v0.6.4` |
| v0.6.5 release-integrity and multi-label eval readiness release | Prepared | `https://github.com/ctxgov/ctxgov/releases/tag/v0.6.5` |
| Project page | Published | `https://ctxgov.github.io/ctxgov/` |
| Agent Context Evals companion | Public v0.5 mutation multi-label artifact | `https://github.com/ctxgov/agent-context-evals` |
| Technical report | Draft ready | `https://github.com/ctxgov/agent-context-evals/blob/main/reports/technical-report.md` |
| Companion release | Prepared | `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.5.0` |
| Demo GIF | Published | `https://raw.githubusercontent.com/ctxgov/agent-context-evals/main/demo/60-second-demo.gif` |
| v0.5 results report | Prepared | `https://github.com/ctxgov/agent-context-evals/blob/main/reports/v0.5-results.md` |
| LinkedIn/outreach pack | Draft ready | `docs/linkedin-and-outreach-pack-2026-06-03.md` |

## What To Inspect First

1. README first screen: does the project read as agent context health eval?
2. Failure taxonomy: are the finding categories concrete?
3. Evaluation artifact: are the cases, labels, scorer, baselines, adapters,
   review packet, and demo reproducible?
4. Technical report: are limitations and reproducibility honest?
5. Demo: can a reviewer understand the artifact in 60 seconds?

## Claim Boundaries

Do not present the project as:

- a security scanner
- a universal benchmark
- a provider compatibility layer
- a production agent runtime
- a memory backend
- an autonomous remediation agent

Correct framing:

`CtxGov is an evaluation artifact for AI-facing context health before agent execution.`

## Outreach Note

Short version:

`I am building CtxGov, an agent context-health evaluation artifact. It checks repo/workflow context for stale, conflicting, unsupported, unsafe, and hidden-failure spans before an AI agent acts. The repo, companion eval artifact, scorer, baselines, doctor adapter result, offline judge harness, demo, and technical report draft are ready for review.`

## Next Proof Needed

- complete independent review of the v0.3 review-intake cases
- publish adjudicated labels and reviewer agreement notes
- add false positive and false negative analysis on reviewed labels
- expand beyond deterministic mutation data into trace-derived reviewed data
- get one downstream issue/PR/design-doc citation with permission
