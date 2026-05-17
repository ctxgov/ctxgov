from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import py_compile
import subprocess
import sys


@dataclass(frozen=True)
class CheckResult:
    name: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _source_pythonpath() -> str:
    src = project_root() / "src"
    existing = os.environ.get("PYTHONPATH")
    if not existing:
        return str(src)
    return f"{src}{os.pathsep}{existing}"


def _python_files() -> list[Path]:
    root = project_root()
    candidates = list((root / "src").rglob("*.py"))
    candidates.extend((root / "tests").rglob("*.py"))
    candidates.extend((root / "scripts").glob("*.py"))
    candidates.extend((root / "schemas" / "python").glob("*.py"))
    return sorted(path for path in candidates if "__pycache__" not in path.parts)


def run_syntax_check() -> CheckResult:
    for path in _python_files():
        py_compile.compile(str(path), doraise=True)
    return CheckResult(name="syntax-check", returncode=0, stdout=f"compiled {len(_python_files())} python file(s)", stderr="")


def _run_subprocess(name: str, cmd: list[str], env_overrides: dict[str, str] | None = None) -> CheckResult:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    completed = subprocess.run(
        cmd,
        cwd=project_root(),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return CheckResult(
        name=name,
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
    )


def run_fixture_validation() -> CheckResult:
    return _run_subprocess(
        "fixture-validation",
        [sys.executable, str(project_root() / "scripts" / "validate_fixtures.py")],
    )


def run_unit_tests() -> CheckResult:
    return _run_subprocess(
        "unit-tests",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        env_overrides={"PYTHONPATH": _source_pythonpath()},
    )


def run_deterministic_checks() -> list[CheckResult]:
    return [
        run_syntax_check(),
        run_fixture_validation(),
        run_unit_tests(),
    ]


def print_report(results: list[CheckResult]) -> None:
    for result in results:
        status = "ok" if result.ok else "fail"
        print(f"[{status}] {result.name}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)


def main() -> int:
    results = run_deterministic_checks()
    print_report(results)
    return 0 if all(result.ok for result in results) else 1
