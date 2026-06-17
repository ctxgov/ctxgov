# Product Taxonomy And Release Ladder

Date: 2026-06-02
Status: local/private taxonomy and release-readiness read model. This document
is not a roadmap, approval matrix, execution receipt, public claim source,
runtime adapter, benchmark result, package plan, or stable MGP claim.

## Purpose

This document prevents CtxGov planning drift by separating product lines,
product surfaces, implementation workstreams, gates, and historical analysis.
It resolves the naming mismatch between the six Task Shard workstreams and the
broader high-ROI product sequence.

## Naming Rules

- `Product line`: durable cross-release family in `docs/product-line-ledger.md`.
  A product line needs a single source of truth, next gate, metrics, rollback,
  upstream inputs, downstream consumers, and a plausible public artifact.
- `Product surface`: user-visible or ecosystem-facing feature under a product
  line. It can become public as an example, report, CLI beta, or case study, but
  it does not become a new product line by default.
- `Implementation workstream`: task-specific fixture, importer, negative case,
  private gate, or report hardening effort. Workstreams are not product names.
- `Gate`: deterministic check or release-readiness boundary. A gate is not a
  product, even when it has a CLI or script.
- `Historical analysis`: prior research, fixture packs, and closed-version
  designs that feed current products. They should be managed as inputs, not as
  parallel active products.

## Canonical Product Lines

Keep exactly five active product lines until a new candidate passes the split
test below:

| Product line | Public posture | Consolidation rule |
| --- | --- | --- |
| Context Injection / Projection Governance | Existing public predecessor; new target writes and live adapters remain approval-gated. | Owns projection, source refs, trust packets, and target-write authority. |
| Session Continuity Sidecar | Private/offline; no live session start or provider/backend mutation. | Owns saved-session handoff, continuity packets, launch previews, and intake. |
| Memory X-Ray | Highest near-term public-example candidate; still no compatibility, benchmark, or stable-MGP claim. | Owns memory mutation evidence, consequence ceilings, rollback, and model-state surface receipts. |
| OSS Efficiency Benchmark | Private benchmark gate; no public efficiency claim. | Owns same-or-better quality gates before token/time/rework savings count. |
| Task Shard Context Control | Private/offline; no workflow execution, worktree creation, provider/model call, target write, or memory write. | Owns long-task split, context admission, budget, rehearsal, merge, and replan receipts. |

## External Sibling Contract

ASCR (Agent State & Context Runtime Contract) is a sibling contract/toolkit, not a CtxGov product line; it can feed all five product lines as a framework-neutral runtime-state shape. CtxGov v0.6.10 is ASCR-aligned L1/L1-plus evidence, CtxGov v0.6.12 is release-integrity maintenance, and CtxGov v0.6.13 is an owner-approved auto-publish research/release-integrity fixture, not an
L5 stable-standard, benchmark, security, provider compatibility, adoption, package, live-adapter, hosted-runtime, or CLI-beta claim.

## Task Shard Workstreams

The six names below are Task Shard implementation workstreams, not six product
lines:

| Workstream | Parent product line | Product surface or gate |
| --- | --- | --- |
| Import-Shape Negatives | Task Shard Context Control | Negative fixture gate for source, omitted-context, runtime, side-effect, and authority drift. |
| Offline Saved-Trace Importers | Task Shard Context Control | Adapter/harness import workstream for read-only saved traces. |
| Task Shard Private Gate | Task Shard Context Control | Private deterministic gate. |
| OSS Task-Shard Regression Case | OSS Efficiency Benchmark | Negative benchmark workstream proving savings zero out when Task Shard quality regresses. |
| Shard Context Rehearsal | Task Shard Context Control | Product surface for per-shard context preview. |
| Context Budget Ledger | Task Shard Context Control | Product surface for token, cache, source recovery, and compaction-loss reporting. |

2026-06-17 HN candidate:
`docs/post-memory-state-task-shard-hn-candidate-2026-06-17.md` keeps Task
Shard Context Budget Ledger / Shard Context Rehearsal under Task Shard Context
Control as an L1 local/offline product surface. It is not a sixth product line,
benchmark, provider/support claim, workflow runtime, worktree executor, target
writer, memory backend, package, SARIF surface, or stable protocol.

## Product Surfaces

Use these names for public-facing or ecosystem-facing surfaces:

`Memory X-Ray Report`, `Activation X-Ray`, `Memory-to-Action Governance Report Shape`, `OSS Efficiency Benchmark`, `Task Shard X-Ray`, `Context Budget Ledger`, `Shard Context Rehearsal`, `Workflow Script Passport`, `Long-Task Governance Benchmark`, `Session Continuity Handoff`, `Context Injection Preview`, `Causal Trace Autopsy`, `Ontology Drift Passport`, `Analysis State Ledger`, `State Evolution Flight Recorder`, `Reset Benefit Probe`, `Rollback Fidelity Receipt`, `Counterfactual Isolation Card`, `State Composition Card`, `Harness Pressure Passport`, `Cognitive State Envelope Inspector`, `Memory Failure Plane Card`, `Trajectory Safety Autopsy`, `Lineage Trust Envelope`, `Sensitive Action Memory Gate`, `Parameter Repair Card`, `Purposeful Bottleneck Contract`, `Procedural Memory Passport`, `State Transition X-Ray`, `Learning Hook Audit`, `Memory Commit Passport`, `Policy Grant Simulator`, `Backend Governability Score`, `Business State Transition Visa`, `Policy Compliance Memory Gate`, `Experience Reuse Gain Card`, `State Mutation Rollback Receipt`, `Cost Attribution Ledger`, `Procedure Step Omission Card`, `Memory Evaluation Receipt`, `Execution State Branch Passport`, `Summary Boundary Maintenance Receipt`, `Full-Context Floor Card`, `Intrinsic Retrieval Surface Passport`, `Adapter Delta Influence Card`, `Cross-Harness Skill Memory Passport`, `Compound Learning Receipt`, and `Memory Salience Lease`.

`Import-Shape Negatives`, `Private Gate`, and regression manifests should not be
marketed as products; they are proof that the products are disciplined.

## Internal Standards

These are cross-surface standards, not product names:

- `MemoryOperationTrace`: purpose-labeled retrieve/reason/learn/inject/act/finalize traces with raw input, formatted prompt, retrieved refs, memory/system token split, latency/cost, and selected/omitted/blocked refs.
- `CanonicalTraceKernel`: new report views must compile to `MemoryOperationTrace + ConsequenceShard + PolicyGrant + StateTransitionReceipt`; this prevents passport/gate surface sprawl.
- `ScaleProfile`: every memory/state influence fixture must declare
  `local_single_user`, `team_project`, or `cluster_multi_tenant`. The profile
  selects required identity, scope, TTL/delete/revision, final-state, rollback,
  and audit fields; it does not create a sixth product line or runtime target.
- `ConsequenceShard`: the Governable State Influence Unit: source extent, operation lineage, state role, activation route, selected/omitted/blocked refs, consequence channel, authority ceiling, TTL/lease, counterfactual probe, rollback/demotion path, and final-state assertion.
- `ShortCircuitMemoryDiagnosis`: storage -> summary/faithfulness -> retrieval -> activation/invocation -> action-parameter authority -> promotion/retirement checks.
- `LearningActionVisa`: learning is a deliberate action with role-specific read/write authority; procedural writes need owner review and non-regression evidence.
- `SensitiveParameterAuthority`: sensitive tool parameters carry lineage, projection policy, allow/refuse/require-user/strip-retry/repair-retry decisions, and strict treatment for parentless derived sensitive state.
- `ConsequenceWeightedDistortionBudget`: every compaction, summary, or shard injection declares which information may be lost per consequence channel and which source, rollback, conflict, or omitted-evidence anchors remain recoverable.
- `PolicyGrantCalibrationReceipt`: every automation rule reports overblock, underblock, owner override, false-allow, false-quarantine, and review-minutes saved by category, not as a single risk score.
- `SourceMonitoringReceipt`: every memory/context candidate records source kind, age, path, trust, private-channel caveat, source-confusion risk, familiarity-only risk, and contradiction/omission state before activation.
- `MemoryLifecycleTransitionVisa`: every transition from episode -> extracted fact -> summary -> procedural lesson -> default/tool route/team policy/train-or-publish signal carries evidence, tests, scope, lease, rollback, and maximum consequence.
- `AuthorizedStateInfluenceProtocol`: internal-only MGP planning name for event log -> learning artifact -> read-only retrieval hook -> tool decision -> policy step -> state mutation -> final-state assertion -> rollback.
- `BusinessStateTransitionVisa` / `LearningHookAudit` / `StateMutationRollbackReceipt`: memory-influenced state changes must record source refs, selected/omitted learnings, policy steps, parameter lineage, state delta, final assertion, owner grant, cost/reliability, and rollback.
- `ExecutionStatePath`: active root-to-current path plus summary boundaries, recent raw trajectory, isolated failure branches, branch hints, and rollback or compensation target. It is a governance read model, not a tree runtime.
- `FullContextFloorCard`: memory, retrieval, compression, sharding, profile, or adapter-influence optimization must prove same-or-better correctness, governance coverage, source recoverability, and final-state outcome against raw/full-context and no-memory baselines before savings count.
- `ModelStateSurfacePassport`: extend model-state surface custody to intrinsic retrieval state, adapter deltas, KV/cache reuse, sampler bias, and harness skill/rule state. Hidden model state never grants authority without source refs, omitted refs, scope, consequence ceiling, and revocation.
- `MemorySalienceLease`: priority or weighting must be typed by source quality, consequence, recency, owner intent, safety, or review evidence; salience changes review/routing priority only and grants no answer, action, write, publication, cache, adapter, or training authority.

## Historical Consolidation

Manage existing products and analysis as inputs to the five active product
lines:

| Historical item | Current management home |
| --- | --- |
| Context Health Doctor | Support diagnostic under Context Injection / Projection Governance and Session Continuity; do not reopen as a standalone product line without new adoption evidence. |
| Flow Profiler | Evidence and telemetry input to OSS Efficiency Benchmark and Task Shard Context Control. |
| Trace Importers | Adapter/harness intake layer feeding Memory X-Ray, Session Continuity, and Task Shard Context Control. |
| Harness Assumption Intake | Negative-fixture and Workflow Script Passport input. |
| Route Authority | Governance-kernel input for consequence ceilings and projection authority. |
| Memory Consequence / Typed Memory Policy / Temporal Memory Safety | Memory X-Ray and MGP policy-profile inputs. |
| Provider Memory Control Surface Matrix | Memory X-Ray source matrix and model-state surface input. |
| Adoption Evidence Packets | OSS Efficiency and public case-study readiness input. |
| CtxGov public repo + Agent Context Health Eval companion | Public artifact surface under Context Injection / Projection Governance plus evaluation evidence input to OSS Efficiency Benchmark, Memory X-Ray, Session Continuity, and Task Shard Context Control. The 2026-06-03 CtxGov `v0.6.8` / companion `v0.7.0` release train is L1/public-local evaluation evidence; the 2026-06-05 CtxGov `v0.6.12` / companion `v0.8.0` train is release-integrity and eval-hardening evidence; the 2026-06-08 CtxGov `v0.6.13-auto-publish-research` release is a public-safe auto-publish research fixture, not a standalone product line and not an L4 public benchmark claim. |
| MemTrace-style operation graphs and MemGraphRAG-style ontology induction | Causal Trace Autopsy, Ontology Drift Passport, Task Shard Context Control, Memory X-Ray, and OSS Efficiency inputs; do not reopen as runtime, graph engine, or ontology product lines. |
| LongDS-style state evolution and harness-pressure evidence | Analysis State Ledger, State Evolution Flight Recorder, Reset Benefit Probe, Rollback Fidelity Receipt, Counterfactual Isolation Card, State Composition Card, Harness Pressure Passport, Task Shard Context Control, and OSS Efficiency inputs; do not reopen as data-science agent, notebook runtime, live trace adapter, or generic harness framework product lines. |
| CoALA memory roles, Agent Skills, MemFail, AgentDoG, human-memory simulation, and MemLineage | Cognitive State Envelope Inspector, Memory Failure Plane Card, Trajectory Safety Autopsy, Lineage Trust Envelope, Sensitive Action Memory Gate, Parameter Repair Card, Purposeful Bottleneck Contract, Procedural Memory Passport, Memory X-Ray, Task Shard Context Control, and OSS Efficiency inputs; the deeper code/PDF details become internal standards for operation traces, write/query separation, short-circuit diagnosis, learning deferral, parameter repair, bottleneck contracts, and actual-action safety review; do not reopen as unified memory DB, cognitive runtime, skill runtime, trajectory auditor, cryptographic log, or security product line. |
| STATE-Bench, Microsoft Foundry Memory, and enterprise stateful memory sources | State Transition X-Ray, Learning Hook Audit, Business State Transition Visa, Policy Compliance Memory Gate, Experience Reuse Gain Card, State Mutation Rollback Receipt, Cost Attribution Ledger, Procedure Step Omission Card, Memory Evaluation Receipt, Memory X-Ray, Task Shard Context Control, and OSS Efficiency inputs; do not reopen as enterprise workflow runtime, Microsoft Foundry integration, STATE-Bench runner, database sandbox, memory backend, public benchmark, provider compatibility, or stable-MGP product line. |
| MAGE, CL-Bench, INTRA, dynamic-LoRA, Supermemory, ECC, and Compound Engineering sources | Execution State Branch Passport, Summary Boundary Maintenance Receipt, Full-Context Floor Card, Intrinsic Retrieval Surface Passport, Adapter Delta Influence Card, Cross-Harness Skill Memory Passport, Compound Learning Receipt, Memory Salience Lease, Memory X-Ray, Task Shard Context Control, and OSS Efficiency inputs; do not reopen as execution-state runtime, intrinsic retriever, LoRA router, memory engine, plugin installer, coding-harness suite, biological-memory product, public benchmark, provider compatibility, or stable-MGP product line. |
| OpenAI, Claude Code, Gemini CLI, LangGraph, Mem0, Zep/Graphiti, and Letta memory control surfaces | Activation X-Ray, Memory-to-Action Governance Report Shape, Memory Commit Passport, Policy Grant Simulator, Backend Governability Score, CanonicalTraceKernel, Memory X-Ray, Task Shard Context Control, and OSS Efficiency inputs; do not reopen as provider integration, hook runtime, markdown-memory manager, JSON store, vector/graph retriever, memory backend, public compatibility matrix, or stable-MGP product line. |
| HN-ready methodology launch pack | Public-facing methodology/demo surface under Memory X-Ray and OSS Efficiency. It prepares copy, strict-readiness data, claim-firewall negative examples, and coverage-map evidence; it is not a new product line, benchmark, case study, CLI beta, provider-support claim, compatibility matrix, adoption claim, or outreach execution. |
| Scale-profile governability release cycle | Planning/readiness SSOT under Memory X-Ray, Task Shard, and OSS Efficiency. It records official Microsoft/Google/OpenAI/Claude/LangGraph memory-state field mapping, `scale_profile` fixture fields, the local 24-case Activation X-Ray scale-profile gate, the user-operable Activation X-Ray Try-in-5-Minutes demo/page/pack, HN URL-submission posture, and release-cycle gates; do not reopen as external-product compatibility, live integration, SARIF upload, benchmark, or sixth product line. |

## Split Test

Do not create a new product line unless all conditions are true:

1. It has a distinct user or buyer from the five active lines.
2. It has a public artifact that can be explained without referencing another
   product as the real value.
3. It has a SSOT doc, CLI/schema/report surface, metrics, rollback, and blocked
   side effects.
4. It has an adoption or case-study path.
5. It does not mainly duplicate runtime, retriever, worktree, vector DB, or
   generic agent orchestration competition.

If any condition fails, keep it as a product surface or workstream.

## Release Ladder

| Level | Allowed public artifact | Required gates |
| --- | --- | --- |
| L0 Private fixture | Nothing public. | Local tests, private gates, no side effects. |
| L1 Sanitized examples | Provider-neutral examples and report shapes. | Redaction, no private paths, no compatibility claim, no benchmark claim, claim lint. |
| L2 Public case study | Permissioned case study. | Permission, source freshness, benchmark receipt, downstream citation or maintainer feedback, rollback. |
| L3 Public CLI beta | Offline/read-only CLI beta. | Stable schema, deterministic validation, failure-mode docs, no provider/model/backend writes. |
| L4 Public benchmark | Public benchmark claim. | Real telemetry, hidden holdout, negative cases, reproducible methodology, equal-or-better quality gates. |
| L5 Stable MGP | Stable protocol claim. | Multiple downstream uses, migration/versioning, compatibility policy, public spec review, rollback strategy. |

2026-06-03/05/08 release-ladder note: CtxGov `v0.6.8`/`v0.6.12`/`v0.6.13` and companion `agent-context-evals` `v0.7.0`/`v0.8.0` are L1/L1-plus readiness, eval-hardening, release-integrity, and auto-publish research evidence only; do not promote them to L4 public benchmark, adoption, security, provider compatibility, hosted runtime, package, automatic-publication authority, or stable-MGP claims without the gates above.

2026-06-05/08 Memory X-Ray L2 note: local release-control/no-op handoff gates remain report-shape controls; CtxGov `v0.6.13-auto-publish-research` is live at `88f0ed28ce4ad26091c37ef6e77bde388871413b`, but stronger claims, live adapters, provider/model/backend writes, packages, reviewer/outreach, and spec claims still require external evidence and explicit approval. Private `ctxvault` planning remains Forgejo-only and must not push this private repo to GitHub.

2026-06-08 OSS Efficiency real-OSS note: `mem0ai/mem0`, `langchain-ai/langgraph`, and `getzep/graphiti` now have private pinned source intake, visible matrix, hidden holdout, non-picked telemetry, fresh dogfood transcript hashes, source freshness recheck, strict-provenance classification, and an internal methodology-only draft. This is L0 private evidence and L4-prep methodology work; telemetry records without transcript hashes are fixture evidence only.

2026-06-08 HN-ready launch note: `release/hn-ready-methodology-launch/2026-06-08/` is an L1/L4-prep methodology launch pack, not a public benchmark or adoption artifact. HN/LinkedIn/X copy may say CtxGov is a local claim firewall and show rejected negative examples, but it must keep `strict_provenance_eligible=false`, `stronger_claim_lane_eligible=false`, `publication_executed=false`, `outreach_performed=false`, and all benchmark/compatibility/adoption/security/endorsement/product-improvement claims false until separate gates pass. The HN path is valid only if the linked artifact is runnable/inspectable and not merely a reading-only landing page.

2026-06-08 v0.12.0 / scale-profile note: the current public HN anchor is
CtxGov `v0.12.0 - Fresh-Clone Product Receipt`, with
`python3 scripts/run_memory_xray_demo.py` as the one-command demo. The
scale-profile governability lane is L1/L4-prep planning only: it may publish
sanitized report-shape examples and a tryable local claim-firewall demo, but it
must not publish savings, benchmark, compatibility, support, adoption,
security, provider, SARIF-upload, or stable-MGP claims.

2026-06-11 cold-start compression note: scale-profile/HN context should restart
from the four-file core recorded in
`docs/post-v0.7.0-scale-profile-governability-release-cycle-2026-06-08.md`.
The R1.1 Activation X-Ray and R2.1 Local Memory State Influence Boundary
release-pack READMEs are execution add-ons only, not new product lines or
default roadmap inputs.

## Adjusted Sequence

Near-term high ROI sequence:

1. Upgrade `Memory X-Ray Report` toward `Activation X-Ray` on saved traces, backed by `CanonicalTraceKernel`.
2. Connect Activation X-Ray, Memory X-Ray, and Task Shard quality into `OSS Efficiency Benchmark`.
3. Harden `Task Shard X-Ray`, `Context Budget Ledger`, and `Shard Context Rehearsal` as private/offline product surfaces.
4. Add `Analysis State Ledger` and `Harness Pressure Passport` only as saved trace/read-model surfaces for state lineage, counterfactual isolation, rollback fidelity, reset decision quality, deterministic checks, and harness verbosity risk.
5. Add `Causal Trace Autopsy` and `Ontology Drift Passport` only as saved trace/read-model surfaces for operation-stage failures, selected/omitted evidence, counterfactual repair, graph drift, and consequence ceilings.
6. Add cognitive-memory surfaces only as saved read models first: `Cognitive State Envelope Inspector`, `Memory Failure Plane Card`, `Lineage Trust Envelope`, `Sensitive Action Memory Gate`, `Parameter Repair Card`, `Trajectory Safety Autopsy`, `Purposeful Bottleneck Contract`, and `Procedural Memory Passport`; implement internal operation/authority standards before any runtime adapter or memory backend.
7. Add `ConsequenceWeightedDistortionBudget`, `PolicyGrantCalibrationReceipt`, `SourceMonitoringReceipt`, and `MemoryLifecycleTransitionVisa` as internal fixture standards before any automatic memory write, default, action, or public-claim authority.
8. Add Memory-to-State governance surfaces only as saved trace/read models: STATE-Bench-shaped event log, learnings, policy/tool/state/cost/rollback fields; do not execute STATE-Bench, Foundry, providers, models, databases, or live adapters.
9. Add execution-state and hidden model-state governance surfaces only as saved trace/read models: active path, summary boundary, failure branch, full-context floor, intrinsic-retrieval refs, adapter-delta influence, cross-harness skill/rule provenance, salience lease, and revocation fields; do not build MAGE, INTRA, dynamic-LoRA loading, memory engines, harness plugins, or biological-memory features.
10. Build `Workflow Script Passport` as inspect-only ecosystem intake, not a workflow executor.
11. Mechanize `Product-Line Ledger` checks after taxonomy fields stabilize.
12. Publish only L1 sanitized report-shape examples first; prefer `Memory-to-Action Governance Report Shape` over stable-MGP wording, use HN-ready copy as methodology/demo launch copy only after exact owner approval and runnable-artifact verification, and defer public benchmark, public CLI
   beta, live adapters, and stable-MGP claims until the release ladder gates
   pass.
13. Use `docs/post-v0.7.0-scale-profile-governability-release-cycle-2026-06-08.md`
   as the cross-session SSOT for official memory/state field mapping,
   `scale_profile` fixture design, v0.12.0 HN launch posture, strict
   provenance telemetry requirements, and release-cycle background work.

## Test, Audit, Rollback

test_constraint:

- Product-line ledger and Task Shard playbook should link to this taxonomy when
  they name workstreams or product surfaces.

audit_constraint:

- New product names must be classified as product line, product surface,
  implementation workstream, gate, or historical input before roadmap promotion.

rollback_constraint:

- Delete or supersede this document and remove links from the ledger and
  playbook. Product authority remains in executed receipts, approval matrices,
  active governance plans, the canonical roadmap, and checked source indexes.
