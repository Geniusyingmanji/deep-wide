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

from scripts import audit_v24593_validator_aligned_title_query_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24593ValidatorAlignedTitleQueryBuildAuditTests(unittest.TestCase):
    def test_v24586_88_public_parent_chain_is_closed(self) -> None:
        self.assertTrue(target._parents_closed())

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

    def build(self, **changes):
        settings = {
            "parents": True,
            "git": clean_git,
            "tracked": True,
            "tests": True,
            "ast": ([], []),
            "watcher": True,
            "lease": True,
        }
        settings.update(changes)
        with (
            patch.object(target, "_parents_closed", return_value=settings["parents"]),
            patch.object(target.common, "_git", side_effect=settings["git"]),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
            patch.object(target.common, "_run_test", return_value=settings["tests"]),
            patch.object(target.common, "ast_findings", return_value=settings["ast"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(
                target.common, "_lease_inactive", return_value=settings["lease"]
            ),
        ):
            return target.build_audit(now=0)

    def test_clean_surface_authorizes_fresh_protocol_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 72)
        self.assertEqual(
            value["freshness_baseline"]["prior_external_question_count"], 468
        )
        self.assertEqual(
            value["freshness_baseline"]["prior_external_entity_count"], 3744
        )
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_validator_aligned_title_query_external_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_parent_tests_leakage_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ({"parents": False}, "v24586_88_parent_chain_drifted"),
            ({"tests": False}, "v24585_93_regression_failed_or_count_drifted"),
            (
                {"ast": (["runtime.py:1:category"], [])},
                "privileged_field_access_in_v24585_92_runtime",
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
            ({"git": dirty}, "v24589_93_source_worktree_not_clean"),
            ({"git": unpushed}, "v24589_93_source_commit_not_pushed"),
            ({"tracked": False}, "v24589_93_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_mechanism_attestation_separates_query_alignment_from_effect(self) -> None:
        evidence = self.build()["mechanism_evidence"]
        self.assertTrue(evidence["v24589_first_query_uses_frozen_validator_full_surface"])
        self.assertTrue(
            evidence[
                "v24589_second_query_uses_frozen_validator_core_else_initialism_else_full"
            ]
        )
        self.assertFalse(
            evidence[
                "same_task_query_and_title_replacement_cooccurrence_proves_query_or_lead_level_causality"
            ]
        )
        self.assertFalse(
            evidence["synthetic_reachability_proves_external_effect_or_quality_gain"]
        )

    def test_budget_credit_validator_and_private_binding_remain_frozen(self) -> None:
        evidence = self.build()["mechanism_evidence"]
        self.assertEqual(
            evidence["remote_worker_parent_batch_cutoffs_seconds"],
            [150, 220, 245, 255],
        )
        self.assertFalse(
            evidence[
                "logical_query_search_batch_fetch_page_source_or_model_budget_changed"
            ]
        )
        self.assertFalse(
            evidence[
                "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit"
            ]
        )
        self.assertFalse(evidence["title_alias_validator_or_evidence_projection_changed"])
        self.assertFalse(
            evidence["v24592_module_global_proof_or_projection_context_used"]
        )

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
