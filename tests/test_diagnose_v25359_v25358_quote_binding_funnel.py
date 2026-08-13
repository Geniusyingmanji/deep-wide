from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25359_v25358_quote_binding_funnel as target  # noqa: E402


class V25359DiagnosisTests(unittest.TestCase):
    def test_content_free_funnel_is_valid_and_build_only(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        funnel = value["content_free_funnel"]
        self.assertEqual(funnel["completed_runtime_tasks"], 20)
        self.assertEqual(funnel["rejected_field_binding_records"], 11)
        self.assertEqual(funnel["verified_quote_records"], 0)
        self.assertTrue(
            value["authorization"]["per_field_quote_verifier_build_only_design"]
        )
        self.assertFalse(
            value["authorization"]["new_external_forward_or_evaluator"]
        )

    def test_resealed_rerun_or_external_authority_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("rerun", "external"):
            changed = copy.deepcopy(value)
            if kind == "rerun":
                changed["authorization"][
                    "same_population_retry_resume_replay_backfill_or_replacement"
                ] = True
            else:
                changed["authorization"]["new_external_forward_or_evaluator"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
