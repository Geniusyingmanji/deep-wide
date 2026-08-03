#!/usr/bin/env python3
"""Run one frozen V2.43.14 visible task for one preregistered arm."""

from __future__ import annotations

import argparse
import json
import os
import sys
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
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24287_hard_deadline_fetch import (  # noqa: E402
    HardDeadlineNativeSearchClient,
    validate_transport_health,
)
from deepwide_agent.v24294_staged_reserve import StagedReservePolicy  # noqa: E402
from deepwide_agent.v24314_forward_contract import (  # noqa: E402
    ARMS,
    CHILD_TERMINAL_NAME,
    CLEANUP_RESERVE_SECONDS,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
    OUTPUT_ROOT,
    RESERVE_POLICY,
    SEARCH,
    TASK_ROOT,
    TWO_WAVE_POLICY,
    payload_sha256,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    validate_v24310_result,
)
from deepwide_agent.v24313_runner_integration import (  # noqa: E402
    build_deadline_model,
    run_v24313_task,
)


def _ordinary_under(path: Path, root: Path) -> Path:
    target = path.resolve(strict=False)
    base = root.resolve()
    if path.is_symlink() or target.is_symlink() or not target.is_relative_to(base):
        raise ValueError("V2.43.14 child path escaped its frozen output root")
    return target


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.43.14 child expected a JSON object")
    return value


def _atomic_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
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


def _atomic_progress(path: Path, value: dict[str, Any]) -> None:
    if (
        value.get("role") != "v24257_score_first_safe_progress"
        or value.get("contains_question_query_url_page_prediction_or_answer") is not False
        or value.get("mapping_gold_evaluator_or_score_read") is not False
    ):
        raise ValueError("V2.43.14 unsafe child progress")
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _transport(search: HardDeadlineNativeSearchClient) -> dict[str, int]:
    return validate_transport_health(
        {
            "hard_fetch_helper_calls": int(search.hard_fetch_helper_calls),
            "hard_fetch_deadline_failures": int(search.hard_fetch_deadline_failures),
            "fetch_helper_failures": int(search.fetch_helper_failures),
        }
    )


def _validate_paths(
    args: Any,
) -> tuple[str, Path, Path, Path, Path, Path, Path, Path]:
    arm = str(args.arm)
    if arm not in ARMS:
        raise ValueError("V2.43.14 child arm is invalid")
    output = (ROOT / OUTPUT_ROOT).resolve()
    task_root = (ROOT / TASK_ROOT / arm).resolve()
    task = _ordinary_under(Path(args.task), output)
    result = _ordinary_under(Path(args.result), output)
    progress = _ordinary_under(Path(args.progress), output)
    receipt = _ordinary_under(Path(args.model_slot_receipt), output)
    transport = _ordinary_under(Path(args.transport_health), output)
    terminal = _ordinary_under(Path(args.child_terminal_receipt), output)
    raw_slots = Path(args.model_slot_directory)
    slots = raw_slots.resolve(strict=False)
    directory = task.parent
    if (
        not task.is_file()
        or not directory.is_relative_to(task_root)
        or not directory.name.startswith("task_")
        or task.name != "visible_task.json"
        or result != directory / "result.json"
        or progress != directory / "safe_progress.json"
        or receipt != directory / "model_slot_receipt.json"
        or transport != directory / "transport_health.json"
        or terminal != directory / CHILD_TERMINAL_NAME
        or raw_slots.is_symlink()
        or slots.is_symlink()
        or slots != (ROOT / MODEL_SLOT_DIRECTORY).resolve()
        or not slots.is_dir()
        or any(
            path.exists() or path.is_symlink()
            for path in (result, progress, receipt, transport, terminal)
        )
    ):
        raise RuntimeError("V2.43.14 child execution surface drifted")
    return arm, task, result, progress, receipt, transport, terminal, slots


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--progress", required=True)
    parser.add_argument("--model-slot-directory", required=True)
    parser.add_argument("--model-slot-receipt", required=True)
    parser.add_argument("--transport-health", required=True)
    parser.add_argument("--child-terminal-receipt", required=True)
    args = parser.parse_args()
    (
        arm,
        task_path,
        result_path,
        progress_path,
        receipt_path,
        transport_path,
        terminal_path,
        slots,
    ) = _validate_paths(args)

    def action() -> None:
        started = __import__("time").monotonic()
        absolute_deadline = started + float(LIMITS["wall_seconds"])
        task = validate_visible_task(_read_object(task_path))
        limits = ScoreFirstLimits(**LIMITS)
        policy = TwoWavePolicy(**TWO_WAVE_POLICY)
        reserve = StagedReservePolicy(**RESERVE_POLICY)
        limits.validate()
        policy.validate()
        reserve.validate()
        model = build_deadline_model(
            url=MODEL["proxy_url"],
            model_name=MODEL["name"],
            reasoning_effort=MODEL["reasoning_effort"],
            service_tier=MODEL["service_tier"],
            static_timeout_seconds=MODEL["timeout_seconds"],
            max_retries=MODEL["max_retries"],
            slot_directory=slots,
            output_root=ROOT / "outputs",
            slot_cap=MODEL_SLOT_CAP,
            pool_id=MODEL_SLOT_POOL_ID,
            absolute_deadline=absolute_deadline,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        if MODEL_SLOT_POOL_ID != POOL_ID:
            raise RuntimeError("V2.43.14 model-slot identity drifted")
        search = HardDeadlineNativeSearchClient(
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
        )
        try:
            result = run_v24313_task(
                task,
                arm=arm,
                model=model,
                search=search,
                limits=limits,
                two_wave_policy=policy,
                reserve_policy=reserve if arm == "candidate" else None,
                progress=lambda value: _atomic_progress(progress_path, dict(value)),
            )
            validate_v24310_result(result, arm)
        except BaseException:
            if not receipt_path.exists() and not receipt_path.is_symlink():
                _atomic_new(receipt_path, model.receipt())
            if not transport_path.exists() and not transport_path.is_symlink():
                _atomic_new(transport_path, _transport(search))
            raise
        receipt_value = model.receipt()
        health = _transport(search)
        _atomic_new(receipt_path, receipt_value)
        _atomic_new(transport_path, health)
        envelope = {
            "artifact_version": 1,
            "role": "v24314_paired_dev64_task_envelope",
            "arm": arm,
            "result": result,
            "transport_health": health,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        envelope["envelope_payload_sha256"] = payload_sha256(envelope)
        _atomic_new(result_path, envelope)

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
