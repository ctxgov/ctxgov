---
id: public_review_sqlite_fts5
title: SQLite FTS5 local search public review note
source_url: https://www.sqlite.org/fts5.html
license_note: SQLite code and documentation are dedicated to the public domain
license_url: https://sqlite.org/draft/copyright.html
public_data_basis: SQLite public-domain documentation, summarized by CtxVault
---

# Local full text search

SQLite FTS5 is a virtual table module for full text search. For the CtxVault
public review pack, this source represents local deterministic search over a
collection of source notes without a model call, embedding service, vector
database, or remote provider.

# Handoff relevance

The safe handoff path should be able to rebuild local context slices, search
them with deterministic SQLite-backed behavior, select a small working set, and
write receipts. This source should be selected for queries about local search,
FTS5, SQLite, token-budgeted context selection, and model-free retrieval.

Public review marker: privacylocalhandoff opensourcepublicreview licensepublicdomainreview.
