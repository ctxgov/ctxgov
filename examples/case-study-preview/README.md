# Case Study Preview Demo

Status: public-safe demo. This demo validates local templates only. It does not
fetch, clone, inspect, install, run, or write to any target project.

## Run

```bash
python3 scripts/validate-case-study-templates.py
```

Expected output:

```text
case study templates validated: 4 files
```

## What This Proves

The validator checks that the case-study preview templates contain the minimum
governance shape needed before public OSS evidence is written:

- source facts and pinned refs;
- claim/context/memory/action authority layers;
- selected, omitted, stale/conflicting, and missing evidence;
- omitted/blocked/stale/conflicting evidence as product objects;
- blocked claim classes;
- safe rewrite slots;
- allowed/blocked/missing/rollback decision table;
- no target write, provider/model call, runtime execution, MCP server start, or
  memory promotion by default.

## Filled Example

Read `mem0-decision-preview.example.md` for a filled public-safe decision
preview. It uses already published aggregate mem0 evidence and does not fetch,
clone, inspect, install, run, or write to the target project.

## Local CLI First Slice

The local `oss-case-study-preview` command can create preview artifacts from an
explicit local source path. Remote README fetch is gated behind
`--allow-network`; the default remote path writes a blocked receipt instead of
touching a target.

## What This Does Not Prove

This demo does not evaluate any external OSS project. It does not claim
quality, security, performance, compatibility, maintainer endorsement, stable
protocol support, runtime behavior, or target write safety.

## Next Step For An OSS Maintainer

Copy the templates under `templates/case-study-preview/`, fill them with a
pinned source ref and source-backed claims, run the validator, then review the
public-safe extract before publishing anything.
