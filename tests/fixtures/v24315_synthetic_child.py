#!/usr/bin/env python3
"""Network-free synthetic child for the V2.43.15 real subprocess smoke."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24267_total_fallback import (  # noqa: E402
    build_total_fallback_result,
)
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    validate_v24310_result,
    zero_effect_receipt,
)
from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    CLEANUP_RESERVE_SECONDS,
    LIMITS,
    MODEL_SLOT_CAP,
    payload_sha256,
)
from deepwide_agent.v24312_deadline_reliability import (
    ROLE as SLOT_ROLE,
    validate_receipt as validate_slot_receipt,
)


def write_new(path: Path, value: dict) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def slot_receipt() -> dict:
    value = {
        "artifact_version": 1,
        "role": SLOT_ROLE,
        "pool_id": POOL_ID,
        "slot_cap": MODEL_SLOT_CAP,
        "acquisitions": 0,
        "slot_timeouts": 0,
        "provider_deadline_failures": 0,
        "total_wait_seconds": 0.0,
        "max_wait_seconds": 0.0,
        "slot_acquisition_counts": [0] * MODEL_SLOT_CAP,
        "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
        "minimum_attempt_seconds": 0.05,
        "remaining_seconds_at_receipt": 1.0,
        "deadline_exhausted": False,
        "label_blind": True,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    from deepwide_agent.v24263_global_model_limiter import payload_sha256

    value["receipt_payload_sha256"] = payload_sha256(value)
    validate_slot_receipt(value, expected_cap=MODEL_SLOT_CAP, expected_acquisitions=0)
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("success", "nonzero"), required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--model-receipt", required=True)
    parser.add_argument("--transport", required=True)
    parser.add_argument("--terminal", required=True)
    args = parser.parse_args()
    task = validate_visible_task(
        json.loads(Path(args.task).read_text(encoding="utf-8"))
    )
    terminal = Path(args.terminal)
    if args.mode == "nonzero":
        write_new(
            terminal,
            child_receipt(
                stage="child_exception",
                exception_type="RuntimeError",
                model_receipt_written=False,
                transport_receipt_written=False,
                result_envelope_written=False,
            ),
        )
        return 7

    result = build_total_fallback_result(
        task,
        limits=ScoreFirstLimits(**LIMITS),
        completion_kind="worker_failure_fallback",
        failure_stage="v24315_synthetic_child",
        failure_type="RuntimeError",
        elapsed_seconds=0.01,
    )
    result[RECEIPT_FIELD] = zero_effect_receipt("candidate")
    validate_v24310_result(result, "candidate")
    transport = {
        "hard_fetch_helper_calls": 0,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
    }
    envelope = {
        "artifact_version": 1,
        "role": "v24315_exact220_task_envelope",
        "arm": "candidate",
        "result": result,
        "transport_health": transport,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    envelope["envelope_payload_sha256"] = payload_sha256(envelope)
    write_new(Path(args.model_receipt), slot_receipt())
    write_new(Path(args.transport), transport)
    write_new(Path(args.result), envelope)
    if not (
        Path(args.model_receipt).is_file()
        and Path(args.transport).is_file()
        and Path(args.result).is_file()
    ):
        raise RuntimeError("V2.43.15 synthetic artifacts are absent")
    write_new(
        terminal,
        child_receipt(
            stage="result_envelope_written",
            exception_type=None,
            model_receipt_written=True,
            transport_receipt_written=True,
            result_envelope_written=True,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
