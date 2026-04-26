from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
from typing import Any

from .layout import default_layout


CONTEXT_BUNDLE_RECEIPT_SCHEMA_VERSION = "ctxvault.context-bundle-receipt/v1"
AUDIT_RECEIPT_SCHEMA_VERSION = "ctxvault.audit-receipt/v1"
WORKSTREAM_RECEIPT_SCHEMA_VERSION = "ctxvault.workstream-receipt/v1"
WORKSTREAM_CANDIDATE_RECEIPT_SCHEMA_VERSION = "ctxvault.workstream-candidate-receipt/v1"
PROJECTION_RECEIPT_SCHEMA_VERSION = "ctxvault.projection-receipt/v1"


def emit_context_bundle_receipt(
    *,
    root: Path,
    output_path: Path,
    bundle_payload: dict[str, Any],
    plan_path: Path | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    bundle_id = str(bundle_payload["id"])
    bundle_path = _object_path(root, "context_bundle", bundle_id)
    if not bundle_path.exists():
        raise ValueError(f"context bundle object is missing at {bundle_path}")

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": CONTEXT_BUNDLE_RECEIPT_SCHEMA_VERSION,
        "generated_at": _isoformat(datetime.now(timezone.utc)),
        "ok": True,
        "kind": "context_bundle_receipt",
        "artifact_path": str(resolved_output),
        "source_root": str(root.resolve()),
        "bundle_id": bundle_id,
        "bundle_ref": f"bundle://{bundle_id}",
        "bundle_storage_ref": f"vault://objects/context_bundle/{bundle_id}.json",
        "bundle_path": str(bundle_path),
        "scope": dict(bundle_payload["scope"]),
        "task_label": str(bundle_payload["task_label"]),
        "sensitivity": str(bundle_payload.get("sensitivity", "public")),
        "exportable": bool(bundle_payload.get("exportable", False)),
        "redaction_state": str(bundle_payload.get("redaction_state", "none")),
        "secret_refs": list(bundle_payload.get("secret_refs", [])),
        "token_budget": int(bundle_payload.get("token_budget", 0) or 0),
        "token_estimate": int(bundle_payload.get("token_estimate", 0) or 0),
        "input_ref_count": len(bundle_payload.get("input_refs", [])),
        "source_pointer_count": len(bundle_payload.get("sections", {}).get("source_pointers", [])),
        "plan_ledger_artifact": _plan_ledger_artifact_hint(
            artifact_type="ctxvault_context_bundle_receipt",
            artifact_path=resolved_output,
            plan_path=plan_path,
            task_id=task_id,
        ),
    }
    _write_json(resolved_output, receipt)
    return {
        "receipt_path": str(resolved_output),
        "receipt": receipt,
    }


def emit_audit_receipt(
    *,
    root: Path,
    output_path: Path,
    audit_payload: dict[str, Any],
    plan_path: Path | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    audit_id = str(audit_payload["id"])
    audit_path = _object_path(root, "audit_run", audit_id)
    if not audit_path.exists():
        raise ValueError(f"audit object is missing at {audit_path}")

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": AUDIT_RECEIPT_SCHEMA_VERSION,
        "generated_at": _isoformat(datetime.now(timezone.utc)),
        "ok": True,
        "kind": "audit_receipt",
        "artifact_path": str(resolved_output),
        "source_root": str(root.resolve()),
        "audit_id": audit_id,
        "audit_ref": f"audit://{audit_id}",
        "audit_storage_ref": f"vault://objects/audit_run/{audit_id}.json",
        "audit_path": str(audit_path),
        "scope": dict(audit_payload["scope"]),
        "subject_ref": str(audit_payload["subject_ref"]),
        "verdict": str(audit_payload["verdict"]),
        "review_state": str(audit_payload["review_state"]),
        "method": str(audit_payload["method"]),
        "claim_ref_count": len(audit_payload.get("claim_refs", [])),
        "evidence_ref_count": len(audit_payload.get("evidence_refs", [])),
        "claim_refs": list(audit_payload.get("claim_refs", [])),
        "evidence_refs": list(audit_payload.get("evidence_refs", [])),
        "notes": audit_payload.get("notes"),
        "plan_ledger_artifact": _plan_ledger_artifact_hint(
            artifact_type="ctxvault_audit_receipt",
            artifact_path=resolved_output,
            plan_path=plan_path,
            task_id=task_id,
        ),
    }
    _write_json(resolved_output, receipt)
    return {
        "receipt_path": str(resolved_output),
        "receipt": receipt,
    }


def emit_workstream_receipt(
    *,
    root: Path,
    output_path: Path,
    workstream_payload: dict[str, Any],
    plan_path: Path | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    workstream_id = str(workstream_payload["id"])
    workstream_path = _object_path(root, "workstream", workstream_id)
    if not workstream_path.exists():
        raise ValueError(f"workstream object is missing at {workstream_path}")

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": WORKSTREAM_RECEIPT_SCHEMA_VERSION,
        "generated_at": _isoformat(datetime.now(timezone.utc)),
        "ok": True,
        "kind": "workstream_receipt",
        "artifact_path": str(resolved_output),
        "source_root": str(root.resolve()),
        "workstream_id": workstream_id,
        "workstream_ref": f"workstream://{workstream_id}",
        "workstream_storage_ref": f"vault://objects/workstream/{workstream_id}.json",
        "workstream_path": str(workstream_path),
        "scope": dict(workstream_payload["scope"]),
        "title": str(workstream_payload["title"]),
        "summary": str(workstream_payload.get("summary") or ""),
        "status": str(workstream_payload.get("status") or "active"),
        "approval_state": str(workstream_payload.get("approval_state") or "approved"),
        "session_ref_count": len(workstream_payload.get("session_refs", [])),
        "episode_ref_count": len(workstream_payload.get("episode_refs", [])),
        "knowledge_ref_count": len(workstream_payload.get("knowledge_refs", [])),
        "derived_from": list(workstream_payload.get("derived_from", [])),
        "task_labels": list(workstream_payload.get("task_labels", [])),
        "recurring_terms": list(workstream_payload.get("recurring_terms", [])),
        "sensitivity": str(workstream_payload.get("sensitivity", "public")),
        "exportable": bool(workstream_payload.get("exportable", False)),
        "redaction_state": str(workstream_payload.get("redaction_state", "none")),
        "secret_refs": list(workstream_payload.get("secret_refs", [])),
        "plan_ledger_artifact": _plan_ledger_artifact_hint(
            artifact_type="ctxvault_workstream_receipt",
            artifact_path=resolved_output,
            plan_path=plan_path,
            task_id=task_id,
            description=f"ctxvault workstream receipt for {workstream_id}",
        ),
    }
    _write_json(resolved_output, receipt)
    return {
        "receipt_path": str(resolved_output),
        "receipt": receipt,
    }


def emit_workstream_candidate_receipt(
    *,
    root: Path,
    output_path: Path,
    candidate_payload: dict[str, Any],
    plan_path: Path | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    candidate_id = str(candidate_payload["id"])
    candidate_path = _object_path(root, "workstream_candidate", candidate_id)
    if not candidate_path.exists():
        raise ValueError(f"workstream candidate object is missing at {candidate_path}")

    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": WORKSTREAM_CANDIDATE_RECEIPT_SCHEMA_VERSION,
        "generated_at": _isoformat(datetime.now(timezone.utc)),
        "ok": True,
        "kind": "workstream_candidate_receipt",
        "artifact_path": str(resolved_output),
        "source_root": str(root.resolve()),
        "candidate_id": candidate_id,
        "candidate_ref": f"workstream-candidate://{candidate_id}",
        "candidate_storage_ref": f"vault://objects/workstream_candidate/{candidate_id}.json",
        "candidate_path": str(candidate_path),
        "scope": dict(candidate_payload["scope"]),
        "title": str(candidate_payload["title"]),
        "summary": str(candidate_payload.get("summary") or ""),
        "proposal_state": str(candidate_payload.get("proposal_state") or "proposed"),
        "candidate_for": candidate_payload.get("candidate_for"),
        "confidence": float(candidate_payload.get("confidence") or 0.0),
        "session_ref_count": len(candidate_payload.get("session_refs", [])),
        "episode_ref_count": len(candidate_payload.get("episode_refs", [])),
        "knowledge_ref_count": len(candidate_payload.get("knowledge_refs", [])),
        "task_labels": list(candidate_payload.get("task_labels", [])),
        "recurring_terms": list(candidate_payload.get("recurring_terms", [])),
        "sensitivity": str(candidate_payload.get("sensitivity", "public")),
        "exportable": bool(candidate_payload.get("exportable", False)),
        "redaction_state": str(candidate_payload.get("redaction_state", "none")),
        "secret_refs": list(candidate_payload.get("secret_refs", [])),
        "plan_ledger_artifact": _plan_ledger_artifact_hint(
            artifact_type="ctxvault_workstream_candidate_receipt",
            artifact_path=resolved_output,
            plan_path=plan_path,
            task_id=task_id,
            description=f"ctxvault workstream candidate receipt for {candidate_id}",
        ),
    }
    _write_json(resolved_output, receipt)
    return {
        "receipt_path": str(resolved_output),
        "receipt": receipt,
    }


def emit_projection_receipt(
    *,
    root: Path,
    output_path: Path,
    projection_payload: dict[str, Any],
    plan_path: Path | None = None,
    task_id: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema_version": PROJECTION_RECEIPT_SCHEMA_VERSION,
        "created_at": _isoformat(datetime.now(timezone.utc)),
        "ok": True,
        "kind": "projection_receipt",
        "artifact_path": str(resolved_output),
        "source_root": str(root.resolve()),
        "receipt_id": str(projection_payload["receipt_id"]),
        "projection_id": str(projection_payload["projection_id"]),
        "projection_kind": str(projection_payload["projection_kind"]),
        "target_kind": str(projection_payload["target_kind"]),
        "target_path": str(projection_payload["target_path"]),
        "source_refs": list(projection_payload.get("source_refs", [])),
        "source_object_kinds": list(projection_payload.get("source_object_kinds", [])),
        "scope": dict(projection_payload["scope"]),
        "plugin_id": str(projection_payload["plugin_id"]),
        "plugin_version": str(projection_payload["plugin_version"]),
        "render_policy": str(projection_payload["render_policy"]),
        "merge_policy": str(projection_payload["merge_policy"]),
        "output_sha256": str(projection_payload["output_sha256"]),
        "output_bytes": int(projection_payload.get("output_bytes", 0) or 0),
        "output_status": str(projection_payload["output_status"]),
        "policy_decision": str(projection_payload["policy_decision"]),
        "review_state": str(projection_payload["review_state"]),
        "warnings": list(projection_payload.get("warnings", [])),
        "plan_ledger_artifact": _plan_ledger_artifact_hint(
            artifact_type="ctxvault_projection_receipt",
            artifact_path=resolved_output,
            plan_path=plan_path,
            task_id=task_id,
            description=description
            or f"ctxvault projection receipt for {projection_payload['projection_id']}",
        ),
    }
    _write_json(resolved_output, receipt)
    return {
        "receipt_path": str(resolved_output),
        "receipt": receipt,
    }


def _object_path(root: Path, object_kind: str, object_id: str) -> Path:
    layout = default_layout(root.resolve())
    return (layout.objects_dir / object_kind / f"{object_id}.json").resolve()


def _plan_ledger_artifact_hint(
    *,
    artifact_type: str,
    artifact_path: Path,
    plan_path: Path | None,
    task_id: str | None,
    description: str | None = None,
) -> dict[str, Any]:
    resolved_plan = plan_path.resolve() if plan_path is not None else None
    artifact_json = {
        "artifact_type": artifact_type,
        "artifact_path": str(artifact_path),
    }
    if description is not None:
        artifact_json["description"] = description
    hint: dict[str, Any] = {
        "artifact_type": artifact_type,
        "artifact_path": str(artifact_path),
        "artifact_json": artifact_json,
        "suggested_artifact_json": json.dumps(artifact_json, ensure_ascii=True, sort_keys=True),
    }
    if description is not None:
        hint["description"] = description
    if resolved_plan is not None:
        hint["plan_path"] = str(resolved_plan)
    if task_id is not None:
        hint["task_id"] = task_id
    if resolved_plan is not None and task_id is not None:
        command_parts = [
            "uv",
            "run",
            "plan-ledger",
            "task",
            "artifact",
            str(resolved_plan),
            task_id,
            artifact_type,
            str(artifact_path),
        ]
        if description is not None:
            command_parts.extend(["--description", description])
        hint["suggested_command"] = " ".join(shlex.quote(part) for part in command_parts)
    else:
        hint["suggested_command_template"] = (
            "uv run plan-ledger task artifact <plan.toml> <task-id> "
            f"{artifact_type} {artifact_path}"
        )
    return hint


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _isoformat(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")
