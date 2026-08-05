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

from scripts import audit_v24611_title_provenance_build as target  # noqa: E402


def clean_git(*args: str) -> str:
    return "" if args == ("status", "--porcelain") else "a" * 40


class V24611TitleProvenanceBuildAuditTests(unittest.TestCase):
    def test_public_parent_chain_is_closed_and_diagnosis_is_design_only(self) -> None:
        self.assertTrue(target._parent_chain_valid())

    def build(self, **changes):
        settings = {
            "parent": True,
            "binding": True,
            "stress": {
                "workers": 8,
                "validations": 8,
                "instance_local_immutable_v24608_projector": True,
                "shared_runtime_original_projection_read_by_collector": False,
                "passed": True,
            },
            "git": clean_git,
            "tracked": True,
            "tests": True,
            "ast": ([], []),
            "watcher": True,
            "lease": True,
        }
        settings.update(changes)
        with (
            patch.object(target, "_parent_chain_valid", return_value=settings["parent"]),
            patch.object(target, "_collector_binding_valid", return_value=settings["binding"]),
            patch.object(target, "_collector_stress", return_value=settings["stress"]),
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
        self.assertEqual(value["tests"]["test_count"], 85)
        self.assertEqual(value["collector"]["stress"]["validations"], 8)
        self.assertEqual(value["freshness_baseline"]["prior_external_question_count"], 484)
        self.assertEqual(value["freshness_baseline"]["prior_external_entity_count"], 3872)
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_content_free_title_provenance_external_protocol_design"
            ]
        )
        self.assertFalse(
            value["authorization"][
                "search_parser_title_validator_or_evidence_rule_change"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_parent_binding_stress_tests_watcher_and_lease_fail_closed(self) -> None:
        failed_stress = {
            "workers": 8,
            "validations": 0,
            "instance_local_immutable_v24608_projector": True,
            "shared_runtime_original_projection_read_by_collector": False,
            "passed": False,
        }
        cases = (
            ({"parent": False}, "v24604_05_parent_chain_drifted"),
            ({"binding": False}, "immutable_v24608_collector_binding_drifted"),
            ({"stress": failed_stress}, "immutable_v24608_collector_stress_failed"),
            ({"tests": False}, "v24605_11_regression_failed_or_count_drifted"),
            (
                {"ast": (["runtime.py:1:category"], [])},
                "privileged_field_access_in_v24605_10_runtime",
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
            ({"git": dirty}, "v24605_11_source_worktree_not_clean"),
            ({"git": unpushed}, "v24605_11_source_commit_not_pushed"),
            ({"tracked": False}, "v24605_11_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

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

    def test_mechanism_preserves_effect_and_does_not_invent_cause(self) -> None:
        evidence = self.build()["mechanism_evidence"]
        self.assertTrue(evidence["v24605_does_not_invent_unobserved_provider_or_adapter_cause"])
        self.assertTrue(
            evidence[
                "synthetic_action_and_citation_titles_preserved_through_union_projection"
            ]
        )
        self.assertFalse(evidence["query_ranking_title_validator_or_evidence_projection_changed"])
        self.assertFalse(evidence["synthetic_fidelity_proves_real_provider_or_quality_cause"])

    def test_budget_credit_and_private_binding_remain_frozen(self) -> None:
        value = self.build()
        evidence = value["mechanism_evidence"]
        self.assertEqual(evidence["remote_worker_parent_batch_cutoffs_seconds"], [150, 220, 245, 255])
        self.assertFalse(
            evidence["logical_query_search_batch_fetch_page_source_or_model_budget_changed"]
        )
        self.assertFalse(
            evidence[
                "title_or_url_hint_receives_evidence_source_entropy_epistemic_or_decision_credit"
            ]
        )
        self.assertFalse(evidence["v24609_module_global_proof_or_projection_context_used"])
        self.assertFalse(value["collector"]["collector_reads_shared_runtime_original_projection"])

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
