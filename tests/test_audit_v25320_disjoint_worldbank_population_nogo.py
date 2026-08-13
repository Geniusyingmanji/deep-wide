from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25320_disjoint_worldbank_population_nogo as target  # noqa: E402


class V25320DisjointWorldBankPopulationNogoTests(unittest.TestCase):
    def test_replay_validates_claim_result_catalog_and_success_bytes(self) -> None:
        value = target._replay()
        self.assertTrue(value["catalog_bound"])
        self.assertTrue(value["response_binding_valid"])
        self.assertEqual(len(value["successful"]), 36)
        self.assertEqual(len(value["failed"]), 12)
        self.assertEqual(len(value["expected_success_paths"]), 36)

    def test_build_audit_is_valid_nogo_with_all_successor_authority_false(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["attempt"]["decision"], "no_go")
        self.assertEqual(value["attempt"]["successful_target_response_count"], 36)
        self.assertEqual(value["attempt"]["failed_target_response_count"], 12)
        self.assertFalse(value["authorization"]["external_monotone_fill_protocol_or_forward"])
        self.assertFalse(value["authorization"]["postfreeze_evaluator"])
        self.assertFalse(value["authorization"]["reuse_successful_partial_responses_for_population_or_successor"])

    def test_resealed_attempt_population_or_authority_tamper_fails(self) -> None:
        value = target.build_audit(now=1)
        for kind in (
            "attempt",
            "failure",
            "population",
            "reuse",
            "forward",
            "credit",
            "hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "attempt":
                changed["attempt"]["successful_target_response_count"] = 37
            elif kind == "failure":
                changed["attempt"]["failed_ordinal_pages"][0] = [1, 1]
            elif kind == "population":
                changed["population"]["task_count"] = 1
            elif kind == "reuse":
                changed["authorization"]["reuse_successful_partial_responses_for_population_or_successor"] = True
            elif kind == "forward":
                changed["authorization"]["external_monotone_fill_protocol_or_forward"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_partial_successes_are_not_population_or_quality_evidence(self) -> None:
        value = target.build_audit(now=1)
        self.assertEqual(value["population"]["selected_target_count"], 0)
        self.assertEqual(value["population"]["entity_count"], 0)
        self.assertEqual(value["population"]["task_count"], 0)
        self.assertFalse(value["population"]["private_population_exists"])
        self.assertFalse(value["authorization"]["postfreeze_evaluator"])

    def test_auditor_emits_no_content_or_credential(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "question_text",
            "page_content",
            "prediction_text",
            "credential_value",
            "run_official_eval_local",
            "AzureNativeSearchClient(",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
