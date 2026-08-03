#!/usr/bin/env python3
"""Post-terminal content-free diagnosis of the V2.42.97 paired-dev64 NO-GO."""

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

from deepwide_agent.v24297_forward_contract import (  # noqa: E402
    ARMS,
    payload_sha256,
    sha256,
)


OUTPUT = Path("results/v24298_v24297_paired_dev64_postterminal_diagnosis_v1_20260803.json")
RESULT = Path("results/v24297_paired_dev64_result_v1_20260803.json")
POSTAUDIT = Path("results/v24297_paired_dev64_postresult_audit_v1_20260803.json")
FORWARD_RESULT = Path("results/v24297_paired_dev64_forward_result_v1_20260803.json")
ROOT_OUTPUT = Path("outputs/v24297_paired_dev64_v1_20260803")
TASK_ROOT = ROOT_OUTPUT / "tasks"
EVAL_ROOT = ROOT_OUTPUT / "fresh_both_arm_evaluator"
SUMMARY = {arm: EVAL_ROOT / arm / "conservative_summary.json" for arm in ARMS}
JOINED = {
    arm: EVAL_ROOT / arm / "terminal_outcomes_evaluator_joined.jsonl" for arm in ARMS
}
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)
BOOTSTRAP_SEED = 24298
BOOTSTRAP_RESAMPLES = 10_000


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.98 expected object: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


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
        "estimand": "mean paired composite delta on frozen fresh dev64 only",
        "percentile_95_interval": [estimates[249], estimates[9749]],
        "future_task_or_held_out_population_inference": False,
        "confirmatory": False,
    }


def _task_telemetry(root: Path, arm: str, position: int) -> dict[str, Any]:
    directory = root / TASK_ROOT / arm / f"task_{position:04d}"
    result = _read(directory / "result.json")["result"]
    health = _read(directory / "transport_health.json")
    retrieval = result.get("staged_reserve_retrieval") or result.get(
        "two_wave_retrieval"
    ) or {}
    receipt = retrieval.get("receipt") or {}
    model_events = list((result.get("telemetry") or {}).get("model_events") or [])
    return {
        "completion_kind": str(result["completion_kind"]),
        "model_generated": result["completion_kind"] in MODEL_GENERATED,
        "admitted_model_calls": int(result["budget"]["admitted_model_calls"]),
        "provider_requests": int(result["cost"]["model"]["requests"]),
        "provider_attempts": int(result["cost"]["model"]["attempts"]),
        "failed_model_stages": [
            str(event["stage"]) for event in model_events if event["success"] is False
        ],
        "controller": str((receipt.get("controller") or {}).get("decision", "none")),
        "reserved_reason": str(
            (receipt.get("reserved_stage") or {}).get("reason", "not_applicable")
        ),
        "selected_tail_count": int(
            (receipt.get("reserved_stage") or {}).get("selected_tail_count", 0)
        ),
        "usable_pages": int((receipt.get("total") or {}).get("usable_pages", 0)),
        "fetches_attempted": int(
            (receipt.get("total") or {}).get("fetches_attempted", 0)
        ),
        "retrieval_status": str(retrieval.get("status", "absent")),
        "retrieval_failure_type": retrieval.get("failure_type"),
        "hard_fetch_deadline_failures": int(health["hard_fetch_deadline_failures"]),
        "fetch_helper_failures": int(health["fetch_helper_failures"]),
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root / RESULT)
    post = _read(root / POSTAUDIT)
    forward = _read(root / FORWARD_RESULT)
    if (
        result.get("status") != "development_gate_no_go"
        or result.get("selected_per_arm") != 64
        or result.get("failure_as_zero") is not True
        or result.get("decision", {}).get("passed") is not False
        or not _sealed(result, "result_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or forward.get("terminal_predictions_per_arm")
        != {arm: 64 for arm in ARMS}
        or not _sealed(forward, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.98 audited parent result drifted")

    summaries = {arm: _read(root / SUMMARY[arm]) for arm in ARMS}
    per_task = {
        arm: {row["opaque_id"]: row for row in summaries[arm]["per_task"]}
        for arm in ARMS
    }
    order = [row["opaque_id"] for row in _read_jsonl(root / JOINED["baseline"])]
    candidate_order = [
        row["opaque_id"] for row in _read_jsonl(root / JOINED["candidate"])
    ]
    if (
        len(order) != 64
        or candidate_order != order
        or any(set(per_task[arm]) != set(order) for arm in ARMS)
    ):
        raise RuntimeError("V2.42.98 paired task identity drifted")

    task_telemetry = {
        arm: [_task_telemetry(root, arm, position) for position in range(1, 65)]
        for arm in ARMS
    }
    fallback_positions = {
        arm: [
            position
            for position, row in enumerate(task_telemetry[arm], start=1)
            if not row["model_generated"]
        ]
        for arm in ARMS
    }
    failure_taxonomy: dict[str, Any] = {}
    transport: dict[str, Any] = {}
    for arm in ARMS:
        stage_failures = Counter(
            stage
            for row in task_telemetry[arm]
            for stage in row["failed_model_stages"]
        )
        fallback_stages = Counter(
            stage
            for row in task_telemetry[arm]
            if not row["model_generated"]
            for stage in row["failed_model_stages"]
        )
        failure_taxonomy[arm] = {
            "fallback_count": len(fallback_positions[arm]),
            "all_failed_model_events_by_stage": dict(sorted(stage_failures.items())),
            "fallback_failed_model_events_by_stage": dict(sorted(fallback_stages.items())),
            "fallback_with_retrieval_failure": sum(
                row["retrieval_status"] == "failed"
                for row in task_telemetry[arm]
                if not row["model_generated"]
            ),
            "fallback_with_fetch_helper_failure": sum(
                row["fetch_helper_failures"] > 0
                for row in task_telemetry[arm]
                if not row["model_generated"]
            ),
        }
        transport[arm] = {
            "hard_fetch_deadline_failures": sum(
                row["hard_fetch_deadline_failures"] for row in task_telemetry[arm]
            ),
            "fetch_helper_failures": sum(
                row["fetch_helper_failures"] for row in task_telemetry[arm]
            ),
        }

    all_deltas: list[float] = []
    groups: dict[str, list[float]] = {}
    fallback_pairs: list[dict[str, Any]] = []
    for position, opaque_id in enumerate(order, start=1):
        delta_by_metric = {
            metric: float(per_task["candidate"][opaque_id]["metrics"][metric])
            - float(per_task["baseline"][opaque_id]["metrics"][metric])
            for metric in QUALITY
        }
        composite = _mean(list(delta_by_metric.values()))
        all_deltas.append(composite)
        candidate_trace = task_telemetry["candidate"][position - 1]
        key = (
            "low_coverage_diversity_tail"
            if candidate_trace["reserved_reason"] == "low_coverage_diversity_tail"
            else "other_candidate_paths"
        )
        groups.setdefault(key, []).append(composite)
        if position in set(fallback_positions["baseline"] + fallback_positions["candidate"]):
            fallback_pairs.append(
                {
                    "position": position,
                    "baseline_completion_kind": task_telemetry["baseline"][position - 1][
                        "completion_kind"
                    ],
                    "candidate_completion_kind": candidate_trace["completion_kind"],
                    "baseline_failed_model_stages": task_telemetry["baseline"][position - 1][
                        "failed_model_stages"
                    ],
                    "candidate_failed_model_stages": candidate_trace[
                        "failed_model_stages"
                    ],
                    "candidate_reserved_reason": candidate_trace["reserved_reason"],
                    "paired_composite_delta": composite,
                }
            )

    value = {
        "artifact_version": 1,
        "role": "v24298_v24297_paired_dev64_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_sha256": sha256(root / RESULT),
            "postresult_audit_sha256": sha256(root / POSTAUDIT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            **{
                f"{arm}_summary_sha256": sha256(root / SUMMARY[arm]) for arm in ARMS
            },
        },
        "boundary": {
            "selected_per_arm": 64,
            "fixed_denominator_failure_as_zero": True,
            "both_arm_prediction_freezes_preceded_evaluator": True,
            "same_judge_full_both_arm_evaluation": True,
            "postterminal_only": True,
            "fed_back_into_same_forward": False,
            "selective_retry_or_error_revaluation": False,
            "question_prediction_answer_instance_or_opaque_id_emitted": False,
        },
        "result_summary": {
            "decision": "no_go",
            "failed_checks": result["decision"]["failed_checks"],
            "candidate_minus_baseline": result["decision"]["candidate_minus_baseline"],
            "system_token_ratio": result["decision"]["system_token_ratio"],
            "task_wall_sum_ratio": result["decision"]["task_wall_sum_ratio"],
        },
        "reliability": {
            "failure_taxonomy": failure_taxonomy,
            "transport": transport,
            "fallback_pairs": fallback_pairs,
            "candidate_extra_fallbacks": len(fallback_positions["candidate"])
            - len(fallback_positions["baseline"]),
        },
        "paired_quality": {
            "all64_composite": {
                **_distribution(all_deltas),
                "exploratory_task_bootstrap": _bootstrap(all_deltas),
            },
            "candidate_path_groups": {
                name: _distribution(values) for name, values in sorted(groups.items())
            },
        },
        "mechanism_activation": {
            "low_coverage_diversity_tail_tasks": result["candidate_health"][
                "low_coverage_diversity_tail"
            ],
            "selected_tail_count": result["candidate_health"]["selected_tail_count"],
            "reserved_usable_pages": result["candidate_health"][
                "reserved_usable_pages"
            ],
            "hosted_search_requests_added_by_reserved": result["candidate_health"][
                "hosted_search_requests_added_by_reserved"
            ],
            "cache_miss_count": result["candidate_health"]["cache_miss_count"],
            "cache_serve_network_fetches": result["candidate_health"][
                "cache_serve_network_fetches"
            ],
        },
        "conclusions": {
            "quality_direction_positive": result["decision"]["candidate_minus_baseline"][
                "quality_composite"
            ]
            > 0,
            "mechanism_naturally_engaged": result["candidate_health"][
                "low_coverage_diversity_tail"
            ]
            > 0,
            "candidate_transport_worse_than_baseline": transport["candidate"][
                "hard_fetch_deadline_failures"
            ]
            > transport["baseline"]["hard_fetch_deadline_failures"],
            "candidate_extra_fallbacks_explained_by_model_stage_failures": all(
                bool(row["candidate_failed_model_stages"])
                for row in fallback_pairs
                if row["candidate_completion_kind"] not in MODEL_GENERATED
            ),
            "reliability_gate_passed": False,
            "exact220_authorized": False,
            "sota": False,
        },
        "next_experiment": {
            "stage": "neutral_provider_failure_recovery_before_any_new_benchmark",
            "target": "reuse only an otherwise-unused third logical model-call slot after synthesis provider failure; preserve the three-call cap and all retrieval budgets",
            "must_not": [
                "rerun_or_revalue_v24297_tasks",
                "increase_search_query_or_fetch_budget",
                "read_mapping_gold_category_question_type_or_evaluator_at_runtime",
            ],
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
        raise RuntimeError("V2.42.98 diagnosis drifted")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "decision": report["result_summary"]["decision"],
                "candidate_extra_fallbacks": report["reliability"][
                    "candidate_extra_fallbacks"
                ],
            },
            sort_keys=True,
        )
    )
