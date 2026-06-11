# HN Worksheet

Status: local worksheet only. No HN submission has been executed.

Recommended URL submission after the public page exists:

```text
title: Show HN: CtxGov - drop in AI memory files, get an influence-boundary report
url: https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html
text: empty
```

Use a URL story, not a text-only post.

First-comment facts, if needed:

- This follows the Activation X-Ray launch.
- The fresh-checkout local command is
  `python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/`.
- Users can swap in their own local file with
  `python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md`.
- Directory scans are supported with
  `python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/`.
- Optional exit-code integration gate:
  `python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --fail-on-blocked`.
- Optional gate-only JSON output:
  `python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/ --format gate --fail-on-blocked`.
- Copyable wrapper example for product integration:
  `python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py`.
- Clean wrapper example returns `allow_inform_only`:
  `python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml`.
- The demo lets users drop in local memory/context/state files and writes an
  influence-boundary report.
- The report classifies candidate, inform-only allowed, blocked, omitted,
  stale/superseded, and imported refs.
- The built-in sample remains available, but this release is about
  user-supplied memory/context/state files.
- It does not claim provider support, compatibility, endorsement, adoption,
  security, benchmark performance, savings, or a stable protocol.

Do not paste generated-polished text into HN. Write any final comment by hand.
