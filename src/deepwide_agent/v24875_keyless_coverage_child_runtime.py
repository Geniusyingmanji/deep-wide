"""Label-blind child runtime for one V2.48.74 keyless coverage bundle."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24873_keyless_fixed_coverage_runtime import run_v24873_task
from .v24874_keyless_coverage_bundle import (
    ALL_NAMES,
    BUNDLE_NAME,
    FINAL_MODEL_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    validate_bundle,
    write_bundle,
)


POLICY_ID = "v24875_keyless_coverage_child_runtime_v1"
TERMINAL_NAME = "child_terminal_receipt.json"


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
        raise ValueError("V2.48.75 task directory escaped output root")
    return target


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
        raise ValueError("V2.48.75 bounded client identity drifted")
    limits.validate()
    if any(
        (task_directory / name).exists() or (task_directory / name).is_symlink()
        for name in (*ALL_NAMES, TERMINAL_NAME)
    ):
        raise FileExistsError("V2.48.75 child artifact surface is not pristine")

    def action() -> dict[str, Any]:
        visible = validate_visible_task(task)
        outcome = run_v24873_task(
            visible,
            arm="baseline",
            model=model,
            search=search,
            limits=limits,
            monotonic=monotonic,
            progress=progress,
        )
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
            raise ValueError("V2.48.75 keyless transport counters are absent")
        return write_bundle(
            output_root=output_root,
            directory=task_directory,
            outcome=outcome,
            status_counts=status_counts,
            transport_failures=transport_failures,
            hard_total_wall_timeouts=hard_timeouts,
            expected_model_slot_cap=expected_model_slot_cap,
        )

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
        raise RuntimeError("V2.48.75 child returned without bundle commit marker")
    validate_bundle(
        output_root=output_root,
        directory=task_directory,
        expected_model_slot_cap=expected_model_slot_cap,
    )
    return value


__all__ = ["POLICY_ID", "TERMINAL_NAME", "run_child_bundle"]
