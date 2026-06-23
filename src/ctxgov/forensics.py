from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


FORENSICS_TIMELINE_SCHEMA_ID = "ctxvault.public-forensics-timeline/v0"
FORENSICS_TRACE_SCHEMA_ID = "ctxvault.public-forensics-trace/v0"
FORENSICS_GAPS_SCHEMA_ID = "ctxvault.public-forensics-gaps/v0"


def build_forensic_timeline(fixture_path: Path, *, limit: int = 100) -> dict[str, Any]:
    fixture = _load_fixture(fixture_path)
    events: list[dict[str, Any]] = []
    dispositions_by_finding: dict[str, list[dict[str, Any]]] = {}
    for disposition in fixture.get("dispositions", []):
        dispositions_by_finding.setdefault(str(disposition.get("finding_id") or ""), []).append(disposition)
    for run in fixture.get("runs", []):
        events.append({"event_at": run.get("created_at"), "event_type": "run_recorded", "run_id": run.get("run_id"), "finding_count": run.get("finding_count", 0)})
        for finding in run.get("findings", []):
            fid = str(finding.get("finding_id") or "")
            events.append({"event_at": run.get("created_at"), "event_type": "finding_recorded", "run_id": run.get("run_id"), "finding_id": fid, "source_ref": finding.get("source_ref"), "reason": finding.get("reason")})
            for disposition in dispositions_by_finding.get(fid, []):
                events.append({"event_at": disposition.get("created_at"), "event_type": "disposition_recorded", "finding_id": fid, "decision": disposition.get("decision"), "reviewer": disposition.get("reviewer")})
    events.sort(key=lambda item: str(item.get("event_at") or ""))
    return {"schema_id": FORENSICS_TIMELINE_SCHEMA_ID, "generated_at": _utc_now(), "fixture": str(fixture_path.resolve()), "event_count": len(events[:limit]), "events": events[:limit], "side_effect_boundary": _side_effect_boundary()}


def trace_evidence_path(fixture_path: Path, finding_id: str) -> dict[str, Any]:
    fixture = _load_fixture(fixture_path)
    finding: dict[str, Any] = {}
    run_info: dict[str, Any] = {}
    for run in fixture.get("runs", []):
        for candidate in run.get("findings", []):
            if str(candidate.get("finding_id") or "") == finding_id:
                finding = candidate
                run_info = {key: run.get(key) for key in ("run_id", "created_at", "decision", "triggered_by", "root_path")}
                break
        if finding:
            break
    dispositions = [item for item in fixture.get("dispositions", []) if str(item.get("finding_id") or "") == finding_id]
    gaps = []
    if not finding:
        gaps.append("finding_not_found")
    if finding and not dispositions:
        gaps.append("no_disposition_recorded")
    return {"schema_id": FORENSICS_TRACE_SCHEMA_ID, "generated_at": _utc_now(), "finding_id": finding_id, "finding": finding, "run": run_info, "dispositions": dispositions, "gaps": gaps, "side_effect_boundary": _side_effect_boundary()}


def identify_evidence_gaps(fixture_path: Path) -> dict[str, Any]:
    fixture = _load_fixture(fixture_path)
    disposition_ids = {str(item.get("finding_id") or "") for item in fixture.get("dispositions", [])}
    gaps = []
    for run in fixture.get("runs", []):
        for finding in run.get("findings", []):
            fid = str(finding.get("finding_id") or "")
            if fid and fid not in disposition_ids:
                gaps.append({"finding_id": fid, "gap_type": "no_disposition_recorded", "source_ref": finding.get("source_ref")})
    return {"schema_id": FORENSICS_GAPS_SCHEMA_ID, "generated_at": _utc_now(), "fixture": str(fixture_path.resolve()), "gap_count": len(gaps), "gaps": gaps, "side_effect_boundary": _side_effect_boundary()}


def _load_fixture(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if payload.get("schema_id") != "ctxgov.public-forensics-fixture/v0":
        raise ValueError(f"unsupported forensics fixture schema_id: {payload.get('schema_id')}")
    return payload


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_access_performed": False,
        "provider_or_model_call_performed": False,
        "runtime_or_adapter_executed": False,
        "target_file_written": False,
        "receipt_store_created": False,
        "scheduler_or_daemon_started": False,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
