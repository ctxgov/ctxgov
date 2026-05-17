from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any


def _parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class OperationPolicyDecision:
    operation: str
    sensitivity: str
    decision: str
    requires_human_review: bool
    backup_status: str
    matched_rule: dict[str, Any] | None
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "sensitivity": self.sensitivity,
            "decision": self.decision,
            "requires_human_review": self.requires_human_review,
            "backup_status": self.backup_status,
            "matched_rule": self.matched_rule,
            "reasons": self.reasons,
        }


@dataclass(frozen=True)
class ExportPolicyDecision:
    sensitivity: str
    decision: str
    requires_human_review: bool
    redactions_required: bool
    matched_rule: dict[str, Any] | None
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sensitivity": self.sensitivity,
            "decision": self.decision,
            "requires_human_review": self.requires_human_review,
            "redactions_required": self.redactions_required,
            "matched_rule": self.matched_rule,
            "reasons": self.reasons,
        }


class CtxVaultPolicy:
    def __init__(self, policy_payload: dict[str, Any]):
        self.policy = policy_payload

    @classmethod
    def from_path(cls, path: Path) -> "CtxVaultPolicy":
        return cls(json.loads(path.read_text()))

    @staticmethod
    def load_backup_receipt(path: Path | None, *, refresh_timestamps: bool = False) -> dict[str, Any] | None:
        if path is None:
            return None
        payload = json.loads(path.read_text())
        if refresh_timestamps:
            return CtxVaultPolicy.freshen_backup_receipt(payload)
        return payload

    @staticmethod
    def freshen_backup_receipt(backup_receipt: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        clock = now or _utc_now()
        refreshed = dict(backup_receipt)
        refreshed["checked_at"] = _utc_timestamp(clock)
        if "recovery_point_at" in refreshed:
            refreshed["recovery_point_at"] = _utc_timestamp(clock - timedelta(minutes=5))
        return refreshed

    def evaluate_operation(
        self,
        *,
        operation: str,
        sensitivity: str,
        backup_receipt: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> OperationPolicyDecision:
        rule = self._match_operation_rule(operation, sensitivity)
        if rule is None:
            return OperationPolicyDecision(
                operation=operation,
                sensitivity=sensitivity,
                decision="allow",
                requires_human_review=False,
                backup_status="not_required",
                matched_rule=None,
                reasons=["no matching operation rule; default allow"],
            )

        reasons: list[str] = []
        backup_status = "not_required"
        if rule.get("requires_backup", False):
            backup_status, backup_reason = self._evaluate_backup_requirement(rule, backup_receipt, now=now)
            reasons.append(backup_reason)
            if backup_status != "ok":
                return OperationPolicyDecision(
                    operation=operation,
                    sensitivity=sensitivity,
                    decision=str(rule["on_failure"]),
                    requires_human_review=bool(rule.get("require_human_review", False)),
                    backup_status=backup_status,
                    matched_rule=rule,
                    reasons=reasons,
                )

        requires_review = bool(rule.get("require_human_review", False))
        if requires_review:
            reasons.append("human review required by policy")
            decision = "review_required"
        else:
            reasons.append("policy gate passed")
            decision = "allow"

        return OperationPolicyDecision(
            operation=operation,
            sensitivity=sensitivity,
            decision=decision,
            requires_human_review=requires_review,
            backup_status=backup_status,
            matched_rule=rule,
            reasons=reasons,
        )

    def evaluate_export(
        self,
        *,
        sensitivity: str,
        exportable: bool,
        redaction_state: str,
        secret_refs: list[str] | None = None,
    ) -> ExportPolicyDecision:
        secret_refs = secret_refs or []
        rule = self._match_export_rule(sensitivity)
        reasons: list[str] = []
        if not exportable:
            return ExportPolicyDecision(
                sensitivity=sensitivity,
                decision="block",
                requires_human_review=False,
                redactions_required=False,
                matched_rule=rule,
                reasons=["payload is marked non-exportable"],
            )

        if rule is None:
            return ExportPolicyDecision(
                sensitivity=sensitivity,
                decision="allow",
                requires_human_review=False,
                redactions_required=bool(secret_refs),
                matched_rule=None,
                reasons=["no matching export rule; default allow"],
            )

        redactions_required = bool(secret_refs) and bool(rule.get("redact_secret_refs", False))
        action = str(rule["action"])
        requires_review = bool(rule.get("require_human_review", False))

        if action == "block":
            reasons.append("policy blocks export for this sensitivity")
            return ExportPolicyDecision(
                sensitivity=sensitivity,
                decision="block",
                requires_human_review=requires_review,
                redactions_required=redactions_required,
                matched_rule=rule,
                reasons=reasons,
            )

        if redactions_required and redaction_state == "none":
            reasons.append("secret refs require redaction before export")
            decision = "redact"
        else:
            decision = action

        if requires_review and decision == "allow":
            decision = "review"
        if requires_review:
            reasons.append("human review required by export policy")
        else:
            reasons.append("export policy gate passed")

        return ExportPolicyDecision(
            sensitivity=sensitivity,
            decision=decision,
            requires_human_review=requires_review,
            redactions_required=redactions_required,
            matched_rule=rule,
            reasons=reasons,
        )

    def evaluate_payload_export(self, payload: dict[str, Any]) -> ExportPolicyDecision:
        return self.evaluate_export(
            sensitivity=str(payload.get("sensitivity", "public")),
            exportable=bool(payload.get("exportable", False)),
            redaction_state=str(payload.get("redaction_state", "none")),
            secret_refs=list(payload.get("secret_refs", [])),
        )

    def _match_operation_rule(self, operation: str, sensitivity: str) -> dict[str, Any] | None:
        for rule in self.policy.get("operation_rules", []):
            if rule.get("operation") != operation:
                continue
            sensitivities = list(rule.get("applies_to_sensitivity", []))
            if sensitivities and sensitivity not in sensitivities:
                continue
            return rule
        return None

    def _match_export_rule(self, sensitivity: str) -> dict[str, Any] | None:
        for rule in self.policy.get("export_rules", []):
            if sensitivity in list(rule.get("sensitivities", [])):
                return rule
        return None

    def _evaluate_backup_requirement(
        self,
        rule: dict[str, Any],
        backup_receipt: dict[str, Any] | None,
        *,
        now: datetime | None = None,
    ) -> tuple[str, str]:
        if backup_receipt is None:
            return "missing", "backup receipt is missing"

        status = str(backup_receipt.get("status", "missing"))
        if status != "ok":
            return status, f"backup receipt status is {status}"

        clock = now or _utc_now()
        checked_at = _parse_timestamp(str(backup_receipt["checked_at"]))
        receipt_age_limit = int(backup_receipt.get("max_age_hours", 0) or 0)
        rule_age_limit = int(rule.get("max_backup_age_hours", 0) or 0)
        effective_hours = rule_age_limit or receipt_age_limit
        if effective_hours:
            expiry = checked_at + timedelta(hours=effective_hours)
            if clock > expiry:
                return "stale", f"backup receipt is older than {effective_hours} hour(s)"

        return "ok", "backup receipt is fresh enough for this operation"
