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
from scripts import audit_v24456_proof_carrying_build as target  # noqa: E402


class V24456ProofCarryingBuildAuditTests(unittest.TestCase):
    def performance(self, *, p95: float = 0.05) -> dict:
        return {
            "scope": "synthetic_test_fixture_only",
            "repetitions": 5,
            "certificate_validation_seconds": [p95] * 5,
            "certificate_validation_median_seconds": p95,
            "certificate_validation_p95_seconds": p95,
            "certificate_validation_max_seconds": p95,
            "parent_post_child_median_seconds": p95,
            "parent_post_child_p95_seconds": p95,
            "parent_post_child_max_seconds": p95,
            "ceiling_seconds": 1.0,
            "ceiling_passed": p95 <= 1.0,
            "network_model_search_fetch_or_evaluator_called": False,
            "profile_is_not_external_latency_estimate": True,
        }

    def build_clean(self, *, performance: dict | None = None) -> dict:
        def clean_git(*args: str) -> str:
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "a" * 40
            if args == ("status", "--porcelain"):
                return ""
            raise AssertionError(args)

        with (
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_git", side_effect=clean_git),
            patch.object(target.base, "_run_test", return_value=True),
            patch.object(target, "_measure_parent_validation", return_value=performance or self.performance()),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            return target.build_audit(now=0)

    def test_runtime_surface_has_no_privileged_access_or_evaluator_import(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])

    def test_clean_build_authorizes_only_offline_adaptive_design(self) -> None:
        value = self.build_clean()
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 26)
        self.assertEqual(value["tests"]["mechanism_test_count"], 21)
        self.assertTrue(value["performance_evidence"]["ceiling_passed"])
        self.assertFalse(value["trust_boundary"]["certificate_is_independently_signed"])
        self.assertFalse(value["trust_boundary"]["malicious_child_resistance_claimed"])
        self.assertTrue(value["authorization"]["adaptive_support_successor_offline_design"])
        for name in (
            "fresh_external_protocol_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_resealed_launch_or_trust_expansion_tamper_fails(self) -> None:
        for name in ("external_probe_launch", "malicious_child_resistance_claimed"):
            with self.subTest(name=name):
                altered = self.build_clean()
                target_path = (
                    altered["authorization"]
                    if name == "external_probe_launch"
                    else altered["trust_boundary"]
                )
                target_path[name] = True
                altered.pop("audit_payload_sha256")
                altered["audit_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(altered)

    def test_latency_gate_failure_closes_offline_authorization(self) -> None:
        slow = self.performance(p95=1.1)
        value = self.build_clean(performance=slow)
        self.assertFalse(value["audit_valid"])
        self.assertIn(
            "proof_carrying_parent_validation_latency_gate_failed",
            value["findings"],
        )
        self.assertFalse(
            value["authorization"]["adaptive_support_successor_offline_design"]
        )

    def test_privileged_access_closes_offline_authorization(self) -> None:
        with patch.object(
            target.base,
            "_ast_findings",
            return_value=(["runtime.py:1:ground_truth"], []),
        ):
            value = self.build_clean()
        self.assertFalse(value["audit_valid"])
        self.assertIn(
            "privileged_field_access_in_v24449_55_runtime", value["findings"]
        )
        self.assertFalse(
            value["authorization"]["adaptive_support_successor_offline_design"]
        )


if __name__ == "__main__":
    unittest.main()
