from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24685_v24679_schema_dev64 as diagnosis  # noqa: E402


class V24685DiagnosisTests(unittest.TestCase):
    def test_live_aggregate_diagnosis_validates(self) -> None:
        value = diagnosis.build_diagnosis(now=0)
        diagnosis.validate_diagnosis(value)
        self.assertEqual(value["diagnosis"]["positive_zero_negative_composite_changed_tasks"], [1, 4, 2])

    def test_no_ids_questions_or_predictions_are_emitted(self) -> None:
        value = diagnosis.build_diagnosis(now=0)
        serialized = diagnosis.json.dumps(value)
        self.assertNotRegex(serialized, r"task_[0-9a-f]{24}")
        self.assertFalse(
            value["source_policy"][
                "contains_opaque_id_question_prediction_instance_id_or_evaluator_row"
            ]
        )

    def test_resealed_exact220_authority_fails_closed(self) -> None:
        value = copy.deepcopy(diagnosis.build_diagnosis(now=0))
        value["claims"]["exact220_authorized"] = True
        value.pop("diagnosis_payload_sha256")
        value["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            diagnosis.validate_diagnosis(value)

    def test_resealed_parser_failure_tamper_fails_closed(self) -> None:
        value = copy.deepcopy(diagnosis.build_diagnosis(now=0))
        value["diagnosis"]["parser_reachability_failure"] = True
        value.pop("diagnosis_payload_sha256")
        value["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(value)
        with self.assertRaises(RuntimeError):
            diagnosis.validate_diagnosis(value)


if __name__ == "__main__":
    unittest.main()
