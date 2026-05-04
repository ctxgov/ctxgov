#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ctxvault.core import CtxVault
from ctxvault.layout import default_layout
from ctxvault.surface import CtxVaultSurface


WORKSTREAM_ID = "ws_20260421_ctxvault_schema"
WORKSTREAM_REF = f"workstream://{WORKSTREAM_ID}"


def run_scorecard(*, root: Path) -> dict[str, Any]:
    root = root.resolve()
    surface = CtxVaultSurface(CtxVault(default_layout(root)))
    surface.vault.initialize()
    surface.vault.import_core_fixtures(REPO_ROOT / "fixtures" / "core")

    source_path = root / "sources" / "v034-context-extract-stability.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(
        "# v0.3.4 context extract stability\n\n"
        "Stable one-click extraction should preserve source fingerprints, object refs, selected slices, "
        "privacy receipts, and projection receipts across repeated local runs.",
        encoding="utf-8",
    )

    dry_run = surface.context_extract(
        source_paths=[source_path],
        source_kind="auto",
        scope_kind="project",
        scope_value="ctxvault",
        prepare_query="stable one click extraction privacy projection receipts",
        workstream_ref=WORKSTREAM_REF,
        project_targets=["workstream-brief"],
        workstream_id=WORKSTREAM_ID,
        dry_run=True,
    )
    first = surface.context_extract(
        source_paths=[source_path],
        source_kind="auto",
        scope_kind="project",
        scope_value="ctxvault",
        prepare_query="stable one click extraction privacy projection receipts",
        workstream_ref=WORKSTREAM_REF,
        project_targets=["workstream-brief"],
        workstream_id=WORKSTREAM_ID,
    )
    second = surface.context_extract(
        source_paths=[source_path],
        source_kind="auto",
        scope_kind="project",
        scope_value="ctxvault",
        prepare_query="stable one click extraction privacy projection receipts",
        workstream_ref=WORKSTREAM_REF,
        project_targets=["workstream-brief"],
        workstream_id=WORKSTREAM_ID,
    )
    inspection = surface.receipt_inspect(receipt_path=Path(second["receipt_path"]))
    doctor = surface.doctor_report()
    doctor_checks = {check["name"]: check for check in doctor["checks"]}

    pass_checks = {
        "dry_run_writes_plan_without_imports": dry_run["status"] == "dry_run" and not dry_run["imports"],
        "stable_idempotency_key": first["receipt"]["idempotency_key"] == second["receipt"]["idempotency_key"],
        "stable_source_fingerprint": first["receipt"]["source_fingerprints"] == second["receipt"]["source_fingerprints"],
        "stable_object_refs": first["receipt"]["object_refs"] == second["receipt"]["object_refs"],
        "stable_selected_slice_refs": (first["prepare"] or {}).get("selected_slice_refs")
        == (second["prepare"] or {}).get("selected_slice_refs"),
        "no_duplicate_context_bloat": (first["slice_rebuild"] or {}).get("slice_count")
        == (second["slice_rebuild"] or {}).get("slice_count"),
        "receipt_chain_inspects": inspection["status"] == "pass" and not inspection["chains"][0]["missing_links"],
        "doctor_extract_checks_pass": doctor_checks["context_extract_receipts"]["status"] == "pass"
        and doctor_checks["projection_selection_receipts"]["status"] == "pass",
        "projection_gated_by_handoff_ready": bool(second["prepare"].get("handoff_ready")) and len(second["projections"]) == 1,
    }
    status = "pass" if all(pass_checks.values()) else "fail"
    scorecard = {
        "schema_id": "ctxvault.v0.3.4-context-extract-stability-scorecard/v1",
        "status": status,
        "root": str(root),
        "source_path": str(source_path),
        "dry_run_receipt_path": dry_run["receipt_path"],
        "first_receipt_path": first["receipt_path"],
        "second_receipt_path": second["receipt_path"],
        "pass_checks": pass_checks,
        "idempotency_key": second["receipt"]["idempotency_key"],
        "source_fingerprints": second["receipt"]["source_fingerprints"],
        "object_refs": second["receipt"]["object_refs"],
        "selected_slice_refs": second["prepare"].get("selected_slice_refs"),
        "slice_count": second["slice_rebuild"].get("slice_count"),
        "receipt_inspection_status": inspection["status"],
        "doctor_status": doctor["status"],
    }
    output_path = root / "artifacts" / "v0.3.4-context-extract-stability-scorecard.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scorecard["scorecard_path"] = str(output_path)
    output_path.write_text(json.dumps(scorecard, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return scorecard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the v0.3.4 deterministic context-extract stability scorecard.")
    parser.add_argument("--root", type=Path, default=Path("/tmp/ctxvault-v034-context-extract-stability"))
    args = parser.parse_args(argv)
    scorecard = run_scorecard(root=args.root)
    print(json.dumps(scorecard, indent=2, sort_keys=True))
    return 0 if scorecard["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
