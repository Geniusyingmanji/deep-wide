from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25321_v25317_transport_capacity as target  # noqa: E402


class V25321TransportCapacityDiagnosisTests(unittest.TestCase):
    def test_diagnosis_replays_exact_content_free_failure_pattern(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(target.validate_diagnosis(value), value)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["aggregate"]["successful_target_response_count"], 36)
        self.assertEqual(value["aggregate"]["failed_target_response_count"], 12)
        self.assertEqual(
            value["aggregate"]["failed_ordinal_pages"],
            [[ordinal, page] for ordinal in range(7, 13) for page in (1, 2)],
        )

    def test_static_transport_barrier_is_exact(self) -> None:
        self.assertTrue(all(target._static_transport_barrier().values()))

    def test_diagnosis_is_bounded_not_false_causal_proof(self) -> None:
        value = target.build_diagnosis(now=1)
        diagnosis = value["diagnosis"]
        self.assertTrue(
            diagnosis[
                "pattern_is_consistent_with_transient_burst_or_connection_capacity"
            ]
        )
        self.assertFalse(diagnosis["pattern_proves_unique_causal_root_cause"])
        self.assertEqual(diagnosis["next_candidate_target_concurrency"], 6)
        self.assertEqual(diagnosis["per_url_provider_attempt_count"], 1)
        self.assertFalse(diagnosis["retry_resume_refetch_backfill_replacement"])

    def test_resealed_diagnosis_or_authority_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("causal", "concurrency", "retry", "reuse", "launch", "credit", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "causal":
                changed["diagnosis"]["pattern_proves_unique_causal_root_cause"] = True
            elif kind == "concurrency":
                changed["diagnosis"]["next_candidate_target_concurrency"] = 12
            elif kind == "retry":
                changed["diagnosis"]["retry_resume_refetch_backfill_replacement"] = True
            elif kind == "reuse":
                changed["diagnosis"]["must_not_reuse_v25317_partial_success_bytes"] = False
            elif kind == "launch":
                changed["authorization"]["successor_population_network_activation_or_launch"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.runner.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_diagnosis_has_no_live_effect_constructor_or_content_emit(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "requests.",
            "urlopen(",
            "AzureNativeSearchClient(",
            "HardTotalWallResponsesClient(",
            "run_official_eval_local",
            "question_text",
            "page_content",
            "prediction_text",
            "credential_value",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
