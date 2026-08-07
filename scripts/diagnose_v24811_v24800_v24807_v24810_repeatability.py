#!/usr/bin/env python3
"""Aggregate-only diagnosis of three frozen same-algorithm exact-220 runs."""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24810_exact220_contract as contract  # noqa: E402


DATE = "20260807"
OUTPUT = Path(
    f"results/v24811_v24800_v24807_v24810_repeatability_diagnosis_v1_{DATE}.json"
)
VERSIONS = ("v24800", "v24807", "v24810")
SELECTED = 220
QUALITY = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
BOOTSTRAP_SEED = 24811
BOOTSTRAP_RESAMPLES = 20_000
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _paths(version: str) -> dict[str, Path]:
    root = Path(f"outputs/{version}_exact220_v1_{DATE}")
    return {
        "result": Path(f"results/{version}_exact220_result_v1_{DATE}.json"),
        "forward_audit": Path(
            f"results/{version}_exact220_forward_audit_v1_{DATE}.json"
        ),
        "postaudit": Path(
            f"results/{version}_exact220_postresult_audit_v1_{DATE}.json"
        ),
        "runtime": root / "runtime_predictions.jsonl",
        "summary": root / "run_summary.json",
        "eval": root / "evaluator/conservative_summary.json",
    }


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.48.11 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.11 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_run(root: Path, version: str) -> dict[str, dict[str, Any]]:
    paths = _paths(version)
    result = _read(root, paths["result"])
    forward = _read(root, paths["forward_audit"])
    post = _read(root, paths["postaudit"])
    summary = _read(root, paths["summary"])
    evaluator = _read(root, paths["eval"])
    if (
        result.get("selected") != SELECTED
        or result.get("failure_as_zero") is not True
        or not _sealed(result, "result_payload_sha256")
        or forward.get("audit_valid") is not True
        or forward.get("findings") != []
        or not _sealed(forward, "audit_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or forward.get("runtime_predictions_sha256")
        != contract.sha256(root / paths["runtime"])
        or post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(root / paths["eval"])
        or summary.get("selected") != SELECTED
        or len(evaluator.get("per_task") or []) != SELECTED
    ):
        raise RuntimeError(f"V2.48.11 {version} frozen chain drifted")
    return {
        "result": result,
        "forward": forward,
        "post": post,
        "summary": summary,
        "evaluator": evaluator,
    }


def _runtime(root: Path, path: Path) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for line in _ordinary(root, path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        opaque = row.get("opaque_id")
        if (
            not isinstance(row, dict)
            or not isinstance(opaque, str)
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
        ):
            raise RuntimeError("V2.48.11 runtime projection drifted")
        output[opaque] = {
            "prediction_sha256": row["prediction_sha256"],
            "completion_kind": str(row.get("completion_kind") or "unknown"),
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.11 runtime denominator drifted")
    return output


def _metrics(evaluator: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in evaluator.get("per_task") or []:
        opaque = row.get("opaque_id")
        metrics = row.get("metrics")
        if (
            not isinstance(opaque, str)
            or OPAQUE.fullmatch(opaque) is None
            or opaque in output
            or not isinstance(row.get("evaluator_valid"), bool)
            or not isinstance(metrics, Mapping)
            or any(
                isinstance(metrics.get(name), bool)
                or not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                for name in QUALITY
            )
        ):
            raise RuntimeError("V2.48.11 evaluator row drifted")
        error = str(row.get("evaluator_error") or "")
        output[opaque] = {
            "valid": row["evaluator_valid"],
            "error_kind": None
            if row["evaluator_valid"]
            else "out_of_range_metric"
            if "out-of-range" in error
            else "empty_inner_join_assignment"
            if "internal error" in error
            else "other",
            "metrics": {name: float(metrics[name]) for name in QUALITY},
        }
    if len(output) != SELECTED:
        raise RuntimeError("V2.48.11 metric denominator drifted")
    return output


def _aggregate(values: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    metrics = {
        name: sum(float(row["metrics"][name]) for row in values.values())
        / SELECTED
        for name in QUALITY
    }
    metrics["quality_composite"] = sum(metrics[name] for name in COMPOSITE) / 4
    return {
        "n": SELECTED,
        "evaluator_valid": sum(row["valid"] is True for row in values.values()),
        "whole_table_successes": sum(
            row["metrics"]["score"] > 0 for row in values.values()
        ),
        "metrics": metrics,
    }


def _bootstrap_range(
    metrics: Mapping[str, Mapping[str, Mapping[str, Any]]], ids: list[str]
) -> dict[str, Any]:
    vectors = [
        [
            sum(metrics[version][item]["metrics"][name] for name in COMPOSITE)
            / 4
            for version in VERSIONS
        ]
        for item in ids
    ]
    rng = random.Random(BOOTSTRAP_SEED)
    ranges: list[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        means = [0.0, 0.0, 0.0]
        for _ in ids:
            row = vectors[rng.randrange(len(vectors))]
            for index, value in enumerate(row):
                means[index] += value
        means = [value / len(ids) for value in means]
        ranges.append(max(means) - min(means))
    ranges.sort()
    return {
        "unit": "task_cluster",
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "observed_run_mean_range": max(
            _aggregate(metrics[version])["metrics"]["quality_composite"]
            for version in VERSIONS
        )
        - min(
            _aggregate(metrics[version])["metrics"]["quality_composite"]
            for version in VERSIONS
        ),
        "percentile_95_interval": [
            ranges[int(0.025 * BOOTSTRAP_RESAMPLES)],
            ranges[int(0.975 * BOOTSTRAP_RESAMPLES) - 1],
        ],
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    runs = {version: _validate_run(root, version) for version in VERSIONS}
    runtime = {
        version: _runtime(root, _paths(version)["runtime"]) for version in VERSIONS
    }
    metrics = {
        version: _metrics(runs[version]["evaluator"]) for version in VERSIONS
    }
    ids = sorted(runtime[VERSIONS[0]])
    if any(set(runtime[v]) != set(ids) or set(metrics[v]) != set(ids) for v in VERSIONS):
        raise RuntimeError("V2.48.11 paired population drifted")
    aggregates = {version: _aggregate(metrics[version]) for version in VERSIONS}
    prediction_identity = Counter(
        str(len({runtime[v][item]["prediction_sha256"] for v in VERSIONS}))
        for item in ids
    )
    success_patterns = Counter(
        "".join("1" if metrics[v][item]["metrics"]["score"] > 0 else "0" for v in VERSIONS)
        for item in ids
    )
    successes = {
        version: {
            item for item in ids if metrics[version][item]["metrics"]["score"] > 0
        }
        for version in VERSIONS
    }
    all_success = set.intersection(*(successes[v] for v in VERSIONS))
    any_success = set.union(*(successes[v] for v in VERSIONS))
    invalid = {
        version: {item for item in ids if not metrics[version][item]["valid"]}
        for version in VERSIONS
    }
    all_invalid = set.intersection(*(invalid[v] for v in VERSIONS))
    any_invalid = set.union(*(invalid[v] for v in VERSIONS))
    value = {
        "artifact_version": 1,
        "role": "v24811_three_run_aggregate_only_repeatability_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "same_algorithm_three_run_variance_material_no_sota",
        "parents": {
            version: {
                name + "_sha256": contract.sha256(root / path)
                for name, path in _paths(version).items()
            }
            for version in VERSIONS
        },
        "boundary": {
            "all_three_exact220_freezes_and_evaluators_complete": True,
            "same_algorithm_task_vector_model_search_budgets_and_concurrency": True,
            "offline_opaque_id_join_only": True,
            "prediction_field_read": False,
            "prediction_hash_used_only_for_aggregate_identity_count": True,
            "mapping_answer_category_question_type_split_resource_opened": False,
            "task_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "per_task_metric_or_transition_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "runs": aggregates,
        "prediction_identity": {
            "all_three_identical": prediction_identity.get("1", 0),
            "exactly_two_unique_predictions": prediction_identity.get("2", 0),
            "all_three_different": prediction_identity.get("3", 0),
        },
        "whole_table": {
            "success_pattern_counts_order_v24800_v24807_v24810": dict(
                sorted(success_patterns.items())
            ),
            "successful_in_all_three": len(all_success),
            "successful_in_any_run": len(any_success),
            "success_set_intersection_over_union": len(all_success) / len(any_success),
        },
        "evaluator": {
            "invalid_counts": {v: len(invalid[v]) for v in VERSIONS},
            "invalid_in_all_three": len(all_invalid),
            "invalid_in_any_run": len(any_invalid),
            "error_taxonomy": {
                v: dict(
                    sorted(
                        Counter(metrics[v][item]["error_kind"] for item in invalid[v]).items()
                    )
                )
                for v in VERSIONS
            },
            "selective_retry_or_revaluation": False,
        },
        "uncertainty": {
            "whole_table_success_min_max": [
                min(aggregates[v]["whole_table_successes"] for v in VERSIONS),
                max(aggregates[v]["whole_table_successes"] for v in VERSIONS),
            ],
            "quality_composite_min_max": [
                min(aggregates[v]["metrics"]["quality_composite"] for v in VERSIONS),
                max(aggregates[v]["metrics"]["quality_composite"] for v in VERSIONS),
            ],
            "paired_bootstrap_run_mean_range": _bootstrap_range(metrics, ids),
        },
        "conclusions": {
            "same_algorithm_predictions_are_byte_stable": False,
            "whole_table_success_set_is_stable": False,
            "single_rollout_is_sufficient_for_candidate_ranking": False,
            "fixed_budget_or_entropy_causal_effect_established": False,
            "leaderboard_or_external_sota_established": False,
        },
        "next_work": {
            "do_not_launch_another_unchanged_public_exact220": True,
            "external_shared_prefix_three_arm_gate_first": True,
            "candidate_promotion_requires_disjoint_external_go_and_replicated_public_confirmatory": True,
            "future_public_report_requires_run_distribution_not_best_run": True,
            "evaluator_errors_remain_failure_as_zero_without_selective_revaluation": True,
        },
        "authorization": {
            "benchmark_external_shared_prefix_execution": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "three_exact220_denominators": all(
            aggregates[v]["n"] == SELECTED for v in VERSIONS
        ),
        "prediction_identity_partition": sum(value["prediction_identity"].values())
        == SELECTED,
        "success_patterns_cover_exact220": sum(success_patterns.values()) == SELECTED,
        "result_metrics_reconcile": all(
            aggregates[v]["metrics"]["quality_composite"]
            == runs[v]["result"]["metrics"]["all_220"]["quality_composite"]
            for v in VERSIONS
        ),
        "whole_table_range_is_six_to_eight": value["uncertainty"][
            "whole_table_success_min_max"
        ]
        == [6, 8],
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["diagnosis_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.48.11 emitted prohibited task content")
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_report(root, value, rebuild=False)


def validate_report(
    root: Path, value: Mapping[str, Any], *, rebuild: bool = True
) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24811_three_run_aggregate_only_repeatability_diagnosis"
        or copied.get("status")
        != "same_algorithm_three_run_variance_material_no_sota"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization")
        != {
            "benchmark_external_shared_prefix_execution": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "selective_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.11 diagnosis drifted")
    if rebuild:
        expected = build_report(root, now=int(copied.get("created_at_unix", -1)))
        if copied != expected:
            raise RuntimeError("V2.48.11 diagnosis is not reproducible")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    report = build_report()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "whole_table_range": report["uncertainty"][
                    "whole_table_success_min_max"
                ],
                "composite_range": report["uncertainty"][
                    "quality_composite_min_max"
                ],
                "all_three_identical_predictions": report["prediction_identity"][
                    "all_three_identical"
                ],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
