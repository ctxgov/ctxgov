from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_FILES = {
    "core": ROOT / "schemas" / "json" / "ctxvault-core-v0.schema.json",
    "governance": ROOT / "schemas" / "json" / "ctxvault-governance-v0.schema.json",
    "controls": ROOT / "schemas" / "json" / "ctxvault-controls-v0.schema.json",
    "runtime_evidence_receipt": (
        ROOT
        / "schemas"
        / "json"
        / "ctxvault-runtime-evidence-receipt-v0.schema.json"
    ),
    "projection_governance_kernel_v041": (
        ROOT
        / "schemas"
        / "json"
        / "ctxvault-projection-governance-kernel-v041.schema.json"
    ),
}

FIXTURE_MAP = {
    ROOT / "fixtures" / "core" / "session.json": ("core", "Session"),
    ROOT / "fixtures" / "core" / "context-bundle.json": ("core", "ContextBundle"),
    ROOT / "fixtures" / "core" / "workstream.json": ("core", "Workstream"),
    ROOT / "fixtures" / "core" / "workstream-candidate.json": ("core", "WorkstreamCandidate"),
    ROOT / "fixtures" / "core" / "prompt-asset.json": ("core", "PromptAsset"),
    ROOT / "fixtures" / "core" / "prompt-patch.json": ("core", "PromptPatch"),
    ROOT / "fixtures" / "core" / "memory-candidate.json": ("core", "MemoryCandidate"),
    ROOT / "fixtures" / "core" / "memory.json": ("core", "Memory"),
    ROOT / "fixtures" / "core" / "knowledge-artifact.json": ("core", "KnowledgeArtifact"),
    ROOT / "fixtures" / "evidence" / "claim-record.json": ("governance", "ClaimRecord"),
    ROOT / "fixtures" / "evidence" / "evidence-link.json": ("governance", "EvidenceLink"),
    ROOT / "fixtures" / "evidence" / "audit-run.json": ("governance", "AuditRun"),
    ROOT / "fixtures" / "evidence" / "adapter-capability-profile.json": ("governance", "AdapterCapabilityProfile"),
    ROOT / "fixtures" / "evidence" / "plugin-manifest.json": ("governance", "PluginManifest"),
    ROOT / "fixtures" / "evidence" / "runtime-evidence-receipt.json": (
        "runtime_evidence_receipt",
        "__root__",
    ),
    ROOT / "fixtures" / "controls" / "backup-check-receipt.json": ("controls", "BackupCheckReceipt"),
    ROOT / "fixtures" / "controls" / "protection-policy.json": ("controls", "ProtectionPolicy"),
    ROOT / "fixtures" / "controls" / "rollback-decision.json": ("controls", "RollbackDecision"),
    ROOT / "fixtures" / "controls" / "projection-receipt.json": ("controls", "ProjectionReceipt"),
    ROOT
    / "fixtures"
    / "v0.4.1-projection-governance-kernel"
    / "example-projection.json": (
        "projection_governance_kernel_v041",
        "ProjectionGovernanceKernelProjection",
    ),
    ROOT
    / "fixtures"
    / "v0.4.1-projection-governance-kernel"
    / "example-receipt.json": (
        "projection_governance_kernel_v041",
        "ProjectionGovernanceKernelReceipt",
    ),
}


class ValidationError(Exception):
    pass


def resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/$defs/"):
        raise ValidationError(f"unsupported $ref {ref}")
    name = ref.split("/", 2)[2]
    try:
        return root_schema["$defs"][name]
    except KeyError as exc:
        raise ValidationError(f"unknown $ref target {ref}") from exc


def validate(instance: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str) -> None:
    if "$ref" in schema:
        validate(instance, resolve_ref(schema["$ref"], root_schema), root_schema, path)
        return

    if "anyOf" in schema:
        errors: list[str] = []
        for option in schema["anyOf"]:
            try:
                validate(instance, option, root_schema, path)
                return
            except ValidationError as exc:
                errors.append(str(exc))
        raise ValidationError(f"{path}: no anyOf option matched ({'; '.join(errors)})")

    if "oneOf" in schema:
        matches = 0
        last_error = "no match"
        for option in schema["oneOf"]:
            try:
                validate(instance, option, root_schema, path)
                matches += 1
            except ValidationError as exc:
                last_error = str(exc)
        if matches != 1:
            raise ValidationError(f"{path}: expected exactly one oneOf match, got {matches} ({last_error})")
        return

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        errors: list[str] = []
        for item in expected_type:
            try:
                validate(instance, {**schema, "type": item}, root_schema, path)
                return
            except ValidationError as exc:
                errors.append(str(exc))
        raise ValidationError(f"{path}: none of the listed types matched ({'; '.join(errors)})")

    if expected_type == "object":
        if not isinstance(instance, dict):
            raise ValidationError(f"{path}: expected object")
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise ValidationError(f"{path}: missing required key '{key}'")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(instance) - set(properties))
            if extra:
                raise ValidationError(f"{path}: unexpected keys {extra}")
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], root_schema, f"{path}.{key}")
        return

    if expected_type == "array":
        if not isinstance(instance, list):
            raise ValidationError(f"{path}: expected array")
        item_schema = schema.get("items")
        if item_schema is not None:
            for idx, item in enumerate(instance):
                validate(item, item_schema, root_schema, f"{path}[{idx}]")
        return

    if expected_type == "string":
        if not isinstance(instance, str):
            raise ValidationError(f"{path}: expected string")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise ValidationError(f"{path}: expected minLength {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise ValidationError(f"{path}: value '{instance}' does not match pattern {schema['pattern']}")
        if "enum" in schema and instance not in schema["enum"]:
            raise ValidationError(f"{path}: value '{instance}' not in enum {schema['enum']}")
        return

    if expected_type == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            raise ValidationError(f"{path}: expected integer")
        if "minimum" in schema and instance < schema["minimum"]:
            raise ValidationError(f"{path}: expected integer >= {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ValidationError(f"{path}: expected integer <= {schema['maximum']}")
        return

    if expected_type == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            raise ValidationError(f"{path}: expected number")
        if "minimum" in schema and instance < schema["minimum"]:
            raise ValidationError(f"{path}: expected number >= {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            raise ValidationError(f"{path}: expected number <= {schema['maximum']}")
        return

    if expected_type == "boolean":
        if not isinstance(instance, bool):
            raise ValidationError(f"{path}: expected boolean")
        return

    if expected_type == "null":
        if instance is not None:
            raise ValidationError(f"{path}: expected null")
        return

    if expected_type is None:
        if "enum" in schema and instance not in schema["enum"]:
            raise ValidationError(f"{path}: value '{instance}' not in enum {schema['enum']}")
        return

    raise ValidationError(f"{path}: unsupported schema type {expected_type}")


def main() -> int:
    schemas = {name: json.loads(path.read_text()) for name, path in SCHEMA_FILES.items()}
    validated = 0
    for fixture_path, (schema_name, def_name) in FIXTURE_MAP.items():
        payload = json.loads(fixture_path.read_text())
        schema = schemas[schema_name] if def_name == "__root__" else {"$ref": f"#/$defs/{def_name}"}
        validate(payload, schema, schemas[schema_name], fixture_path.name)
        validated += 1
    print(f"validated {validated} fixture(s)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
