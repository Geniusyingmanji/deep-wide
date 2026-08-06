from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24738_v24737_failure_domain as target  # noqa: E402


class V24738FailureDomainDiagnosisTests(unittest.TestCase):
    def test_actual_diagnosis_quantifies_failure_amplification(self) -> None:
        value = target.build_diagnosis(now=0)
        target.validate_diagnosis(value)
        self.assertEqual(value["transport"]["failures"], 1)
        self.assertEqual(value["propagation"]["nonchanging_tasks"], 12)
        self.assertEqual(
            value["diagnosis"]["next_requirement"],
            "fresh_target_fixed_dual_representation_or_availability_with_target_granular_abstention",
        )
        self.assertFalse(value["authorization"]["same_population_forward_retry_or_rerun"])

    def test_resealed_impact_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=0)
        for path, replacement in (
            (("propagation", "nonchanging_tasks"), 0),
            (("authorization", "evaluator_execution"), True),
        ):
            tampered = copy.deepcopy(value)
            tampered[path[0]][path[1]] = replacement
            tampered.pop("diagnosis_payload_sha256")
            tampered["diagnosis_payload_sha256"] = target.parent.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_diagnosis(tampered)


if __name__ == "__main__":
    unittest.main()
