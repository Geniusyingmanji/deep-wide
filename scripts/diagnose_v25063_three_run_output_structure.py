#!/usr/bin/env python3
"""Aggregate-only structural diagnosis of three frozen exact-220 runs.

The script decodes only top-level ``instance_id`` and ``prediction`` from each
frozen official prediction row, and only ``instance_id`` and ``error`` from
each frozen evaluator row.  All other JSON values are skipped lexically and
never materialized.  IDs and prediction text are used only for in-memory joins
and structure counts; neither is emitted or hashed separately.

The output contains no question, task/instance ID, table header, row/cell
value, prediction, gold, category, split, per-task score, or credential.  It
performs no network, model, search, fetch, evaluator, or benchmark effect.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import time
import unicodedata
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "20260811"
OUTPUT = Path(f"results/v25063_three_run_output_structure_diagnosis_v1_{DATE}.json")
AUDIT = Path(f"results/v25063_three_run_output_structure_audit_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25063_three_run_output_structure.py")
TEST = Path("tests/test_diagnose_v25063_three_run_output_structure.py")
RUNS = {
    "v24857": {
        "predictions": Path("outputs/v24857_pacing_aware_exact220_v1_20260808/evaluator/official_predictions.jsonl"),
        "evaluation": Path("outputs/v24857_pacing_aware_exact220_v1_20260808/evaluator/official_eval_results.jsonl"),
        "freeze": Path("outputs/v24857_pacing_aware_exact220_v1_20260808/prediction_freeze.json"),
        "postaudit": Path("results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"),
    },
    "v25030": {
        "predictions": Path("outputs/v25030_evidence_conditioned_exact220_v1_20260810/evaluator/official_predictions.jsonl"),
        "evaluation": Path("outputs/v25030_evidence_conditioned_exact220_v1_20260810/evaluator/official_eval_results.jsonl"),
        "freeze": Path("outputs/v25030_evidence_conditioned_exact220_v1_20260810/prediction_freeze.json"),
        "postaudit": Path("results/v25030_evidence_conditioned_exact220_postresult_audit_v1_20260810.json"),
    },
    "v25057": {
        "predictions": Path("outputs/v25057_page_self_exact220_r2_20260811/evaluator/official_predictions.jsonl"),
        "evaluation": Path("outputs/v25057_page_self_exact220_r2_20260811/evaluator/official_eval_results.jsonl"),
        "freeze": Path("outputs/v25057_page_self_exact220_r2_20260811/prediction_freeze.json"),
        "postaudit": Path("results/v25057_page_self_exact220_postresult_audit_r2_20260811.json"),
    },
}
EXPECTED_SHA256 = {
    "v24857": {
        "predictions": "e1d3bb49e60d05eba7302dcdd12229a7eaa84420c5800ff9d94490bf4b3d6c36",
        "evaluation": "1782ab9112c1e8a5638f02db4464ad131a6c4dc7b513864b3e52743f29475d2c",
        "freeze": "3ac7f95b0f69d8f1b1036e5817c6744f79a37bbb5be8cd6fe5ebea3ca48beda9",
        "postaudit": "cf49f952533656d805ca13e807689ea1cd07215553b3f3f9b2dbbf11c115ca20",
    },
    "v25030": {
        "predictions": "0ea0d44e6565bf53de1fd3156919df32ab57e865548d123838a3570b995a69f1",
        "evaluation": "81be75da8ce8b44e39481165c202a88d430dc2c714d7c07df56333e482d34690",
        "freeze": "48b33f8e75bef9540521da0a171a0806d28844ffb53f2f86de13d194e84c7dcd",
        "postaudit": "ebae2aeb6e2a0c3b3abf0552891f6f4e289e7ae94330d97ddf549209acad21d9",
    },
    "v25057": {
        "predictions": "405a62970ac2b8bd54342c591a871d7fe69defdeab5e6b84abadbfd4808a3ae0",
        "evaluation": "ac4026de742aba075ff4c6cdd7e74648692aea163c2cd1b371826a42d78cc02e",
        "freeze": "d8792fb1273109a480578543d321f1bafb9d60e335fda3ab20e08818fb76d093",
        "postaudit": "8f83db539b8bc52e8ab08cef0406d7446c0e706f664273d929e8e2153a707f16",
    },
}
UNKNOWN_EXACT = frozenset(
    {"", "-", "—", "?", "/", "n/a", "na", "none", "null", "unknown", "未知", "不详", "无法确认"}
)
SIGNALS = ("duplicate_identity", "unknown_identity", "all_unknown_nonkey", "all_unknown_full")
SEPARATOR = re.compile(r":?-{3,}:?")
_DECODER = json.JSONDecoder()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def sha256(relative: Path) -> str:
    path = _ordinary(relative)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.50.63 expected ordinary repository file")
    return path


def _json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.63 expected JSON object")
    return value


def _skip_ws(text: str, position: int) -> int:
    while position < len(text) and text[position] in " \t\r\n":
        position += 1
    return position


def _value_end(text: str, position: int) -> int:
    """Lexically find one JSON value boundary without decoding the value."""

    position = _skip_ws(text, position)
    if position >= len(text):
        raise ValueError("missing JSON value")
    if text[position] == '"':
        position += 1
        escaped = False
        while position < len(text):
            character = text[position]
            if character == '"' and not escaped:
                return position + 1
            if character == "\\" and not escaped:
                escaped = True
            else:
                escaped = False
            position += 1
        raise ValueError("unterminated JSON string")
    if text[position] in "[{":
        stack = ["]" if text[position] == "[" else "}"]
        position += 1
        in_string = False
        escaped = False
        while position < len(text):
            character = text[position]
            if in_string:
                if character == '"' and not escaped:
                    in_string = False
                if character == "\\" and not escaped:
                    escaped = True
                else:
                    escaped = False
            elif character == '"':
                in_string = True
            elif character in "[{":
                stack.append("]" if character == "[" else "}")
            elif character in "]}":
                if not stack or character != stack.pop():
                    raise ValueError("unbalanced JSON container")
                if not stack:
                    return position + 1
            position += 1
        raise ValueError("unterminated JSON container")
    end = position
    while end < len(text) and text[end] not in ",}":
        end += 1
    if not text[position:end].strip():
        raise ValueError("empty JSON scalar")
    return end


def selected_top_level_fields(line: str, allowed: frozenset[str]) -> dict[str, Any]:
    """Decode only selected top-level fields; skip all other values lexically."""

    text = str(line).strip()
    position = _skip_ws(text, 0)
    if position >= len(text) or text[position] != "{":
        raise ValueError("expected JSON object")
    position += 1
    selected: dict[str, Any] = {}
    seen: set[str] = set()
    while True:
        position = _skip_ws(text, position)
        if position < len(text) and text[position] == "}":
            position = _skip_ws(text, position + 1)
            if position != len(text):
                raise ValueError("trailing JSON content")
            break
        key, key_end = _DECODER.raw_decode(text, position)
        if not isinstance(key, str) or key in seen:
            raise ValueError("invalid or duplicate top-level JSON key")
        seen.add(key)
        position = _skip_ws(text, key_end)
        if position >= len(text) or text[position] != ":":
            raise ValueError("missing JSON colon")
        start = _skip_ws(text, position + 1)
        end = _value_end(text, start)
        if key in allowed:
            selected[key] = json.loads(text[start:end])
        position = _skip_ws(text, end)
        if position < len(text) and text[position] == ",":
            position += 1
            continue
        if position < len(text) and text[position] == "}":
            continue
        raise ValueError("invalid top-level JSON delimiter")
    if set(selected) != set(allowed):
        raise ValueError("selected JSON field set drifted")
    return selected


def _normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def _unknown(value: object) -> bool:
    normalized = _normalize(value).strip(" .。;；:：()（）[]【】")
    return normalized in UNKNOWN_EXACT or normalized.startswith(("未知（", "未知(", "unknown ("))


def _split_pipe_row(line: str) -> list[str]:
    stripped = str(line).strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return []
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_separator(row: list[str]) -> bool:
    return bool(row) and all(SEPARATOR.fullmatch(cell.replace(" ", "")) for cell in row)


def _shape(prediction: str) -> dict[str, Any]:
    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in str(prediction).replace("\r\n", "\n").splitlines():
        row = _split_pipe_row(line)
        if row:
            current.append(row)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    candidates: list[tuple[list[str], list[list[str]]]] = []
    for group in groups:
        for index, row in enumerate(group):
            if index >= 1 and _is_separator(row) and len(group) >= index + 2 and len(group[index - 1]) == len(row):
                candidates.append((group[index - 1], group[index + 1 :]))
    if len(candidates) != 1:
        raise RuntimeError("V2.50.63 expected exactly one table candidate")
    header, raw_rows = candidates[0]
    rows = [row for row in raw_rows if len(row) == len(header)]
    malformed = len(raw_rows) - len(rows)
    identities = [_normalize(row[0]) for row in rows]
    full_rows = [tuple(_normalize(cell) for cell in row) for row in rows]
    return {
        "column_count": len(header),
        "row_count": len(rows),
        "cell_count": sum(len(row) for row in rows),
        "malformed_width_rows": malformed,
        "empty_cells": sum(not cell.strip() for row in rows for cell in row),
        "duplicate_identity_extra_rows": len(identities) - len(set(identities)),
        "exact_duplicate_extra_rows": len(full_rows) - len(set(full_rows)),
        "unknown_identity_rows": sum(_unknown(row[0]) for row in rows),
        "all_unknown_nonkey_rows": sum(bool(row) and all(_unknown(cell) for cell in row[1:]) for row in rows),
        "all_unknown_full_rows": sum(all(_unknown(cell) for cell in row) for row in rows),
        "unknown_like_cells": sum(_unknown(cell) for row in rows for cell in row),
    }


def _parents() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for run, paths in RUNS.items():
        observed = {name: sha256(path) for name, path in paths.items()}
        if observed != EXPECTED_SHA256[run]:
            raise RuntimeError("V2.50.63 frozen input hash drifted")
        freeze = selected_top_level_fields(
            _ordinary(paths["freeze"]).read_text(encoding="utf-8"),
            frozenset({"selected", "terminal", "label_blind"}),
        )
        postaudit = selected_top_level_fields(
            _ordinary(paths["postaudit"]).read_text(encoding="utf-8"),
            frozenset({"audit_valid", "findings"}),
        )
        if (
            freeze.get("selected") != 220
            or freeze.get("terminal") != 220
            or freeze.get("label_blind") is not True
            or postaudit.get("audit_valid") is not True
            or postaudit.get("findings") != []
        ):
            raise RuntimeError("V2.50.63 frozen parent barrier drifted")
        output[run] = observed
    return output


def _run_counts(run: str) -> dict[str, Any]:
    paths = RUNS[run]
    predictions: dict[str, dict[str, Any]] = {}
    for line in _ordinary(paths["predictions"]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        selected = selected_top_level_fields(line, frozenset({"instance_id", "prediction"}))
        identifier = selected["instance_id"]
        if not isinstance(identifier, str) or identifier in predictions or not isinstance(selected["prediction"], str):
            raise RuntimeError("V2.50.63 prediction identity drifted")
        predictions[identifier] = _shape(selected["prediction"])
    evaluations: dict[str, bool] = {}
    error_types: Counter[str] = Counter()
    for line in _ordinary(paths["evaluation"]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        selected = selected_top_level_fields(line, frozenset({"instance_id", "error"}))
        identifier = selected["instance_id"]
        error = selected["error"]
        if not isinstance(identifier, str) or identifier in evaluations or (error is not None and not isinstance(error, str)):
            raise RuntimeError("V2.50.63 evaluator identity drifted")
        failed = error is not None
        evaluations[identifier] = failed
        if failed:
            error_types["out_of_range"] += "out-of-range" in error
            error_types["internal_error"] += "out-of-range" not in error
    if len(predictions) != 220 or len(evaluations) != 220 or set(predictions) != set(evaluations):
        raise RuntimeError("V2.50.63 fixed denominator or in-memory join drifted")
    aggregate: Counter[str] = Counter()
    crosstabs = {signal: Counter() for signal in SIGNALS}
    column_histogram: Counter[int] = Counter()
    row_histogram: Counter[int] = Counter()
    for identifier, shape in predictions.items():
        aggregate["tasks"] += 1
        aggregate["parseable_unique_table_tasks"] += 1
        for target, source in (
            ("data_rows", "row_count"),
            ("cells", "cell_count"),
            ("malformed_width_rows", "malformed_width_rows"),
            ("empty_cells", "empty_cells"),
            ("duplicate_identity_extra_rows", "duplicate_identity_extra_rows"),
            ("exact_duplicate_extra_rows", "exact_duplicate_extra_rows"),
            ("unknown_identity_rows", "unknown_identity_rows"),
            ("all_unknown_nonkey_rows", "all_unknown_nonkey_rows"),
            ("all_unknown_full_rows", "all_unknown_full_rows"),
            ("unknown_like_cells", "unknown_like_cells"),
        ):
            aggregate[target] += int(shape[source])
        flags = {
            "duplicate_identity": shape["duplicate_identity_extra_rows"] > 0,
            "unknown_identity": shape["unknown_identity_rows"] > 0,
            "all_unknown_nonkey": shape["all_unknown_nonkey_rows"] > 0,
            "all_unknown_full": shape["all_unknown_full_rows"] > 0,
        }
        for signal, present in flags.items():
            aggregate["tasks_with_" + signal] += int(present)
            key = ("signal" if present else "no_signal") + "__" + ("error" if evaluations[identifier] else "valid")
            crosstabs[signal][key] += 1
        column_histogram[int(shape["column_count"])] += 1
        row_histogram[int(shape["row_count"])] += 1
    aggregate["evaluator_error_count"] = sum(evaluations.values())
    return {
        "aggregate": dict(sorted(aggregate.items())),
        "column_count_histogram": {str(key): value for key, value in sorted(column_histogram.items())},
        "row_count_summary": {
            "minimum": min(row_histogram),
            "maximum": max(row_histogram),
            "zero_row_tasks": row_histogram.get(0, 0),
            "one_row_tasks": row_histogram.get(1, 0),
            "multirow_tasks": sum(value for key, value in row_histogram.items() if key > 1),
        },
        "evaluator_error_types": dict(sorted(error_types.items())),
        "structure_error_crosstabs": {
            signal: dict(sorted(values.items())) for signal, values in crosstabs.items()
        },
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    runs = {run: _run_counts(run) for run in RUNS}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25063_three_run_output_structure_counts_only_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "three_frozen_exact220_runs_aggregate_only_audited",
        "parents": _parents(),
        "fixed_denominator": {"runs": 3, "tasks_per_run": 220, "total_task_rows": 660},
        "runs": runs,
        "diagnosis": {
            "all_predictions_have_exactly_one_parseable_table": all(
                row["aggregate"]["parseable_unique_table_tasks"] == 220 for row in runs.values()
            ),
            "all_predictions_have_at_least_one_data_row": all(
                row["row_count_summary"]["zero_row_tasks"] == 0 for row in runs.values()
            ),
            "duplicate_first_column_identity_establishes_duplicate_full_row": False,
            "duplicate_first_column_identity_is_safe_generic_merge_key": False,
            "all_unknown_nonkey_row_is_safe_generic_deletion_target": False,
            "structural_signals_identify_evaluator_internal_errors": False,
            "generic_structural_postprocessor_supported": False,
            "next_candidate_should_target_fact_selection_or_evidence_grounding": True,
            "entropy_or_information_gain_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "prediction_fields_decoded": ["instance_id", "prediction"],
            "evaluator_fields_decoded": ["instance_id", "error"],
            "freeze_fields_decoded": ["selected", "terminal", "label_blind"],
            "postaudit_fields_decoded": ["audit_valid", "findings"],
            "all_other_parent_prediction_and_evaluator_values_skipped_lexically": True,
            "ids_and_predictions_used_only_in_memory": True,
            "question_id_header_row_cell_prediction_gold_category_split_or_per_task_score_emitted": False,
            "mapping_gold_category_question_type_split_score_or_reward_decoded": False,
            "network_model_search_fetch_evaluator_benchmark_or_credential_accessed": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "first_column_deduplication": False,
            "all_unknown_row_deletion": False,
            "postprocessor_exact220_revaluation": False,
            "new_exact220_launch": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    runs = copied.get("runs") or {}
    diagnosis = copied.get("diagnosis") or {}
    policy = copied.get("content_policy") or {}
    authorization = copied.get("authorization") or {}
    expected_aggregates = {
        "v24857": (67, 1696, 38, 10),
        "v25030": (65, 1793, 0, 12),
        "v25057": (64, 1476, 0, 11),
    }
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "status",
            "parents",
            "fixed_denominator",
            "runs",
            "diagnosis",
            "content_policy",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or set(copied.get("parents") or {}) != set(RUNS)
        or any(set((copied.get("parents") or {}).get(run, {})) != set(RUNS[run]) for run in RUNS)
        or any((copied.get("parents") or {}).get(run) != EXPECTED_SHA256[run] for run in RUNS)
        or copied.get("role") != "v25063_three_run_output_structure_counts_only_diagnosis"
        or copied.get("fixed_denominator") != {"runs": 3, "tasks_per_run": 220, "total_task_rows": 660}
        or set(runs) != set(RUNS)
        or any(
            set(runs[run])
            != {
                "aggregate",
                "column_count_histogram",
                "row_count_summary",
                "evaluator_error_types",
                "structure_error_crosstabs",
            }
            for run in runs
        )
        or any(
            set(runs[run]["aggregate"])
            != {
                "all_unknown_full_rows",
                "all_unknown_nonkey_rows",
                "cells",
                "data_rows",
                "duplicate_identity_extra_rows",
                "empty_cells",
                "evaluator_error_count",
                "exact_duplicate_extra_rows",
                "malformed_width_rows",
                "parseable_unique_table_tasks",
                "tasks",
                "tasks_with_all_unknown_full",
                "tasks_with_all_unknown_nonkey",
                "tasks_with_duplicate_identity",
                "tasks_with_unknown_identity",
                "unknown_identity_rows",
                "unknown_like_cells",
            }
            for run in runs
        )
        or any(
            set(runs[run]["row_count_summary"])
            != {"minimum", "maximum", "zero_row_tasks", "one_row_tasks", "multirow_tasks"}
            for run in runs
        )
        or any(set(runs[run]["evaluator_error_types"]) != {"internal_error", "out_of_range"} for run in runs)
        or any(set(runs[run]["structure_error_crosstabs"]) != set(SIGNALS) for run in runs)
        or any(
            not set(values).issubset(
                {"signal__error", "signal__valid", "no_signal__error", "no_signal__valid"}
            )
            for run in runs
            for values in runs[run]["structure_error_crosstabs"].values()
        )
        or set(diagnosis)
        != {
            "all_predictions_have_exactly_one_parseable_table",
            "all_predictions_have_at_least_one_data_row",
            "duplicate_first_column_identity_establishes_duplicate_full_row",
            "duplicate_first_column_identity_is_safe_generic_merge_key",
            "all_unknown_nonkey_row_is_safe_generic_deletion_target",
            "structural_signals_identify_evaluator_internal_errors",
            "generic_structural_postprocessor_supported",
            "next_candidate_should_target_fact_selection_or_evidence_grounding",
            "entropy_or_information_gain_credit_validated",
            "entropy_or_information_gain_signed_credit",
        }
        or set(policy)
        != {
            "prediction_fields_decoded",
            "evaluator_fields_decoded",
            "freeze_fields_decoded",
            "postaudit_fields_decoded",
            "all_other_parent_prediction_and_evaluator_values_skipped_lexically",
            "ids_and_predictions_used_only_in_memory",
            "question_id_header_row_cell_prediction_gold_category_split_or_per_task_score_emitted",
            "mapping_gold_category_question_type_split_score_or_reward_decoded",
            "network_model_search_fetch_evaluator_benchmark_or_credential_accessed",
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection",
        }
        or set(authorization)
        != {
            "first_column_deduplication",
            "all_unknown_row_deletion",
            "postprocessor_exact220_revaluation",
            "new_exact220_launch",
            "retry_resume_or_selective_rerun",
            "leaderboard_or_sota",
        }
        or any(
            (
                runs[run]["aggregate"]["tasks_with_duplicate_identity"],
                runs[run]["aggregate"]["duplicate_identity_extra_rows"],
                runs[run]["aggregate"]["exact_duplicate_extra_rows"],
                runs[run]["aggregate"]["evaluator_error_count"],
            )
            != expected
            for run, expected in expected_aggregates.items()
        )
        or any(runs[run]["aggregate"]["parseable_unique_table_tasks"] != 220 for run in runs)
        or diagnosis.get("all_predictions_have_exactly_one_parseable_table") is not True
        or diagnosis.get("duplicate_first_column_identity_is_safe_generic_merge_key") is not False
        or diagnosis.get("all_unknown_nonkey_row_is_safe_generic_deletion_target") is not False
        or diagnosis.get("generic_structural_postprocessor_supported") is not False
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or policy.get("prediction_fields_decoded") != ["instance_id", "prediction"]
        or policy.get("evaluator_fields_decoded") != ["instance_id", "error"]
        or policy.get("freeze_fields_decoded") != ["selected", "terminal", "label_blind"]
        or policy.get("postaudit_fields_decoded") != ["audit_valid", "findings"]
        or policy.get("mapping_gold_category_question_type_split_score_or_reward_decoded") is not False
        or policy.get("question_id_header_row_cell_prediction_gold_category_split_or_per_task_score_emitted") is not False
        or policy.get("network_model_search_fetch_evaluator_benchmark_or_credential_accessed") is not False
        or any(value is not False for value in authorization.values())
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.63 output-structure diagnosis drifted")
    return copied


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    result = validate_diagnosis(_json(OUTPUT))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stdout=subprocess.PIPE, timeout=20, check=True
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"], cwd=ROOT, text=True, stdout=subprocess.PIPE, timeout=20, check=True
    ).stdout.strip()
    clean = not subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True, stdout=subprocess.PIPE, timeout=20, check=True
    ).stdout.strip()
    tracked = all(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
        for path in (SOURCE, TEST, OUTPUT)
    )
    checks = {
        "diagnosis_valid": True,
        "diagnosis_source_test_and_result_tracked": tracked,
        "git_clean_head_equals_target_main": clean and head == remote,
        "fixed_three_by_220_denominator": result["fixed_denominator"]["total_task_rows"] == 660,
        "all_parent_hashes_bound": result["parents"] == EXPECTED_SHA256,
        "selected_field_decode_policy_exact": result["content_policy"]["prediction_fields_decoded"] == ["instance_id", "prediction"]
        and result["content_policy"]["evaluator_fields_decoded"] == ["instance_id", "error"]
        and result["content_policy"]["freeze_fields_decoded"] == ["selected", "terminal", "label_blind"]
        and result["content_policy"]["postaudit_fields_decoded"] == ["audit_valid", "findings"],
        "no_sensitive_or_per_task_output": result["content_policy"]["question_id_header_row_cell_prediction_gold_category_split_or_per_task_score_emitted"] is False,
        "no_model_search_fetch_evaluator_or_benchmark_effect": result["content_policy"]["network_model_search_fetch_evaluator_benchmark_or_credential_accessed"] is False,
        "unsafe_postprocessors_forbidden": result["authorization"]["first_column_deduplication"] is False
        and result["authorization"]["all_unknown_row_deletion"] is False,
        "no_exact220_or_leaderboard_authority": result["authorization"]["new_exact220_launch"] is False
        and result["authorization"]["leaderboard_or_sota"] is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25063_three_run_output_structure_diagnosis_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": remote, "equal": head == remote},
        "source_sha256": sha256(SOURCE),
        "test_sha256": sha256(TEST),
        "diagnosis_sha256": sha256(OUTPUT),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": copy.deepcopy(result["authorization"]),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v25063_three_run_output_structure_diagnosis_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or any(item is not False for item in (copied.get("authorization") or {}).values())
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.63 audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0), 0o600
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V2.50.63 publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("diagnose", "audit"))
    args = parser.parse_args()
    if args.command == "diagnose":
        value, path = build_diagnosis(), OUTPUT
    else:
        value, path = build_audit(), AUDIT
    publish_exclusive(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
