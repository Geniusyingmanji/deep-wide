from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import (  # noqa: E402
    diagnose_v24479_v24478_post_effect_validation as target,
)


class V24479V24478PostEffectValidationDiagnosisTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: ""
                if args == ("status", "--porcelain")
                else "a" * 40,
            ),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            value = target.build_report(now=0)
        target.validate_report(value)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        return value

    def test_public_receipts_localize_the_bounded_timeout(self) -> None:
        observed = self.build_valid()["public_observation"]
        self.assertEqual(observed["worker_hard_timeout_tasks"], 8)
        self.assertEqual(observed["worker_success_tasks"], 0)
        self.assertTrue(observed["all_recorded_network_effect_starts_equal_finishes"])
        self.assertEqual(observed["complete_validation_entered_tasks"], 1)
        self.assertEqual(observed["complete_validation_returned_tasks"], 0)
        self.assertEqual(
            observed["last_stage_counts"],
            {
                "adaptive_support_entered": 6,
                "complete_validation_entered": 1,
                "public_fetch_effect_finished": 1,
            },
        )

    def test_profile_is_synthetic_and_quantifies_local_replay(self) -> None:
        profile = self.build_valid()["synthetic_profile"]
        self.assertEqual(profile["profiled_test_total_calls"], 1)
        self.assertEqual(
            profile["validate_result_aggregate"]["total_calls"], 11_303
        )
        self.assertEqual(profile["deepcopy_total_calls"], 16_788_412)
        self.assertEqual(profile["payload_sha256_total_calls"], 574_063)
        self.assertTrue(profile["profile_has_instrumentation_overhead"])
        self.assertTrue(profile["profile_is_not_external_latency_estimate"])
        self.assertFalse(profile["benchmark_or_external_task_content_used"])

    def test_budget_design_is_hypothesis_not_launch_authority(self) -> None:
        value = self.build_valid()
        budget = value["budget_evidence"]
        self.assertEqual(budget["frozen_local_closure_reserve_seconds"], 25.0)
        self.assertGreater(
            budget["unprofiled_synthetic_full_chain_suite_seconds"], 25.0
        )
        self.assertEqual(budget["design_worker_timeout_seconds"], 220.0)
        self.assertEqual(budget["design_parent_timeout_seconds"], 245.0)
        self.assertTrue(
            budget["design_values_are_local_successor_hypotheses_not_launch_authority"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_causal_limit_and_population_ban_are_explicit(self) -> None:
        diagnosis = self.build_valid()["diagnosis"]
        self.assertFalse(diagnosis["private_v24478_traceback_or_per_task_timing_available"])
        self.assertFalse(diagnosis["local_replay_is_proven_as_unique_v24478_timeout_cause"])
        self.assertFalse(diagnosis["profile_is_external_latency_estimate"])
        self.assertFalse(diagnosis["same_v24478_population_rerun_allowed"])

    def test_resealed_launch_rerun_or_causal_overclaim_fails(self) -> None:
        cases = (
            (
                "launch",
                lambda value: value["authorization"].__setitem__(
                    "external_probe_launch", True
                ),
            ),
            (
                "rerun",
                lambda value: value["authorization"].__setitem__(
                    "same_v24478_population_rerun", True
                ),
            ),
            (
                "causal",
                lambda value: value["diagnosis"].__setitem__(
                    "local_replay_is_proven_as_unique_v24478_timeout_cause", True
                ),
            ),
            (
                "latency",
                lambda value: value["diagnosis"].__setitem__(
                    "profile_is_external_latency_estimate", True
                ),
            ),
        )
        for name, alter in cases:
            with self.subTest(name=name):
                value = copy.deepcopy(self.build_valid())
                alter(value)
                value.pop("diagnosis_payload_sha256")
                value["diagnosis_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_report(value)

    def test_source_surface_has_no_credential_literal(self) -> None:
        for path in target.SOURCES:
            self.assertIsNone(
                target.SECRET.search(
                    target.base._ordinary(path).read_text(encoding="utf-8")
                )
            )


if __name__ == "__main__":
    unittest.main()
