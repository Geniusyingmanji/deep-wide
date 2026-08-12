from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25201_v25199_inactive_post_effect as target  # noqa: E402


class V25201DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.focused_test_result = target._test()

    def test_frozen_artifacts_and_fix_reproduce_exact_root_cause(self) -> None:
        value = target.build_diagnosis(
            now=1,
            require_clean=False,
            focused_test_result=self.focused_test_result,
        )
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertTrue(
            value["root_cause"][
                "inactive_dynamic_zero_has_one_static_parent_post_effect_explanation"
            ]
        )
        self.assertTrue(value["fix"]["focused_tests_passed"])
        self.assertFalse(value["authorization"]["external_forward_or_evaluator_now"])

    def test_incomplete_observation_fails_closed(self) -> None:
        with mock.patch.object(target, "INVARIANT_AGGREGATE_SHA256", "0" * 64), self.assertRaises(RuntimeError):
            target.build_diagnosis(
                now=1,
                require_clean=False,
                focused_test_result=self.focused_test_result,
            )

    def test_resealed_authority_or_credit_tamper_fails(self) -> None:
        value = target.build_diagnosis(
            now=1,
            require_clean=False,
            focused_test_result=self.focused_test_result,
        )
        changed = copy.deepcopy(value)
        changed["authorization"]["external_forward_or_evaluator_now"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.parent_contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
