from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Callable, Pattern


_SEVERITY_RANK = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

_CN_ID_CHECKSUM_WEIGHTS = (7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
_CN_ID_CHECKSUM_DIGITS = "10X98765432"
_PLACEHOLDER_VALUES = {
    "changeme",
    "dummy",
    "example",
    "fake",
    "placeholder",
    "redacted",
    "sample",
    "test",
}

_DECISION_RANK = {
    "allow": 0,
    "redact": 1,
    "review": 2,
    "block": 3,
}

_TEXT_LIKE_SUFFIXES = {
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".css",
    ".csv",
    ".env",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".log",
    ".md",
    ".mmd",
    ".plist",
    ".py",
    ".rb",
    ".rst",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class PrivacyFinding:
    detector_id: str
    category: str
    severity: str
    start: int
    end: int
    preview: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "detector_id": self.detector_id,
            "category": self.category,
            "severity": self.severity,
            "start": self.start,
            "end": self.end,
            "preview": self.preview,
            "message": self.message,
        }


@dataclass(frozen=True)
class PrivacyScanReport:
    source: str
    decision: str
    highest_severity: str
    reasons: tuple[str, ...]
    findings: tuple[PrivacyFinding, ...]
    total_findings: int
    truncated: bool
    scanned_at: str

    def to_dict(self) -> dict[str, object]:
        severity_counts = Counter(finding.severity for finding in self.findings)
        category_counts = Counter(finding.category for finding in self.findings)
        return {
            "source": self.source,
            "decision": self.decision,
            "highest_severity": self.highest_severity,
            "reasons": list(self.reasons),
            "summary": {
                "total_findings": self.total_findings,
                "returned_findings": len(self.findings),
                "truncated": self.truncated,
                "severity_counts": dict(severity_counts),
                "category_counts": dict(category_counts),
            },
            "findings": [finding.to_dict() for finding in self.findings],
            "scanned_at": self.scanned_at,
        }


@dataclass(frozen=True)
class PrivacyFileScanItem:
    path: str
    filename: str
    exists: bool
    size_bytes: int | None
    content_scan_state: str
    text_bytes_scanned: int
    content_truncated: bool
    decision: str
    highest_severity: str
    reasons: tuple[str, ...]
    path_findings: tuple[PrivacyFinding, ...]
    content_findings: tuple[PrivacyFinding, ...]
    scanned_at: str

    def to_dict(self) -> dict[str, object]:
        path_severity_counts = Counter(finding.severity for finding in self.path_findings)
        content_severity_counts = Counter(finding.severity for finding in self.content_findings)
        return {
            "path": self.path,
            "filename": self.filename,
            "exists": self.exists,
            "size_bytes": self.size_bytes,
            "content_scan_state": self.content_scan_state,
            "text_bytes_scanned": self.text_bytes_scanned,
            "content_truncated": self.content_truncated,
            "decision": self.decision,
            "highest_severity": self.highest_severity,
            "reasons": list(self.reasons),
            "summary": {
                "path_finding_count": len(self.path_findings),
                "content_finding_count": len(self.content_findings),
                "total_findings": len(self.path_findings) + len(self.content_findings),
                "path_severity_counts": dict(path_severity_counts),
                "content_severity_counts": dict(content_severity_counts),
            },
            "path_findings": [finding.to_dict() for finding in self.path_findings],
            "content_findings": [finding.to_dict() for finding in self.content_findings],
            "scanned_at": self.scanned_at,
        }


Validator = Callable[[re.Match[str]], bool]


@dataclass(frozen=True)
class _Detector:
    detector_id: str
    category: str
    severity: str
    pattern: Pattern[str]
    message: str
    validator: Validator | None = None

    def scan(self, text: str) -> list[PrivacyFinding]:
        findings: list[PrivacyFinding] = []
        for match in self.pattern.finditer(text):
            if self.validator is not None and not self.validator(match):
                continue
            findings.append(
                PrivacyFinding(
                    detector_id=self.detector_id,
                    category=self.category,
                    severity=self.severity,
                    start=match.start(),
                    end=match.end(),
                    preview=_preview_value(match.group(0)),
                    message=self.message,
                )
            )
        return findings


_DETECTORS = (
    _Detector(
        detector_id="private_key_block",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"
        ),
        message="Private key material detected.",
    ),
    _Detector(
        detector_id="openai_api_key",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        message="OpenAI-style API key detected.",
    ),
    _Detector(
        detector_id="anthropic_api_key",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b"),
        message="Anthropic-style API key detected.",
    ),
    _Detector(
        detector_id="github_token",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        message="GitHub token detected.",
    ),
    _Detector(
        detector_id="aws_access_key_id",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
        message="AWS access key ID detected.",
    ),
    _Detector(
        detector_id="google_api_key",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"),
        message="Google API key detected.",
    ),
    _Detector(
        detector_id="slack_token",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        message="Slack token detected.",
    ),
    _Detector(
        detector_id="jwt",
        category="credential_secret",
        severity="critical",
        pattern=re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        message="JWT-like bearer token detected.",
    ),
    _Detector(
        detector_id="credential_assignment",
        category="credential_secret",
        severity="high",
        pattern=re.compile(
            r"""(?ix)
            \b(password|passwd|pwd|secret|api[_-]?key|token|access[_-]?token|bearer)\b
            \s*[:=]\s*
            (["'])(?P<value>[^"'\n]{6,})\2
            """
        ),
        message="Credential-like assignment detected.",
        validator=lambda match: _is_non_placeholder(match.group("value")),
    ),
    _Detector(
        detector_id="credit_card",
        category="regulated_personal_data",
        severity="high",
        pattern=re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        message="Credit card number detected.",
        validator=lambda match: _passes_luhn_digits(match.group(0)),
    ),
    _Detector(
        detector_id="us_ssn",
        category="regulated_personal_data",
        severity="high",
        pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        message="US Social Security Number detected.",
    ),
    _Detector(
        detector_id="cn_mainland_id",
        category="regulated_personal_data",
        severity="high",
        pattern=re.compile(r"\b\d{17}[\dXx]\b"),
        message="China mainland resident ID number detected.",
        validator=lambda match: _is_valid_cn_mainland_id(match.group(0)),
    ),
    _Detector(
        detector_id="email_address",
        category="direct_identifier",
        severity="medium",
        pattern=re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        message="Email address detected.",
    ),
    _Detector(
        detector_id="phone_number",
        category="direct_identifier",
        severity="medium",
        pattern=re.compile(r"(?<!\w)(?:\+?\d[\d(). \-]{7,}\d)(?!\w)"),
        message="Phone number detected.",
        validator=lambda match: _looks_like_phone_number(match.group(0)),
    ),
    _Detector(
        detector_id="home_path_unix",
        category="local_identifier",
        severity="low",
        pattern=re.compile(r"(?:/Users|/home)/[A-Za-z0-9._-]+(?:/[^\s\"']*)?"),
        message="Local home-directory path detected.",
    ),
    _Detector(
        detector_id="home_path_windows",
        category="local_identifier",
        severity="low",
        pattern=re.compile(r"[A-Za-z]:\\\\Users\\\\[A-Za-z0-9._-]+(?:\\\\[^\s\"']*)?"),
        message="Windows home-directory path detected.",
    ),
)


def scan_privacy_text(text: str, *, source: str = "inline", max_findings: int = 25) -> PrivacyScanReport:
    raw_findings: list[PrivacyFinding] = []
    for detector in _DETECTORS:
        raw_findings.extend(detector.scan(text))

    deduped = _dedupe_findings(raw_findings)
    returned = tuple(deduped[:max_findings])
    highest_severity = _highest_severity(deduped)
    decision = _decision_for_severity(highest_severity)
    reasons = _reasons_for_findings(deduped, truncated=len(deduped) > max_findings)
    return PrivacyScanReport(
        source=source,
        decision=decision,
        highest_severity=highest_severity,
        reasons=tuple(reasons),
        findings=returned,
        total_findings=len(deduped),
        truncated=len(deduped) > max_findings,
        scanned_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )


def scan_privacy_files(
    paths: list[str | Path],
    *,
    source: str = "attachment",
    max_findings: int = 25,
    max_bytes: int = 262_144,
) -> dict[str, object]:
    items = [
        _scan_privacy_file(Path(path).expanduser(), source=source, max_findings=max_findings, max_bytes=max_bytes)
        for path in paths
    ]
    highest_severity = max(
        (item.highest_severity for item in items),
        key=lambda severity: _SEVERITY_RANK.get(severity, 0),
        default="none",
    )
    decision = max(
        (item.decision for item in items),
        key=lambda current: _DECISION_RANK.get(current, 0),
        default="allow",
    )
    decision_counts = Counter(item.decision for item in items)
    content_state_counts = Counter(item.content_scan_state for item in items)
    total_findings = sum(len(item.path_findings) + len(item.content_findings) for item in items)
    return {
        "source": source,
        "decision": decision,
        "highest_severity": highest_severity,
        "summary": {
            "file_count": len(items),
            "returned_files": len(items),
            "total_findings": total_findings,
            "decision_counts": dict(decision_counts),
            "content_scan_state_counts": dict(content_state_counts),
        },
        "files": [item.to_dict() for item in items],
        "scanned_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def _scan_privacy_file(
    path: Path,
    *,
    source: str,
    max_findings: int,
    max_bytes: int,
) -> PrivacyFileScanItem:
    scanned_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    path_report = scan_privacy_text(str(path), source=f"{source}:path", max_findings=max_findings)

    if not path.exists():
        return PrivacyFileScanItem(
            path=str(path),
            filename=path.name,
            exists=False,
            size_bytes=None,
            content_scan_state="missing",
            text_bytes_scanned=0,
            content_truncated=False,
            decision=max(path_report.decision, "review", key=lambda current: _DECISION_RANK[current]),
            highest_severity=path_report.highest_severity,
            reasons=tuple([*path_report.reasons, "attachment path does not exist"]),
            path_findings=path_report.findings,
            content_findings=(),
            scanned_at=scanned_at,
        )

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return PrivacyFileScanItem(
            path=str(path),
            filename=path.name,
            exists=True,
            size_bytes=path.stat().st_size if path.exists() else None,
            content_scan_state="unreadable",
            text_bytes_scanned=0,
            content_truncated=False,
            decision=max(path_report.decision, "review", key=lambda current: _DECISION_RANK[current]),
            highest_severity=path_report.highest_severity,
            reasons=tuple([*path_report.reasons, f"attachment could not be read: {exc.__class__.__name__}"]),
            path_findings=path_report.findings,
            content_findings=(),
            scanned_at=scanned_at,
        )

    size_bytes = len(raw)
    scan_bytes = raw[:max_bytes]
    content_truncated = size_bytes > max_bytes

    if not _is_probably_text(path, scan_bytes):
        return PrivacyFileScanItem(
            path=str(path),
            filename=path.name,
            exists=True,
            size_bytes=size_bytes,
            content_scan_state="skipped_binary",
            text_bytes_scanned=0,
            content_truncated=content_truncated,
            decision=max(path_report.decision, "review", key=lambda current: _DECISION_RANK[current]),
            highest_severity=path_report.highest_severity,
            reasons=tuple([*path_report.reasons, "binary or unsupported attachment requires manual review"]),
            path_findings=path_report.findings,
            content_findings=(),
            scanned_at=scanned_at,
        )

    text = scan_bytes.decode("utf-8", errors="replace")
    content_report = scan_privacy_text(text, source=f"{source}:content", max_findings=max_findings)
    decision = max(path_report.decision, content_report.decision, key=lambda current: _DECISION_RANK[current])
    highest_severity = max(
        path_report.highest_severity,
        content_report.highest_severity,
        key=lambda severity: _SEVERITY_RANK.get(severity, 0),
    )
    reasons = [*path_report.reasons]
    for reason in content_report.reasons:
        if reason not in reasons:
            reasons.append(reason)
    if content_truncated:
        reasons.append("attachment content scan truncated to max_bytes")
    return PrivacyFileScanItem(
        path=str(path),
        filename=path.name,
        exists=True,
        size_bytes=size_bytes,
        content_scan_state="scanned",
        text_bytes_scanned=len(scan_bytes),
        content_truncated=content_truncated,
        decision=decision,
        highest_severity=highest_severity,
        reasons=tuple(reasons),
        path_findings=path_report.findings,
        content_findings=content_report.findings,
        scanned_at=scanned_at,
    )


def _dedupe_findings(findings: list[PrivacyFinding]) -> list[PrivacyFinding]:
    prioritized = sorted(
        findings,
        key=lambda finding: (
            -_SEVERITY_RANK[finding.severity],
            finding.start,
            -(finding.end - finding.start),
            finding.detector_id,
        ),
    )
    accepted: list[PrivacyFinding] = []
    for finding in prioritized:
        if any(_overlaps(finding, existing) for existing in accepted):
            continue
        accepted.append(finding)
    return sorted(accepted, key=lambda finding: (finding.start, finding.end, finding.detector_id))


def _overlaps(left: PrivacyFinding, right: PrivacyFinding) -> bool:
    return left.start < right.end and right.start < left.end


def _highest_severity(findings: list[PrivacyFinding]) -> str:
    if not findings:
        return "none"
    return max(findings, key=lambda finding: _SEVERITY_RANK[finding.severity]).severity


def _decision_for_severity(severity: str) -> str:
    if severity in {"critical", "high"}:
        return "block"
    if severity == "medium":
        return "review"
    if severity == "low":
        return "redact"
    return "allow"


def _is_probably_text(path: Path, content: bytes) -> bool:
    if path.suffix.lower() in _TEXT_LIKE_SUFFIXES:
        return True
    if not content:
        return True
    if b"\x00" in content:
        return False
    try:
        content.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _reasons_for_findings(findings: list[PrivacyFinding], *, truncated: bool) -> list[str]:
    if not findings:
        return ["no configured privacy detectors matched"]
    reasons: list[str] = []
    severity_counts = Counter(finding.severity for finding in findings)
    category_counts = Counter(finding.category for finding in findings)
    if severity_counts.get("critical", 0):
        reasons.append("secret or credential material detected")
    if severity_counts.get("high", 0):
        reasons.append("high-risk personal data detected")
    if severity_counts.get("medium", 0):
        reasons.append("direct personal identifiers should be reviewed before reuse")
    if severity_counts.get("low", 0):
        reasons.append("local device or user identifiers should be redacted")
    if category_counts.get("credential_secret", 0) and category_counts.get("direct_identifier", 0):
        reasons.append("both secret material and personal identifiers are present")
    if truncated:
        reasons.append("finding list truncated to the configured max_findings")
    return reasons


def _preview_value(value: str) -> str:
    compact = " ".join(value.split())
    if len(compact) > 96:
        compact = compact[:93] + "..."
    return _mask_value(compact)


def _mask_value(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def _is_non_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized not in _PLACEHOLDER_VALUES and "example" not in normalized


def _passes_luhn_digits(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    parity = len(digits) % 2
    for index, digit_char in enumerate(digits):
        digit = int(digit_char)
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _looks_like_phone_number(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if not 10 <= len(digits) <= 15:
        return False
    if len(set(digits)) == 1:
        return False
    return True


def _is_valid_cn_mainland_id(value: str) -> bool:
    normalized = value.upper()
    try:
        datetime.strptime(normalized[6:14], "%Y%m%d")
    except ValueError:
        return False
    checksum = sum(int(digit) * weight for digit, weight in zip(normalized[:17], _CN_ID_CHECKSUM_WEIGHTS))
    expected = _CN_ID_CHECKSUM_DIGITS[checksum % 11]
    return normalized[-1] == expected
