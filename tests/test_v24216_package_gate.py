from __future__ import annotations

import copy
import unittest

from deepwide_agent.v24216_package_gate import evaluate_package_gate


def arm(name: str, *, completed: int = 60, whole: int = 8, quality: float = 0.4, tokens: int = 1000):
    return {
        "artifact_version": 1,
        "role": "v24216_package_gate_dev64_arm_result",
        "arm": name,
        "status": "exact64_released_not_full220_not_sota",
        "selected": 64,
        "conservative_denominator": 64,
        "exact_terminal_before_mapping": True,
        "other_arm_exact_terminal_before_mapping": True,
        "failure_as_zero": True,
        "resume_or_selective_rerun_used": False,
        "full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "metrics": {
            "runtime_completed": completed,
            "runtime_failed": 64 - completed,
            "evaluator_valid": completed,
            "evaluator_invalid_or_not_run": 64 - completed,
            "whole_table_successes": whole,
            "entity_acc": quality,
            "f1_by_row": quality,
            "f1_by_item": quality,
            "column_f1": quality,
            "system_total_tokens": tokens,
        },
        "provenance": {"arm_result_sha256": "a" * 64},
    }


ACTIVATION = {
    "identity_handoff_only": False,
    "eligible_component_count": 2,
    "all_selected_components_covered_exactly_once": True,
    "single_deepest_cumulative_graph_used": True,
    "component_directory_overlay_used": False,
    "complete_parent_and_component_regression_rerun": True,
    "strict_component_activation_validated": True,
    "silent_component_drop_or_baseline_fallback_used": False,
}
IDENTITY = {
    "same_opaque_dev64_ids": True,
    "same_execution_contract": True,
    "same_evaluator_contract": True,
    "both_exact_terminal_before_mapping": True,
    "mapping_join_after_both_terminal": True,
    "outcome_or_score_used_for_execution": False,
}


class V24216PackageGateTests(unittest.TestCase):
    def test_material_completion_gain_go_but_never_launches_full220(self) -> None:
        value = evaluate_package_gate(
            arm("baseline"),
            arm("candidate", completed=61),
            package_activation=ACTIVATION,
            evaluator_identity=IDENTITY,
        )
        self.assertTrue(value["passed"])
        self.assertTrue(value["all220_freeze_design_allowed"])
        self.assertFalse(value["full220_launch_allowed"])

    def test_no_material_gain_is_no_go(self) -> None:
        value = evaluate_package_gate(
            arm("baseline"),
            arm("candidate"),
            package_activation=ACTIVATION,
            evaluator_identity=IDENTITY,
        )
        self.assertFalse(value["passed"])
        self.assertFalse(value["checks"]["material_improvement_any"])

    def test_quality_harm_or_token_overrun_is_no_go(self) -> None:
        harmed = evaluate_package_gate(
            arm("baseline"),
            arm("candidate", completed=61, quality=0.394),
            package_activation=ACTIVATION,
            evaluator_identity=IDENTITY,
        )
        costly = evaluate_package_gate(
            arm("baseline"),
            arm("candidate", completed=61, tokens=1051),
            package_activation=ACTIVATION,
            evaluator_identity=IDENTITY,
        )
        self.assertFalse(harmed["passed"])
        self.assertFalse(costly["passed"])

    def test_label_or_task_content_is_rejected(self) -> None:
        candidate = arm("candidate", completed=61)
        candidate["category"] = "hidden"
        with self.assertRaises(RuntimeError):
            evaluate_package_gate(
                arm("baseline"),
                candidate,
                package_activation=ACTIVATION,
                evaluator_identity=IDENTITY,
            )

    def test_missing_strict_activation_is_rejected(self) -> None:
        activation = copy.deepcopy(ACTIVATION)
        activation["strict_component_activation_validated"] = False
        with self.assertRaises(RuntimeError):
            evaluate_package_gate(
                arm("baseline"),
                arm("candidate", completed=61),
                package_activation=activation,
                evaluator_identity=IDENTITY,
            )


if __name__ == "__main__":
    unittest.main()
