from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


AUTHORITY_LAYERS: dict[str, dict[str, Any]] = {
    "claim": {
        "decision": "source_bound_allowed_only",
        "allowed": "source-backed descriptive claims",
        "blocked": [
            "quality",
            "security",
            "performance",
            "compatibility",
            "maintainer_endorsement",
            "stable_protocol",
            "runtime_behavior",
            "target_write",
        ],
    },
    "context": {
        "decision": "preview_only_with_caveats",
        "allowed": "selected and caveated evidence in local CtxVault preview artifacts",
        "blocked": ["private refs", "stale refs", "unsupported refs", "uninspected target files"],
    },
    "memory": {
        "decision": "blocked_until_lifecycle_and_rollback",
        "allowed": "none by default",
        "blocked": ["durable memory promotion", "reusable summary authority"],
    },
    "action": {
        "decision": "blocked_until_side_effect_approval",
        "allowed": "none by default",
        "blocked": ["target writes", "runtime execution", "provider/model calls", "maintainer outreach"],
    },
}


SAFE_REWRITES: list[dict[str, str]] = [
    {
        "unsafe_claim": "This project is secure.",
        "blocked_reason": "security judgment requires a security review receipt",
        "safe_rewrite": "The public docs describe security-related surfaces; CtxVault has not evaluated security.",
    },
    {
        "unsafe_claim": "This project is compatible with CtxVault.",
        "blocked_reason": "compatibility requires runtime or adapter evidence",
        "safe_rewrite": "This preview maps public source facts to CtxVault governance constraints without running compatibility checks.",
    },
    {
        "unsafe_claim": "The maintainers endorse this case study.",
        "blocked_reason": "endorsement requires explicit maintainer evidence",
        "safe_rewrite": "No maintainer endorsement is claimed.",
    },
    {
        "unsafe_claim": "CtxVault validated the target runtime.",
        "blocked_reason": "runtime behavior requires a separate runtime receipt",
        "safe_rewrite": "CtxVault did not run the target runtime in this preview.",
    },
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-")
    return slug or "target"


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_local_source(source_path: Path, max_source_bytes: int) -> tuple[str, str]:
    resolved = source_path.resolve()
    if resolved.is_dir():
        candidates = [resolved / "README.md", resolved / "README.markdown", resolved / "README"]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                resolved = candidate
                break
        else:
            raise ValueError(f"source directory has no README file: {source_path}")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError(f"source path does not exist or is not a file: {source_path}")
    raw = resolved.read_bytes()
    if len(raw) > max_source_bytes:
        raise ValueError(f"source file exceeds max source bytes: {len(raw)} > {max_source_bytes}")
    return raw.decode("utf-8", errors="replace"), f"file://{resolved}"


def _github_raw_readme_url(repo_url: str, pinned_ref: str) -> str:
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        raise ValueError("network fetch only supports https://github.com/<owner>/<repo> URLs")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub repo URL must include owner and repo")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{pinned_ref}/README.md"


def _fetch_remote_readme(repo_url: str, pinned_ref: str, max_source_bytes: int) -> tuple[str, str]:
    readme_url = _github_raw_readme_url(repo_url, pinned_ref)
    request = Request(readme_url, headers={"User-Agent": "ctxvault-oss-case-study-preview"})
    with urlopen(request, timeout=20) as response:
        raw = response.read(max_source_bytes + 1)
    if len(raw) > max_source_bytes:
        raise ValueError(f"remote README exceeds max source bytes: > {max_source_bytes}")
    return raw.decode("utf-8", errors="replace"), readme_url


def _render_extract(target_name: str, target: dict[str, Any], decision_table: list[dict[str, str]]) -> str:
    rows = "\n".join(
        f"| {row['decision']} | {row['allowed']} | {row['blocked']} | {row['missing']} | {row['rollback']} |"
        for row in decision_table
    )
    return f"""# {target_name} Case-Study Decision Preview

Status: local CtxVault preview. Not published.

## Source Boundary

- Target: `{target_name}`
- Repo URL: `{target.get("repo_url") or "not provided"}`
- Pinned ref: `{target["pinned_ref"]}`
- Checked at: `{target["checked_at_utc"]}`
- License: `{target["license"]}`

## Decision Preview

| Decision | Allowed | Blocked | Missing | Rollback |
| --- | --- | --- | --- | --- |
{rows}

## Authority Layers

- Claim: source-bound claims only.
- Context: preview-only selected and caveated evidence.
- Memory: blocked until lifecycle and rollback exist.
- Action: blocked until side-effect approval exists.

## Safe Rewrites

- Unsafe: "This project is secure." Safe: "The public docs describe security-related surfaces; CtxVault has not evaluated security."
- Unsafe: "This project is compatible with CtxVault." Safe: "This preview maps public source facts to CtxVault governance constraints without running compatibility checks."

## No Target Mutation

This preview does not write target files, run target code, start MCP, call a
provider/model, promote memory, create issues, open pull requests, publish
releases, or contact maintainers.
"""


def _render_rollback(target_name: str) -> str:
    return f"""# {target_name} Case-Study Preview Rollback

## Local Artifacts

- `decision-preview.json`
- `source-fact-receipt.json`
- `claim-lint.json`
- `public-safe-extract.md`
- `rollback.md`

## Rollback Plan

Delete or supersede the local preview output directory. No target project
rollback is needed unless a later approved lane creates public or target-side
state.
"""


def _blocked_network_result(
    *,
    target_name: str,
    repo_url: str | None,
    pinned_ref: str,
    checked_at_utc: str,
    output_dir: Path,
) -> dict[str, Any]:
    result = {
        "schema_id": "ctxvault.oss-case-study-decision-preview/v1",
        "status": "blocked_network_not_approved",
        "target": {
            "name": target_name,
            "repo_url": repo_url,
            "pinned_ref": pinned_ref,
            "checked_at_utc": checked_at_utc,
            "license": "unknown",
        },
        "decision_table": [
            {
                "decision": "source_fetch",
                "allowed": "none",
                "blocked": "remote target fetch requires --allow-network",
                "missing": "local source path or explicit network approval",
                "rollback": "delete local blocked preview receipt",
            }
        ],
        "authority_layers": AUTHORITY_LAYERS,
        "side_effect_boundary": {
            "local_preview_artifacts_written": True,
            "target_fetch_or_clone_performed": False,
            "target_repo_cloned": False,
            "target_file_written": False,
            "runtime_or_adapter_executed": False,
            "mcp_server_started": False,
            "provider_or_model_call_performed": False,
            "memory_promotion_performed": False,
            "github_public_repo_write_performed": False,
            "public_publication_performed": False,
        },
        "rollback": "delete local blocked preview receipt",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "decision-preview.json", result)
    return result


def build_oss_case_study_preview(
    *,
    root: Path,
    target_name: str,
    pinned_ref: str,
    repo_url: str | None = None,
    source_path: Path | None = None,
    output_dir: Path | None = None,
    checked_at_utc: str | None = None,
    license_name: str = "unknown",
    allow_network: bool = False,
    max_source_bytes: int = 262144,
) -> dict[str, Any]:
    checked_at = checked_at_utc or _utc_now()
    resolved_root = root.resolve()
    resolved_output = output_dir or (resolved_root / ".ctxvault" / "case-study-preview" / _slug(target_name))
    if not resolved_output.is_absolute():
        resolved_output = resolved_root / resolved_output
    resolved_output = resolved_output.resolve()

    if source_path is None and repo_url and not allow_network:
        return _blocked_network_result(
            target_name=target_name,
            repo_url=repo_url,
            pinned_ref=pinned_ref,
            checked_at_utc=checked_at,
            output_dir=resolved_output,
        )
    if source_path is None and repo_url is None:
        raise ValueError("oss-case-study-preview requires --source-path or --repo-url")

    target_fetch_performed = False
    if source_path is not None:
        source_text, source_ref = _read_local_source(source_path, max_source_bytes)
    else:
        source_text, source_ref = _fetch_remote_readme(repo_url or "", pinned_ref, max_source_bytes)
        target_fetch_performed = True

    source_sha = _sha256_text(source_text)
    source_bytes = len(source_text.encode("utf-8"))
    target = {
        "name": target_name,
        "repo_url": repo_url,
        "pinned_ref": pinned_ref,
        "checked_at_utc": checked_at,
        "license": license_name,
        "source_ref": source_ref,
        "source_sha256": source_sha,
        "source_bytes": source_bytes,
    }
    evidence_object_schema = {
        "required_fields": [
            "ref",
            "state",
            "reason",
            "authority_layer_blocked",
            "safe_rewrite_or_next_check",
            "rollback_ref",
        ]
    }
    selected_evidence = [
        {
            "ref": source_ref,
            "state": "selected",
            "reason": "pinned source boundary recorded",
            "authority_layer_blocked": None,
            "safe_rewrite_or_next_check": "use source-backed descriptive claims only",
            "rollback_ref": "delete-or-supersede-local-preview-artifacts",
        }
    ]
    omitted_evidence = [
        {
            "ref": f"{repo_url or source_ref}#uninspected-target-files",
            "state": "omitted",
            "reason": "first slice inspects only the explicit source boundary",
            "authority_layer_blocked": "context",
            "safe_rewrite_or_next_check": "pin and inspect additional source refs before broadening claims",
            "rollback_ref": "delete-or-supersede-local-preview-artifacts",
        }
    ]
    missing_evidence = [
        "quality_evaluation",
        "security_review",
        "performance_measurement",
        "runtime_compatibility",
        "maintainer_endorsement",
        "target_write_approval",
    ]
    decision_table = [
        {
            "decision": "public_claim",
            "allowed": "source-bound descriptive claims",
            "blocked": "quality, security, performance, compatibility, endorsement, stable protocol, runtime, target-write claims",
            "missing": "claim-specific receipts",
            "rollback": "delete or supersede public-safe extract",
        },
        {
            "decision": "context_packet",
            "allowed": "selected and caveated local preview evidence",
            "blocked": "uninspected, private, stale, or unsupported refs",
            "missing": "omission reasons for broader source set",
            "rollback": "regenerate or delete local preview artifacts",
        },
        {
            "decision": "memory",
            "allowed": "none",
            "blocked": "memory promotion and durable reuse",
            "missing": "lifecycle decision and rollback",
            "rollback": "no memory state exists",
        },
        {
            "decision": "action",
            "allowed": "none",
            "blocked": "target writes, runtime, provider/model calls, public outreach",
            "missing": "side-effect approval and rollback",
            "rollback": "no target/action state exists",
        },
    ]
    side_effect_boundary = {
        "local_preview_artifacts_written": True,
        "target_fetch_or_clone_performed": target_fetch_performed,
        "target_repo_cloned": False,
        "target_file_written": False,
        "runtime_or_adapter_executed": False,
        "mcp_server_started": False,
        "provider_or_model_call_performed": False,
        "memory_promotion_performed": False,
        "github_public_repo_write_performed": False,
        "public_publication_performed": False,
    }

    source_fact = {
        "schema_id": "ctxvault.case-study.source-fact-recheck/v1",
        "target": target,
        "verification_methods": ["local_source_path" if source_path is not None else "remote_readme_fetch"],
        "source_refs": [source_ref],
        "source_facts": {"source_sha256": source_sha, "source_bytes": source_bytes},
        "volatile_facts": [],
        "authority_layers": AUTHORITY_LAYERS,
        "evidence_object_schema": evidence_object_schema,
        "selected_evidence": selected_evidence,
        "omitted_evidence": omitted_evidence,
        "blocked_evidence": [],
        "stale_or_conflicting_evidence": [],
        "missing_evidence": missing_evidence,
        "side_effect_boundary": side_effect_boundary,
        "rollback": "delete-or-supersede-local-preview-artifacts",
    }
    claim_lint = {
        "schema_id": "ctxvault.case-study.claim-lint/v1",
        "target": {"name": target_name, "pinned_ref": pinned_ref},
        "authority_layers": AUTHORITY_LAYERS,
        "claim_classes": AUTHORITY_LAYERS["claim"]["blocked"],
        "allowed_claims": ["source-backed descriptive claims about the pinned public source"],
        "blocked_claims": AUTHORITY_LAYERS["claim"]["blocked"],
        "safe_rewrites": SAFE_REWRITES,
        "missing_evidence": missing_evidence,
        "publication_decision": "blocked_until_owner_approval",
        "side_effect_boundary": side_effect_boundary,
        "rollback": "delete-or-supersede-claim-lint-preview",
    }
    decision_preview = {
        "schema_id": "ctxvault.oss-case-study-decision-preview/v1",
        "status": "preview_ready",
        "target": target,
        "authority_layers": AUTHORITY_LAYERS,
        "decision_table": decision_table,
        "selected_evidence": selected_evidence,
        "omitted_evidence": omitted_evidence,
        "missing_evidence": missing_evidence,
        "safe_rewrites": SAFE_REWRITES,
        "side_effect_boundary": side_effect_boundary,
        "rollback": "delete-or-supersede-local-preview-artifacts",
    }

    resolved_output.mkdir(parents=True, exist_ok=True)
    if target_fetch_performed:
        (resolved_output / "target-readme.md").write_text(source_text, encoding="utf-8")
    _write_json(resolved_output / "source-fact-receipt.json", source_fact)
    _write_json(resolved_output / "claim-lint.json", claim_lint)
    (resolved_output / "public-safe-extract.md").write_text(
        _render_extract(target_name, target, decision_table),
        encoding="utf-8",
    )
    (resolved_output / "rollback.md").write_text(_render_rollback(target_name), encoding="utf-8")
    _write_json(resolved_output / "decision-preview.json", decision_preview)

    decision_preview["output_dir"] = str(resolved_output)
    decision_preview["local_artifacts"] = [
        str(resolved_output / "decision-preview.json"),
        str(resolved_output / "source-fact-receipt.json"),
        str(resolved_output / "claim-lint.json"),
        str(resolved_output / "public-safe-extract.md"),
        str(resolved_output / "rollback.md"),
    ]
    return decision_preview
