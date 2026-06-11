#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = Path("scripts/run_memory_state_governability_overlay_demo.py")
DEFAULT_OUTPUT_DIR = Path(".ctxvault") / "memory-state-governability-overlay"


def run_memory_state_influence_boundary_report(
    root: Path = ROOT,
    *,
    input_path: Path,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(root).resolve()
    module = _load_demo_module()
    return module.build_memory_state_influence_boundary_report(
        root,
        input_path=input_path,
        output_dir=output_dir,
    )


def _load_demo_module() -> Any:
    script = ROOT / DEMO_SCRIPT
    spec = importlib.util.spec_from_file_location("ctxgov_memory_state_influence_boundary_demo", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ctxgov_memory_state_influence_boundary_demo"] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local memory-state influence-boundary report.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--input", type=Path, required=True, help="Local memory/context/state file or directory to audit.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--format", choices=("json", "summary", "gate"), default="json")
    parser.add_argument("--fail-on-blocked", action="store_true", help="Exit non-zero when the report contains blocked refs.")
    args = parser.parse_args()
    module = _load_demo_module()
    report = module.build_memory_state_influence_boundary_report(
        args.root,
        input_path=args.input,
        output_dir=args.output_dir,
    )
    if args.format == "summary":
        print(module._render_summary(report))
    elif args.format == "gate":
        print(json.dumps(report["integration_gate"], indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
    return module._exit_code_for_report(report, fail_on_blocked=args.fail_on_blocked)


if __name__ == "__main__":
    raise SystemExit(main())
