#!/usr/bin/env python3
"""Aggregate-only four-run diagnosis and synthetic structure-closure witness.

All four exact-220 predictions and evaluator outputs were frozen before this
analysis. Opaque identifiers are used only for in-memory alignment and are
never emitted. Historical scores, transitions, and strata are explicitly
forbidden as future runtime inputs. The synthetic witness establishes only a
reachable projector defect; independent web/model/judge samples prevent a
causal attribution of public-benchmark score differences.
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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24840_structure_preserving_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24839_structure_preserving_projector import (  # noqa: E402
    ProjectionPolicy,
    build_projection,
    visible_requirement_groups,
)


OUTPUT = Path("results/v24841_four_run_structure_closure_diagnosis_v1_20260808.json")
VERSIONS = {
    "v24800": {
        "root": Path("outputs/v24800_exact220_v1_20260807"),
        "result": Path("results/v24800_exact220_result_v1_20260807.json"),
        "postaudit": Path("results/v24800_exact220_postresult_audit_v1_20260807.json"),
    },
    "v24834": {
        "root": Path("outputs/v24834_coverage_margin_exact220_v1_20260807"),
        "result": Path("results/v24834_coverage_margin_exact220_result_v1_20260807.json"),
        "postaudit": Path("results/v24834_coverage_margin_exact220_postresult_audit_v1_20260807.json"),
    },
    "v24837": {
        "root": Path("outputs/v24837_information_bottleneck_exact220_v1_20260807"),
        "result": Path("results/v24837_information_bottleneck_exact220_result_v1_20260807.json"),
        "postaudit": Path("results/v24837_information_bottleneck_exact220_postresult_audit_v1_20260807.json"),
    },
    "v24840": {
        "root": Path("outputs/v24840_structure_preserving_exact220_v1_20260807"),
        "result": Path("results/v24840_structure_preserving_exact220_result_v1_20260807.json"),
        "postaudit": Path("results/v24840_structure_preserving_exact220_postresult_audit_v1_20260807.json"),
    },
}
SELECTED = 220
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
MECHANISM = (
    "projected_chars",
    "raw_content_chars",
    "usable_pages",
    "unique_hosts",
    "queries_executed",
    "fetches_attempted",
    "model_input_tokens",
    "system_total_tokens",
    "synthesized_rows",
    "unknown_cell_ratio",
    "task_wall_seconds",
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
BOOTSTRAP_SEED = 24841
BOOTSTRAP_RESAMPLES = 20_000


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.41 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.41 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_parents() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for name, paths in VERSIONS.items():
        result = _read(paths["result"])
        post = _read(paths["postaudit"])
        summary = _read(paths["root"] / "run_summary.json")
        if (
            result.get("selected") != SELECTED
            or result.get("failure_as_zero") is not True
            or not _sealed(result, "result_payload_sha256")
            or post.get("audit_valid") is not True
            or post.get("findings") != []
            or not _sealed(post, "audit_payload_sha256")
            or summary.get("selected") != SELECTED
            or summary.get("completed") != SELECTED
            or summary.get("failed") != 0
        ):
            raise RuntimeError(f"V2.48.41 frozen parent chain drifted: {name}")
        output[name] = {"result": result, "summary": summary}
    return output


def _metrics(root: Path) -> dict[str, dict[str, Any]]:
    rows = _read(root / "evaluator/conservative_summary.json").get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.48.41 evaluator denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id") if isinstance(row, Mapping) else None
        metric = row.get("metrics") if isinstance(row, Mapping) else None
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(metric, Mapping)
            or any(
                isinstance(metric.get(key), bool)
                or not isinstance(metric.get(key), (int, float))
                or not math.isfinite(float(metric[key]))
                for key in QUALITY
            )
            or not isinstance(row.get("evaluator_valid"), bool)
        ):
            raise RuntimeError("V2.48.41 evaluator row drifted")
        output[opaque_id] = {
            "valid": bool(row["evaluator_valid"]),
            "metrics": {key: float(metric[key]) for key in QUALITY},
        }
    return output


def _tasks(root: Path) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for position in range(1, SELECTED + 1):
        envelope = _read(root / "tasks" / f"task_{position:04d}" / "result.json")
        result = envelope.get("result") or {}
        opaque_id = result.get("opaque_id")
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        total = receipt.get("total") or {}
        controller = receipt.get("controller") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        evidence = result.get("evidence") or {}
        model = (result.get("cost") or {}).get("model") or {}
        timing = result.get("attributed_timing") or {}
        if (
            not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or retrieval.get("status") != "completed"
            or controller.get("decision") not in {"expand", "stop"}
            or controller.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            )
            is not False
        ):
            raise RuntimeError("V2.48.41 task receipt drifted")
        values = {
            "projected_chars": evidence.get("projected_chars"),
            "raw_content_chars": total.get("content_chars"),
            "usable_pages": total.get("usable_pages"),
            "unique_hosts": total.get("unique_hosts"),
            "queries_executed": total.get("queries_executed"),
            "fetches_attempted": total.get("fetches_attempted"),
            "model_input_tokens": model.get("input_tokens"),
            "system_total_tokens": (result.get("cost") or {}).get("system_total_tokens"),
            "synthesized_rows": table.get("row_count"),
        }
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in values.values()
        ):
            raise RuntimeError("V2.48.41 task integer metric drifted")
        unknown = table.get("unknown_cell_ratio")
        wall = timing.get("task_wall_seconds")
        if (
            isinstance(unknown, bool)
            or not isinstance(unknown, (int, float))
            or not 0 <= float(unknown) <= 1
            or isinstance(wall, bool)
            or not isinstance(wall, (int, float))
            or not math.isfinite(float(wall))
            or float(wall) < 0
        ):
            raise RuntimeError("V2.48.41 task continuous metric drifted")
        output[opaque_id] = {
            **values,
            "unknown_cell_ratio": float(unknown),
            "task_wall_seconds": float(wall),
            "decision": str(controller["decision"]),
            "fallback": "fallback" in str(result.get("completion_kind", "")),
        }
    return output


def _aggregate(
    ids: set[str], metrics: Mapping[str, Mapping[str, Any]], tasks: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    quality = {
        key: sum(float(metrics[item]["metrics"][key]) for item in ids) / len(ids)
        for key in QUALITY
    }
    quality["quality_composite"] = sum(quality[key] for key in COMPOSITE) / 4
    return {
        "n": len(ids),
        "evaluator_valid": sum(bool(metrics[item]["valid"]) for item in ids),
        "whole_table_successes": sum(
            float(metrics[item]["metrics"]["score"]) > 0 for item in ids
        ),
        "fallback_tables": sum(bool(tasks[item]["fallback"]) for item in ids),
        "retrieval_routes": dict(
            sorted(Counter(str(tasks[item]["decision"]) for item in ids).items())
        ),
        "metrics": quality,
        "mechanism": {
            key: sum(float(tasks[item][key]) for item in ids) / len(ids)
            for key in MECHANISM
        },
    }


def _paired(
    ids: set[str], control: Mapping[str, Mapping[str, Any]], candidate: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    exact = Counter()
    valid = Counter()
    values: list[float] = []
    for item in ids:
        a_exact = float(control[item]["metrics"]["score"]) > 0
        b_exact = float(candidate[item]["metrics"]["score"]) > 0
        exact[
            "both_exact" if a_exact and b_exact else "lost_exact" if a_exact else "gained_exact" if b_exact else "neither_exact"
        ] += 1
        a_valid = bool(control[item]["valid"])
        b_valid = bool(candidate[item]["valid"])
        valid[
            "both_valid" if a_valid and b_valid else "lost_valid" if a_valid else "gained_valid" if b_valid else "neither_valid"
        ] += 1
        values.append(
            sum(
                float(candidate[item]["metrics"][key])
                - float(control[item]["metrics"][key])
                for key in COMPOSITE
            )
            / 4
        )
    rng = random.Random(BOOTSTRAP_SEED)
    means = sorted(
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return {
        "n": len(ids),
        "exact_transitions": dict(sorted(exact.items())),
        "evaluator_validity_transitions": dict(sorted(valid.items())),
        "composite_delta": sum(values) / len(values),
        "composite_task_cluster_bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "resamples": BOOTSTRAP_RESAMPLES,
            "percentile_95_interval": [means[500], means[19499]],
            "direction_counts": {
                "improved": sum(value > 0 for value in values),
                "tied": sum(value == 0 for value in values),
                "worsened": sum(value < 0 for value in values),
            },
        },
    }


def _synthetic_witness() -> dict[str, Any]:
    question = "Column names: Country | Target Metric. Return the row for Omega Republic."
    lines = ["| Country | Target Metric |", "|---|---:|"]
    lines.extend(f"| filler-{index:03d} | {index} |" for index in range(60))
    lines.append("| Omega Republic | 999 |")
    pages = [
        {
            "title": "long official table",
            "url": "https://official.example/table",
            "content": "\n".join(lines),
        }
    ]
    result = build_projection(
        question,
        pages,
        policy=ProjectionPolicy(
            total_character_cap=260,
            maximum_page_chars=260,
            block_character_cap=180,
        ),
    )
    projection = str(result["projection"])
    return {
        "policy_id": result["policy_id"],
        "same_visible_question_and_page_bytes_only": True,
        "rendered_characters": result["projected_rendered_characters"],
        "target_tail_row_retained": "| Omega Republic | 999 |" in projection,
        "table_header_retained": "| Country | Target Metric |" in projection,
        "orphan_target_row_without_table_header": "| Omega Republic | 999 |" in projection
        and "| Country | Target Metric |" not in projection,
        "benchmark_question_prediction_gold_or_evaluator_used": False,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    parents = _validate_parents()
    metrics = {name: _metrics(paths["root"]) for name, paths in VERSIONS.items()}
    tasks = {name: _tasks(paths["root"]) for name, paths in VERSIONS.items()}
    ids = set(metrics["v24800"])
    if any(ids != set(value) for value in (*metrics.values(), *tasks.values())):
        raise RuntimeError("V2.48.41 paired opaque identity set drifted")
    aggregates = {
        name: _aggregate(ids, metrics[name], tasks[name]) for name in VERSIONS
    }
    paired = {
        f"{control}_to_v24840": _paired(ids, metrics[control], metrics["v24840"])
        for control in ("v24800", "v24834", "v24837")
    }
    exact_frequency = Counter(
        sum(float(metrics[name][item]["metrics"]["score"]) > 0 for name in VERSIONS)
        for item in ids
    )
    valid_frequency = Counter(
        sum(bool(metrics[name][item]["valid"]) for name in VERSIONS) for item in ids
    )
    visible_groups = [
        len(visible_requirement_groups(task["question"]))
        for task in contract.task_vector(ROOT)
    ]
    witness = _synthetic_witness()
    checks = {
        "all_four_parent_chains_valid": len(parents) == 4,
        "all_four_metric_and_task_denominators_exact220": all(
            aggregate["n"] == SELECTED for aggregate in aggregates.values()
        ),
        "all_pair_transitions_exact220": all(
            sum(pair["exact_transitions"].values()) == SELECTED
            and sum(pair["evaluator_validity_transitions"].values()) == SELECTED
            for pair in paired.values()
        ),
        "bootstrap_denominators_exact220": all(pair["n"] == SELECTED for pair in paired.values()),
        "synthetic_orphan_table_row_reproduced": witness[
            "orphan_target_row_without_table_header"
        ]
        is True,
        "opaque_identifier_not_emitted": OPAQUE.search(json.dumps({"a": aggregates, "p": paired}))
        is None,
        "credential_literal_not_emitted": SECRET.search(json.dumps({"a": aggregates, "p": paired}))
        is None,
    }
    value = {
        "artifact_version": 1,
        "role": "v24841_four_run_aggregate_structure_closure_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "structure_quality_signal_positive_but_causal_gain_unproven_orphan_table_header_defect_reachable",
        "parents": {
            name: {
                "result_sha256": contract.sha256(ROOT / paths["result"]),
                "postresult_audit_sha256": contract.sha256(ROOT / paths["postaudit"]),
                "run_summary_sha256": contract.sha256(ROOT / paths["root"] / "run_summary.json"),
                "conservative_summary_sha256": contract.sha256(
                    ROOT / paths["root"] / "evaluator/conservative_summary.json"
                ),
            }
            for name, paths in VERSIONS.items()
        },
        "boundary": {
            "all_predictions_and_evaluators_terminal_before_analysis": True,
            "offline_alignment_uses_opaque_id_in_memory_only": True,
            "task_question_prediction_query_url_page_or_evaluator_text_emitted": False,
            "per_task_metric_transition_or_identifier_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "historical_metric_transition_or_stratum_authorized_as_future_runtime_input": False,
        },
        "aggregates": aggregates,
        "paired_to_v24840": paired,
        "cross_run_stability": {
            "exact_frequency_histogram": {
                str(key): exact_frequency.get(key, 0) for key in range(5)
            },
            "evaluator_valid_frequency_histogram": {
                str(key): valid_frequency.get(key, 0) for key in range(5)
            },
        },
        "visible_requirement_parser_coverage": {
            "selected": SELECTED,
            "zero_group_questions": sum(count == 0 for count in visible_groups),
            "positive_group_questions": sum(count > 0 for count in visible_groups),
            "mean_group_count": sum(visible_groups) / len(visible_groups),
            "maximum_group_count": max(visible_groups),
        },
        "synthetic_structure_witness": witness,
        "conclusions": {
            "v24840_composite_exceeds_v24837_point_estimate": aggregates["v24840"][
                "metrics"
            ]["quality_composite"]
            > aggregates["v24837"]["metrics"]["quality_composite"],
            "v24840_vs_v24837_composite_ci_excludes_zero": not (
                paired["v24837_to_v24840"]["composite_task_cluster_bootstrap"][
                    "percentile_95_interval"
                ][0]
                <= 0
                <= paired["v24837_to_v24840"]["composite_task_cluster_bootstrap"][
                    "percentile_95_interval"
                ][1]
            ),
            "v24840_exceeds_internal_v24800_exact_or_composite": aggregates["v24840"][
                "whole_table_successes"
            ]
            > aggregates["v24800"]["whole_table_successes"]
            or aggregates["v24840"]["metrics"]["quality_composite"]
            > aggregates["v24800"]["metrics"]["quality_composite"],
            "independent_search_fetch_generation_and_judge_samples_remain_confounders": True,
            "this_diagnosis_establishes_projector_causal_quality_gain": False,
            "orphan_long_table_row_without_header_is_reachable": witness[
                "orphan_target_row_without_table_header"
            ],
            "historical_score_or_transition_may_route_future_forward": False,
            "leaderboard_or_sota_established": False,
        },
        "next_work": {
            "candidate": "visible_only_atomic_table_header_closure_under_same_rendered_16k_cap",
            "single_mechanism_change": True,
            "required_properties": [
                "selected long-table tail block atomically requires its table header block",
                "insufficient budget drops the dependent tail instead of emitting orphan evidence",
                "same visible-question and same-forward fetched-page inputs only",
                "rendered context remains at most 16000 characters",
                "entropy and information gain remain shadow-only and assign zero credit",
            ],
            "required_external_gate": {
                "population": "unused_v24829_target_cell_disjoint_worldbank_32x4",
                "same_raw_page_bytes_before_projector_branch": True,
                "control": "v24839_structure_preserving_16k",
                "candidate": "table_header_closure_16k",
                "prediction_freeze_before_private_evaluator": True,
                "failure_as_zero_no_retry_resume_or_selective_revaluation": True,
            },
            "public_exact220_authorized": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "diagnosis_valid": all(checks.values()),
        "authorization": {
            "table_header_closure_projector_build": all(checks.values()),
            "fresh_external_shared_prefix_protocol_design": False,
            "external_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    if artifact["findings"]:
        raise RuntimeError(f"V2.48.41 diagnosis rejected: {artifact['findings']}")
    publish(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": artifact["diagnosis_valid"],
                "findings": artifact["findings"],
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
