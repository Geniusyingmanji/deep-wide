#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.48.00/V2.48.31 exact-220 runs.

This is post-result analysis.  It aligns terminal rows in memory, publishes no
task identifier or per-task metric, and grants no public benchmark authority.
The next forward may use only same-pass content-free transport observations;
historical scores and strata are never runtime inputs.
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

from deepwide_agent import v24831_keyless_exact220_contract as contract  # noqa: E402


OUTPUT = Path("results/v24832_v24800_v24831_stop_gate_diagnosis_v1_20260807.json")
OLD_ROOT = Path("outputs/v24800_exact220_v1_20260807")
NEW_ROOT = Path("outputs/v24831_keyless_exact220_v1_20260807")
OLD_RESULT = Path("results/v24800_exact220_result_v1_20260807.json")
NEW_RESULT = Path("results/v24831_keyless_exact220_result_v1_20260807.json")
OLD_POSTAUDIT = Path("results/v24800_exact220_postresult_audit_v1_20260807.json")
NEW_POSTAUDIT = Path(
    "results/v24831_keyless_exact220_postresult_audit_v1_20260807.json"
)
OLD_FORWARD_AUDIT = Path("results/v24800_exact220_forward_audit_v1_20260807.json")
NEW_FORWARD_AUDIT = Path(
    "results/v24831_keyless_exact220_forward_audit_v1_20260807.json"
)
OLD_EVAL = OLD_ROOT / "evaluator/conservative_summary.json"
NEW_EVAL = NEW_ROOT / "evaluator/conservative_summary.json"
SELECTED = 220
BOOTSTRAP_SEED = 24832
BOOTSTRAP_RESAMPLES = 20_000
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
RETRIEVAL = (
    "queries_executed",
    "fetches_attempted",
    "usable_pages",
    "unique_hosts",
    "content_chars",
    "synthesized_rows",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(path: Path) -> Path:
    absolute = ROOT / path
    if (
        path.is_absolute()
        or ".." in path.parts
        or absolute.is_symlink()
        or not absolute.is_file()
        or not absolute.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.32 expected ordinary repository file: {path}")
    return absolute


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.32 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, Any]:
    old_result = _read(OLD_RESULT)
    new_result = _read(NEW_RESULT)
    old_post = _read(OLD_POSTAUDIT)
    new_post = _read(NEW_POSTAUDIT)
    old_forward = _read(OLD_FORWARD_AUDIT)
    new_forward = _read(NEW_FORWARD_AUDIT)
    if (
        old_result.get("role") != "v24800_exact220_result"
        or new_result.get("role") != "v24791_exact220_result"
        or new_result.get("protocol_id") != contract.PROTOCOL_ID
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
        or old_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(ROOT / OLD_EVAL)
        or new_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(ROOT / NEW_EVAL)
    ):
        raise RuntimeError("V2.48.32 frozen parent chain drifted")
    return {
        "old_result": old_result,
        "new_result": new_result,
        "old_post": old_post,
        "new_post": new_post,
    }


def _metric_projection(path: Path) -> dict[str, dict[str, Any]]:
    rows = _read(path).get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.32 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id") if isinstance(row, Mapping) else None
        metrics = row.get("metrics") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(metrics, Mapping)
            or any(
                isinstance(metrics.get(name), bool)
                or not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                for name in QUALITY
            )
            or not isinstance(row.get("evaluator_valid"), bool)
        ):
            raise RuntimeError("V2.48.32 evaluator projection drifted")
        output[opaque_id] = {
            "evaluator_valid": row["evaluator_valid"],
            "metrics": {name: float(metrics[name]) for name in QUALITY},
        }
    return output


def _task_projection(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(root / "tasks" / f"task_{position:04d}" / "result.json")
        result = envelope.get("result") or {}
        opaque_id = result.get("opaque_id")
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        discovery = receipt.get("discovery_union") or {}
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
            raise RuntimeError("V2.48.32 task projection drifted")
        integers = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": total.get("usable_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "content_chars": total.get("content_chars"),
            "synthesized_rows": table.get("row_count"),
            "mapping_failure_count": discovery.get(
                "raw_query_local_mapping_failure_count"
            ),
            "union_recovery_count": discovery.get("union_recovery_invocation_count"),
        }
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in integers.values()
        ):
            raise RuntimeError("V2.48.32 task count drifted")
        output[opaque_id] = {
            "decision": controller["decision"],
            "reason": controller["reason"],
            **integers,
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.32 task denominator drifted")
    return output


def _aggregate(
    ids: Iterable[str],
    metrics: Mapping[str, Mapping[str, Any]],
    tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.32 cannot aggregate empty stratum")
    n = len(selected)
    metric = {
        name: sum(float(metrics[item]["metrics"][name]) for item in selected) / n
        for name in QUALITY
    }
    metric["quality_composite"] = sum(metric[name] for name in COMPOSITE) / 4
    return {
        "n": n,
        "evaluator_valid": sum(metrics[item]["evaluator_valid"] for item in selected),
        "whole_table_successes": sum(
            metrics[item]["metrics"]["score"] > 0 for item in selected
        ),
        "metrics": metric,
        "retrieval": {
            name: sum(float(tasks[item][name]) for item in selected) / n
            for name in RETRIEVAL
        },
        "transport": {
            "mapping_failure_tasks": sum(
                tasks[item]["mapping_failure_count"] > 0 for item in selected
            ),
            "mapping_failure_count": sum(
                tasks[item]["mapping_failure_count"] for item in selected
            ),
            "union_recovery_tasks": sum(
                tasks[item]["union_recovery_count"] > 0 for item in selected
            ),
            "union_recovery_count": sum(
                tasks[item]["union_recovery_count"] for item in selected
            ),
        },
    }


def _delta(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    if old["n"] != new["n"]:
        raise RuntimeError("V2.48.32 paired denominator drifted")
    return {
        "n": old["n"],
        "evaluator_valid_delta": new["evaluator_valid"] - old["evaluator_valid"],
        "whole_table_success_delta": new["whole_table_successes"]
        - old["whole_table_successes"],
        "metrics": {
            name: float(new["metrics"][name]) - float(old["metrics"][name])
            for name in (*QUALITY, "quality_composite")
        },
        "retrieval": {
            name: float(new["retrieval"][name]) - float(old["retrieval"][name])
            for name in RETRIEVAL
        },
    }


def _paired_group(
    ids: Iterable[str],
    old_metrics: Mapping[str, Mapping[str, Any]],
    new_metrics: Mapping[str, Mapping[str, Any]],
    old_tasks: Mapping[str, Mapping[str, Any]],
    new_tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = set(ids)
    old = _aggregate(selected, old_metrics, old_tasks)
    new = _aggregate(selected, new_metrics, new_tasks)
    return {"old": old, "new": new, "delta": _delta(old, new)}


def _bootstrap(
    ids: Iterable[str],
    old: Mapping[str, Mapping[str, Any]],
    new: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    values = [
        sum(
            new[item]["metrics"][name] - old[item]["metrics"][name]
            for name in COMPOSITE
        )
        / 4
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


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    old_metrics = _metric_projection(OLD_EVAL)
    new_metrics = _metric_projection(NEW_EVAL)
    old_tasks = _task_projection(OLD_ROOT)
    new_tasks = _task_projection(NEW_ROOT)
    ids = set(old_metrics)
    if any(ids != set(value) for value in (new_metrics, old_tasks, new_tasks)):
        raise RuntimeError("V2.48.32 paired identity set drifted")

    strata: dict[str, set[str]] = {
        "new_stop": {item for item in ids if new_tasks[item]["decision"] == "stop"},
        "new_expand": {
            item for item in ids if new_tasks[item]["decision"] == "expand"
        },
        "new_mapping_failure_positive": {
            item for item in ids if new_tasks[item]["mapping_failure_count"] > 0
        },
        "new_mapping_failure_zero": {
            item for item in ids if new_tasks[item]["mapping_failure_count"] == 0
        },
        "new_stop_mapping_failure_positive": {
            item
            for item in ids
            if new_tasks[item]["decision"] == "stop"
            and new_tasks[item]["mapping_failure_count"] > 0
        },
        "new_stop_mapping_failure_zero": {
            item
            for item in ids
            if new_tasks[item]["decision"] == "stop"
            and new_tasks[item]["mapping_failure_count"] == 0
        },
    }
    for reason in sorted({value["reason"] for value in new_tasks.values()}):
        strata[f"new_reason_{reason}"] = {
            item for item in ids if new_tasks[item]["reason"] == reason
        }
    paired_strata = {
        name: _paired_group(
            members, old_metrics, new_metrics, old_tasks, new_tasks
        )
        for name, members in strata.items()
        if members
    }
    overall = _paired_group(ids, old_metrics, new_metrics, old_tasks, new_tasks)
    decision_counts = Counter(new_tasks[item]["decision"] for item in ids)
    reason_counts = Counter(new_tasks[item]["reason"] for item in ids)
    bootstrap = _bootstrap(ids, old_metrics, new_metrics)
    value = {
        "artifact_version": 1,
        "role": "v24832_v24800_v24831_aggregate_only_stop_gate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "stop_gate_quality_regression_observed_causality_unresolved",
        "parents": {
            "v24800_result_sha256": contract.sha256(ROOT / OLD_RESULT),
            "v24800_postresult_audit_sha256": contract.sha256(ROOT / OLD_POSTAUDIT),
            "v24800_forward_audit_sha256": contract.sha256(ROOT / OLD_FORWARD_AUDIT),
            "v24800_conservative_summary_sha256": contract.sha256(ROOT / OLD_EVAL),
            "v24831_result_sha256": contract.sha256(ROOT / NEW_RESULT),
            "v24831_postresult_audit_sha256": contract.sha256(ROOT / NEW_POSTAUDIT),
            "v24831_forward_audit_sha256": contract.sha256(ROOT / NEW_FORWARD_AUDIT),
            "v24831_conservative_summary_sha256": contract.sha256(ROOT / NEW_EVAL),
        },
        "boundary": {
            "both_exact220_forwards_and_evaluators_terminal_before_analysis": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "task_result_prediction_field_used": False,
            "mapping_answer_category_question_type_split_resource_opened": False,
            "task_identifier_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "per_task_metric_or_transition_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "historical_score_or_stratum_authorized_as_future_runtime_input": False,
        },
        "overall": overall,
        "new_controller": {
            "decision_counts": dict(sorted(decision_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "paired_strata": paired_strata,
        "paired_composite_bootstrap": bootstrap,
        "conclusions": {
            "overall_quality_composite_regressed": overall["delta"]["metrics"][
                "quality_composite"
            ]
            < 0,
            "overall_item_and_column_f1_regressed": all(
                overall["delta"]["metrics"][name] < 0
                for name in ("f1_by_item", "column_f1")
            ),
            "new_stop_stratum_quality_composite_regressed": paired_strata[
                "new_stop"
            ]["delta"]["metrics"]["quality_composite"]
            < 0,
            "new_stop_stratum_item_and_column_f1_regressed": all(
                paired_strata["new_stop"]["delta"]["metrics"][name] < 0
                for name in ("f1_by_item", "column_f1")
            ),
            "new_expand_stratum_quality_composite_improved": paired_strata[
                "new_expand"
            ]["delta"]["metrics"]["quality_composite"]
            > 0,
            "new_stop_stratum_has_lower_usable_page_count_than_reference": paired_strata[
                "new_stop"
            ]["delta"]["retrieval"]["usable_pages"]
            < 0,
            "mapping_failure_presence_is_not_a_monotone_quality_harm_signal": paired_strata[
                "new_mapping_failure_zero"
            ]["delta"]["metrics"]["quality_composite"]
            < paired_strata["new_mapping_failure_positive"]["delta"]["metrics"]
            ["quality_composite"],
            "transport_and_generation_differences_confound_stop_gate_effect": True,
            "randomized_or_shared_prefix_causal_effect_established": False,
            "historical_benchmark_metric_may_route_future_forward": False,
            "entropy_or_information_gain_validated_as_credit": False,
            "leaderboard_or_sota_established": False,
        },
        "next_work": {
            "candidate": "transport_aware_sufficiency_abstention",
            "candidate_rule_scope": [
                "same_pass_content_free_transport_receipt",
                "same_pass_coverage_margin",
                "global_frozen_policy_only",
            ],
            "mapping_failure_alone_must_not_receive_credit_or_force_a_tuned_route": True,
            "fail_closed_expand_when_transport_receipt_is_incomplete_or_invalid": True,
            "required_external_gate_arms": [
                "first_wave_only",
                "fixed_full_budget",
                "transport_aware_adaptive",
            ],
            "required_external_gate_controls": [
                "fresh_population",
                "same_frozen_prefix_and_candidate_order",
                "fixed_failure_as_zero_denominator",
                "no_resume_retry_skip_or_selective_rerun",
                "task_cluster_bootstrap",
                "cost_and_evaluator_health_non_regression",
            ],
        },
        "authorization": {
            "transport_aware_controller_build": True,
            "fresh_benchmark_external_gate_design": True,
            "public_dev64": False,
            "public_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "paired_denominator_exact220": overall["old"]["n"]
        == overall["new"]["n"]
        == SELECTED,
        "decision_counts_cover_exact220": sum(decision_counts.values()) == SELECTED,
        "reason_counts_cover_exact220": sum(reason_counts.values()) == SELECTED,
        "stop_expand_partition_exact220": len(strata["new_stop"])
        + len(strata["new_expand"])
        == SELECTED,
        "mapping_partition_exact220": len(strata["new_mapping_failure_positive"])
        + len(strata["new_mapping_failure_zero"])
        == SELECTED,
        "final_result_delta_reconciles": math.isclose(
            overall["delta"]["metrics"]["quality_composite"],
            parents["new_result"]["metrics"]["all_220"]["quality_composite"]
            - parents["old_result"]["metrics"]["all_220"]["quality_composite"],
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
        "bootstrap_denominator_exact220": sum(
            bootstrap["direction_counts"].values()
        )
        == SELECTED,
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.48.32 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24832_v24800_v24831_aggregate_only_stop_gate_diagnosis"
        or copied.get("status")
        != "stop_gate_quality_regression_observed_causality_unresolved"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get(
            "randomized_or_shared_prefix_causal_effect_established"
        )
        is not False
        or copied.get("conclusions", {}).get(
            "historical_benchmark_metric_may_route_future_forward"
        )
        is not False
        or copied.get("authorization", {}).get("public_exact220") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.32 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.32 diagnosis is not reproducible")
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
    report = build()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "quality_composite_delta": report["overall"]["delta"]["metrics"][
                    "quality_composite"
                ],
                "stop_stratum_delta": report["paired_strata"]["new_stop"][
                    "delta"
                ]["metrics"]["quality_composite"],
                "expand_stratum_delta": report["paired_strata"]["new_expand"][
                    "delta"
                ]["metrics"]["quality_composite"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
