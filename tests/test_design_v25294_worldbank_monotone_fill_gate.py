from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25294_worldbank_monotone_fill_gate as target  # noqa: E402


class V25294WorldBankMonotoneFillGateDesignTests(unittest.TestCase):
    def test_parent_diagnosis_is_exactly_bound(self) -> None:
        value = target._parent_barrier()
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(
            target.base.sha256(target.PARENT_DIAGNOSIS),
            target.EXPECTED_PARENT_SHA256,
        )
        design = target.build_design(now=1)
        self.assertEqual(
            design["source_hashes"],
            {
                str(path): target.base.sha256(path)
                for path in (target.SOURCE, target.TEST)
            },
        )

    def test_deterministic_selector_is_order_invariant_fresh_and_disjoint(self) -> None:
        targets = [f"indicator-{index}@2025" for index in range(30)]
        entities = [f"entity-{index:03d}" for index in range(200)]
        by_target = {target: list(entities) for target in targets}
        page_chars = {target: [4_000, 4_100] for target in targets}
        first = target.select_vector(
            by_target,
            page_chars,
            historical_target_keys=targets[:2],
        )
        second = target.select_vector(
            {
                key: list(reversed(by_target[key]))
                for key in reversed(targets)
            },
            {key: list(reversed(page_chars[key])) for key in reversed(targets)},
            historical_target_keys=list(reversed(targets[:2])),
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first["target_keys"]), 4)
        self.assertEqual(len(first["entity_keys"]), 144)
        self.assertTrue(set(first["target_keys"]).isdisjoint(targets[:2]))

    def test_selector_capacity_or_namespace_failure_is_fail_closed(self) -> None:
        targets = [f"target-{index}" for index in range(24)]
        entities = [f"entity-{index}" for index in range(160)]
        by_target = {target: list(entities) for target in targets}
        page_chars = {target: [4_000, 4_100] for target in targets}
        with self.assertRaises(RuntimeError):
            target.select_vector(
                {key: by_target[key] for key in targets[:-1]},
                {key: page_chars[key] for key in targets[:-1]},
                historical_target_keys=[],
            )
        with self.assertRaises(RuntimeError):
            target.select_vector(
                by_target,
                page_chars,
                historical_target_keys=targets[:-3],
            )
        disconnected = {
            key: [f"{key}-entity-{index}" for index in range(160)]
            for key in targets
        }
        with self.assertRaisesRegex(RuntimeError, "no eligible"):
            target.select_vector(
                disconnected,
                page_chars,
                historical_target_keys=[],
            )
        too_large = copy.deepcopy(page_chars)
        too_large[targets[0]][0] = 5_001
        with self.assertRaisesRegex(RuntimeError, "aggregate"):
            target.select_vector(
                by_target,
                too_large,
                historical_target_keys=[],
            )
        with self.assertRaises(ValueError):
            target.deterministic_rank("benchmark_label", "value")

    def test_shared_representation_and_caps_are_exact(self) -> None:
        value = target.build_design(now=1)
        snapshot = value["snapshot_and_representation_contract"]
        runtime = value["runtime_contract"]
        caps = value["physical_caps"]
        self.assertTrue(
            snapshot[
                "same_eight_global_rendered_pages_shared_by_all_tasks_control_candidate_and_binder"
            ]
        )
        self.assertTrue(snapshot["renderer_output_fixed_before_parent_or_candidate_branch"])
        self.assertTrue(
            runtime[
                "control_and_candidate_share_queries_search_responses_fetch_bytes_and_rendered_pages"
            ]
        )
        self.assertEqual(caps["query_cap_per_task"], 4)
        self.assertEqual(caps["fetch_cap_per_task"], 10)
        self.assertEqual(caps["model_call_cap_per_task"], 3)
        self.assertEqual(caps["wall_seconds_per_task"], 240)
        self.assertEqual(caps["page_count_per_task"], 8)
        self.assertFalse(caps["new_query_fetch_model_context_token_or_wall_budget"])

    def test_mechanism_precedes_evaluator_and_requires_real_prediction_change(self) -> None:
        value = target.build_design(now=1)
        mechanism = value["mechanism_gate_before_evaluator"]
        quality = value["postfreeze_quality_gate"]
        self.assertEqual(mechanism["supported_unknown_fill_tasks_minimum"], 2)
        self.assertEqual(mechanism["attributable_prediction_change_tasks_minimum"], 2)
        self.assertEqual(
            mechanism["zero_supported_fill_or_prediction_change"],
            "strict_no_go_without_evaluator",
        )
        self.assertTrue(
            quality[
                "exists_only_after_predictions_forward_result_and_audit_are_pushed"
            ]
        )
        self.assertEqual(quality["candidate_exact_successes_minimum_delta"], 2)
        self.assertEqual(quality["control_exact_to_candidate_inexact_regressions"], 0)

    def test_design_is_label_blind_build_only_and_credit_zero(self) -> None:
        value = target.build_design(now=1)
        self.assertEqual(target.validate_design(value), value)
        self.assertFalse(
            value[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            ]
        )
        self.assertEqual(value["runtime_contract"]["positive_signed_credit_count"], 0)
        authorization = value["authorization"]
        self.assertTrue(
            authorization["population_selector_and_runtime_implementation_build_only"]
        )
        self.assertFalse(authorization["network_population_selection_or_freeze"])
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])
        self.assertFalse(
            authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        )

    def test_resealed_population_renderer_gate_credit_or_authority_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        for kind in ("population", "renderer", "gate", "credit", "authority"):
            changed = copy.deepcopy(value)
            if kind == "population":
                changed["population_contract"]["tasks"] = 19
            elif kind == "renderer":
                changed["snapshot_and_representation_contract"][
                    "renderer_output_fixed_before_parent_or_candidate_branch"
                ] = False
            elif kind == "gate":
                changed["mechanism_gate_before_evaluator"][
                    "attributable_prediction_change_tasks_minimum"
                ] = 0
            elif kind == "credit":
                changed["runtime_contract"]["positive_signed_credit_count"] = 1
            else:
                changed["authorization"]["external_activation_or_launch"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)


if __name__ == "__main__":
    unittest.main()
