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
from scripts import audit_v24462_proof_carrying_adaptive_build as target  # noqa: E402


PERFORMANCE = {
    "scope": "synthetic_test_fixture_only",
    "repetitions": 5,
    "certificate_validation_seconds": [0.01] * 5,
    "certificate_validation_median_seconds": 0.01,
    "certificate_validation_p95_seconds": 0.01,
    "certificate_validation_max_seconds": 0.01,
    "parent_post_child_median_seconds": 0.02,
    "parent_post_child_p95_seconds": 0.02,
    "parent_post_child_max_seconds": 0.02,
    "ceiling_seconds": 1.0,
    "ceiling_passed": True,
    "public_projection_contains_no_lead_page_or_hash": True,
    "network_model_search_fetch_or_evaluator_called": False,
    "profile_is_not_external_latency_estimate": True,
}


class V24462ProofCarryingAdaptiveBuildAuditTests(unittest.TestCase):
    def build_clean(self) -> dict:
        def clean_git(*args: str) -> str:
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "a" * 40
            if args == ("status", "--porcelain"):
                return ""
            raise AssertionError(args)

        with (
            patch.object(target, "_validate_parent"),
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_git", side_effect=clean_git),
            patch.object(target, "_run_test", return_value=True),
            patch.object(target, "_measure_parent_validation", return_value=PERFORMANCE),
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

    def test_clean_audit_authorizes_only_external_protocol_design(self) -> None:
        value = self.build_clean()
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 35)
        self.assertEqual(value["tests"]["mechanism_test_count"], 30)
        self.assertTrue(value["authorization"]["fresh_external_protocol_design"])
        for name in (
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_public_surface_or_recursive_replay_tamper_fails(self) -> None:
        for field in (
            "public_projection_contains_lead_page_or_hash",
            "parent_recursive_historical_semantic_replay_tasks",
        ):
            with self.subTest(field=field):
                altered = self.build_clean()
                altered["proof_evidence"][field] = (
                    True if "contains" in field else 1
                )
                altered.pop("audit_payload_sha256")
                altered["audit_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(altered)

    def test_launch_authorization_tamper_fails(self) -> None:
        altered = self.build_clean()
        altered["authorization"]["external_probe_launch"] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_audit(altered)

    def test_privileged_access_closes_design_authorization(self) -> None:
        with patch.object(
            target.base,
            "_ast_findings",
            return_value=(["runtime.py:1:ground_truth"], []),
        ):
            value = self.build_clean()
        self.assertFalse(value["audit_valid"])
        self.assertIn(
            "privileged_field_access_in_v24459_61_runtime", value["findings"]
        )
        self.assertFalse(value["authorization"]["fresh_external_protocol_design"])


if __name__ == "__main__":
    unittest.main()
