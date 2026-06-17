# LinkedIn Worksheet

Status: worksheet only. Not posted.

Long-running AI agent tasks fail when context is split, summarized, cached, or
omitted without an auditable boundary.

The next CtxGov milestone is a local Task Shard Context Budget Ledger.

It reads a saved long-agent task plan and reports:

- which refs each shard is allowed to see
- which refs were omitted
- which refs are searchable-only
- which events were compacted
- the per-shard token budget
- where cache, merge, and replan risk needs review

The local demo does not execute workflows, create worktrees, call providers,
write targets, write memory, publish SARIF, or claim benchmark, savings,
adoption, security, support, or provider compatibility.

That is the product stance: context budgets are evidence boundaries, not a
license to overclaim efficiency or autonomy.

Question for people building long-running agents and developer tooling:
what proof would you require before trusting a task shard's context budget?
