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
from scripts import diagnose_v24473_v24472_nominal_transport as target  # noqa: E402


class V24473V24472NominalTransportDiagnosisTests(unittest.TestCase):
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

    def test_public_closure_records_pre_effect_validation_failure(self) -> None:
        observed = self.build_valid()["public_observation"]
        self.assertEqual(observed["worker_nonzero_tasks"], 8)
        self.assertEqual(observed["worker_hard_timeout_tasks"], 0)
        self.assertEqual(observed["last_stage_counts"], {"runtime_entered": 8})
        self.assertEqual(
            observed["child_exception_type_counts"], {"ValidationError": 8}
        )
        self.assertEqual(observed["model_effect_started_lower_bound"], 0)
        self.assertEqual(observed["hosted_search_effect_started_lower_bound"], 0)
        self.assertEqual(observed["public_fetch_effect_started_lower_bound"], 0)

    def test_actual_construction_probe_reproduces_nominal_rejection(self) -> None:
        probe = target._construction_probe()
        self.assertFalse(probe["formal_search_is_legacy_nominal_instance"])
        self.assertTrue(probe["formal_search_is_hard_total_wall_instance"])
        self.assertEqual(probe["legacy_contract_exception_type"], "ValueError")
        self.assertEqual(
            probe["legacy_contract_exception_message"],
            "V2.44.38 requires deadline-aware search transport",
        )
        self.assertEqual(probe["provider_model_acquisitions"], 0)
        self.assertEqual(probe["hosted_search_attempts"], 0)
        self.assertEqual(probe["hard_fetch_helper_calls"], 0)
        self.assertTrue(probe["model_effect_surface_unchanged"])
        self.assertTrue(probe["model_remaining_seconds_nonincreasing"])
        self.assertEqual(
            probe["compatible_class_request_method_owner"],
            "HardTotalWallNativeSearchClient",
        )

    def test_diagnosis_preserves_causal_limit_and_population_ban(self) -> None:
        diagnosis = self.build_valid()["diagnosis"]
        self.assertFalse(diagnosis["private_v24472_traceback_available"])
        self.assertFalse(
            diagnosis["nominal_mismatch_proven_as_unique_private_v24472_exception"]
        )
        self.assertFalse(diagnosis["same_v24472_population_rerun_allowed"])

    def test_only_local_append_only_design_is_authorized(self) -> None:
        authorization = self.build_valid()["authorization"]
        self.assertTrue(authorization["append_only_nominal_compatibility_design"])
        self.assertTrue(authorization["local_synthetic_integration_test_design"])
        for name in (
            "same_v24472_population_rerun",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[name])

    def test_resealed_causal_launch_or_rerun_tamper_fails(self) -> None:
        cases = (
            (
                "causal",
                lambda value: value["diagnosis"].__setitem__(
                    "nominal_mismatch_proven_as_unique_private_v24472_exception", True
                ),
            ),
            (
                "launch",
                lambda value: value["authorization"].__setitem__(
                    "external_probe_launch", True
                ),
            ),
            (
                "rerun",
                lambda value: value["authorization"].__setitem__(
                    "same_v24472_population_rerun", True
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


if __name__ == "__main__":
    unittest.main()
