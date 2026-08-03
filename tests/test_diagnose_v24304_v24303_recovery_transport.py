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

from scripts import diagnose_v24304_v24303_recovery_transport as target  # noqa: E402


class V24304RecoveryTransportDiagnosisTests(unittest.TestCase):
    def test_recomputes_recovery_failures_and_provider_retries(self) -> None:
        value = target.build_report(ROOT, now=1)
        target.validate_report(ROOT, value)
        recovery = value["recovery_transport"]
        self.assertEqual(recovery["success_positions"], [4, 13, 18, 19])
        self.assertEqual(recovery["failure_positions"], [2, 14, 20])
        self.assertEqual(recovery["failure_provider_attempts"], [5, 5, 6])
        self.assertTrue(recovery["all_failures_had_provider_internal_retries"])

    def test_capacity_evidence_supports_cap2_without_causal_overclaim(self) -> None:
        value = target.build_report(ROOT, now=1)
        capacity = value["concurrency_evidence"]
        self.assertTrue(capacity["v24262_cap2"]["passed"])
        self.assertFalse(capacity["v24262_cap4"]["passed"])
        self.assertFalse(capacity["cap8_caused_v24303_failures_proven"])
        self.assertTrue(capacity["cap2_is_best_supported_next_transport_setting"])
        self.assertFalse(
            value["recovery_transport"]["failure_burst_clustering_identifiable"]
        )

    def test_evaluator_errors_are_taxonomized_without_revaluation(self) -> None:
        value = target.build_report(ROOT, now=1)
        health = value["evaluator_health"]
        self.assertEqual(health["baseline"]["invalid_positions"], [4, 56])
        self.assertEqual(health["candidate"]["invalid_positions"], [4, 42, 50])
        self.assertEqual(
            health["candidate"]["taxonomy"],
            {"official_evaluator_internal_error": 3},
        )
        self.assertFalse(health["candidate"]["selective_revaluation_performed"])

    def test_report_is_content_free_and_does_not_authorize_benchmark(self) -> None:
        value = target.build_report(ROOT, now=1)
        encoded = json.dumps(value)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertFalse(value["authorization"]["additional_dev64"])
        self.assertFalse(value["authorization"]["exact220"])
        self.assertFalse(value["authorization"]["evaluator_call"])

    def test_resealed_tamper_is_recomputed_and_rejected(self) -> None:
        value = target.build_report(ROOT, now=1)
        altered = copy.deepcopy(value)
        altered["conclusions"]["exact220_authorized"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
