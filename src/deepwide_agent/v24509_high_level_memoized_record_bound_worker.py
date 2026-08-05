"""Bounded V2.45.05 worker with fail-closed high-level memoization.

The proof surface and V2.45.04 certificate remain byte-compatible.  The only
change is that V2.45.08 wraps the trusted child execution alongside the
existing V2.44.85 lower-graph memo.  Both content-free receipts are validated
before any successful child terminal receipt or ``worker_complete`` stage can
be published.  The high-level receipt is in-process only; the unchanged
complete semantic result and exact-byte certificate remain the durable proof.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24399_failure_observable_runner import (
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from .v24469_bounded_worker_supervisor import StageJournal, bind_worker_to_parent
from .v24470_bounded_adaptive_integration import _validate_layout
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24486_memoized_worker_integration import validate_memo_receipt
from .v24504_proof_carrying_record_bound_reserve import (
    CERTIFICATE_NAME,
    build_envelope_from_validated_execution,
    build_terminal_certificate,
    run_single_validation_v24503_task,
)
from .v24508_execution_scoped_high_level_validation_memo import (
    HighLevelValidationMemo,
    validate_receipt as validate_high_level_receipt,
)


POLICY_ID = "v24509_fail_closed_high_level_memoized_record_bound_worker_v1"
COMBINED_RECEIPT_KEYS = frozenset(
    {
        "policy_id",
        "low_level_validation_memo_receipt",
        "high_level_validation_memo_receipt",
        "both_memos_validated_before_success_terminal",
        "durable_proof_surface_and_certificate_unchanged",
        "high_level_receipt_persisted_or_emitted_to_public_aggregate",
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    }
)


def build_combined_receipt(
    low: Mapping[str, Any], high: Mapping[str, Any]
) -> dict[str, Any]:
    value = {
        "policy_id": POLICY_ID,
        "low_level_validation_memo_receipt": validate_memo_receipt(low),
        "high_level_validation_memo_receipt": validate_high_level_receipt(high),
        "both_memos_validated_before_success_terminal": True,
        "durable_proof_surface_and_certificate_unchanged": True,
        "high_level_receipt_persisted_or_emitted_to_public_aggregate": False,
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    return validate_combined_receipt(value)


def validate_combined_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    low = copied.get("low_level_validation_memo_receipt")
    high = copied.get("high_level_validation_memo_receipt")
    true_fields = (
        "both_memos_validated_before_success_terminal",
        "durable_proof_surface_and_certificate_unchanged",
    )
    false_fields = (
        "high_level_receipt_persisted_or_emitted_to_public_aggregate",
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != COMBINED_RECEIPT_KEYS
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(low, Mapping)
        or validate_memo_receipt(low) != low
        or not isinstance(high, Mapping)
        or validate_high_level_receipt(high) != high
        or high.get("total_misses") != 3
        or high.get("total_hits", -1) < 3
        or high.get("total_mismatches") != 0
        or any(
            item.get("misses") != 1 or item.get("hits", -1) < 1
            for item in high["layers"].values()
        )
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.09 combined memo receipt drifted")
    return copied


def run_high_level_memoized_record_bound_worker(
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
    output_root, directory, checkpoint_directory = _validate_layout(
        output_root, directory, checkpoint_directory
    )
    bind_worker_to_parent(expected_parent_pid=expected_supervisor_pid)
    journal = StageJournal(checkpoint_directory, ordinal=ordinal)
    journal.record("worker_entered")
    combined: dict[str, Any] | None = None
    model: Any = None
    search: Any = None

    def action() -> None:
        nonlocal combined, model, search
        stage = "model_construction"
        try:
            model = model_factory(journal.record)
            journal.record("model_constructed")
            stage = "search_construction"
            search = search_factory(journal.record)
            journal.record("search_constructed")
            stage = "runtime"
            journal.record("runtime_entered")
            low = ExecutionValidationMemo()
            high = HighLevelValidationMemo()
            with low:
                with high:
                    validated = run_single_validation_v24503_task(
                        task,
                        model=model,
                        search=search,
                        partition_seed_sha256=partition_seed_sha256,
                        limits=limits,
                        monotonic=monotonic,
                    )
            combined = build_combined_receipt(
                low.content_free_receipt(), high.content_free_receipt()
            )
            journal.record("parent_runtime_returned")
            journal.record("adaptive_support_entered")
            journal.record("adaptive_support_returned")
            journal.record("complete_validation_entered")
            journal.record("complete_validation_returned")
        except BaseException as error:
            persist_failure_artifacts(
                error,
                failure_stage=stage,
                model=model,
                search=search,
                expected_model_cap=expected_model_cap,
                writer=writer,
            )
            raise
        outcome = validated._trusted_outcome()
        journal.record("artifact_persistence_entered")
        durable_envelope = build_envelope_from_validated_execution(validated)
        artifacts = {
            MODEL_NAME: outcome.model_slot_receipt,
            TRANSPORT_NAME: outcome.transport_health,
            SEARCH_NAME: outcome.search_single_shot_receipt,
            RESULT_NAME: durable_envelope,
        }
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            writer(name, artifacts[name])
        journal.record("certificate_persistence_entered")
        certificate = build_terminal_certificate(
            directory,
            validated,
            memo_receipt=combined["low_level_validation_memo_receipt"],
            validator_manifest_sha256=validator_manifest_sha256,
            expected_artifacts=artifacts,
        )
        writer(CERTIFICATE_NAME, certificate)

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name="child_terminal_receipt.json",
    )
    if combined is None:
        raise RuntimeError("V2.45.09 combined memo receipt is absent")
    validate_combined_receipt(combined)
    journal.record("worker_complete")
    return dict(combined)


__all__ = [
    "POLICY_ID",
    "build_combined_receipt",
    "run_high_level_memoized_record_bound_worker",
    "validate_combined_receipt",
]
