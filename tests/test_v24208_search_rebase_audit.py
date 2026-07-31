from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24204_postdecision_work_order import (  # noqa: E402
    build_work_order_manifest,
)
from deepwide_agent.v24208_search_rebase_audit import (  # noqa: E402
    build_search_rebase_manifest,
    classify_search_rebase_order,
)


class V24208SearchRebaseAuditTests(unittest.TestCase):
    def test_all_36_orders_have_expected_dispositions(self) -> None:
        summary = build_search_rebase_manifest()["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["search_selected_count"], 18)
        self.assertEqual(summary["search_absent_noop_count"], 18)
        self.assertEqual(summary["baseline_only_parent_count"], 6)
        self.assertEqual(summary["markdown_parent_count"], 12)
        self.assertEqual(summary["search_candidate_materialized_count"], 0)
        self.assertEqual(summary["benchmark_launch_authorized_count"], 0)

    def test_search_orders_cover_each_baseline_and_parent_variant(self) -> None:
        rows = [
            row
            for row in build_search_rebase_manifest()["rows"].values()
            if row["search_component_selected"]
        ]
        self.assertEqual({row["baseline_name"] for row in rows}, {"p12", "schema76", "schema77"})
        self.assertEqual(
            {row["parent_candidate_variant"] for row in rows},
            {"selected_baseline", "selected_markdown_candidate"},
        )
        self.assertTrue(
            all(row["historical_v24180_quality_gate_terminal_required_for_publication"] for row in rows)
        )

    def test_audit_never_builds_or_authorizes(self) -> None:
        for row in build_search_rebase_manifest()["rows"].values():
            self.assertFalse(row["search_candidate_bytes_built_or_materialized"])
            self.assertFalse(row["search_component_publication_available"])
            self.assertFalse(row["joint_package_built_or_materialized"])
            self.assertFalse(row["benchmark_forward_or_full220_launch_allowed"])

    def test_tampered_or_unregistered_order_fails_closed(self) -> None:
        digest, row = next(iter(build_work_order_manifest()["rows"].items()))
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = []
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            classify_search_rebase_order(tampered)
        unknown = copy.deepcopy(row)
        unknown["decision_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "not registered"):
            classify_search_rebase_order(unknown)


if __name__ == "__main__":
    unittest.main()
