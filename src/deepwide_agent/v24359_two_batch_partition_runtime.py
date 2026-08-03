"""Two-batch discovery successor to the frozen explicit-partition runtime.

The V2.43.55 parent remains byte-for-byte unchanged.  This wrapper inserts
V2.43.58 below it so four visible logical queries execute as two hosted-search
batches, registrable hosts are unioned before the existing deterministic 9+1
partition, and at most ten pages are fetched.  The hidden verifier boundary,
parent support IDs, entropy utility rule, and candidate retain/revert policy
are inherited unchanged from the validated parent.
"""

from __future__ import annotations

import copy
import re
import time
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24355_explicit_partition_runtime import (
    MAXIMUM_FETCH_SOURCES,
    run_v24355_task,
    validate_result as validate_parent_result,
)
from .v24358_two_batch_discovery import (
    DISCOVERY_BATCH_COUNT,
    LOGICAL_QUERY_COUNT,
    TwoBatchRegistrableHostUnionSearchClient,
    build_discovery_receipt,
    validate_discovery_receipt,
)


POLICY_ID = "v24359_two_batch_explicit_partition_runtime_v1"
ROLE = "v24359_two_batch_explicit_partition_task_result"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "explicit_partition_result",
        "two_batch_discovery_receipt",
        "two_batch_discovery_private_state",
        "runtime_boundary",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "result_sha256",
    }
)


def run_v24359_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    if re.fullmatch(r"[0-9a-f]{64}", partition_seed_sha256) is None:
        raise ValueError("V2.43.59 partition seed drifted")
    chosen = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=LOGICAL_QUERY_COUNT,
        fetch_targets=MAXIMUM_FETCH_SOURCES,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    chosen.validate()
    if (
        chosen.search_queries != LOGICAL_QUERY_COUNT
        or chosen.fetch_targets != MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.59 discovery/fetch budget drifted")
    discovery = TwoBatchRegistrableHostUnionSearchClient(search)
    parent = run_v24355_task(
        visible,
        model=model,
        search=discovery,
        partition_seed_sha256=partition_seed_sha256,
        limits=chosen,
        monotonic=monotonic,
    )
    validate_parent_result(parent)
    state = discovery.private_replay_state()
    partition = parent["hidden_verifier_receipt"]["partition_receipt"]
    receipt = build_discovery_receipt(state, partition)
    if (
        receipt["logical_query_count"] != LOGICAL_QUERY_COUNT
        or receipt["discovery_batch_count"] != DISCOVERY_BATCH_COUNT
        or receipt["selected_host_count"] > MAXIMUM_FETCH_SOURCES
        or parent["hidden_verifier_receipt"]["total_fetch_calls"]
        > MAXIMUM_FETCH_SOURCES
    ):
        raise ValueError("V2.43.59 two-batch/fetch conservation drifted")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "explicit_partition_result": copy.deepcopy(parent),
        "two_batch_discovery_receipt": copy.deepcopy(receipt),
        "two_batch_discovery_private_state": copy.deepcopy(state),
        "runtime_boundary": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    parent = value.get("explicit_partition_result")
    receipt = value.get("two_batch_discovery_receipt")
    state = value.get("two_batch_discovery_private_state")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(parent, Mapping)
        or not isinstance(receipt, Mapping)
        or not isinstance(state, Mapping)
        or value.get("runtime_boundary") != ["opaque_id", "question"]
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.59 result identity drifted")
    validate_parent_result(parent)
    partition = parent["hidden_verifier_receipt"]["partition_receipt"]
    validate_discovery_receipt(
        receipt,
        private_state=state,
        partition_receipt=partition,
    )
    core = parent["parent_result"]["semantic_result"]["core_result"]
    parent_runtime = parent["hidden_verifier_receipt"]
    if (
        receipt["provider_search_call_count"]
        != int(core["cost"]["search"]["calls"])
        or receipt["logical_query_count"] != LOGICAL_QUERY_COUNT
        or receipt["discovery_batch_count"] != DISCOVERY_BATCH_COUNT
        or receipt["selected_host_count"]
        != partition["selected_source_count"]
        or receipt["proposal_host_count"]
        != partition["proposal_source_count"]
        or receipt["verifier_host_count"]
        != partition["verifier_source_count"]
        or receipt["partition_receipt_sha256"] != partition["receipt_sha256"]
        or parent_runtime["total_fetch_calls"] > MAXIMUM_FETCH_SOURCES
        or parent_runtime["total_fetch_calls"]
        != parent_runtime["parent_fetch_calls"]
        + parent_runtime["hidden_verifier_fetch_calls"]
    ):
        raise ValueError("V2.43.59 cross-layer accounting drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "run_v24359_task",
    "validate_result",
]
