from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24524_alias_title_integration_build as target  # noqa: E402


class V24524AliasTitleIntegrationBuildAuditTests(unittest.TestCase):
    def test_frozen_v24523_parent_is_valid(self) -> None:
        self.assertTrue(target._parent_valid())

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

    def test_clean_surface_authorizes_proof_parent_design_only(self) -> None:
        def git(*args: str) -> str:
            return "" if args == ("status", "--porcelain") else "a" * 40

        with (
            patch.object(target, "_parent_valid", return_value=True),
            patch.object(target.common, "_git", side_effect=git),
            patch.object(target.common, "_tracked", return_value=True),
            patch.object(target.common, "_run_test", return_value=True),
            patch.object(target.common, "_watcher", return_value=True),
            patch.object(target.common, "_lease_inactive", return_value=True),
        ):
            value = target.build_audit(now=0)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 41)
        self.assertTrue(
            value["authorization"][
                "proof_carrying_alias_worker_and_bounded_parent_design"
            ]
        )
        self.assertFalse(
            value["authorization"]["fresh_alias_external_protocol_design"]
        )
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_parent_tests_leakage_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ("parent", "v24523_parent_build_audit_drifted"),
            ("tests", "v24413_v24524_regression_failed_or_count_drifted"),
            ("access", "privileged_field_access_in_v24524_runtime"),
            ("watcher", "protected_watcher_identity_drifted"),
            ("lease", "shared_api_lease_active"),
        )
        for mode, expected in cases:
            with self.subTest(mode=mode):
                def git(*args: str) -> str:
                    return "" if args == ("status", "--porcelain") else "a" * 40

                ast_value = (
                    (["runtime.py:1:category"], [])
                    if mode == "access"
                    else ([], [])
                )
                with (
                    patch.object(
                        target, "_parent_valid", return_value=mode != "parent"
                    ),
                    patch.object(target.common, "_git", side_effect=git),
                    patch.object(target.common, "_tracked", return_value=True),
                    patch.object(
                        target.common, "_run_test", return_value=mode != "tests"
                    ),
                    patch.object(
                        target.common, "ast_findings", return_value=ast_value
                    ),
                    patch.object(
                        target.common, "_watcher", return_value=mode != "watcher"
                    ),
                    patch.object(
                        target.common,
                        "_lease_inactive",
                        return_value=mode != "lease",
                    ),
                ):
                    value = target.build_audit(now=0)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_dirty_unpushed_or_untracked_source_fails_closed(self) -> None:
        cases = (
            ("dirty", "v24524_source_worktree_not_clean"),
            ("unpushed", "v24524_source_commit_not_pushed"),
            ("untracked", "v24524_source_not_tracked"),
        )
        for mode, expected in cases:
            with self.subTest(mode=mode):
                def git(*args: str) -> str:
                    if args == ("status", "--porcelain"):
                        return "M source.py" if mode == "dirty" else ""
                    if args == ("rev-parse", "HEAD"):
                        return "a" * 40
                    return "b" * 40 if mode == "unpushed" else "a" * 40

                with (
                    patch.object(target, "_parent_valid", return_value=True),
                    patch.object(target.common, "_git", side_effect=git),
                    patch.object(
                        target.common,
                        "_tracked",
                        return_value=mode != "untracked",
                    ),
                    patch.object(target.common, "_run_test", return_value=True),
                    patch.object(target.common, "_watcher", return_value=True),
                    patch.object(target.common, "_lease_inactive", return_value=True),
                ):
                    value = target.build_audit(now=0)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])


if __name__ == "__main__":
    unittest.main()
