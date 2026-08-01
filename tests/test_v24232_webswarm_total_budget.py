from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24231_webswarm_guidance_baseline import (  # noqa: E402
    build_guidance_ablation_bundle,
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
    object_sha256 as guidance_sha256,
)
from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    apply_budget_charge,
    build_budget_start_bundle,
    build_cost_vector,
    build_shared_total_budget_contract,
    initialize_arm_budget_ledger,
    object_sha256,
    validate_arm_budget_ledger,
    validate_budget_start_bundle,
    validate_budget_transition,
    validate_shared_total_budget_contract,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def contract(**overrides: int) -> dict[str, object]:
    caps = {
        "model_calls": 100,
        "model_attempts": 120,
        "search_calls": 100,
        "fetch_calls": 200,
        "other_tool_calls": 100,
        "orchestrator_calls": 100,
        "input_tokens": 100_000,
        "output_tokens": 20_000,
        "wall_milliseconds": 1_000_000,
    }
    caps.update(overrides)
    return build_shared_total_budget_contract(**caps)


def guidance_policy(
    budget: dict[str, object],
) -> dict[str, object]:
    return build_guidance_policy(
        selection_protocol_sha256=digest("selection"),
        model_contract_sha256=digest("model"),
        search_fetch_contract_sha256=digest("search-fetch"),
        total_budget_contract_sha256=str(budget["contract_sha256"]),
        root_scope_projection_protocol_sha256=digest("root-projection"),
        process_signal_vocabulary_sha256=digest("process-vocabulary"),
    )


def signal(kind: str, tactic: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": tactic, "value_sha256": digest(label)}


def probe(policy: dict[str, object]) -> dict[str, object]:
    return build_web_probe_receipt(
        policy=policy,
        root_scope_projection_sha256=digest("root"),
        parent_node_ref_sha256=digest("parent"),
        probe_run_ref_sha256=digest("probe"),
        topology="distributed",
        probe_search_calls=3,
        probe_fetch_calls=2,
        probe_model_calls=1,
        probe_input_tokens=100,
        probe_output_tokens=20,
        probe_wall_seconds=4.0004,
    )


def scout(policy: dict[str, object], slot: int) -> dict[str, object]:
    return build_scout_process_trace(
        policy=policy,
        root_scope_projection_sha256=digest("root"),
        parent_node_ref_sha256=digest("parent"),
        homogeneous_group_ref_sha256=digest("group"),
        scout_slot=slot,
        sibling_node_ref_sha256=digest(f"sibling-{slot}"),
        sibling_mode_sha256=digest("mode"),
        process_signals=[
            signal(
                "effective_query_pattern",
                "combine_visible_entity_and_attribute_terms",
                f"query-{slot}",
            )
        ],
        model_calls=1,
        search_calls=1,
        fetch_calls=1,
        input_tokens=10,
        output_tokens=5,
        wall_seconds=1.0,
        scout_terminal_status="completed",
    )


def experience(
    policy: dict[str, object], scouts: list[dict[str, object]]
) -> dict[str, object]:
    return build_sibling_process_experience(
        policy=policy,
        scouts=scouts,
        experience_extractor_ref_sha256=digest("extractor"),
        process_signals=[
            signal(
                "workflow_hint",
                "verify_with_independent_source",
                "workflow",
            )
        ],
        extractor_model_calls=1,
        extractor_input_tokens=300,
        extractor_output_tokens=30,
        extractor_wall_seconds=2.0002,
    )


def guidance(
    budget: dict[str, object],
) -> tuple[
    dict[str, object],
    dict[str, object],
    list[dict[str, object]],
    dict[str, dict[str, object]],
]:
    policy = guidance_policy(budget)
    probe_value = probe(policy)
    scouts = [scout(policy, 1), scout(policy, 2)]
    experience_value = experience(policy, scouts)
    shared = {
        "policy": policy,
        "root_scope_projection_sha256": digest("root"),
        "parent_node_ref_sha256": digest("parent"),
        "homogeneous_group_ref_sha256": digest("group"),
        "sibling_count": 8,
    }
    arm_values = [
        build_guidance_arm(
            **shared,
            arm_name="full",
            arm_ref_sha256=digest("arm-full"),
            scouts=scouts,
            probe=probe_value,
            experience=experience_value,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_probing",
            arm_ref_sha256=digest("arm-no-probing"),
            scouts=scouts,
            probe=None,
            experience=experience_value,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_experience_upstream",
            arm_ref_sha256=digest("arm-no-experience-upstream"),
            scouts=[],
            probe=probe_value,
            experience=None,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_experience_matched_schedule",
            arm_ref_sha256=digest("arm-no-experience-matched"),
            scouts=scouts,
            probe=probe_value,
            experience=None,
        ),
    ]
    bundle = build_guidance_ablation_bundle(
        policy=policy,
        bundle_ref_sha256=digest("guidance-bundle"),
        arms=arm_values,
    )
    sources = {
        "full": {
            "scouts": scouts,
            "probe": probe_value,
            "experience": experience_value,
        },
        "no_probing": {
            "scouts": scouts,
            "probe": None,
            "experience": experience_value,
        },
        "no_experience_upstream": {
            "scouts": [],
            "probe": probe_value,
            "experience": None,
        },
        "no_experience_matched_schedule": {
            "scouts": scouts,
            "probe": probe_value,
            "experience": None,
        },
    }
    return policy, bundle, arm_values, sources


def ledger(
    budget: dict[str, object],
    policy: dict[str, object],
    arm: dict[str, object],
    source: dict[str, object],
) -> dict[str, object]:
    return initialize_arm_budget_ledger(
        contract=budget,
        guidance_policy=policy,
        arm=arm,
        scouts=source["scouts"],
        probe=source["probe"],
        experience=source["experience"],
        charge_ref_sha256=digest(f"overhead-{arm['arm_name']}"),
        method_overhead_model_attempts=arm["probe_extractor_cost"]["model_calls"],
        method_overhead_other_tool_calls=0,
        method_overhead_orchestrator_calls=1,
    )


def execution_cost(**overrides: int) -> dict[str, int]:
    values = {
        "model_calls": 1,
        "model_attempts": 1,
        "search_calls": 1,
        "fetch_calls": 2,
        "other_tool_calls": 0,
        "orchestrator_calls": 1,
        "input_tokens": 100,
        "output_tokens": 20,
        "wall_milliseconds": 1000,
    }
    values.update(overrides)
    return build_cost_vector(**values)


class V24232WebSwarmTotalBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.budget = contract()
        self.policy, self.guidance_bundle, self.arms, self.sources = guidance(
            self.budget
        )
        self.by_name = {arm["arm_name"]: arm for arm in self.arms}

    def test_contract_is_exact_positive_and_build_only(self) -> None:
        validate_shared_total_budget_contract(self.budget)
        self.assertEqual(
            self.budget["cost_dimensions"],
            [
                "model_calls",
                "model_attempts",
                "search_calls",
                "fetch_calls",
                "other_tool_calls",
                "orchestrator_calls",
                "input_tokens",
                "output_tokens",
                "wall_milliseconds",
            ],
        )
        self.assertEqual(self.budget["wall_rounding"], "ceil_each_source_charge")
        self.assertFalse(self.budget["runtime_budget_wrapper_implemented"])
        self.assertFalse(
            self.budget["pre_side_effect_ordering_independently_verified"]
        )
        self.assertFalse(
            self.budget["caller_reported_execution_cost_independently_verified"]
        )
        self.assertFalse(
            self.budget[
                "method_overhead_attempts_extra_tools_independently_verified"
            ]
        )
        for key in (
            "production_package_authorized",
            "active_forward_integration_authorized",
            "benchmark_forward_or_evaluator_authorized",
            "dev64_or_exact220_launch_authorized",
            "shared_api_lease_acquire_authorized",
            "leaderboard_submission_or_sota_claim_authorized",
        ):
            self.assertFalse(self.budget[key], key)
        with self.assertRaisesRegex(ValueError, "every shared budget cap"):
            contract(search_calls=0)
        with self.assertRaisesRegex(ValueError, "attempts are below"):
            contract(model_calls=3, model_attempts=2)

    def test_initial_ledgers_debit_exact_guidance_overhead(self) -> None:
        expected = {
            "full": (2, 3, 2, 400, 50, 6002),
            "no_probing": (1, 0, 0, 300, 30, 2001),
            "no_experience_upstream": (1, 3, 2, 100, 20, 4001),
            "no_experience_matched_schedule": (1, 3, 2, 100, 20, 4001),
        }
        for name, arm in self.by_name.items():
            with self.subTest(name=name):
                value = ledger(
                    self.budget,
                    self.policy,
                    arm,
                    self.sources[name],
                )
                validate_arm_budget_ledger(
                    value,
                    contract=self.budget,
                    guidance_policy=self.policy,
                    guidance_arm=arm,
                    scouts=self.sources[name]["scouts"],
                    probe=self.sources[name]["probe"],
                    experience=self.sources[name]["experience"],
                )
                self.assertEqual(value["charge_count"], 1)
                self.assertTrue(value["method_overhead_charged_first"])
                self.assertFalse(value["hard_stop_required"])
                fields = expected[name]
                self.assertEqual(value["totals"]["model_calls"], fields[0])
                self.assertEqual(value["totals"]["search_calls"], fields[1])
                self.assertEqual(value["totals"]["fetch_calls"], fields[2])
                self.assertEqual(value["totals"]["input_tokens"], fields[3])
                self.assertEqual(value["totals"]["output_tokens"], fields[4])
                self.assertEqual(value["totals"]["wall_milliseconds"], fields[5])
                self.assertEqual(value["totals"]["orchestrator_calls"], 1)

    def test_charge_transition_is_hash_chained_and_additive(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        first = ledger(self.budget, self.policy, arm, source)
        cost = execution_cost()
        second = apply_budget_charge(
            first,
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_arm=arm,
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
            charge_kind="fanout_execution",
            charge_ref_sha256=digest("fanout-1"),
            source_cost_sha256=digest("fanout-cost-1"),
            cost=cost,
        )
        validate_budget_transition(
            first,
            second,
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_arm=arm,
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
            charge_kind="fanout_execution",
            charge_ref_sha256=digest("fanout-1"),
            source_cost_sha256=digest("fanout-cost-1"),
            cost=cost,
        )
        self.assertEqual(second["charge_count"], 2)
        self.assertEqual(
            second["charges"][1]["previous_charge_sha256"],
            first["charges"][0]["charge_sha256"],
        )
        for dimension, amount in cost.items():
            self.assertEqual(
                second["totals"][dimension], first["totals"][dimension] + amount
            )

        second["charges"][0]["cost"]["search_calls"] = 999
        self.assertEqual(first["charges"][0]["cost"]["search_calls"], 3)

    def test_duplicate_zero_unknown_and_over_cap_charges_fail_closed(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        first = ledger(self.budget, self.policy, arm, source)
        shared = {
            "contract": self.budget,
            "guidance_policy": self.policy,
            "guidance_arm": arm,
            "scouts": source["scouts"],
            "probe": source["probe"],
            "experience": source["experience"],
            "source_cost_sha256": digest("source"),
        }
        with self.assertRaisesRegex(ValueError, "duplicate charge"):
            apply_budget_charge(
                first,
                **shared,
                charge_kind="fanout_execution",
                charge_ref_sha256=first["charges"][0]["charge_ref_sha256"],
                cost=execution_cost(),
            )
        with self.assertRaisesRegex(ValueError, "zero-cost"):
            apply_budget_charge(
                first,
                **shared,
                charge_kind="fanout_execution",
                charge_ref_sha256=digest("zero"),
                cost=build_cost_vector(
                    model_calls=0,
                    model_attempts=0,
                    search_calls=0,
                    fetch_calls=0,
                    other_tool_calls=0,
                    orchestrator_calls=0,
                    input_tokens=0,
                    output_tokens=0,
                    wall_milliseconds=0,
                ),
            )
        with self.assertRaisesRegex(ValueError, "execution charge kind"):
            apply_budget_charge(
                first,
                **shared,
                charge_kind="method_overhead",
                charge_ref_sha256=digest("second-overhead"),
                cost=execution_cost(),
            )
        with self.assertRaisesRegex(ValueError, "cap exceeded"):
            apply_budget_charge(
                first,
                **shared,
                charge_kind="fanout_execution",
                charge_ref_sha256=digest("over-cap"),
                cost=execution_cost(search_calls=98),
            )

    def test_every_cost_dimension_is_enforced(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        first = ledger(self.budget, self.policy, arm, source)
        for dimension in self.budget["cost_dimensions"]:
            with self.subTest(dimension=dimension):
                values = {key: 0 for key in self.budget["cost_dimensions"]}
                values[dimension] = first["remaining"][dimension] + 1
                if dimension == "model_calls":
                    values["model_attempts"] = values["model_calls"]
                cost = build_cost_vector(**values)
                with self.assertRaisesRegex(ValueError, "cap exceeded"):
                    apply_budget_charge(
                        first,
                        contract=self.budget,
                        guidance_policy=self.policy,
                        guidance_arm=arm,
                        scouts=source["scouts"],
                        probe=source["probe"],
                        experience=source["experience"],
                        charge_kind="fanout_execution",
                        charge_ref_sha256=digest(f"over-{dimension}"),
                        source_cost_sha256=digest(f"source-{dimension}"),
                        cost=cost,
                    )

    def test_exact_cap_requires_hard_stop_and_post_stop_charge_fails(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        first = ledger(self.budget, self.policy, arm, source)
        exact = apply_budget_charge(
            first,
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_arm=arm,
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
            charge_kind="fanout_execution",
            charge_ref_sha256=digest("exact"),
            source_cost_sha256=digest("exact-source"),
            cost=execution_cost(search_calls=97),
        )
        self.assertEqual(exact["remaining"]["search_calls"], 0)
        self.assertTrue(exact["hard_stop_required"])
        with self.assertRaisesRegex(ValueError, "already reached a hard stop"):
            apply_budget_charge(
                exact,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
                charge_kind="renderer",
                charge_ref_sha256=digest("after-stop"),
                source_cost_sha256=digest("after-stop-source"),
                cost=execution_cost(search_calls=0),
            )

        resealed = copy.deepcopy(exact)
        post_stop = copy.deepcopy(resealed["charges"][-1])
        post_stop["sequence_index"] = 3
        post_stop["previous_charge_sha256"] = resealed["charges"][-1][
            "charge_sha256"
        ]
        post_stop["charge_ref_sha256"] = digest("resealed-after-stop")
        post_stop["source_cost_sha256"] = digest("resealed-after-stop-source")
        post_stop["cost"] = execution_cost(search_calls=0)
        post_stop.pop("charge_sha256")
        post_stop["charge_sha256"] = object_sha256(post_stop)
        resealed["charges"].append(post_stop)
        resealed["charge_count"] = 3
        for dimension, amount in post_stop["cost"].items():
            resealed["totals"][dimension] += amount
            resealed["remaining"][dimension] -= amount
        resealed.pop("ledger_sha256")
        resealed["ledger_sha256"] = object_sha256(resealed)
        with self.assertRaisesRegex(ValueError, "follows a hard stop"):
            validate_arm_budget_ledger(
                resealed,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
            )

    def test_tamper_reseal_and_joint_underreporting_are_rejected(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        value = ledger(self.budget, self.policy, arm, source)
        bad = copy.deepcopy(value)
        bad["charges"][0]["cost"]["search_calls"] = 0
        bad["charges"][0].pop("charge_sha256")
        bad["charges"][0]["charge_sha256"] = object_sha256(bad["charges"][0])
        bad["totals"]["search_calls"] = 0
        bad["remaining"]["search_calls"] = self.budget["caps"]["search_calls"]
        bad.pop("ledger_sha256")
        bad["ledger_sha256"] = object_sha256(bad)
        with self.assertRaisesRegex(ValueError, "method overhead differs"):
            validate_arm_budget_ledger(
                bad,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
            )

        wrong_arm = copy.deepcopy(arm)
        wrong_arm["probe_extractor_cost"]["search_calls"] = 0
        wrong_arm.pop("arm_sha256")
        wrong_arm["arm_sha256"] = guidance_sha256(wrong_arm)
        bad["arm_sha256"] = wrong_arm["arm_sha256"]
        bad["charges"][0]["arm_sha256"] = wrong_arm["arm_sha256"]
        bad["charges"][0].pop("charge_sha256")
        bad["charges"][0]["charge_sha256"] = object_sha256(bad["charges"][0])
        bad.pop("ledger_sha256")
        bad["ledger_sha256"] = object_sha256(bad)
        with self.assertRaises(ValueError):
            validate_arm_budget_ledger(
                bad,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=wrong_arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
            )

    def test_hash_chain_reordering_or_deletion_is_rejected(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        first = ledger(self.budget, self.policy, arm, source)
        second = apply_budget_charge(
            first,
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_arm=arm,
            scouts=source["scouts"],
            probe=source["probe"],
            experience=source["experience"],
            charge_kind="fanout_execution",
            charge_ref_sha256=digest("fanout"),
            source_cost_sha256=digest("fanout-source"),
            cost=execution_cost(),
        )
        tampered = copy.deepcopy(second)
        tampered["charges"][1]["previous_charge_sha256"] = digest("wrong")
        tampered["charges"][1].pop("charge_sha256")
        tampered["charges"][1]["charge_sha256"] = object_sha256(
            tampered["charges"][1]
        )
        tampered.pop("ledger_sha256")
        tampered["ledger_sha256"] = object_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "hash chain"):
            validate_arm_budget_ledger(
                tampered,
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
            )

    def test_exact_schemas_and_cross_contract_binding_fail_closed(self) -> None:
        arm = self.by_name["full"]
        source = self.sources["full"]
        value = ledger(self.budget, self.policy, arm, source)
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_shared_total_budget_contract({**self.budget, "extra": False})
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_arm_budget_ledger(
                {**value, "extra": False},
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
            )

        other_budget = contract(input_tokens=200_000)
        with self.assertRaises(ValueError):
            validate_arm_budget_ledger(
                value,
                contract=other_budget,
                guidance_policy=self.policy,
                guidance_arm=arm,
                scouts=source["scouts"],
                probe=source["probe"],
                experience=source["experience"],
            )

    def test_four_arm_start_bundle_has_identical_caps_and_nonempty_capacity(self) -> None:
        ledgers = [
            ledger(
                self.budget,
                self.policy,
                arm,
                self.sources[str(arm["arm_name"])],
            )
            for arm in self.arms
        ]
        value = build_budget_start_bundle(
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_bundle=self.guidance_bundle,
            guidance_bundle_ref_sha256=digest("guidance-bundle"),
            guidance_arms=self.arms,
            guidance_sources=self.sources,
            ledgers=list(reversed(ledgers)),
        )
        validate_budget_start_bundle(
            value,
            contract=self.budget,
            guidance_policy=self.policy,
            guidance_bundle=self.guidance_bundle,
            guidance_bundle_ref_sha256=digest("guidance-bundle"),
            guidance_arms=self.arms,
            guidance_sources=self.sources,
            ledgers=ledgers,
        )
        self.assertTrue(value["exact_arm_set"])
        self.assertTrue(value["identical_caps_across_arms"])
        self.assertTrue(value["method_overhead_charged_first_for_all_arms"])
        self.assertFalse(value["runtime_budget_enforcement_integrated"])
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_budget_start_bundle(
                {**value, "extra": False},
                contract=self.budget,
                guidance_policy=self.policy,
                guidance_bundle=self.guidance_bundle,
                guidance_bundle_ref_sha256=digest("guidance-bundle"),
                guidance_arms=self.arms,
                guidance_sources=self.sources,
                ledgers=ledgers,
            )

    def test_start_bundle_rejects_overhead_that_exhausts_a_cap(self) -> None:
        tight = contract(search_calls=3)
        policy, guidance_bundle, arms, sources = guidance(tight)
        ledgers = [
            ledger(tight, policy, arm, sources[str(arm["arm_name"])])
            for arm in arms
        ]
        with self.assertRaisesRegex(ValueError, "exhausts a shared cap"):
            build_budget_start_bundle(
                contract=tight,
                guidance_policy=policy,
                guidance_bundle=guidance_bundle,
                guidance_bundle_ref_sha256=digest("guidance-bundle"),
                guidance_arms=arms,
                guidance_sources=sources,
                ledgers=ledgers,
            )

    def test_all_authorizations_remain_false(self) -> None:
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(ACTIVE_FORWARD_INTEGRATION_AUTHORIZED)
        self.assertFalse(BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED)
        self.assertFalse(DEV64_OR_EXACT220_LAUNCH_AUTHORIZED)
        self.assertFalse(SHARED_API_LEASE_ACQUIRE_AUTHORIZED)
        self.assertFalse(LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED)


if __name__ == "__main__":
    unittest.main()
