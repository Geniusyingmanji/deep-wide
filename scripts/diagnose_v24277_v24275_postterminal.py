#!/usr/bin/env python3
"""Content-free post-terminal diagnosis of the V2.42.75 dev64 NO-GO.

This offline report joins sealed outcomes by opaque identifier only after both
arms are complete.  It emits aggregate counts and distributions, never task
identifiers, questions, queries, URLs, pages, predictions, answers, labels, or
per-task scores.  The report is diagnostic and cannot authorize another
benchmark run or feed evaluator outcomes into a forward policy.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


OUTPUT = Path(
    "results/v24277_v24275_postterminal_mechanism_diagnosis_v1_20260802.json"
)
SELECTED = 64
METRICS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1", "score")
COST_FIELDS = (
    "search_calls",
    "search_tool_calls",
    "search_fetch_calls",
    "search_fetch_failures",
    "search_input_tokens",
    "search_output_tokens",
    "search_total_tokens",
    "model_input_tokens",
    "model_total_tokens",
    "system_total_tokens",
)
SOURCES = {
    "control_runtime": (
        Path("outputs/v24271_keyless_dev64_v1_20260802/candidate_runtime_predictions.jsonl"),
        "ff20e0e6f9f17056f816ce110116c50176d90c346a1ad543eb4f1386c317eab8",
    ),
    "control_summary": (
        Path("outputs/v24271_keyless_dev64_v1_20260802/candidate_run_summary.json"),
        "0872084e04da01824db16ca3e6d85d7851a047889c070fa2503bbe6a69841f45",
    ),
    "candidate_runtime": (
        Path("outputs/v24275_two_wave_dev64_v2_20260802/candidate_runtime_predictions.jsonl"),
        "4baff8a3b7a001bbfacb39f62bc72c1eab4666d6f05cc8bedd4f16126e8ac872",
    ),
    "candidate_summary": (
        Path("outputs/v24275_two_wave_dev64_v2_20260802/candidate_run_summary.json"),
        "3a85fea661941743ee3b70cbb03f3a6c86b08b473096d7cd997ea7b85a637614",
    ),
    "control_evaluator_summary": (
        Path("outputs/v24275_two_wave_dev64_v2_20260802/evaluator/control/conservative_summary.json"),
        "ee28a13bd2d1b06545cd581f0ac74a713a9d22acb9c99471e06686afe8f26645",
    ),
    "candidate_evaluator_summary": (
        Path("outputs/v24275_two_wave_dev64_v2_20260802/evaluator/candidate/conservative_summary.json"),
        "9111aa77e41e27f4cb0245c90376f2fa08188441a18f4fbc7a7e4d66319a8a33",
    ),
    "final_result": (
        Path("results/v24275_two_wave_dev64_result_v2_20260802.json"),
        "f70ee9ca9619e2b3c72fdfd1831e377eff9380f6fc8d28d7f312bd00cb9e36a1",
    ),
    "postresult_audit": (
        Path("results/v24275_two_wave_dev64_postresult_audit_v2_20260802.json"),
        "cff4b299e1dfe27e60a27569eb44192d8aa278eb732408e3e5544b322f303ca5",
    ),
    "postresult_audit_erratum": (
        Path("results/v24275_two_wave_dev64_postresult_audit_erratum_v1_20260802.json"),
        "b27e8292a7c342b51662920822d10223feded3adc8662062b2e706334b13b5e3",
    ),
    "execution_start": (
        Path("results/v24275_two_wave_dev64_execution_start_v2_20260802.json"),
        "7cf230f57830db1f6a1b1739139e82c1080bd1a6457f53d7b5e526293a9388ae",
    ),
    "forward_result": (
        Path("results/v24275_two_wave_dev64_forward_result_v2_20260802.json"),
        "c7d2428f01690919bdb3cc91c0ae76b9987029de58c6b96fbdbc999512460f10",
    ),
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.42.77 expected JSON objects")
    return values


def _ratio(candidate: float | int, control: float | int) -> float:
    if float(control) <= 0:
        raise RuntimeError("V2.42.77 ratio denominator is not positive")
    return float(candidate) / float(control)


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise RuntimeError("V2.42.77 empty distribution")
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise RuntimeError("V2.42.77 invalid distribution")
    return {
        "n": len(numbers),
        "mean": sum(numbers) / len(numbers),
        "median": statistics.median(numbers),
        "p25": _quantile(numbers, 0.25),
        "p75": _quantile(numbers, 0.75),
        "minimum": min(numbers),
        "maximum": max(numbers),
    }


def _direction(values: Sequence[float], *, positive_is_better: bool) -> dict[str, int]:
    epsilon = 1e-12
    better = sum(value > epsilon for value in values) if positive_is_better else sum(value < -epsilon for value in values)
    worse = sum(value < -epsilon for value in values) if positive_is_better else sum(value > epsilon for value in values)
    return {"better": better, "tie": len(values) - better - worse, "worse": worse}


def _metric_delta(
    identities: Sequence[str], control: Mapping[str, Any], candidate: Mapping[str, Any], metric: str
) -> list[float]:
    return [
        float(candidate[identity]["metrics"][metric])
        - float(control[identity]["metrics"][metric])
        for identity in identities
    ]


def _group(
    identities: Sequence[str],
    control_runtime: Mapping[str, Any],
    candidate_runtime: Mapping[str, Any],
    control_eval: Mapping[str, Any],
    candidate_eval: Mapping[str, Any],
) -> dict[str, Any]:
    if not identities:
        return {"selected": 0}
    value: dict[str, Any] = {
        "selected": len(identities),
        "mean_control_elapsed_seconds": sum(
            float(control_runtime[identity]["elapsed_seconds"]) for identity in identities
        )
        / len(identities),
        "mean_candidate_elapsed_seconds": sum(
            float(candidate_runtime[identity]["elapsed_seconds"]) for identity in identities
        )
        / len(identities),
        "mean_control_search_tokens": sum(
            int(control_runtime[identity]["cost"]["search_total_tokens"])
            for identity in identities
        )
        / len(identities),
        "mean_candidate_search_tokens": sum(
            int(candidate_runtime[identity]["cost"]["search_total_tokens"])
            for identity in identities
        )
        / len(identities),
        "mean_control_fetch_calls": sum(
            int(control_runtime[identity]["cost"]["search_fetch_calls"])
            for identity in identities
        )
        / len(identities),
        "mean_candidate_fetch_calls": sum(
            int(candidate_runtime[identity]["cost"]["search_fetch_calls"])
            for identity in identities
        )
        / len(identities),
        "quality_deltas": {},
    }
    for metric in METRICS:
        delta = _metric_delta(identities, control_eval, candidate_eval, metric)
        value["quality_deltas"][metric] = {
            "mean": sum(delta) / len(delta),
            "direction": _direction(delta, positive_is_better=True),
        }
    return value


def _bound_sources(root: Path) -> dict[str, dict[str, str]]:
    bound: dict[str, dict[str, str]] = {}
    for name, (relative, expected) in SOURCES.items():
        path = root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2.42.77 source drifted: {name}")
        bound[name] = {"path": str(relative), "sha256": expected}
    return bound


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    bound = _bound_sources(root)
    final = read_object(root / SOURCES["final_result"][0])
    audit = read_object(root / SOURCES["postresult_audit"][0])
    erratum = read_object(root / SOURCES["postresult_audit_erratum"][0])
    start = read_object(root / SOURCES["execution_start"][0])
    forward = read_object(root / SOURCES["forward_result"][0])
    control_summary = read_object(root / SOURCES["control_summary"][0])
    candidate_summary = read_object(root / SOURCES["candidate_summary"][0])
    if (
        final.get("status") != "development_gate_no_go"
        or final.get("selected_per_arm") != SELECTED
        or final.get("decision", {}).get("passed") is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or erratum.get("valid") is not True
        or final.get("claims", {}).get("public_full220_result") is not False
        or final.get("claims", {}).get("sota") is not False
        or forward.get("terminal_predictions") != SELECTED
    ):
        raise RuntimeError("V2.42.77 terminal parent state drifted")

    control_rows = _read_jsonl(root / SOURCES["control_runtime"][0])
    candidate_rows = _read_jsonl(root / SOURCES["candidate_runtime"][0])
    control_runtime = {row["opaque_id"]: row for row in control_rows}
    candidate_runtime = {row["opaque_id"]: row for row in candidate_rows}
    control_eval_value = read_object(root / SOURCES["control_evaluator_summary"][0])
    candidate_eval_value = read_object(root / SOURCES["candidate_evaluator_summary"][0])
    control_eval = {row["opaque_id"]: row for row in control_eval_value["per_task"]}
    candidate_eval = {row["opaque_id"]: row for row in candidate_eval_value["per_task"]}
    identities = sorted(control_runtime)
    if (
        len(identities) != SELECTED
        or set(identities) != set(candidate_runtime)
        or set(identities) != set(control_eval)
        or set(identities) != set(candidate_eval)
        or any(
            row.get("label_blind") is not True
            or row.get(
                "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            for row in [*control_rows, *candidate_rows]
        )
    ):
        raise RuntimeError("V2.42.77 paired identity or boundary drifted")

    cost: dict[str, Any] = {}
    for name in COST_FIELDS:
        control = int(control_summary["cost_totals"][name])
        candidate = int(candidate_summary["cost_totals"][name])
        cost[name] = {
            "control": control,
            "candidate": candidate,
            "candidate_minus_control": candidate - control,
            "candidate_over_control": _ratio(candidate, control),
        }

    paired: dict[str, Any] = {}
    for name, extractor in (
        ("elapsed_seconds", lambda row: float(row["elapsed_seconds"])),
        ("search_total_tokens", lambda row: float(row["cost"]["search_total_tokens"])),
        ("search_fetch_calls", lambda row: float(row["cost"]["search_fetch_calls"])),
        ("model_input_tokens", lambda row: float(row["cost"]["model_input_tokens"])),
    ):
        delta = [extractor(candidate_runtime[identity]) - extractor(control_runtime[identity]) for identity in identities]
        paired[name] = {
            "candidate_minus_control": _distribution(delta),
            "direction": _direction(delta, positive_is_better=False),
        }
    paired["quality"] = {}
    for metric in METRICS:
        delta = _metric_delta(identities, control_eval, candidate_eval, metric)
        paired["quality"][metric] = {
            "candidate_minus_control": _distribution(delta),
            "direction": _direction(delta, positive_is_better=True),
        }

    stop = [identity for identity in identities if candidate_runtime[identity]["telemetry"]["controller_stop"] == 1]
    expand = [identity for identity in identities if candidate_runtime[identity]["telemetry"]["controller_expand"] == 1]
    deadline = [identity for identity in identities if candidate_runtime[identity]["telemetry"]["hard_fetch_deadline_failures"] > 0]
    if len(stop) + len(expand) != SELECTED:
        raise RuntimeError("V2.42.77 controller partition drifted")

    control_retrieval_seconds = float(control_summary["stage_seconds_sum"]["search"]) + float(
        control_summary["stage_seconds_sum"]["fetch"]
    )
    candidate_retrieval_seconds = float(candidate_summary["stage_seconds_sum"]["search"]) + float(
        candidate_summary["stage_seconds_sum"]["fetch"]
    )
    batch_wall = int(forward["created_at_unix"]) - int(start["created_at_unix"])
    value = {
        "artifact_version": 1,
        "role": "v24277_v24275_postterminal_mechanism_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": {
            "selected_per_arm": SELECTED,
            "post_terminal_observational": True,
            "causal_claim_available": False,
            "consumed_dev64": True,
            "per_task_identity_or_content_persisted": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "bound_sources": bound,
        "forward_latency": {
            "sealed_timestamp_batch_wall_seconds": batch_wall,
            "candidate_throughput_tasks_per_second": SELECTED / batch_wall,
            "same_load_linear_exact220_extrapolation_seconds": 220 * batch_wall / SELECTED,
            "control_task_wall_sum_seconds": final["control"]["task_wall_sum_seconds"],
            "candidate_task_wall_sum_seconds": final["candidate"]["task_wall_sum_seconds"],
            "candidate_over_control_task_wall_sum": final["decision"]["task_wall_sum_ratio"],
            "control_retrieval_stage_sum_seconds": control_retrieval_seconds,
            "candidate_retrieval_stage_sum_seconds": candidate_retrieval_seconds,
            "candidate_over_control_retrieval_stage_sum": _ratio(
                candidate_retrieval_seconds, control_retrieval_seconds
            ),
            "control_synthesis_stage_sum_seconds": control_summary["stage_seconds_sum"]["synthesis"],
            "candidate_synthesis_stage_sum_seconds": candidate_summary["stage_seconds_sum"]["synthesis"],
            "candidate_over_control_synthesis_stage_sum": _ratio(
                candidate_summary["stage_seconds_sum"]["synthesis"],
                control_summary["stage_seconds_sum"]["synthesis"],
            ),
        },
        "aggregate_cost": cost,
        "candidate_controller": {
            "stop_tasks": len(stop),
            "expand_tasks": len(expand),
            "logical_queries": candidate_summary["telemetry_totals"]["logical_query_count"],
            "fetch_requested": candidate_summary["telemetry_totals"]["fetch_requested_source_count"],
            "fetch_usable": candidate_summary["telemetry_totals"]["fetch_usable_page_count"],
            "hard_fetch_deadline_events": candidate_summary["telemetry_totals"]["hard_fetch_deadline_failures"],
            "tasks_with_hard_fetch_deadline": len(deadline),
            "fetch_helper_failures": candidate_summary["telemetry_totals"]["fetch_helper_failures"],
            "unrecoverable_search_failures": candidate_summary["telemetry_totals"]["raw_unrecoverable_failure_count"],
        },
        "paired_distributions": paired,
        "controller_groups": {
            "stop": _group(stop, control_runtime, candidate_runtime, control_eval, candidate_eval),
            "expand": _group(expand, control_runtime, candidate_runtime, control_eval, candidate_eval),
            "hard_fetch_deadline": _group(deadline, control_runtime, candidate_runtime, control_eval, candidate_eval),
        },
        "gate": {
            "status": final["decision"]["status"],
            "failed_checks": sorted(
                name for name, passed in final["decision"]["checks"].items() if not passed
            ),
            "quality_checks_all_passed": all(
                final["decision"]["checks"][name]
                for name in (
                    "quality_composite_delta",
                    "entity_acc_delta",
                    "f1_by_row_delta",
                    "f1_by_item_delta",
                    "column_f1_delta",
                    "whole_table_success_delta",
                    "model_generated_table_delta",
                )
            ),
            "exact220_design_authorized": False,
            "exact220_launch_authorized": False,
            "sota_claim_authorized": False,
        },
        "mechanism_conclusions": {
            "fetch_reduction_translated_to_search_token_reduction": False,
            "search_input_tokens_increased": cost["search_input_tokens"]["candidate_minus_control"] > 0,
            "search_total_token_reduction_fraction": 1.0 - cost["search_total_tokens"]["candidate_over_control"],
            "fetch_call_reduction_fraction": 1.0 - cost["search_fetch_calls"]["candidate_over_control"],
            "synthesis_stage_materially_reduced": False,
            "next_primary_cost_axis": "native_search_input_context_and_request_count",
            "next_secondary_cost_axis": "structured_synthesis_output_and_latency",
        },
        "next_experiment_contract": {
            "neutral_low_vs_medium_search_context_pair_required": True,
            "neutral_bounded_structured_synthesis_pair_required": True,
            "controller_objective": "calibrated_expected_terminal_loss_reduction_per_predicted_search_token",
            "dev64_may_be_reused_as_new_confirmation": False,
            "next_confirmatory_primary_scope": "historically_evaluated_test156_not_used_in_v24275_per_task_diagnosis_with_all220_secondary",
            "successor_must_be_frozen_before_confirmation": True,
            "new_benchmark_launch_authorized_by_this_report": False,
        },
        "source_policy": {
            "question_query_url_host_page_prediction_answer_or_task_id_persisted": False,
            "benchmark_category_or_split_used_for_grouping": False,
            "per_task_metric_or_cost_row_persisted": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "benchmark_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate_report(value)
    return value


def validate_report(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    scope = value.get("scope")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    gate = value.get("gate")
    if (
        value.get("role") != "v24277_v24275_postterminal_mechanism_diagnosis"
        or not isinstance(scope, Mapping)
        or scope.get("selected_per_arm") != SELECTED
        or scope.get("post_terminal_observational") is not True
        or scope.get("causal_claim_available") is not False
        or scope.get("per_task_identity_or_content_persisted") is not False
        or not isinstance(gate, Mapping)
        or gate.get("status") != "no_go"
        or gate.get("failed_checks")
        != ["candidate_hard_fetch_deadline_failures", "search_token_ratio", "task_wall_sum_ratio"]
        or gate.get("exact220_launch_authorized") is not False
        or value.get("candidate_controller", {}).get("stop_tasks")
        + value.get("candidate_controller", {}).get("expand_tasks")
        != SELECTED
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or value.get("bound_sources") != _bound_sources(ROOT)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.77 diagnosis drifted")


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / OUTPUT, report)
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}, sort_keys=True))
