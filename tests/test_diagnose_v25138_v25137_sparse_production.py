from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25137_sparse_production_external_contract as contract  # noqa: E402
from scripts import diagnose_v25138_v25137_sparse_production as target  # noqa: E402


class V25138DiagnosisTests(unittest.TestCase):
    def test_frozen_counts_only_revision_funnel(self) -> None:
        value = target.build_diagnosis(now=1)
        funnel = value["content_free_funnel"]
        self.assertEqual(funnel["task_count"], 20)
        self.assertEqual(
            funnel["target_field_page_gain_histogram"],
            {"-1": 1, "0": 13, "1": 6},
        )
        self.assertEqual(
            funnel["target_field_pair_gain_histogram"],
            {"-1": 1, "0": 13, "1": 5, "2": 1},
        )
        self.assertEqual(
            funnel["complete_target_field_page_gain_histogram"], {"0": 20}
        )
        self.assertEqual(funnel["verified_gain_tasks"], 6)
        self.assertEqual(funnel["revision_provider_valid_tasks"], 6)
        self.assertEqual(funnel["revision_changed_prediction_tasks"], 1)
        self.assertEqual(funnel["revision_unchanged_prediction_tasks"], 5)
        self.assertEqual(funnel["identity_replay_tasks"], 14)

    def test_scanner_decodes_only_explicit_content_free_members(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        safe = target.safe_row(line)
        self.assertEqual(set(safe), set(target.SAFE_MEMBERS))
        self.assertNotIn("opaque_id", safe)
        self.assertNotIn("predictions", safe)
        self.assertNotIn("parent_result", safe)

    def test_source_contract_proves_revision_did_not_receive_production_table(self) -> None:
        value = target.build_diagnosis(now=1)
        source = value["revision_source_contract"]
        self.assertTrue(source["single_revision_provider_forward_site"])
        self.assertTrue(source["inherited_candidate_synthesis_user_forwarded_verbatim"])
        self.assertFalse(source["production_prediction_inserted_into_revision_prompt"])
        self.assertFalse(source["revision_user_argument_mutated_before_provider_forward"])

    def test_parent_hashes_and_closed_evaluator_surface_are_bound(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(
            set(value["parents"]),
            {
                "forward_result_sha256",
                "forward_audit_sha256",
                "prediction_freeze_sha256",
                "task_rows_sha256",
                "runtime_source_sha256",
                "audit_valid",
                "mechanism_gate_passed",
                "failed_checks",
            },
        )
        self.assertFalse(value["authorization"]["v25137_evaluator_or_quality_result"])
        self.assertTrue(all(target._absent(path) for path in target.FUTURE_SURFACES))

    def test_resealed_funnel_credit_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("funnel", "credit", "external", "quality"):
            changed = copy.deepcopy(value)
            if kind == "funnel":
                changed["content_free_funnel"]["revision_changed_prediction_tasks"] = 2
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            elif kind == "external":
                changed["authorization"]["new_fresh_disjoint_external_protocol_or_launch"] = True
            else:
                changed["authorization"]["v25137_evaluator_or_quality_result"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)

    def test_row_schema_addition_fails_closed_without_decoding_value(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        value = json.loads(line)
        value["unexpected"] = "must-not-be-accepted"
        with self.assertRaises(ValueError):
            target.safe_row(json.dumps(value, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
