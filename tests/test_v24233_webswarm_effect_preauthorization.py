from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_budget_start_bundle,
    build_cost_vector,
    object_sha256,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    build_effect_preauthorization_start_bundle,
    initialize_effect_preauthorization_state,
    issue_effect_permit,
    settle_effect_permit,
    validate_effect_preauthorization_start_bundle,
    validate_effect_preauthorization_state,
    validate_effect_preauthorization_transition,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract,
    digest,
    guidance,
    ledger,
)


def cost(**overrides: int) -> dict[str, int]:
    values = {
        "model_calls": 1,
        "model_attempts": 2,
        "search_calls": 3,
        "fetch_calls": 4,
        "other_tool_calls": 1,
        "orchestrator_calls": 1,
        "input_tokens": 500,
        "output_tokens": 100,
        "wall_milliseconds": 10_000,
    }
    values.update(overrides)
    return build_cost_vector(**values)


class V24233WebSwarmEffectPreauthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.budget = contract()
        self.policy, self.guidance_bundle, self.arms, self.sources = guidance(
            self.budget
        )
        self.by_name = {str(arm["arm_name"]): arm for arm in self.arms}
        self.arm = self.by_name["full"]
        self.source = self.sources["full"]
        self.initial_ledger = ledger(
            self.budget,
            self.policy,
            self.arm,
            self.source,
        )
        self.state = initialize_effect_preauthorization_state(
            initial_budget_ledger=self.initial_ledger,
            **self.shared,
        )

    @property
    def shared(self) -> dict[str, object]:
        return {
            "contract": self.budget,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    def issue(
        self,
        previous: dict[str, object] | None = None,
        *,
        suffix: str = "1",
        reserved: dict[str, int] | None = None,
    ) -> dict[str, object]:
        return issue_effect_permit(
            self.state if previous is None else previous,
            **self.shared,
            permit_ref_sha256=digest(f"permit-{suffix}"),
            charge_kind="fanout_execution",
            charge_ref_sha256=digest(f"charge-{suffix}"),
            estimate_source_sha256=digest(f"estimate-{suffix}"),
            reserved_cost=cost() if reserved is None else reserved,
        )

    def settle(
        self,
        previous: dict[str, object],
        *,
        permit_suffix: str = "1",
        settlement_suffix: str = "1",
        actual: dict[str, int] | None = None,
    ) -> dict[str, object]:
        return settle_effect_permit(
            previous,
            **self.shared,
            permit_ref_sha256=digest(f"permit-{permit_suffix}"),
            effect_receipt_sha256=digest(f"effect-{settlement_suffix}"),
            actual_cost_source_sha256=digest(f"actual-{settlement_suffix}"),
            actual_cost=cost(
                model_attempts=1,
                search_calls=2,
                fetch_calls=3,
                other_tool_calls=0,
                input_tokens=400,
                output_tokens=80,
                wall_milliseconds=8_000,
            )
            if actual is None
            else actual,
        )

    def validate(self, value: dict[str, object]) -> None:
        validate_effect_preauthorization_state(value, **self.shared)

    def test_initial_state_is_exact_empty_and_build_only(self) -> None:
        self.validate(self.state)
        self.assertTrue(self.state["build_only"])
        self.assertEqual(self.state["event_count"], 0)
        self.assertEqual(self.state["issued_permit_count"], 0)
        self.assertEqual(self.state["pending_permit_refs"], [])
        self.assertEqual(
            self.state["initial_budget_ledger_sha256"],
            self.initial_ledger["ledger_sha256"],
        )
        self.assertEqual(
            self.state["current_budget_ledger_sha256"],
            self.initial_ledger["ledger_sha256"],
        )
        for field in (
            "single_writer_compare_and_swap_independently_verified",
            "reserved_cost_independently_verified",
            "actual_cost_independently_measured",
            "provider_limits_enforce_reservation_independently_verified",
            "external_cost_overrun_prevented_independently_verified",
            "effect_after_permit_independently_verified",
            "runtime_effect_wrapper_integrated",
            "external_side_effect_authorized",
            "benchmark_forward_or_evaluator_authorized",
        ):
            self.assertFalse(self.state[field], field)

    def test_permit_charges_upper_bound_before_emission(self) -> None:
        current = self.issue()
        self.validate(current)
        validate_effect_preauthorization_transition(
            self.state,
            current,
            **self.shared,
        )
        permit = current["events"][0]
        self.assertTrue(permit["upper_bound_charged_before_permit_emission"])
        self.assertFalse(permit["external_side_effect_authorized"])
        self.assertEqual(current["event_count"], 1)
        self.assertEqual(current["issued_permit_count"], 1)
        self.assertEqual(current["settled_permit_count"], 0)
        self.assertEqual(
            current["pending_permit_refs"], [digest("permit-1")]
        )
        for dimension, amount in cost().items():
            self.assertEqual(
                current["current_budget_ledger"]["totals"][dimension],
                self.initial_ledger["totals"][dimension] + amount,
            )
            self.assertEqual(
                current["charged_upper_bound_totals"][dimension], amount
            )

    def test_settlement_is_single_use_bounded_and_does_not_refund(self) -> None:
        issued = self.issue()
        actual = cost(
            model_attempts=1,
            search_calls=2,
            fetch_calls=3,
            other_tool_calls=0,
            input_tokens=400,
            output_tokens=80,
            wall_milliseconds=8_000,
        )
        settled = self.settle(issued, actual=actual)
        self.validate(settled)
        validate_effect_preauthorization_transition(
            issued,
            settled,
            **self.shared,
        )
        receipt = settled["events"][-1]
        self.assertTrue(
            receipt["actual_cost_within_declared_charged_upper_bound"]
        )
        self.assertTrue(receipt["charged_budget_ledger_sha256_unchanged"])
        self.assertFalse(receipt["unused_reservation_refunded"])
        self.assertFalse(receipt["actual_cost_independently_measured"])
        self.assertEqual(
            settled["current_budget_ledger_sha256"],
            issued["current_budget_ledger_sha256"],
        )
        self.assertEqual(settled["pending_permit_refs"], [])
        self.assertEqual(settled["settled_permit_count"], 1)
        for dimension in actual:
            self.assertEqual(
                settled["settled_actual_totals"][dimension], actual[dimension]
            )
            self.assertEqual(
                settled["settled_unused_reservation_totals"][dimension],
                cost()[dimension] - actual[dimension],
            )
            self.assertEqual(
                settled["current_budget_ledger"]["totals"][dimension],
                issued["current_budget_ledger"]["totals"][dimension],
            )
        with self.assertRaisesRegex(ValueError, "absent or already settled"):
            self.settle(settled)

    def test_actual_cost_over_any_reserved_dimension_fails_closed(self) -> None:
        issued = self.issue()
        for dimension in self.budget["cost_dimensions"]:
            with self.subTest(dimension=dimension):
                actual = copy.deepcopy(cost())
                actual[dimension] += 1
                if dimension == "model_calls":
                    actual["model_attempts"] = actual["model_calls"]
                with self.assertRaisesRegex(ValueError, "exceeds the charged"):
                    self.settle(issued, actual=actual)

    def test_over_cap_zero_duplicate_and_unknown_reservations_fail(self) -> None:
        over = {key: 0 for key in self.budget["cost_dimensions"]}
        over["search_calls"] = self.initial_ledger["remaining"]["search_calls"] + 1
        with self.assertRaisesRegex(ValueError, "cap exceeded"):
            self.issue(reserved=build_cost_vector(**over))

        zero = {key: 0 for key in self.budget["cost_dimensions"]}
        with self.assertRaisesRegex(ValueError, "positive cost"):
            self.issue(reserved=build_cost_vector(**zero))

        issued = self.issue()
        with self.assertRaisesRegex(ValueError, "duplicate permit"):
            self.issue(issued)
        with self.assertRaisesRegex(ValueError, "duplicate charge"):
            issue_effect_permit(
                issued,
                **self.shared,
                permit_ref_sha256=digest("permit-2"),
                charge_kind="fanout_execution",
                charge_ref_sha256=digest("charge-1"),
                estimate_source_sha256=digest("estimate-2"),
                reserved_cost=cost(),
            )
        with self.assertRaisesRegex(ValueError, "absent or already settled"):
            self.settle(
                issued,
                permit_suffix="missing",
                settlement_suffix="missing",
            )

    def test_multiple_permits_are_serially_admitted_and_settle_out_of_order(self) -> None:
        first = self.issue(suffix="1")
        second = self.issue(first, suffix="2")
        self.assertEqual(second["event_count"], 2)
        self.assertEqual(second["issued_permit_count"], 2)
        self.assertEqual(
            second["pending_permit_refs"],
            [digest("permit-1"), digest("permit-2")],
        )
        self.assertEqual(
            second["events"][1]["previous_event_sha256"],
            second["events"][0]["permit_sha256"],
        )
        settle_second = self.settle(
            second,
            permit_suffix="2",
            settlement_suffix="2",
        )
        settle_first = self.settle(
            settle_second,
            permit_suffix="1",
            settlement_suffix="1",
        )
        self.validate(settle_first)
        self.assertEqual(settle_first["pending_permit_refs"], [])
        self.assertEqual(settle_first["settled_permit_count"], 2)
        self.assertTrue(
            settle_first["parallel_permits_supported_by_serial_admission"]
        )

    def test_one_effect_receipt_cannot_settle_two_permits(self) -> None:
        first = self.issue(suffix="1")
        second = self.issue(first, suffix="2")
        settled_first = self.settle(
            second,
            permit_suffix="1",
            settlement_suffix="shared",
        )
        with self.assertRaisesRegex(ValueError, "duplicate effect receipt"):
            self.settle(
                settled_first,
                permit_suffix="2",
                settlement_suffix="shared",
            )

    def test_exact_cap_blocks_new_permits_but_allows_pending_settlement(self) -> None:
        exact = cost(search_calls=self.initial_ledger["remaining"]["search_calls"])
        issued = self.issue(reserved=exact)
        self.assertTrue(issued["hard_stop_required"])
        with self.assertRaisesRegex(ValueError, "already reached a hard stop"):
            self.issue(issued, suffix="2")
        actual = copy.deepcopy(exact)
        actual["search_calls"] -= 1
        settled = self.settle(issued, actual=actual)
        self.validate(settled)
        self.assertTrue(settled["hard_stop_required"])
        self.assertEqual(settled["pending_permit_refs"], [])
        self.assertEqual(
            settled["current_budget_ledger_sha256"],
            issued["current_budget_ledger_sha256"],
        )

    def test_event_tamper_reseal_deletion_and_reordering_fail_closed(self) -> None:
        issued = self.issue()
        settled = self.settle(issued)

        tampered = copy.deepcopy(issued)
        tampered["events"][0]["reserved_cost"]["search_calls"] -= 1
        tampered["events"][0].pop("permit_sha256")
        tampered["events"][0]["permit_sha256"] = object_sha256(
            tampered["events"][0]
        )
        tampered.pop("state_sha256")
        tampered["state_sha256"] = object_sha256(tampered)
        with self.assertRaises(ValueError):
            self.validate(tampered)

        deleted = copy.deepcopy(settled)
        deleted["events"] = deleted["events"][1:]
        deleted["event_count"] = 1
        deleted.pop("state_sha256")
        deleted["state_sha256"] = object_sha256(deleted)
        with self.assertRaises(ValueError):
            self.validate(deleted)

        reordered = copy.deepcopy(settled)
        reordered["events"].reverse()
        reordered.pop("state_sha256")
        reordered["state_sha256"] = object_sha256(reordered)
        with self.assertRaises(ValueError):
            self.validate(reordered)

    def test_cross_contract_arm_and_extra_schema_fail_closed(self) -> None:
        issued = self.issue()
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            self.validate({**issued, "extra": False})

        other_budget = contract(input_tokens=200_000)
        with self.assertRaises(ValueError):
            validate_effect_preauthorization_state(
                issued,
                contract=other_budget,
                guidance_policy=self.policy,
                guidance_arm=self.arm,
                scouts=self.source["scouts"],
                probe=self.source["probe"],
                experience=self.source["experience"],
            )
        other_arm = self.by_name["no_probing"]
        other_source = self.sources["no_probing"]
        with self.assertRaises(ValueError):
            validate_effect_preauthorization_state(
                issued,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=other_arm,
                scouts=other_source["scouts"],
                probe=other_source["probe"],
                experience=other_source["experience"],
            )

    def test_four_arm_start_bundle_revalidates_v24232_budget_bundle(self) -> None:
        ledgers = [
            ledger(
                self.budget,
                self.policy,
                arm,
                self.sources[str(arm["arm_name"])],
            )
            for arm in self.arms
        ]
        budget_bundle = build_budget_start_bundle(
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_bundle=self.guidance_bundle,
            guidance_bundle_ref_sha256=digest("guidance-bundle"),
            guidance_arms=self.arms,
            guidance_sources=self.sources,
            ledgers=ledgers,
        )
        states = [
            initialize_effect_preauthorization_state(
                initial_budget_ledger=current,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=self.sources[str(arm["arm_name"])]["scouts"],
                probe=self.sources[str(arm["arm_name"])]["probe"],
                experience=self.sources[str(arm["arm_name"])]["experience"],
            )
            for arm, current in zip(self.arms, ledgers)
        ]
        shared = {
            "contract": self.budget,
            "guidance_policy": self.policy,
            "guidance_bundle": self.guidance_bundle,
            "guidance_bundle_ref_sha256": digest("guidance-bundle"),
            "guidance_arms": self.arms,
            "guidance_sources": self.sources,
            "budget_ledgers": ledgers,
            "budget_start_bundle": budget_bundle,
            "states": list(reversed(states)),
        }
        bundle = build_effect_preauthorization_start_bundle(**shared)
        validate_effect_preauthorization_start_bundle(bundle, **shared)
        self.assertEqual(set(bundle["arm_names"]), set(self.by_name))
        self.assertTrue(bundle["all_states_begin_without_effect_events"])
        self.assertFalse(bundle["runtime_effect_wrapper_integrated"])
        self.assertFalse(bundle["external_side_effect_authorized"])

        nonpristine = list(states)
        nonpristine[0] = self.issue(states[0])
        with self.assertRaisesRegex(ValueError, "not pristine"):
            build_effect_preauthorization_start_bundle(
                **{**shared, "states": nonpristine}
            )

    def test_all_authorizations_remain_false(self) -> None:
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(ACTIVE_FORWARD_INTEGRATION_AUTHORIZED)
        self.assertFalse(EXTERNAL_SIDE_EFFECT_AUTHORIZED)
        self.assertFalse(BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED)
        self.assertFalse(DEV64_OR_EXACT220_LAUNCH_AUTHORIZED)
        self.assertFalse(SHARED_API_LEASE_ACQUIRE_AUTHORIZED)
        self.assertFalse(LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED)


if __name__ == "__main__":
    unittest.main()
