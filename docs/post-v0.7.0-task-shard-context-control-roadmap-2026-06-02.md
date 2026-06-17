# Post-v0.7.0 Task Shard Context Control Roadmap

Date: 2026-06-02
Status: post-v0.7.0 private design input only. This document adds no current
v0.7.0 runtime behavior, provider/model call, live adapter, target write,
memory write, workflow execution, autonomous approval, public benchmark claim,
public adoption claim, or stable MGP claim. The user sometimes wrote MPG; this
document treats it as MGP.

2026-06-11 context compression: this document is not in the default
scale-profile/HN cold-start core. Read it only when changing Task Shard import
contracts, split/merge/replan quality gates, or scale-profile validation carrier
behavior. The reduced core and R1.1/R2.1 execution add-ons are owned by
`/Users/chris/projects/ctxvault/docs/post-v0.7.0-scale-profile-governability-release-cycle-2026-06-08.md`.

Initial private fixture/schema slice executed on 2026-06-02:

- `src/ctxvault/task_shard_context.py`
- `schemas/json/ctxvault-task-shard-context-control-fixture-pack-v0.schema.json`
- `schemas/json/ctxvault-task-shard-context-import-shapes-v0.schema.json`
- `fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-context-control-fixture-pack-20260602.json`
- `fixtures/v0.7.0-mgp-sidecar/task-shard-context-control/task-shard-context-import-shapes-20260602.json`
- `ctxvault task-shard evaluate`
- `ctxvault task-shard validate`
- `tests/test_task_shard_context_control_fixture.py`

This slice records no runtime execution, workflow launch, worktree creation,
provider/model call, target write, memory backend write, public claim, or stable
MGP claim.

2026-06-17 HN candidate scope lock:
`docs/post-memory-state-task-shard-hn-candidate-2026-06-17.md` selects Task
Shard Context Budget Ledger / Shard Context Rehearsal as the next
post-memory-state HN-standard milestone. It is a Task Shard product surface
only, with a local/offline saved-plan report and no workflow execution,
worktree creation, provider/model call, target write, memory/backend write,
benchmark, savings, adoption, security, compatibility, package, SARIF, or
stable-protocol claim.

2026-06-02 approved implementation update:

- The validator/evaluator is now a product module rather than test-local logic.
- The CLI is validate/evaluate only and reads local JSON fixtures.
- Claude Dynamic Workflows, Cline, OpenHands, Aider repo-map, and Plandex
  context-map import shapes are represented as offline fixture contracts.
- OSS Efficiency Benchmark now requires `split_quality`,
  `context_minimality`, `merge_safety`, and `replan_accuracy` to be
  same-or-better before long-task savings count.
- This update remains post-v0.7.0 private/offline work and does not add live
  adapter, runtime, worktree, provider/model, target-write, memory-write, or
  public-claim behavior.

2026-06-02 approved second implementation update:

- Import-shape validation now requires source-ref and omitted-context-ref
  contracts, and the negative fixture covers missing surface, runtime flip,
  side-effect flip, missing source refs, and missing omitted refs.
- Offline saved-trace importer read models now convert Claude Dynamic
  Workflows, Cline, OpenHands, Aider, and Plandex import shapes into fixture
  contracts without executing those systems.
- `Shard Context Rehearsal` now produces per-shard minimal context packets and
  blocked live-operation transcripts from the existing fixture pack.
- `Context Budget Ledger` now reports token pressure, cache authority, source
  recovery, selected/omitted/searchable/compacted refs, and compaction-loss
  risk from the same fixture pack.
- `scripts/check_task_shard_private_gate.py` is the private local gate for this
  product slice, but it is intentionally not wired into `ctxvault check` until
  unrelated old full-test missing-file failures are repaired.
- `docs/task-shard-context-control-next-session-playbook-2026-06-02.md` is the
  new-session task list and folder-decision entrypoint.
- The update remains private/offline/read-only: it does not execute workflows,
  create worktrees, call providers/models, write targets, write memory
  backends, promote memory, or create public/stable claims.

2026-06-02 approved third implementation update:

- Import-shape negative fixtures now cover 8 variants, adding
  `source_recovery_disabled` and `omitted_context_invisible` to the existing
  missing surface, runtime, side-effect, source-ref, and omitted-ref drift
  checks.
- Saved-trace import validation now contract-matches generated and committed
  read models back to the source import-shapes fixture for artifact refs,
  normalized read models, selected source refs, omitted context refs, and
  blocked authority.
- OSS Efficiency Task Shard regression coverage now has 3 negative cases:
  split-quality regression, context-minimality regression, and merge/replan
  regression. All can save token/time, but accepted savings remain zero when
  Task Shard quality regresses.
- The update remains private/offline/read-only: it does not execute workflows,
  create worktrees, call providers/models, write targets, write memory
  backends, promote memory, or create public/stable claims.

2026-06-03 research/design refresh:

- MemTrace and MemGraphRAG were cross-validated in
  `docs/post-v0.7.0-memory-context-causal-trace-and-ontology-governance-refresh-2026-06-03.md`.
- The refresh does not overturn Task Shard Context Control. It sharpens the
  shard boundary from "task chunk" to `ConsequenceShard`: source-backed
  evidence extent plus operation lineage plus selected/omitted refs plus
  allowed consequence envelope plus rollback.
- Future Task Shard fixtures should be able to emit or import causal trace
  overlays, counterfactual repair cards, memory minimality meters, and
  ontology drift passports as saved read models only.
- The refresh remains private/offline/design-only: it does not add runtime
  execution, graph construction, ontology generation, workflow launch,
  worktree creation, provider/model call, target write, memory write, public
  benchmark claim, or stable-MGP claim.

2026-06-03 LongDS/harness-state refinement:

- LongDS, MemTrace/smartcomment, and recent harness-engineering sources were
  cross-validated in
  `docs/post-v0.7.0-longds-state-ledger-and-harness-pressure-refresh-2026-06-03.md`.
- The refinement does not overturn Task Shard Context Control. It adds
  `AnalysisStateFrame` as a future read-model primitive for stateful analysis
  tasks where cleaned tables, formulas, thresholds, derived artifacts,
  counterfactual branches, rollback parents, and reset policy need explicit
  lineage.
- Future Task Shard fixtures should distinguish a task shard, a
  `ConsequenceShard`, and an `AnalysisStateFrame`: a shard may own execution
  scope, a consequence shard owns allowed effect, and a state frame owns a
  versioned analysis/runtime-state projection.
- The refinement remains private/offline/design-only: it does not run
  notebooks, execute workflows, launch devboxes/worktrees, instrument live
  MemTrace/smartcomment, call providers/models, write targets, write memory, or
  create public LongDS/benchmark/stable-MGP claims.

2026-06-03 cognitive-memory/lineage/trajectory refinement:

- CoALA, Agent Skills, MemFail, AgentDoG, a human-memory simulation benchmark,
  and MemLineage were cross-validated in
  `docs/post-v0.7.0-cognitive-memory-diagnostics-lineage-and-trajectory-safety-refresh-2026-06-03.md`.
- The refinement does not overturn Task Shard Context Control. It adds
  `CognitiveStateEnvelope` as a future wrapper over working, semantic,
  procedural, episodic, summary, analysis-state, ontology, tool-policy, or
  trajectory-lesson state that can affect a shard.
- Future Task Shard fixtures should distinguish execution scope, consequence
  scope, analysis state, and cognitive state: a shard owns work, a
  `ConsequenceShard` owns allowed effect, an `AnalysisStateFrame` owns
  versioned analytical/runtime state, and a `CognitiveStateEnvelope` owns role,
  activation route, failure plane, lineage trust, bottleneck policy, and repair.
- The refinement remains private/offline/design-only: it does not create a
  unified memory DB, cognitive runtime, skill runtime, live trajectory auditor,
  cryptographic transparency log, security product, provider/model call,
  target write, memory write, public benchmark/security claim, or stable-MGP
  claim.

2026-06-03 deeper code/PDF operation-standard refinement:

- MemFail code confirms a useful black-box boundary: memory systems expose
  retrieval, update, and finalize hooks; evaluation traces separate raw query,
  formatted prompt, retrieved memories, memory/system token counts, cost, and
  retrieval/LLM latency; write-only turns should not be treated like activation
  query turns.
- MemFail error analysis uses a short-circuit diagnosis chain: storage
  presence, summary/condition faithfulness, retrieval/composed recoverability,
  and invocation. CtxGov should extend this with action-parameter authority and
  promotion/retirement checks before blaming a whole memory system.
- AgentDoG code confirms that saved trajectories can be ingested with profile,
  user/agent/environment turns, thought/action fields, and actual executed
  action review. CtxGov should classify what happened, affected party,
  concrete effect, failure mode, risk consequence, and risk source, not only
  prompt risk or final answer text.
- CoALA PDF sharpens the safety boundary: retrieval, reasoning, and learning are
  internal actions; learning should be deliberate and role-scoped, and procedural
  memory changes are higher risk than semantic or episodic notes.
- MemLineage PDF sharpens lineage from memory-level trust to parameter-level
  authority: sensitive actions need tool/parameter projection policy, trusted or
  untrusted ancestry, and allow/refuse/require-user/strip-retry/repair-retry
  decisions. CtxGov should import this as saved receipts, not implement a
  cryptographic log first.
- The human-memory simulation PDF makes bottlenecking an objective, not an
  accident: a constrained memory contract needs a declared purpose, capacity,
  loss policy, and metric; otherwise compaction loss remains a failure.

2026-06-03 public companion eval feedback loop:

- `ctxgov/agent-context-evals` `v0.7.0` is now a public local evaluation
  artifact that Task Shard should reuse as an external-facing fixture pattern,
  not as runtime authority. Public links verified on 2026-06-03: CtxGov
  `v0.6.8`, companion `v0.7.0`, v0.7 results report, static live-report
  fixture, and project page.
- The companion suite contains 96 trace-shaped local cases across terminal
  logs, handoff summaries, AGENTS/Cursor/CLAUDE-style rules, release notes,
  GitHub PR/release/issues snippets, package registry manifests, local
  transcripts, and memory traces. Those source families map directly to future
  Task Shard overlays for workflow-script passports, import-shape contracts,
  hidden terminal failure, release integrity, rollback, source coverage, and
  model-state surface checks.
- Offline adapters now exist for GitHub PR/release/issues payloads,
  CI/terminal logs, rules files, package registry manifests, local transcripts,
  and memory trace metadata. Future Task Shard fixtures can mirror this adapter
  shape while staying local/offline/read-only.
- The useful research signal is not the synthetic score itself. v0.7 reports
  regex baseline F1 1.0, CtxGov heuristic F1 0.9583, and CtxGov doctor F1 1.0
  on trace-shaped local data; this proves scaffold coverage and evidence-span
  plumbing, not real-world benchmark performance. The Task Shard lane should
  use the report structure and error-analysis artifacts as a readiness pattern
  while continuing to require private saved traces and quality gates before any
  benchmark or workflow claim.
- The public artifact boundary remains strict: no workflow execution,
  worktree creation, provider/model call, target write, memory write, live
  adapter, public benchmark, security, adoption, provider-compatibility, or
  stable-MGP claim follows from the companion release.

## Purpose

Recent long-task agent systems show that the next scarce capability is not just
memory persistence. It is governed control over:

```text
task split -> per-shard context admission -> execution receipt
-> result merge -> replan -> next context injection
```

CtxGov should add this as a roadmap lane after v0.7.0. The lane should not make
CtxGov an agent runtime. It should make CtxGov the portable control plane that
explains why a long-task shard existed, which context it was allowed to see,
what it omitted, what result changed the plan, and which downstream behavior
can rely on the result.

2026-06-08 scale-profile update: Task Shard Context Control is also the
validation carrier for `scale_profile`. A shard fixture should declare whether
it is `local_single_user`, `team_project`, or `cluster_multi_tenant`, then
prove that selected/omitted/blocked refs, identity scope, policy grant,
final-state assertion, rollback, and deletion/expiry duties are preserved
through split -> context admission -> execution receipt -> merge -> replan.
The detailed 24-case scale-aware fixture proposal lives in
`docs/post-v0.7.0-scale-profile-governability-release-cycle-2026-06-08.md`.
This remains saved-trace/read-model work only and creates no workflow runtime,
worktree execution, provider/model call, target write, memory/backend write,
external compatibility claim, or public benchmark claim.

## Source Judgment

Checked source families:

- Claude Code dynamic workflows:
  https://claude.com/blog/introducing-dynamic-workflows-in-claude-code
- Claude Code parallel agents, context window, worktrees:
  https://code.claude.com/docs/en/agents
  https://code.claude.com/docs/en/context-window
  https://code.claude.com/docs/en/worktrees
- Cline task scoping and context compression:
  https://docs.cline.bot/core-workflows/task-management
- OpenHands condensers:
  https://docs.openhands.dev/sdk/arch/condenser
  https://docs.openhands.dev/sdk/guides/context-condenser
- SWE-agent summarizers:
  https://swe-agent.com/0.7/config/summarizers/
- Aider repo map:
  https://aider.chat/docs/repomap.html
- Plandex context management:
  https://docs.plandex.ai/core-concepts/context-management/
- Continue context providers:
  https://docs.continue.dev/customize/custom-providers
- DeepSeek context cache and sparse-attention serving:
  https://api-docs.deepseek.com/guides/kv_cache
  https://docs.vllm.ai/en/stable/features/deepseek_v32.html
- Chroma context rot:
  https://www.trychroma.com/research/context-rot
- Context as a Tool:
  https://arxiv.org/abs/2512.22087
- LongSeeker / Context-ReAct:
  https://arxiv.org/abs/2605.05191
- Runtime-Structured Task Decomposition:
  https://arxiv.org/abs/2605.15425

Fact judgment:

- Claude Code moved beyond one-off subagents: Dynamic Workflows, announced on
  2026-05-28, lets Claude write orchestration scripts, split work into many
  parallel subagents, verify results, save progress, and coordinate outside the
  conversation. This is a strong product signal that orchestration state is
  moving outside the prompt.
- Claude Code docs also verify the practical substrate: subagents use separate
  context windows and summarize back; worktrees isolate file edits; `/batch` is
  packaged subagents plus worktrees; `/context` and `/compact` expose context
  pressure and compaction behavior.
- Cline documents task scoping as a first-class practice: one task per goal,
  automatic compression near context limits, checkpoints, task history, and new
  task boundaries when context becomes noisy.
- OpenHands and SWE-agent focus on compression, not split governance:
  condensers/summarizers keep event histories and command outputs within token
  limits while preserving recent or important content.
- Aider, Plandex, and Continue are stronger references for context selection
  than for task splitting. Their reusable lesson is budgeted codebase maps,
  context providers, manual overrides, and relevant snippet selection.
- DeepSeek is a lower-layer signal: context caching and sparse attention improve
  long-context economics, but they do not decide task split, context admission,
  or replanning. Hardware progress reduces cost; it does not remove governance
  need.
- Chroma context rot and the recent context-management papers support the same
  conclusion: bigger context is not enough. Agents need active working-set
  control, omitted-context visibility, and benchmarked compression/split
  decisions.
- Runtime-Structured Task Decomposition is especially relevant: static
  decomposition can increase retry cost, while executable control logic that
  reruns only failed subtasks reduces retry cost. This directly supports a
  CtxGov product that evaluates split quality and failed-shard isolation rather
  than celebrating decomposition by itself.
- MemTrace is a stronger diagnostic signal than result-level memory
  benchmarks: it frames failures as operation-level causal paths through
  executable memory evolution graphs. For CtxGov, the transferable idea is not
  to own instrumentation, but to import or emit saved operation/variable trace
  overlays so Memory X-Ray and Task Shard reports can say where evidence was
  lost, corrupted, overgeneralized, omitted, or used under the wrong intent.
- MemGraphRAG is a stronger construction-layer signal than generic GraphRAG:
  it argues that fragment-level graph extraction lacks global corpus
  perspective and can create inconsistent, conflicting, fragmented graphs. For
  CtxGov, the transferable idea is an `Ontology Drift Passport` and graph-route
  consequence receipt, not a graph database or ontology builder.
- LongDS is the strongest current signal that long-running data-analysis agents
  fail because analytical state evolves across many turns. The transferable
  patterns are initial construction, state inheritance, state update,
  counterfactual perturbation, rollback, and multi-state composition. For
  CtxGov, this becomes an `AnalysisStateFrame` and state-ledger read model, not
  a data-science runtime.
- CoALA and Agent Skills sharpen the memory-role distinction behind task
  sharding: working, semantic, procedural, and episodic state should not share
  one activation policy. Procedural state such as skills, runbooks, and harness
  rules changes future execution and should get stronger admission than facts.
- MemFail adds a memory-specific fault plane: summary, storage, retrieval,
  activation/reasoning, action-parameter, promotion, and retirement failures
  should be distinguished before blaming a whole shard or adding more context.
- AgentDoG and MemLineage add trajectory and lineage pressure: future shard
  receipts should show risk origin, harm surface, and whether sensitive action
  parameters descend from trusted or untrusted memory, without turning CtxGov
  into a live safety/runtime enforcement system.
- The human-memory simulation benchmark warns that perfect recall is not always
  the desired product behavior. Future shard tests should allow purposeful
  bottleneck contracts when the downstream app is simulating limited memory or
  testing robustness under constrained recall.
- Deeper MemFail, AgentDoG, CoALA, MemLineage, and human-memory PDF/code reading
  turns the previous high-level memory taxonomy into concrete operation
  standards: write/query separation, raw-query vs formatted-prompt refs,
  selected/retrieved/omitted memory refs, latency/cost/token split,
  activation disclosure, short-circuit failure diagnosis, learning deferral,
  sensitive parameter authority, repair-or-refuse decisions, and
  actual-action trajectory review.
- Harness-engineering sources converge on local legibility, deterministic
  checks, progressive disclosure, isolated execution, and feedback loops.
  Harness-Bench and the non-monotone harness-sensitivity paper warn that
  model capability should be reported at the model-harness configuration level
  and that stricter or more verbose harnessing is not universally better.

## Roadmap Decision

Update the post-v0.7.0 roadmap. Keep Memory X-Ray first, but add Task Shard
Context Control as the next high-ROI lane that connects Session Continuity,
Memory X-Ray, and OSS Efficiency Benchmark.

Recommended order:

1. Keep `Memory X-Ray` as the first proof surface for memory mutation and
   activation governance.
2. Add `Task Shard Context Control` as the next private design and fixture
   lane. It governs long-task split, per-shard context injection, compaction,
   merge, and replan artifacts.
3. Integrate the lane into `OSS Efficiency Benchmark` so savings are counted
   only when task success, source coverage, governance coverage, and merge
   quality are same-or-better.
4. Defer live workflow orchestration, provider adapters, worktree execution,
   and agent launching to ecosystem runtimes. CtxGov imports receipts and
   previews plans first.

This is an addition, not a refactor that overturns MGP. The core MGP concept
becomes:

> MGP governs which evidence, memory, context shard, model-state surface, or
> workflow result may affect which downstream consequence.

## Current Open Design Problems

The deeper source review leaves these core questions unresolved. They should be
kept as private/offline fixture targets, not runtime work:

1. `extraction_quality`: source refs exist, but the design still needs a
   deterministic standard for when raw episodes, tool outputs, retrieved rows,
   graph edges, summaries, or trajectory events are allowed to become candidate
   memory. The standard should preserve raw input refs, formatted prompt refs,
   memory snapshots, retrieved refs, selected refs, omitted refs, and
   source-confusion risk.
2. `activation_minimality`: Memory X-Ray can report risk and source gaps, but
   the next standard should prove the smallest activated memory/context set
   that preserves correctness, governance, source coverage, rollback, and
   consequence ceiling.
3. `compaction_distortion`: Context Budget Ledger reports token pressure and
   compaction-loss risk, but it should add a consequence-weighted distortion
   budget: cite/default/action/merge/replan/public-claim channels need
   different non-loss constraints.
4. `write_promotion_boundary`: The design distinguishes write, activation,
   composition, promotion, and retirement, but it still needs transition visas
   for episode -> fact -> summary -> procedural lesson -> default/tool route/
   team policy/train-or-publish signal.
5. `automation_calibration`: Policy grants can reduce human review, but every
   automated allowance or downgrade needs overblock/underblock, owner override,
   false-allow, false-quarantine, and review-minutes-saved calibration before
   it can expand authority.
6. `lineage_to_parameter_authority`: MemLineage-style ancestry should not be
   copied as cryptographic infrastructure first. The high-ROI standard is to
   import lineage refs and decide whether sensitive parameters may be allowed,
   refused, require user confirmation, stripped, repaired, or retried.

Near-term safe automation path:

```text
saved trace -> operation trace -> deterministic policy compilation
-> required tests -> counterfactual/minimality probes
-> automation decision receipt -> owner override calibration
```

This path can become more intelligent by using LLMs only to propose conflict
explanations, expected effects, omitted evidence, and repair candidates. The
authority boundary stays deterministic: no LLM proposal grants write, default,
action, promotion, publication, provider/model, target-write, or stable-MGP
authority without a matching policy grant, tests, source refs, and rollback.

## Product Designs

Product naming follows
`docs/product-taxonomy-and-release-ladder-2026-06-02.md`: the designs below are
product surfaces under `Task Shard Context Control`, not new product lines
unless they later pass the taxonomy split test.

### 1. Task Shard X-Ray

High ROI, core CtxGov product.

Input:

- saved traces, task plans, worktree logs, PR branches, subagent summaries,
  context packs, OpenHands condensations, SWE-agent summarized observations,
  Aider/Plandex/Continue context maps, or Claude workflow artifacts when
  available.

Output:

- `TaskShardPlan`
- `ShardContextVisa`
- `ShardResultReceipt`
- `ShardMergeReceipt`
- `ReplanTriggerReceipt`
- `ContextMinimalityProof`

User-visible value:

- "This long task split into 9 shards. These 3 were independent. These 2 had
  hidden file overlap. This shard saw stale context. This result was merged
  without verification. This omitted source probably caused the rework."

Why it is defensible:

- Existing tools can run agents, but they usually do not prove split quality,
  omitted context, authority boundaries, merge safety, and rollback in one
  portable object.

### 2. Context Budget Ledger

High ROI, core CtxGov product with hardware-aware value.

Output:

- `ContextBudgetLedger`
- `CacheStabilityReceipt`
- `CompactionLossCard`
- `WorkingSetRiskCard`

It records:

- selected, omitted, searchable-only, compacted, deleted, and blocked context;
- token budget and cache-stability risk;
- source recoverability after compaction;
- which context was injected into each shard;
- whether a larger window would have reduced or increased retrieval burden.

This turns "context window is full" into a governance and performance report.

### 3. Workflow Script Passport

Medium-high ROI, ecosystem-facing product.

Purpose:

- Inspect orchestration scripts, not execute them.
- Record which loop, fan-out, verifier, retry, checkpoint, and merge stages the
  script claims to have.
- Distinguish script-held state from prompt-held state.

Useful for:

- Claude dynamic workflows,
- user-authored workflow scripts,
- future Codex/Cline/OpenHands style orchestrators,
- worktree-based open-source orchestrators.

Do not build the orchestrator first. Build the passport and validator.

### 4. Shard Context Rehearsal

High ROI because it reuses existing Session Continuity machinery.

It extends `context-injection rehearsal` from new-session startup into
per-shard startup:

```text
task -> shard plan -> per-shard minimal context packet
-> blocked/live operation transcript -> merge plan -> replan decision
```

This should stay preview-only until a separate approval receipt allows any live
agent/session launch.

### 5. Long-Task Governance Benchmark

High impact, benchmark-first.

Add to the private benchmark suite before any public claim:

- `split_quality`: shards are independent or dependencies are explicit.
- `context_minimality`: injected context is the smallest set preserving success.
- `omitted_critical_context`: high-value omitted refs are detected.
- `compaction_fidelity`: compressed history preserves decisions, blockers,
  file refs, and source anchors.
- `replan_accuracy`: failed or surprising shard results trigger the correct
  plan update.
- `merge_safety`: shard outputs do not silently conflict.
- `retry_isolation`: failed subtasks rerun without replaying unrelated work.
- `context_rot_resistance`: performance does not depend on stuffing all
  history into the active prompt.
- `cache_stability`: stable prefixes and reusable context stay stable when
  possible, but cache hits never become authority.

### 6. Analysis State Ledger

High ROI for data-analysis, notebook, SQL, and long-lived tool workflows.

Input:

- saved notebook or tool traces, code-cell outputs, SQL/dataframe snapshots,
  derived table/chart refs, formula refs, parameter changes, baseline
  decisions, reset logs, rollback logs, and validation receipts.

Output:

- `AnalysisStateFrame`
- `StateEvolutionFlightRecorder`
- `ResetBenefitProbe`
- `RollbackFidelityReceipt`
- `CounterfactualIsolationCard`
- `StateCompositionCard`
- `HarnessPressurePassport`

User-visible value:

- "This result depends on cleaned table S01, formula F03, and baseline
  threshold T110. The counterfactual branch at S18 changed only T110->T100 and
  did not overwrite the baseline. The rollback to S12 is source-backed; a full
  reset would likely destroy valid derived state."

Design rule:

- Do not run notebooks or data agents. Import saved state evidence and validate
  lineage, branch isolation, rollback fidelity, reset decision quality, and
  deterministic harness pressure.

### 7. Causal Trace Autopsy

High ROI, shared with Memory X-Ray.

Input:

- saved memory traces, task-shard traces, condenser events, graph construction
  artifacts, context packets, merge receipts, failed answers, and expected
  answers or reviewer verdicts.

Output:

- `EvidenceExtent`
- `OperationNode`
- `VariableNode`
- `ConsequenceShard`
- `AttributionReceipt`
- `CounterfactualRepairCard`

User-visible value:

- "The answer failed because shard 4 used a compacted summary that dropped the
  source version ref. Replacing that operation output with the raw evidence
  rescues the merge, while loading two omitted refs does not. The fix is to
  demote this summary and require source recovery before merge authority."

Design rule:

- A causal trace is evidence, not proof. It can guide repair, quarantine, and
  benchmark cases, but it does not grant runtime or memory-write authority.

### 8. Ontology Drift Passport

Medium-high ROI for GraphRAG and compiled-knowledge ecosystems.

Input:

- saved GraphRAG construction snapshots, extracted entities/relations,
  community summaries, concept merge logs, local/global retrieval paths,
  vector fallback records, and answer citations.

Output:

- `OntologySnapshotPassport`
- `ConceptMergeDecision`
- `RelationDriftCard`
- `GraphFragmentationCard`
- `OntologyAwareRetrievalReceipt`

User-visible value:

- "This graph answer relied on a high-degree bridge relation created by local
  extraction. A conflicting concept merge was available but omitted. The graph
  path may inform the answer, but it cannot default a project policy or action
  until the relation drift is reviewed."

Design rule:

- Do not build GraphRAG. Inspect graph construction and retrieval artifacts as
  candidate evidence routes with source, drift, omission, and consequence
  ceilings.

### 9. Cognitive Operation Standards

High ROI as a shared standard across Memory X-Ray, Task Shard, and OSS
Efficiency, not as a new product line.

Output:

- `MemoryOperationTrace`
- `ShortCircuitMemoryDiagnosis`
- `LearningActionVisa`
- `SensitiveParameterAuthorityReceipt`
- `ActualActionTrajectoryReview`
- `MemoryBottleneckContract`

Rules:

- Separate write-only turns, activation-query turns, finalization turns, and
  sensitive-action turns.
- Record raw input, formatted prompt ref, all-memory snapshot ref when
  available, retrieved refs, selected/omitted/blocked refs, token/time/cost
  split, and whether the answer disclosed which memory it used.
- Diagnose in order: storage, summary/faithfulness, retrieval, invocation,
  action-parameter authority, promotion, and retirement.
- Treat learning as a deliberate action with role-scoped read/write authority;
  procedural learning requires owner review and non-regression evidence.
- For sensitive actions, evaluate the actual tool call and parameter lineage;
  permit allow, refuse, require-user, strip-and-retry, or repair-and-retry.
- Use purposeful bottlenecks only when the fixture declares objective,
  capacity, loss policy, and metric.

## Layer Split

| Layer | Put here | Keep out |
| --- | --- | --- |
| Adapter / harness | Offline importers for workflow logs, task histories, worktree metadata, subagent summaries, condenser events, repo maps, context providers, saved traces, notebook/cell logs, SQL/dataframe snapshots, reset logs, rollback logs, lints, tests, E2E receipts, smartcomment-style operation graphs, memory-system get/update/finalize traces, and AgentDoG-style trajectories. | Starting agents, worktrees, provider sessions, notebooks, devboxes, live tracing adapters, or runtime workflows. |
| Runtime | External systems execute Claude/Codex/Cline/OpenHands/Aider/Plandex/DeepSeek workflows. | CtxGov does not become the orchestrator. |
| Projection / read model | Task shard plans, context visas, budget ledgers, compaction-loss cards, result receipts, merge receipts, workflow passports, analysis state ledgers, reset probes, rollback fidelity receipts, harness pressure passports, MemoryOperationTrace, ShortCircuitMemoryDiagnosis, LearningActionVisa, SensitiveParameterAuthorityReceipt, ActualActionTrajectoryReview, and MemoryBottleneckContract. | Raw runtime truth without source refs. |
| Algorithm / eval | Split-quality scoring, minimality proofs, replan triggers, merge-conflict probes, omitted-context probes, retry-isolation metrics, state-lineage scoring, dependency-chain risk, reset decision quality, harness verbosity risk, operation-stage attribution, counterfactual rescue, ontology drift checks, write/query separation checks, short-circuit memory diagnosis, activation disclosure checks, parameter-authority decisions, and learning-deferral checks. | LLM-only self-judgment, more reasoning tokens, more retrieved memories, or more prompt rules as proof. |
| Retrieval | Candidate context generation, repo maps, provider/context-source manifests, selected/omitted refs, state-frame refs, raw-evidence refs, memory snapshot refs, retrieved-memory refs, formulas, test failures, and validation receipts. | Permission to inject or default-promote context. |
| Storage | Immutable evidence refs, hashes, trace ids, state frame metadata, environment digests, parent/branch edges, operation hashes, formatted-prompt refs, memory-snapshot refs, trajectory refs, parameter-lineage refs, receipts, rollback plans, tombstones. | Mutable memory, notebook, dataframe, workflow, or worktree state as canonical truth. |

## MGP Upgrade

Add a sixth and seventh gate beside memory write, activation, composition,
promotion, and retirement:

6. `ContextExecutionAdmission`: split, inject, compact, summarize, delete,
   rehydrate, merge, and replan context for long-task execution.
7. `CognitiveOperationAdmission`: retrieve, reason, learn/write, finalize,
   inject, act, repair, or retire behavior-changing cognitive state.

Future fields:

- `task_id`
- `shard_id`
- `state_frame_id`
- `state_parent_refs`
- `state_branch_kind`
- `state_transition_kind`
- `split_reason`
- `dependency_refs`
- `source_dataset_refs`
- `derived_artifact_refs`
- `parameter_binding_refs`
- `assumption_binding_refs`
- `environment_digest`
- `owned_paths`
- `shared_paths`
- `read_only_paths`
- `selected_context_refs`
- `omitted_context_refs`
- `searchable_only_refs`
- `compacted_event_refs`
- `context_budget`
- `cache_stability`
- `compaction_loss`
- `rollback_parent_ref`
- `reset_policy_hint`
- `operation_kind`
- `turn_purpose`
- `memory_role`
- `read_only`
- `should_grade`
- `raw_input_ref`
- `formatted_prompt_ref`
- `all_memory_snapshot_ref`
- `retrieved_memory_refs`
- `memory_tokens`
- `system_prompt_tokens`
- `retrieval_time`
- `llm_time`
- `activation_disclosure`
- `learning_deferral_policy`
- `failure_plane`
- `parameter_projection`
- `parameter_authority_decision`
- `source_monitoring`
- `source_confusion_risk`
- `consequence_weighted_distortion_budget`
- `policy_grant_ref`
- `automation_calibration_ref`
- `memory_lifecycle_transition`
- `actual_action_effect`
- `affected_party`
- `result_refs`
- `merge_conflict_refs`
- `replan_trigger`
- `operation_trace_refs`
- `counterfactual_probe_refs`
- `counterfactual_isolation`
- `state_composition_refs`
- `harness_pressure_refs`
- `ontology_snapshot_refs`
- `consequence_shard_id`
- `maximum_consequence`
- `approval_ceiling`
- `rollback`

Core rule:

> A task shard is not a chunk. It is the smallest governed execution boundary
> that can explain input context, owned state, result authority, and rollback.

2026-06-03 refinement:

> A governed shard is also not necessarily a task. It is the smallest
> consequence-bearing evidence unit that can explain source extent, operation
> lineage, selected and omitted refs, allowed effect, and repair path.

2026-06-03 LongDS/harness refinement:

> A long-running analysis state is also not just context. It is a versioned
> state frame whose parent, branch, parameter bindings, derived artifacts,
> validation receipts, reset policy, and rollback parent must be inspectable
> before downstream results inherit it.

2026-06-03 cognitive operation refinement:

> A memory/context operation is not a memory item. It is a purpose-labeled
> action whose input, retrieved state, omissions, activation, learning decision,
> sensitive parameters, actual effect, and repair path must be inspectable before
> downstream behavior inherits it.

## Product Position

Do not position this as "we run 100 agents." That market is already heating up.

Position it as:

> CtxGov tells teams whether a long-running agent workflow used the right
> context, split safely, preserved evidence, and merged results without hidden
> authority drift.

High-ROI ecosystem products:

1. `Task Shard X-Ray` for Claude dynamic workflows, `/batch`, Cline tasks,
   OpenHands runs, and worktree orchestrators.
2. `Context Budget Ledger` for token, cache, and source-recovery diagnostics.
3. `Shard Context Rehearsal` for previewing per-shard injection before a live
   workflow.
4. `Workflow Script Passport` for inspecting orchestration scripts and
   verifying loop/merge/checkpoint claims.
5. `Long-Task Governance Benchmark` for same-or-better correctness,
   governance, source coverage, split quality, context minimality, merge
   safety, replan accuracy, and efficiency.
6. `Analysis State Ledger` for state-frame lineage, counterfactual isolation,
   reset decision quality, rollback fidelity, and multi-state composition.
7. `Harness Pressure Passport` for deterministic checks, quiet-success /
   loud-failure output, evaluator independence, and harness verbosity risk.
8. `Causal Trace Autopsy` for operation-stage failure attribution and
   counterfactual repair over memory/context/task traces.
9. `Ontology Drift Passport` for GraphRAG and compiled-knowledge construction
   artifacts.
10. Cross-surface `Cognitive Operation Standards` for write/query separation,
    operation traces, short-circuit memory diagnosis, learning deferral,
    sensitive parameter authority, and actual-action review.

Lower-ROI work:

- Building another worktree manager.
- Building another subagent runtime.
- Building another repo map or vector retriever.
- Claiming context-window improvements without omitted-context tests.
- Optimizing token use before success, source coverage, merge safety, and
  governance coverage pass.
- Adding more reasoning steps, prompt rules, skills, or subagents to compensate
  for unmodeled state lineage.
- Treating reset as universally helpful or harmful instead of measuring reset
  decision quality.
- Treating memory failures as retrieval problems when the real fault is summary
  faithfulness, invocation, parameter authority, unsafe learning, or procedural
  activation.

## Current Boundary

No task from this document enters the current private v0.7.0 execution unless
an owner explicitly records it as a current-version task. The owner-approved
post-v0.7.0 private/offline implementation tasks above are now recorded as
local fixtures, module functions, CLI summaries, tests, and private gate
scripts only. Safe current actions:

- documentation,
- verified-source indexing,
- private fixture planning,
- roadmap sequencing,
- local offline fixture validation/evaluation when explicitly approved.

Blocked:

- live workflow execution,
- live worktree creation,
- live provider/model call,
- target write,
- memory backend write,
- automatic approval,
- public benchmark/adoption/compatibility/stable-MGP claim.

## Test, Audit, Rollback

test_constraint:

- Future implementation must include positive and negative fixtures for split
  quality, context minimality, omitted critical context, compaction fidelity,
  replan accuracy, merge safety, retry isolation, context-rot resistance, and
  cache stability. New causal-trace fixtures must also cover operation-stage
  attribution, omitted-evidence recall, counterfactual repair, raw-evidence
  recoverability, ontology drift, and graph fragmentation before any public
  claim. New state-ledger fixtures must cover initial construction,
  inheritance, update, counterfactual perturbation, rollback, multi-state
  composition, reset-helpful/reset-harmful cases, deterministic harness
  backpressure, and harness verbosity regressions. New cognitive-operation
  fixtures must cover write-only vs activation-query separation, raw-query vs
  formatted-prompt refs, memory snapshot and retrieval refs, summary
  faithfulness, retrieval recoverability, invocation correctness,
  activation disclosure, learning deferral, procedural write review,
  sensitive-parameter authority, strip/repair/refuse decisions, actual-action
  effect, purposeful bottleneck objective fit, source-monitoring accuracy,
  source-confusion detection, consequence-weighted distortion budgets,
  policy-grant calibration, and lifecycle transition visas.

audit_constraint:

- Record primary URLs, query time, source freshness caveats, selected/omitted
  evidence, no-runtime flags, no-provider/model-call flags, no-target-write
  flags, no-memory-write flags, and no-public-claim flags in the verified
  external research index. For MemTrace-like mechanics, record whether details
  came from primary paper text, secondary summaries, or owner-supplied notes.

rollback_constraint:

- Delete or supersede this document and remove active/roadmap/index references.
  No current v0.7.0 runtime, provider state, worktree, target file, memory
  backend state, public claim, or stable MGP posture changes.
