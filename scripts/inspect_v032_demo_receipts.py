#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def inspect_receipts(*, root: Path | None = None, summary_path: Path | None = None) -> dict[str, Any]:
    resolved_summary_path = _resolve_summary_path(root=root, summary_path=summary_path)
    summary = _read_json(resolved_summary_path)
    selected_refs = list(summary["selection"]["selected_slice_refs"])
    checks = [
        _check_context_selection_receipt(summary["selection"], selected_refs),
        *[
            _check_projection_receipt(name, projection, selected_refs)
            for name, projection in summary["projections"].items()
        ],
    ]
    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    report = {
        "schema_id": "ctxvault.v0.3.2-demo-receipt-inspection/v1",
        "status": status,
        "summary_path": str(resolved_summary_path),
        "selected_slice_refs": selected_refs,
        "checks": checks,
    }
    report_path = resolved_summary_path.parent / "receipt-inspection.json"
    _write_json(report_path, report)
    report["report_path"] = str(report_path.resolve())
    _write_json(report_path, report)
    return report


def _check_context_selection_receipt(selection: dict[str, Any], selected_refs: list[str]) -> dict[str, Any]:
    receipt_path = Path(selection["receipt_path"])
    errors: list[str] = []
    payload: dict[str, Any] = {}
    if not receipt_path.exists():
        errors.append("context selection receipt is missing")
    else:
        payload = _read_json(receipt_path)
        if payload.get("schema_id") != "ctxvault.context-selection-receipt/v1":
            errors.append("context selection receipt schema_id mismatch")
        if payload.get("selected_slice_refs") != selected_refs:
            errors.append("context selection receipt selected_slice_refs mismatch")
        if payload.get("budget_status") != selection.get("budget_status"):
            errors.append("context selection receipt budget_status mismatch")
    return {
        "name": "context_selection_receipt",
        "status": "fail" if errors else "pass",
        "receipt_path": str(receipt_path),
        "errors": errors,
        "selection_ref": payload.get("selection_ref"),
    }


def _check_projection_receipt(name: str, projection: dict[str, Any], selected_refs: list[str]) -> dict[str, Any]:
    output_path = Path(projection["output_path"])
    receipt_path = Path(projection["receipt_path"])
    errors: list[str] = []
    payload: dict[str, Any] = {}
    if not output_path.exists():
        errors.append("projection output is missing")
    if not receipt_path.exists():
        errors.append("projection receipt is missing")
    if receipt_path.exists():
        payload = _read_json(receipt_path)
        if payload.get("schema_version") != "ctxvault.projection-receipt/v1":
            errors.append("projection receipt schema_version mismatch")
        if payload.get("selected_slice_refs") != selected_refs:
            errors.append("projection receipt selected_slice_refs mismatch")
        if payload.get("policy_decision") != "allow":
            errors.append("projection receipt policy_decision is not allow")
        if payload.get("review_state") != "approved":
            errors.append("projection receipt review_state is not approved")
        privacy = payload.get("privacy_preflight") if isinstance(payload.get("privacy_preflight"), dict) else {}
        if privacy.get("decision") != "allow":
            errors.append("projection privacy preflight did not allow")
        if not str(payload.get("context_selection_ref") or "").startswith("context-selection://ctxsel_"):
            errors.append("projection receipt is not linked to a context-selection ref")
    if output_path.exists() and payload:
        expected_sha = hashlib.sha256(output_path.read_bytes()).hexdigest()
        if payload.get("output_sha256") != expected_sha:
            errors.append("projection output_sha256 mismatch")
    return {
        "name": f"projection_receipt:{name}",
        "status": "fail" if errors else "pass",
        "output_path": str(output_path),
        "receipt_path": str(receipt_path),
        "errors": errors,
        "target_kind": payload.get("target_kind"),
        "context_selection_ref": payload.get("context_selection_ref"),
    }


def _resolve_summary_path(*, root: Path | None, summary_path: Path | None) -> Path:
    if summary_path is not None:
        return summary_path.resolve()
    if root is None:
        root = Path("/tmp/ctxvault-v032-deterministic-demo")
    return (root.resolve() / "artifacts" / "v0.3.2-demo" / "summary.json").resolve()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.resolve().parent.mkdir(parents=True, exist_ok=True)
    path.resolve().write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect the receipt chain emitted by the v0.3.2 deterministic demo.")
    parser.add_argument("--root", type=Path, help="Demo root containing artifacts/v0.3.2-demo/summary.json.")
    parser.add_argument("--summary-path", type=Path, help="Explicit demo summary path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = inspect_receipts(root=args.root, summary_path=args.summary_path)
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
