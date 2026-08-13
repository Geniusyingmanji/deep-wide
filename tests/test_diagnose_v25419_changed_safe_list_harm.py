from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import diagnose_v25419_changed_safe_list_harm as target  # noqa: E402


class V25419ChangedSafeListHarmDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.diagnose(now=1)

    def test_diagnosis_is_valid_and_replays_expected_edit_counts(self) -> None:
        self.assertEqual(target.validate(self.value), self.value)
        self.assertEqual(
            self.value["coordinate_disposition"],
            {"harm": 11, "neutral_correct": 3},
        )
        self.assertEqual(
            self.value["field_coordinate_disposition"]["Authors:harm"], 11
        )

    def test_shared_effect_stage_deltas_are_nonpositive(self) -> None:
        deltas = self.value["same_branch_changed_safe_minus_base"]
        self.assertLess(deltas["v25375_membership_absent"]["quality_composite"], 0)
        self.assertLess(deltas["v25401_membership_present"]["quality_composite"], 0)
        self.assertTrue(
            self.value["checks"][
                "same_branch_base_to_edit_is_shared_effect_causal_boundary"
            ]
        )

    def test_independent_route_branch_delta_is_not_claimed_as_causal(self) -> None:
        self.assertTrue(
            self.value["checks"][
                "route_branch_base_difference_not_treated_as_causal"
            ]
        )

    def test_only_fresh_candidate_gate_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["list_atomic_guard_build"])
        self.assertTrue(authorization["fresh_disjoint_shared_effect_gate_design"])
        self.assertFalse(authorization["reuse_current_population_for_candidate_validation"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])
        self.assertFalse(authorization["entropy_or_signed_credit_claim"])

    def test_tamper_fails_even_when_resealed(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["coordinate_disposition"]["harm"] = 10
        changed.pop("diagnosis_payload_sha256")
        changed = contract.seal(changed, "diagnosis_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate(changed)


if __name__ == "__main__":
    unittest.main()
