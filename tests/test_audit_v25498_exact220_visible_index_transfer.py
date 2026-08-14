from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25498_exact220_visible_index_transfer as target  # noqa: E402


class V25498VisibleIndexTransferTests(unittest.TestCase):
    def test_diagnosis_barrier_and_task_hashes_are_exact(self) -> None:
        self.assertTrue(target._diagnosis_barrier())
        exposure = target.visible_exposure()
        self.assertEqual(exposure["task_count"], 220)
        self.assertEqual(
            exposure["opaque_id_vector_sha256"], target.OPAQUE_VECTOR_SHA256
        )
        self.assertEqual(
            exposure["visible_question_vector_sha256"],
            target.QUESTION_VECTOR_SHA256,
        )

    def test_explicit_url_and_source_exposure_is_exact(self) -> None:
        exposure = target.visible_exposure()
        for field, amount in target.EXPECTED_EXPOSURE_COUNTS.items():
            with self.subTest(field=field):
                self.assertEqual(exposure[field], amount)
        self.assertEqual(exposure["exact_visible_schema_tasks"], 194)
        self.assertEqual(exposure["empty_exact_visible_schema_tasks"], 26)
        self.assertEqual(
            exposure[
                "question_only_visible_index_bootstrap_reachable_upper_bound_tasks"
            ],
            0,
        )

    def test_transfer_is_no_go_but_generic_grammar_build_is_authorized(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(
            value["transfer_decision"][
                "explicit_visible_index_bootstrap_for_fixed_exact220"
            ],
            "no_go",
        )
        self.assertFalse(
            value["authorization"][
                "explicit_visible_index_bootstrap_exact220_successor_build"
            ]
        )
        self.assertTrue(
            value["authorization"][
                "generic_parent_and_detail_visible_schema_grammar_build"
            ]
        )
        self.assertFalse(value["authorization"]["new_external_protocol_or_forward"])
        self.assertEqual(value["positive_signed_credit_count"], 0)

    def test_resealed_exposure_launch_or_credit_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in ("exposure", "launch", "credit"):
            changed = copy.deepcopy(value)
            if kind == "exposure":
                changed["visible_transfer"]["explicit_http_url_tasks"] = 1
            elif kind == "launch":
                changed["authorization"]["new_external_protocol_or_forward"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.external.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
