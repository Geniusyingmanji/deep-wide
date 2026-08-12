#!/usr/bin/env python3
"""Counts-only diagnosis of the frozen V2.51.67 observer NO-GO.

Only terminal booleans, coarse failure names, effect counters, and the sealed
V2.51.65/V2.51.58/V2.51.35 content-free receipts are decoded.  Opaque task
identity, question, query, URL, page, key/value, parent payload, prediction,
mapping, gold, evaluator output, score, reward, and credential fields remain
opaque JSON character ranges and are never emitted.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25158_vertical_key_value_candidate_runtime as vertical  # noqa: E402
from deepwide_agent import v25165_observed_vertical_key_value_runtime as observed  # noqa: E402
from deepwide_agent import v25167_observed_vertical_external_contract as contract  # noqa: E402
from scripts import diagnose_v25146_v25145_quote_attested as scanner  # noqa: E402
from scripts import run_v25167_observed_vertical_external as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25169_v25167_observer_censoring_counts_only_diagnosis"
OUTPUT = Path(
    f"results/v25169_v25167_observer_censoring_diagnosis_v1_{DATE}.json"
)
FAILED_CHECKS = [
    "all_production_predictions_model_generated",
    "disposition_localization_is_nonzero_and_rejecting",
    "minimum_observed_page_and_vertical_block_reach",
    "observer_entry_completion_and_cache_exact",
    "revision_provider_forward_exactly_verified_gain",
    "sparse_provider_forward_formula",
    "verified_gain_range",
    "verified_gain_to_candidate_selector_forward_exact",
]
FUTURE_SURFACES = (
    contract.EVALUATOR,
    contract.EVALUATOR_TEST,
    contract.EVALUATOR_PROTOCOL,
    contract.RESULT,
    contract.POSTAUDIT,
    contract.POSTFREEZE_GOLD,
)
VERTICAL_RESULT_EXPECTED = frozenset(
    {
        "artifact_version",
        "benchmark_launch_or_evaluator_authorized",
        "content_free_receipt",
        "cost",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "opaque_id",
        "parent_result",
        "parent_result_payload_sha256",
        "policy_id",
        "prediction",
        "prediction_kind",
        "prediction_sha256",
        "production_prediction",
        "production_prediction_sha256",
        "result_payload_sha256",
        "role",
        "status",
    }
)
SPARSE_RESULT_EXPECTED = frozenset(
    {
        "artifact_version",
        "benchmark_launch_or_evaluator_authorized",
        "content_free_receipt",
        "cost",
        "entropy_or_information_gain_assigns_signed_credit",
        "failure_types",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "opaque_id",
        "parent_result",
        "parent_result_payload_sha256",
        "policy_id",
        "prediction",
        "prediction_kind",
        "prediction_sha256",
        "production_prediction",
        "production_prediction_sha256",
        "result_payload_sha256",
        "role",
        "status",
    }
)
FAILURE_KEYS = frozenset(
    {
        "plan",
        "grounded_plan",
        "gain_verification",
        "production",
        "revision",
        "post_effect",
    }
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.51.69 expected ordinary repository file")
    return path


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def _failure_map(value: object) -> dict[str, str | None]:
    if not isinstance(value, Mapping) or set(value) != FAILURE_KEYS:
        raise RuntimeError("V2.51.69 failure receipt drifted")
    output: dict[str, str | None] = {}
    for name in sorted(FAILURE_KEYS):
        item = value[name]
        if item is not None and (
            not isinstance(item, str) or not item or len(item) > 128
        ):
            raise RuntimeError("V2.51.69 unsafe failure receipt")
        output[name] = item
    return output


def safe_row(line: str) -> dict[str, Any]:
    """Decode only content-free receipts, counters, and coarse stage state."""

    top, top_raw = scanner._members(
        line,
        expected=scanner.EXPECTED_TOP,
        decode=frozenset(
            {
                "runtime_completed",
                "failure_as_zero",
                "prediction_kind",
                "failure_types",
                "content_free_receipt",
                "actual_effect_snapshot",
                "effect_health",
                "entropy_or_information_gain_assigns_signed_credit",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            }
        ),
        raw=frozenset({"parent_result"}),
    )
    vertical_result, vertical_raw = scanner._members(
        top_raw["parent_result"],
        expected=VERTICAL_RESULT_EXPECTED,
        decode=frozenset({"content_free_receipt"}),
        raw=frozenset({"parent_result"}),
    )
    sparse_result, _ = scanner._members(
        vertical_raw["parent_result"],
        expected=SPARSE_RESULT_EXPECTED,
        decode=frozenset({"content_free_receipt", "failure_types"}),
    )

    observed_receipt = observed.validate_receipt(top["content_free_receipt"])
    vertical_receipt = vertical.validate_receipt(
        vertical_result["content_free_receipt"]
    )
    sparse_receipt = sparse.validate_receipt(
        sparse_result["content_free_receipt"]
    )
    observed.validate_receipt(
        observed_receipt, parent_receipt=vertical_receipt
    )
    effect = runner._validate_actual_effect_snapshot(
        top["actual_effect_snapshot"]
    )
    health = runner._health(top["effect_health"])
    failures = _failure_map(top["failure_types"])
    sparse_failures = _failure_map(sparse_result["failure_types"])

    if (
        top["runtime_completed"] is not True
        or top["failure_as_zero"] is not False
        or top["prediction_kind"]
        != (
            "model_generated"
            if sparse_receipt["production_provider_output_valid"]
            else "fallback"
        )
        or failures != sparse_failures
        or top["entropy_or_information_gain_assigns_signed_credit"] is not False
        or top[
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or observed_receipt["parent_candidate_revision_entry_count"]
        != vertical_receipt["candidate_revision_entry_count"]
        or vertical_receipt["parent_revision_eligible"]
        is not sparse_receipt["revision_eligible"]
        or vertical_receipt["parent_revision_failure_present"]
        is not sparse_receipt["revision_failure_present"]
        or effect["model_provider_requests"]
        != sparse_receipt["model_provider_request_count"]
        or effect["model_provider_attempts"]
        != sparse_receipt["model_provider_attempt_count"]
        or effect["model_logical_requests"]
        != sparse_receipt["provider_forward_count"]
        or effect["logical_queries"] != sparse_receipt["physical_query_count"]
        or effect["fetch_requests"] != sparse_receipt["physical_fetch_count"]
        or health != top["effect_health"]
    ):
        raise RuntimeError("V2.51.69 content-free cross-binding drifted")

    return {
        "prediction_kind": top["prediction_kind"],
        "failures": failures,
        "observed_receipt": observed_receipt,
        "vertical_receipt": vertical_receipt,
        "sparse_receipt": sparse_receipt,
        "effect": effect,
        "health": health,
    }


def _safe_rows() -> list[dict[str, Any]]:
    rows = [
        safe_row(line)
        for line in _ordinary(contract.TASK_ROWS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.69 fixed denominator drifted")
    return rows


def _hist(values: Sequence[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.69 expected JSON object")
    return value


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    authorization = audit.get("authorization") or {}
    if (
        not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256")
        != contract.sha256(_ordinary(contract.FORWARD_RESULT))
        or audit.get("task_rows_sha256")
        != contract.sha256(_ordinary(contract.TASK_ROWS))
        or audit.get("prediction_freeze_sha256")
        != contract.sha256(_ordinary(contract.PREDICTION_FREEZE))
        or forward.get("mechanism_decision", {}).get("failed_checks")
        != FAILED_CHECKS
        or audit.get("mechanism_decision", {}).get("failed_checks")
        != FAILED_CHECKS
        or authorization
        != {
            "binding_successor_design": False,
            "postfreeze_external_evaluator_implementation_and_protocol": False,
            "vertical_binding_policy_change": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        }
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.51.69 frozen parent barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validate_parents()
    rows = _safe_rows()
    sparse_receipts = [row["sparse_receipt"] for row in rows]
    vertical_receipts = [row["vertical_receipt"] for row in rows]
    observed_receipts = [row["observed_receipt"] for row in rows]
    effects = [row["effect"] for row in rows]
    health = [row["health"] for row in rows]

    gain_validity = Counter(
        (
            bool(receipt["verified_source_identity_field_gain"]),
            bool(receipt["production_provider_output_valid"]),
        )
        for receipt in sparse_receipts
    )
    health_names = tuple(sorted(health[0]))
    funnel: dict[str, Any] = {
        "task_count": len(rows),
        "prediction_kind_histogram": _hist(
            [row["prediction_kind"] for row in rows]
        ),
        "production_failure_type_histogram": _hist(
            [row["failures"]["production"] for row in rows]
        ),
        "production_provider_output_valid_tasks": sum(
            value["production_provider_output_valid"]
            for value in sparse_receipts
        ),
        "production_fallback_tasks": sum(
            value["production_fallback_used"] for value in sparse_receipts
        ),
        "verified_gain_tasks": sum(
            value["verified_source_identity_field_gain"]
            for value in sparse_receipts
        ),
        "gain_by_production_validity": {
            "gain_false_valid_false": gain_validity[(False, False)],
            "gain_false_valid_true": gain_validity[(False, True)],
            "gain_true_valid_false": gain_validity[(True, False)],
            "gain_true_valid_true": gain_validity[(True, True)],
        },
        "verified_gain_with_valid_production_tasks": gain_validity[(True, True)],
        "verified_gain_censored_by_invalid_production_tasks": gain_validity[
            (True, False)
        ],
        "revision_synthesis_entry_tasks": sum(
            value["revision_synthesis_entry_count"] for value in sparse_receipts
        ),
        "revision_eligible_tasks": sum(
            value["revision_eligible"] for value in sparse_receipts
        ),
        "revision_provider_forward_tasks": sum(
            value["revision_synthesis_provider_forward_count"]
            for value in sparse_receipts
        ),
        "identity_replay_tasks": sum(
            value["identity_replay_used"] for value in sparse_receipts
        ),
        "candidate_revision_entry_tasks": sum(
            value["candidate_revision_entry_count"]
            for value in vertical_receipts
        ),
        "observer_entry_tasks": sum(
            value["disposition_observer_entry_count"]
            for value in observed_receipts
        ),
        "observer_completed_tasks": sum(
            value["disposition_observer_completed_count"]
            for value in observed_receipts
        ),
        "observer_failure_tasks": sum(
            value["disposition_observer_failure_present"]
            for value in observed_receipts
        ),
        "verified_delta_computations": sum(
            value["verified_delta_computation_count"]
            for value in observed_receipts
        ),
        "verified_delta_cache_reuses": sum(
            value["verified_delta_cache_reuse_count"]
            for value in observed_receipts
        ),
        "model_provider_request_total": sum(
            value["model_provider_requests"] for value in effects
        ),
        "model_provider_attempt_total": sum(
            value["model_provider_attempts"] for value in effects
        ),
        "model_provider_success_total": sum(
            value["model_provider_successes"] for value in effects
        ),
        "all_three_provider_calls_succeeded_tasks": sum(
            value["model_provider_requests"]
            == value["model_provider_attempts"]
            == value["model_provider_successes"]
            == 3
            for value in effects
        ),
        "effect_health_totals": {
            name: sum(value[name] for value in health) for name in health_names
        },
        "physical_query_total": sum(value["logical_queries"] for value in effects),
        "physical_fetch_total": sum(value["fetch_requests"] for value in effects),
        "physical_model_forward_total": sum(
            value["model_logical_requests"] for value in effects
        ),
    }
    expected = {
        "task_count": 20,
        "prediction_kind_histogram": {"fallback": 11, "model_generated": 9},
        "production_failure_type_histogram": {"None": 9, "ValueError": 11},
        "production_provider_output_valid_tasks": 9,
        "production_fallback_tasks": 11,
        "verified_gain_tasks": 3,
        "gain_by_production_validity": {
            "gain_false_valid_false": 8,
            "gain_false_valid_true": 9,
            "gain_true_valid_false": 3,
            "gain_true_valid_true": 0,
        },
        "verified_gain_with_valid_production_tasks": 0,
        "verified_gain_censored_by_invalid_production_tasks": 3,
        "revision_synthesis_entry_tasks": 20,
        "revision_eligible_tasks": 0,
        "revision_provider_forward_tasks": 0,
        "identity_replay_tasks": 20,
        "candidate_revision_entry_tasks": 0,
        "observer_entry_tasks": 0,
        "observer_completed_tasks": 0,
        "observer_failure_tasks": 0,
        "verified_delta_computations": 0,
        "verified_delta_cache_reuses": 0,
        "model_provider_request_total": 60,
        "model_provider_attempt_total": 60,
        "model_provider_success_total": 60,
        "all_three_provider_calls_succeeded_tasks": 20,
        "effect_health_totals": {name: 0 for name in health_names},
        "physical_query_total": 80,
        "physical_fetch_total": 208,
        "physical_model_forward_total": 60,
    }
    if funnel != expected:
        raise RuntimeError("V2.51.69 content-free funnel drifted")

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(
                _ordinary(contract.FORWARD_RESULT)
            ),
            "forward_audit_sha256": contract.sha256(
                _ordinary(contract.FORWARD_AUDIT)
            ),
            "prediction_freeze_sha256": contract.sha256(
                _ordinary(contract.PREDICTION_FREEZE)
            ),
            "task_rows_sha256": contract.sha256(_ordinary(contract.TASK_ROWS)),
            "audit_valid": True,
            "localization_gate_passed": False,
            "failed_checks": list(FAILED_CHECKS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "diagnosis": {
            "provider_transport_search_fetch_and_hard_deadline_failure_are_not_the_observed_cause": True,
            "eleven_production_outputs_failed_the_frozen_table_contract_after_successful_provider_effect": True,
            "all_three_verified_retrieval_gain_tasks_have_invalid_production_outputs": True,
            "revision_eligibility_is_conjunctive_verified_gain_and_valid_production": True,
            "the_conjunction_censored_all_candidate_and_observer_entries": True,
            "zero_observer_entry_does_not_establish_zero_vertical_surface_or_zero_identity_binding": True,
            "v25167_does_not_measure_vertical_disposition_reachability": True,
            "current_receipts_cannot_distinguish_no_pipe_table_bad_separator_row_width_escaped_pipe_ambiguity_or_other_normalizer_rejection": True,
            "next_build_only_candidate_is_a_behavior_preserving_content_free_production_normalizer_disposition_observer": True,
            "normalizer_observer_must_run_on_first_production_response_before_fallback_and_never_change_output": True,
            "normalizer_observer_must_not_emit_response_question_identity_url_page_value_prediction_or_semantic_hash": True,
            "fresh_disjoint_population_is_required_and_v25167_must_not_be_retried_resumed_or_reused": True,
            "binding_policy_search_query_fetch_model_context_token_wall_and_network_caps_must_not_change": True,
            "quality_effect_is_unknown_and_evaluator_remains_forbidden": True,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "benchmark_status": {
            "latest_normal_complete_run": "v25057_page_self_exact220_r2",
            "latest_normal_complete_exact_over_220": 6,
            "latest_normal_complete_composite": 0.4499596032520462,
            "latest_complete_but_severely_degraded_run": "v25130_causal_salience_exact220",
            "latest_complete_but_severely_degraded_exact_over_220": 1,
            "latest_complete_but_severely_degraded_composite": 0.3778654237910814,
            "best_observed_single_rollout_run": "v24857_pacing_aware_exact220",
            "best_observed_single_rollout_exact_over_220": 9,
            "best_observed_single_rollout_composite": 0.45724897824812605,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
        "content_policy": {
            "decoded_surfaces": [
                "terminal_booleans_and_coarse_failure_types",
                "content_free_effect_and_health_counters",
                "v25165_content_free_observer_receipt",
                "v25158_content_free_vertical_candidate_receipt",
                "v25135_content_free_sparse_production_receipt",
            ],
            "opaque_id_question_query_url_title_page_key_value_parent_payload_prediction_answer_mapping_gold_category_split_evaluator_score_reward_credential_decoded": False,
            "disallowed_members_scanned_only_to_find_json_boundaries": True,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        },
        "authorization": {
            "production_normalizer_disposition_observer_build_only": True,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "new_external_protocol_or_launch": False,
            "v25167_evaluator_or_quality_result": False,
            "v25167_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
        "findings": [],
        "diagnosis_valid": True,
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    funnel = copied.get("content_free_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("parents", {}).get("audit_valid") is not True
        or copied.get("parents", {}).get("localization_gate_passed") is not False
        or copied.get("parents", {}).get("failed_checks") != FAILED_CHECKS
        or funnel.get("task_count") != 20
        or funnel.get("production_provider_output_valid_tasks") != 9
        or funnel.get("production_fallback_tasks") != 11
        or funnel.get("verified_gain_tasks") != 3
        or funnel.get("verified_gain_with_valid_production_tasks") != 0
        or funnel.get("verified_gain_censored_by_invalid_production_tasks") != 3
        or funnel.get("revision_eligible_tasks") != 0
        or funnel.get("candidate_revision_entry_tasks") != 0
        or funnel.get("observer_entry_tasks") != 0
        or funnel.get("all_three_provider_calls_succeeded_tasks") != 20
        or any(funnel.get("effect_health_totals", {}).values())
        or diagnosis.get(
            "zero_observer_entry_does_not_establish_zero_vertical_surface_or_zero_identity_binding"
        )
        is not True
        or diagnosis.get(
            "next_build_only_candidate_is_a_behavior_preserving_content_free_production_normalizer_disposition_observer"
        )
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or authorization
        != {
            "production_normalizer_disposition_observer_build_only": True,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "new_external_protocol_or_launch": False,
            "v25167_evaluator_or_quality_result": False,
            "v25167_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.69 diagnosis drifted")
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
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "role": ROLE}, sort_keys=True))


if __name__ == "__main__":
    main()
