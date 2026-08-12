from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25252_v25248_shadow_no_go as target  # noqa: E402


class V25252V25248ShadowNoGoDiagnosisTests(unittest.TestCase):
    def test_receipt_lookup_uses_role_not_fixed_depth(self) -> None:
        expected = {"role": target.SPARSE_RECEIPT_ROLE, "safe": 1}
        nested = {
            "content_free_receipt": {"role": "other"},
            "parent_result": {
                "parent_result": {"content_free_receipt": expected}
            },
        }
        self.assertEqual(target._receipt_by_role(nested, target.SPARSE_RECEIPT_ROLE), expected)

    def test_real_frozen_diagnosis_is_content_free_and_exact(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        diagnosis = value["diagnosis"]
        self.assertEqual(diagnosis["completed_runtime_tasks"], 63)
        self.assertEqual(diagnosis["tasks_exceeding_declared_model3_or_fetch10"], 3)
        self.assertEqual(diagnosis["overshoot_final_prediction_changed_from_production_tasks"], 0)
        self.assertEqual(diagnosis["header_totality_shadow_entry_tasks"], 0)
        self.assertTrue(value["conclusions"]["value_error_exact_post_effect_stage_remains_unidentified"])
        self.assertFalse(value["authorization"]["fresh_external_protocol_design"])

    def test_resealed_external_launch_credit_or_count_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("launch", "credit", "count"):
            changed = copy.deepcopy(value)
            if kind == "launch":
                changed["authorization"]["fresh_external_protocol_design"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["diagnosis"]["tasks_exceeding_declared_model3_or_fetch10"] = 2
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_does_not_import_or_call_evaluator(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("import evaluation", source)


if __name__ == "__main__":
    unittest.main()
