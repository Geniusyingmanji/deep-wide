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
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ARMS,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SCOUT_COUNT,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    build_guidance_ablation_bundle,
    build_guidance_arm,
    build_guidance_policy,
    build_scout_process_trace,
    build_sibling_process_experience,
    build_web_probe_receipt,
    object_sha256,
    reject_privileged_metadata,
    render_process_experience_prompt,
    validate_guidance_ablation_bundle,
    validate_guidance_arm,
    validate_guidance_policy,
    validate_scout_process_trace,
    validate_sibling_process_experience,
    validate_web_probe_receipt,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def policy() -> dict[str, object]:
    return build_guidance_policy(
        selection_protocol_sha256=digest("selection-protocol"),
        model_contract_sha256=digest("model-contract"),
        search_fetch_contract_sha256=digest("search-fetch-contract"),
        total_budget_contract_sha256=digest("total-budget-contract"),
        root_scope_projection_protocol_sha256=digest("root-projection"),
        process_signal_vocabulary_sha256=digest("process-vocabulary"),
    )


TACTICS = {
    "effective_query_pattern": "combine_visible_entity_and_attribute_terms",
    "ineffective_query_pattern": "avoid_broad_underspecified_query",
    "reliable_source_family": "prefer_official_primary_source",
    "unreliable_source_family": "avoid_unsupported_aggregator",
    "useful_page_type": "prefer_structured_table_page",
    "dead_end_page_type": "avoid_search_snippet_only",
    "workflow_hint": "verify_with_independent_source",
}


def signal(kind: str, label: str) -> dict[str, str]:
    return {"kind": kind, "tactic": TACTICS.get(kind, "invalid"), "value_sha256": digest(label)}


def probe(
    frozen: dict[str, object], *, topology: str = "distributed"
) -> dict[str, object]:
    return build_web_probe_receipt(
        policy=frozen,
        root_scope_projection_sha256=digest("root-scope"),
        parent_node_ref_sha256=digest("parent-node"),
        probe_run_ref_sha256=digest(f"probe-{topology}"),
        topology=topology,
        probe_search_calls=3,
        probe_fetch_calls=2,
        probe_model_calls=1,
        probe_input_tokens=100,
        probe_output_tokens=20,
        probe_wall_seconds=4.5,
    )


def scout(
    frozen: dict[str, object],
    *,
    slot: int,
    parent: str = "parent-node",
    group: str = "homogeneous-group",
    mode: str = "atom-mode",
    node: str | None = None,
) -> dict[str, object]:
    name = node or f"sibling-{slot}"
    return build_scout_process_trace(
        policy=frozen,
        root_scope_projection_sha256=digest("root-scope"),
        parent_node_ref_sha256=digest(parent),
        homogeneous_group_ref_sha256=digest(group),
        scout_slot=slot,
        sibling_node_ref_sha256=digest(name),
        sibling_mode_sha256=digest(mode),
        process_signals=[
            signal("effective_query_pattern", f"query-pattern-{slot}"),
            signal("reliable_source_family", f"source-family-{slot}"),
        ],
        model_calls=2,
        search_calls=3,
        fetch_calls=4,
        input_tokens=200,
        output_tokens=40,
        wall_seconds=8.0,
        scout_terminal_status="completed",
    )


def scouts(frozen: dict[str, object]) -> list[dict[str, object]]:
    return [scout(frozen, slot=1), scout(frozen, slot=2)]


def experience(
    frozen: dict[str, object],
    scout_values: list[dict[str, object]],
) -> dict[str, object]:
    return build_sibling_process_experience(
        policy=frozen,
        scouts=scout_values,
        experience_extractor_ref_sha256=digest("experience-extractor"),
        process_signals=[
            signal("effective_query_pattern", "shared-query-pattern"),
            signal("useful_page_type", "shared-page-type"),
            signal("workflow_hint", "shared-workflow-hint"),
        ],
        extractor_model_calls=1,
        extractor_input_tokens=300,
        extractor_output_tokens=30,
        extractor_wall_seconds=2.5,
    )


def arms(
    frozen: dict[str, object],
    scout_values: list[dict[str, object]],
    probe_value: dict[str, object],
    experience_value: dict[str, object],
) -> list[dict[str, object]]:
    shared = {
        "policy": frozen,
        "root_scope_projection_sha256": digest("root-scope"),
        "parent_node_ref_sha256": digest("parent-node"),
        "homogeneous_group_ref_sha256": digest("homogeneous-group"),
        "sibling_count": 8,
    }
    return [
        build_guidance_arm(
            **shared,
            arm_name="full",
            arm_ref_sha256=digest("arm-full"),
            scouts=scout_values,
            probe=probe_value,
            experience=experience_value,
        ),
        build_guidance_arm(
            **shared,
            arm_name="no_probing",
            arm_ref_sha256=digest("arm-no-probing"),
            scouts=scout_values,
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
            scouts=scout_values,
            probe=probe_value,
            experience=None,
        ),
    ]


class V24231WebSwarmGuidanceBaselineTests(unittest.TestCase):
    def test_policy_matches_public_webswarm_version_and_scope(self) -> None:
        value = policy()
        validate_guidance_policy(value)
        self.assertEqual(value["source_arxiv"], "2607.08662")
        self.assertEqual(value["source_version"], 1)
        self.assertEqual(
            value["source_repository_commit"],
            "40c9aacad7cd6e9cdb3e7add954d59b766425717",
        )
        self.assertEqual(value["scout_count"], SCOUT_COUNT)
        self.assertEqual(
            value["experience_scope"],
            "same_instance_same_parent_homogeneous_siblings_only",
        )
        self.assertFalse(value["test_or_benchmark_outcome_used_for_policy_selection"])
        self.assertFalse(value["runtime_label_routing_used"])

    def test_probe_topology_maps_to_frozen_process_tactics_and_counts_cost(self) -> None:
        frozen = policy()
        expected = {
            "centralized": "extract_hub_then_verify_gaps",
            "centralized_with_gaps": "extract_hub_then_target_visible_gaps",
            "distributed": "partition_visible_dimension_then_deduplicate",
        }
        for topology, tactic in expected.items():
            with self.subTest(topology=topology):
                value = probe(frozen, topology=topology)
                validate_web_probe_receipt(value, policy=frozen)
                self.assertEqual(value["process_tactic"], tactic)
                self.assertEqual(value["probe_search_calls"], 3)
                self.assertEqual(value["probe_fetch_calls"], 2)
                self.assertFalse(
                    value[
                        "raw_question_query_url_page_text_answer_prediction_or_evaluator_payload_embedded"
                    ]
                )

    def test_probe_rejects_unknown_topology_bad_cost_and_extra_schema(self) -> None:
        frozen = policy()
        with self.assertRaisesRegex(ValueError, "topology"):
            probe(frozen, topology="benchmark-specific")
        with self.assertRaises(ValueError):
            build_web_probe_receipt(
                policy=frozen,
                root_scope_projection_sha256=digest("root-scope"),
                parent_node_ref_sha256=digest("parent-node"),
                probe_run_ref_sha256=digest("probe"),
                topology="distributed",
                probe_search_calls=-1,
                probe_fetch_calls=0,
                probe_model_calls=0,
                probe_input_tokens=0,
                probe_output_tokens=0,
                probe_wall_seconds=0.0,
            )
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_web_probe_receipt(
                {**probe(frozen), "question_type": "hidden"}, policy=frozen
            )

    def test_scout_trace_accepts_only_typed_process_signal_hashes(self) -> None:
        frozen = policy()
        value = scout(frozen, slot=1)
        validate_scout_process_trace(value, policy=frozen)
        self.assertEqual(
            {row["kind"] for row in value["process_signals"]},
            {"effective_query_pattern", "reliable_source_family"},
        )
        self.assertFalse(value["raw_factual_value_visible_in_process_signal_schema"])
        self.assertFalse(value["process_fact_separation_independently_verified"])
        self.assertFalse(
            value[
                "raw_task_query_url_page_text_answer_prediction_or_evaluator_payload_embedded"
            ]
        )

    def test_scout_trace_rejects_invalid_slot_signal_duplicate_and_cost(self) -> None:
        frozen = policy()
        for slot in (0, 3, True):
            with self.subTest(slot=slot):
                with self.assertRaises(ValueError):
                    scout(frozen, slot=slot)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "vocabulary"):
            build_scout_process_trace(
                policy=frozen,
                root_scope_projection_sha256=digest("root-scope"),
                parent_node_ref_sha256=digest("parent-node"),
                homogeneous_group_ref_sha256=digest("group"),
                scout_slot=1,
                sibling_node_ref_sha256=digest("sibling"),
                sibling_mode_sha256=digest("mode"),
                process_signals=[signal("answer_fact", "raw-value")],
                model_calls=0,
                search_calls=0,
                fetch_calls=0,
                input_tokens=0,
                output_tokens=0,
                wall_seconds=0.0,
                scout_terminal_status="completed",
            )
        duplicate = signal("workflow_hint", "same")
        with self.assertRaisesRegex(ValueError, "duplicates"):
            build_scout_process_trace(
                policy=frozen,
                root_scope_projection_sha256=digest("root-scope"),
                parent_node_ref_sha256=digest("parent-node"),
                homogeneous_group_ref_sha256=digest("group"),
                scout_slot=1,
                sibling_node_ref_sha256=digest("sibling"),
                sibling_mode_sha256=digest("mode"),
                process_signals=[duplicate, duplicate],
                model_calls=0,
                search_calls=0,
                fetch_calls=0,
                input_tokens=0,
                output_tokens=0,
                wall_seconds=0.0,
                scout_terminal_status="completed",
            )

    def test_experience_requires_exactly_two_same_parent_homogeneous_scouts(self) -> None:
        frozen = policy()
        values = scouts(frozen)
        item = experience(frozen, values)
        validate_sibling_process_experience(item, policy=frozen, scouts=values)
        self.assertEqual(len(item["source_scout_trace_sha256s"]), 2)
        self.assertTrue(item["same_instance_only"])
        self.assertTrue(item["same_parent_only"])
        self.assertTrue(item["homogeneous_siblings_only"])
        self.assertTrue(item["remaining_siblings_only"])
        self.assertTrue(item["process_advice_schema_only"])
        self.assertFalse(item["factual_evidence_authority"])
        self.assertFalse(item["process_fact_separation_independently_verified"])

        for bad in ([values[0]], [values[0], values[1], values[0]]):
            with self.subTest(count=len(bad)):
                with self.assertRaisesRegex(ValueError, "exactly two"):
                    experience(frozen, bad)
        with self.assertRaisesRegex(ValueError, "same-parent homogeneous"):
            experience(
                frozen,
                [values[0], scout(frozen, slot=2, parent="different-parent")],
            )
        with self.assertRaisesRegex(ValueError, "same-parent homogeneous"):
            experience(
                frozen,
                [values[0], scout(frozen, slot=2, mode="different-mode")],
            )
        with self.assertRaisesRegex(ValueError, "not distinct"):
            experience(
                frozen,
                [values[0], scout(frozen, slot=2, node="sibling-1")],
            )

    def test_process_experience_renderer_is_generic_and_origin_validated(self) -> None:
        frozen = policy()
        values = scouts(frozen)
        item = experience(frozen, values)
        prompt = render_process_experience_prompt(
            experience=item,
            policy=frozen,
            scouts=values,
            root_scope_projection_sha256=digest("root-scope"),
            parent_node_ref_sha256=digest("parent-node"),
            homogeneous_group_ref_sha256=digest("homogeneous-group"),
        )
        self.assertEqual(
            prompt,
            "[SCOUT-DERIVED PROCESS ADVICE; NOT FACTUAL EVIDENCE]\n"
            "- combine visible entity and attribute terms.\n"
            "- prefer structured table page.\n"
            "- verify with independent source.\n"
            "Do not cite this advice as evidence. Verify all task facts from "
            "current page-backed sources.",
        )
        self.assertNotIn("shared-query-pattern", prompt)
        self.assertNotIn("shared-page-type", prompt)
        self.assertNotIn("shared-workflow-hint", prompt)
        self.assertNotIn("entity attribute pair", prompt)
        for row in item["process_signals"]:
            self.assertNotIn(row["value_sha256"], prompt)
        for label in ("root-scope", "parent-node", "homogeneous-group"):
            self.assertNotIn(digest(label), prompt)

        with self.assertRaisesRegex(ValueError, "experience prompt identity"):
            render_process_experience_prompt(
                experience=item,
                policy=frozen,
                scouts=values,
                root_scope_projection_sha256=digest("different-root"),
                parent_node_ref_sha256=digest("parent-node"),
                homogeneous_group_ref_sha256=digest("homogeneous-group"),
            )
        with self.assertRaisesRegex(ValueError, "sibling process experience contract"):
            render_process_experience_prompt(
                experience=item,
                policy=frozen,
                scouts=[values[0], scout(frozen, slot=2, node="replacement")],
                root_scope_projection_sha256=digest("root-scope"),
                parent_node_ref_sha256=digest("parent-node"),
                homogeneous_group_ref_sha256=digest("homogeneous-group"),
            )

    def test_full_and_no_probing_overhead_are_exact(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        values = arms(frozen, scout_values, probe_value, experience_value)
        by_name = {value["arm_name"]: value for value in values}

        full = by_name["full"]
        self.assertEqual(
            full["probe_extractor_cost"],
            {
                "model_calls": 2,
                "search_calls": 3,
                "fetch_calls": 2,
                "input_tokens": 400,
                "output_tokens": 50,
                "wall_seconds": 7.0,
            },
        )
        no_probe = by_name["no_probing"]
        self.assertEqual(
            no_probe["probe_extractor_cost"],
            {
                "model_calls": 1,
                "search_calls": 0,
                "fetch_calls": 0,
                "input_tokens": 300,
                "output_tokens": 30,
                "wall_seconds": 2.5,
            },
        )
        for value in values:
            self.assertTrue(value["method_specific_overhead_counted"])
            self.assertTrue(
                value["method_specific_overhead_debited_from_shared_total_cap"]
            )
            self.assertEqual(
                value["shared_total_budget_contract_sha256"],
                frozen["total_budget_contract_sha256"],
            )
            self.assertFalse(value["experience_has_factual_evidence_authority"])
            self.assertFalse(value["benchmark_metadata_available_to_forward"])
            self.assertFalse(value["benchmark_forward_or_evaluator_authorized"])

    def test_upstream_no_experience_and_matched_schedule_control_are_distinct(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        by_name = {
            value["arm_name"]: value
            for value in arms(frozen, scout_values, probe_value, experience_value)
        }
        upstream = by_name["no_experience_upstream"]
        matched = by_name["no_experience_matched_schedule"]
        self.assertEqual(upstream["scout_count"], 0)
        self.assertEqual(upstream["fanout_count"], upstream["sibling_count"])
        self.assertEqual(upstream["scout_trace_sha256s"], [])
        self.assertFalse(upstream["same_sibling_schedule"])
        self.assertEqual(matched["scout_count"], 2)
        self.assertEqual(matched["fanout_count"], matched["sibling_count"] - 2)
        self.assertEqual(len(matched["scout_trace_sha256s"]), 2)
        self.assertTrue(matched["same_sibling_schedule"])
        self.assertFalse(upstream["experience_reuse_enabled"])
        self.assertFalse(matched["experience_reuse_enabled"])

    def test_arm_switches_fail_closed(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        shared = {
            "policy": frozen,
            "arm_ref_sha256": digest("arm"),
            "root_scope_projection_sha256": digest("root-scope"),
            "parent_node_ref_sha256": digest("parent-node"),
            "homogeneous_group_ref_sha256": digest("homogeneous-group"),
            "sibling_count": 8,
        }
        with self.assertRaisesRegex(ValueError, "lacks a probe"):
            build_guidance_arm(
                **shared,
                arm_name="full",
                scouts=scout_values,
                probe=None,
                experience=experience_value,
            )
        with self.assertRaisesRegex(ValueError, "carries a probe"):
            build_guidance_arm(
                **shared,
                arm_name="no_probing",
                scouts=scout_values,
                probe=probe_value,
                experience=experience_value,
            )
        with self.assertRaisesRegex(ValueError, "scout schedule"):
            build_guidance_arm(
                **shared,
                arm_name="no_experience_upstream",
                scouts=scout_values,
                probe=probe_value,
                experience=None,
            )
        with self.assertRaisesRegex(ValueError, "carries experience"):
            build_guidance_arm(
                **shared,
                arm_name="no_experience_matched_schedule",
                scouts=scout_values,
                probe=probe_value,
                experience=experience_value,
            )

    def test_four_arm_bundle_freezes_budget_and_reports_schedule_confound(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        arm_values = arms(frozen, scout_values, probe_value, experience_value)
        value = build_guidance_ablation_bundle(
            policy=frozen,
            bundle_ref_sha256=digest("bundle"),
            arms=list(reversed(arm_values)),
        )
        validate_guidance_ablation_bundle(
            value,
            policy=frozen,
            bundle_ref_sha256=digest("bundle"),
            arms=arm_values,
        )
        self.assertEqual(tuple(value["arm_names"]), ARMS)
        self.assertTrue(value["exact_arm_set"])
        self.assertFalse(value["only_guidance_switches_differ"])
        self.assertTrue(value["upstream_no_experience_schedule_difference_disclosed"])
        self.assertTrue(value["matched_schedule_no_experience_control_present"])
        self.assertTrue(value["probe_and_extractor_overhead_included"])
        self.assertTrue(value["same_model_search_fetch_prompt_output_budget_attempts"])
        self.assertTrue(value["shared_total_budget_cap_includes_method_overhead"])
        self.assertTrue(value["future_reportable_score_requires_fresh_exact220"])
        self.assertTrue(value["failure_as_zero_no_resume_no_selective_retry"])
        self.assertFalse(value["quality_cost_or_benchmark_effect_observed"])
        self.assertFalse(value["leaderboard_submission_or_sota_claim_authorized"])

    def test_bundle_rejects_missing_duplicate_and_invariant_drift(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        arm_values = arms(frozen, scout_values, probe_value, experience_value)
        with self.assertRaisesRegex(ValueError, "exactly four"):
            build_guidance_ablation_bundle(
                policy=frozen,
                bundle_ref_sha256=digest("bundle"),
                arms=arm_values[:3],
            )
        with self.assertRaisesRegex(ValueError, "arm set"):
            build_guidance_ablation_bundle(
                policy=frozen,
                bundle_ref_sha256=digest("bundle"),
                arms=[arm_values[0], arm_values[0], arm_values[2], arm_values[3]],
            )
        drifted = copy.deepcopy(arm_values)
        drifted[1]["shared_model_contract_sha256"] = digest("different-model")
        drifted[1].pop("arm_sha256")
        drifted[1]["arm_sha256"] = object_sha256(drifted[1])
        with self.assertRaisesRegex(ValueError, "invariant drifted"):
            build_guidance_ablation_bundle(
                policy=frozen,
                bundle_ref_sha256=digest("bundle"),
                arms=drifted,
            )

        jointly_drifted = copy.deepcopy(arm_values)
        for arm in jointly_drifted:
            arm["benchmark_forward_or_evaluator_authorized"] = True
            arm.pop("arm_sha256")
            arm["arm_sha256"] = object_sha256(arm)
        with self.assertRaisesRegex(ValueError, "safe invariant drifted"):
            build_guidance_ablation_bundle(
                policy=frozen,
                bundle_ref_sha256=digest("bundle"),
                arms=jointly_drifted,
            )

        wrong_policy = copy.deepcopy(arm_values)
        for arm in wrong_policy:
            arm["policy_sha256"] = digest("different-policy")
            arm.pop("arm_sha256")
            arm["arm_sha256"] = object_sha256(arm)
        with self.assertRaisesRegex(ValueError, "safe invariant drifted"):
            build_guidance_ablation_bundle(
                policy=frozen,
                bundle_ref_sha256=digest("bundle"),
                arms=wrong_policy,
            )

        missing_full_experience = copy.deepcopy(arm_values)
        missing_full_experience[0]["experience_sha256"] = None
        missing_full_experience[0].pop("arm_sha256")
        missing_full_experience[0]["arm_sha256"] = object_sha256(
            missing_full_experience[0]
        )
        with self.assertRaisesRegex(ValueError, "ablation switches"):
            build_guidance_ablation_bundle(
                policy=frozen,
                bundle_ref_sha256=digest("bundle"),
                arms=missing_full_experience,
            )

    def test_privileged_nested_metadata_is_rejected(self) -> None:
        reject_privileged_metadata({"visible": {"objective_type": "enumeration"}})
        for forbidden in (
            {"safe": [{"question_type": "hidden"}]},
            {"safe": {"ground-truth": "hidden"}},
            {"safe": {"evaluator_score": 1}},
            {"safe": {"raw_page": "content"}},
            {"safe": {"url": "hidden"}},
            {"safe": {"reward": 1}},
        ):
            with self.subTest(forbidden=forbidden):
                with self.assertRaisesRegex(ValueError, "privileged runtime metadata"):
                    reject_privileged_metadata(forbidden)

    def test_tamper_and_reseal_policy_probe_scout_experience_arm_bundle_fail(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        arm_values = arms(frozen, scout_values, probe_value, experience_value)
        bundle = build_guidance_ablation_bundle(
            policy=frozen,
            bundle_ref_sha256=digest("tamper-bundle"),
            arms=arm_values,
        )

        cases = []
        bad_policy = copy.deepcopy(frozen)
        bad_policy["source_repository_commit"] = "0" * 40
        bad_policy.pop("policy_sha256")
        bad_policy["policy_sha256"] = object_sha256(bad_policy)
        cases.append((validate_guidance_policy, bad_policy, {}, "policy contract"))

        bad_probe = copy.deepcopy(probe_value)
        bad_probe["benchmark_label_mapping_gold_score_or_reward_used"] = True
        bad_probe.pop("probe_receipt_sha256")
        bad_probe["probe_receipt_sha256"] = object_sha256(bad_probe)
        cases.append(
            (
                validate_web_probe_receipt,
                bad_probe,
                {"policy": frozen},
                "probe receipt contract",
            )
        )

        bad_scout = copy.deepcopy(scout_values[0])
        bad_scout["raw_factual_value_visible_in_process_signal_schema"] = True
        bad_scout.pop("scout_trace_sha256")
        bad_scout["scout_trace_sha256"] = object_sha256(bad_scout)
        cases.append(
            (
                validate_scout_process_trace,
                bad_scout,
                {"policy": frozen},
                "scout process trace contract",
            )
        )

        bad_experience = copy.deepcopy(experience_value)
        bad_experience["factual_evidence_authority"] = True
        bad_experience.pop("experience_sha256")
        bad_experience["experience_sha256"] = object_sha256(bad_experience)
        cases.append(
            (
                validate_sibling_process_experience,
                bad_experience,
                {"policy": frozen, "scouts": scout_values},
                "sibling process experience contract",
            )
        )
        for validator, value, kwargs, message in cases:
            with self.subTest(validator=validator.__name__):
                with self.assertRaisesRegex(ValueError, message):
                    validator(value, **kwargs)

        bad_arm = copy.deepcopy(arm_values[0])
        bad_arm["experience_has_factual_evidence_authority"] = True
        bad_arm.pop("arm_sha256")
        bad_arm["arm_sha256"] = object_sha256(bad_arm)
        with self.assertRaisesRegex(ValueError, "guidance arm contract"):
            validate_guidance_arm(
                bad_arm,
                policy=frozen,
                scouts=scout_values,
                probe=probe_value,
                experience=experience_value,
            )

        bad_bundle = copy.deepcopy(bundle)
        bad_bundle["quality_cost_or_benchmark_effect_observed"] = True
        bad_bundle.pop("bundle_sha256")
        bad_bundle["bundle_sha256"] = object_sha256(bad_bundle)
        with self.assertRaisesRegex(ValueError, "bundle contract"):
            validate_guidance_ablation_bundle(
                bad_bundle,
                policy=frozen,
                bundle_ref_sha256=digest("tamper-bundle"),
                arms=arm_values,
            )

    def test_exact_schemas_reject_extra_fields(self) -> None:
        frozen = policy()
        scout_values = scouts(frozen)
        probe_value = probe(frozen)
        experience_value = experience(frozen, scout_values)
        arm_values = arms(frozen, scout_values, probe_value, experience_value)
        bundle = build_guidance_ablation_bundle(
            policy=frozen,
            bundle_ref_sha256=digest("schemas"),
            arms=arm_values,
        )
        checks = (
            (validate_guidance_policy, frozen, {}),
            (validate_web_probe_receipt, probe_value, {"policy": frozen}),
            (validate_scout_process_trace, scout_values[0], {"policy": frozen}),
            (
                validate_sibling_process_experience,
                experience_value,
                {"policy": frozen, "scouts": scout_values},
            ),
        )
        for validator, value, kwargs in checks:
            with self.subTest(validator=validator.__name__):
                with self.assertRaisesRegex(ValueError, "schema is not exact"):
                    validator({**value, "extra": False}, **kwargs)
        with self.assertRaisesRegex(ValueError, "schema is not exact"):
            validate_guidance_ablation_bundle(
                {**bundle, "extra": False},
                policy=frozen,
                bundle_ref_sha256=digest("schemas"),
                arms=arm_values,
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
