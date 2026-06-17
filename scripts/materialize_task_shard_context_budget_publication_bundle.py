from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy the Task Shard publication bundle into a checkout.")
    parser.add_argument("--source-root", default=str(ROOT))
    parser.add_argument("--checkout", required=True)
    args = parser.parse_args()

    source_root = Path(args.source_root).resolve()
    checkout = Path(args.checkout).resolve()
    payload = _build_bundle(source_root)
    errors = []
    copied = []
    if not (checkout / ".git").exists():
        errors.append("checkout must be a git checkout with .git")
    else:
        for item in payload["publication_files"]:
            rel = item["path"]
            src = source_root / rel
            dst = checkout / rel
            if not src.exists():
                errors.append(f"missing source file: {rel}")
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied.append(rel)

    result = {
        "schema_id": "ctxgov.task-shard-context-budget-publication-bundle-materialization/v0",
        "status": "pass_task_shard_context_budget_publication_bundle_materialized" if not errors else "fail_task_shard_context_budget_publication_bundle_materialized",
        "milestone": "Task Shard Context Budget Ledger",
        "copied_file_count": len(copied),
        "copied_files": copied,
        "errors": errors,
        "publication_bundle_sha256": payload["publication_bundle_sha256"],
        "local_checkout_write_executed": bool(copied),
        "publication_executed": False,
        "outreach_performed": False,
        "commit_created": False,
        "push_executed": False,
        "release_created": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _build_bundle(source_root: Path) -> dict:
    script = source_root / "scripts" / "build_task_shard_context_budget_publication_bundle.py"
    spec = importlib.util.spec_from_file_location("build_task_shard_context_budget_publication_bundle", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module.ROOT = source_root
    module.RELEASE = source_root / "release" / "task-shard-context-budget-ledger" / "2026-06-18"
    return module.build_bundle()


if __name__ == "__main__":
    raise SystemExit(main())
