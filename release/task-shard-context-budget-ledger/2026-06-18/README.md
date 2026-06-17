# Task Shard Context Budget Ledger

Date: 2026-06-18

Status: local/offline release candidate. This pack is not a public claim source
until owner approval. It is not a workflow runtime, worktree executor,
provider/model integration, target writer, memory/backend writer, benchmark,
savings report, adoption claim, security claim, compatibility/support claim,
package, SARIF upload, HN post, LinkedIn post, X post, or stable protocol.

## Milestone

Task Shard Context Budget Ledger / Shard Context Rehearsal.

## One-Command Demo

```sh
python3 scripts/run_task_shard_context_budget_demo.py --input examples/task-shard-context-budget/
```

The demo reads a saved long-agent task plan and writes local reports under:

```text
.ctxvault/task-shard-context-budget/
```

## Narrow Claim

CtxGov can report selected, omitted, searchable-only, and compacted context
refs per saved task shard, plus per-shard context budgets and local risk cards
for cache authority, compaction, merge, and replan boundaries.

## Verification

```sh
python3 scripts/check_task_shard_context_budget_final_preflight.py
python3 scripts/check_task_shard_context_budget_social_draft_drift.py
python3 -m unittest tests.test_task_shard_context_budget_hn_candidate
```

## Manual Boundary

Owner approval is required before commit, push, Pages deploy, HN submission,
LinkedIn post, X post, or any external publication action.
