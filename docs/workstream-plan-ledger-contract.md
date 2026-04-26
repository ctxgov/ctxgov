# Workstream Plan-Ledger Contract

`ctxvault` publishes workstream state to `plan-ledger` through stable receipt
files, not by mutating ledger state directly.

## Public Scope

The public contract is limited to receipt and artifact interoperability:

- `ctxvault_workstream_candidate_receipt`
- `ctxvault_workstream_receipt`

## Stable Receipt Fields

Candidate receipts expose:

- `candidate_id`
- `candidate_ref`
- `proposal_state`
- `candidate_for`
- `confidence`
- `session_ref_count`
- `episode_ref_count`
- `knowledge_ref_count`
- `task_labels`
- `recurring_terms`
- `plan_ledger_artifact`

Workstream receipts expose:

- `workstream_id`
- `workstream_ref`
- `status`
- `approval_state`
- `session_ref_count`
- `episode_ref_count`
- `knowledge_ref_count`
- `derived_from`
- `task_labels`
- `recurring_terms`
- `plan_ledger_artifact`

## Suggested Flow

1. Build a read-only preview in `ctxvault`.
2. Create a durable `WorkstreamCandidate`.
3. Review and promote it into a durable `Workstream`.
4. Emit the appropriate receipt.
5. Register that receipt in `plan-ledger`.

The contract here is the shape of the receipt and artifact payload, not any
private release or operator workflow that may exist outside the public core.
