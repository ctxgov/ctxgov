# Conflict Edition Adjudication Sample

This is a deterministic, pathless audit sample for the Conflict Edition report.
It is not a benchmark, runtime precedence result, security review, or project-quality claim.

- Report ID: `soc_conflict_6098a3b8c7176f99`
- Checked at: `2026-06-29T00:00:00Z`
- Sample size: `12`
- Adjudication counts: `accepted`:2, `needs_refinement`:10
- Evidence tiers: `instruction_config_only`:2, `mixed_instruction_config_and_readme_docs`:7, `other_context_only`:1, `readme_docs_only`:2

## Labels

- `accepted`: The sampled finding is suitable as a review-needed declared-conflict signal within the stated report boundary.
- `needs_refinement`: The sampled finding should remain caveated or be manually reviewed before it supports external messaging.
- `false_positive`: The sampled finding should be excluded from external messaging unless rechecked and corrected.

## Sample

### gemini-cli / ccm_0004_approval_conflict

- Type: `approval_conflict`
- Evidence tier: `other_context_only`
- Adjudication: `needs_refinement`
- Source tier mix: `other_context`:1
- Reason: The evidence tier is lower-authority or unclassified and needs manual review before external messaging.
- Release use: Keep in appendix or local receipts until manually reviewed.

### openai-agents-python / ccm_0003_execution_conflict

- Type: `execution_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:2, `other_context`:7, `readme_or_docs`:8
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### continue / ccm_0001_network_conflict

- Type: `network_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:1, `other_context`:1, `readme_or_docs`:15
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### langgraph / ccm_0004_precedence_missing

- Type: `precedence_missing`
- Evidence tier: `instruction_config_only`
- Adjudication: `accepted`
- Source tier mix: `instruction_or_config`:2
- Reason: The signal is sourced only from instruction/config surfaces within the declared-conflict boundary.
- Release use: May support aggregate review-needed counts, but not runtime, security, quality, or compatibility claims.

### opencode / ccm_0004_publish_conflict

- Type: `publish_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:2, `readme_or_docs`:5
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### opencode / ccm_0005_scope_conflict

- Type: `scope_conflict`
- Evidence tier: `instruction_config_only`
- Adjudication: `accepted`
- Source tier mix: `instruction_or_config`:14
- Reason: The signal is sourced only from instruction/config surfaces within the declared-conflict boundary.
- Release use: May support aggregate review-needed counts, but not runtime, security, quality, or compatibility claims.

### crewai / ccm_0006_sensitivity_boundary_conflict

- Type: `sensitivity_boundary_conflict`
- Evidence tier: `readme_docs_only`
- Adjudication: `needs_refinement`
- Source tier mix: `readme_or_docs`:16
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### continue / ccm_0002_target_write_conflict

- Type: `target_write_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:1, `other_context`:2, `readme_or_docs`:22
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### graphiti / ccm_0002_target_write_conflict

- Type: `target_write_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:2, `readme_or_docs`:9
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### goose / ccm_0003_execution_conflict

- Type: `execution_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:2, `other_context`:1, `readme_or_docs`:8
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### cline / ccm_0002_target_write_conflict

- Type: `target_write_conflict`
- Evidence tier: `mixed_instruction_config_and_readme_docs`
- Adjudication: `needs_refinement`
- Source tier mix: `instruction_or_config`:15, `other_context`:4, `readme_or_docs`:30
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.

### llama-index / ccm_0003_execution_conflict

- Type: `execution_conflict`
- Evidence tier: `readme_docs_only`
- Adjudication: `needs_refinement`
- Source tier mix: `readme_or_docs`:36
- Reason: The signal includes README/docs evidence, which can describe examples or usage rather than active agent policy.
- Release use: Use only with explicit README/docs caveat; do not use as a standalone headline claim.
