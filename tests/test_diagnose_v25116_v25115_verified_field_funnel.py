from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25115_schema_recovered_external_recovery_contract as contract  # noqa: E402
from scripts import diagnose_v25116_v25115_verified_field_funnel as target  # noqa: E402


class V25116VerifiedFieldFunnelDiagnosisTests(unittest.TestCase):
    def test_frozen_field_discovery_verification_and_enforcement_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        self.assertEqual(funnel["submitted_column_dispositions"], 54)
        self.assertEqual(funnel["found_column_dispositions"], 11)
        self.assertEqual(funnel["unavailable_column_dispositions"], 43)
        self.assertEqual(funnel["parent_accepted_fields"], 10)
        self.assertEqual(funnel["verifier_exposure_tasks"], 10)
        self.assertEqual(funnel["enforcement_changed_cells"], 0)
        self.assertEqual(funnel["prediction_changed_tasks"], 2)

    def test_changed_predictions_are_abstention_only(self) -> None:
        value = target.build_diagnosis(now=1)
        prediction = value["prediction_structure"]
        self.assertEqual(prediction["changed_tasks"], 2)
        self.assertEqual(prediction["same_table_shape_tasks"], 2)
        self.assertEqual(prediction["cell_changes"], 3)
        self.assertEqual(prediction["fact_to_unknown_changes"], 3)
        self.assertEqual(prediction["unknown_to_fact_changes"], 0)
        self.assertEqual(prediction["fact_to_different_fact_changes"], 0)

    def test_resealed_funnel_direction_credit_or_launch_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("funnel", "direction", "credit", "launch"):
            changed = copy.deepcopy(value)
            if kind == "funnel":
                changed["content_free_funnel"]["found_column_dispositions"] = 12
            elif kind == "direction":
                changed["prediction_structure"]["unknown_to_fact_changes"] = 1
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["authorization"]["new_external_forward"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
