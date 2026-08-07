"""Pure fixed-full-budget control policy for the next DeepWide comparison.

The existing V2.42.72 controller remains byte-for-byte frozen.  This module
supplies a policy point that disables entropy and latency utility terms and
admits the second wave whenever physical cleanup time remains.  It is a strong
no-entropy compute control, not a proposed adaptive controller.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .v24272_two_wave_entropy_voc import (
    FirstWaveObservation,
    TwoWavePolicy,
    decide_two_wave,
)


POLICY_ID = "v24799_deadline_bounded_fixed_full_budget_no_entropy_control_v1"
ROLE = "v24799_fixed_full_budget_synthetic_gate_receipt"
POLICY_VALUES = {
    "wave1_queries": 2,
    "wave1_fetches": 6,
    "wave2_queries": 2,
    "wave2_fetches": 4,
    "minimum_usable_pages": 6,
    "minimum_novel_pages": 6,
    "minimum_unique_hosts": 6,
    "content_chars_per_column": 1_000_000_000,
    "maximum_wave1_seconds": 30.0,
    "latency_loss_per_second": 0.0,
    "information_gain_weight": 0.0,
    "minimum_net_value": -1.0,
    "beta_prior_alpha": 1.0,
    "beta_prior_beta": 1.0,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def fixed_full_budget_policy() -> TwoWavePolicy:
    value = TwoWavePolicy(**POLICY_VALUES)
    value.validate()
    if dataclasses.asdict(value) != POLICY_VALUES:
        raise RuntimeError("V2.47.99 fixed policy drifted")
    return value


def _observations() -> list[FirstWaveObservation]:
    values: list[FirstWaveObservation] = []
    for fetches in range(7):
        for usable in range(fetches + 1):
            for novel in range(usable + 1):
                for hosts in range(usable + 1):
                    for columns in (1, 4, 20):
                        for row_target in (0, 1, 25):
                            for elapsed in (0.0, 15.0, 29.0):
                                values.append(
                                    FirstWaveObservation(
                                        queries_executed=2,
                                        sources_discovered=fetches * 3,
                                        fetches_attempted=fetches,
                                        usable_pages=usable,
                                        novel_pages=novel,
                                        unique_hosts=hosts,
                                        content_chars=usable * 5_000,
                                        required_column_count=columns,
                                        explicit_row_target=row_target,
                                        search_seconds=elapsed / 2,
                                        fetch_seconds=elapsed / 2,
                                        unrecoverable_search_failures=0,
                                    )
                                )
    return values


def build_synthetic_gate() -> dict[str, Any]:
    policy = fixed_full_budget_policy()
    observations = _observations()
    decisions = [decide_two_wave(item, policy=policy) for item in observations]
    deadline = FirstWaveObservation(
        queries_executed=2,
        sources_discovered=18,
        fetches_attempted=6,
        usable_pages=6,
        novel_pages=6,
        unique_hosts=6,
        content_chars=30_000,
        required_column_count=4,
        explicit_row_target=0,
        search_seconds=15.0,
        fetch_seconds=15.0,
        unrecoverable_search_failures=0,
    )
    deadline_decision = decide_two_wave(deadline, policy=policy)
    if (
        not observations
        or any(item["decision"] != "expand" for item in decisions)
        or any(item["delta_budget"] != {"queries": 2, "fetches": 4, "delta_only": True} for item in decisions)
        or any(float(item["entropy_value"]) != 0.0 for item in decisions)
        or any(float(item["latency_cost"]) != 0.0 for item in decisions)
        or deadline_decision["decision"] != "stop"
        or deadline_decision["reason"] != "latency_ceiling"
    ):
        raise RuntimeError("V2.47.99 synthetic full-budget gate failed")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "policy": dict(POLICY_VALUES),
        "synthetic_observation_count": len(observations),
        "pre_synthesis_safety_ceiling_expand_count": sum(
            item["decision"] == "expand" for item in decisions
        ),
        "zero_entropy_value_count": sum(
            float(item["entropy_value"]) == 0.0 for item in decisions
        ),
        "zero_latency_utility_count": sum(
            float(item["latency_cost"]) == 0.0 for item in decisions
        ),
        "deadline_boundary_decision": deadline_decision["decision"],
        "deadline_boundary_reason": deadline_decision["reason"],
        "hard_query_cap": policy.wave1_queries + policy.wave2_queries,
        "hard_fetch_cap": policy.wave1_fetches + policy.wave2_fetches,
        "first_wave_safety_ceiling_seconds": 30.0,
        "legacy_reason_name_positive_entropy_voc_is_semantically_ignored": True,
        "entropy_or_information_gain_used_for_admission": False,
        "question_query_url_page_prediction_answer_or_credential_read_or_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_gate(value)


def validate_gate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    count = copied.get("synthetic_observation_count")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("policy") != POLICY_VALUES
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count <= 0
        or copied.get("pre_synthesis_safety_ceiling_expand_count") != count
        or copied.get("zero_entropy_value_count") != count
        or copied.get("zero_latency_utility_count") != count
        or copied.get("deadline_boundary_decision") != "stop"
        or copied.get("deadline_boundary_reason") != "latency_ceiling"
        or copied.get("hard_query_cap") != 4
        or copied.get("hard_fetch_cap") != 10
        or copied.get("first_wave_safety_ceiling_seconds") != 30.0
        or copied.get("entropy_or_information_gain_used_for_admission") is not False
        or copied.get(
            "question_query_url_page_prediction_answer_or_credential_read_or_emitted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("file_environment_network_model_search_fetch_or_process_accessed")
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.99 fixed full-budget gate drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "POLICY_VALUES",
    "build_synthetic_gate",
    "fixed_full_budget_policy",
    "payload_sha256",
    "validate_gate",
]
