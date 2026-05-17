from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


RECEIPT_INSPECTION_SCHEMA_ID = "ctxvault.receipt-inspection/v1"


def build_receipt_inspection(
    root: Path,
    *,
    receipt_path: Path | None = None,
    receipt_ref: str | None = None,
    latest: bool = False,
    include_payload: bool = False,
) -> dict[str, Any]:
    resolved_root = root.resolve()
    if sum(1 for item in (receipt_path, receipt_ref, latest) if item) > 1:
        raise ValueError("receipt_path, receipt_ref, and latest are mutually exclusive")
    inventory = _receipt_inventory(resolved_root)
    target = _resolve_target_receipt(
        inventory,
        root=resolved_root,
        receipt_path=receipt_path,
        receipt_ref=receipt_ref,
        latest=latest,
    )
    if target is None:
        receipts = [
            _public_receipt_summary(receipt, include_payload=include_payload)
            for receipt in inventory["receipts"]
        ]
        report = {
            "schema_id": RECEIPT_INSPECTION_SCHEMA_ID,
            "generated_at": _utc_now(),
            "root": str(resolved_root),
            "mode": "read_only",
            "status": "pass",
            "target": None,
            "latest": False,
            "receipt_count": len(receipts),
            "receipts": receipts,
            "chains": [],
            "next_actions": _inventory_next_actions(receipts),
        }
        report["summary_text"] = render_receipt_inspection_summary(report)
        return report

    chain = _build_receipt_chain(target, inventory, include_payload=include_payload)
    status = "warn" if chain["missing_links"] or chain["warnings"] else "pass"
    report = {
        "schema_id": RECEIPT_INSPECTION_SCHEMA_ID,
        "generated_at": _utc_now(),
        "root": str(resolved_root),
        "mode": "read_only",
        "status": status,
        "target": _public_receipt_summary(target, include_payload=False),
        "latest": bool(latest),
        "receipt_count": len(inventory["receipts"]),
        "receipts": [],
        "chains": [chain],
        "next_actions": _chain_next_actions(chain),
    }
    report["summary_text"] = render_receipt_inspection_summary(report)
    return report


def render_receipt_inspection_summary(report: dict[str, Any]) -> str:
    lines = [
        "CtxVault receipt inspection",
        f"Status: {report.get('status')}",
        f"Root: {report.get('root')}",
    ]
    chains = report.get("chains") if isinstance(report.get("chains"), list) else []
    if not chains:
        receipts = report.get("receipts") if isinstance(report.get("receipts"), list) else []
        lines.append(f"Receipts found: {len(receipts)}")
        for receipt in receipts[:12]:
            if not isinstance(receipt, dict):
                continue
            lines.append(
                f"- {_summary_label(receipt.get('kind'))}: {receipt.get('primary_ref') or receipt.get('path')}"
            )
        if len(receipts) > 12:
            lines.append(f"- ... {len(receipts) - 12} more receipt(s)")
        _append_next_actions(lines, report.get("next_actions"))
        return "\n".join(lines)

    chain = chains[0] if isinstance(chains[0], dict) else {}
    lines.append(f"Chain status: {chain.get('status')}")
    root_receipt = chain.get("root_receipt") if isinstance(chain.get("root_receipt"), dict) else {}
    if root_receipt:
        lines.append(f"Target: {_summary_label(root_receipt.get('kind'))}")
        lines.append(f"Receipt: {root_receipt.get('path')}")
    context = chain.get("context_summary") if isinstance(chain.get("context_summary"), dict) else {}
    selected_refs = _string_list(context.get("selected_slice_refs"))
    required_refs = _string_list(context.get("required_slice_refs"))
    object_refs = _string_list(context.get("object_refs"))
    privacy_decisions = _string_list(context.get("privacy_decisions"))
    projection_targets = _string_list(context.get("projection_targets"))
    quality_statuses = _string_list(context.get("quality_statuses"))
    lines.append(f"Selected slices: {len(selected_refs)}")
    if selected_refs:
        for ref in selected_refs[:5]:
            lines.append(f"- selected: {ref}")
        if len(selected_refs) > 5:
            lines.append(f"- ... {len(selected_refs) - 5} more selected slice(s)")
    if required_refs:
        lines.append(f"Required slices retained: {len(required_refs)}")
    if object_refs:
        lines.append(f"Imported objects: {len(object_refs)}")
    if privacy_decisions:
        lines.append(f"Privacy decisions: {', '.join(privacy_decisions)}")
    if quality_statuses:
        lines.append(f"Quality status: {', '.join(quality_statuses)}")
    if projection_targets:
        lines.append(f"Projection targets: {', '.join(projection_targets)}")
    missing_links = chain.get("missing_links") if isinstance(chain.get("missing_links"), list) else []
    warnings = chain.get("warnings") if isinstance(chain.get("warnings"), list) else []
    if missing_links:
        lines.append(f"Missing receipt links: {len(missing_links)}")
        for link in missing_links[:5]:
            if isinstance(link, dict):
                lines.append(f"- missing {link.get('relation')}: {link.get('target')}")
    if warnings:
        lines.append(f"Warnings: {', '.join(str(item) for item in warnings)}")
    nodes = chain.get("nodes") if isinstance(chain.get("nodes"), list) else []
    if nodes:
        lines.append("Receipt chain:")
        for node in nodes:
            if isinstance(node, dict):
                lines.append(f"- {_summary_label(node.get('kind'))}: {node.get('primary_ref') or node.get('path')}")
    _append_next_actions(lines, report.get("next_actions"))
    return "\n".join(lines)


def scan_receipt_summaries(root: Path) -> list[dict[str, Any]]:
    inventory = _receipt_inventory(root.resolve())
    return [_public_receipt_summary(receipt, include_payload=False) for receipt in inventory["receipts"]]


def scan_receipt_records(root: Path) -> list[dict[str, Any]]:
    inventory = _receipt_inventory(root.resolve())
    return [_public_receipt_summary(receipt, include_payload=True) for receipt in inventory["receipts"]]


def _receipt_inventory(root: Path) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for receipt_root in _receipt_roots(root):
        if not receipt_root.exists():
            continue
        for path in sorted(receipt_root.rglob("*.json")):
            resolved = path.resolve()
            path_key = str(resolved)
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            try:
                payload = json.loads(resolved.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                continue
            if not isinstance(payload, dict):
                continue
            kind = _receipt_kind(payload)
            if kind == "unknown":
                continue
            receipts.append(
                {
                    "path": path_key,
                    "kind": kind,
                    "schema": _receipt_schema(payload),
                    "payload": payload,
                    "primary_ref": _receipt_primary_ref(payload, kind),
                    "ids": _receipt_ids(payload, kind),
                    "links": _receipt_links(payload, kind),
                    "summary": _receipt_status_summary(payload, kind),
                    "mtime_ns": resolved.stat().st_mtime_ns,
                }
            )

    by_path: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        by_path[receipt["path"]] = receipt
        for value in receipt["ids"]:
            by_id[value] = receipt
    return {"root": str(root), "receipts": receipts, "by_path": by_path, "by_id": by_id}


def _receipt_roots(root: Path) -> list[Path]:
    return [
        root / ".ctxvault" / "exports" / "receipts",
        root / "exports" / "receipts",
        root / "artifacts",
        root / "receipts",
        root / ".ctxvault",
    ]


def _receipt_kind(payload: dict[str, Any]) -> str:
    schema_id = str(payload.get("schema_id") or "")
    schema_version = str(payload.get("schema_version") or "")
    if schema_id == "ctxvault.context-extract-receipt/v1":
        return "context_extract"
    if schema_id == "ctxvault.context-selection-receipt/v1":
        return "context_selection"
    if schema_id == "ctxvault.privacy-preflight-receipt/v1":
        return "privacy_preflight"
    if schema_id == "ctxvault.context-quality-receipt/v1":
        return "context_quality"
    if schema_id.endswith("-scorecard/v1") or schema_id in {
        "ctxvault.context-density-scorecard/v1",
        "ctxvault.source-conflict-scorecard/v1",
        "ctxvault.source-retention-scorecard/v1",
    }:
        return "quality_scorecard"
    if schema_version == "ctxvault.projection-receipt/v1" or payload.get("kind") == "projection_receipt":
        return "projection"
    return "unknown"


def _receipt_schema(payload: dict[str, Any]) -> str:
    return str(payload.get("schema_id") or payload.get("schema_version") or "")


def _receipt_primary_ref(payload: dict[str, Any], kind: str) -> str | None:
    if kind == "context_extract":
        return _non_empty_string(payload.get("extract_ref"))
    if kind == "context_selection":
        return _non_empty_string(payload.get("selection_ref"))
    if kind == "privacy_preflight":
        receipt_id = _non_empty_string(payload.get("receipt_id"))
        return f"receipt://privacy-preflight/{receipt_id}" if receipt_id else None
    if kind == "projection":
        projection_id = _non_empty_string(payload.get("projection_id"))
        return f"projection://{projection_id}" if projection_id else None
    return _non_empty_string(payload.get("receipt_id"))


def _receipt_ids(payload: dict[str, Any], kind: str) -> list[str]:
    ids = [
        _receipt_primary_ref(payload, kind),
        _non_empty_string(payload.get("receipt_id")),
        _non_empty_string(payload.get("selection_id")),
        _non_empty_string(payload.get("selection_ref")),
        _non_empty_string(payload.get("extract_id")),
        _non_empty_string(payload.get("extract_ref")),
        _non_empty_string(payload.get("projection_id")),
    ]
    if kind == "context_selection":
        selection_id = _non_empty_string(payload.get("selection_id"))
        if selection_id:
            ids.append(f"context-selection://{selection_id}")
    if kind == "context_extract":
        extract_id = _non_empty_string(payload.get("extract_id"))
        if extract_id:
            ids.append(f"context-extract://{extract_id}")
    if kind == "privacy_preflight":
        receipt_id = _non_empty_string(payload.get("receipt_id"))
        if receipt_id:
            ids.append(f"receipt://privacy-preflight/{receipt_id}")
    if kind == "projection":
        projection_id = _non_empty_string(payload.get("projection_id"))
        if projection_id:
            ids.append(f"projection://{projection_id}")
    return _unique([value for value in ids if value])


def _receipt_links(payload: dict[str, Any], kind: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    if kind == "context_extract":
        prepare = payload.get("prepare") if isinstance(payload.get("prepare"), dict) else {}
        _add_link(links, "context_selection_receipt_path", prepare.get("receipt_path"))
        _add_link(links, "context_selection_ref", prepare.get("selection_ref"))
        for projection in payload.get("projections") or []:
            if not isinstance(projection, dict):
                continue
            _add_link(links, "projection_receipt_path", projection.get("receipt_path"))
            receipt = projection.get("receipt") if isinstance(projection.get("receipt"), dict) else {}
            _add_link(links, "projection_context_selection_ref", receipt.get("context_selection_ref"))
    elif kind == "context_selection":
        _add_link(links, "privacy_preflight_receipt_path", payload.get("privacy_preflight_receipt_path"))
        _add_link(links, "privacy_preflight_ref", payload.get("privacy_preflight_ref"))
    elif kind == "projection":
        _add_link(links, "context_selection_ref", payload.get("context_selection_ref"))
    return links


def _add_link(links: list[dict[str, str]], relation: str, value: Any) -> None:
    text = _non_empty_string(value)
    if text:
        links.append({"relation": relation, "target": text})


def _receipt_status_summary(payload: dict[str, Any], kind: str) -> dict[str, Any]:
    if kind == "context_extract":
        prepare = payload.get("prepare") if isinstance(payload.get("prepare"), dict) else {}
        return {
            "status": payload.get("status"),
            "dry_run": bool(payload.get("dry_run", False)),
            "idempotency_key": payload.get("idempotency_key"),
            "object_counts": payload.get("object_counts") or {},
            "selection_status": prepare.get("selection_status"),
            "handoff_ready": prepare.get("handoff_ready"),
            "projection_count": len(payload.get("projections") or []),
            "skipped_projection_count": len(payload.get("skipped_projections") or []),
        }
    if kind == "context_selection":
        quality = payload.get("context_quality_receipt") if isinstance(payload.get("context_quality_receipt"), dict) else {}
        density = quality.get("density_scorecard") if isinstance(quality.get("density_scorecard"), dict) else {}
        return {
            "budget_status": payload.get("budget_status"),
            "privacy_preflight_ref": payload.get("privacy_preflight_ref"),
            "selected_slice_count": len(payload.get("selected_slice_refs") or []),
            "required_refs_retained": quality.get("required_refs_retained"),
            "quality_status": quality.get("status") or density.get("status"),
            "search_stop_reason": payload.get("search_stop_reason"),
        }
    if kind == "privacy_preflight":
        return {
            "decision": payload.get("decision"),
            "selected_slice_count": len(payload.get("selected_slice_refs") or []),
            "blocked_slice_count": len(payload.get("blocked_slice_refs") or []),
        }
    if kind == "projection":
        return {
            "target_kind": payload.get("target_kind"),
            "target_path": payload.get("target_path"),
            "output_status": payload.get("output_status"),
            "review_state": payload.get("review_state"),
            "selected_slice_count": len(payload.get("selected_slice_refs") or []),
            "context_selection_ref": payload.get("context_selection_ref"),
        }
    return {"status": payload.get("status")}


def _resolve_target_receipt(
    inventory: dict[str, Any],
    *,
    root: Path,
    receipt_path: Path | None,
    receipt_ref: str | None,
    latest: bool,
) -> dict[str, Any] | None:
    if receipt_path is not None:
        resolved = receipt_path if receipt_path.is_absolute() else root / receipt_path
        path_key = str(resolved.resolve())
        if path_key not in inventory["by_path"]:
            raise FileNotFoundError(path_key)
        return inventory["by_path"][path_key]
    if receipt_ref:
        target = _resolve_receipt_link({"target": receipt_ref, "relation": "target"}, inventory, root=root)
        if target is None:
            raise ValueError(f"unknown receipt_ref: {receipt_ref}")
        return target
    if latest:
        receipts = list(inventory["receipts"])
        if not receipts:
            return None
        return max(receipts, key=lambda receipt: int(receipt.get("mtime_ns") or 0))
    return None


def _build_receipt_chain(
    target: dict[str, Any],
    inventory: dict[str, Any],
    *,
    include_payload: bool,
) -> dict[str, Any]:
    pending = [target]
    visited: set[str] = set()
    nodes: list[dict[str, Any]] = []
    missing_links: list[dict[str, str]] = []
    warnings: list[str] = []
    root = Path(str(inventory["root"]))
    chain_receipts: list[dict[str, Any]] = []
    while pending:
        receipt = pending.pop(0)
        path_key = receipt["path"]
        if path_key in visited:
            continue
        visited.add(path_key)
        chain_receipts.append(receipt)
        node_links: list[dict[str, str]] = []
        for link in receipt["links"]:
            linked = _resolve_receipt_link(link, inventory, root=root)
            if linked is None:
                missing_links.append(
                    {
                        "from_path": receipt["path"],
                        "relation": link["relation"],
                        "target": link["target"],
                    }
                )
                continue
            node_links.append(
                {
                    "relation": link["relation"],
                    "target": link["target"],
                    "resolved_path": linked["path"],
                    "kind": linked["kind"],
                    "primary_ref": linked.get("primary_ref"),
                }
            )
            if linked["path"] not in visited:
                pending.append(linked)
        node = _public_receipt_summary(receipt, include_payload=include_payload)
        node["linked_receipts"] = node_links
        nodes.append(node)
        _extend_chain_warnings(warnings, receipt)
    return {
        "root_receipt": _public_receipt_summary(target, include_payload=False),
        "status": "warn" if missing_links or warnings else "pass",
        "node_count": len(nodes),
        "nodes": nodes,
        "missing_links": missing_links,
        "warnings": _unique(warnings),
        "context_summary": _chain_context_summary(chain_receipts),
    }


def _resolve_receipt_link(link: dict[str, str], inventory: dict[str, Any], *, root: Path) -> dict[str, Any] | None:
    target = str(link.get("target") or "").strip()
    if not target:
        return None
    if target in inventory["by_id"]:
        return inventory["by_id"][target]
    candidate_path = Path(target)
    if candidate_path.suffix.lower() == ".json":
        resolved = candidate_path if candidate_path.is_absolute() else root / candidate_path
        return inventory["by_path"].get(str(resolved.resolve()))
    name = target.rsplit("/", 1)[-1]
    return inventory["by_id"].get(name)


def _public_receipt_summary(receipt: dict[str, Any], *, include_payload: bool) -> dict[str, Any]:
    summary = {
        "path": receipt["path"],
        "kind": receipt["kind"],
        "schema": receipt["schema"],
        "primary_ref": receipt.get("primary_ref"),
        "ids": list(receipt.get("ids") or []),
        "summary": dict(receipt.get("summary") or {}),
    }
    if include_payload:
        summary["payload"] = receipt["payload"]
    return summary


def _chain_context_summary(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    selected_slice_refs: list[str] = []
    required_slice_refs: list[str] = []
    source_refs: list[str] = []
    object_refs: list[str] = []
    privacy_decisions: list[str] = []
    projection_targets: list[str] = []
    quality_statuses: list[str] = []
    for receipt in receipts:
        payload = receipt["payload"]
        selected_slice_refs.extend(_string_list(payload.get("selected_slice_refs")))
        required_slice_refs.extend(_string_list(payload.get("required_slice_refs")))
        source_refs.extend(_string_list(payload.get("source_refs")))
        object_refs.extend(_string_list(payload.get("object_refs")))
        if receipt["kind"] == "context_extract":
            object_refs.extend(_string_list(payload.get("object_refs")))
            prepare = payload.get("prepare") if isinstance(payload.get("prepare"), dict) else {}
            selected_slice_refs.extend(_string_list(prepare.get("selected_slice_refs")))
            required_slice_refs.extend(_string_list(prepare.get("required_slice_refs")))
        if receipt["kind"] == "privacy_preflight":
            decision = _non_empty_string(payload.get("decision"))
            if decision:
                privacy_decisions.append(decision)
        if receipt["kind"] == "projection":
            target_kind = _non_empty_string(payload.get("target_kind"))
            if target_kind:
                projection_targets.append(target_kind)
        quality = payload.get("context_quality_receipt") if isinstance(payload.get("context_quality_receipt"), dict) else {}
        density = quality.get("density_scorecard") if isinstance(quality.get("density_scorecard"), dict) else {}
        quality_status = _non_empty_string(quality.get("status") or density.get("status"))
        if quality_status:
            quality_statuses.append(quality_status)
    return {
        "selected_slice_refs": _unique(selected_slice_refs),
        "required_slice_refs": _unique(required_slice_refs),
        "source_refs": _unique(source_refs),
        "object_refs": _unique(object_refs),
        "privacy_decisions": _unique(privacy_decisions),
        "projection_targets": _unique(projection_targets),
        "quality_statuses": _unique(quality_statuses),
    }


def _extend_chain_warnings(warnings: list[str], receipt: dict[str, Any]) -> None:
    payload = receipt["payload"]
    kind = receipt["kind"]
    if kind == "context_extract":
        status = _non_empty_string(payload.get("status"))
        if status in {"blocked", "dry_run"}:
            warnings.append(f"context_extract_status:{status}")
    elif kind == "context_selection":
        budget_status = _non_empty_string(payload.get("budget_status"))
        if budget_status and budget_status != "within_budget":
            warnings.append(f"context_selection_budget:{budget_status}")
        quality = payload.get("context_quality_receipt") if isinstance(payload.get("context_quality_receipt"), dict) else {}
        if quality.get("required_refs_retained") is False:
            warnings.append("context_quality_required_refs_missing")
    elif kind == "privacy_preflight":
        decision = _non_empty_string(payload.get("decision"))
        if decision in {"review", "block"}:
            warnings.append(f"privacy_preflight_decision:{decision}")
    elif kind == "projection":
        review_state = _non_empty_string(payload.get("review_state"))
        if review_state and review_state != "approved":
            warnings.append(f"projection_review_state:{review_state}")


def _chain_next_actions(chain: dict[str, Any]) -> list[dict[str, str]]:
    if chain["missing_links"]:
        return [
            {
                "kind": "repair_receipts",
                "description": "Rerun context-prepare or context-project so receipt links point at existing local receipt files.",
            }
        ]
    warnings = set(chain.get("warnings") or [])
    if "context_extract_status:dry_run" in warnings:
        return [
            {
                "kind": "run_context_extract",
                "description": "Rerun context-extract without --dry-run to import sources and prepare receipts.",
            }
        ]
    if any(str(item).startswith("context_extract_status:blocked") for item in warnings):
        return [
            {
                "kind": "inspect_prepare",
                "description": "Inspect selection warnings before projecting extracted context.",
            }
        ]
    return [
        {
            "kind": "inspect_chain",
            "description": "Review selected refs, privacy decisions, quality receipts, and projection targets before sharing context.",
        }
    ]


def _inventory_next_actions(receipts: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not receipts:
        return [
            {
                "kind": "create_receipt",
                "description": "Run context-extract --dry-run or context-prepare --write-receipt to create an inspectable receipt.",
            }
        ]
    return [
        {
            "kind": "inspect_receipt",
            "description": "Run receipt-inspect with --receipt-path or --receipt-ref to inspect one receipt chain.",
        }
    ]


def _summary_label(kind: Any) -> str:
    return {
        "context_extract": "context extract",
        "context_selection": "context selection",
        "privacy_preflight": "privacy preflight",
        "context_quality": "context quality",
        "quality_scorecard": "quality scorecard",
        "projection": "projection",
    }.get(str(kind or ""), str(kind or "receipt"))


def _append_next_actions(lines: list[str], actions: Any) -> None:
    if not isinstance(actions, list) or not actions:
        return
    lines.append("Next actions:")
    for action in actions:
        if not isinstance(action, dict):
            continue
        description = str(action.get("description") or action.get("kind") or "").strip()
        if description:
            lines.append(f"- {description}")


def _non_empty_string(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
