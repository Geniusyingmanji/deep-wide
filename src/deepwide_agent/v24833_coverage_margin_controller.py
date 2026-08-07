"""Coverage-margin successor for bounded two-wave retrieval.

The V2.48.31 exact-220 diagnosis found that early stopping frequently occurred
after only part of the six-fetch prefix produced usable, novel pages.  This
append-only policy keeps the existing replay-validated V2.42.72 kernel but
raises the evidence sufficiency boundary:

* all six first-wave fetch slots must be attempted;
* all six must return usable and content-novel pages;
* at least two independent hosts and the existing per-column content floor are
  still required;
* an incomplete prefix expands while it remains inside a 60-second safety
  ceiling; and
* entropy remains a zero-weight shadow measurement and receives no credit.

The module is pure.  It has no filesystem, environment, process, network,
benchmark, evaluator, score, reward, label, or credential capability.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .v24272_two_wave_entropy_voc import (
    POLICY_ID as BASE_POLICY_ID,
    FirstWaveObservation,
    TwoWavePolicy,
    decide_two_wave,
    validate_receipt as validate_base_receipt,
)


POLICY_ID = "v24833_label_blind_coverage_margin_controller_v1"
ROLE = "v24833_coverage_margin_decision_receipt"
POLICY_VALUES = {
    "wave1_queries": 2,
    "wave1_fetches": 6,
    "wave2_queries": 2,
    "wave2_fetches": 4,
    "minimum_usable_pages": 6,
    "minimum_novel_pages": 6,
    "minimum_unique_hosts": 2,
    "content_chars_per_column": 1_200,
    "maximum_wave1_seconds": 60.0,
    "latency_loss_per_second": 0.0,
    "information_gain_weight": 0.0,
    "minimum_net_value": -1.0,
    "beta_prior_alpha": 1.0,
    "beta_prior_beta": 1.0,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def coverage_margin_policy() -> TwoWavePolicy:
    policy = TwoWavePolicy(**POLICY_VALUES)
    policy.validate()
    return policy


def _observation_dict(value: FirstWaveObservation) -> dict[str, Any]:
    if not isinstance(value, FirstWaveObservation):
        raise ValueError("V2.48.33 requires a typed first-wave observation")
    copied = dataclasses.asdict(value)
    value.validate(coverage_margin_policy())
    return copied


def decide_coverage_margin(observation: FirstWaveObservation) -> dict[str, Any]:
    """Return a sealed outer receipt around the frozen base decision."""

    observed = _observation_dict(observation)
    policy = coverage_margin_policy()
    base = decide_two_wave(observation, policy=policy)
    full_fetch_yield = (
        observation.fetches_attempted == policy.wave1_fetches
        and observation.usable_pages == policy.wave1_fetches
        and observation.novel_pages == policy.wave1_fetches
    )
    host_margin = observation.unique_hosts >= policy.minimum_unique_hosts
    content_margin = (
        observation.content_chars
        >= policy.content_chars_per_column * observation.required_column_count
    )
    inside_safety_ceiling = (
        observation.search_seconds + observation.fetch_seconds
        < policy.maximum_wave1_seconds
    )
    early_stop = base["reason"] == "first_wave_sufficient"
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_controller_policy_id": BASE_POLICY_ID,
        "policy": dict(POLICY_VALUES),
        "first_wave_observation": observed,
        "base_decision_receipt": copy.deepcopy(base),
        "coverage_margin": {
            "full_fetch_yield": full_fetch_yield,
            "host_margin_satisfied": host_margin,
            "content_margin_satisfied": content_margin,
            "inside_safety_ceiling": inside_safety_ceiling,
            "early_stop_authorized": early_stop,
        },
        "decision": base["decision"],
        "reason": base["reason"],
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "historical_benchmark_metric_or_stratum_read": False,
        "question_text_or_content_read_by_controller": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "base_controller_policy_id",
        "policy",
        "first_wave_observation",
        "base_decision_receipt",
        "coverage_margin",
        "decision",
        "reason",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_credit",
        "historical_benchmark_metric_or_stratum_read",
        "question_text_or_content_read_by_controller",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "receipt_sha256",
    }
    policy_raw = copied.get("policy")
    observation_raw = copied.get("first_wave_observation")
    base = copied.get("base_decision_receipt")
    margin = copied.get("coverage_margin")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("base_controller_policy_id") != BASE_POLICY_ID
        or policy_raw != POLICY_VALUES
        or not isinstance(observation_raw, Mapping)
        or set(observation_raw)
        != {field.name for field in dataclasses.fields(FirstWaveObservation)}
        or not isinstance(base, Mapping)
        or not isinstance(margin, Mapping)
        or set(margin)
        != {
            "full_fetch_yield",
            "host_margin_satisfied",
            "content_margin_satisfied",
            "inside_safety_ceiling",
            "early_stop_authorized",
        }
        or any(not isinstance(margin.get(name), bool) for name in margin)
        or copied.get("decision") not in {"expand", "stop"}
        or copied.get("decision") != base.get("decision")
        or copied.get("reason") != base.get("reason")
        or copied.get("entropy_information_gain_shadow_only") is not True
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get("historical_benchmark_metric_or_stratum_read") is not False
        or copied.get("question_text_or_content_read_by_controller") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.33 coverage-margin receipt drifted")
    observation = FirstWaveObservation(**dict(observation_raw))
    observation.validate(coverage_margin_policy())
    validate_base_receipt(base)
    expected_base = decide_two_wave(observation, policy=coverage_margin_policy())
    if dict(base) != expected_base:
        raise ValueError("V2.48.33 base decision replay drifted")
    policy = coverage_margin_policy()
    expected_margin = {
        "full_fetch_yield": observation.fetches_attempted == policy.wave1_fetches
        and observation.usable_pages == policy.wave1_fetches
        and observation.novel_pages == policy.wave1_fetches,
        "host_margin_satisfied": observation.unique_hosts
        >= policy.minimum_unique_hosts,
        "content_margin_satisfied": observation.content_chars
        >= policy.content_chars_per_column * observation.required_column_count,
        "inside_safety_ceiling": observation.search_seconds
        + observation.fetch_seconds
        < policy.maximum_wave1_seconds,
        "early_stop_authorized": base["reason"] == "first_wave_sufficient",
    }
    if dict(margin) != expected_margin:
        raise ValueError("V2.48.33 coverage margin replay drifted")
    if margin["early_stop_authorized"] and not all(
        margin[name]
        for name in (
            "full_fetch_yield",
            "host_margin_satisfied",
            "content_margin_satisfied",
        )
    ):
        raise ValueError("V2.48.33 unsafe early stop")
    if (
        margin["inside_safety_ceiling"]
        and not margin["early_stop_authorized"]
        and copied["decision"] != "expand"
    ):
        raise ValueError("V2.48.33 incomplete in-budget prefix did not expand")
    if base.get("entropy_value") != 0 or base.get("policy", {}).get(
        "information_gain_weight"
    ) != 0:
        raise ValueError("V2.48.33 entropy affected admission")
    return copied


def build_synthetic_gate() -> dict[str, Any]:
    """Exhaust a bounded content-free grid and prove the safety invariants."""

    counts = {
        "observations": 0,
        "early_stops": 0,
        "in_budget_incomplete_expands": 0,
        "latency_stops": 0,
        "unsafe_early_stops": 0,
        "in_budget_incomplete_stops": 0,
        "entropy_nonzero": 0,
    }
    for fetches in range(0, 7):
        for usable in range(fetches + 1):
            for novel in range(usable + 1):
                for hosts in range(usable + 1):
                    for content_chars in (0, 4_800, 12_000):
                        for elapsed in (10.0, 59.999, 60.0, 75.0):
                            observation = FirstWaveObservation(
                                queries_executed=2,
                                sources_discovered=max(fetches, usable),
                                fetches_attempted=fetches,
                                usable_pages=usable,
                                novel_pages=novel,
                                unique_hosts=hosts,
                                content_chars=content_chars,
                                required_column_count=4,
                                explicit_row_target=0,
                                search_seconds=elapsed / 2,
                                fetch_seconds=elapsed / 2,
                                unrecoverable_search_failures=0,
                            )
                            receipt = decide_coverage_margin(observation)
                            margin = receipt["coverage_margin"]
                            counts["observations"] += 1
                            counts["early_stops"] += int(
                                margin["early_stop_authorized"]
                            )
                            incomplete = not all(
                                margin[name]
                                for name in (
                                    "full_fetch_yield",
                                    "host_margin_satisfied",
                                    "content_margin_satisfied",
                                )
                            )
                            in_budget = margin["inside_safety_ceiling"]
                            counts["in_budget_incomplete_expands"] += int(
                                incomplete
                                and in_budget
                                and receipt["decision"] == "expand"
                            )
                            counts["latency_stops"] += int(
                                not in_budget
                                and receipt["reason"] == "latency_ceiling"
                            )
                            counts["unsafe_early_stops"] += int(
                                margin["early_stop_authorized"] and incomplete
                            )
                            counts["in_budget_incomplete_stops"] += int(
                                incomplete
                                and in_budget
                                and receipt["decision"] == "stop"
                            )
                            counts["entropy_nonzero"] += int(
                                receipt["base_decision_receipt"]["entropy_value"]
                                != 0
                            )
    value = {
        "artifact_version": 1,
        "role": "v24833_coverage_margin_synthetic_gate",
        "policy_id": POLICY_ID,
        "policy": dict(POLICY_VALUES),
        "counts": counts,
        "checks": {
            "grid_nonempty": counts["observations"] > 1_000,
            "early_stop_reachable": counts["early_stops"] > 0,
            "in_budget_incomplete_expand_reachable": counts[
                "in_budget_incomplete_expands"
            ]
            > 0,
            "latency_stop_reachable": counts["latency_stops"] > 0,
            "unsafe_early_stop_zero": counts["unsafe_early_stops"] == 0,
            "in_budget_incomplete_stop_zero": counts[
                "in_budget_incomplete_stops"
            ]
            == 0,
            "entropy_value_zero": counts["entropy_nonzero"] == 0,
        },
        "historical_benchmark_metric_or_stratum_read": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
    }
    value["gate_payload_sha256"] = payload_sha256(value)
    return validate_synthetic_gate(value)


def validate_synthetic_gate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("gate_payload_sha256", None)
    if (
        copied.get("role") != "v24833_coverage_margin_synthetic_gate"
        or copied.get("policy_id") != POLICY_ID
        or copied.get("policy") != POLICY_VALUES
        or not isinstance(copied.get("counts"), Mapping)
        or not isinstance(copied.get("checks"), Mapping)
        or not copied["checks"]
        or not all(value is True for value in copied["checks"].values())
        or copied.get("historical_benchmark_metric_or_stratum_read") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.33 synthetic gate drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "POLICY_VALUES",
    "build_synthetic_gate",
    "coverage_margin_policy",
    "decide_coverage_margin",
    "payload_sha256",
    "validate_receipt",
    "validate_synthetic_gate",
]
