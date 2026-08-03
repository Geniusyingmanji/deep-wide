#!/usr/bin/env python3
"""Offline label-blind build audit for V2.42.86.

The audit reads source, tests, and already frozen forward artifacts only.  It
does not call a model, search, fetch, or evaluator and does not open benchmark
mapping, gold tables, categories, splits, or scores.  Historical predictions
are parsed mechanically only to measure syntax safety; no score is computed or
claimed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import extract_visible_columns  # noqa: E402
from deepwide_agent.v24286_visible_schema_runtime import (  # noqa: E402
    extract_robust_visible_columns,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = Path("results/v24286_visible_schema_timing_build_audit_v1_20260803.json")
SOURCE = Path("src/deepwide_agent/v24286_visible_schema_runtime.py")
TEST = Path("tests/test_v24286_visible_schema_runtime.py")
FROZEN_FORWARD = Path("results/v24267_exact220_forward_result_v1_20260802.json")
FROZEN_TASKS = Path("outputs/v24267_exact220_v1_20260802/tasks")
FROZEN_DEV64 = Path("results/v24275_two_wave_dev64_result_v2_20260802.json")
FROZEN_RESULT = Path("results/v24267_exact220_result_v1_20260802.json")
FROZEN_EVALUATOR_LOG = Path(
    "outputs/v24267_exact220_v1_20260802/evaluator/evaluate.log"
)
FORBIDDEN_KEYS = frozenset(
    {
        "answer_key",
        "category",
        "evaluator",
        "ground_truth",
        "gold",
        "mapping",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
FORBIDDEN_IMPORTS = frozenset(
    {"ctypes", "multiprocessing", "os", "pathlib", "requests", "socket", "subprocess"}
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.42.86 expected object: {path}")
    return value


def _literal_key_accesses(tree: ast.AST) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        key: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key in FORBIDDEN_KEYS:
            values.append({"line": int(node.lineno), "key": key})
    return values


def _imports(tree: ast.AST) -> set[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            values.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            values.add((node.module or "").split(".")[0])
    return values


def _source_audit(root: Path) -> dict[str, Any]:
    path = root / SOURCE
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = _imports(tree)
    privileged = _literal_key_accesses(tree)
    value = {
        "sha256": sha256(path),
        "forbidden_imports": sorted(imports.intersection(FORBIDDEN_IMPORTS)),
        "privileged_exact_key_accesses": privileged,
        "credential_literal_present": SECRET.search(source) is not None,
        "concrete_opaque_id_present": OPAQUE.search(source) is not None,
        "benchmark_evaluator_or_result_path_literal_present": any(
            marker in source
            for marker in (
                "overall_20250916",
                "overall_20250916_tables",
                "evaluator_mapping",
                "official_eval_results",
                "conservative_summary",
                "v24267_exact220",
                "v24275_two_wave_dev64",
            )
        ),
    }
    value["passed"] = not any(
        (
            value["forbidden_imports"],
            privileged,
            value["credential_literal_present"],
            value["concrete_opaque_id_present"],
            value["benchmark_evaluator_or_result_path_literal_present"],
        )
    )
    return value


def _prediction_syntax(prediction: str) -> dict[str, Any]:
    pipe_lines = [
        line.strip()
        for line in str(prediction).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    widths = [len(line.split("|")) - 2 for line in pipe_lines]
    return {
        "pipe_row_count": len(pipe_lines),
        "rectangular_by_plain_pipe_split": bool(widths) and len(set(widths)) == 1,
        "ascii_quote_count": sum(line.count('"') for line in pipe_lines),
        "escaped_pipe_count": sum(line.count("\\|") for line in pipe_lines),
    }


def _frozen_replay(root: Path) -> dict[str, Any]:
    task_root = root / FROZEN_TASKS
    directories = sorted(path for path in task_root.iterdir() if path.is_dir())
    if len(directories) != 220:
        raise RuntimeError("V2.42.86 frozen exact220 task surface drifted")
    aggregate = {
        "selected": len(directories),
        "robust_schema_available": 0,
        "legacy_schema_available": 0,
        "same_visible_schema": 0,
        "changed_visible_schema": 0,
        "legacy_only_schema": 0,
        "robust_only_schema": 0,
        "both_schema_absent": 0,
        "existing_rectangular_predictions": 0,
        "existing_predictions_with_ascii_quotes": 0,
        "existing_predictions_with_escaped_pipes": 0,
        "question_column_prediction_or_opaque_id_persisted": False,
    }
    for directory in directories:
        visible = _read(directory / "visible_task.json")
        result = _read(directory / "result.json")
        if set(visible) != {"opaque_id", "question"}:
            raise RuntimeError("V2.42.86 frozen visible boundary drifted")
        question = visible["question"]
        if not isinstance(question, str):
            raise RuntimeError("V2.42.86 frozen visible question is invalid")
        legacy = extract_visible_columns(question)
        robust = extract_robust_visible_columns(question)
        aggregate["legacy_schema_available"] += bool(legacy)
        aggregate["robust_schema_available"] += bool(robust)
        aggregate["same_visible_schema"] += bool(legacy and robust and legacy == robust)
        aggregate["changed_visible_schema"] += bool(legacy and robust and legacy != robust)
        aggregate["legacy_only_schema"] += bool(legacy and not robust)
        aggregate["robust_only_schema"] += bool(robust and not legacy)
        aggregate["both_schema_absent"] += bool(not legacy and not robust)
        syntax = _prediction_syntax(str(result.get("prediction", "")))
        aggregate["existing_rectangular_predictions"] += bool(
            syntax["rectangular_by_plain_pipe_split"]
        )
        aggregate["existing_predictions_with_ascii_quotes"] += bool(
            syntax["ascii_quote_count"]
        )
        aggregate["existing_predictions_with_escaped_pipes"] += bool(
            syntax["escaped_pipe_count"]
        )
    # The aggregate intentionally contains no per-task row, value, text, or
    # identifier.  This attestation is checked again by the report validator.
    return aggregate


def _failure_taxonomy(root: Path) -> dict[str, int]:
    text = (root / FROZEN_EVALUATOR_LOG).read_text(encoding="utf-8")
    value = {
        "official_evaluator_empty_inner_dataframe_bug": text.count(
            "Cannot set a DataFrame with multiple columns to the single column"
        ),
        "official_evaluator_out_of_range_metric_bug": text.count(
            "official evaluator returned out-of-range metrics"
        ),
        "forward_csv_quote_parser_risk": text.count("EOF inside string starting at row"),
        "forward_duplicate_mapping_column_risk": text.count(
            "DataFrame' object has no attribute 'tolist'"
        ),
    }
    if value != {
        "official_evaluator_empty_inner_dataframe_bug": 11,
        "official_evaluator_out_of_range_metric_bug": 1,
        "forward_csv_quote_parser_risk": 1,
        "forward_duplicate_mapping_column_risk": 1,
    }:
        raise RuntimeError("V2.42.86 evaluator failure taxonomy drifted")
    return value


def validate_report(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "parents",
        "surface_manifest",
        "static_audit",
        "frozen_exact220_mechanical_replay",
        "evaluator_failure_taxonomy",
        "timing_diagnosis",
        "candidate_scope",
        "authorization",
        "findings",
        "audit_valid",
        "audit_payload_sha256",
    }
    parents = value.get("parents")
    static = value.get("static_audit")
    replay = value.get("frozen_exact220_mechanical_replay")
    taxonomy = value.get("evaluator_failure_taxonomy")
    timing = value.get("timing_diagnosis")
    authorization = value.get("authorization")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24286_visible_schema_timing_build_audit"
        or value.get("label_blind") is not True
        or not isinstance(parents, Mapping)
        or not isinstance(static, Mapping)
        or static.get("passed") is not True
        or not isinstance(replay, Mapping)
        or replay.get("selected") != 220
        or replay.get("question_column_prediction_or_opaque_id_persisted") is not False
        or not isinstance(taxonomy, Mapping)
        or sum(int(number) for number in taxonomy.values()) != 14
        or taxonomy.get("official_evaluator_empty_inner_dataframe_bug") != 11
        or taxonomy.get("official_evaluator_out_of_range_metric_bug") != 1
        or taxonomy.get("forward_csv_quote_parser_risk") != 1
        or taxonomy.get("forward_duplicate_mapping_column_risk") != 1
        or not isinstance(timing, Mapping)
        or timing.get("single_search_took_forty_to_fifty_minutes") is not False
        or timing.get("old_outer_search_event_mixes_network_fetch") is not True
        or not isinstance(authorization, Mapping)
        or any(authorization.values())
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.86 build audit drifted")
    numeric_replay = set(replay) - {"question_column_prediction_or_opaque_id_persisted"}
    if any(
        isinstance(replay[name], bool)
        or not isinstance(replay[name], int)
        or replay[name] < 0
        or replay[name] > 220
        for name in numeric_replay
    ):
        raise RuntimeError("V2.42.86 replay aggregate drifted")


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    forward = _read(root / FROZEN_FORWARD)
    dev64 = _read(root / FROZEN_DEV64)
    result = _read(root / FROZEN_RESULT)
    if (
        forward.get("selected") != 220
        or forward.get("terminal_predictions") != 220
        or dev64.get("status") != "development_gate_no_go"
        or dev64.get("decision", {}).get("passed") is not False
        or result.get("metrics", {}).get("evaluator_invalid_or_not_run") != 14
    ):
        raise RuntimeError("V2.42.86 parent result surface drifted")
    static = _source_audit(root)
    replay = _frozen_replay(root)
    taxonomy = _failure_taxonomy(root)
    findings = [] if static["passed"] else ["static_surface_failed"]
    value = {
        "artifact_version": 1,
        "role": "v24286_visible_schema_timing_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "exact220_forward": {"path": str(FROZEN_FORWARD), "sha256": sha256(root / FROZEN_FORWARD)},
            "exact220_result": {"path": str(FROZEN_RESULT), "sha256": sha256(root / FROZEN_RESULT)},
            "two_wave_dev64_no_go": {"path": str(FROZEN_DEV64), "sha256": sha256(root / FROZEN_DEV64)},
            "frozen_evaluator_log": {
                "path": str(FROZEN_EVALUATOR_LOG),
                "sha256": sha256(root / FROZEN_EVALUATOR_LOG),
            },
        },
        "surface_manifest": {
            str(SOURCE): sha256(root / SOURCE),
            str(TEST): sha256(root / TEST),
        },
        "static_audit": static,
        "frozen_exact220_mechanical_replay": replay,
        "evaluator_failure_taxonomy": taxonomy,
        "timing_diagnosis": {
            "single_search_took_forty_to_fifty_minutes": False,
            "old_outer_search_event_mixes_network_fetch": True,
            "new_receipt_separates_provider_search_network_fetch_cache_controller_and_model": True,
            "historical_exact220_stage_timing_recoverable_retroactively": False,
        },
        "candidate_scope": (
            "build_only_visible_schema_reliability_and_additive_timing_not_quality_"
            "improvement_or_evaluator_bug_fix"
        ),
        "authorization": {
            "model_search_fetch_or_evaluator_call": False,
            "dev64_launch": False,
            "exact220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
            "training_credit_assignment": False,
        },
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_report(value)
    return value


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.86 output must be repository-relative")
    report = build_report(root)
    _publish_new(root / output, report)
    print(json.dumps({"path": str(output), "audit_valid": report["audit_valid"]}, sort_keys=True))


if __name__ == "__main__":
    main()
