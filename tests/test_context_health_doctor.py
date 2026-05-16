from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxvault import cli
from ctxvault.context_health import build_context_health_report, write_context_health_report
from scripts.validate_fixtures import validate


SCHEMA = ROOT / "schemas" / "json" / "ctxvault-context-health-report-v0.schema.json"
EXAMPLE_REPORT = ROOT / "fixtures" / "v0.6.2-context-health-doctor" / "example-context-health-report.json"
SAMPLE_REPO = ROOT / "fixtures" / "v0.6.2-context-health-doctor" / "sample-repo"
CLEAN_REPO = ROOT / "fixtures" / "v0.6.2-context-health-doctor" / "clean-repo"


class ContextHealthDoctorTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = cli.main(list(args))
        return result, stdout.getvalue()

    def copy_sample_repo(self, tmpdir: str) -> Path:
        target = Path(tmpdir) / "sample-repo"
        shutil.copytree(SAMPLE_REPO, target, ignore=shutil.ignore_patterns(".ctxvault"))
        return target

    def test_context_health_report_fixture_matches_schema(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        fixture = json.loads(EXAMPLE_REPORT.read_text(encoding="utf-8"))

        validate(fixture, schema, schema, EXAMPLE_REPORT.name)

    def test_build_report_finds_required_health_risks(self) -> None:
        report = build_context_health_report(SAMPLE_REPO)
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

        validate(report, schema, schema, "runtime-context-health-report")
        self.assertEqual(report["schema_id"], "ctxvault.context-health-report/v0")
        self.assertEqual(report["mode"], "read_only_local_scan")

        finding_types = {finding["finding_type"] for finding in report["findings"]}
        for expected in [
            "stale_context",
            "conflicting_instruction",
            "duplicated_rule",
            "unsupported_claim",
            "missing_raw_ref",
            "over_compressed_summary",
            "memory_without_lifecycle_or_rollback",
            "action_or_publication_without_evidence",
            "terminal_failure_hidden",
        ]:
            self.assertIn(expected, finding_types)

        self.assertEqual(report["decision_table"]["claim"]["status"], "blocked")
        self.assertEqual(report["decision_table"]["context"]["status"], "blocked")
        self.assertEqual(report["decision_table"]["memory"]["status"], "blocked")
        self.assertEqual(report["decision_table"]["action"]["status"], "blocked")
        self.assertFalse(any(report["side_effects"].values()))
        self.assertFalse(report["output_policy"]["raw_source_copied"])
        self.assertFalse(report["output_policy"]["target_files_written"])

        for finding in report["findings"]:
            self.assertTrue(finding["finding_id"])
            self.assertTrue(finding["source_ref"].startswith("file://"))
            self.assertTrue(finding["authority_layer_affected"])
            self.assertTrue(finding["safe_rewrite_or_next_check"])
            self.assertTrue(finding["rollback_ref"].startswith("delete://"))

    def test_clean_repo_fixture_remains_allowed(self) -> None:
        report = build_context_health_report(CLEAN_REPO)

        self.assertEqual(report["summary"]["finding_count"], 0)
        self.assertEqual(report["decision_table"]["claim"]["status"], "allowed")
        self.assertEqual(report["decision_table"]["context"]["status"], "allowed")
        self.assertEqual(report["decision_table"]["memory"]["status"], "allowed")
        self.assertEqual(report["decision_table"]["action"]["status"], "allowed")

    def test_write_report_outputs_json_markdown_receipt_index_and_backup_manifest(self) -> None:
        with TemporaryDirectory() as tmpdir:
            sample = self.copy_sample_repo(tmpdir)
            before = {
                path.relative_to(sample): path.read_text(encoding="utf-8")
                for path in sample.rglob("*")
                if path.is_file() and ".ctxvault" not in path.relative_to(sample).parts
            }

            result = write_context_health_report(sample, output_root=Path(".ctxvault") / "health")

            json_report = Path(result["json_report_path"])
            markdown_report = Path(result["markdown_report_path"])
            run_receipt = Path(result["run_receipt_path"])
            backup_manifest_path = Path(result["backup_manifest_path"])
            index_path = Path(result["index_path"])

            for path in [json_report, markdown_report, run_receipt, backup_manifest_path, index_path]:
                self.assertTrue(path.exists(), str(path))

            report = json.loads(json_report.read_text(encoding="utf-8"))
            markdown = markdown_report.read_text(encoding="utf-8")
            receipt = json.loads(run_receipt.read_text(encoding="utf-8"))
            backup_manifest = json.loads(backup_manifest_path.read_text(encoding="utf-8"))
            evidence_manifest = json.loads(Path(result["evidence_manifest_path"]).read_text(encoding="utf-8"))

            self.assertIn("## Decision Table", markdown)
            for finding in report["findings"]:
                self.assertIn(finding["finding_id"], markdown)
            self.assertEqual(receipt["schema_id"], "ctxvault.context-health-run-receipt/v0")
            self.assertFalse(receipt["raw_source_copied"])
            self.assertFalse(receipt["target_files_written"])
            self.assertEqual(receipt["receipt_copy_path"], str(Path(result["output_root"]) / "receipts" / f"{result['report_id']}-run-receipt.json"))
            self.assertIn(str(json_report), receipt["rollback"]["delete_paths"])
            self.assertIn(str(json_report.parent), result["rollback"]["delete_paths"])
            self.assertIn(str(Path(result["output_root"]) / "reports" / "markdown" / f"{result['report_id']}.md"), result["rollback"]["delete_paths"])
            self.assertEqual(result["rollback"]["index_path"], str(index_path))
            self.assertEqual(backup_manifest["schema_id"], "ctxvault.context-health-backup-manifest/v0")
            self.assertFalse(backup_manifest["raw_source_copied"])
            self.assertFalse(any(backup_manifest["side_effects"].values()))
            self.assertTrue(backup_manifest["included_artifacts"])
            self.assertEqual(backup_manifest["excluded_material"][0]["class"], "raw_scanned_source")
            self.assertFalse(evidence_manifest["raw_source_copied"])
            self.assertTrue(evidence_manifest["source_digest_refs"])
            self.assertTrue(all("text" not in entry for entry in evidence_manifest["source_digest_refs"]))

            after = {
                path.relative_to(sample): path.read_text(encoding="utf-8")
                for path in sample.rglob("*")
                if path.is_file() and ".ctxvault" not in path.relative_to(sample).parts
            }
            self.assertEqual(before, after)

    def test_doctor_cli_path_uses_context_health_doctor_without_changing_legacy_doctor(self) -> None:
        with TemporaryDirectory() as tmpdir:
            sample = self.copy_sample_repo(tmpdir)

            code, stdout = self.run_cli("doctor", "--path", str(sample), "--output", ".ctxvault/health")

            self.assertEqual(code, 0)
            result = json.loads(stdout)
            self.assertEqual(result["schema_id"], "ctxvault.context-health-write-summary/v0")
            self.assertNotIn("report", result)
            self.assertEqual(result["mode"], "read_only_local_scan")
            self.assertTrue(Path(result["json_report_path"]).exists())
            self.assertTrue(Path(result["backup_manifest_path"]).exists())
            self.assertFalse(result["raw_source_copied"])
            self.assertFalse(result["target_files_written"])

            code, stdout = self.run_cli("doctor", "--path", str(sample), "--output", ".ctxvault/health", "--include-report")

            self.assertEqual(code, 0)
            full_result = json.loads(stdout)
            self.assertEqual(full_result["schema_id"], "ctxvault.context-health-write-result/v0")
            self.assertEqual(full_result["report"]["schema_id"], "ctxvault.context-health-report/v0")

        with TemporaryDirectory() as tmpdir:
            code, stdout = self.run_cli("doctor", "--root", tmpdir)

            self.assertEqual(code, 0)
            legacy = json.loads(stdout)
            self.assertEqual(legacy["schema_id"], "ctxvault.doctor-report/v1")
            self.assertEqual(legacy["mode"], "read_only")

    def test_missing_scan_path_fails_closed_without_creating_output_tree(self) -> None:
        with TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing-repo"

            with self.assertRaises(FileNotFoundError):
                write_context_health_report(missing)

            self.assertFalse(missing.exists())

    def test_doctor_cli_missing_scan_path_returns_error_without_creating_output_tree(self) -> None:
        with TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing-repo"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli.main(["doctor", "--path", str(missing), "--output", ".ctxvault/health"])

            self.assertEqual(code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("Context Health Doctor scan path does not exist", stderr.getvalue())
            self.assertFalse(missing.exists())

    def test_scan_boundaries_account_for_omitted_files_and_skip_ctxvault_outputs(self) -> None:
        with TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir) / "repo"
            repo.mkdir()
            (repo / "README.md").write_text("Current version is v0.6.2.\n", encoding="utf-8")
            (repo / "large.md").write_text("x" * 40, encoding="utf-8")
            (repo / "binary.md").write_bytes(b"\xff\xfe\x00")
            ctxvault_report = repo / ".ctxvault" / "health" / "runs" / "old"
            ctxvault_report.mkdir(parents=True)
            (ctxvault_report / "context-health-report.md").write_text(
                "Stable MGP and security complete claims from old generated output.",
                encoding="utf-8",
            )

            report = build_context_health_report(repo, max_file_bytes=12)

            self.assertIn("file://large.md", report["evidence"]["omitted_refs"])
            self.assertIn("file://binary.md", report["evidence"]["omitted_refs"])
            self.assertNotIn("context-health-report.md", json.dumps(report, sort_keys=True))

    def test_file_scan_uses_parent_local_health_storage_by_default(self) -> None:
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "AGENTS.md"
            path.write_text("No network fetch is allowed.\nNetwork is approved for this task.\n", encoding="utf-8")

            result = write_context_health_report(path)

            self.assertTrue(Path(result["json_report_path"]).exists())
            self.assertEqual(Path(result["output_root"]).resolve(), (Path(tmpdir) / ".ctxvault" / "health").resolve())
            self.assertTrue(
                Path(result["backup_manifest_path"]).resolve().is_relative_to((Path(tmpdir) / ".ctxvault" / "backups").resolve())
            )


if __name__ == "__main__":
    unittest.main()
