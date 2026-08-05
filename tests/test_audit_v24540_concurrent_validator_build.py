from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24540_concurrent_validator_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24540ConcurrentValidatorBuildAuditTests(unittest.TestCase):
    def test_quarantine_fix_binding_and_concurrent_stress_are_real(self) -> None:
        self.assertTrue(target._quarantine_valid())
        self.assertTrue(target._fix_is_ancestor())
        self.assertTrue(target._serialized_binding_valid())
        stress = target._concurrent_stress()
        self.assertTrue(stress["passed"])
        self.assertEqual(stress["validations"], 200)

    def build(self, **changes):
        settings = {
            "quarantine": True,
            "ancestor": True,
            "binding": True,
            "stress": {"rounds": 25, "workers": 8, "validations": 200, "passed": True},
            "git": clean_git,
            "tracked": True,
            "tests": True,
            "ast": ([], []),
            "watcher": True,
            "lease": True,
            "process": True,
        }
        settings.update(changes)
        with (
            patch.object(target, "_quarantine_valid", return_value=settings["quarantine"]),
            patch.object(target, "_fix_is_ancestor", return_value=settings["ancestor"]),
            patch.object(target, "_serialized_binding_valid", return_value=settings["binding"]),
            patch.object(target, "_concurrent_stress", return_value=settings["stress"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
            patch.object(
                target.quarantine,
                "_no_active_v24539_process",
                return_value=settings["process"],
            ),
        ):
            return target.build_audit(now=0)

    def test_clean_surface_authorizes_protocol_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 66)
        self.assertEqual(value["repair"]["stress"]["validations"], 200)
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_action_credit_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_quarantine_fix_binding_stress_and_tests_fail_closed(self) -> None:
        failed_stress = {"rounds": 25, "workers": 8, "validations": 8, "passed": False}
        cases = (
            ({"quarantine": False}, "v24539_quarantine_drifted"),
            ({"ancestor": False}, "concurrent_validator_fix_not_in_head_and_target_main"),
            ({"binding": False}, "serialized_validator_binding_drifted"),
            ({"stress": failed_stress}, "concurrent_validator_stress_failed"),
            ({"tests": False}, "v24533_v24540_regression_failed_or_count_drifted"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_leakage_watcher_lease_and_process_fail_closed(self) -> None:
        cases = (
            ({"ast": (["runtime.py:1:category"], [])}, "privileged_field_access_in_v24533_v24539_runtime"),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"lease": False}, "shared_api_lease_active"),
            ({"process": False}, "v24539_process_still_active"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_dirty_unpushed_or_untracked_source_fails_closed(self) -> None:
        def dirty(*args: str) -> str:
            return "M source.py" if args == ("status", "--porcelain") else "a" * 40

        def unpushed(*args: str) -> str:
            if args == ("status", "--porcelain"):
                return ""
            return "a" * 40 if args == ("rev-parse", "HEAD") else "b" * 40

        cases = (
            ({"git": dirty}, "v24540_source_worktree_not_clean"),
            ({"git": unpushed}, "v24540_source_commit_not_pushed"),
            ({"tracked": False}, "v24540_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_publisher_is_create_only(self) -> None:
        with self.assertRaises(FileExistsError):
            target.publish_new(target.QUARANTINE_AUDIT, {})


if __name__ == "__main__":
    unittest.main()
