#!/usr/bin/env python3
"""Aggregate-only reliability diagnosis of frozen V2.52.67.

The frozen task rows contain questions, predictions, runtime envelopes, and
opaque task identities.  This module never materializes those values.  A
lexical JSON boundary scanner decodes only terminal/runtime flags, finite
exception types, and sealed content-free stage, budget, health, effect, and
production receipts.  The output is aggregate-only and does not read any
mapping, answer, evaluator result, per-task metric, or correctness signal.

This is a post-freeze reliability diagnosis.  It cannot authorize a retry,
selective re-evaluation, runtime treatment, external forward, or another
DeepWideBench rollout.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25265_production_only_totality_runtime as runtime  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import diagnose_v25063_three_run_output_structure as lexical  # noqa: E402
from scripts import diagnose_v25228_v25208_production_totality as nested  # noqa: E402
from scripts import run_v25260_observed_reliability_external as accounting  # noqa: E402
from scripts import run_v25267_production_only_exact220 as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25270_v25267_production_only_content_free_reliability_diagnosis"
SOURCE = Path("scripts/diagnose_v25270_v25267_production_only_reliability.py")
TEST = Path("tests/test_diagnose_v25270_v25267_production_only_reliability.py")
OUTPUT = Path(
    f"results/v25270_v25267_production_only_reliability_diagnosis_v1_{DATE}.json"
)

PARENT_PATHS = {
    "forward_result": contract.FORWARD_RESULT,
    "forward_audit": contract.FORWARD_AUDIT,
    "task_rows": contract.RUNTIME_RESULTS,
    "prediction_freeze": contract.PREDICTION_FREEZE,
    "run_summary": contract.RUN_SUMMARY,
}
EXPECTED_SHA256 = {
    "forward_result": "8e31dc56d5b878042398552174d2a5bf6f046ee5df39a2d414e8517f463e2d71",
    "forward_audit": "c1c8329bb90837334813b171c21a416680a183ff79686911cad00779f2ad34d7",
    "task_rows": "ea15f93e9126f18dbcb4c9272551045176396b6cb67af9a2b3d02c38b6330526",
    "prediction_freeze": "25e2c949b0e61b8c7a0679e86655fdc7ca931850d3e8710a5a0ae077b1394ece",
    "run_summary": "d6374dc7099583530ddae6031b1386f9716f00568f5e367ed42b3ebf87e44a7e",
}
EXPECTED_AGGREGATE_SHA256 = (
    "821a2aacd28200d92a4d65679f47f7f5c148c1d02a86ab30ebfe733781f3778f"
)

SAFE_TOP_LEVEL_MEMBERS = frozenset(
    {
        "terminal",
        "runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "prediction_kind",
        "content_free_stage_receipt",
        "content_free_budget_receipt",
        "effect_health",
        "actual_effect_snapshot",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_skip_backfill_replacement_or_selective_rerun",
        "contains_question_query_url_page_answer_or_credential_outside_prediction",
    }
)
EXPECTED_TOP_LEVEL_MEMBERS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "opaque_id",
        "runtime_input_keys",
        "terminal",
        "runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "prediction",
        "prediction_sha256",
        "prediction_kind",
        "runtime_result",
        "runtime_result_payload_sha256",
        "content_free_stage_receipt",
        "content_free_budget_receipt",
        "cost",
        "elapsed_seconds",
        "effect_health",
        "actual_effect_snapshot",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "retry_resume_skip_backfill_replacement_or_selective_rerun",
        "contains_question_query_url_page_answer_or_credential_outside_prediction",
        "result_payload_sha256",
    }
)
RUNTIME_SAFE_PATHS = {
    "failure_types": ("runtime_result", "failure_types"),
    "content_free_receipt": ("runtime_result", "content_free_receipt"),
}
FAILURE_SLOTS = ("plan", "grounded_plan", "production", "post_effect")
HEALTH_NAMES = (
    "model_request_failures",
    "model_hard_total_wall_timeouts",
    "search_transport_failures",
    "search_hard_total_wall_timeouts",
    "fetch_helper_failures",
    "fetch_hard_deadline_failures",
    "fetch_deadline_rejections",
)
EFFECT_NAMES = (
    "model_logical_requests",
    "model_provider_requests",
    "model_provider_attempts",
    "model_provider_successes",
    "model_slot_acquisitions",
    "search_invocations",
    "logical_queries",
    "fetch_invocations",
    "fetch_requests",
    "fetch_calls",
    "fetch_helper_calls",
)
OUTCOME_NAMES = (
    "outer_failure",
    "completed_fallback",
    "completed_model_generated",
)


def _ordinary(relative: Path) -> Path:
    return contract.ordinary(ROOT, relative, tracked=True)


def _selected_top_level(line: str) -> dict[str, Any]:
    """Decode only the frozen content-free top-level allowlist."""

    text = str(line).strip()
    position = lexical._skip_ws(text, 0)
    if position >= len(text) or text[position] != "{":
        raise ValueError("V2.52.70 expected top-level JSON object")
    position += 1
    selected: dict[str, Any] = {}
    names: set[str] = set()
    while True:
        position = lexical._skip_ws(text, position)
        if position < len(text) and text[position] == "}":
            position = lexical._skip_ws(text, position + 1)
            if position != len(text):
                raise ValueError("V2.52.70 trailing JSON content")
            break
        name, name_end = lexical._DECODER.raw_decode(text, position)
        if not isinstance(name, str) or name in names:
            raise ValueError("V2.52.70 duplicate or invalid member")
        names.add(name)
        position = lexical._skip_ws(text, name_end)
        if position >= len(text) or text[position] != ":":
            raise ValueError("V2.52.70 missing member separator")
        start = lexical._skip_ws(text, position + 1)
        end = lexical._value_end(text, start)
        if name in SAFE_TOP_LEVEL_MEMBERS:
            selected[name] = json.loads(text[start:end])
        position = lexical._skip_ws(text, end)
        if position < len(text) and text[position] == ",":
            position += 1
            continue
        if position < len(text) and text[position] == "}":
            continue
        raise ValueError("V2.52.70 invalid member delimiter")
    if names != EXPECTED_TOP_LEVEL_MEMBERS or set(selected) != SAFE_TOP_LEVEL_MEMBERS:
        raise ValueError("V2.52.70 frozen task-row schema drifted")
    return selected


def _safe_failure_types(value: object) -> dict[str, str | None]:
    if not isinstance(value, Mapping) or set(value) != set(FAILURE_SLOTS):
        raise ValueError("V2.52.70 failure-type schema drifted")
    copied = dict(value)
    if any(
        item is not None
        and (not isinstance(item, str) or not item or len(item) > 128)
        for item in copied.values()
    ):
        raise ValueError("V2.52.70 unsafe failure type")
    return copied


def safe_row(line: str) -> dict[str, Any]:
    """Project one frozen task row to validated content-free telemetry."""

    selected = _selected_top_level(line)
    completed = selected["runtime_completed"] is True
    stage = selected["content_free_stage_receipt"]
    budget = selected["content_free_budget_receipt"]
    health = selected["effect_health"]
    effect = selected["actual_effect_snapshot"]
    if (
        selected["terminal"] is not True
        or not isinstance(selected["runtime_completed"], bool)
        or not isinstance(selected["failure_as_zero"], bool)
        or selected["failure_as_zero"] is completed
        or selected["prediction_kind"] not in {"model_generated", "fallback"}
        or not isinstance(stage, Mapping)
        or runtime.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or accounting.transport._health(health) != health
        or accounting.transport._validate_actual_effect_snapshot(effect) != effect
        or effect["logical_queries"] != budget["query_admitted_count"]
        or effect["fetch_requests"] != budget["fetch_admitted_count"]
        or effect["model_logical_requests"] != budget["model_admitted_count"]
        or any(
            selected[name] is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_backfill_replacement_or_selective_rerun",
                "contains_question_query_url_page_answer_or_credential_outside_prediction",
            )
        )
    ):
        raise RuntimeError("V2.52.70 content-free row drifted")

    output = dict(selected)
    if completed:
        failures = _safe_failure_types(
            nested._selected_nested_value(line, RUNTIME_SAFE_PATHS["failure_types"])
        )
        receipt_value = nested._selected_nested_value(
            line, RUNTIME_SAFE_PATHS["content_free_receipt"]
        )
        if not isinstance(receipt_value, Mapping):
            raise ValueError("V2.52.70 content-free receipt is not an object")
        receipt = runtime.validate_receipt(receipt_value)
        if (
            selected["outer_failure_type"] is not None
            or stage["failure_present"] is not False
            or selected["prediction_kind"]
            != ("model_generated" if receipt["production_provider_output_valid"] else "fallback")
            or receipt["post_effect_failure_present"]
            is not (failures["post_effect"] is not None)
        ):
            raise RuntimeError("V2.52.70 completed row drifted")
        output["failure_types"] = failures
        output["content_free_receipt"] = receipt
    else:
        if (
            not isinstance(selected["outer_failure_type"], str)
            or not selected["outer_failure_type"]
            or selected["prediction_kind"] != "fallback"
            or stage["failure_present"] is not True
        ):
            raise RuntimeError("V2.52.70 outer-failure row drifted")
        output["failure_types"] = None
        output["content_free_receipt"] = None
    return output


def _parents(*, require_clean: bool) -> dict[str, str]:
    if require_clean and (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.52.70 requires clean pushed HEAD")
    observed = {name: contract.sha256(_ordinary(path)) for name, path in PARENT_PATHS.items()}
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.52.70 frozen parent hash drifted")

    forward = runner.validate_forward_result(
        json.loads(_ordinary(contract.FORWARD_RESULT).read_text(encoding="utf-8"))
    )
    summary = runner.validate_summary(
        json.loads(_ordinary(contract.RUN_SUMMARY).read_text(encoding="utf-8"))
    )
    audit = json.loads(_ordinary(contract.FORWARD_AUDIT).read_text(encoding="utf-8"))
    freeze = json.loads(_ordinary(contract.PREDICTION_FREEZE).read_text(encoding="utf-8"))
    if (
        forward["selected"] != contract.TASK_COUNT
        or forward["terminal_predictions"] != contract.TASK_COUNT
        or forward["runtime_results_sha256"] != observed["task_rows"]
        or forward["prediction_freeze_sha256"] != observed["prediction_freeze"]
        or forward["run_summary_sha256"] != observed["run_summary"]
        or summary["selected"] != contract.TASK_COUNT
        or summary["completed"] != contract.TASK_COUNT
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256") != observed["forward_result"]
        or audit.get("runtime_results_sha256") != observed["task_rows"]
        or audit.get("prediction_freeze_sha256") != observed["prediction_freeze"]
        or audit.get("run_summary_sha256") != observed["run_summary"]
        or audit.get("mapping_gold_category_question_type_split_evaluator_score_reward_read_by_audit")
        is not False
        or audit.get("network_model_search_fetch_or_evaluator_called_by_audit") is not False
        or freeze.get("selected") != contract.TASK_COUNT
        or freeze.get("terminal") != contract.TASK_COUNT
        or freeze.get("runtime_results_sha256") != observed["task_rows"]
        or freeze.get("run_summary_sha256") != observed["run_summary"]
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or not contract.sealed(freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.52.70 frozen forward barrier drifted")
    return observed


def _counter(counter: Counter[str]) -> dict[str, int]:
    return {name: int(counter[name]) for name in sorted(counter)}


def _outcome(row: Mapping[str, Any]) -> str:
    if row["runtime_completed"] is not True:
        return "outer_failure"
    if row["prediction_kind"] == "fallback":
        return "completed_fallback"
    return "completed_model_generated"


def _aggregate() -> dict[str, Any]:
    rows = [
        safe_row(line)
        for line in _ordinary(contract.RUNTIME_RESULTS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.52.70 fixed task denominator drifted")

    outcomes: Counter[str] = Counter()
    outer_types: Counter[str] = Counter()
    stage_failure_pairs: Counter[str] = Counter()
    failure_types: dict[str, Counter[str]] = {
        slot: Counter() for slot in FAILURE_SLOTS
    }
    health_totals = Counter({name: 0 for name in HEALTH_NAMES})
    health_task_counts = Counter({name: 0 for name in HEALTH_NAMES})
    health_outcomes = Counter({name: 0 for name in OUTCOME_NAMES})
    health_by_outcome: dict[str, Counter[str]] = {
        name: Counter({field: 0 for field in HEALTH_NAMES}) for name in OUTCOME_NAMES
    }
    effect_totals = Counter({name: 0 for name in EFFECT_NAMES})
    effect_by_outcome: dict[str, Counter[str]] = {
        name: Counter({field: 0 for field in EFFECT_NAMES}) for name in OUTCOME_NAMES
    }
    effect_signatures: dict[str, Counter[str]] = {
        name: Counter() for name in OUTCOME_NAMES
    }
    provider_forward_histogram: Counter[str] = Counter()
    receipt_flags: Counter[str] = Counter()
    stage_entered = Counter({name: 0 for name in runtime.STAGES})
    stage_completed = Counter({name: 0 for name in runtime.STAGES})
    rejected_tasks = 0
    outer_all_model_requests_succeeded = 0
    outer_three_model_successes = 0
    outer_zero_health = 0

    for row in rows:
        outcome = _outcome(row)
        outcomes[outcome] += 1
        stage = row["content_free_stage_receipt"]
        budget = row["content_free_budget_receipt"]
        health = row["effect_health"]
        effect = row["actual_effect_snapshot"]
        stage_entered.update(stage["stage_entered_counts"])
        stage_completed.update(stage["stage_completed_counts"])
        if stage["failure_present"]:
            stage_failure_pairs[f"{stage['failure_stage']}:{stage['failure_type']}"] += 1
        if outcome == "outer_failure":
            outer_types[str(row["outer_failure_type"])] += 1
        failures = row["failure_types"]
        if failures is not None:
            for slot in FAILURE_SLOTS:
                if failures[slot] is not None:
                    failure_types[slot][str(failures[slot])] += 1
            receipt = row["content_free_receipt"]
            provider_forward_histogram[str(receipt["provider_forward_count"])] += 1
            for flag in (
                "production_provider_output_valid",
                "production_fallback_used",
                "parent_result_valid",
                "post_effect_failure_present",
                "suppressed_revision_entry_count",
            ):
                receipt_flags[flag] += int(receipt[flag])
        health_totals.update(health)
        any_health = sum(health.values()) > 0
        health_outcomes[outcome] += int(any_health)
        health_by_outcome[outcome].update(health)
        for name, count in health.items():
            health_task_counts[name] += int(count > 0)
        effect_totals.update({name: int(effect[name]) for name in EFFECT_NAMES})
        effect_by_outcome[outcome].update(
            {name: int(effect[name]) for name in EFFECT_NAMES}
        )
        signature = (
            f"q{effect['logical_queries']}/f{effect['fetch_requests']}"
            f"/m{effect['model_logical_requests']}"
        )
        effect_signatures[outcome][signature] += 1
        rejected_tasks += int(
            any(
                budget[name] > 0
                for name in (
                    "query_rejected_count",
                    "fetch_rejected_count",
                    "model_rejected_count",
                )
            )
        )
        if outcome == "outer_failure":
            outer_all_model_requests_succeeded += int(
                effect["model_provider_successes"] == effect["model_logical_requests"]
            )
            outer_three_model_successes += int(effect["model_provider_successes"] == 3)
            outer_zero_health += int(not any_health)

    output = {
        "fixed_task_denominator": len(rows),
        "outcome_counts": {name: int(outcomes[name]) for name in OUTCOME_NAMES},
        "outer_failure_type_counts": _counter(outer_types),
        "stage_failure_stage_type_counts": _counter(stage_failure_pairs),
        "stage_entered_totals": {name: int(stage_entered[name]) for name in runtime.STAGES},
        "stage_completed_totals": {name: int(stage_completed[name]) for name in runtime.STAGES},
        "completed_failure_type_counts": {
            slot: _counter(failure_types[slot]) for slot in FAILURE_SLOTS
        },
        "completed_receipt_flag_totals": _counter(receipt_flags),
        "provider_forward_count_histogram": _counter(provider_forward_histogram),
        "terminal_effect_health_totals": {
            name: int(health_totals[name]) for name in HEALTH_NAMES
        },
        "tasks_with_health_event_by_type": {
            name: int(health_task_counts[name]) for name in HEALTH_NAMES
        },
        "tasks_with_any_health_event": sum(health_outcomes.values()),
        "tasks_with_any_health_event_by_outcome": {
            name: int(health_outcomes[name]) for name in OUTCOME_NAMES
        },
        "health_event_totals_by_outcome": {
            outcome: {
                name: int(health_by_outcome[outcome][name]) for name in HEALTH_NAMES
            }
            for outcome in OUTCOME_NAMES
        },
        "effect_totals": {name: int(effect_totals[name]) for name in EFFECT_NAMES},
        "effect_totals_by_outcome": {
            outcome: {
                name: int(effect_by_outcome[outcome][name]) for name in EFFECT_NAMES
            }
            for outcome in OUTCOME_NAMES
        },
        "effect_signature_counts_by_outcome": {
            outcome: _counter(effect_signatures[outcome]) for outcome in OUTCOME_NAMES
        },
        "budget_rejection_tasks": rejected_tasks,
        "outer_failure_tasks_with_all_model_requests_successful": (
            outer_all_model_requests_succeeded
        ),
        "outer_failure_tasks_with_three_model_successes": outer_three_model_successes,
        "outer_failure_tasks_with_zero_health_event": outer_zero_health,
        "positive_signed_credit_count": 0,
    }
    return output


def build_diagnosis(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    aggregate = _aggregate()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": _parents(require_clean=require_clean),
        "aggregate": aggregate,
        "diagnosis": {
            "outer_failures_and_completed_fallbacks_are_distinct_failure_classes": True,
            "health_event_count_is_not_a_task_failure_count": True,
            "existing_two_stage_observer_is_too_coarse_to_localize_sparse_production_outer_failures": True,
            "next_build_should_add_behavior_preserving_production_checkpoint_and_finite_microstages": True,
            "post_checkpoint_failure_may_preserve_only_an_already_validated_production_table": True,
            "pre_checkpoint_failure_must_remain_fail_closed": True,
            "completed_production_fallbacks_require_a_separate_parser_totality_gate": True,
            "most_outer_failures_are_post_effect_internal_validation_failures_not_transport_failures": True,
            "frozen_v25267_population_must_not_be_retried_replayed_or_selectively_revalued": True,
            "aggregate_diagnosis_establishes_quality_or_causal_credit": False,
        },
        "content_policy": {
            "top_level_members_decoded": sorted(SAFE_TOP_LEVEL_MEMBERS),
            "completed_runtime_nested_paths_decoded": [
                list(RUNTIME_SAFE_PATHS[name]) for name in sorted(RUNTIME_SAFE_PATHS)
            ],
            "all_other_values_skipped_lexically": True,
            "task_identity_question_query_url_page_prediction_answer_mapping_gold_category_split_metric_score_or_credential_decoded_hashed_or_emitted": False,
            "evaluator_file_or_per_task_correctness_opened": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "content_free_reliability_diagnosis": True,
            "synthetic_behavior_preserving_checkpoint_and_microstage_build_only": True,
            "runtime_activation_or_prediction_change": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation_of_v25267": False,
            "external_forward_or_new_deepwidebench_rollout": False,
            "avg_at_4_leaderboard_or_sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    aggregate = copied.get("aggregate")
    diagnosis = copied.get("diagnosis")
    policy = copied.get("content_policy")
    authorization = copied.get("authorization")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "parents",
            "aggregate",
            "diagnosis",
            "content_policy",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("parents") != EXPECTED_SHA256
        or not isinstance(aggregate, Mapping)
        or contract.payload_sha256(aggregate) != EXPECTED_AGGREGATE_SHA256
        or aggregate.get("fixed_task_denominator") != contract.TASK_COUNT
        or sum(aggregate.get("outcome_counts", {}).values()) != contract.TASK_COUNT
        or aggregate.get("outcome_counts", {}).get("outer_failure") != 11
        or aggregate.get("outcome_counts", {}).get("completed_fallback") != 7
        or aggregate.get("outcome_counts", {}).get("completed_model_generated") != 202
        or aggregate.get("budget_rejection_tasks") != 0
        or aggregate.get("outer_failure_tasks_with_all_model_requests_successful") != 11
        or aggregate.get("outer_failure_tasks_with_three_model_successes") != 10
        or aggregate.get("outer_failure_tasks_with_zero_health_event") != 9
        or aggregate.get("positive_signed_credit_count") != 0
        or sum(aggregate.get("terminal_effect_health_totals", {}).values()) != 19
        or not isinstance(diagnosis, Mapping)
        or any(
            diagnosis.get(name) is not True
            for name in (
                "outer_failures_and_completed_fallbacks_are_distinct_failure_classes",
                "health_event_count_is_not_a_task_failure_count",
                "existing_two_stage_observer_is_too_coarse_to_localize_sparse_production_outer_failures",
                "next_build_should_add_behavior_preserving_production_checkpoint_and_finite_microstages",
                "post_checkpoint_failure_may_preserve_only_an_already_validated_production_table",
                "pre_checkpoint_failure_must_remain_fail_closed",
                "completed_production_fallbacks_require_a_separate_parser_totality_gate",
                "most_outer_failures_are_post_effect_internal_validation_failures_not_transport_failures",
                "frozen_v25267_population_must_not_be_retried_replayed_or_selectively_revalued",
            )
        )
        or diagnosis.get("aggregate_diagnosis_establishes_quality_or_causal_credit") is not False
        or policy
        != {
            "top_level_members_decoded": sorted(SAFE_TOP_LEVEL_MEMBERS),
            "completed_runtime_nested_paths_decoded": [
                list(RUNTIME_SAFE_PATHS[name]) for name in sorted(RUNTIME_SAFE_PATHS)
            ],
            "all_other_values_skipped_lexically": True,
            "task_identity_question_query_url_page_prediction_answer_mapping_gold_category_split_metric_score_or_credential_decoded_hashed_or_emitted": False,
            "evaluator_file_or_per_task_correctness_opened": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
        }
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "content_free_reliability_diagnosis": True,
            "synthetic_behavior_preserving_checkpoint_and_microstage_build_only": True,
            "runtime_activation_or_prediction_change": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation_of_v25267": False,
            "external_forward_or_new_deepwidebench_rollout": False,
            "avg_at_4_leaderboard_or_sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.70 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("diagnose",))
    args = parser.parse_args()
    if args.command == "diagnose":
        value = build_diagnosis()
        publish_exclusive(ROOT / OUTPUT, value)
        print(
            json.dumps(
                {
                    "path": str(OUTPUT),
                    "outcomes": value["aggregate"]["outcome_counts"],
                    "health_events": sum(
                        value["aggregate"]["terminal_effect_health_totals"].values()
                    ),
                    "new_exact220_rollout": value["authorization"][
                        "external_forward_or_new_deepwidebench_rollout"
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
