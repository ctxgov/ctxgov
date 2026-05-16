# CtxVault Safe Rewrite Cookbook

Status: public-safe local draft. Not published by this file change.

Use this cookbook before a case-study preview becomes public copy. The goal is
to keep useful source-backed statements while blocking claims that need stronger
evidence.

| Unsafe Claim | Blocked Reason | Safe Rewrite | Evidence Needed To Unblock |
| --- | --- | --- | --- |
| This project is secure. | Security judgment requires a security review receipt. | The public docs describe security-related surfaces; CtxVault has not evaluated security. | Security review, scope, date, reviewer, rollback. |
| This project is fast. | Performance claim requires benchmark or measurement evidence. | No performance claim is made by this preview. | Benchmark design, run receipt, limits, rollback. |
| This project is compatible with CtxVault. | Compatibility requires runtime or adapter evidence. | This preview maps source facts to CtxVault governance constraints without running compatibility checks. | Adapter/runtime run receipt and failure boundary. |
| The maintainers endorse this case study. | Endorsement requires explicit maintainer evidence. | No maintainer endorsement is claimed. | Maintainer statement and public correction path. |
| CtxVault validated the target runtime. | Runtime validation requires a separate runtime receipt. | CtxVault did not run target code in this preview. | Runtime command, sandbox, logs, no-write proof, rollback. |
| The case study proves stable MGP support. | Stable protocol claims require conformance policy. | This preview uses private governance concepts and makes no stable protocol claim. | Conformance suite, versioning, compatibility policy. |
| The AI can act on this context. | Action authority requires side-effect approval. | The preview is read-only and grants no action authority. | Action gate, target boundary, owner approval, rollback. |

## Rule

If a statement implies quality, security, performance, compatibility,
maintainer intent, stable protocol behavior, runtime behavior, target writes,
provider/model calls, memory promotion, or action authority, block it until a
receipt exists.
