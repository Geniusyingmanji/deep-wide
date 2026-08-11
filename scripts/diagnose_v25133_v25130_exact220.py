#!/usr/bin/env python3
"""Aggregate post-result diagnosis for frozen V2.51.30 exact-220.

This offline diagnosis binds only already-frozen artifacts.  Runtime rows are
lexically decoded for a small content-free field set; predictions, pages,
queries, evaluator rows, gold, categories, splits, and per-task scores are not
decoded.  Opaque IDs and visible questions are used transiently only to count
whether the label-blind visible-schema parser was total.  Neither is emitted.

The result is diagnostic and build-design authority only.  It cannot launch a
forward, evaluator, retry, replacement, selective rerun, or leaderboard job.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
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

from deepwide_agent import v25110_exact_visible_schema as visible_schema  # noqa: E402
from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from scripts.diagnose_v25063_three_run_output_structure import (  # noqa: E402
    selected_top_level_fields,
)


DATE = "20260811"
OUTPUT = Path(f"results/v25133_v25130_exact220_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25133_v25130_exact220.py")
TEST = Path("tests/test_diagnose_v25133_v25130_exact220.py")

INPUTS = {
    "runtime_results": contract.RUNTIME_RESULTS,
    "run_summary": contract.RUN_SUMMARY,
    "forward_result": contract.FORWARD_RESULT,
    "result": Path(
        f"results/v25132_v25130_terminal_summary_exact220_result_v1_{DATE}.json"
    ),
    "postresult_audit": Path(
        f"results/v25132_v25130_terminal_summary_exact220_postresult_audit_v1_{DATE}.json"
    ),
    "baseline_result": contract.BASELINE_RESULT,
}

EXPECTED_SHA256 = {
    "runtime_results": "25dbd4d162ef14916425e8c5a1073169d534c3c0719576cdfd4fefb767b9e18f",
    "run_summary": "4a98580f3d66864f7ebf19572421bb36b846b87b123ca289e64a58d08d6a9887",
    "forward_result": "ba49f6fe517c7a6dcea270163e2338ee4ef69919dba545fef22dabbf7ef0cb33",
    "result": "b84bcecb9454ebfd315e2c249eb4eaf6529a2b9a0d9853db32a77aed34b9c752",
    "postresult_audit": "6dde295aa4328d38b07ba9cde3d2a3edd0ff8bcac1c98897199b4c7175aa9a62",
    "baseline_result": "a9e51c5c479a79e46f74574dac905bc607032be501b8a21a696106172f59f1d9",
}

RUNTIME_ROW_FIELDS = frozenset(
    {
        "opaque_id",
        "runtime_completed",
        "failure_as_zero",
        "outer_failure_type",
        "model_success",
        "actual_effect_snapshot",
    }
)

SUMMARY_FIELDS = frozenset(
    {
        "selected",
        "completed",
        "runtime_completed",
        "failure_as_zero_tasks",
        "model_generated_tables",
        "fallback_tables",
        "both_arms_model_success_tasks",
        "grounded_plan_strategy_applied_tasks",
        "selection_changed_tasks",
        "positive_target_field_page_gain_tasks",
        "retrieval_mechanism_engaged_tasks",
        "prediction_changed_tasks",
        "attributable_prediction_changed_tasks",
        "unattributable_prediction_changed_tasks",
        "prediction_identity_handoff_tasks",
        "grounded_prompt_checklist_tasks",
        "paired_synthesis_salience_tasks",
        "prompt_length_preserved_tasks",
        "physical_query_count",
        "physical_fetch_count",
        "physical_model_logical_call_count",
        "model_provider_request_count",
        "system_total_tokens",
        "forward_wall_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "official_evaluator_called",
    }
)

RESULT_FIELDS = frozenset({"selected", "metrics", "efficiency", "claims", "status"})
POSTAUDIT_FIELDS = frozenset({"audit_valid", "findings"})
EFFECT_FIELDS = (
    "model_logical_requests",
    "logical_queries",
    "fetch_requests",
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
        raise RuntimeError("V2.51.33 expected ordinary repository file")
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
        raise RuntimeError("V2.51.33 frozen parent hash drifted")
    post = _selected_file(INPUTS["postresult_audit"], POSTAUDIT_FIELDS)
    if post != {"audit_valid": True, "findings": []}:
        raise RuntimeError("V2.51.33 parent postresult audit drifted")
    return observed


def _bounded_count(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V2.51.33 invalid content-free count: {name}")
    return value


def _runtime_decomposition() -> dict[str, Any]:
    tasks = contract.task_vector(ROOT)
    questions = {task["opaque_id"]: task["question"] for task in tasks}
    if len(questions) != 220:
        raise RuntimeError("V2.51.33 visible task vector drifted")

    rows = 0
    identifiers: set[str] = set()
    failures: Counter[str] = Counter()
    schema_absent = schema_present = 0
    zero_effect = nonzero_effect = 0
    zero_effect_schema_absent = nonzero_effect_schema_present = 0
    failure_effect_totals: Counter[str] = Counter()
    completed_candidate_fallback = 0

    for line in _ordinary(INPUTS["runtime_results"]).read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        selected = selected_top_level_fields(line, RUNTIME_ROW_FIELDS)
        identifier = selected["opaque_id"]
        if (
            not isinstance(identifier, str)
            or re.fullmatch(r"task_[0-9a-f]{24}", identifier) is None
            or identifier not in questions
            or identifier in identifiers
        ):
            raise RuntimeError("V2.51.33 runtime identity drifted")
        identifiers.add(identifier)
        rows += 1
        completed = selected["runtime_completed"]
        failed = selected["failure_as_zero"]
        if not isinstance(completed, bool) or not isinstance(failed, bool):
            raise RuntimeError("V2.51.33 terminal state drifted")
        if completed is failed:
            raise RuntimeError("V2.51.33 completion/failure partition drifted")

        success = selected["model_success"]
        if not isinstance(success, dict) or set(success) != set(contract.ARMS):
            raise RuntimeError("V2.51.33 model-success envelope drifted")
        if completed and success[contract.CANDIDATE_ARM] is False:
            completed_candidate_fallback += 1

        if not failed:
            if selected["outer_failure_type"] is not None:
                raise RuntimeError("V2.51.33 completed row has outer failure")
            continue

        failure_type = selected["outer_failure_type"]
        if not isinstance(failure_type, str) or not failure_type:
            raise RuntimeError("V2.51.33 outer failure type drifted")
        failures[failure_type] += 1
        snapshot = selected["actual_effect_snapshot"]
        if (
            not isinstance(snapshot, dict)
            or snapshot.get(
                "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential"
            )
            is not False
            or snapshot.get(
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            )
            is not False
        ):
            raise RuntimeError("V2.51.33 actual-effect receipt drifted")
        effect_counts = {
            name: _bounded_count(snapshot.get(name), name) for name in EFFECT_FIELDS
        }
        for name, count in effect_counts.items():
            failure_effect_totals[name] += count
        has_effect = any(effect_counts.values())
        columns = visible_schema.extract_exact_visible_columns(questions[identifier])
        if columns:
            schema_present += 1
        else:
            schema_absent += 1
        if has_effect:
            nonzero_effect += 1
            nonzero_effect_schema_present += int(bool(columns))
        else:
            zero_effect += 1
            zero_effect_schema_absent += int(not columns)

    if rows != 220 or identifiers != set(questions):
        raise RuntimeError("V2.51.33 runtime denominator drifted")
    return {
        "runtime_rows": rows,
        "outer_failure_rows": sum(failures.values()),
        "outer_failure_types": dict(sorted(failures.items())),
        "zero_effect_outer_failures": zero_effect,
        "nonzero_effect_outer_failures": nonzero_effect,
        "exact_visible_schema_absent_outer_failures": schema_absent,
        "exact_visible_schema_present_outer_failures": schema_present,
        "zero_effect_and_exact_schema_absent": zero_effect_schema_absent,
        "nonzero_effect_and_exact_schema_present": nonzero_effect_schema_present,
        "outer_failure_effect_totals": dict(failure_effect_totals),
        "runtime_completed_candidate_fallbacks": completed_candidate_fallback,
        "task_identifier_or_question_emitted": False,
        "prediction_query_url_page_gold_category_split_or_per_task_score_decoded": False,
    }


def _all220(relative: Path) -> dict[str, Any]:
    selected = _selected_file(relative, RESULT_FIELDS)
    metrics = selected.get("metrics", {}).get("all_220")
    if (
        selected.get("selected") != 220
        or selected.get("status") != "exact220_single_rollout_complete"
        or not isinstance(metrics, dict)
        or metrics.get("selected") != 220
        or selected.get("claims", {}).get("sota") is not False
    ):
        raise RuntimeError("V2.51.33 result aggregate drifted")
    return {
        "whole_table_successes": int(metrics["whole_table_successes"]),
        "score": float(metrics["score"]),
        "quality_composite": float(metrics["quality_composite"]),
        "entity_acc": float(metrics["entity_acc"]),
        "f1_by_row": float(metrics["f1_by_row"]),
        "f1_by_item": float(metrics["f1_by_item"]),
        "column_f1": float(metrics["column_f1"]),
        "evaluator_valid": int(metrics["evaluator_valid"]),
        "evaluator_error_as_zero": int(metrics["evaluator_invalid_or_not_run"]),
        "model_generated_tables": int(metrics["model_generated_tables"]),
        "fallback_tables": int(metrics["fallback_tables"]),
        "system_total_tokens": int(metrics["system_total_tokens"]),
        "forward_wall_seconds": float(selected["efficiency"]["forward_wall_seconds"]),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parents = _parents()
    summary = _selected_file(INPUTS["run_summary"], SUMMARY_FIELDS)
    if (
        summary["selected"] != 220
        or summary["completed"] != 220
        or summary["runtime_completed"] + summary["failure_as_zero_tasks"] != 220
        or summary["model_generated_tables"] + summary["fallback_tables"] != 220
        or summary[
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        ]
        is not False
        or summary["entropy_or_information_gain_assigns_signed_credit"] is not False
        or summary["official_evaluator_called"] is not False
    ):
        raise RuntimeError("V2.51.33 run summary drifted")

    decomposition = _runtime_decomposition()
    if (
        decomposition["outer_failure_rows"] != summary["failure_as_zero_tasks"]
        or decomposition["runtime_completed_candidate_fallbacks"]
        != summary["fallback_tables"] - summary["failure_as_zero_tasks"]
    ):
        raise RuntimeError("V2.51.33 runtime/summary decomposition drifted")

    current = _all220(INPUTS["result"])
    baseline = _all220(INPUTS["baseline_result"])
    comparison = {
        "whole_table_success_delta": current["whole_table_successes"]
        - baseline["whole_table_successes"],
        "score_delta": current["score"] - baseline["score"],
        "quality_composite_delta": current["quality_composite"]
        - baseline["quality_composite"],
        "entity_acc_delta": current["entity_acc"] - baseline["entity_acc"],
        "f1_by_row_delta": current["f1_by_row"] - baseline["f1_by_row"],
        "f1_by_item_delta": current["f1_by_item"] - baseline["f1_by_item"],
        "column_f1_delta": current["column_f1"] - baseline["column_f1"],
        "system_total_token_ratio": current["system_total_tokens"]
        / baseline["system_total_tokens"],
        "forward_wall_seconds_delta": current["forward_wall_seconds"]
        - baseline["forward_wall_seconds"],
    }
    mechanism = {
        "runtime_completed_tasks": int(summary["runtime_completed"]),
        "grounded_plan_strategy_applied_tasks": int(
            summary["grounded_plan_strategy_applied_tasks"]
        ),
        "selection_changed_tasks": int(summary["selection_changed_tasks"]),
        "positive_target_field_page_gain_tasks": int(
            summary["positive_target_field_page_gain_tasks"]
        ),
        "retrieval_mechanism_engaged_tasks": int(
            summary["retrieval_mechanism_engaged_tasks"]
        ),
        "attributable_prediction_changed_tasks": int(
            summary["attributable_prediction_changed_tasks"]
        ),
        "unattributable_prediction_changed_tasks": int(
            summary["unattributable_prediction_changed_tasks"]
        ),
        "paired_synthesis_salience_tasks": int(
            summary["paired_synthesis_salience_tasks"]
        ),
        "prediction_identity_handoff_tasks": int(
            summary["prediction_identity_handoff_tasks"]
        ),
        "retrieval_mechanism_engagement_rate_over_completed": summary[
            "retrieval_mechanism_engaged_tasks"
        ]
        / summary["runtime_completed"],
        "identity_handoff_rate_over_completed": summary[
            "prediction_identity_handoff_tasks"
        ]
        / summary["runtime_completed"],
        "physical_query_count": int(summary["physical_query_count"]),
        "physical_fetch_count": int(summary["physical_fetch_count"]),
        "physical_model_logical_call_count": int(
            summary["physical_model_logical_call_count"]
        ),
    }

    diagnosis = {
        "schema_totality_bug_established": decomposition[
            "zero_effect_and_exact_schema_absent"
        ]
        == 26,
        "nonzero_effect_outer_failure_is_separate": decomposition[
            "nonzero_effect_outer_failures"
        ]
        == 1,
        "transport_or_provider_failure_explains_zero_effect_failures": False,
        "current_exact220_strictly_below_v24857": comparison[
            "whole_table_success_delta"
        ]
        < 0
        and comparison["quality_composite_delta"] < 0,
        "paired_synthesis_is_dense_but_retrieval_gain_is_sparse": mechanism[
            "paired_synthesis_salience_tasks"
        ]
        == mechanism["runtime_completed_tasks"]
        and mechanism["retrieval_mechanism_engaged_tasks"] == 3,
        "next_candidate_requires_schema_total_visible_fallback": True,
        "next_candidate_uses_one_production_synthesis_without_verified_gain": True,
        "second_synthesis_allowed_only_after_same_forward_verified_gain": True,
        "next_candidate_must_preserve_parent_prediction_on_posteffect_invariant_failure": True,
        "next_candidate_must_not_increase_query_fetch_model_context_token_or_wall_caps": True,
        "entropy_or_information_gain_signed_credit": 0,
        "positive_credit_requires_admissible_observation_matched_prediction_change_and_outer_utility": True,
        "new_exact220_launch_authorized": False,
        "leaderboard_or_sota": False,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25133_v25130_exact220_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": parents,
        "runtime_decomposition": decomposition,
        "mechanism_funnel": mechanism,
        "runs": {"v25130": current, "v24857": baseline},
        "v25130_minus_v24857": comparison,
        "diagnosis": diagnosis,
        "content_policy": {
            "aggregate_only_output": True,
            "task_identifier_question_prediction_query_url_page_gold_category_split_or_per_task_score_emitted": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
            "offline_visible_schema_totality_check_only": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "credential_value_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "aggregate_diagnosis": True,
            "schema_total_sparse_synthesis_build_design": True,
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
    decomposition = copied.get("runtime_decomposition") or {}
    mechanism = copied.get("mechanism_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    policy = copied.get("content_policy") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25133_v25130_exact220_aggregate_diagnosis"
        or copied.get("parents") != EXPECTED_SHA256
        or decomposition.get("runtime_rows") != 220
        or decomposition.get("outer_failure_rows") != 27
        or decomposition.get("outer_failure_types") != {"ValueError": 27}
        or decomposition.get("zero_effect_outer_failures") != 26
        or decomposition.get("nonzero_effect_outer_failures") != 1
        or decomposition.get("zero_effect_and_exact_schema_absent") != 26
        or decomposition.get("nonzero_effect_and_exact_schema_present") != 1
        or decomposition.get("runtime_completed_candidate_fallbacks") != 9
        or mechanism.get("runtime_completed_tasks") != 193
        or mechanism.get("paired_synthesis_salience_tasks") != 193
        or mechanism.get("prediction_identity_handoff_tasks") != 190
        or mechanism.get("retrieval_mechanism_engaged_tasks") != 3
        or mechanism.get("attributable_prediction_changed_tasks") != 3
        or mechanism.get("unattributable_prediction_changed_tasks") != 0
        or copied.get("runs", {}).get("v25130", {}).get(
            "whole_table_successes"
        )
        != 1
        or copied.get("runs", {}).get("v24857", {}).get(
            "whole_table_successes"
        )
        != 9
        or copied.get("v25130_minus_v24857", {}).get(
            "whole_table_success_delta"
        )
        != -8
        or copied.get("v25130_minus_v24857", {}).get(
            "quality_composite_delta"
        )
        >= 0
        or any(
            diagnosis.get(name) is not True
            for name in (
                "schema_totality_bug_established",
                "nonzero_effect_outer_failure_is_separate",
                "current_exact220_strictly_below_v24857",
                "paired_synthesis_is_dense_but_retrieval_gain_is_sparse",
                "next_candidate_requires_schema_total_visible_fallback",
                "next_candidate_uses_one_production_synthesis_without_verified_gain",
                "second_synthesis_allowed_only_after_same_forward_verified_gain",
                "next_candidate_must_preserve_parent_prediction_on_posteffect_invariant_failure",
                "next_candidate_must_not_increase_query_fetch_model_context_token_or_wall_caps",
                "positive_credit_requires_admissible_observation_matched_prediction_change_and_outer_utility",
            )
        )
        or diagnosis.get(
            "transport_or_provider_failure_explains_zero_effect_failures"
        )
        is not False
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or diagnosis.get("new_exact220_launch_authorized") is not False
        or diagnosis.get("leaderboard_or_sota") is not False
        or authorization
        != {
            "aggregate_diagnosis": True,
            "schema_total_sparse_synthesis_build_design": True,
            "fresh_external_protocol_or_launch": False,
            "new_exact220_launch": False,
            "retry_resume_replacement_or_selective_rerun": False,
            "evaluator_or_revaluation": False,
            "leaderboard_or_sota": False,
        }
        or policy.get("aggregate_only_output") is not True
        or policy.get(
            "task_identifier_question_prediction_query_url_page_gold_category_split_or_per_task_score_emitted"
        )
        is not False
        or policy.get("historical_outcome_used_as_future_runtime_router_signal")
        is not False
        or policy.get("credential_value_read_hashed_persisted_or_emitted")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.33 diagnosis drifted")
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
                    "outer_failures": value["runtime_decomposition"][
                        "outer_failure_rows"
                    ],
                    "schema_absent_zero_effect_failures": value[
                        "runtime_decomposition"
                    ]["zero_effect_and_exact_schema_absent"],
                    "whole_table_success_delta": value["v25130_minus_v24857"][
                        "whole_table_success_delta"
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
