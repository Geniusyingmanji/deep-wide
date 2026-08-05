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

from scripts import audit_v24586_nested_collector_repair_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24586NestedCollectorRepairBuildAuditTests(unittest.TestCase):
    def test_quarantine_binding_and_real_stress_are_valid(self) -> None:
        self.assertTrue(target._quarantine_valid())
        self.assertTrue(target._repair_binding_valid())
        stress = target._collector_stress()
        self.assertTrue(stress["passed"])
        self.assertEqual(stress["validations"], 8)

    def build(self, **changes):
        settings = {
            "quarantine": True,
            "binding": True,
            "stress": {
                "workers": 8,
                "validations": 8,
                "instance_local_immutable_projector": True,
                "shared_runtime_original_projection_read_by_collector": False,
                "passed": True,
            },
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
            patch.object(target, "_repair_binding_valid", return_value=settings["binding"]),
            patch.object(target, "_collector_stress", return_value=settings["stress"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
            patch.object(target.quarantine, "_no_active_process", return_value=settings["process"]),
        ):
            return target.build_audit(now=0)

    def test_clean_surface_authorizes_fresh_protocol_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 27)
        self.assertEqual(value["repair"]["stress"]["validations"], 8)
        self.assertEqual(
            value["freshness_baseline"]["prior_external_question_count"], 460
        )
        self.assertEqual(
            value["freshness_baseline"]["prior_external_entity_count"], 3680
        )
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_prededup_preservation_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])

    def test_repair_is_instance_local_and_preserves_effect_surface(self) -> None:
        repair = self.build()["repair"]
        self.assertTrue(repair["collector_project_calls_instance_local_immutable_projector"])
        self.assertFalse(repair["collector_reads_shared_runtime_original_projection"])
        self.assertFalse(repair["nested_runtime_rebinding_can_change_collector_target"])
        self.assertTrue(repair["mixed_failure_projection_remains_total"])
        self.assertFalse(
            repair["task_model_search_fetch_evidence_credit_budget_or_evaluator_changed"]
        )

    def test_quarantine_binding_stress_and_environment_fail_closed(self) -> None:
        failed_stress = {
            "workers": 8,
            "validations": 0,
            "instance_local_immutable_projector": True,
            "shared_runtime_original_projection_read_by_collector": False,
            "passed": False,
        }
        cases = (
            ({"quarantine": False}, "v24584_quarantine_drifted"),
            ({"binding": False}, "immutable_collector_binding_drifted"),
            ({"stress": failed_stress}, "immutable_collector_stress_failed"),
            ({"tests": False}, "v24580_86_regression_failed_or_count_drifted"),
            (
                {"ast": (["runtime.py:1:category"], [])},
                "privileged_field_access_in_v24580_85_runtime",
            ),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"lease": False}, "shared_api_lease_active"),
            ({"process": False}, "v24583_process_still_active"),
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
            ({"git": dirty}, "v24585_86_source_worktree_not_clean"),
            ({"git": unpushed}, "v24585_86_source_commit_not_pushed"),
            ({"tracked": False}, "v24585_86_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_runtime_and_audit_sources_are_label_blind_and_secret_free(self) -> None:
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

    def test_quarantine_forbids_reuse_and_advances_freshness(self) -> None:
        state = self.build()["v24584_quarantine"]
        self.assertFalse(
            state["same_population_resume_retry_rerun_or_evaluation_authorized"]
        )
        self.assertEqual(state["next_prior_question_count"], 460)
        self.assertEqual(state["next_prior_entity_count"], 3680)

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
