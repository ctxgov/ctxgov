from __future__ import annotations

import os
import json
from pathlib import Path
import py_compile
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TRACE = ROOT / "examples" / "session-continuity-public-preview" / "saved-goal-trace.synthetic.json"
MEMORY_XRAY_PACK = ROOT / "release" / "v0.7.0" / "memory-xray-l1-public-preview" / "memory-xray-l1-examples-pack.json"
CHANGE_GATE_BASELINE = ROOT / "examples" / "change-gate-public-preview" / "baseline"
CHANGE_GATE_HEAD = ROOT / "examples" / "change-gate-public-preview" / "head"
FEDERATION_BASE = ROOT / "examples" / "federation-public-preview"
OSS_CASE_SOURCE = ROOT / "examples" / "oss-case-study-public-preview" / "mem0-source.md"
OSS_TELEMETRY_MANIFEST = ROOT / "release" / "v0.8.0" / "oss-efficiency-raw-telemetry-manifest.json"
OSS_TELEMETRY_RECEIPT = ROOT / "release" / "v0.8.0" / "oss-efficiency-raw-telemetry-receipt.example.json"
FORENSICS_FIXTURE = ROOT / "release" / "v0.8.0" / "forensics-public-preview-fixture.json"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False, env=env)


def main() -> int:
    checks: list[dict[str, object]] = []
    for rel in [
        "src/ctxgov/__init__.py",
        "src/ctxgov/cli.py",
        "src/ctxgov/session_continuity.py",
        "src/ctxgov/memory_xray.py",
        "src/ctxgov/change_analysis.py",
        "src/ctxgov/federation.py",
        "src/ctxgov/oss_case_study.py",
        "src/ctxgov/oss_efficiency.py",
        "src/ctxgov/forensics.py",
    ]:
        py_compile.compile(str(ROOT / rel), doraise=True)
    checks.append({"name": "syntax", "status": "pass"})

    commands = [
        [sys.executable, "-m", "ctxgov.cli", "--help"],
        [sys.executable, "-m", "ctxgov.cli", "continuity", "compile", str(TRACE)],
        [sys.executable, "-m", "ctxgov.cli", "continuity", "render", str(TRACE)],
        [sys.executable, "-m", "ctxgov.cli", "continuity", "apply", "--mode", "dry-run", str(TRACE)],
        [sys.executable, "-m", "ctxgov.cli", "memory-xray", "validate", str(MEMORY_XRAY_PACK)],
        [sys.executable, "-m", "ctxgov.cli", "change-gate-check", "--baseline-root", str(CHANGE_GATE_BASELINE), "--head-root", str(CHANGE_GATE_HEAD)],
        [sys.executable, "-m", "ctxgov.cli", "change-gate-federate", "--base-path", str(FEDERATION_BASE), "--no-git-required"],
        [sys.executable, "-m", "ctxgov.cli", "oss-case-study-preview", "--target-name", "mem0", "--repo-url", "https://github.com/mem0ai/mem0", "--pinned-ref", "366945965df43aa7084be98d1b5073b62a20b431", "--source-path", str(OSS_CASE_SOURCE)],
        [sys.executable, "-m", "ctxgov.cli", "oss-efficiency", "evaluate", "--manifest", str(OSS_TELEMETRY_MANIFEST), "--checked-at", "2026-06-23T00:00:00Z"],
        [sys.executable, "-m", "ctxgov.cli", "oss-efficiency", "validate", str(OSS_TELEMETRY_RECEIPT)],
        [sys.executable, "-m", "ctxgov.cli", "forensics-timeline", "--fixture", str(FORENSICS_FIXTURE)],
        [sys.executable, "-m", "ctxgov.cli", "forensics-trace", "--fixture", str(FORENSICS_FIXTURE), "--finding-id", "finding-public-authority-001"],
        [sys.executable, "-m", "ctxgov.cli", "forensics-gaps", "--fixture", str(FORENSICS_FIXTURE)],
    ]
    for command in commands:
        completed = _run(command)
        checks.append({"name": " ".join(command[2:]), "status": "pass" if completed.returncode == 0 else "fail", "returncode": completed.returncode})
        if completed.returncode != 0:
            print(json.dumps({"status": "fail", "checks": checks, "stderr": completed.stderr, "stdout": completed.stdout}, indent=2, sort_keys=True))
            return 1

    print(json.dumps({"status": "pass", "checks": checks, "side_effect_boundary": {"network_call": False, "provider_model_call": False, "public_write": False, "target_repo_write": False}}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
