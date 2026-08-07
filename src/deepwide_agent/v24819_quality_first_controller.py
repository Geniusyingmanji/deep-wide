"""Quality-first shared-prefix controller for open-world table completion.

V2.48.15 exposed a semantic error in the earlier budget ladder: its first wave
observed only the first required target column, yet the second-column lookups
were treated as optional information gathering.  A raw lookup-cost number could
therefore stop the controller before four structurally required cells had ever
been observed.

This append-only successor gives actions a stricter meaning:

* an action that can observe a still-missing required visible cell is mandatory
  whenever the frozen lookup budget permits it;
* missing, incomplete, or drifted calibration expands safely instead of
  authorizing a quality-losing stop;
* cost-sensitive stopping is reachable only after mandatory coverage is
  satisfied and a concrete calibration artifact is bound by path and matching
  declared/observed digests;
* entropy/information gain remains a zero-weight shadow measurement and never
  receives signed credit.

The runtime accepts only ``{opaque_id, question}``.  It has no filesystem,
environment, process, benchmark, evaluator, gold, score, reward, or network
capability; caller-owned clients perform all model/search/fetch effects.
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

from . import v24804_shared_prefix_budget_ladder as _parent


POLICY_ID = "v24819_quality_first_mandatory_coverage_controller_v1"
ROLE = "v24819_quality_first_controller_task_result"
RECEIPT_ROLE = "v24819_quality_first_controller_receipt"
DECISION_ROLE = "v24819_quality_first_controller_decision"
ARMS = _parent.ARMS
DECISIONS = _parent.DECISIONS
GENERIC_FETCH_CAP = _parent.GENERIC_FETCH_CAP
FIRST_WAVE_LOOKUP_CAP = _parent.FIRST_WAVE_LOOKUP_CAP
SECOND_WAVE_LOOKUP_CAP = _parent.SECOND_WAVE_LOOKUP_CAP
TARGETED_LOOKUP_CAP = _parent.TARGETED_LOOKUP_CAP
COUNTRY_COUNT = _parent.COUNTRY_COUNT
SHA256 = re.compile(r"[0-9a-f]{64}")
CALIBRATION_PATH = re.compile(r"results/[A-Za-z0-9_.-]+\.json")


@dataclasses.dataclass(frozen=True)
class CalibrationBinding:
    """Content-free binding to a real, externally verified calibration file.

    The pure controller does not open files.  A launch audit computes the
    observed digest and binds it into the frozen protocol; digest disagreement
    is represented as an invalid binding and causes safe expansion.
    """

    artifact_path: str = ""
    declared_artifact_sha256: str = ""
    observed_artifact_sha256: str = ""
    artifact_payload_sha256: str = ""
    calibration_task_count: int = 0
    terminal_utility_observed: bool = False
    heldout_validation_passed: bool = False
    external_artifact_verified_before_runtime: bool = False
    quality_cost_exchange_rate: float = 0.0

    def validate_shape(self) -> None:
        string_fields = (
            "artifact_path",
            "declared_artifact_sha256",
            "observed_artifact_sha256",
            "artifact_payload_sha256",
        )
        if any(not isinstance(getattr(self, name), str) for name in string_fields):
            raise ValueError("V2.48.19 calibration binding string drifted")
        if (
            isinstance(self.calibration_task_count, bool)
            or not isinstance(self.calibration_task_count, int)
            or self.calibration_task_count < 0
        ):
            raise ValueError("V2.48.19 calibration task count drifted")
        for name in (
            "terminal_utility_observed",
            "heldout_validation_passed",
            "external_artifact_verified_before_runtime",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError("V2.48.19 calibration readiness drifted")
        rate = self.quality_cost_exchange_rate
        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not math.isfinite(float(rate))
            or float(rate) < 0.0
        ):
            raise ValueError("V2.48.19 quality/cost exchange rate drifted")

    def status(self) -> dict[str, Any]:
        self.validate_shape()
        findings: list[str] = []
        if CALIBRATION_PATH.fullmatch(self.artifact_path) is None:
            findings.append("artifact_path_missing_or_invalid")
        if SHA256.fullmatch(self.declared_artifact_sha256) is None:
            findings.append("declared_artifact_digest_missing_or_invalid")
        if SHA256.fullmatch(self.observed_artifact_sha256) is None:
            findings.append("observed_artifact_digest_missing_or_invalid")
        if (
            SHA256.fullmatch(self.declared_artifact_sha256) is not None
            and SHA256.fullmatch(self.observed_artifact_sha256) is not None
            and self.declared_artifact_sha256 != self.observed_artifact_sha256
        ):
            findings.append("artifact_digest_drifted")
        if SHA256.fullmatch(self.artifact_payload_sha256) is None:
            findings.append("artifact_payload_seal_missing_or_invalid")
        if self.calibration_task_count <= 0:
            findings.append("calibration_population_empty")
        if not self.terminal_utility_observed:
            findings.append("terminal_utility_not_observed")
        if not self.heldout_validation_passed:
            findings.append("heldout_validation_not_passed")
        if not self.external_artifact_verified_before_runtime:
            findings.append("external_artifact_not_verified")
        return {
            "valid": not findings,
            "findings": sorted(findings),
            "real_artifact_binding_required": True,
            "declared_and_observed_digest_match_required": True,
        }


@dataclasses.dataclass(frozen=True)
class QualityFirstPolicy:
    """Frozen policy whose cost scale is inert without valid calibration."""

    calibration_binding: CalibrationBinding = dataclasses.field(
        default_factory=CalibrationBinding
    )
    per_lookup_resource_units: float = 1.0
    minimum_net_value: float = 0.0
    information_gain_feature_weight: float = 0.0

    def validate(self) -> None:
        if not isinstance(self.calibration_binding, CalibrationBinding):
            raise ValueError("V2.48.19 calibration binding type drifted")
        self.calibration_binding.validate_shape()
        for name in (
            "per_lookup_resource_units",
            "minimum_net_value",
            "information_gain_feature_weight",
        ):
            number = getattr(self, name)
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(float(number))
            ):
                raise ValueError(f"V2.48.19 {name} drifted")
        if self.per_lookup_resource_units < 0:
            raise ValueError("V2.48.19 resource cost is negative")
        if self.information_gain_feature_weight != 0:
            raise ValueError("V2.48.19 entropy cannot receive signed credit")


def _policy_dict(policy: QualityFirstPolicy) -> dict[str, Any]:
    policy.validate()
    return dataclasses.asdict(policy)


def _policy_from_mapping(value: Mapping[str, Any]) -> QualityFirstPolicy:
    expected = {
        "calibration_binding",
        "per_lookup_resource_units",
        "minimum_net_value",
        "information_gain_feature_weight",
    }
    binding_raw = value.get("calibration_binding")
    if set(value) != expected or not isinstance(binding_raw, Mapping):
        raise ValueError("V2.48.19 policy schema drifted")
    if set(binding_raw) != {field.name for field in dataclasses.fields(CalibrationBinding)}:
        raise ValueError("V2.48.19 calibration schema drifted")
    policy = QualityFirstPolicy(
        calibration_binding=CalibrationBinding(**dict(binding_raw)),
        per_lookup_resource_units=value["per_lookup_resource_units"],
        minimum_net_value=value["minimum_net_value"],
        information_gain_feature_weight=value["information_gain_feature_weight"],
    )
    policy.validate()
    return policy


def _keys(values: Sequence[str], *, name: str) -> list[str]:
    copied = list(values)
    if (
        not all(isinstance(value, str) and value for value in copied)
        or len(set(copied)) != len(copied)
    ):
        raise ValueError(f"V2.48.19 {name} key vector drifted")
    return copied


def _key_hash(values: Sequence[str]) -> str:
    return _parent.payload_sha256(list(values))


def decide_quality_first_state(
    *,
    required_visible_cell_keys: Sequence[str],
    observed_required_cell_keys: Sequence[str],
    candidate_action_cell_keys: Sequence[str],
    valid_first_records: int,
    returned_first_results: int,
    valid_first_countries: int,
    remaining_lookup_budget: int,
    policy: QualityFirstPolicy,
) -> dict[str, Any]:
    """Choose an action from content-free coverage state, before suffix data.

    This lower-level function is intentionally public for attack tests and for
    future non-World-Bank callers.  It receives only opaque cell keys and
    aggregate first-wave counts; no values, labels, gold, or evaluator state.
    """

    policy.validate()
    required = _keys(required_visible_cell_keys, name="required")
    observed = _keys(observed_required_cell_keys, name="observed")
    action = _keys(candidate_action_cell_keys, name="candidate action")
    required_set = set(required)
    observed_set = set(observed)
    action_set = set(action)
    if not observed_set <= required_set:
        raise ValueError("V2.48.19 observed cell is not visibly required")
    for name, number, maximum in (
        ("valid first records", valid_first_records, FIRST_WAVE_LOOKUP_CAP),
        ("returned first results", returned_first_results, FIRST_WAVE_LOOKUP_CAP),
        ("valid first countries", valid_first_countries, COUNTRY_COUNT),
    ):
        if (
            isinstance(number, bool)
            or not isinstance(number, int)
            or not 0 <= number <= maximum
        ):
            raise ValueError(f"V2.48.19 {name} drifted")
    if returned_first_results < valid_first_records:
        raise ValueError("V2.48.19 first-wave response conservation drifted")
    if (
        isinstance(remaining_lookup_budget, bool)
        or not isinstance(remaining_lookup_budget, int)
        or remaining_lookup_budget < 0
    ):
        raise ValueError("V2.48.19 remaining lookup budget drifted")

    missing = required_set - observed_set
    mandatory_actionable = missing & action_set
    unrecoverable = missing - action_set
    action_budget_permits = remaining_lookup_budget >= len(action)

    alpha = 1.0 + float(valid_first_records)
    beta = 1.0 + float(FIRST_WAVE_LOOKUP_CAP - valid_first_records)
    yield_mean = alpha / (alpha + beta)
    expected_records = len(action) * yield_mean
    expected_new_countries = max(
        0.0, float(COUNTRY_COUNT - valid_first_countries) * yield_mean
    )
    before, after = _parent._four_layer_risk(
        valid_first_records=valid_first_records,
        valid_first_countries=valid_first_countries,
        expected_second_records=expected_records,
        expected_second_new_countries=expected_new_countries,
    )
    loss_before = _parent._terminal_loss(before)
    loss_after = _parent._terminal_loss(after)
    reduction = round(max(0.0, loss_before - loss_after), 12)
    information_gain = round(
        _parent.beta_expected_information_gain(alpha, beta, len(action))
        if action
        else 0.0,
        12,
    )
    raw_cost = round(len(action) * float(policy.per_lookup_resource_units), 12)
    calibration = policy.calibration_binding.status()
    calibrated_penalty: float | None = None
    net_value: float | None = None
    exchange_applied = False
    if calibration["valid"]:
        calibrated_penalty = round(
            raw_cost
            * float(policy.calibration_binding.quality_cost_exchange_rate),
            12,
        )
        net_value = round(reduction - calibrated_penalty, 12)

    mandatory_override = False
    safe_calibration_expand = False
    cost_sensitive_stop = False
    quality_cost_stopping_authorized = (
        not missing
        and bool(action)
        and action_budget_permits
        and bool(calibration["valid"])
    )
    if mandatory_actionable and action_budget_permits:
        decision = "expand"
        reason = "mandatory_visible_cell_coverage"
        mandatory_override = True
    elif mandatory_actionable:
        decision = "stop"
        reason = "mandatory_coverage_budget_blocked"
    elif missing:
        decision = "stop"
        reason = "required_coverage_not_actionable"
    elif not action:
        decision = "stop"
        reason = "no_candidate_suffix_action"
    elif not action_budget_permits:
        decision = "stop"
        reason = "candidate_suffix_budget_blocked"
    elif not calibration["valid"]:
        decision = "expand"
        reason = "calibration_missing_or_drifted_safe_expand"
        safe_calibration_expand = True
    else:
        exchange_applied = True
        if net_value is not None and net_value > policy.minimum_net_value:
            decision = "expand"
            reason = "positive_calibrated_terminal_utility"
        else:
            decision = "stop"
            reason = "nonpositive_calibrated_terminal_utility"
            cost_sensitive_stop = True

    value = {
        "artifact_version": 1,
        "role": DECISION_ROLE,
        "policy_id": POLICY_ID,
        "policy": _policy_dict(policy),
        "calibration_binding_status": calibration,
        "coverage_observation": {
            "required_visible_cell_count": len(required),
            "observed_required_cell_count": len(observed_set),
            "missing_required_cell_count": len(missing),
            "candidate_action_cell_count": len(action),
            "mandatory_actionable_cell_count": len(mandatory_actionable),
            "unrecoverable_missing_cell_count": len(unrecoverable),
            "remaining_lookup_budget": remaining_lookup_budget,
            "candidate_action_budget_permits": action_budget_permits,
            "required_cell_vector_sha256": _key_hash(required),
            "observed_cell_vector_sha256": _key_hash(sorted(observed_set)),
            "candidate_action_vector_sha256": _key_hash(action),
        },
        "first_wave_observation": {
            "attempted_lookup_count": FIRST_WAVE_LOOKUP_CAP,
            "returned_result_count": returned_first_results,
            "valid_exact_record_count": valid_first_records,
            "valid_country_count": valid_first_countries,
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
        "information_gain_feature_value": 0.0,
        "raw_resource_cost_units": raw_cost,
        "calibrated_cost_penalty": calibrated_penalty,
        "net_value": net_value,
        "quality_cost_exchange_rate_applied": exchange_applied,
        "quality_cost_stopping_authorized": quality_cost_stopping_authorized,
        "mandatory_coverage_override_applied": mandatory_override,
        "calibration_safe_expansion_applied": safe_calibration_expand,
        "cost_sensitive_stopping_applied": cost_sensitive_stop,
        "decision": decision,
        "reason": reason,
        "suffix_response_or_value_read": False,
        "entropy_assigns_signed_credit": False,
        "terminal_utility_signed_credit_observed_for_this_action": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["decision_sha256"] = _parent.payload_sha256(value)
    return validate_decision(value)


def decide_quality_first(
    *,
    visible_contract: Mapping[str, Any],
    first_records: Sequence[Mapping[str, str]],
    first_stats: Mapping[str, int],
    remaining_lookup_budget: int,
    policy: QualityFirstPolicy,
) -> dict[str, Any]:
    """Derive the required/action key sets from the visible task contract."""

    contract = _parent.validate_visible_contract(visible_contract)
    records = _parent.validate_official_records(first_records, contract)
    stats = _parent._validate_lookup_stats(first_stats, records)
    first_requests, second_requests = _parent._request_partition(contract)
    first_keys = {request["member_label"] for request in first_requests}
    observed = [record["target_key"] for record in records]
    if not set(observed) <= first_keys:
        raise ValueError("V2.48.19 first wave observed a suffix target")
    return decide_quality_first_state(
        required_visible_cell_keys=[
            request["member_label"]
            for request in [*first_requests, *second_requests]
        ],
        observed_required_cell_keys=observed,
        candidate_action_cell_keys=[
            request["member_label"] for request in second_requests
        ],
        valid_first_records=len(records),
        returned_first_results=stats["returned_result_count"],
        valid_first_countries=len(_parent._record_country_set(records)),
        remaining_lookup_budget=remaining_lookup_budget,
        policy=policy,
    )


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("decision_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "policy",
        "calibration_binding_status",
        "coverage_observation",
        "first_wave_observation",
        "valid_lookup_yield_posterior",
        "four_layer_risk_before",
        "four_layer_expected_risk_after",
        "terminal_loss_before",
        "expected_terminal_loss_after",
        "expected_terminal_loss_reduction",
        "expected_information_gain_nats",
        "information_gain_feature_value",
        "raw_resource_cost_units",
        "calibrated_cost_penalty",
        "net_value",
        "quality_cost_exchange_rate_applied",
        "quality_cost_stopping_authorized",
        "mandatory_coverage_override_applied",
        "calibration_safe_expansion_applied",
        "cost_sensitive_stopping_applied",
        "decision",
        "reason",
        "suffix_response_or_value_read",
        "entropy_assigns_signed_credit",
        "terminal_utility_signed_credit_observed_for_this_action",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "decision_sha256",
    }
    if set(copied) != expected:
        raise ValueError("V2.48.19 decision schema drifted")
    policy_raw = copied.get("policy")
    if not isinstance(policy_raw, Mapping):
        raise ValueError("V2.48.19 decision policy is absent")
    policy = _policy_from_mapping(policy_raw)
    calibration = copied.get("calibration_binding_status")
    coverage = copied.get("coverage_observation")
    first = copied.get("first_wave_observation")
    posterior = copied.get("valid_lookup_yield_posterior")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != DECISION_ROLE
        or copied.get("policy_id") != POLICY_ID
        or calibration != policy.calibration_binding.status()
        or not isinstance(coverage, Mapping)
        or set(coverage)
        != {
            "required_visible_cell_count",
            "observed_required_cell_count",
            "missing_required_cell_count",
            "candidate_action_cell_count",
            "mandatory_actionable_cell_count",
            "unrecoverable_missing_cell_count",
            "remaining_lookup_budget",
            "candidate_action_budget_permits",
            "required_cell_vector_sha256",
            "observed_cell_vector_sha256",
            "candidate_action_vector_sha256",
        }
        or not isinstance(first, Mapping)
        or set(first)
        != {
            "attempted_lookup_count",
            "returned_result_count",
            "valid_exact_record_count",
            "valid_country_count",
        }
        or first.get("attempted_lookup_count") != FIRST_WAVE_LOOKUP_CAP
        or not isinstance(posterior, Mapping)
        or posterior.get("family") != "Beta-Bernoulli"
        or copied.get("decision") not in DECISIONS
        or copied.get("suffix_response_or_value_read") is not False
        or copied.get("entropy_assigns_signed_credit") is not False
        or copied.get("terminal_utility_signed_credit_observed_for_this_action")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "file_environment_network_model_search_fetch_or_process_accessed"
        )
        is not False
        or copied.get("information_gain_feature_value") != 0.0
        or seal != _parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.19 decision drifted")
    integer_fields = (
        "required_visible_cell_count",
        "observed_required_cell_count",
        "missing_required_cell_count",
        "candidate_action_cell_count",
        "mandatory_actionable_cell_count",
        "unrecoverable_missing_cell_count",
        "remaining_lookup_budget",
    )
    if any(
        isinstance(coverage.get(name), bool)
        or not isinstance(coverage.get(name), int)
        or coverage[name] < 0
        for name in integer_fields
    ):
        raise ValueError("V2.48.19 coverage count drifted")
    if (
        coverage["observed_required_cell_count"]
        + coverage["missing_required_cell_count"]
        != coverage["required_visible_cell_count"]
        or coverage["mandatory_actionable_cell_count"]
        > min(
            coverage["missing_required_cell_count"],
            coverage["candidate_action_cell_count"],
        )
        or coverage["unrecoverable_missing_cell_count"]
        + coverage["mandatory_actionable_cell_count"]
        != coverage["missing_required_cell_count"]
        or coverage["candidate_action_budget_permits"]
        != (
            coverage["remaining_lookup_budget"]
            >= coverage["candidate_action_cell_count"]
        )
        or any(
            SHA256.fullmatch(str(coverage.get(name, ""))) is None
            for name in (
                "required_cell_vector_sha256",
                "observed_cell_vector_sha256",
                "candidate_action_vector_sha256",
            )
        )
    ):
        raise ValueError("V2.48.19 coverage conservation drifted")
    numeric = (
        "terminal_loss_before",
        "expected_terminal_loss_after",
        "expected_terminal_loss_reduction",
        "expected_information_gain_nats",
        "information_gain_feature_value",
        "raw_resource_cost_units",
    )
    if any(
        isinstance(copied.get(name), bool)
        or not isinstance(copied.get(name), (int, float))
        or not math.isfinite(float(copied[name]))
        for name in numeric
    ):
        raise ValueError("V2.48.19 decision number drifted")
    for name in ("calibrated_cost_penalty", "net_value"):
        number = copied.get(name)
        if number is not None and (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
        ):
            raise ValueError("V2.48.19 calibrated number drifted")
    mandatory = coverage["mandatory_actionable_cell_count"] > 0
    permits = coverage["candidate_action_budget_permits"]
    if mandatory and permits:
        expected_decision, expected_reason = (
            "expand",
            "mandatory_visible_cell_coverage",
        )
    elif mandatory:
        expected_decision, expected_reason = (
            "stop",
            "mandatory_coverage_budget_blocked",
        )
    elif coverage["missing_required_cell_count"] > 0:
        expected_decision, expected_reason = (
            "stop",
            "required_coverage_not_actionable",
        )
    elif coverage["candidate_action_cell_count"] == 0:
        expected_decision, expected_reason = "stop", "no_candidate_suffix_action"
    elif not permits:
        expected_decision, expected_reason = "stop", "candidate_suffix_budget_blocked"
    elif not calibration["valid"]:
        expected_decision, expected_reason = (
            "expand",
            "calibration_missing_or_drifted_safe_expand",
        )
    elif copied.get("net_value") is not None and copied["net_value"] > policy.minimum_net_value:
        expected_decision, expected_reason = (
            "expand",
            "positive_calibrated_terminal_utility",
        )
    else:
        expected_decision, expected_reason = (
            "stop",
            "nonpositive_calibrated_terminal_utility",
        )
    if (
        (copied["decision"], copied["reason"])
        != (expected_decision, expected_reason)
        or copied["mandatory_coverage_override_applied"]
        is not (mandatory and permits)
        or copied["calibration_safe_expansion_applied"]
        is not (
            coverage["missing_required_cell_count"] == 0
            and coverage["candidate_action_cell_count"] > 0
            and permits
            and not calibration["valid"]
        )
        or copied["cost_sensitive_stopping_applied"]
        is not (
            expected_reason == "nonpositive_calibrated_terminal_utility"
        )
    ):
        raise ValueError("V2.48.19 decision precedence drifted")
    return copied


def _receipt(
    *,
    budget: Any,
    model_cost: Mapping[str, int],
    search_cost: Mapping[str, int],
    generic_page_count: int,
    decision: Mapping[str, Any],
    first_stats: Mapping[str, int],
    full_stats: Mapping[str, int],
    prefix_sha256: str,
) -> dict[str, Any]:
    adaptive_fetches = (
        GENERIC_FETCH_CAP
        + FIRST_WAVE_LOOKUP_CAP
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
        "mandatory_required_coverage_precedes_cost_stopping": True,
        "missing_or_drifted_calibration_safe_expands": True,
        "adaptive_suffix_response_read_if_stopped": False,
        "fixed_arm_suffix_physical_effect_not_charged_to_stopping_adaptive_arm": True,
        "model_cost": {key: int(number) for key, number in model_cost.items()},
        "search_cost": {key: int(number) for key, number in search_cost.items()},
        "entropy_shadow_only_not_signed_credit": True,
        "positive_task_credit_assigned": False,
        "question_query_url_page_prediction_answer_value_country_indicator_or_opaque_id_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = _parent.payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    logical = copied.get("arm_logical_fetch_targets")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "three_arm_design",
        "shared_prefix_sha256",
        "shared_plan_search_fetch_synthesis_and_first_lookup_exact",
        "prefix_effect_executions",
        "repeated_upstream_effects",
        "branch_failure_projects_all_arms_to_same_failure",
        "model_stage_vector",
        "physical_model_calls",
        "physical_search_queries",
        "physical_fetch_targets",
        "generic_fetch_targets",
        "generic_usable_pages",
        "first_wave_lookup_targets",
        "second_wave_lookup_targets",
        "first_wave_lookup",
        "full_lookup",
        "arm_logical_fetch_targets",
        "adaptive_decision_sha256",
        "mandatory_required_coverage_precedes_cost_stopping",
        "missing_or_drifted_calibration_safe_expands",
        "adaptive_suffix_response_read_if_stopped",
        "fixed_arm_suffix_physical_effect_not_charged_to_stopping_adaptive_arm",
        "model_cost",
        "search_cost",
        "entropy_shadow_only_not_signed_credit",
        "positive_task_credit_assigned",
        "question_query_url_page_prediction_answer_value_country_indicator_or_opaque_id_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
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
        or copied.get("generic_fetch_targets") != GENERIC_FETCH_CAP
        or copied.get("first_wave_lookup_targets") != FIRST_WAVE_LOOKUP_CAP
        or copied.get("second_wave_lookup_targets") != SECOND_WAVE_LOOKUP_CAP
        or not isinstance(logical, Mapping)
        or set(logical) != set(ARMS)
        or logical.get("first_wave_only")
        != GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP
        or logical.get("fixed_full_budget")
        != GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP
        or logical.get("coverage_risk_adaptive")
        not in {
            GENERIC_FETCH_CAP + FIRST_WAVE_LOOKUP_CAP,
            GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP,
        }
        or SHA256.fullmatch(str(copied.get("adaptive_decision_sha256", "")))
        is None
        or copied.get("mandatory_required_coverage_precedes_cost_stopping")
        is not True
        or copied.get("missing_or_drifted_calibration_safe_expands") is not True
        or copied.get("adaptive_suffix_response_read_if_stopped") is not False
        or copied.get(
            "fixed_arm_suffix_physical_effect_not_charged_to_stopping_adaptive_arm"
        )
        is not True
        or copied.get("entropy_shadow_only_not_signed_credit") is not True
        or copied.get("positive_task_credit_assigned") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != _parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.19 receipt drifted")
    return copied


def run_v24819_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: Any,
    quality_first_policy: QualityFirstPolicy,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Execute one shared-prefix three-arm task with quality-first routing."""

    visible = _parent.validate_visible_task(task)
    visible_contract = _parent._visible_contract(visible["question"])
    limits.validate()
    quality_first_policy.validate()
    if (
        limits.model_calls != 2
        or limits.search_queries != COUNTRY_COUNT
        or limits.fetch_targets != GENERIC_FETCH_CAP + TARGETED_LOOKUP_CAP
    ):
        raise ValueError("V2.48.19 fixed effect envelope drifted")
    started = float(monotonic())
    budget = _parent._Budget(limits, started, monotonic)
    model_before = _parent._counter_snapshot(model, _parent.MODEL_COUNTERS)
    search_before = _parent._counter_snapshot(search, _parent.SEARCH_COUNTERS)

    if not budget.admit_model("shared_plan"):
        raise RuntimeError("V2.48.19 shared plan was not admitted")
    raw_plan = model.complete(
        _parent.PLAN_SYSTEM,
        _parent.PLAN_USER.format(
            question=visible["question"], query_limit=COUNTRY_COUNT
        ),
        max_output_tokens=limits.plan_output_tokens,
        json_mode=True,
    )
    plan = _parent._validated_plan(
        _parent.parse_json_object(_parent._model_text(raw_plan)),
        visible["question"],
        limits,
    )
    queries = _parent.visible_query_vector(visible["question"], COUNTRY_COUNT)
    if budget.admit_search(len(queries)) != COUNTRY_COUNT:
        raise RuntimeError("V2.48.19 shared search was not fully admitted")
    union = _parent.TaskUnionDiscoverySearchClient(search)
    batches = union.search_many(
        queries,
        max_results=limits.search_results_per_query,
        search_depth="advanced",
        include_raw_content=False,
    )
    leads = _parent._page_title_only_lead_requests(batches, GENERIC_FETCH_CAP)
    if len(leads) != GENERIC_FETCH_CAP:
        raise RuntimeError("V2.48.19 shared generic prefix is incomplete")
    if budget.admit_fetch(GENERIC_FETCH_CAP) != GENERIC_FETCH_CAP:
        raise RuntimeError("V2.48.19 generic prefix fetch was not admitted")
    generic_raw = union.fetch_urls(leads[:GENERIC_FETCH_CAP])
    generic_pages = _parent._final_url_page_vector(
        generic_raw, prefix="E", page_chars=limits.page_chars
    )
    evidence = _parent._format_evidence(
        generic_pages, character_cap=limits.evidence_chars
    )
    if not budget.admit_model("shared_synthesis"):
        raise RuntimeError("V2.48.19 shared synthesis was not admitted")
    columns = list(visible_contract["columns"])
    raw_synthesis = model.complete(
        _parent.SYNTHESIS_SYSTEM,
        _parent.SYNTHESIS_USER.format(
            question=visible["question"],
            columns=json.dumps(columns, ensure_ascii=False),
            evidence=evidence,
        ),
        max_output_tokens=limits.synthesis_output_tokens,
        json_mode=False,
    )
    base_prediction = _parent._canonical(
        _parent._model_text(raw_synthesis), columns, visible["question"]
    ) or _parent._unknown_table(visible_contract)
    base_prediction = _parent.project_visible_rows(base_prediction, visible_contract)

    first_requests, second_requests = _parent._request_partition(visible_contract)
    if budget.admit_fetch(FIRST_WAVE_LOOKUP_CAP) != FIRST_WAVE_LOOKUP_CAP:
        raise RuntimeError("V2.48.19 first lookup wave was not admitted")
    first_raw = union.fetch_urls(first_requests)
    first_records, first_stats = _parent.project_exact_lookup_responses(
        first_raw, visible_contract
    )
    prefix = _parent._prefix(
        visible_contract=visible_contract,
        plan=plan,
        queries=queries,
        generic_pages=generic_pages,
        base_prediction=base_prediction,
        first_requests=first_requests,
        first_records=first_records,
        first_stats=first_stats,
    )
    remaining_lookup_budget = limits.fetch_targets - budget.fetch_targets
    decision = decide_quality_first(
        visible_contract=visible_contract,
        first_records=first_records,
        first_stats=first_stats,
        remaining_lookup_budget=remaining_lookup_budget,
        policy=quality_first_policy,
    )
    first_prediction, first_admissions, first_completion = (
        _parent.apply_target_values(
            base_prediction, visible_contract, first_records
        )
    )

    if budget.admit_fetch(SECOND_WAVE_LOOKUP_CAP) != SECOND_WAVE_LOOKUP_CAP:
        raise RuntimeError("V2.48.19 fixed full suffix was not admitted")
    second_raw = union.fetch_urls(second_requests)
    full_records, full_stats = _parent.project_exact_lookup_responses(
        [*first_raw, *second_raw], visible_contract
    )
    fixed_prediction, full_admissions, full_completion = (
        _parent.apply_target_values(base_prediction, visible_contract, full_records)
    )
    adaptive_prediction = (
        fixed_prediction if decision["decision"] == "expand" else first_prediction
    )
    predictions = {
        "first_wave_only": first_prediction,
        "fixed_full_budget": fixed_prediction,
        "coverage_risk_adaptive": adaptive_prediction,
    }
    model_cost = _parent._counter_delta(
        _parent._counter_snapshot(model, _parent.MODEL_COUNTERS), model_before
    )
    search_cost = _parent._counter_delta(
        _parent._counter_snapshot(search, _parent.SEARCH_COUNTERS), search_before
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
        "quality_first_policy": _policy_dict(quality_first_policy),
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
        "elapsed_seconds": round(
            max(0.0, float(monotonic()) - started), 6
        ),
        "private_visible_provider_and_prediction_content_present": True,
        "private_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    result["result_sha256"] = _parent.payload_sha256(result)
    return validate_result(result)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "quality_first_policy",
        "shared_prefix",
        "second_wave_requests",
        "full_official_records",
        "first_wave_cell_admissions",
        "full_cell_admissions",
        "first_wave_completion_check",
        "full_completion_check",
        "adaptive_decision",
        "predictions",
        "prediction_sha256",
        "receipt",
        "elapsed_seconds",
        "private_visible_provider_and_prediction_content_present",
        "private_content_emitted_to_public_aggregate",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "result_sha256",
    }
    policy_raw = copied.get("quality_first_policy")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    elapsed = copied.get("elapsed_seconds")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id", "")))
        is None
        or not isinstance(policy_raw, Mapping)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or copied.get("private_visible_provider_and_prediction_content_present")
        is not True
        or copied.get("private_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or seal != _parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.19 task result drifted")
    policy = _policy_from_mapping(policy_raw)
    prefix = _parent._validate_prefix(copied.get("shared_prefix", {}))
    contract = prefix["visible_contract"]
    expected_first, expected_second = _parent._request_partition(contract)
    if (
        prefix["first_wave_requests"] != expected_first
        or copied.get("second_wave_requests") != expected_second
    ):
        raise ValueError("V2.48.19 lookup request binding drifted")
    first_records = _parent.validate_official_records(
        prefix["first_wave_records"], contract
    )
    full_records = _parent.validate_official_records(
        copied.get("full_official_records"), contract
    )
    first_keys = {record["target_key"] for record in first_records}
    full_keys = {record["target_key"] for record in full_records}
    expected_first_keys = {
        request["member_label"] for request in expected_first
    }
    first_by_key = {record["target_key"]: record for record in first_records}
    full_by_key = {record["target_key"]: record for record in full_records}
    if (
        not first_keys <= expected_first_keys
        or not first_keys <= full_keys
        or any(full_by_key[key] != first_by_key[key] for key in first_keys)
    ):
        raise ValueError("V2.48.19 lookup record partition drifted")
    first_prediction, first_admissions, first_completion = (
        _parent.apply_target_values(
            prefix["base_prediction"], contract, first_records
        )
    )
    fixed_prediction, full_admissions, full_completion = (
        _parent.apply_target_values(
            prefix["base_prediction"], contract, full_records
        )
    )
    decision = validate_decision(copied.get("adaptive_decision", {}))
    expected_decision = decide_quality_first(
        visible_contract=contract,
        first_records=first_records,
        first_stats=prefix["first_wave_lookup_stats"],
        remaining_lookup_budget=SECOND_WAVE_LOOKUP_CAP,
        policy=policy,
    )
    adaptive_prediction = (
        fixed_prediction if decision["decision"] == "expand" else first_prediction
    )
    receipt = validate_receipt(copied.get("receipt", {}))
    _parent._validate_lookup_stats(
        prefix["first_wave_lookup_stats"], first_records
    )
    _parent._validate_lookup_stats(receipt["first_wave_lookup"], first_records)
    _parent._validate_lookup_stats(receipt["full_lookup"], full_records)
    if (
        decision != expected_decision
        or predictions
        != {
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
        != GENERIC_FETCH_CAP
        + FIRST_WAVE_LOOKUP_CAP
        + (SECOND_WAVE_LOOKUP_CAP if decision["decision"] == "expand" else 0)
    ):
        raise ValueError("V2.48.19 three-arm derivation drifted")
    if (
        decision["decision"] == "stop"
        and predictions["coverage_risk_adaptive"]
        != predictions["first_wave_only"]
    ):
        raise ValueError("V2.48.19 stopping arm read suffix data")
    return copied


__all__ = [
    "ARMS",
    "CalibrationBinding",
    "DECISION_ROLE",
    "POLICY_ID",
    "QualityFirstPolicy",
    "ROLE",
    "decide_quality_first",
    "decide_quality_first_state",
    "run_v24819_task",
    "validate_decision",
    "validate_receipt",
    "validate_result",
]
