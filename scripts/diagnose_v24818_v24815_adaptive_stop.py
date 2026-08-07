#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.48.15 adaptive stop.

The diagnosis is post-freeze and post-evaluation.  It may read the already
sealed external smoke artifacts in memory, but publishes no task identifier,
question, entity, value, prediction, query, URL, page, or per-task metric.
It performs no model, search, fetch, benchmark, or evaluator call.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
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

from deepwide_agent import v24815_worldbank_successor_contract as contract  # noqa: E402
from deepwide_agent.v24812_batched_search_accounting import (  # noqa: E402
    validate_envelope,
)
from scripts import evaluate_v24815_worldbank_successor as evaluator  # noqa: E402


DATE = "20260807"
OUTPUT = Path(
    f"results/v24818_v24815_adaptive_stop_diagnosis_v1_{DATE}.json"
)
RESULT = Path(f"results/v24815_worldbank_successor_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24815_worldbank_successor_postresult_audit_v1_{DATE}.json"
)
SMOKE_MARKER = b"v24805-smoke-policy-not-main-calibration"
METRICS = (
    "exact_table_success",
    "entity_recall",
    "row_f1",
    "item_f1",
    "column_f1",
    "composite",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)"
    r"[A-Za-z0-9_-]{16,}"
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
        raise RuntimeError(f"V2.48.18 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.18 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _task_envelopes(root: Path) -> list[dict[str, Any]]:
    output = []
    for ordinal in range(1, contract.SELECTED_COUNT + 1):
        relative = contract.TASK_ROOT / f"task_{ordinal:04d}" / "result.json"
        output.append(validate_envelope(_read(root, relative)))
    return output


def _metric_delta(
    fixed: Mapping[str, float | int], first: Mapping[str, float | int]
) -> dict[str, float | int]:
    return {
        name: (
            int(fixed[name]) - int(first[name])
            if name == "exact_table_success"
            else float(fixed[name]) - float(first[name])
        )
        for name in METRICS
    }


def _sum_deltas(rows: list[Mapping[str, float | int]]) -> dict[str, float | int]:
    return {
        name: (
            sum(int(row[name]) for row in rows)
            if name == "exact_table_success"
            else sum(float(row[name]) for row in rows)
        )
        for name in METRICS
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = _read(root, RESULT)
    post = _read(root, POSTAUDIT)
    forward = _read(root, contract.FORWARD_AUDIT)
    protocol = contract.validate_protocol(root, _read(root, contract.PROTOCOL))
    private = _read(root, contract.POPULATION_PRIVATE)
    if (
        not _sealed(result, "result_payload_sha256")
        or result.get("passed") is not True
        or result.get("predictions_sha256")
        != contract.sha256(root / contract.PREDICTIONS)
        or not _sealed(post, "audit_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(forward, "audit_payload_sha256")
        or forward.get("audit_valid") is not True
        or forward.get("findings") != []
    ):
        raise RuntimeError("V2.48.18 frozen parent chain drifted")

    envelopes = _task_envelopes(root)
    tasks = protocol["visible_tasks"]
    gold = evaluator._private_gold(private)
    if len(envelopes) != len(tasks) or len(gold) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.18 external denominator drifted")

    decisions: Counter[str] = Counter()
    stop_deltas: list[dict[str, float | int]] = []
    expand_deltas: list[dict[str, float | int]] = []
    stopped_suffix_records = 0
    stopped_first_records = 0
    stopped_net_values: list[float] = []
    stopped_loss_reductions: list[float] = []
    stopped_costs: list[float] = []
    for task, envelope in zip(tasks, envelopes, strict=True):
        value = envelope["result"]
        if value.get("opaque_id") != task["opaque_id"]:
            raise RuntimeError("V2.48.18 task/result order drifted")
        decision = value["adaptive_decision"]
        choice = str(decision["decision"])
        decisions[choice] += 1
        arms = value["predictions"]
        expected = gold[task["opaque_id"]]
        first = evaluator.evaluate_prediction(
            arms["first_wave_only"], task["question"], expected
        )
        fixed = evaluator.evaluate_prediction(
            arms["fixed_full_budget"], task["question"], expected
        )
        delta = _metric_delta(fixed, first)
        if choice == "stop":
            stop_deltas.append(delta)
            stopped_first_records += len(value["shared_prefix"]["first_wave_records"])
            stopped_suffix_records += (
                len(value["full_official_records"])
                - len(value["shared_prefix"]["first_wave_records"])
            )
            stopped_net_values.append(float(decision["net_value"]))
            stopped_loss_reductions.append(
                float(decision["expected_terminal_loss_reduction"])
            )
            stopped_costs.append(float(decision["expected_lookup_cost"]))
        elif choice == "expand":
            expand_deltas.append(delta)
        else:
            raise RuntimeError("V2.48.18 adaptive decision drifted")

    rebuilt = evaluator.evaluate_rows(
        [
            {
                "opaque_id": task["opaque_id"],
                "predictions": envelope["result"]["predictions"],
            }
            for task, envelope in zip(tasks, envelopes, strict=True)
        ],
        protocol,
        gold,
    )
    if rebuilt != result.get("metrics"):
        raise RuntimeError("V2.48.18 parent metrics do not replay")
    if not stop_deltas:
        raise RuntimeError("V2.48.18 expected an observed stop")

    stop_sum = _sum_deltas(stop_deltas)
    expand_sum = _sum_deltas(expand_deltas)
    smoke_hash = hashlib.sha256(SMOKE_MARKER).hexdigest()
    policy = protocol["execution"]["adaptive_policy"]
    value = {
        "artifact_version": 1,
        "role": "v24818_v24815_adaptive_stop_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "smoke_cost_quality_scale_uncalibrated_boundary_stop_no_go",
        "parents": {
            "protocol_sha256": contract.sha256(root / contract.PROTOCOL),
            "forward_audit_sha256": contract.sha256(root / contract.FORWARD_AUDIT),
            "result_sha256": contract.sha256(root / RESULT),
            "postresult_audit_sha256": contract.sha256(root / POSTAUDIT),
        },
        "denominator": contract.SELECTED_COUNT,
        "decision_counts": dict(sorted(decisions.items())),
        "stopped_suffix_observation": {
            "stopped_task_count": len(stop_deltas),
            "first_wave_valid_record_count": stopped_first_records,
            "additional_valid_record_count_in_physically_executed_fixed_suffix": stopped_suffix_records,
            "fixed_full_minus_first_wave_metric_sum": stop_sum,
            "all_stopped_task_composite_deltas_positive": all(
                float(row["composite"]) > 0 for row in stop_deltas
            ),
            "all_stopped_task_item_f1_deltas_positive": all(
                float(row["item_f1"]) > 0 for row in stop_deltas
            ),
            "minimum_net_value": min(stopped_net_values),
            "maximum_net_value": max(stopped_net_values),
            "expected_terminal_loss_reduction_sum": sum(stopped_loss_reductions),
            "expected_lookup_cost_sum": sum(stopped_costs),
            "absolute_cost_loss_boundary_margin_sum": sum(
                abs(value) for value in stopped_net_values
            ),
        },
        "expanded_suffix_observation": {
            "expanded_task_count": len(expand_deltas),
            "fixed_full_minus_first_wave_metric_sum": expand_sum,
        },
        "calibration_audit": {
            "calibration_reference_is_explicit_smoke_marker": policy.get(
                "calibration_ref_sha256"
            )
            == smoke_hash,
            "calibration_artifact_path_bound_in_protocol": "calibration_artifact_path"
            in policy,
            "empirical_cost_to_quality_exchange_rate_bound": False,
            "cost_and_terminal_loss_reduction_directly_subtracted": True,
            "entropy_feature_weight": float(
                policy.get("information_gain_feature_weight", math.nan)
            ),
            "entropy_assigned_signed_credit": False,
        },
        "conclusions": {
            "fixed_suffix_has_positive_quality_utility_on_every_stopped_smoke_task": all(
                float(row["composite"]) > 0 for row in stop_deltas
            ),
            "observed_stop_is_quality_pareto_dominated_by_fixed_full": all(
                float(row["composite"]) > 0
                and all(float(row[name]) >= 0 for name in METRICS if name != "composite")
                for row in stop_deltas
            ),
            "adaptive_policy_quality_noninferiority_established": False,
            "entropy_or_signed_credit_validated": False,
            "deepwidebench_improvement_measured": False,
            "sota_supported": False,
            "same_population_replay_or_threshold_tuning_allowed": False,
            "fresh_external_quality_first_controller_required": True,
        },
        "boundary": {
            "post_prediction_freeze_and_post_evaluation_aggregate_only": True,
            "private_artifacts_read_only_in_memory": True,
            "task_identifier_question_entity_value_prediction_query_url_page_or_credential_emitted": False,
            "per_task_metric_or_decision_emitted": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "same_population_retry_resume_rerun_or_revaluation": False,
        },
        "authorization": {
            "append_only_quality_first_controller_design": True,
            "fresh_external_population_design": True,
            "fresh_external_activation_or_launch": False,
            "same_population_replay_or_revaluation": False,
            "public_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
        "findings": [],
        "diagnosis_valid": True,
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_report(
    root: Path,
    value: Mapping[str, Any],
    *,
    rebuild: bool = True,
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    encoded = json.dumps(copied, ensure_ascii=False, sort_keys=True)
    if (
        copied.get("role")
        != "v24818_v24815_adaptive_stop_aggregate_diagnosis"
        or copied.get("denominator") != contract.SELECTED_COUNT
        or copied.get("decision_counts") != {"expand": 11, "stop": 1}
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or copied.get("calibration_audit", {}).get(
            "calibration_reference_is_explicit_smoke_marker"
        )
        is not True
        or copied.get("calibration_audit", {}).get(
            "empirical_cost_to_quality_exchange_rate_bound"
        )
        is not False
        or copied.get("conclusions", {}).get(
            "observed_stop_is_quality_pareto_dominated_by_fixed_full"
        )
        is not True
        or copied.get("conclusions", {}).get("sota_supported") is not False
        or copied.get("authorization", {}).get(
            "same_population_replay_or_revaluation"
        )
        is not False
        or copied.get("authorization", {}).get("public_dev64_or_exact220")
        is not False
        or copied.get("authorization", {}).get("leaderboard_or_sota") is not False
        or OPAQUE.search(encoded) is not None
        or SECRET.search(encoded) is not None
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.18 diagnosis drifted")
    if rebuild:
        expected = build_report(
            root, now=int(copied.get("created_at_unix", 0))
        )
        if copied != expected:
            raise RuntimeError("V2.48.18 diagnosis replay drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git(ROOT, "status", "--porcelain") or _git(
        ROOT, "rev-parse", "HEAD"
    ) != _git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.48.18 diagnosis requires clean pushed HEAD")
    value = build_report(ROOT)
    validate_report(ROOT, value)
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": value["status"],
                "decision_counts": value["decision_counts"],
                "stopped_suffix_observation": value[
                    "stopped_suffix_observation"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
