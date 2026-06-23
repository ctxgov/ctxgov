# Change Gate Public Guide

The public Change Gate command reads explicit local agent-facing files and prints
a JSON review artifact.

```bash
ctxgov change-gate-check --baseline-root examples/change-gate-public-preview/baseline --head-root examples/change-gate-public-preview/head
```

Boundary: no target writes, no policy enforcement, no network/API calls, no
provider/model calls, and no replacement for human review.
