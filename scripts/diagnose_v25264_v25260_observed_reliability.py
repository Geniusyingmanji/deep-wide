#!/usr/bin/env python3
"""Content-free diagnosis of the frozen V2.52.60 reliability forward.

Task rows contain task identities, questions inside nested runtime envelopes,
pages, and predictions.  This module never decodes those members.  A lexical
JSON boundary scanner materializes only terminal/runtime flags, prediction
kind, content-free health/effect counters, and sealed stage/budget receipts.
The output is aggregate-only and cannot authorize a retry, evaluator, runtime
change, or DeepWideBench forward.
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

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from scripts import audit_v25263_observed_reliability_forward as parent  # noqa: E402
from scripts import diagnose_v25063_three_run_output_structure as lexical  # noqa: E402
from scripts import run_v25260_observed_reliability_external as runner  # noqa: E402


ROLE = "v25264_v25260_observed_reliability_content_free_diagnosis"
SOURCE = Path("scripts/diagnose_v25264_v25260_observed_reliability.py")
TEST = Path("tests/test_diagnose_v25264_v25260_observed_reliability.py")
OUTPUT = Path(f"results/v25264_v25260_observed_reliability_diagnosis_v1_{contract.DATE}.json")
EXPECTED_SHA256 = {
    "forward_result": "9ed2ab4f3b23600d8f434e1223c681ca43bd5143c2252a38e43b9292d74dcd27",
    "forward_audit": "22769b4e1e219e5a8b3c0247f9163083a1102389e0f6c6db184b597b6744f2b7",
    "task_rows": "17885a57bed89469fe62378b26f25fa31062123cb3507be70f8cc0d08c53f95c",
    "prediction_freeze": "171fada6a4f27ef86ca16c7c6722b0cf8895a2cd171117a95340c56c6eacf7e5",
}
PARENT_PATHS = {
    "forward_result": contract.FORWARD_RESULT,
    "forward_audit": contract.FORWARD_AUDIT,
    "task_rows": contract.TASK_ROWS,
    "prediction_freeze": contract.PREDICTION_FREEZE,
}
SAFE_MEMBERS = frozenset(
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
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "contains_question_package_query_url_page_answer_or_credential_outside_prediction",
    }
)
EXPECTED_TOP_LEVEL_MEMBERS = frozenset(
    {
        "actual_effect_snapshot",
        "artifact_version",
        "contains_question_package_query_url_page_answer_or_credential_outside_prediction",
        "content_free_budget_receipt",
        "content_free_stage_receipt",
        "cost",
        "effect_health",
        "elapsed_seconds",
        "entropy_or_information_gain_assigns_signed_credit",
        "failure_as_zero",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "opaque_id",
        "outer_failure_type",
        "prediction",
        "prediction_kind",
        "prediction_sha256",
        "protocol_id",
        "result_payload_sha256",
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "role",
        "runtime_completed",
        "runtime_input_keys",
        "runtime_result",
        "runtime_result_payload_sha256",
        "terminal",
    }
)
HEALTH_NAMES = (
    "model_request_failures",
    "model_hard_total_wall_timeouts",
    "search_transport_failures",
    "search_hard_total_wall_timeouts",
    "fetch_helper_failures",
    "fetch_hard_deadline_failures",
    "fetch_deadline_rejections",
)


def _ordinary(relative: Path) -> Path:
    return contract.ordinary(ROOT, relative, tracked=True)


def safe_row(line: str) -> dict[str, Any]:
    """Decode only explicitly content-free members of one frozen task row."""

    text = str(line).strip()
    position = lexical._skip_ws(text, 0)
    if position >= len(text) or text[position] != "{":
        raise ValueError("V2.52.64 expected top-level JSON object")
    position += 1
    selected: dict[str, Any] = {}
    names: set[str] = set()
    while True:
        position = lexical._skip_ws(text, position)
        if position < len(text) and text[position] == "}":
            position = lexical._skip_ws(text, position + 1)
            if position != len(text):
                raise ValueError("V2.52.64 trailing JSON content")
            break
        name, name_end = lexical._DECODER.raw_decode(text, position)
        if not isinstance(name, str) or name in names:
            raise ValueError("V2.52.64 duplicate or invalid member")
        names.add(name)
        position = lexical._skip_ws(text, name_end)
        if position >= len(text) or text[position] != ":":
            raise ValueError("V2.52.64 missing member separator")
        start = lexical._skip_ws(text, position + 1)
        end = lexical._value_end(text, start)
        if name in SAFE_MEMBERS:
            selected[name] = json.loads(text[start:end])
        position = lexical._skip_ws(text, end)
        if position < len(text) and text[position] == ",":
            position += 1
            continue
        if position < len(text) and text[position] == "}":
            continue
        raise ValueError("V2.52.64 invalid member delimiter")
    if names != EXPECTED_TOP_LEVEL_MEMBERS or set(selected) != SAFE_MEMBERS:
        raise ValueError("V2.52.64 frozen row schema drifted")

    stage = selected["content_free_stage_receipt"]
    budget = selected["content_free_budget_receipt"]
    effect = selected["actual_effect_snapshot"]
    health = selected["effect_health"]
    if (
        selected["terminal"] is not True
        or selected["runtime_completed"] is not True
        or selected["failure_as_zero"] is not False
        or selected["outer_failure_type"] is not None
        or selected["prediction_kind"] != "model_generated"
        or runner.runtime.validate_stage_receipt(stage) != stage
        or runner.runtime.validate_budget_receipt(budget) != budget
        or runner.transport._validate_actual_effect_snapshot(effect) != effect
        or runner.transport._health(health) != health
        or stage["outer_physical_budget_receipt"] != budget
        or effect["logical_queries"] != budget["query_admitted_count"]
        or effect["fetch_requests"] != budget["fetch_admitted_count"]
        or effect["model_logical_requests"] != budget["model_admitted_count"]
        or any(
            selected[name] is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_population_replacement_or_selective_rerun",
                "contains_question_package_query_url_page_answer_or_credential_outside_prediction",
            )
        )
    ):
        raise RuntimeError("V2.52.64 content-free row drifted")
    return selected


def _parents() -> dict[str, str]:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.52.64 requires clean pushed HEAD")
    observed = {name: contract.sha256(_ordinary(path)) for name, path in PARENT_PATHS.items()}
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.52.64 frozen parent hash drifted")
    forward = runner.validate_forward_result(
        json.loads(_ordinary(contract.FORWARD_RESULT).read_text(encoding="utf-8"))
    )
    audit = parent.validate_audit(
        json.loads(_ordinary(contract.FORWARD_AUDIT).read_text(encoding="utf-8"))
    )
    if (
        forward["reliability_decision"]["reliability_gate_passed"] is not True
        or audit["audit_valid"] is not True
        or audit["findings"] != []
        or audit["forward_result_sha256"] != observed["forward_result"]
        or audit["task_rows_sha256"] != observed["task_rows"]
        or audit["prediction_freeze_sha256"] != observed["prediction_freeze"]
        or audit["authorization"]["postforward_reliability_diagnosis"] is not True
        or audit["authorization"]["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"] is not False
    ):
        raise RuntimeError("V2.52.64 frozen parent barrier drifted")
    return observed


def _aggregate() -> dict[str, Any]:
    rows = [
        safe_row(line)
        for line in _ordinary(contract.TASK_ROWS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.52.64 fixed denominator drifted")
    health_totals = Counter({name: 0 for name in HEALTH_NAMES})
    positive_rows: list[dict[str, Any]] = []
    stage_failures = 0
    budget_rejections = 0
    for row in rows:
        health_totals.update(row["effect_health"])
        if sum(row["effect_health"].values()) > 0:
            positive_rows.append(row)
        stage_failures += int(row["content_free_stage_receipt"]["failure_present"])
        budget = row["content_free_budget_receipt"]
        budget_rejections += int(
            budget["query_rejected_count"]
            + budget["fetch_rejected_count"]
            + budget["model_rejected_count"]
            > 0
        )

    affected_effects = [row["actual_effect_snapshot"] for row in positive_rows]
    output = {
        "fixed_task_denominator": len(rows),
        "runtime_completed_tasks": sum(row["runtime_completed"] for row in rows),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in rows),
        "model_generated_tasks": sum(row["prediction_kind"] == "model_generated" for row in rows),
        "fallback_tasks": sum(row["prediction_kind"] == "fallback" for row in rows),
        "stage_failure_tasks": stage_failures,
        "budget_rejection_tasks": budget_rejections,
        "terminal_effect_health_totals": dict(health_totals),
        "tasks_with_any_health_event": len(positive_rows),
        "tasks_with_only_one_search_transport_failure": sum(
            row["effect_health"]["search_transport_failures"] == 1
            and sum(row["effect_health"].values()) == 1
            for row in rows
        ),
        "affected_task_effect_totals": {
            "queries": sum(effect["logical_queries"] for effect in affected_effects),
            "fetch_requests": sum(effect["fetch_requests"] for effect in affected_effects),
            "fetch_calls": sum(effect["fetch_calls"] for effect in affected_effects),
            "model_logical_requests": sum(effect["model_logical_requests"] for effect in affected_effects),
            "model_provider_attempts": sum(effect["model_provider_attempts"] for effect in affected_effects),
            "model_provider_requests": sum(effect["model_provider_requests"] for effect in affected_effects),
            "model_provider_successes": sum(effect["model_provider_successes"] for effect in affected_effects),
        },
        "positive_signed_credit_count": 0,
    }
    expected_health = {name: 0 for name in HEALTH_NAMES}
    expected_health["search_transport_failures"] = 3
    if (
        output["fixed_task_denominator"] != 64
        or output["runtime_completed_tasks"] != 64
        or output["failure_as_zero_tasks"] != 0
        or output["model_generated_tasks"] != 64
        or output["fallback_tasks"] != 0
        or stage_failures != 0
        or budget_rejections != 0
        or output["terminal_effect_health_totals"] != expected_health
        or output["tasks_with_any_health_event"] != 3
        or output["tasks_with_only_one_search_transport_failure"] != 3
        or output["affected_task_effect_totals"]
        != {
            "queries": 12,
            "fetch_requests": 31,
            "fetch_calls": 31,
            "model_logical_requests": 10,
            "model_provider_attempts": 10,
            "model_provider_requests": 10,
            "model_provider_successes": 10,
        }
    ):
        raise RuntimeError("V2.52.64 expected aggregate drifted")
    return output


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": _parents(),
        "aggregate": _aggregate(),
        "conclusions": {
            "truthful_4_query_14_fetch_4_model_totality_gate_strict_go": True,
            "all_three_health_events_are_recoverable_search_transport_noise": True,
            "health_events_are_not_outer_stage_budget_fetch_model_or_timeout_failures": True,
            "affected_tasks_still_complete_with_model_generated_predictions": True,
            "fresh64_population_must_not_be_retried_replaced_or_reused": True,
            "fresh64_proves_totality_and_physical_caps_not_answer_quality": True,
            "latest_complete_deepwidebench_result_remains_v25208": True,
            "v24857_is_single_rollout_peak_not_stably_replicated_baseline": True,
            "next_exact220_may_reuse_only_the_verified_totality_shell_not_unproven_header_or_quote_treatments": True,
            "prediction_freeze_and_forward_audit_must_precede_any_evaluator": True,
        },
        "aggregate_score_context": {
            "latest_complete_v25208": {"exact_successes": 5, "denominator": 220, "composite": 0.39866919974486725},
            "single_rollout_peak_v24857": {"exact_successes": 9, "denominator": 220, "composite": 0.45724897824812605},
            "v24857_replication_v24969": {"exact_successes": 5, "denominator": 220, "composite": 0.4302256606559135},
            "avg_at_4_leaderboard_or_sota_evidence": False,
        },
        "content_policy": {
            "top_level_members_decoded": sorted(SAFE_MEMBERS),
            "all_other_top_level_values_skipped_lexically": True,
            "only_sealed_content_free_stage_budget_health_and_effect_objects_decoded": True,
            "task_identity_question_package_query_url_page_prediction_answer_gold_category_split_metric_score_or_credential_decoded_or_emitted": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "content_free_reliability_diagnosis": True,
            "build_exact220_totality_successor_from_verified_shell": True,
            "retry_resume_reuse_replacement_or_selective_rerun_of_v25260": False,
            "candidate_header_quote_or_entropy_treatment_activation": False,
            "external_forward": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    aggregate = copied.get("aggregate") or {}
    conclusions = copied.get("conclusions") or {}
    score = copied.get("aggregate_score_context") or {}
    policy = copied.get("content_policy") or {}
    authorization = copied.get("authorization") or {}
    expected_health = {name: 0 for name in HEALTH_NAMES}
    expected_health["search_transport_failures"] = 3
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "parents", "aggregate",
            "conclusions", "aggregate_score_context", "content_policy",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("parents") != EXPECTED_SHA256
        or aggregate.get("fixed_task_denominator") != 64
        or aggregate.get("runtime_completed_tasks") != 64
        or aggregate.get("failure_as_zero_tasks") != 0
        or aggregate.get("model_generated_tasks") != 64
        or aggregate.get("fallback_tasks") != 0
        or aggregate.get("stage_failure_tasks") != 0
        or aggregate.get("budget_rejection_tasks") != 0
        or aggregate.get("terminal_effect_health_totals") != expected_health
        or aggregate.get("tasks_with_any_health_event") != 3
        or aggregate.get("tasks_with_only_one_search_transport_failure") != 3
        or aggregate.get("affected_task_effect_totals")
        != {
            "queries": 12,
            "fetch_requests": 31,
            "fetch_calls": 31,
            "model_logical_requests": 10,
            "model_provider_attempts": 10,
            "model_provider_requests": 10,
            "model_provider_successes": 10,
        }
        or aggregate.get("positive_signed_credit_count") != 0
        or set(conclusions)
        != {
            "truthful_4_query_14_fetch_4_model_totality_gate_strict_go",
            "all_three_health_events_are_recoverable_search_transport_noise",
            "health_events_are_not_outer_stage_budget_fetch_model_or_timeout_failures",
            "affected_tasks_still_complete_with_model_generated_predictions",
            "fresh64_population_must_not_be_retried_replaced_or_reused",
            "fresh64_proves_totality_and_physical_caps_not_answer_quality",
            "latest_complete_deepwidebench_result_remains_v25208",
            "v24857_is_single_rollout_peak_not_stably_replicated_baseline",
            "next_exact220_may_reuse_only_the_verified_totality_shell_not_unproven_header_or_quote_treatments",
            "prediction_freeze_and_forward_audit_must_precede_any_evaluator",
        }
        or not all(conclusions.values())
        or score
        != {
            "latest_complete_v25208": {"exact_successes": 5, "denominator": 220, "composite": 0.39866919974486725},
            "single_rollout_peak_v24857": {"exact_successes": 9, "denominator": 220, "composite": 0.45724897824812605},
            "v24857_replication_v24969": {"exact_successes": 5, "denominator": 220, "composite": 0.4302256606559135},
            "avg_at_4_leaderboard_or_sota_evidence": False,
        }
        or policy
        != {
            "top_level_members_decoded": sorted(SAFE_MEMBERS),
            "all_other_top_level_values_skipped_lexically": True,
            "only_sealed_content_free_stage_budget_health_and_effect_objects_decoded": True,
            "task_identity_question_package_query_url_page_prediction_answer_gold_category_split_metric_score_or_credential_decoded_or_emitted": False,
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
            "build_exact220_totality_successor_from_verified_shell": True,
            "retry_resume_reuse_replacement_or_selective_rerun_of_v25260": False,
            "candidate_header_quote_or_entropy_treatment_activation": False,
            "external_forward": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.64 diagnosis drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if output.resolve() != (ROOT / OUTPUT).resolve():
        raise ValueError("V2.52.64 output path drifted")
    value = build_diagnosis()
    runner._publish_json(output, value)
    print(json.dumps({"path": str(OUTPUT), "role": ROLE}, sort_keys=True))


if __name__ == "__main__":
    main()
