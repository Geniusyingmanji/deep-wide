#!/usr/bin/env python3
"""Aggregate-only failure-surface diagnosis of frozen V2.48.00.

The exact-220 forward and evaluator are already terminal. This script opens
their frozen artifacts only after the prediction barrier, joins rows in
memory, and publishes coarse counts and group aggregates. It emits no task
identifier, question, prediction, answer, query, URL, page, credential, field
name, or per-task metric and performs no remote effect.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24800_exact220_contract as contract  # noqa: E402


OUTPUT = Path("results/v24803_v24800_aggregate_failure_surface_v1_20260807.json")
RUN_ROOT = Path("outputs/v24800_exact220_v1_20260807")
FINAL_RESULT = Path("results/v24800_exact220_result_v1_20260807.json")
POSTAUDIT = Path("results/v24800_exact220_postresult_audit_v1_20260807.json")
FORWARD_AUDIT = Path("results/v24800_exact220_forward_audit_v1_20260807.json")
SUMMARY = RUN_ROOT / "evaluator/conservative_summary.json"
OFFICIAL_ROWS = RUN_ROOT / "evaluator/official_eval_results.jsonl"
RUN_SUMMARY = RUN_ROOT / "run_summary.json"
TASK_ROOT = RUN_ROOT / "tasks"
SELECTED = 220
METRICS = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE_METRICS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
RETRIEVAL_FIELDS = (
    "queries_executed", "fetches_attempted", "usable_pages", "unique_hosts",
    "content_chars",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
INSTANCE = re.compile(r"(?:deep2wide_result|wide2deep_ws)_[^\"\\]+")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.48.03 expected ordinary repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.03 expected JSON object")
    return value


def _jsonl(root: Path, relative: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _ordinary(root, relative).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("V2.48.03 expected JSONL objects")
        rows.append(value)
    return rows


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents(root: Path) -> dict[str, dict[str, Any]]:
    result = _read(root, FINAL_RESULT)
    post = _read(root, POSTAUDIT)
    forward = _read(root, FORWARD_AUDIT)
    summary = _read(root, SUMMARY)
    run_summary = _read(root, RUN_SUMMARY)
    all220 = (result.get("metrics") or {}).get("all_220") or {}
    if (
        result.get("role") != "v24800_exact220_result"
        or result.get("selected") != SELECTED
        or result.get("failure_as_zero") is not True
        or not _sealed(result, "result_payload_sha256")
        or post.get("role") != "v24800_exact220_postresult_audit"
        or post.get("audit_valid") is not True or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or forward.get("role") != "v24800_exact220_forward_audit"
        or forward.get("audit_valid") is not True or forward.get("findings") != []
        or not _sealed(forward, "audit_payload_sha256")
        or post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(root / SUMMARY)
        or result.get("provenance", {}).get("merged_official_eval_results_sha256")
        != contract.sha256(root / OFFICIAL_ROWS)
        or forward.get("run_summary_sha256") != contract.sha256(root / RUN_SUMMARY)
        or all220.get("selected") != SELECTED
        or (summary.get("groups") or {}).get("all_220", {}).get("selected")
        != SELECTED or run_summary.get("selected") != SELECTED
    ):
        raise RuntimeError("V2.48.03 frozen parent chain drifted")
    return {
        "result": result, "post": post, "forward": forward,
        "summary": summary, "run_summary": run_summary,
    }


def _metrics(root: Path) -> dict[str, dict[str, Any]]:
    rows = _read(root, SUMMARY).get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.03 evaluator summary denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id")
        instance_id = row.get("instance_id")
        metrics = row.get("metrics")
        if (
            not isinstance(opaque_id, str) or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output or not isinstance(instance_id, str)
            or not instance_id or not isinstance(metrics, Mapping)
            or not isinstance(row.get("evaluator_valid"), bool)
            or any(
                isinstance(metrics.get(name), bool)
                or not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                or not 0.0 <= float(metrics[name]) <= 1.0 for name in METRICS
            )
        ):
            raise RuntimeError("V2.48.03 evaluator metric row drifted")
        output[opaque_id] = {
            "instance_id": instance_id,
            "evaluator_valid": row["evaluator_valid"],
            "evaluator_error": str(row.get("evaluator_error") or ""),
            "metrics": {name: float(metrics[name]) for name in METRICS},
            "system_total_tokens": int(
                (row.get("cost") or {}).get("system_total_tokens", 0)
            ),
        }
    return output


def _messages(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in _jsonl(root, OFFICIAL_ROWS):
        instance_id = row.get("instance_id")
        if (
            not isinstance(instance_id, str) or not instance_id
            or instance_id in output
            or not isinstance(row.get("error"), (str, type(None)))
            or not isinstance(row.get("msg"), (str, type(None)))
        ):
            raise RuntimeError("V2.48.03 official evaluator row drifted")
        message = str(row.get("msg") or "")
        output[instance_id] = {
            "message_class": (
                "visible_schema_mismatch" if message.startswith("required_columns")
                else "entity_anchor_failure"
                if message.startswith("the entity is wrong") else "other"
            )
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.03 official evaluator denominator drifted")
    return output


def _normalization_status(result: Mapping[str, Any]) -> str:
    events = (result.get("normalization") or {}).get("events") or []
    if not isinstance(events, list) or not events:
        return "absent"
    statuses = [
        str(event.get("status") or "unknown")
        for event in events if isinstance(event, Mapping)
    ]
    return statuses[-1] if statuses else "absent"


def _tasks(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(root, TASK_ROOT / f"task_{position:04d}/result.json")
        result = envelope.get("result") or {}
        opaque_id = result.get("opaque_id")
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        total = receipt.get("total") or {}
        wave2 = receipt.get("wave2") or {}
        schema = result.get("visible_schema") or {}
        if (
            envelope.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ) is not False
            or envelope.get("benchmark_evaluator_called_by_envelope_builder") is not False
            or not isinstance(opaque_id, str) or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output or retrieval.get("status") != "completed"
            or not isinstance(wave2.get("executed"), bool)
            or schema.get("status") not in {
                "applied", "no_unambiguous_visible_schema"
            }
        ):
            raise RuntimeError("V2.48.03 frozen task row drifted")
        output[opaque_id] = {
            **{name: int(total[name]) for name in RETRIEVAL_FIELDS},
            "wave2_executed": wave2["executed"],
            "visible_schema_status": str(schema["status"]),
            "normalization_status": _normalization_status(result),
            "completion_kind": str(result.get("completion_kind") or "unknown"),
        }
    return output


def _failure_class(metric: Mapping[str, Any], message: Mapping[str, Any]) -> str:
    if metric["evaluator_valid"] is not True:
        return (
            "evaluator_out_of_range_metric"
            if "out-of-range" in str(metric["evaluator_error"])
            else "evaluator_internal_error"
        )
    if float(metric["metrics"]["score"]) > 0:
        return "whole_table_success"
    if message["message_class"] == "visible_schema_mismatch":
        return "visible_schema_mismatch"
    if (
        message["message_class"] == "entity_anchor_failure"
        or float(metric["metrics"]["entity_acc"]) == 0.0
    ):
        return "entity_anchor_failure"
    return "partial_quality"


def _aggregate(
    ids: Iterable[str], metrics: Mapping[str, Mapping[str, Any]],
    tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.03 cannot aggregate an empty class")
    means = {
        name: sum(float(metrics[item]["metrics"][name]) for item in selected)
        / len(selected) for name in METRICS
    }
    means["quality_composite"] = sum(
        means[name] for name in COMPOSITE_METRICS
    ) / len(COMPOSITE_METRICS)
    return {
        "n": len(selected),
        "evaluator_valid": sum(
            metrics[item]["evaluator_valid"] is True for item in selected
        ),
        "metrics": means,
        "mean_system_total_tokens": sum(
            int(metrics[item]["system_total_tokens"]) for item in selected
        ) / len(selected),
        "retrieval_means": {
            name: sum(float(tasks[item][name]) for item in selected) / len(selected)
            for name in RETRIEVAL_FIELDS
        },
        "wave2_executed": sum(
            tasks[item]["wave2_executed"] is True for item in selected
        ),
        "visible_schema_status": dict(sorted(Counter(
            tasks[item]["visible_schema_status"] for item in selected
        ).items())),
        "normalization_status": dict(sorted(Counter(
            tasks[item]["normalization_status"] for item in selected
        ).items())),
        "completion_kind": dict(sorted(Counter(
            tasks[item]["completion_kind"] for item in selected
        ).items())),
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parents = _validate_parents(root)
    metrics = _metrics(root)
    messages = _messages(root)
    tasks = _tasks(root)
    ids = set(metrics)
    if ids != set(tasks) or len(ids) != SELECTED:
        raise RuntimeError("V2.48.03 task/evaluator population drifted")
    instance_ids = [str(row["instance_id"]) for row in metrics.values()]
    if (
        len(set(instance_ids)) != SELECTED
        or set(instance_ids) != set(messages)
    ):
        raise RuntimeError("V2.48.03 evaluator join drifted")
    groups: dict[str, set[str]] = defaultdict(set)
    for opaque_id in ids:
        metric = metrics[opaque_id]
        groups[_failure_class(metric, messages[metric["instance_id"]])].add(
            opaque_id
        )
    aggregates = {
        name: _aggregate(members, metrics, tasks)
        for name, members in sorted(groups.items())
    }
    run_summary = parents["run_summary"]
    all220 = parents["result"]["metrics"]["all_220"]
    class_counts = {name: value["n"] for name, value in aggregates.items()}
    value = {
        "artifact_version": 1,
        "role": "v24803_v24800_aggregate_failure_surface",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "frozen_exact220_failure_surface_diagnosed_no_new_forward",
        "parents": {
            "result_sha256": contract.sha256(root / FINAL_RESULT),
            "postresult_audit_sha256": contract.sha256(root / POSTAUDIT),
            "forward_audit_sha256": contract.sha256(root / FORWARD_AUDIT),
            "conservative_summary_sha256": contract.sha256(root / SUMMARY),
            "official_eval_results_sha256": contract.sha256(root / OFFICIAL_ROWS),
            "run_summary_sha256": contract.sha256(root / RUN_SUMMARY),
        },
        "boundary": {
            "post_prediction_freeze_aggregate_only": True,
            "offline_join_uses_opaque_id_and_instance_id_only_in_memory": True,
            "question_prediction_answer_query_url_page_field_name_or_credential_emitted": False,
            "task_identifier_instance_identifier_or_per_task_metric_emitted": False,
            "mapping_answer_category_question_type_or_split_used_for_taxonomy": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_feedback_retry_resume_or_selective_revaluation": False,
            "aggregate_diagnosis_must_not_feed_public_benchmark_runtime_routing": True,
        },
        "denominator": SELECTED,
        "failure_class_counts": class_counts,
        "failure_class_aggregates": aggregates,
        "transport": {
            "provider_attempts": run_summary["direct_search_totals"]["provider_attempts"],
            "successful_queries": run_summary["direct_search_totals"]["successful_queries"],
            "failed_queries": run_summary["direct_search_totals"]["failed_queries"],
            "status_429": run_summary["direct_search_totals"]["status_429"],
            "status_5xx": run_summary["direct_search_totals"]["status_5xx"],
            "slot_timeouts": run_summary["direct_search_totals"]["slot_timeouts"],
            "second_wave_executed_tasks": run_summary[
                "fixed_full_budget_control_totals"
            ]["second_wave_executed_tasks"],
        },
        "reconciliation": {
            "class_counts_sum_to_220": sum(class_counts.values()) == SELECTED,
            "whole_table_success_count_matches_result": class_counts.get(
                "whole_table_success", 0
            ) == all220["whole_table_successes"],
            "evaluator_error_count_matches_result": class_counts.get(
                "evaluator_internal_error", 0
            ) + class_counts.get("evaluator_out_of_range_metric", 0)
            == all220["evaluator_invalid_or_not_run"],
            "second_wave_count_matches_forward": sum(
                task["wave2_executed"] is True for task in tasks.values()
            ) == run_summary["fixed_full_budget_control_totals"][
                "second_wave_executed_tasks"
            ],
        },
        "conclusions": {
            "provider_transport_is_observed_primary_failure_surface": False,
            "official_evaluator_invalidity_is_agent_controllable": False,
            "visible_schema_mismatch_is_a_nonzero_agent_controllable_surface":
                class_counts.get("visible_schema_mismatch", 0) > 0,
            "entity_anchor_failure_is_a_nonzero_agent_controllable_surface":
                class_counts.get("entity_anchor_failure", 0) > 0,
            "fixed_full_budget_causal_superiority_established": False,
            "entropy_or_information_gain_credit_validated": False,
            "failure_class_membership_is_valid_runtime_route_signal": False,
            "public_benchmark_overfitting_risk_remains": True,
            "sota_established": False,
        },
        "next_work": {
            "external_shared_prefix_three_arm_required": True,
            "first_wave_fixed_full_and_coverage_risk_adaptive_arms": True,
            "identity_target_and_source_dependency_gates_before_entropy": True,
            "visible_output_contract_tested_only_on_benchmark_external_tasks": True,
            "evaluator_internal_errors_remain_failure_as_zero_without_selective_retry": True,
            "new_public_exact220_before_external_gate": False,
        },
        "authorization": {
            "benchmark_external_shared_prefix_implementation": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = dict(value["reconciliation"])
    checks.update({
        "expected_failure_classes_present": set(class_counts) == {
            "entity_anchor_failure", "evaluator_internal_error",
            "evaluator_out_of_range_metric", "partial_quality",
            "visible_schema_mismatch", "whole_table_success",
        },
        "parent_postresult_audit_clean": parents["post"]["audit_valid"] is True
        and parents["post"]["findings"] == [],
        "parent_forward_audit_clean": parents["forward"]["audit_valid"] is True
        and parents["forward"]["findings"] == [],
    })
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if (
        OPAQUE.search(encoded) or INSTANCE.search(encoded) or SECRET.search(encoded)
        or "required_columns" in encoded or "the entity is wrong" in encoded
    ):
        raise RuntimeError("V2.48.03 emitted prohibited task-level content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_report(root, value, rebuild=False)


def validate_report(
    root: Path, value: Mapping[str, Any], *, rebuild: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v24803_v24800_aggregate_failure_surface"
        or copied.get("status")
        != "frozen_exact220_failure_surface_diagnosed_no_new_forward"
        or copied.get("denominator") != SELECTED
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization") != {
            "benchmark_external_shared_prefix_implementation": True,
            "new_public_dev64": False, "new_public_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "leaderboard_submission": False, "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.03 aggregate diagnosis drifted")
    if rebuild:
        expected = build_report(root, now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.03 aggregate diagnosis is not reproducible")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    publish(ROOT / OUTPUT, report)
    print(json.dumps({
        "path": str(OUTPUT),
        "failure_class_counts": report["failure_class_counts"],
        "authorization": report["authorization"],
    }, sort_keys=True))
