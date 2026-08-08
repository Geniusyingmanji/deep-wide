#!/usr/bin/env python3
"""Run one label-blind V2.48.77 keyless coverage task."""

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

from deepwide_agent import v24877_keyless_coverage_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
)
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    ThinSameResponseCitationTitleBackfillSearchClient,
    validate_thin_search_class,
)
from deepwide_agent.v24875_keyless_coverage_child_runtime import (  # noqa: E402
    run_child_bundle,
)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.77 expected ordinary visible task")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.77 visible task must be an object")
    return value


def _task_directory(task_argument: str) -> tuple[Path, Path]:
    task = Path(task_argument).resolve(strict=False)
    output = (ROOT / contract.OUTPUT_ROOT).resolve()
    task_root = (ROOT / contract.TASK_ROOT).resolve()
    directory = task.parent
    if (
        task.is_symlink()
        or not task.is_file()
        or task.name != "visible_task.json"
        or directory.is_symlink()
        or not directory.is_dir()
        or not directory.is_relative_to(task_root)
        or not directory.is_relative_to(output)
    ):
        raise RuntimeError("V2.48.77 child task surface drifted")
    return task, directory


def _atomic_progress(path: Path, value: dict[str, Any]) -> None:
    if (
        value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer")
        is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        raise ValueError("V2.48.77 unsafe child progress")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    task_path, directory = _task_directory(args.task)
    started = time.monotonic()
    deadline = started + float(contract.LIMITS["wall_seconds"])
    limits = ScoreFirstLimits(**contract.LIMITS)
    limits.validate()
    inner_model = HardTotalWallResponsesClient(
        contract.MODEL["proxy_url"],
        contract.MODEL["name"],
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.MODEL["timeout_seconds"],
        max_retries=contract.MODEL["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        stage_callback=lambda _stage: None,
    )
    model = DeadlineAwareGlobalModelSlotLimiter(
        inner_model,
        slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
        output_root=ROOT / "outputs",
        slot_cap=contract.MODEL_SLOT_CAP,
        pool_id=POOL_ID,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
    )
    if contract.MODEL_SLOT_CAP != 8:
        raise RuntimeError("V2.48.77 model slot cap drifted")
    validate_thin_search_class()
    search = ThinSameResponseCitationTitleBackfillSearchClient(
        contract.SEARCH["proxy_url"],
        contract.SEARCH["model"],
        reasoning_effort=contract.MODEL["reasoning_effort"],
        service_tier=contract.MODEL["service_tier"],
        timeout=contract.SEARCH["timeout_seconds"],
        max_retries=contract.SEARCH["max_retries"],
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        max_workers=contract.SEARCH["workers"],
        batch_size=contract.SEARCH["batch_size"],
        search_context_size=contract.SEARCH["context_size"],
        max_output_tokens=contract.SEARCH["max_output_tokens"],
        fetch_pages=False,
        fetch_workers=contract.SEARCH["fetch_workers"],
        fetch_timeout=contract.SEARCH["fetch_timeout_seconds"],
        max_page_chars=contract.LIMITS["page_chars"],
        hard_fetch_deadline_seconds=contract.SEARCH[
            "hard_fetch_deadline_seconds"
        ],
    )
    run_child_bundle(
        output_root=ROOT / contract.OUTPUT_ROOT,
        directory=directory,
        task=_read(task_path),
        model=model,
        search=search,
        limits=limits,
        expected_model_slot_cap=contract.MODEL_SLOT_CAP,
        monotonic=time.monotonic,
        progress=lambda value: _atomic_progress(
            directory / "safe_progress.json", dict(value)
        ),
    )


if __name__ == "__main__":
    main()
