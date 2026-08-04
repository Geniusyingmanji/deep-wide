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
from scripts import diagnose_v24467_v24466_total_wall as target  # noqa: E402


PROBE = {
    "scope": "ephemeral_127_0_0_1_slow_drip_http_only",
    "configured_total_deadline_seconds": 0.35,
    "configured_cleanup_reserve_seconds": 0.1,
    "configured_initial_effect_window_seconds": 0.25,
    "drip_interval_seconds": 0.012,
    "model": {
        "elapsed_seconds": 1.0,
        "returned_success": True,
        "remaining_effect_seconds_after_return": 0.0,
        "returned_after_total_deadline": True,
    },
    "hosted_search": {
        "elapsed_seconds": 1.2,
        "returned_success": True,
        "remaining_effect_seconds_after_return": 0.0,
        "returned_after_total_deadline": True,
    },
    "both_returned_success_after_total_deadline": True,
    "external_network_model_search_fetch_or_evaluator_called": False,
    "benchmark_task_or_private_content_used": False,
}


class V24467V24466TotalWallDiagnosisTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target, "_slow_drip_probe", return_value=PROBE),
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
        return value

    def test_real_parent_closure_preserves_unidentifiable_stage(self) -> None:
        value = self.build_valid()
        observed = value["public_observation"]
        diagnosis = value["diagnosis"]
        self.assertEqual(observed["parent_hard_timeout_tasks"], 8)
        self.assertEqual(observed["failure_snapshot_tasks"], 0)
        self.assertEqual(observed["unobserved_effect_tasks"], 8)
        self.assertEqual(observed["terminal_reserve_seconds"], 65)
        self.assertFalse(
            diagnosis["exact_v24466_blocking_call_or_validation_stage_identifiable"]
        )
        self.assertFalse(diagnosis["total_wall_gap_proven_as_unique_v24466_cause"])

    def test_actual_loopback_probe_proves_total_wall_counterexample(self) -> None:
        value = target._slow_drip_probe()
        self.assertTrue(value["both_returned_success_after_total_deadline"])
        self.assertGreater(
            value["model"]["elapsed_seconds"],
            value["configured_total_deadline_seconds"],
        )
        self.assertGreater(
            value["hosted_search"]["elapsed_seconds"],
            value["configured_total_deadline_seconds"],
        )
        self.assertEqual(value["model"]["remaining_effect_seconds_after_return"], 0)
        self.assertEqual(
            value["hosted_search"]["remaining_effect_seconds_after_return"], 0
        )

    def test_only_append_only_design_is_authorized(self) -> None:
        authorization = self.build_valid()["authorization"]
        for name in (
            "true_total_wall_effect_guard_design",
            "content_free_stage_checkpoint_design",
            "bounded_single_validation_finalize_design",
        ):
            self.assertTrue(authorization[name])
        for name in (
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[name])

    def test_resealed_causal_or_launch_tamper_fails_closed(self) -> None:
        cases = (
            (
                "causal",
                lambda value: value["diagnosis"].__setitem__(
                    "total_wall_gap_proven_as_unique_v24466_cause", True
                ),
            ),
            (
                "identifiable",
                lambda value: value["diagnosis"].__setitem__(
                    "exact_v24466_blocking_call_or_validation_stage_identifiable",
                    True,
                ),
            ),
            (
                "launch",
                lambda value: value["authorization"].__setitem__(
                    "external_probe_launch", True
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

    def test_dirty_or_untracked_source_closes_design_authorization(self) -> None:
        with (
            patch.object(target, "_slow_drip_probe", return_value=PROBE),
            patch.object(target.base, "_tracked", return_value=False),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: "dirty"
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
        self.assertFalse(value["diagnosis_valid"])
        self.assertFalse(
            value["authorization"]["true_total_wall_effect_guard_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])


if __name__ == "__main__":
    unittest.main()
