from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Iterator

from .intelligence import (
    build_episode_synthesis_payload,
    build_session_aggregate_preview,
    build_session_profile,
    build_workstream_candidate_payload,
    build_workstream_intelligence_report,
    build_workstream_payload,
    build_workstream_preview,
    compare_session_profiles,
    derive_episode_payloads,
    render_manual_note,
)
from .layout import VaultLayout
from .policy import CtxVaultPolicy


CORE_MODEL_TO_KIND = {
    "Session": "session",
    "Episode": "episode",
    "Turn": "turn",
    "Workstream": "workstream",
    "WorkstreamCandidate": "workstream_candidate",
    "PromptAsset": "prompt_asset",
    "PromptRun": "prompt_run",
    "PromptPatch": "prompt_patch",
    "MemoryCandidate": "memory_candidate",
    "Memory": "memory",
    "KnowledgeArtifact": "knowledge_artifact",
    "ContextBundle": "context_bundle",
    "EvalRun": "eval_run",
}

GOVERNANCE_MODEL_TO_KIND = {
    "ClaimRecord": "claim_record",
    "EvidenceLink": "evidence_link",
    "AuditRun": "audit_run",
    "AdapterCapabilityProfile": "adapter_capability_profile",
}

KIND_TO_SCHEME = {
    "session": "session",
    "episode": "episode",
    "turn": "turn",
    "workstream": "workstream",
    "workstream_candidate": "workstream-candidate",
    "prompt_asset": "prompt",
    "prompt_run": "prompt-run",
    "prompt_patch": "prompt-patch",
    "memory_candidate": "memory-candidate",
    "memory": "memory",
    "knowledge_artifact": "knowledge",
    "context_bundle": "bundle",
    "eval_run": "eval",
    "claim_record": "claim",
    "evidence_link": "evidence",
    "audit_run": "audit",
    "adapter_capability_profile": "adapter",
}

CORE_FIXTURE_MODELS = {
    "session.json": "Session",
    "context-bundle.json": "ContextBundle",
    "workstream.json": "Workstream",
    "workstream-candidate.json": "WorkstreamCandidate",
    "prompt-asset.json": "PromptAsset",
    "prompt-patch.json": "PromptPatch",
    "memory-candidate.json": "MemoryCandidate",
    "memory.json": "Memory",
    "knowledge-artifact.json": "KnowledgeArtifact",
}

GOVERNANCE_FIXTURE_MODELS = {
    "claim-record.json": "ClaimRecord",
    "evidence-link.json": "EvidenceLink",
    "audit-run.json": "AuditRun",
    "adapter-capability-profile.json": "AdapterCapabilityProfile",
}

SENSITIVITY_ORDER = {
    "public": 0,
    "internal": 1,
    "sensitive": 2,
    "restricted": 3,
}

REDACTION_ORDER = {
    "none": 0,
    "partial": 1,
    "fully_redacted": 2,
    "withheld": 3,
}

RELIABLE_EVIDENCE_CONFIDENCE = 0.75
REFERENCE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://.+")
PROMPT_PATCH_MUTABLE_FIELDS = {
    "name",
    "intent",
    "instruction",
    "required_context_types",
    "output_contract",
    "model_preferences",
    "known_failure_modes",
    "anti_patterns",
    "quality_metrics",
    "sensitivity",
    "redaction_state",
    "secret_refs",
    "exportable",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _utc_compact_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _content_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _semantic_ref(object_kind: str, object_id: str) -> str:
    return f"{KIND_TO_SCHEME[object_kind]}://{object_id}"


def _storage_ref(object_kind: str, object_id: str) -> str:
    return f"vault://objects/{object_kind}/{object_id}.json"


def _text_body(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def _query_tokens(query: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", query.lower())


def _estimate_tokens(parts: Iterable[str]) -> int:
    total_chars = sum(len(part) for part in parts if part)
    return max(1, total_chars // 4) if total_chars else 0


def _session_turn_count(payload: dict[str, Any]) -> int:
    explicit = payload.get("turn_count")
    if explicit not in (None, ""):
        return max(0, int(explicit))
    signal_summary = payload.get("signal_summary") if isinstance(payload.get("signal_summary"), dict) else {}
    followup_count = signal_summary.get("followup_count", 0)
    return max(0, int(followup_count) + 1)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _string_list(values: Iterable[Any] | None) -> list[str]:
    if values is None:
        return []
    return _unique(str(value).strip() for value in values if str(value).strip())


def _payload_sensitivity(payloads: Iterable[dict[str, Any]]) -> str:
    best = "public"
    best_rank = -1
    for payload in payloads:
        sensitivity = str(payload.get("sensitivity", "public"))
        rank = SENSITIVITY_ORDER.get(sensitivity, -1)
        if rank > best_rank:
            best = sensitivity
            best_rank = rank
    return best if best_rank >= 0 else "internal"


def _payload_redaction_state(payloads: Iterable[dict[str, Any]]) -> str:
    best = "none"
    best_rank = -1
    for payload in payloads:
        state = str(payload.get("redaction_state", "none"))
        rank = REDACTION_ORDER.get(state, -1)
        if rank > best_rank:
            best = state
            best_rank = rank
    return best if best_rank >= 0 else "none"


@dataclass(frozen=True)
class StoredObjectEnvelope:
    object_id: str
    object_kind: str
    schema_family: str
    semantic_ref: str
    storage_ref: str
    content_sha256: str
    stored_at: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "object_kind": self.object_kind,
            "schema_family": self.schema_family,
            "semantic_ref": self.semantic_ref,
            "storage_ref": self.storage_ref,
            "content_sha256": self.content_sha256,
            "stored_at": self.stored_at,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class SearchHit:
    object_id: str
    semantic_ref: str
    storage_ref: str
    score: float
    payload: dict[str, Any]


@dataclass(frozen=True)
class ResolvedPrompt:
    object_id: str
    semantic_ref: str
    storage_ref: str
    payload: dict[str, Any]
    instruction: str
    required_context_types: list[str]


@dataclass(frozen=True)
class ContextItemInput:
    ref: str
    content: str


@dataclass(frozen=True)
class ContextBuildRequest:
    scope_kind: str
    scope_value: str
    task_label: str
    prompt_id: str | None = None
    session_id: str | None = None
    memory_query: str = ""
    knowledge_query: str = ""
    max_memories: int = 5
    max_knowledge: int = 4
    max_recent_turns: int = 6
    token_budget: int = 12000
    bundle_id: str | None = None
    active_task_state: tuple[ContextItemInput, ...] = ()
    recent_conversation: tuple[ContextItemInput, ...] = ()


class CtxVault:
    def __init__(self, layout: VaultLayout):
        self.layout = layout

    def initialize(self) -> VaultLayout:
        self.layout.vault_root.mkdir(parents=True, exist_ok=True)
        self.layout.objects_dir.mkdir(parents=True, exist_ok=True)
        self.layout.indexes_dir.mkdir(parents=True, exist_ok=True)
        self.layout.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.layout.exports_dir.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            self._create_schema(conn)
        return self.layout

    def rebuild_indexes(self) -> dict[str, Any]:
        self.layout.vault_root.mkdir(parents=True, exist_ok=True)
        self.layout.objects_dir.mkdir(parents=True, exist_ok=True)
        self.layout.indexes_dir.mkdir(parents=True, exist_ok=True)
        self.layout.reviews_dir.mkdir(parents=True, exist_ok=True)
        self.layout.exports_dir.mkdir(parents=True, exist_ok=True)
        if self.layout.sqlite_path.exists():
            self.layout.sqlite_path.unlink()

        indexed_object_count = 0
        object_kinds: dict[str, int] = {}
        with self._connection() as conn:
            self._create_schema(conn)
            for object_path in sorted(self.layout.objects_dir.rglob("*.json")):
                if not object_path.is_file():
                    continue
                envelope = self._load_stored_envelope(object_path)
                self._upsert_object_projection(conn, envelope, object_path)
                indexed_object_count += 1
                object_kinds[envelope.object_kind] = object_kinds.get(envelope.object_kind, 0) + 1
            conn.commit()

        return {
            "sqlite_path": str(self.layout.sqlite_path),
            "indexed_object_count": indexed_object_count,
            "object_kinds": object_kinds,
            "rebuilt_at": _utc_now(),
        }

    def store_core_object(self, model_name: str, payload: dict[str, Any]) -> StoredObjectEnvelope:
        if model_name not in CORE_MODEL_TO_KIND:
            raise KeyError(f"unsupported core model {model_name}")
        object_id = str(payload.get("id", "")).strip()
        if not object_id:
            raise ValueError("payload must include a non-empty id")

        self.initialize()
        object_kind = CORE_MODEL_TO_KIND[model_name]
        envelope = StoredObjectEnvelope(
            object_id=object_id,
            object_kind=object_kind,
            schema_family="core",
            semantic_ref=_semantic_ref(object_kind, object_id),
            storage_ref=_storage_ref(object_kind, object_id),
            content_sha256=_content_hash(payload),
            stored_at=_utc_now(),
            payload=payload,
        )

        object_path = self._object_path(object_kind, object_id)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_text(json.dumps(envelope.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n")

        with self._connection() as conn:
            self._upsert_object_projection(conn, envelope, object_path)

        return envelope

    def import_core_fixture(self, fixture_path: Path, model_name: str | None = None) -> StoredObjectEnvelope:
        inferred_model = model_name or CORE_FIXTURE_MODELS.get(fixture_path.name)
        if inferred_model is None:
            raise KeyError(f"no core fixture model mapping for {fixture_path.name}")
        return self.store_core_object(inferred_model, json.loads(fixture_path.read_text()))

    def import_core_fixtures(self, fixtures_dir: Path) -> list[StoredObjectEnvelope]:
        envelopes: list[StoredObjectEnvelope] = []
        for fixture_name in sorted(CORE_FIXTURE_MODELS):
            fixture_path = fixtures_dir / fixture_name
            if fixture_path.exists():
                envelopes.append(self.import_core_fixture(fixture_path, CORE_FIXTURE_MODELS[fixture_name]))
        return envelopes

    def store_governance_object(self, model_name: str, payload: dict[str, Any]) -> StoredObjectEnvelope:
        if model_name not in GOVERNANCE_MODEL_TO_KIND:
            raise KeyError(f"unsupported governance model {model_name}")
        object_id = str(payload.get("id", "")).strip()
        if not object_id:
            raise ValueError("payload must include a non-empty id")

        self.initialize()
        object_kind = GOVERNANCE_MODEL_TO_KIND[model_name]
        envelope = StoredObjectEnvelope(
            object_id=object_id,
            object_kind=object_kind,
            schema_family="governance",
            semantic_ref=_semantic_ref(object_kind, object_id),
            storage_ref=_storage_ref(object_kind, object_id),
            content_sha256=_content_hash(payload),
            stored_at=_utc_now(),
            payload=payload,
        )

        object_path = self._object_path(object_kind, object_id)
        object_path.parent.mkdir(parents=True, exist_ok=True)
        object_path.write_text(json.dumps(envelope.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n")

        with self._connection() as conn:
            self._upsert_object_projection(conn, envelope, object_path)

        return envelope

    def import_governance_fixture(self, fixture_path: Path, model_name: str | None = None) -> StoredObjectEnvelope:
        inferred_model = model_name or GOVERNANCE_FIXTURE_MODELS.get(fixture_path.name)
        if inferred_model is None:
            raise KeyError(f"no governance fixture model mapping for {fixture_path.name}")
        return self.store_governance_object(inferred_model, json.loads(fixture_path.read_text()))

    def capture_claim(self, payload: dict[str, Any]) -> StoredObjectEnvelope:
        return self.store_governance_object("ClaimRecord", payload)

    def link_evidence(self, payload: dict[str, Any]) -> StoredObjectEnvelope:
        return self.store_governance_object("EvidenceLink", payload)

    def resolve_prompt(self, prompt_id: str) -> ResolvedPrompt:
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT object_id, semantic_ref, storage_ref, storage_path, instruction
                FROM prompt_assets
                WHERE object_id = ?
                """,
                (prompt_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown prompt asset {prompt_id}")
            payload = self._load_payload(Path(str(row["storage_path"])))
            return ResolvedPrompt(
                object_id=str(row["object_id"]),
                semantic_ref=str(row["semantic_ref"]),
                storage_ref=str(row["storage_ref"]),
                payload=payload,
                instruction=str(row["instruction"]),
                required_context_types=list(payload.get("required_context_types", [])),
            )

    def list_prompts(
        self,
        *,
        scope: tuple[str, str] | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        with self._connection() as conn:
            sql = [
                """
                SELECT
                  object_id,
                  semantic_ref,
                  storage_ref,
                  storage_path
                FROM prompt_assets
                WHERE status = 'active'
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            sql.append(
                """
                ORDER BY
                  updated_at DESC,
                  object_id ASC
                LIMIT ?
                """
            )
            params.append(limit)
            return [
                self._prompt_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]

    def list_memory_candidates(
        self,
        *,
        scope: tuple[str, str] | None = None,
        proposal_state: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        with self._connection() as conn:
            sql = [
                """
                SELECT
                  object_id,
                  semantic_ref,
                  storage_ref,
                  storage_path,
                  confidence
                FROM memory_candidates
                WHERE 1 = 1
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            if proposal_state is not None:
                sql.append("AND proposal_state = ?")
                params.append(proposal_state)
            sql.append(
                """
                ORDER BY
                  created_at DESC,
                  confidence DESC,
                  object_id ASC
                LIMIT ?
                """
            )
            params.append(limit)
            return [
                self._memory_candidate_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]

    def list_prompt_patches(
        self,
        *,
        scope: tuple[str, str] | None = None,
        proposal_state: str | None = None,
        prompt_asset_id: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        with self._connection() as conn:
            sql = [
                """
                SELECT
                  object_id,
                  semantic_ref,
                  storage_ref,
                  storage_path,
                  confidence
                FROM prompt_patches
                WHERE 1 = 1
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            if proposal_state is not None:
                sql.append("AND proposal_state = ?")
                params.append(proposal_state)
            if prompt_asset_id is not None:
                sql.append("AND prompt_asset_id = ?")
                params.append(prompt_asset_id)
            sql.append(
                """
                ORDER BY
                  created_at DESC,
                  confidence DESC,
                  object_id ASC
                LIMIT ?
                """
            )
            params.append(limit)
            return [
                self._prompt_patch_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]

    def preview_prompt_patch(self, patch_id: str) -> dict[str, Any]:
        self.initialize()
        patch_row_data, prompt_row_data, patch_payload, prompt_payload = self._prompt_patch_context(patch_id)
        prompt_preview = self._prompt_payload_preview_from_patch(prompt_payload, patch_payload)
        changed_fields = sorted(str(field) for field in patch_payload.get("changes", {}))
        return {
            "patch": deepcopy(patch_payload),
            "patch_ref": patch_row_data["semantic_ref"],
            "patch_storage_ref": patch_row_data["storage_ref"],
            "prompt_ref": prompt_row_data["semantic_ref"],
            "prompt_storage_ref": prompt_row_data["storage_ref"],
            "prompt_content_sha256": prompt_row_data["content_sha256"],
            "prompt_preview": prompt_preview,
            "preview_content_sha256": _content_hash(prompt_preview),
            "changed_fields": changed_fields,
            "source_refs": list(patch_payload.get("source_refs", [])),
        }

    def list_sessions(
        self,
        *,
        scope: tuple[str, str] | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        return self.search_sessions("", scope=scope, limit=limit)

    def list_episodes(
        self,
        *,
        scope: tuple[str, str] | None = None,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        with self._connection() as conn:
            sql = [
                """
                SELECT object_id, semantic_ref, storage_ref, storage_path
                FROM object_index
                WHERE object_kind = 'episode'
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            sql.append("ORDER BY stored_at ASC, object_id ASC")
            hits = [
                self._episode_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]
        if session_id is not None:
            hits = [hit for hit in hits if str(hit.payload.get("session_id") or "") == session_id]
        hits.sort(key=self._episode_sort_key)
        return hits[:limit]

    def search_sessions(
        self,
        query: str,
        *,
        scope: tuple[str, str] | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        tokens = _query_tokens(query)
        with self._connection() as conn:
            self._sync_session_projection(conn)
            sql = [
                """
                SELECT
                  object_id,
                  semantic_ref,
                  storage_ref,
                  storage_path,
                  client,
                  source_app,
                  source_surface,
                  source_format,
                  capture_method,
                  title,
                  task_label,
                  status,
                  started_at,
                  ended_at,
                  turn_count
                FROM sessions
                WHERE 1 = 1
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            for token in tokens:
                sql.append(
                    """
                    AND (
                      LOWER(object_id) LIKE ?
                      OR LOWER(client) LIKE ?
                      OR LOWER(COALESCE(source_app, '')) LIKE ?
                      OR LOWER(COALESCE(source_surface, '')) LIKE ?
                      OR LOWER(COALESCE(source_format, '')) LIKE ?
                      OR LOWER(COALESCE(capture_method, '')) LIKE ?
                      OR LOWER(title) LIKE ?
                      OR LOWER(task_label) LIKE ?
                    )
                    """
                )
                like = f"%{token}%"
                params.extend([like, like, like, like, like, like, like, like])
            sql.append(
                """
                ORDER BY
                  COALESCE(ended_at, started_at) DESC,
                  started_at DESC,
                  object_id ASC
                LIMIT ?
                """
            )
            params.append(limit)
            return [
                self._session_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]

    def related_sessions(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        self.initialize()
        if limit < 1:
            raise ValueError("related session limit must be at least 1")

        anchor_session = self._load_object_payload("session", session_id)
        scope = self._scope_from_payload(anchor_session)
        session_hits = self.list_sessions(scope=scope, limit=200)
        episodes_by_session = self._episodes_by_session(scope=scope)
        profiles = {
            hit.object_id: self._session_profile_from_payload(
                hit.payload,
                scope=scope,
                episode_payloads=episodes_by_session.get(hit.object_id, []),
                include_turns=hit.object_id == session_id,
            )
            for hit in session_hits
        }
        anchor_profile = profiles.get(session_id) or self._session_profile_from_payload(
            anchor_session,
            scope=scope,
            episode_payloads=episodes_by_session.get(session_id, []),
            include_turns=True,
        )

        related: list[dict[str, Any]] = []
        for hit in session_hits:
            if hit.object_id == session_id:
                continue
            candidate_profile = profiles[hit.object_id]
            comparison = compare_session_profiles(anchor_profile, candidate_profile)
            if comparison["score"] <= 0:
                continue
            related.append(
                {
                    "session": deepcopy(hit.payload),
                    "profile": candidate_profile,
                    **comparison,
                }
            )

        related.sort(
            key=lambda item: (
                -float(item["score"]),
                -len(item["shared_terms"]),
                str((item["session"] or {}).get("ended_at") or (item["session"] or {}).get("started_at") or ""),
                str((item["session"] or {}).get("id") or ""),
            )
        )
        return {
            "anchor_session": deepcopy(anchor_session),
            "anchor_profile": anchor_profile,
            "summary": {
                "candidate_count": max(0, len(session_hits) - 1),
                "returned_count": min(limit, len(related)),
            },
            "related_sessions": related[:limit],
        }

    def session_aggregate_preview(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        related = self.related_sessions(session_id, limit=limit)
        aggregate = build_session_aggregate_preview(
            related["anchor_profile"],
            [item["profile"] for item in related["related_sessions"]],
        )
        return {
            **related,
            "aggregate": aggregate,
        }

    def list_workstreams(
        self,
        *,
        scope: tuple[str, str] | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        with self._connection() as conn:
            sql = [
                """
                SELECT
                  object_id,
                  semantic_ref,
                  storage_ref,
                  storage_path
                FROM workstreams
                WHERE 1 = 1
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            if status is not None:
                sql.append("AND status = ?")
                params.append(status)
            sql.append(
                """
                ORDER BY
                  updated_at DESC,
                  object_id ASC
                LIMIT ?
                """
            )
            params.append(limit)
            return [
                self._workstream_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]

    def list_workstream_candidates(
        self,
        *,
        scope: tuple[str, str] | None = None,
        proposal_state: str | None = None,
        limit: int = 20,
    ) -> list[SearchHit]:
        self.initialize()
        with self._connection() as conn:
            sql = [
                """
                SELECT
                  object_id,
                  semantic_ref,
                  storage_ref,
                  storage_path,
                  confidence
                FROM workstream_candidates
                WHERE 1 = 1
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            if proposal_state is not None:
                sql.append("AND proposal_state = ?")
                params.append(proposal_state)
            sql.append(
                """
                ORDER BY
                  created_at DESC,
                  confidence DESC,
                  object_id ASC
                LIMIT ?
                """
            )
            params.append(limit)
            return [
                self._workstream_candidate_hit_from_row(dict(row))
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]

    def workstream_preview(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        aggregate_payload = self.session_aggregate_preview(session_id, limit=limit)
        scope = self._scope_from_payload(aggregate_payload["anchor_session"])
        episodes_by_session = self._episodes_by_session(scope=scope)
        session_ids = [
            str(aggregate_payload["anchor_session"]["id"]),
            *[str(item["session"]["id"]) for item in aggregate_payload.get("related_sessions", [])],
        ]
        episode_payloads = [
            deepcopy(payload)
            for session_key in session_ids
            for payload in episodes_by_session.get(session_key, [])
        ]
        knowledge_refs = self._knowledge_refs_for_sessions(
            [aggregate_payload["anchor_session"], *[item["session"] for item in aggregate_payload.get("related_sessions", [])]],
            episode_payloads=episode_payloads,
        )
        return build_workstream_preview(
            aggregate_payload,
            episode_payloads=episode_payloads,
            knowledge_refs=knowledge_refs,
        )

    def workstream_intelligence(
        self,
        workstream_id: str,
        *,
        limit: int = 6,
    ) -> dict[str, Any]:
        workstream_payload = self._load_object_payload("workstream", workstream_id)
        linked_knowledge: list[dict[str, Any]] = []
        linked_ids: set[str] = set()
        for ref in list(workstream_payload.get("knowledge_refs") or []):
            knowledge_id = str(ref).replace("knowledge://", "", 1).strip()
            if not knowledge_id or knowledge_id in linked_ids:
                continue
            payload = self._optional_object_payload("knowledge_artifact", knowledge_id)
            if payload is None:
                continue
            linked_ids.add(knowledge_id)
            linked_knowledge.append(deepcopy(payload))

        scope = self._scope_from_payload(workstream_payload)
        knowledge_payloads = linked_knowledge
        query_terms = [
            str(term).strip()
            for term in list(workstream_payload.get("recurring_terms") or [])[:4]
            if str(term).strip()
        ]
        if not query_terms:
            query_terms = _query_tokens(" ".join(str(label).strip() for label in workstream_payload.get("task_labels", []) if str(label).strip()))[:4]
        if not query_terms:
            query_terms = _query_tokens(str(workstream_payload.get("title") or ""))[:4]
        query = " ".join(_unique(query_terms)).strip()
        if not knowledge_payloads and scope is not None and query:
            knowledge_payloads = [
                deepcopy(hit.payload)
                for hit in self.search_knowledge(query, scope=scope, limit=limit)
            ]

        memory_payloads: list[dict[str, Any]] = []
        if scope is not None:
            memory_payloads = [
                deepcopy(hit.payload)
                for hit in self.search_memories(query, scope=scope, limit=limit)
            ]

        return build_workstream_intelligence_report(
            workstream_payload,
            knowledge_payloads=knowledge_payloads,
            memory_payloads=memory_payloads,
        )

    def create_workstream_candidate(
        self,
        session_id: str,
        *,
        limit: int = 5,
        candidate_id: str | None = None,
        candidate_for: str | None = None,
        title: str | None = None,
        summary: str | None = None,
        rationale: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        preview = self.workstream_preview(session_id, limit=limit)
        candidate_payload = build_workstream_candidate_payload(
            preview["suggested_workstream"],
            candidate_id=candidate_id,
            candidate_for=candidate_for,
            title=title,
            summary=summary,
            rationale=rationale,
            notes=notes,
        )
        candidate_envelope = self.store_core_object("WorkstreamCandidate", candidate_payload)
        return {
            **preview,
            "candidate": candidate_envelope.payload,
            "candidate_ref": candidate_envelope.semantic_ref,
        }

    def review_workstream_candidate(
        self,
        candidate_id: str,
        *,
        decision: str,
        reviewer: str = "human_review",
        notes: str | None = None,
        workstream_id: str | None = None,
        policy_payload: dict[str, Any] | None = None,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        if not reviewer.strip():
            raise ValueError("reviewer must be a non-empty string")

        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT
                  wc.object_id,
                  wc.semantic_ref,
                  wc.storage_ref,
                  wc.storage_path,
                  wc.proposal_state,
                  wc.candidate_for,
                  oi.content_sha256
                FROM workstream_candidates AS wc
                JOIN object_index AS oi ON oi.object_id = wc.object_id
                WHERE wc.object_id = ?
                """,
                (candidate_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown workstream candidate {candidate_id}")
            candidate_row = dict(row)

        candidate_payload = self._load_payload(Path(str(candidate_row["storage_path"])))
        if candidate_payload.get("proposal_state") != "proposed":
            raise ValueError(f"workstream candidate {candidate_id} is not in proposed state")

        policy_decision = None
        workstream_envelope: StoredObjectEnvelope | None = None
        if decision == "approved":
            if policy_payload is None:
                raise ValueError("policy payload is required to approve a workstream candidate")
            policy_decision = CtxVaultPolicy(policy_payload).evaluate_operation(
                operation="workstream_promotion",
                sensitivity=str(candidate_payload.get("sensitivity", "internal")),
                backup_receipt=backup_receipt,
            )
            if policy_decision.decision not in {"allow", "review_required"}:
                reasons = "; ".join(policy_decision.reasons)
                raise ValueError(f"workstream promotion blocked: {policy_decision.decision} ({reasons})")
            target_id = workstream_id or str(candidate_payload.get("candidate_for") or "").strip() or None
            existing_workstream = None
            if target_id is not None:
                existing_workstream = self._optional_object_payload("workstream", target_id)
            workstream_envelope = self.store_core_object(
                "Workstream",
                build_workstream_payload(
                    candidate_payload,
                    workstream_id=target_id,
                    existing_workstream=existing_workstream,
                ),
            )

        candidate_payload["proposal_state"] = "merged" if decision == "approved" else "rejected"
        candidate_envelope = self.store_core_object("WorkstreamCandidate", candidate_payload)
        receipt = self._write_workstream_candidate_review_receipt(
            candidate_row=candidate_row,
            candidate_envelope=candidate_envelope,
            decision=decision,
            reviewer=reviewer,
            notes=notes,
            workstream_envelope=workstream_envelope,
            policy_decision=policy_decision.to_dict() if policy_decision is not None else None,
        )
        return {
            "candidate": candidate_envelope.payload,
            "candidate_ref": candidate_envelope.semantic_ref,
            "workstream": workstream_envelope.payload if workstream_envelope is not None else None,
            "workstream_ref": workstream_envelope.semantic_ref if workstream_envelope is not None else None,
            "review_receipt": receipt,
            "review_receipt_path": receipt["path"],
            "policy_decision": policy_decision.to_dict() if policy_decision is not None else None,
        }

    def derive_episodes(self, session_id: str) -> dict[str, Any]:
        session_payload = self._load_object_payload("session", session_id)
        scope = self._scope_from_payload(session_payload)
        existing = self.list_episodes(scope=scope, session_id=session_id, limit=max(1, int(session_payload.get("turn_count") or 1000)))
        if existing:
            return {
                "session": session_payload,
                "episodes": [deepcopy(hit.payload) for hit in existing],
                "reused_existing": True,
            }

        turn_limit = max(1, int(session_payload.get("turn_count") or 1))
        turn_hits = self._recent_turn_hits(scope=scope, limit=turn_limit, session_id=session_id)
        episode_payloads = derive_episode_payloads(session_payload, [deepcopy(hit.payload) for hit in turn_hits])
        for payload in episode_payloads:
            self.store_core_object("Episode", payload)

        updated_session = deepcopy(session_payload)
        updated_session["derived_asset_refs"] = _string_list(
            [
                *updated_session.get("derived_asset_refs", []),
                *[f"episode://{payload['id']}" for payload in episode_payloads],
            ]
        )
        self.store_core_object("Session", updated_session)
        return {
            "session": updated_session,
            "episodes": episode_payloads,
            "reused_existing": False,
        }

    def synthesize_episode(
        self,
        episode_id: str,
        *,
        knowledge_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        episode_payload = self._load_object_payload("episode", episode_id)
        session_payload = self._load_object_payload("session", str(episode_payload["session_id"]))
        scope = self._scope_from_payload(episode_payload) or self._scope_from_payload(session_payload)
        turn_limit = max(1, int(session_payload.get("turn_count") or 1))
        turn_hits = self._recent_turn_hits(scope=scope, limit=turn_limit, session_id=str(session_payload["id"]))
        ordered_turns = [deepcopy(hit.payload) for hit in turn_hits]
        start_index = max(0, int(episode_payload.get("start_turn_index") or 0))
        end_index = max(start_index, int(episode_payload.get("end_turn_index") or start_index))
        episode_turns = ordered_turns[start_index : end_index + 1]
        if not episode_turns:
            raise ValueError(f"episode {episode_id} does not map to any stored turns")

        knowledge_payload = build_episode_synthesis_payload(
            session_payload,
            episode_payload,
            episode_turns,
            knowledge_id=knowledge_id,
            title=title,
        )
        self.store_core_object("KnowledgeArtifact", knowledge_payload)

        knowledge_ref = f"knowledge://{knowledge_payload['id']}"
        updated_episode = deepcopy(episode_payload)
        updated_episode["derived_refs"] = _string_list([*updated_episode.get("derived_refs", []), knowledge_ref])
        updated_episode["updated_at"] = _utc_now()
        self.store_core_object("Episode", updated_episode)

        updated_session = deepcopy(session_payload)
        updated_session["derived_asset_refs"] = _string_list(
            [
                *updated_session.get("derived_asset_refs", []),
                f"episode://{updated_episode['id']}",
                knowledge_ref,
            ]
        )
        self.store_core_object("Session", updated_session)
        return {
            "episode": updated_episode,
            "knowledge_artifact": knowledge_payload,
        }

    def export_knowledge_note(
        self,
        knowledge_id: str,
        *,
        output_path: Path,
        canonical_target: str,
        privacy: str | None = None,
        status: str = "draft",
        note_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        knowledge_payload = self._load_object_payload("knowledge_artifact", knowledge_id)
        return render_manual_note(
            knowledge_payload,
            output_path=output_path,
            canonical_target=canonical_target,
            privacy=privacy,
            status=status,
            note_id=note_id,
            title=title,
        )

    def search_memories(
        self,
        query: str,
        *,
        scope: tuple[str, str] | None = None,
        limit: int = 5,
        pinned_only: bool = False,
    ) -> list[SearchHit]:
        self.initialize()
        tokens = _query_tokens(query)
        with self._connection() as conn:
            if tokens and self._has_table(conn, "memory_fts"):
                sql = [
                    """
                    SELECT
                      m.object_id,
                      m.semantic_ref,
                      m.storage_ref,
                      m.storage_path,
                      m.confidence,
                      m.pinned,
                      m.retrieval_priority,
                      bm25(memory_fts) AS rank
                    FROM memory_fts
                    JOIN memories AS m ON memory_fts.object_id = m.object_id
                    WHERE memory_fts MATCH ?
                      AND m.status = 'active'
                      AND m.approval_state = 'approved'
                    """
                ]
                params: list[Any] = [" ".join(tokens)]
                if pinned_only:
                    sql.append("AND m.pinned = 1")
                if scope is not None:
                    sql.append("AND m.scope_kind = ? AND m.scope_value = ?")
                    params.extend(scope)
                sql.append(
                    """
                    ORDER BY
                      m.pinned DESC,
                      m.retrieval_priority DESC,
                      rank ASC,
                      m.confidence DESC,
                      m.updated_at DESC,
                      m.object_id ASC
                    LIMIT ?
                    """
                )
                params.append(limit)
                return [
                    self._memory_hit_from_row(dict(row))
                    for row in conn.execute("\n".join(sql), params).fetchall()
                ]
            else:
                sql = [
                    """
                    SELECT
                      object_id,
                      semantic_ref,
                      storage_ref,
                      storage_path,
                      confidence,
                      pinned,
                      retrieval_priority
                    FROM memories
                    WHERE status = 'active'
                      AND approval_state = 'approved'
                    """
                ]
                params = []
                if pinned_only:
                    sql.append("AND pinned = 1")
                if scope is not None:
                    sql.append("AND scope_kind = ? AND scope_value = ?")
                    params.extend(scope)
                for token in tokens:
                    sql.append("AND LOWER(statement) LIKE ?")
                    params.append(f"%{token}%")
                sql.append(
                    """
                    ORDER BY
                      pinned DESC,
                      retrieval_priority DESC,
                      confidence DESC,
                      updated_at DESC,
                      object_id ASC
                    LIMIT ?
                    """
                )
                params.append(limit)
                return [
                    self._memory_hit_from_row(dict(row))
                    for row in conn.execute("\n".join(sql), params).fetchall()
                ]

    def search_knowledge(
        self,
        query: str,
        *,
        scope: tuple[str, str] | None = None,
        limit: int = 4,
    ) -> list[SearchHit]:
        self.initialize()
        tokens = _query_tokens(query)
        with self._connection() as conn:
            if tokens and self._has_table(conn, "knowledge_fts"):
                sql = [
                    """
                    SELECT
                      k.object_id,
                      k.semantic_ref,
                      k.storage_ref,
                      k.storage_path,
                      bm25(knowledge_fts) AS rank
                    FROM knowledge_fts
                    JOIN knowledge_artifacts AS k ON knowledge_fts.object_id = k.object_id
                    WHERE knowledge_fts MATCH ?
                      AND k.status = 'active'
                    """
                ]
                params: list[Any] = [" ".join(tokens)]
                if scope is not None:
                    sql.append("AND k.scope_kind = ? AND k.scope_value = ?")
                    params.extend(scope)
                sql.append(
                    """
                    ORDER BY
                      rank ASC,
                      k.updated_at DESC,
                      k.object_id ASC
                    LIMIT ?
                    """
                )
                params.append(limit)
                return [
                    self._knowledge_hit_from_row(dict(row))
                    for row in conn.execute("\n".join(sql), params).fetchall()
                ]
            else:
                sql = [
                    """
                    SELECT object_id, semantic_ref, storage_ref, storage_path
                    FROM knowledge_artifacts
                    WHERE status = 'active'
                    """
                ]
                params = []
                if scope is not None:
                    sql.append("AND scope_kind = ? AND scope_value = ?")
                    params.extend(scope)
                for token in tokens:
                    sql.append("AND (LOWER(title) LIKE ? OR LOWER(body_text) LIKE ?)")
                    params.extend([f"%{token}%", f"%{token}%"])
                sql.append(
                    """
                    ORDER BY
                      updated_at DESC,
                      object_id ASC
                    LIMIT ?
                    """
                )
                params.append(limit)
                return [
                    self._knowledge_hit_from_row(dict(row))
                    for row in conn.execute("\n".join(sql), params).fetchall()
                ]

    def run_audit(
        self,
        *,
        scope_kind: str,
        scope_value: str,
        subject_ref: str,
        claim_refs: list[str] | None = None,
        audit_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        claims = self._load_claims(subject_ref=subject_ref, claim_refs=claim_refs)
        if not claims:
            raise KeyError(f"no claims found for subject {subject_ref}")

        claim_ids = [str(claim["id"]) for claim in claims]
        evidence_links = self._load_evidence_links(claim_ids)
        verdict, review_state, derived_notes = self._derive_audit_outcome(claims, evidence_links)

        payload = {
            "id": audit_id or f"audit_{_utc_compact_timestamp()}_{hashlib.sha256(subject_ref.encode('utf-8')).hexdigest()[:8]}",
            "scope": {
                "kind": scope_kind,
                "value": scope_value,
            },
            "subject_ref": subject_ref,
            "claim_refs": [f"claim://{claim_id}" for claim_id in claim_ids],
            "evidence_refs": _unique([str(link["evidence_ref"]) for link in evidence_links]),
            "verdict": verdict,
            "method": "deterministic_local_evidence",
            "review_state": review_state,
            "notes": "\n".join(part for part in [notes, derived_notes] if part),
            "created_at": _utc_now(),
        }
        self.store_governance_object("AuditRun", payload)
        return payload

    def review_audit(
        self,
        audit_id: str,
        *,
        decision: str,
        notes: str | None = None,
        override_verdict: str | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT storage_path
                FROM audit_runs
                WHERE object_id = ?
                """,
                (audit_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown audit run {audit_id}")
            payload = self._load_payload(Path(str(row["storage_path"])))
        payload["review_state"] = decision
        payload["method"] = "human_review"
        if override_verdict is not None:
            payload["verdict"] = override_verdict
        if notes:
            existing_notes = payload.get("notes")
            payload["notes"] = f"{existing_notes}\nHuman review: {notes}" if existing_notes else f"Human review: {notes}"

        self.store_governance_object("AuditRun", payload)
        return payload

    def review_memory_candidate(
        self,
        candidate_id: str,
        *,
        decision: str,
        reviewer: str = "human_review",
        notes: str | None = None,
        memory_id: str | None = None,
        policy_payload: dict[str, Any] | None = None,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        if not reviewer.strip():
            raise ValueError("reviewer must be a non-empty string")

        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT
                  mc.object_id,
                  mc.semantic_ref,
                  mc.storage_ref,
                  mc.storage_path,
                  mc.proposal_state,
                  oi.content_sha256
                FROM memory_candidates AS mc
                JOIN object_index AS oi ON oi.object_id = mc.object_id
                WHERE mc.object_id = ?
                """,
                (candidate_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown memory candidate {candidate_id}")
            candidate_row = dict(row)

        candidate_payload = self._load_payload(Path(str(candidate_row["storage_path"])))
        if candidate_payload.get("proposal_state") != "proposed":
            raise ValueError(f"memory candidate {candidate_id} is not in proposed state")

        policy_decision = None
        memory_envelope: StoredObjectEnvelope | None = None
        if decision == "approved":
            if policy_payload is None:
                raise ValueError("policy payload is required to approve a memory candidate")
            policy_decision = CtxVaultPolicy(policy_payload).evaluate_operation(
                operation="memory_promotion",
                sensitivity=str(candidate_payload.get("sensitivity", "internal")),
                backup_receipt=backup_receipt,
            )
            if policy_decision.decision not in {"allow", "review_required"}:
                reasons = "; ".join(policy_decision.reasons)
                raise ValueError(f"memory promotion blocked: {policy_decision.decision} ({reasons})")
            memory_envelope = self.store_core_object(
                "Memory",
                self._memory_payload_from_candidate(candidate_payload, memory_id=memory_id),
            )

        candidate_payload["proposal_state"] = "merged" if decision == "approved" else "rejected"
        candidate_envelope = self.store_core_object("MemoryCandidate", candidate_payload)
        receipt = self._write_memory_candidate_review_receipt(
            candidate_row=candidate_row,
            candidate_envelope=candidate_envelope,
            decision=decision,
            reviewer=reviewer,
            notes=notes,
            memory_envelope=memory_envelope,
            policy_decision=policy_decision.to_dict() if policy_decision is not None else None,
        )
        return {
            "candidate": candidate_envelope.payload,
            "candidate_ref": candidate_envelope.semantic_ref,
            "memory": memory_envelope.payload if memory_envelope is not None else None,
            "memory_ref": memory_envelope.semantic_ref if memory_envelope is not None else None,
            "review_receipt": receipt,
            "review_receipt_path": receipt["path"],
            "policy_decision": policy_decision.to_dict() if policy_decision is not None else None,
        }

    def review_prompt_patch(
        self,
        patch_id: str,
        *,
        decision: str,
        reviewer: str = "human_review",
        notes: str | None = None,
        policy_payload: dict[str, Any] | None = None,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        if not reviewer.strip():
            raise ValueError("reviewer must be a non-empty string")

        patch_row_data, prompt_row_data, patch_payload, prompt_payload = self._prompt_patch_context(patch_id)
        if patch_payload.get("proposal_state") != "proposed":
            raise ValueError(f"prompt patch {patch_id} is not in proposed state")

        policy_decision = None
        prompt_envelope: StoredObjectEnvelope | None = None
        eval_refs = self._prompt_eval_refs("prompt_patch", patch_id)
        if decision == "approved":
            if policy_payload is None:
                raise ValueError("policy payload is required to approve a prompt patch")
            policy_decision = CtxVaultPolicy(policy_payload).evaluate_operation(
                operation="prompt_patch_promotion",
                sensitivity=str(patch_payload.get("sensitivity", prompt_payload.get("sensitivity", "internal"))),
                backup_receipt=backup_receipt,
            )
            if policy_decision.decision not in {"allow", "review_required"}:
                reasons = "; ".join(policy_decision.reasons)
                raise ValueError(f"prompt patch promotion blocked: {policy_decision.decision} ({reasons})")
            if not self._prompt_has_passed_eval("prompt_patch", patch_id):
                raise ValueError("prompt patch promotion requires a passed prompt_patch eval before approval")
            prompt_envelope = self.store_core_object("PromptAsset", self._prompt_payload_from_patch(prompt_payload, patch_payload))

        patch_payload["proposal_state"] = "merged" if decision == "approved" else "rejected"
        patch_envelope = self.store_core_object("PromptPatch", patch_payload)
        receipt = self._write_prompt_patch_review_receipt(
            patch_row=patch_row_data,
            prompt_row=prompt_row_data,
            patch_envelope=patch_envelope,
            decision=decision,
            reviewer=reviewer,
            notes=notes,
            prompt_envelope=prompt_envelope,
            preview_content_sha256=_content_hash(self._prompt_payload_preview_from_patch(prompt_payload, patch_payload)),
            eval_refs=eval_refs,
            policy_decision=policy_decision.to_dict() if policy_decision is not None else None,
        )
        return {
            "patch": patch_envelope.payload,
            "patch_ref": patch_envelope.semantic_ref,
            "prompt": prompt_envelope.payload if prompt_envelope is not None else None,
            "prompt_ref": prompt_envelope.semantic_ref if prompt_envelope is not None else None,
            "review_receipt": receipt,
            "review_receipt_path": receipt["path"],
            "policy_decision": policy_decision.to_dict() if policy_decision is not None else None,
        }

    def run_prompt_eval(
        self,
        target_type: str,
        target_id: str,
        *,
        dataset_ref: str,
        assert_contains: list[str] | None = None,
        assert_not_contains: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.initialize()
        if target_type not in {"prompt_asset", "prompt_patch"}:
            raise ValueError("target_type must be prompt_asset or prompt_patch")
        if not REFERENCE_PATTERN.match(dataset_ref):
            raise ValueError("dataset_ref must be a reference like eval://suite/name")

        contains = _string_list(assert_contains)
        not_contains = _string_list(assert_not_contains)
        evaluated_prompt, target_ref, target_storage_ref = self._resolve_prompt_eval_target(target_type, target_id)
        metrics, result = self._evaluate_prompt_payload(
            evaluated_prompt,
            assert_contains=contains,
            assert_not_contains=not_contains,
        )
        created_at = _utc_now()
        eval_payload = {
            "id": f"eval_{target_type}_{target_id}_{_utc_compact_timestamp().lower()}",
            "target_type": target_type,
            "target_id": target_id,
            "dataset_ref": dataset_ref,
            "metrics": {
                **metrics,
                "target_ref": target_ref,
                "target_storage_ref": target_storage_ref,
            },
            "result": result,
            "notes": notes,
            "created_at": created_at,
        }
        eval_envelope = self.store_core_object("EvalRun", eval_payload)

        stored_prompt = evaluated_prompt
        if target_type == "prompt_asset" and result in {"passed", "failed"}:
            prompt_payload = deepcopy(evaluated_prompt)
            prompt_payload["eval_status"] = result
            prompt_payload["updated_at"] = created_at
            prompt_envelope = self.store_core_object("PromptAsset", prompt_payload)
            stored_prompt = prompt_envelope.payload
            target_ref = prompt_envelope.semantic_ref
            target_storage_ref = prompt_envelope.storage_ref

        return {
            "eval_run": eval_envelope.payload,
            "eval_ref": eval_envelope.semantic_ref,
            "target_ref": target_ref,
            "target_storage_ref": target_storage_ref,
            "evaluated_prompt": stored_prompt,
        }

    def build_context(self, request: ContextBuildRequest) -> dict[str, Any]:
        self.initialize()
        scope = (request.scope_kind, request.scope_value)

        resolved_prompt = self.resolve_prompt(request.prompt_id) if request.prompt_id else None
        default_query = request.memory_query or request.knowledge_query or request.task_label
        memory_query = request.memory_query or default_query
        knowledge_query = request.knowledge_query or default_query

        core_rule_hits = self.search_memories("", scope=scope, limit=3, pinned_only=True)
        memory_hits = self.search_memories(memory_query, scope=scope, limit=request.max_memories + len(core_rule_hits))
        knowledge_hits = self.search_knowledge(knowledge_query, scope=scope, limit=request.max_knowledge + 3)

        core_rule_ids = {hit.object_id for hit in core_rule_hits}
        relevant_memories = [hit for hit in memory_hits if hit.object_id not in core_rule_ids][: request.max_memories]

        project_context = self._project_profile_hits(scope=scope, limit=3)
        project_context_ids = {hit.object_id for hit in project_context}
        relevant_knowledge = [hit for hit in knowledge_hits if hit.object_id not in project_context_ids][: request.max_knowledge]

        if request.recent_conversation:
            recent_conversation_items = [
                {"ref": item.ref, "content": item.content}
                for item in request.recent_conversation
            ]
            recent_turn_hits: list[SearchHit] = []
        else:
            recent_turn_hits = self._recent_turn_hits(
                scope=scope,
                limit=request.max_recent_turns,
                session_id=request.session_id,
            )
            recent_conversation_items = [
                {"ref": hit.semantic_ref, "content": self._recent_turn_content(hit.payload)}
                for hit in recent_turn_hits
            ]

        all_payloads = [hit.payload for hit in core_rule_hits + relevant_memories + project_context + relevant_knowledge + recent_turn_hits]
        if resolved_prompt is not None:
            all_payloads.append(resolved_prompt.payload)

        sections = {
            "core_rules": [
                {"ref": hit.semantic_ref, "content": str(hit.payload.get("statement", ""))}
                for hit in core_rule_hits
            ],
            "project_context": [
                {"ref": hit.semantic_ref, "content": _text_body(hit.payload.get("body")) or str(hit.payload.get("title", ""))}
                for hit in project_context
            ],
            "active_task_state": [
                {"ref": item.ref, "content": item.content}
                for item in request.active_task_state
            ],
            "relevant_memories": [
                {"ref": hit.semantic_ref, "content": str(hit.payload.get("statement", ""))}
                for hit in relevant_memories
            ],
            "relevant_knowledge": [
                {"ref": hit.semantic_ref, "content": _text_body(hit.payload.get("body")) or str(hit.payload.get("title", ""))}
                for hit in relevant_knowledge
            ],
            "recent_conversation": recent_conversation_items,
            "source_pointers": _unique(
                [
                    resolved_prompt.storage_ref if resolved_prompt else "",
                    *[hit.storage_ref for hit in core_rule_hits],
                    *[hit.storage_ref for hit in relevant_memories],
                    *[hit.storage_ref for hit in project_context],
                    *[hit.storage_ref for hit in relevant_knowledge],
                    *[hit.storage_ref for hit in recent_turn_hits],
                    *[
                        ref
                        for payload in all_payloads
                        for ref in payload.get("source_refs", [])
                    ],
                ]
            ),
        }

        text_parts = [
            resolved_prompt.instruction if resolved_prompt else "",
            *[item["content"] for item in sections["core_rules"]],
            *[item["content"] for item in sections["project_context"]],
            *[item["content"] for item in sections["active_task_state"]],
            *[item["content"] for item in sections["relevant_memories"]],
            *[item["content"] for item in sections["relevant_knowledge"]],
            *[item["content"] for item in sections["recent_conversation"]],
        ]

        bundle_payload = {
            "id": request.bundle_id or self._bundle_id(request),
            "scope": {
                "kind": request.scope_kind,
                "value": request.scope_value,
            },
            "task_label": request.task_label,
            "sections": sections,
            "input_refs": _unique(
                [
                    resolved_prompt.semantic_ref if resolved_prompt else "",
                    *[hit.semantic_ref for hit in core_rule_hits],
                    *[hit.semantic_ref for hit in relevant_memories],
                    *[hit.semantic_ref for hit in project_context],
                    *[hit.semantic_ref for hit in relevant_knowledge],
                    *[hit.semantic_ref for hit in recent_turn_hits],
                ]
            ),
            "token_budget": request.token_budget,
            "token_estimate": _estimate_tokens(text_parts),
            "assembly_policy": {
                "policy_id": "bundle_policy_v1",
                "mode": "deterministic_core",
                "memory_query": memory_query,
                "knowledge_query": knowledge_query,
                "prompt_id": request.prompt_id,
                "session_id": request.session_id,
                "max_recent_turns": request.max_recent_turns,
            },
            "sensitivity": _payload_sensitivity(all_payloads),
            "redaction_state": _payload_redaction_state(all_payloads),
            "secret_refs": _unique(
                [
                    ref
                    for payload in all_payloads
                    for ref in payload.get("secret_refs", [])
                ]
            ),
            "exportable": all(bool(payload.get("exportable", False)) for payload in all_payloads) if all_payloads else True,
            "created_at": _utc_now(),
        }

        self.store_core_object("ContextBundle", bundle_payload)
        return bundle_payload

    def _recent_turn_hits(
        self,
        *,
        scope: tuple[str, str] | None,
        limit: int,
        session_id: str | None = None,
    ) -> list[SearchHit]:
        if limit <= 0:
            return []

        with self._connection() as conn:
            sql = [
                """
                SELECT object_id, semantic_ref, storage_ref, storage_path
                FROM object_index
                WHERE object_kind = 'turn'
                """
            ]
            params: list[Any] = []
            if scope is not None:
                sql.append("AND scope_kind = ? AND scope_value = ?")
                params.extend(scope)
            sql.append("ORDER BY stored_at DESC, object_id DESC")
            hits = [
                SearchHit(
                    object_id=str(row["object_id"]),
                    semantic_ref=str(row["semantic_ref"]),
                    storage_ref=str(row["storage_ref"]),
                    score=0.0,
                    payload=self._load_payload(Path(str(row["storage_path"]))),
                )
                for row in conn.execute("\n".join(sql), params).fetchall()
            ]
        hits.sort(key=self._recent_turn_sort_key)
        if not hits:
            if session_id:
                raise ValueError(f"session {session_id} did not contain stored turns in scope")
            return []

        if session_id:
            session_hits = [hit for hit in hits if str(hit.payload.get("session_id") or "") == session_id]
            if not session_hits:
                raise ValueError(f"session {session_id} did not contain stored turns in scope")
            return session_hits[-limit:]

        latest_session_id = str(hits[-1].payload.get("session_id") or "").strip()
        if latest_session_id:
            session_hits = [hit for hit in hits if str(hit.payload.get("session_id") or "") == latest_session_id]
            return session_hits[-limit:]
        return hits[-limit:]

    def _episodes_by_session(self, *, scope: tuple[str, str] | None) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for hit in self.list_episodes(scope=scope, limit=1000):
            session_id = str(hit.payload.get("session_id") or "").strip()
            if not session_id:
                continue
            grouped.setdefault(session_id, []).append(deepcopy(hit.payload))
        return grouped

    def _knowledge_refs_for_sessions(
        self,
        session_payloads: list[dict[str, Any]],
        *,
        episode_payloads: list[dict[str, Any]],
    ) -> list[str]:
        refs: list[str] = []
        for payload in session_payloads:
            refs.extend(
                str(ref).strip()
                for ref in payload.get("derived_asset_refs", [])
                if str(ref).strip().startswith("knowledge://")
            )
        for payload in episode_payloads:
            refs.extend(
                str(ref).strip()
                for ref in payload.get("derived_refs", [])
                if str(ref).strip().startswith("knowledge://")
            )
        return _unique(refs)

    def _session_profile_from_payload(
        self,
        session_payload: dict[str, Any],
        *,
        scope: tuple[str, str] | None,
        episode_payloads: list[dict[str, Any]],
        include_turns: bool,
    ) -> dict[str, Any]:
        turn_payloads: list[dict[str, Any]] = []
        if include_turns:
            turn_limit = max(1, int(session_payload.get("turn_count") or 1))
            turn_payloads = [
                deepcopy(hit.payload)
                for hit in self._recent_turn_hits(
                    scope=scope,
                    limit=turn_limit,
                    session_id=str(session_payload["id"]),
                )
            ]
        return build_session_profile(
            session_payload,
            turn_payloads=turn_payloads,
            episode_payloads=episode_payloads,
        )

    def _recent_turn_sort_key(self, hit: SearchHit) -> tuple[str, str, int, str]:
        payload = hit.payload
        return (
            str(payload.get("created_at") or ""),
            str(payload.get("session_id") or ""),
            int(payload.get("ordinal") or 0),
            hit.object_id,
        )

    def _recent_turn_content(self, payload: dict[str, Any]) -> str:
        role = str(payload.get("role") or "unknown").strip() or "unknown"
        content = str(payload.get("content") or "").strip()
        return f"{role}: {content}" if content else role

    def _bundle_id(self, request: ContextBuildRequest) -> str:
        seed = hashlib.sha256(
            "|".join(
                [
                    request.scope_kind,
                    request.scope_value,
                    request.task_label,
                    request.prompt_id or "",
                    request.session_id or "",
                    request.memory_query,
                    request.knowledge_query,
                ]
            ).encode("utf-8")
        ).hexdigest()[:8]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"bundle_{stamp}_{seed}"

    def _object_path(self, object_kind: str, object_id: str) -> Path:
        return self.layout.objects_dir / object_kind / f"{object_id}.json"

    def _connect(self) -> sqlite3.Connection:
        self.layout.indexes_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.layout.sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def _create_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS object_index (
              object_id TEXT PRIMARY KEY,
              object_kind TEXT NOT NULL,
              schema_family TEXT NOT NULL,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              status TEXT,
              content_sha256 TEXT NOT NULL,
              stored_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_assets (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              name TEXT NOT NULL,
              intent TEXT NOT NULL,
              status TEXT NOT NULL,
              instruction TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_patches (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              prompt_asset_id TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              proposal_state TEXT NOT NULL,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_candidates (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              type TEXT NOT NULL,
              proposal_state TEXT NOT NULL,
              candidate_for TEXT,
              statement TEXT NOT NULL,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memories (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              type TEXT NOT NULL,
              status TEXT NOT NULL,
              approval_state TEXT NOT NULL,
              statement TEXT NOT NULL,
              confidence REAL NOT NULL,
              pinned INTEGER NOT NULL DEFAULT 0,
              retrieval_priority REAL NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS memory_search_cache (
              object_id TEXT PRIMARY KEY,
              statement TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_artifacts (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              kind TEXT NOT NULL,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              body_text TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS knowledge_search_cache (
              object_id TEXT PRIMARY KEY,
              title TEXT NOT NULL,
              body_text TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              client TEXT NOT NULL,
              source_app TEXT,
              source_surface TEXT,
              source_format TEXT,
              capture_method TEXT,
              title TEXT NOT NULL,
              task_label TEXT NOT NULL,
              status TEXT NOT NULL,
              started_at TEXT NOT NULL,
              ended_at TEXT,
              turn_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS workstreams (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              title TEXT NOT NULL,
              status TEXT NOT NULL,
              approval_state TEXT NOT NULL,
              summary TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS workstream_candidates (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              title TEXT NOT NULL,
              proposal_state TEXT NOT NULL,
              candidate_for TEXT,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS context_bundles (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              task_label TEXT NOT NULL,
              token_budget INTEGER NOT NULL,
              token_estimate INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              subject_ref TEXT NOT NULL,
              claim_text TEXT NOT NULL,
              status TEXT NOT NULL,
              sensitivity TEXT NOT NULL,
              redaction_state TEXT NOT NULL,
              exportable INTEGER NOT NULL,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_links (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              claim_id TEXT NOT NULL,
              evidence_ref TEXT NOT NULL,
              relation TEXT NOT NULL,
              confidence REAL NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_runs (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              scope_kind TEXT,
              scope_value TEXT,
              subject_ref TEXT NOT NULL,
              verdict TEXT NOT NULL,
              method TEXT NOT NULL,
              review_state TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS eval_runs (
              object_id TEXT PRIMARY KEY,
              semantic_ref TEXT NOT NULL,
              storage_ref TEXT NOT NULL,
              storage_path TEXT NOT NULL,
              target_type TEXT NOT NULL,
              target_id TEXT NOT NULL,
              dataset_ref TEXT NOT NULL,
              result TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            """
        )
        try:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(object_id UNINDEXED, statement)")
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(object_id UNINDEXED, title, body_text)")
        except sqlite3.OperationalError:
            pass
        self._ensure_session_projection_schema(conn)
        conn.commit()

    def _has_table(self, conn: sqlite3.Connection, table_name: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _table_columns(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
        return {str(row["name"]) for row in rows}

    def _ensure_session_projection_schema(self, conn: sqlite3.Connection) -> None:
        if not self._has_table(conn, "sessions"):
            return
        columns = self._table_columns(conn, "sessions")
        if "source_app" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN source_app TEXT")
        if "source_surface" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN source_surface TEXT")
        if "source_format" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN source_format TEXT")
        if "capture_method" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN capture_method TEXT")

    def _sync_session_projection(self, conn: sqlite3.Connection) -> None:
        if not self._has_table(conn, "sessions"):
            return
        rows = conn.execute(
            """
            SELECT oi.storage_path
            FROM object_index AS oi
            LEFT JOIN sessions AS s ON s.object_id = oi.object_id
            WHERE oi.object_kind = 'session'
              AND (
                s.object_id IS NULL
                OR s.source_app IS NULL
                OR s.source_surface IS NULL
                OR s.source_format IS NULL
                OR s.capture_method IS NULL
              )
            ORDER BY oi.stored_at ASC, oi.object_id ASC
            """
        ).fetchall()
        for row in rows:
            storage_path = Path(str(row["storage_path"]))
            payload = self._load_payload(storage_path)
            envelope = StoredObjectEnvelope(
                object_id=str(payload["id"]),
                object_kind="session",
                schema_family="core",
                semantic_ref=_semantic_ref("session", str(payload["id"])),
                storage_ref=_storage_ref("session", str(payload["id"])),
                content_sha256=_content_hash(payload),
                stored_at=_utc_now(),
                payload=payload,
            )
            scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
            self._upsert_session(
                conn,
                envelope,
                storage_path,
                str(scope.get("kind")) if scope.get("kind") is not None else None,
                str(scope.get("value")) if scope.get("value") is not None else None,
            )
        if rows:
            conn.commit()

    def _upsert_object_projection(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
    ) -> None:
        payload = envelope.payload
        scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
        scope_kind = scope.get("kind")
        scope_value = scope.get("value")
        status = str(payload.get("status", ""))

        conn.execute(
            """
            INSERT INTO object_index (
              object_id, object_kind, schema_family, semantic_ref, storage_ref,
              storage_path, scope_kind, scope_value, status, content_sha256, stored_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              object_kind = excluded.object_kind,
              schema_family = excluded.schema_family,
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              status = excluded.status,
              content_sha256 = excluded.content_sha256,
              stored_at = excluded.stored_at
            """,
            (
                envelope.object_id,
                envelope.object_kind,
                envelope.schema_family,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                status,
                envelope.content_sha256,
                envelope.stored_at,
            ),
        )

        if envelope.object_kind == "prompt_asset":
            self._upsert_prompt(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "prompt_patch":
            self._upsert_prompt_patch(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "memory_candidate":
            self._upsert_memory_candidate(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "memory":
            self._upsert_memory(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "session":
            self._upsert_session(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "workstream":
            self._upsert_workstream(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "workstream_candidate":
            self._upsert_workstream_candidate(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "knowledge_artifact":
            self._upsert_knowledge(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "context_bundle":
            self._upsert_bundle(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "claim_record":
            self._upsert_claim(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "evidence_link":
            self._upsert_evidence_link(conn, envelope, object_path)
        elif envelope.object_kind == "audit_run":
            self._upsert_audit_run(conn, envelope, object_path, scope_kind, scope_value)
        elif envelope.object_kind == "eval_run":
            self._upsert_eval_run(conn, envelope, object_path)

        conn.commit()

    def _upsert_prompt(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO prompt_assets (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              name, intent, status, instruction, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              name = excluded.name,
              intent = excluded.intent,
              status = excluded.status,
              instruction = excluded.instruction,
              updated_at = excluded.updated_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["name"],
                payload["intent"],
                payload["status"],
                payload["instruction"],
                payload["updated_at"],
            ),
        )

    def _upsert_prompt_patch(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO prompt_patches (
              object_id, semantic_ref, storage_ref, storage_path, prompt_asset_id,
              scope_kind, scope_value, proposal_state, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              prompt_asset_id = excluded.prompt_asset_id,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              proposal_state = excluded.proposal_state,
              confidence = excluded.confidence,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                payload["prompt_asset_id"],
                scope_kind,
                scope_value,
                payload["proposal_state"],
                float(payload["confidence"]),
                payload["created_at"],
            ),
        )

    def _upsert_memory_candidate(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO memory_candidates (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              type, proposal_state, candidate_for, statement, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              type = excluded.type,
              proposal_state = excluded.proposal_state,
              candidate_for = excluded.candidate_for,
              statement = excluded.statement,
              confidence = excluded.confidence,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["type"],
                payload["proposal_state"],
                payload.get("candidate_for"),
                payload["statement"],
                float(payload["confidence"]),
                payload["created_at"],
            ),
        )

    def _upsert_memory(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        retrieval_policy = payload.get("retrieval_policy", {}) or {}
        pinned = 1 if bool(retrieval_policy.get("pinned", False)) else 0
        priority = float(retrieval_policy.get("priority", 0.0) or 0.0)

        conn.execute(
            """
            INSERT INTO memories (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              type, status, approval_state, statement, confidence, pinned,
              retrieval_priority, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              type = excluded.type,
              status = excluded.status,
              approval_state = excluded.approval_state,
              statement = excluded.statement,
              confidence = excluded.confidence,
              pinned = excluded.pinned,
              retrieval_priority = excluded.retrieval_priority,
              updated_at = excluded.updated_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["type"],
                payload["status"],
                payload["approval_state"],
                payload["statement"],
                float(payload["confidence"]),
                pinned,
                priority,
                payload["updated_at"],
            ),
        )
        conn.execute(
            """
            INSERT INTO memory_search_cache (object_id, statement)
            VALUES (?, ?)
            ON CONFLICT(object_id) DO UPDATE SET statement = excluded.statement
            """,
            (envelope.object_id, payload["statement"]),
        )
        if self._has_table(conn, "memory_fts"):
            conn.execute("DELETE FROM memory_fts WHERE object_id = ?", (envelope.object_id,))
            conn.execute(
                "INSERT INTO memory_fts (object_id, statement) VALUES (?, ?)",
                (envelope.object_id, payload["statement"]),
            )

    def _upsert_session(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO sessions (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              client, source_app, source_surface, source_format, capture_method,
              title, task_label, status, started_at, ended_at, turn_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              client = excluded.client,
              source_app = excluded.source_app,
              source_surface = excluded.source_surface,
              source_format = excluded.source_format,
              capture_method = excluded.capture_method,
              title = excluded.title,
              task_label = excluded.task_label,
              status = excluded.status,
              started_at = excluded.started_at,
              ended_at = excluded.ended_at,
              turn_count = excluded.turn_count
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                str(payload.get("client") or "unknown"),
                str(payload.get("source_app") or payload.get("client") or "unknown"),
                str(payload.get("source_surface") or "unknown"),
                str(payload.get("source_format") or "unknown"),
                str(payload.get("capture_method") or "unknown"),
                str(payload.get("title") or envelope.object_id),
                str(payload.get("task_label") or payload.get("title") or envelope.object_id),
                str(payload.get("status") or "active"),
                str(payload.get("started_at") or envelope.stored_at),
                payload.get("ended_at"),
                _session_turn_count(payload),
            ),
        )

    def _upsert_workstream(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO workstreams (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              title, status, approval_state, summary, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              title = excluded.title,
              status = excluded.status,
              approval_state = excluded.approval_state,
              summary = excluded.summary,
              updated_at = excluded.updated_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                str(payload.get("title") or envelope.object_id),
                str(payload.get("status") or "active"),
                str(payload.get("approval_state") or "approved"),
                str(payload.get("summary") or ""),
                str(payload.get("updated_at") or envelope.stored_at),
            ),
        )

    def _upsert_workstream_candidate(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO workstream_candidates (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              title, proposal_state, candidate_for, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              title = excluded.title,
              proposal_state = excluded.proposal_state,
              candidate_for = excluded.candidate_for,
              confidence = excluded.confidence,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                str(payload.get("title") or envelope.object_id),
                str(payload.get("proposal_state") or "proposed"),
                payload.get("candidate_for"),
                float(payload.get("confidence") or 0.0),
                str(payload.get("created_at") or envelope.stored_at),
            ),
        )

    def _upsert_knowledge(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        body_text = _text_body(payload.get("body"))
        conn.execute(
            """
            INSERT INTO knowledge_artifacts (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              kind, title, status, body_text, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              kind = excluded.kind,
              title = excluded.title,
              status = excluded.status,
              body_text = excluded.body_text,
              updated_at = excluded.updated_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["kind"],
                payload["title"],
                payload["status"],
                body_text,
                payload["updated_at"],
            ),
        )
        conn.execute(
            """
            INSERT INTO knowledge_search_cache (object_id, title, body_text)
            VALUES (?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              title = excluded.title,
              body_text = excluded.body_text
            """,
            (envelope.object_id, payload["title"], body_text),
        )
        if self._has_table(conn, "knowledge_fts"):
            conn.execute("DELETE FROM knowledge_fts WHERE object_id = ?", (envelope.object_id,))
            conn.execute(
                "INSERT INTO knowledge_fts (object_id, title, body_text) VALUES (?, ?, ?)",
                (envelope.object_id, payload["title"], body_text),
            )

    def _upsert_bundle(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO context_bundles (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              task_label, token_budget, token_estimate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              task_label = excluded.task_label,
              token_budget = excluded.token_budget,
              token_estimate = excluded.token_estimate,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["task_label"],
                int(payload["token_budget"]),
                int(payload["token_estimate"]),
                payload["created_at"],
            ),
        )

    def _upsert_claim(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO claims (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              subject_ref, claim_text, status, sensitivity, redaction_state, exportable, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              subject_ref = excluded.subject_ref,
              claim_text = excluded.claim_text,
              status = excluded.status,
              sensitivity = excluded.sensitivity,
              redaction_state = excluded.redaction_state,
              exportable = excluded.exportable,
              updated_at = excluded.updated_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["subject_ref"],
                payload["claim_text"],
                payload["status"],
                payload["sensitivity"],
                payload["redaction_state"],
                1 if bool(payload["exportable"]) else 0,
                payload["updated_at"],
            ),
        )

    def _upsert_evidence_link(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO evidence_links (
              object_id, semantic_ref, storage_ref, storage_path, claim_id,
              evidence_ref, relation, confidence, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              claim_id = excluded.claim_id,
              evidence_ref = excluded.evidence_ref,
              relation = excluded.relation,
              confidence = excluded.confidence,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                payload["claim_id"],
                payload["evidence_ref"],
                payload["relation"],
                float(payload["confidence"]),
                payload["created_at"],
            ),
        )

    def _upsert_audit_run(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO audit_runs (
              object_id, semantic_ref, storage_ref, storage_path, scope_kind, scope_value,
              subject_ref, verdict, method, review_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              scope_kind = excluded.scope_kind,
              scope_value = excluded.scope_value,
              subject_ref = excluded.subject_ref,
              verdict = excluded.verdict,
              method = excluded.method,
              review_state = excluded.review_state,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                scope_kind,
                scope_value,
                payload["subject_ref"],
                payload["verdict"],
                payload["method"],
                payload["review_state"],
                payload["created_at"],
            ),
        )

    def _upsert_eval_run(
        self,
        conn: sqlite3.Connection,
        envelope: StoredObjectEnvelope,
        object_path: Path,
    ) -> None:
        payload = envelope.payload
        conn.execute(
            """
            INSERT INTO eval_runs (
              object_id, semantic_ref, storage_ref, storage_path, target_type,
              target_id, dataset_ref, result, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id) DO UPDATE SET
              semantic_ref = excluded.semantic_ref,
              storage_ref = excluded.storage_ref,
              storage_path = excluded.storage_path,
              target_type = excluded.target_type,
              target_id = excluded.target_id,
              dataset_ref = excluded.dataset_ref,
              result = excluded.result,
              created_at = excluded.created_at
            """,
            (
                envelope.object_id,
                envelope.semantic_ref,
                envelope.storage_ref,
                str(object_path),
                payload["target_type"],
                payload["target_id"],
                payload["dataset_ref"],
                payload["result"],
                payload["created_at"],
            ),
        )

    def _load_payload(self, storage_path: Path) -> dict[str, Any]:
        return json.loads(storage_path.read_text())["payload"]

    def _load_stored_envelope(self, storage_path: Path) -> StoredObjectEnvelope:
        payload = json.loads(storage_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"expected envelope object in {storage_path}")
        envelope_payload = payload.get("payload")
        if not isinstance(envelope_payload, dict):
            raise ValueError(f"expected envelope payload in {storage_path}")
        return StoredObjectEnvelope(
            object_id=str(payload["object_id"]),
            object_kind=str(payload["object_kind"]),
            schema_family=str(payload["schema_family"]),
            semantic_ref=str(payload["semantic_ref"]),
            storage_ref=str(payload["storage_ref"]),
            content_sha256=str(payload["content_sha256"]),
            stored_at=str(payload["stored_at"]),
            payload=envelope_payload,
        )

    def _load_object_payload(self, object_kind: str, object_id: str) -> dict[str, Any]:
        self.initialize()
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT storage_path
                FROM object_index
                WHERE object_kind = ? AND object_id = ?
                """,
                (object_kind, object_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown {object_kind} {object_id}")
        return self._load_payload(Path(str(row["storage_path"])))

    def _optional_object_payload(self, object_kind: str, object_id: str) -> dict[str, Any] | None:
        try:
            return self._load_object_payload(object_kind, object_id)
        except KeyError:
            return None

    def _scope_from_payload(self, payload: dict[str, Any]) -> tuple[str, str] | None:
        scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
        scope_kind = str(scope.get("kind") or "").strip()
        scope_value = str(scope.get("value") or "").strip()
        if scope_kind and scope_value:
            return (scope_kind, scope_value)
        return None

    def _load_claims(self, *, subject_ref: str, claim_refs: list[str] | None) -> list[dict[str, Any]]:
        with self._connection() as conn:
            if claim_refs:
                claim_ids = [self._claim_id_from_ref(ref) for ref in claim_refs]
                placeholders = ",".join("?" for _ in claim_ids)
                return [
                    self._load_payload(Path(str(row["storage_path"])))
                    for row in conn.execute(
                        f"""
                        SELECT storage_path
                        FROM claims
                        WHERE object_id IN ({placeholders})
                        ORDER BY object_id ASC
                        """,
                        claim_ids,
                    ).fetchall()
                ]
            else:
                return [
                    self._load_payload(Path(str(row["storage_path"])))
                    for row in conn.execute(
                        """
                        SELECT storage_path
                        FROM claims
                        WHERE subject_ref = ?
                        ORDER BY updated_at ASC, object_id ASC
                        """,
                        (subject_ref,),
                    ).fetchall()
                ]

    def _load_evidence_links(self, claim_ids: list[str]) -> list[dict[str, Any]]:
        if not claim_ids:
            return []
        placeholders = ",".join("?" for _ in claim_ids)
        with self._connection() as conn:
            return [
                self._load_payload(Path(str(row["storage_path"])))
                for row in conn.execute(
                    f"""
                    SELECT storage_path
                    FROM evidence_links
                    WHERE claim_id IN ({placeholders})
                    ORDER BY confidence DESC, object_id ASC
                    """,
                    claim_ids,
                ).fetchall()
            ]

    def _derive_audit_outcome(
        self,
        claims: list[dict[str, Any]],
        evidence_links: list[dict[str, Any]],
    ) -> tuple[str, str, str]:
        per_claim_links: dict[str, list[dict[str, Any]]] = {str(claim["id"]): [] for claim in claims}
        for link in evidence_links:
            per_claim_links.setdefault(str(link["claim_id"]), []).append(link)

        claim_verdicts: list[str] = []
        strong_supports = 0
        strong_contradictions = 0
        for claim in claims:
            links = per_claim_links.get(str(claim["id"]), [])
            support_confidence = max(
                (float(link["confidence"]) for link in links if link["relation"] == "supports"),
                default=0.0,
            )
            contradiction_confidence = max(
                (float(link["confidence"]) for link in links if link["relation"] == "contradicts"),
                default=0.0,
            )
            if support_confidence >= RELIABLE_EVIDENCE_CONFIDENCE and contradiction_confidence >= RELIABLE_EVIDENCE_CONFIDENCE:
                claim_verdicts.append("needs_human_review")
            elif contradiction_confidence >= RELIABLE_EVIDENCE_CONFIDENCE:
                claim_verdicts.append("contradicted_by_local_evidence")
                strong_contradictions += 1
            elif support_confidence >= RELIABLE_EVIDENCE_CONFIDENCE:
                claim_verdicts.append("supported_by_local_evidence")
                strong_supports += 1
            elif support_confidence > 0 or contradiction_confidence > 0:
                claim_verdicts.append("needs_human_review")
            else:
                claim_verdicts.append("insufficient_local_evidence")

        unique_verdicts = set(claim_verdicts)
        if "needs_human_review" in unique_verdicts:
            verdict = "needs_human_review"
            review_state = "open"
        elif "supported_by_local_evidence" in unique_verdicts and "contradicted_by_local_evidence" in unique_verdicts:
            verdict = "needs_human_review"
            review_state = "open"
        elif unique_verdicts == {"supported_by_local_evidence"}:
            verdict = "supported_by_local_evidence"
            review_state = "approved"
        elif unique_verdicts == {"contradicted_by_local_evidence"}:
            verdict = "contradicted_by_local_evidence"
            review_state = "approved"
        elif unique_verdicts == {"insufficient_local_evidence"}:
            verdict = "insufficient_local_evidence"
            review_state = "approved"
        else:
            verdict = "needs_human_review"
            review_state = "open"

        note = (
            f"deterministic audit summary: claims={len(claims)}, evidence_links={len(evidence_links)}, "
            f"strong_supports={strong_supports}, strong_contradictions={strong_contradictions}, "
            f"claim_verdicts={claim_verdicts}"
        )
        return verdict, review_state, note

    def _claim_id_from_ref(self, ref: str) -> str:
        return ref.split("://", 1)[1] if "://" in ref else ref

    def _memory_payload_from_candidate(
        self,
        candidate_payload: dict[str, Any],
        *,
        memory_id: str | None = None,
    ) -> dict[str, Any]:
        candidate_id = str(candidate_payload["id"])
        now = _utc_now()
        candidate_for = str(candidate_payload.get("candidate_for") or "").strip()
        return {
            "id": memory_id or self._memory_id_from_candidate(candidate_id),
            "type": candidate_payload["type"],
            "scope": dict(candidate_payload["scope"]),
            "status": "active",
            "approval_state": "approved",
            "statement": candidate_payload["statement"],
            "source_refs": _unique([*list(candidate_payload.get("source_refs", [])), _semantic_ref("memory_candidate", candidate_id)]),
            "confidence": float(candidate_payload["confidence"]),
            "valid_from": now,
            "valid_to": None,
            "supersedes": [candidate_for] if candidate_for else [],
            "retracts": [],
            "retrieval_policy": {
                "pinned": False,
                "priority": float(candidate_payload["confidence"]),
                "decay": "medium",
            },
            "sensitivity": candidate_payload["sensitivity"],
            "redaction_state": candidate_payload["redaction_state"],
            "secret_refs": list(candidate_payload.get("secret_refs", [])),
            "exportable": bool(candidate_payload.get("exportable", True)),
            "created_at": now,
            "updated_at": now,
        }

    def _memory_id_from_candidate(self, candidate_id: str) -> str:
        if candidate_id.startswith("memc_"):
            return f"mem_{candidate_id[5:]}"
        return f"mem_{hashlib.sha256(candidate_id.encode('utf-8')).hexdigest()[:12]}"

    def _resolve_prompt_eval_target(self, target_type: str, target_id: str) -> tuple[dict[str, Any], str, str]:
        with self._connection() as conn:
            if target_type == "prompt_asset":
                row = conn.execute(
                    """
                    SELECT semantic_ref, storage_ref, storage_path
                    FROM prompt_assets
                    WHERE object_id = ?
                    """,
                    (target_id,),
                ).fetchone()
                if row is None:
                    raise KeyError(f"unknown prompt asset {target_id}")
                return (
                    self._load_payload(Path(str(row["storage_path"]))),
                    str(row["semantic_ref"]),
                    str(row["storage_ref"]),
                )

            patch_row = conn.execute(
                """
                SELECT semantic_ref, storage_ref, storage_path
                FROM prompt_patches
                WHERE object_id = ?
                """,
                (target_id,),
            ).fetchone()
            if patch_row is None:
                raise KeyError(f"unknown prompt patch {target_id}")
            patch_row_data = dict(patch_row)

        patch_payload = self._load_payload(Path(str(patch_row_data["storage_path"])))
        prompt_row = self._prompt_row(str(patch_payload["prompt_asset_id"]))
        prompt_payload = self._load_payload(Path(str(prompt_row["storage_path"])))
        return (
            self._prompt_payload_preview_from_patch(prompt_payload, patch_payload),
            str(patch_row_data["semantic_ref"]),
            str(patch_row_data["storage_ref"]),
        )

    def _evaluate_prompt_payload(
        self,
        prompt_payload: dict[str, Any],
        *,
        assert_contains: list[str],
        assert_not_contains: list[str],
    ) -> tuple[dict[str, Any], str]:
        searchable_text = _canonical_json(prompt_payload).lower()
        contains_passed = [value for value in assert_contains if value.lower() in searchable_text]
        contains_failed = [value for value in assert_contains if value.lower() not in searchable_text]
        not_contains_passed = [value for value in assert_not_contains if value.lower() not in searchable_text]
        not_contains_failed = [value for value in assert_not_contains if value.lower() in searchable_text]
        assertions_total = len(assert_contains) + len(assert_not_contains)

        if assertions_total == 0:
            result = "inconclusive"
        elif contains_failed or not_contains_failed:
            result = "failed"
        else:
            result = "passed"

        return (
            {
                "assert_contains": assert_contains,
                "assert_not_contains": assert_not_contains,
                "contains_passed": contains_passed,
                "contains_failed": contains_failed,
                "not_contains_passed": not_contains_passed,
                "not_contains_failed": not_contains_failed,
                "assertions_total": assertions_total,
                "text_sha256": hashlib.sha256(searchable_text.encode("utf-8")).hexdigest(),
            },
            result,
        )

    def _prompt_row(self, prompt_id: str) -> dict[str, Any]:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT pa.object_id, pa.semantic_ref, pa.storage_ref, pa.storage_path, oi.content_sha256
                FROM prompt_assets AS pa
                JOIN object_index AS oi ON oi.object_id = pa.object_id
                WHERE pa.object_id = ?
                """,
                (prompt_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown prompt asset {prompt_id}")
            return dict(row)

    def _prompt_patch_context(self, patch_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        with self._connection() as conn:
            patch_row = conn.execute(
                """
                SELECT
                  pp.object_id,
                  pp.semantic_ref,
                  pp.storage_ref,
                  pp.storage_path,
                  pp.proposal_state,
                  pp.prompt_asset_id,
                  oi.content_sha256
                FROM prompt_patches AS pp
                JOIN object_index AS oi ON oi.object_id = pp.object_id
                WHERE pp.object_id = ?
                """,
                (patch_id,),
            ).fetchone()
            if patch_row is None:
                raise KeyError(f"unknown prompt patch {patch_id}")
            patch_row_data = dict(patch_row)

        patch_payload = self._load_payload(Path(str(patch_row_data["storage_path"])))
        prompt_row_data = self._prompt_row(str(patch_payload["prompt_asset_id"]))
        prompt_payload = self._load_payload(Path(str(prompt_row_data["storage_path"])))
        return patch_row_data, prompt_row_data, patch_payload, prompt_payload

    def _prompt_eval_refs(self, target_type: str, target_id: str) -> list[str]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT semantic_ref
                FROM eval_runs
                WHERE target_type = ? AND target_id = ?
                ORDER BY created_at ASC, object_id ASC
                """,
                (target_type, target_id),
            ).fetchall()
        return [str(row["semantic_ref"]) for row in rows]

    def _prompt_has_passed_eval(self, target_type: str, target_id: str) -> bool:
        with self._connection() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM eval_runs
                WHERE target_type = ? AND target_id = ? AND result = 'passed'
                LIMIT 1
                """,
                (target_type, target_id),
            ).fetchone()
        return row is not None

    def _prompt_payload_preview_from_patch(self, prompt_payload: dict[str, Any], patch_payload: dict[str, Any]) -> dict[str, Any]:
        changes = patch_payload.get("changes")
        if not isinstance(changes, dict):
            raise ValueError("prompt patch changes must be an object")
        invalid_fields = sorted(set(changes) - PROMPT_PATCH_MUTABLE_FIELDS)
        if invalid_fields:
            raise ValueError(f"prompt patch includes unsupported fields: {invalid_fields}")

        updated_prompt = deepcopy(prompt_payload)
        for field, value in changes.items():
            updated_prompt[field] = deepcopy(value)
        return updated_prompt

    def _prompt_payload_from_patch(self, prompt_payload: dict[str, Any], patch_payload: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        updated_prompt = self._prompt_payload_preview_from_patch(prompt_payload, patch_payload)
        updated_prompt["derived_from"] = _unique(
            [
                *list(prompt_payload.get("derived_from", [])),
                _semantic_ref("prompt_patch", str(patch_payload["id"])),
                *list(patch_payload.get("source_refs", [])),
            ]
        )
        updated_prompt["eval_status"] = "pending"
        updated_prompt["last_promoted_at"] = now
        updated_prompt["updated_at"] = now
        return updated_prompt

    def _write_workstream_candidate_review_receipt(
        self,
        *,
        candidate_row: dict[str, Any],
        candidate_envelope: StoredObjectEnvelope,
        decision: str,
        reviewer: str,
        notes: str | None,
        workstream_envelope: StoredObjectEnvelope | None,
        policy_decision: dict[str, Any] | None,
    ) -> dict[str, Any]:
        reviewed_at = _utc_now()
        stamp = _utc_compact_timestamp()
        receipt = {
            "id": f"review_wsc_{candidate_envelope.object_id}_{stamp.lower()}",
            "review_kind": "workstream_candidate",
            "subject_ref": candidate_row["semantic_ref"],
            "decision": decision,
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "notes": notes,
            "candidate_content_sha256_before": candidate_row["content_sha256"],
            "candidate_storage_ref_before": candidate_row["storage_ref"],
            "candidate_ref_after": candidate_envelope.semantic_ref,
            "candidate_storage_ref_after": candidate_envelope.storage_ref,
            "candidate_content_sha256_after": candidate_envelope.content_sha256,
            "result_ref": workstream_envelope.semantic_ref if workstream_envelope is not None else None,
            "result_storage_ref": workstream_envelope.storage_ref if workstream_envelope is not None else None,
            "result_content_sha256": workstream_envelope.content_sha256 if workstream_envelope is not None else None,
            "policy_decision": policy_decision,
        }
        review_dir = self.layout.reviews_dir / "workstream_candidate"
        review_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = review_dir / f"{candidate_envelope.object_id}-{stamp}.json"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
        return {"path": str(receipt_path), "payload": receipt}

    def _write_memory_candidate_review_receipt(
        self,
        *,
        candidate_row: dict[str, Any],
        candidate_envelope: StoredObjectEnvelope,
        decision: str,
        reviewer: str,
        notes: str | None,
        memory_envelope: StoredObjectEnvelope | None,
        policy_decision: dict[str, Any] | None,
    ) -> dict[str, Any]:
        reviewed_at = _utc_now()
        stamp = _utc_compact_timestamp()
        receipt = {
            "id": f"review_memc_{candidate_envelope.object_id}_{stamp.lower()}",
            "review_kind": "memory_candidate",
            "subject_ref": candidate_row["semantic_ref"],
            "decision": decision,
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "notes": notes,
            "candidate_content_sha256_before": candidate_row["content_sha256"],
            "candidate_storage_ref_before": candidate_row["storage_ref"],
            "candidate_ref_after": candidate_envelope.semantic_ref,
            "candidate_storage_ref_after": candidate_envelope.storage_ref,
            "candidate_content_sha256_after": candidate_envelope.content_sha256,
            "result_ref": memory_envelope.semantic_ref if memory_envelope is not None else None,
            "result_storage_ref": memory_envelope.storage_ref if memory_envelope is not None else None,
            "policy_decision": policy_decision,
        }
        review_dir = self.layout.reviews_dir / "memory_candidate"
        review_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = review_dir / f"{candidate_envelope.object_id}-{stamp}.json"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
        return {"path": str(receipt_path), "payload": receipt}

    def _write_prompt_patch_review_receipt(
        self,
        *,
        patch_row: dict[str, Any],
        prompt_row: dict[str, Any],
        patch_envelope: StoredObjectEnvelope,
        decision: str,
        reviewer: str,
        notes: str | None,
        prompt_envelope: StoredObjectEnvelope | None,
        preview_content_sha256: str,
        eval_refs: list[str],
        policy_decision: dict[str, Any] | None,
    ) -> dict[str, Any]:
        reviewed_at = _utc_now()
        stamp = _utc_compact_timestamp()
        result_payload = prompt_envelope.payload if prompt_envelope is not None else None
        receipt = {
            "id": f"review_ppatch_{patch_envelope.object_id}_{stamp.lower()}",
            "review_kind": "prompt_patch",
            "subject_ref": patch_row["semantic_ref"],
            "target_prompt_ref_before": prompt_row["semantic_ref"],
            "target_prompt_storage_ref_before": prompt_row["storage_ref"],
            "target_prompt_content_sha256_before": prompt_row["content_sha256"],
            "patch_preview_content_sha256": preview_content_sha256,
            "eval_refs_before_review": list(eval_refs),
            "decision": decision,
            "reviewed_by": reviewer,
            "reviewed_at": reviewed_at,
            "notes": notes,
            "patch_content_sha256_before": patch_row["content_sha256"],
            "patch_storage_ref_before": patch_row["storage_ref"],
            "patch_ref_after": patch_envelope.semantic_ref,
            "patch_storage_ref_after": patch_envelope.storage_ref,
            "patch_content_sha256_after": patch_envelope.content_sha256,
            "result_ref": prompt_envelope.semantic_ref if prompt_envelope is not None else None,
            "result_storage_ref": prompt_envelope.storage_ref if prompt_envelope is not None else None,
            "result_content_sha256": prompt_envelope.content_sha256 if prompt_envelope is not None else None,
            "lineage": {
                "stable_prompt_ref": prompt_row["semantic_ref"],
                "patch_ref": patch_envelope.semantic_ref,
                "patch_source_refs": list(patch_envelope.payload.get("source_refs", [])),
                "derived_from_after": list(result_payload.get("derived_from", [])) if result_payload is not None else None,
            },
            "policy_decision": policy_decision,
        }
        review_dir = self.layout.reviews_dir / "prompt_patch"
        review_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = review_dir / f"{patch_envelope.object_id}-{stamp}.json"
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n")
        return {"path": str(receipt_path), "payload": receipt}

    def _project_profile_hits(self, *, scope: tuple[str, str], limit: int = 3) -> list[SearchHit]:
        with self._connection() as conn:
            return [
                self._knowledge_hit_from_row(dict(row))
                for row in conn.execute(
                    """
                    SELECT object_id, semantic_ref, storage_ref, storage_path
                    FROM knowledge_artifacts
                    WHERE status = 'active'
                      AND kind = 'project_profile'
                      AND scope_kind = ? AND scope_value = ?
                    ORDER BY updated_at DESC, object_id ASC
                    LIMIT ?
                    """,
                    (scope[0], scope[1], limit),
                ).fetchall()
            ]

    def _prompt_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=1.0,
            payload=payload,
        )

    def _memory_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        score = float(row["confidence"]) + float(row["pinned"]) + float(row["retrieval_priority"])
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=score,
            payload=payload,
        )

    def _memory_candidate_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=float(row["confidence"]),
            payload=payload,
        )

    def _workstream_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=1.0,
            payload=payload,
        )

    def _workstream_candidate_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=float(row["confidence"]),
            payload=payload,
        )

    def _prompt_patch_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=float(row["confidence"]),
            payload=payload,
        )

    def _knowledge_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=1.0,
            payload=payload,
        )

    def _episode_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=1.0,
            payload=payload,
        )

    def _episode_sort_key(self, hit: SearchHit) -> tuple[str, int, str]:
        payload = hit.payload
        return (
            str(payload.get("start_at") or ""),
            int(payload.get("start_turn_index") or 0),
            hit.object_id,
        )

    def _session_hit_from_row(self, row: dict[str, Any]) -> SearchHit:
        payload = self._load_payload(Path(row["storage_path"]))
        payload["turn_count"] = int(row["turn_count"])
        if not str(payload.get("source_app") or "").strip():
            payload["source_app"] = str(row.get("source_app") or payload.get("client") or "unknown")
        if not str(payload.get("source_surface") or "").strip():
            payload["source_surface"] = str(row.get("source_surface") or "unknown")
        if not str(payload.get("source_format") or "").strip():
            payload["source_format"] = str(row.get("source_format") or "unknown")
        if not str(payload.get("capture_method") or "").strip():
            payload["capture_method"] = str(row.get("capture_method") or "unknown")
        return SearchHit(
            object_id=row["object_id"],
            semantic_ref=row["semantic_ref"],
            storage_ref=row["storage_ref"],
            score=1.0,
            payload=payload,
        )
