"""Label-blind child runtime for one coverage-revision artifact bundle.

Client construction and credentials remain outside this module so a future
protocol can bind them without persisting secrets.  This layer validates the
visible task, executes V2.48.62 with already-constructed bounded clients,
collects direct/rate/pacing receipts from the same search instance, writes the
V2.48.63 create-exclusive bundle, and writes the content-free child terminal
receipt last.  It has no evaluator capability and grants no benchmark launch.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24309_runner_exit_integration import run_child_with_terminal_receipt
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24856_pacing_aware_admission import (
    validate_receipt as validate_pacing_receipt,
)
from .v24862_same_task_coverage_runtime import (
    PAGE_ATTRIBUTE,
    run_v24862_task,
)
from .v24863_coverage_revision_child_bundle import (
    ALL_NAMES,
    BUNDLE_NAME,
    FINAL_MODEL_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    validate_bundle,
    write_bundle,
)


POLICY_ID = "v24864_coverage_revision_child_runtime_v1"
TERMINAL_NAME = "child_terminal_receipt.json"
PACING_ATTRIBUTE = "_v24862_pacing_admission_receipt"


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
        raise ValueError("V2.48.64 task directory escaped output root")
    return target


def run_child_bundle(
    *,
    output_root: Path,
    directory: Path,
    task: Mapping[str, Any],
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    task_directory = _ordinary_directory(directory, output_root)
    if (
        not isinstance(model, DeadlineAwareGlobalModelSlotLimiter)
        or not isinstance(search, ThinSameResponseCitationTitleBackfillSearchClient)
        or int(model.slot_cap) != int(expected_model_slot_cap)
    ):
        raise ValueError("V2.48.64 bounded client identity drifted")
    limits.validate()
    two_wave_policy.validate()
    if any(
        (task_directory / name).exists()
        or (task_directory / name).is_symlink()
        for name in (*ALL_NAMES, TERMINAL_NAME)
    ):
        raise FileExistsError("V2.48.64 child artifact surface is not pristine")

    def action() -> dict[str, Any]:
        visible = validate_visible_task(task)
        outcome = run_v24862_task(
            visible,
            arm="baseline",
            model=model,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            monotonic=monotonic,
            progress=progress,
        )
        direct_method = getattr(search, "direct_search_receipt", None)
        rate_method = getattr(search, "rate_aware_search_receipt", None)
        pacing = getattr(search, PACING_ATTRIBUTE, None)
        pages = getattr(search, PAGE_ATTRIBUTE, None)
        if (
            not callable(direct_method)
            or not callable(rate_method)
            or not isinstance(pacing, Mapping)
            or not isinstance(pages, tuple)
        ):
            raise ValueError("V2.48.64 same-task search receipts are absent")
        validate_pacing_receipt(pacing)
        return write_bundle(
            output_root=output_root,
            directory=task_directory,
            outcome=outcome,
            direct_receipt=direct_method(),
            rate_receipt=rate_method(),
            pacing_receipt=pacing,
            expected_model_slot_cap=expected_model_slot_cap,
            expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
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
        raise RuntimeError("V2.48.64 child returned without bundle commit marker")
    validate_bundle(
        output_root=output_root,
        directory=task_directory,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
    )
    return value


__all__ = [
    "PACING_ATTRIBUTE",
    "POLICY_ID",
    "TERMINAL_NAME",
    "run_child_bundle",
]
