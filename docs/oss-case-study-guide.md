# OSS Case Study Public Guide

OSS Case Study Preview reads an explicit saved local public-source excerpt and
prints source-descriptive governance boundaries.

```bash
ctxgov oss-case-study-preview --target-name mem0 --repo-url https://github.com/mem0ai/mem0 --pinned-ref 366945965df43aa7084be98d1b5073b62a20b431 --source-path examples/oss-case-study-public-preview/mem0-source.md
```

`repo-url` and `pinned-ref` are metadata in the public package. The command does
not fetch remote content, clone repositories, contact maintainers, or validate a
target runtime.
