from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import correct_v24855_pacing_critical_path as correction  # noqa: E402


class V24855PacingCriticalPathCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = correction.build(now=1)

    def test_source_is_preserved_and_fields_are_explicitly_superseded(self) -> None:
        source = self.value["source"]
        self.assertFalse(source["source_artifact_mutated"])
        self.assertEqual(len(source["superseded_fields"]), 3)

    def test_sum_wait_count_replays_but_is_not_critical_path(self) -> None:
        value = self.value["correction"]
        self.assertEqual(value["source_sum_wait_below_30_count"], 21)
        self.assertTrue(value["sum_wait_must_not_be_subtracted_from_wall_clock"])

    def test_corrected_max_wait_partition_is_19_plus_8(self) -> None:
        value = self.value["correction"]
        self.assertEqual(value["v24854_latency_stop_count"], 27)
        self.assertEqual(value["corrected_max_wait_below_30_count"], 19)
        self.assertEqual(value["corrected_residual_slow_count"], 8)
        self.assertTrue(value["max_wait_is_conservative_same_pass_content_free_proxy"])

    def test_correction_is_aggregate_only_and_label_blind(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(correction.OPAQUE.search(encoded))
        self.assertIsNone(correction.SECRET.search(encoded))
        self.assertFalse(
            self.value["boundary"][
                "historical_stop_membership_authorized_as_runtime_route"
            ]
        )

    def test_public_benchmark_and_quality_claims_are_forbidden(self) -> None:
        self.assertFalse(
            self.value["conclusions"]["pacing_mixture_proves_quality_gain"]
        )
        self.assertFalse(self.value["authorization"]["public_dev64_or_exact220"])
        self.assertFalse(self.value["authorization"]["leaderboard_or_sota"])

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / correction.OUTPUT
        if path.is_file():
            published = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(correction.validate(published), published)


if __name__ == "__main__":
    unittest.main()
