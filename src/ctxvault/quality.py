from __future__ import annotations

import hashlib
import re
from typing import Any, Iterable


CONTEXT_QUALITY_RECEIPT_SCHEMA_ID = "ctxvault.context-quality-receipt/v1"
CONTEXT_DENSITY_SCORECARD_SCHEMA_ID = "ctxvault.context-density-scorecard/v1"
RETRIEVAL_GAIN_RECEIPT_SCHEMA_ID = "ctxvault.retrieval-gain-receipt/v1"
SEARCH_DECISION_TRACE_SCHEMA_ID = "ctxvault.search-decision-trace/v1"
SOURCE_CONFLICT_SCORECARD_SCHEMA_ID = "ctxvault.source-conflict-scorecard/v1"
SOURCE_RETENTION_SCORECARD_SCHEMA_ID = "ctxvault.source-retention-scorecard/v1"
PROMPT_PATCH_DENSITY_CHECK_SCHEMA_ID = "ctxvault.prompt-patch-density-check/v1"

_STALE_OR_MISLEADING_RE = re.compile(
    r"\b(stale|outdated|deprecated|obsolete|superseded|misleading|incorrect)\b",
    re.IGNORECASE,
)
_CONFLICT_RE = re.compile(r"\b(conflict|conflicting|contradict|contradiction|contradicts)\b", re.IGNORECASE)
_BOILERPLATE_RE = re.compile(r"\b(todo|lorem ipsum|placeholder|deprecated|obsolete|tbd)\b", re.IGNORECASE)
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def build_context_quality_receipt(
    *,
    query: str,
    target_kind: str,
    candidate_items: list[dict[str, Any]],
    selected_items: list[dict[str, Any]],
    token_budget: int,
    required_slice_refs: list[str] | None = None,
    reviewer_override_notes: list[str] | None = None,
) -> dict[str, Any]:
    required_refs = _unique(required_slice_refs or [])
    omitted = _omitted_refs_with_reason(candidate_items)
    density = build_context_density_scorecard(
        candidate_items=candidate_items,
        selected_items=selected_items,
        token_budget=token_budget,
        required_slice_refs=required_refs,
        omitted_refs_with_reason=omitted,
        reviewer_override_notes=reviewer_override_notes,
    )
    conflict = build_source_conflict_scorecard(
        candidate_items=candidate_items,
        selected_items=selected_items,
        omitted_refs_with_reason=omitted,
    )
    trace = build_search_decision_trace(
        query=query,
        target_kind=target_kind,
        candidate_items=candidate_items,
        selected_items=selected_items,
        token_budget=token_budget,
        omitted_refs_with_reason=omitted,
    )
    gain = build_retrieval_gain_receipt(
        candidate_items=candidate_items,
        selected_items=selected_items,
        required_slice_refs=required_refs,
        omitted_refs_with_reason=omitted,
        conflict_scorecard=conflict,
        search_stop_reason=str(trace["stop_reason"]),
    )

    return {
        "schema_id": CONTEXT_QUALITY_RECEIPT_SCHEMA_ID,
        "contract_state": "experimental",
        "query": query,
        "target_kind": target_kind,
        "input_token_estimate": density["input_token_estimate"],
        "projected_token_estimate": density["projected_token_estimate"],
        "required_refs_retained": density["required_refs_retained"],
        "omitted_refs_with_reason": omitted,
        "budget_pressure": density["budget_pressure"],
        "compression_ratio": density["compression_ratio"],
        "reviewer_override_notes": list(reviewer_override_notes or []),
        "retrieval_gain_proxy": gain["retrieval_gain_proxy"],
        "conflict_delta": gain["conflict_delta"],
        "duplicate_context_ratio": gain["duplicate_context_ratio"],
        "new_required_refs_resolved": gain["new_required_refs_resolved"],
        "misleading_refs_rejected": gain["misleading_refs_rejected"],
        "search_stop_reason": trace["stop_reason"],
        "density_scorecard": density,
        "retrieval_gain_receipt": gain,
        "search_decision_trace": trace,
        "source_conflict_scorecard": conflict,
    }


def build_context_density_scorecard(
    *,
    candidate_items: list[dict[str, Any]],
    selected_items: list[dict[str, Any]],
    token_budget: int,
    required_slice_refs: list[str] | None = None,
    omitted_refs_with_reason: list[dict[str, Any]] | None = None,
    reviewer_override_notes: list[str] | None = None,
) -> dict[str, Any]:
    required_refs = _unique(required_slice_refs or [])
    selected_refs = _slice_refs(selected_items)
    candidate_refs = _slice_refs(candidate_items)
    omitted = list(omitted_refs_with_reason or _omitted_refs_with_reason(candidate_items))
    input_tokens = sum(_token_estimate(item) for item in candidate_items)
    projected_tokens = sum(_token_estimate(item) for item in selected_items)
    budget = max(0, int(token_budget))
    required_missing = [ref for ref in required_refs if ref not in selected_refs]
    blocked_refs = [
        str(item["slice_ref"])
        for item in candidate_items
        if str(item.get("privacy_class") or "") == "withheld"
    ]

    return {
        "schema_id": CONTEXT_DENSITY_SCORECARD_SCHEMA_ID,
        "contract_state": "experimental",
        "status": _density_status(projected_tokens=projected_tokens, token_budget=budget, selected_refs=selected_refs),
        "input_token_estimate": input_tokens,
        "selected_token_estimate": projected_tokens,
        "projected_token_estimate": projected_tokens,
        "token_budget": budget,
        "budget_pressure": _ratio(projected_tokens, budget) if budget else (1.0 if projected_tokens else 0.0),
        "compression_ratio": _ratio(projected_tokens, input_tokens),
        "candidate_slice_refs": candidate_refs,
        "selected_slice_refs": selected_refs,
        "omitted_refs": [str(item["slice_ref"]) for item in omitted],
        "omitted_refs_with_reason": omitted,
        "blocked_refs": blocked_refs,
        "required_slice_refs": required_refs,
        "required_refs_retained": not required_missing,
        "missing_required_refs": required_missing,
        "source_diversity": {
            "candidate_source_count": len(_source_refs(candidate_items)),
            "selected_source_count": len(_source_refs(selected_items)),
            "selected_source_refs": _source_refs(selected_items),
        },
        "reviewer_override_notes": list(reviewer_override_notes or []),
    }


def build_retrieval_gain_receipt(
    *,
    candidate_items: list[dict[str, Any]],
    selected_items: list[dict[str, Any]],
    required_slice_refs: list[str] | None = None,
    omitted_refs_with_reason: list[dict[str, Any]] | None = None,
    conflict_scorecard: dict[str, Any] | None = None,
    search_stop_reason: str = "not_recorded",
) -> dict[str, Any]:
    required_refs = _unique(required_slice_refs or [])
    selected_refs = _slice_refs(selected_items)
    omitted = list(omitted_refs_with_reason or _omitted_refs_with_reason(candidate_items))
    duplicate_ratio = _duplicate_context_ratio(candidate_items)
    conflict = conflict_scorecard or build_source_conflict_scorecard(
        candidate_items=candidate_items,
        selected_items=selected_items,
        omitted_refs_with_reason=omitted,
    )
    misleading_rejected = [
        str(item["slice_ref"])
        for item in omitted
        if str(item.get("reason")) in {"stale_or_misleading_rejected", "conflict_rejected"}
    ]
    required_resolved = [ref for ref in required_refs if ref in selected_refs]
    selected_source_count = len(_source_refs(selected_items))
    candidate_source_count = len(_source_refs(candidate_items))
    stale_selected_penalty = len(conflict["selected_stale_refs"]) + len(conflict["selected_conflict_refs"])
    gain_proxy = (
        selected_source_count
        + len(required_resolved)
        + len(misleading_rejected)
        - duplicate_ratio
        - stale_selected_penalty
    )

    return {
        "schema_id": RETRIEVAL_GAIN_RECEIPT_SCHEMA_ID,
        "contract_state": "experimental",
        "retrieval_gain_proxy": round(float(gain_proxy), 4),
        "candidate_source_count": candidate_source_count,
        "selected_source_count": selected_source_count,
        "source_coverage_delta": selected_source_count,
        "required_refs_resolved": required_resolved,
        "new_required_refs_resolved": len(required_resolved),
        "conflict_delta": int(conflict["conflict_delta"]),
        "duplicate_context_ratio": duplicate_ratio,
        "stale_source_risk": {
            "candidate_stale_ref_count": len(conflict["stale_refs"]),
            "selected_stale_ref_count": len(conflict["selected_stale_refs"]),
        },
        "misleading_refs_rejected": misleading_rejected,
        "search_stop_reason": search_stop_reason,
        "reviewer_visible_reasons": _retrieval_gain_reasons(
            selected_source_count=selected_source_count,
            required_resolved=required_resolved,
            duplicate_ratio=duplicate_ratio,
            conflict=conflict,
            misleading_rejected=misleading_rejected,
        ),
    }


def build_search_decision_trace(
    *,
    query: str,
    target_kind: str,
    candidate_items: list[dict[str, Any]],
    selected_items: list[dict[str, Any]],
    token_budget: int,
    omitted_refs_with_reason: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selected_refs = set(_slice_refs(selected_items))
    omitted_by_ref = {
        str(item["slice_ref"]): str(item.get("reason") or "not_selected")
        for item in list(omitted_refs_with_reason or _omitted_refs_with_reason(candidate_items))
    }
    per_candidate = []
    for item in candidate_items:
        ref = str(item["slice_ref"])
        selected = ref in selected_refs
        per_candidate.append(
            {
                "slice_ref": ref,
                "source_ref": str(item.get("source_ref") or ""),
                "selected": selected,
                "rejected_reason": None if selected else omitted_by_ref.get(ref, "not_selected"),
                "score": float(item.get("score") or 0.0),
                "token_estimate": _token_estimate(item),
                "changed_final_packet": selected,
            }
        )
    projected_tokens = sum(_token_estimate(item) for item in selected_items)
    return {
        "schema_id": SEARCH_DECISION_TRACE_SCHEMA_ID,
        "contract_state": "experimental",
        "query": query,
        "target_kind": target_kind,
        "ranking_policy": "deterministic_bm25_v1",
        "candidate_slice_refs": _slice_refs(candidate_items),
        "selected_slice_refs": _slice_refs(selected_items),
        "rejected_slice_refs": [item["slice_ref"] for item in per_candidate if not bool(item["selected"])],
        "stop_reason": _search_stop_reason(candidate_items, selected_items, int(token_budget)),
        "continue_reason": None,
        "budget_impact": {
            "token_budget": max(0, int(token_budget)),
            "projected_token_estimate": projected_tokens,
            "budget_pressure": _ratio(projected_tokens, max(0, int(token_budget)))
            if int(token_budget) > 0
            else (1.0 if projected_tokens else 0.0),
        },
        "retrieval_changed_final_packet": bool(selected_items),
        "per_candidate": per_candidate,
    }


def build_source_conflict_scorecard(
    *,
    candidate_items: list[dict[str, Any]],
    selected_items: list[dict[str, Any]],
    omitted_refs_with_reason: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    selected_refs = set(_slice_refs(selected_items))
    stale_refs = [ref for ref, text in _item_texts(candidate_items) if _STALE_OR_MISLEADING_RE.search(text)]
    conflict_refs = [ref for ref, text in _item_texts(candidate_items) if _CONFLICT_RE.search(text)]
    selected_stale = [ref for ref in stale_refs if ref in selected_refs]
    selected_conflict = [ref for ref in conflict_refs if ref in selected_refs]
    omitted_by_ref = {
        str(item["slice_ref"]): str(item.get("reason") or "not_selected")
        for item in list(omitted_refs_with_reason or _omitted_refs_with_reason(candidate_items))
    }
    surfaced_conflicts = [ref for ref in conflict_refs if ref in selected_refs or ref in omitted_by_ref]
    return {
        "schema_id": SOURCE_CONFLICT_SCORECARD_SCHEMA_ID,
        "contract_state": "experimental",
        "status": "pass" if not selected_stale and not selected_conflict else "needs_review",
        "stale_refs": stale_refs,
        "conflict_refs": conflict_refs,
        "selected_stale_refs": selected_stale,
        "selected_conflict_refs": selected_conflict,
        "surfaced_conflict_refs": surfaced_conflicts,
        "misleading_refs_rejected": _unique(
            ref
            for ref in [*stale_refs, *conflict_refs]
            if ref in omitted_by_ref and ref not in selected_refs
        ),
        "conflict_delta": -(len(selected_stale) + len(selected_conflict)),
    }


def build_source_retention_scorecard(
    *,
    scenarios: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = []
    min_recall = 1.0
    forbidden_hit_count = 0
    for scenario in scenarios:
        expected = _unique(scenario.get("expected_source_refs") or [])
        selected = _unique(scenario.get("selected_source_refs") or [])
        forbidden = _unique(scenario.get("forbidden_source_refs") or [])
        matched = [ref for ref in expected if ref in selected]
        forbidden_matched = [ref for ref in forbidden if ref in selected]
        recall = len(matched) / len(expected) if expected else 1.0
        min_recall = min(min_recall, recall)
        forbidden_hit_count += len(forbidden_matched)
        normalized.append(
            {
                "id": str(scenario.get("id") or ""),
                "query": str(scenario.get("query") or ""),
                "expected_source_refs": expected,
                "selected_source_refs": selected,
                "matched_expected_source_refs": matched,
                "expected_source_recall": recall,
                "forbidden_source_refs": forbidden,
                "matched_forbidden_source_refs": forbidden_matched,
            }
        )
    status = "pass" if min_recall >= 1.0 and forbidden_hit_count == 0 else "fail"
    return {
        "schema_id": SOURCE_RETENTION_SCORECARD_SCHEMA_ID,
        "contract_state": "experimental",
        "status": status,
        "thresholds": {
            "min_expected_source_recall": 1.0,
            "max_forbidden_hit_count": 0,
        },
        "summary": {
            "scenario_count": len(normalized),
            "min_expected_source_recall": min_recall,
            "forbidden_hit_count": forbidden_hit_count,
        },
        "scenarios": normalized,
    }


def build_prompt_patch_density_check(
    *,
    patch_ref: str,
    prompt_ref: str,
    prompt_payload: dict[str, Any],
    prompt_preview: dict[str, Any],
    changed_fields: list[str],
) -> dict[str, Any]:
    before_instruction = str(prompt_payload.get("instruction") or "")
    after_instruction = str(prompt_preview.get("instruction") or "")
    duplicate_rules = _duplicate_prompt_lines(after_instruction)
    conflicting_instructions = _conflicting_prompt_rules(after_instruction)
    stale_boilerplate = sorted(set(match.group(0).lower() for match in _BOILERPLATE_RE.finditer(after_instruction)))
    before_chars = len(before_instruction)
    after_chars = len(after_instruction)
    added_chars = max(0, after_chars - before_chars)
    bloat_ratio = _ratio(added_chars, max(1, before_chars))
    findings = {
        "duplicate_rule_count": len(duplicate_rules),
        "stale_boilerplate_count": len(stale_boilerplate),
        "conflicting_instruction_count": len(conflicting_instructions),
        "bloat_ratio": bloat_ratio,
    }
    status = "pass"
    if duplicate_rules or conflicting_instructions or stale_boilerplate or bloat_ratio > 0.35:
        status = "needs_review"
    return {
        "schema_id": PROMPT_PATCH_DENSITY_CHECK_SCHEMA_ID,
        "contract_state": "experimental",
        "status": status,
        "patch_ref": patch_ref,
        "prompt_ref": prompt_ref,
        "changed_fields": list(changed_fields),
        "instruction_chars_before": before_chars,
        "instruction_chars_after": after_chars,
        "added_instruction_chars": added_chars,
        "bloat_ratio": bloat_ratio,
        "duplicate_rules": duplicate_rules,
        "stale_boilerplate": stale_boilerplate,
        "conflicting_instructions": conflicting_instructions,
        "findings": findings,
        "candidate_action": "review_candidate_only",
        "mutates_active_prompt": False,
    }


def _omitted_refs_with_reason(candidate_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    omitted: list[dict[str, Any]] = []
    for item in candidate_items:
        if bool(item.get("is_selected")):
            continue
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        text = _item_text(item)
        if str(item.get("privacy_class") or "") == "withheld":
            reason = "blocked_by_privacy"
        elif _CONFLICT_RE.search(text):
            reason = "conflict_rejected"
        elif _STALE_OR_MISLEADING_RE.search(text):
            reason = "stale_or_misleading_rejected"
        elif str(item.get("preference_action") or "") in {"hide", "archive"}:
            reason = f"preference_{item['preference_action']}"
        else:
            reason = "not_selected"
        omitted.append(
            {
                "slice_ref": str(item["slice_ref"]),
                "source_ref": str(item.get("source_ref") or payload.get("source_ref") or ""),
                "reason": reason,
                "token_estimate": _token_estimate(item),
            }
        )
    return omitted


def _density_status(*, projected_tokens: int, token_budget: int, selected_refs: list[str]) -> str:
    if not selected_refs:
        return "empty"
    if token_budget >= 0 and projected_tokens > token_budget:
        return "over_budget"
    return "pass"


def _search_stop_reason(candidate_items: list[dict[str, Any]], selected_items: list[dict[str, Any]], token_budget: int) -> str:
    if not candidate_items:
        return "no_candidates"
    if not selected_items:
        return "no_selected_candidates"
    projected_tokens = sum(_token_estimate(item) for item in selected_items)
    if token_budget >= 0 and projected_tokens >= token_budget:
        return "budget_exhausted"
    if len(selected_items) < len(candidate_items):
        return "selected_packet_sufficient"
    return "candidate_set_exhausted"


def _retrieval_gain_reasons(
    *,
    selected_source_count: int,
    required_resolved: list[str],
    duplicate_ratio: float,
    conflict: dict[str, Any],
    misleading_rejected: list[str],
) -> list[str]:
    reasons = [f"selected_source_count={selected_source_count}"]
    if required_resolved:
        reasons.append(f"required_refs_resolved={len(required_resolved)}")
    if duplicate_ratio:
        reasons.append(f"duplicate_context_ratio={duplicate_ratio}")
    if conflict.get("selected_stale_refs") or conflict.get("selected_conflict_refs"):
        reasons.append("selected_stale_or_conflicting_refs_need_review")
    if misleading_rejected:
        reasons.append(f"misleading_refs_rejected={len(misleading_rejected)}")
    return reasons


def _duplicate_context_ratio(items: list[dict[str, Any]]) -> float:
    hashes = [
        str((item.get("payload") or {}).get("content_sha256") or _stable_item_hash(item))
        for item in items
    ]
    if not hashes:
        return 0.0
    return _ratio(len(hashes) - len(set(hashes)), len(hashes))


def _duplicate_prompt_lines(text: str) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for line in text.splitlines():
        normalized = _normalize_prompt_line(line)
        if not normalized:
            continue
        if normalized in seen:
            duplicates.add(normalized)
        seen.add(normalized)
    return sorted(duplicates)


def _conflicting_prompt_rules(text: str) -> list[dict[str, str]]:
    rules: dict[str, set[str]] = {}
    for line in text.splitlines():
        normalized = _normalize_prompt_line(line)
        if not normalized:
            continue
        polarity = None
        if normalized.startswith(("do not ", "dont ", "never ")):
            polarity = "negative"
        elif normalized.startswith(("must ", "always ", "do ")):
            polarity = "positive"
        if polarity is None:
            continue
        key = re.sub(r"^(do not|dont|never|must|always|do)\s+", "", normalized).strip()
        if not key:
            continue
        rules.setdefault(key, set()).add(polarity)
    return [
        {"rule": rule, "conflict": "positive_and_negative"}
        for rule, polarities in sorted(rules.items())
        if {"positive", "negative"}.issubset(polarities)
    ]


def _normalize_prompt_line(line: str) -> str:
    text = line.strip().lower()
    text = re.sub(r"^[-*0-9.\s]+", "", text)
    text = " ".join(_WORD_RE.findall(text))
    return text if len(text) >= 12 else ""


def _item_text(item: dict[str, Any]) -> str:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    return " ".join(
        str(value or "")
        for value in [
            item.get("title"),
            item.get("source_ref"),
            payload.get("title"),
            payload.get("heading_path"),
            payload.get("redacted_preview"),
        ]
    )


def _item_texts(items: list[dict[str, Any]]) -> Iterable[tuple[str, str]]:
    for item in items:
        yield str(item["slice_ref"]), _item_text(item)


def _slice_refs(items: list[dict[str, Any]]) -> list[str]:
    return _unique(str(item.get("slice_ref") or "") for item in items)


def _source_refs(items: list[dict[str, Any]]) -> list[str]:
    return _unique(str(item.get("source_ref") or "") for item in items)


def _token_estimate(item: dict[str, Any]) -> int:
    return max(0, int(item.get("token_estimate") or 0))


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _stable_item_hash(item: dict[str, Any]) -> str:
    return hashlib.sha256(_item_text(item).encode("utf-8")).hexdigest()


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered
