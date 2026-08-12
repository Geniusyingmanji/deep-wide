from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25211_receipt_reliability_gate as target  # noqa: E402


class V25211ReceiptReliabilityGateDesignTests(unittest.TestCase):
    def test_parent_clean_build_audit_is_exactly_bound(self) -> None:
        self.assertTrue(target._parent_barrier())
        self.assertEqual(
            target.parent.base.sha256(target.PARENT_AUDIT),
            target.EXPECTED_PARENT_AUDIT_SHA256,
        )

    def test_population_size_concurrency_and_strata_are_frozen(self) -> None:
        value = target.build_design(now=1)
        self.assertEqual(target.TASK_COUNT, 64)
        self.assertEqual(target.TASKS_PER_STRATUM, 16)
        self.assertEqual(value["population_design"]["risk_strata"], list(target.RISK_STRATA))
        self.assertEqual(value["population_design"]["executor_concurrency"], 32)
        self.assertEqual(value["population_design"]["model_slot_cap"], 32)

    def test_stage_order_and_go_gate_are_strict(self) -> None:
        value = target.build_design(now=1)
        self.assertEqual(
            [row["stage"] for row in value["staged_protocol"]],
            [
                "dual_probe_build",
                "fresh_population_freeze",
                "single_observation_forward",
                "aggregate_disposition_gate",
                "candidate_specific_safe_state_observer",
            ],
        )
        self.assertEqual(
            value["aggregate_go_gate"][
                "minimum_same_parent_identical_violation_vector_count"
            ],
            3,
        )

    def test_design_authorizes_probe_build_only(self) -> None:
        authorization = target.build_design(now=1)["authorization"]
        self.assertTrue(authorization["dual_receipt_failure_probe_build_only"])
        self.assertFalse(authorization["fresh_population_selection_or_external_access"])
        self.assertFalse(authorization["external_forward_or_activation"])
        self.assertFalse(
            authorization["runtime_compatibility_validator_relaxation_or_prediction_change"]
        )
        self.assertFalse(
            authorization["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_resealed_stage_gate_authorization_or_credit_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        for kind in ("stage", "gate", "authorization", "credit", "parent"):
            changed = copy.deepcopy(value)
            if kind == "stage":
                changed["staged_protocol"][0]["stage"] = "compatibility"
            elif kind == "gate":
                changed["aggregate_go_gate"][
                    "minimum_same_parent_identical_violation_vector_count"
                ] = 1
            elif kind == "authorization":
                changed["authorization"]["external_forward_or_activation"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["parent_build_audit"]["sha256"] = "0" * 64
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)


if __name__ == "__main__":
    unittest.main()
