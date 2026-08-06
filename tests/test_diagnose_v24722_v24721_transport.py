from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24722_v24721_transport as target  # noqa: E402


class V24722TransportDiagnosisTests(unittest.TestCase):
    def test_actual_diagnosis_is_content_free_and_no_go(self) -> None:
        value = target.build_diagnosis(now=0)
        target.validate_diagnosis(value)
        self.assertEqual(value["transport"]["primary_successes"], 9)
        self.assertEqual(value["transport"]["comparator_successes"], 12)
        self.assertEqual(value["representation"]["joint_common_value_mismatch_total"], 0)
        self.assertFalse(value["diagnosis"]["same_population_retry_or_rerun_authorized"])
        self.assertFalse(value["authorization"]["benchmark_dev64_or_exact220"])

    def test_resealed_count_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=0)
        for path, replacement in (
            (("transport", "primary_successes"), 12),
            (("authorization", "same_population_transport_retry_or_rerun"), True),
        ):
            tampered = copy.deepcopy(value)
            tampered[path[0]][path[1]] = replacement
            tampered.pop("diagnosis_payload_sha256")
            tampered["diagnosis_payload_sha256"] = target.parent.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_diagnosis(tampered)


if __name__ == "__main__":
    unittest.main()
