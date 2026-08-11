#!/usr/bin/env python3
"""Post-freeze PyPI evaluator for the V2.51.29 causal-salience gate.

This evaluator-only module was created after the frozen predictions and
content-free forward audit were committed and pushed.  The package mapping is
fixed from the public description-clue vector and is not imported by forward
code.  Gold and quality outcomes can never feed back into the frozen forward.
"""

from __future__ import annotations

import argparse
import ast
import copy
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25129_causal_salience_external_contract as contract  # noqa: E402
from scripts import run_v25129_causal_salience_external as runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TEST = Path("tests/test_evaluate_v25129_causal_salience_external.py")
MAX_GOLD_RESPONSE_BYTES = 64 * 1024 * 1024
GOLD_CONNECT_TIMEOUT_SECONDS = 5.0
GOLD_READ_TIMEOUT_SECONDS = 60.0
EVALUATOR_LEASE_OWNER = "v25129_causal_salience_external_evaluator_v1"
EVALUATOR_LEASE_PURPOSE = "single_postfreeze_pypi_gold_snapshot_and_quality_gate"
METRICS = ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")

# Fixed only from contract.CLUES, before reading any prediction text.
PACKAGE_VECTOR = (
    "typer",
    "rich",
    "prompt-toolkit",
    "fire",
    "click",
    "textual",
    "dateparser",
    "requests",
    "aiohttp",
    "uvicorn",
    "starlette",
    "fastapi",
    "flask",
    "django",
    "pandera",
    "marshmallow",
    "cattrs",
    "msgspec",
    "pyjwt",
    "cryptography",
)


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.51.29 evaluator requires clean pushed HEAD")


def _read(relative: Path, *, tracked: bool) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.29 evaluator expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.51.29 evaluator expected JSONL objects")
    return rows


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def package_vector() -> tuple[str, ...]:
    if (
        len(PACKAGE_VECTOR) != contract.TASK_COUNT
        or len(set(PACKAGE_VECTOR)) != contract.TASK_COUNT
        or len(contract.CLUES) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.51.29 evaluator package mapping drifted")
    return PACKAGE_VECTOR


def endpoint_vector() -> tuple[str, ...]:
    values = tuple(
        f"https://pypi.org/pypi/{project}/json" for project in package_vector()
    )
    if len(values) != contract.TASK_COUNT or len(set(values)) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.29 evaluator endpoint vector drifted")
    return values


def _validate_forward_parents() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]
]:
    protocol = contract.validate_protocol(
        ROOT, _read(contract.PROTOCOL, tracked=True)
    )
    forward = runner.validate_forward_result(
        _read(contract.FORWARD_RESULT, tracked=True)
    )
    audit = _read(contract.FORWARD_AUDIT, tracked=True)
    rows = [
        runner.validate_task_row(row)
        for row in _read_jsonl(contract.TASK_ROWS, tracked=True)
    ]
    freeze = _read(contract.PREDICTION_FREEZE, tracked=True)
    expected_ids = [row["opaque_id"] for row in contract.task_vector()]
    if (
        audit.get("role") != "v25129_causal_salience_external_forward_audit"
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not all((audit.get("checks") or {}).values())
        or audit.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or audit.get("task_rows_sha256")
        != contract.sha256(ROOT / contract.TASK_ROWS)
        or audit.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or audit.get("mechanism_decision") != forward.get("mechanism_decision")
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not True
        or audit.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not True
        or not contract.sealed(audit, "audit_payload_sha256")
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or freeze.get("role")
        != "v25129_causal_salience_external_prediction_freeze"
        or freeze.get("protocol_id") != contract.PROTOCOL_ID
        or freeze.get("task_rows_sha256")
        != contract.sha256(ROOT / contract.TASK_ROWS)
        or freeze.get(
            "all_predictions_terminal_before_hidden_mapping_gold_evaluator_or_quality_decision"
        )
        is not True
        or [row["opaque_id"] for row in rows] != expected_ids
        or protocol.get("protected_watchers") != contract.watcher_snapshot()
    ):
        raise RuntimeError("V2.51.29 evaluator parent barrier failed")
    return protocol, forward, audit, rows


def implementation_audit(*, require_tracked: bool) -> dict[str, Any]:
    source_path = contract.ordinary(ROOT, contract.EVALUATOR, tracked=require_tracked)
    test_path = contract.ordinary(ROOT, TEST, tracked=require_tracked)
    source_text = source_path.read_text(encoding="utf-8")
    test_text = test_path.read_text(encoding="utf-8")
    source_tree = ast.parse(source_text, filename=str(source_path))
    test_tree = ast.parse(test_text, filename=str(test_path))
    request_calls: list[dict[str, str]] = []
    privileged_accesses: list[dict[str, str]] = []
    runner_attributes: set[str] = set()
    privileged_fields = {
        "category",
        "question_type",
        "task_category",
        "ground_truth",
        "answer_key",
        "split",
        "score",
        "reward",
    }
    for node in source_tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for child in ast.walk(node):
            if (
                isinstance(child, ast.Attribute)
                and isinstance(child.value, ast.Name)
                and child.value.id == "runner"
            ):
                runner_attributes.add(child.attr)
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "requests"
            ):
                request_calls.append(
                    {"function": node.name, "method": child.func.attr}
                )
            if isinstance(child, ast.Subscript):
                key = (
                    child.slice.value
                    if isinstance(child.slice, ast.Constant)
                    else None
                )
                if isinstance(key, str) and key in privileged_fields:
                    privileged_accesses.append(
                        {"function": node.name, "field": key}
                    )
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "get"
                and child.args
                and isinstance(child.args[0], ast.Constant)
                and child.args[0].value in privileged_fields
            ):
                privileged_accesses.append(
                    {"function": node.name, "field": child.args[0].value}
                )
    test_count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(test_tree)
    )
    checks = {
        "evaluator_and_test_are_ordinary": True,
        "network_capability_only_in_fetch_gold": request_calls
        == [{"function": "_fetch_gold", "method": "get"}],
        "credential_literal_zero": not contract.SECRET.search(source_text + test_text),
        "independent_test_count_at_least_eight": test_count >= 8,
        "privileged_benchmark_field_access_zero": not privileged_accesses,
        "runner_capability_limited_to_frozen_validation": runner_attributes
        <= {"validate_forward_result", "validate_task_row"},
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "request_calls": request_calls,
        "privileged_accesses": privileged_accesses,
        "runner_attributes": sorted(runner_attributes),
        "test_count": test_count,
        "evaluator_sha256": contract.sha256(source_path),
        "test_sha256": contract.sha256(test_path),
    }


def quality_rule() -> dict[str, Any]:
    return {
        **copy.deepcopy(contract.quality_gate()),
        "all_postfreeze_gold_tasks_valid": True,
        "candidate_exact_strict_gain": True,
        "candidate_entity_row_item_column_composite_nonregression": True,
        "mechanism_equal_search_fetch_evidence_and_effective_model_budget": True,
    }


def build_evaluator_protocol(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_implementation_tracked: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    protocol, forward, audit, rows = _validate_forward_parents()
    implementation = implementation_audit(
        require_tracked=require_implementation_tracked
    )
    future = (
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.POSTFREEZE_GOLD,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.51.29 evaluator surface is not pristine")
    if not implementation["audit_valid"]:
        raise RuntimeError(
            f"V2.51.29 evaluator implementation audit failed: {implementation['findings']}"
        )
    if audit["mechanism_decision"].get("mechanism_gate_passed") is not True:
        raise RuntimeError("V2.51.29 mechanism gate withheld evaluator authority")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25129_causal_salience_external_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "evaluator_sha256": implementation["evaluator_sha256"],
            "evaluator_test_sha256": implementation["test_sha256"],
        },
        "population": {
            "fixed_denominator": contract.TASK_COUNT,
            "prediction_rows": len(rows),
            "clue_vector_sha256": contract.payload_sha256(contract.CLUES),
            "package_vector_sha256": contract.payload_sha256(package_vector()),
            "endpoint_vector_sha256": contract.payload_sha256(endpoint_vector()),
        },
        "evaluation": {
            "exact_endpoint_calls": contract.TASK_COUNT,
            "calls_per_endpoint": 1,
            "redirects": 0,
            "retries_or_refetches": 0,
            "concurrency": contract.EXECUTOR_CONCURRENCY,
            "same_postfreeze_gold_snapshot_for_both_arms": True,
            "fixed_denominator_failure_as_zero": True,
            "metrics": ["exact_table_successes", *METRICS],
            "gold_rule": {
                "package": "pypi_info_name_canonical_identity_checked",
                "version": "pypi_info_version",
                "released": "earliest_upload_date_among_files_under_info_version",
                "requires": "pypi_info_requires_python_or_Unknown",
            },
            "quality_rule": quality_rule(),
        },
        "implementation_audit": implementation,
        "source_policy": {
            "created_only_after_pushed_prediction_freeze_and_forward_audit": True,
            "mapping_frozen_from_public_clues_before_prediction_text_read": True,
            "forward_files_are_read_only": True,
            "gold_or_evaluator_feedback_to_forward": False,
            "category_question_type_split_or_deepwidebench_gold_read": False,
            "entropy_or_information_gain_credit_validated": False,
        },
        "authorization": {
            "one_postfreeze_external_evaluation": True,
            "retry_refetch_selective_revaluation": False,
            "full220_successor_build_only_if_quality_go": True,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "evaluator_protocol_payload_sha256")


def validate_evaluator_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    parents = copied.get("parents") or {}
    population = copied.get("population") or {}
    evaluation = copied.get("evaluation") or {}
    implementation = implementation_audit(require_tracked=True)
    expected_authorization = {
        "one_postfreeze_external_evaluation": True,
        "retry_refetch_selective_revaluation": False,
        "full220_successor_build_only_if_quality_go": True,
        "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
    }
    if (
        copied.get("role")
        != "v25129_causal_salience_external_evaluator_preregistration"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or parents.get("forward_protocol_sha256")
        != contract.sha256(ROOT / contract.PROTOCOL)
        or parents.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or parents.get("forward_audit_sha256")
        != contract.sha256(ROOT / contract.FORWARD_AUDIT)
        or parents.get("task_rows_sha256")
        != contract.sha256(ROOT / contract.TASK_ROWS)
        or parents.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or parents.get("evaluator_sha256") != implementation["evaluator_sha256"]
        or parents.get("evaluator_test_sha256") != implementation["test_sha256"]
        or population.get("fixed_denominator") != contract.TASK_COUNT
        or population.get("prediction_rows") != contract.TASK_COUNT
        or population.get("clue_vector_sha256")
        != contract.payload_sha256(contract.CLUES)
        or population.get("package_vector_sha256")
        != contract.payload_sha256(package_vector())
        or population.get("endpoint_vector_sha256")
        != contract.payload_sha256(endpoint_vector())
        or evaluation.get("exact_endpoint_calls") != contract.TASK_COUNT
        or evaluation.get("calls_per_endpoint") != 1
        or evaluation.get("redirects") != 0
        or evaluation.get("retries_or_refetches") != 0
        or evaluation.get("same_postfreeze_gold_snapshot_for_both_arms") is not True
        or evaluation.get("fixed_denominator_failure_as_zero") is not True
        or evaluation.get("quality_rule") != quality_rule()
        or copied.get("implementation_audit") != implementation
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "evaluator_protocol_payload_sha256")
    ):
        raise RuntimeError("V2.51.29 evaluator protocol drifted")
    return copied


def _normalize_package(value: object) -> str:
    return re.sub(r"[-_.]+", "-", " ".join(str(value).split()).casefold())


def _normalize_value(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _normalize_requires(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [
        line.strip()
        for line in str(text).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(lines) < 2:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    columns = cells[0]
    separator = cells[1]
    if len(separator) != len(columns) or any(
        not re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))
        for cell in separator
    ):
        return [], []
    return columns, [row for row in cells[2:] if len(row) == len(columns)]


def evaluate_prediction(
    prediction: str, gold: Mapping[str, Any]
) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    exact_columns = columns == list(contract.COLUMNS)
    selected = rows if exact_columns else []
    expected = _normalize_package(gold["package"])
    predicted = {
        _normalize_package(row[0]): row
        for row in selected
        if _normalize_package(row[0])
    }
    entity = int(expected in predicted)
    entity_precision = entity / len(predicted) if predicted else 0.0
    entity_recall = float(entity)
    row_f1 = (
        2 * entity_precision * entity_recall / (entity_precision + entity_recall)
        if entity_precision + entity_recall
        else 0.0
    )
    correct_items = 0
    if expected in predicted:
        row = predicted[expected]
        correct_items += int(
            _normalize_value(row[1]) == _normalize_value(gold["version"])
        )
        correct_items += int(
            _normalize_value(row[2]) == _normalize_value(gold["released"])
        )
        correct_items += int(
            _normalize_requires(row[3]) == _normalize_requires(gold["requires"])
        )
    predicted_items = len(predicted) * 3
    item_precision = correct_items / predicted_items if predicted_items else 0.0
    item_recall = correct_items / 3
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    exact = int(
        exact_columns
        and len(selected) == 1
        and list(predicted) == [expected]
        and correct_items == 3
    )
    column_f1 = 1.0 if exact_columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": entity_recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (entity_recall + row_f1 + item_f1 + column_f1) / 4,
    }


def _invalid_gold(index: int) -> dict[str, Any]:
    endpoint = endpoint_vector()[index]
    return {
        "index": index,
        "opaque_id": contract.task_vector()[index]["opaque_id"],
        "clue_sha256": contract.payload_sha256(contract.CLUES[index]),
        "requested_package": package_vector()[index],
        "endpoint_sha256": hashlib.sha256(endpoint.encode()).hexdigest(),
        "package": package_vector()[index],
        "version": "Unknown",
        "released": "Unknown",
        "requires": "Unknown",
        "response_sha256": "",
        "response_bytes": 0,
        "http_status": 0,
        "attempts": 1,
        "valid": False,
    }


def _fetch_gold(index: int) -> dict[str, Any]:
    project = package_vector()[index]
    endpoint = endpoint_vector()[index]
    output = _invalid_gold(index)
    try:
        with requests.get(
            endpoint,
            headers={
                "User-Agent": "DeepWideResearch/1.0 (+v25129-postfreeze-evaluator)"
            },
            timeout=(GOLD_CONNECT_TIMEOUT_SECONDS, GOLD_READ_TIMEOUT_SECONDS),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            if status != 200 or str(response.url) != endpoint:
                raise ValueError("V2.51.29 PyPI endpoint identity drifted")
            response.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_GOLD_RESPONSE_BYTES:
                    raise ValueError("V2.51.29 PyPI response exceeds cap")
                chunks.append(bytes(chunk))
            raw = b"".join(chunks)
        value = json.loads(raw.decode("utf-8"))
        info = value.get("info") if isinstance(value, Mapping) else None
        releases = value.get("releases") if isinstance(value, Mapping) else None
        if not isinstance(info, Mapping) or not isinstance(releases, Mapping):
            raise ValueError("V2.51.29 PyPI response schema drifted")
        name = str(info.get("name") or "").strip()
        version = str(info.get("version") or "").strip()
        if _normalize_package(name) != _normalize_package(project) or not version:
            raise ValueError("V2.51.29 PyPI project/version identity drifted")
        files = releases.get(version)
        if not isinstance(files, list) or not files:
            raise ValueError("V2.51.29 latest-release files absent")
        dates = sorted(
            str(item.get("upload_time_iso_8601") or item.get("upload_time") or "")[:10]
            for item in files
            if isinstance(item, Mapping)
            and re.fullmatch(
                r"\d{4}-\d{2}-\d{2}",
                str(
                    item.get("upload_time_iso_8601")
                    or item.get("upload_time")
                    or ""
                )[:10],
            )
        )
        if not dates:
            raise ValueError("V2.51.29 latest-release date absent")
        requires = str(info.get("requires_python") or "Unknown").strip()
        for field in (name, version, requires):
            if not field or len(field) > 500 or any(char in field for char in "\r\n\x00|"):
                raise ValueError("V2.51.29 PyPI gold field invalid")
        output.update(
            {
                "package": name,
                "version": version,
                "released": dates[0],
                "requires": requires,
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "response_bytes": len(raw),
                "http_status": status,
                "valid": True,
            }
        )
    except Exception:
        pass
    return output


def validate_gold_rows(values: object) -> list[dict[str, Any]]:
    if not isinstance(values, list) or len(values) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.29 gold row denominator drifted")
    expected_keys = {
        "index",
        "opaque_id",
        "clue_sha256",
        "requested_package",
        "endpoint_sha256",
        "package",
        "version",
        "released",
        "requires",
        "response_sha256",
        "response_bytes",
        "http_status",
        "attempts",
        "valid",
    }
    tasks = contract.task_vector()
    endpoints = endpoint_vector()
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping):
            raise RuntimeError("V2.51.29 gold row is not an object")
        row = dict(raw)
        valid = row.get("valid") is True
        if (
            set(row) != expected_keys
            or row.get("index") != index
            or row.get("opaque_id") != tasks[index]["opaque_id"]
            or row.get("clue_sha256")
            != contract.payload_sha256(contract.CLUES[index])
            or row.get("requested_package") != package_vector()[index]
            or row.get("endpoint_sha256")
            != hashlib.sha256(endpoints[index].encode()).hexdigest()
            or row.get("attempts") != 1
            or not isinstance(row.get("response_bytes"), int)
            or int(row["response_bytes"]) < 0
            or not isinstance(row.get("http_status"), int)
            or (
                valid
                and (
                    row.get("http_status") != 200
                    or int(row["response_bytes"]) <= 0
                    or not re.fullmatch(r"[0-9a-f]{64}", str(row.get("response_sha256")))
                    or _normalize_package(row.get("package"))
                    != _normalize_package(package_vector()[index])
                    or not str(row.get("version") or "").strip()
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("released")))
                    or not str(row.get("requires") or "").strip()
                )
            )
            or (
                not valid
                and (
                    row.get("response_sha256") != ""
                    or row.get("response_bytes") != 0
                    or row.get("http_status") != 0
                )
            )
        ):
            raise RuntimeError("V2.51.29 gold row drifted")
        output.append(row)
    return output


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], gold_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    checked = [runner.validate_task_row(row) for row in rows]
    validated_gold = validate_gold_rows(list(gold_rows))
    gold = {str(row["opaque_id"]): row for row in validated_gold}
    expected_ids = [row["opaque_id"] for row in contract.task_vector()]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked] != expected_ids
        or list(gold) != expected_ids
    ):
        raise RuntimeError("V2.51.29 evaluator denominator drifted")
    metric_rows: dict[str, list[dict[str, float | int]]] = {
        arm: [] for arm in contract.ARMS
    }
    invalid = 0
    zero = {
        "exact_table_success": 0,
        "entity_recall": 0.0,
        "row_f1": 0.0,
        "item_f1": 0.0,
        "column_f1": 0.0,
        "composite": 0.0,
    }
    for row in checked:
        gold_row = gold[row["opaque_id"]]
        if gold_row.get("valid") is not True:
            invalid += 1
            for arm in contract.ARMS:
                metric_rows[arm].append(dict(zero))
        else:
            for arm in contract.ARMS:
                metric_rows[arm].append(
                    evaluate_prediction(str(row["predictions"][arm]), gold_row)
                )
    arms: dict[str, Any] = {}
    for arm in contract.ARMS:
        values = metric_rows[arm]
        exact = sum(int(item["exact_table_success"]) for item in values)
        arms[arm] = {
            "tasks": contract.TASK_COUNT,
            "evaluator_valid": contract.TASK_COUNT - invalid,
            "evaluator_invalid_or_not_run": invalid,
            "fallback_tasks": sum(
                not row["model_success"][arm] for row in checked
            ),
            "exact_table_successes": exact,
            "exact_table_accuracy": exact / contract.TASK_COUNT,
            **{
                key: sum(float(item[key]) for item in values) / contract.TASK_COUNT
                for key in METRICS
            },
        }
    delta_keys = (
        "exact_table_successes",
        "exact_table_accuracy",
        *METRICS,
        "evaluator_invalid_or_not_run",
        "fallback_tasks",
    )
    delta = {
        key: arms[contract.CANDIDATE_ARM][key] - arms[contract.CONTROL_ARM][key]
        for key in delta_keys
    }
    return {
        "arms": arms,
        f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta,
    }


def quality_decision(
    metrics: Mapping[str, Any], mechanism: Mapping[str, Any]
) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    delta = metrics.get(
        f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}"
    ) or {}
    checks = {
        "mechanism_gate_passed": mechanism.get("mechanism_gate_passed") is True,
        "fixed_denominator": all(
            (arms.get(arm) or {}).get("tasks") == contract.TASK_COUNT
            for arm in contract.ARMS
        ),
        "all_gold_tasks_valid": all(
            (arms.get(arm) or {}).get("evaluator_valid") == contract.TASK_COUNT
            for arm in contract.ARMS
        ),
        "candidate_exact_strict_gain": float(
            delta.get("exact_table_successes", -1)
        )
        > 0,
        "entity_nonregression": float(delta.get("entity_recall", -1)) >= 0,
        "row_nonregression": float(delta.get("row_f1", -1)) >= 0,
        "item_nonregression": float(delta.get("item_f1", -1)) >= 0,
        "column_nonregression": float(delta.get("column_f1", -1)) >= 0,
        "composite_nonregression": float(delta.get("composite", -1)) >= 0,
        "evaluator_invalid_nonincrease": float(
            delta.get("evaluator_invalid_or_not_run", 1)
        )
        <= 0,
        "fallback_nonincrease": float(delta.get("fallback_tasks", 1)) <= 0,
        "same_search_fetch_evidence_length_and_effective_model_budget": all(
            mechanism.get("checks", {}).get(name) is True
            for name in (
                "exact_physical_query_budget",
                "physical_fetch_cap_preserved",
                "effective_arm_model_budgets_exact_and_equal",
                "evidence_lengths_equal",
            )
        ),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "causal_salience_external_quality_gate_go": passed,
        "full220_successor_build_authorized": passed,
        "deepwidebench_dev64_exact220_launch_authorized": False,
        "leaderboard_or_sota_authorized": False,
    }


def run_evaluation() -> dict[str, Any]:
    _clean_pushed()
    evaluator_protocol = validate_evaluator_protocol(
        _read(contract.EVALUATOR_PROTOCOL, tracked=True)
    )
    protocol, forward, audit, rows = _validate_forward_parents()
    future = (contract.POSTFREEZE_GOLD, contract.RESULT, contract.POSTAUDIT)
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.51.29 evaluator result surface is not pristine")
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner=EVALUATOR_LEASE_OWNER,
        purpose=EVALUATOR_LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
            raise RuntimeError("V2.51.29 evaluator surface changed after lease")
        if contract.watcher_snapshot() != protocol["protected_watchers"]:
            raise RuntimeError("V2.51.29 protected watcher identity drifted")
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            gold_rows = list(pool.map(_fetch_gold, range(contract.TASK_COUNT)))
        gold_rows.sort(key=lambda row: int(row["index"]))
        gold_rows = validate_gold_rows(gold_rows)
        snapshot = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25129_postfreeze_pypi_gold_snapshot",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "prediction_freeze_sha256": contract.sha256(
                    ROOT / contract.PREDICTION_FREEZE
                ),
                "clue_vector_sha256": evaluator_protocol["population"][
                    "clue_vector_sha256"
                ],
                "package_vector_sha256": evaluator_protocol["population"][
                    "package_vector_sha256"
                ],
                "endpoint_vector_sha256": evaluator_protocol["population"][
                    "endpoint_vector_sha256"
                ],
                "rows": gold_rows,
                "valid_rows": sum(bool(row["valid"]) for row in gold_rows),
                "attempts": sum(int(row["attempts"]) for row in gold_rows),
                "one_call_per_endpoint_no_redirect_retry_or_refetch": True,
                "same_snapshot_for_both_frozen_arms": True,
                "created_only_after_prediction_freeze_and_pushed_forward_audit": True,
            },
            "snapshot_payload_sha256",
        )
        metrics = evaluate_rows(rows, gold_rows)
        decision = quality_decision(metrics, audit["mechanism_decision"])
        _publish(ROOT / contract.POSTFREEZE_GOLD, snapshot)
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25129_causal_salience_external_quality_result",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "status": (
                    "causal_salience_external_quality_gate_go"
                    if decision["causal_salience_external_quality_gate_go"]
                    else "causal_salience_external_quality_gate_no_go"
                ),
                "passed": decision["causal_salience_external_quality_gate_go"],
                "evaluator_protocol_sha256": contract.sha256(
                    ROOT / contract.EVALUATOR_PROTOCOL
                ),
                "forward_result_sha256": contract.sha256(
                    ROOT / contract.FORWARD_RESULT
                ),
                "forward_audit_sha256": contract.sha256(
                    ROOT / contract.FORWARD_AUDIT
                ),
                "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
                "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
                "gold_snapshot_sha256": contract.sha256(
                    ROOT / contract.POSTFREEZE_GOLD
                ),
                "evaluation_wall_seconds": round(
                    max(0.0, time.monotonic() - started), 6
                ),
                "metrics": metrics,
                "mechanism": audit["mechanism_decision"],
                "decision": decision,
                "fixed_denominator_failure_as_zero": True,
                "claim_scope": {
                    "benchmark_external_matched_quality_measured": True,
                    "deepwidebench_quality_measured": False,
                    "entropy_or_information_gain_credit_validated": False,
                    "leaderboard_or_sota_supported": False,
                },
                "authorization": {
                    "full220_successor_build": decision[
                        "full220_successor_build_authorized"
                    ],
                    "deepwidebench_dev64_exact220_launch": False,
                    "retry_refetch_selective_revaluation": False,
                    "leaderboard_or_sota": False,
                },
            },
            "result_payload_sha256",
        )
        _publish(ROOT / contract.RESULT, value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    decision = quality_decision(
        copied.get("metrics") or {}, copied.get("mechanism") or {}
    )
    if (
        copied.get("role") != "v25129_causal_salience_external_quality_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("decision") != decision
        or copied.get("passed")
        is not decision["causal_salience_external_quality_gate_go"]
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get("authorization", {}).get("deepwidebench_dev64_exact220_launch")
        is not False
        or copied.get("authorization", {}).get(
            "retry_refetch_selective_revaluation"
        )
        is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.51.29 evaluator result drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    evaluator_protocol = validate_evaluator_protocol(
        _read(contract.EVALUATOR_PROTOCOL, tracked=True)
    )
    protocol, _forward, audit, rows = _validate_forward_parents()
    result = validate_result(_read(contract.RESULT, tracked=True))
    snapshot = _read(contract.POSTFREEZE_GOLD, tracked=True)
    try:
        validated_gold = validate_gold_rows(snapshot.get("rows"))
        gold_rows_valid = True
    except RuntimeError:
        validated_gold = []
        gold_rows_valid = False
    recomputed_metrics = (
        evaluate_rows(rows, validated_gold) if gold_rows_valid else {"invalid": True}
    )
    checks = {
        "evaluator_protocol_valid": True,
        "result_valid": True,
        "gold_snapshot_sealed": contract.sealed(snapshot, "snapshot_payload_sha256"),
        "gold_rows_validate": gold_rows_valid,
        "gold_snapshot_file_hash_bound": result.get("gold_snapshot_sha256")
        == contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
        "gold_snapshot_bound_to_prediction_freeze": snapshot.get(
            "prediction_freeze_sha256"
        )
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "clue_package_endpoint_vectors_hash_bound": snapshot.get(
            "clue_vector_sha256"
        )
        == evaluator_protocol["population"]["clue_vector_sha256"]
        and snapshot.get("package_vector_sha256")
        == evaluator_protocol["population"]["package_vector_sha256"]
        and snapshot.get("endpoint_vector_sha256")
        == evaluator_protocol["population"]["endpoint_vector_sha256"],
        "exactly_one_attempt_per_endpoint": snapshot.get("attempts")
        == contract.TASK_COUNT
        and len(validated_gold) == contract.TASK_COUNT
        and all(row.get("attempts") == 1 for row in validated_gold),
        "valid_row_count_recomputes": snapshot.get("valid_rows")
        == sum(bool(row["valid"]) for row in validated_gold),
        "same_gold_snapshot_for_both_arms": snapshot.get(
            "same_snapshot_for_both_frozen_arms"
        )
        is True,
        "metrics_recompute_exactly": result.get("metrics") == recomputed_metrics,
        "decision_recomputes_exactly": result.get("decision")
        == quality_decision(recomputed_metrics, audit["mechanism_decision"]),
        "fixed_denominator_failure_as_zero": result.get(
            "fixed_denominator_failure_as_zero"
        )
        is True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "no_retry_refetch_or_selective_revaluation": result.get(
            "authorization", {}
        ).get("retry_refetch_selective_revaluation")
        is False,
        "no_deepwidebench_launch_leaderboard_or_sota_authority": result.get(
            "authorization", {}
        ).get("deepwidebench_dev64_exact220_launch")
        is False
        and result.get("authorization", {}).get("leaderboard_or_sota") is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    quality_go = not findings and result["passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v25129_causal_salience_external_quality_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "evaluator_protocol_sha256": contract.sha256(
            ROOT / contract.EVALUATOR_PROTOCOL
        ),
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "gold_snapshot_sha256": contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "causal_salience_external_quality_gate_go": quality_go,
        "authorization": {
            "full220_successor_build": quality_go,
            "deepwidebench_dev64_exact220_launch": False,
            "retry_refetch_selective_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = validate_evaluator_protocol(build_evaluator_protocol())
        path = contract.EVALUATOR_PROTOCOL
        _publish(ROOT / path, value)
    elif args.command == "evaluate":
        value = run_evaluation()
        path = contract.RESULT
    else:
        value = build_postaudit()
        if value["findings"]:
            raise RuntimeError(value["findings"])
        path = contract.POSTAUDIT
        _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "status": value.get("status"),
                "passed": value.get("passed"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
