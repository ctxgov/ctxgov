# v0.5.0 Governed Context Projection Example

Status: v0.5.0 public release artifact.

Governed context projection for AI work.

Boundary phrase for publication review: no target repository writes and no provider/model execution.

This example is synthetic and sanitized. It demonstrates the v0.5.0 evidence ->
decision -> projection -> receipt shape without exposing private local paths,
private receipts, raw OSS source excerpts, provider/model outputs, or target
repository writes.

## Files

- `packet.json`: synthetic reviewed evidence packet.
- `projection-preview/INDEX.md`: agent-facing projection preview index.
- `projection-preview/caveated.md`: useful context retained with caveats.
- `projection-preview/blocked.md`: candidate context withheld from projection.
- `projection-preview/receipt.json`: receipt proving source refs, routes,
  no-write boundaries, and rollback.

## What It Shows

1. Evidence starts as candidate context.
2. Review decisions caveat or block candidate material.
3. Projection material is generated from reviewed decisions only.
4. The receipt records selected, caveated, blocked, omitted, and not-done
   states.
5. Rollback is deleting the example projection; no source repository is
   mutated.

## Not Claimed

Do not use this example to claim benchmark results, reliability improvement,
adapter support, runtime support, provider/model compatibility, hardware/cost
benefits, automatic repository optimization, stable Memory Governance Protocol,
Memory OS behavior, RAG replacement, hallucination prevention, or security
certification.
