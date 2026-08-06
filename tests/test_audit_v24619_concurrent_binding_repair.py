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

from scripts import audit_v24619_concurrent_binding_repair as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24619ConcurrentBindingRepairAuditTests(unittest.TestCase):
    def test_parent_deadlock_is_terminal_consumed_and_nonretryable(self) -> None:
        self.assertTrue(target._parent_closed())

    def build(self, **changes):
        settings = {
            "parent": True,
            "binding": True,
            "git": clean_git,
            "tracked": True,
            "tests": True,
            "ast": ([], []),
            "watcher": True,
            "lease": True,
        }
        settings.update(changes)
        with (
            patch.object(target, "_parent_closed", return_value=settings["parent"]),
            patch.object(target, "_binding_valid", return_value=settings["binding"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
        ):
            return target.build_audit(now=0)

    def test_clean_surface_authorizes_fresh_protocol_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 44)
        self.assertEqual(value["freshness_baseline"]["prior_external_question_count"], 500)
        self.assertEqual(value["freshness_baseline"]["prior_external_entity_count"], 4000)
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_content_free_title_provenance_successor_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])

    def test_parent_binding_tests_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ({"parent": False}, "v24616_17_terminal_deadlock_chain_drifted"),
            ({"binding": False}, "v24618_concurrent_binding_drifted_or_active"),
            ({"tests": False}, "v24618_19_regression_failed_or_count_drifted"),
            (
                {"ast": (["runtime.py:1:category"], [])},
                "privileged_field_access_in_v24618_runtime",
            ),
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
            ({"git": dirty}, "v24618_19_source_worktree_not_clean"),
            ({"git": unpushed}, "v24618_19_source_commit_not_pushed"),
            ({"tracked": False}, "v24618_19_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.build(**changes)["findings"])

    def test_runtime_ast_and_surface_are_label_blind_and_secret_free(self) -> None:
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

    def test_binding_repair_is_concurrent_idle_and_content_free(self) -> None:
        self.assertTrue(target._binding_valid())
        repair = self.build()["binding_repair"]
        self.assertTrue(repair["eight_runtime_holders_overlap"])
        self.assertTrue(repair["first_holder_installs_and_final_holder_restores"])
        self.assertTrue(repair["same_thread_cross_mode_nesting_fails_immediately"])
        self.assertFalse(repair["real_proof_total_bounded_modules_mutated"])

    def test_batch_ceiling_is_not_misreported_as_watchdog(self) -> None:
        diagnosis = self.build()["batch_deadline_diagnosis"]
        self.assertTrue(diagnosis["declared_batch_wall_is_postcompletion_latency_gate"])
        self.assertFalse(diagnosis["declared_batch_wall_is_enforcing_watchdog"])
        self.assertTrue(diagnosis["preworker_cross_thread_binding_deadlock_established"])
        self.assertFalse(diagnosis["provider_or_search_latency_established_as_failure_cause"])

    def test_audit_never_authorizes_benchmark_evaluator_or_parser_change(self) -> None:
        authorization = self.build()["authorization"]
        self.assertFalse(authorization["fresh_external_activation_or_launch"])
        self.assertFalse(authorization["search_parser_title_validator_or_evidence_rule_change"])
        self.assertFalse(authorization["paired_dev64_or_exact220"])
        self.assertFalse(authorization["evaluator_access_authorized"])
        self.assertFalse(authorization["leaderboard_or_sota"])

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
