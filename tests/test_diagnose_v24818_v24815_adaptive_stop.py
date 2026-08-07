from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24818_v24815_adaptive_stop as target  # noqa: E402


class V24818AdaptiveStopDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_frozen_denominator_and_decisions_reconcile(self) -> None:
        self.assertEqual(self.value["denominator"], 12)
        self.assertEqual(self.value["decision_counts"], {"expand": 11, "stop": 1})

    def test_stopped_suffix_was_quality_improving(self) -> None:
        stopped = self.value["stopped_suffix_observation"]
        self.assertEqual(stopped["stopped_task_count"], 1)
        self.assertEqual(stopped["first_wave_valid_record_count"], 2)
        self.assertEqual(stopped["additional_valid_record_count_in_physically_executed_fixed_suffix"], 4)
        self.assertAlmostEqual(
            stopped["fixed_full_minus_first_wave_metric_sum"]["item_f1"], 0.5
        )
        self.assertAlmostEqual(
            stopped["fixed_full_minus_first_wave_metric_sum"]["composite"],
            0.125,
        )
        self.assertTrue(stopped["all_stopped_task_composite_deltas_positive"])

    def test_smoke_cost_scale_is_not_an_empirical_calibration(self) -> None:
        audit = self.value["calibration_audit"]
        self.assertTrue(audit["calibration_reference_is_explicit_smoke_marker"])
        self.assertFalse(audit["calibration_artifact_path_bound_in_protocol"])
        self.assertFalse(audit["empirical_cost_to_quality_exchange_rate_bound"])
        self.assertEqual(audit["entropy_feature_weight"], 0.0)

    def test_output_is_aggregate_only_and_does_not_authorize_replay(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertFalse(
            self.value["authorization"]["same_population_replay_or_revaluation"]
        )
        self.assertFalse(self.value["authorization"]["public_dev64_or_exact220"])
        self.assertFalse(self.value["boundary"]["network_model_search_fetch_benchmark_or_evaluator_called"])

    def test_replay_and_tamper_rejection(self) -> None:
        target.validate_report(ROOT, self.value)
        altered = copy.deepcopy(self.value)
        altered["authorization"]["leaderboard_or_sota"] = True
        unsigned = dict(altered)
        unsigned.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.contract.payload_sha256(unsigned)
        with self.assertRaises(RuntimeError):
            target.validate_report(ROOT, altered, rebuild=False)


if __name__ == "__main__":
    unittest.main()
