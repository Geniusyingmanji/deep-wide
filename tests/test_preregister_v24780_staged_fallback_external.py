from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24780_staged_fallback_external as target  # noqa: E402


class V24780StagedFallbackProtocolTests(unittest.TestCase):
    def protocol(self):
        return target.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )

    def test_protocol_binds_fresh_population_and_staged_runtime(self) -> None:
        value = self.protocol()
        self.assertEqual(value["population"]["historical_entity_count"], 4_752)
        self.assertEqual(value["population"]["fresh_entity_count"], 32)
        self.assertEqual(value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])
        runtime = value["runtime"]
        self.assertEqual(
            runtime["implementation"],
            "v24778_staged_visible_entity_fetch_fallback_v1",
        )
        self.assertEqual(runtime["initial_fetch_cap_per_task"], 8)
        self.assertEqual(runtime["conditional_reserve_fetch_cap_per_task"], 2)
        self.assertEqual(runtime["maximum_physical_fetches_per_task"], 10)
        self.assertEqual(runtime["failed_url_retry_cap_per_task"], 0)
        self.assertFalse(runtime["semantic_projector_changed_from_v24775"])

    def test_mechanism_gate_requires_reserve_and_safe_change(self) -> None:
        gate = self.protocol()["mechanism_gate_before_private_truth"]
        self.assertEqual(gate["minimum_changed_task_count"], 1)
        self.assertEqual(gate["minimum_changed_cell_count"], 1)
        self.assertEqual(gate["minimum_projection_backed_support_set_count"], 1)
        self.assertEqual(gate["minimum_reserve_fetch_request_count"], 1)
        self.assertEqual(gate["minimum_reserve_usable_page_count"], 1)
        self.assertEqual(
            gate["minimum_entity_slots_brought_to_two_sources_by_reserve"], 1
        )
        self.assertFalse(
            gate["reserve_coverage_and_safe_change_joint_activation_is_causal_proof"]
        )

    def test_credit_quality_and_benchmark_claims_remain_closed(self) -> None:
        value = self.protocol()
        self.assertFalse(value["entropy_credit_scope"]["credit_assignment_experiment"])
        self.assertFalse(value["entropy_credit_scope"]["coverage_gain_is_positive_credit"])
        self.assertFalse(value["claim_scope"]["deepwidebench_dev64_or_exact220_score"])
        self.assertFalse(value["claim_scope"]["leaderboard_or_sota"])
        authorization = value["authorization"]
        self.assertTrue(authorization["runner_or_control_plane_build"])
        for key in (
            "package_audit_generation",
            "preactivation_audit_generation",
            "activation",
            "execution_start",
            "one_external_forward_launch",
            "quality_surface_open",
            "paired_dev64",
            "exact220",
            "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[key])

    def test_resealed_tamper_fails_closed(self) -> None:
        value = self.protocol()
        mutations = (
            lambda item: item["runtime"].__setitem__(
                "maximum_physical_fetches_per_task", 11
            ),
            lambda item: item["runtime"].__setitem__(
                "reserve_routing_uses_field_candidate_value_or_model_judgment", True
            ),
            lambda item: item["mechanism_gate_before_private_truth"].__setitem__(
                "minimum_reserve_usable_page_count", 0
            ),
            lambda item: item["authorization"].__setitem__(
                "one_external_forward_launch", True
            ),
        )
        for mutate in mutations:
            changed = copy.deepcopy(value)
            mutate(changed)
            changed["protocol_payload_sha256"] = target.payload_sha256(
                {
                    key: current
                    for key, current in changed.items()
                    if key != "protocol_payload_sha256"
                }
            )
            with self.assertRaises(RuntimeError):
                target.validate_protocol(changed)


if __name__ == "__main__":
    unittest.main()
