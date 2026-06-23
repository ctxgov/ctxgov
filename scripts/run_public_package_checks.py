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

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False, env=env)


def main() -> int:
    checks: list[dict[str, object]] = []
    for rel in ["src/ctxgov/__init__.py", "src/ctxgov/cli.py", "src/ctxgov/session_continuity.py", "src/ctxgov/memory_xray.py"]:
        py_compile.compile(str(ROOT / rel), doraise=True)
    checks.append({"name": "syntax", "status": "pass"})

    commands = [
        [sys.executable, "-m", "ctxgov.cli", "--help"],
        [sys.executable, "-m", "ctxgov.cli", "continuity", "compile", str(TRACE)],
        [sys.executable, "-m", "ctxgov.cli", "continuity", "render", str(TRACE)],
        [sys.executable, "-m", "ctxgov.cli", "continuity", "apply", "--mode", "dry-run", str(TRACE)],
        [sys.executable, "-m", "ctxgov.cli", "memory-xray", "validate", str(MEMORY_XRAY_PACK)],
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
