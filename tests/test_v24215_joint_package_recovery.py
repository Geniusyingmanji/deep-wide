from __future__ import annotations

import copy
import unittest

from deepwide_agent.v24204_postdecision_work_order import (
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import ENTROPY
from deepwide_agent.v24214_joint_package import build_joint_package_manifest
from deepwide_agent.v24215_joint_package_recovery import (
    ACTUAL_ENTROPY_PATH,
    FROZEN_WRONG_ENTROPY_PATH,
    build_recovery_manifest,
    build_recovery_order,
    validate_recovery_order,
)


class V24215JointPackageRecoveryTests(unittest.TestCase):
    def test_exactly_eighteen_entropy_paths_are_corrected(self) -> None:
        base = build_joint_package_manifest()["rows"]
        recovery = build_recovery_manifest()
        rows = recovery["rows"]
        changed = [decision for decision in rows if rows[decision] != base[decision]]
        self.assertEqual(len(changed), 18)
        self.assertEqual(recovery["summary"]["entropy_path_corrected_count"], 18)
        self.assertEqual(
            recovery["summary"]["byte_identical_nonentropy_order_count"], 18
        )
        for decision in changed:
            row = rows[decision]
            self.assertIn(ENTROPY, row["eligible_components"])
            self.assertEqual(row["deepest_publication_path"], ACTUAL_ENTROPY_PATH)
            entropy = next(
                stage for stage in row["parent_chain"] if stage["stage"] == "entropy"
            )
            self.assertEqual(entropy["publication_path"], ACTUAL_ENTROPY_PATH)
            self.assertNotEqual(
                entropy["publication_path"], FROZEN_WRONG_ENTROPY_PATH
            )

    def test_nonentropy_orders_are_byte_identical(self) -> None:
        base = build_joint_package_manifest()["rows"]
        rows = build_recovery_manifest()["rows"]
        unchanged = [
            decision
            for decision, row in rows.items()
            if ENTROPY not in row["eligible_components"]
        ]
        self.assertEqual(len(unchanged), 18)
        for decision in unchanged:
            self.assertEqual(rows[decision], base[decision])

    def test_owner_schema_component_and_authority_fields_do_not_change(self) -> None:
        base = build_joint_package_manifest()["rows"]
        rows = build_recovery_manifest()["rows"]
        invariant = (
            "baseline_name",
            "eligible_components",
            "parent_dependency_order_components",
            "deepest_semantic_owner",
            "deepest_byte_owner",
            "final_state_schema_version",
            "identity_handoff_only",
            "joint_revalidation_required",
            "candidate_directory_overlay_allowed",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "benchmark_forward_or_full220_launch_allowed",
        )
        for decision in rows:
            for field in invariant:
                self.assertEqual(rows[decision][field], base[decision][field])

    def test_tampered_recovery_order_fails_closed(self) -> None:
        work_order = next(
            row
            for row in build_work_order_manifest()["rows"].values()
            if ENTROPY in row["eligible_components"]
        )
        value = build_recovery_order(work_order)
        broken = copy.deepcopy(value)
        broken["deepest_publication_path"] = FROZEN_WRONG_ENTROPY_PATH
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            validate_recovery_order(broken)


if __name__ == "__main__":
    unittest.main()
