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
from deepwide_agent import v24490_entropy_targeted_support_search as targeted  # noqa: E402
from deepwide_agent.v24510_proposal_seeded_entropy_target_planner import (  # noqa: E402
    ProposalSeededTargetPlanner,
    build_target_plan,
    validate_receipt,
    validate_target_plan,
)


BASELINE = """```markdown
| Software | Initial release year |
| --- | --- |
| Alpha | 2020 |
```"""


def observation(value: str, host: str) -> dict:
    return {
        "row_key": "Alpha",
        "column": "Initial release year",
        "value": value,
        "source_host": host,
        "fetch_integrity": True,
    }


def proposal_only(*, proposals: tuple[str, ...] = ("2021",)) -> dict:
    catalog = credit.build_uncertainty_catalog(
        BASELINE,
        [
            observation(value, f"proposal-{ordinal}.example")
            for ordinal, value in enumerate(proposals, start=1)
        ],
    )
    return credit.apply_active_evidence(catalog, [])


class V24510ProposalSeededEntropyTargetPlannerTests(unittest.TestCase):
    def test_proposal_only_dead_zone_gets_reachable_label_blind_plan(self) -> None:
        state = proposal_only()
        self.assertIsNone(targeted.build_target_plan(state))
        plan = build_target_plan(state)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan["seed_mode"], "proposal_seeded")
        self.assertEqual(plan["leading_alternative"], "2021")
        self.assertEqual(plan["current_alternative_proposal_support_count"], 1)
        self.assertEqual(plan["current_alternative_active_support_count"], 0)
        self.assertEqual(plan["support_deficit"], 2)
        self.assertEqual(plan["maximum_targeted_fetches"], 2)
        self.assertGreaterEqual(
            plan[
                "projected_alternative_posterior_probability_after_planned_support"
            ],
            credit.MINIMUM_ALTERNATIVE_POSTERIOR,
        )
        validate_target_plan(plan, active_result=state)

    def test_query_seed_does_not_receive_active_or_decision_credit(self) -> None:
        state = proposal_only()
        plan = build_target_plan(state)
        self.assertIsNotNone(plan)
        self.assertEqual(state["receipt"]["active_observation_count"], 0)
        self.assertEqual(state["receipt"]["source_credit_record_count"], 0)
        self.assertEqual(state["receipt"]["safe_change_count"], 0)
        self.assertEqual(state["receipt"]["decision_credit_total_nats"], 0)
        one = credit.apply_active_evidence(
            state["catalog"], [observation("2021", "active-one.example")]
        )
        self.assertEqual(one["receipt"]["safe_change_count"], 0)
        self.assertEqual(one["receipt"]["decision_credit_total_nats"], 0)
        two = credit.apply_active_evidence(
            state["catalog"],
            [
                observation("2021", "active-one.example"),
                observation("2021", "active-two.example"),
            ],
        )
        self.assertEqual(two["receipt"]["safe_change_count"], 1)
        self.assertGreater(two["receipt"]["decision_credit_total_nats"], 0)
        self.assertEqual(
            len(two["resolutions"][0]["source_credit_records"]), 2
        )

    def test_unreachable_or_ambiguous_proposal_does_not_plan(self) -> None:
        state = proposal_only(proposals=("2021", "2022"))
        plan = build_target_plan(state)
        self.assertIsNone(plan)
        empty = credit.apply_active_evidence(
            credit.build_uncertainty_catalog(BASELINE, []), []
        )
        self.assertIsNone(build_target_plan(empty))

    def test_context_patches_exact_bindings_and_restores_on_every_exit(self) -> None:
        originals = (
            targeted.build_target_plan,
            targeted.build_target_plan_without_validation,
            targeted.validate_target_plan,
        )
        state = proposal_only()
        with ProposalSeededTargetPlanner() as planner:
            plan = targeted.build_target_plan(state)
            self.assertIsNotNone(plan)
            assert plan is not None
            targeted.validate_target_plan(plan, active_result=state)
            self.assertEqual(
                targeted.build_target_plan_without_validation(state), plan
            )
        for current, original in zip(
            (
                targeted.build_target_plan,
                targeted.build_target_plan_without_validation,
                targeted.validate_target_plan,
            ),
            originals,
        ):
            self.assertIs(current, original)
        receipt = validate_receipt(planner.content_free_receipt())
        self.assertEqual(receipt["proposal_seeded_plan_builds"], 1)
        self.assertGreaterEqual(receipt["validation_calls"], 2)
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with ProposalSeededTargetPlanner():
                raise RuntimeError("boom")
        self.assertIs(targeted.build_target_plan, originals[0])

    def test_plan_tamper_and_binding_drift_fail_closed(self) -> None:
        state = proposal_only()
        plan = build_target_plan(state)
        assert plan is not None
        for name, value in (
            ("seed_mode", "active_supported"),
            ("support_deficit", 1),
            ("minimum_new_active_support_count", 0),
        ):
            changed = copy.deepcopy(plan)
            changed[name] = value
            with self.assertRaises(ValueError):
                validate_target_plan(changed, active_result=state)
        with patch.object(targeted, "build_target_plan", lambda value: None):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                ProposalSeededTargetPlanner().__enter__()

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path(
                "src/deepwide_agent/v24510_proposal_seeded_entropy_target_planner.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
