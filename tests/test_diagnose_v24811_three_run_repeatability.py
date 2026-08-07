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

from scripts import diagnose_v24811_v24800_v24807_v24810_repeatability as target


class V24811ThreeRunRepeatabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_three_full220_runs_reconcile(self):
        self.assertEqual(set(self.value["runs"]), set(target.VERSIONS))
        self.assertTrue(all(row["n"] == 220 for row in self.value["runs"].values()))
        self.assertEqual(
            [self.value["runs"][v]["whole_table_successes"] for v in target.VERSIONS],
            [8, 8, 6],
        )

    def test_prediction_identity_partition(self):
        identity = self.value["prediction_identity"]
        self.assertEqual(sum(identity.values()), 220)
        self.assertLess(identity["all_three_identical"], 220)
        self.assertGreater(identity["all_three_different"], 0)

    def test_success_set_is_unstable(self):
        whole = self.value["whole_table"]
        self.assertEqual(sum(whole["success_pattern_counts_order_v24800_v24807_v24810"].values()), 220)
        self.assertLess(whole["success_set_intersection_over_union"], 1.0)
        self.assertFalse(self.value["conclusions"]["whole_table_success_set_is_stable"])

    def test_output_is_aggregate_only_and_forbids_public_rerun(self):
        encoded = json.dumps(self.value, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertFalse(self.value["boundary"]["prediction_field_read"])
        self.assertFalse(self.value["authorization"]["new_public_exact220"])
        self.assertFalse(self.value["authorization"]["selective_revaluation"])

    def test_reproducible_and_tamper_rejected(self):
        target.validate_report(ROOT, self.value)
        altered = copy.deepcopy(self.value)
        altered["authorization"]["sota_claim"] = True
        unsigned = dict(altered)
        unsigned.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.contract.payload_sha256(unsigned)
        with self.assertRaises(RuntimeError):
            target.validate_report(ROOT, altered, rebuild=False)


if __name__ == "__main__":
    unittest.main()
