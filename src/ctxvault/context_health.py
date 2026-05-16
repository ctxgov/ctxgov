from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


CONTEXT_HEALTH_REPORT_SCHEMA_ID = "ctxvault.context-health-report/v0"
CONTEXT_HEALTH_RUN_RECEIPT_SCHEMA_ID = "ctxvault.context-health-run-receipt/v0"
CONTEXT_HEALTH_BACKUP_MANIFEST_SCHEMA_ID = "ctxvault.context-health-backup-manifest/v0"

SCAN_SUFFIXES = {".md", ".markdown", ".txt", ".log", ".json"}
EXCLUDED_DIR_NAMES = {
    ".ctxvault",
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}
DEFAULT_MAX_FILE_BYTES = 512 * 1024
AUTHORITY_LAYERS = ("claim", "context", "memory", "action")


def build_context_health_report(
    scan_path: Path,
    *,
    output_root: Path | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict[str, Any]:
    resolved_scan_path = scan_path.resolve()
    _validate_scan_path(resolved_scan_path, max_file_bytes=max_file_bytes)
    storage_base = _storage_base_for_scan_path(resolved_scan_path)
    resolved_output_root = _resolve_output_root(storage_base, output_root)
    backup_root = storage_base / ".ctxvault" / "backups" / "context-health-doctor"
    scanned_files = _collect_scan_files(resolved_scan_path, max_file_bytes=max_file_bytes)
    findings = _build_findings(resolved_scan_path, scanned_files)
    report_id = _report_id(resolved_scan_path, findings)
    run_root = resolved_output_root / "runs" / report_id
    for finding in findings:
        finding["rollback_ref"] = f"delete://{run_root}"

    return {
        "schema_id": CONTEXT_HEALTH_REPORT_SCHEMA_ID,
        "report_id": report_id,
        "generated_at": _utc_now(),
        "scanned_path": str(resolved_scan_path),
        "mode": "read_only_local_scan",
        "output_policy": {
            "output_root": str(resolved_output_root),
            "health_root": str(resolved_output_root),
            "backup_root": str(backup_root.resolve()),
            "raw_source_copied": False,
            "target_files_written": False,
        },
        "decision_table": _decision_table(findings),
        "summary": _summary(findings),
        "findings": findings,
        "evidence": _evidence_accounting(findings, scanned_files),
        "side_effects": _false_side_effects(),
        "rollback": {
            "rollback_ref": f"delete://{run_root}",
            "delete_paths": [str(run_root)],
            "supersede_with": "Regenerate the Context Health Report after resolving or caveating findings.",
        },
    }


def write_context_health_report(
    scan_path: Path,
    *,
    output_root: Path | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> dict[str, Any]:
    resolved_scan_path = scan_path.resolve()
    _validate_scan_path(resolved_scan_path, max_file_bytes=max_file_bytes)
    storage_base = _storage_base_for_scan_path(resolved_scan_path)
    resolved_output_root = _resolve_output_root(storage_base, output_root)
    report = build_context_health_report(
        resolved_scan_path,
        output_root=resolved_output_root,
        max_file_bytes=max_file_bytes,
    )
    report_id = str(report["report_id"])
    run_root = resolved_output_root / "runs" / report_id
    json_report_path = run_root / "context-health-report.json"
    markdown_report_path = run_root / "context-health-report.md"
    receipt_path = run_root / "context-health-run-receipt.json"
    evidence_manifest_path = resolved_output_root / "evidence" / f"{report_id}-evidence-manifest.json"
    reports_json_path = resolved_output_root / "reports" / "json" / f"{report_id}.json"
    reports_markdown_path = resolved_output_root / "reports" / "markdown" / f"{report_id}.md"
    receipt_copy_path = resolved_output_root / "receipts" / f"{report_id}-run-receipt.json"
    index_path = resolved_output_root / "index" / "context-health-report-index.jsonl"

    for path in [
        run_root,
        resolved_output_root / "reports" / "json",
        resolved_output_root / "reports" / "markdown",
        resolved_output_root / "evidence",
        resolved_output_root / "receipts",
        resolved_output_root / "index",
        resolved_output_root / "tmp",
        resolved_output_root / "restore-preview",
    ]:
        path.mkdir(parents=True, exist_ok=True)

    markdown = render_context_health_markdown(report)
    _write_json(json_report_path, report)
    _write_text(markdown_report_path, markdown)
    _write_json(reports_json_path, report)
    _write_text(reports_markdown_path, markdown)
    _write_json(evidence_manifest_path, _evidence_manifest(report, resolved_scan_path, _collect_scan_files(resolved_scan_path, max_file_bytes=max_file_bytes)))

    receipt = _run_receipt(
        report=report,
        json_report_path=json_report_path,
        markdown_report_path=markdown_report_path,
        evidence_manifest_path=evidence_manifest_path,
        output_root=resolved_output_root,
        receipt_copy_path=receipt_copy_path,
    )
    _write_json(receipt_path, receipt)
    _write_json(receipt_copy_path, receipt)

    backup_manifest = _write_backup_manifest(
        report=report,
        scan_path=resolved_scan_path,
        output_paths=[
            json_report_path,
            markdown_report_path,
            receipt_path,
            evidence_manifest_path,
            reports_json_path,
            reports_markdown_path,
        ],
    )

    index_entry = {
        "report_id": report_id,
        "generated_at": report["generated_at"],
        "json_report_path": str(json_report_path),
        "markdown_report_path": str(markdown_report_path),
        "run_receipt_path": str(receipt_path),
        "backup_manifest_path": backup_manifest["manifest_path"],
        "finding_count": report["summary"]["finding_count"],
        "json_sha256": _sha256_file(json_report_path),
        "markdown_sha256": _sha256_file(markdown_report_path),
        "rollback_ref": report["rollback"]["rollback_ref"],
    }
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_entry, ensure_ascii=True, sort_keys=True) + "\n")

    rollback = _write_result_rollback(
        report=report,
        run_root=run_root,
        reports_json_path=reports_json_path,
        reports_markdown_path=reports_markdown_path,
        evidence_manifest_path=evidence_manifest_path,
        receipt_copy_path=receipt_copy_path,
        backup_manifest_path=Path(str(backup_manifest["manifest_path"])),
        index_path=index_path,
    )
    return {
        "schema_id": "ctxvault.context-health-write-result/v0",
        "report_id": report_id,
        "mode": "read_only_local_scan",
        "scanned_path": str(resolved_scan_path),
        "output_root": str(resolved_output_root),
        "json_report_path": str(json_report_path),
        "markdown_report_path": str(markdown_report_path),
        "run_receipt_path": str(receipt_path),
        "evidence_manifest_path": str(evidence_manifest_path),
        "index_path": str(index_path),
        "backup_manifest_path": backup_manifest["manifest_path"],
        "backup_root": backup_manifest["backup_root"],
        "raw_source_copied": False,
        "target_files_written": False,
        "side_effects": _false_side_effects(),
        "rollback": rollback,
        "summary": report["summary"],
        "decision_table": report["decision_table"],
        "report": report,
    }


def summarize_context_health_write_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": "ctxvault.context-health-write-summary/v0",
        "report_schema_id": CONTEXT_HEALTH_REPORT_SCHEMA_ID,
        "report_id": result["report_id"],
        "mode": result["mode"],
        "scanned_path": result["scanned_path"],
        "output_root": result["output_root"],
        "json_report_path": result["json_report_path"],
        "markdown_report_path": result["markdown_report_path"],
        "run_receipt_path": result["run_receipt_path"],
        "evidence_manifest_path": result["evidence_manifest_path"],
        "backup_manifest_path": result["backup_manifest_path"],
        "raw_source_copied": result["raw_source_copied"],
        "target_files_written": result["target_files_written"],
        "side_effects": result["side_effects"],
        "rollback": result["rollback"],
        "summary": result["summary"],
        "decision_table": result["decision_table"],
    }


def render_context_health_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Context Health Report",
        "",
        f"- Report: `{report['report_id']}`",
        f"- Mode: `{report['mode']}`",
        f"- Scanned path: `{report['scanned_path']}`",
        f"- Findings: `{report['summary']['finding_count']}`",
        "",
        "## Decision Table",
        "",
        "| Decision | Status | Reason | Next check | Rollback |",
        "| --- | --- | --- | --- | --- |",
    ]
    for layer in AUTHORITY_LAYERS:
        decision = report["decision_table"][layer]
        lines.append(
            "| "
            + " | ".join(
                [
                    layer,
                    decision["status"],
                    _md_cell(decision["reason"]),
                    _md_cell(decision["next_check"]),
                    _md_cell(decision["rollback"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Findings", ""])
    if not report["findings"]:
        lines.append("No findings.")
    for finding in report["findings"]:
        lines.extend(
            [
                f"### {finding['finding_id']}",
                "",
                f"- Source: `{finding['source_ref']}`",
                f"- Type: `{finding['finding_type']}`",
                f"- Authority: `{', '.join(finding['authority_layer_affected'])}`",
                f"- Severity: `{finding['severity']}`",
                f"- Reason: {finding['reason']}",
                f"- Next: {finding['safe_rewrite_or_next_check']}",
                f"- Rollback: `{finding['rollback_ref']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _collect_scan_files(root: Path, *, max_file_bytes: int) -> list[dict[str, Any]]:
    if root.is_file():
        return [_scan_file(root, root.parent, max_file_bytes=max_file_bytes)]
    if not root.exists():
        return []
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
            continue
        if path.suffix.lower() not in SCAN_SUFFIXES and path.name not in {"AGENTS.md", "CLAUDE.md", "README.md"}:
            continue
        files.append(_scan_file(path, root, max_file_bytes=max_file_bytes))
    return files


def _scan_file(path: Path, root: Path, *, max_file_bytes: int) -> dict[str, Any]:
    rel = path.relative_to(root) if _is_relative_to(path, root) else Path(path.name)
    try:
        size = path.stat().st_size
    except OSError as exc:
        return {
            "path": path,
            "relative_path": str(rel),
            "source_ref": f"file://{rel}",
            "text": "",
            "sha256": "",
            "size_bytes": 0,
            "read_error": f"stat_error:{type(exc).__name__}",
        }
    try:
        sha256 = _sha256_file(path)
    except OSError as exc:
        return {
            "path": path,
            "relative_path": str(rel),
            "source_ref": f"file://{rel}",
            "text": "",
            "sha256": "",
            "size_bytes": size,
            "read_error": f"hash_error:{type(exc).__name__}",
        }
    if size > max_file_bytes:
        return {
            "path": path,
            "relative_path": str(rel),
            "source_ref": f"file://{rel}",
            "text": "",
            "sha256": sha256,
            "size_bytes": size,
            "read_error": "oversized",
        }
    try:
        text = path.read_text(encoding="utf-8")
        read_error = None
    except UnicodeDecodeError:
        text = ""
        read_error = "unicode_decode_error"
    except OSError as exc:
        text = ""
        read_error = f"read_error:{type(exc).__name__}"
    return {
        "path": path,
        "relative_path": str(rel),
        "source_ref": f"file://{rel}",
        "text": text,
        "sha256": sha256,
        "size_bytes": size,
        "read_error": read_error,
    }


def _build_findings(root: Path, scanned_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(_conflict_findings(scanned_files))
    findings.extend(_duplicate_rule_findings(scanned_files))
    for item in scanned_files:
        findings.extend(_file_findings(item))
    for idx, finding in enumerate(findings, start=1):
        finding["finding_id"] = f"chf_{idx:04d}_{finding['finding_type']}"
        finding["rollback_ref"] = f"delete://{root / '.ctxvault' / 'health'}/runs/<run_id>"
    return findings


def _conflict_findings(scanned_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    version_refs: dict[str, set[str]] = defaultdict(set)
    no_network_refs: set[str] = set()
    network_allowed_refs: set[str] = set()
    no_target_write_refs: set[str] = set()
    target_write_allowed_refs: set[str] = set()
    for item in scanned_files:
        text = item["text"]
        source_ref = item["source_ref"]
        if not text:
            continue
        for version in re.findall(r"\bv\d+\.\d+(?:\.\d+)?\b", text, flags=re.IGNORECASE):
            if re.search(r"\b(current|active|now|today)\b.{0,40}" + re.escape(version), text, flags=re.IGNORECASE) or re.search(
                re.escape(version) + r".{0,40}\b(current|active|now|today)\b",
                text,
                flags=re.IGNORECASE,
            ):
                version_refs[version.lower()].add(source_ref)
        lowered = text.lower()
        if re.search(r"\b(no|never|do not)\b.{0,30}\bnetwork\b", lowered):
            no_network_refs.add(source_ref)
        if re.search(r"\bnetwork\b.{0,30}\b(allowed|approved|enabled)\b", lowered):
            network_allowed_refs.add(source_ref)
        if re.search(r"\b(no|never|do not)\b.{0,40}\b(target|project|repo).{0,30}\bwrite", lowered):
            no_target_write_refs.add(source_ref)
        if re.search(r"\b(target|project|repo).{0,30}\bwrite.{0,30}\b(allowed|approved|enabled)\b", lowered):
            target_write_allowed_refs.add(source_ref)
    if len(version_refs) > 1:
        refs = sorted({ref for refs in version_refs.values() for ref in refs})
        findings.append(
            _finding(
                refs[0],
                "stale_context",
                ["context"],
                "high",
                f"Multiple current version claims are present: {', '.join(sorted(version_refs))}.",
                "Resolve the active version in instruction files before agent consumption.",
            )
        )
    if no_network_refs and network_allowed_refs:
        source = sorted(no_network_refs | network_allowed_refs)[0]
        findings.append(
            _finding(
                source,
                "conflicting_instruction",
                ["context", "action"],
                "high",
                "Network policy conflicts across scanned context.",
                "Choose one network boundary and regenerate context before use.",
            )
        )
    if no_target_write_refs and target_write_allowed_refs:
        source = sorted(no_target_write_refs | target_write_allowed_refs)[0]
        findings.append(
            _finding(
                source,
                "conflicting_instruction",
                ["context", "action"],
                "high",
                "Target-write policy conflicts across scanned context.",
                "Choose one target-write boundary and require an approval receipt before action.",
            )
        )
    return findings


def _duplicate_rule_findings(scanned_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_rule: dict[str, set[str]] = defaultdict(set)
    for item in scanned_files:
        for raw_line in item["text"].splitlines():
            normalized = " ".join(raw_line.strip().lower().split())
            if len(normalized) < 24:
                continue
            if not re.search(r"\b(always|never|must|required|do not|no)\b", normalized):
                continue
            by_rule[normalized].add(item["source_ref"])
    findings = []
    for rule, refs in sorted(by_rule.items()):
        if len(refs) < 2:
            continue
        findings.append(
            _finding(
                sorted(refs)[0],
                "duplicated_rule",
                ["context"],
                "low",
                f"Rule appears in multiple sources: {rule[:120]}",
                "Keep one canonical instruction and reference it from duplicates.",
            )
        )
    return findings


def _file_findings(item: dict[str, Any]) -> list[dict[str, Any]]:
    text = item["text"]
    source_ref = item["source_ref"]
    findings: list[dict[str, Any]] = []
    lowered = text.lower()
    if not text:
        return findings
    if _has_private_boundary_risk(lowered):
        findings.append(
            _finding(
                source_ref,
                "private_public_boundary_risk",
                ["claim", "context", "action"],
                "critical",
                "Potential private or secret-like material appears in context that may be published or projected.",
                "Redact or block this source before public use or projection.",
            )
        )
    if _has_unsupported_claim(lowered):
        findings.append(
            _finding(
                source_ref,
                "unsupported_claim",
                ["claim"],
                "high",
                "Public-quality, security, performance, compatibility, endorsement, stable-protocol, or target-write claim lacks local evidence.",
                "Attach source-fact, claim-lint, and rollback receipts or rewrite as internal experimental wording.",
            )
        )
    if _looks_like_summary_without_raw_refs(lowered):
        findings.append(
            _finding(
                source_ref,
                "missing_raw_ref",
                ["context", "memory"],
                "medium",
                "Summary-like context lacks raw refs, source refs, receipts, or digests.",
                "Add raw refs or receipts before relying on this summary.",
            )
        )
    if _looks_over_compressed(lowered):
        findings.append(
            _finding(
                source_ref,
                "over_compressed_summary",
                ["context", "memory"],
                "medium",
                "Summary is too compressed to audit what was selected or omitted.",
                "Expand with selected and omitted refs before reuse.",
            )
        )
    if _is_memory_without_lifecycle(item, lowered):
        findings.append(
            _finding(
                source_ref,
                "memory_without_lifecycle_or_rollback",
                ["memory"],
                "high",
                "Memory-like content lacks lifecycle, source, deletion, or rollback fields.",
                "Add lifecycle state, source refs, and rollback refs before memory promotion.",
            )
        )
    if _has_action_without_evidence(lowered):
        findings.append(
            _finding(
                source_ref,
                "action_or_publication_without_evidence",
                ["action", "claim"],
                "high",
                "Action or publication language appears without sufficient evidence or rollback.",
                "Add an approval receipt, evidence refs, and rollback before executing or publishing.",
            )
        )
    if _terminal_failure_hidden(item, lowered):
        findings.append(
            _finding(
                source_ref,
                "terminal_failure_hidden",
                ["context", "action"],
                "high",
                "Terminal summary claims success while failed tests, exit codes, or permission errors are present.",
                "Surface failed command, exit code, and permission errors in the next report.",
            )
        )
    return findings


def _finding(
    source_ref: str,
    finding_type: str,
    authority_layers: list[str],
    severity: str,
    reason: str,
    safe_rewrite_or_next_check: str,
) -> dict[str, Any]:
    return {
        "finding_id": "",
        "source_ref": source_ref,
        "finding_type": finding_type,
        "authority_layer_affected": authority_layers,
        "severity": severity,
        "reason": reason,
        "safe_rewrite_or_next_check": safe_rewrite_or_next_check,
        "rollback_ref": "",
    }


def _has_private_boundary_risk(text: str) -> bool:
    patterns = [
        r"\b(api[_-]?key|secret|password|token)\s*[:=]\s*\S+",
        r"\b[a-z0-9_]*(api[_-]?key|secret|password|token)[a-z0-9_]*\s*=\s*\S+",
        r"\bprivate key\b",
        r"\bauthorization:\s*\S+",
        r"\bbearer\s+[a-z0-9._-]{8,}\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _has_unsupported_claim(text: str) -> bool:
    patterns = [
        r"\bstable\s+(mgp|protocol|memory governance protocol)\b",
        r"\bsecurity\s+(complete|certified|guarantee|guaranteed)\b",
        r"\bperformance\s+(guarantee|certified|benchmark)\b",
        r"\bcompatibility\s+(guarantee|certified|complete)\b",
        r"\bendorsed\s+by\b",
        r"\btarget[- ]?write\s+(support|authority|ready)\b",
        r"\bhallucination\s+(prevention|guarantee|proof)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def _looks_like_summary_without_raw_refs(text: str) -> bool:
    if "summary" not in text and "summarized" not in text:
        return False
    return not re.search(r"\b(raw[_ -]?ref|source[_ -]?ref|receipt|sha256|file://|https?://)\b", text)


def _looks_over_compressed(text: str) -> bool:
    return bool(re.search(r"\b(many|various|several|lots of|important things|key things)\b", text)) and _looks_like_summary_without_raw_refs(text)


def _is_memory_without_lifecycle(item: dict[str, Any], text: str) -> bool:
    path_text = str(item["relative_path"]).lower()
    if "memory" not in path_text and "memory" not in text:
        return False
    return not re.search(r"\b(lifecycle|rollback|delete|deletion|ttl|expires|source[_ -]?ref|raw[_ -]?ref|receipt)\b", text)


def _has_action_without_evidence(text: str) -> bool:
    if not re.search(r"\b(publish|release|ship|deploy|push|write|open pr|create issue|target write)\b", text):
        return False
    if re.search(r"\b(no|without|missing)\s+(receipt|evidence|rollback|approval)\b", text):
        return True
    return not re.search(r"\b(receipt|evidence|rollback|approval|source[_ -]?ref|sha256)\b", text)


def _terminal_failure_hidden(item: dict[str, Any], text: str) -> bool:
    path = str(item["relative_path"]).lower()
    if not path.endswith((".log", ".txt")) and "terminal" not in path:
        return False
    has_success_summary = bool(re.search(r"\b(all checks passed|all passed|success|succeeded)\b", text))
    has_failure = bool(re.search(r"\b(failed|exit code[: ]+[1-9]\d*|permission denied|error:)\b", text))
    return has_success_summary and has_failure


def _decision_table(findings: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    by_layer: dict[str, list[dict[str, Any]]] = {layer: [] for layer in AUTHORITY_LAYERS}
    for finding in findings:
        for layer in finding["authority_layer_affected"]:
            by_layer[layer].append(finding)
    decisions: dict[str, dict[str, str]] = {}
    for layer, items in by_layer.items():
        if any(item["severity"] in {"critical", "high"} for item in items):
            status = "blocked"
        elif items:
            status = "caveated"
        else:
            status = "allowed"
        if items:
            reason = f"{len(items)} finding(s) affect {layer} authority."
            next_check = f"Resolve or caveat {layer} findings before relying on this layer."
        else:
            reason = f"No findings currently block {layer} authority in scanned local files."
            next_check = "Re-run the doctor after context changes."
        decisions[layer] = {
            "status": status,
            "reason": reason,
            "next_check": next_check,
            "rollback": "Delete or supersede the report run; no target files were written.",
        }
    return decisions


def _summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    severities = Counter(str(finding["severity"]) for finding in findings)
    finding_types = Counter(str(finding["finding_type"]) for finding in findings)
    return {
        "finding_count": len(findings),
        "severity_counts": dict(sorted(severities.items())),
        "finding_type_counts": dict(sorted(finding_types.items())),
    }


def _evidence_accounting(findings: list[dict[str, Any]], scanned_files: list[dict[str, Any]]) -> dict[str, list[str]]:
    selected = sorted({str(item["source_ref"]) for item in scanned_files if not item.get("read_error")})
    blocked = sorted({finding["source_ref"] for finding in findings if finding["severity"] in {"critical", "high"}})
    stale = sorted({finding["source_ref"] for finding in findings if finding["finding_type"] == "stale_context"})
    conflicting = sorted(
        {
            finding["source_ref"]
            for finding in findings
            if finding["finding_type"] in {"conflicting_instruction", "stale_context"}
        }
    )
    caveated = sorted({finding["source_ref"] for finding in findings if finding["severity"] in {"medium", "low", "info"}})
    omitted = sorted({str(item["source_ref"]) for item in scanned_files if item.get("read_error")})
    return {
        "selected_refs": selected,
        "omitted_refs": omitted,
        "blocked_refs": blocked,
        "stale_refs": stale,
        "conflicting_refs": conflicting,
        "caveated_refs": caveated,
    }


def _evidence_manifest(report: dict[str, Any], scan_path: Path, scanned_files: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_id": "ctxvault.context-health-evidence-manifest/v0",
        "report_id": report["report_id"],
        "generated_at": report["generated_at"],
        "scanned_path": str(scan_path),
        "raw_source_copied": False,
        "evidence": report["evidence"],
        "source_digest_refs": [
            {
                "source_ref": item["source_ref"],
                "sha256": item["sha256"],
                "size_bytes": item["size_bytes"],
                "read_error": item["read_error"],
            }
            for item in scanned_files
        ],
        "findings": [
            {
                "finding_id": finding["finding_id"],
                "source_ref": finding["source_ref"],
                "finding_type": finding["finding_type"],
                "severity": finding["severity"],
                "authority_layer_affected": finding["authority_layer_affected"],
                "rollback_ref": finding["rollback_ref"],
            }
            for finding in report["findings"]
        ],
    }


def _run_receipt(
    *,
    report: dict[str, Any],
    json_report_path: Path,
    markdown_report_path: Path,
    evidence_manifest_path: Path,
    output_root: Path,
    receipt_copy_path: Path,
) -> dict[str, Any]:
    return {
        "schema_id": CONTEXT_HEALTH_RUN_RECEIPT_SCHEMA_ID,
        "report_id": report["report_id"],
        "generated_at": report["generated_at"],
        "mode": report["mode"],
        "output_root": str(output_root),
        "json_report_path": str(json_report_path),
        "json_report_sha256": _sha256_file(json_report_path),
        "markdown_report_path": str(markdown_report_path),
        "markdown_report_sha256": _sha256_file(markdown_report_path),
        "evidence_manifest_path": str(evidence_manifest_path),
        "evidence_manifest_sha256": _sha256_file(evidence_manifest_path),
        "receipt_copy_path": str(receipt_copy_path),
        "raw_source_copied": False,
        "target_files_written": False,
        "side_effects": _false_side_effects(),
        "rollback_ref": report["rollback"]["rollback_ref"],
        "rollback": {
            "delete_paths": [
                str(Path(str(report["rollback"]["delete_paths"][0]))),
                str(json_report_path),
                str(markdown_report_path),
                str(evidence_manifest_path),
                str(receipt_copy_path),
            ],
            "index_policy": "Append-only index entries are audit history; supersede with a later run instead of editing source files.",
        },
    }


def _write_backup_manifest(
    *,
    report: dict[str, Any],
    scan_path: Path,
    output_paths: list[Path],
) -> dict[str, str]:
    backup_root = Path(str(report["output_policy"]["backup_root"])).resolve()
    report_backup_root = backup_root / str(report["report_id"])
    report_backup_root.mkdir(parents=True, exist_ok=True)
    manifest_path = report_backup_root / "backup-manifest.json"
    manifest = {
        "schema_id": CONTEXT_HEALTH_BACKUP_MANIFEST_SCHEMA_ID,
        "report_id": report["report_id"],
        "generated_at": report["generated_at"],
        "scanned_path": str(scan_path),
        "backup_root": str(backup_root),
        "raw_source_copied": False,
        "target_files_written": False,
        "side_effects": _false_side_effects(),
        "included_artifacts": [_artifact_entry(path) for path in output_paths],
        "excluded_material": [
            {
                "class": "raw_scanned_source",
                "reason": "Raw source copies are blocked by default for Context Health Doctor backups.",
            }
        ],
        "rollback": {
            "delete_paths": [str(report_backup_root)],
            "supersede_with": "Regenerate the manifest after regenerating the report.",
        },
    }
    _write_json(manifest_path, manifest)
    return {"backup_root": str(backup_root), "manifest_path": str(manifest_path)}


def _artifact_entry(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "sha256": _sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _false_side_effects() -> dict[str, bool]:
    return {
        "network_fetch_performed": False,
        "provider_or_model_call_performed": False,
        "runtime_or_adapter_executed": False,
        "browser_or_cloud_state_read": False,
        "mcp_server_started": False,
        "target_file_written": False,
        "memory_promotion_performed": False,
        "raw_source_copied": False,
        "public_publication_performed": False,
        "stable_protocol_claim": False,
    }


def _validate_scan_path(scan_path: Path, *, max_file_bytes: int) -> None:
    if max_file_bytes < 1:
        raise ValueError("max_file_bytes must be greater than zero")
    if not scan_path.exists():
        raise FileNotFoundError(f"Context Health Doctor scan path does not exist: {scan_path}")
    if not scan_path.is_file() and not scan_path.is_dir():
        raise ValueError(f"Context Health Doctor scan path must be a file or directory: {scan_path}")


def _storage_base_for_scan_path(scan_path: Path) -> Path:
    return scan_path if scan_path.is_dir() else scan_path.parent


def _resolve_output_root(storage_base: Path, output_root: Path | None) -> Path:
    if output_root is None:
        return (storage_base / ".ctxvault" / "health").resolve()
    if output_root.is_absolute():
        return output_root.resolve()
    return (storage_base / output_root).resolve()


def _write_result_rollback(
    *,
    report: dict[str, Any],
    run_root: Path,
    reports_json_path: Path,
    reports_markdown_path: Path,
    evidence_manifest_path: Path,
    receipt_copy_path: Path,
    backup_manifest_path: Path,
    index_path: Path,
) -> dict[str, Any]:
    backup_run_root = backup_manifest_path.parent
    return {
        "rollback_ref": report["rollback"]["rollback_ref"],
        "delete_paths": [
            str(run_root),
            str(reports_json_path),
            str(reports_markdown_path),
            str(evidence_manifest_path),
            str(receipt_copy_path),
            str(backup_run_root),
        ],
        "index_path": str(index_path),
        "index_policy": "Keep the append-only index as audit history or supersede it with a later run; no source file rollback is required.",
        "target_files_written": False,
        "raw_source_copied": False,
    }


def _report_id(scan_path: Path, findings: list[dict[str, Any]]) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    digest = hashlib.sha256(
        json.dumps(
            {
                "scan_path": str(scan_path),
                "findings": [
                    {
                        "source_ref": finding["source_ref"],
                        "finding_type": finding["finding_type"],
                        "reason": finding["reason"],
                    }
                    for finding in findings
                ],
            },
            ensure_ascii=True,
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:10]
    return f"context_health_{timestamp}_{digest}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
        return True
    except ValueError:
        return False


def _md_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
