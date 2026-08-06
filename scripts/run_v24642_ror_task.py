#!/usr/bin/env python3
"""Run one V2.46.42 visible ROR task without evaluator capability."""

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
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from deepwide_agent.v24642_deterministic_pair_runtime import (  # noqa: E402
    run_v24642_task,
)
from deepwide_agent.v24642_ror_external_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    LIMITS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    SEARCH,
)


RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
TERMINAL_NAME = "child_terminal_receipt.json"


def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.46.42 child expected object")
    return value


def ordinary(path: Path) -> Path:
    root = (ROOT / OUTPUT_ROOT).resolve()
    value = path.resolve(strict=False)
    if path.is_symlink() or not value.is_relative_to(root):
        raise ValueError("V2.46.42 child path escaped output")
    return value


def new(path: Path, value: dict[str, Any]) -> None:
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
        "model_receipt",
        "transport_receipt",
        "terminal_receipt",
    ):
        parser.add_argument("--" + name.replace("_", "-"), required=True)
    args = parser.parse_args()
    task_path = ordinary(Path(args.task))
    directory = task_path.parent
    result_path = ordinary(Path(args.result))
    model_path = ordinary(Path(args.model_receipt))
    transport_path = ordinary(Path(args.transport_receipt))
    terminal_path = ordinary(Path(args.terminal_receipt))
    expected = {
        task_path: "visible_task.json",
        result_path: RESULT_NAME,
        model_path: MODEL_NAME,
        transport_path: TRANSPORT_NAME,
        terminal_path: TERMINAL_NAME,
    }
    if any(path.parent != directory or path.name != name for path, name in expected.items()):
        raise ValueError("V2.46.42 child surface drifted")

    def action() -> None:
        deadline = time.monotonic() + float(LIMITS["wall_seconds"])
        task = validate_visible_task(read(task_path))
        limits = ScoreFirstLimits(**LIMITS)
        inner = HardTotalWallResponsesClient(
            MODEL["proxy_url"],
            MODEL["name"],
            reasoning_effort=MODEL["reasoning_effort"],
            service_tier=MODEL["service_tier"],
            timeout=MODEL["timeout_seconds"],
            max_retries=MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=ROOT / MODEL_SLOT_DIRECTORY,
            output_root=ROOT / "outputs",
            slot_cap=MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
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
            result = run_v24642_task(
                task,
                model=model,
                search=search,
                limits=limits,
                monotonic=time.monotonic,
            )
        except BaseException:
            if not model_path.exists():
                new(model_path, model.receipt())
            if not transport_path.exists():
                new(transport_path, search.transport_health())
            raise
        new(model_path, model.receipt())
        new(transport_path, search.transport_health())
        new(result_path, result)

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
