from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Any

from .intelligence import WORKSTREAM_DENSITY_BUDGET


COMPILED_WORKSTREAM_STATE_SCHEMA_ID = "ctxvault.compiled-workstream-state/v1"


def build_compiled_workstream_state(
    workstream_payload: dict[str, Any],
    *,
    intelligence_report: dict[str, Any],
    projection_receipts: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the v0.3 compiled workstream read model without creating truth."""

    workstream_id = str(workstream_payload["id"])
    workstream_ref = f"workstream://{workstream_id}"
    current_state = dict(intelligence_report.get("current_state") or {})
    promotion_profile = dict(intelligence_report.get("promotion_profile") or {})
    source_refs = _unique(
        [
            workstream_ref,
            *[str(ref).strip() for ref in workstream_payload.get("source_refs", []) if str(ref).strip()],
            *list((intelligence_report.get("sources") or {}).get("knowledge_refs") or []),
            *list((intelligence_report.get("sources") or {}).get("memory_refs") or []),
        ]
    )
    event_time = generated_at or _utc_now()
    receipt_refs = _receipt_refs(projection_receipts or [])
    warnings = _unique(
        [
            *[str(item).strip() for item in promotion_profile.get("warnings", []) if str(item).strip()],
            *[str(gap.get("detail") or "").strip() for gap in intelligence_report.get("gaps", []) if str(gap.get("detail") or "").strip()],
        ]
    )

    return {
        "schema_id": COMPILED_WORKSTREAM_STATE_SCHEMA_ID,
        "state_id": f"cws_{_slug(workstream_id)}",
        "workstream_ref": workstream_ref,
        "generated_at": event_time,
        "contract_state": "experimental_read_model",
        "source_refs": source_refs,
        "current_truth": {
            "title": str(current_state.get("title") or workstream_payload.get("title") or workstream_id),
            "summary": _sourced_text(
                str(current_state.get("summary") or workstream_payload.get("summary") or "No summary available."),
                source_refs=source_refs,
            ),
            "active_decisions": [
                _sourced_text(text, source_refs=source_refs)
                for text in _decision_like_items(list(current_state.get("reusable_judgments") or []))
            ],
            "active_constraints": [
                _sourced_text(text, source_refs=source_refs)
                for text in _constraint_like_items(list(current_state.get("reusable_judgments") or []), warnings=warnings)
            ],
            "open_questions": [
                _sourced_text(text, source_refs=source_refs)
                for text in list(current_state.get("open_questions") or [])
                if str(text).strip()
            ],
            "next_actions": [
                _sourced_text(str(item.get("question") or item.get("suggested_action") or item.get("detail") or ""), source_refs=source_refs)
                for item in intelligence_report.get("next_questions", [])
                if str(item.get("question") or item.get("suggested_action") or item.get("detail") or "").strip()
            ],
            "reusable_judgments": [
                _sourced_text(text, source_refs=source_refs)
                for text in list(current_state.get("reusable_judgments") or [])
                if str(text).strip()
            ],
        },
        "evidence_timeline": _evidence_timeline(
            workstream_payload,
            workstream_ref=workstream_ref,
            generated_at=event_time,
            projection_receipts=projection_receipts or [],
        ),
        "review": {
            "approval_state": "approved_inputs_only"
            if str(workstream_payload.get("approval_state") or "") == "approved"
            else "contains_proposed_inputs",
            "required_before_projection": str(workstream_payload.get("approval_state") or "") != "approved",
            "receipt_refs": receipt_refs,
        },
        "projection_targets": _projection_targets(projection_receipts or []),
        "density": _density_state(str(current_state.get("summary") or workstream_payload.get("summary") or ""), warnings),
        "warnings": warnings,
    }


def _sourced_text(text: str, *, source_refs: list[str]) -> dict[str, Any]:
    return {"text": str(text).strip(), "source_refs": list(source_refs)}


def _decision_like_items(items: list[Any]) -> list[str]:
    decisions = [
        str(item).strip()
        for item in items
        if str(item).strip()
        and re.search(r"\b(should|must|choose|keep|prefer|use|treat|remain)\b", str(item), re.IGNORECASE)
    ]
    return _unique(decisions)[:4]


def _constraint_like_items(items: list[Any], *, warnings: list[str]) -> list[str]:
    constraints = [
        str(item).strip()
        for item in items
        if str(item).strip()
        and re.search(r"\b(do not|don't|never|avoid|must not|not )\b", str(item), re.IGNORECASE)
    ]
    constraints.extend(f"Advisory density warning: {warning}" for warning in warnings[:2])
    return _unique(constraints)[:4]


def _evidence_timeline(
    workstream_payload: dict[str, Any],
    *,
    workstream_ref: str,
    generated_at: str,
    projection_receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_refs = [str(ref).strip() for ref in workstream_payload.get("source_refs", []) if str(ref).strip()]
    events: list[dict[str, Any]] = [
        {
            "event_ref": workstream_ref,
            "event_kind": "candidate_review",
            "occurred_at": str(workstream_payload.get("updated_at") or workstream_payload.get("created_at") or generated_at),
            "summary": "Approved workstream state is the source for compiled current truth.",
            "source_refs": _unique([workstream_ref, *source_refs]),
            "review_state": "approved"
            if str(workstream_payload.get("approval_state") or "") == "approved"
            else "proposed",
        }
    ]
    for ref in source_refs[:8]:
        events.append(
            {
                "event_ref": ref,
                "event_kind": "source_import",
                "occurred_at": str(workstream_payload.get("created_at") or generated_at),
                "summary": f"Source ref contributes to compiled workstream state: {ref}",
                "source_refs": [ref],
                "review_state": "not_required",
            }
        )
    for receipt in projection_receipts:
        receipt_ref = _receipt_ref(receipt)
        if receipt_ref is None:
            continue
        events.append(
            {
                "event_ref": receipt_ref,
                "event_kind": "projection_write",
                "occurred_at": str(receipt.get("generated_at") or receipt.get("created_at") or generated_at),
                "summary": f"Projection receipt recorded for {receipt.get('target_kind') or 'unknown target'}.",
                "source_refs": [receipt_ref, *_string_list(receipt.get("source_refs"))],
                "review_state": str(receipt.get("review_state") or "not_required"),
            }
        )
    return events


def _projection_targets(projection_receipts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_target: dict[str, dict[str, Any]] = {}
    for receipt in projection_receipts:
        target_kind = str(receipt.get("target_kind") or "").strip()
        if not target_kind:
            continue
        by_target[target_kind] = {
            "target_kind": target_kind,
            "status": "projected" if str(receipt.get("output_status") or "") == "written" else "blocked",
            "receipt_ref": _receipt_ref(receipt),
        }
    defaults = ["harness.agents-md", "harness.claude-md", "wiki.markdown-workstream"]
    for target in defaults:
        by_target.setdefault(target, {"target_kind": target, "status": "not_projected", "receipt_ref": None})
    return [by_target[target] for target in sorted(by_target)]


def _density_state(summary: str, warnings: list[str]) -> dict[str, Any]:
    return {
        "summary_word_count": _word_count(summary),
        "summary_budget": {
            "target_min": 24,
            "target_max": int(WORKSTREAM_DENSITY_BUDGET["summary_target_words"]),
            "hard_warning": int(WORKSTREAM_DENSITY_BUDGET["summary_warning_words"]),
        },
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def _receipt_refs(projection_receipts: list[dict[str, Any]]) -> list[str]:
    return _unique(ref for receipt in projection_receipts for ref in [_receipt_ref(receipt)] if ref)


def _receipt_ref(receipt: dict[str, Any]) -> str | None:
    receipt_id = str(receipt.get("receipt_id") or "").strip()
    if receipt_id:
        return f"receipt://{receipt_id}"
    projection_id = str(receipt.get("projection_id") or "").strip()
    if projection_id:
        return f"receipt://projection/{projection_id}"
    return None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text))


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "_", value.replace("ws_", "", 1)).strip("_").lower() or "workstream"


def _unique(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
