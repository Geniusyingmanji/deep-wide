#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.48.44/48 exact-220 runs.

The two runs use the same visible task vector, prompt, model, search family,
budgets, and concurrency, but they are independent retrieval/generation/judge
rollouts.  V2.48.48 changes the projection cap from 16k to 30k and records a
content-free projection receipt.  This script joins opaque identifiers only in
memory and publishes aggregate counts, means, bins, correlations, and paired
uncertainty.  It never emits a task identifier, question, prediction, answer,
query, URL, page, field name, evaluator message, or credential.

All predictions and evaluator rows are frozen before this analysis.  The
output is diagnostic-only and cannot route, retry, re-evaluate, or select a
prediction in either parent run.
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

from deepwide_agent import v24848_atomic_table_header_30k_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24846_atomic_table_header_30k_profile import validate_receipt  # noqa: E402


DATE = "20260808"
OUTPUT = Path(
    f"results/v24849_v24844_v24848_projection_budget_diagnosis_v1_{DATE}.json"
)
SELECTED = 220
BOOTSTRAP_SEED = 24849
BOOTSTRAP_RESAMPLES = 20_000
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
INSTANCE = re.compile(r"(?:deep2wide_result|wide2deep_ws)_[^\"\\]+")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
VERSIONS = {
    "v24844": {
        "root": Path(f"outputs/v24844_atomic_table_header_exact220_v1_{DATE}"),
        "result": Path(
            f"results/v24844_atomic_table_header_exact220_result_v1_{DATE}.json"
        ),
        "forward": Path(
            f"results/v24844_atomic_table_header_exact220_forward_audit_v1_{DATE}.json"
        ),
        "post": Path(
            f"results/v24844_atomic_table_header_exact220_postresult_audit_v1_{DATE}.json"
        ),
        "protocol_id": "v24844_fresh_v24842_atomic_table_header_exact220_v1",
    },
    "v24848": {
        "root": contract.OUTPUT_ROOT,
        "result": Path(
            f"results/v24848_atomic_table_header_30k_exact220_result_v1_{DATE}.json"
        ),
        "forward": contract.FORWARD_AUDIT,
        "post": Path(
            f"results/v24848_atomic_table_header_30k_exact220_postresult_audit_v1_{DATE}.json"
        ),
        "protocol_id": contract.PROTOCOL_ID,
    },
}


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.49 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.49 expected JSON object")
    return value


def _jsonl(relative: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in _ordinary(relative).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.48.49 expected JSONL objects")
    return rows


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, paths in VERSIONS.items():
        result = _read(paths["result"])
        forward = _read(paths["forward"])
        post = _read(paths["post"])
        summary = _read(paths["root"] / "run_summary.json")
        freeze = _read(paths["root"] / "prediction_freeze.json")
        runtime = paths["root"] / "runtime_predictions.jsonl"
        evaluator = paths["root"] / "evaluator/conservative_summary.json"
        if (
            result.get("protocol_id") != paths["protocol_id"]
            or result.get("selected") != SELECTED
            or result.get("failure_as_zero") is not True
            or not _sealed(result, "result_payload_sha256")
            or forward.get("protocol_id") != paths["protocol_id"]
            or forward.get("audit_valid") is not True
            or forward.get("findings") != []
            or not _sealed(forward, "audit_payload_sha256")
            or post.get("protocol_id") != paths["protocol_id"]
            or post.get("audit_valid") is not True
            or post.get("findings") != []
            or not _sealed(post, "audit_payload_sha256")
            or summary.get("selected") != SELECTED
            or summary.get("completed") != SELECTED
            or summary.get("failed") != 0
            or freeze.get("selected") != SELECTED
            or freeze.get("terminal") != SELECTED
            or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
            or freeze.get("runtime_predictions_sha256")
            != contract.sha256(ROOT / runtime)
            or post.get("provenance", {}).get("conservative_summary_sha256")
            != contract.sha256(ROOT / evaluator)
        ):
            raise RuntimeError(f"V2.48.49 frozen parent drifted: {name}")
        output[name] = {
            "result": result,
            "forward": forward,
            "post": post,
            "summary": summary,
        }
    return output


def _runtime(relative: Path) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for row in _jsonl(relative):
        opaque = row.get("opaque_id")
        if (
            not isinstance(opaque, str)
            or OPAQUE.fullmatch(opaque) is None
            or opaque in output
            or row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            or not isinstance(row.get("prediction_sha256"), str)
            or len(row["prediction_sha256"]) != 64
            or not isinstance(row.get("completion_kind"), str)
        ):
            raise RuntimeError("V2.48.49 runtime row drifted")
        output[opaque] = {
            "prediction_sha256": row["prediction_sha256"],
            "completion_kind": row["completion_kind"],
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.49 runtime denominator drifted")
    return output


def _metrics(relative: Path) -> dict[str, dict[str, Any]]:
    rows = _read(relative).get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.49 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque = row.get("opaque_id") if isinstance(row, Mapping) else None
        metrics = row.get("metrics") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque, str)
            or OPAQUE.fullmatch(opaque) is None
            or opaque in output
            or not isinstance(row.get("evaluator_valid"), bool)
            or not isinstance(metrics, Mapping)
            or any(
                isinstance(metrics.get(key), bool)
                or not isinstance(metrics.get(key), (int, float))
                or not math.isfinite(float(metrics[key]))
                for key in QUALITY
            )
        ):
            raise RuntimeError("V2.48.49 evaluator row drifted")
        error = str(row.get("evaluator_error") or "")
        output[opaque] = {
            "valid": bool(row["evaluator_valid"]),
            "error_kind": None
            if row["evaluator_valid"]
            else "out_of_range_metric"
            if "out-of-range" in error
            else "empty_inner_join_assignment"
            if "internal error" in error.casefold()
            else "other",
            "metrics": {key: float(metrics[key]) for key in QUALITY},
        }
    return output


def _nonnegative_integer(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V2.48.49 invalid task integer: {name}")
    return value


def _nonnegative_number(value: Any, *, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise RuntimeError(f"V2.48.49 invalid task number: {name}")
    return float(value)


def _tasks(root: Path, *, receipts: bool) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        directory = root / "tasks" / f"task_{position:04d}"
        envelope = _read(directory / "result.json")
        result = envelope.get("result") or {}
        opaque = result.get("opaque_id")
        retrieval = ((result.get("two_wave_retrieval") or {}).get("receipt") or {})
        total = retrieval.get("total") or {}
        search = (result.get("cost") or {}).get("search") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        values = {
            "search_calls": _nonnegative_integer(search.get("calls"), name="search calls"),
            "search_failures": _nonnegative_integer(
                search.get("failures"), name="search failures"
            ),
            "fetch_calls": _nonnegative_integer(
                search.get("fetch_calls"), name="fetch calls"
            ),
            "fetch_failures": _nonnegative_integer(
                search.get("fetch_failures"), name="fetch failures"
            ),
            "usable_pages": _nonnegative_integer(
                total.get("usable_pages"), name="usable pages"
            ),
            "novel_pages": _nonnegative_integer(
                total.get("novel_pages"), name="novel pages"
            ),
            "unique_hosts": _nonnegative_integer(
                total.get("unique_hosts"), name="unique hosts"
            ),
            "raw_content_chars": _nonnegative_integer(
                total.get("content_chars"), name="raw content chars"
            ),
            "projected_chars": _nonnegative_integer(
                (result.get("evidence") or {}).get("projected_chars"),
                name="projected chars",
            ),
            "synthesized_rows": _nonnegative_integer(
                table.get("row_count"), name="synthesized rows"
            ),
            "unknown_cell_ratio": _nonnegative_number(
                table.get("unknown_cell_ratio"), name="unknown ratio"
            ),
            "system_total_tokens": _nonnegative_integer(
                (result.get("cost") or {}).get("system_total_tokens"),
                name="system tokens",
            ),
            "task_wall_seconds": _nonnegative_number(
                (result.get("attributed_timing") or {}).get("task_wall_seconds"),
                name="task wall",
            ),
        }
        if values["unknown_cell_ratio"] > 1:
            raise RuntimeError("V2.48.49 unknown-cell ratio exceeded one")
        if (
            not isinstance(opaque, str)
            or OPAQUE.fullmatch(opaque) is None
            or opaque in output
        ):
            raise RuntimeError("V2.48.49 task identity drifted")
        if receipts:
            receipt = validate_receipt(_read(directory / contract.PROJECTION_RECEIPT_NAME))
            values.update(
                {
                    "receipt_rendered_chars": int(
                        receipt["projected_rendered_characters"]
                    ),
                    "input_content_chars": int(receipt["input_content_characters"]),
                    "allocated_content_chars": int(
                        receipt["allocated_content_characters"]
                    ),
                    "input_pages": int(receipt["input_page_count"]),
                    "projected_pages": int(receipt["projected_page_count"]),
                    "input_blocks": int(receipt["input_block_count"]),
                    "projected_blocks": int(receipt["projected_block_count"]),
                    "supported_requirements": int(
                        receipt["supported_visible_requirement_group_count"]
                    ),
                    "retained_requirements": int(
                        receipt[
                            "retained_supported_visible_requirement_group_count"
                        ]
                    ),
                    "missed_requirements": int(
                        receipt["missed_supported_visible_requirement_group_count"]
                    ),
                    "table_continuations": int(
                        receipt["selected_table_continuation_block_count"]
                    ),
                    "header_dependencies": int(
                        receipt["table_header_dependency_addition_count"]
                    ),
                    "orphans": int(
                        receipt["orphan_selected_table_continuation_block_count"]
                    ),
                }
            )
        output[opaque] = values
    return output


def _aggregate_metrics(
    ids: Iterable[str], values: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    selected = sorted(ids)
    if not selected:
        raise RuntimeError("V2.48.49 cannot aggregate empty metric group")
    metrics = {
        key: sum(float(values[item]["metrics"][key]) for item in selected)
        / len(selected)
        for key in QUALITY
    }
    metrics["quality_composite"] = sum(metrics[key] for key in COMPOSITE) / 4
    return {
        "n": len(selected),
        "evaluator_valid": sum(values[item]["valid"] is True for item in selected),
        "whole_table_successes": sum(
            float(values[item]["metrics"]["score"]) > 0 for item in selected
        ),
        "metrics": metrics,
    }


def _mean(ids: Iterable[str], values: Mapping[str, Mapping[str, Any]], key: str) -> float:
    selected = list(ids)
    return sum(float(values[item][key]) for item in selected) / len(selected)


def _correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or not xs:
        raise RuntimeError("V2.48.49 correlation vector drifted")
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    dx = [value - mean_x for value in xs]
    dy = [value - mean_y for value in ys]
    denominator = math.sqrt(
        sum(value * value for value in dx) * sum(value * value for value in dy)
    )
    if denominator == 0:
        return None
    return round(sum(a * b for a, b in zip(dx, dy, strict=True)) / denominator, 12)


def _paired(
    ids: set[str],
    before: Mapping[str, Mapping[str, Any]],
    after: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    exact: Counter[str] = Counter()
    deltas: list[float] = []
    directions: Counter[str] = Counter()
    for item in sorted(ids):
        old_exact = float(before[item]["metrics"]["score"]) > 0
        new_exact = float(after[item]["metrics"]["score"]) > 0
        exact[
            "both_exact"
            if old_exact and new_exact
            else "lost_exact"
            if old_exact
            else "gained_exact"
            if new_exact
            else "neither_exact"
        ] += 1
        delta = sum(
            float(after[item]["metrics"][key])
            - float(before[item]["metrics"][key])
            for key in COMPOSITE
        ) / 4
        deltas.append(delta)
        directions["improved" if delta > 0 else "worsened" if delta < 0 else "tied"] += 1
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return {
        "n": len(ids),
        "exact_transitions": dict(sorted(exact.items())),
        "composite_delta": sum(deltas) / len(deltas),
        "composite_task_cluster_bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "resamples": BOOTSTRAP_RESAMPLES,
            "percentile_95_interval": [means[500], means[19499]],
            "interval_excludes_zero": means[500] > 0 or means[19499] < 0,
            "direction_counts": dict(sorted(directions.items())),
        },
    }


def _delta_bins(
    ids: set[str],
    metrics_before: Mapping[str, Mapping[str, Any]],
    metrics_after: Mapping[str, Mapping[str, Any]],
    tasks_before: Mapping[str, Mapping[str, Any]],
    tasks_after: Mapping[str, Mapping[str, Any]],
    *,
    key: str,
    intervals: tuple[tuple[float, float], ...],
) -> list[dict[str, Any]]:
    output = []
    for lower, upper in intervals:
        selected = [
            item
            for item in ids
            if lower
            <= float(tasks_after[item][key]) - float(tasks_before[item][key])
            < upper
        ]
        if not selected:
            continue
        deltas = [
            sum(
                float(metrics_after[item]["metrics"][name])
                - float(metrics_before[item]["metrics"][name])
                for name in COMPOSITE
            )
            / 4
            for item in selected
        ]
        output.append(
            {
                "lower_inclusive": lower,
                "upper_exclusive": upper,
                "n": len(selected),
                "mean_mechanism_delta": sum(
                    float(tasks_after[item][key]) - float(tasks_before[item][key])
                    for item in selected
                )
                / len(selected),
                "mean_composite_delta": sum(deltas) / len(deltas),
                "improved": sum(value > 0 for value in deltas),
                "tied": sum(value == 0 for value in deltas),
                "worsened": sum(value < 0 for value in deltas),
            }
        )
    return output


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    runtime = {
        name: _runtime(paths["root"] / "runtime_predictions.jsonl")
        for name, paths in VERSIONS.items()
    }
    metrics = {
        name: _metrics(paths["root"] / "evaluator/conservative_summary.json")
        for name, paths in VERSIONS.items()
    }
    tasks = {
        "v24844": _tasks(VERSIONS["v24844"]["root"], receipts=False),
        "v24848": _tasks(VERSIONS["v24848"]["root"], receipts=True),
    }
    ids = set(runtime["v24844"])
    if any(
        ids != set(values)
        for values in (*runtime.values(), *metrics.values(), *tasks.values())
    ):
        raise RuntimeError("V2.48.49 paired identity population drifted")

    before = _aggregate_metrics(ids, metrics["v24844"])
    after = _aggregate_metrics(ids, metrics["v24848"])
    paired = _paired(ids, metrics["v24844"], metrics["v24848"])
    common_valid = {
        item
        for item in ids
        if metrics["v24844"][item]["valid"]
        and metrics["v24848"][item]["valid"]
    }
    invalid_before = {item for item in ids if not metrics["v24844"][item]["valid"]}
    invalid_after = {item for item in ids if not metrics["v24848"][item]["valid"]}
    validity = Counter(
        f"before_{'valid' if metrics['v24844'][item]['valid'] else 'invalid'}_"
        f"after_{'valid' if metrics['v24848'][item]['valid'] else 'invalid'}"
        for item in ids
    )
    mechanisms = (
        "search_calls",
        "search_failures",
        "fetch_calls",
        "fetch_failures",
        "usable_pages",
        "novel_pages",
        "unique_hosts",
        "raw_content_chars",
        "projected_chars",
        "synthesized_rows",
        "unknown_cell_ratio",
        "system_total_tokens",
        "task_wall_seconds",
    )
    mechanism_means = {
        key: {
            "v24844": _mean(ids, tasks["v24844"], key),
            "v24848": _mean(ids, tasks["v24848"], key),
            "v24848_minus_v24844": _mean(ids, tasks["v24848"], key)
            - _mean(ids, tasks["v24844"], key),
        }
        for key in mechanisms
    }
    composite_deltas = [
        sum(
            float(metrics["v24848"][item]["metrics"][key])
            - float(metrics["v24844"][item]["metrics"][key])
            for key in COMPOSITE
        )
        / 4
        for item in sorted(ids)
    ]
    correlations = {
        key: _correlation(
            [
                float(tasks["v24848"][item][key])
                - float(tasks["v24844"][item][key])
                for item in sorted(ids)
            ],
            composite_deltas,
        )
        for key in (
            "fetch_failures",
            "usable_pages",
            "unique_hosts",
            "raw_content_chars",
            "projected_chars",
            "synthesized_rows",
            "unknown_cell_ratio",
            "system_total_tokens",
        )
    }
    v48_receipt = parents["v24848"]["summary"]["projection_receipts"]
    above_16k = {
        item for item in ids if tasks["v24848"][item]["receipt_rendered_chars"] > 16_000
    }
    at_or_below_16k = ids - above_16k
    cap_exposure = {
        "above_16k": {
            "n": len(above_16k),
            "v24848_metrics": _aggregate_metrics(above_16k, metrics["v24848"]),
            "paired": _paired(above_16k, metrics["v24844"], metrics["v24848"]),
            "mean_v24848_rendered_chars": _mean(
                above_16k, tasks["v24848"], "receipt_rendered_chars"
            ),
        },
        "at_or_below_16k": {
            "n": len(at_or_below_16k),
            "v24848_metrics": _aggregate_metrics(at_or_below_16k, metrics["v24848"]),
            "paired": _paired(
                at_or_below_16k, metrics["v24844"], metrics["v24848"]
            ),
            "mean_v24848_rendered_chars": _mean(
                at_or_below_16k, tasks["v24848"], "receipt_rendered_chars"
            ),
        },
    }
    exact_receipt_totals = {
        "valid_receipts": sum(
            1 for item in ids if tasks["v24848"][item]["receipt_rendered_chars"] >= 0
        ),
        "rendered_characters": sum(
            tasks["v24848"][item]["receipt_rendered_chars"] for item in ids
        ),
        "retained_supported_visible_requirements": sum(
            tasks["v24848"][item]["retained_requirements"] for item in ids
        ),
        "missed_supported_visible_requirements": sum(
            tasks["v24848"][item]["missed_requirements"] for item in ids
        ),
        "selected_table_continuations": sum(
            tasks["v24848"][item]["table_continuations"] for item in ids
        ),
        "table_header_dependency_additions": sum(
            tasks["v24848"][item]["header_dependencies"] for item in ids
        ),
        "orphan_table_continuations": sum(
            tasks["v24848"][item]["orphans"] for item in ids
        ),
    }
    checks = {
        "both_parent_chains_valid": len(parents) == 2,
        "paired_denominator_exact220": len(ids) == SELECTED,
        "overall_metrics_reconcile": before["metrics"]["quality_composite"]
        == parents["v24844"]["result"]["metrics"]["all_220"]["quality_composite"]
        and after["metrics"]["quality_composite"]
        == parents["v24848"]["result"]["metrics"]["all_220"]["quality_composite"],
        "exact_transitions_reconcile": sum(paired["exact_transitions"].values())
        == SELECTED,
        "validity_transitions_reconcile": sum(validity.values()) == SELECTED,
        "cap_exposure_partition_reconciles": len(above_16k) + len(at_or_below_16k)
        == SELECTED,
        "projection_receipt_totals_reconcile": all(
            exact_receipt_totals[key] == v48_receipt[key]
            for key in exact_receipt_totals
        ),
        "v24848_receipts_complete_and_content_free": v48_receipt["valid_receipts"]
        == SELECTED
        and v48_receipt["missing_receipts"] == 0
        and v48_receipt[
            "contains_question_query_url_host_page_projection_content_or_hash"
        ]
        is False,
        "v24848_atomic_continuation_mechanism_inactive": exact_receipt_totals[
            "selected_table_continuations"
        ]
        == exact_receipt_totals["table_header_dependency_additions"]
        == exact_receipt_totals["orphan_table_continuations"]
        == 0,
        "no_active_parent_or_evaluator_required_by_analysis": True,
    }
    value = {
        "artifact_version": 1,
        "role": "v24849_v24844_v24848_aggregate_projection_budget_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "thirty_k_fullset_no_go_is_confounded_and_quality_gating_precedes_another_public_run",
        "parents": {
            name: {
                "result_sha256": contract.sha256(ROOT / paths["result"]),
                "forward_audit_sha256": contract.sha256(ROOT / paths["forward"]),
                "postresult_audit_sha256": contract.sha256(ROOT / paths["post"]),
                "runtime_predictions_sha256": contract.sha256(
                    ROOT / paths["root"] / "runtime_predictions.jsonl"
                ),
                "run_summary_sha256": contract.sha256(
                    ROOT / paths["root"] / "run_summary.json"
                ),
                "conservative_summary_sha256": contract.sha256(
                    ROOT / paths["root"] / "evaluator/conservative_summary.json"
                ),
            }
            for name, paths in VERSIONS.items()
        },
        "boundary": {
            "both_exact220_predictions_and_evaluators_terminal_before_analysis": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "task_identifier_question_prediction_answer_query_url_page_field_or_evaluator_text_emitted": False,
            "per_task_metric_or_transition_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_feedback_retry_resume_skip_or_selective_revaluation": False,
            "historical_metric_bin_or_evaluator_outcome_authorized_as_future_runtime_route": False,
        },
        "overall": {
            "v24844": before,
            "v24848": after,
            "delta_v24848_minus_v24844": {
                "evaluator_valid": after["evaluator_valid"] - before["evaluator_valid"],
                "whole_table_successes": after["whole_table_successes"]
                - before["whole_table_successes"],
                "metrics": {
                    key: after["metrics"][key] - before["metrics"][key]
                    for key in (*QUALITY, "quality_composite")
                },
            },
            "prediction_sha256_identical_tasks": sum(
                runtime["v24844"][item]["prediction_sha256"]
                == runtime["v24848"][item]["prediction_sha256"]
                for item in ids
            ),
            "prediction_sha256_changed_tasks": sum(
                runtime["v24844"][item]["prediction_sha256"]
                != runtime["v24848"][item]["prediction_sha256"]
                for item in ids
            ),
            "paired": paired,
        },
        "common_evaluator_valid_intersection": {
            "n": len(common_valid),
            "v24844": _aggregate_metrics(common_valid, metrics["v24844"]),
            "v24848": _aggregate_metrics(common_valid, metrics["v24848"]),
        },
        "evaluator": {
            "validity_transitions": dict(sorted(validity.items())),
            "v24844_invalid_failure_as_zero": len(invalid_before),
            "v24848_invalid_failure_as_zero": len(invalid_after),
            "invalid_intersection": len(invalid_before & invalid_after),
            "invalid_union": len(invalid_before | invalid_after),
            "error_taxonomy": {
                "v24844": dict(
                    sorted(
                        Counter(
                            metrics["v24844"][item]["error_kind"]
                            for item in invalid_before
                        ).items()
                    )
                ),
                "v24848": dict(
                    sorted(
                        Counter(
                            metrics["v24848"][item]["error_kind"]
                            for item in invalid_after
                        ).items()
                    )
                ),
            },
            "selective_retry_or_revaluation": False,
        },
        "mechanism": {
            "means": mechanism_means,
            "delta_pearson_correlation_with_composite_delta": correlations,
            "projected_character_delta_bins": _delta_bins(
                ids,
                metrics["v24844"],
                metrics["v24848"],
                tasks["v24844"],
                tasks["v24848"],
                key="projected_chars",
                intervals=(
                    (-1_000_000, -4_000),
                    (-4_000, 0),
                    (0, 4_000),
                    (4_000, 8_000),
                    (8_000, 12_000),
                    (12_000, 1_000_000),
                ),
            ),
            "raw_content_character_delta_bins": _delta_bins(
                ids,
                metrics["v24844"],
                metrics["v24848"],
                tasks["v24844"],
                tasks["v24848"],
                key="raw_content_chars",
                intervals=(
                    (-1_000_000, -10_000),
                    (-10_000, 0),
                    (0, 10_000),
                    (10_000, 30_000),
                    (30_000, 1_000_000),
                ),
            ),
            "v24848_cap_exposure": cap_exposure,
            "v24848_projection_receipt_totals": exact_receipt_totals,
        },
        "conclusions": {
            "v24848_exceeds_v24844_exact_or_composite": False,
            "v24847_external_shared_prefix_gain_transferred_to_deepwidebench": False,
            "thirty_k_projection_is_a_fullset_improvement": False,
            "independent_fullset_rollouts_identify_projection_cap_causality": False,
            "retrieval_generation_and_evaluator_variation_remain_confounders": True,
            "v24848_naturally_tested_atomic_table_continuation_closure": False,
            "more_rendered_characters_are_sufficient_for_quality": False,
            "quality_identity_dependency_and_redundancy_gating_is_next": True,
            "entropy_or_information_gain_credit_validated": False,
            "leaderboard_or_sota_established": False,
        },
        "next_work": {
            "do_not_launch_another_unchanged_public_exact220": True,
            "fresh_shared_prefix_arms": [
                "fixed_atomic_16k",
                "fixed_atomic_30k",
                "matched_cost_visible_quality_gated_30k",
            ],
            "quality_gate_visible_only_features": [
                "visible_requirement_coverage",
                "source_and_record_identity",
                "target_value_binding",
                "source_dependency",
                "novelty",
                "conflict",
                "redundancy",
                "structure",
            ],
            "same_raw_page_bytes_before_arm_branch": True,
            "same_model_prompt_output_cap_and_concurrency": True,
            "entropy_information_gain_shadow_only": True,
            "signed_credit_requires_same_state_deletion_replacement_or_sibling_continuation": True,
            "public_exact220_requires_external_exact_and_composite_go": True,
        },
        "authorization": {
            "visible_quality_gated_projector_build": all(checks.values()),
            "fresh_shared_prefix_external_protocol_design": all(checks.values()),
            "external_launch": False,
            "new_public_dev64_or_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
    }
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if (
        OPAQUE.search(encoded)
        or INSTANCE.search(encoded)
        or SECRET.search(encoded)
        or "required_columns" in encoded
        or "the entity is wrong" in encoded
    ):
        raise RuntimeError("V2.48.49 emitted prohibited task-level content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate(value, rebuild=False)


def validate(value: Mapping[str, Any], *, rebuild: bool = True) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24849_v24844_v24848_aggregate_projection_budget_diagnosis"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("conclusions", {}).get(
            "v24847_external_shared_prefix_gain_transferred_to_deepwidebench"
        )
        is not False
        or copied.get("authorization")
        != {
            "visible_quality_gated_projector_build": True,
            "fresh_shared_prefix_external_protocol_design": True,
            "external_launch": False,
            "new_public_dev64_or_exact220": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.49 diagnosis drifted")
    if rebuild:
        expected = build(now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.49 diagnosis is not reproducible")
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
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "exact_transitions": artifact["overall"]["paired"][
                    "exact_transitions"
                ],
                "composite_delta": artifact["overall"][
                    "delta_v24848_minus_v24844"
                ]["metrics"]["quality_composite"],
                "bootstrap_interval": artifact["overall"]["paired"][
                    "composite_task_cluster_bootstrap"
                ]["percentile_95_interval"],
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
