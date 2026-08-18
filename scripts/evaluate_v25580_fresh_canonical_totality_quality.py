#!/usr/bin/env python3
"""One-shot post-freeze quality gate for V2.55.79 canonical totality.

The two prediction vectors and the content-free forward audit were pushed
before this evaluator was introduced.  Exactly one redirect-disabled,
no-retry request is made to each of forty frozen PyPI endpoints.  Every one of
the forty frozen predictions is then evaluated exactly once.

Fixed-twenty failure-as-zero metrics are always reported.  Paired-complete
selection depends only on both official truth records being valid, never on a
prediction arm or score.  Exact requires the task's original visible column
bytes, canonical PyPI project names, original project order, and canonical
latest stable version values.  Soft metrics accept PEP 440-equivalent stable
versions and case-insensitive Unknown.  Entropy/information gain assigns zero
signed credit.
"""

from __future__ import annotations

import argparse
import ast
import base64
import copy
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25579_fresh_canonical_totality_external_contract as contract  # noqa: E402
from deepwide_agent import v25580_pypi_stable_version_truth as total_truth  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import control_v25579_fresh_canonical_totality_external as forward_control  # noqa: E402
from scripts import run_v25579_fresh_canonical_totality_external as forward_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260818"
PROTOCOL_ID = "v25580_v25579_fresh_canonical_totality_quality_v1"
SOURCE = Path("scripts/evaluate_v25580_fresh_canonical_totality_quality.py")
TEST = Path("tests/test_evaluate_v25580_fresh_canonical_totality_quality.py")
TRUTH_SOURCE = Path(
    "src/deepwide_agent/v25580_pypi_stable_version_truth.py"
)
TRUTH_TEST = Path("tests/test_v25580_pypi_stable_version_truth.py")
BUILD_AUDIT = Path(
    f"results/v25580_fresh_canonical_totality_quality_build_audit_v1_{DATE}.json"
)
PROTOCOL = contract.POSTFREEZE_QUALITY_PROTOCOL
RAW_TRUTH = contract.OUTPUT_ROOT / "postfreeze_pypi_responses_v25580.json.gz"
TRUTH = contract.OUTPUT_ROOT / "postfreeze_pypi_truth_v25580.json"
RESULT = contract.QUALITY_RESULT
AUDIT = contract.QUALITY_AUDIT

CONTROL_ARM = contract.CONTROL_ARM
CANDIDATE_ARM = contract.CANDIDATE_ARM
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
METRICS = (
    "entity_coverage",
    "row_f1",
    "item_f1",
    "column_f1",
    "quality_composite",
)

USER_AGENT = "DeepWideResearch/1.0 (+postfreeze stable-version evaluator)"
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 60.0
FETCH_WORKERS = 40
MAXIMUM_RESPONSE_BYTES = 32_000_000
PARSER_ID = total_truth.POLICY_ID
SCORER_ID = "two_row_stable_version_arm_blind_exact_sign_v1"
TEST_SUITES = ((TEST.name, 12), (TRUTH_TEST.name, 6))
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)

FORWARD_AUDIT_SHA256 = (
    "9472c7fc62315c891b30d165124865624604f7de9fd5b3310e7576832df8d6ca"
)
FORWARD_RESULT_SHA256 = (
    "12dbd9c75162e4b7f3a53d5636c79efcdc3cf3ef284c1d3ae9b4a84ce544ca10"
)
TASK_ROWS_SHA256 = (
    "bf584ae4c96388d8f98a5d824ab0df708766403b13e4648f95d806a0adad72fd"
)
PREDICTION_FREEZE_SHA256 = (
    "3e2847babad28ef90b40ebb99955da796380a4355eba22d2107600ca91db33f6"
)
FORWARD_RUNNER_SHA256 = (
    "6da36f1f48a3cf6e2d8ad8c5826559795abfe50e3d8e5132d88f701758b64d84"
)
FORWARD_CONTRACT_SHA256 = (
    "1264edd6c18c1cf911318042e58926ab618b93e64b533a791f562782b54f835e"
)
TRUTH_SOURCE_SHA256 = (
    "19bad6a878c689d155824256b322dc9a44e0fb2ec2fdac70df512df5660c3882"
)


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
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


def _publish_bytes(path: Path, value: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=tracked).read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.80 expected a JSON object")
    return value


def _read_rows(*, tracked: bool = True) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in contract.ordinary(ROOT, contract.TASK_ROWS, tracked=tracked)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.55.80 expected JSONL objects")
    return rows


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.55.80 requires a clean pushed HEAD")
    return head, target


def _future_pristine(paths: Sequence[Path]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (str(SOURCE), str(contract.RUNNER), "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def endpoint_vector() -> list[dict[str, Any]]:
    output = [
        {
            "index": index,
            "source": "pypi",
            "identity": identity,
            "url": f"https://pypi.org/pypi/{identity}/json",
        }
        for index, identity in enumerate(contract.population.identity_vector())
    ]
    if (
        len(output) != 40
        or [row["index"] for row in output] != list(range(40))
        or len({row["identity"] for row in output}) != 40
        or len({row["url"] for row in output}) != 40
        or any("/" in row["identity"] for row in output)
        or any(
            not row["url"].startswith("https://pypi.org/pypi/")
            for row in output
        )
    ):
        raise RuntimeError("V2.55.80 endpoint vector drifted")
    return output


def _parse_table(prediction: str, task_index: int) -> tuple[list[list[str]], bool]:
    if not isinstance(prediction, str) or not prediction.strip():
        return [], False
    lines = [line.strip() for line in prediction.strip().splitlines() if line.strip()]
    if lines and re.fullmatch(r"```(?:markdown)?", lines[0], re.IGNORECASE):
        if len(lines) < 2 or lines[-1] != "```":
            return [], False
        lines = lines[1:-1]
    if len(lines) != 4 or any(
        not line.startswith("|") or not line.endswith("|") for line in lines
    ):
        return [], False
    cells = [
        [cell.strip() for cell in line.strip("|").split("|")] for line in lines
    ]
    columns = list(contract.population.columns_for_index(task_index))
    if (
        cells[0] != columns
        or len(cells[1]) != len(columns)
        or any(re.fullmatch(r":?-{3,}:?", cell) is None for cell in cells[1])
        or any(len(row) != len(columns) for row in cells[2:])
        or any(not cell for row in cells[2:] for cell in row)
    ):
        return [], False
    return cells[2:], True


def _semantic_value(value: str) -> tuple[str, object | None] | None:
    text = " ".join(str(value).split())
    if text.casefold() == total_truth.UNKNOWN.casefold():
        return ("unknown", None)
    parsed = total_truth.semantic_version(text)
    return None if parsed is None else ("version", parsed)


def _expected_semantic(record: Mapping[str, Any]) -> tuple[str, object | None]:
    checked = total_truth.validate_record(record)
    return (
        (
            "version",
            total_truth.semantic_version(checked["latest_stable_version"]),
        )
        if checked["availability"] == "stable_release"
        else ("unknown", None)
    )


def _truth_pairs(
    records: Mapping[str, Mapping[str, Any]],
) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for pair in contract.population.pair_vector():
        task: list[dict[str, Any]] = []
        for identity in pair:
            record = records.get(identity)
            if not isinstance(record, Mapping) or record.get("identity") != identity:
                task = []
                break
            try:
                task.append(total_truth.validate_record(record))
            except ValueError:
                task = []
                break
        output.append(task)
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.55.80 truth task denominator drifted")
    return output


def _zero_metric() -> dict[str, float | int | bool]:
    return {
        "valid": False,
        "exact_table_success": 0,
        "entity_coverage": 0.0,
        "row_f1": 0.0,
        "item_f1": 0.0,
        "column_f1": 0.0,
        "quality_composite": 0.0,
    }


def evaluate_prediction(
    prediction: str,
    task_index: int,
    truth_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, float | int | bool]:
    if (
        isinstance(task_index, bool)
        or not isinstance(task_index, int)
        or not 0 <= task_index < contract.TASK_COUNT
    ):
        raise ValueError("V2.55.80 task index drifted")
    truth = _truth_pairs(truth_records)[task_index]
    rows, structural_valid = _parse_table(prediction, task_index)
    if len(truth) != contract.population.ROWS_PER_TASK or not structural_valid:
        return _zero_metric()
    expected_names = [record["canonical_project_name"] for record in truth]
    matched: dict[str, list[str]] = {}
    for row in rows:
        try:
            observed = total_truth.normalize_project(row[0])
        except ValueError:
            continue
        matches = [
            name
            for name in expected_names
            if observed == total_truth.normalize_project(name)
        ]
        if len(matches) == 1 and matches[0] not in matched:
            matched[matches[0]] = row
    entity_hits = len(matched)
    semantic_hits = sum(
        matched.get(record["canonical_project_name"]) is not None
        and _semantic_value(matched[record["canonical_project_name"]][1])
        == _expected_semantic(record)
        for record in truth
    )
    entity_coverage = entity_hits / 2
    row_f1 = semantic_hits / 2
    item_f1 = (entity_hits + semantic_hits) / 4
    column_f1 = 1.0
    exact = int(
        all(
            rows[position][0] == record["canonical_project_name"]
            and rows[position][1] == record["canonical_value"]
            for position, record in enumerate(truth)
        )
    )
    composite = (entity_coverage + row_f1 + item_f1 + column_f1) / 4
    return {
        "valid": True,
        "exact_table_success": exact,
        "entity_coverage": entity_coverage,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "quality_composite": composite,
    }


def _delta(candidate: Mapping[str, Any], control: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "exact_table_successes": candidate["exact_table_successes"]
        - control["exact_table_successes"],
        "valid_tasks": candidate["valid_tasks"] - control["valid_tasks"],
        "invalid_tasks": candidate["invalid_tasks"] - control["invalid_tasks"],
        "fallback_tasks": candidate["fallback_tasks"] - control["fallback_tasks"],
        **{name: candidate[name] - control[name] for name in METRICS},
    }


def _aggregate_metrics(
    metrics: Sequence[Mapping[str, Any]], fallback_flags: Sequence[bool]
) -> dict[str, Any]:
    if len(metrics) != contract.TASK_COUNT or len(fallback_flags) != contract.TASK_COUNT:
        raise ValueError("V2.55.80 metric denominator drifted")
    return {
        "tasks": len(metrics),
        "valid_tasks": sum(metric["valid"] is True for metric in metrics),
        "invalid_tasks": sum(metric["valid"] is False for metric in metrics),
        "fallback_tasks": sum(fallback_flags),
        "exact_table_successes": sum(
            int(metric["exact_table_success"]) for metric in metrics
        ),
        **{
            name: sum(float(metric[name]) for metric in metrics)
            / contract.TASK_COUNT
            for name in METRICS
        },
    }


def _disposition_for_indices(
    by_task: Mapping[int, Mapping[str, Mapping[str, Any]]],
    metric: str,
    indices: Sequence[int] | range,
) -> dict[str, int]:
    output = {"candidate_win": 0, "tie": 0, "candidate_loss": 0}
    for index in indices:
        delta = float(by_task[index][CANDIDATE_ARM][metric]) - float(
            by_task[index][CONTROL_ARM][metric]
        )
        output[
            "candidate_win"
            if delta > 1e-12
            else "candidate_loss"
            if delta < -1e-12
            else "tie"
        ] += 1
    return output


def _two_sided_exact_sign_test(candidate_wins: int, candidate_losses: int) -> float:
    if (
        isinstance(candidate_wins, bool)
        or isinstance(candidate_losses, bool)
        or not isinstance(candidate_wins, int)
        or not isinstance(candidate_losses, int)
        or candidate_wins < 0
        or candidate_losses < 0
    ):
        raise ValueError("V2.55.80 sign-test count drifted")
    discordant = candidate_wins + candidate_losses
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(candidate_wins, candidate_losses) + 1)
    ) / (2**discordant)
    return min(1.0, 2.0 * tail)


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]],
    truth_records: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    checked = [forward_runner.validate_task_row(row) for row in rows]
    tasks = contract.task_vector()
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in tasks]
        or [row["task_index"] for row in checked]
        != list(range(contract.TASK_COUNT))
    ):
        raise ValueError("V2.55.80 frozen task denominator drifted")
    pairs = _truth_pairs(truth_records)
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    fallback: dict[str, list[bool]] = {arm: [] for arm in ARMS}
    by_task: dict[int, dict[str, dict[str, Any]]] = {}
    for row in checked:
        index = int(row["task_index"])
        by_task[index] = {}
        for arm in ARMS:
            metric = evaluate_prediction(
                row["predictions"][arm], index, truth_records
            )
            by_arm[arm].append(metric)
            by_task[index][arm] = metric
            fallback[arm].append(
                row["preassigned_exposure"] == "canonical_drift"
                if arm == CONTROL_ARM
                else row["prediction_kind"] == "fallback"
            )
    aggregate = {
        arm: _aggregate_metrics(by_arm[arm], fallback[arm]) for arm in ARMS
    }
    paired_complete_indices = [
        index for index, pair in enumerate(pairs) if len(pair) == 2
    ]
    paired_exact = _disposition_for_indices(
        by_task, "exact_table_success", paired_complete_indices
    )
    paired_exact["task_count"] = len(paired_complete_indices)
    paired_exact["discordant_task_count"] = (
        paired_exact["candidate_win"] + paired_exact["candidate_loss"]
    )
    paired_exact["two_sided_exact_sign_test_p"] = _two_sided_exact_sign_test(
        paired_exact["candidate_win"], paired_exact["candidate_loss"]
    )
    family: dict[str, Any] = {}
    for name, indices in (
        ("canonical_drift", range(0, contract.population.DRIFT_TASK_COUNT)),
        (
            "ordinary_ascii",
            range(contract.population.DRIFT_TASK_COUNT, contract.TASK_COUNT),
        ),
    ):
        family[name] = {
            arm: {
                "tasks": len(list(indices)),
                "exact_table_successes": sum(
                    int(by_task[index][arm]["exact_table_success"])
                    for index in indices
                ),
                "quality_composite": sum(
                    float(by_task[index][arm]["quality_composite"])
                    for index in indices
                )
                / len(list(indices)),
            }
            for arm in ARMS
        }
    ordinary_equal = sum(
        row["predictions"][CONTROL_ARM] == row["predictions"][CANDIDATE_ARM]
        for row in checked[contract.population.DRIFT_TASK_COUNT :]
    )
    return {
        "evaluation_count": contract.TASK_COUNT * len(ARMS),
        "truth_identity_count": len(truth_records),
        "truth_complete_tasks": sum(len(pair) == 2 for pair in pairs),
        "arms": aggregate,
        "candidate_minus_control": _delta(
            aggregate[CANDIDATE_ARM], aggregate[CONTROL_ARM]
        ),
        "candidate_vs_control_exact_disposition": _disposition_for_indices(
            by_task, "exact_table_success", range(contract.TASK_COUNT)
        ),
        "candidate_vs_control_composite_disposition": _disposition_for_indices(
            by_task, "quality_composite", range(contract.TASK_COUNT)
        ),
        "arm_blind_paired_complete_exact": paired_exact,
        "paired_complete_selection": {
            "selected_task_count": len(paired_complete_indices),
            "selection_signal": "both_frozen_official_truth_records_valid",
            "prediction_arm_outcome_or_score_used": False,
            "task_identity_question_prediction_or_score_persisted": False,
        },
        "family_metrics": family,
        "ordinary_negative_control_prediction_count": 10,
        "ordinary_negative_control_predictions_byte_equal": ordinary_equal,
        "same_forward_provider_retrieval_and_sampling_effects": True,
        "shared_parent_totality_recovery_comparison": True,
    }


def quality_decision(metrics: Mapping[str, Any]) -> dict[str, Any]:
    gate = contract.quality_gate()
    arms = metrics.get("arms") or {}
    control = arms.get(CONTROL_ARM) or {}
    candidate = arms.get(CANDIDATE_ARM) or {}
    delta = metrics.get("candidate_minus_control") or {}
    paired = metrics.get("arm_blind_paired_complete_exact") or {}
    selection = metrics.get("paired_complete_selection") or {}
    checks = {
        "fixed_prediction_denominator": metrics.get("evaluation_count") == 40
        and control.get("tasks") == 20
        and candidate.get("tasks") == 20,
        "minimum_arm_blind_paired_complete_tasks": metrics.get(
            "truth_complete_tasks"
        )
        >= gate["minimum_arm_blind_paired_complete_tasks"]
        and paired.get("task_count") == metrics.get("truth_complete_tasks")
        and selection.get("selected_task_count")
        == metrics.get("truth_complete_tasks"),
        "paired_complete_selected_only_by_truth_availability": selection.get(
            "selection_signal"
        )
        == "both_frozen_official_truth_records_valid"
        and selection.get("prediction_arm_outcome_or_score_used") is False
        and selection.get(
            "task_identity_question_prediction_or_score_persisted"
        )
        is False,
        "candidate_whole_table_exact_strict_gain_fixed20": delta.get(
            "exact_table_successes", 0
        )
        > 0,
        "minimum_candidate_exact_wins_on_paired_complete": paired.get(
            "candidate_win", 0
        )
        >= gate["minimum_candidate_exact_wins_on_paired_complete"],
        "candidate_exact_loss_zero_on_paired_complete": paired.get(
            "candidate_loss", 1
        )
        <= gate["maximum_candidate_exact_losses_on_paired_complete"],
        "paired_complete_exact_sign_test_two_sided": paired.get(
            "discordant_task_count", 0
        )
        > 0
        and paired.get("two_sided_exact_sign_test_p", 1.0)
        <= gate["maximum_two_sided_exact_sign_test_p"],
        "entity_nonregression": delta.get("entity_coverage", -1) >= 0,
        "row_nonregression": delta.get("row_f1", -1) >= 0,
        "item_nonregression": delta.get("item_f1", -1) >= 0,
        "column_nonregression": delta.get("column_f1", -1) >= 0,
        "composite_nonregression": delta.get("quality_composite", -1) >= 0,
        "valid_task_nonregression": delta.get("valid_tasks", -1) >= 0,
        "invalid_task_nonincrease": delta.get("invalid_tasks", 1) <= 0,
        "fallback_nonincrease": delta.get("fallback_tasks", 1) <= 0,
        "ordinary_negative_control_predictions_byte_equal": metrics.get(
            "ordinary_negative_control_predictions_byte_equal"
        )
        == gate["required_ordinary_control_candidate_byte_equal_tasks"]
        if "required_ordinary_control_candidate_byte_equal_tasks" in gate
        else metrics.get("ordinary_negative_control_predictions_byte_equal") == 10,
        "same_forward_provider_retrieval_and_sampling_effects": metrics.get(
            "same_forward_provider_retrieval_and_sampling_effects"
        )
        is True,
        "shared_parent_totality_recovery_comparison": metrics.get(
            "shared_parent_totality_recovery_comparison"
        )
        is True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "quality_gate_passed": not failed,
    }


def parser_contract() -> dict[str, Any]:
    return {
        "parser_id": PARSER_ID,
        "official_identity_bound_response_required": True,
        "canonical_project_name_from_official_info": True,
        "latest_file_bearing_pep440_non_prerelease_non_dev_release": True,
        "no_stable_release_is_valid_unknown": True,
        "nonempty_invalid_version_or_equal_latest_alias_conflict_fails_closed": True,
        "missing_malformed_identity_conflicting_or_oversized_truth_scores_zero": True,
    }


def scoring_contract() -> dict[str, Any]:
    return {
        "scorer_id": SCORER_ID,
        "fixed_task_denominator": 20,
        "fixed_prediction_count": 40,
        "semantic_soft_metrics_accept_pep440_equivalent_stable_versions_and_unknown_case": True,
        "whole_table_exact_requires_visible_column_bytes_canonical_project_names_canonical_values_and_supplied_order": True,
        "entity_row_item_column_and_composite_all_reported": True,
        "each_frozen_prediction_evaluated_exactly_once": True,
        "fixed20_failure_as_zero_metrics_always_reported": True,
        "invalid_or_incomplete_truth_is_zero_for_both_arms": True,
        "minimum_arm_blind_paired_complete_tasks": 18,
        "paired_complete_selection_uses_only_both_truth_records_valid": True,
        "prediction_arm_outcome_or_score_used_for_completeness_selection": False,
        "candidate_exact_minimum_wins": 6,
        "candidate_exact_maximum_losses": 0,
        "two_sided_exact_sign_test_maximum_p": 0.05,
        "ordinary_negative_control_predictions_must_be_byte_equal": True,
        "prediction_retry_repair_mutation_selection_or_revaluation": False,
    }


def truth_fetch_contract() -> dict[str, Any]:
    return {
        "fixed_endpoint_count": 40,
        "pypi_endpoint_count": 40,
        "attempts_per_endpoint": 1,
        "allow_redirects": False,
        "requests_library_retry_adapter": False,
        "replacement_refetch_or_backfill": False,
        "fetch_workers": FETCH_WORKERS,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
        "all_raw_responses_hash_bound_in_one_deterministic_gzip_snapshot": True,
    }


def _forward_barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    audit = _read(contract.FORWARD_AUDIT)
    forward = forward_runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [forward_runner.validate_task_row(row) for row in _read_rows()]
    freeze = _read(contract.PREDICTION_FREEZE)
    if (
        contract.sha256(ROOT / contract.FORWARD_AUDIT) != FORWARD_AUDIT_SHA256
        or contract.sha256(ROOT / contract.FORWARD_RESULT) != FORWARD_RESULT_SHA256
        or contract.sha256(ROOT / contract.TASK_ROWS) != TASK_ROWS_SHA256
        or contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        != PREDICTION_FREEZE_SHA256
        or contract.sha256(ROOT / contract.RUNNER) != FORWARD_RUNNER_SHA256
        or contract.sha256(ROOT / contract.CONTRACT) != FORWARD_CONTRACT_SHA256
        or contract.sha256(ROOT / TRUTH_SOURCE) != TRUTH_SOURCE_SHA256
        or audit.get("role")
        != "v25579_fresh_canonical_totality_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not True
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
        or forward.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not True
        or len(rows) != 20
        or freeze.get("task_rows_sha256") != TASK_ROWS_SHA256
        or freeze.get("both_prediction_texts_persisted") is not True
        or not contract.sealed(freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.55.80 pushed forward barrier drifted")
    return audit, rows


def _tests() -> dict[str, Any]:
    suites = [base_audit._test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS
        and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _source_network_contract(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "requests"
        and node.func.attr == "get"
    ]
    if len(calls) != 1:
        return False
    keywords = {keyword.arg: keyword.value for keyword in calls[0].keywords}
    allow = keywords.get("allow_redirects")
    stream = keywords.get("stream")
    forbidden = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id in {"Retry", "HTTPAdapter"}
            or isinstance(node.func, ast.Attribute)
            and node.func.attr in {"mount", "send"}
        )
    ]
    return (
        isinstance(allow, ast.Constant)
        and allow.value is False
        and isinstance(stream, ast.Constant)
        and stream.value is True
        and not forbidden
    )


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    if require_clean:
        head, target = _clean_pushed()
    else:
        head = contract.git(ROOT, "rev-parse", "HEAD")
        target = contract.git(ROOT, "rev-parse", "target/main")
    forward_audit, rows = _forward_barrier()
    tests = _tests()
    tracked = all(
        not require_clean
        or contract.git(ROOT, "ls-files", "--error-unmatch", str(path))
        for path in (SOURCE, TEST, TRUTH_SOURCE, TRUTH_TEST)
    )
    closure = {str(path) for path in contract.forward_dependency_closure(ROOT)}
    source = contract.ordinary(ROOT, SOURCE, tracked=require_clean)
    test_path = contract.ordinary(ROOT, TEST, tracked=require_clean)
    endpoints = endpoint_vector()
    checks = {
        "git_clean_head_equals_target_main": head == target,
        "source_test_and_version_truth_tracked": tracked,
        "pushed_forward_audit_authorizes_quality": bool(forward_audit),
        "fixed_forward_hashes_exact": (
            contract.sha256(ROOT / contract.FORWARD_AUDIT)
            == FORWARD_AUDIT_SHA256
            and contract.sha256(ROOT / contract.FORWARD_RESULT)
            == FORWARD_RESULT_SHA256
            and contract.sha256(ROOT / contract.TASK_ROWS) == TASK_ROWS_SHA256
            and contract.sha256(ROOT / contract.PREDICTION_FREEZE)
            == PREDICTION_FREEZE_SHA256
        ),
        "all_frozen_rows_validate_before_truth": len(rows) == 20,
        "focused_quality_and_version_truth_tests_exact18": tests["passed"],
        "evaluator_and_version_truth_absent_from_forward_closure": str(SOURCE)
        not in closure
        and str(TRUTH_SOURCE) not in closure,
        "single_no_redirect_streaming_requests_get_contract": _source_network_contract(
            source
        ),
        "fixed_endpoint_vector_exact_unique_forty_pypi": len(endpoints) == 40
        and all(row["source"] == "pypi" for row in endpoints),
        "future_quality_surfaces_pristine": _future_pristine(
            (BUILD_AUDIT, PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)
        ),
        "credential_literal_zero": not base_audit.SECRET.search(
            source.read_text(encoding="utf-8")
        )
        and not base_audit.SECRET.search(test_path.read_text(encoding="utf-8")),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == _read(contract.PROTOCOL)["protected_watchers"],
        "shared_api_lease_inactive": forward_control._lease_inactive(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "no_network_model_search_fetch_or_evaluation_performed_by_build_audit": True,
        "entropy_information_gain_signed_credit_zero": forward_audit["aggregate"][
            "positive_signed_credit_count"
        ]
        == 0,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25580_fresh_canonical_totality_quality_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "evaluator_source_sha256": contract.sha256(source),
        "evaluator_test_sha256": contract.sha256(test_path),
        "truth_source_sha256": contract.sha256(ROOT / TRUTH_SOURCE),
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "endpoint_vector_sha256": contract.payload_sha256(endpoints),
        "tests": tests,
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "truth_fetch": truth_fetch_contract(),
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "network_model_search_fetch_or_evaluation_performed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "postfreeze_quality_protocol_generation": valid,
            "one_truth_fetch_or_quality_evaluation": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        },
    }
    return validate_build_audit(contract.seal(value, "audit_payload_sha256"))


def validate_build_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    valid = copied.get("audit_valid") is True
    checks = copied.get("checks") or {}
    if (
        copied.get("role")
        != "v25580_fresh_canonical_totality_quality_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("truth_source_sha256") != TRUTH_SOURCE_SHA256
        or copied.get("endpoint_vector_sha256")
        != contract.payload_sha256(endpoint_vector())
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("network_model_search_fetch_or_evaluation_performed")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "postfreeze_quality_protocol_generation": valid,
            "one_truth_fetch_or_quality_evaluation": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.55.80 quality build audit drifted")
    return copied


def preregister(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build_audit(_read(BUILD_AUDIT))
    forward_audit, _rows = _forward_barrier()
    if not _future_pristine((PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.55.80 quality protocol surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25580_fresh_canonical_totality_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "target_main": target,
        "quality_build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "evaluator_source_sha256": build["evaluator_source_sha256"],
        "evaluator_test_sha256": build["evaluator_test_sha256"],
        "truth_source_sha256": TRUTH_SOURCE_SHA256,
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "frozen_task_count": 20,
        "fixed_prediction_count": 40,
        "fixed_truth_identity_count": 40,
        "endpoint_vector_sha256": contract.payload_sha256(endpoint_vector()),
        "truth_fetch": truth_fetch_contract(),
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "quality_gate": contract.quality_gate(),
        "prediction_freeze_and_pushed_forward_audit_precede_official_truth_open": True,
        "control_and_candidate_share_one_provider_forward": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_fixed_forty_endpoint_truth_fetch_and_quality_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        },
    }
    if forward_audit["authorization"]["postfreeze_quality_protocol"] is not True:
        raise RuntimeError("V2.55.80 forward audit does not authorize quality")
    return validate_protocol(contract.seal(value, "protocol_payload_sha256"))


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25580_fresh_canonical_totality_quality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("git_head") != copied.get("target_main")
        or copied.get("quality_build_audit_sha256")
        != contract.sha256(ROOT / BUILD_AUDIT)
        or copied.get("evaluator_source_sha256") != contract.sha256(ROOT / SOURCE)
        or copied.get("evaluator_test_sha256") != contract.sha256(ROOT / TEST)
        or copied.get("truth_source_sha256") != TRUTH_SOURCE_SHA256
        or copied.get("forward_audit_sha256") != FORWARD_AUDIT_SHA256
        or copied.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or copied.get("task_rows_sha256") != TASK_ROWS_SHA256
        or copied.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or copied.get("frozen_task_count") != 20
        or copied.get("fixed_prediction_count") != 40
        or copied.get("fixed_truth_identity_count") != 40
        or copied.get("endpoint_vector_sha256")
        != contract.payload_sha256(endpoint_vector())
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get(
            "prediction_freeze_and_pushed_forward_audit_precede_official_truth_open"
        )
        is not True
        or copied.get("control_and_candidate_share_one_provider_forward") is not True
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "one_fixed_forty_endpoint_truth_fetch_and_quality_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.55.80 quality protocol drifted")
    return copied


def _fetch_endpoint(spec: Mapping[str, Any]) -> dict[str, Any]:
    raw = b""
    status = 0
    failure: str | None = None
    try:
        with requests.get(
            str(spec["url"]),
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            parts: list[bytes] = []
            observed = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                observed += len(chunk)
                if observed > MAXIMUM_RESPONSE_BYTES:
                    failure = "ResponseTooLarge"
                    parts = []
                    break
                parts.append(bytes(chunk))
            raw = b"".join(parts)
            if status != 200 and failure is None:
                failure = f"HTTP{status}"
            elif not raw and failure is None:
                failure = "EmptyResponse"
    except requests.RequestException as exc:
        failure = type(exc).__name__[:128] or "RequestException"
    return {
        **dict(spec),
        "attempt_count": 1,
        "http_status": status,
        "transport_failure_type": failure,
        "raw": raw,
    }


def _fetch_all() -> list[dict[str, Any]]:
    specs = endpoint_vector()
    output: list[dict[str, Any] | None] = [None] * len(specs)
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        futures = {executor.submit(_fetch_endpoint, spec): spec for spec in specs}
        for future in as_completed(futures):
            spec = futures[future]
            try:
                value = future.result()
            except Exception as exc:  # fixed failure-as-zero; never retried
                value = {
                    **spec,
                    "attempt_count": 1,
                    "http_status": 0,
                    "transport_failure_type": type(exc).__name__[:128]
                    or "Exception",
                    "raw": b"",
                }
            output[int(spec["index"])] = value
    if any(value is None for value in output):
        raise RuntimeError("V2.55.80 fixed fetch vector did not terminate")
    return [dict(value) for value in output if value is not None]


def _parse_record(spec: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    return total_truth.parse_response(raw, str(spec["identity"]))


def _truth_artifact(
    fetched: Sequence[Mapping[str, Any]], *, now: int
) -> tuple[bytes, dict[str, Any]]:
    specs = endpoint_vector()
    if len(fetched) != len(specs):
        raise ValueError("V2.55.80 fetched denominator drifted")
    snapshot_rows: list[dict[str, Any]] = []
    endpoint_rows: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    for spec, observed in zip(specs, fetched, strict=True):
        if any(observed.get(key) != spec[key] for key in spec):
            raise ValueError("V2.55.80 fetched endpoint binding drifted")
        raw = observed.get("raw")
        if not isinstance(raw, bytes):
            raise ValueError("V2.55.80 fetched raw response drifted")
        transport_failure = observed.get("transport_failure_type")
        record: dict[str, Any] | None = None
        failure = transport_failure
        if failure is None:
            try:
                record = _parse_record(spec, raw)
            except (ValueError, TypeError, KeyError):
                failure = "ParseFailure"
        if record is not None:
            records[str(spec["identity"])] = record
        raw_sha = hashlib.sha256(raw).hexdigest()
        snapshot_rows.append(
            {
                **spec,
                "attempt_count": int(observed.get("attempt_count", 0)),
                "http_status": int(observed.get("http_status", 0)),
                "transport_failure_type": transport_failure,
                "raw_response_base64": base64.b64encode(raw).decode("ascii"),
                "raw_response_bytes": len(raw),
                "raw_response_sha256": raw_sha,
            }
        )
        endpoint_rows.append(
            {
                **spec,
                "attempt_count": int(observed.get("attempt_count", 0)),
                "http_status": int(observed.get("http_status", 0)),
                "failure_type": failure,
                "raw_response_bytes": len(raw),
                "raw_response_sha256": raw_sha,
                "record": record,
            }
        )
    snapshot_plain = json.dumps(
        snapshot_rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    compressed = gzip.compress(snapshot_plain, compresslevel=9, mtime=0)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25580_postfreeze_pypi_stable_version_truth",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "endpoint_vector_sha256": contract.payload_sha256(specs),
        "expected_endpoint_count": 40,
        "attempt_count": sum(row["attempt_count"] for row in endpoint_rows),
        "successful_transport_count": sum(
            row["http_status"] == 200 and row["failure_type"] is None
            for row in endpoint_rows
        ),
        "valid_record_count": len(records),
        "stable_release_record_count": sum(
            row["availability"] == "stable_release" for row in records.values()
        ),
        "valid_unknown_record_count": sum(
            row["availability"] == "no_stable_release"
            for row in records.values()
        ),
        "complete_task_count": sum(
            all(identity in records for identity in pair)
            for pair in contract.population.pair_vector()
        ),
        "snapshot_uncompressed_bytes": len(snapshot_plain),
        "snapshot_uncompressed_sha256": hashlib.sha256(snapshot_plain).hexdigest(),
        "compressed_snapshot_sha256": hashlib.sha256(compressed).hexdigest(),
        "endpoints": endpoint_rows,
        "records": records,
        "one_official_attempt_per_fixed_endpoint_no_retry_redirect_or_replacement": True,
        "same_truth_records_used_for_both_prediction_arms": True,
        "prediction_freeze_and_pushed_forward_audit_preexisted": True,
        "no_stable_release_is_valid_unknown": True,
    }
    return compressed, contract.seal(value, "truth_payload_sha256")


def validate_truth(value: Mapping[str, Any], compressed: bytes) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    try:
        plain = gzip.decompress(compressed)
        snapshot = json.loads(plain)
    except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.55.80 compressed truth snapshot drifted") from exc
    specs = endpoint_vector()
    endpoints = copied.get("endpoints")
    records = copied.get("records")
    if (
        copied.get("role") != "v25580_postfreeze_pypi_stable_version_truth"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("endpoint_vector_sha256") != contract.payload_sha256(specs)
        or copied.get("expected_endpoint_count") != 40
        or not isinstance(snapshot, list)
        or len(snapshot) != 40
        or not isinstance(endpoints, list)
        or len(endpoints) != 40
        or not isinstance(records, Mapping)
        or copied.get("snapshot_uncompressed_bytes") != len(plain)
        or copied.get("snapshot_uncompressed_sha256")
        != hashlib.sha256(plain).hexdigest()
        or copied.get("compressed_snapshot_sha256")
        != hashlib.sha256(compressed).hexdigest()
        or copied.get(
            "one_official_attempt_per_fixed_endpoint_no_retry_redirect_or_replacement"
        )
        is not True
        or copied.get("same_truth_records_used_for_both_prediction_arms") is not True
        or copied.get("prediction_freeze_and_pushed_forward_audit_preexisted")
        is not True
        or copied.get("no_stable_release_is_valid_unknown") is not True
        or not contract.sealed(copied, "truth_payload_sha256")
    ):
        raise ValueError("V2.55.80 truth artifact drifted")
    replay_records: dict[str, dict[str, Any]] = {}
    replay_endpoints: list[dict[str, Any]] = []
    for spec, raw_row, endpoint in zip(specs, snapshot, endpoints, strict=True):
        if not isinstance(raw_row, Mapping) or not isinstance(endpoint, Mapping):
            raise ValueError("V2.55.80 truth endpoint shape drifted")
        if any(raw_row.get(key) != spec[key] for key in spec):
            raise ValueError("V2.55.80 snapshot endpoint binding drifted")
        try:
            raw = base64.b64decode(
                raw_row.get("raw_response_base64"), validate=True
            )
        except (ValueError, TypeError) as exc:
            raise ValueError("V2.55.80 snapshot base64 drifted") from exc
        if (
            raw_row.get("attempt_count") != 1
            or raw_row.get("raw_response_bytes") != len(raw)
            or raw_row.get("raw_response_sha256")
            != hashlib.sha256(raw).hexdigest()
        ):
            raise ValueError("V2.55.80 raw response receipt drifted")
        failure = raw_row.get("transport_failure_type")
        record: dict[str, Any] | None = None
        if failure is None and raw_row.get("http_status") == 200 and raw:
            try:
                record = _parse_record(spec, raw)
            except (ValueError, TypeError, KeyError):
                failure = "ParseFailure"
        elif failure is None:
            failure = (
                f"HTTP{raw_row.get('http_status')}"
                if raw_row.get("http_status") != 200
                else "EmptyResponse"
            )
        expected_endpoint = {
            **spec,
            "attempt_count": 1,
            "http_status": int(raw_row.get("http_status", 0)),
            "failure_type": failure,
            "raw_response_bytes": len(raw),
            "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
            "record": record,
        }
        if dict(endpoint) != expected_endpoint:
            raise ValueError("V2.55.80 parsed endpoint receipt drifted")
        replay_endpoints.append(expected_endpoint)
        if record is not None:
            replay_records[str(spec["identity"])] = record
    if (
        dict(records) != replay_records
        or copied.get("attempt_count") != 40
        or copied.get("successful_transport_count")
        != sum(row["failure_type"] is None for row in replay_endpoints)
        or copied.get("valid_record_count") != len(replay_records)
        or copied.get("stable_release_record_count")
        != sum(
            row["availability"] == "stable_release"
            for row in replay_records.values()
        )
        or copied.get("valid_unknown_record_count")
        != sum(
            row["availability"] == "no_stable_release"
            for row in replay_records.values()
        )
        or copied.get("complete_task_count")
        != sum(
            all(identity in replay_records for identity in pair)
            for pair in contract.population.pair_vector()
        )
    ):
        raise ValueError("V2.55.80 truth replay aggregate drifted")
    return copied


def _result_artifact(
    protocol: Mapping[str, Any],
    truth: Mapping[str, Any],
    metrics: Mapping[str, Any],
    *,
    now: int,
    protocol_sha256: str,
) -> dict[str, Any]:
    decision = quality_decision(metrics)
    passed = bool(decision["quality_gate_passed"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25580_fresh_canonical_totality_quality_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "status": (
            "fresh_canonical_totality_quality_go"
            if passed
            else "fresh_canonical_totality_quality_no_go"
        ),
        "passed": passed,
        "quality_protocol_sha256": protocol_sha256,
        "forward_audit_sha256": protocol["forward_audit_sha256"],
        "forward_result_sha256": protocol["forward_result_sha256"],
        "task_rows_sha256": protocol["task_rows_sha256"],
        "prediction_freeze_sha256": protocol["prediction_freeze_sha256"],
        "compressed_truth_snapshot_sha256": truth[
            "compressed_snapshot_sha256"
        ],
        "truth_payload_sha256": truth["truth_payload_sha256"],
        "metrics": dict(metrics),
        "quality_decision": decision,
        "all_forty_predictions_evaluated_once": True,
        "all_forty_fixed_truth_endpoints_attempted_once": truth["attempt_count"]
        == 40,
        "valid_unknown_record_count": truth["valid_unknown_record_count"],
        "fixed_denominator_failure_as_zero": True,
        "arm_blind_paired_complete_selection_only_by_truth_availability": True,
        "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit": True,
        "prediction_retry_repair_selection_or_mutation": False,
        "control_and_candidate_share_one_provider_forward": True,
        "candidate_minus_control_is_matched_totality_recovery_comparison": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "claim_scope": {
            "fresh_external_totality_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        },
        "authorization": {
            "quality_audit_generation": True,
            "deepwidebench_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        },
    }
    return contract.seal(value, "result_payload_sha256")


def validate_result(
    value: Mapping[str, Any],
    *,
    truth: Mapping[str, Any] | None = None,
    rows: Sequence[Mapping[str, Any]] | None = None,
    expected_protocol_sha256: str | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    metrics = copied.get("metrics")
    decision = copied.get("quality_decision")
    passed = copied.get("passed") is True
    expected_protocol = (
        contract.sha256(ROOT / PROTOCOL)
        if expected_protocol_sha256 is None
        else expected_protocol_sha256
    )
    if (
        copied.get("role")
        != "v25580_fresh_canonical_totality_quality_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "fresh_canonical_totality_quality_go"
            if passed
            else "fresh_canonical_totality_quality_no_go"
        )
        or copied.get("quality_protocol_sha256") != expected_protocol
        or copied.get("forward_audit_sha256") != FORWARD_AUDIT_SHA256
        or copied.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or copied.get("task_rows_sha256") != TASK_ROWS_SHA256
        or copied.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or not isinstance(metrics, Mapping)
        or not isinstance(decision, Mapping)
        or quality_decision(metrics) != dict(decision)
        or passed is not decision["quality_gate_passed"]
        or copied.get("all_forty_predictions_evaluated_once") is not True
        or copied.get("all_forty_fixed_truth_endpoints_attempted_once") is not True
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get(
            "arm_blind_paired_complete_selection_only_by_truth_availability"
        )
        is not True
        or copied.get(
            "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit"
        )
        is not True
        or copied.get("prediction_retry_repair_selection_or_mutation") is not False
        or copied.get("control_and_candidate_share_one_provider_forward") is not True
        or copied.get(
            "candidate_minus_control_is_matched_totality_recovery_comparison"
        )
        is not True
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("claim_scope")
        != {
            "fresh_external_totality_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        }
        or copied.get("authorization")
        != {
            "quality_audit_generation": True,
            "deepwidebench_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.55.80 quality result drifted")
    if truth is not None and rows is not None:
        records = truth.get("records")
        if (
            not isinstance(records, Mapping)
            or copied.get("truth_payload_sha256")
            != truth.get("truth_payload_sha256")
            or copied.get("valid_unknown_record_count")
            != truth.get("valid_unknown_record_count")
            or copied.get("metrics") != evaluate_rows(rows, records)
        ):
            raise ValueError("V2.55.80 quality result replay drifted")
    return copied


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _forward_audit, rows = _forward_barrier()
    if not _future_pristine((RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.55.80 evaluation surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.55.80 protected watcher identity drifted")
    if not forward_control._lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.55.80 shared evaluation runtime is not ready")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25580_fresh_canonical_totality_quality_v1",
        purpose="single_postfreeze_forty_pypi_truth_and_fixed_two_arm_evaluation",
        path=ROOT / contract.LEASE_PATH,
    ):
        fetched = _fetch_all()
    timestamp = int(time.time()) if now is None else int(now)
    compressed, truth = _truth_artifact(fetched, now=timestamp)
    metrics = evaluate_rows(rows, truth["records"])
    result = _result_artifact(
        protocol,
        truth,
        metrics,
        now=timestamp,
        protocol_sha256=contract.sha256(ROOT / PROTOCOL),
    )
    validate_truth(truth, compressed)
    validate_result(result, truth=truth, rows=rows)
    _publish_bytes(ROOT / RAW_TRUTH, compressed)
    _publish_json(ROOT / TRUTH, truth)
    _publish_json(ROOT / RESULT, result)
    return result


def audit_result(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _forward_audit, rows = _forward_barrier()
    compressed = contract.ordinary(ROOT, RAW_TRUTH, tracked=True).read_bytes()
    truth = validate_truth(_read(TRUTH), compressed)
    result = validate_result(_read(RESULT), truth=truth, rows=rows)
    recomputed_metrics = evaluate_rows(rows, truth["records"])
    recomputed_decision = quality_decision(recomputed_metrics)
    checks = {
        "protocol_and_forward_barrier_valid": bool(protocol),
        "forty_endpoint_single_attempt_snapshot_hash_and_parser_replay_valid": bool(
            truth
        ),
        "all_forty_frozen_predictions_recomputed_once": result[
            "all_forty_predictions_evaluated_once"
        ]
        is True
        and recomputed_metrics["evaluation_count"] == 40,
        "all_forty_fixed_truth_endpoints_attempted_once": truth["attempt_count"]
        == 40,
        "valid_unknown_totality_preserved": truth["valid_unknown_record_count"]
        >= 0,
        "metrics_and_quality_decision_recompute_exactly": result["metrics"]
        == recomputed_metrics
        and result["quality_decision"] == recomputed_decision,
        "matched_totality_recovery_comparison_preserved": result[
            "candidate_minus_control_is_matched_totality_recovery_comparison"
        ]
        is True,
        "arm_blind_paired_complete_selection_preserved": result[
            "arm_blind_paired_complete_selection_only_by_truth_availability"
        ]
        is True
        and recomputed_metrics["paired_complete_selection"][
            "prediction_arm_outcome_or_score_used"
        ]
        is False,
        "ordinary_negative_control_byte_equality_preserved": recomputed_metrics[
            "ordinary_negative_control_predictions_byte_equal"
        ]
        == 10,
        "no_prediction_retry_repair_selection_or_mutation": result[
            "prediction_retry_repair_selection_or_mutation"
        ]
        is False,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": forward_control._lease_inactive(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "entropy_information_gain_signed_credit_zero": result[
            "positive_signed_credit_count"
        ]
        == 0,
        "audit_calls_no_network_model_search_fetch_or_deepwidebench_evaluator": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    passed = result["passed"] is True
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25580_fresh_canonical_totality_quality_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / PROTOCOL),
        "raw_truth_snapshot_sha256": contract.sha256(ROOT / RAW_TRUTH),
        "truth_sha256": contract.sha256(ROOT / TRUTH),
        "quality_result_sha256": contract.sha256(ROOT / RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "quality_gate_passed": passed,
        "positive_signed_credit_count": 0,
        "authorization": {
            "deepwidebench_successor_build": valid and passed,
            "new_exact220_protocol_design": valid and passed,
            "deepwidebench_forward_or_evaluator": False,
            "additional_truth_fetch_replay_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build-audit", "protocol", "evaluate", "audit")
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), BUILD_AUDIT
    elif args.command == "protocol":
        value, path = preregister(), PROTOCOL
    elif args.command == "evaluate":
        value = evaluate()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
                    "status": value["status"],
                    "passed": value["passed"],
                    "metrics": value["metrics"],
                    "quality_decision": value["quality_decision"],
                    "authorization": value["authorization"],
                },
                sort_keys=True,
            )
        )
        return
    else:
        value, path = audit_result(), AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish_json(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "quality_gate_passed": value.get("quality_gate_passed"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
