from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24204_postdecision_work_order import (  # noqa: E402
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import ENTROPY, SEARCH  # noqa: E402
from deepwide_agent.v24211_entropy_feasibility import (  # noqa: E402
    TARGET_SCHEMA_BY_PARENT_SCHEMA,
    build_entropy_feasibility_manifest,
    build_entropy_integration_order,
)


class V24211EntropyFeasibilityTests(unittest.TestCase):
    def test_all_18_decisions_and_14_parent_byte_graphs_are_derived(self) -> None:
        value = build_entropy_feasibility_manifest()
        summary = value["summary"]
        self.assertEqual(summary["decision_count"], 18)
        self.assertEqual(summary["baseline_counts"], {"p12": 6, "schema76": 6, "schema77": 6})
        self.assertEqual(
            summary["parent_owner_counts"],
            {"baseline": 3, "markdown": 3, "scope": 3, "search": 9},
        )
        self.assertEqual(summary["unique_parent_byte_graph_count"], 14)
        self.assertEqual(summary["search_bytes_required_count"], 9)
        self.assertEqual(summary["search_bytes_forbidden_count"], 9)
        self.assertEqual(
            summary["target_state_schema_versions"], list(range(87, 101))
        )

    def test_search_presence_is_an_exact_parent_boundary(self) -> None:
        rows = build_entropy_feasibility_manifest()["rows"].values()
        with_search = [row for row in rows if SEARCH in row["eligible_components"]]
        without_search = [row for row in rows if SEARCH not in row["eligible_components"]]
        self.assertEqual(len(with_search), 9)
        self.assertEqual(len(without_search), 9)
        for row in with_search:
            self.assertEqual(row["parent_owner"], "search")
            self.assertTrue(row["search_bytes_required"])
            self.assertFalse(row["search_bytes_forbidden"])
            self.assertFalse(row["silent_presearch_fallback_allowed"])
            self.assertIn("v24210", row["required_parent_publication_path"])
        for row in without_search:
            self.assertNotEqual(row["parent_owner"], "search")
            self.assertFalse(row["search_bytes_required"])
            self.assertTrue(row["search_bytes_forbidden"])
            self.assertFalse(row["silent_presearch_fallback_allowed"])

    def test_zero_byte_scope_aliases_share_their_markdown_parent_graph(self) -> None:
        rows = build_entropy_feasibility_manifest()["rows"].values()
        mainline_no_search = [
            row
            for row in rows
            if row["baseline_name"] in {"schema76", "schema77"}
            and SEARCH not in row["eligible_components"]
        ]
        by_baseline: dict[str, set[tuple[str, int]]] = {}
        for row in mainline_no_search:
            by_baseline.setdefault(row["baseline_name"], set()).add(
                (row["parent_graph_id"], row["target_state_schema_version"])
            )
        self.assertEqual(len(by_baseline["schema76"]), 2)
        self.assertEqual(len(by_baseline["schema77"]), 2)

    def test_parent_schema_to_target_schema_is_one_to_one_and_append_only(self) -> None:
        self.assertEqual(set(TARGET_SCHEMA_BY_PARENT_SCHEMA.values()), set(range(87, 101)))
        self.assertEqual(len(TARGET_SCHEMA_BY_PARENT_SCHEMA), 14)

    def test_every_order_requires_model_gate_and_real_adapters_without_launch(self) -> None:
        for row in build_entropy_feasibility_manifest()["rows"].values():
            self.assertTrue(row["required_gate2a_controller_design_allowed"])
            self.assertEqual(row["required_gate2a_status"], "replicate_aware_gate2a_pass")
            self.assertTrue(row["model_sha256_must_bind_publication"])
            self.assertTrue(row["job_manifest_sha256_must_bind_model_and_publication"])
            self.assertFalse(
                row[
                    "parent_forward_closure_contains_real_state_transition_adapters"
                ]
            )
            self.assertFalse(
                row["parent_forward_closure_contains_entropy_controller_kernel"]
            )
            self.assertFalse(
                row[
                    "parent_forward_closure_contains_entropy_controller_runner_hook"
                ]
            )
            self.assertTrue(
                row["historical_adapters_are_not_parent_bytes"]
            )
            self.assertTrue(row["real_state_transition_adapters_required"])
            self.assertFalse(row["projection_only_action_arm_allowed"])
            self.assertFalse(row["static_candidate_rebase_currently_feasible"])
            self.assertEqual(len(row["static_candidate_rebase_blockers"]), 4)
            self.assertFalse(row["controller_candidate_bytes_built_or_materialized"])
            self.assertFalse(row["benchmark_forward_or_full220_launch_allowed"])

    def test_non_entropy_or_tampered_work_order_fails_closed(self) -> None:
        rows = build_work_order_manifest()["rows"].values()
        non_entropy = next(row for row in rows if ENTROPY not in row["eligible_components"])
        with self.assertRaisesRegex(RuntimeError, "does not select entropy"):
            build_entropy_integration_order(non_entropy)
        entropy = next(row for row in rows if ENTROPY in row["eligible_components"])
        broken = copy.deepcopy(entropy)
        broken["eligible_components"] = []
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            build_entropy_integration_order(broken)


if __name__ == "__main__":
    unittest.main()
