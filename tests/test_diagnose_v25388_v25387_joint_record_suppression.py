from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25388_v25387_joint_record_suppression as target  # noqa: E402


class V25388JointRecordSuppressionDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_funnel_locates_joint_record_suppression(self) -> None:
        funnel = self.value["content_free_funnel"]
        self.assertEqual(funnel["task_count"], 20)
        self.assertEqual(funnel["joint_envelope_exact_tasks"], 20)
        self.assertEqual(funnel["grounded_record_member_nonempty_tasks"], 8)
        self.assertEqual(funnel["grounded_record_count_total"], 11)
        self.assertEqual(funnel["joint_record_member_nonempty_tasks"], 0)
        self.assertEqual(funnel["joint_record_count_total"], 0)

    def test_only_build_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["hybrid_joint_or_grounded_record_fallback_build_only"]
        )
        self.assertFalse(authorization["new_external_forward"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])
        self.assertFalse(self.value["entropy_or_information_gain_assigns_signed_credit"])

    def test_resealed_count_credit_or_launch_tamper_fails(self) -> None:
        for kind in ("count", "credit", "launch"):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["content_free_funnel"]["grounded_record_count_total"] += 1
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["authorization"]["new_external_forward"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_bindings_are_exact(self) -> None:
        self.assertEqual(
            self.value["source_bindings"],
            {str(path): expected for path, expected in target.FIXED_HASHES.items()},
        )


if __name__ == "__main__":
    unittest.main()
