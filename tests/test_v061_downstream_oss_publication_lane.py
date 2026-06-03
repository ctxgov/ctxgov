from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ctxgov import cli


README = ROOT / "README.md"
PAGES = ROOT / "docs" / "index.html"
TEMPLATE_DIR = ROOT / "templates" / "case-study-preview"
COOKBOOK = ROOT / "release" / "v0.6.1" / "public-evidence" / "safe-rewrite-cookbook.md"
FILLED_EXAMPLE = ROOT / "examples" / "case-study-preview" / "mem0-decision-preview.example.md"


class V061DownstreamOssPublicationLaneTests(unittest.TestCase):
    def run_cli(self, *args: str) -> tuple[int, dict]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = cli.main(list(args))
        return code, json.loads(stdout.getvalue())

    def test_readme_stays_v062_focused_while_v061_public_pages_remain_available(self) -> None:
        readme = README.read_text(encoding="utf-8")
        pages = PAGES.read_text(encoding="utf-8")

        for required in [
            "Agent Context Health Evaluation for AI Workflows.",
            "v0.6.4",
            "Context Health Doctor",
            "Claim Boundaries",
            "Memory X-Ray L1",
            "Task Shard",
        ]:
            self.assertIn(required, readme)
        self.assertNotIn("oss-case-study-preview", readme)
        self.assertNotIn("--allow-network", readme)
        for required in [
            "Agent Context Health Evaluation for AI Workflows",
            "CtxGov v0.6.7 release",
            "Companion v0.6 results report",
            "No provider/model call",
            "No target repository write",
        ]:
            self.assertIn(required, pages)

    def test_templates_cookbook_and_filled_example_expose_blocked_claims_and_rollback(self) -> None:
        source_template = json.loads((TEMPLATE_DIR / "source-fact-receipt.template.json").read_text(encoding="utf-8"))
        claim_template = json.loads((TEMPLATE_DIR / "claim-lint.template.json").read_text(encoding="utf-8"))
        cookbook = COOKBOOK.read_text(encoding="utf-8")
        filled = FILLED_EXAMPLE.read_text(encoding="utf-8")

        for layer in ["claim", "context", "memory", "action"]:
            self.assertIn(layer, source_template["authority_layers"])
            self.assertIn(layer, claim_template["authority_layers"])
        for field in [
            "ref",
            "state",
            "reason",
            "authority_layer_blocked",
            "safe_rewrite_or_next_check",
            "rollback_ref",
        ]:
            self.assertIn(field, source_template["evidence_object_schema"]["required_fields"])
        for blocked_claim in ["secure", "fast", "compatible", "endorse", "runtime", "action authority"]:
            self.assertIn(blocked_claim, cookbook)
        for required in [
            "mem0 Decision Preview Example",
            "Decision Preview",
            "Evidence Objects",
            "Safe Rewrites",
            "No target/action state exists",
        ]:
            self.assertIn(required, filled)

    def test_oss_case_study_preview_cli_is_local_first_and_blocks_remote_fetch_by_default(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "README.md"
            source.write_text("# Example OSS\n\nPublic docs for a test project.\n", encoding="utf-8")

            code, payload = self.run_cli(
                "oss-case-study-preview",
                "--root",
                str(root),
                "--target-name",
                "Example OSS",
                "--repo-url",
                "https://github.com/example/example-oss",
                "--pinned-ref",
                "abc123",
                "--source-path",
                str(source),
                "--output-dir",
                "preview",
                "--checked-at-utc",
                "2026-05-16T12:30:00Z",
            )

            self.assertEqual(code, 0)
            self.assertEqual(payload["schema_id"], "ctxvault.oss-case-study-decision-preview/v1")
            self.assertEqual(payload["status"], "preview_ready")
            self.assertEqual(
                {row["decision"] for row in payload["decision_table"]},
                {"public_claim", "context_packet", "memory", "action"},
            )
            for blocked in [
                "target_repo_cloned",
                "target_file_written",
                "runtime_or_adapter_executed",
                "mcp_server_started",
                "provider_or_model_call_performed",
                "memory_promotion_performed",
                "github_public_repo_write_performed",
                "public_publication_performed",
            ]:
                self.assertFalse(payload["side_effect_boundary"][blocked], blocked)

            blocked_code, blocked_payload = self.run_cli(
                "oss-case-study-preview",
                "--root",
                str(root),
                "--target-name",
                "Remote Only",
                "--repo-url",
                "https://github.com/example/remote-only",
                "--pinned-ref",
                "def456",
                "--output-dir",
                "blocked-preview",
            )
            self.assertEqual(blocked_code, 1)
            self.assertEqual(blocked_payload["status"], "blocked_network_not_approved")
            self.assertFalse(blocked_payload["side_effect_boundary"]["target_fetch_or_clone_performed"])
            self.assertFalse(blocked_payload["side_effect_boundary"]["target_repo_cloned"])


if __name__ == "__main__":
    unittest.main()
