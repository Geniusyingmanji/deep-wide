from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import record_v24783_projection_population_capacity_precheck as target  # noqa: E402


class V24783ProjectionPopulationCapacityPrecheckTests(unittest.TestCase):
    def build(self) -> dict:
        with (
            patch.object(target, "_parent_valid", return_value=True),
            patch.object(target, "_git", return_value="a" * 40),
            patch.object(target.contract, "sha256", return_value="b" * 64),
        ):
            return target.build_record(now=0)

    def test_actual_parent_authorizes_design_without_launch(self) -> None:
        self.assertTrue(target._parent_valid())
        parent = target._read(ROOT / target.PARENT)
        self.assertTrue(
            parent["authorization"][
                "fresh_disjoint_population_and_inert_protocol_design"
            ]
        )
        self.assertFalse(
            parent["authorization"]["fresh_external_activation_or_launch"]
        )

    def test_exact_aggregate_counts_and_source_reads_are_frozen(self) -> None:
        value = self.build()
        self.assertEqual(value["source"]["immutable_tree_read_count"], 2)
        self.assertEqual(value["source"]["immutable_record_read_count"], 6_964)
        self.assertEqual(
            value["probe_results"]["noneducation_country_cap4"][
                "maximum_selected_count"
            ],
            20,
        )
        curve = value["probe_results"]["all_types_capacity_curve"]
        self.assertEqual(curve["minimum_feasible_country_cap"], 7)
        self.assertEqual(curve["country_count_vector_at_minimum_cap_sorted"], [4, 7, 7, 7, 7])

    def test_source_policy_records_no_benchmark_or_private_read(self) -> None:
        value = self.build()
        self.assertEqual(
            value["source_policy"],
            {
                "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
                "prior_private_population_truth_provenance_or_quality_opened_or_hashed": False,
                "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
                "model_hosted_search_benchmark_forward_or_evaluator_called": False,
                "credential_read_hashed_persisted_or_emitted": False,
            },
        )

    def test_resealed_capacity_or_launch_tamper_fails_closed(self) -> None:
        for mutate in (
            lambda value: value["probe_results"]["all_types_capacity_curve"].__setitem__(
                "minimum_feasible_country_cap", 6
            ),
            lambda value: value["authorization"].__setitem__(
                "activation_or_external_launch", True
            ),
        ):
            altered = copy.deepcopy(self.build())
            mutate(altered)
            altered.pop("record_payload_sha256")
            altered["record_payload_sha256"] = target.contract.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_record(altered)

    def test_create_only_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "record.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
