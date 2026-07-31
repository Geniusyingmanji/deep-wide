from __future__ import annotations

import unittest

from deepwide_agent.v24200_successor import (
    PACKAGE_GATE_CONTRACT,
    SOURCE_ORDER,
    build_decision_manifest,
    classify_source,
    decision_from_statuses,
    eligible_components,
    reject_forbidden_metadata,
    select_hierarchical_baseline,
)


def terminal(**overrides: str) -> dict[str, str]:
    value = {name: "no_go" for name in SOURCE_ORDER}
    value.update(overrides)
    return value


def envelope(name: str, status: str) -> dict[str, object]:
    specs = {
        "schema76": (
            "v24154_scope_combined_fasttrack_watcher_state",
            "8e1a15ce3e5342538e57d136c170031e2d0d34e268d5761b9de8d55c91b12f80",
            ("forward_resume_used", "selective_rerun_used", "leaderboard_or_sota_claim"),
        ),
        "schema77": (
            "v24176_predicate_completion_paired_dev_watcher_state",
            "8c1c3c4d9f7ed8604258fa301ea931a6425cf6c189c5e1c30c0ee387eddd1f1e",
            (
                "forward_resume_used",
                "selective_rerun_used",
                "test156_or_full220_launch_allowed",
                "test156_or_full220_api_called",
                "leaderboard_submission_or_sota_claim",
            ),
        ),
    }
    role, digest, false_fields = specs[name]
    value: dict[str, object] = {
        "role": role,
        "protocol_sha256": digest,
        "status": status,
    }
    value.update({field: False for field in false_fields})
    return value


class V24200SuccessorTests(unittest.TestCase):
    def test_schema76_no_go_always_falls_back_to_p12(self) -> None:
        for schema77 in ("go", "no_go", "waiting"):
            self.assertEqual(
                select_hierarchical_baseline(
                    {"schema76": "no_go", "schema77": schema77}
                ),
                "p12",
            )

    def test_schema77_only_inherits_after_schema76_go(self) -> None:
        self.assertEqual(
            select_hierarchical_baseline(
                {"schema76": "go", "schema77": "no_go"}
            ),
            "schema76",
        )
        self.assertEqual(
            select_hierarchical_baseline({"schema76": "go", "schema77": "go"}),
            "schema77",
        )
        self.assertIsNone(
            select_hierarchical_baseline(
                {"schema76": "go", "schema77": "waiting"}
            )
        )

    def test_mainline_and_markdown_scope_are_separate(self) -> None:
        decision = decision_from_statuses(terminal(schema76="go"))
        assert decision is not None
        self.assertEqual(decision["baseline_name"], "schema76")
        self.assertTrue(decision["mainline_scope"])
        self.assertFalse(decision["markdown_branch_scope"])
        self.assertNotIn(
            "markdown_branch_scope_open_fallback",
            decision["eligible_components"],
        )
        self.assertFalse(decision["integrated_package_required"])
        self.assertFalse(decision["package_gate_required_before_all220_freeze"])
        self.assertTrue(
            decision["empty_component_set_uses_selected_baseline_identity_handoff"]
        )

    def test_markdown_scope_requires_markdown_parent(self) -> None:
        statuses = terminal(markdown_branch_scope="go")
        with self.assertRaisesRegex(RuntimeError, "lacks Markdown GO"):
            eligible_components(statuses)

    def test_component_go_only_enters_package_gate(self) -> None:
        decision = decision_from_statuses(
            terminal(
                schema76="go",
                schema77="go",
                search_yield="go",
                markdown="go",
                markdown_branch_scope="go",
                entropy_credit="go",
            )
        )
        assert decision is not None
        self.assertEqual(
            decision["eligible_components"],
            [
                "search_yield_shared_query",
                "markdown_rank_slot",
                "markdown_branch_scope_open_fallback",
                "entropy_credit_controller",
            ],
        )
        self.assertEqual(
            decision["component_go_authority"],
            "deterministic_build_and_package_gate_only",
        )
        self.assertTrue(decision["package_gate_required_before_all220_freeze"])
        self.assertTrue(decision["integrated_package_required"])
        self.assertFalse(
            decision["empty_component_set_uses_selected_baseline_identity_handoff"]
        )
        self.assertFalse(decision["all220_freeze_or_launch_allowed"])
        self.assertFalse(PACKAGE_GATE_CONTRACT["benchmark_launch_allowed"])

    def test_waiting_any_source_prevents_terminal_package_decision(self) -> None:
        for name in SOURCE_ORDER:
            statuses = terminal(schema76="go", schema77="go")
            statuses[name] = "waiting"
            self.assertIsNone(decision_from_statuses(statuses), name)

    def test_manifest_has_36_unique_packages(self) -> None:
        manifest = build_decision_manifest()
        self.assertEqual(len(manifest), 36)
        self.assertEqual(
            {row["baseline_name"] for row in manifest.values()},
            {"p12", "schema76", "schema77"},
        )

    def test_evaluator_only_metadata_is_rejected_recursively(self) -> None:
        for value in (
            {"category": "x"},
            {"nested": {"question_type": "x"}},
            {"nested": [{"ground_truth": "x"}]},
            {"score": 1.0},
        ):
            with self.assertRaisesRegex(RuntimeError, "evaluator-only"):
                reject_forbidden_metadata(value)

    def test_status_classifier_binds_protocol_and_false_authority(self) -> None:
        self.assertEqual(
            classify_source("schema76", envelope("schema76", "complete_exact220_released")),
            "go",
        )
        self.assertEqual(
            classify_source(
                "schema76", envelope("schema76", "complete_paired_dev_no_go")
            ),
            "no_go",
        )
        waiting = envelope("schema76", "waiting_for_p12_trial2_exact220_release")
        self.assertEqual(classify_source("schema76", waiting), "waiting")
        waiting["forward_resume_used"] = True
        with self.assertRaisesRegex(RuntimeError, "authorization drifted"):
            classify_source("schema76", waiting)

    def test_schema77_go_does_not_rescue_schema76_no_go(self) -> None:
        decision = decision_from_statuses(
            terminal(schema76="no_go", schema77="go", search_yield="go")
        )
        assert decision is not None
        self.assertEqual(decision["baseline_name"], "p12")
        self.assertEqual(
            decision["eligible_components"], ["search_yield_shared_query"]
        )


if __name__ == "__main__":
    unittest.main()
