#!/usr/bin/env python3
"""Content-free post-terminal diagnosis of the V2.42.87 exact-220 run.

This report is deliberately offline.  It opens frozen predictions and
evaluator rows only after both V2.42.67 and V2.42.87 are terminal, joins them
by opaque identifier in memory, and publishes aggregate mechanism statistics.
It never persists identifiers, questions, queries, URLs, pages, predictions,
answers, benchmark labels, or per-task scores.  Nothing in this module can be
imported by an active forward runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24288_v24287_exact220_diagnosis_v1_20260803.json")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SELECTED = 220
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
METRICS = (*QUALITY, "score")
SOURCES = {
    "v24267_result": Path("results/v24267_exact220_result_v1_20260802.json"),
    "v24267_runtime": Path("outputs/v24267_exact220_v1_20260802/evaluator/terminal_outcomes_evaluator_joined.jsonl"),
    "v24267_evaluator": Path("outputs/v24267_exact220_v1_20260802/evaluator/conservative_summary.json"),
    "v24287_result": Path("results/v24287_exact220_result_v1_20260803.json"),
    "v24287_postresult_audit": Path("results/v24287_exact220_postresult_audit_v1_20260803.json"),
    "v24287_runtime": Path("outputs/v24287_exact220_v1_20260803/evaluator/terminal_outcomes_evaluator_joined.jsonl"),
    "v24287_evaluator": Path("outputs/v24287_exact220_v1_20260803/evaluator/conservative_summary.json"),
    "v24287_run_summary": Path("outputs/v24287_exact220_v1_20260803/run_summary.json"),
}


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.88 expected a JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.42.88 expected JSONL objects")
    return rows


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.88 source is not ordinary: {relative}")
    if not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.88 source escaped the repository: {relative}")
    return path


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def _distribution(values: Sequence[float]) -> dict[str, float | int]:
    numbers = [float(value) for value in values]
    if not numbers or any(not math.isfinite(value) for value in numbers):
        raise RuntimeError("V2.42.88 invalid distribution")
    return {
        "n": len(numbers),
        "mean": sum(numbers) / len(numbers),
        "median": statistics.median(numbers),
        "p25": _quantile(numbers, 0.25),
        "p75": _quantile(numbers, 0.75),
        "minimum": min(numbers),
        "maximum": max(numbers),
    }


def _direction(values: Sequence[float]) -> dict[str, int]:
    epsilon = 1e-12
    better = sum(value > epsilon for value in values)
    worse = sum(value < -epsilon for value in values)
    return {"better": better, "tie": len(values) - better - worse, "worse": worse}


def _table_row_count(prediction: str) -> int:
    lines = [
        line.strip()
        for line in str(prediction).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    best = 0
    for position in range(len(lines) - 1):
        separator = [cell.strip() for cell in lines[position + 1].strip("|").split("|")]
        if not separator or not all(cell and "-" in cell and set(cell) <= set("-: ") for cell in separator):
            continue
        width = len(lines[position].strip("|").split("|"))
        rows = 0
        for line in lines[position + 2 :]:
            if len(line.strip("|").split("|")) != width:
                break
            rows += 1
        best = max(best, rows)
    return best


def _metric_delta(
    identities: Sequence[str],
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    metric: str,
) -> list[float]:
    return [
        float(candidate[identity]["metrics"][metric])
        - float(control[identity]["metrics"][metric])
        for identity in identities
    ]


def _composite(row: Mapping[str, Any]) -> float:
    return sum(float(row["metrics"][metric]) for metric in QUALITY) / len(QUALITY)


def _group(
    identities: Sequence[str],
    control_eval: Mapping[str, Any],
    candidate_eval: Mapping[str, Any],
    control_rows: Mapping[str, int],
    candidate_rows: Mapping[str, int],
) -> dict[str, Any]:
    if not identities:
        return {"selected": 0}
    row_delta = [candidate_rows[identity] - control_rows[identity] for identity in identities]
    composite_delta = [
        _composite(candidate_eval[identity]) - _composite(control_eval[identity])
        for identity in identities
    ]
    metrics: dict[str, Any] = {}
    for metric in METRICS:
        delta = _metric_delta(identities, control_eval, candidate_eval, metric)
        metrics[metric] = {
            "candidate_minus_control": _distribution(delta),
            "direction": _direction(delta),
        }
    return {
        "selected": len(identities),
        "prediction_row_count": {
            "control_sum": sum(control_rows[identity] for identity in identities),
            "candidate_sum": sum(candidate_rows[identity] for identity in identities),
            "candidate_minus_control": _distribution(row_delta),
            "direction": _direction(row_delta),
        },
        "quality_composite": {
            "candidate_minus_control": _distribution(composite_delta),
            "direction": _direction(composite_delta),
        },
        "quality_metrics": metrics,
    }


def _task_results(root: Path) -> dict[str, dict[str, Any]]:
    task_root = root / "outputs/v24287_exact220_v1_20260803/tasks"
    values: dict[str, dict[str, Any]] = {}
    for path in sorted(task_root.glob("task_*/result.json")):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise RuntimeError("V2.42.88 task result path drifted")
        envelope = _read_json(path)
        result = envelope.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("opaque_id"), str):
            raise RuntimeError("V2.42.88 task result envelope drifted")
        values[result["opaque_id"]] = result
    return values


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    bound = {
        name: {"path": str(relative), "sha256": sha256(_ordinary(root, relative))}
        for name, relative in SOURCES.items()
    }
    result67 = _read_json(root / SOURCES["v24267_result"])
    result87 = _read_json(root / SOURCES["v24287_result"])
    audit87 = _read_json(root / SOURCES["v24287_postresult_audit"])
    summary87 = _read_json(root / SOURCES["v24287_run_summary"])
    if (
        result67.get("status") != "exact220_single_rollout_complete"
        or result87.get("status") != "exact220_single_rollout_complete"
        or result67.get("selected") != SELECTED
        or result87.get("selected") != SELECTED
        or result87.get("claims", {}).get("sota") is not False
        or audit87.get("audit_valid") is not True
        or audit87.get("findings") != []
        or audit87.get("execution_closure", {}).get("shared_api_lease_active") is not False
        or summary87.get("completed") != SELECTED
    ):
        raise RuntimeError("V2.42.88 terminal parent state drifted")

    runtime67_rows = _read_jsonl(root / SOURCES["v24267_runtime"])
    runtime87_rows = _read_jsonl(root / SOURCES["v24287_runtime"])
    runtime67 = {row["opaque_id"]: row for row in runtime67_rows}
    runtime87 = {row["opaque_id"]: row for row in runtime87_rows}
    eval67_value = _read_json(root / SOURCES["v24267_evaluator"])
    eval87_value = _read_json(root / SOURCES["v24287_evaluator"])
    eval67 = {row["opaque_id"]: row for row in eval67_value["per_task"]}
    eval87 = {row["opaque_id"]: row for row in eval87_value["per_task"]}
    identities = list(runtime87)
    if (
        len(identities) != SELECTED
        or len(set(identities)) != SELECTED
        or set(identities) != set(runtime67)
        or set(identities) != set(eval67)
        or set(identities) != set(eval87)
        or any(row.get("label_blind") is not True for row in [*runtime67_rows, *runtime87_rows])
    ):
        raise RuntimeError("V2.42.88 paired identity or boundary drifted")

    task_results = _task_results(root)
    if len(task_results) != 218 or not set(task_results).issubset(identities):
        raise RuntimeError("V2.42.88 task artifact population drifted")
    retrieval = {
        identity: result["two_wave_retrieval"]["receipt"]
        for identity, result in task_results.items()
        if result.get("two_wave_retrieval", {}).get("status") == "completed"
    }
    if len(retrieval) != 218:
        raise RuntimeError("V2.42.88 completed retrieval population drifted")
    stop = [identity for identity, value in retrieval.items() if value["controller"]["decision"] == "stop"]
    expand = [identity for identity, value in retrieval.items() if value["controller"]["decision"] == "expand"]
    low_coverage = [
        identity
        for identity in expand
        if retrieval[identity]["total"]["usable_pages"] < 4
        or retrieval[identity]["total"]["unique_hosts"] < 2
        or retrieval[identity]["total"]["content_chars"]
        < retrieval[identity]["required_column_count"] * 1_200
    ]
    if len(stop) != 175 or len(expand) != 43 or len(low_coverage) != 23:
        raise RuntimeError("V2.42.88 controller partition drifted")

    rows67 = {identity: _table_row_count(row["prediction"]) for identity, row in runtime67.items()}
    rows87 = {identity: _table_row_count(row["prediction"]) for identity, row in runtime87.items()}
    test = [identity for identity in identities if eval87[identity]["split"] == "test"]
    devval = [identity for identity in identities if eval87[identity]["split"] != "test"]
    fallback_kinds = Counter(row["completion_kind"] for row in runtime87_rows if row["completion_kind"].endswith("fallback"))
    evaluator_errors = Counter(
        "out_of_range" if "out-of-range" in str(row.get("evaluator_error") or "") else "internal_error"
        for row in eval87.values()
        if row.get("evaluator_valid") is not True
    )
    wave_totals: dict[str, Any] = {}
    for wave in ("wave1", "wave2", "total"):
        wave_totals[wave] = {
            name: sum(float(value[wave][name]) for value in retrieval.values())
            for name in (
                "queries_executed",
                "sources_discovered",
                "fetches_attempted",
                "usable_pages",
                "novel_pages",
                "content_chars",
                "search_seconds",
                "fetch_seconds",
                "unrecoverable_search_failures",
            )
        }
    metrics67 = result67["metrics"]
    metrics87 = result87["metrics"]["all_220"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24288_v24287_exact220_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": {
            "selected": SELECTED,
            "post_terminal_observational": True,
            "causal_claim_available": False,
            "per_task_identity_content_metric_or_cost_persisted": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "bound_sources": bound,
        "aggregate_result": {
            "v24267": metrics67,
            "v24287": metrics87,
            "quality_composite_delta": metrics87["quality_composite"]
            - metrics67["quality_composite"],
            "whole_table_success_delta": metrics87["whole_table_successes"]
            - metrics67["whole_table_successes"],
        },
        "prediction_rows": {
            "v24267_sum": sum(rows67.values()),
            "v24287_sum": sum(rows87.values()),
            "candidate_minus_control": _distribution([rows87[identity] - rows67[identity] for identity in identities]),
            "direction": _direction([rows87[identity] - rows67[identity] for identity in identities]),
        },
        "paired_scopes": {
            "all220": _group(identities, eval67, eval87, rows67, rows87),
            "test156": _group(test, eval67, eval87, rows67, rows87),
            "consumed_devval64": _group(devval, eval67, eval87, rows67, rows87),
        },
        "controller": {
            "stop": _group(stop, eval67, eval87, rows67, rows87),
            "expand": _group(expand, eval67, eval87, rows67, rows87),
            "expand_low_coverage": _group(low_coverage, eval67, eval87, rows67, rows87),
            "low_coverage_rule": {
                "controller_decision": "expand",
                "usable_pages_lt": 4,
                "unique_hosts_lt": 2,
                "content_chars_lt_required_columns_times": 1_200,
                "label_or_evaluator_metric_used": False,
            },
        },
        "retrieval_totals": wave_totals,
        "failure_taxonomy": {
            "forward_fallbacks": dict(sorted(fallback_kinds.items())),
            "synthesis_provider_best_effort_fallbacks": 4,
            "parent_hard_deadline_fallbacks": 2,
            "hard_fetch_deadline_events": summary87["hard_fetch_deadline_failures"],
            "evaluator_errors": dict(sorted(evaluator_errors.items())),
            "evaluator_errors_selectively_retried": 0,
        },
        "mechanism_conclusions": {
            "engineering_efficiency_improved": True,
            "quality_regressed": True,
            "sota_supported": False,
            "single_component_causal_attribution_supported": False,
            "stop_path_mean_quality_composite_delta": _group(stop, eval67, eval87, rows67, rows87)["quality_composite"]["candidate_minus_control"]["mean"],
            "expand_path_mean_quality_composite_delta": _group(expand, eval67, eval87, rows67, rows87)["quality_composite"]["candidate_minus_control"]["mean"],
            "next_candidate": "label_blind bounded rescue only after second-wave low coverage",
        },
        "source_policy": {
            "question_query_url_host_page_prediction_answer_task_id_or_label_persisted": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "active_forward_source_imported_this_module": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "benchmark_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    validate_report(value)
    return value


def validate_report(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    controller = value.get("controller") or {}
    conclusions = value.get("mechanism_conclusions") or {}
    if (
        value.get("role") != "v24288_v24287_exact220_postterminal_diagnosis"
        or seal != payload_sha256(unsigned)
        or OPAQUE.search(encoded)
        or value.get("scope", {}).get("selected") != SELECTED
        or controller.get("stop", {}).get("selected") != 175
        or controller.get("expand", {}).get("selected") != 43
        or controller.get("expand_low_coverage", {}).get("selected") != 23
        or conclusions.get("quality_regressed") is not True
        or conclusions.get("sota_supported") is not False
        or any(value.get("authorization", {}).values())
        or any(
            value.get("source_policy", {}).get(name) is not False
            for name in value.get("source_policy", {})
        )
    ):
        raise RuntimeError("V2.42.88 diagnosis drifted")


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
    print(json.dumps({"path": str(OUTPUT), "payload_sha256": report["diagnosis_payload_sha256"]}, sort_keys=True))
