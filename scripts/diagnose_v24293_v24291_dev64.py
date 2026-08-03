#!/usr/bin/env python3
"""Post-terminal, content-free diagnosis of the V2.42.91 dev64 NO-GO."""

from __future__ import annotations

import json
import os
import random
import statistics
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24291_forward_contract import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24293_v24291_dev64_postterminal_diagnosis_v1_20260803.json")
RESULT = Path("results/v24291_dev64_result_v1_20260803.json")
POSTAUDIT = Path("results/v24291_dev64_postresult_audit_v1_20260803.json")
RECOVERY_AUDIT = Path("results/v24292_dev64_evaluator_recovery_postresult_audit_v1_20260803.json")
RUNTIME = Path("outputs/v24291_low_coverage_dev64_v1_20260803/candidate_runtime_predictions.jsonl")
TASK_ROOT = Path("outputs/v24291_low_coverage_dev64_v1_20260803/tasks")
EVAL_ROOT = Path("outputs/v24291_low_coverage_dev64_v1_20260803/evaluator")
CONTROL_SUMMARY = EVAL_ROOT / "control/conservative_summary.json"
CANDIDATE_SUMMARY = EVAL_ROOT / "candidate/conservative_summary.json"
CONTROL_JOINED = EVAL_ROOT / "control/terminal_outcomes_evaluator_joined.jsonl"
CANDIDATE_JOINED = EVAL_ROOT / "candidate/terminal_outcomes_evaluator_joined.jsonl"
CONTROL_EVAL = EVAL_ROOT / "control/official_eval_results.jsonl"
CANDIDATE_EVAL = EVAL_ROOT / "candidate/official_eval_results.jsonl"
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
BOOTSTRAP_SEED = 24293
BOOTSTRAP_RESAMPLES = 10_000


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.93 expected object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _distribution(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "mean": _mean(values),
        "median": statistics.median(values) if values else 0.0,
        "positive": sum(value > 0 for value in values),
        "zero": sum(value == 0 for value in values),
        "negative": sum(value < 0 for value in values),
        "minimum": min(values) if values else 0.0,
        "maximum": max(values) if values else 0.0,
    }


def _bootstrap(values: list[float]) -> dict[str, Any]:
    generator = random.Random(BOOTSTRAP_SEED)
    estimates = sorted(
        _mean([values[generator.randrange(len(values))] for _ in values])
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return {
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "estimand": "mean paired composite delta on the fixed consumed dev-validation64 only",
        "percentile_95_interval": [estimates[249], estimates[9749]],
        "future_task_or_held_out_population_inference": False,
        "confirmatory": False,
    }


def _error_class(error: str) -> str:
    if "out-of-range metrics" in error:
        return "official_evaluator_out_of_range_metric"
    if "internal error" in error:
        return "official_evaluator_internal_error"
    return "other_evaluator_error"


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root / RESULT)
    post = _read(root / POSTAUDIT)
    recovery = _read(root / RECOVERY_AUDIT)
    if (
        result.get("status") != "development_gate_no_go"
        or result.get("selected_per_arm") != 64
        or result.get("failure_as_zero") is not True
        or result.get("decision", {}).get("passed") is not False
        or not _sealed(result, "result_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or recovery.get("audit_valid") is not True
        or recovery.get("findings") != []
        or not _sealed(recovery, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.93 audited result parent drifted")

    control_summary = _read(root / CONTROL_SUMMARY)
    candidate_summary = _read(root / CANDIDATE_SUMMARY)
    control = {row["opaque_id"]: row for row in control_summary["per_task"]}
    candidate = {row["opaque_id"]: row for row in candidate_summary["per_task"]}
    runtime = _read_jsonl(root / RUNTIME)
    if len(control) != 64 or set(control) != set(candidate) or [row["opaque_id"] for row in runtime] != list(control):
        raise RuntimeError("V2.42.93 paired task identity drifted")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    budget_blocked: list[dict[str, Any]] = []
    for position, row in enumerate(runtime, start=1):
        opaque_id = row["opaque_id"]
        telemetry = row["rescue_telemetry"]
        route = "expand" if telemetry["controller_expand"] else "stop"
        reason = "controller_stop"
        if route == "expand":
            task = _read(root / TASK_ROOT / f"task_{position:04d}/result.json")["result"]
            receipt = task["two_wave_retrieval"]["receipt"]
            reason = receipt["rescue"]["reason"]
            remaining = max(
                0,
                int(receipt["two_wave_policy"]["wave1_fetches"])
                + int(receipt["two_wave_policy"]["wave2_fetches"])
                - int(receipt["total_before_rescue"]["fetches_attempted"]),
            )
            if reason == "no_tail_or_remaining_budget":
                budget_blocked.append(
                    {
                        "tail_candidates": int(receipt["rescue"]["tail_candidates"]),
                        "remaining_fetch_capacity": remaining,
                        "usable_pages_before_rescue": int(receipt["total_before_rescue"]["usable_pages"]),
                        "unique_hosts_before_rescue": int(receipt["total_before_rescue"]["unique_hosts"]),
                        "content_chars_before_rescue": int(receipt["total_before_rescue"]["content_chars"]),
                        "required_column_count": int(receipt["required_column_count"]),
                    }
                )
        deltas = {
            name: float(candidate[opaque_id]["metrics"][name])
            - float(control[opaque_id]["metrics"][name])
            for name in QUALITY
        }
        deltas["quality_composite"] = _mean([deltas[name] for name in QUALITY])
        deltas["score"] = float(candidate[opaque_id]["metrics"]["score"]) - float(control[opaque_id]["metrics"]["score"])
        deltas["control_evaluator_valid"] = bool(control[opaque_id]["evaluator_valid"])
        deltas["candidate_evaluator_valid"] = bool(candidate[opaque_id]["evaluator_valid"])
        grouped.setdefault((route, reason), []).append(deltas)

    group_report: dict[str, Any] = {}
    all_composite: list[float] = []
    for (route, reason), values in sorted(grouped.items()):
        composites = [float(row["quality_composite"]) for row in values]
        all_composite.extend(composites)
        group_report[f"{route}:{reason}"] = {
            "selected": len(values),
            "candidate_evaluator_valid": sum(row["candidate_evaluator_valid"] for row in values),
            "control_evaluator_valid": sum(row["control_evaluator_valid"] for row in values),
            "whole_table_score_delta_sum": sum(float(row["score"]) for row in values),
            "mean_candidate_minus_control": {
                **{name: _mean([float(row[name]) for row in values]) for name in QUALITY},
                "quality_composite": _mean(composites),
            },
            "paired_composite_distribution": _distribution(composites),
        }

    control_joined = {row["opaque_id"]: row for row in _read_jsonl(root / CONTROL_JOINED)}
    candidate_joined = {row["opaque_id"]: row for row in _read_jsonl(root / CANDIDATE_JOINED)}
    changed = sum(control_joined[key].get("prediction") != candidate_joined[key].get("prediction") for key in control_joined)
    errors: dict[str, Any] = {}
    for arm, path in (("control", CONTROL_EVAL), ("candidate", CANDIDATE_EVAL)):
        rows = _read_jsonl(root / path)
        taxonomy = Counter(_error_class(str(row["error"])) for row in rows if row.get("error"))
        errors[arm] = {
            "selected": len(rows),
            "evaluator_valid": len(rows) - sum(taxonomy.values()),
            "evaluator_invalid": sum(taxonomy.values()),
            "error_taxonomy": dict(sorted(taxonomy.items())),
            "selective_revaluation_performed": False,
        }

    value = {
        "artifact_version": 1,
        "role": "v24293_v24291_dev64_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_sha256": sha256(root / RESULT),
            "postresult_audit_sha256": sha256(root / POSTAUDIT),
            "recovery_postresult_audit_sha256": sha256(root / RECOVERY_AUDIT),
            "control_summary_sha256": sha256(root / CONTROL_SUMMARY),
            "candidate_summary_sha256": sha256(root / CANDIDATE_SUMMARY),
            "candidate_runtime_sha256": sha256(root / RUNTIME),
        },
        "boundary": {
            "selected_per_arm": 64,
            "fixed_denominator_failure_as_zero": True,
            "candidate_prediction_freeze_preceded_evaluator": True,
            "same_judge_full_both_arm_evaluation": True,
            "postterminal_only": True,
            "fed_back_into_same_forward": False,
            "question_prediction_answer_instance_or_opaque_id_emitted": False,
        },
        "result_summary": {
            "decision": "no_go",
            "failed_checks": result["decision"]["failed_checks"],
            "candidate_minus_control": result["decision"]["candidate_minus_control"],
            "system_token_ratio": result["decision"]["system_token_ratio"],
            "task_wall_sum_ratio": result["decision"]["task_wall_sum_ratio"],
            "changed_predictions": changed,
            "identical_predictions": 64 - changed,
        },
        "paired_groups": group_report,
        "paired_all64_composite": {
            **_distribution(all_composite),
            "exploratory_task_bootstrap": _bootstrap(all_composite),
        },
        "mechanism_activation": {
            "controller_stop": result["candidate_health"]["controller_stop"],
            "controller_expand": result["candidate_health"]["controller_expand"],
            "rescue_triggered": result["candidate_health"]["rescue_triggered"],
            "budget_blocked_low_coverage_tasks": len(budget_blocked),
            "budget_blocked_aggregate": {
                "tail_candidates": sorted(row["tail_candidates"] for row in budget_blocked),
                "remaining_fetch_capacity": sorted(row["remaining_fetch_capacity"] for row in budget_blocked),
                "usable_pages_before_rescue": sorted(row["usable_pages_before_rescue"] for row in budget_blocked),
                "required_column_count": sorted(row["required_column_count"] for row in budget_blocked),
            },
        },
        "evaluator_health": errors,
        "conclusions": {
            "quality_direction_positive": result["decision"]["candidate_minus_control"]["quality_composite"] > 0,
            "whole_table_improved": result["decision"]["candidate_minus_control"]["whole_table_successes"] > 0,
            "quality_gain_statistically_resolved": False,
            "quality_gain_attributable_to_rescue": False,
            "rescue_mechanism_engaged": False,
            "reserved_tail_capacity_required_before_any_new_benchmark": True,
            "exact220_authorized": False,
            "sota": False,
        },
        "next_experiment": {
            "stage": "neutral_and_synthetic_only",
            "policy": "within the same ten-fetch cap, reserve two post-expand slots and select top-ranked versus diversity-tail adaptively after eight fetch outcomes",
            "nominal_schedule": "6_first_wave_plus_2_second_wave_plus_2_reserved",
            "additional_hosted_search_requests": 0,
            "maximum_total_fetches": 10,
            "benchmark_dev64_or_exact220_launch": False,
        },
        "authorization": {
            "training_credit_assignment": False,
            "additional_dev64": False,
            "exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> None:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.42.93 diagnosis drifted")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish(ROOT / OUTPUT, report)
    print(json.dumps({"path": str(OUTPUT), "decision": report["result_summary"]["decision"]}, sort_keys=True))
