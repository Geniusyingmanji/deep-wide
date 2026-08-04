from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24465_single_validation_adaptive_build as target  # noqa: E402


PERFORMANCE = {
    "scope": "synthetic_test_fixture_only",
    "repetitions": 3,
    "complete_validation_wall_seconds": 30.0,
    "recursive_envelope_seconds": [15.0, 15.0, 15.0],
    "recursive_envelope_median_seconds": 15.0,
    "recursive_envelope_p95_seconds": 15.0,
    "fast_envelope_seconds": [0.1, 0.1, 0.1],
    "fast_envelope_median_seconds": 0.1,
    "fast_envelope_p95_seconds": 0.1,
    "fast_envelope_p95_ceiling_seconds": 1.0,
    "fast_envelope_ceiling_passed": True,
    "fast_and_recursive_envelope_values_equal": True,
    "minimum_future_terminal_reserve_seconds": 45.0,
    "terminal_reserve_exceeds_fast_p95_seconds": True,
    "network_model_search_fetch_or_evaluator_called": False,
    "profile_is_not_external_latency_estimate": True,
}
FAILED = {
    "selected": 16,
    "batch_wall_seconds": 510.0,
}


class V24465SingleValidationAdaptiveBuildAuditTests(unittest.TestCase):
    def build_clean(self) -> dict:
        def clean_git(*args: str) -> str:
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "a" * 40
            if args == ("status", "--porcelain"):
                return ""
            raise AssertionError(args)

        with (
            patch.object(target, "_validate_parents", return_value=FAILED),
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_git", side_effect=clean_git),
            patch.object(target, "_run_test", return_value=True),
            patch.object(target, "_measure_builders", return_value=PERFORMANCE),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            return target.build_audit(now=0)

    def test_runtime_has_no_privileged_access_or_evaluator_import(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])

    def test_clean_audit_authorizes_only_new_external_design(self) -> None:
        value = self.build_clean()
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 23)
        self.assertTrue(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(value["authorization"]["same_v24463_population_rerun"])
        self.assertFalse(value["authorization"]["external_probe_launch"])

    def test_replay_or_reserve_tamper_fails(self) -> None:
        for field, bad in (
            ("complete_semantic_validation_count_per_successful_child", 2),
            ("future_effect_deadline_must_precede_parent_timeout_by_at_least_seconds", 20.0),
        ):
            with self.subTest(field=field):
                value = self.build_clean()
                value["single_validation_evidence"][field] = bad
                value.pop("audit_payload_sha256")
                value["audit_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(value)

    def test_same_population_or_launch_tamper_fails(self) -> None:
        for field in ("same_v24463_population_rerun", "external_probe_launch"):
            with self.subTest(field=field):
                value = self.build_clean()
                value["authorization"][field] = True
                value.pop("audit_payload_sha256")
                value["audit_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(value)

    def test_privileged_access_closes_design_authorization(self) -> None:
        with patch.object(
            target.base,
            "_ast_findings",
            return_value=(["runtime.py:1:ground_truth"], []),
        ):
            value = self.build_clean()
        self.assertFalse(value["audit_valid"])
        self.assertFalse(value["authorization"]["fresh_external_protocol_design"])


if __name__ == "__main__":
    unittest.main()
