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
from scripts import audit_v24481_separated_budget_build as target  # noqa: E402


class V24481SeparatedBudgetBuildAuditTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target, "_validate_parent"),
            patch.object(
                target,
                "_run_test",
                return_value={
                    "passed": True,
                    "return_code": 0,
                    "elapsed_seconds": 26.0,
                },
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
        self.assertEqual(value["findings"], [])
        return value

    def test_clean_audit_authorizes_design_only(self) -> None:
        value = self.build_valid()
        self.assertEqual(value["tests"]["test_count"], 21)
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_phase_and_full_chain_evidence_are_bound(self) -> None:
        value = self.build_valid()
        evidence = value["mechanism_evidence"]
        self.assertTrue(evidence["remote_effect_budget_seconds_unchanged_at_150"])
        self.assertEqual(evidence["local_validation_reserve_seconds"], 70.0)
        self.assertEqual(evidence["worker_total_seconds"], 220.0)
        self.assertEqual(evidence["parent_total_seconds"], 245.0)
        self.assertTrue(evidence["unchanged_full_semantic_validation_chain_completed"])
        self.assertTrue(evidence["proof_certificate_semantics_unchanged"])
        self.assertTrue(
            value["performance_evidence"][
                "full_chain_fits_local_validation_reserve"
            ]
        )

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
                    "same_v24478_population_rerun", True
                ),
            ),
            (
                "remote_budget",
                lambda value: value["mechanism_evidence"].__setitem__(
                    "remote_effect_budget_seconds_unchanged_at_150", False
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

    def test_slow_or_failed_full_chain_closes_authorization(self) -> None:
        for execution in (
            {"passed": False, "return_code": 1, "elapsed_seconds": 26.0},
            {"passed": True, "return_code": 0, "elapsed_seconds": 71.0},
        ):
            with self.subTest(execution=execution):
                def run_test(path, _timeout):
                    if path == target.FULL_CHAIN_TEST_PATH:
                        return execution
                    return {
                        "passed": True,
                        "return_code": 0,
                        "elapsed_seconds": 1.0,
                    }

                with (
                    patch.object(target, "_validate_parent"),
                    patch.object(target, "_run_test", side_effect=run_test),
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
                    value["authorization"][
                        "fresh_disjoint_external_protocol_design"
                    ]
                )

    def test_runtime_source_is_label_blind(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
