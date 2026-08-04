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
from scripts import audit_v24458_adaptive_entropy_support_build as target  # noqa: E402


class V24458AdaptiveEntropySupportBuildAuditTests(unittest.TestCase):
    def build_clean(self) -> dict:
        def clean_git(*args: str) -> str:
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "a" * 40
            if args == ("status", "--porcelain"):
                return ""
            raise AssertionError(args)

        with (
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_git", side_effect=clean_git),
            patch.object(target, "_run_test", return_value=True),
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

    def test_clean_build_authorizes_only_proof_integration_design(self) -> None:
        value = self.build_clean()
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 11)
        self.assertEqual(value["tests"]["mechanism_test_count"], 6)
        self.assertEqual(
            [item["timeout_seconds"] for item in value["tests"]["suites"]],
            [900, 360],
        )
        self.assertEqual(value["mechanism_evidence"]["maximum_additional_fetches"], 3)
        self.assertFalse(value["mechanism_evidence"]["thresholds_relaxed"])
        self.assertTrue(
            value["authorization"]["proof_carrying_adaptive_integration_design"]
        )
        for name in (
            "fresh_external_protocol_design",
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_resealed_launch_or_threshold_expansion_tamper_fails(self) -> None:
        for field in ("external_probe_launch", "maximum_additional_fetches"):
            with self.subTest(field=field):
                altered = self.build_clean()
                if field == "external_probe_launch":
                    altered["authorization"][field] = True
                else:
                    altered["mechanism_evidence"][field] = 4
                altered.pop("audit_payload_sha256")
                altered["audit_payload_sha256"] = payload_sha256(altered)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(altered)

    def test_credit_feedback_expansion_tamper_fails(self) -> None:
        altered = self.build_clean()
        altered["credit_evidence"][
            "allocated_credit_used_for_same_run_routing_or_training"
        ] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_audit(altered)

    def test_privileged_access_closes_integration_authorization(self) -> None:
        with patch.object(
            target.base,
            "_ast_findings",
            return_value=(["runtime.py:1:ground_truth"], []),
        ):
            value = self.build_clean()
        self.assertFalse(value["audit_valid"])
        self.assertIn("privileged_field_access_in_v24457_runtime", value["findings"])
        self.assertFalse(
            value["authorization"]["proof_carrying_adaptive_integration_design"]
        )


if __name__ == "__main__":
    unittest.main()
