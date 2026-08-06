from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import project_v24718_identity_full220_result as projector  # noqa: E402


class V24718IdentityFull220ResultTests(unittest.TestCase):
    def test_actual_predictions_are_complete_identity(self) -> None:
        value = projector.prediction_identity()
        self.assertTrue(value["identity_complete"])
        self.assertEqual(value["same_prediction_bytes_tasks"], 220)
        self.assertEqual(value["different_prediction_tasks"], 0)

    def test_control_result_and_forward_nogo_are_valid(self) -> None:
        self.assertEqual(projector._control_valid()["metrics"]["whole_table_successes"], 7)
        self.assertFalse(projector._forward_nogo_valid()["audit_valid"])

    def test_validation_requires_zero_new_evaluator_calls_and_no_improvement(self) -> None:
        value = {
            "role": "v24718_v24714_identity_full220_result",
            "selected": 220,
            "identity": {"identity_complete": True, "same_prediction_bytes_tasks": 220},
            "metrics": {"whole_table_successes": 7, "score": 7 / 220},
            "evaluation": {"new_evaluator_calls": 0, "historical_rows_reused": 220},
            "claims": {"benchmark_improvement": False, "sota": False},
            "authorization": {"additional_evaluator_or_revaluation": False},
        }
        value["result_payload_sha256"] = projector.contract.payload_sha256(value)
        projector.validate_result(value)
        for path, replacement in (
            (("evaluation", "new_evaluator_calls"), 1),
            (("claims", "benchmark_improvement"), True),
            (("claims", "sota"), True),
        ):
            tampered = copy.deepcopy(value)
            tampered[path[0]][path[1]] = replacement
            tampered.pop("result_payload_sha256")
            tampered["result_payload_sha256"] = projector.contract.payload_sha256(tampered)
            with self.assertRaisesRegex(RuntimeError, "drifted"):
                projector.validate_result(tampered)

    def test_nonidentity_fails_before_control_projection(self) -> None:
        with (
            patch.object(
                projector,
                "prediction_identity",
                return_value={"identity_complete": False},
            ),
            patch.object(projector, "_git", side_effect=lambda *args: "" if args[0] == "status" else "a" * 40),
            patch.object(projector, "_control_valid") as control,
        ):
            with self.assertRaisesRegex(RuntimeError, "not prediction-identical"):
                projector.build_result(now=0)
        control.assert_not_called()


if __name__ == "__main__":
    unittest.main()
