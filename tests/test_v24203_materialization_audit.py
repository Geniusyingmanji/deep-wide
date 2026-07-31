from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import build_decision_manifest  # noqa: E402
from deepwide_agent.v24203_materialization_audit import (
    build_materialization_manifest,
    classify_decision,
    reject_forbidden_metadata,
)  # noqa: E402


class V24203MaterializationAuditTests(unittest.TestCase):
    def test_all_36_decisions_are_classified_without_silent_fallback(self) -> None:
        result = build_materialization_manifest(build_decision_manifest())
        summary = result["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(
            summary["baseline_counts"],
            {"p12": 12, "schema76": 12, "schema77": 12},
        )
        self.assertEqual(summary["identity_handoff_decision_count"], 3)
        self.assertEqual(summary["blocked_nonempty_package_decision_count"], 33)
        self.assertFalse(summary["any_nonempty_package_materializable_now"])
        self.assertTrue(
            all(
                row["silent_component_drop_or_fallback_allowed"] is False
                for row in result["rows"].values()
            )
        )

    def test_empty_component_decisions_are_identity_handoffs_only(self) -> None:
        result = build_materialization_manifest(build_decision_manifest())
        rows = [row for row in result["rows"].values() if not row["eligible_components"]]
        self.assertEqual({row["baseline_name"] for row in rows}, {"p12", "schema76", "schema77"})
        self.assertTrue(all(row["identity_handoff_only"] for row in rows))
        self.assertTrue(all(row["frozen_package_bytes_available"] for row in rows))
        self.assertTrue(all(row["blockers"] == [] for row in rows))
        self.assertTrue(all(not row["benchmark_forward_or_full220_launch_allowed"] for row in rows))

    def test_nonempty_decisions_require_publication_and_joint_audit(self) -> None:
        result = build_materialization_manifest(build_decision_manifest())
        for row in result["rows"].values():
            if not row["eligible_components"]:
                continue
            self.assertFalse(row["frozen_package_bytes_available"])
            self.assertTrue(row["package_gate_required"])
            self.assertIn(
                "postdecision_joint_conflict_audit_and_regression_absent",
                row["blockers"],
            )

    def test_entropy_never_materializes_from_design_authority(self) -> None:
        result = build_materialization_manifest(build_decision_manifest())
        entropy = [
            row
            for row in result["rows"].values()
            if "entropy_credit_controller" in row["eligible_components"]
        ]
        self.assertEqual(len(entropy), 18)
        for row in entropy:
            self.assertIn("entropy_controller_implementation_authority_absent", row["blockers"])
            self.assertIn("entropy_controller_selected_baseline_publication_absent", row["blockers"])

    def test_markdown_scope_requires_markdown_and_namespace_flag(self) -> None:
        manifest = build_decision_manifest()
        key, row = next(iter(manifest.items()))
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = ["markdown_branch_scope_open_fallback"]
        tampered["markdown_branch_scope"] = True
        with self.assertRaisesRegex(RuntimeError, "lacks Markdown"):
            classify_decision(key, tampered)
        tampered = copy.deepcopy(row)
        tampered["markdown_branch_scope"] = not row["markdown_branch_scope"]
        with self.assertRaisesRegex(RuntimeError, "branch-scope flag"):
            classify_decision(key, tampered)

    def test_unknown_or_reordered_components_fail_closed(self) -> None:
        manifest = build_decision_manifest()
        key, row = next(
            (key, row)
            for key, row in manifest.items()
            if len(row["eligible_components"]) >= 2
        )
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = list(reversed(tampered["eligible_components"]))
        with self.assertRaisesRegex(RuntimeError, "order or uniqueness"):
            classify_decision(key, tampered)
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = ["unknown_component"]
        with self.assertRaisesRegex(RuntimeError, "order or uniqueness|unknown"):
            classify_decision(key, tampered)

    def test_privileged_metadata_is_rejected_recursively(self) -> None:
        for value in (
            {"question_type": "x"},
            {"nested": {"gold": "x"}},
            {"nested": [{"reward": 1}]},
            {"task_id": "x"},
        ):
            with self.assertRaisesRegex(RuntimeError, "privileged metadata"):
                reject_forbidden_metadata(value)


if __name__ == "__main__":
    unittest.main()
