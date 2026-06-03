# Curated GitHub Issues For CtxGov

Date: 2026-06-03
Status: local issue staging. These are not created on GitHub until a maintainer
posts them.

## 1. [eval] Define labeled case schema for Agent Context Health Eval

Labels: `eval`, `docs`, `needs-design`

Body:

Define the JSONL schema for context-health benchmark cases and labels.

Acceptance:

- case rows include `case_id`, `source`, `ai_context`, `expected_finding_type`,
  and `expected_evidence_span`
- label rows include `case_id`, `finding_type`, `evidence_span`, `start_char`,
  `end_char`, and `rationale`
- clean controls use `finding_type: none`
- README documents limitations and no security/benchmark overclaim

## 2. [eval] Add 50 synthetic context-hazard cases

Labels: `eval`, `good first issue`

Body:

Add an initial synthetic case pack covering stale, conflicting, unsupported,
unsafe, hidden-failure, and clean-control cases.

Acceptance:

- at least 50 cases
- each case has a matching label
- each positive case has an evidence span
- clean controls are marked explicitly
- no private paths, credentials, or raw third-party excerpts

## 3. [eval] Implement finding-type precision/recall scorer

Labels: `eval`, `python`, `needs-validation`

Body:

Implement a deterministic scorer for finding-type precision, recall, and F1.

Acceptance:

- reads labels JSONL and predictions JSONL
- emits JSON metrics
- reports false positives and false negatives by `case_id`
- handles clean controls
- has a short CLI help path

## 4. [baseline] Add regex baseline

Labels: `eval`, `baseline`, `good first issue`

Body:

Add a transparent regex baseline so CtxGov results can be compared against a
simple non-agent method.

Acceptance:

- no model call
- no network call
- finding rules are documented
- output format matches scorer input
- limitations section explains why regex is only a baseline

## 5. [docs] Publish failure taxonomy

Labels: `docs`, `eval`, `public-surface`

Body:

Publish the initial failure taxonomy for Agent Context Health Eval.

Acceptance:

- includes stale, conflicting, unsupported, unsafe, hidden-failure, and clean
  controls
- includes examples and non-goals
- does not claim security coverage or universal benchmark status

## 6. [demo] Add 60-second demo GIF

Labels: `demo`, `public-surface`

Body:

Create a 60-second before/after demo GIF for the project page and README.

Acceptance:

- left side shows bad AI-facing context
- right side shows CtxGov findings with evidence spans
- ends with limitation line
- under 10 MB if checked into the repo, or linked from a stable release asset

## 7. [release] Prepare v0.6.3 canonical GitHub release

Labels: `release`, `public-surface`, `needs-owner-approval`

Body:

Prepare the v0.6.3 GitHub source release for public-surface cleanup.

Acceptance:

- release notes and GitHub release body are ready
- README renders correctly
- About description and topics are updated
- release URL works
- package/CLI migration is explicitly out of scope

## 8. [outreach] Track reviewer/HM feedback loops

Labels: `outreach`, `docs`

Body:

Set up a simple feedback tracker for research engineers, evals engineers, and
hiring managers.

Acceptance:

- includes target, role, artifact sent, date, reply status, and follow-up
- weekly cadence is documented
- no mass outreach or unsupported claims
