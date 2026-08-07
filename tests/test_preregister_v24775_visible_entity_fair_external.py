from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import preregister_v24775_visible_entity_fair_external as target  # noqa: E402


class V24775VisibleEntityFairProtocolTests(unittest.TestCase):
    def test_protocol_binds_fresh_population_runtime_and_visible_only_tasks(self) -> None:
        value = target.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
        self.assertEqual(value["population"]["historical_entity_count"], 4_720)
        self.assertEqual(value["population"]["fresh_entity_count"], 32)
        self.assertEqual(value["population"]["task_count"], 8)
        self.assertEqual(
            value["task_contract"]["runtime_input_keys"],
            ["opaque_id", "question"],
        )
        self.assertEqual(
            value["runtime"]["implementation"],
            "v24770_visible_entity_fair_semantic_unknown_recovery_v1",
        )
        self.assertEqual(value["runtime"]["limits"]["model_calls"], 2)
        self.assertEqual(value["runtime"]["visible_entity_queries"], 4)
        self.assertEqual(value["runtime"]["fetch_target_cap"], 10)

    def test_mechanism_quality_and_entropy_claims_are_separated(self) -> None:
        value = target.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
        mechanism = value["mechanism_gate_before_private_truth"]
        self.assertEqual(mechanism["minimum_changed_task_count"], 2)
        self.assertEqual(mechanism["minimum_changed_cell_count"], 4)
        self.assertEqual(
            mechanism["minimum_projection_backed_support_set_count"], 4
        )
        self.assertEqual(
            mechanism["minimum_entity_slots_with_two_requested_aligned_sources"],
            4,
        )
        self.assertFalse(value["entropy_credit_scope"]["credit_assignment_experiment"])
        self.assertFalse(value["claim_scope"]["deepwidebench_dev64_or_exact220_score"])
        self.assertFalse(value["claim_scope"]["leaderboard_or_sota"])

    def test_publication_authorizes_build_only(self) -> None:
        value = target.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
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

    def test_tamper_fails_closed(self) -> None:
        value = target.build_protocol(
            now=1, require_clean=False, require_pristine=False
        )
        for mutate in (
            lambda item: item["runtime"]["limits"].__setitem__("fetch_targets", 11),
            lambda item: item["task_contract"].__setitem__(
                "runtime_input_keys", ["opaque_id", "question", "category"]
            ),
            lambda item: item["authorization"].__setitem__(
                "one_external_forward_launch", True
            ),
        ):
            changed = copy.deepcopy(value)
            mutate(changed)
            with self.assertRaises(RuntimeError):
                target.validate_protocol(changed)


if __name__ == "__main__":
    unittest.main()
