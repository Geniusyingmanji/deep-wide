#!/usr/bin/env python3
"""Aggregate-only post-result diagnosis of V2.48.31 and V2.48.34.

The analysis aligns already frozen terminal rows only in memory.  It emits no
task identifier, question, prediction, query, URL, page, evaluator text, or
per-task metric.  Historical metrics and strata are explicitly forbidden as
future runtime inputs; the purpose is to reject unsupported causal stories and
define a benchmark-external successor gate.
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

from deepwide_agent import v24834_coverage_margin_exact220_contract as contract  # noqa: E402


OUTPUT = Path("results/v24835_v24831_v24834_evidence_budget_diagnosis_v1_20260807.json")
CONTROL_ROOT = Path("outputs/v24831_keyless_exact220_v1_20260807")
CANDIDATE_ROOT = Path("outputs/v24834_coverage_margin_exact220_v1_20260807")
CONTROL_RESULT = Path("results/v24831_keyless_exact220_result_v1_20260807.json")
CANDIDATE_RESULT = Path("results/v24834_coverage_margin_exact220_result_v1_20260807.json")
CONTROL_POSTAUDIT = Path("results/v24831_keyless_exact220_postresult_audit_v1_20260807.json")
CANDIDATE_POSTAUDIT = Path("results/v24834_coverage_margin_exact220_postresult_audit_v1_20260807.json")
CONTROL_FORWARD_AUDIT = Path("results/v24831_keyless_exact220_forward_audit_v1_20260807.json")
CANDIDATE_FORWARD_AUDIT = Path("results/v24834_coverage_margin_exact220_forward_audit_v1_20260807.json")
CONTROL_EVAL = CONTROL_ROOT / "evaluator/conservative_summary.json"
CANDIDATE_EVAL = CANDIDATE_ROOT / "evaluator/conservative_summary.json"
CONTROL_SUMMARY = CONTROL_ROOT / "run_summary.json"
CANDIDATE_SUMMARY = CANDIDATE_ROOT / "run_summary.json"
SELECTED = 220
BOOTSTRAP_SEED = 24835
BOOTSTRAP_RESAMPLES = 20_000
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
MECHANISM = (
    "queries_executed", "fetches_attempted", "usable_pages", "unique_hosts",
    "content_chars", "projected_chars", "model_input_tokens", "search_input_tokens",
    "synthesized_rows", "unknown_cell_ratio", "task_wall_seconds",
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
        raise RuntimeError(f"V2.48.35 expected ordinary repository file: {path}")
    return absolute


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.35 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, Any]:
    control = _read(CONTROL_RESULT)
    candidate = _read(CANDIDATE_RESULT)
    control_post = _read(CONTROL_POSTAUDIT)
    candidate_post = _read(CANDIDATE_POSTAUDIT)
    control_forward = _read(CONTROL_FORWARD_AUDIT)
    candidate_forward = _read(CANDIDATE_FORWARD_AUDIT)
    control_summary = _read(CONTROL_SUMMARY)
    candidate_summary = _read(CANDIDATE_SUMMARY)
    if (
        control.get("protocol_id")
        != "v24831_keyless_gpt56_hosted_search_exact220_replication_v1"
        or candidate.get("protocol_id") != contract.PROTOCOL_ID
        or control.get("selected") != SELECTED
        or candidate.get("selected") != SELECTED
        or control.get("failure_as_zero") is not True
        or candidate.get("failure_as_zero") is not True
        or not _sealed(control, "result_payload_sha256")
        or not _sealed(candidate, "result_payload_sha256")
        or any(value.get("audit_valid") is not True or value.get("findings") != []
               for value in (control_post, candidate_post, control_forward, candidate_forward))
        or any(not _sealed(value, "audit_payload_sha256")
               for value in (control_post, candidate_post, control_forward, candidate_forward))
        or control_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(ROOT / CONTROL_EVAL)
        or candidate_post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(ROOT / CANDIDATE_EVAL)
        or control_summary.get("completed") != SELECTED
        or candidate_summary.get("completed") != SELECTED
    ):
        raise RuntimeError("V2.48.35 frozen parent chain drifted")
    return {
        "control_result": control,
        "candidate_result": candidate,
        "control_summary": control_summary,
        "candidate_summary": candidate_summary,
    }


def _metric_projection(path: Path) -> dict[str, dict[str, Any]]:
    rows = _read(path).get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.35 evaluator denominator drifted")
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
            raise RuntimeError("V2.48.35 evaluator projection drifted")
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
        total = receipt.get("total") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        evidence = result.get("evidence") or {}
        model_cost = (result.get("cost") or {}).get("model") or {}
        search_cost = (result.get("cost") or {}).get("search") or {}
        timing = result.get("attributed_timing") or {}
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or retrieval.get("status") != "completed"
            or controller.get("decision") not in {"expand", "stop"}
            or controller.get("reason") not in {
                "first_wave_sufficient", "positive_entropy_voc",
                "latency_ceiling", "nonpositive_entropy_voc", "no_delta_budget",
            }
            or controller.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ) is not False
            or controller.get("question_text_or_content_read_by_kernel") is not False
        ):
            raise RuntimeError("V2.48.35 task projection drifted")
        integers = {
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "usable_pages": total.get("usable_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "content_chars": total.get("content_chars"),
            "projected_chars": evidence.get("projected_chars"),
            "model_input_tokens": model_cost.get("input_tokens"),
            "search_input_tokens": search_cost.get("input_tokens"),
            "synthesized_rows": table.get("row_count"),
        }
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in integers.values()
        ):
            raise RuntimeError("V2.48.35 task count drifted")
        ratio = table.get("unknown_cell_ratio")
        wall = timing.get("task_wall_seconds")
        if (
            isinstance(ratio, bool) or not isinstance(ratio, (int, float))
            or not 0 <= float(ratio) <= 1
            or isinstance(wall, bool) or not isinstance(wall, (int, float))
            or not math.isfinite(float(wall)) or float(wall) < 0
        ):
            raise RuntimeError("V2.48.35 task continuous metric drifted")
        output[opaque_id] = {
            "decision": controller["decision"],
            "reason": controller["reason"],
            **integers,
            "unknown_cell_ratio": float(ratio),
            "task_wall_seconds": float(wall),
            "fallback": result.get("completion_kind") == "best_effort_fallback",
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.35 task denominator drifted")
    return output


def _aggregate(
    ids: Iterable[str], metrics: Mapping[str, Mapping[str, Any]],
    tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.35 cannot aggregate empty stratum")
    n = len(selected)
    metric = {
        name: sum(float(metrics[item]["metrics"][name]) for item in selected) / n
        for name in QUALITY
    }
    metric["quality_composite"] = sum(metric[name] for name in COMPOSITE) / 4
    return {
        "n": n,
        "evaluator_valid": sum(metrics[item]["evaluator_valid"] for item in selected),
        "whole_table_successes": sum(metrics[item]["metrics"]["score"] > 0 for item in selected),
        "fallback_tables": sum(bool(tasks[item]["fallback"]) for item in selected),
        "metrics": metric,
        "mechanism": {
            name: sum(float(tasks[item][name]) for item in selected) / n
            for name in MECHANISM
        },
    }


def _delta(control: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if control["n"] != candidate["n"]:
        raise RuntimeError("V2.48.35 paired denominator drifted")
    return {
        "n": control["n"],
        "evaluator_valid_delta": candidate["evaluator_valid"] - control["evaluator_valid"],
        "whole_table_success_delta": candidate["whole_table_successes"] - control["whole_table_successes"],
        "fallback_table_delta": candidate["fallback_tables"] - control["fallback_tables"],
        "metrics": {
            name: float(candidate["metrics"][name]) - float(control["metrics"][name])
            for name in (*QUALITY, "quality_composite")
        },
        "mechanism": {
            name: float(candidate["mechanism"][name]) - float(control["mechanism"][name])
            for name in MECHANISM
        },
    }


def _paired_group(
    ids: Iterable[str], control_metrics: Mapping[str, Mapping[str, Any]],
    candidate_metrics: Mapping[str, Mapping[str, Any]],
    control_tasks: Mapping[str, Mapping[str, Any]],
    candidate_tasks: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = set(ids)
    control = _aggregate(selected, control_metrics, control_tasks)
    candidate = _aggregate(selected, candidate_metrics, candidate_tasks)
    return {"control": control, "candidate": candidate, "delta": _delta(control, candidate)}


def _bootstrap(
    ids: Iterable[str], control: Mapping[str, Mapping[str, Any]],
    candidate: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    selected = sorted(ids)
    values = [
        sum(candidate[item]["metrics"][name] - control[item]["metrics"][name]
            for name in COMPOSITE) / 4
        for item in selected
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return {
        "unit": "task_cluster",
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "mean_delta": sum(values) / len(values),
        "percentile_95_interval": [
            means[int(0.025 * BOOTSTRAP_RESAMPLES)],
            means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1],
        ],
        "direction_counts": {
            "improved": sum(value > 0 for value in values),
            "tied": sum(value == 0 for value in values),
            "worsened": sum(value < 0 for value in values),
        },
    }


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or not xs:
        raise RuntimeError("V2.48.35 correlation vector drifted")
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    covariance = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    return covariance / math.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    control_metrics = _metric_projection(CONTROL_EVAL)
    candidate_metrics = _metric_projection(CANDIDATE_EVAL)
    control_tasks = _task_projection(CONTROL_ROOT)
    candidate_tasks = _task_projection(CANDIDATE_ROOT)
    ids = set(control_metrics)
    if any(ids != set(value) for value in (candidate_metrics, control_tasks, candidate_tasks)):
        raise RuntimeError("V2.48.35 paired identity set drifted")

    strata = {
        "candidate_expand": {item for item in ids if candidate_tasks[item]["decision"] == "expand"},
        "candidate_stop": {item for item in ids if candidate_tasks[item]["decision"] == "stop"},
        "control_stop_candidate_expand": {
            item for item in ids
            if control_tasks[item]["decision"] == "stop"
            and candidate_tasks[item]["decision"] == "expand"
        },
        "both_stop": {
            item for item in ids
            if control_tasks[item]["decision"] == "stop"
            and candidate_tasks[item]["decision"] == "stop"
        },
        "both_expand": {
            item for item in ids
            if control_tasks[item]["decision"] == "expand"
            and candidate_tasks[item]["decision"] == "expand"
        },
    }
    overall = _paired_group(
        ids, control_metrics, candidate_metrics, control_tasks, candidate_tasks
    )
    paired_strata = {
        name: _paired_group(
            members, control_metrics, candidate_metrics, control_tasks, candidate_tasks
        )
        for name, members in strata.items() if members
    }
    route_transitions = Counter(
        f"control_{control_tasks[item]['decision']}_candidate_{candidate_tasks[item]['decision']}"
        for item in ids
    )
    candidate_reasons = Counter(candidate_tasks[item]["reason"] for item in ids)
    quality_deltas = [
        sum(candidate_metrics[item]["metrics"][name] - control_metrics[item]["metrics"][name]
            for name in COMPOSITE) / 4
        for item in sorted(ids)
    ]
    correlations = {
        name: _pearson(
            [candidate_tasks[item][name] - control_tasks[item][name] for item in sorted(ids)],
            quality_deltas,
        )
        for name in MECHANISM
    }
    bootstrap = _bootstrap(ids, control_metrics, candidate_metrics)
    value = {
        "artifact_version": 1,
        "role": "v24835_v24831_v24834_aggregate_only_evidence_budget_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "more_evidence_more_exact_but_lower_composite_causality_unresolved",
        "parents": {
            "v24831_result_sha256": contract.sha256(ROOT / CONTROL_RESULT),
            "v24831_postresult_audit_sha256": contract.sha256(ROOT / CONTROL_POSTAUDIT),
            "v24831_forward_audit_sha256": contract.sha256(ROOT / CONTROL_FORWARD_AUDIT),
            "v24831_conservative_summary_sha256": contract.sha256(ROOT / CONTROL_EVAL),
            "v24831_run_summary_sha256": contract.sha256(ROOT / CONTROL_SUMMARY),
            "v24834_result_sha256": contract.sha256(ROOT / CANDIDATE_RESULT),
            "v24834_postresult_audit_sha256": contract.sha256(ROOT / CANDIDATE_POSTAUDIT),
            "v24834_forward_audit_sha256": contract.sha256(ROOT / CANDIDATE_FORWARD_AUDIT),
            "v24834_conservative_summary_sha256": contract.sha256(ROOT / CANDIDATE_EVAL),
            "v24834_run_summary_sha256": contract.sha256(ROOT / CANDIDATE_SUMMARY),
        },
        "boundary": {
            "both_exact220_forwards_and_evaluators_terminal_before_analysis": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "task_result_prediction_field_used": False,
            "mapping_answer_category_question_type_split_resource_opened": False,
            "task_identifier_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "per_task_metric_transition_or_identifier_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "historical_score_stratum_or_correlation_authorized_as_future_runtime_input": False,
        },
        "overall": overall,
        "route_transitions": dict(sorted(route_transitions.items())),
        "candidate_reason_counts": dict(sorted(candidate_reasons.items())),
        "paired_strata": paired_strata,
        "paired_composite_bootstrap": bootstrap,
        "exploratory_mechanism_delta_quality_correlations": correlations,
        "system_aggregate": {
            "token_delta": candidate_tasks and (
                parents["candidate_summary"]["system_total_tokens"]
                - parents["control_summary"]["system_total_tokens"]
            ),
            "token_ratio": parents["candidate_summary"]["system_total_tokens"]
            / parents["control_summary"]["system_total_tokens"],
            "forward_wall_delta_seconds": parents["candidate_summary"]["forward_wall_seconds"]
            - parents["control_summary"]["forward_wall_seconds"],
            "forward_wall_ratio": parents["candidate_summary"]["forward_wall_seconds"]
            / parents["control_summary"]["forward_wall_seconds"],
            "search_call_delta": parents["candidate_summary"]["search_calls"]
            - parents["control_summary"]["search_calls"],
            "search_fetch_call_delta": parents["candidate_summary"]["search_fetch_calls"]
            - parents["control_summary"]["search_fetch_calls"],
        },
        "conclusions": {
            "whole_table_exact_count_improved": overall["delta"]["whole_table_success_delta"] > 0,
            "quality_composite_regressed": overall["delta"]["metrics"]["quality_composite"] < 0,
            "entity_row_item_and_column_all_regressed": all(
                overall["delta"]["metrics"][name] < 0
                for name in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
            ),
            "candidate_used_more_queries_fetches_pages_hosts_and_content": all(
                overall["delta"]["mechanism"][name] > 0
                for name in (
                    "queries_executed", "fetches_attempted", "usable_pages",
                    "unique_hosts", "content_chars",
                )
            ),
            "candidate_used_more_model_and_search_input_tokens": all(
                overall["delta"]["mechanism"][name] > 0
                for name in ("model_input_tokens", "search_input_tokens")
            ),
            "candidate_fallback_count_increased": overall["delta"]["fallback_table_delta"] > 0,
            "candidate_stop_stratum_regressed": paired_strata["candidate_stop"]["delta"]["metrics"]["quality_composite"] < 0,
            "candidate_expand_stratum_regressed": paired_strata["candidate_expand"]["delta"]["metrics"]["quality_composite"] < 0,
            "independent_generation_search_and_judge_variance_remain_confounders": True,
            "route_strata_establish_controller_causal_effect": False,
            "more_retrieval_is_universally_better": False,
            "raw_page_count_character_count_or_entropy_validated_as_credit": False,
            "historical_benchmark_metric_may_route_future_forward": False,
            "leaderboard_or_sota_established": False,
        },
        "next_work": {
            "candidate": "shared_prefix_information_bottleneck_evidence_projection",
            "candidate_rule_scope": [
                "fresh benchmark-external tasks",
                "same frozen discovery prefix and fetched page vector",
                "visible question and visible schema only",
                "source-stable row-or-target support groups",
                "fixed synthesis context budget",
                "entropy and information gain shadow only",
            ],
            "required_external_gate_arms": [
                "stable_first_seen_projection",
                "source_stable_support_aware_projection",
            ],
            "required_external_gate_controls": [
                "fresh target-cell-disjoint population",
                "same plan query search fetch and raw page bytes",
                "same synthesis model and maximum context/output budget",
                "projection decision frozen before synthesis",
                "fixed failure-as-zero denominator",
                "no resume retry skip selective rerun or revaluation",
                "task-cluster bootstrap",
            ],
            "go_conditions": [
                "candidate whole-table exact strictly improves",
                "candidate quality composite and item F1 do not regress",
                "candidate fallback and evaluator-invalid counts do not increase",
                "candidate synthesis input tokens do not increase",
                "candidate projected characters do not increase",
                "candidate retains all independently supported required target groups",
            ],
            "public_exact220_authorized_after_this_diagnosis": False,
        },
        "authorization": {
            "information_bottleneck_projector_build": True,
            "fresh_benchmark_external_shared_prefix_gate_design": True,
            "fresh_external_activation_or_launch": False,
            "public_dev64_or_exact220": False,
            "same_run_retry_resume_or_selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "paired_denominator_exact220": overall["control"]["n"]
        == overall["candidate"]["n"] == SELECTED,
        "route_transitions_cover_exact220": sum(route_transitions.values()) == SELECTED,
        "candidate_reasons_cover_exact220": sum(candidate_reasons.values()) == SELECTED,
        "bootstrap_denominator_exact220": sum(bootstrap["direction_counts"].values()) == SELECTED,
        "final_result_composite_delta_reconciles": math.isclose(
            overall["delta"]["metrics"]["quality_composite"],
            parents["candidate_result"]["metrics"]["all_220"]["quality_composite"]
            - parents["control_result"]["metrics"]["all_220"]["quality_composite"],
            rel_tol=0.0, abs_tol=1e-12,
        ),
        "final_result_exact_delta_reconciles": overall["delta"]["whole_table_success_delta"]
        == parents["candidate_result"]["metrics"]["all_220"]["whole_table_successes"]
        - parents["control_result"]["metrics"]["all_220"]["whole_table_successes"],
        "token_delta_reconciles": value["system_aggregate"]["token_delta"]
        == parents["candidate_result"]["metrics"]["all_220"]["system_total_tokens"]
        - parents["control_result"]["metrics"]["all_220"]["system_total_tokens"],
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.48.35 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24835_v24831_v24834_aggregate_only_evidence_budget_diagnosis"
        or copied.get("status")
        != "more_evidence_more_exact_but_lower_composite_causality_unresolved"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get("route_strata_establish_controller_causal_effect") is not False
        or copied.get("conclusions", {}).get("historical_benchmark_metric_may_route_future_forward") is not False
        or copied.get("authorization", {}).get("public_dev64_or_exact220") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.35 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.35 diagnosis is not reproducible")
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
    report = build()
    publish(ROOT / OUTPUT, report)
    print(json.dumps({
        "path": str(OUTPUT),
        "exact_delta": report["overall"]["delta"]["whole_table_success_delta"],
        "quality_composite_delta": report["overall"]["delta"]["metrics"]["quality_composite"],
        "projected_chars_delta": report["overall"]["delta"]["mechanism"]["projected_chars"],
        "model_input_tokens_delta": report["overall"]["delta"]["mechanism"]["model_input_tokens"],
        "authorization": report["authorization"],
    }, sort_keys=True))
