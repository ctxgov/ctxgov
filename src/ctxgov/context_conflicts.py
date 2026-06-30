from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .change_analysis import DEFAULT_MAX_FILE_BYTES, SurfaceFile, discover_surfaces, parse_surface


CONTEXT_CONFLICT_MAP_SCHEMA_ID = "ctxgov.context-conflict-map/v0"

HIGH_AUTHORITY_SURFACE_KINDS = frozenset(
    {
        "agent_instruction",
        "claude_instruction",
        "gemini_instruction",
        "github_copilot_instruction",
        "cursor_rule",
        "cline_rule",
        "mcp_config",
    }
)


@dataclass(frozen=True)
class _PolicySignals:
    source_ref: str
    surface_kind: str
    source_tier: str
    sha256: str
    size_bytes: int
    authority: dict[str, Any]
    capabilities: list[str]
    scope: dict[str, Any]
    sensitivity: str
    network_denied: bool
    network_allowed: bool
    write_denied: bool
    write_allowed: bool
    execute_denied: bool
    execute_allowed: bool
    publish_denied: bool
    publish_allowed: bool
    approval_required: bool
    approval_bypassed: bool
    precedence_declared: bool
    mcp_capability_exposed: bool
    mcp_mentioned: bool


def build_context_conflict_map(
    root: Path,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    checked_at: str | None = None,
) -> dict[str, Any]:
    resolved = root.resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"repo path does not exist or is not a directory: {resolved}")

    surfaces = discover_surfaces(resolved, max_file_bytes=max_file_bytes)
    signals = [_policy_signals(surface) for surface in surfaces]
    findings = _build_findings(signals)
    _attach_finding_tiers(findings, signals)
    for index, finding in enumerate(findings, start=1):
        finding["finding_id"] = f"ccm_{index:04d}_{finding['finding_type']}"

    surface_rows = [_surface_row(signal) for signal in signals]
    precedence = _precedence_summary(signals, findings)
    return {
        "schema_id": CONTEXT_CONFLICT_MAP_SCHEMA_ID,
        "object_type": "ContextConflictMap",
        "version": "v0",
        "created_at": checked_at or _utc_now(),
        "mode": "read_only_declared_context_conflict_map",
        "analysis_boundary": {
            "declared_instruction_conflicts_only": True,
            "runtime_precedence_truth_claimed": False,
            "model_behavior_claimed": False,
            "security_or_safety_review_claimed": False,
        },
        "source_capture": {
            "local_path_recorded": False,
            "raw_source_copied": False,
            "surface_manifest_digest": _digest(_surface_manifest_rows(surfaces)),
        },
        "surface_summary": _surface_summary(signals),
        "precedence": precedence,
        "summary": _summary(findings, precedence),
        "findings": findings,
        "surfaces": surface_rows,
        "claim_boundary": _claim_boundary(),
        "side_effect_boundary": _side_effect_boundary(),
    }


def render_context_conflict_summary(report: dict[str, Any]) -> str:
    lines = [
        "# Context Conflict Map",
        "",
        "This report records declared instruction conflicts across local agent-facing",
        "context surfaces. It is not a benchmark, security review, runtime",
        "precedence result, provider compatibility result, endorsement, or",
        "production-readiness claim.",
        "",
        f"- Report schema: `{report['schema_id']}`",
        f"- Checked at: `{report['created_at']}`",
        f"- Surfaces: `{report['surface_summary']['surface_count']}`",
        f"- Findings: `{report['summary']['finding_count']}`",
        f"- Precedence declared: `{str(report['precedence']['declared']).lower()}`",
        "- Runtime boundary: no provider/model calls, no API calls, no network calls, no target writes.",
        "- Evidence tiers: instruction/config signals are separated from README/docs signals.",
        "",
        "## Methodology",
        "",
        "The analyzer reads local files that match agent-context surface patterns,",
        "classifies each source into `instruction_or_config`, `readme_or_docs`, or",
        "`other_context`, and reports declared policy collisions across those tiers.",
        "Findings that involve README/docs are intentionally caveated because docs",
        "can describe examples, usage, or history rather than active agent policy.",
        "",
        "## Findings",
        "",
    ]
    if not report["findings"]:
        lines.append("No declared instruction conflicts were detected by the local heuristics.")
    for finding in report["findings"]:
        lines.extend(
            [
                f"### {finding['finding_id']}",
                "",
                f"- Type: `{finding['finding_type']}`",
                f"- Severity: `{finding['severity']}`",
                f"- Evidence tier: `{finding['evidence_tier']}`",
                f"- Sources: {_compact_list(finding['source_refs'])}",
                f"- Reason: {finding['reason']}",
                f"- Next check: {finding['recommended_next_check']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            "The checked output omits local filesystem paths and raw source content.",
            "Findings mean review-needed declared conflicts, not proof of actual agent runtime behavior.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _policy_signals(surface: SurfaceFile) -> _PolicySignals:
    parsed = parse_surface(surface)
    text = surface.text or ""
    lowered = text.lower()
    network_denied = _network_denied(lowered)
    write_denied = _write_denied(lowered)
    execute_denied = _execute_denied(lowered)
    publish_denied = _publish_denied(lowered)
    mcp_capability_exposed = _mcp_capability_exposed(surface, lowered)
    capabilities = list(parsed.capabilities)
    return _PolicySignals(
        source_ref=surface.source_ref,
        surface_kind=surface.surface_kind,
        source_tier=_source_tier(surface),
        sha256=surface.sha256,
        size_bytes=surface.size_bytes,
        authority=dict(parsed.authority),
        capabilities=capabilities,
        scope=dict(parsed.scope),
        sensitivity=parsed.sensitivity,
        network_denied=network_denied,
        network_allowed=not network_denied and (_network_allowed(lowered) or "network" in capabilities or mcp_capability_exposed),
        write_denied=write_denied,
        write_allowed=not write_denied and (_write_allowed(lowered) or bool({"write", "delete", "deploy", "publish"} & set(capabilities))),
        execute_denied=execute_denied,
        execute_allowed=not execute_denied and (_execute_allowed(lowered) or "execute" in capabilities),
        publish_denied=publish_denied,
        publish_allowed=not publish_denied and (_publish_allowed(lowered) or "publish" in capabilities),
        approval_required=bool(parsed.authority.get("has_approval_gate")) or _approval_required(lowered),
        approval_bypassed=_approval_bypassed(lowered),
        precedence_declared=_precedence_declared(lowered),
        mcp_capability_exposed=mcp_capability_exposed,
        mcp_mentioned="mcp" in lowered or "model context protocol" in lowered,
    )


def _build_findings(signals: list[_PolicySignals]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(
        [
            _binary_conflict(
                signals,
                finding_type="network_conflict",
                severity="high",
                denied_attr="network_denied",
                allowed_attr="network_allowed",
                reason="At least one surface denies network access while another declares or exposes network capability.",
                recommended_next_check="Declare one network boundary and state which instruction source has precedence.",
            ),
            _binary_conflict(
                signals,
                finding_type="target_write_conflict",
                severity="high",
                denied_attr="write_denied",
                allowed_attr="write_allowed",
                reason="At least one surface denies repository writes while another declares write-like capability.",
                recommended_next_check="Choose one repository write policy and link lower-priority instruction files to it.",
            ),
            _binary_conflict(
                signals,
                finding_type="execution_conflict",
                severity="high",
                denied_attr="execute_denied",
                allowed_attr="execute_allowed",
                reason="At least one surface denies command execution while another declares execution capability.",
                recommended_next_check="Resolve shell/tool execution policy before relying on the combined context.",
            ),
            _binary_conflict(
                signals,
                finding_type="publish_conflict",
                severity="high",
                denied_attr="publish_denied",
                allowed_attr="publish_allowed",
                reason="At least one surface denies publication while another declares publish or release capability.",
                recommended_next_check="Keep publication authority in one canonical policy and require explicit review for exceptions.",
            ),
            _binary_conflict(
                signals,
                finding_type="approval_conflict",
                severity="high",
                denied_attr="approval_required",
                allowed_attr="approval_bypassed",
                reason="Approval requirements conflict with an autonomous or no-approval instruction.",
                recommended_next_check="State whether approval is required and which file wins when another file bypasses it.",
            ),
        ]
    )
    findings = [finding for finding in findings if finding]
    scope = _scope_conflict(signals)
    if scope:
        findings.append(scope)
    sensitivity = _sensitivity_boundary_conflict(signals)
    if sensitivity:
        findings.append(sensitivity)
    precedence = _precedence_missing(signals)
    if precedence:
        findings.append(precedence)
    orphan = _mcp_capability_orphan(signals)
    if orphan:
        findings.append(orphan)
    return findings


def _binary_conflict(
    signals: list[_PolicySignals],
    *,
    finding_type: str,
    severity: str,
    denied_attr: str,
    allowed_attr: str,
    reason: str,
    recommended_next_check: str,
) -> dict[str, Any]:
    denied_refs = sorted(signal.source_ref for signal in signals if bool(getattr(signal, denied_attr)))
    allowed_refs = sorted(signal.source_ref for signal in signals if bool(getattr(signal, allowed_attr)))
    if not denied_refs or not allowed_refs:
        return {}
    return _finding(
        finding_type=finding_type,
        severity=severity,
        source_refs=sorted(set(denied_refs) | set(allowed_refs)),
        reason=reason,
        recommended_next_check=recommended_next_check,
        evidence={"denied_refs": denied_refs, "allowed_refs": allowed_refs},
    )


def _scope_conflict(signals: list[_PolicySignals]) -> dict[str, Any]:
    scoped = {signal.source_ref: str(signal.scope.get("scope_kind", "project")) for signal in signals}
    scope_values = sorted(set(scoped.values()))
    if len(scope_values) < 2:
        return {}
    high_refs = [signal.source_ref for signal in signals if signal.surface_kind in HIGH_AUTHORITY_SURFACE_KINDS]
    if len(high_refs) < 2:
        return {}
    return _finding(
        finding_type="scope_conflict",
        severity="medium",
        source_refs=sorted(high_refs),
        reason=f"High-authority surfaces declare multiple scope levels: {', '.join(scope_values)}.",
        recommended_next_check="State whether project, workspace, user, or system scope takes precedence for agent instructions.",
        evidence={"scope_by_ref": scoped},
    )


def _sensitivity_boundary_conflict(signals: list[_PolicySignals]) -> dict[str, Any]:
    public_refs = sorted(signal.source_ref for signal in signals if signal.sensitivity == "public")
    restricted_refs = sorted(signal.source_ref for signal in signals if signal.sensitivity in {"sensitive", "restricted"})
    if not public_refs or not restricted_refs:
        return {}
    return _finding(
        finding_type="sensitivity_boundary_conflict",
        severity="medium",
        source_refs=sorted(set(public_refs) | set(restricted_refs)),
        reason="Public and sensitive/restricted instruction surfaces are both present without a declared boundary in the detected surfaces.",
        recommended_next_check="Declare which sensitive instruction sources may influence public-facing agent behavior.",
        evidence={"public_refs": public_refs, "sensitive_or_restricted_refs": restricted_refs},
    )


def _precedence_missing(signals: list[_PolicySignals]) -> dict[str, Any]:
    high_refs = sorted(signal.source_ref for signal in signals if signal.surface_kind in HIGH_AUTHORITY_SURFACE_KINDS)
    high_kinds = sorted({signal.surface_kind for signal in signals if signal.source_ref in high_refs})
    if len(high_refs) < 2 or any(signal.precedence_declared for signal in signals):
        return {}
    return _finding(
        finding_type="precedence_missing",
        severity="medium",
        source_refs=high_refs,
        reason="Multiple high-authority agent context surfaces were found, but no detected surface declares which source wins.",
        recommended_next_check="Add an explicit precedence statement, for example: AGENTS.md wins over CLAUDE.md and MCP config.",
        evidence={"high_authority_surface_kinds": high_kinds},
    )


def _mcp_capability_orphan(signals: list[_PolicySignals]) -> dict[str, Any]:
    mcp_refs = sorted(signal.source_ref for signal in signals if signal.mcp_capability_exposed)
    if not mcp_refs:
        return {}
    non_mcp_mentions = [signal.source_ref for signal in signals if signal.surface_kind != "mcp_config" and signal.mcp_mentioned]
    if non_mcp_mentions:
        return {}
    return _finding(
        finding_type="mcp_capability_orphan",
        severity="low",
        source_refs=mcp_refs,
        reason="MCP configuration exposes capabilities, but no non-MCP instruction surface mentions the MCP boundary.",
        recommended_next_check="Reference MCP capability policy from the top-level agent instruction file.",
        evidence={"mcp_refs": mcp_refs},
    )


def _finding(
    *,
    finding_type: str,
    severity: str,
    source_refs: list[str],
    reason: str,
    recommended_next_check: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "finding_id": "",
        "finding_type": finding_type,
        "severity": severity,
        "source_refs": source_refs,
        "source_tiers": {},
        "evidence_tier": "unclassified",
        "reason": reason,
        "recommended_next_check": recommended_next_check,
        "evidence": evidence,
    }


def _surface_row(signal: _PolicySignals) -> dict[str, Any]:
    return {
        "source_ref": signal.source_ref,
        "surface_kind": signal.surface_kind,
        "source_tier": signal.source_tier,
        "sha256": signal.sha256,
        "authority": signal.authority,
        "capabilities": signal.capabilities,
        "scope": signal.scope,
        "sensitivity": signal.sensitivity,
        "policy_signals": {
            "network_denied": signal.network_denied,
            "network_allowed": signal.network_allowed,
            "write_denied": signal.write_denied,
            "write_allowed": signal.write_allowed,
            "execute_denied": signal.execute_denied,
            "execute_allowed": signal.execute_allowed,
            "publish_denied": signal.publish_denied,
            "publish_allowed": signal.publish_allowed,
            "approval_required": signal.approval_required,
            "approval_bypassed": signal.approval_bypassed,
            "precedence_declared": signal.precedence_declared,
            "mcp_capability_exposed": signal.mcp_capability_exposed,
        },
    }


def _surface_summary(signals: list[_PolicySignals]) -> dict[str, Any]:
    kinds = Counter(signal.surface_kind for signal in signals)
    source_tiers = Counter(signal.source_tier for signal in signals)
    scopes = Counter(str(signal.scope.get("scope_kind", "project")) for signal in signals)
    sensitivities = Counter(signal.sensitivity for signal in signals)
    capabilities = sorted({capability for signal in signals for capability in signal.capabilities})
    return {
        "surface_count": len(signals),
        "surface_kinds": dict(sorted(kinds.items())),
        "source_tier_counts": dict(sorted(source_tiers.items())),
        "high_authority_surface_count": sum(1 for signal in signals if signal.surface_kind in HIGH_AUTHORITY_SURFACE_KINDS),
        "capabilities": capabilities,
        "scope_counts": dict(sorted(scopes.items())),
        "sensitivity_counts": dict(sorted(sensitivities.items())),
    }


def _precedence_summary(signals: list[_PolicySignals], findings: list[dict[str, Any]]) -> dict[str, Any]:
    declaration_refs = sorted(signal.source_ref for signal in signals if signal.precedence_declared)
    high_refs = sorted(signal.source_ref for signal in signals if signal.surface_kind in HIGH_AUTHORITY_SURFACE_KINDS)
    return {
        "declared": bool(declaration_refs),
        "declaration_refs": declaration_refs,
        "high_authority_surface_refs": high_refs,
        "high_authority_surface_kinds": sorted({signal.surface_kind for signal in signals if signal.source_ref in high_refs}),
        "unresolved_decision_count": sum(1 for finding in findings if finding.get("finding_type") == "precedence_missing"),
    }


def _summary(findings: list[dict[str, Any]], precedence: dict[str, Any]) -> dict[str, Any]:
    severities = Counter(str(finding["severity"]) for finding in findings)
    finding_types = Counter(str(finding["finding_type"]) for finding in findings)
    evidence_tiers = Counter(str(finding.get("evidence_tier", "unclassified")) for finding in findings)
    return {
        "finding_count": len(findings),
        "severity_counts": dict(sorted(severities.items())),
        "finding_type_counts": dict(sorted(finding_types.items())),
        "evidence_tier_counts": dict(sorted(evidence_tiers.items())),
        "unresolved_precedence_decision_count": int(precedence["unresolved_decision_count"]),
    }


def _attach_finding_tiers(findings: list[dict[str, Any]], signals: list[_PolicySignals]) -> None:
    by_ref = {signal.source_ref: signal for signal in signals}
    for finding in findings:
        tier_counts = Counter(
            by_ref[source_ref].source_tier if source_ref in by_ref else "other_context"
            for source_ref in finding.get("source_refs", [])
        )
        finding["source_tiers"] = dict(sorted(tier_counts.items()))
        finding["evidence_tier"] = _evidence_tier(set(tier_counts))


def _evidence_tier(source_tiers: set[str]) -> str:
    if not source_tiers:
        return "unclassified"
    if source_tiers <= {"instruction_or_config"}:
        return "instruction_config_only"
    if source_tiers <= {"readme_or_docs"}:
        return "readme_docs_only"
    if "instruction_or_config" in source_tiers and "readme_or_docs" in source_tiers:
        return "mixed_instruction_config_and_readme_docs"
    if "readme_or_docs" in source_tiers:
        return "mixed_with_readme_docs"
    return "other_context_only"


def _surface_manifest_rows(surfaces: list[SurfaceFile]) -> list[dict[str, Any]]:
    return [
        {
            "source_ref": surface.source_ref,
            "surface_kind": surface.surface_kind,
            "source_tier": _source_tier(surface),
            "sha256": surface.sha256,
            "size_bytes": surface.size_bytes,
        }
        for surface in surfaces
    ]


def _source_tier(surface: SurfaceFile) -> str:
    if surface.surface_kind in HIGH_AUTHORITY_SURFACE_KINDS:
        return "instruction_or_config"
    normalized_ref = surface.source_ref.lower()
    if surface.surface_kind == "readme" or "/docs/" in normalized_ref or normalized_ref.startswith("file://docs/"):
        return "readme_or_docs"
    return "other_context"


def _network_denied(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(no|never|do not|don't|must not|without)\b.{0,50}\b(network|internet|web|http|api|external)\b",
            r"\b(network|internet|web|http|api|external)\b.{0,50}\b(disabled|forbidden|blocked|denied)\b",
        ],
    )


def _network_allowed(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(network|internet|web|http|api|external)\b.{0,60}\b(allowed|enabled|approved|permitted|available)\b",
            r"\b(may|can|must|use)\b.{0,40}\b(network|internet|web|http|api|external)\b",
        ],
    )


def _write_denied(text: str) -> bool:
    return "read-only" in text or "read only" in text or _matches_any(
        text,
        [
            r"\b(no|never|do not|don't|must not|without)\b.{0,60}\b(write|modify|edit|change|delete|commit|push)\b",
            r"\b(write|modify|edit|change|delete|commit|push)\b.{0,60}\b(forbidden|blocked|denied|disabled)\b",
        ],
    )


def _write_allowed(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(write|modify|edit|change|delete|commit|push)\b.{0,60}\b(allowed|enabled|approved|permitted|available)\b",
            r"\b(may|can|must)\b.{0,40}\b(write|modify|edit|change|delete|commit|push)\b",
        ],
    )


def _execute_denied(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(no|never|do not|don't|must not|without)\b.{0,50}\b(execute|run|shell|command)\b",
            r"\b(execute|run|shell|command)\b.{0,50}\b(forbidden|blocked|denied|disabled)\b",
        ],
    )


def _execute_allowed(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(execute|run|shell|command)\b.{0,50}\b(allowed|enabled|approved|permitted|available)\b",
            r"\b(may|can|must)\b.{0,40}\b(execute|run|shell|command)\b",
        ],
    )


def _publish_denied(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(no|never|do not|don't|must not|without)\b.{0,50}\b(publish|release|post|upload|announce)\b",
            r"\b(publish|release|post|upload|announce)\b.{0,50}\b(forbidden|blocked|denied|disabled)\b",
        ],
    )


def _publish_allowed(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(publish|release|post|upload|announce)\b.{0,50}\b(allowed|enabled|approved|permitted|available)\b",
            r"\b(may|can|must)\b.{0,40}\b(publish|release|post|upload|announce)\b",
        ],
    )


def _approval_required(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(approval|required review|review required|human review|ask first|owner approval)\b",
            r"\b(requires|required|must have)\b.{0,40}\b(approval|review)\b",
        ],
    )


def _approval_bypassed(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(without|no)\b.{0,30}\b(approval|review|human review)\b",
            r"\b(autonomous|autonomously)\b.{0,50}\b(write|edit|change|execute|publish|act)\b",
            r"\b(does not|do not|don't)\b.{0,30}\b(require|need)\b.{0,30}\b(approval|review)\b",
        ],
    )


def _precedence_declared(text: str) -> bool:
    return _matches_any(
        text,
        [
            r"\b(precedence|priority|higher priority|order of authority|instruction order)\b",
            r"\b(wins|takes precedence|source of truth|canonical instruction)\b",
            r"\b(overrides|override)\b.{0,40}\b(agents\.md|claude\.md|mcp|readme|instruction)\b",
        ],
    )


def _mcp_capability_exposed(surface: SurfaceFile, text: str) -> bool:
    if surface.surface_kind != "mcp_config":
        return False
    if _matches_any(text, [r"\bmcpservers\b", r"\b(command|args|url|transport|server)\b", r"https?://"]):
        return True
    try:
        payload = json.loads(surface.text or "{}")
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and bool(payload)


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL) for pattern in patterns)


def _claim_boundary() -> dict[str, bool]:
    return {
        "public_benchmark_claim_created": False,
        "public_efficiency_claim_created": False,
        "public_adoption_claim_created": False,
        "security_or_safety_claim_created": False,
        "runtime_precedence_truth_claim_created": False,
        "provider_compatibility_claim_created": False,
        "production_readiness_claim_created": False,
        "stable_api_or_protocol_claim_created": False,
    }


def _side_effect_boundary() -> dict[str, bool]:
    return {
        "network_call_performed": False,
        "provider_model_call_performed": False,
        "api_call_performed": False,
        "runtime_or_adapter_executed": False,
        "target_repo_modified": False,
        "target_content_modified": False,
        "scheduler_or_daemon_started": False,
        "package_published": False,
        "public_write_performed": False,
    }


def _compact_list(items: list[str]) -> str:
    return ", ".join(f"`{item}`" for item in items) if items else "-"


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True).encode()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
