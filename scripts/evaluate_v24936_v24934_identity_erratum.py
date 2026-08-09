#!/usr/bin/env python3
"""Append-only identity evaluator erratum for frozen V2.49.34 predictions.

V2.49.34 predictions render the visible row identity as ``name [ISO3]``.
Its inherited evaluator built gold identities as ``name`` and compared the two
after punctuation stripping, so every otherwise valid row became a different
entity.  This erratum never changes or regenerates a prediction.  It evaluates
the complete frozen 24-task x 2-arm vector once after an explicit protocol is
published, accepting only the two visible renderings ``name`` and
``name [matching ISO3]`` as the same canonical entity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24934_contextual_record_external_contract as contract  # noqa: E402
from scripts import evaluate_v24923_target_value_external as frozen_base  # noqa: E402


DATE = "20260809"
ROLE_PREFIX = "v24936_v24934_identity_evaluator_erratum"
INVALID_AUDIT = Path(
    "results/DO_NOT_USE_invalid_v24934_evaluator_identity_mismatch_20260809/"
    "invalid_run_audit.json"
)
PROTOCOL = Path(
    f"results/{ROLE_PREFIX}_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/{ROLE_PREFIX}_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/{ROLE_PREFIX}_postresult_audit_v1_{DATE}.json")
SOURCE = Path("scripts/evaluate_v24936_v24934_identity_erratum.py")
TEST = Path("tests/test_v24936_v24934_identity_erratum.py")
ORIGINAL_RESULT = contract.RESULT
ORIGINAL_POSTAUDIT = contract.POSTAUDIT
ORIGINAL_EVALUATOR_PROTOCOL = contract.EVALUATOR_PROTOCOL
OBSERVATION = re.compile(r"^(.+?)\s+\[([A-Z]{3})\]:\s*(\S.*)$")
TAGGED_IDENTITY = re.compile(r"^(.+?)\s+\[([A-Z]{3})\]\s*$")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _read(path: Path) -> dict[str, Any]:
    absolute = path if path.is_absolute() else ROOT / path
    if (
        absolute.is_symlink()
        or not absolute.is_file()
        or not absolute.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.36 expected ordinary object: {path}")
    value = json.loads(absolute.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.36 expected JSON object")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    absolute = path if path.is_absolute() else ROOT / path
    if absolute.is_symlink() or not absolute.is_file():
        raise RuntimeError("V2.49.36 expected ordinary JSONL")
    rows = [
        json.loads(line)
        for line in absolute.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.49.36 expected JSONL objects")
    return rows


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    absolute = ROOT / path
    if absolute.exists() or absolute.is_symlink():
        raise FileExistsError(path)
    absolute.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        absolute, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.36 requires clean pushed HEAD")


def _tracked(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    return frozen_base._matrix(text)


def canonical_visible_identity(
    rendered: str, entities: Sequence[tuple[str, str]]
) -> str | None:
    """Map only exact visible name or name+matching-code aliases."""

    key = _norm(rendered)
    matches = {
        _norm(name)
        for name, iso3 in entities
        if key in {_norm(name), _norm(f"{name} [{iso3}]")}
    }
    return next(iter(matches)) if len(matches) == 1 else None


def build_gold(
    tasks: Sequence[Mapping[str, Any]], pages: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    raw_pages = pages.get("pages")
    if not isinstance(raw_pages, list) or len(raw_pages) != len(contract.TARGETS):
        raise RuntimeError("V2.49.36 evaluator page vector drifted")
    page_values: list[dict[str, str]] = []
    for page in raw_pages:
        if not isinstance(page, Mapping):
            raise RuntimeError("V2.49.36 evaluator page drifted")
        values: dict[str, str] = {}
        for line in str(page.get("content", "")).splitlines():
            match = OBSERVATION.match(line.strip())
            if match is not None and match.group(2) not in values:
                values[match.group(2)] = match.group(3).strip()
        if len(values) < 170:
            raise RuntimeError("V2.49.36 evaluator observation capacity drifted")
        page_values.append(values)
    output: dict[str, dict[str, Any]] = {}
    for task in contract.validate_task_vector(tasks):
        entities = contract.parse_visible_entities(task["question"])
        output[task["opaque_id"]] = {
            "entities": [list(item) for item in entities],
            "rows": [
                {
                    "Country": name,
                    **{
                        contract.visible_columns()[index + 1]: page_values[index][iso3]
                        for index in range(len(contract.TARGETS))
                    },
                }
                for name, iso3 in entities
            ],
        }
    return output


def evaluate_prediction(
    prediction: str,
    gold: Sequence[Mapping[str, str]],
    entities: Sequence[tuple[str, str]],
) -> dict[str, float | int]:
    expected_columns = contract.visible_columns()
    columns, rows = _matrix(prediction)
    if columns != expected_columns:
        rows = []
    expected = {_norm(row["Country"]): row for row in gold}
    predicted: dict[str, list[str]] = {}
    duplicate_identities = 0
    for row in rows:
        if len(row) != len(columns):
            continue
        canonical = canonical_visible_identity(row[0], entities)
        if canonical is None:
            continue
        if canonical in predicted:
            duplicate_identities += 1
            continue
        predicted[canonical] = row
    true_entities = len(set(expected) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(expected)
    row_f1 = (
        2 * precision * recall / (precision + recall) if precision + recall else 0.0
    )
    item_true = 0
    for key, row in predicted.items():
        if key not in expected:
            continue
        item_true += sum(
            _numeric_equal(row[index], expected[key][columns[index]])
            for index in range(1, len(columns))
        )
    predicted_items = len(predicted) * len(contract.TARGETS)
    gold_items = len(expected) * len(contract.TARGETS)
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    exact = int(
        duplicate_identities == 0
        and len(rows) == len(expected)
        and len(predicted) == len(expected)
        and true_entities == len(expected)
        and item_true == gold_items
    )
    column_f1 = 1.0 if columns == expected_columns else 0.0
    return {
        "exact_table_success": exact,
        "entity_recall": recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": (recall + row_f1 + item_f1 + column_f1) / 4,
    }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], gold: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    values: dict[str, list[dict[str, float | int]]] = {
        arm: [] for arm in contract.ARMS
    }
    seen: set[str] = set()
    for row in rows:
        opaque = str(row.get("opaque_id", ""))
        predictions = row.get("predictions")
        if (
            opaque in seen
            or opaque not in gold
            or not isinstance(predictions, Mapping)
            or set(predictions) != set(contract.ARMS)
        ):
            raise RuntimeError("V2.49.36 prediction row drifted")
        seen.add(opaque)
        bundle = gold[opaque]
        entities = [tuple(item) for item in bundle["entities"]]
        for arm in contract.ARMS:
            values[arm].append(
                evaluate_prediction(
                    str(predictions[arm]), bundle["rows"], entities
                )
            )
    if len(seen) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.49.36 evaluation denominator drifted")
    aggregate: dict[str, Any] = {}
    for arm, metrics in values.items():
        aggregate[arm] = {
            "tasks": contract.SELECTED_COUNT,
            "exact_table_successes": sum(
                int(row["exact_table_success"]) for row in metrics
            ),
            **{
                key: sum(float(row[key]) for row in metrics)
                / contract.SELECTED_COUNT
                for key in (
                    "entity_recall",
                    "row_f1",
                    "item_f1",
                    "column_f1",
                    "composite",
                )
            },
        }
    delta = {
        key: aggregate["target_value_30k"][key] - aggregate["parent_30k"][key]
        for key in (
            "exact_table_successes",
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
        )
    }
    return {
        "arms": aggregate,
        "contextual_record_30k_minus_unicode_total_30k": delta,
    }


def identity_format_aggregate(
    tasks: Sequence[Mapping[str, Any]], predictions: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    task_map = {
        task["opaque_id"]: contract.parse_visible_entities(task["question"])
        for task in contract.validate_task_vector(tasks)
    }
    output = {
        arm: {
            "tables": 0,
            "rows": 0,
            "exact_visible_name_rows": 0,
            "matching_name_iso3_rows": 0,
            "wrong_iso3_rows": 0,
            "other_rows": 0,
        }
        for arm in contract.ARMS
    }
    seen: set[str] = set()
    for item in predictions:
        opaque = str(item.get("opaque_id", ""))
        arms = item.get("predictions")
        hashes = item.get("prediction_sha256")
        if (
            opaque in seen
            or opaque not in task_map
            or not isinstance(arms, Mapping)
            or set(arms) != set(contract.ARMS)
            or not isinstance(hashes, Mapping)
            or set(hashes) != set(contract.ARMS)
            or item.get("retry_resume_skip_or_selective_rerun") is not False
        ):
            raise RuntimeError("V2.49.36 frozen prediction vector drifted")
        seen.add(opaque)
        entities = task_map[opaque]
        name_keys = {_norm(name) for name, _iso3 in entities}
        tagged_keys = {_norm(f"{name} [{iso3}]") for name, iso3 in entities}
        for arm in contract.ARMS:
            prediction = str(arms[arm])
            if hashes[arm] != contract.payload_sha256(prediction):
                raise RuntimeError("V2.49.36 frozen prediction hash drifted")
            _columns, matrix = _matrix(prediction)
            output[arm]["tables"] += 1
            for row in matrix:
                output[arm]["rows"] += 1
                rendered = row[0] if row else ""
                key = _norm(rendered)
                if key in name_keys:
                    output[arm]["exact_visible_name_rows"] += 1
                elif key in tagged_keys:
                    output[arm]["matching_name_iso3_rows"] += 1
                elif TAGGED_IDENTITY.fullmatch(rendered.strip()):
                    output[arm]["wrong_iso3_rows"] += 1
                else:
                    output[arm]["other_rows"] += 1
    if len(seen) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.49.36 frozen prediction denominator drifted")
    return output


def _original_artifacts() -> dict[str, dict[str, Any]]:
    values = {
        "forward_protocol": _read(contract.PROTOCOL),
        "forward_result": _read(contract.FORWARD_RESULT),
        "forward_audit": _read(contract.FORWARD_AUDIT),
        "evaluator_protocol": _read(ORIGINAL_EVALUATOR_PROTOCOL),
        "result": _read(ORIGINAL_RESULT),
        "postresult_audit": _read(ORIGINAL_POSTAUDIT),
        "prediction_freeze": _read(contract.PREDICTION_FREEZE),
    }
    seal_fields = {
        "forward_protocol": "protocol_payload_sha256",
        "forward_result": "result_payload_sha256",
        "forward_audit": "audit_payload_sha256",
        "evaluator_protocol": "protocol_payload_sha256",
        "result": "result_payload_sha256",
        "postresult_audit": "audit_payload_sha256",
        "prediction_freeze": "freeze_payload_sha256",
    }
    if any(
        not _sealed(values[name], seal)
        for name, seal in seal_fields.items()
    ):
        raise RuntimeError("V2.49.36 original artifact seal drifted")
    if (
        values["forward_protocol"].get("protocol_id") != contract.PROTOCOL_ID
        or values["forward_result"].get("all_predictions_terminal_before_evaluator_open")
        is not True
        or values["forward_audit"].get("audit_valid") is not True
        or values["forward_audit"].get("findings") != []
        or values["postresult_audit"].get("audit_valid") is not True
        or values["postresult_audit"].get("findings") != []
    ):
        raise RuntimeError("V2.49.36 original freeze barrier drifted")
    return values


def _source_manifest() -> dict[str, str]:
    paths = (
        SOURCE,
        TEST,
        Path("scripts/evaluate_v24934_contextual_record_external.py"),
        Path("scripts/evaluate_v24923_target_value_external.py"),
        Path("src/deepwide_agent/v24934_contextual_record_external_contract.py"),
    )
    return {str(path): sha256(ROOT / path) for path in paths}


def _input_manifest() -> dict[str, str]:
    paths = (
        contract.VISIBLE_TASKS,
        contract.FROZEN_PAGES,
        contract.PREDICTIONS,
        contract.PREDICTION_FREEZE,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        ORIGINAL_EVALUATOR_PROTOCOL,
        ORIGINAL_RESULT,
        ORIGINAL_POSTAUDIT,
    )
    return {str(path): sha256(ROOT / path) for path in paths}


def _synthetic_bug_reproduction() -> dict[str, Any]:
    columns = contract.visible_columns()
    prediction = (
        "| " + " | ".join(columns) + " |\n"
        "|---|---:|---:|\n"
        "| Alpha Republic [ALP] | 101 | 202 |"
    )
    gold = [
        {
            "Country": "Alpha Republic",
            columns[1]: "101",
            columns[2]: "202",
        }
    ]
    old = frozen_base.evaluate_prediction(prediction, gold)
    corrected = evaluate_prediction(
        prediction, gold, [("Alpha Republic", "ALP")]
    )
    wrong = evaluate_prediction(
        prediction.replace("[ALP]", "[BET]"),
        gold,
        [("Alpha Republic", "ALP")],
    )
    return {
        "old_entity_recall": old["entity_recall"],
        "old_exact": old["exact_table_success"],
        "corrected_entity_recall": corrected["entity_recall"],
        "corrected_exact": corrected["exact_table_success"],
        "wrong_iso3_entity_recall": wrong["entity_recall"],
        "wrong_iso3_exact": wrong["exact_table_success"],
    }


def _run_tests() -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            TEST.name,
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "expected": 8,
        "observed": observed,
        "passed": completed.returncode == 0 and observed == 8,
        "output_sha256": payload_sha256(completed.stdout),
    }


def build_invalid_audit() -> dict[str, Any]:
    _clean_pushed()
    original = _original_artifacts()
    tasks = _read_jsonl(contract.VISIBLE_TASKS)
    predictions = _read_jsonl(contract.PREDICTIONS)
    aggregate = identity_format_aggregate(tasks, predictions)
    reproduction = _synthetic_bug_reproduction()
    tests = _run_tests()
    original_metrics = original["result"].get("metrics") or {}
    original_arms = original_metrics.get("arms") or {}
    format_complete = all(
        row == {
            "tables": 24,
            "rows": 192,
            "exact_visible_name_rows": 0,
            "matching_name_iso3_rows": 192,
            "wrong_iso3_rows": 0,
            "other_rows": 0,
        }
        for row in aggregate.values()
    )
    original_all_zero = all(
        (original_arms.get(arm) or {}).get("entity_recall") == 0
        and (original_arms.get(arm) or {}).get("row_f1") == 0
        and (original_arms.get(arm) or {}).get("item_f1") == 0
        for arm in contract.ARMS
    )
    checks = {
        "original_freeze_and_seals_valid": True,
        "frozen_prediction_vector_exact24x2": len(predictions) == 24,
        "all_384_rows_use_matching_visible_name_iso3": format_complete,
        "original_entity_row_item_metrics_all_zero": original_all_zero,
        "synthetic_old_evaluator_reproduces_zero": reproduction[
            "old_entity_recall"
        ]
        == 0
        and reproduction["old_exact"] == 0,
        "synthetic_corrected_identity_recovers_exact": reproduction[
            "corrected_entity_recall"
        ]
        == 1
        and reproduction["corrected_exact"] == 1,
        "synthetic_wrong_iso3_remains_rejected": reproduction[
            "wrong_iso3_entity_recall"
        ]
        == 0
        and reproduction["wrong_iso3_exact"] == 0,
        "focused_tests_exact8": tests["passed"],
        "source_and_test_tracked": _tracked(SOURCE) and _tracked(TEST),
        "network_model_search_fetch_or_evaluator_not_called": True,
    }
    findings = [name for name, passed in checks.items() if passed is not True]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24936_v24934_evaluator_identity_mismatch_invalid_audit",
        "created_at_unix": int(time.time()),
        "status": "invalid_for_quality_evaluator_entity_identity_mismatch",
        "invalid_quality_artifacts": {
            str(ORIGINAL_RESULT): sha256(ROOT / ORIGINAL_RESULT),
            str(ORIGINAL_POSTAUDIT): sha256(ROOT / ORIGINAL_POSTAUDIT),
        },
        "valid_reusable_frozen_artifacts": {
            str(contract.PREDICTIONS): sha256(ROOT / contract.PREDICTIONS),
            str(contract.PREDICTION_FREEZE): sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            str(contract.VISIBLE_TASKS): sha256(ROOT / contract.VISIBLE_TASKS),
            str(contract.FROZEN_PAGES): sha256(ROOT / contract.FROZEN_PAGES),
        },
        "root_cause": {
            "gold_identity_rendering": "visible_name_without_iso3",
            "prediction_identity_rendering": "visible_name_with_matching_iso3",
            "frozen_evaluator_behavior": "punctuation_stripped_exact_string_identity",
            "effect": "all_valid_rows_mechanically_missed_for_both_arms",
        },
        "identity_format_aggregate": aggregate,
        "synthetic_reproduction": reproduction,
        "tests": tests,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "prediction_or_page_modified": False,
            "benchmark_forward_model_search_fetch_or_api_called": False,
            "postfreeze_visible_task_and_prediction_read": True,
            "mapping_category_question_type_split_or_deepwidebench_evaluator_read": False,
            "per_task_correctness_used_for_selection_or_tuning": False,
            "complete_frozen_population_only": True,
        },
        "authorization": {
            "append_only_complete_erratum_protocol_generation": not findings,
            "public_exact220_candidate_design": False,
            "public_exact220_launch": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_invalid_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role")
        != "v24936_v24934_evaluator_identity_mismatch_invalid_audit"
        or copied.get("status")
        != "invalid_for_quality_evaluator_entity_identity_mismatch"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("authorization", {}).get(
            "append_only_complete_erratum_protocol_generation"
        )
        is not True
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.36 invalid audit drifted")
    return copied


def build_protocol() -> dict[str, Any]:
    _clean_pushed()
    invalid = validate_invalid_audit(_read(INVALID_AUDIT))
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, RESULT, POSTAUDIT)):
        raise FileExistsError("V2.49.36 future surface is not pristine")
    source_manifest = _source_manifest()
    input_manifest = _input_manifest()
    if not all(_tracked(Path(path)) for path in source_manifest):
        raise RuntimeError("V2.49.36 source manifest is not tracked")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24936_v24934_identity_evaluator_erratum_preregistration",
        "created_at_unix": int(time.time()),
        "git_head": _git("rev-parse", "HEAD"),
        "invalid_audit": {
            "path": str(INVALID_AUDIT),
            "sha256": sha256(ROOT / INVALID_AUDIT),
            "audit_payload_sha256": invalid["audit_payload_sha256"],
        },
        "frozen_input_manifest": input_manifest,
        "frozen_input_manifest_sha256": payload_sha256(input_manifest),
        "source_manifest": source_manifest,
        "source_manifest_sha256": payload_sha256(source_manifest),
        "selected_tasks": 24,
        "selected_arm_predictions": 48,
        "single_correction": {
            "field": "visible_row_identity_canonicalization",
            "old": "normalized_rendered_row_equals_normalized_visible_name",
            "new": "exact_visible_name_or_exact_visible_name_with_matching_iso3_maps_to_same_canonical_entity",
            "wrong_iso3_rejected": True,
            "prediction_page_gold_value_or_numeric_comparison_changed": False,
        },
        "evaluation_contract": {
            "complete_frozen_24_by_2_vector_evaluated_once": True,
            "no_prediction_regeneration_selection_retry_or_rewrite": True,
            "same_fixed_denominator_failure_as_zero": True,
            "same_exact_and_quality_metrics": True,
            "go_rule": "candidate_exact_strict_gain_and_entity_row_item_column_composite_nonregression",
        },
        "claim_scope": {
            "corrected_benchmark_external_quality_only": True,
            "deepwidebench_quality": False,
            "entropy_or_credit_assignment_validated": False,
            "public_exact220_or_sota": False,
        },
        "authorization": {
            "one_complete_erratum_evaluation": True,
            "fresh_external_successor_design": False,
            "public_exact220_candidate_design": False,
            "public_exact220_launch": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    source_manifest = _source_manifest()
    input_manifest = _input_manifest()
    invalid = validate_invalid_audit(_read(INVALID_AUDIT))
    if (
        copied.get("role")
        != "v24936_v24934_identity_evaluator_erratum_preregistration"
        or copied.get("selected_tasks") != 24
        or copied.get("selected_arm_predictions") != 48
        or copied.get("invalid_audit")
        != {
            "path": str(INVALID_AUDIT),
            "sha256": sha256(ROOT / INVALID_AUDIT),
            "audit_payload_sha256": invalid["audit_payload_sha256"],
        }
        or copied.get("frozen_input_manifest") != input_manifest
        or copied.get("frozen_input_manifest_sha256")
        != payload_sha256(input_manifest)
        or copied.get("source_manifest") != source_manifest
        or copied.get("source_manifest_sha256") != payload_sha256(source_manifest)
        or copied.get("single_correction", {}).get("wrong_iso3_rejected") is not True
        or copied.get("single_correction", {}).get(
            "prediction_page_gold_value_or_numeric_comparison_changed"
        )
        is not False
        or copied.get("authorization", {}).get("one_complete_erratum_evaluation")
        is not True
        or copied.get("authorization", {}).get("public_exact220_candidate_design")
        is not False
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.36 protocol drifted")
    return copied


def run_evaluation() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    if (ROOT / RESULT).exists() or (ROOT / RESULT).is_symlink():
        raise FileExistsError(RESULT)
    tasks = _read_jsonl(contract.VISIBLE_TASKS)
    pages = _read(contract.FROZEN_PAGES)
    predictions = _read_jsonl(contract.PREDICTIONS)
    identity_aggregate = identity_format_aggregate(tasks, predictions)
    metrics = evaluate_rows(predictions, build_gold(tasks, pages))
    delta = metrics["contextual_record_30k_minus_unicode_total_30k"]
    passed = delta["exact_table_successes"] > 0 and all(
        delta[key] >= 0
        for key in (
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
        )
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24936_v24934_identity_evaluator_erratum_result",
        "created_at_unix": int(time.time()),
        "status": "corrected_external_go" if passed else "corrected_external_no_go",
        "passed": passed,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "invalid_original_result_sha256": sha256(ROOT / ORIGINAL_RESULT),
        "frozen_input_manifest_sha256": protocol["frozen_input_manifest_sha256"],
        "source_manifest_sha256": protocol["source_manifest_sha256"],
        "evaluated_tasks": 24,
        "evaluated_arm_predictions": 48,
        "identity_format_aggregate": identity_aggregate,
        "metrics": metrics,
        "fixed_denominator_failure_as_zero": True,
        "prediction_page_or_value_modified": False,
        "retry_resume_skip_selective_rerun_or_selective_reevaluation": False,
        "claim_scope": {
            "corrected_benchmark_external_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "fresh_external_successor_design": passed,
            "public_exact220_candidate_design": False,
            "public_exact220_launch": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def build_postaudit() -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    result = _read(RESULT)
    checks = {
        "result_sealed": _sealed(result, "result_payload_sha256"),
        "protocol_binding_valid": result.get("protocol_sha256")
        == sha256(ROOT / PROTOCOL)
        and result.get("protocol_payload_sha256")
        == protocol["protocol_payload_sha256"],
        "complete_fixed_denominator_24_by_2": result.get("evaluated_tasks") == 24
        and result.get("evaluated_arm_predictions") == 48,
        "frozen_input_manifest_bound": result.get("frozen_input_manifest_sha256")
        == protocol["frozen_input_manifest_sha256"],
        "source_manifest_bound": result.get("source_manifest_sha256")
        == protocol["source_manifest_sha256"],
        "original_invalid_result_bound": result.get(
            "invalid_original_result_sha256"
        )
        == sha256(ROOT / ORIGINAL_RESULT),
        "prediction_page_or_value_unchanged": result.get(
            "prediction_page_or_value_modified"
        )
        is False,
        "no_retry_rerun_or_selective_reevaluation": result.get(
            "retry_resume_skip_selective_rerun_or_selective_reevaluation"
        )
        is False,
        "public_exact220_and_sota_forbidden": result.get("authorization", {}).get(
            "public_exact220_candidate_design"
        )
        is False
        and result.get("authorization", {}).get("public_exact220_launch") is False
        and result.get("authorization", {}).get("sota_claim") is False,
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == _read(contract.PROTOCOL).get("execution", {}).get("protected_watchers"),
    }
    findings = [name for name, passed in checks.items() if passed is not True]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24936_v24934_identity_evaluator_erratum_postresult_audit",
        "created_at_unix": int(time.time()),
        "result_sha256": sha256(ROOT / RESULT),
        "result_payload_sha256": result.get("result_payload_sha256"),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_evaluator_recalled_by_audit": False,
        "authorization": {
            "fresh_external_successor_design": not findings
            and result.get("passed") is True,
            "public_exact220_candidate_design": False,
            "public_exact220_launch": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("invalidate", "protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "invalidate":
        value = build_invalid_audit()
        path = INVALID_AUDIT
    elif args.command == "protocol":
        value = build_protocol()
        path = PROTOCOL
    elif args.command == "evaluate":
        value = run_evaluation()
        path = RESULT
    else:
        value = build_postaudit()
        path = POSTAUDIT
    if value.get("findings"):
        raise RuntimeError(f"V2.49.36 {args.command} failed: {value['findings']}")
    _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "status": value.get("status"),
                "passed": value.get("passed"),
                "metrics": value.get("metrics"),
                "audit_valid": value.get("audit_valid"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
