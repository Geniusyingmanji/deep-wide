from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import (  # noqa: E402
    BASELINES,
    PACKAGE_GATE_CONTRACT,
    build_decision_manifest,
)
from deepwide_agent.v24203_materialization_audit import (  # noqa: E402
    build_materialization_manifest,
)
from deepwide_agent.v24204_postdecision_work_order import (  # noqa: E402
    build_work_order_manifest,
    select_work_order,
    validate_terminal_decision,
)


def full_decision(digest: str, row: dict[str, object]) -> dict[str, object]:
    components = list(row["eligible_components"])
    integrated = bool(components)
    return {
        "baseline_name": row["baseline_name"],
        "baseline_publication": BASELINES[str(row["baseline_name"])],
        "mainline_scope": row["mainline_scope"],
        "markdown_branch_scope": row["markdown_branch_scope"],
        "eligible_components": components,
        "component_go_authority": "deterministic_build_and_package_gate_only",
        "integrated_package_namespace": "results/v24200_integrated_packages",
        "integrated_package_required": integrated,
        "package_gate_contract": PACKAGE_GATE_CONTRACT,
        "package_gate_required_before_all220_freeze": integrated,
        "empty_component_set_uses_selected_baseline_identity_handoff": not integrated,
        "identity_handoff_still_requires_separate_all220_freeze_and_executor": True,
        "all220_freeze_or_launch_allowed": False,
        "v24199_diagnostic_only_not_execution_authority": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "decision_payload_sha256": digest,
    }


class V24204PostdecisionWorkOrderTests(unittest.TestCase):
    def test_all_36_work_orders_are_predeclared_and_nonexecuting(self) -> None:
        value = build_work_order_manifest()
        self.assertEqual(value["summary"]["decision_count"], 36)
        self.assertEqual(value["summary"]["identity_handoff_ready_count"], 3)
        self.assertEqual(value["summary"]["blocked_nonempty_work_order_count"], 33)
        self.assertEqual(value["summary"]["candidate_package_materialized_count"], 0)
        self.assertEqual(value["summary"]["benchmark_launch_authorized_count"], 0)
        for row in value["rows"].values():
            self.assertFalse(row["candidate_code_built_merged_or_materialized"])
            self.assertFalse(row["package_gate_evaluated_or_launched"])
            self.assertFalse(row["benchmark_forward_or_full220_launch_allowed"])

    def test_identity_handoff_reuses_only_selected_baseline_publication(self) -> None:
        value = build_work_order_manifest()
        rows = [row for row in value["rows"].values() if row["identity_handoff_only"]]
        self.assertEqual({row["baseline_name"] for row in rows}, set(BASELINES))
        for row in rows:
            self.assertEqual(row["eligible_components"], [])
            self.assertEqual(row["component_work"], {})
            self.assertEqual(row["blockers"], [])
            self.assertEqual(row["baseline_publication"], BASELINES[row["baseline_name"]])
            self.assertFalse(row["package_gate_required"])

    def test_nonempty_work_orders_never_authorize_component_publishers(self) -> None:
        value = build_work_order_manifest()
        rows = [row for row in value["rows"].values() if not row["identity_handoff_only"]]
        self.assertEqual(len(rows), 33)
        for row in rows:
            self.assertIn(
                "postdecision_joint_conflict_audit_and_regression_absent",
                row["blockers"],
            )
            self.assertTrue(row["package_gate_required"])
            for component in row["component_work"].values():
                self.assertFalse(
                    component["implementation_publisher_authorized_by_this_work_order"]
                )

    def test_entropy_work_order_remains_design_only_and_blocked(self) -> None:
        rows = build_work_order_manifest()["rows"].values()
        entropy = [
            row for row in rows if "entropy_credit_controller" in row["eligible_components"]
        ]
        self.assertEqual(len(entropy), 18)
        for row in entropy:
            contract = row["component_work"]["entropy_credit_controller"]
            self.assertFalse(contract["controller_implementation_authority_available"])
            self.assertTrue(contract["separate_implementation_authority_required"])
            self.assertFalse(row["integrated_package_bytes_available"])

    def test_terminal_decision_is_content_addressed_and_selected_exactly(self) -> None:
        digest, row = next(iter(build_decision_manifest().items()))
        decision = full_decision(digest, row)
        safe = validate_terminal_decision(decision)
        selected = select_work_order(decision)
        self.assertEqual(safe["decision_sha256"], digest)
        self.assertEqual(selected["decision_sha256"], digest)
        self.assertEqual(selected["eligible_components"], row["eligible_components"])

    def test_decision_tampering_and_privileged_guard_fail_closed(self) -> None:
        digest, row = next(iter(build_decision_manifest().items()))
        decision = full_decision(digest, row)
        tampered = copy.deepcopy(decision)
        tampered["eligible_components"] = []
        with self.assertRaisesRegex(RuntimeError, "decision bytes"):
            validate_terminal_decision(tampered)
        tampered = copy.deepcopy(decision)
        tampered["mapping_gold_category_question_type_evaluator_score_read"] = True
        with self.assertRaisesRegex(RuntimeError, "privileged-read guard"):
            validate_terminal_decision(tampered)
        tampered = copy.deepcopy(decision)
        tampered["decision_payload_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "frozen manifest"):
            validate_terminal_decision(tampered)

    def test_materialization_parent_still_reports_three_and_thirty_three(self) -> None:
        value = build_materialization_manifest(build_decision_manifest())
        self.assertEqual(value["summary"]["identity_handoff_decision_count"], 3)
        self.assertEqual(value["summary"]["blocked_nonempty_package_decision_count"], 33)


if __name__ == "__main__":
    unittest.main()
