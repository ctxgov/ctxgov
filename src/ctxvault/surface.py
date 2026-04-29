from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .adapters import AdapterRegistry, projection_adapter_healthcheck
from .backup import emit_backup_bundle
from .core import ContextBuildRequest, ContextItemInput, CtxVault
from .policy import CtxVaultPolicy
from .plugins import LocalPluginExecutorRegistry, PluginRegistry
from .privacy import scan_privacy_files, scan_privacy_text
from .projections import emit_agents_md_projection, emit_claude_md_projection, emit_wiki_workstream_md_projection
from .receipts import emit_audit_receipt, emit_context_bundle_receipt, emit_workstream_candidate_receipt, emit_workstream_receipt
from .share_handoff import (
    compose_share_handoff_capture,
    list_share_handoffs,
    mark_share_handoff_consumed,
    preview_share_handoff,
    stage_share_handoff,
)
from .versioning import (
    accept_pairing_offer,
    apply_replica,
    apply_restore,
    apply_sync_manifest,
    create_snapshot,
    diff_snapshots,
    emit_pairing_offer,
    emit_sync_manifest,
    emit_sync_receipt,
    evaluate_replica_trust,
    import_replica,
    list_mutations,
    list_pairing_offers,
    list_replica_trust_devices,
    list_snapshots,
    list_sync_conflicts,
    list_transport_events,
    load_replica_trust_registry,
    plan_restore,
    record_mutation,
    review_sync_conflict,
    set_replica_device_trust,
    snapshot_lineage,
    snapshot_provenance,
    sync_status,
    verify_replica,
    write_local_backup,
)


class CtxVaultSurface:
    def __init__(self, vault: CtxVault):
        self.vault = vault

    def trace_record(self, model_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        envelope = self.vault.store_core_object(model_name, payload)
        return {
            "object_id": envelope.object_id,
            "object_kind": envelope.object_kind,
            "semantic_ref": envelope.semantic_ref,
            "storage_ref": envelope.storage_ref,
            "content_sha256": envelope.content_sha256,
        }

    def _record_mutation(
        self,
        *,
        mutation_kind: str,
        object_ref: str,
        actor: str | None = None,
        decision: str | None = None,
        scope: dict[str, Any] | None = None,
        related_refs: list[str] | None = None,
        notes: str | None = None,
        status: str = "recorded",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return record_mutation(
            layout=self.vault.layout,
            mutation_kind=mutation_kind,
            object_ref=object_ref,
            actor=actor,
            decision=decision,
            scope=scope,
            related_refs=related_refs,
            notes=notes,
            status=status,
            details=details,
        )

    def prompt_resolve(self, prompt_id: str) -> dict[str, Any]:
        resolved = self.vault.resolve_prompt(prompt_id)
        return {
            "object_id": resolved.object_id,
            "semantic_ref": resolved.semantic_ref,
            "storage_ref": resolved.storage_ref,
            "instruction": resolved.instruction,
            "required_context_types": resolved.required_context_types,
            "payload": resolved.payload,
        }

    def prompt_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_prompts(scope=scope, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def session_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_sessions(scope=scope, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def session_search(
        self,
        query: str,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.search_sessions(query, scope=scope, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def session_related(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        return self.vault.related_sessions(session_id, limit=limit)

    def session_aggregate_preview(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        return self.vault.session_aggregate_preview(session_id, limit=limit)

    def companion_dashboard(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        session_limit: int = 8,
        workstream_limit: int = 5,
        review_limit: int = 8,
        intelligence_limit: int = 6,
    ) -> dict[str, Any]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        session_hits = self.vault.list_sessions(scope=scope, limit=session_limit)
        workstream_hits = self.vault.list_workstreams(scope=scope, status="active", limit=workstream_limit)
        memory_candidate_hits = self.vault.list_memory_candidates(scope=scope, proposal_state="proposed", limit=review_limit)
        workstream_candidate_hits = self.vault.list_workstream_candidates(
            scope=scope,
            proposal_state="proposed",
            limit=review_limit,
        )
        prompt_patch_hits = self.vault.list_prompt_patches(scope=scope, proposal_state="proposed", limit=review_limit)

        active_workstreams = [
            _companion_workstream_card(
                hit.payload,
                self.vault.workstream_intelligence(hit.object_id, limit=intelligence_limit),
            )
            for hit in workstream_hits
        ]
        recent_sessions = [_companion_session_card(hit.payload) for hit in session_hits]

        review_items = [
            *[_companion_review_card("memory_candidate", hit) for hit in memory_candidate_hits],
            *[_companion_review_card("workstream_candidate", hit) for hit in workstream_candidate_hits],
            *[_companion_review_card("prompt_patch", hit) for hit in prompt_patch_hits],
        ]
        review_items.sort(key=_companion_review_sort_key, reverse=True)
        review_items = review_items[:review_limit]

        return {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "scope": {"kind": scope_kind, "value": scope_value} if scope is not None else None,
            "summary": {
                "active_workstream_count": len(active_workstreams),
                "recent_session_count": len(recent_sessions),
                "review_item_count": len(review_items),
                "active_workstream_id": active_workstreams[0]["id"] if active_workstreams else None,
            },
            "active_workstreams": active_workstreams,
            "recent_sessions": recent_sessions,
            "review_queue": {
                "returned_count": len(review_items),
                "by_kind": {
                    "memory_candidate": len(memory_candidate_hits),
                    "workstream_candidate": len(workstream_candidate_hits),
                    "prompt_patch": len(prompt_patch_hits),
                },
                "items": review_items,
            },
        }

    def companion_capture_candidate(
        self,
        *,
        statement: str,
        why_it_matters: str,
        scope_kind: str = "project",
        scope_value: str = "ctxvault",
        candidate_type: str = "workflow_pattern",
        source_refs: list[str] | None = None,
        notes: str | None = None,
        candidate_id: str | None = None,
        claim_id: str | None = None,
        confidence: float = 0.8,
        candidate_for: str | None = None,
        sensitivity: str = "internal",
        redaction_state: str = "none",
        exportable: bool = True,
        source_app: str = "ctxvault",
        source_surface: str = "ios",
        source_format: str = "companion_capture",
        capture_method: str = "manual_entry",
        imported_via: str = "ctxvault_companion",
        capture_text: str | None = None,
    ) -> dict[str, Any]:
        normalized_statement = str(statement).strip()
        normalized_why = str(why_it_matters).strip()
        if not normalized_statement:
            raise ValueError("statement must be a non-empty string")
        if not normalized_why:
            raise ValueError("why_it_matters must be a non-empty string")

        timestamp = _companion_now()
        effective_candidate_id = candidate_id or _companion_generated_id("memc")
        effective_claim_id = claim_id or _companion_generated_id("claim")
        normalized_source_refs = _companion_string_list(source_refs)
        claim_payload = {
            "id": effective_claim_id,
            "scope": {"kind": scope_kind, "value": scope_value},
            "subject_ref": f"memory-candidate://{effective_candidate_id}",
            "claim_text": str(capture_text or normalized_statement).strip(),
            "status": "recorded",
            "source_refs": normalized_source_refs,
            "sensitivity": sensitivity,
            "redaction_state": redaction_state,
            "secret_refs": [],
            "exportable": exportable,
            "notes": _companion_capture_notes(
                notes=notes,
                source_app=source_app,
                source_surface=source_surface,
                source_format=source_format,
                capture_method=capture_method,
                imported_via=imported_via,
            ),
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        claim_envelope = self.vault.capture_claim(claim_payload)

        candidate_payload = {
            "id": effective_candidate_id,
            "type": candidate_type,
            "scope": {"kind": scope_kind, "value": scope_value},
            "statement": normalized_statement,
            "why_it_matters": normalized_why,
            "source_refs": _companion_unique_refs([f"claim://{effective_claim_id}", *normalized_source_refs]),
            "confidence": float(confidence),
            "proposal_state": "proposed",
            "candidate_for": candidate_for,
            "sensitivity": sensitivity,
            "redaction_state": redaction_state,
            "secret_refs": [],
            "exportable": exportable,
            "created_at": timestamp,
        }
        candidate_envelope = self.vault.store_core_object("MemoryCandidate", candidate_payload)
        return {
            "capture_metadata": {
                "source_app": source_app,
                "source_surface": source_surface,
                "source_format": source_format,
                "capture_method": capture_method,
                "imported_via": imported_via,
            },
            "claim": claim_envelope.payload,
            "claim_ref": claim_envelope.semantic_ref,
            "candidate": candidate_envelope.payload,
            "candidate_ref": candidate_envelope.semantic_ref,
        }

    def companion_share_handoff_stage(
        self,
        *,
        shared_root: Path | None = None,
        title: str | None = None,
        text: str | None = None,
        urls: list[str] | None = None,
        attachment_paths: list[str | Path] | None = None,
        source_app: str = "ctxvault",
        source_surface: str = "ios",
        source_format: str = "share_extension_payload",
        capture_method: str = "share_extension",
        imported_via: str = "ctxvault_share_extension",
        notes: str | None = None,
        metadata: dict[str, Any] | None = None,
        handoff_id: str | None = None,
    ) -> dict[str, Any]:
        resolved_shared_root = self._resolve_companion_shared_root(shared_root)
        result = stage_share_handoff(
            shared_root=resolved_shared_root,
            title=title,
            text=text,
            urls=urls,
            attachment_paths=attachment_paths,
            source_app=source_app,
            source_surface=source_surface,
            source_format=source_format,
            capture_method=capture_method,
            imported_via=imported_via,
            notes=notes,
            metadata=metadata,
            handoff_id=handoff_id,
        )
        return {
            "shared_root": str(resolved_shared_root),
            "queue_dir": result["queue_dir"],
            "handoff_path": result["handoff_path"],
            "handoff": result["handoff"],
        }

    def companion_share_handoff_list(
        self,
        *,
        shared_root: Path | None = None,
        limit: int = 50,
        include_archived: bool = False,
    ) -> dict[str, Any]:
        resolved_shared_root = self._resolve_companion_shared_root(shared_root)
        result = list_share_handoffs(
            shared_root=resolved_shared_root,
            limit=limit,
            include_archived=include_archived,
        )
        return {
            **result,
            "shared_root": str(resolved_shared_root),
        }

    def companion_share_handoff_preview(
        self,
        *,
        handoff_path: Path,
        shared_root: Path | None = None,
        max_findings: int = 25,
        max_bytes: int = 262_144,
    ) -> dict[str, Any]:
        resolved_shared_root = self._resolve_companion_shared_root(shared_root)
        result = preview_share_handoff(
            shared_root=resolved_shared_root,
            handoff_path=handoff_path.resolve(),
            max_findings=max_findings,
            max_bytes=max_bytes,
        )
        return {
            **result,
            "shared_root": str(resolved_shared_root),
        }

    def companion_share_handoff_consume(
        self,
        *,
        handoff_path: Path,
        why_it_matters: str,
        shared_root: Path | None = None,
        statement: str | None = None,
        scope_kind: str = "project",
        scope_value: str = "ctxvault",
        candidate_type: str = "workflow_pattern",
        confidence: float = 0.8,
        candidate_for: str | None = None,
        sensitivity: str = "internal",
        redaction_state: str = "none",
        exportable: bool = True,
        notes: str | None = None,
        reviewed_by: str = "share_handoff_consume",
        allow_blocked: bool = False,
        max_findings: int = 25,
        max_bytes: int = 262_144,
    ) -> dict[str, Any]:
        normalized_why = str(why_it_matters).strip()
        if not normalized_why:
            raise ValueError("why_it_matters must be a non-empty string")

        resolved_shared_root = self._resolve_companion_shared_root(shared_root)
        resolved_handoff_path = handoff_path.resolve()
        preview = preview_share_handoff(
            shared_root=resolved_shared_root,
            handoff_path=resolved_handoff_path,
            max_findings=max_findings,
            max_bytes=max_bytes,
        )
        preview_decision = str(preview.get("decision") or "allow")
        if preview_decision == "block" and not allow_blocked:
            raise ValueError("share handoff preview is blocked; set allow_blocked to consume anyway")

        capture_defaults = compose_share_handoff_capture(
            shared_root=resolved_shared_root,
            handoff_path=resolved_handoff_path,
        )
        capture = self.companion_capture_candidate(
            statement=str(statement or capture_defaults["statement"]).strip(),
            why_it_matters=normalized_why,
            scope_kind=scope_kind,
            scope_value=scope_value,
            candidate_type=candidate_type,
            source_refs=list(capture_defaults.get("source_refs") or []),
            notes=_companion_merge_notes(
                str(capture_defaults.get("notes") or "").strip() or None,
                notes,
            ),
            confidence=confidence,
            candidate_for=candidate_for,
            sensitivity=sensitivity,
            redaction_state=redaction_state,
            exportable=exportable,
            source_app=str(capture_defaults.get("source_app") or "ctxvault"),
            source_surface=str(capture_defaults.get("source_surface") or "ios"),
            source_format=str(capture_defaults.get("source_format") or "share_extension_payload"),
            capture_method=str(capture_defaults.get("capture_method") or "share_extension"),
            imported_via=str(capture_defaults.get("imported_via") or "ctxvault_share_extension"),
            capture_text=str(capture_defaults.get("capture_text") or "").strip() or None,
        )
        archived = mark_share_handoff_consumed(
            shared_root=resolved_shared_root,
            handoff_path=resolved_handoff_path,
            preview_decision=preview_decision,
            claim_ref=str(capture["claim_ref"]),
            candidate_ref=str(capture["candidate_ref"]),
            consumed_by=reviewed_by,
            consumption_notes=notes,
        )
        return {
            "shared_root": str(resolved_shared_root),
            "preview": {
                **preview,
                "shared_root": str(resolved_shared_root),
            },
            "handoff_path": archived["handoff_path"],
            "handoff": archived["handoff"],
            "capture": capture,
        }

    def companion_review_action(
        self,
        *,
        queue_kind: str,
        object_id: str,
        decision: str,
        reviewer: str = "human_review",
        notes: str | None = None,
        workstream_id: str | None = None,
        memory_id: str | None = None,
        policy_payload: dict[str, Any] | None = None,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if queue_kind == "memory_candidate":
            result = self.memory_candidate_review(
                object_id,
                decision=decision,
                reviewer=reviewer,
                notes=notes,
                memory_id=memory_id,
                policy_payload=policy_payload,
                backup_receipt=backup_receipt,
            )
        elif queue_kind == "workstream_candidate":
            result = self.workstream_candidate_review(
                object_id,
                decision=decision,
                reviewer=reviewer,
                notes=notes,
                workstream_id=workstream_id,
                policy_payload=policy_payload,
                backup_receipt=backup_receipt,
            )
        elif queue_kind == "prompt_patch":
            result = self.prompt_patch_review(
                object_id,
                decision=decision,
                reviewer=reviewer,
                notes=notes,
                policy_payload=policy_payload,
                backup_receipt=backup_receipt,
            )
        else:
            raise ValueError("queue_kind must be memory_candidate, workstream_candidate, or prompt_patch")
        return {
            "queue_kind": queue_kind,
            "object_id": object_id,
            "decision": decision,
            "result": result,
        }

    def companion_review_batch(
        self,
        *,
        items: list[dict[str, Any]],
        decision: str,
        reviewer: str = "human_review",
        notes: str | None = None,
        policy_payload: dict[str, Any] | None = None,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not items:
            raise ValueError("items must not be empty")
        if len(items) > 25:
            raise ValueError("batch review is capped at 25 items per request")
        results: list[dict[str, Any]] = []
        counts_by_queue: dict[str, int] = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("each batch review item must be an object")
            queue_kind = str(item["queue_kind"])
            result = self.companion_review_action(
                queue_kind=queue_kind,
                object_id=str(item["object_id"]),
                decision=decision,
                reviewer=reviewer,
                notes=notes,
                workstream_id=str(item.get("workstream_id") or "").strip() or None,
                memory_id=str(item.get("memory_id") or "").strip() or None,
                policy_payload=policy_payload,
                backup_receipt=backup_receipt,
            )
            results.append(result)
            counts_by_queue[queue_kind] = counts_by_queue.get(queue_kind, 0) + 1
        return {
            "decision": decision,
            "reviewer": reviewer,
            "item_count": len(results),
            "counts_by_queue": counts_by_queue,
            "results": results,
        }

    def companion_ask_from_workstream(
        self,
        *,
        question: str,
        workstream_id: str | None = None,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        prompt_id: str | None = None,
        bundle_id: str | None = None,
        token_budget: int = 12000,
        max_recent_turns: int = 6,
        max_memories: int = 5,
        max_knowledge: int = 4,
        intelligence_limit: int = 6,
    ) -> dict[str, Any]:
        normalized_question = str(question).strip()
        if not normalized_question:
            raise ValueError("question must be a non-empty string")

        workstream_payload = self._resolve_companion_workstream(
            workstream_id=workstream_id,
            scope_kind=scope_kind,
            scope_value=scope_value,
        )
        resolved_scope = dict(workstream_payload.get("scope") or {})
        intelligence_report = self.vault.workstream_intelligence(str(workstream_payload["id"]), limit=intelligence_limit)
        session_payload = self._resolve_companion_workstream_session(workstream_payload)
        active_task_state = _companion_active_task_state(
            workstream_payload,
            intelligence_report=intelligence_report,
        )
        query = _companion_ask_query(
            normalized_question,
            workstream_payload=workstream_payload,
            intelligence_report=intelligence_report,
        )
        bundle = self.context_build(
            {
                "scope_kind": str(resolved_scope.get("kind") or scope_kind or "project"),
                "scope_value": str(resolved_scope.get("value") or scope_value or "ctxvault"),
                "task_label": normalized_question,
                "prompt_id": prompt_id,
                "session_id": str(session_payload["id"]),
                "memory_query": query,
                "knowledge_query": query,
                "max_memories": max_memories,
                "max_knowledge": max_knowledge,
                "max_recent_turns": max_recent_turns,
                "token_budget": token_budget,
                "bundle_id": bundle_id,
                "active_task_state": active_task_state,
            }
        )
        workstream_card = _companion_workstream_card(workstream_payload, intelligence_report)
        ask_packet = {
            "mode": "active_workstream",
            "question": normalized_question,
            "workstream_ref": f"workstream://{workstream_payload['id']}",
            "session_ref": f"session://{session_payload['id']}",
            "bundle_ref": f"bundle://{bundle['id']}",
            "prompt_id": prompt_id,
            "handoff_text": _companion_ask_handoff_text(
                question=normalized_question,
                workstream_card=workstream_card,
                session_payload=session_payload,
                bundle=bundle,
            ),
        }
        return {
            "generated_at": _companion_now(),
            "workstream": workstream_card,
            "anchor_session": _companion_session_card(session_payload),
            "question": normalized_question,
            "bundle": bundle,
            "ask_packet": ask_packet,
        }

    def companion_workstream_sessions(
        self,
        *,
        workstream_id: str | None = None,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        session_limit: int = 8,
        recent_turn_limit: int = 4,
        selected_session_id: str | None = None,
        intelligence_limit: int = 6,
    ) -> dict[str, Any]:
        workstream_payload = self._resolve_companion_workstream(
            workstream_id=workstream_id,
            scope_kind=scope_kind,
            scope_value=scope_value,
        )
        intelligence_report = self.vault.workstream_intelligence(str(workstream_payload["id"]), limit=intelligence_limit)
        session_payloads = self._companion_workstream_session_payloads(workstream_payload)
        selected_session = self._resolve_companion_workstream_session(
            workstream_payload,
            session_id=selected_session_id,
        )
        session_cards = []
        for session_payload in reversed(session_payloads[-session_limit:]):
            turn_payloads = self._companion_session_turn_payloads(session_payload, limit=recent_turn_limit)
            session_cards.append(
                _companion_session_picker_card(
                    session_payload,
                    turn_payloads=turn_payloads,
                    selected_session_id=str(selected_session["id"]),
                )
            )
        return {
            "generated_at": _companion_now(),
            "workstream": _companion_workstream_card(workstream_payload, intelligence_report),
            "selected_session_id": str(selected_session["id"]),
            "sessions": session_cards,
        }

    def companion_followup_ask(
        self,
        *,
        question: str,
        workstream_id: str | None = None,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        session_id: str | None = None,
        turn_ref: str | None = None,
        prompt_id: str | None = None,
        bundle_id: str | None = None,
        token_budget: int = 12000,
        max_recent_turns: int = 6,
        max_memories: int = 5,
        max_knowledge: int = 4,
        intelligence_limit: int = 6,
    ) -> dict[str, Any]:
        normalized_question = str(question).strip()
        if not normalized_question:
            raise ValueError("question must be a non-empty string")

        workstream_payload = self._resolve_companion_workstream(
            workstream_id=workstream_id,
            scope_kind=scope_kind,
            scope_value=scope_value,
        )
        intelligence_report = self.vault.workstream_intelligence(str(workstream_payload["id"]), limit=intelligence_limit)
        session_payload = self._resolve_companion_workstream_session(
            workstream_payload,
            session_id=session_id,
        )
        turn_payloads = self._companion_session_turn_payloads(
            session_payload,
            limit=max(1, int(session_payload.get("turn_count") or 0), max_recent_turns),
        )
        followup_turn = _companion_resolve_followup_turn(turn_payloads, turn_ref=turn_ref)
        resolved_scope = dict(workstream_payload.get("scope") or {})
        active_task_state = [
            *_companion_active_task_state(workstream_payload, intelligence_report=intelligence_report),
            _companion_followup_state_item(session_payload, followup_turn),
        ]
        query = _companion_ask_query(
            normalized_question,
            workstream_payload=workstream_payload,
            intelligence_report=intelligence_report,
        )
        recent_conversation = [_companion_context_turn_item(payload) for payload in turn_payloads[-max_recent_turns:]]
        bundle = self.context_build(
            {
                "scope_kind": str(resolved_scope.get("kind") or scope_kind or "project"),
                "scope_value": str(resolved_scope.get("value") or scope_value or "ctxvault"),
                "task_label": normalized_question,
                "prompt_id": prompt_id,
                "session_id": str(session_payload["id"]),
                "memory_query": f"{query} {_companion_preview_text(str(followup_turn.get('content') or ''), max_chars=120)}".strip(),
                "knowledge_query": query,
                "max_memories": max_memories,
                "max_knowledge": max_knowledge,
                "max_recent_turns": max_recent_turns,
                "token_budget": token_budget,
                "bundle_id": bundle_id,
                "active_task_state": active_task_state,
                "recent_conversation": recent_conversation,
            }
        )
        workstream_card = _companion_workstream_card(workstream_payload, intelligence_report)
        ask_packet = {
            "mode": "workstream_followup",
            "question": normalized_question,
            "workstream_ref": f"workstream://{workstream_payload['id']}",
            "session_ref": f"session://{session_payload['id']}",
            "followup_turn_ref": _companion_turn_ref(followup_turn),
            "bundle_ref": f"bundle://{bundle['id']}",
            "prompt_id": prompt_id,
            "handoff_text": _companion_followup_handoff_text(
                question=normalized_question,
                workstream_card=workstream_card,
                session_payload=session_payload,
                followup_turn=followup_turn,
                bundle=bundle,
            ),
        }
        return {
            "generated_at": _companion_now(),
            "workstream": workstream_card,
            "selected_session": _companion_session_card(session_payload),
            "followup_turn": _companion_turn_card(followup_turn),
            "question": normalized_question,
            "bundle": bundle,
            "ask_packet": ask_packet,
        }

    def companion_sync_feed(
        self,
        *,
        activity_limit: int = 12,
        target_limit: int = 6,
        pairing_limit: int = 6,
        conflict_limit: int = 6,
    ) -> dict[str, Any]:
        self.vault.initialize()
        dashboard = self.transport_dashboard(
            sync_limit=max(target_limit, 1),
            mutation_limit=max(activity_limit, 1),
            pairing_limit=max(pairing_limit, 1),
            conflict_limit=max(conflict_limit, 1),
        )
        trust_devices = list((dashboard.get("trust_devices") or {}).get("devices") or [])
        trusted_devices = [
            _companion_transport_device_card(device)
            for device in trust_devices
            if str(device.get("trust_state") or "").strip() == "allow"
        ]
        review_devices = [
            _companion_transport_device_card(device)
            for device in trust_devices
            if str(device.get("trust_state") or "").strip() == "review"
        ]
        blocked_devices = [
            _companion_transport_device_card(device)
            for device in trust_devices
            if str(device.get("trust_state") or "").strip() == "block"
        ]
        open_pairings = [
            _companion_pairing_offer_card(offer)
            for offer in list((dashboard.get("pairing_offers") or {}).get("offers") or [])
            if str(offer.get("status") or "").strip() == "open" and not bool(offer.get("is_expired"))
        ][:pairing_limit]
        open_conflicts = [
            _companion_sync_conflict_card(conflict)
            for conflict in list((dashboard.get("sync_conflicts") or {}).get("conflicts") or [])
            if str(conflict.get("status") or "").strip() == "open"
        ][:conflict_limit]
        sync_targets = [
            _companion_sync_target_card(target)
            for target in list((dashboard.get("sync") or {}).get("targets") or [])[:target_limit]
        ]
        recent_activity = [
            _companion_transport_event_card(event)
            for event in list((dashboard.get("activity") or {}).get("events") or [])[:activity_limit]
        ]
        summary = dict(dashboard.get("summary") or {})
        summary["blocked_device_count"] = len(blocked_devices)
        return {
            "generated_at": _companion_now(),
            "summary": summary,
            "trusted_devices": trusted_devices,
            "review_devices": review_devices,
            "blocked_devices": blocked_devices,
            "open_pairing_offers": open_pairings,
            "sync_targets": sync_targets,
            "open_sync_conflicts": open_conflicts,
            "recent_activity": recent_activity,
        }

    def companion_pairing_offer_accept(
        self,
        *,
        pairing_offer_path: Path,
        reviewed_by: str,
        trust_state: str = "allow",
        label: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        result = accept_pairing_offer(
            layout=self.vault.layout,
            pairing_offer_path=pairing_offer_path,
            trust_state=trust_state,
            reviewed_by=reviewed_by,
            label=label,
            notes=notes,
        )
        return {
            "accepted_by": result["accepted_by"],
            "pairing_offer": _companion_pairing_offer_card(result["pairing_offer"]),
            "trust_entry": _companion_transport_device_card(result["trust_result"]["entry"]),
            "activity": _companion_transport_event_card(result["operation"]),
        }

    def companion_trust_device_set(
        self,
        *,
        device_id: str,
        trust_state: str,
        label: str | None = None,
        notes: str | None = None,
        allowed_transports: list[str] | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        result = set_replica_device_trust(
            layout=self.vault.layout,
            device_id=device_id,
            trust_state=trust_state,
            label=label,
            notes=notes,
            allowed_transports=allowed_transports,
        )
        return {
            "trust_entry": _companion_transport_device_card(result["entry"]),
            "activity": _companion_transport_event_card(result["operation"]),
        }

    def companion_sync_conflict_review(
        self,
        *,
        conflict_marker_path: Path,
        reviewed_by: str,
        resolution: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        result = review_sync_conflict(
            layout=self.vault.layout,
            conflict_marker_path=conflict_marker_path,
            reviewed_by=reviewed_by,
            resolution=resolution,
            notes=notes,
        )
        return {
            "conflict": _companion_sync_conflict_card(result["conflict_marker"]),
            "activity": _companion_transport_event_card(result["operation"]),
        }

    def workstream_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_workstreams(scope=scope, status=status, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def workstream_preview(
        self,
        session_id: str,
        *,
        limit: int = 5,
    ) -> dict[str, Any]:
        return self.vault.workstream_preview(session_id, limit=limit)

    def workstream_intelligence(
        self,
        workstream_id: str,
        *,
        limit: int = 6,
    ) -> dict[str, Any]:
        return self.vault.workstream_intelligence(workstream_id, limit=limit)

    def workstream_candidate_create(
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
        return self.vault.create_workstream_candidate(
            session_id,
            limit=limit,
            candidate_id=candidate_id,
            candidate_for=candidate_for,
            title=title,
            summary=summary,
            rationale=rationale,
            notes=notes,
        )

    def workstream_candidate_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        proposal_state: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_workstream_candidates(scope=scope, proposal_state=proposal_state, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def workstream_candidate_review(
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
        result = self.vault.review_workstream_candidate(
            candidate_id,
            decision=decision,
            reviewer=reviewer,
            notes=notes,
            workstream_id=workstream_id,
            policy_payload=policy_payload,
            backup_receipt=backup_receipt,
        )
        related_refs = []
        if isinstance(result.get("workstream"), dict) and str(result["workstream"].get("id") or "").strip():
            related_refs.append(f"workstream://{result['workstream']['id']}")
        self._record_mutation(
            mutation_kind="workstream_candidate.review",
            object_ref=f"workstream-candidate://{candidate_id}",
            actor=reviewer,
            decision=decision,
            scope=dict((result.get("candidate") or {}).get("scope") or {}),
            related_refs=related_refs,
            notes=notes,
            details={
                "proposal_state": (result.get("candidate") or {}).get("proposal_state"),
                "workstream_id": workstream_id or ((result.get("workstream") or {}).get("id") if isinstance(result.get("workstream"), dict) else None),
            },
        )
        return result

    def episode_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        session_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_episodes(scope=scope, session_id=session_id, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def episode_derive(self, session_id: str) -> dict[str, Any]:
        return self.vault.derive_episodes(session_id)

    def episode_synthesize(
        self,
        episode_id: str,
        *,
        knowledge_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        return self.vault.synthesize_episode(episode_id, knowledge_id=knowledge_id, title=title)

    def knowledge_export_note(
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
        return self.vault.export_knowledge_note(
            knowledge_id,
            output_path=output_path,
            canonical_target=canonical_target,
            privacy=privacy,
            status=status,
            note_id=note_id,
            title=title,
        )

    def memory_search(
        self,
        query: str,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        limit: int = 5,
        pinned_only: bool = False,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.search_memories(query, scope=scope, limit=limit, pinned_only=pinned_only)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def memory_candidate_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        proposal_state: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_memory_candidates(scope=scope, proposal_state=proposal_state, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def prompt_patch_list(
        self,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        proposal_state: str | None = None,
        prompt_asset_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_prompt_patches(
            scope=scope,
            proposal_state=proposal_state,
            prompt_asset_id=prompt_asset_id,
            limit=limit,
        )
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def knowledge_search(
        self,
        query: str,
        *,
        scope_kind: str | None = None,
        scope_value: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.search_knowledge(query, scope=scope, limit=limit)
        return [
            {
                "object_id": hit.object_id,
                "semantic_ref": hit.semantic_ref,
                "storage_ref": hit.storage_ref,
                "score": hit.score,
                "payload": hit.payload,
            }
            for hit in hits
        ]

    def context_build(self, request: dict[str, Any]) -> dict[str, Any]:
        active_task_state = tuple(
            ContextItemInput(ref=item["ref"], content=item["content"])
            for item in request.get("active_task_state", [])
        )
        recent_conversation = tuple(
            ContextItemInput(ref=item["ref"], content=item["content"])
            for item in request.get("recent_conversation", [])
        )
        return self.vault.build_context(
            ContextBuildRequest(
                scope_kind=request["scope_kind"],
                scope_value=request["scope_value"],
                task_label=request["task_label"],
                prompt_id=request.get("prompt_id"),
                session_id=request.get("session_id"),
                memory_query=request.get("memory_query", ""),
                knowledge_query=request.get("knowledge_query", ""),
                max_memories=int(request.get("max_memories", 5)),
                max_knowledge=int(request.get("max_knowledge", 4)),
                max_recent_turns=int(request.get("max_recent_turns", 6)),
                token_budget=int(request.get("token_budget", 12000)),
                bundle_id=request.get("bundle_id"),
                active_task_state=active_task_state,
                recent_conversation=recent_conversation,
            )
        )

    def audit_run(
        self,
        *,
        scope_kind: str,
        scope_value: str,
        subject_ref: str,
        claim_refs: list[str] | None = None,
        audit_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return self.vault.run_audit(
            scope_kind=scope_kind,
            scope_value=scope_value,
            subject_ref=subject_ref,
            claim_refs=claim_refs,
            audit_id=audit_id,
            notes=notes,
        )

    def audit_review(
        self,
        audit_id: str,
        *,
        decision: str,
        notes: str | None = None,
        override_verdict: str | None = None,
    ) -> dict[str, Any]:
        result = self.vault.review_audit(
            audit_id,
            decision=decision,
            notes=notes,
            override_verdict=override_verdict,
        )
        self._record_mutation(
            mutation_kind="audit.review",
            object_ref=f"audit://{audit_id}",
            actor="human_review",
            decision=decision,
            scope=dict(result.get("scope") or {}),
            notes=notes,
            details={
                "review_state": result.get("review_state"),
                "verdict": result.get("verdict"),
                "override_verdict": override_verdict,
            },
        )
        return result

    def memory_candidate_review(
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
        result = self.vault.review_memory_candidate(
            candidate_id,
            decision=decision,
            reviewer=reviewer,
            notes=notes,
            memory_id=memory_id,
            policy_payload=policy_payload,
            backup_receipt=backup_receipt,
        )
        related_refs = []
        if isinstance(result.get("memory"), dict) and str(result["memory"].get("id") or "").strip():
            related_refs.append(f"memory://{result['memory']['id']}")
        self._record_mutation(
            mutation_kind="memory_candidate.review",
            object_ref=f"memory-candidate://{candidate_id}",
            actor=reviewer,
            decision=decision,
            scope=dict((result.get("candidate") or {}).get("scope") or {}),
            related_refs=related_refs,
            notes=notes,
            details={
                "proposal_state": (result.get("candidate") or {}).get("proposal_state"),
                "memory_id": memory_id or ((result.get("memory") or {}).get("id") if isinstance(result.get("memory"), dict) else None),
            },
        )
        return result

    def prompt_patch_review(
        self,
        patch_id: str,
        *,
        decision: str,
        reviewer: str = "human_review",
        notes: str | None = None,
        policy_payload: dict[str, Any] | None = None,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.vault.review_prompt_patch(
            patch_id,
            decision=decision,
            reviewer=reviewer,
            notes=notes,
            policy_payload=policy_payload,
            backup_receipt=backup_receipt,
        )
        self._record_mutation(
            mutation_kind="prompt_patch.review",
            object_ref=f"prompt-patch://{patch_id}",
            actor=reviewer,
            decision=decision,
            scope=dict((result.get("patch") or {}).get("scope") or {}),
            related_refs=[
                f"prompt://{str((result.get('prompt') or {}).get('id') or '').strip()}"
            ]
            if isinstance(result.get("prompt"), dict) and str(result["prompt"].get("id") or "").strip()
            else None,
            notes=notes,
            details={"proposal_state": (result.get("patch") or {}).get("proposal_state")},
        )
        return result

    def prompt_eval_run(
        self,
        target_type: str,
        target_id: str,
        *,
        dataset_ref: str,
        assert_contains: list[str] | None = None,
        assert_not_contains: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return self.vault.run_prompt_eval(
            target_type,
            target_id,
            dataset_ref=dataset_ref,
            assert_contains=assert_contains,
            assert_not_contains=assert_not_contains,
            notes=notes,
        )

    def privacy_scan(
        self,
        text: str,
        *,
        source: str = "inline",
        max_findings: int = 25,
    ) -> dict[str, Any]:
        return scan_privacy_text(text, source=source, max_findings=max_findings).to_dict()

    def privacy_scan_files(
        self,
        file_paths: list[Path],
        *,
        source: str = "attachment",
        max_findings: int = 25,
        max_bytes: int = 262_144,
    ) -> dict[str, Any]:
        return scan_privacy_files(
            file_paths,
            source=source,
            max_findings=max_findings,
            max_bytes=max_bytes,
        )

    def context_receipt_emit(
        self,
        bundle: dict[str, Any],
        *,
        output_path: Path,
        plan_path: Path | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        return emit_context_bundle_receipt(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            bundle_payload=bundle,
            plan_path=plan_path,
            task_id=task_id,
        )

    def audit_receipt_emit(
        self,
        audit: dict[str, Any],
        *,
        output_path: Path,
        plan_path: Path | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        return emit_audit_receipt(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            audit_payload=audit,
            plan_path=plan_path,
            task_id=task_id,
        )

    def workstream_receipt_emit(
        self,
        workstream: dict[str, Any],
        *,
        output_path: Path,
        plan_path: Path | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        return emit_workstream_receipt(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            workstream_payload=workstream,
            plan_path=plan_path,
            task_id=task_id,
        )

    def workstream_candidate_receipt_emit(
        self,
        candidate: dict[str, Any],
        *,
        output_path: Path,
        plan_path: Path | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        return emit_workstream_candidate_receipt(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            candidate_payload=candidate,
            plan_path=plan_path,
            task_id=task_id,
        )

    def policy_check(
        self,
        *,
        policy_payload: dict[str, Any],
        operation: str,
        sensitivity: str,
        backup_receipt: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        policy = CtxVaultPolicy(policy_payload)
        return policy.evaluate_operation(
            operation=operation,
            sensitivity=sensitivity,
            backup_receipt=backup_receipt,
        ).to_dict()

    def export_check(
        self,
        *,
        policy_payload: dict[str, Any],
        sensitivity: str,
        exportable: bool,
        redaction_state: str,
        secret_refs: list[str] | None = None,
    ) -> dict[str, Any]:
        policy = CtxVaultPolicy(policy_payload)
        return policy.evaluate_export(
            sensitivity=sensitivity,
            exportable=exportable,
            redaction_state=redaction_state,
            secret_refs=secret_refs,
        ).to_dict()

    def adapter_status(self, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        registry = AdapterRegistry(profiles)
        return registry.list_profiles()

    def adapter_resolve(self, profiles: list[dict[str, Any]], capability: str) -> dict[str, Any]:
        registry = AdapterRegistry(profiles)
        return registry.resolve_capability(capability).to_dict()

    def adapter_healthcheck(self, *, target_kind: str = "agents-md", target_path: Path | None = None) -> dict[str, Any]:
        return projection_adapter_healthcheck(
            root=self.vault.layout.repo_root,
            target_kind=target_kind,
            target_path=target_path,
        )

    def plugin_status(self, manifests: list[dict[str, Any]]) -> list[dict[str, Any]]:
        registry = PluginRegistry(manifests)
        return registry.list_manifests()

    def plugin_resolve(self, manifests: list[dict[str, Any]], capability: str) -> dict[str, Any]:
        registry = PluginRegistry(manifests)
        return registry.resolve_capability(capability).to_dict()

    def plugin_execute(
        self,
        manifests: list[dict[str, Any]],
        capability: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        return self._local_plugin_executor_registry().execute(manifests, capability, arguments)

    def harness_agents_md_emit(
        self,
        *,
        workstream_id: str,
        output_path: Path,
        receipt_output_path: Path,
        memory_limit: int = 5,
    ) -> dict[str, Any]:
        workstream = self._load_object_payload("workstream", workstream_id)
        if workstream.get("approval_state") != "approved":
            raise ValueError(f"workstream {workstream_id} must be approved before projection")
        memories = self._load_projection_memories(scope=workstream["scope"], limit=memory_limit)
        return emit_agents_md_projection(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            receipt_output_path=receipt_output_path,
            workstream_payload=workstream,
            memory_payloads=memories,
        )

    def harness_claude_md_emit(
        self,
        *,
        workstream_id: str,
        output_path: Path,
        receipt_output_path: Path,
        memory_limit: int = 5,
    ) -> dict[str, Any]:
        workstream = self._load_object_payload("workstream", workstream_id)
        if workstream.get("approval_state") != "approved":
            raise ValueError(f"workstream {workstream_id} must be approved before projection")
        memories = self._load_projection_memories(scope=workstream["scope"], limit=memory_limit)
        return emit_claude_md_projection(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            receipt_output_path=receipt_output_path,
            workstream_payload=workstream,
            memory_payloads=memories,
        )

    def wiki_workstream_markdown_emit(
        self,
        *,
        workstream_id: str,
        output_path: Path,
        receipt_output_path: Path,
        memory_limit: int = 5,
    ) -> dict[str, Any]:
        workstream = self._load_object_payload("workstream", workstream_id)
        if workstream.get("approval_state") != "approved":
            raise ValueError(f"workstream {workstream_id} must be approved before projection")
        memories = self._load_projection_memories(scope=workstream["scope"], limit=memory_limit)
        return emit_wiki_workstream_md_projection(
            root=self.vault.layout.repo_root,
            output_path=output_path,
            receipt_output_path=receipt_output_path,
            workstream_payload=workstream,
            memory_payloads=memories,
        )

    def backup_emit(
        self,
        *,
        root: Path,
        output_path: Path,
        receipt_format: str,
        scope_kind: str,
        scope_value: str,
        max_age_hours: int = 24,
        restore_tested: bool = False,
        notes: str | None = None,
        plan_id: str | None = None,
        target: str | None = None,
    ) -> dict[str, Any]:
        return emit_backup_bundle(
            root=root,
            output_path=output_path,
            receipt_format=receipt_format,
            scope_kind=scope_kind,
            scope_value=scope_value,
            max_age_hours=max_age_hours,
            restore_tested=restore_tested,
            notes=notes,
            plan_id=plan_id,
            target=target,
        )

    def snapshot_create(
        self,
        *,
        scope_kind: str,
        scope_value: str,
        label: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return create_snapshot(
            root=self.vault.layout.repo_root,
            layout=self.vault.layout,
            scope_kind=scope_kind,
            scope_value=scope_value,
            label=label,
        )

    def snapshot_list(self, *, limit: int = 20) -> list[dict[str, Any]]:
        self.vault.initialize()
        return list_snapshots(layout=self.vault.layout, limit=limit)

    def snapshot_diff(self, *, base_snapshot_id: str, head_snapshot_id: str) -> dict[str, Any]:
        self.vault.initialize()
        return diff_snapshots(
            layout=self.vault.layout,
            base_snapshot_id=base_snapshot_id,
            head_snapshot_id=head_snapshot_id,
        )

    def snapshot_restore_plan(
        self,
        *,
        snapshot_id: str,
        include_workspace: bool = True,
        include_vault: bool = True,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return plan_restore(
            root=self.vault.layout.repo_root,
            layout=self.vault.layout,
            snapshot_id=snapshot_id,
            include_workspace=include_workspace,
            include_vault=include_vault,
        )

    def snapshot_restore_apply(
        self,
        *,
        snapshot_id: str,
        include_workspace: bool = True,
        include_vault: bool = True,
        allow_deletes: bool = False,
        reviewed_by: str | None = None,
        refresh_indexes: bool = True,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return apply_restore(
            root=self.vault.layout.repo_root,
            layout=self.vault.layout,
            snapshot_id=snapshot_id,
            include_workspace=include_workspace,
            include_vault=include_vault,
            allow_deletes=allow_deletes,
            reviewed_by=reviewed_by,
            refresh_indexes=refresh_indexes,
        )

    def sync_receipt_emit(
        self,
        *,
        snapshot_id: str,
        target: str,
        transport: str,
        device_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return emit_sync_receipt(
            layout=self.vault.layout,
            snapshot_id=snapshot_id,
            target=target,
            transport=transport,
            device_id=device_id,
            notes=notes,
        )

    def sync_status(self, *, limit: int = 50) -> dict[str, Any]:
        self.vault.initialize()
        return sync_status(layout=self.vault.layout, limit=limit)

    def mutation_list(self, *, limit: int = 50, mutation_kind: str | None = None) -> dict[str, Any]:
        self.vault.initialize()
        return list_mutations(layout=self.vault.layout, limit=limit, mutation_kind=mutation_kind)

    def transport_dashboard(
        self,
        *,
        sync_limit: int = 20,
        mutation_limit: int = 10,
        pairing_limit: int = 10,
        conflict_limit: int = 10,
        include_expired_pairings: bool = False,
    ) -> dict[str, Any]:
        self.vault.initialize()
        sync_payload = sync_status(layout=self.vault.layout, limit=sync_limit)
        mutations = list_mutations(layout=self.vault.layout, limit=mutation_limit)
        pairings = list_pairing_offers(
            layout=self.vault.layout,
            limit=pairing_limit,
            include_expired=include_expired_pairings,
        )
        trust_devices = list_replica_trust_devices(layout=self.vault.layout)
        conflicts = list_sync_conflicts(layout=self.vault.layout, limit=conflict_limit)
        activity = list_transport_events(layout=self.vault.layout, limit=max(sync_limit, mutation_limit, pairing_limit, conflict_limit))
        allow_devices = [
            device
            for device in list(trust_devices.get("devices") or [])
            if str(device.get("trust_state") or "").strip() == "allow"
        ]
        review_devices = [
            device
            for device in list(trust_devices.get("devices") or [])
            if str(device.get("trust_state") or "").strip() == "review"
        ]
        open_conflicts = [
            conflict
            for conflict in list(conflicts.get("conflicts") or [])
            if str(conflict.get("status") or "").strip() == "open"
        ]
        open_pairings = [
            offer
            for offer in list(pairings.get("offers") or [])
            if str(offer.get("status") or "").strip() == "open" and not bool(offer.get("is_expired"))
        ]
        return {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "summary": {
                "latest_local_snapshot_id": (
                    None
                    if not isinstance(sync_payload.get("latest_local_snapshot"), dict)
                    else sync_payload["latest_local_snapshot"].get("snapshot_id")
                ),
                "current_local_snapshot_id": (
                    None
                    if not isinstance(sync_payload.get("current_local_snapshot"), dict)
                    else sync_payload["current_local_snapshot"].get("snapshot_id")
                ),
                "out_of_date_target_count": int((sync_payload.get("summary") or {}).get("out_of_date_target_count") or 0),
                "trusted_device_count": len(allow_devices),
                "review_device_count": len(review_devices),
                "open_pairing_offer_count": len(open_pairings),
                "open_sync_conflict_count": len(open_conflicts),
                "recent_mutation_count": int((mutations.get("summary") or {}).get("returned_count") or 0),
                "recent_transport_event_count": int((activity.get("summary") or {}).get("returned_count") or 0),
            },
            "sync": sync_payload,
            "mutations": mutations,
            "pairing_offers": pairings,
            "trust_devices": trust_devices,
            "sync_conflicts": conflicts,
            "activity": activity,
        }

    def snapshot_lineage(
        self,
        *,
        snapshot_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return snapshot_lineage(
            layout=self.vault.layout,
            snapshot_id=snapshot_id,
            limit=limit,
        )

    def snapshot_provenance(
        self,
        *,
        snapshot_id: str,
        limit: int = 100,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return snapshot_provenance(
            layout=self.vault.layout,
            snapshot_id=snapshot_id,
            limit=limit,
        )

    def sync_manifest_emit(
        self,
        *,
        target: str,
        transport: str,
        device_id: str | None = None,
        snapshot_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return emit_sync_manifest(
            layout=self.vault.layout,
            target=target,
            transport=transport,
            device_id=device_id,
            snapshot_id=snapshot_id,
            notes=notes,
        )

    def sync_manifest_apply(self, *, sync_manifest_path: Path) -> dict[str, Any]:
        self.vault.initialize()
        return apply_sync_manifest(
            layout=self.vault.layout,
            sync_manifest_path=sync_manifest_path,
        )

    def local_backup_write(
        self,
        *,
        target: str,
        scope_kind: str = "project",
        scope_value: str = "ctxvault",
        label: str | None = None,
        transport: str = "local_copy",
        device_id: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return write_local_backup(
            root=self.vault.layout.repo_root,
            layout=self.vault.layout,
            target=target,
            scope_kind=scope_kind,
            scope_value=scope_value,
            label=label,
            transport=transport,
            device_id=device_id,
            notes=notes,
        )

    def replica_verify(
        self,
        *,
        replica_root: Path,
        snapshot_id: str | None = None,
        sync_manifest_path: Path | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return verify_replica(
            replica_root=replica_root,
            snapshot_id=snapshot_id,
            sync_manifest_path=sync_manifest_path,
        )

    def replica_import(
        self,
        *,
        replica_root: Path,
        snapshot_id: str | None = None,
        sync_manifest_path: Path | None = None,
        trust_policy: dict[str, Any] | None = None,
        reviewed_by: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return import_replica(
            layout=self.vault.layout,
            replica_root=replica_root,
            snapshot_id=snapshot_id,
            sync_manifest_path=sync_manifest_path,
            trust_policy=trust_policy,
            trust_registry=load_replica_trust_registry(layout=self.vault.layout),
            reviewed_by=reviewed_by,
        )

    def replica_apply(
        self,
        *,
        replica_root: Path,
        snapshot_id: str | None = None,
        sync_manifest_path: Path | None = None,
        include_workspace: bool = True,
        include_vault: bool = True,
        allow_deletes: bool = False,
        reviewed_by: str | None = None,
        refresh_indexes: bool = True,
        trust_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return apply_replica(
            root=self.vault.layout.repo_root,
            layout=self.vault.layout,
            replica_root=replica_root,
            snapshot_id=snapshot_id,
            sync_manifest_path=sync_manifest_path,
            include_workspace=include_workspace,
            include_vault=include_vault,
            allow_deletes=allow_deletes,
            reviewed_by=reviewed_by,
            refresh_indexes=refresh_indexes,
            trust_policy=trust_policy,
            trust_registry=load_replica_trust_registry(layout=self.vault.layout),
        )

    def replica_trust_evaluate(
        self,
        *,
        replica_root: Path,
        snapshot_id: str | None = None,
        sync_manifest_path: Path | None = None,
        trust_policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return evaluate_replica_trust(
            replica_root=replica_root,
            snapshot_id=snapshot_id,
            sync_manifest_path=sync_manifest_path,
            trust_policy=trust_policy,
            trust_registry=load_replica_trust_registry(layout=self.vault.layout),
        )

    def replica_trust_list(self) -> dict[str, Any]:
        self.vault.initialize()
        return list_replica_trust_devices(layout=self.vault.layout)

    def replica_pairing_offer_emit(
        self,
        *,
        device_id: str,
        label: str | None = None,
        notes: str | None = None,
        allowed_transports: list[str] | None = None,
        pairing_id: str | None = None,
        expires_in_hours: int = 24,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return emit_pairing_offer(
            layout=self.vault.layout,
            device_id=device_id,
            label=label,
            notes=notes,
            allowed_transports=allowed_transports,
            pairing_id=pairing_id,
            expires_in_hours=expires_in_hours,
        )

    def replica_pairing_offer_list(
        self,
        *,
        limit: int = 50,
        include_expired: bool = False,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return list_pairing_offers(
            layout=self.vault.layout,
            limit=limit,
            include_expired=include_expired,
        )

    def replica_pairing_offer_accept(
        self,
        *,
        pairing_offer_path: Path,
        trust_state: str = "allow",
        reviewed_by: str,
        label: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return accept_pairing_offer(
            layout=self.vault.layout,
            pairing_offer_path=pairing_offer_path,
            trust_state=trust_state,
            reviewed_by=reviewed_by,
            label=label,
            notes=notes,
        )

    def replica_trust_set(
        self,
        *,
        device_id: str,
        trust_state: str,
        label: str | None = None,
        notes: str | None = None,
        allowed_transports: list[str] | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return set_replica_device_trust(
            layout=self.vault.layout,
            device_id=device_id,
            trust_state=trust_state,
            label=label,
            notes=notes,
            allowed_transports=allowed_transports,
        )

    def sync_conflict_review(
        self,
        *,
        conflict_marker_path: Path,
        reviewed_by: str,
        resolution: str,
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return review_sync_conflict(
            layout=self.vault.layout,
            conflict_marker_path=conflict_marker_path,
            reviewed_by=reviewed_by,
            resolution=resolution,
            notes=notes,
        )

    def sync_conflict_list(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> dict[str, Any]:
        self.vault.initialize()
        return list_sync_conflicts(layout=self.vault.layout, limit=limit, status=status)

    def _load_object_payload(self, object_kind: str, object_id: str) -> dict[str, Any]:
        self.vault.initialize()
        object_path = self.vault.layout.objects_dir / object_kind / f"{object_id}.json"
        if not object_path.exists():
            raise ValueError(f"{object_kind} object is missing at {object_path}")
        envelope = json.loads(object_path.read_text(encoding="utf-8"))
        payload = envelope.get("payload")
        if not isinstance(payload, dict):
            raise ValueError(f"stored payload for {object_kind} {object_id} is invalid")
        return payload

    def _resolve_companion_workstream(
        self,
        *,
        workstream_id: str | None,
        scope_kind: str | None,
        scope_value: str | None,
    ) -> dict[str, Any]:
        if workstream_id:
            return self._load_object_payload("workstream", workstream_id)
        scope = (scope_kind, scope_value) if scope_kind and scope_value else None
        hits = self.vault.list_workstreams(scope=scope, status="active", limit=1)
        if not hits:
            scope_label = f"{scope_kind}:{scope_value}" if scope is not None else "the current vault"
            raise ValueError(f"no active workstream is available in {scope_label}")
        return hits[0].payload

    def _resolve_companion_shared_root(self, shared_root: Path | None) -> Path:
        if shared_root is None:
            return self.vault.layout.repo_root.resolve()
        path = Path(shared_root).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.vault.layout.repo_root / path).resolve()

    def _companion_workstream_session_payloads(self, workstream_payload: dict[str, Any]) -> list[dict[str, Any]]:
        session_ids = _companion_session_refs(workstream_payload)
        session_payloads: list[dict[str, Any]] = []
        for session_id in session_ids:
            try:
                session_payloads.append(self._load_object_payload("session", session_id))
            except ValueError:
                continue
        if not session_payloads:
            raise ValueError(f"workstream {workstream_payload['id']} does not reference stored sessions")
        session_payloads.sort(key=_companion_session_sort_key)
        return session_payloads

    def _resolve_companion_workstream_session(
        self,
        workstream_payload: dict[str, Any],
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        session_payloads = self._companion_workstream_session_payloads(workstream_payload)
        if session_id is None:
            return session_payloads[-1]
        for payload in session_payloads:
            if str(payload.get("id") or "") == session_id:
                return payload
        raise ValueError(f"session {session_id} is not linked to workstream {workstream_payload['id']}")

    def _companion_session_turn_payloads(
        self,
        session_payload: dict[str, Any],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        scope_payload = session_payload.get("scope") if isinstance(session_payload.get("scope"), dict) else {}
        scope = None
        if scope_payload.get("kind") is not None and scope_payload.get("value") is not None:
            scope = (str(scope_payload["kind"]), str(scope_payload["value"]))
        hits = self.vault._recent_turn_hits(
            scope=scope,
            limit=limit,
            session_id=str(session_payload["id"]),
        )
        turn_payloads = [hit.payload for hit in hits]
        turn_payloads.sort(
            key=lambda payload: (
                str(payload.get("created_at") or ""),
                int(payload.get("ordinal") or 0),
                str(payload.get("id") or ""),
            )
        )
        return turn_payloads[-limit:]

    def _load_projection_memories(
        self,
        *,
        scope: dict[str, Any],
        limit: int,
    ) -> list[dict[str, Any]]:
        self.vault.initialize()
        memory_dir = self.vault.layout.objects_dir / "memory"
        if not memory_dir.exists():
            return []
        candidates: list[dict[str, Any]] = []
        for object_path in sorted(memory_dir.glob("*.json")):
            envelope = json.loads(object_path.read_text(encoding="utf-8"))
            payload = envelope.get("payload")
            if not isinstance(payload, dict):
                continue
            payload_scope = payload.get("scope")
            if payload_scope != scope:
                continue
            if payload.get("approval_state") != "approved":
                continue
            if payload.get("status") not in {None, "active"}:
                continue
            if not bool(payload.get("exportable", False)):
                continue
            candidates.append(payload)
        candidates.sort(
            key=lambda payload: (
                not bool(payload.get("retrieval_policy", {}).get("pinned", False)),
                -float(payload.get("retrieval_policy", {}).get("priority", 0.0) or 0.0),
                str(payload.get("id", "")),
            )
        )
        return candidates[:limit]

    def _local_plugin_executor_registry(self) -> LocalPluginExecutorRegistry:
        return LocalPluginExecutorRegistry(
            {
                "projection.harness.agents-md": self._execute_projection_harness_agents_md,
                "projection.harness.claude-md": self._execute_projection_harness_claude_md,
                "projection.wiki.markdown-workstream": self._execute_projection_wiki_markdown_workstream,
            }
        )

    def _execute_projection_harness_agents_md(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.harness_agents_md_emit(
            workstream_id=str(arguments["workstream_id"]),
            output_path=Path(str(arguments["output_path"])),
            receipt_output_path=Path(str(arguments["receipt_output_path"])),
            memory_limit=int(arguments.get("memory_limit", 5)),
        )

    def _execute_projection_harness_claude_md(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.harness_claude_md_emit(
            workstream_id=str(arguments["workstream_id"]),
            output_path=Path(str(arguments["output_path"])),
            receipt_output_path=Path(str(arguments["receipt_output_path"])),
            memory_limit=int(arguments.get("memory_limit", 5)),
        )

    def _execute_projection_wiki_markdown_workstream(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.wiki_workstream_markdown_emit(
            workstream_id=str(arguments["workstream_id"]),
            output_path=Path(str(arguments["output_path"])),
            receipt_output_path=Path(str(arguments["receipt_output_path"])),
            memory_limit=int(arguments.get("memory_limit", 5)),
        )


def _companion_session_card(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(payload.get("id") or ""),
        "title": str(payload.get("title") or payload.get("id") or "").strip(),
        "task_label": str(payload.get("task_label") or "").strip(),
        "status": str(payload.get("status") or "active").strip() or "active",
        "turn_count": int(payload.get("turn_count") or 0),
        "started_at": payload.get("started_at"),
        "ended_at": payload.get("ended_at"),
        "client": str(payload.get("client") or "").strip(),
        "source_app": str(payload.get("source_app") or payload.get("client") or "unknown").strip(),
        "source_surface": str(payload.get("source_surface") or "unknown").strip(),
        "source_format": str(payload.get("source_format") or "unknown").strip(),
        "capture_method": str(payload.get("capture_method") or "unknown").strip(),
        "imported_via": str(payload.get("imported_via") or "").strip(),
        "scope": dict(payload.get("scope") or {}),
    }


def _companion_session_picker_card(
    payload: dict[str, Any],
    *,
    turn_payloads: list[dict[str, Any]],
    selected_session_id: str,
) -> dict[str, Any]:
    card = _companion_session_card(payload)
    latest_turn = turn_payloads[-1] if turn_payloads else None
    latest_assistant_turn = next(
        (turn_payload for turn_payload in reversed(turn_payloads) if str(turn_payload.get("role") or "").strip() == "assistant"),
        None,
    )
    card.update(
        {
            "is_selected": str(payload.get("id") or "") == selected_session_id,
            "last_activity_at": (latest_turn or {}).get("created_at") or payload.get("ended_at") or payload.get("started_at"),
            "latest_turn_ref": _companion_turn_ref(latest_turn),
            "latest_turn_preview": _companion_preview_text(str((latest_turn or {}).get("content") or "")) if latest_turn else None,
            "latest_assistant_turn_ref": _companion_turn_ref(latest_assistant_turn),
            "latest_assistant_preview": (
                _companion_preview_text(str((latest_assistant_turn or {}).get("content") or ""))
                if latest_assistant_turn
                else None
            ),
            "recent_turns": [_companion_turn_card(turn_payload) for turn_payload in turn_payloads],
        }
    )
    return card


def _companion_workstream_card(workstream_payload: dict[str, Any], intelligence_report: dict[str, Any]) -> dict[str, Any]:
    current_state = intelligence_report.get("current_state") if isinstance(intelligence_report.get("current_state"), dict) else {}
    promotion_profile = intelligence_report.get("promotion_profile") if isinstance(intelligence_report.get("promotion_profile"), dict) else {}
    return {
        "id": str(workstream_payload.get("id") or ""),
        "title": str(workstream_payload.get("title") or workstream_payload.get("id") or "").strip(),
        "summary": str(workstream_payload.get("summary") or "").strip(),
        "status": str(workstream_payload.get("status") or "active").strip() or "active",
        "approval_state": str(workstream_payload.get("approval_state") or "").strip(),
        "updated_at": workstream_payload.get("updated_at"),
        "task_labels": [str(label).strip() for label in list(workstream_payload.get("task_labels") or []) if str(label).strip()][:4],
        "focus_terms": [str(term).strip() for term in list(workstream_payload.get("recurring_terms") or []) if str(term).strip()][:6],
        "open_questions": [str(item).strip() for item in list(current_state.get("open_questions") or []) if str(item).strip()][:3],
        "reusable_judgments": [str(item).strip() for item in list(current_state.get("reusable_judgments") or []) if str(item).strip()][:4],
        "promotion_readiness": str(promotion_profile.get("readiness") or "").strip(),
        "source_ref_count": len(list(workstream_payload.get("source_refs") or [])),
        "knowledge_ref_count": len(list(workstream_payload.get("knowledge_refs") or [])),
        "scope": dict(workstream_payload.get("scope") or {}),
    }


def _companion_transport_device_card(device: dict[str, Any]) -> dict[str, Any]:
    return {
        "device_id": str(device.get("device_id") or "").strip(),
        "label": str(device.get("label") or "").strip() or None,
        "trust_state": str(device.get("trust_state") or "review").strip() or "review",
        "notes": str(device.get("notes") or "").strip() or None,
        "allowed_transports": [
            str(item).strip()
            for item in list(device.get("allowed_transports") or [])
            if str(item).strip()
        ],
        "updated_at": device.get("updated_at"),
        "actions": ["set_allow", "set_review", "set_block"],
    }


def _companion_pairing_offer_card(offer: dict[str, Any]) -> dict[str, Any]:
    status = str(offer.get("status") or "open").strip() or "open"
    is_expired = bool(offer.get("is_expired"))
    actions = ["accept_pairing"] if status == "open" and not is_expired else []
    return {
        "pairing_id": str(offer.get("pairing_id") or "").strip(),
        "pairing_offer_path": str(offer.get("pairing_offer_path") or "").strip(),
        "device_id": str(offer.get("device_id") or "").strip(),
        "label": str(offer.get("label") or "").strip() or None,
        "notes": str(offer.get("notes") or "").strip() or None,
        "status": status,
        "is_expired": is_expired,
        "created_at": offer.get("created_at"),
        "expires_at": offer.get("expires_at"),
        "accepted_at": offer.get("accepted_at"),
        "accepted_by": str(offer.get("accepted_by") or "").strip() or None,
        "accepted_trust_state": str(offer.get("accepted_trust_state") or "").strip() or None,
        "allowed_transports": [
            str(item).strip()
            for item in list(offer.get("allowed_transports") or [])
            if str(item).strip()
        ],
        "actions": actions,
    }


def _companion_sync_target_card(target: dict[str, Any]) -> dict[str, Any]:
    pending_snapshot_ids = [
        str(item).strip()
        for item in list(target.get("pending_snapshot_ids") or [])
        if str(item).strip()
    ]
    return {
        "endpoint_key": str(target.get("endpoint_key") or "").strip(),
        "device_id": str(target.get("device_id") or "").strip() or None,
        "target": str(target.get("target") or "").strip() or None,
        "transport": str(target.get("transport") or "").strip() or None,
        "state": str(target.get("state") or "").strip() or "unknown",
        "snapshot_id": str(target.get("snapshot_id") or "").strip() or None,
        "snapshot_lag": target.get("snapshot_lag"),
        "pending_snapshot_ids": pending_snapshot_ids,
        "pending_snapshot_count": len(pending_snapshot_ids),
        "latest_sync_at": target.get("latest_sync_at"),
    }


def _companion_sync_conflict_card(conflict: dict[str, Any]) -> dict[str, Any]:
    status = str(conflict.get("status") or "open").strip() or "open"
    actions = ["keep_local", "accept_remote", "needs_followup"] if status == "open" else []
    return {
        "id": str(conflict.get("id") or "").strip(),
        "conflict_marker_path": str(conflict.get("conflict_marker_path") or "").strip(),
        "status": status,
        "reason": str(conflict.get("reason") or "").strip() or None,
        "requires_review": bool(conflict.get("requires_review")),
        "created_at": conflict.get("created_at"),
        "reviewed_at": conflict.get("reviewed_at"),
        "reviewed_by": str(conflict.get("reviewed_by") or "").strip() or None,
        "resolution": str(conflict.get("resolution") or "").strip() or None,
        "local_snapshot_id": str(conflict.get("local_snapshot_id") or "").strip() or None,
        "incoming_snapshot_id": str(conflict.get("incoming_snapshot_id") or "").strip() or None,
        "replica_root": str(conflict.get("replica_root") or "").strip() or None,
        "actions": actions,
    }


def _companion_transport_event_card(event: dict[str, Any]) -> dict[str, Any]:
    operation = str(event.get("operation") or "").strip() or "unknown"
    return {
        "timestamp": event.get("timestamp"),
        "operation": operation,
        "headline": _companion_transport_event_headline(event),
        "device_id": str(event.get("device_id") or "").strip() or None,
        "target": str(event.get("target") or "").strip() or None,
        "snapshot_id": str(event.get("snapshot_id") or "").strip() or None,
        "pairing_id": str(event.get("pairing_id") or "").strip() or None,
        "conflict_id": str(event.get("conflict_id") or "").strip() or None,
        "mutation_kind": str(event.get("mutation_kind") or "").strip() or None,
        "trust_state": str(event.get("trust_state") or "").strip() or None,
        "resolution": str(event.get("resolution") or "").strip() or None,
    }


def _companion_transport_event_headline(event: dict[str, Any]) -> str:
    operation = str(event.get("operation") or "").strip() or "unknown"
    if operation == "replica.pairing-offer":
        device_id = str(event.get("device_id") or "").strip() or "unknown device"
        return f"Pairing offer created for {device_id}"
    if operation == "replica.pairing-accept":
        device_id = str(event.get("device_id") or "").strip() or "unknown device"
        return f"Paired and trusted {device_id}"
    if operation == "replica.trust-set":
        device_id = str(event.get("device_id") or "").strip() or "unknown device"
        trust_state = str(event.get("trust_state") or "").strip() or "review"
        return f"Trust set to {trust_state} for {device_id}"
    if operation == "sync.conflict-marker":
        incoming = str(event.get("incoming_snapshot_id") or "").strip() or "incoming snapshot"
        return f"Sync conflict opened for {incoming}"
    if operation == "sync.conflict-review":
        resolution = str(event.get("resolution") or "").strip() or "reviewed"
        return f"Sync conflict reviewed: {resolution}"
    if operation == "sync.receipt":
        target = str(event.get("target") or "").strip() or "target"
        return f"Sync receipt recorded for {target}"
    if operation == "snapshot.create":
        snapshot_id = str(event.get("snapshot_id") or "").strip() or "snapshot"
        return f"Snapshot created: {snapshot_id}"
    if operation == "snapshot.restore":
        snapshot_id = str(event.get("snapshot_id") or "").strip() or "snapshot"
        return f"Snapshot restored: {snapshot_id}"
    if operation.startswith("mutation."):
        mutation_kind = str(event.get("mutation_kind") or "").strip() or "governed write"
        return f"Governed mutation recorded: {mutation_kind}"
    return operation.replace(".", " ")


def _companion_review_card(queue_kind: str, hit: Any) -> dict[str, Any]:
    payload = hit.payload
    source_refs = list(payload.get("source_refs") or [])
    secret_refs = list(payload.get("secret_refs") or [])
    if queue_kind == "memory_candidate":
        title = str(payload.get("type") or "memory_candidate").replace("_", " ").strip().title()
        summary = str(payload.get("statement") or "").strip()
    elif queue_kind == "workstream_candidate":
        title = str(payload.get("title") or hit.object_id).strip()
        summary = str(payload.get("summary") or "").strip()
    else:
        title = str(payload.get("prompt_asset_id") or hit.object_id).strip()
        summary = str(payload.get("rationale") or "").strip()
    ranking_inputs = _review_ranking_inputs(
        queue_kind=queue_kind,
        object_id=hit.object_id,
        payload=payload,
        source_refs=source_refs,
        secret_refs=secret_refs,
        summary=summary,
    )
    return {
        "queue_kind": queue_kind,
        "object_id": hit.object_id,
        "semantic_ref": hit.semantic_ref,
        "storage_ref": hit.storage_ref,
        "title": title,
        "summary": summary,
        "proposal_state": str(payload.get("proposal_state") or "").strip(),
        "confidence": float(payload.get("confidence") or 0.0),
        "created_at": payload.get("created_at"),
        "candidate_for": str(payload.get("candidate_for") or "").strip() or None,
        "source_ref_count": len(source_refs),
        "ranking_inputs": ranking_inputs,
        "recommended_bucket": ranking_inputs["recommended_bucket"],
        "ranking_score": ranking_inputs["ranking_score"],
    }


def _companion_review_sort_key(item: dict[str, Any]) -> tuple[float, str, float, str]:
    return (
        float(item.get("ranking_score") or 0.0),
        str(item.get("created_at") or ""),
        float(item.get("confidence") or 0.0),
        str(item.get("object_id") or ""),
    )


def _review_ranking_inputs(
    *,
    queue_kind: str,
    object_id: str,
    payload: dict[str, Any],
    source_refs: list[str],
    secret_refs: list[str],
    summary: str,
) -> dict[str, Any]:
    sensitivity = str(payload.get("sensitivity") or "internal").strip() or "internal"
    candidate_for = str(payload.get("candidate_for") or "").strip()
    evidence_strength = "direct" if source_refs else "missing"
    source_freshness = "recent" if payload.get("created_at") else "unknown"
    urgency = "active_workstream" if candidate_for or queue_kind == "prompt_patch" else "routine"
    reuse_value = "high" if queue_kind in {"prompt_patch", "workstream_candidate"} or len(source_refs) >= 2 else "medium"
    risk = _review_risk(queue_kind=queue_kind, sensitivity=sensitivity, secret_refs=secret_refs)
    review_effort = "large" if len(summary) > 280 or len(source_refs) > 5 else "medium" if queue_kind == "prompt_patch" else "small"
    harness_surface_risk = "medium" if queue_kind == "prompt_patch" else "low"
    stale_projection_risk = queue_kind == "prompt_patch"
    recommended_bucket = _review_bucket(
        risk=risk,
        evidence_strength=evidence_strength,
        queue_kind=queue_kind,
        stale_projection_risk=stale_projection_risk,
    )
    ranking_score = _review_ranking_score(
        risk=risk,
        reuse_value=reuse_value,
        urgency=urgency,
        evidence_strength=evidence_strength,
        stale_projection_risk=stale_projection_risk,
    )
    return {
        "candidate_ref": f"{_review_ref_prefix(queue_kind)}://{object_id}",
        "candidate_kind": queue_kind,
        "source_freshness": source_freshness,
        "reuse_value": reuse_value,
        "urgency": urgency,
        "risk": risk,
        "sensitivity": sensitivity,
        "evidence_strength": evidence_strength,
        "duplicate_score": 0.0,
        "harness_surface_risk": harness_surface_risk,
        "stale_projection_risk": stale_projection_risk,
        "review_effort": review_effort,
        "recommended_bucket": recommended_bucket,
        "ranking_reasons": _review_ranking_reasons(
            queue_kind=queue_kind,
            risk=risk,
            reuse_value=reuse_value,
            evidence_strength=evidence_strength,
            stale_projection_risk=stale_projection_risk,
        ),
        "ranking_score": ranking_score,
        "ranking_semantics": "advisory_only_no_auto_promotion",
    }


def _review_ref_prefix(queue_kind: str) -> str:
    return {
        "memory_candidate": "memory-candidate",
        "workstream_candidate": "workstream-candidate",
        "prompt_patch": "prompt-patch",
    }.get(queue_kind, queue_kind.replace("_", "-"))


def _review_risk(*, queue_kind: str, sensitivity: str, secret_refs: list[str]) -> str:
    if secret_refs or sensitivity in {"sensitive", "restricted"}:
        return "high"
    if queue_kind == "prompt_patch" or sensitivity == "internal":
        return "medium"
    return "low"


def _review_bucket(*, risk: str, evidence_strength: str, queue_kind: str, stale_projection_risk: bool) -> str:
    if risk == "high" or stale_projection_risk:
        return "review_first"
    if risk == "low" and evidence_strength == "direct" and queue_kind != "prompt_patch":
        return "batch_candidate"
    return "normal"


def _review_ranking_score(
    *,
    risk: str,
    reuse_value: str,
    urgency: str,
    evidence_strength: str,
    stale_projection_risk: bool,
) -> float:
    score = 0.0
    score += {"low": 1.0, "medium": 2.0, "high": 3.0}.get(risk, 1.0)
    score += {"medium": 1.0, "high": 2.0}.get(reuse_value, 0.0)
    score += 1.0 if urgency == "active_workstream" else 0.0
    score += 1.0 if evidence_strength == "direct" else 0.0
    score += 1.0 if stale_projection_risk else 0.0
    return score


def _review_ranking_reasons(
    *,
    queue_kind: str,
    risk: str,
    reuse_value: str,
    evidence_strength: str,
    stale_projection_risk: bool,
) -> list[str]:
    reasons = [
        f"{queue_kind.replace('_', ' ')} candidate has {risk} review risk",
        f"reuse value is {reuse_value}",
        f"evidence strength is {evidence_strength}",
    ]
    if stale_projection_risk:
        reasons.append("candidate may affect active projected harness instructions")
    return reasons


def _companion_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _companion_generated_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%dt%H%M%Sz').lower()}_{uuid4().hex[:8]}"


def _companion_string_list(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _companion_unique_refs(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _companion_merge_notes(*values: str | None) -> str | None:
    parts = [str(value).strip() for value in values if str(value or "").strip()]
    if not parts:
        return None
    return "\n\n".join(parts)


def _companion_capture_notes(
    *,
    notes: str | None,
    source_app: str,
    source_surface: str,
    source_format: str,
    capture_method: str,
    imported_via: str,
) -> str:
    metadata_lines = [
        "Companion capture metadata:",
        f"source_app={source_app}",
        f"source_surface={source_surface}",
        f"source_format={source_format}",
        f"capture_method={capture_method}",
        f"imported_via={imported_via}",
    ]
    extra_notes = str(notes or "").strip()
    if extra_notes:
        metadata_lines.extend(["", extra_notes])
    return "\n".join(metadata_lines)


def _companion_turn_ref(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    turn_id = str(payload.get("id") or "").strip()
    if not turn_id:
        return None
    return f"turn://{turn_id}"


def _companion_turn_card(payload: dict[str, Any]) -> dict[str, Any]:
    content = str(payload.get("content") or "").strip()
    return {
        "id": str(payload.get("id") or ""),
        "ref": _companion_turn_ref(payload),
        "role": str(payload.get("role") or "unknown").strip() or "unknown",
        "ordinal": int(payload.get("ordinal") or 0),
        "created_at": payload.get("created_at"),
        "content_preview": _companion_preview_text(content),
        "content": content,
    }


def _companion_preview_text(text: str, *, max_chars: int = 160) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    if max_chars <= 3:
        return normalized[:max_chars]
    return normalized[: max_chars - 3].rstrip() + "..."


def _companion_resolve_followup_turn(
    turn_payloads: list[dict[str, Any]],
    *,
    turn_ref: str | None,
) -> dict[str, Any]:
    if not turn_payloads:
        raise ValueError("selected session does not contain stored turns")
    if turn_ref:
        normalized_ref = str(turn_ref).strip()
        turn_id = normalized_ref.replace("turn://", "", 1) if normalized_ref.startswith("turn://") else normalized_ref
        for payload in turn_payloads:
            if str(payload.get("id") or "") == turn_id:
                return payload
        raise ValueError(f"turn {turn_id} is not available in the selected session")
    latest_assistant_turn = next(
        (payload for payload in reversed(turn_payloads) if str(payload.get("role") or "").strip() == "assistant"),
        None,
    )
    return latest_assistant_turn or turn_payloads[-1]


def _companion_active_task_state(
    workstream_payload: dict[str, Any],
    *,
    intelligence_report: dict[str, Any],
) -> list[dict[str, str]]:
    current_state = intelligence_report.get("current_state") if isinstance(intelligence_report.get("current_state"), dict) else {}
    workstream_ref = f"workstream://{workstream_payload['id']}"
    items = [
        {
            "ref": workstream_ref,
            "content": f"active workstream: {str(workstream_payload.get('summary') or workstream_payload.get('title') or '').strip()}",
        }
    ]
    reusable_judgments = [str(item).strip() for item in list(current_state.get("reusable_judgments") or []) if str(item).strip()]
    if reusable_judgments:
        items.append(
            {
                "ref": workstream_ref,
                "content": "reusable judgments: " + "; ".join(reusable_judgments[:4]),
            }
        )
    open_questions = [str(item).strip() for item in list(current_state.get("open_questions") or []) if str(item).strip()]
    if open_questions:
        items.append(
            {
                "ref": workstream_ref,
                "content": "open questions: " + "; ".join(open_questions[:3]),
            }
        )
    return items


def _companion_followup_state_item(session_payload: dict[str, Any], followup_turn: dict[str, Any]) -> dict[str, str]:
    session_label = str(session_payload.get("title") or session_payload.get("id") or "").strip()
    role = str(followup_turn.get("role") or "unknown").strip() or "unknown"
    preview = _companion_preview_text(str(followup_turn.get("content") or ""), max_chars=140)
    return {
        "ref": _companion_turn_ref(followup_turn) or f"session://{session_payload['id']}",
        "content": f"follow-up anchor in {session_label}: {role}: {preview}",
    }


def _companion_context_turn_item(turn_payload: dict[str, Any]) -> dict[str, str]:
    role = str(turn_payload.get("role") or "unknown").strip() or "unknown"
    content = str(turn_payload.get("content") or "").strip()
    return {
        "ref": _companion_turn_ref(turn_payload) or "",
        "content": f"{role}: {content}" if content else role,
    }


def _companion_ask_query(
    question: str,
    *,
    workstream_payload: dict[str, Any],
    intelligence_report: dict[str, Any],
) -> str:
    current_state = intelligence_report.get("current_state") if isinstance(intelligence_report.get("current_state"), dict) else {}
    parts = [
        question,
        str(workstream_payload.get("title") or "").strip(),
        *[str(label).strip() for label in list(workstream_payload.get("task_labels") or []) if str(label).strip()][:2],
        *[str(term).strip() for term in list(workstream_payload.get("recurring_terms") or []) if str(term).strip()][:4],
        *[str(item).strip() for item in list(current_state.get("open_questions") or []) if str(item).strip()][:1],
    ]
    return " ".join(_companion_unique_refs(parts))


def _companion_ask_handoff_text(
    *,
    question: str,
    workstream_card: dict[str, Any],
    session_payload: dict[str, Any],
    bundle: dict[str, Any],
) -> str:
    lines = [
        "Mode: ask-from-active-workstream",
        f"Workstream: {workstream_card['title']}",
        f"Anchor session: {str(session_payload.get('title') or session_payload.get('id') or '').strip()}",
        f"Question: {question}",
        "",
        "Answering rules:",
        "- Use the attached deterministic context bundle as the working set.",
        "- Prefer reusable judgments and current workstream state over transcript-shaped recap.",
        "- If the bundle is insufficient, say what is missing instead of guessing.",
        "",
        f"Bundle ref: bundle://{bundle['id']}",
        f"Bundle task label: {bundle['task_label']}",
    ]
    return "\n".join(lines)


def _companion_followup_handoff_text(
    *,
    question: str,
    workstream_card: dict[str, Any],
    session_payload: dict[str, Any],
    followup_turn: dict[str, Any],
    bundle: dict[str, Any],
) -> str:
    followup_preview = _companion_preview_text(str(followup_turn.get("content") or ""), max_chars=180)
    lines = [
        "Mode: follow-up-from-workstream",
        f"Workstream: {workstream_card['title']}",
        f"Selected session: {str(session_payload.get('title') or session_payload.get('id') or '').strip()}",
        f"Follow-up anchor: {str(followup_turn.get('role') or 'unknown').strip()}: {followup_preview}",
        f"Question: {question}",
        "",
        "Answering rules:",
        "- Use the attached deterministic context bundle as the working set.",
        "- Treat the selected follow-up anchor as the immediate conversation target.",
        "- Prefer workstream judgments and explicit recent turns over broad recap.",
        "- If the bundle is insufficient, say what is missing instead of guessing.",
        "",
        f"Bundle ref: bundle://{bundle['id']}",
        f"Bundle task label: {bundle['task_label']}",
    ]
    return "\n".join(lines)


def _companion_session_refs(workstream_payload: dict[str, Any]) -> list[str]:
    refs = []
    for ref in list(workstream_payload.get("session_refs") or []):
        text = str(ref).strip()
        if text.startswith("session://"):
            refs.append(text.replace("session://", "", 1))
    return _companion_unique_refs(refs)


def _companion_session_sort_key(payload: dict[str, Any]) -> tuple[str, str]:
    return (
        str(payload.get("ended_at") or payload.get("started_at") or ""),
        str(payload.get("id") or ""),
    )
