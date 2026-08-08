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

from scripts import diagnose_v24912_v24911_nonengagement as diagnosis  # noqa: E402


class V24912V24911NonengagementDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build(now=1_786_211_500)

    def test_complete_frozen_chains_reconcile(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["findings"], [])
        self.assertTrue(all(self.value["checks"].values()))

    def test_declared_12k_does_not_reach_helper(self) -> None:
        binding = self.value["helper_cap_binding"]
        self.assertEqual(binding["candidate_declared_input_page_character_cap"], 12_000)
        self.assertEqual(binding["legacy_helper_contract_page_character_cap"], 5_000)
        self.assertTrue(binding["helper_imports_limits_from_legacy_v24287_contract"])
        self.assertTrue(binding["helper_max_page_chars_keyword_reads_legacy_limits"])
        self.assertFalse(binding["candidate_12000_cap_reaches_helper_process"])

    def test_fetch_boundary_rejects_5001(self) -> None:
        binding = self.value["helper_cap_binding"]
        self.assertTrue(binding["parent_fetch_validator_accepts_5000_characters"])
        self.assertTrue(binding["parent_fetch_validator_rejects_5001_characters"])

    def test_candidate_observations_obey_legacy_envelope(self) -> None:
        mechanism = self.value["runs"]["v24911"]["mechanism"]
        self.assertEqual(mechanism["observable_task_telemetry"], 218)
        self.assertEqual(mechanism["missing_task_telemetry"], 2)
        self.assertEqual(
            mechanism[
                "legacy_5000_character_per_usable_page_envelope_violation_count"
            ],
            0,
        )

    def test_projection_receipt_observability_is_missing(self) -> None:
        mechanism = self.value["runs"]["v24911"]["mechanism"]
        self.assertEqual(mechanism["content_free_projection_receipt_file_count"], 0)
        self.assertTrue(
            self.value["conclusions"]["projection_receipt_observability_missing"]
        )

    def test_quality_is_valid_but_not_long_page_causal_evidence(self) -> None:
        runs = self.value["runs"]
        self.assertEqual(runs["v24909"]["quality"]["whole_table_successes"], 7)
        self.assertEqual(runs["v24911"]["quality"]["whole_table_successes"], 6)
        self.assertFalse(
            self.value["conclusions"][
                "quality_difference_attributable_to_long_page_window"
            ]
        )
        self.assertFalse(
            self.value["comparisons"]["v24911_minus_v24909"][
                "causal_packer_effect_estimate"
            ]
        )

    def test_rollouts_are_mostly_different_predictions(self) -> None:
        comparison = self.value["comparisons"]["v24911_minus_v24909"]
        self.assertEqual(comparison["prediction_hash_identity_count"], 11)
        self.assertEqual(comparison["prediction_hash_difference_count"], 209)
        self.assertFalse(comparison["same_fetch_bytes_or_random_seed_shared"])

    def test_report_is_aggregate_only_and_content_safe(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertIsNone(re.search(r"(?:deep2wide_result_|wide2deep_ws_)", encoded))
        self.assertNotIn("| Result |", encoded)
        self.assertFalse(
            self.value["boundary"][
                "historical_correctness_or_score_authorized_as_future_runtime_input"
            ]
        )

    def test_successor_requires_external_shared_prefix_gate(self) -> None:
        gate = self.value["next_gate"]
        self.assertTrue(
            gate["baseline_and_candidate_share_identical_12000_character_fetch_bytes"]
        )
        self.assertTrue(gate["prediction_freeze_before_gold_or_quality_read"])
        self.assertFalse(self.value["authorization"]["public_dev64_or_exact220"])

    def test_resealed_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["helper_cap_binding"]["candidate_12000_cap_reaches_helper_process"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = diagnosis.candidate.payload_sha256(
            altered
        )
        with self.assertRaises(RuntimeError):
            diagnosis.validate(altered)

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / diagnosis.OUTPUT
        if path.is_file():
            published = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(diagnosis.validate(published), published)


if __name__ == "__main__":
    unittest.main()
