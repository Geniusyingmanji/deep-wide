#!/usr/bin/env python3
"""Generate and freeze all 220 label-blind consensus predictions once."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24817_consensus_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24816_label_blind_consensus import (  # noqa: E402
    build_consensus,
    symmetric_medoid_fallback,
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.17 expected object")
    return value


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _new_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.17 generation requires clean pushed HEAD")
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    future = (
        contract.OUTPUT_ROOT, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.48.17 generation surface is not pristine")
    if contract.protected_watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.48.17 protected watcher drifted")
    bundle = contract.source_bundle(ROOT)
    tasks = bundle["task_vector"]
    source_maps = [
        {row["opaque_id"]: row for row in source["rows"]}
        for source in bundle["sources"]
    ]
    started = time.monotonic()
    rows = []
    counts: Counter[str] = Counter()
    totals: Counter[str] = Counter()
    for task in tasks:
        predictions = [source[task["opaque_id"]]["prediction"] for source in source_maps]
        try:
            result = build_consensus(task["question"], predictions)
            kind = "strict_consensus"
            receipt = result["receipt"]
            for name in (
                "two_source_supported_output_rows", "medoid_only_rows_preserved",
                "single_source_rows_excluded", "majority_supported_cells",
                "single_known_unknown_fills", "medoid_fallback_cells",
                "unresolved_known_conflict_cells", "output_row_count",
            ):
                totals[name] += int(receipt[name])
        except ValueError:
            result = symmetric_medoid_fallback(task["question"], predictions)
            kind = "symmetric_medoid_fallback"
        prediction = result["prediction"]
        source_matches = sum(prediction == source for source in predictions)
        counts[kind] += 1
        counts["identity_to_a_source"] += int(source_matches > 0)
        counts["novel_prediction"] += int(source_matches == 0)
        rows.append(
            {
                "opaque_id": task["opaque_id"],
                "status": "completed",
                "completion_kind": kind,
                "prediction": prediction,
                "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
                "elapsed_seconds": 0.0,
                "cost": {
                    "model_requests": 0, "model_attempts": 0,
                    "model_input_tokens": 0, "model_output_tokens": 0,
                    "model_total_tokens": 0, "search_calls": 0,
                    "fetch_calls": 0,
                },
                "consensus_result_sha256": result["result_sha256"],
                "source_prediction_sha256": [
                    hashlib.sha256(value.encode()).hexdigest()
                    for value in predictions
                ],
                "label_blind": True,
                "mapping_gold_category_question_type_split_evaluator_score_read": False,
            }
        )
    wall = max(0.0, time.monotonic() - started)
    if len(rows) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.17 generation denominator drifted")
    (ROOT / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True)
    _new_jsonl(ROOT / contract.RUNTIME_PREDICTIONS, rows)
    summary = {
        "artifact_version": 1,
        "role": "v24817_consensus_exact220_run_summary",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "completed": contract.SELECTED_COUNT,
        "failed": 0,
        "source_rollout_count": 3,
        "source_prediction_count": 660,
        "generation_counts": dict(sorted(counts.items())),
        "consensus_totals": dict(sorted(totals.items())),
        "incremental_model_requests": 0,
        "incremental_search_calls": 0,
        "incremental_fetch_calls": 0,
        "postprocess_wall_seconds": round(wall, 6),
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "source_evaluator_result_or_score_file_opened_or_hashed": False,
    }
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    _new_json(ROOT / contract.RUN_SUMMARY, summary)
    row_hashes = [row["prediction_sha256"] for row in rows]
    freeze = {
        "artifact_version": 1,
        "role": "v24817_consensus_exact220_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "terminal": contract.SELECTED_COUNT,
        "runtime_predictions_sha256": contract.sha256(
            ROOT / contract.RUNTIME_PREDICTIONS
        ),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "prediction_hashes_sha256": contract.payload_sha256(row_hashes),
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "source_evaluator_result_or_score_file_opened_or_hashed": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    _new_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24817_consensus_exact220_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "terminal_predictions": contract.SELECTED_COUNT,
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "runtime_predictions_sha256": contract.sha256(
            ROOT / contract.RUNTIME_PREDICTIONS
        ),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "generation_counts": summary["generation_counts"],
        "consensus_totals": summary["consensus_totals"],
        "incremental_model_search_or_fetch_effects": 0,
        "postprocess_wall_seconds": summary["postprocess_wall_seconds"],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "source_evaluator_result_or_score_file_opened_or_hashed": False,
        "official_evaluator_called": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    _new_json(ROOT / contract.FORWARD_RESULT, forward)
    print(json.dumps({"forward": str(contract.FORWARD_RESULT), "summary": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
