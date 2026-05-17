from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


PUBLIC_COPY_PATHS = [
    ROOT / "README.md",
    ROOT / "ROADMAP.md",
    ROOT / "release" / "v0.6.2" / "RELEASE_NOTES.md",
    ROOT / "release" / "v0.6.2" / "github-release.md",
    ROOT / "release" / "v0.6.2" / "publication" / "v062-publication-receipt-2026-05-16.json",
    ROOT / "release" / "v0.6.2" / "publication" / "v062-public-surface-cleanup-receipt-2026-05-16.json",
    ROOT / "docs" / "v0.3-compiled-context" / "experimental-fixtures" / "compiled-workstream-state.json",
    ROOT / "docs" / "v0.4.1-projection-governance-kernel.md",
    ROOT / "docs" / "v0.4.1-execution-approval-matrix.md",
    ROOT / "fixtures" / "v0.4.1-projection-governance-kernel" / "example-projection.json",
    ROOT / "fixtures" / "v0.4.1-projection-governance-kernel" / "approval-matrix.json",
]

PRIVATE_PLANNING_MARKERS = [
    "docs/active.md",
    "v0.6.2-downstream-oss-evidence-integration-plan",
    "v0.6.1-closeout-v0.6.2-cold-start",
    "post-m1-capability-roadmap-and-p05-research",
    "ctxvault-local-docs-consumption-guide",
    "private-roadmap",
    "src_private_roadmap_note",
    "dirty worktree",
    "/Users/chris",
]

ROADMAP_OR_PROMO_MARKERS = [
    "being prepared",
    "next release",
    "public beta ready",
    "benchmark or leaderboard results",
]


class V062PublicSurfaceCleanupTests(unittest.TestCase):
    def test_public_copy_has_no_private_planning_markers(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_COPY_PATHS)

        for marker in PRIVATE_PLANNING_MARKERS:
            self.assertNotIn(marker, combined)

    def test_readme_stays_focused_on_current_v062_release(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        normalized = " ".join(readme.split())

        self.assertIn("v0.6.2 public release artifact", readme)
        self.assertIn("Context Health Doctor", readme)
        self.assertIn("does not modify scanned source files", normalized)
        self.assertIn("package registry publication", readme)
        self.assertNotIn("Proof Scene", readme)
        self.assertNotIn("Compatibility Notes", readme)
        self.assertNotIn("Reviewer Path", readme)
        self.assertNotIn("Additional v0.6.0", readme)
        self.assertNotIn("downstream OSS case-study adoption", readme)

    def test_release_copy_matches_actual_write_boundary(self) -> None:
        release_copy = (ROOT / "release" / "v0.6.2" / "github-release.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "release" / "v0.6.2" / "RELEASE_NOTES.md").read_text(encoding="utf-8")
        normalized_release_copy = " ".join(release_copy.split())
        normalized_release_notes = " ".join(release_notes.split())

        self.assertIn("chosen output and rollback paths", normalized_release_copy)
        self.assertIn("does not modify scanned source files", normalized_release_copy)
        self.assertIn("chosen output and rollback paths", normalized_release_notes)
        self.assertIn("scanned source-file modification", normalized_release_notes)
        self.assertNotIn("does not write target repo files", release_copy)
        self.assertNotIn("target repository writes", release_notes)

    def test_roadmap_file_is_boundary_document_not_future_plan(self) -> None:
        boundary = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")

        self.assertIn("does not publish future plans", boundary)
        self.assertIn("current shipped artifacts", boundary)
        for marker in ROADMAP_OR_PROMO_MARKERS:
            self.assertNotIn(marker, boundary)

    def test_publication_receipt_keeps_package_and_outreach_blocked(self) -> None:
        receipt = json.loads(
            (
                ROOT
                / "release"
                / "v0.6.2"
                / "publication"
                / "v062-publication-receipt-2026-05-16.json"
            ).read_text(encoding="utf-8")
        )

        self.assertFalse(receipt["owner_approval"]["package_publish_approved_for_this_lane"])
        self.assertFalse(receipt["owner_approval"]["external_outreach_approved_for_this_lane"])
        self.assertFalse(receipt["side_effect_boundary"]["package_published"])
        self.assertFalse(receipt["side_effect_boundary"]["maintainer_outreach_performed"])

        cleanup_receipt = json.loads(
            (
                ROOT
                / "release"
                / "v0.6.2"
                / "publication"
                / "v062-public-surface-cleanup-receipt-2026-05-16.json"
            ).read_text(encoding="utf-8")
        )
        self.assertFalse(cleanup_receipt["side_effect_boundary"]["package_published"])
        self.assertFalse(cleanup_receipt["side_effect_boundary"]["external_outreach_performed"])


if __name__ == "__main__":
    unittest.main()
