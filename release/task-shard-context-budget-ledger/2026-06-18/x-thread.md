# X Worksheet

Status: worksheet only. Not posted.

1/ Long-running AI agent tasks fail when context is split, summarized, cached,
or omitted without an auditable boundary.

CtxGov's next local milestone is a Task Shard Context Budget Ledger.

2/ The demo reads a saved long-agent task plan and reports selected, omitted,
searchable-only, and compacted context refs per shard.

It also shows per-shard token budgets.

3/ Cache hits are not authority.

Larger context windows are not authority.

The report keeps merge and replan risk visible before downstream work relies on
a shard result.

4/ Boundary:

no workflow execution
no worktree creation
no provider call
no target write
no memory write
no SARIF upload
no benchmark, savings, adoption, security, support, or compatibility claim

5/ Public page candidate:

https://ctxgov.github.io/ctxgov/task-shard-context-budget-try-in-5-minutes.html

Question: what proof should exist before a long-running agent shard is trusted?
