#!/usr/bin/env python3
"""Post-freeze paired quality gate for the V2.55.50 visible constraints.

The shared-parent control and deterministic candidate predictions were frozen,
audited, committed, and pushed before this evaluator existed.  The evaluator
performs exactly one redirect-disabled, no-retry request to each of forty fixed
public authority endpoints: twenty PyPI project JSON documents and twenty
Hugging Face model API documents.  Every one of the forty frozen predictions
is scored exactly once.  Missing, conflicting, malformed, or unavailable truth
is failure-as-zero for both arms on the fixed twenty-task denominator.

Truth and quality are evaluator-only.  They are absent from the forward
dependency closure and can never affect the already frozen predictions.
Entropy or information gain assigns no signed credit.
"""

from __future__ import annotations

import argparse
import ast
import base64
import copy
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import requests
from packaging.version import InvalidVersion, Version


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25550_visible_constraint_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import control_v25550_visible_constraint_external as forward_control  # noqa: E402
from scripts import run_v25550_visible_constraint_external as forward_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260814"
PROTOCOL_ID = "v25551_v25550_visible_constraint_shared_parent_quality_v1"
SOURCE = Path("scripts/evaluate_v25551_visible_constraint_quality.py")
TEST = Path("tests/test_evaluate_v25551_visible_constraint_quality.py")
BUILD_AUDIT = Path(
    f"results/v25551_visible_constraint_quality_build_audit_v1_{DATE}.json"
)
PROTOCOL = contract.POSTFREEZE_QUALITY_PROTOCOL
RAW_TRUTH = contract.OUTPUT_ROOT / "postfreeze_authority_responses_v25551.json.gz"
TRUTH = contract.OUTPUT_ROOT / "postfreeze_authority_truth_v25551.json"
RESULT = contract.QUALITY_RESULT
AUDIT = contract.QUALITY_AUDIT

BASE_ARM = contract.runtime.CONTROL_ARM
CANDIDATE_ARM = contract.runtime.CANDIDATE_ARM
ARMS = (BASE_ARM, CANDIDATE_ARM)
METRICS = (
    "entity_coverage",
    "row_f1",
    "item_f1",
    "column_f1",
    "quality_composite",
)

USER_AGENT = "DeepWideResearch/1.0 (+postfreeze paired quality evaluator)"
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 60.0
FETCH_WORKERS = 20
PYPI_MAXIMUM_RESPONSE_BYTES = 32_000_000
HUGGINGFACE_MAXIMUM_RESPONSE_BYTES = 4_000_000
PYPI_PARSER_ID = "pypi_latest_pep440_stable_first_upload_utc_date_v1"
HUGGINGFACE_PARSER_ID = "huggingface_safetensors_total_exact_million_v1"
SCORER_ID = "two_row_visible_constraint_semantic_soft_canonical_exact_v1"
EXPECTED_TESTS = 10

# Two endpoints were inspected manually after prediction freeze only to verify
# the public API field name and transport shape.  No aggregate score, gate, task
# selection, prediction edit, threshold, or endpoint replacement was performed.
# The official frozen evaluation below still makes one fresh attempt to every
# endpoint and does not reuse either diagnostic response.
PREPROTOCOL_SCHEMA_PROBES = (
    "HuggingFaceTB/SmolLM2-135M-Instruct",
    "Qwen/Qwen3-0.6B",
)

FORWARD_AUDIT_SHA256 = (
    "61ac60f280aa23c6573b6ac768807a473a7119c61c185351ccfbae28e806fedb"
)
FORWARD_RESULT_SHA256 = (
    "53d0e993c3feceacf5c5bdc1b0a8e8ce16c08343920d966a16697746048b511b"
)
TASK_ROWS_SHA256 = (
    "2c44d2a7137eaa2dd9a8f08b4adff573b72fa1ee0d8ac11d93b50adee21cc2ea"
)
PREDICTION_FREEZE_SHA256 = (
    "00599099b6c2b66a3b629280e5c54c50a36b850c30926045aa7ba53eb6acc1a2"
)
FORWARD_RUNNER_SHA256 = (
    "9a815f2bc89e95c4a06d5f364999bb543d43c3a0e5071d9fb9942a11b9eed8f3"
)
FORWARD_CONTRACT_SHA256 = (
    "badff60b42ef540c50a3c1f3a399d8efde1eec9d0f877b3e473de1930d621f7b"
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
        contract.ordinary(ROOT, relative, tracked=tracked).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.51 expected a JSON object")
    return value


def _read_rows(*, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.55.51 expected JSONL objects")
    return rows


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.55.51 requires a clean pushed HEAD")
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
    markers = (
        str(SOURCE),
        str(contract.RUNNER),
        "scripts/run_official_eval_local.py",
    )
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


def _normalize_pypi(value: object) -> str:
    return re.sub(r"[-_.]+", "-", str(value or "").strip()).casefold()


def endpoint_vector() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for identity in contract.population.identity_vector():
        source = "pypi" if "/" not in identity else "huggingface"
        url = (
            f"https://pypi.org/pypi/{identity}/json"
            if source == "pypi"
            else f"https://huggingface.co/api/models/{identity}"
        )
        output.append(
            {
                "index": len(output),
                "source": source,
                "identity": identity,
                "url": url,
            }
        )
    expected_sources = ["pypi"] * 20 + ["huggingface"] * 20
    if (
        len(output) != contract.TASK_COUNT * contract.population.ROWS_PER_TASK
        or [value["index"] for value in output] != list(range(40))
        or [value["source"] for value in output] != expected_sources
        or len({value["identity"] for value in output}) != 40
        or len({value["url"] for value in output}) != 40
        or any(not str(value["url"]).startswith("https://") for value in output)
    ):
        raise RuntimeError("V2.55.51 endpoint vector drifted")
    return output


def _utc_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("upload timestamp missing")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("upload timestamp malformed") from exc
    if parsed.tzinfo is None:
        raise ValueError("upload timestamp timezone missing")
    return parsed.astimezone(timezone.utc).date().isoformat()


def _date_canonical(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%d").date()
    return f"{parsed.year}年{parsed.month}月{parsed.day}日"


def parse_pypi_response(raw: bytes, identity: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("PyPI JSON malformed") from exc
    info = value.get("info") if isinstance(value, dict) else None
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(info, Mapping) or not isinstance(releases, Mapping):
        raise ValueError("PyPI schema malformed")
    if _normalize_pypi(info.get("name")) != _normalize_pypi(identity):
        raise ValueError("PyPI identity mismatch")
    candidates: list[tuple[Version, str, Sequence[Any]]] = []
    for raw_version, files in releases.items():
        if not isinstance(raw_version, str):
            raise ValueError("PyPI version key malformed")
        try:
            version = Version(raw_version)
        except InvalidVersion:
            continue
        if version.is_prerelease or version.is_devrelease:
            continue
        if isinstance(files, Sequence) and not isinstance(files, (str, bytes)) and files:
            candidates.append((version, raw_version, files))
    if not candidates:
        raise ValueError("PyPI stable release absent")
    latest = max(version for version, _raw, _files in candidates)
    selected = [row for row in candidates if row[0] == latest]
    if len(selected) != 1:
        raise ValueError("PyPI latest stable release conflict")
    _version, raw_version, files = selected[0]
    dates: list[str] = []
    for file_row in files:
        if not isinstance(file_row, Mapping):
            raise ValueError("PyPI release file malformed")
        dates.append(
            _utc_date(
                file_row.get("upload_time_iso_8601")
                or file_row.get("upload_time")
            )
        )
    publication_date = min(dates)
    return {
        "source": "pypi",
        "identity": identity,
        "latest_stable_version": raw_version,
        "release_file_count": len(files),
        "release_date_iso": publication_date,
        "canonical_value": _date_canonical(publication_date),
        "sort_key": publication_date,
    }


def _million_decimal(total: int) -> Decimal:
    return Decimal(total) / Decimal(1_000_000)


def _canonical_million(total: int) -> str:
    decimal = _million_decimal(total)
    text = format(decimal, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return f"{text} million"


def parse_huggingface_response(raw: bytes, identity: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Hugging Face JSON malformed") from exc
    if not isinstance(value, Mapping) or value.get("id") != identity:
        raise ValueError("Hugging Face identity mismatch")
    safetensors = value.get("safetensors")
    if not isinstance(safetensors, Mapping):
        raise ValueError("Hugging Face safetensors metadata absent")
    total = safetensors.get("total")
    if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
        raise ValueError("Hugging Face safetensors total malformed")
    parameters = safetensors.get("parameters")
    verified = False
    if parameters is not None:
        if not isinstance(parameters, Mapping) or not parameters:
            raise ValueError("Hugging Face parameter breakdown malformed")
        amounts = list(parameters.values())
        if any(
            isinstance(amount, bool) or not isinstance(amount, int) or amount < 0
            for amount in amounts
        ):
            raise ValueError("Hugging Face parameter amount malformed")
        if sum(amounts) != total:
            raise ValueError("Hugging Face parameter total conflict")
        verified = True
    return {
        "source": "huggingface",
        "identity": identity,
        "safetensors_total": total,
        "parameter_breakdown_sum_verified": verified,
        "canonical_value": _canonical_million(total),
        "sort_key": total,
    }


def _columns(task_index: int) -> tuple[str, ...]:
    return (
        contract.population.DATE_COLUMNS
        if task_index < contract.population.DATE_TASK_COUNT
        else contract.population.SCALE_COLUMNS
    )


def _parse_table(prediction: str, task_index: int) -> tuple[list[list[str]], bool]:
    if not isinstance(prediction, str) or not prediction.strip():
        return [], False
    lines = [line.strip() for line in prediction.strip().splitlines() if line.strip()]
    if lines and re.fullmatch(r"```(?:markdown)?", lines[0], flags=re.IGNORECASE):
        if len(lines) < 2 or lines[-1] != "```":
            return [], False
        lines = lines[1:-1]
    if len(lines) != 4 or any(
        not line.startswith("|") or not line.endswith("|") for line in lines
    ):
        return [], False
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    columns = list(_columns(task_index))
    if (
        cells[0] != columns
        or len(cells[1]) != len(columns)
        or any(re.fullmatch(r":?-{3,}:?", cell) is None for cell in cells[1])
        or any(len(row) != len(columns) for row in cells[2:])
        or any(not cell for row in cells[2:] for cell in row)
    ):
        return [], False
    return cells[2:], True


def _parse_date_cell(value: str) -> str | None:
    text = " ".join(str(value).split())
    patterns = (
        (r"\d{4}年\d{1,2}月\d{1,2}日", "%Y年%m月%d日"),
        (r"\d{4}-\d{1,2}-\d{1,2}", "%Y-%m-%d"),
        (r"[A-Za-z]{3,9} \d{1,2}, \d{4}", "%b %d, %Y"),
        (r"[A-Za-z]{3,9} \d{1,2}, \d{4}", "%B %d, %Y"),
    )
    for pattern, form in patterns:
        if re.fullmatch(pattern, text) is None:
            continue
        try:
            return datetime.strptime(text, form).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_million_cell(value: str) -> Decimal | None:
    match = re.fullmatch(
        r"([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)\s+million",
        " ".join(str(value).split()),
        flags=re.IGNORECASE,
    )
    if match is None:
        return None
    try:
        amount = Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None
    return amount if amount >= 0 and amount.is_finite() else None


def _truth_pairs(records: Mapping[str, Mapping[str, Any]]) -> list[list[dict[str, Any]]]:
    output: list[list[dict[str, Any]]] = []
    for pair in contract.population.pair_vector():
        task: list[dict[str, Any]] = []
        for identity in pair:
            record = records.get(identity)
            if not isinstance(record, Mapping) or record.get("identity") != identity:
                task = []
                break
            task.append(dict(record))
        output.append(task)
    if len(output) != contract.TASK_COUNT:
        raise RuntimeError("V2.55.51 truth task denominator drifted")
    return output


def _semantic_value(task_index: int, value: str) -> object | None:
    return (
        _parse_date_cell(value)
        if task_index < contract.population.DATE_TASK_COUNT
        else _parse_million_cell(value)
    )


def _expected_semantic(task_index: int, record: Mapping[str, Any]) -> object:
    return (
        record["release_date_iso"]
        if task_index < contract.population.DATE_TASK_COUNT
        else _million_decimal(int(record["safetensors_total"]))
    )


def _identity_matches(task_index: int, observed: str, expected: str) -> bool:
    return (
        _normalize_pypi(observed) == _normalize_pypi(expected)
        if task_index < contract.population.DATE_TASK_COUNT
        else observed == expected
    )


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
    pairs = _truth_pairs(truth_records)
    truth = pairs[task_index]
    rows, structural_valid = _parse_table(prediction, task_index)
    if len(truth) != contract.population.ROWS_PER_TASK or not structural_valid:
        return _zero_metric()
    expected_identities = [record["identity"] for record in truth]
    matched: dict[str, list[str]] = {}
    for row in rows:
        matches = [
            identity
            for identity in expected_identities
            if _identity_matches(task_index, row[0], identity)
        ]
        if len(matches) == 1 and matches[0] not in matched:
            matched[matches[0]] = row
    entity_hits = len(matched)
    semantic_hits = 0
    for record in truth:
        row = matched.get(record["identity"])
        if row is not None and _semantic_value(task_index, row[1]) == _expected_semantic(
            task_index, record
        ):
            semantic_hits += 1
    entity_coverage = entity_hits / 2
    row_f1 = semantic_hits / 2
    item_f1 = (entity_hits + semantic_hits) / 4
    column_f1 = 1.0
    ordered_truth = sorted(
        enumerate(truth), key=lambda item: item[1]["sort_key"], reverse=True
    )
    exact = int(
        all(
            rows[position][0] == record["identity"]
            and (
                rows[position][1] == record["canonical_value"]
                if task_index < contract.population.DATE_TASK_COUNT
                else _parse_million_cell(rows[position][1])
                == _expected_semantic(task_index, record)
            )
            for position, (_original, record) in enumerate(ordered_truth)
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


def _delta(candidate: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "exact_table_successes": candidate["exact_table_successes"]
        - base["exact_table_successes"],
        "valid_tasks": candidate["valid_tasks"] - base["valid_tasks"],
        "invalid_tasks": candidate["invalid_tasks"] - base["invalid_tasks"],
        "fallback_tasks": candidate["fallback_tasks"] - base["fallback_tasks"],
        **{name: candidate[name] - base[name] for name in METRICS},
    }


def _aggregate_metrics(
    metrics: Sequence[Mapping[str, Any]], rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "tasks": len(metrics),
        "valid_tasks": sum(metric["valid"] is True for metric in metrics),
        "invalid_tasks": sum(metric["valid"] is False for metric in metrics),
        "fallback_tasks": sum(row["prediction_kind"] == "fallback" for row in rows),
        "exact_table_successes": sum(
            int(metric["exact_table_success"]) for metric in metrics
        ),
        **{
            name: sum(float(metric[name]) for metric in metrics) / contract.TASK_COUNT
            for name in METRICS
        },
    }


def _disposition(
    by_task: Mapping[int, Mapping[str, Mapping[str, Any]]], metric: str
) -> dict[str, int]:
    output = {"candidate_win": 0, "tie": 0, "candidate_loss": 0}
    for index in range(contract.TASK_COUNT):
        delta = float(by_task[index][CANDIDATE_ARM][metric]) - float(
            by_task[index][BASE_ARM][metric]
        )
        key = (
            "candidate_win"
            if delta > 1e-12
            else "candidate_loss"
            if delta < -1e-12
            else "tie"
        )
        output[key] += 1
    return output


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], truth_records: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    checked = [forward_runner.validate_task_row(row) for row in rows]
    tasks = contract.task_vector()
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in tasks]
        or [row["task_index"] for row in checked] != list(range(contract.TASK_COUNT))
    ):
        raise ValueError("V2.55.51 frozen task denominator drifted")
    pairs = _truth_pairs(truth_records)
    by_arm: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    by_task: dict[int, dict[str, dict[str, Any]]] = {}
    for row in checked:
        index = int(row["task_index"])
        by_task[index] = {}
        for arm in ARMS:
            metric = evaluate_prediction(row["predictions"][arm], index, truth_records)
            by_arm[arm].append(metric)
            by_task[index][arm] = metric
    aggregate = {
        arm: _aggregate_metrics(by_arm[arm], checked) for arm in ARMS
    }
    family_metrics: dict[str, Any] = {}
    for family, indices in (
        ("date", range(0, contract.population.DATE_TASK_COUNT)),
        (
            "scale",
            range(contract.population.DATE_TASK_COUNT, contract.TASK_COUNT),
        ),
    ):
        family_metrics[family] = {
            arm: {
                "tasks": len(indices),
                "exact_table_successes": sum(
                    int(by_task[index][arm]["exact_table_success"])
                    for index in indices
                ),
                "quality_composite": sum(
                    float(by_task[index][arm]["quality_composite"])
                    for index in indices
                )
                / len(indices),
            }
            for arm in ARMS
        }
    return {
        "evaluation_count": contract.TASK_COUNT * len(ARMS),
        "truth_identity_count": len(truth_records),
        "truth_complete_tasks": sum(len(pair) == 2 for pair in pairs),
        "arms": aggregate,
        "candidate_minus_control": _delta(
            aggregate[CANDIDATE_ARM], aggregate[BASE_ARM]
        ),
        "candidate_vs_control_exact_disposition": _disposition(
            by_task, "exact_table_success"
        ),
        "candidate_vs_control_composite_disposition": _disposition(
            by_task, "quality_composite"
        ),
        "family_metrics": family_metrics,
        "shared_parent_treatment_comparison": True,
    }


def quality_decision(metrics: Mapping[str, Any]) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    control = arms.get(BASE_ARM) or {}
    candidate = arms.get(CANDIDATE_ARM) or {}
    delta = metrics.get("candidate_minus_control") or {}
    checks = {
        "fixed_prediction_denominator": metrics.get("evaluation_count")
        == contract.TASK_COUNT * len(ARMS)
        and control.get("tasks") == contract.TASK_COUNT
        and candidate.get("tasks") == contract.TASK_COUNT,
        "truth_valid_for_all_fixed_tasks": metrics.get("truth_complete_tasks")
        == contract.TASK_COUNT
        and metrics.get("truth_identity_count") == 40,
        "candidate_whole_table_exact_strict_gain": delta.get(
            "exact_table_successes", 0
        )
        > 0,
        "entity_nonregression": delta.get("entity_coverage", -1) >= 0,
        "row_nonregression": delta.get("row_f1", -1) >= 0,
        "item_nonregression": delta.get("item_f1", -1) >= 0,
        "column_nonregression": delta.get("column_f1", -1) >= 0,
        "composite_nonregression": delta.get("quality_composite", -1) >= 0,
        "valid_task_nonregression": delta.get("valid_tasks", -1) >= 0,
        "invalid_task_nonincrease": delta.get("invalid_tasks", 1) <= 0,
        "fallback_nonincrease": delta.get("fallback_tasks", 1) <= 0,
        "shared_parent_treatment_comparison": metrics.get(
            "shared_parent_treatment_comparison"
        )
        is True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {"checks": checks, "failed_checks": failed, "quality_gate_passed": not failed}


def parser_contract() -> dict[str, Any]:
    return {
        "pypi_parser_id": PYPI_PARSER_ID,
        "pypi_latest_pep440_parseable_non_prerelease_non_dev_release": True,
        "pypi_release_date_is_earliest_utc_upload_calendar_date": True,
        "pypi_equal_maximum_version_alias_conflict_fails_closed": True,
        "huggingface_parser_id": HUGGINGFACE_PARSER_ID,
        "huggingface_value_is_exact_safetensors_total_divided_by_one_million": True,
        "huggingface_parameter_breakdown_mismatch_fails_closed": True,
        "missing_malformed_identity_conflicting_or_oversized_truth_scores_zero": True,
    }


def scoring_contract() -> dict[str, Any]:
    return {
        "scorer_id": SCORER_ID,
        "fixed_task_denominator": contract.TASK_COUNT,
        "fixed_prediction_count": contract.TASK_COUNT * len(ARMS),
        "semantic_soft_metrics_accept_equivalent_visible_date_or_million_value": True,
        "whole_table_exact_requires_exact_schema_two_rows_canonical_value_and_stable_descending_order": True,
        "entity_row_item_column_and_composite_all_reported": True,
        "each_frozen_prediction_evaluated_exactly_once": True,
        "invalid_or_incomplete_truth_is_zero_for_both_arms": True,
        "prediction_retry_repair_mutation_selection_or_revaluation": False,
    }


def truth_fetch_contract() -> dict[str, Any]:
    return {
        "fixed_endpoint_count": 40,
        "pypi_endpoint_count": 20,
        "huggingface_endpoint_count": 20,
        "attempts_per_endpoint": 1,
        "allow_redirects": False,
        "requests_library_retry_adapter": False,
        "replacement_refetch_or_backfill": False,
        "fetch_workers": FETCH_WORKERS,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "pypi_maximum_response_bytes": PYPI_MAXIMUM_RESPONSE_BYTES,
        "huggingface_maximum_response_bytes": HUGGINGFACE_MAXIMUM_RESPONSE_BYTES,
        "all_raw_responses_hash_bound_in_one_deterministic_gzip_snapshot": True,
    }


def schema_probe_disclosure() -> dict[str, Any]:
    return {
        "count": len(PREPROTOCOL_SCHEMA_PROBES),
        "identities": list(PREPROTOCOL_SCHEMA_PROBES),
        "occurred_after_prediction_freeze": True,
        "purpose": "confirm_public_huggingface_api_schema_and_transport_only",
        "aggregate_quality_metric_or_gate_computed": False,
        "task_prediction_threshold_endpoint_or_population_changed": False,
        "diagnostic_response_reused_by_official_evaluation": False,
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
        or audit.get("role") != "v25550_visible_constraint_external_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not True
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
        or forward.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not True
        or len(rows) != contract.TASK_COUNT
        or freeze.get("task_rows_sha256") != TASK_ROWS_SHA256
        or freeze.get("both_prediction_texts_persisted") is not True
        or not contract.sealed(freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.55.51 pushed forward barrier drifted")
    return audit, rows


def _test() -> dict[str, Any]:
    return base_audit._test(TEST.name, EXPECTED_TESTS)


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
    forbidden_calls = [
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
        and not forbidden_calls
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
    test = _test()
    tracked = all(
        not require_clean
        or contract.git(ROOT, "ls-files", "--error-unmatch", str(path))
        for path in (SOURCE, TEST)
    )
    closure = {str(path) for path in contract.forward_dependency_closure(ROOT)}
    source = contract.ordinary(ROOT, SOURCE, tracked=require_clean)
    test_path = contract.ordinary(ROOT, TEST, tracked=require_clean)
    endpoints = endpoint_vector()
    checks = {
        "git_clean_head_equals_target_main": head == target,
        "source_and_test_tracked": tracked,
        "pushed_forward_audit_authorizes_quality": bool(forward_audit),
        "fixed_forward_hashes_exact": (
            contract.sha256(ROOT / contract.FORWARD_AUDIT) == FORWARD_AUDIT_SHA256
            and contract.sha256(ROOT / contract.FORWARD_RESULT)
            == FORWARD_RESULT_SHA256
            and contract.sha256(ROOT / contract.TASK_ROWS) == TASK_ROWS_SHA256
            and contract.sha256(ROOT / contract.PREDICTION_FREEZE)
            == PREDICTION_FREEZE_SHA256
        ),
        "all_frozen_rows_validate_before_truth": len(rows) == contract.TASK_COUNT,
        "focused_quality_tests_exact10": test["passed"],
        "evaluator_source_absent_from_forward_closure": str(SOURCE) not in closure,
        "truth_mapping_and_network_capability_absent_from_forward_closure": all(
            "evaluate_v25551" not in path for path in closure
        ),
        "single_no_redirect_streaming_requests_get_contract": _source_network_contract(
            source
        ),
        "fixed_endpoint_vector_exact_unique_forty": len(endpoints) == 40,
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
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25551_visible_constraint_quality_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "evaluator_source_sha256": contract.sha256(source),
        "evaluator_test_sha256": contract.sha256(test_path),
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "endpoint_vector_sha256": contract.payload_sha256(endpoints),
        "test": test,
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "truth_fetch": truth_fetch_contract(),
        "preprotocol_schema_probe_disclosure": schema_probe_disclosure(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_evaluation_performed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "postfreeze_quality_protocol_generation": not findings,
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
        copied.get("role") != "v25551_visible_constraint_quality_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or copied.get("test", {}).get("expected") != EXPECTED_TESTS
        or copied.get("test", {}).get("observed") != EXPECTED_TESTS
        or copied.get("test", {}).get("passed") is not True
        or copied.get("endpoint_vector_sha256")
        != contract.payload_sha256(endpoint_vector())
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("preprotocol_schema_probe_disclosure")
        != schema_probe_disclosure()
        or copied.get("network_model_search_fetch_or_evaluation_performed") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
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
        raise ValueError("V2.55.51 quality build audit drifted")
    return copied


def preregister(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build_audit(_read(BUILD_AUDIT))
    forward_audit, _rows = _forward_barrier()
    if not _future_pristine((PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.55.51 quality protocol surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25551_visible_constraint_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "target_main": target,
        "quality_build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "evaluator_source_sha256": build["evaluator_source_sha256"],
        "evaluator_test_sha256": build["evaluator_test_sha256"],
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "frozen_task_count": contract.TASK_COUNT,
        "fixed_prediction_count": contract.TASK_COUNT * len(ARMS),
        "fixed_truth_identity_count": 40,
        "endpoint_vector_sha256": contract.payload_sha256(endpoint_vector()),
        "truth_fetch": truth_fetch_contract(),
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "quality_gate": contract.quality_gate(),
        "preprotocol_schema_probe_disclosure": schema_probe_disclosure(),
        "prediction_freeze_and_pushed_forward_audit_precede_official_truth_open": True,
        "control_and_candidate_share_one_v25401_parent_forward": True,
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
        raise RuntimeError("V2.55.51 forward audit does not authorize quality")
    return validate_protocol(contract.seal(value, "protocol_payload_sha256"))


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25551_visible_constraint_quality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("git_head") != copied.get("target_main")
        or copied.get("quality_build_audit_sha256")
        != contract.sha256(ROOT / BUILD_AUDIT)
        or copied.get("evaluator_source_sha256") != contract.sha256(ROOT / SOURCE)
        or copied.get("evaluator_test_sha256") != contract.sha256(ROOT / TEST)
        or copied.get("forward_audit_sha256") != FORWARD_AUDIT_SHA256
        or copied.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or copied.get("task_rows_sha256") != TASK_ROWS_SHA256
        or copied.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or copied.get("frozen_task_count") != contract.TASK_COUNT
        or copied.get("fixed_prediction_count") != contract.TASK_COUNT * len(ARMS)
        or copied.get("fixed_truth_identity_count") != 40
        or copied.get("endpoint_vector_sha256")
        != contract.payload_sha256(endpoint_vector())
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get("preprotocol_schema_probe_disclosure")
        != schema_probe_disclosure()
        or copied.get(
            "prediction_freeze_and_pushed_forward_audit_precede_official_truth_open"
        )
        is not True
        or copied.get("control_and_candidate_share_one_v25401_parent_forward")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
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
        raise ValueError("V2.55.51 quality protocol drifted")
    return copied


def _maximum_bytes(spec: Mapping[str, Any]) -> int:
    return (
        PYPI_MAXIMUM_RESPONSE_BYTES
        if spec["source"] == "pypi"
        else HUGGINGFACE_MAXIMUM_RESPONSE_BYTES
    )


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
            cap = _maximum_bytes(spec)
            parts: list[bytes] = []
            observed = 0
            for chunk in response.iter_content(chunk_size=65_536):
                if not chunk:
                    continue
                observed += len(chunk)
                if observed > cap:
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
        raise RuntimeError("V2.55.51 fixed fetch vector did not terminate")
    return [dict(value) for value in output if value is not None]


def _parse_record(spec: Mapping[str, Any], raw: bytes) -> dict[str, Any]:
    return (
        parse_pypi_response(raw, str(spec["identity"]))
        if spec["source"] == "pypi"
        else parse_huggingface_response(raw, str(spec["identity"]))
    )


def _truth_artifact(
    fetched: Sequence[Mapping[str, Any]], *, now: int
) -> tuple[bytes, dict[str, Any]]:
    specs = endpoint_vector()
    if len(fetched) != len(specs):
        raise ValueError("V2.55.51 fetched denominator drifted")
    snapshot_rows: list[dict[str, Any]] = []
    endpoint_rows: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    for spec, observed in zip(specs, fetched, strict=True):
        if any(observed.get(key) != spec[key] for key in spec):
            raise ValueError("V2.55.51 fetched endpoint binding drifted")
        raw = observed.get("raw")
        if not isinstance(raw, bytes):
            raise ValueError("V2.55.51 fetched raw response drifted")
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
        "role": "v25551_postfreeze_authority_truth",
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
    }
    return compressed, contract.seal(value, "truth_payload_sha256")


def validate_truth(value: Mapping[str, Any], compressed: bytes) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    try:
        plain = gzip.decompress(compressed)
        snapshot = json.loads(plain)
    except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.55.51 compressed truth snapshot drifted") from exc
    specs = endpoint_vector()
    endpoints = copied.get("endpoints")
    records = copied.get("records")
    if (
        copied.get("role") != "v25551_postfreeze_authority_truth"
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
        or copied.get("one_official_attempt_per_fixed_endpoint_no_retry_redirect_or_replacement")
        is not True
        or copied.get("same_truth_records_used_for_both_prediction_arms") is not True
        or copied.get("prediction_freeze_and_pushed_forward_audit_preexisted")
        is not True
        or not contract.sealed(copied, "truth_payload_sha256")
    ):
        raise ValueError("V2.55.51 truth artifact drifted")
    replay_records: dict[str, dict[str, Any]] = {}
    replay_endpoints: list[dict[str, Any]] = []
    for spec, raw_row, endpoint in zip(specs, snapshot, endpoints, strict=True):
        if not isinstance(raw_row, Mapping) or not isinstance(endpoint, Mapping):
            raise ValueError("V2.55.51 truth endpoint shape drifted")
        if any(raw_row.get(key) != spec[key] for key in spec):
            raise ValueError("V2.55.51 snapshot endpoint binding drifted")
        try:
            raw = base64.b64decode(raw_row.get("raw_response_base64"), validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("V2.55.51 snapshot base64 drifted") from exc
        if (
            raw_row.get("attempt_count") != 1
            or raw_row.get("raw_response_bytes") != len(raw)
            or raw_row.get("raw_response_sha256")
            != hashlib.sha256(raw).hexdigest()
        ):
            raise ValueError("V2.55.51 raw response receipt drifted")
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
            raise ValueError("V2.55.51 parsed endpoint receipt drifted")
        replay_endpoints.append(expected_endpoint)
        if record is not None:
            replay_records[str(spec["identity"])] = record
    if (
        dict(records) != replay_records
        or copied.get("attempt_count") != 40
        or copied.get("successful_transport_count")
        != sum(row["failure_type"] is None for row in replay_endpoints)
        or copied.get("valid_record_count") != len(replay_records)
        or copied.get("complete_task_count")
        != sum(
            all(identity in replay_records for identity in pair)
            for pair in contract.population.pair_vector()
        )
    ):
        raise ValueError("V2.55.51 truth replay aggregate drifted")
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
        "role": "v25551_visible_constraint_shared_parent_quality_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "status": "visible_constraint_shared_parent_quality_go"
        if passed
        else "visible_constraint_shared_parent_quality_no_go",
        "passed": passed,
        "quality_protocol_sha256": protocol_sha256,
        "forward_audit_sha256": protocol["forward_audit_sha256"],
        "forward_result_sha256": protocol["forward_result_sha256"],
        "task_rows_sha256": protocol["task_rows_sha256"],
        "prediction_freeze_sha256": protocol["prediction_freeze_sha256"],
        "compressed_truth_snapshot_sha256": truth["compressed_snapshot_sha256"],
        "truth_payload_sha256": truth["truth_payload_sha256"],
        "metrics": dict(metrics),
        "quality_decision": decision,
        "all_forty_predictions_evaluated_once": True,
        "all_forty_fixed_truth_endpoints_attempted_once": truth["attempt_count"] == 40,
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit": True,
        "prediction_retry_repair_selection_or_mutation": False,
        "control_and_candidate_share_one_v25401_parent_forward": True,
        "candidate_minus_control_is_shared_parent_treatment_effect": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "claim_scope": {
            "fresh_external_shared_parent_quality_measured": True,
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
        copied.get("role") != "v25551_visible_constraint_shared_parent_quality_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "visible_constraint_shared_parent_quality_go"
            if passed
            else "visible_constraint_shared_parent_quality_no_go"
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
            "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit"
        )
        is not True
        or copied.get("prediction_retry_repair_selection_or_mutation") is not False
        or copied.get("control_and_candidate_share_one_v25401_parent_forward")
        is not True
        or copied.get("candidate_minus_control_is_shared_parent_treatment_effect")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("claim_scope")
        != {
            "fresh_external_shared_parent_quality_measured": True,
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
        raise ValueError("V2.55.51 quality result drifted")
    if truth is not None and rows is not None:
        records = truth.get("records")
        if (
            not isinstance(records, Mapping)
            or copied.get("truth_payload_sha256") != truth.get("truth_payload_sha256")
            or copied.get("metrics") != evaluate_rows(rows, records)
        ):
            raise ValueError("V2.55.51 quality result replay drifted")
    return copied


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _forward_audit, rows = _forward_barrier()
    if not _future_pristine((RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.55.51 evaluation surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.55.51 protected watcher identity drifted")
    if not forward_control._lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.55.51 shared evaluation runtime is not ready")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25551_visible_constraint_shared_parent_quality_v1",
        purpose="single_postfreeze_forty_endpoint_truth_and_fixed_two_arm_evaluation",
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
        "metrics_and_quality_decision_recompute_exactly": (
            result["metrics"] == recomputed_metrics
            and result["quality_decision"] == recomputed_decision
        ),
        "shared_parent_candidate_comparison_preserved": result[
            "candidate_minus_control_is_shared_parent_treatment_effect"
        ]
        is True,
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
        "role": "v25551_visible_constraint_shared_parent_quality_audit",
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
