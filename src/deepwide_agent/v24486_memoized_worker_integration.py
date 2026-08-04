"""Fail-closed worker integration for the V2.44.85 validation memo.

The frozen V2.44.70 worker remains the owner of task execution, persistence,
certificate creation, terminal receipt, and stage journal.  This append-only
adapter scopes V2.44.85 around exactly one worker call.  After the unchanged
worker returns, it requires one original-validation miss per layer, at least
one safe hit, zero mismatches, and restoration of all 17 bindings before the
worker process may return success.

The memo receipt is returned only to the in-process caller and is never added
to the exact private task artifact surface.  The frozen ``worker_complete``
stage remains the unique successful terminal stage.  This module performs no
benchmark selection or evaluator access and has no category, mapping, gold,
reward, score, or credential input.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24399_failure_observable_runner import MODEL_NAME, RESULT_NAME, TRANSPORT_NAME
from .v24469_bounded_worker_supervisor import StageJournal, bind_worker_to_parent
from .v24470_bounded_adaptive_integration import (
    _validate_layout,
    run_and_persist_stage_hooked_task,
)
from .v24485_execution_scoped_validation_memo import (
    EXPECTED_BINDING_COUNT,
    MAXIMUM_LAYER_COUNT,
    POLICY_ID as MEMO_POLICY_ID,
    ExecutionValidationMemo,
)


POLICY_ID = "v24486_fail_closed_memoized_worker_integration_v1"
MINIMUM_TOTAL_HITS = 8


def validate_memo_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    layers = copied.get("layers")
    if (
        copied.get("policy_id") != MEMO_POLICY_ID
        or copied.get("layer_count") != MAXIMUM_LAYER_COUNT
        or copied.get("binding_count") != EXPECTED_BINDING_COUNT
        or not isinstance(layers, Mapping)
        or len(layers) != MAXIMUM_LAYER_COUNT
        or copied.get("total_misses") != MAXIMUM_LAYER_COUNT
        or copied.get("total_hits", -1) < MINIMUM_TOTAL_HITS
        or copied.get("total_mismatches") != 0
        or copied.get("total_calls")
        != copied.get("total_misses") + copied.get("total_hits")
        or any(
            not isinstance(item, Mapping)
            or item.get("misses") != 1
            or item.get("calls") != item.get("misses") + item.get("hits")
            or item.get("mismatches") != 0
            for item in layers.values()
        )
        or copied.get("first_validation_uses_unchanged_frozen_validator") is not True
        or copied.get(
            "cache_hit_recomputes_outer_seal_and_compares_exact_bytes_and_type_shape"
        )
        is not True
        or copied.get("cache_scope_single_context_single_worker_execution") is not True
        or copied.get("cache_entries_per_layer_at_most_one") is not True
        or copied.get("bindings_restored") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
    ):
        raise ValueError("V2.44.86 memo receipt drifted")
    return copied


def run_memoized_worker(
    task: Mapping[str, Any],
    *,
    ordinal: int,
    expected_supervisor_pid: int,
    checkpoint_directory: Path,
    output_root: Path,
    directory: Path,
    model_factory: Callable[[Callable[[str], None]], Any],
    search_factory: Callable[[Callable[[str], None]], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
    validator_manifest_sha256: str,
) -> dict[str, Any]:
    """Run one frozen worker with execution-scoped validator memoization."""

    output_root, directory, checkpoint_directory = _validate_layout(
        output_root, directory, checkpoint_directory
    )
    bind_worker_to_parent(expected_parent_pid=expected_supervisor_pid)
    journal = StageJournal(checkpoint_directory, ordinal=ordinal)
    journal.record("worker_entered")
    memo = ExecutionValidationMemo()
    memo_receipt: dict[str, Any] | None = None

    def action() -> None:
        nonlocal memo_receipt
        with memo:
            run_and_persist_stage_hooked_task(
                task,
                model_factory=lambda: model_factory(journal.record),
                search_factory=lambda: search_factory(journal.record),
                partition_seed_sha256=partition_seed_sha256,
                limits=limits,
                monotonic=monotonic,
                expected_model_cap=expected_model_cap,
                directory=directory,
                writer=writer,
                validator_manifest_sha256=validator_manifest_sha256,
                stage_callback=journal.record,
            )
        # Validate before the frozen terminal helper can write a successful
        # child receipt or the worker can publish worker_complete.
        memo_receipt = validate_memo_receipt(memo.content_free_receipt())

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
    )
    if memo_receipt is None:
        raise RuntimeError("V2.44.86 memo receipt is absent")
    journal.record("worker_complete")
    receipt = memo_receipt
    return receipt


__all__ = [
    "MINIMUM_TOTAL_HITS",
    "POLICY_ID",
    "run_memoized_worker",
    "validate_memo_receipt",
]
