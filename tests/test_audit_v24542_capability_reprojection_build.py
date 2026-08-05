from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24542_capability_reprojection_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24542CapabilityReprojectionBuildAuditTests(unittest.TestCase):
    def build(self, **changes):
        settings = {
            "quarantine": True,
            "repair": True,
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
            patch.object(target, "_repair_shape_valid", return_value=settings["repair"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
            patch.object(
                target.quarantine,
                "_no_active_v24541_process",
                return_value=settings["process"],
            ),
        ):
            return target.build_audit(now=0)

    def test_clean_surface_authorizes_protocol_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 73)
        self.assertTrue(value["repair"]["pure_projector_restored_only_during_total_aggregate"])
        self.assertTrue(value["authorization"]["fresh_disjoint_action_credit_external_protocol_design"])
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_quarantine_repair_and_tests_fail_closed(self) -> None:
        cases = (
            ({"quarantine": False}, "v24541_quarantine_drifted"),
            ({"repair": False}, "capability_reprojection_repair_drifted"),
            ({"tests": False}, "v24533_v24542_regression_failed_or_count_drifted"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_leakage_watcher_lease_and_process_fail_closed(self) -> None:
        cases = (
            ({"ast": (["runtime.py:1:category"], [])}, "privileged_field_access_in_v24533_v24541_runtime"),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"lease": False}, "shared_api_lease_active"),
            ({"process": False}, "v24541_process_still_active"),
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
            ({"git": dirty}, "v24542_source_worktree_not_clean"),
            ({"git": unpushed}, "v24542_source_commit_not_pushed"),
            ({"tracked": False}, "v24542_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_real_quarantine_and_repair_shape_are_valid(self) -> None:
        self.assertTrue(target._quarantine_valid())
        self.assertTrue(target._repair_shape_valid())


if __name__ == "__main__":
    unittest.main()
