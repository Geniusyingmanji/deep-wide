#!/usr/bin/env python3
"""Aggregate-only repeatability diagnosis for two frozen exact-220 rollouts.

V2.48.00 and V2.48.07 execute the same forward algorithm, visible task vector,
model/search budgets, and concurrency on fresh output surfaces.  Both predictions
and evaluations are already frozen.  This script performs an offline opaque-id
join and emits aggregates only: no task identifier, question, prediction, answer,
query, URL, page, credential, or per-task metric is published.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24807_exact220_contract as contract  # noqa: E402


DATE = "20260807"
OUTPUT = Path(f"results/v24808_v24800_v24807_repeatability_diagnosis_v1_{DATE}.json")
OLD_PROTOCOL_ID = "v24800_fixed_full_budget_no_entropy_exact220_v1"
NEW_PROTOCOL_ID = contract.PROTOCOL_ID
OLD_ROOT = Path(f"outputs/v24800_exact220_v1_{DATE}")
NEW_ROOT = contract.OUTPUT_ROOT
OLD_RESULT = Path(f"results/v24800_exact220_result_v1_{DATE}.json")
NEW_RESULT = Path(f"results/v24807_exact220_result_v1_{DATE}.json")
OLD_FORWARD_AUDIT = Path(f"results/v24800_exact220_forward_audit_v1_{DATE}.json")
NEW_FORWARD_AUDIT = Path(f"results/v24807_exact220_forward_audit_v1_{DATE}.json")
OLD_POSTAUDIT = Path(f"results/v24800_exact220_postresult_audit_v1_{DATE}.json")
NEW_POSTAUDIT = Path(f"results/v24807_exact220_postresult_audit_v1_{DATE}.json")
OLD_RUNTIME = OLD_ROOT / "runtime_predictions.jsonl"
NEW_RUNTIME = NEW_ROOT / "runtime_predictions.jsonl"
OLD_SUMMARY = OLD_ROOT / "run_summary.json"
NEW_SUMMARY = NEW_ROOT / "run_summary.json"
OLD_EVAL = OLD_ROOT / "evaluator/conservative_summary.json"
NEW_EVAL = NEW_ROOT / "evaluator/conservative_summary.json"
SELECTED = 220
BOOTSTRAP_SEED = 24808
BOOTSTRAP_RESAMPLES = 20_000
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.48.08 expected ordinary repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.08 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents(root: Path) -> dict[str, dict[str, Any]]:
    old_result = _read(root, OLD_RESULT)
    new_result = _read(root, NEW_RESULT)
    old_forward = _read(root, OLD_FORWARD_AUDIT)
    new_forward = _read(root, NEW_FORWARD_AUDIT)
    old_post = _read(root, OLD_POSTAUDIT)
    new_post = _read(root, NEW_POSTAUDIT)
    if (
        old_result.get("protocol_id") != OLD_PROTOCOL_ID
        or new_result.get("protocol_id") != NEW_PROTOCOL_ID
        or old_result.get("selected") != SELECTED
        or new_result.get("selected") != SELECTED
        or old_result.get("failure_as_zero") is not True
        or new_result.get("failure_as_zero") is not True
        or not _sealed(old_result, "result_payload_sha256")
        or not _sealed(new_result, "result_payload_sha256")
        or old_forward.get("protocol_id") != OLD_PROTOCOL_ID
        or new_forward.get("protocol_id") != NEW_PROTOCOL_ID
        or old_forward.get("audit_valid") is not True
        or new_forward.get("audit_valid") is not True
        or old_forward.get("findings") != []
        or new_forward.get("findings") != []
        or not _sealed(old_forward, "audit_payload_sha256")
        or not _sealed(new_forward, "audit_payload_sha256")
        or old_post.get("protocol_id") != OLD_PROTOCOL_ID
        or new_post.get("protocol_id") != NEW_PROTOCOL_ID
        or old_post.get("audit_valid") is not True
        or new_post.get("audit_valid") is not True
        or old_post.get("findings") != []
        or new_post.get("findings") != []
        or not _sealed(old_post, "audit_payload_sha256")
        or not _sealed(new_post, "audit_payload_sha256")
        or old_forward.get("runtime_predictions_sha256")
        != contract.sha256(root / OLD_RUNTIME)
        or new_forward.get("runtime_predictions_sha256")
        != contract.sha256(root / NEW_RUNTIME)
        or old_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(root / OLD_EVAL)
        or new_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(root / NEW_EVAL)
    ):
        raise RuntimeError("V2.48.08 frozen parent chain drifted")
    return {"old_result": old_result, "new_result": new_result}


def _runtime(root: Path, relative: Path) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for line in _ordinary(root, relative).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        opaque_id = row.get("opaque_id")
        if (
            not isinstance(row, dict)
            or not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get("mapping_gold_category_question_type_split_evaluator_score_read")
            is not False
            or not isinstance(row.get("prediction_sha256"), str)
            or len(row["prediction_sha256"]) != 64
            or not isinstance(row.get("completion_kind"), str)
        ):
            raise RuntimeError("V2.48.08 runtime projection drifted")
        output[opaque_id] = {
            "prediction_sha256": row["prediction_sha256"],
            "completion_kind": row["completion_kind"],
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.08 runtime denominator drifted")
    return output


def _metrics(root: Path, relative: Path) -> dict[str, dict[str, Any]]:
    rows = _read(root, relative).get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.08 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id")
        metrics = row.get("metrics")
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(row.get("evaluator_valid"), bool)
            or not isinstance(metrics, dict)
            or any(
                isinstance(metrics.get(name), bool)
                or not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                for name in QUALITY
            )
        ):
            raise RuntimeError("V2.48.08 evaluator projection drifted")
        error = str(row.get("evaluator_error") or "")
        output[opaque_id] = {
            "valid": row["evaluator_valid"],
            "error_kind": None
            if row["evaluator_valid"]
            else "out_of_range_metric"
            if "out-of-range" in error
            else "empty_inner_join_assignment"
            if "internal error" in error
            else "other",
            "metrics": {name: float(metrics[name]) for name in QUALITY},
        }
    return output


def _aggregate(ids: Iterable[str], values: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    selected = sorted(ids)
    metrics = {
        name: sum(float(values[item]["metrics"][name]) for item in selected)
        / len(selected)
        for name in QUALITY
    }
    metrics["quality_composite"] = sum(metrics[name] for name in COMPOSITE) / 4
    return {
        "n": len(selected),
        "evaluator_valid": sum(values[item]["valid"] is True for item in selected),
        "whole_table_successes": sum(values[item]["metrics"]["score"] > 0 for item in selected),
        "metrics": metrics,
    }


def _bootstrap(ids: Iterable[str], old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    selected = sorted(ids)
    values = [
        sum(new[item]["metrics"][name] - old[item]["metrics"][name] for name in COMPOSITE) / 4
        for item in selected
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    interval = [means[int(0.025 * BOOTSTRAP_RESAMPLES)], means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]]
    return {
        "unit": "task_cluster",
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "mean_delta": sum(values) / len(values),
        "percentile_95_interval": interval,
        "interval_excludes_zero": interval[0] > 0 or interval[1] < 0,
        "direction_counts": {
            "improved": sum(value > 0 for value in values),
            "tied": sum(value == 0 for value in values),
            "worsened": sum(value < 0 for value in values),
        },
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parents = _validate_parents(root)
    old_runtime, new_runtime = _runtime(root, OLD_RUNTIME), _runtime(root, NEW_RUNTIME)
    old_metrics, new_metrics = _metrics(root, OLD_EVAL), _metrics(root, NEW_EVAL)
    ids = set(old_runtime)
    if ids != set(new_runtime) or ids != set(old_metrics) or ids != set(new_metrics) or len(ids) != SELECTED:
        raise RuntimeError("V2.48.08 paired population drifted")
    old_aggregate, new_aggregate = _aggregate(ids, old_metrics), _aggregate(ids, new_metrics)
    old_summary, new_summary = _read(root, OLD_SUMMARY), _read(root, NEW_SUMMARY)
    bootstrap = _bootstrap(ids, old_metrics, new_metrics)
    invalid_old = {item for item in ids if not old_metrics[item]["valid"]}
    invalid_new = {item for item in ids if not new_metrics[item]["valid"]}
    common_valid = ids - invalid_old - invalid_new
    common_old, common_new = _aggregate(common_valid, old_metrics), _aggregate(common_valid, new_metrics)
    metric_directions = {
        name: {
            "improved": sum(new_metrics[item]["metrics"][name] > old_metrics[item]["metrics"][name] for item in ids),
            "tied": sum(new_metrics[item]["metrics"][name] == old_metrics[item]["metrics"][name] for item in ids),
            "worsened": sum(new_metrics[item]["metrics"][name] < old_metrics[item]["metrics"][name] for item in ids),
        }
        for name in QUALITY
    }
    whole = Counter(
        f"old_{'success' if old_metrics[item]['metrics']['score'] > 0 else 'failure'}_"
        f"new_{'success' if new_metrics[item]['metrics']['score'] > 0 else 'failure'}"
        for item in ids
    )
    validity = Counter(
        f"old_{'valid' if old_metrics[item]['valid'] else 'invalid'}_"
        f"new_{'valid' if new_metrics[item]['valid'] else 'invalid'}"
        for item in ids
    )
    completions = Counter(
        f"old_{old_runtime[item]['completion_kind']}_new_{new_runtime[item]['completion_kind']}"
        for item in ids
    )
    value = {
        "artifact_version": 1,
        "role": "v24808_v24800_v24807_aggregate_only_repeatability_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "same_algorithm_single_rollout_variance_is_material",
        "parents": {
            "v24800_result_sha256": contract.sha256(root / OLD_RESULT),
            "v24800_forward_audit_sha256": contract.sha256(root / OLD_FORWARD_AUDIT),
            "v24800_postresult_audit_sha256": contract.sha256(root / OLD_POSTAUDIT),
            "v24800_runtime_predictions_sha256": contract.sha256(root / OLD_RUNTIME),
            "v24800_run_summary_sha256": contract.sha256(root / OLD_SUMMARY),
            "v24800_conservative_summary_sha256": contract.sha256(root / OLD_EVAL),
            "v24807_result_sha256": contract.sha256(root / NEW_RESULT),
            "v24807_forward_audit_sha256": contract.sha256(root / NEW_FORWARD_AUDIT),
            "v24807_postresult_audit_sha256": contract.sha256(root / NEW_POSTAUDIT),
            "v24807_runtime_predictions_sha256": contract.sha256(root / NEW_RUNTIME),
            "v24807_run_summary_sha256": contract.sha256(root / NEW_SUMMARY),
            "v24807_conservative_summary_sha256": contract.sha256(root / NEW_EVAL),
        },
        "boundary": {
            "both_exact220_prediction_freezes_and_evaluators_complete": True,
            "same_forward_algorithm_task_vector_model_search_budgets_and_concurrency": True,
            "offline_join_uses_opaque_id_only_for_alignment": True,
            "prediction_field_read": False,
            "prediction_hash_used_only_for_aggregate_identity_count": True,
            "mapping_answer_category_question_type_split_resource_opened": False,
            "task_identifier_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "per_task_metric_or_transition_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_feedback_retry_resume_skip_or_selective_revaluation": False,
        },
        "overall": {
            "v24800": old_aggregate,
            "v24807": new_aggregate,
            "delta_v24807_minus_v24800": {
                "evaluator_valid": new_aggregate["evaluator_valid"] - old_aggregate["evaluator_valid"],
                "whole_table_successes": new_aggregate["whole_table_successes"] - old_aggregate["whole_table_successes"],
                "metrics": {
                    name: new_aggregate["metrics"][name] - old_aggregate["metrics"][name]
                    for name in (*QUALITY, "quality_composite")
                },
            },
            "prediction_sha256_identical_tasks": sum(
                old_runtime[item]["prediction_sha256"] == new_runtime[item]["prediction_sha256"] for item in ids
            ),
            "prediction_sha256_changed_tasks": sum(
                old_runtime[item]["prediction_sha256"] != new_runtime[item]["prediction_sha256"] for item in ids
            ),
            "completion_kind_transitions": dict(sorted(completions.items())),
            "paired_metric_direction_counts": metric_directions,
            "whole_table_transitions": dict(sorted(whole.items())),
            "paired_composite_bootstrap": bootstrap,
        },
        "common_evaluator_valid_intersection": {
            "n": len(common_valid),
            "v24800": common_old,
            "v24807": common_new,
            "metrics_delta": {
                name: common_new["metrics"][name] - common_old["metrics"][name]
                for name in (*QUALITY, "quality_composite")
            },
        },
        "evaluator": {
            "validity_transitions": dict(sorted(validity.items())),
            "v24800_invalid_failure_as_zero": len(invalid_old),
            "v24807_invalid_failure_as_zero": len(invalid_new),
            "invalid_intersection": len(invalid_old & invalid_new),
            "invalid_union": len(invalid_old | invalid_new),
            "invalid_set_jaccard": len(invalid_old & invalid_new) / len(invalid_old | invalid_new),
            "error_taxonomy": {
                "v24800": dict(sorted(Counter(old_metrics[item]["error_kind"] for item in invalid_old).items())),
                "v24807": dict(sorted(Counter(new_metrics[item]["error_kind"] for item in invalid_new).items())),
            },
            "confirmed_released_evaluator_failure_modes": {
                "empty_inner_join_assignment": "pandas apply on an empty joined frame returns a DataFrame that released code assigns to one column",
                "out_of_range_unique_column_metric": "many-to-many key normalization can make unique-column true positives exceed ground-truth rows",
            },
            "selective_retry_or_revaluation": False,
        },
        "cost_and_retrieval": {
            "v24800": {
                "system_total_tokens": old_summary["system_total_tokens"],
                "provider_attempts": old_summary["direct_search_totals"]["provider_attempts"],
                "queries_executed": old_summary["fixed_full_budget_control_totals"]["total_queries_executed"],
                "fetches_attempted": old_summary["fixed_full_budget_control_totals"]["total_fetches_attempted"],
                "second_wave_executed_tasks": old_summary["fixed_full_budget_control_totals"]["second_wave_executed_tasks"],
                "forward_wall_seconds": parents["old_result"]["efficiency"]["forward_wall_seconds"],
            },
            "v24807": {
                "system_total_tokens": new_summary["system_total_tokens"],
                "provider_attempts": new_summary["direct_search_totals"]["provider_attempts"],
                "queries_executed": new_summary["fixed_full_budget_control_totals"]["total_queries_executed"],
                "fetches_attempted": new_summary["fixed_full_budget_control_totals"]["total_fetches_attempted"],
                "second_wave_executed_tasks": new_summary["fixed_full_budget_control_totals"]["second_wave_executed_tasks"],
                "forward_wall_seconds": parents["new_result"]["efficiency"]["forward_wall_seconds"],
            },
        },
        "conclusions": {
            "same_algorithm_predictions_are_byte_stable": False,
            "whole_table_single_rollout_gain_replicated": False,
            "quality_composite_difference_is_statistically_resolved": bootstrap["interval_excludes_zero"],
            "single_rollout_internal_frontier_is_stable_enough_for_causal_claims": False,
            "evaluator_invalid_set_is_stable": False,
            "fixed_budget_or_entropy_causal_effect_established": False,
            "leaderboard_or_external_sota_established": False,
        },
        "next_work": {
            "do_not_launch_another_unchanged_public_exact220": True,
            "do_not_selectively_revaluate_invalid_rows": True,
            "repair_evaluator_only_for_future_preregistered_protocols_and_report_both_official_and_repaired_metrics": True,
            "mechanism_selection_requires_shared_prefix_benchmark_external_evidence": True,
            "primary_optimization_target": "identity_coverage_and_schema_binding_before_more_search",
            "report_future_public_candidates_against_v24800_and_v24807_with_uncertainty": True,
        },
        "authorization": {
            "evaluator_compatibility_repair_design": True,
            "benchmark_external_shared_prefix_execution_design": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "paired_denominator_exact220": old_aggregate["n"] == new_aggregate["n"] == SELECTED,
        "prediction_identity_partition_exact220": value["overall"]["prediction_sha256_identical_tasks"] + value["overall"]["prediction_sha256_changed_tasks"] == SELECTED,
        "whole_table_transitions_cover_exact220": sum(whole.values()) == SELECTED,
        "validity_transitions_cover_exact220": sum(validity.values()) == SELECTED,
        "metric_directions_cover_exact220": all(sum(counts.values()) == SELECTED for counts in metric_directions.values()),
        "invalid_set_arithmetic": len(invalid_old | invalid_new) == len(invalid_old) + len(invalid_new) - len(invalid_old & invalid_new),
        "final_result_metrics_reconcile": old_aggregate["metrics"]["quality_composite"] == parents["old_result"]["metrics"]["all_220"]["quality_composite"] and new_aggregate["metrics"]["quality_composite"] == parents["new_result"]["metrics"]["all_220"]["quality_composite"],
        "same_algorithm_whole_table_net_delta_zero": value["overall"]["delta_v24807_minus_v24800"]["whole_table_successes"] == 0,
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.48.08 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_report(root, value, rebuild=False)


def validate_report(root: Path, value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v24808_v24800_v24807_aggregate_only_repeatability_diagnosis"
        or copied.get("status") != "same_algorithm_single_rollout_variance_is_material"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get("whole_table_single_rollout_gain_replicated") is not False
        or copied.get("authorization") != {
            "evaluator_compatibility_repair_design": True,
            "benchmark_external_shared_prefix_execution_design": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.08 repeatability diagnosis drifted")
    if rebuild:
        expected = build_report(root, now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.08 diagnosis is not reproducible")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
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
        "identical_predictions": report["overall"]["prediction_sha256_identical_tasks"],
        "whole_table_delta": report["overall"]["delta_v24807_minus_v24800"]["whole_table_successes"],
        "composite_delta": report["overall"]["delta_v24807_minus_v24800"]["metrics"]["quality_composite"],
        "bootstrap_interval": report["overall"]["paired_composite_bootstrap"]["percentile_95_interval"],
        "authorization": report["authorization"],
    }, sort_keys=True))
