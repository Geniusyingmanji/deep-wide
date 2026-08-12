#!/usr/bin/env python3
"""Aggregate reliability diagnosis for the frozen V2.52.08 exact-220 run.

The diagnosis reads only hash-bound, post-audited artifacts.  Runtime JSONL is
lexically decoded for content-free status, failure, health, and mechanism
receipts.  Evaluator JSONL is decoded only for its error field.  Task IDs,
questions, pages, predictions, evaluator metrics, gold data, categories, and
splits are never decoded or emitted.

This artifact may guide a build-only reliability observer.  It cannot
authorize another rollout, evaluation, retry, selective rerun, or leaderboard
claim.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
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

from scripts.diagnose_v25063_three_run_output_structure import (  # noqa: E402
    selected_top_level_fields,
)


DATE = "20260812"
OUTPUT = Path(f"results/v25209_v25208_exact220_reliability_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25209_v25208_exact220.py")
TEST = Path("tests/test_diagnose_v25209_v25208_exact220.py")

INPUTS = {
    "runtime_results": Path(
        f"outputs/v25208_quote_aware_exact220_r2_{DATE}/frozen_task_results.jsonl"
    ),
    "run_summary": Path(
        f"outputs/v25208_quote_aware_exact220_r2_{DATE}/run_summary.json"
    ),
    "compatibility_aggregate": Path(
        f"outputs/v25208_quote_aware_exact220_r2_{DATE}/compatibility_aggregate.json"
    ),
    "evaluator_results": Path(
        f"outputs/v25208_quote_aware_exact220_r2_{DATE}/evaluator/official_eval_results.jsonl"
    ),
    "result": Path(f"results/v25208_quote_aware_exact220_result_r2_{DATE}.json"),
    "postresult_audit": Path(
        f"results/v25208_quote_aware_exact220_postresult_audit_r2_{DATE}.json"
    ),
}

EXPECTED_SHA256 = {
    "runtime_results": "ea56b3966db6ffb003769061a13660e9ea3f1edeeca2ec4c9d2ee97dd6e575f5",
    "run_summary": "58389f6201f741f3139e58b4f650c959ba7c5cd04de5868fc9a49976974fbd74",
    "compatibility_aggregate": "26f969047a6847fa7313416a16e848bd8d72646e340f323d124da8a054dc0286",
    "evaluator_results": "4bdd898c1c15b4e1e7c364ad3f3bd012e91337b8586f10ae787b035ee94e5750",
    "result": "f7b048b7708e42a6daff57bf0b02244c4f81c290ef1d3ba9d56188aa6064cb5c",
    "postresult_audit": "360b655a083e1971b4d093906bea9ceb6d963a3a851fc8506821325e73b664e0",
}

RUNTIME_ROW_FIELDS = frozenset(
    {
        "runtime_completed",
        "failure_as_zero",
        "prediction_kind",
        "failure_types",
        "failure_observation",
        "effect_health",
        "content_free_receipt",
    }
)
EVALUATOR_ROW_FIELDS = frozenset({"error"})
RESULT_FIELDS = frozenset(
    {"status", "selected", "metrics", "efficiency", "comparisons", "claims"}
)
POSTAUDIT_FIELDS = frozenset({"audit_valid", "findings", "checks"})
FAILURE_TYPE_KEYS = frozenset(
    {"plan", "grounded_plan", "gain_verification", "production", "revision", "post_effect"}
)
HEALTH_FIELDS = (
    "search_transport_failures",
    "search_hard_total_wall_timeouts",
    "fetch_helper_failures",
    "fetch_deadline_rejections",
    "fetch_hard_deadline_failures",
    "model_request_failures",
    "model_hard_total_wall_timeouts",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.52.09 expected ordinary repository file")
    return path


def sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _selected_file(relative: Path, fields: frozenset[str]) -> dict[str, Any]:
    return selected_top_level_fields(
        _ordinary(relative).read_text(encoding="utf-8"), fields
    )


def _parents() -> dict[str, str]:
    observed = {name: sha256(path) for name, path in INPUTS.items()}
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.52.09 frozen parent hash drifted")
    post = _selected_file(INPUTS["postresult_audit"], POSTAUDIT_FIELDS)
    if (
        post.get("audit_valid") is not True
        or post.get("findings") != []
        or not isinstance(post.get("checks"), dict)
        or not post["checks"]
        or not all(value is True for value in post["checks"].values())
    ):
        raise RuntimeError("V2.52.09 parent post-result audit drifted")
    return observed


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V2.52.09 invalid content-free count: {name}")
    return value


def _runtime_decomposition() -> dict[str, Any]:
    rows = 0
    runtime_completed = 0
    failure_as_zero = 0
    model_generated = 0
    fallbacks = 0
    outer_codes: Counter[str] = Counter()
    completed_failure_types: Counter[str] = Counter()
    health_affected_tasks: Counter[str] = Counter()
    health_event_totals: Counter[str] = Counter()
    outer_health_affected_tasks: Counter[str] = Counter()
    quote_repair_applied = 0

    for line in _ordinary(INPUTS["runtime_results"]).read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        selected = selected_top_level_fields(line, RUNTIME_ROW_FIELDS)
        rows += 1
        completed = selected.get("runtime_completed")
        failed = selected.get("failure_as_zero")
        kind = selected.get("prediction_kind")
        if (
            not isinstance(completed, bool)
            or not isinstance(failed, bool)
            or completed is failed
            or kind not in {"model_generated", "fallback"}
        ):
            raise RuntimeError("V2.52.09 runtime terminal partition drifted")
        runtime_completed += int(completed)
        failure_as_zero += int(failed)
        model_generated += int(kind == "model_generated")
        fallbacks += int(kind == "fallback")

        health = selected.get("effect_health")
        if not isinstance(health, dict):
            raise RuntimeError("V2.52.09 effect-health envelope drifted")
        for name in HEALTH_FIELDS:
            count = _nonnegative_int(health.get(name), name)
            health_event_totals[name] += count
            health_affected_tasks[name] += int(count > 0)
            outer_health_affected_tasks[name] += int(failed and count > 0)

        if failed:
            observation = selected.get("failure_observation")
            if (
                not isinstance(observation, dict)
                or observation.get("outer_failure_stage") != "runtime"
                or observation.get("outer_failure_type") != "ValueError"
                or observation.get("static_exception_message_mapped") is not True
                or not isinstance(observation.get("failure_code"), str)
                or selected.get("failure_types") is not None
                or selected.get("content_free_receipt") is not None
                or kind != "fallback"
            ):
                raise RuntimeError("V2.52.09 outer failure envelope drifted")
            outer_codes[observation["failure_code"]] += 1
            continue

        if selected.get("failure_observation") is not None:
            raise RuntimeError("V2.52.09 completed row has outer failure")
        failure_types = selected.get("failure_types")
        receipt = selected.get("content_free_receipt")
        if (
            not isinstance(failure_types, dict)
            or set(failure_types) != FAILURE_TYPE_KEYS
            or not isinstance(receipt, dict)
        ):
            raise RuntimeError("V2.52.09 completed runtime envelope drifted")
        for stage, value in failure_types.items():
            if value is not None:
                if not isinstance(value, str) or not value:
                    raise RuntimeError("V2.52.09 failure type drifted")
                completed_failure_types[f"{stage}:{value}"] += 1
        quote_repair_applied += _nonnegative_int(
            receipt.get("quote_aware_repair_applied_count"),
            "quote_aware_repair_applied_count",
        )

    if rows != 220:
        raise RuntimeError("V2.52.09 runtime denominator drifted")
    return {
        "runtime_rows": rows,
        "runtime_completed_tasks": runtime_completed,
        "failure_as_zero_tasks": failure_as_zero,
        "model_generated_tables": model_generated,
        "fallback_tables": fallbacks,
        "outer_failure_fallback_tables": failure_as_zero,
        "completed_production_fallback_tables": fallbacks - failure_as_zero,
        "outer_failure_code_counts": dict(sorted(outer_codes.items())),
        "completed_failure_type_counts": dict(sorted(completed_failure_types.items())),
        "health_affected_task_counts": dict(sorted(health_affected_tasks.items())),
        "health_event_totals": dict(sorted(health_event_totals.items())),
        "outer_failure_health_affected_task_counts": dict(
            sorted(outer_health_affected_tasks.items())
        ),
        "quote_aware_repair_applied_count": quote_repair_applied,
        "task_identifier_question_page_prediction_or_score_decoded_or_emitted": False,
    }


def _evaluator_decomposition() -> dict[str, Any]:
    rows = 0
    codes: Counter[str] = Counter()
    for line in _ordinary(INPUTS["evaluator_results"]).read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        selected = selected_top_level_fields(line, EVALUATOR_ROW_FIELDS)
        rows += 1
        error = selected.get("error")
        if error is None:
            codes["valid"] += 1
        elif error == "RuntimeError: official evaluator reported an internal error":
            codes["internal_error"] += 1
        elif isinstance(error, str) and error.startswith(
            "RuntimeError: official evaluator returned out-of-range metrics:"
        ):
            codes["out_of_range_metric"] += 1
        else:
            codes["unclassified_error"] += 1
    if rows != 220:
        raise RuntimeError("V2.52.09 evaluator denominator drifted")
    return {
        "evaluator_rows": rows,
        "valid_rows": codes["valid"],
        "invalid_rows": rows - codes["valid"],
        "invalid_code_counts": {
            key: codes[key]
            for key in ("internal_error", "out_of_range_metric", "unclassified_error")
            if codes[key]
        },
        "instance_identifier_metric_or_score_emitted": False,
    }


def _benchmark_result() -> dict[str, Any]:
    selected = _selected_file(INPUTS["result"], RESULT_FIELDS)
    metrics = selected.get("metrics", {}).get("all_220")
    efficiency = selected.get("efficiency")
    claims = selected.get("claims")
    comparisons = selected.get("comparisons")
    if (
        selected.get("status") != "exact220_single_rollout_complete"
        or selected.get("selected") != 220
        or not isinstance(metrics, dict)
        or not isinstance(efficiency, dict)
        or not isinstance(claims, dict)
        or not isinstance(comparisons, dict)
        or claims.get("sota") is not False
        or claims.get("avg_at_4") is not False
        or claims.get("leaderboard_submitted") is not False
    ):
        raise RuntimeError("V2.52.09 result aggregate drifted")
    return {
        "selected": int(metrics["selected"]),
        "whole_table_successes": int(metrics["whole_table_successes"]),
        "score": float(metrics["score"]),
        "entity_acc": float(metrics["entity_acc"]),
        "f1_by_row": float(metrics["f1_by_row"]),
        "f1_by_item": float(metrics["f1_by_item"]),
        "column_f1": float(metrics["column_f1"]),
        "quality_composite": float(metrics["quality_composite"]),
        "evaluator_valid": int(metrics["evaluator_valid"]),
        "evaluator_invalid_or_not_run": int(metrics["evaluator_invalid_or_not_run"]),
        "model_generated_tables": int(metrics["model_generated_tables"]),
        "fallback_tables": int(metrics["fallback_tables"]),
        "system_total_tokens": int(metrics["system_total_tokens"]),
        "forward_wall_seconds": float(efficiency["forward_wall_seconds"]),
        "evaluator_parallel_wall_seconds": float(
            efficiency["evaluator_parallel_wall_seconds"]
        ),
        "v24857_whole_table_success_delta": int(
            comparisons["v24857_best"]["whole_table_success_delta"]
        ),
        "v24857_quality_composite_delta": float(
            comparisons["v24857_best"]["quality_composite_delta"]
        ),
        "v25130_whole_table_success_delta": int(
            comparisons["v25130_latest_complete"]["whole_table_success_delta"]
        ),
        "v25130_quality_composite_delta": float(
            comparisons["v25130_latest_complete"]["quality_composite_delta"]
        ),
        "avg_at_4": False,
        "leaderboard_submitted": False,
        "sota": False,
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parents = _parents()
    runtime = _runtime_decomposition()
    evaluator = _evaluator_decomposition()
    benchmark = _benchmark_result()
    summary = json.loads(_ordinary(INPUTS["run_summary"]).read_text(encoding="utf-8"))
    compatibility = json.loads(
        _ordinary(INPUTS["compatibility_aggregate"]).read_text(encoding="utf-8")
    )
    if (
        summary.get("selected") != 220
        or summary.get("completed") != 220
        or summary.get("runtime_completed") != runtime["runtime_completed_tasks"]
        or summary.get("failure_as_zero_tasks") != runtime["failure_as_zero_tasks"]
        or summary.get("model_generated_tables") != runtime["model_generated_tables"]
        or summary.get("fallback_tables") != runtime["fallback_tables"]
        or summary.get("same_raw_counterfactual_active_tasks") != 0
        or summary.get("prediction_changed_tasks") != 0
        or summary.get("positive_signed_credit_count") != 0
        or compatibility.get("task_count") != 220
        or compatibility.get("compatibility_applied_tasks") != 2
        or compatibility.get("compatibility_applied_runtime_completed_tasks") != 1
        or compatibility.get("compatibility_applied_outer_failure_tasks") != 1
        or compatibility.get("residual_v25158_receipt_failure_tasks") != 0
        or benchmark["evaluator_valid"] != evaluator["valid_rows"]
        or benchmark["evaluator_invalid_or_not_run"] != evaluator["invalid_rows"]
    ):
        raise RuntimeError("V2.52.09 cross-artifact aggregate drifted")

    mechanism = {
        "same_raw_counterfactual_active_tasks": 0,
        "prediction_changed_tasks": 0,
        "quote_aware_repair_applied_count": runtime[
            "quote_aware_repair_applied_count"
        ],
        "post_effect_compatibility_applied_tasks": 2,
        "positive_signed_credit_count": 0,
        "fullset_score_attributable_to_quote_aware_repair": False,
        "entropy_or_information_gain_policy_effect": False,
    }
    diagnosis = {
        "complete_exact220_result_exists": True,
        "current_result_is_not_project_best": True,
        "quote_aware_external_validity_not_established_on_fullset": True,
        "reliability_precedes_new_search_or_credit_treatment": True,
        "first_reliability_target_is_receipt_validation": True,
        "second_reliability_target_is_production_contract_totality": True,
        "evaluator_invalidity_requires_separate_offline_hardening": True,
        "search_transport_or_fetch_deadline_events_alone_explain_fallbacks": False,
        "next_candidate_is_content_free_receipt_disposition_observer_build_only": True,
        "next_candidate_may_preserve_completed_production_only_after_exact_safe_state_proof": True,
        "new_exact220_launch_authorized": False,
        "selective_retry_or_revaluation_authorized": False,
        "leaderboard_or_sota": False,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25209_v25208_exact220_aggregate_reliability_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": parents,
        "benchmark_result": benchmark,
        "runtime_reliability": runtime,
        "evaluator_reliability": evaluator,
        "mechanism": mechanism,
        "diagnosis": diagnosis,
        "content_policy": {
            "aggregate_only_output": True,
            "runtime_jsonl_decoded_fields": sorted(RUNTIME_ROW_FIELDS),
            "evaluator_jsonl_decoded_fields": sorted(EVALUATOR_ROW_FIELDS),
            "task_identifier_question_page_prediction_gold_category_split_metric_or_score_emitted": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "aggregate_reliability_diagnosis": True,
            "content_free_receipt_disposition_observer_build_only": True,
            "runtime_policy_or_prediction_change": False,
            "fresh_external_protocol_or_launch": False,
            "new_exact220_launch": False,
            "retry_resume_replacement_or_selective_rerun": False,
            "evaluator_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    benchmark = copied.get("benchmark_result") or {}
    runtime = copied.get("runtime_reliability") or {}
    evaluator = copied.get("evaluator_reliability") or {}
    mechanism = copied.get("mechanism") or {}
    diagnosis = copied.get("diagnosis") or {}
    policy = copied.get("content_policy") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "parents",
            "benchmark_result",
            "runtime_reliability",
            "evaluator_reliability",
            "mechanism",
            "diagnosis",
            "content_policy",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25209_v25208_exact220_aggregate_reliability_diagnosis"
        or copied.get("parents") != EXPECTED_SHA256
        or benchmark.get("selected") != 220
        or benchmark.get("whole_table_successes") != 5
        or benchmark.get("quality_composite") != 0.39866919974486725
        or benchmark.get("v24857_whole_table_success_delta") != -4
        or benchmark.get("v24857_quality_composite_delta") >= 0
        or benchmark.get("v25130_whole_table_success_delta") != 4
        or benchmark.get("v25130_quality_composite_delta") <= 0
        or benchmark.get("sota") is not False
        or runtime.get("runtime_rows") != 220
        or runtime.get("runtime_completed_tasks") != 209
        or runtime.get("failure_as_zero_tasks") != 11
        or runtime.get("model_generated_tables") != 204
        or runtime.get("fallback_tables") != 16
        or runtime.get("outer_failure_fallback_tables") != 11
        or runtime.get("completed_production_fallback_tables") != 5
        or runtime.get("outer_failure_code_counts")
        != {"v25135_receipt_validation": 10, "v25180_receipt_validation": 1}
        or runtime.get("completed_failure_type_counts")
        != {"post_effect:ValueError": 1, "production:ValueError": 5}
        or runtime.get("quote_aware_repair_applied_count") != 0
        or evaluator.get("evaluator_rows") != 220
        or evaluator.get("valid_rows") != 214
        or evaluator.get("invalid_rows") != 6
        or evaluator.get("invalid_code_counts")
        != {"internal_error": 5, "out_of_range_metric": 1}
        or mechanism
        != {
            "same_raw_counterfactual_active_tasks": 0,
            "prediction_changed_tasks": 0,
            "quote_aware_repair_applied_count": 0,
            "post_effect_compatibility_applied_tasks": 2,
            "positive_signed_credit_count": 0,
            "fullset_score_attributable_to_quote_aware_repair": False,
            "entropy_or_information_gain_policy_effect": False,
        }
        or any(
            diagnosis.get(name) is not True
            for name in (
                "complete_exact220_result_exists",
                "current_result_is_not_project_best",
                "quote_aware_external_validity_not_established_on_fullset",
                "reliability_precedes_new_search_or_credit_treatment",
                "first_reliability_target_is_receipt_validation",
                "second_reliability_target_is_production_contract_totality",
                "evaluator_invalidity_requires_separate_offline_hardening",
                "next_candidate_is_content_free_receipt_disposition_observer_build_only",
                "next_candidate_may_preserve_completed_production_only_after_exact_safe_state_proof",
            )
        )
        or diagnosis.get(
            "search_transport_or_fetch_deadline_events_alone_explain_fallbacks"
        )
        is not False
        or diagnosis.get("new_exact220_launch_authorized") is not False
        or diagnosis.get("selective_retry_or_revaluation_authorized") is not False
        or diagnosis.get("leaderboard_or_sota") is not False
        or policy.get("aggregate_only_output") is not True
        or policy.get("runtime_jsonl_decoded_fields") != sorted(RUNTIME_ROW_FIELDS)
        or policy.get("evaluator_jsonl_decoded_fields") != ["error"]
        or policy.get(
            "task_identifier_question_page_prediction_gold_category_split_metric_or_score_emitted"
        )
        is not False
        or policy.get("historical_outcome_used_as_future_runtime_router_signal")
        is not False
        or policy.get("credential_value_read_hashed_persisted_or_emitted")
        is not False
        or authorization
        != {
            "aggregate_reliability_diagnosis": True,
            "content_free_receipt_disposition_observer_build_only": True,
            "runtime_policy_or_prediction_change": False,
            "fresh_external_protocol_or_launch": False,
            "new_exact220_launch": False,
            "retry_resume_replacement_or_selective_rerun": False,
            "evaluator_or_revaluation": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.09 diagnosis drifted")
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
                    "whole_table_successes": value["benchmark_result"][
                        "whole_table_successes"
                    ],
                    "fallback_tables": value["runtime_reliability"][
                        "fallback_tables"
                    ],
                    "outer_failure_tasks": value["runtime_reliability"][
                        "failure_as_zero_tasks"
                    ],
                    "new_exact220_launch": value["authorization"][
                        "new_exact220_launch"
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
