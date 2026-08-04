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
    audit_v24483_separated_worker_integration_build as target,
)


class V24483SeparatedWorkerIntegrationBuildAuditTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target, "_validate_parent"),
            patch.object(
                target,
                "_run_test",
                return_value={
                    "passed": True,
                    "return_code": 0,
                    "elapsed_seconds": 35.0,
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
        return value

    def test_clean_audit_authorizes_protocol_design_only(self) -> None:
        value = self.build_valid()
        self.assertEqual(value["tests"]["test_count"], 47)
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_real_process_and_timeout_evidence_is_bound(self) -> None:
        evidence = self.build_valid()["mechanism_evidence"]
        self.assertTrue(
            evidence["one_origin_crosses_real_parent_supervisor_worker_processes"]
        )
        self.assertEqual(evidence["remote_effect_deadline_seconds"], 150.0)
        self.assertEqual(evidence["worker_deadline_seconds"], 220.0)
        self.assertEqual(evidence["parent_deadline_seconds"], 245.0)
        self.assertTrue(evidence["worker_process_group_cutoff_preserved"])
        self.assertTrue(
            evidence["timeout_failure_stage_and_effect_lower_bounds_preserved"]
        )
        self.assertTrue(
            evidence["complete_validation_and_terminal_certificate_preserved"]
        )

    def test_resealed_launch_rerun_or_deadline_tamper_fails(self) -> None:
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
                "deadline",
                lambda value: value["mechanism_evidence"].__setitem__(
                    "remote_effect_deadline_seconds", 220.0
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

    def test_slow_or_failed_real_chain_closes_authorization(self) -> None:
        for execution in (
            {"passed": False, "return_code": 1, "elapsed_seconds": 35.0},
            {"passed": True, "return_code": 0, "elapsed_seconds": 55.0},
        ):
            with self.subTest(execution=execution):
                def run_test(path, _timeout):
                    if path == target.REAL_CHAIN_PATH:
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
