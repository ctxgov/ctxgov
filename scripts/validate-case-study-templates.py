#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "templates" / "case-study-preview"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_keys(data: dict, keys: list[str], path: Path) -> None:
    missing = [key for key in keys if key not in data]
    require(not missing, f"{path}: missing keys: {', '.join(missing)}")


def main() -> None:
    source_fact = load_json(TEMPLATE_DIR / "source-fact-receipt.template.json")
    claim_lint = load_json(TEMPLATE_DIR / "claim-lint.template.json")
    extract = (TEMPLATE_DIR / "public-safe-extract.template.md").read_text(encoding="utf-8")
    rollback = (TEMPLATE_DIR / "rollback.template.md").read_text(encoding="utf-8")

    require_keys(
        source_fact,
        [
            "schema_id",
            "target",
            "verification_methods",
            "source_refs",
            "authority_layers",
            "evidence_object_schema",
            "selected_evidence",
            "omitted_evidence",
            "blocked_evidence",
            "missing_evidence",
            "side_effect_boundary",
            "rollback",
        ],
        TEMPLATE_DIR / "source-fact-receipt.template.json",
    )
    for layer in ["claim", "context", "memory", "action"]:
        require(layer in source_fact["authority_layers"], f"source template missing authority layer {layer}")
    for field in [
        "ref",
        "state",
        "reason",
        "authority_layer_blocked",
        "safe_rewrite_or_next_check",
        "rollback_ref",
    ]:
        require(
            field in source_fact["evidence_object_schema"]["required_fields"],
            f"source template missing evidence object field {field}",
        )
    require(source_fact["side_effect_boundary"]["target_file_written"] is False, "source template may not allow target writes")
    require(source_fact["side_effect_boundary"]["provider_or_model_call_performed"] is False, "source template may not allow provider calls")

    require_keys(
        claim_lint,
        [
            "schema_id",
            "target",
            "authority_layers",
            "claim_classes",
            "allowed_claims",
            "blocked_claims",
            "safe_rewrites",
            "missing_evidence",
            "publication_decision",
            "side_effect_boundary",
            "rollback",
        ],
        TEMPLATE_DIR / "claim-lint.template.json",
    )
    for layer in ["claim", "context", "memory", "action"]:
        require(layer in claim_lint["authority_layers"], f"claim-lint missing authority layer {layer}")
    for required_class in [
        "quality",
        "security",
        "performance",
        "compatibility",
        "maintainer_endorsement",
        "stable_protocol",
        "runtime_behavior",
        "target_write",
    ]:
        require(required_class in claim_lint["claim_classes"], f"claim-lint missing class {required_class}")
    require(claim_lint["publication_decision"] == "blocked_until_owner_approval", "publication must default blocked")

    for required_section in [
        "Source Boundary",
        "Selected Evidence",
        "Omitted Evidence",
        "Missing Evidence",
        "Authority Ladder",
        "Blocked Claims",
        "Decision Table",
        "Safe Rewrites",
        "No Target Mutation",
    ]:
        require(required_section in extract, f"extract template missing {required_section}")
    for required_state in ["Allowed", "Blocked", "Missing", "Rollback"]:
        require(required_state in extract, f"extract template missing decision state {required_state}")
    for required_section in ["Local Artifacts", "Public Artifacts", "Rollback Plan", "No Target Mutation"]:
        require(required_section in rollback, f"rollback template missing {required_section}")

    print("case study templates validated: 4 files")


if __name__ == "__main__":
    main()
