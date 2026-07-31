from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.runtime import RuntimeConfig  # noqa: E402
from deepwide_agent.shadow_risk import build_shadow_snapshot  # noqa: E402
from deepwide_agent.v24121_continuation import object_sha256  # noqa: E402
from deepwide_agent.v24122_execution import V24122TrueContinuationRuntime  # noqa: E402
from deepwide_agent.v24211_entropy_controller import (  # noqa: E402
    CONTEXT_ACTIONS,
    FEATURE_KEYS,
    MODEL_ROLE,
    NO_ENTROPY_FEATURE_KEYS,
)
from deepwide_agent.v24211_entropy_runtime import (  # noqa: E402
    EntropyControllerRestart,
    PRODUCTION_PACKAGE_AUTHORIZED,
    RUNTIME_POLICY_ID,
    V24211EntropyRuntime,
)


SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def _action_model(
    feature_keys: tuple[str, ...], *, contribution: float, tokens: int
) -> dict[str, object]:
    width = len(feature_keys) + 1
    return {
        "fit_records": 5,
        "calibration_records": 3,
        "raw_coefficients": {
            "task_contribution": [0.0] * width,
            "log_action_system_tokens": [0.0] * width,
        },
        "affine_calibrators": {
            "task_contribution": [contribution, 0.0],
            "log_action_system_tokens": [math.log1p(tokens), 0.0],
        },
    }


def _branch(
    feature_keys: tuple[str, ...], *, positive_context: str | None
) -> dict[str, object]:
    return {
        "feature_keys": list(feature_keys),
        "models": {
            context: {
                action: _action_model(
                    feature_keys,
                    contribution=(
                        0.3
                        if context == positive_context and index == 0
                        else -0.1
                    ),
                    tokens=100 + index,
                )
                for index, action in enumerate(actions)
            }
            for context, actions in CONTEXT_ACTIONS.items()
        },
    }


def sealed_model(*, positive_context: str | None) -> dict[str, object]:
    value: dict[str, object] = {
        "artifact_version": 1,
        "role": MODEL_ROLE,
        "job_manifest_sha256": SHA_B,
        "model_ready": True,
        "blockers": [],
        "full_model": _branch(FEATURE_KEYS, positive_context=positive_context),
        "no_entropy_baseline": _branch(
            NO_ENTROPY_FEATURE_KEYS, positive_context=positive_context
        ),
        "fit_record_count": 45,
        "calibration_record_count": 27,
        "fit_task_clusters": 16,
        "calibration_task_clusters": 8,
        "ridge_lambda": 0.001,
        "minimum_fit_records_per_context_action": 5,
        "minimum_calibration_records_per_context_action": 3,
        "fit_calibration_aggregate_sha256": SHA_C,
        "audit_outcomes_read": False,
        "controller_or_training_authorized": False,
    }
    value["model_sha256"] = object_sha256(value)
    return value


def sealed_action_model(*, context: str, action: str) -> dict[str, object]:
    if action not in CONTEXT_ACTIONS[context]:
        raise ValueError("test action is outside its context")
    value = sealed_model(positive_context=None)
    for branch_name in ("full_model", "no_entropy_baseline"):
        branch = value[branch_name]
        branch["models"][context][action]["affine_calibrators"][
            "task_contribution"
        ] = [0.3, 0.0]
    value.pop("model_sha256")
    value["model_sha256"] = object_sha256(value)
    return value


def candidate(name: str) -> dict[str, object]:
    return {
        "canonical_identity": name,
        "search_identity": name,
        "aliases": [name],
        "cells": {"Name": name, "Value": ""},
        "eligibility": "unresolved",
        "eligibility_reason": "needs evidence",
        "evidence_ids": [],
        "membership_evidence_ids": [],
        "membership_records": [],
        "predicate_evidence": {},
        "cell_evidence": {"Value": []},
        "cell_status": {"Value": "unknown"},
        "missing_columns": ["Value"],
    }


def base_state() -> dict[str, object]:
    return {
        "schema_version": 100,
        "pipeline_version": "synthetic-v24211",
        "opaque_id": "task_" + "1" * 24,
        "status": "running",
        "failure": None,
        "prediction": None,
        "plan": {
            "route": "enumerate_then_enrich",
            "anchor_cardinality": "row_set",
            "subject_to_resolve": "Example",
            "columns": ["Name", "Value"],
            "row_identity": ["Name"],
        },
        "scope_plan": {
            "scope_to_enumerate": "Example members",
            "row_identity": ["Name"],
            "required_predicates": [],
            "row_query_templates": {},
            "expected_rows": {"lower": 1, "point": 2, "upper": 3},
        },
        "belief": {
            "candidates": [
                {"name": "Example", "probability": 0.6},
                {"name": "Other", "probability": 0.3},
            ],
            "other_probability": 0.1,
            "chosen_subject": "Example",
        },
        "anchor_final_review": {
            "candidates": [
                {"name": "Example", "probability": 0.8},
                {"name": "Other", "probability": 0.1},
            ],
            "other_probability": 0.1,
            "chosen_subject": "Example",
        },
        "candidates": {
            "columns": ["Name", "Value"],
            "row_identity": ["Name"],
            "rows": [candidate("Alpha")],
            "estimated_unseen_mass": 0.5,
            "covered_partitions": [],
            "missing_partitions": ["rest"],
            "recent_unique_yield": 1,
        },
        "candidate_rows": None,
        "merged_rows": None,
        "candidate_recovery_decision": None,
        "recovered_candidates": None,
        "coverage_gap_plan": None,
        "coverage_gap_decision": None,
        "coverage_gap_candidates": None,
        "final_coverage_plan": None,
        "final_coverage_candidates": None,
        "final_coverage_review": None,
        "pre_final_coverage_identity_keys": None,
        "pre_final_coverage_gate": None,
        "final_coverage_gate": None,
        "candidate_stage_status": {},
        "mention_gap_entities": None,
        "mention_gap_budget_report": None,
        "mention_gap_candidates": None,
        "closed_row_domain_report": None,
        "mixed_row_domain_report": None,
        "rank_slot_occupant_report": None,
        "row_query_plan": None,
        "row_enrichment_batches": {},
        "row_enrichment_complete": False,
        "row_refinement_risks": None,
        "row_refinement_query_plan": None,
        "row_refinement_batches": {},
        "row_refinement_complete": False,
        "row_refinement_status": None,
        "membership_gap_target_row_ids": None,
        "membership_gap_query_plan": None,
        "membership_gap_batches": {},
        "membership_gap_complete": False,
        "membership_gap_status": None,
        "post_occupant_attribute_target_row_ids": None,
        "post_occupant_attribute_risks": None,
        "post_occupant_attribute_query_plan": None,
        "post_occupant_attribute_batches": {},
        "post_occupant_attribute_complete": False,
        "post_occupant_attribute_status": None,
        "post_occupant_attribute_final_risks": None,
        "unknown_cell_recovery_target_row_ids": None,
        "unknown_cell_recovery_risks": None,
        "unknown_cell_recovery_query_plan": None,
        "unknown_cell_recovery_batches": {},
        "unknown_cell_recovery_unaddressed_row_ids": [],
        "unknown_cell_recovery_complete": False,
        "unknown_cell_recovery_status": None,
        "unknown_cell_recovery_final_risks": None,
        "unit_normalization_report": None,
        "post_verification_coverage_gate": None,
        "directory_slot_contract": None,
        "directory_fetch_attempts_by_url": {},
        "directory_fetched_urls": [],
        "directory_fetch_status": None,
        "directory_slot_report": None,
        "scope_semantic_sanitizer": [],
        "bulk_scope_profile": None,
        "search_batches": {},
        "search_stage_stats": {},
        "search_stage_evidence_ids": {},
        "search_stage_errors": [],
        "evidence": [],
        "model_traces": [],
        "hosted_search_traces": {},
        "shadow_risk_snapshots": [],
        "wall_seconds": 0.0,
    }


def state_at_context(context: str) -> tuple[dict[str, object], dict[str, object]]:
    value = base_state()
    stage = {
        "anchor": "after_initial_belief",
        "late_0": "after_candidate_discovery",
        "late_1": "after_row_enrichment",
    }[context]
    if context == "late_1":
        rows = [candidate("Alpha"), candidate("Beta")]
        for index, row in enumerate(rows):
            row["row_id"] = f"row_{index:016d}"
        value["candidate_rows"] = copy.deepcopy(rows)
        value["merged_rows"] = {
            "columns": ["Name", "Value"],
            "rows": rows,
            "row_count": 2,
            "eligible_or_unresolved_count": 2,
            "eligible_count": 0,
        }
        value["row_enrichment_complete"] = True
    snapshot = build_shadow_snapshot(value, stage)
    value["shadow_risk_snapshots"].append(snapshot)
    return value, snapshot


class Search:
    calls = 0
    failures = 0
    tool_calls = 0
    fetch_calls = 0
    fetch_failures = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    def search_many(self, queries, **kwargs):
        self.calls += len(queries)
        self.tool_calls += len(queries)
        self.fetch_calls += len(queries)
        self.input_tokens += 10
        self.output_tokens += 20
        self.total_tokens += 30
        return [
            {
                "query": query,
                "answer": "",
                "provider": "synthetic",
                "error": None,
                "results": [
                    {
                        "title": "Official directory",
                        "url": f"https://example.org/{index}",
                        "raw_content": "Alpha and Beta are members of Example.",
                        "content": "Alpha and Beta are members of Example.",
                    }
                ],
            }
            for index, query in enumerate(queries)
        ]


class Model:
    requests = 0
    calls = 0
    failures = 0
    attempts = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0


class Harness(V24211EntropyRuntime):
    def __init__(self, model_value: dict[str, object]) -> None:
        self.model = Model()
        self.search = Search()
        self.config = RuntimeConfig()
        self.out_dir = Path("/nonexistent-v24211")
        self.config_sha256 = SHA_A
        self.saved: list[dict[str, object]] = []
        self._v24211_model = copy.deepcopy(model_value)
        self._v24211_model_sha256 = str(model_value["model_sha256"])
        self._v24211_job_manifest_sha256 = SHA_B
        self._v24211_parent_manifest_sha256 = SHA_C
        self._v24211_policy_branch = "full_entropy"
        self._v24211_active_question = None
        self._v24211_in_controller_retrieval = False

    def _save(self, state):
        self.saved.append(copy.deepcopy(state))


class RestartHarness(Harness):
    def __init__(self, model_value: dict[str, object]) -> None:
        super().__init__(model_value)
        self.parent_entries = 0

    def _run_incremental_candidate_workers(
        self,
        state,
        question,
        *,
        search_stage_names,
        prior_candidates,
        max_queries,
        target_entities,
    ):
        result = copy.deepcopy(prior_candidates)
        result["rows"].append(candidate("Beta"))
        return result


def fake_parent_stages(self, state, question, checkpoint_wall_time):
    self.parent_entries += 1
    # This is the exact V2.41.22 top-of-stage behavior needed after a
    # discover-entities action.  On the first entry there is no pending delta;
    # on the restart the sealed observation is reduced before later decisions.
    self._consume_incremental_discovery(state, question)
    self._record_shadow(state, "after_candidate_discovery")
    state["prediction"] = "done"
    state["status"] = "completed"
    return {"prediction": "done", "status": "completed"}


class V24211EntropyRuntimeTests(unittest.TestCase):
    def test_production_package_remains_unauthorized(self) -> None:
        self.assertIs(PRODUCTION_PACKAGE_AUTHORIZED, False)

    def test_constructor_validates_model_before_forward_use(self) -> None:
        value = sealed_model(positive_context=None)
        tampered = copy.deepcopy(value)
        tampered["model_ready"] = False
        with patch(
            "deepwide_agent.v24211_entropy_runtime.PRODUCTION_PACKAGE_AUTHORIZED",
            True,
        ):
            with self.assertRaisesRegex(ValueError, "seal or provenance"):
                V24211EntropyRuntime(
                    Model(),
                    Search(),
                    RuntimeConfig(),
                    Path("/nonexistent-v24211-constructor"),
                    entropy_action_model=tampered,
                    entropy_action_model_sha256=str(value["model_sha256"]),
                    entropy_action_model_job_manifest_sha256=SHA_B,
                    entropy_selected_parent_manifest_sha256=SHA_C,
                )

    def test_unpublished_constructor_fails_before_model_validation(self) -> None:
        value = sealed_model(positive_context=None)
        with self.assertRaisesRegex(RuntimeError, "sealed production package"):
            V24211EntropyRuntime(
                Model(),
                Search(),
                RuntimeConfig(),
                Path("/nonexistent-v24211-unpublished"),
                entropy_action_model=value,
                entropy_action_model_sha256=str(value["model_sha256"]),
                entropy_action_model_job_manifest_sha256=SHA_B,
                entropy_selected_parent_manifest_sha256=SHA_C,
            )

    def test_all_context_action_pairs_execute_real_state_transitions(self) -> None:
        cases = tuple(
            (context, action)
            for context, actions in CONTEXT_ACTIONS.items()
            for action in actions
        )
        self.assertEqual(len(cases), 9)
        self.assertEqual(len({action for _, action in cases}), 7)
        for context, action in cases:
            with self.subTest(context=context, action=action):
                runtime = Harness(
                    sealed_action_model(context=context, action=action)
                )
                state, snapshot = state_at_context(context)
                before = object_sha256(state)
                runtime._v24211_active_question = "visible question"
                try:
                    changed = runtime._v24211_apply_decision(
                        state, snapshot, context=context
                    )
                finally:
                    runtime._v24211_active_question = None
                self.assertTrue(changed)
                self.assertEqual(runtime.search.calls, 2)
                self.assertNotEqual(object_sha256(state), before)
                transition = state["v24211_entropy_decisions"][0]
                self.assertEqual(transition["selected_action"], action)
                self.assertTrue(transition["state_mutated_by_action"])
                self.assertFalse(transition["projection_only_action_arm_called"])
                self.assertEqual(
                    transition["decision_receipt_sha256"],
                    transition["decision_receipt"]["receipt_sha256"],
                )
                self.assertEqual(
                    runtime._v24211_attempted_contexts(state), {context}
                )

    def test_action_executes_two_searches_mutates_state_and_restarts_once(self) -> None:
        runtime = RestartHarness(sealed_model(positive_context="late_0"))
        state = base_state()
        with patch.object(
            V24122TrueContinuationRuntime,
            "_run_task_stages",
            fake_parent_stages,
        ):
            result = runtime._run_task_stages(
                state, "visible question", lambda: None
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(runtime.search.calls, 2)
        self.assertEqual(runtime.parent_entries, 2)
        self.assertEqual(len(state["v24211_entropy_decisions"]), 1)
        transition = state["v24211_entropy_decisions"][0]
        self.assertEqual(transition["runtime_policy_id"], RUNTIME_POLICY_ID)
        self.assertEqual(transition["decision_kind"], "action")
        self.assertEqual(transition["selected_action"], "discover_entities")
        self.assertTrue(transition["state_mutated_by_action"])
        self.assertFalse(transition["projection_only_action_arm_called"])
        self.assertTrue(state["v24122_incremental_discovery"]["consumed"])
        self.assertEqual(len(state["candidates"]["rows"]), 2)

    def test_stop_records_once_without_search_or_restart(self) -> None:
        runtime = RestartHarness(sealed_model(positive_context=None))
        state = base_state()
        with patch.object(
            V24122TrueContinuationRuntime,
            "_run_task_stages",
            fake_parent_stages,
        ):
            result = runtime._run_task_stages(
                state, "visible question", lambda: None
            )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(runtime.search.calls, 0)
        self.assertEqual(runtime.parent_entries, 1)
        transition = state["v24211_entropy_decisions"][0]
        self.assertEqual(transition["decision_kind"], "stop")
        self.assertFalse(transition["state_mutated_by_action"])

    def test_missing_signal_abstains_without_search(self) -> None:
        runtime = Harness(sealed_model(positive_context="late_1"))
        state = base_state()
        snapshot = build_shadow_snapshot(state, "after_row_enrichment")
        snapshot["raw_risk_vector"]["row_unresolved_rate"] = None
        snapshot["raw_risk_vector"]["cell_uncertain_rate"] = None
        runtime._v24211_active_question = "visible question"
        try:
            changed = runtime._v24211_apply_decision(
                state, snapshot, context="late_1"
            )
        finally:
            runtime._v24211_active_question = None
        self.assertFalse(changed)
        self.assertEqual(runtime.search.calls, 0)
        self.assertEqual(
            state["v24211_entropy_decisions"][0]["decision_kind"], "abstain"
        )

    def test_transition_ledger_tamper_fails_before_duplicate_decision(self) -> None:
        runtime = Harness(sealed_model(positive_context=None))
        state = base_state()
        snapshot = build_shadow_snapshot(state, "after_candidate_discovery")
        runtime._v24211_active_question = "visible question"
        try:
            runtime._v24211_apply_decision(state, snapshot, context="late_0")
            state["v24211_entropy_decisions"][0]["decision_kind"] = "action"
            with self.assertRaisesRegex(ValueError, "seal drifted"):
                runtime._v24211_apply_decision(state, snapshot, context="late_0")
        finally:
            runtime._v24211_active_question = None

    def test_nested_receipt_tamper_fails_even_after_outer_reseal(self) -> None:
        runtime = Harness(sealed_model(positive_context=None))
        state = base_state()
        snapshot = build_shadow_snapshot(state, "after_candidate_discovery")
        runtime._v24211_active_question = "visible question"
        try:
            runtime._v24211_apply_decision(state, snapshot, context="late_0")
            transition = state["v24211_entropy_decisions"][0]
            receipt = transition["decision_receipt"]
            receipt["question_text_read_by_controller"] = True
            receipt["receipt_sha256"] = object_sha256(
                {
                    key: value
                    for key, value in receipt.items()
                    if key != "receipt_sha256"
                }
            )
            transition["decision_receipt_sha256"] = receipt["receipt_sha256"]
            transition["runtime_transition_sha256"] = object_sha256(
                {
                    key: value
                    for key, value in transition.items()
                    if key != "runtime_transition_sha256"
                }
            )
            with self.assertRaisesRegex(ValueError, "nested decision"):
                runtime._v24211_apply_decision(
                    state, snapshot, context="late_0"
                )
        finally:
            runtime._v24211_active_question = None

    def test_restart_loop_is_bounded_and_clears_question(self) -> None:
        runtime = Harness(sealed_model(positive_context=None))
        state = base_state()
        with patch.object(
            V24122TrueContinuationRuntime,
            "_run_task_stages",
            side_effect=EntropyControllerRestart("forced"),
        ) as parent:
            with self.assertRaisesRegex(RuntimeError, "restart bound"):
                runtime._run_task_stages(
                    state, "visible question", lambda: None
                )
        self.assertEqual(parent.call_count, 4)
        self.assertIsNone(runtime._v24211_active_question)


if __name__ == "__main__":
    unittest.main()
