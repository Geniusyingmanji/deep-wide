from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25335_v25330_transport_capacity as target  # noqa: E402


class V25335TransportCapacityDiagnosisTests(unittest.TestCase):
    def test_consumed_manifest_is_exact96_144_169(self) -> None:
        value = target._manifest()
        self.assertTrue(all(value["checks"].values()))
        self.assertEqual(value["target_count"], 96)
        self.assertEqual(value["entity_count"], 144)
        self.assertEqual(value["response_count"], 169)
        self.assertEqual(value["per_attempt_response_counts"], [48, 36, 43, 42])

    def test_counterfactual_replay_selects3_not2_under110_seconds(self) -> None:
        result = target.current.validate_result(target._read(target.current.RESULT))
        cap2 = target._counterfactual_schedule(result, 2)
        cap3 = target._counterfactual_schedule(result, 3)
        self.assertEqual(cap2["counterfactual_makespan_seconds"], 139.981309)
        self.assertEqual(cap3["counterfactual_makespan_seconds"], 93.91118)
        self.assertGreater(cap2["counterfactual_makespan_seconds"], 110)
        self.assertLess(cap3["counterfactual_makespan_seconds"], 110)
        self.assertFalse(cap3["replay_is_not_a_performance_guarantee_or_provider_causal_proof"] is False)

    def test_diagnosis_is_valid_bounded_and_build_only(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        self.assertFalse(value["diagnosis"]["counterfactual_replay_proves_future_success"])
        self.assertFalse(value["diagnosis"]["transport_pattern_proves_unique_causal_root_cause"])
        self.assertTrue(value["diagnosis"]["next_candidate_changes_only_max_target_concurrency_to3"])
        self.assertTrue(value["authorization"]["concurrency3_fresh_disjoint_transport_successor_build"])
        self.assertFalse(value["authorization"]["successor_population_network_activation_or_launch"])

    def test_resealed_manifest_replay_diagnosis_or_authority_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("manifest", "replay", "success", "cause", "launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "manifest":
                changed["consumed_manifest"]["response_count"] = 168
            elif kind == "replay":
                changed["counterfactual_capacity_replay"]["3"]["counterfactual_makespan_seconds"] = 80.0
            elif kind == "success":
                changed["diagnosis"]["counterfactual_replay_proves_future_success"] = True
            elif kind == "cause":
                changed["diagnosis"]["transport_pattern_proves_unique_causal_root_cause"] = True
            elif kind == "launch":
                changed["authorization"]["successor_population_network_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.current.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_diagnosis_has_no_live_effect_constructor_or_content_emit(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "question_text", "page_content", "prediction_text", "credential_value",
            "requests.", "urlopen(", "AzureNativeSearchClient(", "run_official_eval_local",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
