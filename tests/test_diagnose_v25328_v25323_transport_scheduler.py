from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25328_v25323_transport_scheduler as target  # noqa: E402


class V25328TransportSchedulerDiagnosisTests(unittest.TestCase):
    def test_diagnosis_replays_exact_two_attempt_failure_patterns(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["before_v25317"]["failed_target_response_count"], 12)
        self.assertEqual(value["after_v25323"]["failed_target_response_count"], 5)
        self.assertEqual(
            value["after_v25323"]["failed_ordinal_pages"],
            [[22, 1], [22, 2], [23, 2], [24, 1], [24, 2]],
        )

    def test_consumed_manifest_is_exact72_144_127(self) -> None:
        value = target._manifest()
        self.assertTrue(all(value["checks"].values()))
        self.assertEqual(value["target_count"], 72)
        self.assertEqual(value["entity_count"], 144)
        self.assertEqual(value["response_count"], 127)
        self.assertEqual(value["per_attempt_response_counts"], [48, 36, 43])

    def test_scheduler_diagnosis_is_bounded_not_false_causal_proof(self) -> None:
        value = target.build_diagnosis(now=1)
        diagnosis = value["diagnosis"]
        self.assertTrue(
            diagnosis["pattern_is_consistent_with_burst_or_connection_rate_capacity"]
        )
        self.assertFalse(diagnosis["pattern_proves_unique_causal_root_cause"])
        self.assertTrue(
            diagnosis["next_candidate_changes_only_transport_start_scheduling"]
        )
        self.assertEqual(
            diagnosis["next_candidate_minimum_request_start_interval_seconds"], 1.0
        )
        self.assertFalse(
            diagnosis["next_candidate_retry_resume_refetch_backfill_replacement"]
        )

    def test_resealed_manifest_scheduler_or_authority_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("target", "response", "scheduler", "retry", "launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "target":
                changed["consumed_manifest"]["target_count"] = 71
            elif kind == "response":
                changed["consumed_manifest"]["response_count"] = 126
            elif kind == "scheduler":
                changed["diagnosis"]["next_candidate_minimum_request_start_interval_seconds"] = 0.0
            elif kind == "retry":
                changed["diagnosis"]["next_candidate_retry_resume_refetch_backfill_replacement"] = True
            elif kind == "launch":
                changed["authorization"]["successor_population_network_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.current.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_diagnosis_has_no_live_effect_constructor_or_content_emit(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "question_text",
            "query_text",
            "page_content",
            "prediction_text",
            "credential_value",
            "requests.",
            "urlopen(",
            "run_official_eval_local",
            "AzureNativeSearchClient(",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
