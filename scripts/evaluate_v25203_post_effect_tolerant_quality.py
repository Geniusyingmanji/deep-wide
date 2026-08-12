#!/usr/bin/env python3
"""Post-freeze CRAN evaluator for the V2.52.03 quality gate.

This evaluator-only module was created after the prediction freeze and
content-free forward audit were committed and pushed.  It downloads exactly
one official CRAN PACKAGES.gz snapshot, extracts the twenty already-frozen
visible package identities, and scores both frozen arms against that same
snapshot.  Gold and quality outcomes cannot feed back into the forward.
"""

from __future__ import annotations

import argparse
import ast
import copy
import fcntl
import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25177_quote_aware_pipe_normalizer as public_loader,
)
from deepwide_agent import (  # noqa: E402
    v25203_post_effect_tolerant_quality_contract as contract,
)
from scripts import run_v25203_post_effect_tolerant_quality as runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TEST = contract.EVALUATOR_TEST
GOLD_ENDPOINT = "https://cran.r-project.org/src/contrib/PACKAGES.gz"
MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 128 * 1024 * 1024
GOLD_CONNECT_TIMEOUT_SECONDS = 5.0
GOLD_READ_TIMEOUT_SECONDS = 60.0
EVALUATOR_LEASE_OWNER = "v25203_post_effect_tolerant_quality_evaluator_v1"
EVALUATOR_LEASE_PURPOSE = "single_postfreeze_cran_snapshot_quality_gate_v1"
METRICS = ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.52.03 evaluator requires clean pushed HEAD")


def _read(relative: Path, *, tracked: bool) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.03 evaluator expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.52.03 evaluator expected JSONL objects")
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
    values = tuple(contract.PACKAGES)
    if len(values) != contract.TASK_COUNT or len(set(values)) != len(values):
        raise RuntimeError("V2.52.03 evaluator package vector drifted")
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
    sidecar = runner.validate_compatibility_aggregate(
        _read(contract.COMPATIBILITY_AGGREGATE, tracked=True)
    )
    expected_ids = [row["opaque_id"] for row in contract.task_vector()]
    if (
        audit.get("role")
        != "v25203_post_effect_tolerant_quality_forward_audit"
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
        or audit.get("compatibility_aggregate_sha256")
        != contract.sha256(ROOT / contract.COMPATIBILITY_AGGREGATE)
        or audit.get("mechanism_decision") != forward.get("mechanism_decision")
        or audit.get("authorization", {}).get(
            "postfreeze_evaluator_implementation_and_protocol"
        )
        is not True
        or audit.get("mechanism_decision", {}).get(
            "same_response_mechanism_gate_passed"
        )
        is not True
        or not contract.sealed(audit, "audit_payload_sha256")
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or freeze.get("role")
        != "v25203_post_effect_tolerant_quality_prediction_freeze"
        or freeze.get("protocol_id") != contract.PROTOCOL_ID
        or freeze.get("task_rows_sha256")
        != contract.sha256(ROOT / contract.TASK_ROWS)
        or freeze.get("compatibility_aggregate_sha256")
        != contract.sha256(ROOT / contract.COMPATIBILITY_AGGREGATE)
        or freeze.get(
            "all_predictions_terminal_before_gold_evaluator_or_quality_decision"
        )
        is not True
        or [row["opaque_id"] for row in rows] != expected_ids
        or sidecar["task_count"] != contract.TASK_COUNT
        or protocol.get("protected_watchers") != contract.watcher_snapshot()
    ):
        raise RuntimeError("V2.52.03 evaluator parent barrier failed")
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
            key: object | None = None
            if isinstance(child, ast.Subscript) and isinstance(
                child.slice, ast.Constant
            ):
                key = child.slice.value
            elif (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "get"
                and child.args
                and isinstance(child.args[0], ast.Constant)
            ):
                key = child.args[0].value
            if isinstance(key, str) and key in privileged_fields:
                privileged_accesses.append(
                    {"function": node.name, "field": key}
                )
    test_count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(test_tree)
    )
    checks = {
        "evaluator_and_test_are_ordinary": True,
        "network_capability_only_in_fetch_gold_snapshot": request_calls
        == [{"function": "_fetch_gold_snapshot", "method": "get"}],
        "credential_literal_zero": not contract.SECRET.search(
            source_text + test_text
        ),
        "independent_test_count_at_least_nine": test_count >= 9,
        "privileged_benchmark_field_access_zero": not privileged_accesses,
        "runner_capability_limited_to_frozen_validation": runner_attributes
        <= {
            "validate_forward_result",
            "validate_task_row",
            "validate_compatibility_aggregate",
        },
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
        "candidate_exact_successes_at_least_ten": True,
        "candidate_exact_gain_at_least_ten": True,
        "candidate_entity_row_item_column_composite_nonregression": True,
    }


def build_evaluator_protocol(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_implementation_tracked: bool = True,
) -> dict[str, Any]:
    if require_clean:
        _clean_pushed()
    protocol, _forward, audit, rows = _validate_forward_parents()
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
        raise RuntimeError("V2.52.03 evaluator surface is not pristine")
    if not implementation["audit_valid"]:
        raise RuntimeError(
            "V2.52.03 evaluator implementation audit failed: "
            + repr(implementation["findings"])
        )
    if audit["mechanism_decision"].get(
        "same_response_mechanism_gate_passed"
    ) is not True:
        raise RuntimeError("V2.52.03 mechanism gate withheld evaluator authority")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25203_post_effect_tolerant_quality_evaluator_preregistration",
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
            "compatibility_aggregate_sha256": contract.sha256(
                ROOT / contract.COMPATIBILITY_AGGREGATE
            ),
            "evaluator_sha256": implementation["evaluator_sha256"],
            "evaluator_test_sha256": implementation["test_sha256"],
        },
        "population": {
            "fixed_denominator": contract.TASK_COUNT,
            "prediction_rows": len(rows),
            "package_vector_sha256": contract.payload_sha256(package_vector()),
        },
        "evaluation": {
            "gold_endpoint_sha256": hashlib.sha256(
                GOLD_ENDPOINT.encode()
            ).hexdigest(),
            "exact_http_get_calls": 1,
            "redirects": 0,
            "retries_refetches_or_selective_revaluation": 0,
            "maximum_compressed_bytes": MAX_COMPRESSED_BYTES,
            "maximum_decompressed_bytes": MAX_DECOMPRESSED_BYTES,
            "same_postfreeze_snapshot_for_both_arms": True,
            "fixed_denominator_failure_as_zero": True,
            "metrics": ["exact_table_successes", "exact_table_accuracy", *METRICS],
            "gold_rule": {
                "source": "official_cran_src_contrib_PACKAGES_gz",
                "record_parser": "strict_unique_dcf_record_with_continuation_unfolding",
                "fields": list(contract.COLUMNS),
                "all_twenty_records_required": True,
            },
            "quality_rule": quality_rule(),
        },
        "implementation_audit": implementation,
        "protected_watchers": protocol["protected_watchers"],
        "source_policy": {
            "created_only_after_pushed_prediction_freeze_and_forward_audit": True,
            "forward_files_are_read_only": True,
            "one_fixed_official_cran_snapshot_only": True,
            "gold_or_evaluator_feedback_to_forward": False,
            "category_question_type_split_or_deepwidebench_gold_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "one_postfreeze_external_evaluation": True,
            "retry_refetch_selective_revaluation": False,
            "deepwidebench_exact220_only_after_pushed_postresult_audit_go": True,
            "deepwidebench_dev64_exact220_leaderboard_or_sota_now": False,
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
        "deepwidebench_exact220_only_after_pushed_postresult_audit_go": True,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_now": False,
    }
    if (
        copied.get("role")
        != "v25203_post_effect_tolerant_quality_evaluator_preregistration"
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
        or parents.get("compatibility_aggregate_sha256")
        != contract.sha256(ROOT / contract.COMPATIBILITY_AGGREGATE)
        or parents.get("evaluator_sha256") != implementation["evaluator_sha256"]
        or parents.get("evaluator_test_sha256") != implementation["test_sha256"]
        or population.get("fixed_denominator") != contract.TASK_COUNT
        or population.get("prediction_rows") != contract.TASK_COUNT
        or population.get("package_vector_sha256")
        != contract.payload_sha256(package_vector())
        or evaluation.get("gold_endpoint_sha256")
        != hashlib.sha256(GOLD_ENDPOINT.encode()).hexdigest()
        or evaluation.get("exact_http_get_calls") != 1
        or evaluation.get("redirects") != 0
        or evaluation.get("retries_refetches_or_selective_revaluation") != 0
        or evaluation.get("same_postfreeze_snapshot_for_both_arms") is not True
        or evaluation.get("fixed_denominator_failure_as_zero") is not True
        or evaluation.get("quality_rule") != quality_rule()
        or copied.get("implementation_audit") != implementation
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "evaluator_protocol_payload_sha256")
    ):
        raise RuntimeError("V2.52.03 evaluator protocol drifted")
    return copied


def _collapse(value: object) -> str:
    return " ".join(str(value).split())


def _normalize_identity(value: object) -> str:
    return _collapse(value).casefold()


def _normalize_value(value: object) -> str:
    collapsed = _collapse(value).strip('"')
    collapsed = re.sub(r"\s*\|\s*", "|", collapsed)
    return collapsed.casefold()


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    values = public_loader._public_loader_like_values(str(text))
    if not values or values[0] != list(contract.COLUMNS):
        return [], []
    rows = [row for row in values[1:] if len(row) == len(contract.COLUMNS)]
    if len(rows) != len(values) - 1:
        return [], []
    return values[0], rows


def evaluate_prediction(
    prediction: str, gold: Mapping[str, Any]
) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    exact_columns = columns == list(contract.COLUMNS)
    selected = rows if exact_columns else []
    expected = _normalize_identity(gold["package"])
    predicted = {
        _normalize_identity(row[0]): row
        for row in selected
        if _normalize_identity(row[0])
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
            _normalize_value(row[2]) == _normalize_value(gold["license"])
        )
        correct_items += int(
            _normalize_value(row[3])
            == _normalize_value(gold["needs_compilation"])
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


def _decompress_capped(raw: bytes) -> bytes:
    chunks: list[bytes] = []
    size = 0
    with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as source:
        while True:
            chunk = source.read(1 << 20)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_DECOMPRESSED_BYTES:
                raise ValueError("V2.52.03 CRAN snapshot exceeds decompressed cap")
            chunks.append(chunk)
    return b"".join(chunks)


def parse_dcf_records(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}
    last_key: str | None = None
    for raw in str(text).replace("\r\n", "\n").split("\n"):
        if not raw.strip():
            if current:
                records.append(current)
                current = {}
                last_key = None
            continue
        if raw[:1].isspace():
            if last_key is None:
                raise ValueError("V2.52.03 orphan DCF continuation")
            current[last_key] = _collapse(current[last_key] + " " + raw.strip())
            continue
        if ":" not in raw:
            raise ValueError("V2.52.03 malformed DCF field")
        key, value = raw.split(":", 1)
        key = key.strip()
        if (
            not key
            or key in current
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]*", key) is None
        ):
            raise ValueError("V2.52.03 duplicate or invalid DCF key")
        current[key] = value.strip()
        last_key = key
    if current:
        records.append(current)
    return records


def _invalid_gold_rows() -> list[dict[str, Any]]:
    return [
        {
            "index": index,
            "opaque_id": contract.task_vector()[index]["opaque_id"],
            "requested_package": package,
            "package": package,
            "version": "Unknown",
            "license": "Unknown",
            "needs_compilation": "Unknown",
            "valid": False,
        }
        for index, package in enumerate(package_vector())
    ]


def _extract_gold_rows(records: Sequence[Mapping[str, str]]) -> list[dict[str, Any]]:
    by_package: dict[str, list[Mapping[str, str]]] = {}
    for record in records:
        package = str(record.get("Package") or "")
        by_package.setdefault(package, []).append(record)
    output: list[dict[str, Any]] = []
    for index, package in enumerate(package_vector()):
        matches = by_package.get(package, [])
        if len(matches) != 1:
            raise ValueError("V2.52.03 CRAN package record is not unique")
        record = matches[0]
        values = {
            "package": str(record.get("Package") or "").strip(),
            "version": _collapse(record.get("Version") or ""),
            "license": _collapse(record.get("License") or ""),
            "needs_compilation": _collapse(
                record.get("NeedsCompilation") or ""
            ),
        }
        if (
            values["package"] != package
            or any(
                not value
                or len(value) > 5000
                or any(char in value for char in "\r\n\x00")
                for value in values.values()
            )
        ):
            raise ValueError("V2.52.03 CRAN gold field invalid")
        output.append(
            {
                "index": index,
                "opaque_id": contract.task_vector()[index]["opaque_id"],
                "requested_package": package,
                **values,
                "valid": True,
            }
        )
    return output


def _fetch_gold_snapshot() -> dict[str, Any]:
    rows = _invalid_gold_rows()
    status = 0
    raw = b""
    decoded = b""
    try:
        with requests.get(
            GOLD_ENDPOINT,
            headers={
                "User-Agent": "DeepWideResearch/1.0 (+v25203-postfreeze-evaluator)"
            },
            timeout=(GOLD_CONNECT_TIMEOUT_SECONDS, GOLD_READ_TIMEOUT_SECONDS),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            if status != 200 or str(response.url) != GOLD_ENDPOINT:
                raise ValueError("V2.52.03 CRAN endpoint identity drifted")
            response.raise_for_status()
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_COMPRESSED_BYTES:
                    raise ValueError("V2.52.03 CRAN snapshot exceeds compressed cap")
                chunks.append(bytes(chunk))
            raw = b"".join(chunks)
        decoded = _decompress_capped(raw)
        text = decoded.decode("utf-8")
        rows = _extract_gold_rows(parse_dcf_records(text))
    except Exception:
        rows = _invalid_gold_rows()
        raw = b""
        decoded = b""
        status = 0
    return {
        "endpoint_sha256": hashlib.sha256(GOLD_ENDPOINT.encode()).hexdigest(),
        "response_sha256": hashlib.sha256(raw).hexdigest() if raw else "",
        "response_bytes": len(raw),
        "decompressed_sha256": (
            hashlib.sha256(decoded).hexdigest() if decoded else ""
        ),
        "decompressed_bytes": len(decoded),
        "http_status": status,
        "attempts": 1,
        "rows": rows,
        "valid_rows": sum(bool(row["valid"]) for row in rows),
    }


def validate_gold_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("snapshot_payload_sha256", None)
    expected_keys = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "prediction_freeze_sha256",
        "package_vector_sha256",
        "endpoint_sha256",
        "response_sha256",
        "response_bytes",
        "decompressed_sha256",
        "decompressed_bytes",
        "http_status",
        "attempts",
        "rows",
        "valid_rows",
        "single_call_no_redirect_retry_refetch_or_selective_revaluation",
        "same_snapshot_for_both_frozen_arms",
        "created_only_after_prediction_freeze_and_pushed_forward_audit",
        "snapshot_payload_sha256",
    }
    rows = copied.get("rows")
    row_keys = {
        "index",
        "opaque_id",
        "requested_package",
        "package",
        "version",
        "license",
        "needs_compilation",
        "valid",
    }
    if not isinstance(rows, list) or len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.52.03 gold snapshot denominator drifted")
    valid_rows = 0
    tasks = contract.task_vector()
    packages = package_vector()
    for index, raw_row in enumerate(rows):
        if not isinstance(raw_row, Mapping):
            raise RuntimeError("V2.52.03 gold snapshot row is not an object")
        row = dict(raw_row)
        valid = row.get("valid") is True
        if (
            set(row) != row_keys
            or row.get("index") != index
            or row.get("opaque_id") != tasks[index]["opaque_id"]
            or row.get("requested_package") != packages[index]
            or not isinstance(row.get("valid"), bool)
            or (valid and row.get("package") != packages[index])
            or any(
                not isinstance(row.get(name), str)
                or not str(row[name])
                or any(char in str(row[name]) for char in "\r\n\x00")
                for name in (
                    "package",
                    "version",
                    "license",
                    "needs_compilation",
                )
            )
            or (
                not valid
                and any(
                    row.get(name) != "Unknown"
                    for name in ("version", "license", "needs_compilation")
                )
            )
        ):
            raise RuntimeError("V2.52.03 gold snapshot row drifted")
        valid_rows += int(valid)
    response_valid = valid_rows == contract.TASK_COUNT
    if (
        set(copied) != expected_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25203_postfreeze_cran_gold_snapshot"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or copied.get("package_vector_sha256")
        != contract.payload_sha256(packages)
        or copied.get("endpoint_sha256")
        != hashlib.sha256(GOLD_ENDPOINT.encode()).hexdigest()
        or copied.get("attempts") != 1
        or copied.get("valid_rows") != valid_rows
        or not isinstance(copied.get("response_bytes"), int)
        or not isinstance(copied.get("decompressed_bytes"), int)
        or copied["response_bytes"] < 0
        or copied["decompressed_bytes"] < 0
        or copied["response_bytes"] > MAX_COMPRESSED_BYTES
        or copied["decompressed_bytes"] > MAX_DECOMPRESSED_BYTES
        or (
            response_valid
            and (
                copied.get("http_status") != 200
                or copied["response_bytes"] <= 0
                or copied["decompressed_bytes"] <= 0
                or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("response_sha256")))
                is None
                or re.fullmatch(
                    r"[0-9a-f]{64}", str(copied.get("decompressed_sha256"))
                )
                is None
            )
        )
        or (
            not response_valid
            and (
                copied.get("http_status") != 0
                or copied.get("response_sha256") != ""
                or copied.get("response_bytes") != 0
                or copied.get("decompressed_sha256") != ""
                or copied.get("decompressed_bytes") != 0
            )
        )
        or any(
            copied.get(name) is not True
            for name in (
                "single_call_no_redirect_retry_refetch_or_selective_revaluation",
                "same_snapshot_for_both_frozen_arms",
                "created_only_after_prediction_freeze_and_pushed_forward_audit",
            )
        )
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.52.03 gold snapshot drifted")
    return copied


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    checked = [runner.validate_task_row(row) for row in rows]
    gold_snapshot = validate_gold_snapshot(snapshot)
    gold = {str(row["opaque_id"]): row for row in gold_snapshot["rows"]}
    expected_ids = [row["opaque_id"] for row in contract.task_vector()]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked] != expected_ids
        or set(gold) != set(expected_ids)
    ):
        raise RuntimeError("V2.52.03 evaluator identity denominator drifted")
    per_arm: dict[str, list[dict[str, float | int]]] = {
        arm: [] for arm in contract.ARMS
    }
    for row in checked:
        gold_row = gold[str(row["opaque_id"])]
        for arm in contract.ARMS:
            per_arm[arm].append(
                evaluate_prediction(str(row["predictions"][arm]), gold_row)
                if gold_row["valid"]
                else {
                    "exact_table_success": 0,
                    **{name: 0.0 for name in METRICS},
                }
            )
    invalid = contract.TASK_COUNT - int(gold_snapshot["valid_rows"])
    arms: dict[str, Any] = {}
    for arm in contract.ARMS:
        values = per_arm[arm]
        exact = sum(int(item["exact_table_success"]) for item in values)
        arms[arm] = {
            "tasks": contract.TASK_COUNT,
            "evaluator_valid": contract.TASK_COUNT - invalid,
            "evaluator_invalid_or_not_run": invalid,
            "fallback_tasks": sum(
                row["prediction_kind"] != "model_generated" for row in checked
            ),
            "exact_table_successes": exact,
            "exact_table_accuracy": exact / contract.TASK_COUNT,
            **{
                name: sum(float(item[name]) for item in values)
                / contract.TASK_COUNT
                for name in METRICS
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
        key: arms[contract.CANDIDATE_ARM][key]
        - arms[contract.CONTROL_ARM][key]
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
    control = arms.get(contract.CONTROL_ARM) or {}
    candidate = arms.get(contract.CANDIDATE_ARM) or {}
    delta = metrics.get(
        f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}"
    ) or {}
    checks = {
        "mechanism_gate_passed": mechanism.get(
            "same_response_mechanism_gate_passed"
        )
        is True,
        "fixed_denominator_all_valid": all(
            (arms.get(arm) or {}).get("tasks") == contract.TASK_COUNT
            and (arms.get(arm) or {}).get("evaluator_valid")
            == contract.TASK_COUNT
            for arm in contract.ARMS
        ),
        "candidate_exact_successes_at_least_ten": int(
            candidate.get("exact_table_successes", -1)
        )
        >= contract.quality_gate()["minimum_candidate_exact_successes"],
        "candidate_exact_gain_at_least_ten": float(
            delta.get("exact_table_successes", -1)
        )
        >= contract.quality_gate()["minimum_candidate_exact_gain"],
        "candidate_exact_strictly_greater": float(
            candidate.get("exact_table_successes", -1)
        )
        > float(control.get("exact_table_successes", -1)),
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
        "positive_signed_credit_zero": mechanism.get("checks", {}).get(
            "positive_signed_credit_zero"
        )
        is True,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "post_effect_tolerant_quality_gate_go": passed,
        "deepwidebench_exact220_build_authorized": passed,
        "deepwidebench_exact220_launch_authorized_now": False,
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
        raise RuntimeError("V2.52.03 evaluator result surface is not pristine")
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        ROOT,
        owner=EVALUATOR_LEASE_OWNER,
        purpose=EVALUATOR_LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
            raise RuntimeError("V2.52.03 evaluator surface changed after lease")
        if contract.watcher_snapshot() != protocol["protected_watchers"]:
            raise RuntimeError("V2.52.03 protected watcher identity drifted")
        fetched = _fetch_gold_snapshot()
        snapshot = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25203_postfreeze_cran_gold_snapshot",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "prediction_freeze_sha256": contract.sha256(
                    ROOT / contract.PREDICTION_FREEZE
                ),
                "package_vector_sha256": evaluator_protocol["population"][
                    "package_vector_sha256"
                ],
                **fetched,
                "single_call_no_redirect_retry_refetch_or_selective_revaluation": True,
                "same_snapshot_for_both_frozen_arms": True,
                "created_only_after_prediction_freeze_and_pushed_forward_audit": True,
            },
            "snapshot_payload_sha256",
        )
        snapshot = validate_gold_snapshot(snapshot)
        metrics = evaluate_rows(rows, snapshot)
        decision = quality_decision(metrics, audit["mechanism_decision"])
        _publish(ROOT / contract.POSTFREEZE_GOLD, snapshot)
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25203_post_effect_tolerant_quality_result",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "status": (
                    "post_effect_tolerant_quality_gate_go"
                    if decision["post_effect_tolerant_quality_gate_go"]
                    else "post_effect_tolerant_quality_gate_no_go"
                ),
                "passed": decision["post_effect_tolerant_quality_gate_go"],
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
                    "deepwidebench_exact220_build": decision[
                        "deepwidebench_exact220_build_authorized"
                    ],
                    "deepwidebench_exact220_launch_now": False,
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
        copied.get("role") != "v25203_post_effect_tolerant_quality_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("decision") != decision
        or copied.get("passed")
        is not decision["post_effect_tolerant_quality_gate_go"]
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get("claim_scope", {}).get("deepwidebench_quality_measured")
        is not False
        or copied.get("claim_scope", {}).get(
            "entropy_or_information_gain_credit_validated"
        )
        is not False
        or copied.get("authorization", {}).get(
            "deepwidebench_exact220_launch_now"
        )
        is not False
        or copied.get("authorization", {}).get(
            "retry_refetch_selective_revaluation"
        )
        is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.52.03 evaluator result drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    evaluator_protocol = validate_evaluator_protocol(
        _read(contract.EVALUATOR_PROTOCOL, tracked=True)
    )
    protocol, _forward, audit, rows = _validate_forward_parents()
    result = validate_result(_read(contract.RESULT, tracked=True))
    snapshot = validate_gold_snapshot(_read(contract.POSTFREEZE_GOLD, tracked=True))
    metrics = evaluate_rows(rows, snapshot)
    decision = quality_decision(metrics, audit["mechanism_decision"])
    checks = {
        "evaluator_protocol_valid": True,
        "result_valid": True,
        "gold_snapshot_valid_and_sealed": True,
        "gold_snapshot_file_hash_bound": result.get("gold_snapshot_sha256")
        == contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
        "gold_snapshot_bound_to_prediction_freeze": snapshot.get(
            "prediction_freeze_sha256"
        )
        == evaluator_protocol["parents"]["prediction_freeze_sha256"],
        "package_and_endpoint_hashes_bound": snapshot.get(
            "package_vector_sha256"
        )
        == evaluator_protocol["population"]["package_vector_sha256"]
        and snapshot.get("endpoint_sha256")
        == evaluator_protocol["evaluation"]["gold_endpoint_sha256"],
        "exactly_one_snapshot_attempt": snapshot.get("attempts") == 1,
        "all_twenty_gold_rows_valid": snapshot.get("valid_rows")
        == contract.TASK_COUNT,
        "metrics_recompute_exactly": metrics == result["metrics"],
        "quality_decision_recomputes_exactly": decision == result["decision"],
        "fixed_denominator_failure_as_zero": result[
            "fixed_denominator_failure_as_zero"
        ]
        is True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "no_retry_refetch_or_selective_revaluation": result["authorization"][
            "retry_refetch_selective_revaluation"
        ]
        is False,
        "no_leaderboard_or_sota_authority": result["authorization"][
            "leaderboard_or_sota"
        ]
        is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    quality_go = not findings and result["passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v25203_post_effect_tolerant_quality_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "evaluator_protocol_sha256": contract.sha256(
            ROOT / contract.EVALUATOR_PROTOCOL
        ),
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "gold_snapshot_sha256": contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
        "metrics": metrics,
        "decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "post_effect_tolerant_quality_gate_go": quality_go,
        "source_policy": contract.source_policy(),
        "authorization": {
            "deepwidebench_exact220_build": quality_go,
            "deepwidebench_exact220_launch_after_this_audit_is_pushed": quality_go,
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
