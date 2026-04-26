from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Iterable


EPISODE_KIND_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("debug", ("debug", "bug", "fix", "error", "failing", "failure", "traceback", "regression")),
    ("review", ("review", "audit", "inspect", "analyze", "analyse", "evaluate")),
    ("summarize", ("summary", "summarize", "summarise", "recap")),
    ("plan", ("plan", "roadmap", "strategy", "break down", "steps", "milestone")),
    ("design", ("design", "architecture", "architect", "schema", "system design")),
    ("execute", ("implement", "implementation", "write", "build", "ship", "wire", "code", "add", "change")),
    ("clarify", ("how", "what", "why", "explain", "understand", "clarify")),
)

PIVOT_MARKERS = (
    "new task",
    "another task",
    "switch to",
    "next step",
    "now implement",
    "now build",
    "now debug",
    "now review",
    "接下来",
    "现在实现",
    "现在调试",
    "换一个",
    "切换到",
)

CORRECTION_MARKERS = (
    "actually",
    "instead",
    "not that",
    "wrong",
    "fix that",
    "不是",
    "不对",
    "改成",
    "改为",
)

SESSION_PROFILE_STOPWORDS = {
    "about",
    "after",
    "agent",
    "analyze",
    "assistant",
    "build",
    "client",
    "code",
    "context",
    "ctxvault",
    "debug",
    "designing",
    "deterministic",
    "discuss",
    "from",
    "help",
    "implement",
    "implementation",
    "into",
    "just",
    "know",
    "local",
    "need",
    "next",
    "notes",
    "please",
    "project",
    "review",
    "session",
    "should",
    "some",
    "step",
    "steps",
    "task",
    "that",
    "then",
    "they",
    "this",
    "through",
    "user",
    "using",
    "want",
    "with",
    "work",
}

WORKSTREAM_DENSITY_BUDGET = {
    "summary_target_words": 48,
    "summary_warning_words": 60,
    "rationale_target_words": 72,
    "rationale_warning_words": 96,
    "notes_rotation_words": 160,
    "notes_hard_rotation_words": 220,
    "recurring_terms_max": 8,
    "task_labels_max": 8,
    "reusable_judgments_min": 2,
    "reusable_judgments_max": 6,
    "open_questions_max": 5,
}

TRANSCRIPT_SHAPE_MARKERS = (
    "assistant",
    "chat",
    "conversation",
    "first,",
    "i said",
    "next,",
    "then ",
    "turn ",
    "user",
    "we discussed",
)

JUDGMENT_MARKERS = (
    "avoid",
    "build",
    "compress",
    "do not",
    "keep",
    "must",
    "never",
    "prefer",
    "promote",
    "remain",
    "should",
    "treat",
    "use",
)

NEGATIVE_JUDGMENT_MARKERS = (
    "avoid",
    "do not",
    "don't",
    "must not",
    "never",
    "not ",
    "should not",
    "wrong",
)

POSITIVE_JUDGMENT_MARKERS = (
    "build",
    "keep",
    "must",
    "prefer",
    "promote",
    "remain",
    "should",
    "treat",
    "use",
)


def derive_episode_payloads(session_payload: dict[str, Any], turn_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_turns = sorted(turn_payloads, key=_turn_sort_key)
    if not ordered_turns:
        return []

    boundaries = [0]
    current_kind = _dominant_kind(ordered_turns[:1])
    for index in range(1, len(ordered_turns)):
        segment = ordered_turns[boundaries[-1] : index]
        turn = ordered_turns[index]
        proposed_kind = _infer_kind(turn)
        if _should_start_new_episode(segment, turn, current_kind=current_kind, proposed_kind=proposed_kind):
            boundaries.append(index)
            current_kind = proposed_kind
    boundaries.append(len(ordered_turns))

    scope = dict(session_payload.get("scope") or {})
    session_ref = f"session://{session_payload['id']}"
    session_token = _slug_token(_strip_prefix(str(session_payload["id"]), "sess_"))
    created_at = _utc_now()
    episodes: list[dict[str, Any]] = []

    for sequence, (start, end) in enumerate(zip(boundaries, boundaries[1:]), start=1):
        segment = ordered_turns[start:end]
        kind = _dominant_kind(segment)
        start_turn = segment[0]
        end_turn = segment[-1]
        turn_refs = [f"turn://{turn['id']}" for turn in segment]
        payloads = [session_payload, *segment]
        episodes.append(
            {
                "id": f"ep_{session_token}_{sequence:02d}_{kind}",
                "session_id": str(session_payload["id"]),
                "kind": kind,
                "goal": _goal_from_turns(segment),
                "start_turn_index": start,
                "end_turn_index": end - 1,
                "start_at": str(start_turn.get("created_at") or session_payload.get("started_at") or created_at),
                "end_at": str(end_turn.get("created_at") or start_turn.get("created_at") or created_at),
                "input_refs": _collect_input_refs(session_ref, segment),
                "outcome": _outcome_from_turns(segment),
                "quality_signals": _quality_signals(segment),
                "derived_refs": [],
                "scope": scope,
                "status": "active",
                "source_refs": [session_ref, *turn_refs],
                "sensitivity": _combined_sensitivity(payloads),
                "redaction_state": _combined_redaction_state(payloads),
                "secret_refs": _unique(
                    str(ref).strip()
                    for payload in payloads
                    for ref in payload.get("secret_refs", [])
                    if str(ref).strip()
                ),
                "exportable": all(bool(payload.get("exportable", True)) for payload in payloads),
                "created_at": created_at,
                "updated_at": created_at,
            }
        )

    return episodes


def build_episode_synthesis_payload(
    session_payload: dict[str, Any],
    episode_payload: dict[str, Any],
    turn_payloads: list[dict[str, Any]],
    *,
    knowledge_id: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    ordered_turns = sorted(turn_payloads, key=_turn_sort_key)
    if not ordered_turns:
        raise ValueError("episode synthesis requires at least one turn")

    session_ref = f"session://{session_payload['id']}"
    episode_ref = f"episode://{episode_payload['id']}"
    turn_refs = [f"turn://{turn['id']}" for turn in ordered_turns]
    source_refs = [episode_ref, session_ref, *turn_refs]
    artifact_id = knowledge_id or _default_synthesis_id(session_payload, episode_payload)
    artifact_title = title or _default_synthesis_title(session_payload, episode_payload)
    payloads = [session_payload, episode_payload, *ordered_turns]
    created_at = _utc_now()

    return {
        "id": artifact_id,
        "kind": "synthesis",
        "title": artifact_title,
        "scope": dict(episode_payload.get("scope") or session_payload.get("scope") or {}),
        "body": _render_synthesis_body(
            session_payload=session_payload,
            episode_payload=episode_payload,
            ordered_turns=ordered_turns,
            source_refs=source_refs,
        ),
        "source_refs": source_refs,
        "derived_from": [episode_ref],
        "status": "active",
        "sensitivity": _combined_sensitivity(payloads),
        "redaction_state": _combined_redaction_state(payloads),
        "secret_refs": _unique(
            str(ref).strip()
            for payload in payloads
            for ref in payload.get("secret_refs", [])
            if str(ref).strip()
        ),
        "exportable": all(bool(payload.get("exportable", True)) for payload in payloads),
        "created_at": created_at,
        "updated_at": created_at,
    }


def render_manual_note(
    knowledge_payload: dict[str, Any],
    *,
    output_path: Path,
    canonical_target: str,
    privacy: str | None = None,
    status: str = "draft",
    note_id: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    resolved_output = output_path.resolve()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    note_object_id = note_id or resolved_output.stem
    note_title = title or str(knowledge_payload.get("title") or note_object_id)
    note_privacy = privacy or _note_privacy_from_sensitivity(str(knowledge_payload.get("sensitivity") or "internal"))
    created_at = _utc_now()
    evidence_refs = _unique(str(ref).strip() for ref in knowledge_payload.get("source_refs", []) if str(ref).strip())

    front_matter = [
        "---",
        f"id: {json.dumps(note_object_id, ensure_ascii=True)}",
        f"title: {json.dumps(note_title, ensure_ascii=True)}",
        'type: "note"',
        f"privacy: {json.dumps(note_privacy, ensure_ascii=True)}",
        f"status: {json.dumps(status, ensure_ascii=True)}",
        f"canonical_target: {json.dumps(canonical_target, ensure_ascii=True)}",
        f"evidence_refs: {json.dumps(evidence_refs, ensure_ascii=True)}",
        f"created_at: {json.dumps(created_at, ensure_ascii=True)}",
        "---",
        "",
    ]

    lines = [
        f"# {note_title}",
        "",
        "## Source Artifact",
        f"- `{_knowledge_ref(str(knowledge_payload['id']))}`",
        f"- Kind: `{knowledge_payload.get('kind', 'unknown')}`",
        "",
        "## Summary",
        str(knowledge_payload.get("body") or "").strip() or "No summary available.",
        "",
        "## Evidence",
    ]
    lines.extend(f"- `{ref}`" for ref in evidence_refs)
    content = "\n".join(front_matter + lines).rstrip() + "\n"
    resolved_output.write_text(content, encoding="utf-8")

    return {
        "knowledge_id": str(knowledge_payload["id"]),
        "knowledge_ref": _knowledge_ref(str(knowledge_payload["id"])),
        "note_id": note_object_id,
        "title": note_title,
        "output_path": str(resolved_output),
        "canonical_target": canonical_target,
        "privacy": note_privacy,
        "status": status,
        "evidence_refs": evidence_refs,
    }


def build_session_profile(
    session_payload: dict[str, Any],
    *,
    turn_payloads: list[dict[str, Any]],
    episode_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered_turns = sorted(turn_payloads, key=_turn_sort_key)
    effective_episodes = list(episode_payloads) or derive_episode_payloads(session_payload, ordered_turns)
    title = str(session_payload.get("title") or session_payload.get("id") or "").strip()
    task_label = str(session_payload.get("task_label") or "").strip()
    client = str(session_payload.get("client") or "").strip()
    source_app = str(session_payload.get("source_app") or client or "").strip()
    source_surface = str(session_payload.get("source_surface") or "").strip()
    source_format = str(session_payload.get("source_format") or "").strip()
    capture_method = str(session_payload.get("capture_method") or "").strip()
    focus_terms = _session_focus_terms(session_payload, ordered_turns, effective_episodes)
    goals = _unique(str(payload.get("goal") or "").strip() for payload in effective_episodes if str(payload.get("goal") or "").strip())
    outcomes = _unique(str(payload.get("outcome") or "").strip() for payload in effective_episodes if str(payload.get("outcome") or "").strip())
    episode_kinds = _unique(str(payload.get("kind") or "other").strip() for payload in effective_episodes if str(payload.get("kind") or "").strip())
    return {
        "session_id": str(session_payload["id"]),
        "session_ref": f"session://{session_payload['id']}",
        "title": title,
        "task_label": task_label,
        "client": client,
        "source_app": source_app,
        "source_surface": source_surface,
        "source_format": source_format,
        "capture_method": capture_method,
        "focus_terms": focus_terms,
        "episode_kinds": episode_kinds,
        "goals": goals[:5],
        "outcomes": outcomes[:5],
        "turn_count": len(ordered_turns) if ordered_turns else int(session_payload.get("turn_count") or 0),
        "started_at": session_payload.get("started_at"),
        "ended_at": session_payload.get("ended_at"),
    }


def compare_session_profiles(anchor_profile: dict[str, Any], candidate_profile: dict[str, Any]) -> dict[str, Any]:
    anchor_terms = list(anchor_profile.get("focus_terms") or [])
    candidate_terms = set(candidate_profile.get("focus_terms") or [])
    shared_terms = [term for term in anchor_terms if term in candidate_terms]

    anchor_kinds = list(anchor_profile.get("episode_kinds") or [])
    candidate_kinds = set(candidate_profile.get("episode_kinds") or [])
    shared_episode_kinds = [kind for kind in anchor_kinds if kind in candidate_kinds]

    shared_task_label = (
        bool(anchor_profile.get("task_label"))
        and str(anchor_profile.get("task_label") or "").strip().lower()
        == str(candidate_profile.get("task_label") or "").strip().lower()
    )

    score = float(len(shared_terms) * 2 + len(shared_episode_kinds) * 1.5 + (2 if shared_task_label else 0))
    if anchor_terms and candidate_terms:
        score += round(len(shared_terms) / max(len(anchor_terms), len(candidate_terms)), 3)
    reasons: list[str] = []
    if shared_terms:
        reasons.append(f"shared focus terms: {', '.join(shared_terms[:4])}")
    if shared_episode_kinds:
        reasons.append(f"shared episode kinds: {', '.join(shared_episode_kinds[:3])}")
    if shared_task_label:
        reasons.append("same task label")

    return {
        "score": round(score, 3),
        "shared_terms": shared_terms[:6],
        "shared_episode_kinds": shared_episode_kinds[:4],
        "shared_task_label": shared_task_label,
        "reasons": reasons,
    }


def build_session_aggregate_preview(anchor_profile: dict[str, Any], related_profiles: list[dict[str, Any]]) -> dict[str, Any]:
    profiles = [anchor_profile, *related_profiles]
    term_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    client_counts: dict[str, int] = {}
    source_app_counts: dict[str, int] = {}
    task_labels: list[str] = []
    source_refs: list[str] = []

    for profile in profiles:
        source_refs.append(str(profile.get("session_ref") or ""))
        task_label = str(profile.get("task_label") or "").strip()
        if task_label:
            task_labels.append(task_label)
        client = str(profile.get("client") or "").strip()
        if client:
            client_counts[client] = client_counts.get(client, 0) + 1
        source_app = str(profile.get("source_app") or "").strip()
        if source_app:
            source_app_counts[source_app] = source_app_counts.get(source_app, 0) + 1
        for term in list(profile.get("focus_terms") or []):
            term_counts[term] = term_counts.get(term, 0) + 1
        for kind in list(profile.get("episode_kinds") or []):
            kind_counts[kind] = kind_counts.get(kind, 0) + 1

    recurring_terms = [
        {"term": term, "session_count": count}
        for term, count in sorted(term_counts.items(), key=lambda item: (-item[1], item[0]))
        if count > 1
    ][:8]
    episode_kind_counts = {
        kind: count for kind, count in sorted(kind_counts.items(), key=lambda item: (-item[1], item[0]))
    }
    clients = [
        {"client": client, "session_count": count}
        for client, count in sorted(client_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    source_apps = [
        {"source_app": source_app, "session_count": count}
        for source_app, count in sorted(source_app_counts.items(), key=lambda item: (-item[1], item[0]))
    ]

    return {
        "session_count": len(profiles),
        "source_refs": [ref for ref in _unique(source_refs) if ref],
        "recurring_terms": recurring_terms,
        "episode_kind_counts": episode_kind_counts,
        "clients": clients,
        "source_apps": source_apps,
        "task_labels": _unique(task_labels)[:8],
    }


def build_workstream_preview(
    session_aggregate_payload: dict[str, Any],
    *,
    episode_payloads: list[dict[str, Any]],
    knowledge_refs: list[str],
) -> dict[str, Any]:
    anchor_session = deepcopy(session_aggregate_payload["anchor_session"])
    related_sessions = [deepcopy(item) for item in session_aggregate_payload.get("related_sessions", [])]
    aggregate = deepcopy(session_aggregate_payload["aggregate"])
    session_payloads = [anchor_session, *[dict(item["session"]) for item in related_sessions]]
    all_payloads = [*session_payloads, *episode_payloads]

    session_refs = _unique(f"session://{payload['id']}" for payload in session_payloads if str(payload.get("id") or "").strip())
    episode_refs = _unique(f"episode://{payload['id']}" for payload in episode_payloads if str(payload.get("id") or "").strip())
    recurring_terms = [str(item.get("term") or "").strip() for item in aggregate.get("recurring_terms", []) if str(item.get("term") or "").strip()]
    task_labels = [str(label).strip() for label in aggregate.get("task_labels", []) if str(label).strip()]

    suggested_title = _workstream_title(session_payloads, task_labels=task_labels, recurring_terms=recurring_terms)
    suggested_summary = _workstream_summary(
        session_payloads,
        aggregate=aggregate,
        recurring_terms=recurring_terms,
        episode_payloads=episode_payloads,
    )
    suggested_rationale = _workstream_rationale(
        session_payloads,
        aggregate=aggregate,
        recurring_terms=recurring_terms,
    )
    suggested = {
        "scope": dict(anchor_session.get("scope") or {}),
        "title": suggested_title,
        "summary": suggested_summary,
        "rationale": suggested_rationale,
        "source_refs": _unique([*session_refs, *episode_refs, *_unique(knowledge_refs)]),
        "session_refs": session_refs,
        "episode_refs": episode_refs,
        "knowledge_refs": _unique(knowledge_refs),
        "recurring_terms": recurring_terms[:8],
        "task_labels": task_labels[:8],
        "episode_kind_counts": dict(aggregate.get("episode_kind_counts") or {}),
        "confidence": _workstream_confidence(
            session_payloads,
            aggregate=aggregate,
            recurring_terms=recurring_terms,
            episode_payloads=episode_payloads,
        ),
        "candidate_id_hint": _default_workstream_candidate_id(
            scope_value=str((anchor_session.get("scope") or {}).get("value") or ""),
            title=suggested_title,
        ),
        "workstream_id_hint": _default_workstream_id(
            scope_value=str((anchor_session.get("scope") or {}).get("value") or ""),
            title=suggested_title,
        ),
        "sensitivity": _combined_sensitivity(all_payloads),
        "redaction_state": _combined_redaction_state(all_payloads),
        "secret_refs": _unique(
            str(ref).strip()
            for payload in all_payloads
            for ref in payload.get("secret_refs", [])
            if str(ref).strip()
        ),
        "exportable": all(bool(payload.get("exportable", True)) for payload in all_payloads),
        "promotion_profile": build_workstream_promotion_profile(
            title=suggested_title,
            summary=suggested_summary,
            rationale=suggested_rationale,
            notes=None,
            source_refs=[*session_refs, *episode_refs, *_unique(knowledge_refs)],
            session_refs=session_refs,
            episode_refs=episode_refs,
            knowledge_refs=_unique(knowledge_refs),
        ),
    }
    return {
        **deepcopy(session_aggregate_payload),
        "episode_refs": episode_refs,
        "knowledge_refs": _unique(knowledge_refs),
        "suggested_workstream": suggested,
    }


def build_workstream_candidate_payload(
    suggested_workstream: dict[str, Any],
    *,
    candidate_id: str | None = None,
    candidate_for: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    rationale: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    effective_title = title or str(suggested_workstream.get("title") or "").strip()
    if not effective_title:
        raise ValueError("workstream candidate title must be non-empty")
    effective_summary = summary or str(suggested_workstream.get("summary") or "").strip()
    if not effective_summary:
        raise ValueError("workstream candidate summary must be non-empty")
    effective_rationale = rationale or str(suggested_workstream.get("rationale") or "").strip()
    if not effective_rationale:
        raise ValueError("workstream candidate rationale must be non-empty")
    scope = dict(suggested_workstream.get("scope") or {})
    scope_value = str(scope.get("value") or "")
    object_id = candidate_id or _default_workstream_candidate_id(scope_value=scope_value, title=effective_title)
    return {
        "id": object_id,
        "scope": scope,
        "title": effective_title,
        "summary": effective_summary,
        "rationale": effective_rationale,
        "source_refs": _unique(str(ref).strip() for ref in suggested_workstream.get("source_refs", []) if str(ref).strip()),
        "session_refs": _unique(str(ref).strip() for ref in suggested_workstream.get("session_refs", []) if str(ref).strip()),
        "episode_refs": _unique(str(ref).strip() for ref in suggested_workstream.get("episode_refs", []) if str(ref).strip()),
        "knowledge_refs": _unique(str(ref).strip() for ref in suggested_workstream.get("knowledge_refs", []) if str(ref).strip()),
        "recurring_terms": _unique(str(term).strip() for term in suggested_workstream.get("recurring_terms", []) if str(term).strip())[:8],
        "task_labels": _unique(str(label).strip() for label in suggested_workstream.get("task_labels", []) if str(label).strip())[:8],
        "episode_kind_counts": dict(suggested_workstream.get("episode_kind_counts") or {}),
        "confidence": float(suggested_workstream.get("confidence") or 0.0),
        "proposal_state": "proposed",
        "candidate_for": candidate_for,
        "notes": notes,
        "sensitivity": str(suggested_workstream.get("sensitivity") or "internal"),
        "redaction_state": str(suggested_workstream.get("redaction_state") or "none"),
        "secret_refs": _unique(str(ref).strip() for ref in suggested_workstream.get("secret_refs", []) if str(ref).strip()),
        "exportable": bool(suggested_workstream.get("exportable", True)),
        "created_at": _utc_now(),
    }


def build_workstream_payload(
    candidate_payload: dict[str, Any],
    *,
    workstream_id: str | None = None,
    existing_workstream: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_id = str(candidate_payload["id"])
    candidate_ref = f"workstream-candidate://{candidate_id}"
    target_id = workstream_id or str(candidate_payload.get("candidate_for") or "").strip() or _default_workstream_id(
        scope_value=str((candidate_payload.get("scope") or {}).get("value") or ""),
        title=str(candidate_payload.get("title") or ""),
        candidate_id=candidate_id,
    )
    now = _utc_now()
    existing = existing_workstream or {}
    existing_source_refs = [str(ref).strip() for ref in existing.get("source_refs", []) if str(ref).strip()]
    existing_derived_from = [str(ref).strip() for ref in existing.get("derived_from", []) if str(ref).strip()]

    return {
        "id": target_id,
        "scope": dict(candidate_payload["scope"]),
        "title": str(candidate_payload["title"]),
        "summary": str(candidate_payload["summary"]),
        "status": "active",
        "approval_state": "approved",
        "source_refs": _unique([*existing_source_refs, *list(candidate_payload.get("source_refs", [])), candidate_ref]),
        "session_refs": _unique([*list(existing.get("session_refs", [])), *list(candidate_payload.get("session_refs", []))]),
        "episode_refs": _unique([*list(existing.get("episode_refs", [])), *list(candidate_payload.get("episode_refs", []))]),
        "knowledge_refs": _unique([*list(existing.get("knowledge_refs", [])), *list(candidate_payload.get("knowledge_refs", []))]),
        "derived_from": _unique([*existing_derived_from, candidate_ref]),
        "recurring_terms": _unique([*list(existing.get("recurring_terms", [])), *list(candidate_payload.get("recurring_terms", []))])[:8],
        "task_labels": _unique([*list(existing.get("task_labels", [])), *list(candidate_payload.get("task_labels", []))])[:8],
        "episode_kind_counts": _merge_episode_kind_counts(
            existing.get("episode_kind_counts"),
            candidate_payload.get("episode_kind_counts"),
        ),
        "notes": candidate_payload.get("notes"),
        "secret_refs": _unique([*list(existing.get("secret_refs", [])), *list(candidate_payload.get("secret_refs", []))]),
        "sensitivity": _combined_sensitivity([payload for payload in [existing, candidate_payload] if payload]),
        "redaction_state": _combined_redaction_state([payload for payload in [existing, candidate_payload] if payload]),
        "exportable": bool(existing.get("exportable", True)) and bool(candidate_payload.get("exportable", True)),
        "created_at": str(existing.get("created_at") or now),
        "updated_at": now,
    }


def build_workstream_promotion_profile(
    *,
    title: str,
    summary: str,
    rationale: str,
    notes: str | None,
    source_refs: list[str],
    session_refs: list[str],
    episode_refs: list[str],
    knowledge_refs: list[str],
    reusable_judgments: list[str] | None = None,
    open_questions: list[str] | None = None,
) -> dict[str, Any]:
    effective_judgments = _unique(
        reusable_judgments
        or [
            *_extract_reusable_judgments(summary),
            *_extract_reusable_judgments(rationale),
            *_extract_reusable_judgments(notes or ""),
        ]
    )[: WORKSTREAM_DENSITY_BUDGET["reusable_judgments_max"]]
    effective_questions = _unique(open_questions or _extract_open_questions(notes or ""))[
        : WORKSTREAM_DENSITY_BUDGET["open_questions_max"]
    ]

    summary_words = _word_count(summary)
    rationale_words = _word_count(rationale)
    notes_words = _word_count(notes or "")

    checks = [
        _budget_check(
            name="summary_within_budget",
            measured=summary_words,
            target=WORKSTREAM_DENSITY_BUDGET["summary_target_words"],
            warning=WORKSTREAM_DENSITY_BUDGET["summary_warning_words"],
            unit="words",
        ),
        _budget_check(
            name="rationale_within_budget",
            measured=rationale_words,
            target=WORKSTREAM_DENSITY_BUDGET["rationale_target_words"],
            warning=WORKSTREAM_DENSITY_BUDGET["rationale_warning_words"],
            unit="words",
        ),
        _presence_check(
            name="has_source_grounding",
            present=bool(source_refs),
            detail=f"{len(source_refs)} source ref(s)" if source_refs else "no source refs attached",
            fail_when_missing=True,
        ),
        _presence_check(
            name="has_reusable_judgments",
            present=len(effective_judgments) >= 1,
            detail=f"{len(effective_judgments)} reusable judgment(s)",
            fail_when_missing=False,
        ),
        _transcript_shape_check(name="avoids_transcript_shape_summary", text=summary),
        _transcript_shape_check(name="avoids_transcript_shape_rationale", text=rationale),
        _budget_check(
            name="notes_need_rotation",
            measured=notes_words,
            target=WORKSTREAM_DENSITY_BUDGET["notes_rotation_words"],
            warning=WORKSTREAM_DENSITY_BUDGET["notes_hard_rotation_words"],
            unit="words",
            invert_label=True,
        ),
    ]

    readiness = "ready"
    if any(check["status"] == "fail" for check in checks):
        readiness = "blocked"
    elif any(check["status"] == "warn" for check in checks):
        readiness = "warning"

    return {
        "readiness": readiness,
        "budget": deepcopy(WORKSTREAM_DENSITY_BUDGET),
        "measures": {
            "title_words": _word_count(title),
            "summary_words": summary_words,
            "rationale_words": rationale_words,
            "notes_words": notes_words,
            "source_ref_count": len(source_refs),
            "session_ref_count": len(session_refs),
            "episode_ref_count": len(episode_refs),
            "knowledge_ref_count": len(knowledge_refs),
            "reusable_judgment_count": len(effective_judgments),
            "open_question_count": len(effective_questions),
        },
        "checks": checks,
        "warnings": [check["detail"] for check in checks if check["status"] in {"warn", "fail"}],
        "reusable_judgments": effective_judgments,
        "open_questions": effective_questions,
    }


def build_workstream_intelligence_report(
    workstream_payload: dict[str, Any],
    *,
    knowledge_payloads: list[dict[str, Any]],
    memory_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    workstream_ref = f"workstream://{workstream_payload['id']}"
    knowledge_refs = [f"knowledge://{payload['id']}" for payload in knowledge_payloads if str(payload.get("id") or "").strip()]
    memory_refs = [f"memory://{payload['id']}" for payload in memory_payloads if str(payload.get("id") or "").strip()]

    reusable_judgments = _unique(
        [
            *_extract_reusable_judgments(str(workstream_payload.get("summary") or "")),
            *_extract_reusable_judgments(str(workstream_payload.get("notes") or "")),
            *[
                judgment
                for payload in knowledge_payloads
                for judgment in _extract_reusable_judgments(_textish_body(payload.get("body")))
            ],
            *[
                str(payload.get("statement") or "").strip()
                for payload in memory_payloads
                if str(payload.get("statement") or "").strip()
            ],
        ]
    )[: WORKSTREAM_DENSITY_BUDGET["reusable_judgments_max"]]

    open_questions = _unique(
        [
            *_extract_open_questions(str(workstream_payload.get("notes") or "")),
            *[
                question
                for payload in knowledge_payloads
                for question in _extract_open_questions(_textish_body(payload.get("body")))
            ],
        ]
    )[: WORKSTREAM_DENSITY_BUDGET["open_questions_max"]]

    promotion_profile = build_workstream_promotion_profile(
        title=str(workstream_payload.get("title") or ""),
        summary=str(workstream_payload.get("summary") or ""),
        rationale=str(workstream_payload.get("notes") or "") or str(workstream_payload.get("summary") or ""),
        notes=str(workstream_payload.get("notes") or ""),
        source_refs=[str(ref).strip() for ref in workstream_payload.get("source_refs", []) if str(ref).strip()],
        session_refs=[str(ref).strip() for ref in workstream_payload.get("session_refs", []) if str(ref).strip()],
        episode_refs=[str(ref).strip() for ref in workstream_payload.get("episode_refs", []) if str(ref).strip()],
        knowledge_refs=[str(ref).strip() for ref in workstream_payload.get("knowledge_refs", []) if str(ref).strip()],
        reusable_judgments=reusable_judgments,
        open_questions=open_questions,
    )
    contradictions = _detect_workstream_contradictions(
        workstream_payload,
        knowledge_payloads=knowledge_payloads,
        memory_payloads=memory_payloads,
    )
    gaps = _detect_workstream_gaps(
        workstream_payload,
        promotion_profile=promotion_profile,
        contradictions=contradictions,
        knowledge_payloads=knowledge_payloads,
        reusable_judgments=reusable_judgments,
        open_questions=open_questions,
    )
    next_questions = _build_next_question_suggestions(
        workstream_payload,
        contradictions=contradictions,
        gaps=gaps,
        open_questions=open_questions,
    )

    return {
        "workstream_ref": workstream_ref,
        "workstream": deepcopy(workstream_payload),
        "summary": {
            "session_count": len(list(workstream_payload.get("session_refs") or [])),
            "episode_count": len(list(workstream_payload.get("episode_refs") or [])),
            "knowledge_count": len(knowledge_payloads),
            "memory_count": len(memory_payloads),
            "contradiction_count": len(contradictions),
            "gap_count": len(gaps),
            "next_question_count": len(next_questions),
        },
        "current_state": {
            "title": str(workstream_payload.get("title") or ""),
            "summary": str(workstream_payload.get("summary") or ""),
            "task_labels": _unique(str(label).strip() for label in workstream_payload.get("task_labels", []) if str(label).strip()),
            "focus_terms": _unique(str(term).strip() for term in workstream_payload.get("recurring_terms", []) if str(term).strip()),
            "reusable_judgments": reusable_judgments,
            "open_questions": open_questions,
            "distilled_asset_refs": _unique([*knowledge_refs, *memory_refs]),
        },
        "promotion_profile": promotion_profile,
        "contradictions": contradictions,
        "gaps": gaps,
        "next_questions": next_questions,
        "sources": {
            "knowledge_refs": knowledge_refs,
            "memory_refs": memory_refs,
        },
    }


def _budget_check(
    *,
    name: str,
    measured: int,
    target: int,
    warning: int,
    unit: str,
    invert_label: bool = False,
) -> dict[str, Any]:
    if measured <= target:
        status = "pass"
    elif measured <= warning:
        status = "warn"
    else:
        status = "fail"
    if invert_label:
        detail = f"{measured} {unit}; rotate once it passes {target}"
    else:
        detail = f"{measured} {unit}; target <= {target}, warning > {target}"
    return {
        "name": name,
        "status": status,
        "detail": detail,
        "measured": measured,
        "target": target,
        "warning": warning,
    }


def _presence_check(*, name: str, present: bool, detail: str, fail_when_missing: bool) -> dict[str, Any]:
    return {
        "name": name,
        "status": "pass" if present else ("fail" if fail_when_missing else "warn"),
        "detail": detail,
    }


def _transcript_shape_check(*, name: str, text: str) -> dict[str, Any]:
    transcript_shaped = _looks_transcript_shaped(text)
    return {
        "name": name,
        "status": "warn" if transcript_shaped else "pass",
        "detail": "transcript-shaped phrasing detected" if transcript_shaped else "dense summary shape",
    }


def _looks_transcript_shaped(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if not normalized:
        return False
    hit_count = sum(1 for marker in TRANSCRIPT_SHAPE_MARKERS if marker in normalized)
    first_person = len(re.findall(r"\b(i|we|you)\b", normalized))
    return hit_count >= 2 or (hit_count >= 1 and first_person >= 2)


def _textish_body(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_textish_body(item) for item in value if _textish_body(item))
    if isinstance(value, dict):
        parts: list[str] = []
        for key in ("summary", "body", "content", "text", "statement"):
            candidate = _textish_body(value.get(key))
            if candidate:
                parts.append(candidate)
        if parts:
            return "\n".join(parts)
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w-]+\b", str(text or "")))


def _markdown_section_bullets(text: str, headings: set[str]) -> list[str]:
    lines = str(text or "").splitlines()
    current_heading = ""
    items: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_heading = re.sub(r"^#+\s*", "", line).strip().lower()
            continue
        if current_heading in headings and line.startswith("- "):
            items.append(_normalize_extracted_line(line[2:]))
    return [item for item in items if item]


def _normalize_extracted_line(text: str) -> str:
    normalized = re.sub(r"`+", "", str(text or "").strip())
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" -")


def _extract_open_questions(text: str) -> list[str]:
    explicit = _markdown_section_bullets(text, {"open questions", "questions", "unresolved questions"})
    sentence_questions = [
        _normalize_extracted_line(match.group(1))
        for match in re.finditer(r"([^.!?\n]+?\?)", str(text or ""))
    ]
    return _unique(question for question in [*explicit, *sentence_questions] if question)[: WORKSTREAM_DENSITY_BUDGET["open_questions_max"]]


def _extract_reusable_judgments(text: str) -> list[str]:
    explicit = _markdown_section_bullets(
        text,
        {"key points", "reusable judgments", "judgments", "summary", "actions or procedures"},
    )
    sentences = [
        _normalize_extracted_line(part)
        for part in re.split(r"(?<=[.!?])\s+|\n+", str(text or ""))
        if _normalize_extracted_line(part)
    ]
    heuristic = [
        sentence
        for sentence in sentences
        if _looks_like_judgment(sentence)
    ]
    return _unique(item for item in [*explicit, *heuristic] if item)[: WORKSTREAM_DENSITY_BUDGET["reusable_judgments_max"]]


def _looks_like_judgment(text: str) -> bool:
    normalized = str(text or "").strip().lower()
    if len(normalized) < 24:
        return False
    return any(marker in normalized for marker in JUDGMENT_MARKERS)


def _detect_workstream_contradictions(
    workstream_payload: dict[str, Any],
    *,
    knowledge_payloads: list[dict[str, Any]],
    memory_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = [
        *_judgment_records_from_source(
            f"workstream://{workstream_payload['id']}",
            "workstream_summary",
            str(workstream_payload.get("summary") or ""),
        ),
        *_judgment_records_from_source(
            f"workstream://{workstream_payload['id']}",
            "workstream_notes",
            str(workstream_payload.get("notes") or ""),
        ),
    ]
    for payload in knowledge_payloads:
        records.extend(
            _judgment_records_from_source(
                f"knowledge://{payload['id']}",
                "knowledge_artifact",
                _textish_body(payload.get("body")),
            )
        )
    for payload in memory_payloads:
        statement = str(payload.get("statement") or "").strip()
        if statement:
            records.extend(_judgment_records_from_source(f"memory://{payload['id']}", "memory", statement))

    contradictions: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left["base_ref"] == right["base_ref"]:
                continue
            if left["polarity"] == "neutral" or right["polarity"] == "neutral":
                continue
            if left["polarity"] == right["polarity"]:
                continue
            shared_terms = [term for term in left["subject_terms"] if term in right["subject_terms"]]
            if len(shared_terms) < 2:
                continue
            subject = ", ".join(shared_terms[:3])
            pair_key = tuple(sorted([left["ref"], right["ref"]]) + [subject])
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            contradictions.append(
                {
                    "kind": "judgment_conflict",
                    "subject": subject,
                    "left_ref": left["ref"],
                    "right_ref": right["ref"],
                    "left_statement": left["text"],
                    "right_statement": right["text"],
                    "shared_terms": shared_terms[:4],
                    "reason": f"opposite judgment polarity over {subject}",
                }
            )
    return contradictions[:5]


def _judgment_records_from_source(base_ref: str, source_type: str, text: str) -> list[dict[str, Any]]:
    judgments = _extract_reusable_judgments(text)
    records: list[dict[str, Any]] = []
    for index, judgment in enumerate(judgments, start=1):
        subject_terms = _judgment_subject_terms(judgment)
        if len(subject_terms) < 2:
            continue
        records.append(
            {
                "ref": f"{base_ref}#{source_type}:{index}",
                "base_ref": base_ref,
                "source_type": source_type,
                "text": judgment,
                "subject_terms": subject_terms,
                "polarity": _judgment_polarity(judgment),
            }
        )
    return records


def _judgment_subject_terms(text: str) -> list[str]:
    stopwords = SESSION_PROFILE_STOPWORDS | {
        "and",
        "are",
        "because",
        "into",
        "must",
        "never",
        "not",
        "remain",
        "should",
        "than",
        "that",
        "them",
        "these",
        "this",
        "those",
        "use",
        "using",
    }
    tokens = re.findall(r"[A-Za-z0-9_]+", str(text or "").lower())
    return _unique(token for token in tokens if len(token) > 2 and token not in stopwords)[:6]


def _judgment_polarity(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if any(marker in normalized for marker in NEGATIVE_JUDGMENT_MARKERS):
        return "negative"
    if any(marker in normalized for marker in POSITIVE_JUDGMENT_MARKERS):
        return "positive"
    return "neutral"


def _detect_workstream_gaps(
    workstream_payload: dict[str, Any],
    *,
    promotion_profile: dict[str, Any],
    contradictions: list[dict[str, Any]],
    knowledge_payloads: list[dict[str, Any]],
    reusable_judgments: list[str],
    open_questions: list[str],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    session_refs = list(workstream_payload.get("session_refs") or [])
    workstream_ref = f"workstream://{workstream_payload['id']}"
    if session_refs and not knowledge_payloads:
        gaps.append(
            {
                "gap_type": "missing_distilled_knowledge",
                "severity": "high",
                "detail": "workstream links sessions but has no distilled knowledge artifacts",
                "source_refs": [workstream_ref, *session_refs[:3]],
                "suggested_action": "promote one or more syntheses before expanding the current summary",
            }
        )
    if not reusable_judgments:
        gaps.append(
            {
                "gap_type": "missing_reusable_judgments",
                "severity": "medium",
                "detail": "current state lacks explicit reusable judgments",
                "source_refs": [workstream_ref],
                "suggested_action": "compress the workstream into two to six durable judgments",
            }
        )
    if not open_questions:
        gaps.append(
            {
                "gap_type": "no_active_questions",
                "severity": "low",
                "detail": "no open questions are captured in the distilled layer",
                "source_refs": [workstream_ref],
                "suggested_action": "capture the next unresolved question instead of growing the narrative summary",
            }
        )
    for check in list(promotion_profile.get("checks") or []):
        if check.get("status") == "pass":
            continue
        gap_type = check["name"]
        severity = "high" if check["status"] == "fail" else "medium"
        suggested_action = "refresh the current summary and rotate history outward"
        if gap_type == "has_reusable_judgments":
            suggested_action = "rewrite the current state around reusable judgments rather than chronological prose"
        elif gap_type == "has_source_grounding":
            suggested_action = "restore source refs before promotion continues"
        gaps.append(
            {
                "gap_type": gap_type,
                "severity": severity,
                "detail": str(check.get("detail") or gap_type),
                "source_refs": [workstream_ref],
                "suggested_action": suggested_action,
            }
        )
    if contradictions:
        gaps.append(
            {
                "gap_type": "needs_conflict_resolution",
                "severity": "high",
                "detail": f"{len(contradictions)} contradiction(s) need canonical resolution",
                "source_refs": [workstream_ref, *[item["left_ref"] for item in contradictions[:2]]],
                "suggested_action": "resolve conflicts before further promotion or export expansion",
            }
        )
    return gaps[:8]


def _build_next_question_suggestions(
    workstream_payload: dict[str, Any],
    *,
    contradictions: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    open_questions: list[str],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    workstream_ref = f"workstream://{workstream_payload['id']}"
    for question in open_questions:
        suggestions.append(
            {
                "question": question,
                "reason": "already captured as an open question in the distilled layer",
                "priority": "high",
                "source_refs": [workstream_ref],
            }
        )
    for contradiction in contradictions:
        subject = contradiction.get("subject") or "this conflict"
        suggestions.append(
            {
                "question": f"Which judgment should become canonical for {subject}?",
                "reason": "contradiction detected across distilled assets",
                "priority": "high",
                "source_refs": [contradiction["left_ref"], contradiction["right_ref"]],
            }
        )
    gap_to_question = {
        "missing_distilled_knowledge": "What reusable judgment from this workstream should be promoted into a synthesis first?",
        "missing_reusable_judgments": "Which two or three durable judgments best describe this workstream now?",
        "no_active_questions": "What unresolved question is currently blocking or redirecting this workstream?",
        "summary_within_budget": "What belongs in the current canonical summary versus archive history?",
        "rationale_within_budget": "What rationale still matters for future reuse, and what can be dropped?",
        "notes_need_rotation": "Which details should stay in current state, and which should move to history or archive?",
        "needs_conflict_resolution": "What decision will resolve the current contradiction without weakening the deterministic substrate?",
    }
    for gap in gaps:
        question = gap_to_question.get(str(gap.get("gap_type") or ""))
        if not question:
            continue
        suggestions.append(
            {
                "question": question,
                "reason": str(gap.get("detail") or gap.get("gap_type") or "gap detected"),
                "priority": "medium" if gap.get("severity") == "low" else "high",
                "source_refs": list(gap.get("source_refs") or [workstream_ref]),
            }
        )
    deduped: list[dict[str, Any]] = []
    seen_questions: set[str] = set()
    for item in suggestions:
        question = str(item.get("question") or "").strip()
        if not question or question in seen_questions:
            continue
        seen_questions.add(question)
        deduped.append(item)
    return deduped[:5]


def _render_synthesis_body(
    *,
    session_payload: dict[str, Any],
    episode_payload: dict[str, Any],
    ordered_turns: list[dict[str, Any]],
    source_refs: list[str],
) -> str:
    lines = [
        "## Episode",
        f"- Session: `session://{session_payload['id']}`",
        f"- Episode: `episode://{episode_payload['id']}`",
        f"- Kind: `{episode_payload.get('kind', 'other')}`",
        f"- Goal: {episode_payload.get('goal', '')}",
    ]
    outcome = str(episode_payload.get("outcome") or "").strip()
    if outcome:
        lines.append(f"- Outcome: {outcome}")

    key_points = _key_points_from_turns(ordered_turns)
    if key_points:
        lines.extend(["", "## Key Points", *[f"- {point}" for point in key_points]])

    open_questions = _open_questions_from_turns(ordered_turns)
    if open_questions:
        lines.extend(["", "## Open Questions", *[f"- {question}" for question in open_questions]])

    lines.extend(["", "## Evidence", *[f"- `{ref}`" for ref in source_refs]])
    return "\n".join(lines)


def _should_start_new_episode(
    segment: list[dict[str, Any]],
    turn: dict[str, Any],
    *,
    current_kind: str,
    proposed_kind: str,
) -> bool:
    if len(segment) < 2:
        return False
    if str(turn.get("role") or "").lower() != "user":
        return False
    text = _content_text(turn).lower()
    if any(marker in text for marker in PIVOT_MARKERS):
        return True
    return proposed_kind not in {"other", current_kind} and proposed_kind != current_kind


def _dominant_kind(turn_payloads: list[dict[str, Any]]) -> str:
    for turn in turn_payloads:
        kind = _infer_kind(turn)
        if kind != "other":
            return kind
    return "other"


def _infer_kind(turn_payload: dict[str, Any]) -> str:
    text = _content_text(turn_payload).lower()
    for kind, patterns in EPISODE_KIND_PATTERNS:
        if any(pattern in text for pattern in patterns):
            return kind
    return "other"


def _goal_from_turns(turn_payloads: list[dict[str, Any]]) -> str:
    for turn in turn_payloads:
        if str(turn.get("role") or "").lower() == "user":
            return _excerpt(_content_text(turn), limit=160)
    return _excerpt(_content_text(turn_payloads[0]), limit=160)


def _outcome_from_turns(turn_payloads: list[dict[str, Any]]) -> str:
    for turn in reversed(turn_payloads):
        if str(turn.get("role") or "").lower() == "assistant":
            return _excerpt(_content_text(turn), limit=160)
    return _excerpt(_content_text(turn_payloads[-1]), limit=160)


def _collect_input_refs(session_ref: str, turn_payloads: list[dict[str, Any]]) -> list[str]:
    values = [session_ref]
    for turn in turn_payloads:
        prompt_asset_id = str(turn.get("prompt_asset_id") or "").strip()
        bundle_id = str(turn.get("context_bundle_id") or "").strip()
        if prompt_asset_id:
            values.append(f"prompt://{prompt_asset_id}")
        if bundle_id:
            values.append(f"bundle://{bundle_id}")
        values.extend(str(ref).strip() for ref in turn.get("source_refs", []) if str(ref).strip())
    return _unique(values)


def _quality_signals(turn_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    user_corrections = 0
    assistant_revisions = 0
    tool_total = 0
    tool_successes = 0
    accepted_outputs = 0

    for index, turn in enumerate(turn_payloads):
        role = str(turn.get("role") or "").lower()
        text = _content_text(turn).lower()
        annotations = turn.get("annotations") if isinstance(turn.get("annotations"), dict) else {}
        if role == "user" and any(marker in text for marker in CORRECTION_MARKERS):
            user_corrections += 1
        if role == "assistant" and index > 0:
            assistant_revisions += 1
        if role == "tool":
            tool_total += 1
            status = str(turn.get("status") or annotations.get("status") or "").lower()
            if status in {"ok", "success", "completed", "accepted"}:
                tool_successes += 1
        if role == "assistant" and str(annotations.get("status") or "").lower() == "accepted":
            accepted_outputs += 1

    return {
        "user_corrections": user_corrections,
        "assistant_revisions": assistant_revisions,
        "accepted_outputs": accepted_outputs,
        "tool_success_rate": (tool_successes / tool_total) if tool_total else None,
    }


def _key_points_from_turns(turn_payloads: list[dict[str, Any]]) -> list[str]:
    points: list[str] = []
    for turn in turn_payloads:
        role = str(turn.get("role") or "unknown").lower()
        text = _excerpt(_content_text(turn), limit=140)
        if not text:
            continue
        label = {
            "user": "User request",
            "assistant": "Assistant response",
            "tool": "Tool result",
        }.get(role, role.title())
        points.append(f"{label}: {text}")
    return _unique(points)[:6]


def _open_questions_from_turns(turn_payloads: list[dict[str, Any]]) -> list[str]:
    questions = [
        _excerpt(_content_text(turn), limit=140)
        for turn in turn_payloads
        if str(turn.get("role") or "").lower() == "user" and "?" in _content_text(turn)
    ]
    return _unique(question for question in questions if question)[:3]


def _default_synthesis_id(session_payload: dict[str, Any], episode_payload: dict[str, Any]) -> str:
    session_token = _slug_token(_strip_prefix(str(session_payload["id"]), "sess_"))
    episode_token = _slug_token(_strip_prefix(str(episode_payload["id"]), "ep_"))
    return f"know_{session_token}_{episode_token}_synth_v1"


def _default_synthesis_title(session_payload: dict[str, Any], episode_payload: dict[str, Any]) -> str:
    session_title = str(session_payload.get("title") or session_payload["id"]).strip()
    kind = str(episode_payload.get("kind") or "other").replace("_", " ")
    return f"{session_title} - {kind.title()} Synthesis"


def _knowledge_ref(knowledge_id: str) -> str:
    return f"knowledge://{knowledge_id}"


def _note_privacy_from_sensitivity(sensitivity: str) -> str:
    if sensitivity == "public":
        return "public"
    if sensitivity == "sensitive":
        return "sensitive"
    return "private"


def _content_text(turn_payload: dict[str, Any]) -> str:
    content = turn_payload.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return _normalize_whitespace(content)
    return _normalize_whitespace(json.dumps(content, ensure_ascii=True, sort_keys=True))


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _session_focus_terms(
    session_payload: dict[str, Any],
    turn_payloads: list[dict[str, Any]],
    episode_payloads: list[dict[str, Any]],
) -> list[str]:
    texts = [
        str(session_payload.get("title") or ""),
        str(session_payload.get("task_label") or ""),
        *[str(payload.get("goal") or "") for payload in episode_payloads],
        *[str(payload.get("outcome") or "") for payload in episode_payloads],
    ]
    if turn_payloads:
        texts.extend(
            [
                _content_text(turn_payloads[0]),
                _content_text(turn_payloads[-1]),
            ]
        )
    counts: dict[str, int] = {}
    for text in texts:
        for token in _profile_tokens(text):
            counts[token] = counts.get(token, 0) + 1
    return [term for term, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]]


def _profile_tokens(value: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9]{3,}", value.lower())
    return [token for token in tokens if token not in SESSION_PROFILE_STOPWORDS]


def _excerpt(value: str, *, limit: int) -> str:
    normalized = _normalize_whitespace(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _turn_sort_key(turn_payload: dict[str, Any]) -> tuple[str, int, str]:
    return (
        str(turn_payload.get("created_at") or ""),
        int(turn_payload.get("ordinal") or 0),
        str(turn_payload.get("id") or ""),
    )


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _combined_sensitivity(payloads: list[dict[str, Any]]) -> str:
    ranks = {"public": 0, "internal": 1, "sensitive": 2, "restricted": 3}
    best = "public"
    best_rank = -1
    for payload in payloads:
        sensitivity = str(payload.get("sensitivity") or "internal")
        rank = ranks.get(sensitivity, 1)
        if rank > best_rank:
            best = sensitivity
            best_rank = rank
    return best


def _combined_redaction_state(payloads: list[dict[str, Any]]) -> str:
    ranks = {"none": 0, "partial": 1, "fully_redacted": 2, "withheld": 3}
    best = "none"
    best_rank = -1
    for payload in payloads:
        state = str(payload.get("redaction_state") or "none")
        rank = ranks.get(state, 0)
        if rank > best_rank:
            best = state
            best_rank = rank
    return best


def _strip_prefix(value: str, prefix: str) -> str:
    return value[len(prefix) :] if value.startswith(prefix) else value


def _workstream_title(session_payloads: list[dict[str, Any]], *, task_labels: list[str], recurring_terms: list[str]) -> str:
    if task_labels:
        return task_labels[0]
    title = str(session_payloads[0].get("title") or "").strip() if session_payloads else ""
    if title:
        return title
    if recurring_terms:
        return f"Workstream: {' '.join(recurring_terms[:3])}"
    anchor_id = str(session_payloads[0].get("id") or "workstream") if session_payloads else "workstream"
    return f"Workstream {anchor_id}"


def _workstream_summary(
    session_payloads: list[dict[str, Any]],
    *,
    aggregate: dict[str, Any],
    recurring_terms: list[str],
    episode_payloads: list[dict[str, Any]],
) -> str:
    session_count = len(session_payloads)
    episode_count = len(episode_payloads)
    scope_value = str((session_payloads[0].get("scope") or {}).get("value") or "").strip() if session_payloads else ""
    focus = ", ".join(recurring_terms[:4]) if recurring_terms else "related conversation context"
    task_labels = [str(label).strip() for label in aggregate.get("task_labels", []) if str(label).strip()]
    if task_labels:
        return (
            f"Cross-session workstream for {task_labels[0]} in {scope_value or 'the local vault'}, "
            f"covering {session_count} related session(s) and {episode_count} derived episode(s). "
            f"Recurring focus terms: {focus}."
        )
    return (
        f"Cross-session workstream covering {session_count} related session(s) and {episode_count} derived "
        f"episode(s) in {scope_value or 'the local vault'}. Recurring focus terms: {focus}."
    )


def _workstream_rationale(
    session_payloads: list[dict[str, Any]],
    *,
    aggregate: dict[str, Any],
    recurring_terms: list[str],
) -> str:
    session_count = len(session_payloads)
    task_labels = [str(label).strip() for label in aggregate.get("task_labels", []) if str(label).strip()]
    if task_labels:
        return (
            f"{session_count} related sessions share the task label {task_labels[0]!r} and recurring terms "
            f"{', '.join(recurring_terms[:4]) or 'from the same initiative'}, so they should be reviewed together "
            "as one durable workstream."
        )
    return (
        f"{session_count} related sessions share recurring terms "
        f"{', '.join(recurring_terms[:4]) or 'from the same initiative'}, so they should be reviewed together "
        "as one durable workstream."
    )


def _workstream_confidence(
    session_payloads: list[dict[str, Any]],
    *,
    aggregate: dict[str, Any],
    recurring_terms: list[str],
    episode_payloads: list[dict[str, Any]],
) -> float:
    score = 0.35
    score += min(0.25, max(0, len(session_payloads) - 1) * 0.08)
    score += min(0.2, len(recurring_terms) * 0.04)
    score += min(0.15, len(episode_payloads) * 0.03)
    if aggregate.get("task_labels"):
        score += 0.05
    return round(min(score, 0.95), 3)


def _merge_episode_kind_counts(
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
) -> dict[str, int]:
    merged: dict[str, int] = {}
    for payload in [left or {}, right or {}]:
        for key, value in payload.items():
            count = int(value or 0)
            merged[key] = max(merged.get(key, 0), count)
    return {key: merged[key] for key in sorted(merged)}


def _default_workstream_candidate_id(*, scope_value: str, title: str) -> str:
    slug = _slug_token(title)
    scope_token = _slug_token(scope_value or "context")
    return f"wsc_{scope_token}_{slug}"


def _default_workstream_id(*, scope_value: str, title: str, candidate_id: str | None = None) -> str:
    if candidate_id and candidate_id.startswith("wsc_"):
        return f"ws_{candidate_id[4:]}"
    slug = _slug_token(title)
    scope_token = _slug_token(scope_value or "context")
    return f"ws_{scope_token}_{slug}"


def _slug_token(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return normalized[:48] or "episode"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
