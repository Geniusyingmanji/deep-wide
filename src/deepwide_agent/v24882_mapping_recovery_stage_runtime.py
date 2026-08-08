"""Content-free stage observability for the mapping-recovery child runtime."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24873_keyless_fixed_coverage_runtime import run_v24873_task
from .v24879_mapping_recovery_effect_bundle import (
    ALL_NAMES,
    BUNDLE_NAME,
    FINAL_MODEL_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    validate_bundle,
    write_bundle,
)
from .v24880_mapping_recovery_child_runtime import TERMINAL_NAME


POLICY_ID = "v24882_content_free_mapping_recovery_stage_runtime_v1"
STAGE_ROLE = "v24882_mapping_recovery_stage_receipt"
STAGE_NAME = "mapping_recovery_stage_receipt.json"
STAGES = (
    "visible_input_validated",
    "parent_runtime_entered",
    "parent_runtime_returned",
    "bundle_effect_validation_entered",
    "bundle_committed",
)


def build_stage_receipt(stage: str) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError("V2.48.82 invalid content-free stage")
    value = {
        "artifact_version": 1,
        "role": STAGE_ROLE,
        "policy_id": POLICY_ID,
        "stage": stage,
        "stage_ordinal": STAGES.index(stage) + 1,
        "contains_question_query_url_host_page_prediction_candidate_value_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_process_or_evaluator_effect_by_stage_writer": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "stage",
        "stage_ordinal",
        "contains_question_query_url_host_page_prediction_candidate_value_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_process_or_evaluator_effect_by_stage_writer",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    stage = copied.get("stage")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or stage not in STAGES
        or copied.get("stage_ordinal") != STAGES.index(str(stage)) + 1
        or copied.get(
            "contains_question_query_url_host_page_prediction_candidate_value_answer_opaque_id_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_process_or_evaluator_effect_by_stage_writer"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.82 stage receipt drifted")
    return copied


def _ordinary_directory(directory: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = directory.resolve()
    if (
        output_root.is_symlink()
        or not output_root.is_dir()
        or directory.is_symlink()
        or not directory.is_dir()
        or not target.is_relative_to(root)
    ):
        raise ValueError("V2.48.82 task directory escaped output root")
    return target


def _atomic_stage(path: Path, value: Mapping[str, Any]) -> None:
    receipt = validate_stage_receipt(value)
    if path.is_symlink() or path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("V2.48.82 stage path is not ordinary")
    current = None
    if path.exists():
        if not path.is_file():
            raise ValueError("V2.48.82 stage artifact is not ordinary")
        current = validate_stage_receipt(
            json.loads(path.read_text(encoding="utf-8"))
        )
    if current is not None and int(receipt["stage_ordinal"]) <= int(
        current["stage_ordinal"]
    ):
        raise ValueError("V2.48.82 stage did not advance")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(receipt, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def run_child_bundle(
    *,
    output_root: Path,
    directory: Path,
    task: Mapping[str, Any],
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    expected_model_slot_cap: int,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    task_directory = _ordinary_directory(directory, output_root)
    if (
        not isinstance(model, DeadlineAwareGlobalModelSlotLimiter)
        or not isinstance(search, ThinSameResponseCitationTitleBackfillSearchClient)
        or int(model.slot_cap) != int(expected_model_slot_cap)
    ):
        raise ValueError("V2.48.82 bounded client identity drifted")
    limits.validate()
    if any(
        (task_directory / name).exists() or (task_directory / name).is_symlink()
        for name in (*ALL_NAMES, TERMINAL_NAME, STAGE_NAME)
    ):
        raise FileExistsError("V2.48.82 child artifact surface is not pristine")
    stage_path = task_directory / STAGE_NAME

    def stage(name: str) -> None:
        _atomic_stage(stage_path, build_stage_receipt(name))

    def action() -> dict[str, Any]:
        visible = validate_visible_task(task)
        stage("visible_input_validated")
        stage("parent_runtime_entered")
        outcome = run_v24873_task(
            visible,
            arm="baseline",
            model=model,
            search=search,
            limits=limits,
            monotonic=monotonic,
            progress=progress,
        )
        stage("parent_runtime_returned")
        status_counts = getattr(search, "status_counts", None)
        transport_failures = getattr(search, "transport_failures", None)
        hard_timeouts = getattr(search, "hard_total_wall_timeouts", None)
        if (
            not isinstance(status_counts, Mapping)
            or isinstance(transport_failures, bool)
            or not isinstance(transport_failures, int)
            or transport_failures < 0
            or isinstance(hard_timeouts, bool)
            or not isinstance(hard_timeouts, int)
            or hard_timeouts < 0
        ):
            raise ValueError("V2.48.82 keyless transport counters are absent")
        stage("bundle_effect_validation_entered")
        value = write_bundle(
            output_root=output_root,
            directory=task_directory,
            outcome=outcome,
            status_counts=status_counts,
            transport_failures=transport_failures,
            hard_total_wall_timeouts=hard_timeouts,
            expected_model_slot_cap=expected_model_slot_cap,
        )
        stage("bundle_committed")
        return value

    value = run_child_with_terminal_receipt(
        output_root=output_root,
        directory=task_directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=FINAL_MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=TERMINAL_NAME,
    )
    if not (task_directory / BUNDLE_NAME).is_file():
        raise RuntimeError("V2.48.82 child returned without bundle commit marker")
    validate_bundle(
        output_root=output_root,
        directory=task_directory,
        expected_model_slot_cap=expected_model_slot_cap,
    )
    final_stage = validate_stage_receipt(
        json.loads(stage_path.read_text(encoding="utf-8"))
    )
    if final_stage["stage"] != "bundle_committed":
        raise RuntimeError("V2.48.82 success lacks terminal stage")
    return value


__all__ = [
    "POLICY_ID",
    "STAGES",
    "STAGE_NAME",
    "build_stage_receipt",
    "run_child_bundle",
    "validate_stage_receipt",
]
