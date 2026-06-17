# HN Worksheet

Status: worksheet only. Not posted.

title: Show HN: CtxGov - audit context budgets for long-running AI agent tasks
url: https://ctxgov.github.io/ctxgov/task-shard-context-budget-try-in-5-minutes.html
text: empty

## First Comment Draft

This follows the Memory State Influence Boundary report.

The demo is local/offline and reads a saved long-agent task plan.

It reports selected, omitted, searchable-only, and compacted context refs per
shard.

It includes a context budget ledger and non-mutating shard context rehearsal.

It does not execute workflows, create worktrees, call providers, write targets,
write memory, publish SARIF, or claim benchmark/savings/adoption/security/
provider compatibility.

The useful question is whether a long-running agent task can prove which
context each shard was allowed to see before downstream work relies on it.
