# Forensics Public Guide

Forensics public preview reads an explicit fixture and prints timeline, trace,
or gap JSON.

```bash
ctxgov forensics-timeline --fixture release/v0.8.0/forensics-public-preview-fixture.json
ctxgov forensics-trace --fixture release/v0.8.0/forensics-public-preview-fixture.json --finding-id finding-public-authority-001
ctxgov forensics-gaps --fixture release/v0.8.0/forensics-public-preview-fixture.json
```

The public command does not create `.ctxvault`, SQLite stores, receipt stores,
target files, or external state.
