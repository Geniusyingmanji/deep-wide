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

from scripts import audit_v24715_order_join_package_build as audit  # noqa: E402


class V24715OrderJoinBuildTests(unittest.TestCase):
    def test_runtime_ast_and_dependencies_are_clean(self) -> None:
        self.assertEqual(audit.ast_findings(), ([], []))
        self.assertFalse(any(
            marker in dependency for dependency in audit.preregister.DEPENDENCIES
            for marker in audit.FORBIDDEN_DEPENDENCY_MARKERS
        ))

    def test_order_failure_and_predecessor_parents_are_valid(self) -> None:
        self.assertTrue(audit._parents_valid())

    def test_expected_test_count_is_31(self) -> None:
        self.assertEqual(sum(expected for _pattern, expected in audit.TESTS), 31)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 31)

    def test_build_failure_does_not_authorize_protocol_or_launch(self) -> None:
        fake_git = lambda *args: "a" * 40 if args[0] == "rev-parse" else ""
        with (
            patch.object(audit, "_git", side_effect=fake_git),
            patch.object(audit, "_tracked", return_value=True),
            patch.object(audit, "_parents_valid", return_value=True),
            patch.object(audit, "_run_tests", return_value=(30, False)),
            patch.object(audit, "ast_findings", return_value=([], [])),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(audit, "_lease_inactive", return_value=True),
            patch.object(audit, "_active", return_value=False),
            patch.object(
                audit,
                "_join_evidence",
                return_value={
                    "visible_count": 220,
                    "control_count": 220,
                    "visible_unique_count": 220,
                    "control_unique_count": 220,
                    "same_id_set": True,
                    "raw_file_order_equal": False,
                    "same_position_count": 3,
                    "ordered_join_matches_control_order": True,
                },
            ),
        ):
            value = audit.build_audit(now=0)
        self.assertFalse(value["audit_valid"])
        self.assertFalse(value["authorization"]["protocol_publication"])
        self.assertFalse(value["authorization"]["activation_or_forward_launch"])

    def test_resealed_launch_tamper_fails_validation(self) -> None:
        value = {
            "role": "v24715_order_join_package_build_audit",
            "audit_valid": True, "findings": [],
            "parents": {"valid": True},
            "repair": {"ordered_join_matches_control_order": True},
            "tests": {"passed": True, "observed": 31},
            "label_blind_audit": {"passed": True},
            "runtime_state": {"shared_api_lease_inactive": True, "forward_runner_active": False},
            "authorization": {"protocol_publication": True, "activation_or_forward_launch": False,
                              "evaluator": False, "leaderboard_or_sota": False},
        }
        value["audit_payload_sha256"] = audit.contract.payload_sha256(value)
        audit.validate_audit(value)
        tampered = copy.deepcopy(value)
        tampered["authorization"]["activation_or_forward_launch"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = audit.contract.payload_sha256(tampered)
        with self.assertRaisesRegex(RuntimeError, "drifted"):
            audit.validate_audit(tampered)


if __name__ == "__main__":
    unittest.main()
