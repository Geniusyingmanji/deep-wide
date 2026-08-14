from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25463_date_bounded_official_xml_exact220_transfer as target  # noqa: E402


class V25463DateBoundedOfficialXmlExact220TransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_quality_double_go_is_hash_bound_but_forward_stays_forbidden(self) -> None:
        self.assertEqual(
            target.base.sha256(target.QUALITY_AUDIT),
            target.QUALITY_AUDIT_SHA256,
        )
        self.assertTrue(
            self.value["quality_audit"]["mechanism_and_quality_double_go"]
        )
        self.assertFalse(
            self.value["authorization"]["v25457_exact220_successor_build"]
        )
        self.assertFalse(
            self.value["authorization"]["deepwidebench_forward_or_evaluator"]
        )

    def test_visible_task_vector_has_zero_strict_rfc_request_exposure(self) -> None:
        transfer = self.value["visible_transfer"]
        self.assertEqual(transfer["task_count"], 220)
        self.assertEqual(transfer["strict_rfc_request_exposure_tasks"], 0)
        self.assertEqual(transfer["requested_official_xml_url_count"], 0)
        self.assertEqual(transfer["empty_page_identity_handoff_tasks"], 220)
        self.assertEqual(
            transfer["candidate_specific_prediction_change_reachable_tasks"], 0
        )

    def test_only_aggregate_hashes_and_counts_are_persisted(self) -> None:
        transfer = self.value["visible_transfer"]
        self.assertFalse(
            transfer[
                "question_opaque_id_request_url_prediction_or_per_task_feature_persisted"
            ]
        )
        self.assertNotIn("tasks", transfer)
        self.assertFalse(
            self.value[
                "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertEqual(self.value["positive_signed_credit_count"], 0)

    def test_resealed_exposure_decision_or_authorization_tamper_fails(self) -> None:
        self.assertEqual(target.validate_audit(self.value), self.value)
        for kind in ("exposure", "decision", "authorization"):
            changed = copy.deepcopy(self.value)
            if kind == "exposure":
                changed["visible_transfer"]["strict_rfc_request_exposure_tasks"] = 1
            elif kind == "decision":
                changed["transfer_decision"]["fixed_exact220_candidate_exposure"] = "go"
            else:
                changed["authorization"]["deepwidebench_forward_or_evaluator"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
