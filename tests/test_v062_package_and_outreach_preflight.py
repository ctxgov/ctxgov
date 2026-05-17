from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
PACKAGE_PREFLIGHT = ROOT / "release" / "v0.6.2" / "package-registry-preflight.md"
OUTREACH_PREFLIGHT = ROOT / "release" / "v0.6.2" / "external-outreach-preflight.md"
APPROVAL_MATRIX = ROOT / "release" / "v0.6.2" / "package-and-outreach-approval-matrix.json"
PREFLIGHT_RECEIPT = ROOT / "release" / "v0.6.2" / "package-outreach-preflight-receipt-2026-05-16.json"


FORBIDDEN_PUBLIC_CLAIMS = [
    "security guarantee",
    "benchmark result",
    "performance improvement",
    "universal compatibility",
    "stable protocol",
    "automatic remediation",
    "maintainer endorsement",
]


class V062PackageAndOutreachPreflightTests(unittest.TestCase):
    def test_pyproject_has_conservative_package_metadata_without_compatibility_overclaim(self) -> None:
        pyproject = PYPROJECT.read_text(encoding="utf-8")

        self.assertIn('version = "0.6.2.post1"', pyproject)
        self.assertIn('ctxvault = "ctxvault.cli:main"', pyproject)
        self.assertIn('Development Status :: 3 - Alpha', pyproject)
        self.assertIn('License :: OSI Approved :: Apache Software License', pyproject)
        self.assertIn("[project.urls]", pyproject)
        self.assertIn('Repository = "https://github.com/ctxvault/ctxvault"', pyproject)
        self.assertNotRegex(pyproject, r"Programming Language :: Python :: 3\.\d+")
        self.assertNotIn("Production/Stable", pyproject)

    def test_package_preflight_blocks_upload_and_recommends_testpypi_first(self) -> None:
        preflight = PACKAGE_PREFLIGHT.read_text(encoding="utf-8")
        normalized = " ".join(preflight.split())

        self.assertIn("No package registry publication has been performed.", normalized)
        self.assertIn("Option A: TestPyPI First, Then PyPI", preflight)
        self.assertIn("Recommendation: choose this for the first package publication.", preflight)
        self.assertIn("yank plus patch release, not overwrite", preflight)
        self.assertIn("--no-deps --no-build-isolation", preflight)
        self.assertNotIn("python3 -m twine " + "upload", preflight)

    def test_outreach_preflight_keeps_exact_copy_inside_claim_boundary(self) -> None:
        outreach = OUTREACH_PREFLIGHT.read_text(encoding="utf-8")
        normalized_original = " ".join(outreach.split())
        normalized = " ".join(outreach.split()).lower()

        self.assertIn("No external outreach has been performed.", normalized_original)
        self.assertIn("Option B: Package-First Announcement", outreach)
        self.assertIn("Recommendation: best next public outreach sequence after TestPyPI/PyPI", outreach)
        self.assertIn("modify scanned source files", normalized)
        self.assertIn("call models/providers", normalized)
        self.assertIn("fetch the network", normalized)
        for forbidden in FORBIDDEN_PUBLIC_CLAIMS:
            self.assertNotIn(f"{forbidden} claimed", normalized)

    def test_approval_matrix_splits_no_approval_from_owner_approval(self) -> None:
        matrix = json.loads(APPROVAL_MATRIX.read_text(encoding="utf-8"))

        self.assertEqual(matrix["schema_id"], "ctxvault.v062-package-outreach-approval-matrix/v1")
        self.assertEqual(matrix["status"], "owner_options_selected_local_preparation_only")
        self.assertEqual(matrix["owner_selected_options"]["public-preflight-push"]["selected_option"], "B")
        self.assertEqual(matrix["owner_selected_options"]["package-registry-target"]["selected_option"], "A")
        self.assertEqual(matrix["owner_selected_options"]["package-publishing-mechanism"]["selected_option"], "A")
        self.assertEqual(matrix["owner_selected_options"]["external-outreach-channel"]["selected_option"], "B")
        self.assertEqual(matrix["owner_selected_options"]["maintainer-outreach"]["selected_option"], "A")
        self.assertGreaterEqual(len(matrix["no_approval_executed"]), 4)

        required_ids = {item["id"]: item for item in matrix["approval_required"]}
        self.assertEqual(required_ids["package-registry-target"]["recommended_option"], "A")
        self.assertEqual(required_ids["package-publishing-mechanism"]["recommended_option"], "A")
        self.assertEqual(required_ids["external-outreach-channel"]["recommended_option"], "B")

        blocked = set(matrix["explicitly_blocked_until_approved"])
        for required in [
            "pypi_upload",
            "testpypi_upload",
            "twine_upload",
            "social_post",
            "maintainer_outreach",
            "package_install_claim_in_public_copy",
        ]:
            self.assertIn(required, blocked)

    def test_preflight_receipt_records_local_smoke_without_external_side_effects(self) -> None:
        receipt = json.loads(PREFLIGHT_RECEIPT.read_text(encoding="utf-8"))

        self.assertEqual(receipt["schema_id"], "ctxvault.v062-package-outreach-preflight-receipt/v1")
        self.assertEqual(receipt["status"], "local_package_and_outreach_preflight_completed_no_external_publication")
        self.assertEqual(receipt["selected_package_version"], "0.6.2.post1")
        self.assertEqual(receipt["package_smoke"]["wheel_file"], "ctxvault-0.6.2.post1-py3-none-any.whl")
        self.assertRegex(receipt["package_smoke"]["wheel_sha256"], r"^[0-9a-f]{64}$")
        self.assertGreater(receipt["package_smoke"]["wheel_size_bytes"], 0)
        self.assertFalse(receipt["package_smoke"]["side_effects"]["package_uploaded"])
        self.assertFalse(receipt["package_smoke"]["side_effects"]["registry_state_changed"])
        self.assertFalse(receipt["package_smoke"]["side_effects"]["external_outreach_performed"])
        self.assertFalse(receipt["tooling_state"]["python_build_module_available"])
        self.assertFalse(receipt["tooling_state"]["twine_module_available"])
        self.assertIn("TestPyPI upload", receipt["explicitly_not_done"])

    def test_preflight_docs_do_not_expose_private_paths_or_future_roadmap(self) -> None:
        combined = "\n".join(
            [
                PACKAGE_PREFLIGHT.read_text(encoding="utf-8"),
                OUTREACH_PREFLIGHT.read_text(encoding="utf-8"),
                APPROVAL_MATRIX.read_text(encoding="utf-8"),
                PREFLIGHT_RECEIPT.read_text(encoding="utf-8"),
            ]
        )

        for pattern in [
            r"/Users/[A-Za-z0-9._-]+",
            r"private[-_]roadmap",
            r"dirty[- ]worktree",
            r"post-m1-capability",
            r"being\s+prepared",
            r"next\s+release",
            r"public\s+beta\s+ready",
        ]:
            self.assertIsNone(re.search(pattern, combined))


if __name__ == "__main__":
    unittest.main()
