from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import diagnose_v25058_v25057_zero_exposure as target  # noqa: E402


class V25058ZeroExposureDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_exact220_zero_exposure_and_cold_variation(self) -> None:
        self.assertEqual(self.value["fixed_denominator"]["tasks"], 220)
        self.assertEqual(self.value["production_exposure"]["projected_pages"], 1523)
        self.assertEqual(
            self.value["production_exposure"]["mechanism_exposed_pages"], 0
        )
        self.assertEqual(
            self.value["cross_cold_run"]["prediction_hash_changed_tasks"], 208
        )
        self.assertEqual(
            self.value["cross_cold_run"]["whole_table_success_delta"], -1
        )
        self.assertEqual(
            self.value["cross_cold_run"]["quality_composite_delta"],
            -0.0003312325898634505,
        )

    def test_zero_exposure_forbids_treatment_causality_and_repeat_220(self) -> None:
        diagnosis = self.value["diagnosis"]
        self.assertFalse(
            diagnosis[
                "prediction_or_quality_difference_attributable_to_page_self_treatment"
            ]
        )
        self.assertTrue(
            diagnosis[
                "prediction_hash_changes_are_cold_search_and_model_rollout_variation"
            ]
        )
        self.assertFalse(
            diagnosis["repeat_exact220_with_same_page_self_binding_is_authorized"]
        )
        self.assertEqual(diagnosis["entropy_or_information_gain_signed_credit"], 0)
        self.assertFalse(self.value["authorization"]["new_exact220_launch"])

    def test_output_policy_is_aggregate_only(self) -> None:
        policy = self.value["content_policy"]
        self.assertTrue(
            policy["opaque_ids_or_prediction_hashes_used_only_for_in_memory_alignment"]
        )
        self.assertFalse(
            policy[
                "question_id_prediction_page_url_query_gold_category_or_per_task_metric_emitted"
            ]
        )
        self.assertFalse(
            policy["network_model_search_fetch_evaluator_or_credential_accessed"]
        )

    def test_resealed_exposure_or_authorization_tamper_fails(self) -> None:
        for mutation in ("exposure", "launch", "extra_field"):
            changed = copy.deepcopy(self.value)
            if mutation == "exposure":
                changed["production_exposure"]["mechanism_exposed_pages"] = 1
            elif mutation == "launch":
                changed["authorization"]["new_exact220_launch"] = True
            else:
                changed["production_exposure"]["page_text"] = "must not emit"
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "diagnosis.json"
            target.publish_exclusive(path, self.value)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), self.value)
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, self.value)


if __name__ == "__main__":
    unittest.main()
