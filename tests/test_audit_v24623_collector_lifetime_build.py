from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24623_collector_lifetime_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24623CollectorLifetimeBuildAuditTests(unittest.TestCase):
    def build(self, **changes):
        settings = {
            "design": True,
            "git": clean_git,
            "tracked": True,
            "tests": True,
            "ast": ([], []),
            "watcher": True,
            "lease": True,
        }
        settings.update(changes)
        with (
            patch.object(target, "_design_valid", return_value=settings["design"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
        ):
            return target.build_audit(now=0)

    def test_real_design_is_valid(self) -> None:
        self.assertTrue(target._design_valid())

    def test_clean_surface_authorizes_protocol_only(self) -> None:
        value = self.build()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["tests"]["test_count"], 35)
        self.assertTrue(value["authorization"]["v24622_protocol_publication"])
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])

    def test_design_tests_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ({"design": False}, "v24622_collector_lifetime_design_or_freshness_drifted"),
            ({"tests": False}, "v24622_23_regression_failed_or_count_drifted"),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"lease": False}, "shared_api_lease_active"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.build(**changes)["findings"])

    def test_dirty_unpushed_or_untracked_fails_closed(self) -> None:
        def dirty(*args: str) -> str:
            return "M source.py" if args == ("status", "--porcelain") else "a" * 40

        def unpushed(*args: str) -> str:
            if args == ("status", "--porcelain"):
                return ""
            return "a" * 40 if args == ("rev-parse", "HEAD") else "b" * 40

        cases = (
            ({"git": dirty}, "v24622_source_worktree_not_clean"),
            ({"git": unpushed}, "v24622_source_commit_not_pushed"),
            ({"tracked": False}, "v24622_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.build(**changes)["findings"])

    def test_label_or_evaluator_access_fails_closed(self) -> None:
        value = self.build(ast=(["runtime.py:1:category"], []))
        self.assertIn("privileged_field_access_in_v24622_runtime", value["findings"])
        value = self.build(ast=([], ["runtime.py:1:evaluator"]))
        self.assertIn("evaluator_import_in_v24622_runtime", value["findings"])

    def test_collector_repair_is_narrow_and_preserves_controls(self) -> None:
        repair = self.build()["collector_lifetime_repair"]
        self.assertTrue(repair["collector_enters_before_task_futures"])
        self.assertTrue(repair["collector_remains_active_through_main_aggregate"])
        self.assertTrue(repair["collector_exits_after_aggregate_or_exception"])
        self.assertFalse(repair["fast_control_validator_changed"])
        self.assertFalse(repair["enforcing_batch_watchdog_changed"])
        self.assertFalse(repair["search_fetch_model_or_credit_budget_changed"])

    def test_runtime_source_is_label_blind_and_secret_free(self) -> None:
        accesses, imports = target.common.ast_findings(target.RUNTIME_SOURCES[0])
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

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
