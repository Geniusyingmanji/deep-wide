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

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from scripts import diagnose_v25264_v25260_observed_reliability as target  # noqa: E402


class V25264ObservedReliabilityDiagnosisTests(unittest.TestCase):
    def test_frozen_content_free_health_diagnosis(self) -> None:
        value = target.build_diagnosis(now=1)
        aggregate = value["aggregate"]
        self.assertEqual(aggregate["fixed_task_denominator"], 64)
        self.assertEqual(aggregate["runtime_completed_tasks"], 64)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 0)
        self.assertEqual(aggregate["tasks_with_any_health_event"], 3)
        self.assertEqual(
            aggregate["terminal_effect_health_totals"]["search_transport_failures"], 3
        )
        self.assertEqual(aggregate["affected_task_effect_totals"]["fetch_calls"], 31)
        self.assertEqual(aggregate["affected_task_effect_totals"]["model_provider_successes"], 10)
        self.assertTrue(value["conclusions"]["fresh64_proves_totality_and_physical_caps_not_answer_quality"])

    def test_scanner_never_materializes_identity_question_page_or_prediction(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        safe = target.safe_row(line)
        self.assertEqual(set(safe), set(target.SAFE_MEMBERS))
        for forbidden in ("opaque_id", "prediction", "runtime_result", "question", "pages"):
            self.assertNotIn(forbidden, safe)

    def test_parent_hashes_and_authority_are_frozen(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(value["parents"], target.EXPECTED_SHA256)
        self.assertTrue(value["authorization"]["build_exact220_totality_successor_from_verified_shell"])
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertFalse(value["authorization"]["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"])

    def test_resealed_health_credit_quality_or_retry_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("health", "credit", "quality", "retry", "conclusion"):
            changed = copy.deepcopy(value)
            if kind == "health":
                changed["aggregate"]["terminal_effect_health_totals"]["model_request_failures"] = 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "quality":
                changed["authorization"]["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"] = True
            elif kind == "retry":
                changed["authorization"]["retry_resume_reuse_replacement_or_selective_rerun_of_v25260"] = True
            else:
                changed["conclusions"]["fresh64_proves_totality_and_physical_caps_not_answer_quality"] = False
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_added_row_member_fails_closed_without_decoding_its_value(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.TASK_ROWS).read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        value = json.loads(line)
        value["unexpected"] = {"question_type": "must-not-be-accepted"}
        with self.assertRaises(ValueError):
            target.safe_row(json.dumps(value, ensure_ascii=False, separators=(",", ":")))

    def test_source_has_no_evaluator_or_network_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("requests.", source)
        self.assertNotIn("urlopen", source)


if __name__ == "__main__":
    unittest.main()
