#!/usr/bin/env python3
"""Run one visible-only V2.46.71 information-gain ROR task."""

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
from deepwide_agent.v24309_runner_exit_integration import run_child_with_terminal_receipt  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import DeadlineAwareNativeSearchClient  # noqa: E402
from deepwide_agent.v24671_runner_integration import build_envelope, run_v24671_task  # noqa: E402
from deepwide_agent.v24671_ror_external_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    LIMITS,
    MINIMUM_ATTEMPT_SECONDS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    SEARCH,
    TASK_ROOT,
    TASK_WALL_SECONDS,
)


RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
TERMINAL_NAME = "child_terminal_receipt.json"


def _under(path: Path, root: Path) -> Path:
    target = path.resolve(strict=False)
    if path.is_symlink() or not target.is_relative_to(root.resolve()):
        raise ValueError("V2.46.71 child path escaped output root")
    return target


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.46.71 expected object")
    return value


def _new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    for name in (
        "task",
        "result",
        "model_slot_receipt",
        "transport_health",
        "terminal",
    ):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    args = parser.parse_args()
    output = (ROOT / OUTPUT_ROOT).resolve()
    task_root = (ROOT / TASK_ROOT).resolve()
    task_path = _under(Path(args.task), output)
    directory = task_path.parent
    result_path = _under(Path(args.result), output)
    model_path = _under(Path(args.model_slot_receipt), output)
    transport_path = _under(Path(args.transport_health), output)
    terminal_path = _under(Path(args.terminal), output)
    if (
        not task_path.is_file()
        or not directory.is_relative_to(task_root)
        or task_path.name != "visible_task.json"
        or result_path != directory / RESULT_NAME
        or model_path != directory / MODEL_NAME
        or transport_path != directory / TRANSPORT_NAME
        or terminal_path != directory / TERMINAL_NAME
    ):
        raise RuntimeError("V2.46.71 child surface drifted")

    def action() -> None:
        absolute_deadline = time.monotonic() + TASK_WALL_SECONDS
        task = validate_visible_task(_read(task_path))
        limits = ScoreFirstLimits(**LIMITS)
        model = build_deadline_model(
            url=MODEL["proxy_url"],
            model_name=MODEL["name"],
            reasoning_effort=MODEL["reasoning_effort"],
            service_tier=MODEL["service_tier"],
            static_timeout_seconds=MODEL["timeout_seconds"],
            max_retries=MODEL["max_retries"],
            slot_directory=ROOT / MODEL_SLOT_DIRECTORY,
            output_root=ROOT / "outputs",
            slot_cap=MODEL_SLOT_CAP,
            pool_id=MODEL_SLOT_POOL_ID,
            absolute_deadline=absolute_deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_ATTEMPT_SECONDS,
        )
        if MODEL_SLOT_POOL_ID != POOL_ID:
            raise RuntimeError("V2.46.71 slot identity drifted")
        search = DeadlineAwareNativeSearchClient(
            SEARCH["proxy_url"],
            SEARCH["model"],
            reasoning_effort=MODEL["reasoning_effort"],
            service_tier=MODEL["service_tier"],
            timeout=SEARCH["timeout_seconds"],
            max_retries=SEARCH["max_retries"],
            max_workers=SEARCH["workers"],
            batch_size=SEARCH["batch_size"],
            search_context_size=SEARCH["context_size"],
            max_output_tokens=SEARCH["max_output_tokens"],
            fetch_pages=False,
            fetch_workers=SEARCH["fetch_workers"],
            fetch_timeout=SEARCH["fetch_timeout_seconds"],
            max_page_chars=LIMITS["page_chars"],
            hard_fetch_deadline_seconds=SEARCH["hard_fetch_deadline_seconds"],
            absolute_deadline=absolute_deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_ATTEMPT_SECONDS,
        )
        try:
            outcome = run_v24671_task(
                task,
                model=model,
                search=search,
                limits=limits,
                monotonic=time.monotonic,
            )
        except BaseException:
            if not model_path.exists():
                _new(model_path, model.receipt())
            if not transport_path.exists():
                _new(transport_path, search.transport_health())
            raise
        _new(model_path, outcome.model_slot_receipt)
        _new(transport_path, outcome.transport_health)
        _new(result_path, build_envelope(outcome))

    run_child_with_terminal_receipt(
        output_root=ROOT / OUTPUT_ROOT,
        directory=directory,
        action=action,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_NAME,
        transport_receipt_name=TRANSPORT_NAME,
        terminal_name=TERMINAL_NAME,
    )


if __name__ == "__main__":
    main()
