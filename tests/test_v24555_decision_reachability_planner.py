from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24388_uncertainty_credit as credit  # noqa: E402
from deepwide_agent import v24510_proposal_seeded_entropy_target_planner as legacy  # noqa: E402
from deepwide_agent import v24515_neutral_cell_discovery_planner as neutral  # noqa: E402
from deepwide_agent import v24555_decision_reachability_planner as target  # noqa: E402
from deepwide_agent.v24555_decision_reachability_planner import (  # noqa: E402
    DecisionReachabilityPlanner,
    build_target_plan,
    validate_receipt,
    validate_target_plan,
)
from test_v24515_neutral_cell_discovery_planner import empty_state  # noqa: E402


BASELINE = """```markdown
| Software | Initial release year |
| --- | --- |
| Alpha | 2020 |
| Beta | 2020 |
```"""


def observation(row: str, value: str, host: str) -> dict:
    return {
        "row_key": row,
        "column": "Initial release year",
        "value": value,
        "source_host": host,
        "fetch_integrity": True,
    }


def competing_state() -> dict:
    catalog = credit.build_uncertainty_catalog(
        BASELINE,
        [
            observation("Alpha", "2021", "alpha-one.example"),
            observation("Beta", "2021", "beta-one.example"),
            observation("Beta", "2021", "beta-two.example"),
        ],
    )
    return credit.apply_active_evidence(catalog, [])


class V24555DecisionReachabilityPlannerTests(unittest.TestCase):
    def test_one_observation_safe_decision_beats_higher_entropy_two_step(self) -> None:
        state = competing_state()
        old = legacy.build_target_plan(state)
        new = build_target_plan(state)
        self.assertIsNotNone(old)
        self.assertIsNotNone(new)
        assert old is not None and new is not None
        self.assertEqual((old["row_key"], old["support_deficit"]), ("Alpha", 2))
        self.assertEqual((new["row_key"], new["support_deficit"]), ("Beta", 1))
        self.assertGreater(old["combined_entropy_nats"], new["combined_entropy_nats"])
        validate_target_plan(new, active_result=state)

    def test_selected_one_step_projection_crosses_all_unchanged_gates(self) -> None:
        state = competing_state()
        plan = build_target_plan(state)
        assert plan is not None
        self.assertEqual(plan["required_support_count"], 3)
        self.assertEqual(plan["minimum_new_active_support_count"], 1)
        self.assertGreaterEqual(
            plan[
                "projected_alternative_posterior_probability_after_planned_support"
            ],
            credit.MINIMUM_ALTERNATIVE_POSTERIOR,
        )
        after = credit.apply_active_evidence(
            state["catalog"],
            [observation("Beta", "2021", "beta-active.example")],
        )
        self.assertEqual(after["receipt"]["safe_change_count"], 1)
        self.assertGreater(after["receipt"]["decision_credit_total_nats"], 0)
        alpha = credit.apply_active_evidence(
            state["catalog"],
            [observation("Alpha", "2021", "alpha-active.example")],
        )
        self.assertEqual(alpha["receipt"]["safe_change_count"], 0)
        self.assertEqual(alpha["receipt"]["decision_credit_total_nats"], 0)

    def test_context_changes_only_concrete_choice_and_restores_binding(self) -> None:
        state = competing_state()
        original = legacy._build_plan
        self.assertEqual(neutral.build_target_plan(state)["row_key"], "Alpha")
        with DecisionReachabilityPlanner() as planner:
            value = neutral.build_target_plan(state)
            assert value is not None
            self.assertEqual(value["row_key"], "Beta")
            neutral.validate_target_plan(value, active_result=state)
        self.assertIs(legacy._build_plan, original)
        self.assertEqual(neutral.build_target_plan(state)["row_key"], "Alpha")
        receipt = validate_receipt(planner.content_free_receipt())
        self.assertGreaterEqual(receipt["one_observation_plan_calls"], 1)
        self.assertGreaterEqual(receipt["legacy_entropy_choice_changed_calls"], 1)

    def test_neutral_discovery_fallback_and_thresholds_are_preserved(self) -> None:
        state = empty_state()
        with DecisionReachabilityPlanner() as planner:
            value = neutral.build_target_plan(state)
            assert value is not None
            self.assertEqual(value["seed_mode"], "cell_discovery")
            self.assertEqual(value["support_deficit"], 3)
            neutral.validate_target_plan(value, active_result=state)
        receipt = validate_receipt(planner.content_free_receipt())
        self.assertGreaterEqual(receipt["no_reachable_plan_calls"], 1)
        self.assertTrue(
            receipt[
                "source_count_active_support_posterior_margin_leave_one_out_safe_change_and_decision_credit_rules_unchanged"
            ]
        )

    def test_plan_tamper_and_binding_drift_fail_closed(self) -> None:
        state = competing_state()
        plan = build_target_plan(state)
        assert plan is not None
        changed = copy.deepcopy(plan)
        changed["support_deficit"] = 2
        with self.assertRaises(ValueError):
            validate_target_plan(changed, active_result=state)
        with patch.object(legacy, "_build_plan", lambda _value: None):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                DecisionReachabilityPlanner().__enter__()

    def test_exit_binding_drift_restores_frozen_planner_before_failure(self) -> None:
        planner = DecisionReachabilityPlanner()
        planner.__enter__()
        legacy._build_plan = lambda _value: None
        with self.assertRaisesRegex(RuntimeError, "installed planner binding drifted"):
            planner.__exit__(None, None, None)
        self.assertIs(legacy._build_plan, target.ORIGINAL_BUILD_PLAN)

    def test_receipt_tamper_and_runtime_source_are_label_blind(self) -> None:
        state = competing_state()
        with DecisionReachabilityPlanner() as planner:
            neutral.build_target_plan(state)
        receipt = planner.content_free_receipt()
        changed = copy.deepcopy(receipt)
        changed[
            "projection_is_reachability_not_expected_utility_or_causality"
        ] = False
        with self.assertRaises(ValueError):
            validate_receipt(changed)
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24555_decision_reachability_planner.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
