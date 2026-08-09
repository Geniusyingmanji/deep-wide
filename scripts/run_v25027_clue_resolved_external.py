#!/usr/bin/env python3
"""Run the single authorized V2.50.27 clue-resolved paired forward."""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25025_evidence_conditioned_paired_runtime as runtime  # noqa: E402
from deepwide_agent import v25027_clue_resolved_external_contract as contract  # noqa: E402
from scripts import run_v24997_shared_first_wave_external as engine  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def configure() -> None:
    engine.contract = contract
    engine.runtime = runtime


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, engine._read(contract.PROTOCOL))
    start = engine._read(contract.EXECUTION_START)
    if (
        start.get("role") != "v25027_clue_resolved_external_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or start.get("arm_order_vector_sha256")
        != protocol["population"]["arm_order_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization")
        != {
            "one_external_forward": True,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        }
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.27 execution start drifted")
    return protocol, start


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    arm_metrics = {
        arm: {
            name: sum(
                int(row["content_free_receipt"]["arm_metrics"][arm][name])
                for row in rows
            )
            for name in (
                "executed_queries", "fetch_attempts", "usable_pages",
                "query_local_results", "retained_records", "evidence_characters",
            )
        }
        for arm in contract.ARMS
    }
    resolved = [
        runtime.reachability.validate_receipt(
            row["content_free_receipt"]["resolved_schema_reachability_receipt"]
        )
        for row in rows
    ]
    return {
        "terminal_tasks": len(rows),
        "refinement_model_call_attempted_tasks": sum(
            row["content_free_receipt"]["refinement_model_call_attempted"]
            for row in rows
        ),
        "refinement_strategy_applied_tasks": sum(
            row["content_free_receipt"]["refinement_strategy_applied"]
            for row in rows
        ),
        "query_vectors_differ_only_in_second_wave_tasks": sum(
            row["content_free_receipt"]["query_vectors_differ_only_in_second_wave"]
            for row in rows
        ),
        "shared_prefix_byte_equal_tasks": sum(
            row["content_free_receipt"]["shared_prefix_byte_equal_between_arms"]
            for row in rows
        ),
        "candidate_resolved_schema_pages": sum(
            item["candidate_resolved_schema_page_count"] for item in resolved
        ),
        "control_resolved_schema_pages": sum(
            item["control_resolved_schema_page_count"] for item in resolved
        ),
        "tasks_with_candidate_resolved_schema_strict_advantage": sum(
            item["candidate_resolved_schema_page_strict_advantage"]
            for item in resolved
        ),
        "both_arms_model_success_tasks": sum(
            all(row["model_success"].values()) for row in rows
        ),
        "prediction_changed_tasks": sum(row["prediction_changed"] for row in rows),
        "all_tasks_execute_at_most_six_physical_queries": all(
            row["content_free_receipt"]["physical_query_count"] <= 6 for row in rows
        ),
        "all_tasks_fetch_at_most_fourteen_physical_pages": all(
            row["content_free_receipt"]["physical_fetch_count"] <= 14 for row in rows
        ),
        "all_tasks_use_at_most_four_physical_model_calls": all(
            row["content_free_receipt"]["model_logical_call_count"] <= 4
            and row["content_free_receipt"]["model_provider_request_count"] <= 4
            for row in rows
        ),
        "arms": arm_metrics,
    }


def run_forward() -> dict[str, Any]:
    configure()
    engine._clean_pushed()
    protocol, start = _validate_start()
    future = (
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT, contract.EVALUATOR, contract.EVALUATOR_MAPPING,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.27 forward or evaluator surface is not pristine")
    if protocol["execution"]["protected_watchers"] != contract.watcher_snapshot():
        raise RuntimeError("V2.50.27 protected watcher identity drifted")
    engine.validate_search_class()
    tasks = contract.task_vector()
    orders = contract.arm_order_vector()
    engine._prepare_output()
    started = time.monotonic()
    results: list[dict[str, Any] | None] = [None] * len(tasks)
    with acquire_deepwide_api_lease(
        ROOT, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(engine._task, index, task, orders[index]): index
                for index, task in enumerate(tasks)
            }
            for future in as_completed(futures):
                index = futures[future]
                results[index] = future.result()
    rows = [runtime.validate_result(item) for item in results if item is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.27 terminal task denominator drifted")
    engine._publish_jsonl(ROOT / contract.TASK_RESULTS, rows)
    prediction_hashes = [
        {arm: contract.payload_sha256(row["predictions"][arm]) for arm in contract.ARMS}
        for row in rows
    ]
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25027_clue_resolved_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "task_results_sha256": contract.sha256(ROOT / contract.TASK_RESULTS),
            "prediction_hash_vector_sha256": contract.payload_sha256(prediction_hashes),
            "all_predictions_terminal_before_mapping_gold_evaluator_or_quality_decision": True,
            "mapping_module_present_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    engine._publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25027_clue_resolved_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
            "task_results_sha256": contract.sha256(ROOT / contract.TASK_RESULTS),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "aggregate": _aggregate(rows),
            "all_predictions_terminal_before_mapping_gold_evaluator_or_quality_decision": True,
            "mapping_module_present_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "authorization": {
                "forward_audit": True,
                "evaluator": False,
                "public_exact220_or_sota": False,
                "retry_resume_selective_rerun": False,
            },
        },
        "result_payload_sha256",
    )
    engine._publish_json(ROOT / contract.FORWARD_RESULT, value)
    return value


def main() -> None:
    value = run_forward()
    print(json.dumps({
        "path": str(contract.FORWARD_RESULT),
        "aggregate": value["aggregate"],
        "wall_seconds": value["wall_seconds"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
