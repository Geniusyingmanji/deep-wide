#!/usr/bin/env python3
"""Run one V2.47.84 visible task without evaluator capability."""

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

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallNativeSearchClient,
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24784_projection_funnel_integration import (  # noqa: E402
    run_v24784_task,
)
from deepwide_agent.v24784_projection_funnel_execution_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    LIMITS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
    MODEL,
    MODEL_RECEIPT_NAME,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    RESULT_NAME,
    SEARCH,
    TERMINAL_RECEIPT_NAME,
    TRANSPORT_RECEIPT_NAME,
)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("V2.47.84 child expected ordinary task")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.47.84 child expected object task")
    return value


def _ordinary_under(path: Path, root: Path) -> Path:
    target = path.resolve(strict=False)
    base = root.resolve()
    if path.is_symlink() or target.is_symlink() or not target.is_relative_to(base):
        raise ValueError("V2.47.84 child path escaped output root")
    return target


def _atomic_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
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


def _paths(args: Any) -> tuple[Path, Path, Path, Path, Path]:
    output = (ROOT / OUTPUT_ROOT).resolve()
    task = _ordinary_under(Path(args.task), output)
    result = _ordinary_under(Path(args.result), output)
    model = _ordinary_under(Path(args.model_receipt), output)
    transport = _ordinary_under(Path(args.transport_receipt), output)
    terminal = _ordinary_under(Path(args.terminal_receipt), output)
    slots = Path(args.model_slot_directory).resolve(strict=False)
    directory = task.parent
    expected = {
        task: "visible_task.json",
        result: RESULT_NAME,
        model: MODEL_RECEIPT_NAME,
        transport: TRANSPORT_RECEIPT_NAME,
        terminal: TERMINAL_RECEIPT_NAME,
    }
    if (
        not task.is_file()
        or any(path != directory / name for path, name in expected.items())
        or any(
            path.exists() or path.is_symlink()
            for path in (result, model, transport, terminal)
        )
        or slots != (ROOT / MODEL_SLOT_DIRECTORY).resolve()
        or not slots.is_dir()
    ):
        raise RuntimeError("V2.47.84 child execution surface drifted")
    return task, result, model, transport, terminal


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in (
        "task",
        "result",
        "model_slot_directory",
        "model_receipt",
        "transport_receipt",
        "terminal_receipt",
    ):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    args = parser.parse_args()
    task_path, result_path, model_path, transport_path, terminal_path = _paths(args)

    def action() -> None:
        deadline = time.monotonic() + float(LIMITS["wall_seconds"])
        task = validate_visible_task(_read(task_path))
        limits = ScoreFirstLimits(**LIMITS)
        limits.validate()
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
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        search = HardTotalWallNativeSearchClient(
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
            stage_callback=lambda _stage: None,
        )
        try:
            result = run_v24784_task(
                task,
                model=model,
                search=search,
                limits=limits,
                monotonic=time.monotonic,
            )
        except BaseException:
            if not model_path.exists():
                _atomic_new(model_path, model.receipt())
            if not transport_path.exists():
                _atomic_new(transport_path, search.transport_health())
            raise
        _atomic_new(model_path, model.receipt())
        _atomic_new(transport_path, search.transport_health())
        _atomic_new(result_path, result)

    run_child_with_terminal_receipt(
        output_root=ROOT / OUTPUT_ROOT,
        directory=terminal_path.parent,
        action=action,
        result_name=result_path.name,
        model_receipt_name=model_path.name,
        transport_receipt_name=transport_path.name,
        terminal_name=terminal_path.name,
    )


if __name__ == "__main__":
    main()
