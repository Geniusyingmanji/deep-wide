from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24204_postdecision_work_order import build_work_order_manifest
from deepwide_agent.v24210_search_publisher import (
    build_search_publication_manifest,
    build_search_publication_order,
)


class V24210SearchPublisherTests(unittest.TestCase):
    def test_all_36_orders_cover_nine_semantic_and_seven_byte_parents(self) -> None:
        summary = build_search_publication_manifest()["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["search_selected_count"], 18)
        self.assertEqual(summary["search_absent_noop_count"], 18)
        self.assertEqual(summary["semantic_parent_branch_count"], 9)
        self.assertEqual(summary["unique_parent_byte_graph_count"], 7)
        self.assertEqual(summary["p12_schema70_search_target_schema"], 86)

    def test_scope_parent_mapping_is_exact(self) -> None:
        rows = build_search_publication_manifest()["rows"].values()
        selected = [row for row in rows if row["search_component_selected"]]
        p12_scope = [
            row
            for row in selected
            if row["baseline_name"] == "p12"
            and row["semantic_parent_variant"] == "selected_scope_candidate"
        ]
        self.assertEqual(len(p12_scope), 2)
        self.assertTrue(all(row["p12_scope_uses_historical_schema70_parent"] for row in p12_scope))
        self.assertTrue(all(row["target_state_schema_version"] == 86 for row in p12_scope))
        mainline_scope = [
            row
            for row in selected
            if row["baseline_name"] in {"schema76", "schema77"}
            and row["semantic_parent_variant"] == "selected_scope_candidate"
        ]
        self.assertEqual(len(mainline_scope), 4)
        self.assertTrue(all(row["mainline_scope_is_zero_byte_markdown_alias"] for row in mainline_scope))
        self.assertEqual(
            {row["target_state_schema_version"] for row in mainline_scope},
            {83, 85},
        )

    def test_contract_never_authorizes_execution(self) -> None:
        for row in build_search_publication_manifest()["rows"].values():
            self.assertFalse(row["search_candidate_bytes_built_or_materialized"])
            self.assertFalse(row["entropy_controller_published_or_implemented"])
            self.assertFalse(row["joint_package_built_or_materialized"])
            self.assertFalse(row["shared_api_lease_acquired"])
            self.assertFalse(row["network_model_search_fetch_evaluator_or_api_called"])
            self.assertFalse(row["benchmark_forward_or_full220_launch_allowed"])

    def test_tampered_work_order_fails_closed(self) -> None:
        row = next(iter(build_work_order_manifest()["rows"].values()))
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = []
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            build_search_publication_order(tampered)


if __name__ == "__main__":
    unittest.main()
