#!/usr/bin/env python3
"""Run one V2.46.34 visible task; no evaluator capability is imported."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import run_child_with_terminal_receipt  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    ThinSameResponseCitationTitleBackfillSearchClient,
    validate_thin_search_class,
)
from deepwide_agent.v24630_exact220_task_integration import (  # noqa: E402
    build_envelope,
    run_v24630_task,
)
from deepwide_agent.v24634_exact220_contract import (  # noqa: E402
    ARM,
    CHILD_TERMINAL_NAME,
    CLEANUP_RESERVE_SECONDS,
    LIMITS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    RECEIPT_NAME,
    SEARCH,
    TASK_ROOT,
    TRANSPORT_NAME,
    TWO_WAVE_POLICY,
)


def _ordinary_under(path: Path, root: Path) -> Path:
    resolved = path.resolve(strict=False)
    base = root.resolve()
    if path.is_symlink() or resolved.is_symlink() or not resolved.is_relative_to(base):
        raise ValueError("V2.46.34 child path escaped output root")
    return resolved


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.46.34 child expected an object")
    return value


def _atomic_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
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


def _atomic_progress(path: Path, value: dict[str, Any]) -> None:
    if (
        value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer") is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        raise ValueError("V2.46.34 unsafe child progress")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _paths(args: Any) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path]:
    output = (ROOT / OUTPUT_ROOT).resolve()
    task_root = (ROOT / TASK_ROOT).resolve()
    task = _ordinary_under(Path(args.task), output)
    result = _ordinary_under(Path(args.result), output)
    progress = _ordinary_under(Path(args.progress), output)
    model_receipt = _ordinary_under(Path(args.model_slot_receipt), output)
    transport = _ordinary_under(Path(args.transport_health), output)
    single = _ordinary_under(Path(args.search_single_shot_receipt), output)
    backfill = _ordinary_under(Path(args.citation_title_backfill_receipt), output)
    terminal = _ordinary_under(Path(args.child_terminal_receipt), output)
    slots = Path(args.model_slot_directory).resolve(strict=False)
    directory = task.parent
    expected = {
        result: "result.json",
        progress: "safe_progress.json",
        model_receipt: RECEIPT_NAME,
        transport: TRANSPORT_NAME,
        single: "search_single_shot_receipt.json",
        backfill: "citation_title_backfill_receipt.json",
        terminal: CHILD_TERMINAL_NAME,
    }
    if (
        not task.is_file()
        or task.name != "visible_task.json"
        or not directory.is_relative_to(task_root)
        or any(path != directory / name for path, name in expected.items())
        or any(path.exists() or path.is_symlink() for path in expected)
        or slots != (ROOT / MODEL_SLOT_DIRECTORY).resolve()
        or not slots.is_dir()
    ):
        raise RuntimeError("V2.46.34 child execution surface drifted")
    return task, result, progress, model_receipt, transport, single, backfill, terminal


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in (
        "task", "result", "progress", "model_slot_directory", "model_slot_receipt",
        "transport_health", "search_single_shot_receipt",
        "citation_title_backfill_receipt", "child_terminal_receipt",
    ):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    args = parser.parse_args()
    task_path, result_path, progress_path, receipt_path, transport_path, single_path, backfill_path, terminal_path = _paths(args)

    def action() -> None:
        started = time.monotonic()
        deadline = started + float(LIMITS["wall_seconds"])
        task = validate_visible_task(_read(task_path))
        limits = ScoreFirstLimits(**LIMITS)
        policy = TwoWavePolicy(**TWO_WAVE_POLICY)
        limits.validate()
        policy.validate()
        inner_model = HardTotalWallResponsesClient(
            MODEL["proxy_url"],
            MODEL["name"],
            reasoning_effort=MODEL["reasoning_effort"],
            service_tier=MODEL["service_tier"],
            timeout=MODEL["timeout_seconds"],
            max_retries=MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _stage: None,
        )
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner_model,
            slot_directory=ROOT / MODEL_SLOT_DIRECTORY,
            output_root=ROOT / "outputs",
            slot_cap=MODEL_SLOT_CAP,
            pool_id=MODEL_SLOT_POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        if MODEL_SLOT_POOL_ID != POOL_ID:
            raise RuntimeError("V2.46.34 model-slot identity drifted")
        validate_thin_search_class()
        search = ThinSameResponseCitationTitleBackfillSearchClient(
            SEARCH["proxy_url"],
            SEARCH["model"],
            reasoning_effort=MODEL["reasoning_effort"],
            service_tier=MODEL["service_tier"],
            timeout=SEARCH["timeout_seconds"],
            max_retries=SEARCH["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
            max_workers=SEARCH["workers"],
            batch_size=SEARCH["batch_size"],
            search_context_size=SEARCH["context_size"],
            max_output_tokens=SEARCH["max_output_tokens"],
            fetch_pages=False,
            fetch_workers=SEARCH["fetch_workers"],
            fetch_timeout=SEARCH["fetch_timeout_seconds"],
            max_page_chars=LIMITS["page_chars"],
            hard_fetch_deadline_seconds=SEARCH["hard_fetch_deadline_seconds"],
        )
        try:
            outcome = run_v24630_task(
                task,
                arm=ARM,
                model=model,
                search=search,
                limits=limits,
                two_wave_policy=policy,
                monotonic=time.monotonic,
                progress=lambda value: _atomic_progress(progress_path, dict(value)),
            )
        except BaseException:
            if not receipt_path.exists():
                _atomic_new(receipt_path, model.receipt())
            if not transport_path.exists():
                _atomic_new(transport_path, search.transport_health())
            if not single_path.exists():
                _atomic_new(single_path, search.single_shot_receipt())
            if not backfill_path.exists():
                _atomic_new(backfill_path, search.citation_title_backfill_receipt())
            raise
        _atomic_new(receipt_path, outcome.model_slot_receipt)
        _atomic_new(transport_path, outcome.transport_health)
        _atomic_new(single_path, outcome.search_single_shot_receipt)
        _atomic_new(backfill_path, outcome.citation_title_backfill_receipt)
        _atomic_new(result_path, build_envelope(outcome, arm=ARM))

    run_child_with_terminal_receipt(
        output_root=ROOT / OUTPUT_ROOT,
        directory=terminal_path.parent,
        action=action,
        result_name=result_path.name,
        model_receipt_name=receipt_path.name,
        transport_receipt_name=transport_path.name,
        terminal_name=terminal_path.name,
    )


if __name__ == "__main__":
    main()
