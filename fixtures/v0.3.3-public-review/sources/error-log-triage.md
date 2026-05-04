---
id: public_review_error_log_triage
title: Synthetic public error log triage review note
source_url: synthetic://ctxvault/v0.3.3-public-review/error-log-triage
public_data_basis: Synthetic public fixture for log-shaped local review data
---

# Error log shape

This public fixture represents log-shaped evidence from a local package review.
The values are synthetic and contain no hostnames, tokens, account identifiers,
or private filesystem paths.

```text
2026-05-04T00:00:00Z review INFO package_review_started root=scratch
2026-05-04T00:00:01Z review WARN provider_call_skipped reason=local_only_gate
2026-05-04T00:00:02Z review INFO receipt_written kind=context_selection
2026-05-04T00:00:03Z review INFO result=pass scenario=api_response_triage
```

# Handoff relevance

This source should be selected for API response failure triage, local log
review, provider-call skip behavior, receipt verification, and debugging
without external services.

Public review marker: apiresponsefailuretriage.
