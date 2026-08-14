from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25495_fresh_visible_row_key_population as target  # noqa: E402


class V25495FreshVisibleRowKeyPopulationAuditTests(unittest.TestCase):
    def test_build_barrier_and_frozen_hashes_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(
            all(
                target.base.sha256(path) == digest
                for path, digest in target.FIXED_HASHES.items()
            )
        )

    def test_population_audit_passes_without_detail_or_outcome_access(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["selection"]["identity_count"], 20)
        self.assertFalse(
            value["public_index_structural_observation"][
                "detail_page_or_field_body_opened"
            ]
        )
        self.assertFalse(value["authorization"]["external_forward"])

    def test_task_overlap_is_zero_and_vectors_are_bound(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(value["selection"]["question_overlap_count"], 0)
        self.assertEqual(value["selection"]["opaque_id_overlap_count"], 0)
        self.assertEqual(
            value["selection"]["identity_vector_sha256"],
            target.population.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            value["selection"]["task_vector_sha256"],
            target.population.EXPECTED_TASK_VECTOR_SHA256,
        )

    def test_resealed_detail_quality_launch_or_credit_tamper_fails(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        for kind in ("detail", "quality", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "detail":
                changed["public_index_structural_observation"][
                    "detail_page_or_field_body_opened"
                ] = True
            elif kind == "quality":
                changed["public_index_structural_observation"][
                    "prediction_evaluator_score_quality_or_historical_result_opened"
                ] = True
            elif kind == "launch":
                changed["authorization"]["external_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
