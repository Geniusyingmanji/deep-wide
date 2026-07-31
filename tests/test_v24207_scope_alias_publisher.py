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
from deepwide_agent.v24207_scope_alias_publisher import (  # noqa: E402
    build_scope_publication_manifest,
    build_scope_publication_order,
)


class V24207ScopeAliasPublisherTests(unittest.TestCase):
    def test_all_36_orders_have_exact_dispositions(self) -> None:
        summary = build_scope_publication_manifest()["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["scope_selected_count"], 12)
        self.assertEqual(summary["no_scope_noop_count"], 24)
        self.assertEqual(summary["p12_historical_binding_count"], 4)
        self.assertEqual(summary["mainline_zero_byte_alias_count"], 8)
        self.assertEqual(summary["historical_patch_reapplication_count"], 0)
        self.assertEqual(summary["candidate_bytes_modified_count"], 0)
        self.assertEqual(summary["joint_package_materialized_count"], 0)
        self.assertEqual(summary["benchmark_launch_authorized_count"], 0)

    def test_scope_requires_markdown_and_owns_nothing_else(self) -> None:
        for row in build_scope_publication_manifest()["rows"].values():
            if row["branch_scope_component_selected"]:
                self.assertIn("markdown_rank_slot", row["eligible_components"])
                self.assertTrue(row["markdown_parent_component_required"])
            self.assertFalse(row["historical_scope_patch_reapplied"])
            self.assertFalse(row["candidate_bytes_modified_or_materialized"])
            self.assertFalse(row["search_yield_published_or_implemented"])
            self.assertFalse(row["entropy_controller_published_or_implemented"])
            self.assertFalse(row["joint_package_built_or_materialized"])
            self.assertFalse(row["benchmark_forward_or_full220_launch_allowed"])

    def test_mainline_uses_alias_and_p12_uses_schema70(self) -> None:
        rows = build_scope_publication_manifest()["rows"].values()
        selected = [row for row in rows if row["branch_scope_component_selected"]]
        for row in selected:
            if row["baseline_name"] == "p12":
                self.assertEqual(row["publication_mode"], "bind_historical_schema70_bytes")
                self.assertEqual(row["target_state_schema_version"], 70)
            else:
                self.assertEqual(
                    row["publication_mode"],
                    "bind_zero_byte_mainline_scope_namespace_alias",
                )
                self.assertIn(row["target_state_schema_version"], {78, 79})

    def test_tampered_work_order_fails_closed(self) -> None:
        row = next(iter(build_work_order_manifest()["rows"].values()))
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = ["markdown_branch_scope_open_fallback"]
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            build_scope_publication_order(tampered)


if __name__ == "__main__":
    unittest.main()
