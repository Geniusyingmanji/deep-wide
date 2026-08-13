from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25394_v25393_hybrid_row_overlap as target  # noqa: E402


class V25394HybridRowOverlapDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_funnel_is_exhaustive_and_locates_row_overlap(self) -> None:
        funnel = self.value["content_free_funnel"]
        self.assertEqual(funnel["grounded_source_tasks"], 9)
        self.assertEqual(funnel["verified_record_tasks"], 9)
        self.assertEqual(funnel["verified_field_count_total"], 27)
        self.assertEqual(funnel["missing_row_rejected_field_count_total"], 10)
        self.assertEqual(funnel["unchanged_verified_coordinate_count_total"], 11)
        self.assertEqual(funnel["changed_safe_coordinate_count_total"], 6)
        self.assertEqual(funnel["verified_field_disposition_total"], 27)
        self.assertTrue(funnel["verified_field_disposition_is_exhaustive"])

    def test_only_pre_synthesis_verified_row_build_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["pre_synthesis_verified_row_constraint_build_only"]
        )
        self.assertFalse(authorization["new_external_forward"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])
        self.assertFalse(
            self.value["entropy_or_information_gain_assigns_signed_credit"]
        )

    def test_resealed_count_credit_or_launch_tamper_fails(self) -> None:
        for kind in ("count", "credit", "launch"):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["content_free_funnel"][
                    "missing_row_rejected_field_count_total"
                ] += 1
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["authorization"]["new_external_forward"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = (
                target.contract.payload_sha256(changed)
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_bindings_are_exact(self) -> None:
        self.assertEqual(
            self.value["source_bindings"],
            {
                str(path): expected
                for path, expected in target.FIXED_HASHES.items()
            },
        )


if __name__ == "__main__":
    unittest.main()
