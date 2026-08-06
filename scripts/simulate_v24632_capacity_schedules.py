#!/usr/bin/env python3
"""Deterministic content-free schedule simulation after V2.46.31.

The simulation calibrates four anonymous service-time scenarios from the 186
model-generated V2.46.30 task receipts.  Aggregate model-slot wait is not
identified per effect, so the calibration removes aggregate wait from total
model-event time and allocates the residual proportionally across provider
requests.  The resulting p25/p50/p75/p95 scenarios are sensitivity analyses,
not causal counterfactuals or exact runtime predictions.

The synthetic workload has 220 anonymous jobs and exactly 462 model effects:
220 plan, 220 initial synthesis, 20 recovery, and 2 repair effects.  No task
content, task identity, prediction, evaluator row, or score is read or emitted.
"""

from __future__ import annotations

import heapq
import json
import math
import os
import re
import statistics
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    read_object,
    sha256,
)
from scripts import diagnose_v24631_v24630_capacity_postresult as parent  # noqa: E402


OUTPUT = Path("results/v24632_content_free_capacity_simulation_v1_20260806.json")
PARENT_AUDIT = Path(
    "results/v24631_v24630_content_free_capacity_diagnosis_audit_v1_20260806.json"
)
ACTIVE_CAPS = (8, 12, 16, 20, 24, 32)
DEADLINES = (150, 180, 210, 240)
POLICIES = ("fifo", "synthesis_priority", "reserve2")
POLICY_ORDER = {name: index for index, name in enumerate(POLICIES)}
SCENARIO_QUANTILES = (0.25, 0.50, 0.75, 0.95)
SCENARIO_NAMES = ("p25", "p50", "p75", "p95")
RECOVERY_EFFECTS = 20
REPAIR_EFFECTS = 2
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_EFFECT_SECONDS = 0.05
TAIL_WALL_CEILING_SECONDS = 1800.0
MODEL_GENERATED = frozenset(
    {"primary", "normalized_primary", "repaired", "normalized_repaired"}
)
SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(path: Path) -> Path:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.46.32 expected ordinary repository file: {path}")
    return path


def _task_directories(root: Path) -> list[Path]:
    base = root / TASK_ROOT
    expected = [
        base / f"task_{position:04d}"
        for position in range(1, SELECTED_COUNT + 1)
    ]
    if (
        base.is_symlink()
        or not base.is_dir()
        or any(path.is_symlink() or not path.is_dir() for path in expected)
        or sorted(path for path in base.glob("task_*") if path.is_dir()) != expected
    ):
        raise RuntimeError("V2.46.32 exact-220 task partition drifted")
    return expected


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("V2.46.32 empty calibration vector")
    position = (len(ordered) - 1) * float(probability)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _summary(values: Sequence[float]) -> dict[str, Any]:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) or value < 0 for value in numbers):
        raise ValueError("V2.46.32 invalid calibration vector")
    return {
        "count": len(numbers),
        "mean": round(statistics.fmean(numbers), 6),
        "minimum": round(min(numbers), 6),
        "p25": round(_quantile(numbers, 0.25), 6),
        "p50": round(_quantile(numbers, 0.50), 6),
        "p75": round(_quantile(numbers, 0.75), 6),
        "p95": round(_quantile(numbers, 0.95), 6),
        "maximum": round(max(numbers), 6),
    }


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    diagnosis = read_object(_ordinary(root / parent.OUTPUT))
    audit = read_object(_ordinary(root / PARENT_AUDIT))
    parent.validate_report(root, diagnosis)
    if (
        not _sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("diagnosis", {}).get("sha256") != sha256(root / parent.OUTPUT)
        or audit.get("authorization", {}).get(
            "deterministic_content_free_simulation"
        )
        is not True
        or diagnosis.get("authorization", {}).get(
            "deterministic_content_free_simulation"
        )
        is not True
    ):
        raise RuntimeError("V2.46.32 parent diagnosis or audit drifted")
    return diagnosis, audit


def _calibration(root: Path) -> dict[str, Any]:
    vectors: dict[str, list[float]] = {
        "plan_service_seconds": [],
        "postplan_service_seconds": [],
        "retrieval_seconds": [],
        "local_completion_seconds": [],
    }
    tasks = 0
    provider_requests = 0
    for directory in _task_directories(root):
        result_path = directory / parent.RESULT_NAME
        if not result_path.is_file() or result_path.is_symlink():
            continue
        result, model = parent._validate_complete_bundle(directory)
        if str(result["completion_kind"]) not in MODEL_GENERATED:
            continue
        tasks += 1
        events = result["telemetry"]["model_events"]
        observed_model_seconds = sum(float(event["elapsed_seconds"]) for event in events)
        requests = sum(int(event["requests_delta"]) for event in events)
        if requests <= 0 or observed_model_seconds <= 0:
            raise RuntimeError("V2.46.32 model-generated timing is incomplete")
        residual_service = max(
            MINIMUM_EFFECT_SECONDS * requests,
            observed_model_seconds - float(model["total_wait_seconds"]),
        )
        allocated = 0
        for event in events:
            count = int(event["requests_delta"])
            if count <= 0:
                raise RuntimeError("V2.46.32 successful event lacks provider request")
            seconds = max(
                MINIMUM_EFFECT_SECONDS,
                residual_service
                * float(event["elapsed_seconds"])
                / observed_model_seconds
                / count,
            )
            target = (
                "plan_service_seconds"
                if event["stage"] == "plan"
                else "postplan_service_seconds"
            )
            vectors[target].extend([seconds] * count)
            allocated += count
        if allocated != requests:
            raise RuntimeError("V2.46.32 provider request allocation drifted")
        provider_requests += requests
        timing = result["attributed_timing"]
        vectors["retrieval_seconds"].append(
            float(timing["retrieval_envelope_seconds"])
        )
        vectors["local_completion_seconds"].append(
            float(timing["controller_and_adapter_seconds"])
            + float(timing["cache_serve_seconds"])
            + float(timing["unattributed_runtime_seconds"])
        )
    if (
        tasks != 186
        or len(vectors["plan_service_seconds"]) != 186
        or len(vectors["postplan_service_seconds"]) != 189
        or len(vectors["retrieval_seconds"]) != 186
        or len(vectors["local_completion_seconds"]) != 186
        or provider_requests != 375
    ):
        raise RuntimeError("V2.46.32 calibration denominator drifted")
    scenarios = {
        name: {
            "plan_service_seconds": round(
                _quantile(vectors["plan_service_seconds"], probability), 6
            ),
            "postplan_service_seconds": round(
                _quantile(vectors["postplan_service_seconds"], probability), 6
            ),
            "retrieval_seconds": round(
                _quantile(vectors["retrieval_seconds"], probability), 6
            ),
            "local_completion_seconds": round(
                _quantile(vectors["local_completion_seconds"], probability), 6
            ),
        }
        for name, probability in zip(SCENARIO_NAMES, SCENARIO_QUANTILES)
    }
    return {
        "model_generated_tasks": tasks,
        "provider_requests": provider_requests,
        "vector_summaries": {
            name: _summary(values) for name, values in vectors.items()
        },
        "scenarios": scenarios,
        "limitations": {
            "fallback_tasks_excluded_as_right_censored": True,
            "aggregate_slot_wait_not_identified_per_effect": True,
            "residual_service_allocated_proportionally_by_observed_event_time": True,
            "recovery_and_repair_use_shared_postplan_service_distribution": True,
            "independent_identically_distributed_service_times_assumed": True,
            "live_provider_queueing_or_correlation_modeled": False,
            "exact_runtime_or_causal_counterfactual_claimed": False,
        },
    }


def _effect_sets() -> tuple[frozenset[int], frozenset[int]]:
    recoveries = {
        min(
            SELECTED_COUNT - 1,
            int((index + 0.5) * SELECTED_COUNT / RECOVERY_EFFECTS),
        )
        for index in range(RECOVERY_EFFECTS)
    }
    repairs: set[int] = set()
    for index in range(REPAIR_EFFECTS):
        ordinal = min(
            SELECTED_COUNT - 1,
            int((index + 0.25) * SELECTED_COUNT / REPAIR_EFFECTS),
        )
        while ordinal in recoveries or ordinal in repairs:
            ordinal = (ordinal + 1) % SELECTED_COUNT
        repairs.add(ordinal)
    if len(recoveries) != RECOVERY_EFFECTS or len(repairs) != REPAIR_EFFECTS:
        raise RuntimeError("V2.46.32 synthetic effect assignment drifted")
    return frozenset(recoveries), frozenset(repairs)


def _simulate_shared_pool(
    *,
    active_cap: int,
    deadline_seconds: int,
    policy: str,
    scenario: Mapping[str, float],
) -> dict[str, Any]:
    recoveries, repairs = _effect_sets()
    future: list[tuple[float, int, int, str]] = []
    ready: list[tuple[float, int, int, str]] = []
    slots = [0.0] * MODEL_SLOT_CAP
    heapq.heapify(slots)
    admission: dict[int, float] = {}
    completion: dict[int, float] = {}
    last_model: dict[int, float] = {}
    next_task = 0
    sequence = 0
    effect_count = 0
    priority = {"recovery": 0, "repair": 0, "synthesis": 1, "plan": 2}

    def push(available: float, task: int, stage: str) -> None:
        nonlocal sequence
        heapq.heappush(future, (available, sequence, task, stage))
        sequence += 1

    def admit(available: float) -> None:
        nonlocal next_task
        if next_task < SELECTED_COUNT:
            task = next_task
            next_task += 1
            admission[task] = available
            push(available, task, "plan")

    for _ in range(min(active_cap, SELECTED_COUNT)):
        admit(0.0)
    while len(completion) < SELECTED_COUNT:
        slot_available = heapq.heappop(slots)
        while future and future[0][0] <= slot_available + 1e-12:
            ready.append(heapq.heappop(future))
        if not ready:
            first_ready = future[0][0]
            while future and future[0][0] <= first_ready + 1e-12:
                ready.append(heapq.heappop(future))
            start = max(slot_available, first_ready)
        else:
            start = slot_available
        if policy == "fifo":
            chosen = min(
                range(len(ready)), key=lambda index: (ready[index][0], ready[index][1])
            )
        elif policy == "synthesis_priority":
            chosen = min(
                range(len(ready)),
                key=lambda index: (
                    priority[ready[index][3]],
                    ready[index][0],
                    ready[index][1],
                ),
            )
        else:
            raise ValueError("V2.46.32 unknown shared-pool policy")
        available, _, task, stage = ready.pop(chosen)
        start = max(start, available)
        duration = (
            float(scenario["plan_service_seconds"])
            if stage == "plan"
            else float(scenario["postplan_service_seconds"])
        )
        end = start + duration
        heapq.heappush(slots, end)
        effect_count += 1
        if stage == "plan":
            push(end + float(scenario["retrieval_seconds"]), task, "synthesis")
        elif stage == "synthesis" and task in recoveries:
            push(end, task, "recovery")
        elif stage == "synthesis" and task in repairs:
            push(end, task, "repair")
        else:
            last_model[task] = end
            completion[task] = end + float(scenario["local_completion_seconds"])
            admit(completion[task])
    return _simulation_metrics(
        admission=admission,
        completion=completion,
        last_model=last_model,
        deadline_seconds=deadline_seconds,
        effect_count=effect_count,
    )


def _simulate_reserve2(
    *, active_cap: int, deadline_seconds: int, scenario: Mapping[str, float]
) -> dict[str, Any]:
    recoveries, repairs = _effect_sets()
    events: list[tuple[float, int, int, str]] = []
    general_slots = [0.0] * (MODEL_SLOT_CAP - 2)
    reserved_slots = [0.0] * 2
    heapq.heapify(general_slots)
    heapq.heapify(reserved_slots)
    admission: dict[int, float] = {}
    completion: dict[int, float] = {}
    last_model: dict[int, float] = {}
    next_task = 0
    sequence = 0
    effect_count = 0

    def push(available: float, task: int, stage: str) -> None:
        nonlocal sequence
        heapq.heappush(events, (available, sequence, task, stage))
        sequence += 1

    def admit(available: float) -> None:
        nonlocal next_task
        if next_task < SELECTED_COUNT:
            task = next_task
            next_task += 1
            admission[task] = available
            push(available, task, "plan")

    for _ in range(min(active_cap, SELECTED_COUNT)):
        admit(0.0)
    while events:
        available, _, task, stage = heapq.heappop(events)
        if stage == "plan":
            slot_available = heapq.heappop(general_slots)
            pool = general_slots
            duration = float(scenario["plan_service_seconds"])
        else:
            general_available = general_slots[0]
            reserved_available = reserved_slots[0]
            if general_available <= reserved_available:
                slot_available = heapq.heappop(general_slots)
                pool = general_slots
            else:
                slot_available = heapq.heappop(reserved_slots)
                pool = reserved_slots
            duration = float(scenario["postplan_service_seconds"])
        end = max(available, slot_available) + duration
        heapq.heappush(pool, end)
        effect_count += 1
        if stage == "plan":
            push(end + float(scenario["retrieval_seconds"]), task, "synthesis")
        elif stage == "synthesis" and task in recoveries:
            push(end, task, "recovery")
        elif stage == "synthesis" and task in repairs:
            push(end, task, "repair")
        else:
            last_model[task] = end
            completion[task] = end + float(scenario["local_completion_seconds"])
            admit(completion[task])
    return _simulation_metrics(
        admission=admission,
        completion=completion,
        last_model=last_model,
        deadline_seconds=deadline_seconds,
        effect_count=effect_count,
    )


def _simulation_metrics(
    *,
    admission: Mapping[int, float],
    completion: Mapping[int, float],
    last_model: Mapping[int, float],
    deadline_seconds: int,
    effect_count: int,
) -> dict[str, Any]:
    if (
        len(admission) != SELECTED_COUNT
        or len(completion) != SELECTED_COUNT
        or len(last_model) != SELECTED_COUNT
        or effect_count != 2 * SELECTED_COUNT + RECOVERY_EFFECTS + REPAIR_EFFECTS
    ):
        raise RuntimeError("V2.46.32 synthetic workload conservation failed")
    task_seconds = [completion[index] - admission[index] for index in range(SELECTED_COUNT)]
    safe_effect_seconds = [
        last_model[index] - admission[index] for index in range(SELECTED_COUNT)
    ]
    safe_window = float(deadline_seconds) - CLEANUP_RESERVE_SECONDS
    effect_misses = sum(value > safe_window + 1e-9 for value in safe_effect_seconds)
    task_misses = sum(
        value > float(deadline_seconds) + 1e-9 for value in task_seconds
    )
    return {
        "projected_forward_wall_seconds": round(max(completion.values()), 6),
        "effect_window_deadline_misses": effect_misses,
        "task_deadline_misses": task_misses,
        "maximum_safe_effect_elapsed_seconds": round(max(safe_effect_seconds), 6),
        "maximum_task_elapsed_seconds": round(max(task_seconds), 6),
        "mean_task_elapsed_seconds": round(statistics.fmean(task_seconds), 6),
        "model_effects": effect_count,
    }


def simulate_configuration(
    *,
    active_cap: int,
    deadline_seconds: int,
    policy: str,
    scenario: Mapping[str, float],
) -> dict[str, Any]:
    if active_cap not in ACTIVE_CAPS or deadline_seconds not in DEADLINES:
        raise ValueError("V2.46.32 configuration is outside frozen grid")
    if policy == "reserve2":
        return _simulate_reserve2(
            active_cap=active_cap,
            deadline_seconds=deadline_seconds,
            scenario=scenario,
        )
    return _simulate_shared_pool(
        active_cap=active_cap,
        deadline_seconds=deadline_seconds,
        policy=policy,
        scenario=scenario,
    )


def _grid(scenarios: Mapping[str, Mapping[str, float]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passing: list[dict[str, Any]] = []
    for active_cap in ACTIVE_CAPS:
        for deadline in DEADLINES:
            for policy in POLICIES:
                results = {
                    name: simulate_configuration(
                        active_cap=active_cap,
                        deadline_seconds=deadline,
                        policy=policy,
                        scenario=scenarios[name],
                    )
                    for name in SCENARIO_NAMES
                }
                all_zero = all(
                    value["effect_window_deadline_misses"] == 0
                    and value["task_deadline_misses"] == 0
                    for value in results.values()
                )
                tail_wall = results["p95"]["projected_forward_wall_seconds"]
                passed = all_zero and tail_wall <= TAIL_WALL_CEILING_SECONDS
                row = {
                    "active_child_cap": active_cap,
                    "task_deadline_seconds": deadline,
                    "model_slot_policy": policy,
                    "scenario_results": results,
                    "all_scenarios_zero_deadline_miss": all_zero,
                    "p95_forward_wall_within_ceiling": tail_wall
                    <= TAIL_WALL_CEILING_SECONDS,
                    "mechanism_gate_passed": passed,
                }
                rows.append(row)
                if passed:
                    passing.append(row)
    if not passing:
        raise RuntimeError("V2.46.32 no schedule passed sensitivity gate")
    selected = min(
        passing,
        key=lambda row: (
            row["scenario_results"]["p95"]["projected_forward_wall_seconds"],
            row["task_deadline_seconds"],
            row["active_child_cap"],
            POLICY_ORDER[row["model_slot_policy"]],
        ),
    )
    return {
        "configuration_count": len(rows),
        "passing_configuration_count": len(passing),
        "selection_rule": (
            "all p25/p50/p75/p95 scenarios require zero effect-window and task "
            "deadline miss and p95 forward wall <=1800s; then minimize p95 wall, "
            "deadline, active-child cap, and frozen policy order"
        ),
        "selected_schedule": {
            key: selected[key]
            for key in (
                "active_child_cap",
                "task_deadline_seconds",
                "model_slot_policy",
                "scenario_results",
            )
        },
        "passing_schedules": [
            {
                key: row[key]
                for key in (
                    "active_child_cap",
                    "task_deadline_seconds",
                    "model_slot_policy",
                    "scenario_results",
                )
            }
            for row in sorted(
                passing,
                key=lambda row: (
                    row["scenario_results"]["p95"][
                        "projected_forward_wall_seconds"
                    ],
                    row["task_deadline_seconds"],
                    row["active_child_cap"],
                    POLICY_ORDER[row["model_slot_policy"]],
                ),
            )
        ],
        "grid": rows,
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    diagnosis, audit = _parents(root)
    calibration = _calibration(root)
    simulation = _grid(calibration["scenarios"])
    baseline = {
        name: simulate_configuration(
            active_cap=32,
            deadline_seconds=150,
            policy="fifo",
            scenario=calibration["scenarios"][name],
        )
        for name in SCENARIO_NAMES
    }
    selected = simulation["selected_schedule"]
    if (
        simulation["configuration_count"] != 72
        or simulation["passing_configuration_count"] != 7
        or selected["active_child_cap"] != 20
        or selected["task_deadline_seconds"] != 240
        or selected["model_slot_policy"] != "fifo"
        or baseline["p50"]["effect_window_deadline_misses"] != 10
        or baseline["p75"]["effect_window_deadline_misses"] != 126
        or baseline["p95"]["effect_window_deadline_misses"] != 213
        or selected["scenario_results"]["p95"][
            "effect_window_deadline_misses"
        ]
        != 0
        or selected["scenario_results"]["p95"]["task_deadline_misses"] != 0
        or selected["scenario_results"]["p95"][
            "projected_forward_wall_seconds"
        ]
        != 1621.497780
        or selected["scenario_results"]["p95"][
            "projected_forward_wall_seconds"
        ]
        > TAIL_WALL_CEILING_SECONDS
    ):
        raise RuntimeError("V2.46.32 deterministic schedule decision drifted")
    value = {
        "artifact_version": 1,
        "role": "v24632_content_free_capacity_schedule_simulation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "capacity_diagnosis_sha256": sha256(root / parent.OUTPUT),
            "capacity_diagnosis_audit_sha256": sha256(root / PARENT_AUDIT),
            "capacity_diagnosis_payload_sha256": diagnosis[
                "diagnosis_payload_sha256"
            ],
            "capacity_diagnosis_audit_payload_sha256": audit[
                "audit_payload_sha256"
            ],
        },
        "boundary": {
            "postfreeze_content_free_timing_simulation": True,
            "model_generated_result_envelopes_read_only_for_numeric_timing_calibration": True,
            "fallback_timing_excluded_from_service_calibration": True,
            "visible_task_runtime_prediction_evaluator_detail_or_score_rows_read": False,
            "task_position_hash_identifier_question_query_url_page_prediction_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "exact_runtime_prediction_or_causal_counterfactual_claimed": False,
        },
        "workload": {
            "anonymous_tasks": SELECTED_COUNT,
            "model_slots": MODEL_SLOT_CAP,
            "plan_effects": SELECTED_COUNT,
            "initial_synthesis_effects": SELECTED_COUNT,
            "recovery_effects": RECOVERY_EFFECTS,
            "repair_effects": REPAIR_EFFECTS,
            "total_model_effects": 2 * SELECTED_COUNT
            + RECOVERY_EFFECTS
            + REPAIR_EFFECTS,
            "additional_model_search_or_fetch_work_vs_v24630_logical_accounting": False,
            "retrieval_has_unconstrained_parallel_capacity_in_simulation": True,
        },
        "grid_contract": {
            "active_child_caps": list(ACTIVE_CAPS),
            "task_deadlines_seconds": list(DEADLINES),
            "model_slot_policies": list(POLICIES),
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "p95_forward_wall_ceiling_seconds": TAIL_WALL_CEILING_SECONDS,
            "scenario_quantiles": list(SCENARIO_QUANTILES),
        },
        "calibration": calibration,
        "current_schedule_sensitivity": {
            "active_child_cap": 32,
            "task_deadline_seconds": 150,
            "model_slot_policy": "fifo",
            "scenario_results": baseline,
        },
        "simulation": simulation,
        "conclusions": {
            "current_32_8_150_schedule_is_tail_robust_in_simulation": False,
            "bounded_active_child_admission_required_by_selected_schedule": True,
            "longer_task_deadline_required_by_selected_schedule": True,
            "stage_aware_slot_policy_required_by_selected_schedule": False,
            "strict_synthesis_priority_selected": False,
            "simulation_proves_real_provider_zero_fallback": False,
            "neutral_provider_stress_test_required": True,
            "quality_improvement_or_sota_demonstrated": False,
        },
        "next_work": {
            "preregister_neutral_non_benchmark_provider_stress": True,
            "stress_arms": [
                "current_32_active_8_slots_150s_fifo_control",
                "selected_20_active_8_slots_240s_fifo",
                "conservative_16_active_8_slots_210s_fifo",
                "conservative_16_active_6_general_2_postplan_reserved_210s",
            ],
            "required_gate": {
                "zero_pre_provider_synthesis_rejection": True,
                "zero_fallback": True,
                "exact_effect_accounting": True,
                "no_benchmark_manifest_mapping_gold_evaluator_or_score": True,
                "no_additional_work_across_arms": True,
                "selected_or_conservative_arm_wall_competitive": True,
            },
        },
        "authorization": {
            "neutral_provider_stress_protocol_design": True,
            "neutral_provider_stress_launch": False,
            "additional_dev64": False,
            "new_exact220": False,
            "same_run_evaluator_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if SECRET.search(encoded) or OPAQUE.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.46.32 simulation emitted prohibited content")
    value["simulation_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "simulation_payload_sha256"):
        raise RuntimeError("V2.46.32 simulation drifted")
    return dict(value)


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
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish(ROOT / OUTPUT, report)
    selected = report["simulation"]["selected_schedule"]
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "selected_active_child_cap": selected["active_child_cap"],
                "selected_deadline_seconds": selected["task_deadline_seconds"],
                "selected_policy": selected["model_slot_policy"],
                "passing_schedules": report["simulation"][
                    "passing_configuration_count"
                ],
            },
            sort_keys=True,
        )
    )
