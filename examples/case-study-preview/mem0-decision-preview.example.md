# mem0 Decision Preview Example

Status: public-safe filled example using already published aggregate CtxVault
evidence. This example does not fetch, clone, inspect, install, run, or write
to `mem0ai/mem0`.

## Source Boundary

- Target: `mem0ai/mem0`
- Pinned ref: `70bc9e51d57fe005d02b7b6d81b56476bade3cb3`
- Source: public v0.6.0 sanitized extract and v0.6.1 local source-fact recheck
- Side effects: no target write, no provider/model call, no runtime, no adapter,
  no MCP server, no memory promotion

## Decision Preview

| Decision | Allowed | Blocked | Missing | Rollback |
| --- | --- | --- | --- | --- |
| Public claim | Source-bound statements about public metadata and aggregate CtxVault counts. | Quality, security, performance, compatibility, maintainer endorsement, benchmark, runtime, stable protocol, target-write claims. | Fresh source facts before any new publication. | Delete or supersede the public-safe extract. |
| Context packet | Selected and caveated aggregate evidence from the sanitized extract. | Full raw receipt, private local paths, uninspected omitted refs, credential-shaped paths as authority. | Full omitted distribution is not public evidence. | Regenerate from the receipt or delete local preview artifacts. |
| Memory | None. | Durable memory promotion and reusable summary authority. | Lifecycle decision, contradiction policy, delete path. | No memory state exists. |
| Action | None. | Target writes, runtime execution, adapter execution, provider/model calls, outreach. | Owner approval and side-effect rollback. | No target/action state exists. |

## Evidence Objects

| Ref | State | Reason | Authority Layer Blocked | Safe Rewrite Or Next Check | Rollback Ref |
| --- | --- | --- | --- | --- | --- |
| `release/v0.6.0/public-influence/mem0-public-case-study-extract.json` | selected | Public-safe aggregate extract already published. |  | Use only aggregate governance-shape statements. | Supersede public-safe extract. |
| `docs/images/platform/api-key.png` | blocked | Credential-shaped public path marker. | context, memory, action | Describe as a path-only boundary, not a usable secret. | Keep blocked in extract. |
| `omitted_count=1217` | omitted | Full omitted distribution is not public evidence. | claim | Say sampled omitted visibility only. | Supersede extract after a fuller receipt. |

## Safe Rewrites

| Unsafe Claim | Blocked Reason | Safe Rewrite |
| --- | --- | --- |
| `mem0 is secure.` | Security judgment requires a security review. | The public docs include security-adjacent surfaces; CtxVault has not evaluated security. |
| `mem0 is compatible with CtxVault.` | Compatibility requires runtime or adapter evidence. | CtxVault published a read-only governance case study over sanitized public metadata. |
| `mem0 maintainers endorse this case study.` | Endorsement requires explicit maintainer evidence. | No maintainer endorsement is claimed. |
| `CtxVault validated mem0 runtime behavior.` | Runtime validation requires a separate runtime receipt. | CtxVault did not run mem0 code or an adapter in this case study. |

## Final Boundary

This example is a teaching artifact for downstream OSS adoption. It creates no
new public claim, target write, runtime behavior, provider/model call, memory
state, stable protocol claim, GitHub issue, pull request, release, or outreach.
