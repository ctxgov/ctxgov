from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = ROOT / "scripts" / "run_memory_state_governability_overlay_demo.py"
INFLUENCE_BOUNDARY_SCRIPT = ROOT / "scripts" / "run_memory_state_influence_boundary_report.py"
SOCIAL_SCRIPT = ROOT / "scripts" / "render_memory_state_governability_overlay_social_payload.py"
SOCIAL_DRAFT_DRIFT_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_social_draft_drift.py"
PACK_CHECK_SCRIPT = ROOT / "scripts" / "check_memory_state_governability_overlay_publish_pack.py"
FINAL_PREFLIGHT_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_final_preflight.py"
PUBLICATION_BUNDLE_SCRIPT = ROOT / "scripts" / "build_memory_state_influence_boundary_publication_bundle.py"
MATERIALIZE_BUNDLE_SCRIPT = ROOT / "scripts" / "materialize_memory_state_influence_boundary_publication_bundle.py"
PUBLISH_ENVELOPE_SCRIPT = ROOT / "scripts" / "render_memory_state_influence_boundary_publish_command_envelope.py"
OWNER_PACKET_SCRIPT = ROOT / "scripts" / "render_memory_state_influence_boundary_owner_publish_packet.py"
OWNER_PACKET_CONTRACT_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_owner_publish_packet_contract.py"
PUBLIC_CHECKOUT_READINESS_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_public_checkout_readiness.py"
LIVE_CHECK_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_live_publication.py"
PUBLISHER_SCRIPT = ROOT / "scripts" / "publish_memory_state_influence_boundary_public_patch.py"
PUBLIC_PAGE = ROOT / "docs" / "memory-state-influence-boundary-try-in-5-minutes.html"
LEGACY_PUBLIC_PAGE = ROOT / "docs" / "memory-state-governability-overlay-try-in-5-minutes.html"
PACK_ROOT = ROOT / "release" / "memory-state-governability-overlay" / "2026-06-11"
GATE_SCHEMA = ROOT / "schemas" / "json" / "ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json"
REPORT_SCHEMA = ROOT / "schemas" / "json" / "ctxvault-memory-state-influence-boundary-report-v0.schema.json"
GATE_EXAMPLE = PACK_ROOT / "integration-gate.example.json"
GATE_PASS_EXAMPLE = PACK_ROOT / "integration-gate.pass.example.json"
GATE_CONTRACT_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_integration_gate_contract.py"
REPORT_CONTRACT_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_report_contract.py"
CONSUMER_INTEGRATION_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_consumer_integration.py"
CONSUMER_WRAPPER_CONTRACT_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_consumer_wrapper_contract.py"
CONSUMER_WRAPPER_SCRIPT = ROOT / "scripts" / "run_memory_state_influence_boundary_consumer_wrapper_example.py"
RELEASE_DISTINCTNESS_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_release_distinctness.py"
BYO_SMOKE_SCRIPT = ROOT / "scripts" / "check_memory_state_influence_boundary_byo_smoke.py"


def _load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class MemoryStateGovernabilityOverlayDemoTests(unittest.TestCase):
    def test_demo_builds_user_operable_overlay_report(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo")
        with TemporaryDirectory() as tmp:
            report = module.build_memory_state_governability_overlay_demo(
                ROOT,
                output_dir=Path(tmp) / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_governability_overlay_demo")
            self.assertEqual(report["surface_count"], 5)
            self.assertEqual(
                report["fresh_checkout_commands"],
                [
                    "git clone https://github.com/ctxgov/ctxgov.git",
                    "cd ctxgov",
                    "python3 scripts/run_memory_state_governability_overlay_demo.py",
                ],
            )
            self.assertEqual(
                report["scale_profile_counts"],
                {
                    "cluster_multi_tenant": 3,
                    "local_single_user": 1,
                    "team_project": 4,
                },
            )
            self.assertEqual(len(report["required_overlay_fields"]), 11)
            self.assertTrue(all(surface["overlay_requirement_count"] == 11 for surface in report["surface_reports"]))
            for surface in report["surface_reports"]:
                blocked = " ".join(surface["blocked_public_claims"]).lower()
                for term in ("compatibility", "support", "endorsement", "security", "benchmark"):
                    self.assertIn(term, blocked)
            for field, observed in report["claim_boundary"].items():
                self.assertFalse(observed, field)
            for field, observed in report["side_effect_boundary"].items():
                self.assertFalse(observed, field)

            output_files = report["output_files"]
            self.assertTrue((ROOT / output_files["json"]).exists() or Path(output_files["json"]).exists())
            self.assertTrue((ROOT / output_files["markdown"]).exists() or Path(output_files["markdown"]).exists())
            self.assertTrue((ROOT / output_files["html"]).exists() or Path(output_files["html"]).exists())

    def test_demo_summary_command_is_runnable(self) -> None:
        with TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(DEMO_SCRIPT),
                    "--root",
                    str(ROOT),
                    "--output-dir",
                    str(Path(tmp) / "overlay"),
                    "--format",
                    "summary",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Memory State Governability Overlay Demo", completed.stdout)
            self.assertIn("status=pass_memory_state_governability_overlay_demo", completed.stdout)
            self.assertIn("surface_count=5", completed.stdout)
            self.assertIn("compatibility_claim_created=false", completed.stdout)

    def test_user_input_markdown_generates_influence_boundary_report(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_input_md")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "CLAUDE.md"
            input_file.write_text(
                "\n".join(
                    [
                        "# Project Memory",
                        "Always use the local project context before answering.",
                        "Remembered preference: keep release claims conservative.",
                        "Tool writes require rollback before publish.",
                    ]
                ),
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["mode"], "user_input")
            self.assertEqual(report["input_file_count"], 1)
            self.assertEqual(report["input_files"][0]["source_family"], "local_project_memory_file")
            self.assertFalse(report["input_files"][0]["raw_content_included"])
            self.assertIn("memory_or_context_state", report["input_files"][0]["signal_ids"])
            self.assertIn("action_or_tool_authority", report["input_files"][0]["signal_ids"])
            self.assertIn(str(input_file.relative_to(tmp_root)), report["influence_boundary"]["blocked_refs"])
            self.assertEqual(report["influence_boundary"]["selected_refs"], [])
            self.assertIn("does not prove runtime selection", report["influence_boundary"]["selected_refs_note"])
            self.assertFalse(report["integration_gate"]["passed"])
            self.assertEqual(report["integration_gate"]["default_exit_code"], 0)
            self.assertEqual(report["integration_gate"]["fail_on_blocked_exit_code"], 2)
            self.assertEqual(report["integration_gate"]["blocked_ref_count"], 1)
            self.assertFalse(report["integration_gate"]["raw_content_included"])
            for output in report["output_files"].values():
                self.assertTrue((tmp_root / output).exists())
            markdown = (tmp_root / report["output_files"]["markdown"]).read_text(encoding="utf-8")
            html = (tmp_root / report["output_files"]["html"]).read_text(encoding="utf-8")
            self.assertIn("## Integration Gate", markdown)
            self.assertIn("`--fail-on-blocked` exit code: `2`", markdown)
            self.assertIn("Integration Gate", html)
            self.assertIn("--fail-on-blocked", html)

    def test_user_input_directory_scans_json_state_without_raw_secret_leak(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_input_dir")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            state_dir = tmp_root / "memory-state"
            state_dir.mkdir()
            (state_dir / "checkpoint.json").write_text(
                json.dumps(
                    {
                        "thread_id": "thread-1",
                        "checkpoint_id": "cp-1",
                        "channel_values": {"memory": "project release state"},
                        "user_id": "user-1",
                    }
                ),
                encoding="utf-8",
            )
            secret_value = "sk-testsecretvalue000000000000"
            (state_dir / "AGENTS.md").write_text(
                f"Project instruction with api_key={secret_value}\n@../shared-memory.md\n",
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=state_dir,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["input_kind"], "directory")
            self.assertEqual(report["input_file_count"], 2)
            families = {file_report["source_family"] for file_report in report["input_files"]}
            self.assertIn("checkpoint_or_thread_state_json", families)
            self.assertTrue(any(file_report["secret_like_evidence_count"] == 1 for file_report in report["input_files"]))
            self.assertTrue(any("imported_context_ref" in file_report["signal_ids"] for file_report in report["input_files"]))
            output_json = tmp_root / report["output_files"]["json"]
            output_markdown = tmp_root / report["output_files"]["markdown"]
            self.assertNotIn(secret_value, output_json.read_text(encoding="utf-8"))
            self.assertNotIn(secret_value, output_markdown.read_text(encoding="utf-8"))
            self.assertTrue(
                any(finding["finding_id"] == "secret_like_content_redacted" for finding in report["findings"])
            )
            secret_finding = next(
                finding for finding in report["findings"] if finding["finding_id"] == "secret_like_content_redacted"
            )
            self.assertIn("Remove or rotate secret-like values", secret_finding["recommendation"])

    def test_external_input_file_paths_are_input_relative_without_absolute_path_leak(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_external_input_file")
        with TemporaryDirectory() as tmp, TemporaryDirectory() as external:
            tmp_root = Path(tmp)
            external_root = Path(external)
            input_file = external_root / "CLAUDE.md"
            input_file.write_text(
                "Project memory may inform answers only after rollback review.\n",
                encoding="utf-8",
            )

            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["input_path"], "input/CLAUDE.md")
            self.assertEqual(report["input_files"][0]["path"], "input/CLAUDE.md")
            self.assertTrue(
                all(
                    str(evidence["ref"]).startswith("input/CLAUDE.md")
                    for evidence in report["input_files"][0]["signal_evidence"]
                )
            )
            output_json = tmp_root / report["output_files"]["json"]
            output_markdown = tmp_root / report["output_files"]["markdown"]
            output_html = tmp_root / report["output_files"]["html"]
            for rendered in (
                output_json.read_text(encoding="utf-8"),
                output_markdown.read_text(encoding="utf-8"),
                output_html.read_text(encoding="utf-8"),
            ):
                self.assertNotIn(str(external_root), rendered)
                self.assertNotIn(str(input_file), rendered)
                self.assertIn("input/CLAUDE.md", rendered)

    def test_external_input_directory_paths_and_skips_are_input_relative(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_external_input_dir")
        with TemporaryDirectory() as tmp, TemporaryDirectory() as external:
            tmp_root = Path(tmp)
            external_root = Path(external)
            state_dir = external_root / "memory-state"
            state_dir.mkdir()
            (state_dir / "MEMORY.md").write_text(
                "Project memory may inform answers only after rollback review.\n",
                encoding="utf-8",
            )
            (state_dir / "ignored.bin").write_text("not a supported state file\n", encoding="utf-8")

            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=state_dir,
                output_dir=tmp_root / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["input_path"], "input")
            self.assertEqual(report["input_files"][0]["path"], "input/MEMORY.md")
            self.assertEqual(report["skipped_inputs"][0]["path"], "input/ignored.bin")
            output_json = tmp_root / report["output_files"]["json"]
            output_markdown = tmp_root / report["output_files"]["markdown"]
            output_html = tmp_root / report["output_files"]["html"]
            for rendered in (
                output_json.read_text(encoding="utf-8"),
                output_markdown.read_text(encoding="utf-8"),
                output_html.read_text(encoding="utf-8"),
            ):
                self.assertNotIn(str(external_root), rendered)
                self.assertNotIn(str(state_dir), rendered)
                self.assertIn("input/MEMORY.md", rendered)
                self.assertIn("input/ignored.bin", rendered)

    def test_user_input_yaml_state_file_is_supported(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_input_yaml")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "state-profile.yaml"
            sensitive_note = "remembered rollback for private workspace"
            input_file.write_text(
                "\n".join(
                    [
                        "profile:",
                        f"  memory: {sensitive_note}",
                        "  policy: inform only",
                        "  rollback: required",
                    ]
                ),
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertIn(".yaml", report["supported_input_suffixes"])
            self.assertIn(".yml", report["supported_input_suffixes"])
            self.assertEqual(report["input_files"][0]["source_family"], "local_state_yaml")
            self.assertIn("memory_or_context_state", report["input_files"][0]["signal_ids"])
            self.assertIn("$.profile.memory", report["input_files"][0]["yaml_key_paths_sample"])
            self.assertIn("$.profile.memory", report["input_files"][0]["structured_key_paths_sample"])
            self.assertTrue(
                any(
                    evidence.get("evidence_kind") == "structured_value"
                    and evidence["ref"].endswith(":$.profile.memory")
                    and evidence["matched"] == "remembered"
                    for evidence in report["input_files"][0]["signal_evidence"]
                )
            )
            self.assertIn(str(input_file.relative_to(tmp_root)), report["influence_boundary"]["inform_only_allowed_refs"])
            output_json = tmp_root / report["output_files"]["json"]
            output_markdown = tmp_root / report["output_files"]["markdown"]
            output_html = tmp_root / report["output_files"]["html"]
            self.assertNotIn(sensitive_note, output_json.read_text(encoding="utf-8"))
            self.assertNotIn(sensitive_note, output_markdown.read_text(encoding="utf-8"))
            self.assertNotIn(sensitive_note, output_html.read_text(encoding="utf-8"))
            self.assertIn("$.profile.memory", output_markdown.read_text(encoding="utf-8"))
            self.assertIn("structured_value", output_html.read_text(encoding="utf-8"))

    def test_user_input_toml_state_file_is_supported(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_input_toml")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "state-policy.toml"
            input_file.write_text(
                "\n".join(
                    [
                        "[profile]",
                        'memory = "release state"',
                        'policy = "inform_only"',
                        'rollback = "required"',
                    ]
                ),
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertIn(".toml", report["supported_input_suffixes"])
            self.assertEqual(report["input_files"][0]["source_family"], "local_state_toml")
            self.assertIn("$.profile.memory", report["input_files"][0]["structured_key_paths_sample"])
            self.assertIn("memory_or_context_state", report["input_files"][0]["signal_ids"])
            self.assertIn(str(input_file.relative_to(tmp_root)), report["influence_boundary"]["inform_only_allowed_refs"])
            self.assertTrue(report["integration_gate"]["passed"])
            self.assertEqual(report["integration_gate"]["default_exit_code"], 0)
            self.assertEqual(report["integration_gate"]["fail_on_blocked_exit_code"], 0)
            self.assertEqual(report["integration_gate"]["blocked_ref_count"], 0)

    def test_structured_json_value_signals_use_paths_without_raw_value_leak(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_json_value_signals")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "state-export.json"
            sensitive_note = "remembered rollback for private workspace release state"
            input_file.write_text(
                json.dumps({"record": {"note": sensitive_note}}),
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            file_report = report["input_files"][0]
            self.assertEqual(file_report["source_family"], "memory_store_json")
            self.assertIn("memory_or_context_state", file_report["signal_ids"])
            self.assertTrue(
                any(
                    evidence.get("evidence_kind") == "structured_value"
                    and evidence["ref"].endswith(":$.record.note")
                    and evidence["matched"] == "remembered"
                    for evidence in file_report["signal_evidence"]
                )
            )
            output_json = tmp_root / report["output_files"]["json"]
            output_markdown = tmp_root / report["output_files"]["markdown"]
            output_html = tmp_root / report["output_files"]["html"]
            markdown = output_markdown.read_text(encoding="utf-8")
            html = output_html.read_text(encoding="utf-8")
            self.assertNotIn(sensitive_note, output_json.read_text(encoding="utf-8"))
            self.assertNotIn(sensitive_note, markdown)
            self.assertNotIn(sensitive_note, html)
            self.assertIn("Reason:", markdown)
            self.assertIn("Evidence refs", markdown)
            self.assertIn("$.record.note", markdown)
            self.assertIn("kind=`structured_value`", markdown)
            self.assertIn("Evidence refs", html)
            self.assertIn("$.record.note", html)
            self.assertIn("structured_value", html)

    def test_structured_toml_value_signals_use_paths_without_raw_value_leak(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_toml_value_signals")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "state-policy.toml"
            sensitive_note = "memory rollback applies to private workspace"
            input_file.write_text(
                "\n".join(
                    [
                        "[record]",
                        f'note = "{sensitive_note}"',
                    ]
                ),
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            file_report = report["input_files"][0]
            self.assertEqual(file_report["source_family"], "local_state_toml")
            self.assertIn("memory_or_context_state", file_report["signal_ids"])
            self.assertTrue(
                any(
                    evidence.get("evidence_kind") == "structured_value"
                    and evidence["ref"].endswith(":$.record.note")
                    and evidence["matched"] == "memory"
                    for evidence in file_report["signal_evidence"]
                )
            )
            output_json = tmp_root / report["output_files"]["json"]
            output_markdown = tmp_root / report["output_files"]["markdown"]
            output_html = tmp_root / report["output_files"]["html"]
            self.assertNotIn(sensitive_note, output_json.read_text(encoding="utf-8"))
            self.assertNotIn(sensitive_note, output_markdown.read_text(encoding="utf-8"))
            self.assertNotIn(sensitive_note, output_html.read_text(encoding="utf-8"))

    def test_user_input_mdx_context_file_is_supported(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_input_mdx")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "context-note.mdx"
            input_file.write_text(
                "\n".join(
                    [
                        "# Context Note",
                        '<Callout type="memory">Project release state may inform answers only.</Callout>',
                        "Rollback evidence is required before release.",
                    ]
                ),
                encoding="utf-8",
            )
            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=input_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertIn(".mdx", report["supported_input_suffixes"])
            self.assertEqual(report["input_files"][0]["source_family"], "local_context_mdx")
            self.assertIn("memory_or_context_state", report["input_files"][0]["signal_ids"])
            self.assertIn(str(input_file.relative_to(tmp_root)), report["influence_boundary"]["inform_only_allowed_refs"])

    def test_user_input_scan_bounds_skipped_records_and_lists_outputs(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_bounded_skips")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            state_dir = tmp_root / "memory-state"
            state_dir.mkdir()
            (state_dir / "MEMORY.md").write_text(
                "Project memory may inform answers only after rollback review.\n",
                encoding="utf-8",
            )
            for index in range(module.MAX_SKIPPED_INPUT_RECORDS + 7):
                (state_dir / f"ignored-{index:03d}.bin").write_text("not a supported state file\n", encoding="utf-8")

            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=state_dir,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["input_file_count"], 1)
            self.assertEqual(report["skipped_input_count"], module.MAX_SKIPPED_INPUT_RECORDS + 7)
            self.assertEqual(report["skipped_input_record_count"], module.MAX_SKIPPED_INPUT_RECORDS)
            self.assertTrue(report["skipped_input_records_truncated"])
            self.assertEqual(report["scan_limits"]["max_skipped_input_records"], module.MAX_SKIPPED_INPUT_RECORDS)
            skipped_finding = next(
                finding for finding in report["findings"] if finding["finding_id"] == "inputs_omitted_by_scan_boundary"
            )
            self.assertEqual(skipped_finding["omitted_count"], module.MAX_SKIPPED_INPUT_RECORDS + 7)
            self.assertEqual(skipped_finding["omitted_record_count"], module.MAX_SKIPPED_INPUT_RECORDS)
            self.assertTrue(skipped_finding["omitted_records_truncated"])
            self.assertIn("Review omitted inputs separately", skipped_finding["recommendation"])

            output_markdown = tmp_root / report["output_files"]["markdown"]
            output_html = tmp_root / report["output_files"]["html"]
            markdown = output_markdown.read_text(encoding="utf-8")
            html = output_html.read_text(encoding="utf-8")
            self.assertIn(report["output_files"]["json"], markdown)
            self.assertIn(report["output_files"]["markdown"], markdown)
            self.assertIn(report["output_files"]["html"], markdown)
            self.assertIn("skipped input records truncated", markdown)
            self.assertIn("Review omitted inputs separately", markdown)
            self.assertIn(report["output_files"]["json"], html)
            self.assertIn(report["output_files"]["markdown"], html)
            self.assertIn(report["output_files"]["html"], html)
            self.assertIn("Review omitted inputs separately", html)

    def test_user_input_all_over_limit_files_fail_closed(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_over_limit_input")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            state_dir = tmp_root / "memory-state"
            state_dir.mkdir()
            oversized = state_dir / "MEMORY.md"
            oversized.write_text("memory\n" + ("x" * module.MAX_INPUT_FILE_BYTES), encoding="utf-8")

            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=state_dir,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "fail_memory_state_influence_boundary_report")
            self.assertEqual(report["input_file_count"], 0)
            self.assertEqual(report["skipped_input_count"], 1)
            self.assertEqual(report["skipped_inputs"][0]["reason"], "max_input_file_bytes_exceeded")
            self.assertIn("no supported input files were scanned within configured limits", report["errors"])

    def test_user_input_invalid_json_is_blocked_with_parse_finding(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_invalid_json")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            state_file = tmp_root / "checkpoint.json"
            state_file.write_text('{"thread_id": "thread-1", "channel_values": ', encoding="utf-8")

            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=state_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["input_file_count"], 1)
            self.assertIn("json_parse_error", report["input_files"][0]["signal_ids"])
            self.assertEqual(
                report["input_files"][0]["decision"]["decision"],
                "blocked_until_parseable_state_export",
            )
            self.assertIn(str(state_file.relative_to(tmp_root)), report["influence_boundary"]["blocked_refs"])
            parse_finding = next(
                finding for finding in report["findings"] if finding["finding_id"] == "json_parse_error_blocks_state_export"
            )
            self.assertEqual(parse_finding["severity"], "high")
            self.assertFalse(parse_finding["raw_content_included"])
            self.assertIn("repair the JSON/JSONL export", parse_finding["recommendation"])

    def test_user_input_invalid_toml_is_blocked_with_parse_finding(self) -> None:
        module = _load_module(DEMO_SCRIPT, "run_memory_state_governability_overlay_demo_invalid_toml")
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            state_file = tmp_root / "state-policy.toml"
            state_file.write_text("[profile\nmemory = 'release state'\n", encoding="utf-8")

            report = module.build_memory_state_influence_boundary_report(
                tmp_root,
                input_path=state_file,
                output_dir=tmp_root / ".ctxvault" / "overlay",
            )

            self.assertEqual(report["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(report["input_file_count"], 1)
            self.assertIn("toml_parse_error", report["input_files"][0]["signal_ids"])
            self.assertEqual(
                report["input_files"][0]["decision"]["decision"],
                "blocked_until_parseable_state_export",
            )
            self.assertIn(str(state_file.relative_to(tmp_root)), report["influence_boundary"]["blocked_refs"])
            parse_finding = next(
                finding for finding in report["findings"] if finding["finding_id"] == "toml_parse_error_blocks_state_export"
            )
            self.assertEqual(parse_finding["severity"], "high")
            self.assertFalse(parse_finding["raw_content_included"])
            self.assertIn("repair the TOML export", parse_finding["recommendation"])

    def test_user_input_summary_command_is_runnable(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "AGENTS.md"
            input_file.write_text(
                "Project memory: release copy may inform answers only. Never publish without approval.\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(DEMO_SCRIPT),
                    "--root",
                    str(tmp_root),
                    "--input",
                    str(input_file),
                    "--output-dir",
                    str(tmp_root / ".ctxvault" / "overlay"),
                    "--format",
                    "summary",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Local Memory State Influence Boundary Report", completed.stdout)
            self.assertIn("status=pass_memory_state_influence_boundary_report", completed.stdout)
            self.assertIn("input_file_count=1", completed.stdout)
            self.assertIn("raw_content_included=false", completed.stdout)
            self.assertIn("integration_gate_passed=false", completed.stdout)
            self.assertIn("fail_on_blocked_exit_code=2", completed.stdout)
            self.assertIn("finding[0]=info:candidate_memory_state_influence", completed.stdout)
            self.assertIn("recommendation=Keep this ref inform-only", completed.stdout)

    def test_user_input_summary_reports_failure_reason(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            missing = tmp_root / "missing-memory.md"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(DEMO_SCRIPT),
                    "--root",
                    str(tmp_root),
                    "--input",
                    str(missing),
                    "--output-dir",
                    str(tmp_root / ".ctxvault" / "overlay"),
                    "--format",
                    "summary",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertIn("status=fail_memory_state_influence_boundary_report", completed.stdout)
            self.assertIn("error[0]=input path does not exist:", completed.stdout)

    def test_influence_boundary_alias_script_is_runnable(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "MEMORY.md"
            input_file.write_text(
                "Remembered project state. Deploy and publish only after rollback approval.\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INFLUENCE_BOUNDARY_SCRIPT),
                    "--root",
                    str(tmp_root),
                    "--input",
                    str(input_file),
                    "--output-dir",
                    str(tmp_root / ".ctxvault" / "overlay"),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(payload["schema_id"], "ctxvault.memory-state-influence-boundary-report/v0")
            self.assertEqual(payload["input_file_count"], 1)
            self.assertIn("action_or_tool_authority", payload["input_files"][0]["signal_ids"])
            self.assertTrue((tmp_root / payload["output_files"]["json"]).exists())
            self.assertFalse(payload["side_effect_boundary"]["provider_or_model_call_performed"])
            self.assertFalse(payload["side_effect_boundary"]["target_file_written"])

    def test_fail_on_blocked_exits_nonzero_for_blocked_user_input(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "MEMORY.md"
            input_file.write_text(
                "Remembered project state. Deploy and publish only after rollback approval.\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INFLUENCE_BOUNDARY_SCRIPT),
                    "--root",
                    str(tmp_root),
                    "--input",
                    str(input_file),
                    "--output-dir",
                    str(tmp_root / ".ctxvault" / "overlay"),
                    "--format",
                    "summary",
                    "--fail-on-blocked",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            self.assertIn("status=pass_memory_state_influence_boundary_report", completed.stdout)
            self.assertIn("blocked_refs=1", completed.stdout)
            self.assertTrue((tmp_root / ".ctxvault" / "overlay" / "influence-boundary-report.json").exists())

    def test_gate_format_outputs_machine_readable_gate_for_product_integration(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            input_file = tmp_root / "MEMORY.md"
            secret_value = "sk-gateformat0000000000000000"
            input_file.write_text(
                f"Remembered project state. Deploy only after rollback approval. api_key={secret_value}\n",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [
                    sys.executable,
                    str(INFLUENCE_BOUNDARY_SCRIPT),
                    "--root",
                    str(tmp_root),
                    "--input",
                    str(input_file),
                    "--output-dir",
                    str(tmp_root / ".ctxvault" / "overlay"),
                    "--format",
                    "gate",
                    "--fail-on-blocked",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(completed.returncode, 2)
            gate = json.loads(completed.stdout)
            self.assertEqual(
                gate["schema_id"],
                "ctxvault.memory-state-influence-boundary-integration-gate/v0",
            )
            self.assertEqual(gate["mode"], "fail_on_blocked")
            self.assertFalse(gate["passed"])
            self.assertEqual(gate["default_exit_code"], 0)
            self.assertEqual(gate["fail_on_blocked_exit_code"], 2)
            self.assertEqual(gate["blocked_ref_count"], 1)
            self.assertFalse(gate["raw_content_included"])
            self.assertNotIn(secret_value, completed.stdout)
            self.assertTrue((tmp_root / ".ctxvault" / "overlay" / "influence-boundary-report.json").exists())

    def test_gate_format_requires_user_input_mode(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(DEMO_SCRIPT),
                "--format",
                "gate",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        gate = json.loads(completed.stdout)
        self.assertEqual(gate["status"], "fail_integration_gate_unavailable")
        self.assertIn("--input", gate["reason"])

    def test_integration_gate_schema_and_example_match_sample_output(self) -> None:
        blocked_completed = subprocess.run(
            [
                sys.executable,
                str(INFLUENCE_BOUNDARY_SCRIPT),
                "--input",
                "examples/memory-state-influence-boundary/",
                "--format",
                "gate",
                "--fail-on-blocked",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        pass_completed = subprocess.run(
            [
                sys.executable,
                str(INFLUENCE_BOUNDARY_SCRIPT),
                "--input",
                "examples/memory-state-influence-boundary/state-policy.toml",
                "--format",
                "gate",
                "--fail-on-blocked",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(blocked_completed.returncode, 2)
        self.assertEqual(pass_completed.returncode, 0)
        schema = json.loads(GATE_SCHEMA.read_text(encoding="utf-8"))
        example = json.loads(GATE_EXAMPLE.read_text(encoding="utf-8"))
        pass_example = json.loads(GATE_PASS_EXAMPLE.read_text(encoding="utf-8"))
        gate = json.loads(blocked_completed.stdout)
        pass_gate = json.loads(pass_completed.stdout)
        required = schema["required"]
        self.assertEqual(schema["properties"]["schema_id"]["const"], gate["schema_id"])
        self.assertFalse(schema["properties"]["raw_content_included"]["const"])
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("not a stable protocol", schema["description"])
        self.assertEqual(sorted(example), sorted(required))
        self.assertEqual(sorted(pass_example), sorted(required))
        self.assertEqual(example, gate)
        self.assertEqual(pass_example, pass_gate)
        self.assertFalse(gate["passed"])
        self.assertTrue(pass_gate["passed"])

    def test_integration_gate_contract_checker_validates_stdout_schema_example_and_exit_code(self) -> None:
        module = _load_module(GATE_CONTRACT_SCRIPT, "check_memory_state_influence_boundary_integration_gate_contract")
        result = module.check_memory_state_influence_boundary_integration_gate_contract(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_integration_gate_contract")
        self.assertEqual(result["stdout_json_status"], "pass")
        self.assertEqual(result["schema_contract_status"], "pass")
        self.assertEqual(result["example_drift_status"], "pass")
        self.assertEqual(result["exit_code_status"], "pass")
        self.assertEqual(result["gate_command_returncode"], 2)
        self.assertEqual(result["expected_fail_on_blocked_exit_code"], 2)
        self.assertEqual(result["blocked_case_status"], "pass")
        self.assertEqual(result["pass_case_status"], "pass")
        self.assertEqual(result["pass_gate"]["fail_on_blocked_exit_code"], 0)
        self.assertTrue(result["pass_gate"]["passed"])
        self.assertEqual(result["gate"]["schema_id"], "ctxvault.memory-state-influence-boundary-integration-gate/v0")
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])
        self.assertEqual(result["errors"], [])

    def test_full_report_contract_checker_validates_schema_report_raw_boundary_and_gate(self) -> None:
        module = _load_module(REPORT_CONTRACT_SCRIPT, "check_memory_state_influence_boundary_report_contract")
        result = module.check_memory_state_influence_boundary_report_contract(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_report_contract")
        self.assertEqual(result["stdout_json_status"], "pass")
        self.assertEqual(result["schema_contract_status"], "pass")
        self.assertEqual(result["report_contract_status"], "pass")
        self.assertEqual(result["raw_content_boundary_status"], "pass")
        self.assertEqual(result["integration_gate_embedded_status"], "pass")
        self.assertEqual(result["sample_input_file_count"], 9)
        self.assertEqual(result["sample_blocked_ref_count"], 4)
        self.assertEqual(result["sample_stale_or_superseded_ref_count"], 2)
        self.assertRegex(result["sample_output_files"]["json"], r"influence-boundary-report\.json$")
        schema = json.loads(REPORT_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["schema_id"]["const"],
            "ctxvault.memory-state-influence-boundary-report/v0",
        )
        self.assertFalse(schema["$defs"]["scan_limits"]["properties"]["raw_content_included"]["const"])
        self.assertFalse(schema["$defs"]["input_file"]["properties"]["raw_content_included"]["const"])
        self.assertFalse(schema["$defs"]["integration_gate"]["properties"]["raw_content_included"]["const"])
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("not a stable protocol", schema["description"])
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])
        self.assertEqual(result["errors"], [])

    def test_consumer_integration_checker_maps_gate_to_product_decisions(self) -> None:
        module = _load_module(CONSUMER_INTEGRATION_SCRIPT, "check_memory_state_influence_boundary_consumer_integration")
        result = module.check_memory_state_influence_boundary_consumer_integration(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_consumer_integration")
        self.assertEqual(result["blocked_report_contract_status"], "pass")
        self.assertEqual(result["blocked_raw_content_boundary_status"], "pass")
        self.assertEqual(result["blocked_embedded_gate_status"], "pass")
        self.assertEqual(result["pass_report_contract_status"], "pass")
        self.assertEqual(result["pass_raw_content_boundary_status"], "pass")
        self.assertEqual(result["pass_embedded_gate_status"], "pass")
        self.assertEqual(result["blocked_gate_returncode"], 2)
        self.assertEqual(result["pass_gate_returncode"], 0)
        self.assertEqual(result["blocked_decision"]["decision"], "block")
        self.assertEqual(result["blocked_decision"]["reason"], "blocked_refs_present")
        self.assertEqual(result["pass_decision"]["decision"], "allow_inform_only")
        self.assertEqual(result["pass_decision"]["reason"], "gate_passed_no_blocked_refs")
        self.assertFalse(result["blocked_decision"]["consumed_raw_content"])
        self.assertFalse(result["pass_decision"]["consumed_raw_content"])
        self.assertFalse(result["external_absolute_path_leaked"])
        self.assertFalse(result["secret_like_content_leaked"])
        self.assertFalse(result["raw_content_included"])
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])
        self.assertEqual(result["errors"], [])

    def test_byo_smoke_checker_validates_external_input_and_gate_paths(self) -> None:
        module = _load_module(BYO_SMOKE_SCRIPT, "check_memory_state_influence_boundary_byo_smoke")
        result = module.check_memory_state_influence_boundary_byo_smoke(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_byo_smoke")
        self.assertEqual(result["report_status"], "pass_memory_state_influence_boundary_report")
        self.assertEqual(result["input_kind"], "directory")
        self.assertEqual(result["input_file_count"], 2)
        self.assertEqual(result["skipped_input_count"], 1)
        self.assertEqual(result["blocked_ref_count"], 1)
        self.assertEqual(result["inform_only_allowed_ref_count"], 1)
        self.assertEqual(result["omitted_ref_count"], 1)
        self.assertEqual(result["imported_context_ref_count"], 1)
        self.assertEqual(result["blocked_gate_returncode"], 2)
        self.assertEqual(result["pass_gate_returncode"], 0)
        self.assertFalse(result["blocked_gate"]["passed"])
        self.assertTrue(result["pass_gate"]["passed"])
        self.assertFalse(result["external_absolute_path_leaked"])
        self.assertFalse(result["secret_like_content_leaked"])
        self.assertFalse(result["raw_content_included"])
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])

    def test_social_payload_is_ready_for_manual_linkedin_and_x_posting(self) -> None:
        module = _load_module(SOCIAL_SCRIPT, "render_memory_state_governability_overlay_social_payload")
        with TemporaryDirectory() as tmp:
            payload = module.render_memory_state_governability_overlay_social_payload(
                ROOT,
                output_json=Path(tmp) / "social.json",
                output_md=Path(tmp) / "social.md",
            )

            self.assertEqual(payload["status"], "pass_memory_state_governability_overlay_social_payload")
            self.assertEqual(payload["x"]["tweet_count"], 5)
            self.assertTrue(all(count <= 280 for count in payload["x"]["tweet_character_counts"]))
            self.assertIn(
                "python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/",
                payload["linkedin"]["body"],
            )
            self.assertIn("python3 scripts/run_memory_state_influence_boundary_report.py --input ./memory-state/", payload["linkedin"]["body"])
            self.assertIn("YAML/YML state files", payload["linkedin"]["body"])
            self.assertIn("MDX context files", payload["linkedin"]["body"])
            self.assertIn("TOML state profiles", payload["linkedin"]["body"])
            self.assertIn("structured JSON/TOML/YAML", payload["linkedin"]["body"])
            self.assertIn("input-relative paths", payload["linkedin"]["body"])
            self.assertIn("integration_gate", payload["linkedin"]["body"])
            self.assertIn("fail_on_blocked_exit_code", payload["linkedin"]["body"])
            self.assertIn("ctxvault-memory-state-influence-boundary-report-v0.schema.json", payload["linkedin"]["body"])
            self.assertIn("--format gate --fail-on-blocked", payload["linkedin"]["body"])
            self.assertIn("check_memory_state_influence_boundary_integration_gate_contract.py", payload["linkedin"]["body"])
            self.assertIn("check_memory_state_influence_boundary_report_contract.py", payload["linkedin"]["body"])
            self.assertIn("check_memory_state_influence_boundary_consumer_integration.py", payload["linkedin"]["body"])
            self.assertIn("check_memory_state_influence_boundary_consumer_wrapper_contract.py", payload["linkedin"]["body"])
            self.assertIn("run_memory_state_influence_boundary_consumer_wrapper_example.py", payload["linkedin"]["body"])
            self.assertIn(
                "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml",
                payload["linkedin"]["body"],
            )
            self.assertIn("check_memory_state_influence_boundary_byo_smoke.py", payload["linkedin"]["body"])
            self.assertEqual(
                payload["gate_contract_command"],
                "python3 scripts/check_memory_state_influence_boundary_integration_gate_contract.py",
            )
            self.assertEqual(
                payload["report_contract_command"],
                "python3 scripts/check_memory_state_influence_boundary_report_contract.py",
            )
            self.assertEqual(
                payload["consumer_integration_command"],
                "python3 scripts/check_memory_state_influence_boundary_consumer_integration.py",
            )
            self.assertEqual(
                payload["consumer_wrapper_contract_command"],
                "python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py",
            )
            self.assertEqual(
                payload["consumer_wrapper_command"],
                "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py",
            )
            self.assertEqual(
                payload["consumer_wrapper_pass_command"],
                "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml",
            )
            self.assertEqual(
                payload["byo_smoke_command"],
                "python3 scripts/check_memory_state_influence_boundary_byo_smoke.py",
            )
            self.assertTrue(any("allow_inform_only" in tweet for tweet in payload["x"]["tweets"]))
            self.assertIn("review recommendations", payload["linkedin"]["body"])
            self.assertIn("user-supplied", payload["linkedin"]["body"])
            self.assertIn("not a provider integration", payload["linkedin"]["body"])
            self.assertEqual(
                payload["hn"]["title"],
                "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report",
            )
            self.assertEqual(payload["hn"]["submission_type"], "url")
            self.assertEqual(payload["hn"]["text"], "")
            for field, observed in payload["claim_boundary"].items():
                self.assertFalse(observed, field)
            for field, observed in payload["side_effect_boundary"].items():
                self.assertFalse(observed, field)

    def test_social_draft_drift_checker_pins_static_posts_to_payload(self) -> None:
        module = _load_module(SOCIAL_DRAFT_DRIFT_SCRIPT, "check_memory_state_influence_boundary_social_draft_drift")
        result = module.check_memory_state_influence_boundary_social_draft_drift(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_social_draft_drift")
        self.assertEqual(result["payload_status"], "pass_memory_state_governability_overlay_social_payload")
        self.assertEqual(result["payload_json_drift_status"], "pass")
        self.assertEqual(result["payload_markdown_drift_status"], "pass")
        self.assertEqual(result["hn_draft_drift_status"], "pass")
        self.assertEqual(result["linkedin_draft_drift_status"], "pass")
        self.assertEqual(result["x_thread_drift_status"], "pass")
        self.assertEqual(result["old_positioning_status"], "pass")
        self.assertEqual(result["old_positioning_hits"], {})
        self.assertEqual(
            result["hn_title"],
            "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report",
        )
        self.assertEqual(
            result["hn_url"],
            "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
        )
        self.assertEqual(result["x_tweet_count"], 5)
        self.assertTrue(all(count <= 280 for count in result["x_tweet_character_counts"]))
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])
        self.assertEqual(result["errors"], [])

    def test_owner_publish_packet_combines_preflight_commands_and_social_copy(self) -> None:
        module = _load_module(OWNER_PACKET_SCRIPT, "render_memory_state_influence_boundary_owner_publish_packet")
        final_preflight = {
            "status": "pass_memory_state_influence_boundary_final_preflight",
            "go_no_go": "go_local_ready_external_publish_pending",
            "issue_count": 0,
            "command_count": 22,
            "sample_input_file_count": 9,
            "sample_blocked_ref_count": 4,
            "sample_stale_ref_count": 2,
            "publication_bundle_status": "pass_memory_state_influence_boundary_publication_bundle",
            "publication_bundle_sha256": "a" * 64,
            "publication_file_count": 52,
            "materialized_copied_file_count": 52,
            "publish_command_envelope_status": "pass_memory_state_influence_boundary_publish_command_envelope",
            "social_draft_drift_status": "pass_memory_state_influence_boundary_social_draft_drift",
            "social_draft_old_positioning_status": "pass",
            "consumer_wrapper_contract_status": "pass_memory_state_influence_boundary_consumer_wrapper_contract",
            "consumer_wrapper_contract_blocked_decision": "block",
            "consumer_wrapper_contract_pass_decision": "allow_inform_only",
            "release_distinctness_status": "pass_memory_state_influence_boundary_release_distinctness",
            "release_distinctness_warning_count": 0,
            "public_page": "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
        }
        social_payload = {
            "status": "pass_memory_state_governability_overlay_social_payload",
            "hn": {
                "submission_type": "url",
                "title": "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report",
                "url": "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
                "text": "",
            },
            "linkedin": {"body": "LinkedIn body with integration_gate and allow_inform_only."},
            "x": {"tweet_count": 1, "tweets": ["1/ Drop in AI memory files."]},
        }
        social_draft_drift = {
            "status": "pass_memory_state_influence_boundary_social_draft_drift",
            "payload_json_drift_status": "pass",
            "payload_markdown_drift_status": "pass",
            "hn_draft_drift_status": "pass",
            "linkedin_draft_drift_status": "pass",
            "x_thread_drift_status": "pass",
            "old_positioning_status": "pass",
            "old_positioning_hits": {},
        }
        publish_envelope = {
            "status": "pass_memory_state_influence_boundary_publish_command_envelope",
            "publication_bundle_sha256": "a" * 64,
            "publish_commands": [
                "git add README.md scripts/render_memory_state_influence_boundary_owner_publish_packet.py",
                "git commit -m \"Add local memory state influence boundary report\"",
                "git push origin main",
            ],
            "post_publish_commands": ["python3 scripts/check_memory_state_influence_boundary_live_publication.py --live"],
            "manual_social_actions": [
                "submit or update the HN follow-up only after the public page is live",
                "post the prepared X thread manually",
                "post the prepared LinkedIn copy manually",
            ],
        }

        with TemporaryDirectory() as tmp:
            result = module.render_memory_state_influence_boundary_owner_publish_packet(
                ROOT,
                output_json=Path(tmp) / "owner.json",
                output_md=Path(tmp) / "owner.md",
                final_preflight=final_preflight,
                social_payload=social_payload,
                social_draft_drift=social_draft_drift,
                publish_envelope=publish_envelope,
            )

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_owner_publish_packet")
            self.assertEqual(result["publication_bundle_sha256"], "a" * 64)
            self.assertEqual(result["publication_file_count"], 52)
            self.assertEqual(result["final_preflight"]["issue_count"], 0)
            self.assertEqual(result["social_draft_drift"]["old_positioning_status"], "pass")
            self.assertEqual(
                result["hn"]["title"],
                "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report",
            )
            self.assertIn("git push origin main", result["publish_commands"])
            self.assertTrue(any("check_memory_state_influence_boundary_live_publication.py --live" in command for command in result["post_publish_commands"]))
            self.assertTrue(any("social_draft_drift.py" in item for item in result["owner_review_checklist"]))
            self.assertTrue(any("owner_publish_packet_contract.py" in item for item in result["owner_review_checklist"]))
            self.assertFalse(result["publication_executed"])
            self.assertFalse(result["outreach_performed"])
            self.assertTrue((Path(tmp) / "owner.json").exists())
            self.assertTrue((Path(tmp) / "owner.md").exists())
            self.assertIn("Manual platform submission remains manual", (Path(tmp) / "owner.md").read_text(encoding="utf-8"))

    def test_owner_publish_packet_contract_pins_bundle_commands_and_social_copy(self) -> None:
        bundle_module = _load_module(PUBLICATION_BUNDLE_SCRIPT, "build_memory_state_bundle_for_owner_contract")
        contract_module = _load_module(
            OWNER_PACKET_CONTRACT_SCRIPT,
            "check_memory_state_influence_boundary_owner_publish_packet_contract",
        )
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundle_path = tmp_path / "bundle.json"
            bundle = bundle_module.build_memory_state_influence_boundary_publication_bundle(
                ROOT,
                output_json=bundle_path,
                output_md=tmp_path / "bundle.md",
            )
            result = contract_module.check_memory_state_influence_boundary_owner_publish_packet_contract(
                ROOT,
                bundle_path=bundle_path,
            )

            self.assertEqual(
                result["status"],
                "pass_memory_state_influence_boundary_owner_publish_packet_contract",
            )
            self.assertEqual(result["owner_packet_status"], "pass_memory_state_influence_boundary_owner_publish_packet")
            self.assertEqual(result["publication_bundle_status"], "pass_memory_state_influence_boundary_publication_bundle")
            self.assertEqual(result["publication_bundle_sha256"], bundle["publication_bundle_sha256"])
            self.assertEqual(result["publication_file_count"], bundle["publication_file_count"])
            self.assertEqual(result["publish_command_envelope_status"], "pass_memory_state_influence_boundary_publish_command_envelope")
            self.assertEqual(result["social_draft_drift_status"], "pass_memory_state_influence_boundary_social_draft_drift")
            self.assertEqual(result["social_draft_old_positioning_status"], "pass")
            self.assertEqual(result["consumer_wrapper_contract_status"], "pass_memory_state_influence_boundary_consumer_wrapper_contract")
            self.assertEqual(result["release_distinctness_status"], "pass_memory_state_influence_boundary_release_distinctness")
            self.assertEqual(result["owner_review_checklist_status"], "pass")
            self.assertEqual(result["publish_commands_status"], "pass")
            self.assertEqual(result["post_publish_commands_status"], "pass")
            self.assertEqual(result["social_copy_status"], "pass")
            self.assertEqual(result["rendered_output_boundary_status"], "pass")
            self.assertEqual(
                result["hn_title"],
                "Show HN: CtxGov - drop in AI memory files, get an influence-boundary report",
            )
            self.assertEqual(
                result["hn_url"],
                "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
            )
            self.assertTrue(all(count <= 280 for count in result["x_tweet_character_counts"]))
            for field, observed in result["claim_boundary"].items():
                self.assertFalse(observed, field)
            for field, observed in result["side_effect_boundary"].items():
                self.assertFalse(observed, field)
            self.assertFalse(result["publication_executed"])
            self.assertFalse(result["outreach_performed"])
            self.assertEqual(result["errors"], [])

    def test_release_distinctness_checker_keeps_next_hn_launch_separate(self) -> None:
        module = _load_module(RELEASE_DISTINCTNESS_SCRIPT, "check_memory_state_influence_boundary_release_distinctness")
        result = module.check_memory_state_influence_boundary_release_distinctness(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_release_distinctness")
        self.assertEqual(
            result["canonical_public_page"],
            "https://ctxgov.github.io/ctxgov/memory-state-influence-boundary-try-in-5-minutes.html",
        )
        self.assertIn("claim firewall HN launch", result["distinct_from"])
        self.assertIn("Activation X-Ray HN launch", result["distinct_from"])
        self.assertIn("drop in AI memory files", result["required_distinct_phrases"])
        self.assertEqual(result["error_count"], 0)
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])

    def test_consumer_wrapper_contract_checks_schema_examples_and_decisions(self) -> None:
        module = _load_module(CONSUMER_WRAPPER_CONTRACT_SCRIPT, "check_memory_state_influence_boundary_consumer_wrapper_contract")
        result = module.check_memory_state_influence_boundary_consumer_wrapper_contract(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_consumer_wrapper_contract")
        self.assertEqual(result["schema_contract_status"], "pass")
        self.assertEqual(result["example_drift_status"], "pass")
        self.assertEqual(result["decision_status"], "pass")
        self.assertEqual(result["raw_content_boundary_status"], "pass")
        self.assertEqual(result["blocked_decision"], "block")
        self.assertEqual(result["pass_decision"], "allow_inform_only")
        self.assertEqual(result["blocked_gate_returncode"], 2)
        self.assertEqual(result["pass_gate_returncode"], 0)
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])

    def test_consumer_wrapper_example_emits_block_and_pass_decisions_from_gate(self) -> None:
        module = _load_module(CONSUMER_WRAPPER_SCRIPT, "run_memory_state_influence_boundary_consumer_wrapper_example")
        with TemporaryDirectory() as tmp:
            result = module.run_memory_state_influence_boundary_consumer_wrapper_example(
                ROOT,
                output_dir=Path(tmp) / "consumer-wrapper",
            )
            pass_result = module.run_memory_state_influence_boundary_consumer_wrapper_example(
                ROOT,
                input_path=Path("examples/memory-state-influence-boundary/state-policy.toml"),
                output_dir=Path(tmp) / "consumer-wrapper-pass",
            )

        self.assertEqual(result["status"], "pass_memory_state_influence_boundary_consumer_wrapper_example")
        self.assertEqual(result["decision"]["decision"], "block")
        self.assertEqual(result["decision"]["reason"], "blocked_refs_present")
        self.assertEqual(result["decision"]["gate_returncode"], 2)
        self.assertEqual(result["gate_returncode"], 2)
        self.assertEqual(result["gate"]["blocked_ref_count"], 4)
        self.assertFalse(result["gate"]["raw_content_included"])
        self.assertFalse(result["decision"]["consumed_raw_content"])
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])
        self.assertEqual(pass_result["status"], "pass_memory_state_influence_boundary_consumer_wrapper_example")
        self.assertEqual(pass_result["decision"]["decision"], "allow_inform_only")
        self.assertEqual(pass_result["decision"]["reason"], "gate_passed_no_blocked_refs")
        self.assertEqual(pass_result["decision"]["gate_returncode"], 0)
        self.assertEqual(pass_result["gate_returncode"], 0)
        self.assertEqual(pass_result["gate"]["blocked_ref_count"], 0)
        self.assertFalse(pass_result["gate"]["raw_content_included"])
        self.assertFalse(pass_result["decision"]["consumed_raw_content"])
        self.assertFalse(pass_result["publication_executed"])
        self.assertFalse(pass_result["outreach_performed"])

    def test_publish_pack_checker_passes_with_public_page_and_social_copy(self) -> None:
        module = _load_module(PACK_CHECK_SCRIPT, "check_memory_state_governability_overlay_publish_pack")
        result = module.check_memory_state_governability_overlay_publish_pack(ROOT)

        self.assertEqual(result["status"], "pass_memory_state_governability_overlay_publish_pack")
        self.assertEqual(result["surface_count"], 5)
        self.assertEqual(result["fixture_demo_status"], "pass_memory_state_governability_overlay_demo")
        self.assertEqual(result["demo_status"], "pass_memory_state_influence_boundary_report")
        self.assertGreaterEqual(result["input_file_count"], 9)
        self.assertEqual(result["redaction_demo_status"], "pass_memory_state_influence_boundary_report")
        self.assertEqual(result["redaction_input_file_count"], 1)
        self.assertEqual(result["social_payload_status"], "pass_memory_state_governability_overlay_social_payload")
        self.assertEqual(result["social_draft_drift_status"], "pass_memory_state_influence_boundary_social_draft_drift")
        self.assertEqual(result["social_draft_payload_json_drift_status"], "pass")
        self.assertEqual(result["social_draft_payload_markdown_drift_status"], "pass")
        self.assertEqual(result["social_draft_hn_drift_status"], "pass")
        self.assertEqual(result["social_draft_linkedin_drift_status"], "pass")
        self.assertEqual(result["social_draft_x_thread_drift_status"], "pass")
        self.assertEqual(result["social_draft_old_positioning_status"], "pass")
        self.assertEqual(
            result["owner_packet_contract_status"],
            "pass_memory_state_influence_boundary_owner_publish_packet_contract",
        )
        self.assertRegex(result["owner_packet_contract_bundle_sha256"], r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(result["owner_packet_contract_publication_file_count"], 25)
        self.assertEqual(result["report_schema_status"], "checked")
        self.assertEqual(result["consumer_wrapper_schema_status"], "checked")
        self.assertEqual(result["integration_gate_schema_status"], "checked")
        self.assertEqual(result["integration_gate_example_status"], "checked")
        self.assertEqual(result["integration_gate_pass_example_status"], "checked")
        self.assertEqual(result["consumer_wrapper_example_status"], "checked")
        self.assertEqual(result["consumer_wrapper_pass_example_status"], "checked")
        self.assertEqual(result["integration_gate_contract_status"], "pass_memory_state_influence_boundary_integration_gate_contract")
        self.assertEqual(result["report_contract_status"], "pass_memory_state_influence_boundary_report_contract")
        self.assertEqual(result["report_contract_raw_content_boundary_status"], "pass")
        self.assertEqual(result["report_contract_integration_gate_embedded_status"], "pass")
        self.assertEqual(result["consumer_integration_status"], "pass_memory_state_influence_boundary_consumer_integration")
        self.assertEqual(result["consumer_blocked_decision"], "block")
        self.assertEqual(result["consumer_pass_decision"], "allow_inform_only")
        self.assertEqual(result["consumer_wrapper_contract_status"], "pass_memory_state_influence_boundary_consumer_wrapper_contract")
        self.assertEqual(result["consumer_wrapper_contract_schema_status"], "pass")
        self.assertEqual(result["consumer_wrapper_contract_example_drift_status"], "pass")
        self.assertEqual(result["consumer_wrapper_contract_blocked_decision"], "block")
        self.assertEqual(result["consumer_wrapper_contract_pass_decision"], "allow_inform_only")
        self.assertEqual(result["byo_smoke_status"], "pass_memory_state_influence_boundary_byo_smoke")
        self.assertEqual(result["byo_blocked_gate_returncode"], 2)
        self.assertEqual(result["byo_pass_gate_returncode"], 0)
        self.assertTrue(all(count <= 280 for count in result["x_tweet_character_counts"]))
        self.assertTrue(PUBLIC_PAGE.exists())
        self.assertTrue(LEGACY_PUBLIC_PAGE.exists())
        self.assertIn("memory-state-influence-boundary-try-in-5-minutes.html", LEGACY_PUBLIC_PAGE.read_text(encoding="utf-8"))
        self.assertTrue((PACK_ROOT / "linkedin-post.md").exists())
        self.assertTrue((PACK_ROOT / "x-thread.md").exists())
        self.assertIn(
            "python3 scripts/run_memory_state_influence_boundary_report.py --input examples/memory-state-influence-boundary/",
            PUBLIC_PAGE.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "python3 scripts/run_memory_state_influence_boundary_report.py --input ./CLAUDE.md",
            PUBLIC_PAGE.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "python3 scripts/check_memory_state_influence_boundary_byo_smoke.py",
            PUBLIC_PAGE.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "python3 scripts/check_memory_state_influence_boundary_report_contract.py",
            PUBLIC_PAGE.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "python3 scripts/check_memory_state_influence_boundary_consumer_integration.py",
            PUBLIC_PAGE.read_text(encoding="utf-8"),
        )
        self.assertIn(
            "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml",
            PUBLIC_PAGE.read_text(encoding="utf-8"),
        )
        for field, observed in result["claim_boundary"].items():
            self.assertFalse(observed, field)
        for field, observed in result["side_effect_boundary"].items():
            self.assertFalse(observed, field)
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])

    def test_final_preflight_and_live_page_checker_are_ready(self) -> None:
        final_module = _load_module(FINAL_PREFLIGHT_SCRIPT, "check_memory_state_influence_boundary_final_preflight")
        live_module = _load_module(LIVE_CHECK_SCRIPT, "check_memory_state_influence_boundary_live_publication")

        final = final_module.check_memory_state_influence_boundary_final_preflight(ROOT, include_unittests=False)
        live = live_module.check_memory_state_influence_boundary_live_publication(ROOT, live=False)

        self.assertEqual(final["status"], "pass_memory_state_influence_boundary_final_preflight")
        self.assertEqual(final["go_no_go"], "go_local_ready_external_publish_pending")
        self.assertEqual(final["sample_input_file_count"], 9)
        self.assertEqual(final["sample_blocked_ref_count"], 4)
        self.assertEqual(final["sample_stale_ref_count"], 2)
        self.assertEqual(final["publication_bundle_status"], "pass_memory_state_influence_boundary_publication_bundle")
        self.assertEqual(final["publish_command_envelope_status"], "pass_memory_state_influence_boundary_publish_command_envelope")
        self.assertEqual(
            final["owner_packet_contract_status"],
            "pass_memory_state_influence_boundary_owner_publish_packet_contract",
        )
        self.assertEqual(final["owner_packet_contract_bundle_sha256"], final["publication_bundle_sha256"])
        self.assertEqual(final["owner_packet_contract_publication_file_count"], final["publication_file_count"])
        self.assertEqual(final["owner_packet_contract_social_copy_status"], "pass")
        self.assertEqual(final["owner_packet_contract_publish_commands_status"], "pass")
        self.assertEqual(
            final["integration_gate_contract_status"],
            "pass_memory_state_influence_boundary_integration_gate_contract",
        )
        self.assertEqual(
            final["report_contract_status"],
            "pass_memory_state_influence_boundary_report_contract",
        )
        self.assertEqual(final["report_contract_raw_content_boundary_status"], "pass")
        self.assertEqual(final["report_contract_integration_gate_embedded_status"], "pass")
        self.assertEqual(
            final["consumer_integration_status"],
            "pass_memory_state_influence_boundary_consumer_integration",
        )
        self.assertEqual(final["consumer_blocked_decision"], "block")
        self.assertEqual(final["consumer_pass_decision"], "allow_inform_only")
        self.assertEqual(
            final["consumer_wrapper_contract_status"],
            "pass_memory_state_influence_boundary_consumer_wrapper_contract",
        )
        self.assertEqual(final["consumer_wrapper_contract_schema_status"], "pass")
        self.assertEqual(final["consumer_wrapper_contract_example_drift_status"], "pass")
        self.assertEqual(final["consumer_wrapper_contract_blocked_decision"], "block")
        self.assertEqual(final["consumer_wrapper_contract_pass_decision"], "allow_inform_only")
        self.assertEqual(
            final["consumer_wrapper_example_status"],
            "pass_memory_state_influence_boundary_consumer_wrapper_example",
        )
        self.assertEqual(final["consumer_wrapper_example_decision"], "block")
        self.assertEqual(final["consumer_wrapper_example_gate_returncode"], 2)
        self.assertEqual(
            final["consumer_wrapper_block_example_status"],
            "pass_memory_state_influence_boundary_consumer_wrapper_example",
        )
        self.assertEqual(final["consumer_wrapper_block_example_decision"], "block")
        self.assertEqual(final["consumer_wrapper_block_example_gate_returncode"], 2)
        self.assertEqual(
            final["consumer_wrapper_pass_example_status"],
            "pass_memory_state_influence_boundary_consumer_wrapper_example",
        )
        self.assertEqual(final["consumer_wrapper_pass_example_decision"], "allow_inform_only")
        self.assertEqual(final["consumer_wrapper_pass_example_gate_returncode"], 0)
        self.assertEqual(
            final["release_distinctness_status"],
            "pass_memory_state_influence_boundary_release_distinctness",
        )
        self.assertEqual(final["release_distinctness_warning_count"], 0)
        self.assertEqual(final["social_draft_drift_status"], "pass_memory_state_influence_boundary_social_draft_drift")
        self.assertEqual(final["social_draft_hn_drift_status"], "pass")
        self.assertEqual(final["social_draft_linkedin_drift_status"], "pass")
        self.assertEqual(final["social_draft_x_thread_drift_status"], "pass")
        self.assertEqual(final["social_draft_old_positioning_status"], "pass")
        self.assertEqual(final["byo_smoke_status"], "pass_memory_state_influence_boundary_byo_smoke")
        self.assertEqual(final["byo_blocked_gate_returncode"], 2)
        self.assertEqual(final["byo_pass_gate_returncode"], 0)
        self.assertGreaterEqual(final["publication_file_count"], 25)
        self.assertEqual(final["materialized_copied_file_count"], final["publication_file_count"])
        self.assertRegex(final["publication_bundle_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(final["issue_count"], 0)
        self.assertEqual(final["checks"]["memory_state_unittests"]["status"], "skipped_by_caller")
        self.assertEqual(
            final["checks"]["publication_bundle_materialization_smoke"]["observed_status"],
            "pass_memory_state_influence_boundary_publication_bundle_materialized",
        )
        self.assertGreaterEqual(
            final["checks"]["publication_bundle_materialization_smoke"]["payload"]["copied_file_count"],
            25,
        )
        publisher_smoke = final["checks"]["public_patch_publisher_dry_run_smoke"]
        self.assertEqual(
            publisher_smoke["observed_status"],
            "pass_memory_state_influence_boundary_public_patch_publisher",
        )
        self.assertEqual(publisher_smoke["payload"]["mode"], "dry_run")
        self.assertEqual(
            publisher_smoke["payload"]["source_final_preflight_status"],
            "pass_memory_state_influence_boundary_final_preflight",
        )
        self.assertEqual(publisher_smoke["payload"]["source_final_preflight_unittests"], "skipped_by_caller")
        self.assertFalse(publisher_smoke["payload"]["local_checkout_write_executed"])
        self.assertFalse(publisher_smoke["payload"]["commit_created"])
        self.assertFalse(publisher_smoke["payload"]["push_executed"])
        self.assertFalse(publisher_smoke["payload"]["publication_executed"])
        self.assertFalse(publisher_smoke["payload"]["outreach_performed"])
        self.assertEqual(publisher_smoke["payload"]["checkout_status_before"]["line_count"], 0)
        self.assertEqual(publisher_smoke["payload"]["checkout_status_after"]["line_count"], 0)
        self.assertIn("python3 scripts/check_memory_state_influence_boundary_live_publication.py --live", final["required_external_actions"][2])
        self.assertFalse(final["publication_executed"])
        self.assertFalse(final["outreach_performed"])
        self.assertEqual(live["status"], "pass_memory_state_influence_boundary_live_publication_check")
        self.assertFalse(live["live_fetch_performed"])
        self.assertFalse(live["publication_executed"])
        self.assertFalse(live["outreach_performed"])

    def test_live_page_checker_records_http_error_status(self) -> None:
        module = _load_module(LIVE_CHECK_SCRIPT, "check_memory_state_influence_boundary_live_publication_http_error")

        def fake_urlopen(url: str, timeout: float) -> object:
            raise module.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)

        original_urlopen = module.urlopen
        module.urlopen = fake_urlopen
        try:
            result = module.check_memory_state_influence_boundary_live_publication(ROOT, live=True)
        finally:
            module.urlopen = original_urlopen

        self.assertEqual(result["status"], "fail_memory_state_influence_boundary_live_publication_check")
        self.assertTrue(result["live_fetch_performed"])
        self.assertEqual(result["live_status"]["http_status"], 404)
        self.assertIn("HTTP Error 404", result["live_status"]["error"])
        self.assertFalse(result["publication_executed"])
        self.assertFalse(result["outreach_performed"])

    def test_publication_bundle_lists_memory_state_public_patch_files(self) -> None:
        module = _load_module(PUBLICATION_BUNDLE_SCRIPT, "build_memory_state_influence_boundary_publication_bundle")
        with TemporaryDirectory() as tmp:
            result = module.build_memory_state_influence_boundary_publication_bundle(
                ROOT,
                output_json=Path(tmp) / "bundle.json",
                output_md=Path(tmp) / "bundle.md",
            )

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_publication_bundle")
            self.assertEqual(result["milestone"], "Local Memory State Influence Boundary Report")
            self.assertEqual(result["public_repo"], "ctxgov/ctxgov")
            self.assertGreaterEqual(result["publication_file_count"], 25)
            for rel in (
                "README.md",
                "docs/index.html",
                "docs/memory-state-influence-boundary-try-in-5-minutes.html",
                "docs/memory-state-governability-overlay-try-in-5-minutes.html",
                "schemas/README.md",
                "schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json",
                "schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json",
                "schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json",
                "examples/memory-state-influence-boundary/CLAUDE.md",
                "examples/memory-state-influence-boundary/checkpoint.json",
                "examples/memory-state-influence-boundary/context-note.mdx",
                "examples/memory-state-influence-boundary/state-profile.yaml",
                "examples/memory-state-influence-boundary/state-policy.toml",
                "fixtures/v0.7.0-mgp-sidecar/memory-xray/memory-state-governability-overlays-20260611.json",
                "release/memory-state-governability-overlay/2026-06-11/product-integration-quickstart.md",
                "release/memory-state-governability-overlay/2026-06-11/public-checkout-readiness-receipt.md",
                "release/memory-state-governability-overlay/2026-06-11/integration-gate.example.json",
                "release/memory-state-governability-overlay/2026-06-11/integration-gate.pass.example.json",
                "release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json",
                "release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json",
                "release/memory-state-governability-overlay/2026-06-11/memory-state-governability-overlay-social-payload.json",
                "scripts/build_memory_state_influence_boundary_publication_bundle.py",
                "scripts/materialize_memory_state_influence_boundary_publication_bundle.py",
                "scripts/render_memory_state_influence_boundary_owner_publish_packet.py",
                "scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
                "scripts/render_memory_state_influence_boundary_publish_command_envelope.py",
                "scripts/check_memory_state_influence_boundary_byo_smoke.py",
                "scripts/check_memory_state_influence_boundary_integration_gate_contract.py",
                "scripts/check_memory_state_influence_boundary_report_contract.py",
                "scripts/check_memory_state_influence_boundary_consumer_integration.py",
                "scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py",
                "scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py",
                "scripts/check_memory_state_influence_boundary_release_distinctness.py",
                "scripts/check_memory_state_influence_boundary_final_preflight.py",
                "scripts/check_memory_state_influence_boundary_public_checkout_readiness.py",
                "scripts/check_memory_state_influence_boundary_live_publication.py",
                "scripts/check_memory_state_influence_boundary_social_draft_drift.py",
                "scripts/publish_memory_state_influence_boundary_public_patch.py",
                "scripts/run_memory_state_influence_boundary_report.py",
                "scripts/run_memory_state_governability_overlay_demo.py",
                "tests/test_memory_state_governability_overlay_demo.py",
            ):
                self.assertIn(rel, result["publication_files"])
                self.assertIn(rel, result["file_digests"])
                self.assertRegex(result["file_digests"][rel]["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(result["sample_report_status"], "pass_memory_state_influence_boundary_report")
            self.assertEqual(result["final_preflight_status"], "checked_by_outer_preflight")
            self.assertEqual(result["publish_pack_status"], "pass_memory_state_governability_overlay_publish_pack")
            self.assertEqual(result["sample_input_file_count"], 9)
            self.assertEqual(result["sample_blocked_ref_count"], 4)
            self.assertEqual({}, result["private_marker_hits"])
            self.assertTrue(result["publication_bundle_sha256"])
            self.assertFalse(result["publication_executed"])
            self.assertFalse(result["push_executed"])
            self.assertFalse(result["outreach_performed"])

    def test_publication_bundle_materializes_to_clean_checkout_without_public_write(self) -> None:
        bundle_module = _load_module(PUBLICATION_BUNDLE_SCRIPT, "build_memory_state_publication_bundle_materializer_test")
        materialize_module = _load_module(MATERIALIZE_BUNDLE_SCRIPT, "materialize_memory_state_influence_boundary_publication_bundle")
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundle_path = tmp_path / "bundle.json"
            bundle_module.build_memory_state_influence_boundary_publication_bundle(
                ROOT,
                output_json=bundle_path,
                output_md=tmp_path / "bundle.md",
            )
            checkout = tmp_path / "checkout"
            checkout.mkdir()
            subprocess.run(["git", "init"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            result = materialize_module.materialize_memory_state_influence_boundary_publication_bundle(
                ROOT,
                checkout,
                bundle_path=bundle_path,
            )

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_publication_bundle_materialized")
            self.assertGreaterEqual(result["copied_file_count"], 25)
            self.assertIn("docs/memory-state-influence-boundary-try-in-5-minutes.html", result["copied_files"])
            self.assertIn("docs/memory-state-governability-overlay-try-in-5-minutes.html", result["copied_files"])
            self.assertIn(
                "schemas/json/ctxvault-memory-state-influence-boundary-consumer-wrapper-example-v0.schema.json",
                result["copied_files"],
            )
            self.assertIn("examples/memory-state-influence-boundary/CLAUDE.md", result["copied_files"])
            self.assertIn("examples/memory-state-influence-boundary/context-note.mdx", result["copied_files"])
            self.assertIn("examples/memory-state-influence-boundary/state-profile.yaml", result["copied_files"])
            self.assertIn("examples/memory-state-influence-boundary/state-policy.toml", result["copied_files"])
            self.assertIn("release/memory-state-governability-overlay/2026-06-11/product-integration-quickstart.md", result["copied_files"])
            self.assertIn("release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.example.json", result["copied_files"])
            self.assertIn("release/memory-state-governability-overlay/2026-06-11/consumer-wrapper.pass.example.json", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_final_preflight.py", result["copied_files"])
            self.assertIn("scripts/render_memory_state_influence_boundary_owner_publish_packet.py", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_consumer_integration.py", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py", result["copied_files"])
            self.assertIn("scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_release_distinctness.py", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_social_draft_drift.py", result["copied_files"])
            self.assertIn("scripts/check_memory_state_influence_boundary_public_checkout_readiness.py", result["copied_files"])
            self.assertIn("scripts/materialize_memory_state_influence_boundary_publication_bundle.py", result["copied_files"])
            self.assertIn("scripts/run_memory_state_influence_boundary_report.py", result["copied_files"])
            self.assertEqual(result["before_status_line_count"], 0)
            self.assertTrue(result["after_status_lines"])
            self.assertTrue(result["local_checkout_write_executed"])
            self.assertFalse(result["commit_created"])
            self.assertFalse(result["push_executed"])
            self.assertFalse(result["publication_executed"])
            self.assertFalse(result["outreach_performed"])

    def test_publish_command_envelope_is_ready_without_external_publication(self) -> None:
        bundle_module = _load_module(PUBLICATION_BUNDLE_SCRIPT, "build_memory_state_publication_bundle_for_envelope")
        envelope_module = _load_module(PUBLISH_ENVELOPE_SCRIPT, "render_memory_state_influence_boundary_publish_command_envelope")
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bundle_path = tmp_path / "bundle.json"
            bundle = bundle_module.build_memory_state_influence_boundary_publication_bundle(
                ROOT,
                output_json=bundle_path,
                output_md=tmp_path / "bundle.md",
            )
            envelope = envelope_module.render_memory_state_influence_boundary_publish_command_envelope(
                ROOT,
                bundle_path=bundle_path,
            )

            self.assertEqual(envelope["status"], "pass_memory_state_influence_boundary_publish_command_envelope")
            self.assertEqual(envelope["publication_bundle_sha256"], bundle["publication_bundle_sha256"])
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_final_preflight.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_byo_smoke.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_report_contract.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_consumer_integration.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_consumer_wrapper_contract.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py", envelope["pre_publish_commands"])
            self.assertIn(
                "python3 scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py --input examples/memory-state-influence-boundary/state-policy.toml",
                envelope["pre_publish_commands"],
            )
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_social_draft_drift.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/render_memory_state_influence_boundary_owner_publish_packet.py", envelope["pre_publish_commands"])
            self.assertIn(
                "python3 scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py",
                envelope["pre_publish_commands"],
            )
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_release_distinctness.py", envelope["pre_publish_commands"])
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_public_checkout_readiness.py --check-live", envelope["pre_publish_commands"])
            self.assertIn(
                "python3 scripts/publish_memory_state_influence_boundary_public_patch.py --checkout <clean-ctxgov-checkout>",
                envelope["pre_publish_commands"],
            )
            self.assertIn("python3 scripts/check_memory_state_influence_boundary_live_publication.py --live", envelope["post_publish_commands"])
            self.assertIn("git push origin main", envelope["publish_commands"])
            self.assertTrue(any("examples/memory-state-influence-boundary" in command for command in envelope["publish_commands"]))
            self.assertTrue(
                any(
                    "schemas/json/ctxvault-memory-state-influence-boundary-integration-gate-v0.schema.json" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "schemas/json/ctxvault-memory-state-influence-boundary-report-v0.schema.json" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_integration_gate_contract.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_report_contract.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/run_memory_state_influence_boundary_consumer_wrapper_example.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_release_distinctness.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_social_draft_drift.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/render_memory_state_influence_boundary_owner_publish_packet.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_owner_publish_packet_contract.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_consumer_integration.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(
                any(
                    "scripts/check_memory_state_influence_boundary_byo_smoke.py" in command
                    for command in envelope["publish_commands"]
                )
            )
            self.assertTrue(any("release/memory-state-governability-overlay" in command for command in envelope["publish_commands"]))
            self.assertFalse(envelope["commit_created"])
            self.assertFalse(envelope["push_executed"])
            self.assertFalse(envelope["publication_executed"])
            self.assertFalse(envelope["outreach_performed"])

    def test_public_checkout_readiness_checker_materializes_without_external_publication(self) -> None:
        readiness_module = _load_module(PUBLIC_CHECKOUT_READINESS_SCRIPT, "check_memory_state_influence_boundary_public_checkout_readiness")
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            checkout = tmp_path / "checkout"
            checkout.mkdir()
            subprocess.run(["git", "init"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            result = readiness_module.check_memory_state_influence_boundary_public_checkout_readiness(
                ROOT,
                checkout=checkout,
                bundle_path=tmp_path / "bundle.json",
                bundle_md_path=tmp_path / "bundle.md",
                run_final_preflight=False,
                check_live=False,
            )

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_public_checkout_ready")
            self.assertEqual(result["publication_file_count"], result["materialized_copied_file_count"])
            self.assertEqual(result["materialization"]["observed_payload_status"], "pass_memory_state_influence_boundary_publication_bundle_materialized")
            self.assertEqual(result["final_preflight"]["status"], "skipped_by_caller")
            self.assertFalse(result["commit_created"])
            self.assertFalse(result["push_executed"])
            self.assertFalse(result["publication_executed"])
            self.assertFalse(result["outreach_performed"])

    def test_public_patch_publisher_dry_run_does_not_write_checkout(self) -> None:
        module = _load_module(PUBLISHER_SCRIPT, "publish_memory_state_public_patch")
        with TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            checkout.mkdir()
            subprocess.run(["git", "init"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            result = module.publish_memory_state_influence_boundary_public_patch(ROOT, checkout=checkout)

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_public_patch_publisher")
            self.assertEqual(result["mode"], "dry_run")
            self.assertEqual(result["source_final_preflight_status"], "pass_memory_state_influence_boundary_final_preflight")
            self.assertEqual(result["source_final_preflight_unittests"], "skipped_by_caller")
            self.assertFalse(result["local_checkout_write_executed"])
            self.assertFalse(result["commit_created"])
            self.assertFalse(result["push_executed"])
            self.assertFalse(result["publication_executed"])
            self.assertEqual(result["checkout_status_before"]["line_count"], 0)
            self.assertEqual(result["checkout_status_after"]["line_count"], 0)
            self.assertIn("--materialize", " ".join(result["warnings"]))

    def test_public_patch_publisher_materializes_without_commit_or_push(self) -> None:
        module = _load_module(PUBLISHER_SCRIPT, "publish_memory_state_public_patch_materialize")
        with TemporaryDirectory() as tmp:
            checkout = Path(tmp) / "checkout"
            checkout.mkdir()
            subprocess.run(["git", "init"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            result = module.publish_memory_state_influence_boundary_public_patch(ROOT, checkout=checkout, materialize=True)

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_public_patch_publisher")
            self.assertEqual(result["mode"], "materialize_only")
            self.assertTrue(result["local_checkout_write_executed"])
            self.assertEqual(result["materialization"]["status"], "pass_memory_state_influence_boundary_publication_bundle_materialized")
            self.assertGreaterEqual(result["materialization"]["copied_file_count"], 25)
            self.assertEqual(result["target_preflight_status"], "pass_memory_state_influence_boundary_target_preflight")
            self.assertEqual(result["target_preflight"]["observed_payload_status"], "pass_memory_state_influence_boundary_final_preflight")
            self.assertFalse(result["commit_created"])
            self.assertFalse(result["push_executed"])
            self.assertFalse(result["publication_executed"])
            self.assertTrue(result["checkout_status_after"]["line_count"])

    def test_public_patch_publisher_execute_path_pushes_to_local_bare_remote(self) -> None:
        module = _load_module(PUBLISHER_SCRIPT, "publish_memory_state_public_patch_execute")
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            remote = tmp_path / "remote.git"
            checkout = tmp_path / "checkout"
            subprocess.run(["git", "init", "--bare", str(remote)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            checkout.mkdir()
            subprocess.run(["git", "init", "-b", "main"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(["git", "config", "user.email", "ctxgov-test@example.invalid"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(["git", "config", "user.name", "CtxGov Test"], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=checkout, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            result = module.publish_memory_state_influence_boundary_public_patch(
                ROOT,
                checkout=checkout,
                materialize=True,
                execute_commit=True,
                execute_push=True,
            )

            self.assertEqual(result["status"], "pass_memory_state_influence_boundary_public_patch_publisher")
            self.assertEqual(result["mode"], "execute_push")
            self.assertTrue(result["local_checkout_write_executed"])
            self.assertTrue(result["commit_created"])
            self.assertTrue(result["push_executed"])
            self.assertTrue(result["publication_executed"])
            self.assertEqual(result["target_preflight_status"], "pass_memory_state_influence_boundary_target_preflight")
            remote_ref = subprocess.run(
                ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/main"],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            self.assertRegex(remote_ref.stdout.strip(), r"^[0-9a-f]{40}$")

    def test_public_checkout_readiness_checker_reports_clone_failure_without_traceback(self) -> None:
        readiness_module = _load_module(PUBLIC_CHECKOUT_READINESS_SCRIPT, "check_memory_state_influence_boundary_public_checkout_readiness_clone_failure")
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            result = readiness_module.check_memory_state_influence_boundary_public_checkout_readiness(
                ROOT,
                bundle_path=tmp_path / "bundle.json",
                bundle_md_path=tmp_path / "bundle.md",
                clone_url=str(tmp_path / "missing-public.git"),
                run_final_preflight=True,
                check_live=True,
            )

            self.assertEqual(result["status"], "fail_memory_state_influence_boundary_public_checkout_ready")
            issue_ids = {issue["issue_id"] for issue in result["issues"]}
            self.assertIn("public_repo_clone_failed", issue_ids)
            self.assertIn("public_checkout_missing_or_not_git", issue_ids)
            self.assertEqual(result["final_preflight"]["status"], "fail")
            self.assertFalse(result["commit_created"])
            self.assertFalse(result["push_executed"])
            self.assertFalse(result["publication_executed"])
            self.assertFalse(result["outreach_performed"])


if __name__ == "__main__":
    unittest.main()
