# Research Engineering Hiring Packet

Date: 2026-06-03
Status: local packet for personal outreach and LinkedIn Featured. Verify all
links after public deployment.

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
| CtxGov main repo | Local public-surface cleanup prepared | `README.md` |
| v0.6.3 release draft | Local GitHub release body ready | `release/v0.6.3/github-release.md` |
| Project page | Local static page ready | `docs/index.html` |
| Agent Context Evals companion | Public v0.2 scaffold | `https://github.com/ctxgov/agent-context-evals` |
| Technical report | Draft ready | `https://github.com/ctxgov/agent-context-evals/blob/main/reports/technical-report.md` |
| Companion release | Published | `https://github.com/ctxgov/agent-context-evals/releases/tag/v0.2.0` |
| Demo script | Capture script ready | `release/v0.6.3/demo/60-second-demo-script.md` |
| LinkedIn/outreach pack | Draft ready | `docs/linkedin-and-outreach-pack-2026-06-03.md` |

## What To Inspect First

1. README first screen: does the project read as agent context health eval?
2. Failure taxonomy: are the finding categories concrete?
3. Benchmark skeleton: are the cases, labels, scorer, and baseline reproducible?
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

`I am building CtxGov, an agent context-health evaluation artifact. It checks repo/workflow context for stale, conflicting, unsupported, unsafe, and hidden-failure spans before an AI agent acts. The repo, local benchmark skeleton, scorer, baselines, and technical report draft are ready for review.`

## Next Proof Needed

- publish the companion repo
- run and report deterministic baseline metrics
- capture 60-second demo GIF
- get one downstream issue/PR/design-doc citation with permission
- add independent reviewer FP/FN notes
