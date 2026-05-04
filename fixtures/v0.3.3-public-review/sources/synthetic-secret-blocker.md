---
id: public_review_synthetic_secret_blocker
title: Synthetic secret blocker public review note
source_url: synthetic://ctxvault/v0.3.3-public-review/secret-blocker
public_data_basis: Synthetic safety fixture, not sourced from the web
---

# Synthetic blocked source

This source intentionally contains fake credential-shaped material to verify
that the public review pack can withhold sensitive context and block projection
when a withheld slice is explicitly selected.

Fake credential sentinel:
sk-v033publicreviewabcdefghijklmnopqrstuvwxyz1234567890

# Handoff relevance

This source should not be selected for normal safe context handoff queries. If
it is explicitly selected, privacy preflight should return a block decision and
projection should not proceed.
