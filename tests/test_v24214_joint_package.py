from __future__ import annotations

import copy
import unittest

from deepwide_agent.v24204_postdecision_work_order import (
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import (
    ENTROPY,
    MARKDOWN,
    SCOPE,
    SEARCH,
)
from deepwide_agent.v24214_joint_package import (
    build_joint_package_manifest,
    build_joint_package_order,
    validate_joint_package_order,
)


def row_with(components: list[str], baseline: str = "p12") -> dict:
    rows = build_work_order_manifest()["rows"].values()
    return next(
        row
        for row in rows
        if row["baseline_name"] == baseline
        and row["eligible_components"] == components
    )


class V24214JointPackageTests(unittest.TestCase):
    def test_manifest_covers_all_deepest_owners_without_overlay(self) -> None:
        summary = build_joint_package_manifest()["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["identity_handoff_count"], 3)
        self.assertEqual(summary["joint_revalidation_required_count"], 33)
        self.assertEqual(
            summary["deepest_semantic_owner_counts"],
            {
                "baseline": 3,
                "entropy": 18,
                "markdown": 3,
                "scope": 3,
                "search": 9,
            },
        )
        self.assertEqual(
            summary["deepest_byte_owner_counts"],
            {
                "baseline": 3,
                "entropy": 18,
                "markdown": 5,
                "scope": 1,
                "search": 9,
            },
        )
        self.assertEqual(summary["candidate_directory_overlay_count"], 0)

    def test_empty_components_are_exact_baseline_identity_handoffs(self) -> None:
        expected = {"p12": 68, "schema76": 76, "schema77": 77}
        for baseline, schema in expected.items():
            value = build_joint_package_order(row_with([], baseline))
            self.assertTrue(value["identity_handoff_only"])
            self.assertFalse(value["joint_revalidation_required"])
            self.assertEqual(value["deepest_semantic_owner"], "baseline")
            self.assertEqual(value["deepest_byte_owner"], "baseline")
            self.assertEqual(value["final_state_schema_version"], schema)
            self.assertEqual(len(value["parent_chain"]), 1)

    def test_markdown_paths_select_the_cumulative_markdown_candidate(self) -> None:
        expected = {"p12": 69, "schema76": 78, "schema77": 79}
        for baseline, schema in expected.items():
            value = build_joint_package_order(row_with([MARKDOWN], baseline))
            self.assertEqual(
                [stage["stage"] for stage in value["parent_chain"]],
                ["baseline", "markdown"],
            )
            self.assertEqual(value["deepest_semantic_owner"], "markdown")
            self.assertEqual(value["deepest_byte_owner"], "markdown")
            self.assertEqual(value["final_state_schema_version"], schema)

    def test_scope_alias_keeps_mainline_markdown_bytes(self) -> None:
        components = [MARKDOWN, SCOPE]
        expected = {
            "p12": (70, "scope", False),
            "schema76": (78, "markdown", True),
            "schema77": (79, "markdown", True),
        }
        for baseline, (schema, byte_owner, alias) in expected.items():
            value = build_joint_package_order(row_with(components, baseline))
            scope = value["parent_chain"][-1]
            self.assertEqual(value["deepest_semantic_owner"], "scope")
            self.assertEqual(value["deepest_byte_owner"], byte_owner)
            self.assertEqual(value["final_state_schema_version"], schema)
            self.assertIs(scope["zero_byte_alias"], alias)
            if alias:
                self.assertEqual(
                    scope["source_state_schema_version"],
                    scope["target_state_schema_version"],
                )

    def test_search_paths_bind_search_as_deepest_parent(self) -> None:
        manifests = build_joint_package_manifest()["rows"].values()
        rows = [
            row
            for row in manifests
            if SEARCH in row["eligible_components"]
            and ENTROPY not in row["eligible_components"]
        ]
        self.assertEqual(len(rows), 9)
        for value in rows:
            self.assertEqual(value["deepest_semantic_owner"], "search")
            self.assertEqual(value["deepest_byte_owner"], "search")
            self.assertIn(value["final_state_schema_version"], range(80, 87))
            self.assertEqual(value["parent_chain"][-1]["stage"], "search")

    def test_entropy_paths_bind_all_fourteen_registered_parent_graphs(self) -> None:
        rows = [
            row
            for row in build_joint_package_manifest()["rows"].values()
            if ENTROPY in row["eligible_components"]
        ]
        self.assertEqual(len(rows), 18)
        self.assertEqual(
            {row["final_state_schema_version"] for row in rows},
            set(range(87, 101)),
        )
        for value in rows:
            self.assertEqual(value["deepest_semantic_owner"], "entropy")
            self.assertEqual(value["deepest_byte_owner"], "entropy")
            self.assertEqual(value["parent_chain"][-1]["stage"], "entropy")
            self.assertEqual(
                value["selected_components_covered_in_frozen_order"],
                value["eligible_components"],
            )

    def test_no_order_authorizes_gate_api_or_benchmark(self) -> None:
        false_fields = (
            "silent_component_drop_or_baseline_fallback_allowed",
            "candidate_directory_overlay_allowed",
            "joint_package_built_or_materialized",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "network_model_search_fetch_evaluator_or_api_called",
            "mapping_gold_category_question_type_evaluator_score_or_reward_read",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        )
        for value in build_joint_package_manifest()["rows"].values():
            for field in false_fields:
                self.assertFalse(value[field])

    def test_tampered_work_order_or_joint_order_fails_closed(self) -> None:
        work_order = row_with([SEARCH, MARKDOWN, SCOPE, ENTROPY])
        broken_work = copy.deepcopy(work_order)
        broken_work["eligible_components"] = [MARKDOWN]
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            build_joint_package_order(broken_work)

        value = build_joint_package_order(work_order)
        broken_value = copy.deepcopy(value)
        broken_value["deepest_byte_owner"] = "baseline"
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            validate_joint_package_order(broken_value)


if __name__ == "__main__":
    unittest.main()
