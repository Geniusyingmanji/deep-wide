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

from scripts import audit_v24717_order_join_observer_repair as repair  # noqa: E402


class V24717ObserverRepairTests(unittest.TestCase):
    def test_failure_parent_is_valid(self) -> None:
        self.assertTrue(repair._failure_valid())

    def test_active_runner_returns_boolean(self) -> None:
        self.assertIs(type(repair.active_runner()), bool)

    def test_resealed_nonboolean_observation_fails(self) -> None:
        value = {
            "role": "v24715_order_join_package_build_audit",
            "audit_valid": True,
            "findings": [],
            "runtime_state": {"forward_runner_active": False},
            "observer_repair": {
                "failure_sha256": repair.contract.sha256(ROOT / repair.FAILURE),
                "only_semantic_change": "active_runner_observer_returns_boolean",
                "active_runner_observation_type": "bool",
                "base_builder_source_immutable": True,
            },
            "authorization": {
                "protocol_publication": True,
                "activation_or_forward_launch": False,
                "evaluator": False,
                "leaderboard_or_sota": False,
            },
        }
        value["audit_payload_sha256"] = repair.contract.payload_sha256(value)
        repair.validate_audit(value)
        tampered = copy.deepcopy(value)
        tampered["runtime_state"]["forward_runner_active"] = None
        tampered["observer_repair"]["active_runner_observation_type"] = "NoneType"
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = repair.contract.payload_sha256(tampered)
        with self.assertRaisesRegex(RuntimeError, "drifted"):
            repair.validate_audit(tampered)

    def test_build_wrapper_injects_repaired_observer(self) -> None:
        synthetic = {
            "role": "v24715_order_join_package_build_audit",
            "audit_valid": True,
            "findings": [],
            "runtime_state": {"forward_runner_active": False},
            "authorization": {
                "protocol_publication": True,
                "activation_or_forward_launch": False,
                "evaluator": False,
                "leaderboard_or_sota": False,
            },
            "audit_payload_sha256": "old",
        }
        with (
            patch.object(repair, "_failure_valid", return_value=True),
            patch.object(repair.base, "build_audit", return_value=synthetic),
            patch.object(repair, "active_runner", return_value=False),
            patch.object(repair, "validate_audit", side_effect=lambda value: value),
        ):
            value = repair.build_audit()
        self.assertEqual(value["observer_repair"]["active_runner_observation_type"], "bool")
        self.assertTrue(repair.contract.sealed(value, "audit_payload_sha256"))


if __name__ == "__main__":
    unittest.main()
