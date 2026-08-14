from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25490_iana_detail_exact220_transfer as target  # noqa: E402


class V25490IanaDetailExact220TransferTests(unittest.TestCase):
    def test_quality_barrier_and_visible_task_hashes_are_exact(self) -> None:
        self.assertTrue(target._quality_barrier())
        value = target._visible_transfer()
        self.assertEqual(value["task_count"], 220)
        self.assertEqual(value["opaque_id_vector_sha256"], target.OPAQUE_VECTOR_SHA256)
        self.assertEqual(
            value["visible_question_vector_sha256"], target.QUESTION_VECTOR_SHA256
        )

    def test_exact_iana_intervention_has_zero_visible_exposure(self) -> None:
        value = target._visible_transfer()
        self.assertEqual(value["exact_target_schema_tasks"], 0)
        self.assertEqual(value["iana_authority_phrase_tasks"], 0)
        self.assertEqual(value["joint_target_schema_and_authority_tasks"], 0)
        self.assertEqual(value["exact_intervention_reachable_upper_bound_tasks"], 0)
        self.assertEqual(
            value["exact_visible_schema_tasks"]
            + value["empty_exact_visible_schema_tasks"],
            220,
        )

    def test_audit_is_no_effect_no_forward_and_zero_credit(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["transfer_decision"]["fixed_exact220_exact_intervention"], "no_go")
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])
        self.assertTrue(value["authorization"]["generic_row_key_detail_successor_build"])
        self.assertEqual(value["positive_signed_credit_count"], 0)

    def test_resealed_exposure_launch_or_credit_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("exposure", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "exposure":
                changed["visible_transfer"]["exact_target_schema_tasks"] = 1
            elif kind == "launch":
                changed["authorization"]["deepwidebench_forward_or_evaluator"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
