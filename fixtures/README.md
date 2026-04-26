# CtxVault Fixtures

This directory holds small canonical fixtures that future validators and tests
can load without depending on any external runtime.

## Current coverage

- `core/`
  - deterministic core object examples promoted from the earlier schema bundle,
    including workstream and workstream-candidate examples
- `evidence/`
  - evidence-first audit objects for claim capture, evidence linking, audit runs,
    adapter capability profiles, and plugin manifests
- `controls/`
  - backup receipt, protection policy, and rollback examples for deterministic
    safety gates, plus projection receipts for generated external outputs

The first purpose of these fixtures is to lock object shapes, naming, and
governance fields before implementation code spreads across the repo.

The control fixtures are contract examples, not proof that a live backup check
has actually run for the current workspace.

Run the local validator with:

```bash
python3 scripts/validate_fixtures.py
```
