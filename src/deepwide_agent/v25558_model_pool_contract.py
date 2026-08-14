"""Clone-safe contract for the frozen global model-slot pool.

Successor runners may rename artifact roles and output roots, but the shared
``DeadlineAwareGlobalModelSlotLimiter`` intentionally accepts only the single
frozen global pool identifier.  This module exposes that identifier without
inventing a version-local replacement and fails closed on any drift.

The module is pure and performs no file, environment, process, network, model,
search, fetch, evaluator, benchmark, or credential effect.  It authorizes no
launch and assigns no entropy/information-gain signed credit.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from . import v24263_global_model_limiter as global_pool
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25558_clone_safe_model_pool_contract_v1"
ROLE = "v25558_model_pool_contract"
MODEL_POOL_ID = global_pool.POOL_ID


def validate_pool_id(value: object) -> str:
    if not isinstance(value, str) or value != MODEL_POOL_ID:
        raise ValueError("V2.55.58 model pool identifier drifted")
    return value


def contract() -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "model_pool_id": validate_pool_id(MODEL_POOL_ID),
        "successor_specific_pool_id_forbidden": True,
        "deadline_limiter_constructor_smoke_required_before_external_effect": True,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["contract_payload_sha256"] = payload_sha256(value)
    return validate_contract(value)


def validate_contract(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("contract_payload_sha256", None)
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or validate_pool_id(copied.get("model_pool_id")) != MODEL_POOL_ID
        or copied.get("successor_specific_pool_id_forbidden") is not True
        or copied.get(
            "deadline_limiter_constructor_smoke_required_before_external_effect"
        )
        is not True
        or copied.get(
            "file_environment_process_network_model_search_fetch_or_evaluator_accessed"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_history_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.58 model pool contract drifted")
    return copied


__all__ = [
    "MODEL_POOL_ID",
    "POLICY_ID",
    "ROLE",
    "contract",
    "validate_contract",
    "validate_pool_id",
]
