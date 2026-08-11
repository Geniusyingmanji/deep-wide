from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25078_anchor_bounded_external_contract as contract  # noqa: E402
from scripts import diagnose_v25079_v25078_anchor_bounded_external as target  # noqa: E402


class V25079DiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        upstream = funnel["upstream_record_projection"]
        diagnosis = value["diagnosis"]
        self.assertEqual(value["aggregate"]["terminal_tasks"], 20)
        self.assertEqual(value["aggregate"]["verifier_exposure_tasks"], 0)
        self.assertEqual(value["aggregate"]["prediction_changed_tasks"], 5)
        self.assertEqual(funnel["query_local_mapping_failure_rows"], 42)
        self.assertEqual(funnel["terminal_hard_failure_total"], 0)
        self.assertEqual(funnel["proposal_empty_tasks"], 19)
        self.assertEqual(funnel["proposal_nonempty_tasks"], 1)
        self.assertEqual(funnel["parsed_records"], 1)
        self.assertEqual(funnel["verified_records"], 0)
        self.assertEqual(upstream["wave_count"], 40)
        self.assertTrue(all(value == 0 for name, value in upstream.items() if name != "wave_count"))
        self.assertTrue(diagnosis["observed_bottleneck_is_page_identity_to_record_conversion_not_transport"])
        self.assertFalse(value["authorization"]["v25078_evaluator_or_quality_result"])

    def test_parent_hashes_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {"forward_result_sha256", "forward_audit_sha256", "task_rows_sha256"},
        )
        self.assertTrue(all(len(value["parents"][name]) == 64 for name in value["parents"]))

    def test_resealed_evaluator_credit_or_funnel_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("evaluator", "credit", "empty", "upstream"):
            changed = copy.deepcopy(value)
            if kind == "evaluator":
                changed["authorization"]["v25078_evaluator_or_quality_result"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "empty":
                changed["content_free_funnel"]["proposal_empty_tasks"] = 18
            else:
                changed["content_free_funnel"]["upstream_record_projection"][
                    "fetch_projector_discovered_records"
                ] = 1
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
