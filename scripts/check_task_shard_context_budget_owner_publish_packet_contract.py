from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    packet = _build_packet()
    errors = []
    if packet.get("status") != "pass_task_shard_context_budget_owner_publish_packet":
        errors.append("packet status mismatch")
    if packet.get("manual_review_required") != "owner_manual_platform_submit_only":
        errors.append("manual review boundary missing")
    for field in ["publication_executed", "outreach_performed", "commit_created", "push_executed", "release_created"]:
        if packet.get(field) is not False:
            errors.append(f"{field} must remain false")
    required_blocked = {"commit", "push", "HN submit", "LinkedIn post", "X post", "provider/model call"}
    if not required_blocked.issubset(set(packet.get("blocked_without_owner_approval", []))):
        errors.append("blocked owner approval list incomplete")
    result = {
        "schema_id": "ctxgov.task-shard-context-budget-owner-publish-packet-contract/v0",
        "status": "pass_task_shard_context_budget_owner_publish_packet_contract" if not errors else "fail_task_shard_context_budget_owner_publish_packet_contract",
        "packet_status": packet.get("status"),
        "publication_bundle_sha256": packet.get("publication_bundle_sha256"),
        "publication_file_count": packet.get("publication_file_count"),
        "error_count": len(errors),
        "errors": errors,
        "publication_executed": False,
        "outreach_performed": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


def _build_packet() -> dict:
    script = ROOT / "scripts" / "render_task_shard_context_budget_owner_publish_packet.py"
    spec = importlib.util.spec_from_file_location("render_task_shard_context_budget_owner_publish_packet", script)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.build_packet()


if __name__ == "__main__":
    raise SystemExit(main())
