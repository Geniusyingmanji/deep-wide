#!/usr/bin/env python3
"""Finalize V2.48.66 after the post-forward aggregate-only crash.

This recovery consumes the already frozen 220 task directories and the
already written 220-row runtime prediction file.  It performs no process,
model, search, fetch, retry, resume, task rerun, or evaluator effect.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24866_coverage_revision_exact220_contract as contract  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402
from scripts import run_v24866_coverage_revision_exact220 as runner  # noqa: E402


def main() -> None:
    protocol = runner._read(ROOT / contract.PROTOCOL)
    unsigned_protocol = dict(protocol)
    seal = unsigned_protocol.pop("protocol_payload_sha256", None)
    if (
        protocol.get("role") != contract.ROLE
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or seal != contract.payload_sha256(unsigned_protocol)
        or protocol.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or protocol.get("task_contract", {}).get("selected_count") != 220
    ):
        raise RuntimeError("V2.48.66 frozen protocol recovery barrier drifted")
    rows = [
        json.loads(line)
        for line in (ROOT / contract.RUNTIME_PREDICTIONS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    tasks = contract.task_vector(ROOT, protocol)
    if (
        len(rows) != 220
        or [row.get("opaque_id") for row in rows]
        != [task["opaque_id"] for task in tasks]
        or any(
            row.get("status") != "completed"
            or row.get("label_blind") is not True
            or not isinstance(row.get("prediction"), str)
            or not row["prediction"]
            for row in rows
        )
        or any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (
                contract.RUN_SUMMARY,
                contract.PREDICTION_FREEZE,
                contract.FORWARD_RESULT,
            )
        )
    ):
        raise RuntimeError("V2.48.66 frozen forward recovery barrier drifted")

    accepted = 0
    valid_model = valid_transport = valid_single = valid_backfill = 0
    acquisitions = slot_timeouts = 0
    completion: dict[str, int] = {}
    parent_taxonomy: dict[str, int] = {}
    model_generated = {
        "primary",
        "repaired",
        "normalized_primary",
        "normalized_repaired",
    }
    control_outcomes = []
    for position, row in enumerate(rows, 1):
        directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
        gate = runner._read(directory / "coverage_parent_bundle_receipt.json")
        base = runner._read(directory / "base_parent_exit_receipt.json")
        disposition = str(gate["disposition"])
        taxonomy = str(base["failure_taxonomy"])
        parent_taxonomy[taxonomy] = parent_taxonomy.get(taxonomy, 0) + 1
        if disposition == "success":
            runner._validate_bundle({}, directory)
            envelope = runner.validate_envelope(
                runner._read(directory / "result.json")
            )
            control_outcomes.append(SimpleNamespace(result=envelope["result"]))
            accepted += 1
            model = runner.validate_model(
                runner._read(directory / runner.FINAL_MODEL_NAME),
                expected_cap=contract.MODEL_SLOT_CAP,
            )
            acquisitions += int(model["acquisitions"])
            slot_timeouts += int(model["slot_timeouts"])
            valid_model += 1
            runner.validate_transport_health(
                runner._read(directory / runner.TRANSPORT_NAME)
            )
            valid_transport += 1
            runner.algorithm.validate_single(
                runner._read(directory / runner.SINGLE_NAME)
            )
            valid_single += 1
            runner.algorithm.validate_backfill(
                runner._read(directory / runner.BACKFILL_NAME)
            )
            valid_backfill += 1
        else:
            control_outcomes.append(SimpleNamespace(result={}))
        kind = str(row["completion_kind"])
        completion[kind] = completion.get(kind, 0) + 1

    slot_mtimes = [
        path.stat().st_mtime_ns
        for path in (ROOT / contract.MODEL_SLOT_DIRECTORY).glob("slot_*.lock")
    ]
    if len(slot_mtimes) != contract.MODEL_SLOT_CAP:
        raise RuntimeError("V2.48.66 recovery model-slot start boundary drifted")
    forward_wall = round(
        max(
            0,
            (ROOT / contract.RUNTIME_PREDICTIONS).stat().st_mtime_ns
            - min(slot_mtimes),
        )
        / 1_000_000_000,
        6,
    )
    control_totals = runner._fixed_full_budget_totals(control_outcomes)
    summary = {
        "artifact_version": 1,
        "role": "v24866_coverage_revision_exact220_run_summary",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": 220,
        "completed": 220,
        "failed": 0,
        "model_generated_tables": sum(
            row["completion_kind"] in model_generated for row in rows
        ),
        "fallback_tables": sum(
            row["completion_kind"] not in model_generated for row in rows
        ),
        "completion_kinds": dict(sorted(completion.items())),
        "system_total_tokens": sum(
            int(row["cost"]["system_total_tokens"]) for row in rows
        ),
        "model_requests": sum(
            int(row["cost"]["model_calls"]) for row in rows
        ),
        "model_attempts": sum(
            int(row["cost"]["model_attempts"]) for row in rows
        ),
        "search_calls": sum(
            int(row["cost"]["search_calls"]) for row in rows
        ),
        "search_fetch_calls": sum(
            int(row["cost"]["search_fetch_calls"]) for row in rows
        ),
        "task_wall_sum_seconds": round(
            sum(float(row["elapsed_seconds"]) for row in rows), 6
        ),
        "forward_wall_seconds": forward_wall,
        "parent_exit_taxonomy": dict(sorted(parent_taxonomy.items())),
        "accepted_parent_successes": accepted,
        "model_receipts_present": valid_model,
        "valid_model_receipts": valid_model,
        "valid_transport_receipts": valid_transport,
        "valid_single_shot_receipts": valid_single,
        "valid_backfill_receipts": valid_backfill,
        "model_slot_acquisitions": acquisitions,
        "model_slot_timeouts": slot_timeouts,
        "backfill_totals": {},
        "transport_totals": {},
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "direct_search_totals": runner._direct_search_totals(ROOT),
        "coverage_revision_totals": runner._coverage_totals(ROOT),
        "fixed_full_budget_control_totals": control_totals,
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "postforward_recovery": {
            "reason": "aggregate_field_name_keyerror_after_runtime_predictions_write",
            "model_search_fetch_retry_resume_rerun_or_evaluator_effect": False,
            "runtime_prediction_bytes_changed": False,
        },
    }
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    algorithm._new_json(ROOT / contract.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24866_coverage_revision_exact220_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": 220,
        "terminal": 220,
        "runtime_predictions_sha256": contract.sha256(
            ROOT / contract.RUNTIME_PREDICTIONS
        ),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "prediction_hashes_sha256": contract.payload_sha256(
            [row["prediction_sha256"] for row in rows]
        ),
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    algorithm._new_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    start = runner._read(ROOT / contract.EXECUTION_START)
    forward = {
        "artifact_version": 1,
        "role": "v24866_coverage_revision_exact220_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(__import__("time").time()),
        "selected": 220,
        "terminal_predictions": 220,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "direct_search_totals": summary["direct_search_totals"],
        "fixed_full_budget_control_totals": summary[
            "fixed_full_budget_control_totals"
        ],
        "coverage_revision_totals": summary["coverage_revision_totals"],
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "execution_start_sha256": contract.sha256(
            ROOT / contract.EXECUTION_START
        ),
        "execution_start_payload_sha256": start[
            "execution_start_payload_sha256"
        ],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "official_evaluator_called": False,
        "retry_resume_skip_or_selective_rerun_launched": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    algorithm._new_json(ROOT / contract.FORWARD_RESULT, forward)
    print(json.dumps({"terminal": 220, "accepted": accepted}, sort_keys=True))


if __name__ == "__main__":
    main()
