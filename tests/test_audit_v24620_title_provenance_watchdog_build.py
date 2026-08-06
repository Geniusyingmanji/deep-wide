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

from scripts import audit_v24620_title_provenance_watchdog_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24620TitleProvenanceWatchdogBuildAuditTests(unittest.TestCase):
    def build(self, **changes):
        settings = {
            "parent": True,
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
            patch.object(target, "_parent_valid", return_value=settings["parent"]),
            patch.object(target, "_design_valid", return_value=settings["design"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
        ):
            return target.build_audit(now=0)

    def test_parent_and_real_design_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertTrue(target._design_valid())

    def test_clean_surface_authorizes_protocol_publication_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 54)
        self.assertTrue(value["authorization"]["v24620_protocol_publication"])
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_parent_design_tests_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ({"parent": False}, "v24619_parent_audit_drifted"),
            ({"design": False}, "v24620_design_or_freshness_drifted"),
            ({"tests": False}, "v24620_regression_failed_or_count_drifted"),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"lease": False}, "shared_api_lease_active"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.build(**changes)["findings"])

    def test_dirty_unpushed_or_untracked_source_fails_closed(self) -> None:
        def dirty(*args: str) -> str:
            return "M source.py" if args == ("status", "--porcelain") else "a" * 40

        def unpushed(*args: str) -> str:
            if args == ("status", "--porcelain"):
                return ""
            return "a" * 40 if args == ("rev-parse", "HEAD") else "b" * 40

        cases = (
            ({"git": dirty}, "v24620_source_worktree_not_clean"),
            ({"git": unpushed}, "v24620_source_commit_not_pushed"),
            ({"tracked": False}, "v24620_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.build(**changes)["findings"])

    def test_label_or_evaluator_access_and_secret_fail_closed(self) -> None:
        value = self.build(ast=(["runtime.py:1:category"], []))
        self.assertIn("privileged_field_access_in_v24620_runtime", value["findings"])
        value = self.build(ast=([], ["runtime.py:1:evaluator"]))
        self.assertIn("evaluator_import_in_v24620_runtime", value["findings"])

    def test_runtime_design_is_fast_enforcing_and_budget_neutral(self) -> None:
        design = self.build()["runtime_design"]
        self.assertTrue(design["complete_protocol_validation_before_wave"])
        self.assertTrue(design["runtime_task_validation_uses_control_hash_id_and_manifest_only"])
        self.assertFalse(design["runtime_task_switches_to_protocol_binding_mode"])
        self.assertTrue(design["maximum_batch_wall_is_enforcing_watchdog"])
        self.assertFalse(design["logical_query_search_fetch_model_or_credit_budget_changed"])

    def test_runtime_sources_are_label_blind_and_secret_free(self) -> None:
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

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
