from __future__ import annotations

import unittest

from deepwide_agent.v24204_postdecision_work_order import (
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import ENTROPY
from deepwide_agent.v24214_joint_package import build_joint_package_order
from deepwide_agent.v24215_joint_package_recovery import (
    ACTUAL_ENTROPY_PATH,
    build_recovery_order,
)
from scripts.publish_v24215_joint_package_recovery import (
    FAILED_AUDIT_SHA256,
)


class PublishV24215JointPackageRecoveryTests(unittest.TestCase):
    def test_recovery_order_points_to_actual_entropy_publication(self) -> None:
        work_order = next(
            row
            for row in build_work_order_manifest()["rows"].values()
            if ENTROPY in row["eligible_components"]
        )
        base = build_joint_package_order(work_order)
        recovery = build_recovery_order(work_order)
        self.assertNotEqual(
            recovery["joint_order_payload_sha256"],
            base["joint_order_payload_sha256"],
        )
        self.assertEqual(recovery["deepest_publication_path"], ACTUAL_ENTROPY_PATH)
        self.assertEqual(
            next(
                stage
                for stage in recovery["parent_chain"]
                if stage["stage"] == "entropy"
            )["publication_path"],
            ACTUAL_ENTROPY_PATH,
        )

    def test_recovery_parent_sha_is_pinned(self) -> None:
        self.assertEqual(
            FAILED_AUDIT_SHA256,
            "f216e96eaeba94bd04d4ca082903e5825e0c0624608846c199f9888679c8974e",
        )


if __name__ == "__main__":
    unittest.main()
