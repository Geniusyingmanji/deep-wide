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
from scripts import audit_v24477_bounded_nominal_integration_build as target  # noqa: E402


class V24477BoundedNominalIntegrationBuildAuditTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target, "_validate_parent"),
            patch.object(
                target,
                "_run_test",
                return_value={"passed": True, "return_code": 0, "elapsed_seconds": 1.0},
            ),
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
            value = target.build_audit(now=0)
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        return value

    def test_clean_audit_authorizes_design_only(self) -> None:
        value = self.build_valid()
        self.assertEqual(value["tests"]["test_count"], 48)
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["same_v24472_population_rerun"])

    def test_full_chain_evidence_is_frozen(self) -> None:
        evidence = self.build_valid()["mechanism_evidence"]
        for name in (
            "formal_search_satisfies_legacy_nominal_contract",
            "hard_total_wall_request_path_exercised",
            "positive_entropy_decision_credit_observed",
            "safe_output_change_observed",
            "single_complete_validation_returned",
            "artifact_persistence_and_terminal_certificate_completed",
        ):
            self.assertTrue(evidence[name])

    def test_resealed_launch_rerun_or_evidence_tamper_fails(self) -> None:
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
                    "same_v24472_population_rerun", True
                ),
            ),
            (
                "evidence",
                lambda value: value["mechanism_evidence"].__setitem__(
                    "hard_total_wall_request_path_exercised", False
                ),
            ),
        )
        for name, alter in cases:
            with self.subTest(name=name):
                value = copy.deepcopy(self.build_valid())
                alter(value)
                value.pop("audit_payload_sha256")
                value["audit_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_audit(value)

    def test_failed_or_zero_elapsed_suite_closes_authorization(self) -> None:
        for execution in (
            {"passed": False, "return_code": 1, "elapsed_seconds": 1.0},
            {"passed": True, "return_code": 0, "elapsed_seconds": 0.0},
        ):
            with self.subTest(execution=execution):
                with (
                    patch.object(target, "_validate_parent"),
                    patch.object(target, "_run_test", return_value=execution),
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
                    patch.object(
                        target, "lease_observation", return_value={"active": False}
                    ),
                ):
                    value = target.build_audit(now=0)
                self.assertFalse(value["audit_valid"])
                self.assertFalse(
                    value["authorization"]["fresh_disjoint_external_protocol_design"]
                )

    def test_runtime_source_is_label_blind(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
