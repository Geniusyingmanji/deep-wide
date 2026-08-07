from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24838_v24834_v24837_information_bottleneck as diagnosis  # noqa: E402


class V24838InformationBottleneckDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = diagnosis.build(now=1_786_150_000)

    def test_complete_exact220_reconciles(self) -> None:
        overall = self.report["overall"]
        self.assertEqual(overall["control"]["n"], 220)
        self.assertEqual(overall["candidate"]["n"], 220)
        self.assertEqual(overall["delta"]["whole_table_success_delta"], -1)
        self.assertEqual(overall["delta"]["fallback_table_delta"], -1)

    def test_exact_and_invalid_transitions_are_aggregate_only(self) -> None:
        self.assertEqual(
            self.report["exact_transitions"],
            {
                "control_exact_candidate_exact": 5,
                "control_exact_candidate_not_exact": 3,
                "control_not_exact_candidate_exact": 2,
                "control_not_exact_candidate_not_exact": 210,
            },
        )
        self.assertEqual(
            self.report["evaluator_validity_transitions"],
            {
                "control_invalid_candidate_invalid": 6,
                "control_invalid_candidate_valid": 5,
                "control_valid_candidate_invalid": 5,
                "control_valid_candidate_valid": 204,
            },
        )

    def test_compression_saved_context_and_tokens(self) -> None:
        mechanism = self.report["overall"]["delta"]["mechanism"]
        self.assertLess(mechanism["projected_chars"], -6_000)
        self.assertLess(mechanism["model_input_tokens"], -2_000)
        self.assertLess(self.report["system_aggregate"]["token_delta"], -500_000)
        self.assertTrue(
            self.report["conclusions"][
                "candidate_reduced_total_tokens_and_forward_wall"
            ]
        )

    def test_item_f1_improves_but_promotion_gate_fails(self) -> None:
        delta = self.report["overall"]["delta"]
        self.assertGreater(delta["metrics"]["f1_by_item"], 0)
        self.assertLess(delta["metrics"]["quality_composite"], 0)
        self.assertFalse(
            self.report["conclusions"][
                "candidate_exact_and_quality_composite_improved"
            ]
        )
        self.assertFalse(
            self.report["conclusions"]["round_robin_16k_authorized_for_promotion"]
        )

    def test_independent_sampling_prevents_causal_claim(self) -> None:
        conclusions = self.report["conclusions"]
        self.assertTrue(
            conclusions[
                "independent_search_fetch_generation_and_judge_samples_remain_confounders"
            ]
        )
        self.assertFalse(conclusions["this_pair_establishes_projector_causal_effect"])
        self.assertGreater(
            self.report["retrieval_route_transitions"]["control_stop_candidate_expand"],
            0,
        )
        self.assertGreater(
            self.report["retrieval_route_transitions"]["control_expand_candidate_stop"],
            0,
        )

    def test_report_is_label_blind_and_content_free(self) -> None:
        encoded = json.dumps(self.report, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertNotIn("deep2wide_result", encoded)
        self.assertNotIn("| Result |", encoded)
        boundary = self.report["boundary"]
        self.assertFalse(
            boundary[
                "historical_score_transition_or_stratum_authorized_as_future_runtime_input"
            ]
        )

    def test_successor_requires_shared_prefix_external_gate(self) -> None:
        work = self.report["next_work"]
        self.assertIn("structure_preserving_16k_projection", work["candidate"])
        self.assertIn(
            "same raw page byte vector for both arms",
            work["required_external_gate_controls"],
        )
        self.assertFalse(work["public_exact220_authorized_after_this_diagnosis"])

    def test_resealed_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.report)
        altered["overall"]["delta"]["whole_table_success_delta"] += 1
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(
            altered
        )
        with self.assertRaises(RuntimeError):
            diagnosis.validate(altered)


if __name__ == "__main__":
    unittest.main()
