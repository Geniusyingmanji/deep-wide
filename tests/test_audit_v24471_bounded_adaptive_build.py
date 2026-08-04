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
from scripts import audit_v24471_bounded_adaptive_build as target  # noqa: E402


class V24471BoundedAdaptiveBuildAuditTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target, "_validate_parent"),
            patch.object(target, "_run_test", return_value=True),
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
        return value

    def test_clean_audit_authorizes_design_only(self) -> None:
        value = self.build_valid()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 37)
        self.assertTrue(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(
            value["mechanism_evidence"]["same_v24466_population_rerun_allowed"]
        )

    def test_runtime_sources_are_label_blind(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])

    def test_resealed_launch_or_same_population_tamper_fails(self) -> None:
        cases = (
            (
                "launch",
                lambda value: value["authorization"].__setitem__(
                    "external_probe_launch", True
                ),
            ),
            (
                "rerun",
                lambda value: value["mechanism_evidence"].__setitem__(
                    "same_v24466_population_rerun_allowed", True
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

    def test_failed_suite_closes_design_authorization(self) -> None:
        with (
            patch.object(target, "_validate_parent"),
            patch.object(target, "_run_test", return_value=False),
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
        self.assertFalse(value["audit_valid"])
        self.assertFalse(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )

    def test_privileged_access_closes_design_authorization(self) -> None:
        with patch.object(
            target.base,
            "_ast_findings",
            return_value=(["runtime.py:1:ground_truth"], []),
        ):
            value = self.build_valid()
        self.assertFalse(value["audit_valid"])
        self.assertFalse(
            value["authorization"]["fresh_disjoint_external_protocol_design"]
        )


if __name__ == "__main__":
    unittest.main()
