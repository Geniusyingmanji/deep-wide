#!/usr/bin/env python3
"""Prepare and summarize one frozen, sharded DeepWide full-set rollout.

The prepare phase is evaluator-side and must run only after every shard has a
terminal ``run_summary.json``.  It verifies an exact, disjoint task partition,
joins opaque IDs to evaluator instance IDs, and exports only completed forward
predictions to the released evaluator.  The summarize phase restores every
forward/evaluator failure to the denominator as an explicit zero diagnostic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_EVALUATOR_ROOT = (
    ROOT
    / "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch"
)


METRICS = (
    "score",
    "entity_acc",
    "precision_by_row",
    "recall_by_row",
    "f1_by_row",
    "precision_by_item",
    "recall_by_item",
    "f1_by_item",
    "column_precision",
    "column_recall",
    "column_f1",
)

COST_FIELDS = (
    "model_calls",
    "model_successful_calls",
    "model_failed_calls",
    "model_attempts",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "search_calls",
    "search_failures",
    "search_tool_calls",
    "search_fetch_calls",
    "search_fetch_failures",
    "search_input_tokens",
    "search_output_tokens",
    "search_total_tokens",
    "system_total_tokens",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def read_ids(path: Path) -> list[str]:
    values = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate opaque IDs in {path}")
    return values


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _valid_sha256(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _manifest_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _live_evaluator_source_manifest_sha256() -> str:
    paths = sorted(
        path
        for path in (OFFICIAL_EVALUATOR_ROOT / "eval").rglob("*.py")
        if path.is_file()
    )
    rows = [
        {
            "path": str(path.relative_to(OFFICIAL_EVALUATOR_ROOT)),
            "sha256": sha256_file(path),
        }
        for path in paths
    ]
    adapter = ROOT / "scripts/run_official_eval_local.py"
    rows.append(
        {
            "path": "local_adapter/run_official_eval_local.py",
            "sha256": sha256_file(adapter),
        }
    )
    return _manifest_digest(rows)


def _live_answer_corpus_manifest_sha256(root: Path) -> str:
    rows = [
        {"path": path.name, "sha256": sha256_file(path)}
        for path in sorted(path for path in root.glob("*.csv") if path.is_file())
    ]
    return _manifest_digest(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(
        path,
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
    )


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def parse_named_paths(values: list[str], flag: str) -> list[tuple[str, Path]]:
    output: list[tuple[str, Path]] = []
    names: set[str] = set()
    for value in values:
        if "=" not in value:
            raise ValueError(f"{flag} must use NAME=PATH: {value}")
        name, raw_path = value.split("=", 1)
        name = name.strip()
        if not name or name in names:
            raise ValueError(f"invalid or duplicate {flag} name: {name!r}")
        names.add(name)
        output.append((name, Path(raw_path)))
    return output


def _unique_by(
    rows: list[dict[str, Any]], key: str, source: Path
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key, ""))
        if not value:
            raise ValueError(f"row without {key} in {source}")
        if value in output:
            raise ValueError(f"duplicate {key}={value} in {source}")
        output[value] = row
    return output


def prepare_rollout(
    *,
    manifest_rows: list[dict[str, Any]],
    mapping_rows: list[dict[str, Any]],
    shards: list[tuple[str, list[str], list[dict[str, Any]], dict[str, Any]]],
    rollout_id: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if rollout_id not in {1, 2, 3, 4}:
        raise ValueError("rollout_id must be 1..4")
    manifest = _unique_by(manifest_rows, "opaque_id", Path("manifest"))
    mapping = _unique_by(mapping_rows, "opaque_id", Path("mapping"))

    all_ids: list[str] = []
    joined: list[dict[str, Any]] = []
    shard_reports: list[dict[str, Any]] = []
    for name, task_ids, runtime_rows, run_summary in shards:
        overlap = sorted(set(all_ids).intersection(task_ids))
        if overlap:
            raise ValueError(f"shards overlap at {overlap[:3]}")
        all_ids.extend(task_ids)
        runtime = _unique_by(runtime_rows, "opaque_id", Path(name))
        if set(runtime) != set(task_ids):
            missing = sorted(set(task_ids) - set(runtime))
            extra = sorted(set(runtime) - set(task_ids))
            raise ValueError(
                f"{name} runtime/ID mismatch: missing={missing[:3]} extra={extra[:3]}"
            )
        selected = int(run_summary.get("selected", -1))
        completed = int(run_summary.get("completed", -1))
        failed = int(run_summary.get("failed", -1))
        if selected != len(task_ids) or completed + failed != len(task_ids):
            raise ValueError(f"{name} run summary is not terminal or count-complete")

        status_counts: Counter[str] = Counter()
        trace_complete = 0
        for opaque_id in task_ids:
            if opaque_id not in manifest or opaque_id not in mapping:
                raise ValueError(f"{name} opaque ID lacks manifest/mapping: {opaque_id}")
            run = runtime[opaque_id]
            status = str(run.get("status", ""))
            if status not in {"completed", "failed"}:
                raise ValueError(f"non-terminal runtime status for {opaque_id}: {status}")
            prediction = str(run.get("prediction", ""))
            if status == "completed" and not prediction.strip():
                raise ValueError(f"completed task lacks prediction: {opaque_id}")
            status_counts[status] += 1
            process_cost = run.get("process_model_cost") or {}
            if process_cost.get("trace_complete") is True:
                trace_complete += 1
            split = str(mapping[opaque_id].get("split", ""))
            if name.startswith("test") and split != "test":
                raise ValueError(f"test shard contains split={split}: {opaque_id}")
            if name == "devval" and split not in {"dev", "validation"}:
                raise ValueError(f"devval shard contains split={split}: {opaque_id}")
            joined.append(
                {
                    **run,
                    "instance_id": str(mapping[opaque_id]["instance_id"]),
                    "evaluation_group": name,
                    "evaluator_split": split,
                }
            )
        if status_counts["completed"] != completed or status_counts["failed"] != failed:
            raise ValueError(f"{name} runtime rows disagree with run summary")
        shard_reports.append(
            {
                "name": name,
                "selected": len(task_ids),
                "completed": completed,
                "failed": failed,
                "process_trace_complete_tasks": trace_complete,
            }
        )

    if len(all_ids) != len(set(all_ids)):
        raise AssertionError("partition uniqueness check failed")
    official: list[dict[str, Any]] = []
    for run in joined:
        if run["status"] != "completed":
            continue
        opaque_id = str(run["opaque_id"])
        question = str(manifest[opaque_id]["question"])
        prediction = str(run["prediction"])
        official.append(
            {
                "instance_id": run["instance_id"],
                "question": question,
                "rollout_id": rollout_id,
                "prediction": prediction,
                "messages": [
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": prediction},
                ],
            }
        )
    attestation = {
        "artifact_version": 1,
        "phase": "post_terminal_evaluator_side_prepare",
        "rollout_id": rollout_id,
        "selected": len(joined),
        "completed_predictions_exported": len(official),
        "forward_failures_not_exported": len(joined) - len(official),
        "partition_unique": True,
        "all_shards_terminal_before_mapping_join": True,
        "shards": shard_reports,
        "claims": {
            "single_rollout": True,
            "avg_at_4": False,
            "leaderboard_or_sota": False,
            "entropy_or_credit_policy_effect": False,
        },
    }
    return joined, official, attestation


def _metric_means(rows: list[dict[str, Any]], denominator: int) -> dict[str, float]:
    if denominator <= 0:
        return {name: 0.0 for name in METRICS}
    return {
        name: sum(float(row.get(name, 0.0) or 0.0) for row in rows) / denominator
        for name in METRICS
    }


def _cost_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals = {
        name: sum(float((row.get("cost") or {}).get(name, 0.0) or 0.0) for row in rows)
        for name in COST_FIELDS
    }
    totals["wall_seconds_sum"] = sum(
        float(row.get("elapsed_seconds", 0.0) or 0.0) for row in rows
    )
    return totals


def summarize_rollout(
    outcomes: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    *,
    rollout_id: int = 1,
) -> dict[str, Any]:
    if rollout_id not in {1, 2, 3, 4}:
        raise ValueError("rollout_id must be 1..4")
    runtime = _unique_by(outcomes, "opaque_id", Path("terminal outcomes"))
    evaluations = _unique_by(eval_rows, "instance_id", Path("evaluator results"))
    completed_instance_ids = {
        str(row["instance_id"])
        for row in outcomes
        if row.get("status") == "completed"
    }
    unknown_eval = sorted(set(evaluations) - completed_instance_ids)
    missing_eval = sorted(completed_instance_ids - set(evaluations))
    if unknown_eval or missing_eval:
        raise ValueError(
            "evaluator coverage mismatch: "
            f"missing={missing_eval[:3]} unknown={unknown_eval[:3]}"
        )

    per_task: list[dict[str, Any]] = []
    for run in outcomes:
        instance_id = str(run["instance_id"])
        evaluation = evaluations.get(instance_id)
        evaluator_valid = bool(evaluation and not evaluation.get("error"))
        if evaluator_valid:
            for name in METRICS:
                value = evaluation.get(name)
                if not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
                    raise ValueError(f"invalid evaluator metric {name} for {instance_id}")
        per_task.append(
            {
                "opaque_id": run["opaque_id"],
                "instance_id": instance_id,
                "split": run["evaluator_split"],
                "shard": run["evaluation_group"],
                "runtime_status": run.get("status"),
                "runtime_error": run.get("error"),
                "evaluator_valid": evaluator_valid,
                "evaluator_error": None
                if evaluator_valid
                else (evaluation or {}).get("error", "not_run_forward_failure"),
                "metrics": {
                    name: float((evaluation or {}).get(name, 0.0) or 0.0)
                    if evaluator_valid
                    else 0.0
                    for name in METRICS
                },
                "evidence_count": int(run.get("evidence_count", 0) or 0),
                "cost": run.get("cost") or {},
                "elapsed_seconds": float(run.get("elapsed_seconds", 0.0) or 0.0),
                "process_trace_complete": bool(
                    (run.get("process_model_cost") or {}).get("trace_complete")
                ),
            }
        )

    selectors = {
        "test_156": lambda row: row["split"] == "test",
        "dev_24": lambda row: row["split"] == "dev",
        "validation_40": lambda row: row["split"] == "validation",
        "dev_validation_64": lambda row: row["split"] in {"dev", "validation"},
        "all_220": lambda row: True,
    }
    groups: dict[str, Any] = {}
    for name, selector in selectors.items():
        selected = [row for row in per_task if selector(row)]
        valid_metrics = [row["metrics"] for row in selected if row["evaluator_valid"]]
        n = len(selected)
        valid_n = len(valid_metrics)
        groups[name] = {
            "selected": n,
            "runtime_completed": sum(row["runtime_status"] == "completed" for row in selected),
            "runtime_failed": sum(row["runtime_status"] == "failed" for row in selected),
            "evaluator_valid": valid_n,
            "evaluator_invalid_or_not_run": n - valid_n,
            "process_trace_complete_tasks": sum(
                row["process_trace_complete"] for row in selected
            ),
            "completed_valid_only": {
                "denominator": valid_n,
                **_metric_means(valid_metrics, valid_n),
            },
            "conservative_all_selected": {
                "denominator": n,
                "failure_policy": (
                    "forward failure, missing prediction, or evaluator error counts as zero"
                ),
                **_metric_means(valid_metrics, n),
            },
            "cost_totals": _cost_totals(
                [runtime[str(row["opaque_id"])] for row in selected]
            ),
        }

    status = (
        "public_fullset_single_rollout_complete_not_avg_at_4_not_sota"
        if rollout_id == 1
        else (
            f"public_fullset_rollout_{rollout_id}_complete_"
            "historically_dependent_paired_eligible_not_avg_at_4_not_sota"
        )
    )
    return {
        "artifact_version": 1,
        "rollout_id": rollout_id,
        "status": status,
        "groups": groups,
        "claims": {
            "public_tasks_covered": len(per_task),
            "execution_cold_start": True,
            "current_v2_cold_start_internal_test": rollout_id == 1,
            "historically_unseen_or_strict_held_out": False,
            "dev_validation_independent": False,
            "paired_quality_comparison_eligible": rollout_id >= 2,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota": False,
            "entropy_or_credit_policy_effect": False,
        },
        "per_task": per_task,
    }


def validate_prepare_attestation(
    prepare_path: Path, outcomes_path: Path
) -> dict[str, Any]:
    """Validate and project the terminal forward provenance into the result.

    This runs evaluator-side after every forward outcome is terminal.  It
    verifies the exact source files used by ``prepare`` without opening task
    questions or gold beyond what that already-completed evaluator phase did.
    The returned projection contains paths, hashes, and aggregate counts only.
    """

    value = json.loads(prepare_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("prepare attestation must be a JSON object")
    if value.get("artifact_version") != 1:
        raise ValueError("unexpected prepare attestation version")
    if value.get("phase") != "post_terminal_evaluator_side_prepare":
        raise ValueError("unexpected prepare attestation phase")
    rollout_id = value.get("rollout_id")
    if rollout_id not in {1, 2, 3, 4}:
        raise ValueError("invalid prepare rollout_id")
    selected = value.get("selected")
    completed = value.get("completed_predictions_exported")
    failed = value.get("forward_failures_not_exported")
    if (
        selected != 220
        or not isinstance(completed, int)
        or not isinstance(failed, int)
        or completed < 0
        or failed < 0
        or completed + failed != selected
    ):
        raise ValueError("prepare attestation is not an exact terminal 220 partition")
    if value.get("partition_unique") is not True:
        raise ValueError("prepare attestation partition is not unique")
    if value.get("all_shards_terminal_before_mapping_join") is not True:
        raise ValueError("prepare attestation lacks terminal-before-mapping proof")
    outcomes_sha = sha256_file(outcomes_path)
    if value.get("terminal_outcomes_sha256") != outcomes_sha:
        raise ValueError("terminal outcomes drifted after prepare")

    official_path = prepare_path.parent / "official_predictions.jsonl"
    if not official_path.is_file():
        raise ValueError("prepared official predictions are missing")
    official_sha = sha256_file(official_path)
    if value.get("official_predictions_sha256") != official_sha:
        raise ValueError("official predictions drifted after prepare")

    shards = value.get("shards")
    inputs = value.get("inputs")
    if not isinstance(shards, list) or not isinstance(inputs, list):
        raise ValueError("prepare attestation lacks shard provenance")
    shard_by_name: dict[str, dict[str, Any]] = {}
    for row in shards:
        if not isinstance(row, dict):
            raise ValueError("invalid prepare shard entry")
        name = row.get("name")
        if not isinstance(name, str) or not name or name in shard_by_name:
            raise ValueError("invalid or duplicate prepare shard name")
        raw_selected = row.get("selected")
        raw_completed = row.get("completed")
        raw_failed = row.get("failed")
        if not all(
            isinstance(item, int) and not isinstance(item, bool) and item >= 0
            for item in (raw_selected, raw_completed, raw_failed)
        ) or raw_completed + raw_failed != raw_selected:
            raise ValueError("prepare shard is not terminal")
        shard_by_name[name] = row
    if sum(row["selected"] for row in shard_by_name.values()) != 220:
        raise ValueError("prepare shard counts do not cover 220 tasks")

    projected: list[dict[str, Any]] = []
    seen_inputs: set[str] = set()
    for row in inputs:
        if not isinstance(row, dict):
            raise ValueError("invalid prepare input entry")
        name = row.get("name")
        if not isinstance(name, str) or name in seen_inputs or name not in shard_by_name:
            raise ValueError("prepare input/shard names do not match")
        seen_inputs.add(name)
        projected_row: dict[str, Any] = {
            "name": name,
            "selected": shard_by_name[name]["selected"],
            "completed": shard_by_name[name]["completed"],
            "failed": shard_by_name[name]["failed"],
        }
        for label in ("ids", "runtime", "run_summary"):
            raw_path = row.get(label)
            expected_hash = row.get(f"{label}_sha256")
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f"prepare input lacks {label} path")
            if not _valid_sha256(expected_hash):
                raise ValueError(f"prepare input lacks valid {label} hash")
            path = Path(raw_path)
            if not path.is_file() or sha256_file(path) != expected_hash:
                raise ValueError(f"prepare input {label} drifted: {name}")
            projected_row[label] = raw_path
            projected_row[f"{label}_sha256"] = expected_hash
        projected.append(projected_row)
    if set(shard_by_name) != seen_inputs:
        raise ValueError("prepare input/shard partition is incomplete")

    for label in ("manifest", "mapping"):
        raw_path = value.get(label)
        expected_hash = value.get(f"{label}_sha256")
        if not isinstance(raw_path, str) or not raw_path:
            raise ValueError(f"prepare attestation lacks {label} path")
        if not _valid_sha256(expected_hash):
            raise ValueError(f"prepare attestation lacks {label} hash")
        source_path = Path(raw_path)
        if not source_path.is_file() or sha256_file(source_path) != expected_hash:
            raise ValueError(f"prepare {label} drifted")
    return {
        "artifact_version": 1,
        "rollout_id": rollout_id,
        "selected": selected,
        "completed_predictions_exported": completed,
        "forward_failures_not_exported": failed,
        "prepare_attestation_path": str(prepare_path),
        "prepare_attestation_sha256": sha256_file(prepare_path),
        "terminal_outcomes_sha256": outcomes_sha,
        "official_predictions_sha256": official_sha,
        "manifest_sha256": value["manifest_sha256"],
        "mapping_sha256": value["mapping_sha256"],
        "all_shards_terminal_before_mapping_join": True,
        "source_shards": projected,
    }


def validate_evaluator_contract(
    contract_path: Path,
    *,
    expected_predictions_path: Path,
    expected_predictions_sha256: str,
    expected_selected_count: int,
) -> dict[str, Any]:
    value = json.loads(contract_path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("artifact_version") != 2
        or value.get("role")
        != "deepwide_official_evaluator_crash_recovery_contract"
        or value.get("selected_prediction_count") != expected_selected_count
    ):
        raise ValueError("official evaluator run contract is missing or invalid")
    predictions = value.get("predictions")
    if (
        not isinstance(predictions, dict)
        or predictions.get("sha256") != expected_predictions_sha256
        or Path(str(predictions.get("path", ""))).resolve()
        != expected_predictions_path.resolve()
        or not expected_predictions_path.is_file()
        or sha256_file(expected_predictions_path) != expected_predictions_sha256
    ):
        raise ValueError("official evaluator run contract uses different predictions")
    evaluator_source = value.get("evaluator_source")
    query_data = value.get("query_data")
    answers = value.get("answers")
    judge = value.get("judge")
    recovery = value.get("recovery_policy")
    for label, candidate, hash_key in (
        ("evaluator source", evaluator_source, "manifest_sha256"),
        ("query data", query_data, "sha256"),
        ("answer corpus", answers, "manifest_sha256"),
    ):
        digest = candidate.get(hash_key) if isinstance(candidate, dict) else None
        if not _valid_sha256(digest):
            raise ValueError(f"official evaluator {label} hash is invalid")
    query_path = Path(str(query_data.get("path", ""))).resolve()
    answer_root = Path(str(answers.get("root", ""))).resolve()
    if not query_path.is_file() or sha256_file(query_path) != query_data["sha256"]:
        raise ValueError("official evaluator query data drifted")
    if (
        not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root)
        != answers["manifest_sha256"]
    ):
        raise ValueError("official evaluator answer corpus drifted")
    if (
        _live_evaluator_source_manifest_sha256()
        != evaluator_source["manifest_sha256"]
    ):
        raise ValueError("official evaluator source drifted")
    if (
        not isinstance(judge, dict)
        or not isinstance(judge.get("proxy_url"), str)
        or not isinstance(judge.get("model"), str)
        or not isinstance(judge.get("reasoning_effort"), str)
        or not isinstance(judge.get("max_output_tokens"), int)
        or not isinstance(judge.get("timeout_seconds"), int)
        or not isinstance(judge.get("max_retries"), int)
    ):
        raise ValueError("official evaluator judge contract is invalid")
    if recovery != {
        "explicit_resume_required": True,
        "committed_success_or_error_is_terminal": True,
        "committed_rows_must_be_exact_prediction_prefix": True,
        "canonical_result_file_atomic_replace_per_task": True,
        "selective_error_retry_allowed": False,
    }:
        raise ValueError("official evaluator recovery contract is invalid")
    order_sha = value.get("selected_instance_order_sha256")
    if not _valid_sha256(order_sha):
        raise ValueError("official evaluator instance-order hash is invalid")
    return {
        "run_contract_path": str(contract_path),
        "run_contract_sha256": sha256_file(contract_path),
        "evaluator_source_manifest_sha256": evaluator_source[
            "manifest_sha256"
        ],
        "query_data_sha256": query_data["sha256"],
        "answer_corpus_manifest_sha256": answers["manifest_sha256"],
        "judge": judge,
        "selected_prediction_count": expected_selected_count,
        "selected_instance_order_sha256": order_sha,
        "recovery_policy": recovery,
    }


def prepare_main(args: argparse.Namespace) -> None:
    ids = parse_named_paths(args.ids, "--ids")
    runtimes = dict(parse_named_paths(args.runtime, "--runtime"))
    summaries = dict(parse_named_paths(args.run_summary, "--run-summary"))
    if set(runtimes) != {name for name, _ in ids} or set(summaries) != set(runtimes):
        raise ValueError("--ids, --runtime, and --run-summary names must match")
    shards = []
    inputs: list[dict[str, Any]] = []
    for name, ids_path in ids:
        runtime_path = runtimes[name]
        summary_path = summaries[name]
        shards.append(
            (
                name,
                read_ids(ids_path),
                read_jsonl(runtime_path),
                json.loads(summary_path.read_text(encoding="utf-8")),
            )
        )
        inputs.append(
            {
                "name": name,
                "ids": str(ids_path),
                "ids_sha256": sha256_file(ids_path),
                "runtime": str(runtime_path),
                "runtime_sha256": sha256_file(runtime_path),
                "run_summary": str(summary_path),
                "run_summary_sha256": sha256_file(summary_path),
            }
        )
    manifest_path = Path(args.manifest)
    mapping_path = Path(args.mapping)
    joined, official, attestation = prepare_rollout(
        manifest_rows=read_jsonl(manifest_path),
        mapping_rows=read_jsonl(mapping_path),
        shards=shards,
        rollout_id=args.rollout_id,
    )
    out_dir = Path(args.out_dir)
    joined_path = out_dir / "terminal_outcomes_evaluator_joined.jsonl"
    official_path = out_dir / "official_predictions.jsonl"
    write_jsonl(joined_path, joined)
    write_jsonl(official_path, official)
    attestation.update(
        {
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "mapping": str(mapping_path),
            "mapping_sha256": sha256_file(mapping_path),
            "inputs": inputs,
            "terminal_outcomes_sha256": sha256_file(joined_path),
            "official_predictions_sha256": sha256_file(official_path),
        }
    )
    _atomic_text(
        out_dir / "prepare_attestation.json",
        json.dumps(attestation, ensure_ascii=False, indent=2) + "\n",
    )
    print(json.dumps(attestation, ensure_ascii=False))


def summarize_main(args: argparse.Namespace) -> None:
    outcomes_path = Path(args.terminal_outcomes)
    eval_path = Path(args.eval_results)
    prepare_path = (
        Path(args.prepare_attestation)
        if args.prepare_attestation
        else outcomes_path.parent / "prepare_attestation.json"
    )
    provenance = validate_prepare_attestation(
        prepare_path, outcomes_path
    )
    summary = summarize_rollout(
        read_jsonl(outcomes_path),
        read_jsonl(eval_path),
        rollout_id=int(provenance["rollout_id"]),
    )
    summary["terminal_outcomes_sha256"] = sha256_file(outcomes_path)
    summary["eval_results_sha256"] = sha256_file(eval_path)
    evaluator_contract_path = eval_path.parent / "run_config.json"
    summary["evaluator_provenance"] = validate_evaluator_contract(
        evaluator_contract_path,
        expected_predictions_path=prepare_path.parent
        / "official_predictions.jsonl",
        expected_predictions_sha256=provenance[
            "official_predictions_sha256"
        ],
        expected_selected_count=provenance[
            "completed_predictions_exported"
        ],
    )
    summary["rollout_provenance"] = provenance
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _atomic_text(
        output,
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    )
    print(json.dumps({"output": str(output), **summary["groups"]["all_220"]}))


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("--manifest", required=True)
    prepare.add_argument("--mapping", required=True)
    prepare.add_argument("--ids", action="append", required=True)
    prepare.add_argument("--runtime", action="append", required=True)
    prepare.add_argument("--run-summary", action="append", required=True)
    prepare.add_argument("--rollout-id", type=int, default=1)
    prepare.add_argument("--out-dir", required=True)
    prepare.set_defaults(handler=prepare_main)

    summarize = subparsers.add_parser("summarize")
    summarize.add_argument("--terminal-outcomes", required=True)
    summarize.add_argument("--eval-results", required=True)
    summarize.add_argument(
        "--prepare-attestation",
        default="",
        help="defaults to prepare_attestation.json beside terminal outcomes",
    )
    summarize.add_argument("--output", required=True)
    summarize.set_defaults(handler=summarize_main)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
