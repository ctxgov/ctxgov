# CtxVault v0.3.2 Deterministic Demo

This Space demonstrates CtxVault's v0.3.2 trust loop with toy local sources:

`local sources -> context slices -> source-grouped selection -> privacy preflight -> projection receipts`

It is intentionally narrow and inspectable:

- no user uploads;
- no private user data;
- no model calls;
- no embeddings;
- no vector database;
- no remote provider;
- no live connector.

The demo should show three things clearly:

- which context slices were selected;
- which candidate was withheld and not projected;
- which receipts passed inspection.

## Local Preview

From the repository root:

```bash
python3 spaces/huggingface/v032-deterministic-demo/app.py
```

Install `gradio` only for local UI preview. The deterministic demo itself does
not require Gradio.

## Deployment Boundary

Before deployment, confirm:

- generated output still uses toy sources only;
- the fake secret sentinel is not projected;
- public summary does not expose temp filesystem paths;
- the receipt inspection report passes;
- public copy does not claim model, vector, remote provider, official plugin, or
  live connector support.
