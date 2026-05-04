---
id: public_review_api_transcript
title: Synthetic public API transcript review note
source_url: synthetic://ctxvault/v0.3.3-public-review/api-transcript
public_data_basis: Synthetic public fixture for API-shaped local review data
---

# API transcript shape

This public fixture represents a small API-shaped response that a reviewer can
search locally without making a provider call. It is intentionally synthetic,
contains no credentials, and exists to test whether CtxVault can handle
structured response evidence in a safe context handoff.

```json
{
  "request_id": "req_public_demo_001",
  "status": 429,
  "retry_after_seconds": 30,
  "provider_call_executed": false,
  "review_note": "local package review should explain retry and receipt behavior"
}
```

# Handoff relevance

This source should be selected for API response triage, provider-call boundary,
local-only debugging, retry explanation, and audit evidence queries.

Public review marker: apiresponsefailuretriage.
