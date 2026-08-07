#!/usr/bin/env python3
"""Aggregate-only paired diagnosis of frozen V2.47.98 and V2.48.00.

Both exact-220 forwards, prediction freezes, official evaluations, and
post-result audits are already terminal.  This script aligns released rows in
memory and publishes fixed-denominator aggregates only.  It emits no task ID,
question, prediction, answer, query, URL, page, credential, or per-task score,
performs no remote effect, and grants no new benchmark authority.
"""

from __future__ import annotations

import json
import math
import os
import random
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
from scripts import finalize_v24798_exact220 as old_finalizer  # noqa: E402
from scripts import finalize_v24800_exact220 as new_finalizer  # noqa: E402


OUTPUT = Path(
    "results/v24801_v24798_v24800_paired_postresult_diagnosis_v1_20260807.json"
)
OLD_ROOT = Path("outputs/v24798_exact220_v1_20260807")
NEW_ROOT = Path("outputs/v24800_exact220_v1_20260807")
OLD_RESULT = old_finalizer.FINAL_RESULT
NEW_RESULT = new_finalizer.FINAL_RESULT
OLD_POSTAUDIT = old_finalizer.POSTAUDIT
NEW_POSTAUDIT = new_finalizer.POSTAUDIT
OLD_FORWARD_AUDIT = old_finalizer.FORWARD_AUDIT
NEW_FORWARD_AUDIT = new_finalizer.FORWARD_AUDIT
OLD_RUNTIME = OLD_ROOT / "runtime_predictions.jsonl"
NEW_RUNTIME = NEW_ROOT / "runtime_predictions.jsonl"
OLD_RUN_SUMMARY = OLD_ROOT / "run_summary.json"
NEW_RUN_SUMMARY = NEW_ROOT / "run_summary.json"
OLD_EVAL_SUMMARY = old_finalizer.SUMMARY
NEW_EVAL_SUMMARY = new_finalizer.SUMMARY
SELECTED = 220
BOOTSTRAP_SEED = 24801
BOOTSTRAP_RESAMPLES = 20_000
QUALITY_METRICS = (
    "score",
    "entity_acc",
    "f1_by_row",
    "f1_by_item",
    "column_f1",
)
COMPOSITE_METRICS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
RETRIEVAL_FIELDS = (
    "queries_executed",
    "fetches_attempted",
    "usable_pages",
    "unique_hosts",
    "content_chars",
    "synthesized_rows",
    "unknown_cell_ratio",
)
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
        raise RuntimeError(f"V2.48.01 expected ordinary repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.01 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents(root: Path) -> dict[str, dict[str, Any]]:
    old_result = _read(root, OLD_RESULT)
    new_result = _read(root, NEW_RESULT)
    old_post = _read(root, OLD_POSTAUDIT)
    new_post = _read(root, NEW_POSTAUDIT)
    old_forward = _read(root, OLD_FORWARD_AUDIT)
    new_forward = _read(root, NEW_FORWARD_AUDIT)
    if (
        old_result.get("role") != "v24798_exact220_result"
        or new_result.get("role") != "v24800_exact220_result"
        or old_result.get("selected") != SELECTED
        or new_result.get("selected") != SELECTED
        or old_result.get("failure_as_zero") is not True
        or new_result.get("failure_as_zero") is not True
        or not _sealed(old_result, "result_payload_sha256")
        or not _sealed(new_result, "result_payload_sha256")
        or old_post.get("audit_valid") is not True
        or new_post.get("audit_valid") is not True
        or old_post.get("findings") != []
        or new_post.get("findings") != []
        or not _sealed(old_post, "audit_payload_sha256")
        or not _sealed(new_post, "audit_payload_sha256")
        or old_forward.get("audit_valid") is not True
        or new_forward.get("audit_valid") is not True
        or old_forward.get("findings") != []
        or new_forward.get("findings") != []
        or not _sealed(old_forward, "audit_payload_sha256")
        or not _sealed(new_forward, "audit_payload_sha256")
        or old_forward.get("runtime_predictions_sha256")
        != contract.sha256(root / OLD_RUNTIME)
        or new_forward.get("runtime_predictions_sha256")
        != contract.sha256(root / NEW_RUNTIME)
        or old_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(root / OLD_EVAL_SUMMARY)
        or new_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(root / NEW_EVAL_SUMMARY)
    ):
        raise RuntimeError("V2.48.01 frozen parent chain drifted")
    return {
        "old_result": old_result,
        "new_result": new_result,
        "old_post": old_post,
        "new_post": new_post,
    }


def _runtime_projection(root: Path, relative: Path) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for line in _ordinary(root, relative).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        opaque_id = value.get("opaque_id")
        completion = value.get("completion_kind")
        prediction_sha256 = value.get("prediction_sha256")
        if (
            not isinstance(value, dict)
            or not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or not isinstance(completion, str)
            or not completion
            or not isinstance(prediction_sha256, str)
            or len(prediction_sha256) != 64
            or value.get("status") != "completed"
            or value.get("label_blind") is not True
            or value.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            or opaque_id in output
        ):
            raise RuntimeError("V2.48.01 runtime projection drifted")
        output[opaque_id] = {
            "completion_kind": completion,
            "prediction_sha256": prediction_sha256,
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.01 runtime denominator drifted")
    return output


def _metric_projection(root: Path, relative: Path) -> dict[str, dict[str, Any]]:
    summary = _read(root, relative)
    rows = summary.get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.01 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id")
        metrics = row.get("metrics")
        if (
            not isinstance(row, dict)
            or not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(metrics, dict)
            or any(
                isinstance(metrics.get(name), bool)
                or not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                for name in QUALITY_METRICS
            )
            or not isinstance(row.get("evaluator_valid"), bool)
        ):
            raise RuntimeError("V2.48.01 evaluator projection drifted")
        message = str(row.get("evaluator_error") or "")
        output[opaque_id] = {
            "evaluator_valid": row["evaluator_valid"],
            "error_kind": None
            if row["evaluator_valid"]
            else "out_of_range_metric"
            if "out-of-range" in message
            else "internal_error",
            "metrics": {name: float(metrics[name]) for name in QUALITY_METRICS},
        }
    return output


def _task_projection(root: Path, task_root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(
            root, task_root / f"task_{position:04d}" / "result.json"
        )
        result = envelope.get("result") or {}
        opaque_id = result.get("opaque_id")
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        total = receipt.get("total") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or retrieval.get("status") != "completed"
            or controller.get("decision") not in {"expand", "stop"}
            or controller.get("reason")
            not in {
                "first_wave_sufficient",
                "positive_entropy_voc",
                "latency_ceiling",
                "nonpositive_entropy_voc",
                "no_delta_budget",
            }
            or controller.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            )
            is not False
            or controller.get("question_text_or_content_read_by_kernel") is not False
        ):
            raise RuntimeError("V2.48.01 controller projection drifted")
        values = {
            "queries_executed": int(total["queries_executed"]),
            "fetches_attempted": int(total["fetches_attempted"]),
            "usable_pages": int(total["usable_pages"]),
            "unique_hosts": int(total["unique_hosts"]),
            "content_chars": int(total["content_chars"]),
            "synthesized_rows": int(table["row_count"]),
            "unknown_cell_ratio": float(table["unknown_cell_ratio"]),
        }
        if any(not math.isfinite(float(value)) for value in values.values()):
            raise RuntimeError("V2.48.01 non-finite task projection")
        output[opaque_id] = {
            "decision": str(controller["decision"]),
            "reason": str(controller["reason"]),
            **values,
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.01 task projection denominator drifted")
    return output


def _aggregate(
    ids: Iterable[str],
    metrics: Mapping[str, Mapping[str, Any]],
    tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.01 cannot summarize empty group")
    output: dict[str, Any] = {
        "n": len(selected),
        "evaluator_valid": sum(
            metrics[item]["evaluator_valid"] is True for item in selected
        ),
        "whole_table_successes": sum(
            metrics[item]["metrics"]["score"] > 0 for item in selected
        ),
        "metrics": {
            name: sum(metrics[item]["metrics"][name] for item in selected)
            / len(selected)
            for name in QUALITY_METRICS
        },
        "retrieval": {
            name: sum(float(tasks[item][name]) for item in selected) / len(selected)
            for name in RETRIEVAL_FIELDS
        },
    }
    output["metrics"]["quality_composite"] = sum(
        output["metrics"][name] for name in COMPOSITE_METRICS
    ) / len(COMPOSITE_METRICS)
    return output


def _delta(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    if old["n"] != new["n"]:
        raise RuntimeError("V2.48.01 paired group denominator drifted")
    return {
        "n": old["n"],
        "evaluator_valid_delta": new["evaluator_valid"] - old["evaluator_valid"],
        "whole_table_success_delta": new["whole_table_successes"]
        - old["whole_table_successes"],
        "metrics": {
            name: float(new["metrics"][name]) - float(old["metrics"][name])
            for name in (*QUALITY_METRICS, "quality_composite")
        },
        "retrieval": {
            name: float(new["retrieval"][name]) - float(old["retrieval"][name])
            for name in RETRIEVAL_FIELDS
        },
    }


def _direction_counts(
    ids: Iterable[str],
    old: Mapping[str, Mapping[str, Any]],
    new: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, int]]:
    selected = list(ids)
    return {
        name: {
            "improved": sum(
                new[item]["metrics"][name] > old[item]["metrics"][name]
                for item in selected
            ),
            "tied": sum(
                new[item]["metrics"][name] == old[item]["metrics"][name]
                for item in selected
            ),
            "worsened": sum(
                new[item]["metrics"][name] < old[item]["metrics"][name]
                for item in selected
            ),
        }
        for name in QUALITY_METRICS
    }


def _bootstrap_composite_delta(
    ids: Iterable[str],
    old: Mapping[str, Mapping[str, Any]],
    new: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    values = [
        sum(
            new[item]["metrics"][name] - old[item]["metrics"][name]
            for name in COMPOSITE_METRICS
        )
        / len(COMPOSITE_METRICS)
        for item in selected
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    lower = means[int(0.025 * BOOTSTRAP_RESAMPLES)]
    upper = means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]
    return {
        "unit": "task_cluster",
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "mean_delta": sum(values) / len(values),
        "percentile_95_interval": [lower, upper],
        "interval_excludes_zero": lower > 0 or upper < 0,
        "direction_counts": {
            "improved": sum(value > 0 for value in values),
            "tied": sum(value == 0 for value in values),
            "worsened": sum(value < 0 for value in values),
        },
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parents = _validate_parents(root)
    old_runtime = _runtime_projection(root, OLD_RUNTIME)
    new_runtime = _runtime_projection(root, NEW_RUNTIME)
    old_metrics = _metric_projection(root, OLD_EVAL_SUMMARY)
    new_metrics = _metric_projection(root, NEW_EVAL_SUMMARY)
    old_tasks = _task_projection(root, OLD_ROOT / "tasks")
    new_tasks = _task_projection(root, NEW_ROOT / "tasks")
    ids = set(old_runtime)
    if any(
        ids != set(value)
        for value in (new_runtime, old_metrics, new_metrics, old_tasks, new_tasks)
    ) or len(ids) != SELECTED:
        raise RuntimeError("V2.48.01 frozen paired population drifted")

    all_old = _aggregate(ids, old_metrics, old_tasks)
    all_new = _aggregate(ids, new_metrics, new_tasks)
    all_delta = _delta(all_old, all_new)
    old_reason_groups: dict[str, set[str]] = defaultdict(set)
    for item in ids:
        old_reason_groups[old_tasks[item]["reason"]].add(item)
    reason_groups: dict[str, Any] = {}
    for reason, members in sorted(old_reason_groups.items()):
        old = _aggregate(members, old_metrics, old_tasks)
        new = _aggregate(members, new_metrics, new_tasks)
        reason_groups[reason] = {
            "old": old,
            "new": new,
            "delta": _delta(old, new),
            "new_reason_counts": dict(
                sorted(Counter(new_tasks[item]["reason"] for item in members).items())
            ),
        }

    old_summary = _read(root, OLD_RUN_SUMMARY)
    new_summary = _read(root, NEW_RUN_SUMMARY)
    old_result = parents["old_result"]
    new_result = parents["new_result"]
    metric_directions = _direction_counts(ids, old_metrics, new_metrics)
    bootstrap = _bootstrap_composite_delta(ids, old_metrics, new_metrics)
    decision_transitions = Counter(
        f"old_{old_tasks[item]['decision']}_new_{new_tasks[item]['decision']}"
        for item in ids
    )
    reason_transitions = Counter(
        f"old_{old_tasks[item]['reason']}_new_{new_tasks[item]['reason']}"
        for item in ids
    )
    evaluator_transitions = Counter(
        f"old_{'valid' if old_metrics[item]['evaluator_valid'] else 'invalid'}_"
        f"new_{'valid' if new_metrics[item]['evaluator_valid'] else 'invalid'}"
        for item in ids
    )
    whole_table_transitions = Counter(
        f"old_{'success' if old_metrics[item]['metrics']['score'] > 0 else 'failure'}_"
        f"new_{'success' if new_metrics[item]['metrics']['score'] > 0 else 'failure'}"
        for item in ids
    )
    evaluator_errors = {
        "old": dict(
            sorted(
                Counter(
                    str(value["error_kind"])
                    for value in old_metrics.values()
                    if value["error_kind"] is not None
                ).items()
            )
        ),
        "new": dict(
            sorted(
                Counter(
                    str(value["error_kind"])
                    for value in new_metrics.values()
                    if value["error_kind"] is not None
                ).items()
            )
        ),
    }
    value = {
        "artifact_version": 1,
        "role": "v24801_v24798_v24800_aggregate_only_paired_postresult_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "observed_full_budget_gain_with_uncertain_causal_and_sampling_scope",
        "parents": {
            "v24798_result_sha256": contract.sha256(root / OLD_RESULT),
            "v24798_postresult_audit_sha256": contract.sha256(root / OLD_POSTAUDIT),
            "v24798_forward_audit_sha256": contract.sha256(root / OLD_FORWARD_AUDIT),
            "v24798_runtime_predictions_sha256": contract.sha256(root / OLD_RUNTIME),
            "v24798_run_summary_sha256": contract.sha256(root / OLD_RUN_SUMMARY),
            "v24798_conservative_summary_sha256": contract.sha256(
                root / OLD_EVAL_SUMMARY
            ),
            "v24800_result_sha256": contract.sha256(root / NEW_RESULT),
            "v24800_postresult_audit_sha256": contract.sha256(root / NEW_POSTAUDIT),
            "v24800_forward_audit_sha256": contract.sha256(root / NEW_FORWARD_AUDIT),
            "v24800_runtime_predictions_sha256": contract.sha256(root / NEW_RUNTIME),
            "v24800_run_summary_sha256": contract.sha256(root / NEW_RUN_SUMMARY),
            "v24800_conservative_summary_sha256": contract.sha256(
                root / NEW_EVAL_SUMMARY
            ),
        },
        "boundary": {
            "both_forwards_prediction_freezes_and_evaluators_complete": True,
            "offline_join_uses_opaque_id_only_for_alignment": True,
            "prediction_hash_used_only_for_aggregate_identity_count": True,
            "prediction_field_used": False,
            "task_result_used_only_for_completion_controller_retrieval_and_table_shape": True,
            "mapping_answer_category_question_type_split_resource_opened": False,
            "task_identifier_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "per_task_metric_or_transition_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "same_run_retry_resume_skip_or_selective_revaluation": False,
        },
        "overall": {
            "old": all_old,
            "new": all_new,
            "delta": all_delta,
            "prediction_sha256_identical_tasks": sum(
                old_runtime[item]["prediction_sha256"]
                == new_runtime[item]["prediction_sha256"]
                for item in ids
            ),
            "old_forward_wall_seconds": old_result["efficiency"][
                "forward_wall_seconds"
            ],
            "new_forward_wall_seconds": new_result["efficiency"][
                "forward_wall_seconds"
            ],
            "forward_wall_seconds_delta": new_result["efficiency"][
                "forward_wall_seconds"
            ]
            - old_result["efficiency"]["forward_wall_seconds"],
            "old_system_total_tokens": old_summary["system_total_tokens"],
            "new_system_total_tokens": new_summary["system_total_tokens"],
            "system_total_tokens_delta": new_summary["system_total_tokens"]
            - old_summary["system_total_tokens"],
            "system_total_tokens_ratio": new_summary["system_total_tokens"]
            / old_summary["system_total_tokens"],
            "old_model_generated_tables": old_summary["model_generated_tables"],
            "new_model_generated_tables": new_summary["model_generated_tables"],
            "old_fallback_tables": old_summary["fallback_tables"],
            "new_fallback_tables": new_summary["fallback_tables"],
        },
        "old_reason_groups": reason_groups,
        "decision_transitions": dict(sorted(decision_transitions.items())),
        "reason_transitions": dict(sorted(reason_transitions.items())),
        "paired_metric_direction_counts": metric_directions,
        "paired_composite_bootstrap": bootstrap,
        "whole_table_transitions": dict(sorted(whole_table_transitions.items())),
        "evaluator": {
            "validity_transitions": dict(sorted(evaluator_transitions.items())),
            "error_taxonomy": evaluator_errors,
            "old_invalid_failure_as_zero": all_old["n"] - all_old["evaluator_valid"],
            "new_invalid_failure_as_zero": all_new["n"] - all_new["evaluator_valid"],
            "selective_retry_or_revaluation": False,
        },
        "conclusions": {
            "observed_internal_whole_table_frontier_improved": all_delta[
                "whole_table_success_delta"
            ]
            > 0,
            "observed_internal_quality_composite_frontier_improved": all_delta[
                "metrics"
            ]["quality_composite"]
            > 0,
            "observed_row_item_and_column_f1_all_improved": all(
                all_delta["metrics"][name] > 0
                for name in ("f1_by_row", "f1_by_item", "column_f1")
            ),
            "gain_concentrated_in_old_first_wave_sufficient_stratum": reason_groups[
                "first_wave_sufficient"
            ]["delta"]["metrics"]["quality_composite"]
            > 0
            and reason_groups["positive_entropy_voc"]["delta"]["metrics"][
                "quality_composite"
            ]
            <= 0,
            "paired_composite_bootstrap_interval_excludes_zero": bootstrap[
                "interval_excludes_zero"
            ],
            "randomized_or_shared_prefix_causal_effect_established": False,
            "independent_generation_and_evaluator_variance_remain_confounders": True,
            "full_budget_dominates_entropy_controller_at_matched_cost": False,
            "entropy_or_information_gain_is_validated_as_credit": False,
            "more_retrieval_is_universally_better": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "leaderboard_or_external_sota_established": False,
        },
        "next_work": {
            "freeze_v24800_as_current_internal_single_rollout_reference": True,
            "do_not_launch_another_public_exact220_from_this_diagnosis": True,
            "first_experiment": "benchmark_external_shared_prefix_budget_ladder",
            "required_arms": [
                "first_wave_only",
                "fixed_full_budget",
                "coverage_risk_adaptive",
            ],
            "required_controls": [
                "same_frozen_upstream_prefix_and_candidate_evidence_order",
                "same_model_renderer_and_hard_caps",
                "fixed_failure_as_zero_denominator",
                "task_cluster_bootstrap",
                "cost_and_evaluator_health_non_regression",
            ],
            "adaptive_signal_requirements": [
                "explicit_or_estimated_row_coverage_risk",
                "identity_and_target_value_binding_before_information_gain",
                "source_dependency_aware_evidence_groups",
                "expected_terminal_task_loss_reduction_minus_cost",
            ],
            "entropy_credit_requires_same_state_counterfactual_or_artifact_disjoint_outer_utility": True,
        },
        "authorization": {
            "benchmark_external_shared_prefix_design": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "paired_denominator_exact220": all_old["n"] == all_new["n"] == SELECTED,
        "decision_transitions_cover_exact220": sum(decision_transitions.values())
        == SELECTED,
        "reason_transitions_cover_exact220": sum(reason_transitions.values())
        == SELECTED,
        "whole_table_transitions_cover_exact220": sum(
            whole_table_transitions.values()
        )
        == SELECTED,
        "evaluator_transitions_cover_exact220": sum(evaluator_transitions.values())
        == SELECTED,
        "metric_directions_cover_exact220": all(
            sum(counts.values()) == SELECTED for counts in metric_directions.values()
        ),
        "old_reason_groups_partition_exact220": sum(
            group["old"]["n"] for group in reason_groups.values()
        )
        == SELECTED,
        "final_result_delta_reconciles": math.isclose(
            all_delta["metrics"]["quality_composite"],
            new_result["metrics"]["all_220"]["quality_composite"]
            - old_result["metrics"]["all_220"]["quality_composite"],
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and all_delta["whole_table_success_delta"]
        == new_result["metrics"]["all_220"]["whole_table_successes"]
        - old_result["metrics"]["all_220"]["whole_table_successes"],
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.48.01 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_report(root, value, rebuild=False)


def validate_report(
    root: Path, value: Mapping[str, Any], *, rebuild: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24801_v24798_v24800_aggregate_only_paired_postresult_diagnosis"
        or copied.get("status")
        != "observed_full_budget_gain_with_uncertain_causal_and_sampling_scope"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get(
            "randomized_or_shared_prefix_causal_effect_established"
        )
        is not False
        or copied.get("conclusions", {}).get(
            "entropy_or_information_gain_is_validated_as_credit"
        )
        is not False
        or copied.get("authorization")
        != {
            "benchmark_external_shared_prefix_design": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.01 paired diagnosis drifted")
    if rebuild:
        expected = build_report(root, now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.01 paired diagnosis is not reproducible")
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
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "whole_table_success_delta": report["overall"]["delta"][
                    "whole_table_success_delta"
                ],
                "quality_composite_delta": report["overall"]["delta"][
                    "metrics"
                ]["quality_composite"],
                "bootstrap_interval": report["paired_composite_bootstrap"][
                    "percentile_95_interval"
                ],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
