#!/usr/bin/env python3
"""Content-free post-freeze diagnosis of the V2.43.20 paired dev64 NO-GO."""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    ARMS,
    FORWARD_RESULT,
    POSTAUDIT,
    payload_sha256,
    sha256,
)


DATE = "20260803"
ROLE = "v24322_v24320_paired_dev64_postfreeze_diagnosis"
OUTPUT = Path(f"results/v24322_v24320_paired_dev64_diagnosis_v1_{DATE}.json")
FINAL = Path(f"results/v24320_paired_dev64_result_v1_{DATE}.json")
GUARD = Path(f"results/v24321_v24320_evaluator_guard_decision_v1_{DATE}.json")
V24314 = Path(f"results/v24314_paired_dev64_result_v1_{DATE}.json")
EVAL_ROOT = Path(f"outputs/v24320_paired_dev64_v1_{DATE}/fresh_both_arm_evaluator")
JOINED = {arm: EVAL_ROOT / arm / "terminal_outcomes_evaluator_joined.jsonl" for arm in ARMS}
SUMMARY = {arm: EVAL_ROOT / arm / "conservative_summary.json" for arm in ARMS}
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
MODEL_GENERATED = frozenset(
    {"primary", "repaired", "normalized_primary", "normalized_repaired"}
)


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(value, dict) for value in values):
        raise ValueError(f"expected object rows: {path}")
    return values


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _index(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value or value in output:
            raise ValueError("V2.43.22 pairing key drifted")
        output[value] = row
    return output


def _composite(row: Mapping[str, Any]) -> float:
    metrics = row.get("metrics")
    if not isinstance(metrics, Mapping):
        raise ValueError("V2.43.22 metrics absent")
    values = [float(metrics[name]) for name in QUALITY]
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        raise ValueError("V2.43.22 metric drifted")
    return sum(values) / len(values)


def stratum(
    name: str,
    ids: list[str],
    runtime: Mapping[str, Mapping[str, Mapping[str, Any]]],
    metrics: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    deltas = [
        _composite(metrics["candidate"][opaque_id])
        - _composite(metrics["baseline"][opaque_id])
        for opaque_id in ids
    ]
    value: dict[str, Any] = {
        "name": name,
        "task_count": len(ids),
        "mean_composite_delta": sum(deltas) / len(deltas) if deltas else None,
        "median_composite_delta": statistics.median(deltas) if deltas else None,
        "positive_zero_negative": [
            sum(delta > 0 for delta in deltas),
            sum(delta == 0 for delta in deltas),
            sum(delta < 0 for delta in deltas),
        ],
        "whole_table_success_delta": sum(
            float(metrics["candidate"][opaque_id]["metrics"]["score"])
            - float(metrics["baseline"][opaque_id]["metrics"]["score"])
            for opaque_id in ids
        ),
        "same_prediction_hash_count": sum(
            runtime["candidate"][opaque_id]["prediction_sha256"]
            == runtime["baseline"][opaque_id]["prediction_sha256"]
            for opaque_id in ids
        ),
        "baseline_fallback_count": sum(
            runtime["baseline"][opaque_id]["completion_kind"] not in MODEL_GENERATED
            for opaque_id in ids
        ),
        "candidate_fallback_count": sum(
            runtime["candidate"][opaque_id]["completion_kind"] not in MODEL_GENERATED
            for opaque_id in ids
        ),
    }
    for metric in QUALITY:
        value[f"{metric}_delta"] = (
            sum(
                float(metrics["candidate"][opaque_id]["metrics"][metric])
                - float(metrics["baseline"][opaque_id]["metrics"][metric])
                for opaque_id in ids
            )
            / len(ids)
            if ids
            else None
        )
    return value


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    final = read_object(root / FINAL)
    audit = read_object(root / POSTAUDIT)
    guard = read_object(root / GUARD)
    historical = read_object(root / V24314)
    if (
        final.get("status") != "development_gate_no_go"
        or not sealed(final, "result_payload_sha256")
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or not sealed(audit, "audit_payload_sha256")
        or guard.get("passed") is not True
        or guard.get("failed_checks") != []
        or not sealed(guard, "decision_payload_sha256")
        or historical.get("status") != "development_gate_go"
        or not sealed(historical, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.22 parent evidence drifted")
    runtime = {arm: _index(read_jsonl(root / JOINED[arm]), "opaque_id") for arm in ARMS}
    summaries = {arm: read_object(root / SUMMARY[arm]) for arm in ARMS}
    metrics = {arm: _index(summaries[arm]["per_task"], "opaque_id") for arm in ARMS}
    order = list(runtime["baseline"])
    if (
        len(order) != 64
        or any(set(mapping) != set(order) for mapping in (*runtime.values(), *metrics.values()))
    ):
        raise RuntimeError("V2.43.22 paired identity drifted")

    def route(arm: str, opaque_id: str) -> bool:
        return bool(runtime[arm][opaque_id]["mechanism_telemetry"]["controller_expand"])

    reserve = [
        opaque_id
        for opaque_id in order
        if runtime["candidate"][opaque_id]["mechanism_telemetry"]["reserved_stage_executed"]
    ]
    no_reserve = [opaque_id for opaque_id in order if opaque_id not in reserve]
    strata = [
        stratum("all", order, runtime, metrics),
        stratum("candidate_reserved_stage_executed", reserve, runtime, metrics),
        stratum("candidate_reserved_stage_not_executed", no_reserve, runtime, metrics),
    ]
    for baseline_expand in (False, True):
        for candidate_expand in (False, True):
            ids = [
                opaque_id
                for opaque_id in order
                if route("baseline", opaque_id) is baseline_expand
                and route("candidate", opaque_id) is candidate_expand
            ]
            strata.append(
                stratum(
                    f"controller_baseline_{'expand' if baseline_expand else 'stop'}_candidate_{'expand' if candidate_expand else 'stop'}",
                    ids,
                    runtime,
                    metrics,
                )
            )

    routing_discordance = sum(
        route("baseline", opaque_id) != route("candidate", opaque_id)
        for opaque_id in order
    )
    current_delta = float(final["decision"]["candidate_minus_baseline"]["quality_composite"])
    historical_delta = float(
        historical["decision"]["candidate_minus_baseline"]["quality_composite"]
    )
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "postfreeze_diagnosis_complete",
        "provenance": {
            "v24320_forward_result_sha256": sha256(root / FORWARD_RESULT),
            "v24320_final_result_sha256": sha256(root / FINAL),
            "v24320_postresult_audit_sha256": sha256(root / POSTAUDIT),
            "v24321_evaluator_guard_sha256": sha256(root / GUARD),
            "v24314_final_result_sha256": sha256(root / V24314),
            "joined_sha256": {arm: sha256(root / JOINED[arm]) for arm in ARMS},
            "summary_sha256": {arm: sha256(root / SUMMARY[arm]) for arm in ARMS},
        },
        "paired_strata": strata,
        "mechanism_facts": {
            "candidate_reserved_stage_tasks": len(reserve),
            "candidate_reserved_usable_pages": int(
                final["arm_health"]["candidate"]["reserved_usable_pages"]
            ),
            "controller_route_discordant_tasks": routing_discordance,
            "same_prediction_hash_tasks": sum(
                runtime["candidate"][opaque_id]["prediction_sha256"]
                == runtime["baseline"][opaque_id]["prediction_sha256"]
                for opaque_id in order
            ),
            "v24314_composite_delta": historical_delta,
            "v24320_composite_delta": current_delta,
            "same_dev64_independent_run_delta_sign_flip": historical_delta > 0 > current_delta,
            "strict_shared_random_prefix_causal_ablation": False,
        },
        "diagnosis": {
            "outer_reliability_fixed": True,
            "staged_reserve_quality_supported": False,
            "reserve_executed_stratum_mean_delta": next(
                row["mean_composite_delta"]
                for row in strata
                if row["name"] == "candidate_reserved_stage_executed"
            ),
            "both_stop_stratum_mean_delta": next(
                row["mean_composite_delta"]
                for row in strata
                if row["name"] == "controller_baseline_stop_candidate_stop"
            ),
            "independent_upstream_route_noise_material": routing_discordance > 0,
            "reserve_effect_cleanly_identified": False,
            "reason": (
                "Quality loss concentrates in reserve/route-discordant strata, while independently "
                "sampled plans, retrievals, controller routes, and synthesis prevent clean treatment attribution."
            ),
        },
        "successor_requirements": {
            "shared_visible_only_plan_and_first_wave": True,
            "shared_first_six_page_evidence_prefix": True,
            "branch_only_after_shared_prefix": True,
            "reliability_weighted_cell_conditional_information_gain": True,
            "reserve_evidence_separated_from_core_context": True,
            "reserve_may_override_core_only_with_corroboration": True,
            "same_64_task_reconfirmatory_rerun": False,
            "fresh_exact220_launch": False,
        },
        "source_policy": {
            "offline_after_both_arm_prediction_and_evaluator_freeze": True,
            "task_pairing_uses_opaque_id_internally": True,
            "question_opaque_id_prediction_instance_id_or_evaluator_text_emitted": False,
            "same_run_feedback_used_for_forward_or_selection": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "authorization": {
            "shared_prefix_successor_design": True,
            "successor_launch": False,
            "additional_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    strata = value.get("paired_strata")
    if (
        value.get("role") != ROLE
        or value.get("status") != "postfreeze_diagnosis_complete"
        or not isinstance(strata, list)
        or len(strata) != 7
        or sum(row["task_count"] for row in strata[3:]) != 64
        or value.get("mechanism_facts", {}).get("strict_shared_random_prefix_causal_ablation")
        is not False
        or value.get("diagnosis", {}).get("staged_reserve_quality_supported")
        is not False
        or value.get("diagnosis", {}).get("reserve_effect_cleanly_identified")
        is not False
        or value.get("source_policy", {}).get(
            "question_opaque_id_prediction_instance_id_or_evaluator_text_emitted"
        )
        is not False
        or value.get("authorization", {}).get("successor_launch") is not False
        or value.get("authorization", {}).get("leaderboard_or_sota") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.22 diagnosis drifted")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build()
    validate(diagnosis)
    publish(ROOT / OUTPUT, diagnosis)
    print(json.dumps({"path": str(OUTPUT), "status": diagnosis["status"]}, sort_keys=True))
