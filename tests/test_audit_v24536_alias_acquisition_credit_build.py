from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24536_alias_acquisition_credit_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24536AliasAcquisitionCreditBuildAuditTests(unittest.TestCase):
    def test_frozen_parent_and_v24532_no_go_closure_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertTrue(target._v24532_closed_no_go_valid())

    def test_runtime_ast_and_surface_are_label_blind(self) -> None:
        accesses: list[str] = []
        imports: list[str] = []
        for path in target.RUNTIME_SOURCES:
            current_accesses, current_imports = target.common.ast_findings(path)
            accesses.extend(current_accesses)
            imports.extend(current_imports)
        secret_hits = [
            str(path)
            for path in target.SOURCES
            if target.common.SECRET.search(
                target.common._ordinary(path).read_text(encoding="utf-8")
            )
        ]
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertEqual(secret_hits, [])

    def build(self, **changes):
        settings = {
            "parent": True,
            "no_go": True,
            "git": clean_git,
            "tracked": True,
            "tests": True,
            "ast": ([], []),
            "watcher": True,
            "lease": True,
        }
        settings.update(changes)
        with (
            patch.object(target, "_parent_valid", return_value=settings["parent"]),
            patch.object(
                target,
                "_v24532_closed_no_go_valid",
                return_value=settings["no_go"],
            ),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
        ):
            return target.build_audit(now=0)

    def test_clean_surface_authorizes_protocol_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 57)
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_action_credit_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_parent_no_go_and_tests_fail_closed(self) -> None:
        cases = (
            ({"parent": False}, "v24530_parent_build_audit_drifted"),
            ({"no_go": False}, "v24532_no_go_closure_drifted"),
            ({"tests": False}, "v24525_v24536_regression_failed_or_count_drifted"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_leakage_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ({"ast": (["runtime.py:1:category"], [])}, "privileged_field_access_in_v24533_35_runtime"),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"lease": False}, "shared_api_lease_active"),
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
            ({"git": dirty}, "v24533_36_source_worktree_not_clean"),
            ({"git": unpushed}, "v24533_36_source_commit_not_pushed"),
            ({"tracked": False}, "v24533_36_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_publisher_is_create_only(self) -> None:
        with self.assertRaises(FileExistsError):
            target.publish_new(target.PARENT_AUDIT, {})


if __name__ == "__main__":
    unittest.main()
