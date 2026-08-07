"""Shared-prefix three-arm lookup budget ladder for external table tasks.

The runtime accepts only ``{opaque_id, question}``.  One planner, generic
retrieval prefix, and expanded-schema synthesis are executed once.  Four exact
World Bank lookups (one visible target per visible country) are then frozen as
the common wave-one state.  The three predictions are deterministic views of
that state:

* ``first_wave_only`` stops at the frozen state;
* ``fixed_full_budget`` adds the other four exact lookups;
* ``coverage_risk_adaptive`` uses a calibration-bound, content-free decision
  made before those other responses are inspected.

The fixed arm necessarily executes the wave-two suffix in a paired run.  A
stopping adaptive arm cannot read those records and is charged only its
logical prefix cost.  Entropy is a shadow feature, never signed credit.  This
module has no filesystem, process, network, benchmark, evaluator, gold, score,
reward, or category capability; all effects come from caller-owned clients.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .clients import parse_json_object
from .v24257_score_first_runtime import (
    PLAN_SYSTEM,
    PLAN_USER,
    SYNTHESIS_SYSTEM,
    SYNTHESIS_USER,
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    _model_text,
    _validated_plan,
    validate_visible_task,
)
from .v24269_task_union_discovery import TaskUnionDiscoverySearchClient
from .v24272_two_wave_entropy_voc import beta_expected_information_gain
from .v24325_shared_prefix_revision_runtime import _format_evidence
from .v24637_objective_alignment_runtime import (
    MODEL_COUNTERS,
    SEARCH_COUNTERS,
    _Budget,
    payload_sha256,
)
from .v24644_primary_identity_pair_runtime import (
    _final_url_page_vector,
    _page_title_only_lead_requests,
)
from .v24686_worldbank_target_value_runtime import (
    COUNTRY_COUNT,
    EXPECTED_COLUMN_COUNT,
    TARGETED_LOOKUP_CAP,
    TARGET_COLUMN_COUNT,
    LOOKUP_STAT_KEYS,
    _canonical,
    _matrix,
    _unknown_table,
    _visible_contract,
    apply_target_values,
    project_exact_lookup_responses,
    project_visible_rows,
    target_lookup_requests,
    validate_official_records,
    validate_visible_contract,
    visible_query_vector,
)


POLICY_ID = "v24804_shared_prefix_coverage_risk_budget_ladder_v1"
ROLE = "v24804_shared_prefix_budget_ladder_task_result"
RECEIPT_ROLE = "v24804_shared_prefix_budget_ladder_receipt"
DECISION_ROLE = "v24804_coverage_risk_voc_decision"
ARMS = ("first_wave_only", "fixed_full_budget", "coverage_risk_adaptive")
GENERIC_FETCH_CAP = 2
FIRST_WAVE_LOOKUP_CAP = 4
SECOND_WAVE_LOOKUP_CAP = 4
DECISIONS = frozenset({"expand", "stop"})
SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclasses.dataclass(frozen=True)
class AdaptivePolicy:
    """Calibration-bound policy; values must be frozen outside evaluation."""

    calibration_ref_sha256: str
    calibration_complete: bool = True
    beta_prior_alpha: float = 1.0
    beta_prior_beta: float = 1.0
    per_lookup_cost: float = 0.04
    minimum_net_value: float = 0.0
    information_gain_feature_weight: float = 0.0

    def validate(self) -> None:
        if SHA256.fullmatch(str(self.calibration_ref_sha256)) is None:
            raise ValueError("V2.48.04 calibration reference drifted")
        if not isinstance(self.calibration_complete, bool):
            raise ValueError("V2.48.04 calibration readiness is not boolean")
        for name in (
            "beta_prior_alpha", "beta_prior_beta", "per_lookup_cost",
            "minimum_net_value", "information_gain_feature_weight",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"V2.48.04 {name} is not numeric")
            if not math.isfinite(float(value)):
                raise ValueError(f"V2.48.04 {name} is not finite")
        if self.beta_prior_alpha <= 0 or self.beta_prior_beta <= 0:
            raise ValueError("V2.48.04 Beta prior is not positive")
        if self.per_lookup_cost < 0 or self.information_gain_feature_weight != 0:
            raise ValueError(
                "V2.48.04 unvalidated entropy weight or negative lookup cost"
            )


def _policy_dict(policy: AdaptivePolicy) -> dict[str, Any]:
    policy.validate()
    return dataclasses.asdict(policy)


def _request_partition(
    visible_contract: Mapping[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Put target 0 for every country in wave one and target 1 in wave two."""

    requests = target_lookup_requests(visible_contract)
    first = requests[0::TARGET_COLUMN_COUNT]
    second = requests[1::TARGET_COLUMN_COUNT]
    if (
        len(requests) != TARGETED_LOOKUP_CAP
        or len(first) != FIRST_WAVE_LOOKUP_CAP
        or len(second) != SECOND_WAVE_LOOKUP_CAP
        or len({request["member_label"] for request in requests})
        != TARGETED_LOOKUP_CAP
    ):
        raise RuntimeError("V2.48.04 lookup partition drifted")
    return first, second


def _record_country_set(records: Sequence[Mapping[str, str]]) -> set[str]:
    return {str(record.get("country_iso3", "")) for record in records}


def _validate_lookup_stats(
    value: Mapping[str, Any], records: Sequence[Mapping[str, str]]
) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(LOOKUP_STAT_KEYS):
        raise ValueError("V2.48.04 lookup statistic schema drifted")
    copied: dict[str, int] = {}
    for name in LOOKUP_STAT_KEYS:
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("V2.48.04 lookup statistic value drifted")
        copied[name] = number
    if (
        copied["requested_target_count"] != TARGETED_LOOKUP_CAP
        or copied["valid_exact_record_count"] != len(records)
        or copied["returned_result_count"]
        != copied["valid_exact_record_count"]
        + copied["null_value_record_count"]
        + copied["invalid_exact_response_count"]
        + copied["unmatched_or_duplicate_result_count"]
        or copied["requested_target_count"]
        != copied["valid_exact_record_count"]
        + copied["null_value_record_count"]
        + copied["invalid_exact_response_count"]
        + copied["missing_response_count"]
    ):
        raise ValueError("V2.48.04 lookup statistic conservation drifted")
    return copied


def _four_layer_risk(
    *, valid_first_records: int, valid_first_countries: int,
    expected_second_records: float, expected_second_new_countries: float,
) -> tuple[dict[str, float], dict[str, float]]:
    total = float(TARGETED_LOOKUP_CAP)
    rows = float(COUNTRY_COUNT)
    unresolved_before = total - float(valid_first_records)
    unresolved_after = max(0.0, unresolved_before - expected_second_records)
    missing_rows_before = rows - float(valid_first_countries)
    missing_rows_after = max(
        0.0, missing_rows_before - expected_second_new_countries
    )
    before = {
        "anchor_identity": 0.0,
        "open_set_coverage": unresolved_before / total,
        "row_eligibility": missing_rows_before / rows,
        "cell_value_unknown": unresolved_before / total,
    }
    after = {
        "anchor_identity": 0.0,
        "open_set_coverage": unresolved_after / total,
        "row_eligibility": missing_rows_after / rows,
        "cell_value_unknown": unresolved_after / total,
    }
    return (
        {key: round(value, 12) for key, value in before.items()},
        {key: round(value, 12) for key, value in after.items()},
    )


def _terminal_loss(risk: Mapping[str, float]) -> float:
    """Conjunctive exact-table loss proxy with cross-layer interaction."""

    survival = 1.0
    for name in (
        "anchor_identity", "open_set_coverage", "row_eligibility",
        "cell_value_unknown",
    ):
        value = float(risk[name])
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError("V2.48.04 four-layer risk is invalid")
        survival *= 1.0 - value
    return round(1.0 - survival, 12)


def decide_adaptive(
    *, first_records: Sequence[Mapping[str, str]],
    first_stats: Mapping[str, int], policy: AdaptivePolicy,
) -> dict[str, Any]:
    """Decide before wave-two responses are available or inspected."""

    policy.validate()
    valid = int(first_stats.get("valid_exact_record_count", -1))
    returned = int(first_stats.get("returned_result_count", -1))
    if (
        valid != len(first_records) or not 0 <= valid <= FIRST_WAVE_LOOKUP_CAP
        or returned < valid or returned > FIRST_WAVE_LOOKUP_CAP
    ):
        raise ValueError("V2.48.04 first-wave lookup statistics drifted")
    countries = _record_country_set(first_records)
    if len(countries) > valid:
        raise ValueError("V2.48.04 first-wave country coverage drifted")
    alpha = float(policy.beta_prior_alpha) + valid
    beta = float(policy.beta_prior_beta) + FIRST_WAVE_LOOKUP_CAP - valid
    yield_mean = alpha / (alpha + beta)
    expected_records = SECOND_WAVE_LOOKUP_CAP * yield_mean
    expected_new_countries = (
        COUNTRY_COUNT - len(countries)
    ) * yield_mean
    before, after = _four_layer_risk(
        valid_first_records=valid,
        valid_first_countries=len(countries),
        expected_second_records=expected_records,
        expected_second_new_countries=expected_new_countries,
    )
    loss_before = _terminal_loss(before)
    loss_after = _terminal_loss(after)
    reduction = round(max(0.0, loss_before - loss_after), 12)
    information_gain = round(
        beta_expected_information_gain(alpha, beta, SECOND_WAVE_LOOKUP_CAP), 12
    )
    cost = round(policy.per_lookup_cost * SECOND_WAVE_LOOKUP_CAP, 12)
    entropy_value = round(
        policy.information_gain_feature_weight * information_gain, 12
    )
    net = round(reduction + entropy_value - cost, 12)
    if not policy.calibration_complete:
        decision, reason = "stop", "calibration_incomplete_fail_closed"
    elif net > policy.minimum_net_value:
        decision, reason = "expand", "positive_expected_terminal_utility"
    else:
        decision, reason = "stop", "nonpositive_expected_terminal_utility"
    value = {
        "artifact_version": 1,
        "role": DECISION_ROLE,
        "policy_id": POLICY_ID,
        "policy": _policy_dict(policy),
        "first_wave_observation": {
            "attempted_lookup_count": FIRST_WAVE_LOOKUP_CAP,
            "returned_result_count": returned,
            "valid_exact_record_count": valid,
            "valid_country_count": len(countries),
        },
        "valid_lookup_yield_posterior": {
            "family": "Beta-Bernoulli",
            "alpha": round(alpha, 12),
            "beta": round(beta, 12),
            "posterior_mean": round(yield_mean, 12),
        },
        "four_layer_risk_before": before,
        "four_layer_expected_risk_after": after,
        "terminal_loss_before": loss_before,
        "expected_terminal_loss_after": loss_after,
        "expected_terminal_loss_reduction": reduction,
        "expected_information_gain_nats": information_gain,
        "information_gain_feature_value": entropy_value,
        "expected_lookup_cost": cost,
        "net_value": net,
        "decision": decision,
        "reason": reason,
        "wave_two_response_or_value_read": False,
        "entropy_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["decision_sha256"] = payload_sha256(value)
    return validate_decision(value)


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("decision_sha256", None)
    policy_raw = copied.get("policy")
    observation = copied.get("first_wave_observation")
    posterior = copied.get("valid_lookup_yield_posterior")
    expected = {
        "artifact_version", "role", "policy_id", "policy",
        "first_wave_observation", "valid_lookup_yield_posterior",
        "four_layer_risk_before", "four_layer_expected_risk_after",
        "terminal_loss_before", "expected_terminal_loss_after",
        "expected_terminal_loss_reduction", "expected_information_gain_nats",
        "information_gain_feature_value", "expected_lookup_cost", "net_value",
        "decision", "reason", "wave_two_response_or_value_read",
        "entropy_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "decision_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != DECISION_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(policy_raw, Mapping)
        or set(policy_raw) != {field.name for field in dataclasses.fields(AdaptivePolicy)}
        or not isinstance(observation, Mapping)
        or set(observation) != {
            "attempted_lookup_count", "returned_result_count",
            "valid_exact_record_count", "valid_country_count",
        }
        or observation.get("attempted_lookup_count") != FIRST_WAVE_LOOKUP_CAP
        or not isinstance(posterior, Mapping)
        or posterior.get("family") != "Beta-Bernoulli"
        or copied.get("decision") not in DECISIONS
        or copied.get("wave_two_response_or_value_read") is not False
        or copied.get("entropy_assigns_signed_credit") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ) is not False
        or copied.get(
            "file_environment_network_model_search_fetch_or_process_accessed"
        ) is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.04 adaptive decision drifted")
    AdaptivePolicy(**dict(policy_raw)).validate()
    for name in (
        "terminal_loss_before", "expected_terminal_loss_after",
        "expected_terminal_loss_reduction", "expected_information_gain_nats",
        "information_gain_feature_value", "expected_lookup_cost", "net_value",
    ):
        number = copied.get(name)
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise ValueError("V2.48.04 adaptive decision number drifted")
        if not math.isfinite(float(number)):
            raise ValueError("V2.48.04 adaptive decision is non-finite")
    if copied["information_gain_feature_value"] != 0:
        raise ValueError("V2.48.04 entropy changed the uncalibrated decision")
    return copied


def _prefix(
    *, visible_contract: Mapping[str, Any], plan: Mapping[str, Any],
    queries: Sequence[str], generic_pages: Sequence[Mapping[str, str]],
    base_prediction: str, first_requests: Sequence[Mapping[str, str]],
    first_records: Sequence[Mapping[str, str]], first_stats: Mapping[str, int],
) -> dict[str, Any]:
    value = {
        "visible_contract": copy.deepcopy(dict(visible_contract)),
        "plan": copy.deepcopy(dict(plan)),
        "queries": list(queries),
        "generic_pages": copy.deepcopy(list(generic_pages)),
        "base_prediction": str(base_prediction),
        "first_wave_requests": copy.deepcopy(list(first_requests)),
        "first_wave_records": copy.deepcopy(list(first_records)),
        "first_wave_lookup_stats": dict(first_stats),
        "visible_contract_sha256": payload_sha256(visible_contract),
        "plan_sha256": payload_sha256(plan),
        "query_vector_sha256": payload_sha256(list(queries)),
        "generic_page_vector_sha256": payload_sha256(list(generic_pages)),
        "base_prediction_sha256": hashlib.sha256(base_prediction.encode()).hexdigest(),
        "first_wave_request_vector_sha256": payload_sha256(list(first_requests)),
        "first_wave_record_vector_sha256": payload_sha256(list(first_records)),
        "shared_prefix_executed_once": True,
        "branch_visible_before_prefix_freeze": False,
    }
    value["prefix_sha256"] = payload_sha256(value)
    return value


def _validate_prefix(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("prefix_sha256", None)
    contract = validate_visible_contract(copied.get("visible_contract", {}))
    plan = copied.get("plan")
    queries = copied.get("queries")
    pages = copied.get("generic_pages")
    first_requests = copied.get("first_wave_requests")
    first_records = copied.get("first_wave_records")
    expected = {
        "visible_contract", "plan", "queries", "generic_pages",
        "base_prediction", "first_wave_requests", "first_wave_records",
        "first_wave_lookup_stats", "visible_contract_sha256", "plan_sha256",
        "query_vector_sha256", "generic_page_vector_sha256",
        "base_prediction_sha256", "first_wave_request_vector_sha256",
        "first_wave_record_vector_sha256", "shared_prefix_executed_once",
        "branch_visible_before_prefix_freeze", "prefix_sha256",
    }
    if (
        set(copied) != expected
        or not isinstance(plan, Mapping) or not isinstance(queries, list)
        or len(queries) != COUNTRY_COUNT or not all(isinstance(q, str) for q in queries)
        or not isinstance(pages, list) or not isinstance(first_requests, list)
        or len(first_requests) != FIRST_WAVE_LOOKUP_CAP
        or not isinstance(first_records, list)
        or not isinstance(copied.get("base_prediction"), str)
        or copied.get("visible_contract_sha256") != payload_sha256(contract)
        or copied.get("plan_sha256") != payload_sha256(plan)
        or copied.get("query_vector_sha256") != payload_sha256(queries)
        or copied.get("generic_page_vector_sha256") != payload_sha256(pages)
        or copied.get("base_prediction_sha256")
        != hashlib.sha256(copied["base_prediction"].encode()).hexdigest()
        or copied.get("first_wave_request_vector_sha256")
        != payload_sha256(first_requests)
        or copied.get("first_wave_record_vector_sha256")
        != payload_sha256(first_records)
        or copied.get("shared_prefix_executed_once") is not True
        or copied.get("branch_visible_before_prefix_freeze") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.04 shared prefix drifted")
    expected_first, _second = _request_partition(contract)
    if first_requests != expected_first:
        raise ValueError("V2.48.04 first-wave request binding drifted")
    validated_records = validate_official_records(first_records, contract)
    _validate_lookup_stats(copied.get("first_wave_lookup_stats", {}), validated_records)
    return copied


def _receipt(
    *, budget: _Budget, model_cost: Mapping[str, int],
    search_cost: Mapping[str, int], generic_page_count: int,
    decision: Mapping[str, Any], first_stats: Mapping[str, int],
    full_stats: Mapping[str, int], prefix_sha256: str,
) -> dict[str, Any]:
    adaptive_fetches = (
        GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP
        + (SECOND_WAVE_LOOKUP_CAP if decision["decision"] == "expand" else 0)
    )
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "three_arm_design": list(ARMS),
        "shared_prefix_sha256": prefix_sha256,
        "shared_plan_search_fetch_synthesis_and_first_lookup_exact": True,
        "prefix_effect_executions": 1,
        "repeated_upstream_effects": 0,
        "branch_failure_projects_all_arms_to_same_failure": True,
        "model_stage_vector": list(budget.model_stages),
        "physical_model_calls": len(budget.model_stages),
        "physical_search_queries": int(budget.search_queries),
        "physical_fetch_targets": int(budget.fetch_targets),
        "generic_fetch_targets": GENERIC_FETCH_CAP,
        "generic_usable_pages": int(generic_page_count),
        "first_wave_lookup_targets": FIRST_WAVE_LOOKUP_CAP,
        "second_wave_lookup_targets": SECOND_WAVE_LOOKUP_CAP,
        "first_wave_lookup": dict(first_stats),
        "full_lookup": dict(full_stats),
        "arm_logical_fetch_targets": {
            "first_wave_only": GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP,
            "fixed_full_budget": GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP,
            "coverage_risk_adaptive": adaptive_fetches,
        },
        "adaptive_decision_sha256": str(decision["decision_sha256"]),
        "adaptive_wave_two_response_read_if_stopped": False,
        "fixed_arm_suffix_physical_effect_not_charged_to_stopping_adaptive_arm": True,
        "model_cost": {key: int(value) for key, value in model_cost.items()},
        "search_cost": {key: int(value) for key, value in search_cost.items()},
        "entropy_shadow_only_not_signed_credit": True,
        "positive_task_credit_assigned": False,
        "question_query_url_page_prediction_answer_value_country_indicator_or_opaque_id_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    logical = copied.get("arm_logical_fetch_targets")
    expected = {
        "artifact_version", "role", "policy_id", "three_arm_design",
        "shared_prefix_sha256",
        "shared_plan_search_fetch_synthesis_and_first_lookup_exact",
        "prefix_effect_executions", "repeated_upstream_effects",
        "branch_failure_projects_all_arms_to_same_failure",
        "model_stage_vector", "physical_model_calls", "physical_search_queries",
        "physical_fetch_targets", "generic_fetch_targets", "generic_usable_pages",
        "first_wave_lookup_targets", "second_wave_lookup_targets",
        "first_wave_lookup", "full_lookup", "arm_logical_fetch_targets",
        "adaptive_decision_sha256",
        "adaptive_wave_two_response_read_if_stopped",
        "fixed_arm_suffix_physical_effect_not_charged_to_stopping_adaptive_arm",
        "model_cost", "search_cost", "entropy_shadow_only_not_signed_credit",
        "positive_task_credit_assigned",
        "question_query_url_page_prediction_answer_value_country_indicator_or_opaque_id_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized", "receipt_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("three_arm_design") != list(ARMS)
        or SHA256.fullmatch(str(copied.get("shared_prefix_sha256", ""))) is None
        or copied.get("shared_plan_search_fetch_synthesis_and_first_lookup_exact")
        is not True
        or copied.get("prefix_effect_executions") != 1
        or copied.get("repeated_upstream_effects") != 0
        or copied.get("branch_failure_projects_all_arms_to_same_failure") is not True
        or copied.get("model_stage_vector") != ["shared_plan", "shared_synthesis"]
        or copied.get("physical_model_calls") != 2
        or copied.get("physical_search_queries") != COUNTRY_COUNT
        or copied.get("physical_fetch_targets")
        != GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP
        or not isinstance(logical, Mapping) or set(logical) != set(ARMS)
        or logical.get("first_wave_only")
        != GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP
        or logical.get("fixed_full_budget")
        != GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP
        or logical.get("coverage_risk_adaptive") not in {
            GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP,
            GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP,
        }
        or copied.get("adaptive_wave_two_response_read_if_stopped") is not False
        or copied.get(
            "fixed_arm_suffix_physical_effect_not_charged_to_stopping_adaptive_arm"
        ) is not True
        or copied.get("entropy_shadow_only_not_signed_credit") is not True
        or copied.get("positive_task_credit_assigned") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ) is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.04 content-free receipt drifted")
    if (
        copied["generic_fetch_targets"] != GENERIC_FETCH_CAP
        or copied["first_wave_lookup_targets"] != FIRST_WAVE_LOOKUP_CAP
        or copied["second_wave_lookup_targets"] != SECOND_WAVE_LOOKUP_CAP
    ):
        raise ValueError("V2.48.04 receipt budget partition drifted")
    return copied


def run_v24804_task(
    task: Mapping[str, Any], *, model: Any, search: Any,
    limits: ScoreFirstLimits, adaptive_policy: AdaptivePolicy,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    visible_contract = _visible_contract(visible["question"])
    limits.validate()
    adaptive_policy.validate()
    if (
        limits.model_calls != 2 or limits.search_queries != COUNTRY_COUNT
        or limits.fetch_targets != GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP
    ):
        raise ValueError("V2.48.04 fixed effect envelope drifted")
    started = float(monotonic())
    budget = _Budget(limits, started, monotonic)
    model_before = _counter_snapshot(model, MODEL_COUNTERS)
    search_before = _counter_snapshot(search, SEARCH_COUNTERS)

    if not budget.admit_model("shared_plan"):
        raise RuntimeError("V2.48.04 shared plan was not admitted")
    raw_plan = model.complete(
        PLAN_SYSTEM,
        PLAN_USER.format(question=visible["question"], query_limit=COUNTRY_COUNT),
        max_output_tokens=limits.plan_output_tokens,
        json_mode=True,
    )
    plan = _validated_plan(
        parse_json_object(_model_text(raw_plan)), visible["question"], limits
    )
    queries = visible_query_vector(visible["question"], COUNTRY_COUNT)
    if budget.admit_search(len(queries)) != COUNTRY_COUNT:
        raise RuntimeError("V2.48.04 shared search was not fully admitted")
    union = TaskUnionDiscoverySearchClient(search)
    batches = union.search_many(
        queries,
        max_results=limits.search_results_per_query,
        search_depth="advanced",
        include_raw_content=False,
    )
    leads = _page_title_only_lead_requests(batches, GENERIC_FETCH_CAP)
    if len(leads) != GENERIC_FETCH_CAP:
        raise RuntimeError("V2.48.04 shared generic prefix is incomplete")
    if budget.admit_fetch(GENERIC_FETCH_CAP) != GENERIC_FETCH_CAP:
        raise RuntimeError("V2.48.04 generic prefix fetch was not admitted")
    generic_raw = union.fetch_urls(leads[:GENERIC_FETCH_CAP]) if leads else []
    generic_pages = _final_url_page_vector(
        generic_raw, prefix="E", page_chars=limits.page_chars
    )
    evidence = _format_evidence(generic_pages, character_cap=limits.evidence_chars)
    if not budget.admit_model("shared_synthesis"):
        raise RuntimeError("V2.48.04 shared synthesis was not admitted")
    columns = list(visible_contract["columns"])
    raw_synthesis = model.complete(
        SYNTHESIS_SYSTEM,
        SYNTHESIS_USER.format(
            question=visible["question"],
            columns=json.dumps(columns, ensure_ascii=False),
            evidence=evidence,
        ),
        max_output_tokens=limits.synthesis_output_tokens,
        json_mode=False,
    )
    base_prediction = _canonical(
        _model_text(raw_synthesis), columns, visible["question"]
    ) or _unknown_table(visible_contract)
    base_prediction = project_visible_rows(base_prediction, visible_contract)

    first_requests, second_requests = _request_partition(visible_contract)
    if budget.admit_fetch(FIRST_WAVE_LOOKUP_CAP) != FIRST_WAVE_LOOKUP_CAP:
        raise RuntimeError("V2.48.04 first lookup wave was not admitted")
    first_raw = union.fetch_urls(first_requests)
    first_records, first_stats = project_exact_lookup_responses(
        first_raw, visible_contract
    )
    prefix = _prefix(
        visible_contract=visible_contract,
        plan=plan,
        queries=queries,
        generic_pages=generic_pages,
        base_prediction=base_prediction,
        first_requests=first_requests,
        first_records=first_records,
        first_stats=first_stats,
    )
    decision = decide_adaptive(
        first_records=first_records,
        first_stats=first_stats,
        policy=adaptive_policy,
    )
    first_prediction, first_admissions, first_completion = apply_target_values(
        base_prediction, visible_contract, first_records
    )

    if budget.admit_fetch(SECOND_WAVE_LOOKUP_CAP) != SECOND_WAVE_LOOKUP_CAP:
        raise RuntimeError("V2.48.04 fixed full suffix was not admitted")
    second_raw = union.fetch_urls(second_requests)
    full_records, full_stats = project_exact_lookup_responses(
        [*first_raw, *second_raw], visible_contract
    )
    fixed_prediction, full_admissions, full_completion = apply_target_values(
        base_prediction, visible_contract, full_records
    )
    adaptive_prediction = (
        fixed_prediction if decision["decision"] == "expand" else first_prediction
    )
    predictions = {
        "first_wave_only": first_prediction,
        "fixed_full_budget": fixed_prediction,
        "coverage_risk_adaptive": adaptive_prediction,
    }
    model_cost = _counter_delta(
        _counter_snapshot(model, MODEL_COUNTERS), model_before
    )
    search_cost = _counter_delta(
        _counter_snapshot(search, SEARCH_COUNTERS), search_before
    )
    receipt = _receipt(
        budget=budget,
        model_cost=model_cost,
        search_cost=search_cost,
        generic_page_count=len(generic_pages),
        decision=decision,
        first_stats=first_stats,
        full_stats=full_stats,
        prefix_sha256=prefix["prefix_sha256"],
    )
    result = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "adaptive_policy": _policy_dict(adaptive_policy),
        "shared_prefix": prefix,
        "second_wave_requests": second_requests,
        "full_official_records": full_records,
        "first_wave_cell_admissions": first_admissions,
        "full_cell_admissions": full_admissions,
        "first_wave_completion_check": first_completion,
        "full_completion_check": full_completion,
        "adaptive_decision": decision,
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "receipt": receipt,
        "elapsed_seconds": round(max(0.0, float(monotonic()) - started), 6),
        "private_visible_provider_and_prediction_content_present": True,
        "private_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    result["result_sha256"] = payload_sha256(result)
    return validate_result(result)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    policy_raw = copied.get("adaptive_policy")
    expected = {
        "artifact_version", "role", "policy_id", "opaque_id",
        "adaptive_policy", "shared_prefix", "second_wave_requests",
        "full_official_records", "first_wave_cell_admissions",
        "full_cell_admissions", "first_wave_completion_check",
        "full_completion_check", "adaptive_decision", "predictions",
        "prediction_sha256", "receipt", "elapsed_seconds",
        "private_visible_provider_and_prediction_content_present",
        "private_content_emitted_to_public_aggregate",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "result_sha256",
    }
    elapsed = copied.get("elapsed_seconds")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE or copied.get("policy_id") != POLICY_ID
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id", "")))
        is None
        or not isinstance(policy_raw, Mapping)
        or not isinstance(predictions, Mapping) or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping) or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed)) or float(elapsed) < 0
        or copied.get("private_visible_provider_and_prediction_content_present")
        is not True
        or copied.get("private_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ) is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.04 task result drifted")
    policy = AdaptivePolicy(**dict(policy_raw))
    policy.validate()
    prefix = _validate_prefix(copied.get("shared_prefix", {}))
    contract = prefix["visible_contract"]
    second_requests = copied.get("second_wave_requests")
    expected_first, expected_second = _request_partition(contract)
    if prefix["first_wave_requests"] != expected_first or second_requests != expected_second:
        raise ValueError("V2.48.04 lookup request binding drifted")
    first_records = validate_official_records(prefix["first_wave_records"], contract)
    full_records = validate_official_records(
        copied.get("full_official_records"), contract
    )
    first_keys = {record["target_key"] for record in first_records}
    full_keys = {record["target_key"] for record in full_records}
    expected_first_keys = {request["member_label"] for request in expected_first}
    first_by_key = {record["target_key"]: record for record in first_records}
    full_by_key = {record["target_key"]: record for record in full_records}
    if (
        not first_keys <= expected_first_keys
        or not first_keys <= full_keys
        or any(full_by_key[key] != first_by_key[key] for key in first_keys)
    ):
        raise ValueError("V2.48.04 lookup record partition drifted")
    first_prediction, first_admissions, first_completion = apply_target_values(
        prefix["base_prediction"], contract, first_records
    )
    fixed_prediction, full_admissions, full_completion = apply_target_values(
        prefix["base_prediction"], contract, full_records
    )
    decision = validate_decision(copied.get("adaptive_decision", {}))
    expected_decision = decide_adaptive(
        first_records=first_records,
        first_stats=prefix["first_wave_lookup_stats"],
        policy=policy,
    )
    adaptive_prediction = (
        fixed_prediction if decision["decision"] == "expand" else first_prediction
    )
    receipt = validate_receipt(copied.get("receipt", {}))
    _validate_lookup_stats(prefix["first_wave_lookup_stats"], first_records)
    _validate_lookup_stats(receipt["first_wave_lookup"], first_records)
    _validate_lookup_stats(receipt["full_lookup"], full_records)
    if (
        decision != expected_decision
        or predictions != {
            "first_wave_only": first_prediction,
            "fixed_full_budget": fixed_prediction,
            "coverage_risk_adaptive": adaptive_prediction,
        }
        or copied.get("first_wave_cell_admissions") != first_admissions
        or copied.get("full_cell_admissions") != full_admissions
        or copied.get("first_wave_completion_check") != first_completion
        or copied.get("full_completion_check") != full_completion
        or receipt["shared_prefix_sha256"] != prefix["prefix_sha256"]
        or receipt["adaptive_decision_sha256"] != decision["decision_sha256"]
        or receipt["first_wave_lookup"] != prefix["first_wave_lookup_stats"]
        or receipt["arm_logical_fetch_targets"]["coverage_risk_adaptive"]
        != GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP
        + (SECOND_WAVE_LOOKUP_CAP if decision["decision"] == "expand" else 0)
    ):
        raise ValueError("V2.48.04 three-arm derivation drifted")
    if decision["decision"] == "stop" and predictions[
        "coverage_risk_adaptive"
    ] != predictions["first_wave_only"]:
        raise ValueError("V2.48.04 stopping arm read suffix data")
    return copied


__all__ = [
    "ARMS", "AdaptivePolicy", "POLICY_ID", "ROLE", "decide_adaptive",
    "run_v24804_task", "validate_decision", "validate_receipt",
    "validate_result",
]
