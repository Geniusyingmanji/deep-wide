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
from deepwide_agent.v24515_neutral_cell_discovery_planner import (  # noqa: E402
    NeutralCellDiscoveryPlanner,
    build_target_plan,
    validate_receipt,
    validate_target_plan,
)
from test_v24510_proposal_seeded_entropy_target_planner import (  # noqa: E402
    BASELINE,
    observation,
    proposal_only,
)


def empty_state() -> dict:
    return credit.apply_active_evidence(
        credit.build_uncertainty_catalog(BASELINE, []), []
    )


class V24515NeutralCellDiscoveryPlannerTests(unittest.TestCase):
    def test_empty_alternative_dead_zone_gets_neutral_reachable_plan(self) -> None:
        state = empty_state()
        self.assertIsNone(targeted.build_target_plan(state))
        plan = build_target_plan(state)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan["seed_mode"], "cell_discovery")
        self.assertEqual(plan["leading_alternative"], "")
        self.assertEqual(plan["leading_alternative_hypothesis"], "")
        self.assertEqual(plan["current_alternative_support_count"], 0)
        self.assertEqual(plan["support_deficit"], 3)
        self.assertEqual(plan["maximum_targeted_fetches"], 3)
        self.assertFalse(plan["proposal_seed_used_for_query_only"])
        self.assertTrue(all("2021" not in query for query in plan["query_vector"]))
        self.assertTrue(all('""' not in query for query in plan["query_vector"]))
        validate_target_plan(plan, active_result=state)

    def test_discovery_seed_gets_no_credit_but_independent_pages_can(self) -> None:
        state = empty_state()
        plan = build_target_plan(state)
        self.assertIsNotNone(plan)
        self.assertEqual(state["receipt"]["active_observation_count"], 0)
        self.assertEqual(state["receipt"]["source_credit_record_count"], 0)
        self.assertEqual(state["receipt"]["decision_credit_total_nats"], 0)
        one = credit.apply_active_evidence(
            state["catalog"], [observation("2021", "discovery-one.example")]
        )
        self.assertEqual(one["receipt"]["safe_change_count"], 0)
        two = credit.apply_active_evidence(
            state["catalog"],
            [
                observation("2021", "discovery-one.example"),
                observation("2021", "discovery-two.example"),
            ],
        )
        self.assertEqual(two["receipt"]["safe_change_count"], 0)
        three = credit.apply_active_evidence(
            state["catalog"],
            [
                observation("2021", "discovery-one.example"),
                observation("2021", "discovery-two.example"),
                observation("2021", "discovery-three.example"),
            ],
        )
        self.assertEqual(three["receipt"]["safe_change_count"], 1)
        self.assertGreater(three["receipt"]["decision_credit_total_nats"], 0)
        self.assertEqual(len(three["resolutions"][0]["source_credit_records"]), 3)

    def test_existing_proposal_plan_is_preserved_before_discovery_fallback(self) -> None:
        state = proposal_only()
        plan = build_target_plan(state)
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertEqual(plan["seed_mode"], "proposal_seeded")
        self.assertEqual(plan["leading_alternative"], "2021")
        self.assertEqual(plan["support_deficit"], 2)
        self.assertTrue(plan["proposal_seed_used_for_query_only"])
        validate_target_plan(plan, active_result=state)

    def test_unreachable_current_consensus_does_not_discover(self) -> None:
        catalog = credit.build_uncertainty_catalog(
            BASELINE,
            [
                observation("2020", "current-one.example"),
                observation("2020", "current-two.example"),
                observation("2020", "current-three.example"),
            ],
        )
        state = credit.apply_active_evidence(catalog, [])
        self.assertIsNone(build_target_plan(state))

    def test_discovery_plan_tamper_fails_closed(self) -> None:
        state = empty_state()
        plan = build_target_plan(state)
        assert plan is not None
        for name, value in (
            ("leading_alternative", "2021"),
            ("support_deficit", 2),
            ("proposal_seed_used_for_query_only", True),
        ):
            changed = copy.deepcopy(plan)
            changed[name] = value
            with self.assertRaises(ValueError, msg=name):
                validate_target_plan(changed, active_result=state)

    def test_context_patches_exact_bindings_and_restores_with_receipt(self) -> None:
        originals = (
            targeted.build_target_plan,
            targeted.build_target_plan_without_validation,
            targeted.validate_target_plan,
        )
        state = empty_state()
        with NeutralCellDiscoveryPlanner() as planner:
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
        self.assertEqual(receipt["cell_discovery_plan_builds"], 1)
        self.assertFalse(receipt["cell_discovery_seed_value_present"])
        self.assertFalse(receipt["cell_discovery_receives_vote_or_source_credit"])
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with NeutralCellDiscoveryPlanner():
                raise RuntimeError("boom")
        self.assertIs(targeted.build_target_plan, originals[0])

    def test_binding_drift_and_runtime_source_fail_closed(self) -> None:
        with patch.object(targeted, "build_target_plan", lambda value: None):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                NeutralCellDiscoveryPlanner().__enter__()
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24515_neutral_cell_discovery_planner.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
