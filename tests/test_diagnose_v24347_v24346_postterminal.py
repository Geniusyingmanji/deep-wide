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

from deepwide_agent.v24346_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24347_v24346_postterminal as target  # noqa: E402


class V24347V24346PostterminalDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1, require_protocol=False)

    def test_exact_terminal_and_effect_strata(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(aggregate["selected_tasks"], 64)
        self.assertEqual(aggregate["effect_complete"]["tasks"], 43)
        self.assertEqual(aggregate["effect_incomplete"]["tasks"], 21)
        self.assertEqual(
            aggregate["fallback_types"], {"ValidationError": 21, "none": 43}
        )

    def test_incomplete_signature_is_not_a_deadline_exhaustion_signature(self) -> None:
        incomplete = self.value["aggregate"]["effect_incomplete"]
        self.assertEqual(incomplete["model_requests"], 42)
        self.assertEqual(incomplete["model_attempts"], 42)
        self.assertEqual(incomplete["slot_acquisitions"], 42)
        self.assertEqual(incomplete["slot_timeouts"], 0)
        self.assertEqual(incomplete["provider_deadline_failures"], 0)
        self.assertEqual(incomplete["deadline_exhausted_tasks"], 0)
        self.assertEqual(incomplete["no_health_event_tasks"], 18)
        self.assertGreater(
            incomplete["remaining_effect_seconds_at_model_receipt"]["minimum"], 40
        )

    def test_duplicate_row_fault_is_reproduced_but_not_parent_attributed(self) -> None:
        matrix = self.value["benchmark_external_validator_fault_matrix"]
        self.assertEqual(matrix["unique_row_identity"], "validation_accepted")
        self.assertEqual(
            matrix["exact_duplicate_row_identity"], "validation_rejected"
        )
        self.assertEqual(
            matrix["normalized_duplicate_row_identity"], "validation_rejected"
        )
        conclusions = self.value["conclusions"]
        self.assertTrue(
            conclusions[
                "duplicate_normalized_row_identity_reproduces_the_same_coarse_validation_class"
            ]
        )
        self.assertFalse(
            conclusions["duplicate_normalized_row_identity_proven_as_parent_cause"]
        )
        self.assertFalse(
            conclusions["exact_validation_subtype_recoverable_from_frozen_artifacts"]
        )

    def test_content_free_and_no_benchmark_authority(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertNotIn("| Entity |", encoded)
        self.assertFalse(self.value["authorization"]["same_run_forward_or_evaluator"])
        self.assertFalse(self.value["authorization"]["additional_dev64"])
        self.assertFalse(self.value["authorization"]["new_exact220"])
        self.assertFalse(self.value["conclusions"]["sota_supported"])

    def test_resealed_authorization_tamper_is_recomputed_and_rejected(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_exact220"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "diagnosis drifted"):
            target.validate_report(ROOT, altered, require_protocol=False)


if __name__ == "__main__":
    unittest.main()
