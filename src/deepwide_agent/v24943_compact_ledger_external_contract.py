"""Fresh representation-only gate for compact schema-bound ledgers."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24941_open_world_ledger_external_contract as parent


DATE = "20260809"
PROTOCOL_ID = "v24943_fresh_compact_schema_bound_ledger_external_v1"
HISTORICAL_BOUNDARY_COMMIT = "5e69c7a1"
SELECTION_SEED = "v24943-compact-ledger-record-rank-v1"
COHORT_SEED = "v24943-compact-ledger-visible-cohort-v1"
SELECTED_COUNT = 18
ROWS_PER_TASK = 8
DISTRACTOR_ROWS_PER_TASK = 8
PAGE_ROWS_PER_TASK = 16
SELECTED_ENTITY_COUNT = 144
SELECTED_RECORD_COUNT = 152
ARMS = ("parent_30k", "target_value_30k")
DEVELOPMENT_TARGET_KEYS = (*parent.DEVELOPMENT_TARGET_KEYS, *parent.TARGET_KEYS)
TARGETS = ({"label": "Total population", "indicator": "SP.POP.TOTL", "year": "2020"},)
TARGET_KEYS = ("SP.POP.TOTL@2020",)
CATALOG_URL = parent.CATALOG_URL
TARGET_URLS = (
    "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?date=2020&format=json&per_page=400",
)
MODEL = parent.MODEL
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
TASK_WALL_SECONDS = parent.TASK_WALL_SECONDS
FETCH_TIMEOUT_SECONDS = parent.FETCH_TIMEOUT_SECONDS
FETCH_MAX_BYTES = parent.FETCH_MAX_BYTES
LEASE_PATH = parent.LEASE_PATH
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS

BUILD_AUDIT = Path(f"results/v24943_compact_ledger_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24943_compact_ledger_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24943_compact_ledger_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24943_compact_ledger_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24943_compact_ledger_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24943_compact_ledger_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24943_compact_ledger_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24943_compact_ledger_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24943_compact_ledger_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24943_compact_ledger_external_v1_{DATE}")
SNAPSHOT_ROOT = OUTPUT_ROOT / "snapshot"
CATALOG_RESPONSE = SNAPSHOT_ROOT / "country_catalog.bin"
TARGET_RESPONSE_ROOT = SNAPSHOT_ROOT / "target_responses"
FROZEN_PAGES = SNAPSHOT_ROOT / "frozen_pages.json"
SNAPSHOT_FREEZE = SNAPSHOT_ROOT / "snapshot_freeze.json"
VISIBLE_TASKS = OUTPUT_ROOT / "visible_tasks.jsonl"
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PROJECTIONS = OUTPUT_ROOT / "frozen_projections.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
CONTROL = Path("scripts/control_v24943_compact_ledger_external.py")
RUNNER = Path("scripts/run_v24943_compact_ledger_external.py")
CHILD = Path("scripts/run_v24943_compact_ledger_external_task.py")
EVALUATOR = Path("scripts/evaluate_v24943_compact_ledger_external.py")
TEST = Path("tests/test_v24943_compact_ledger_external.py")
CANDIDATE_AUDIT = Path(f"results/v24943_compact_ledger_build_audit_v1_{DATE}.json")
PARENT_RESULT = parent.RESULT
PARENT_POSTAUDIT = parent.POSTAUDIT
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24943_compact_ledger_external_contract.py"),
    Path("src/deepwide_agent/v24942_compact_schema_bound_record_ledger.py"),
    Path("src/deepwide_agent/v24939_schema_bound_record_ledger.py"),
    Path("src/deepwide_agent/v24933_contextual_record_value_projector.py"),
    Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"),
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
    Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
    RUNNER,
    CHILD,
    Path("scripts/run_v24940_open_world_ledger_external.py"),
    Path("scripts/run_v24923_target_value_external.py"),
    Path("scripts/run_v24923_target_value_external_task.py"),
    Path("scripts/deepwide_api_lease.py"),
)
BUILD_SOURCES = (
    *RUNTIME_SOURCES,
    CONTROL,
    EVALUATOR,
    Path("scripts/control_v24923_target_value_external.py"),
    Path("scripts/evaluate_v24940_open_world_ledger_external.py"),
    TEST,
    CANDIDATE_AUDIT,
    PARENT_RESULT,
    PARENT_POSTAUDIT,
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
sealed = parent.sealed
parse_visible_cohort = parent.parse_visible_cohort
parse_visible_countries = parent.parse_visible_countries
parse_visible_entities = parent.parse_visible_entities
protected_watcher_snapshot = parent.protected_watcher_snapshot


def visible_columns() -> list[str]:
    return ["Country", "Cohort", "ISO3", "Total population [SP.POP.TOTL] @2020"]


def arm_order(opaque_id: str) -> tuple[str, str]:
    if not isinstance(opaque_id, str) or not opaque_id.startswith("task_"):
        raise ValueError("V2.49.43 opaque arm-order key drifted")
    return (
        ARMS
        if int(hashlib.sha256(opaque_id.encode()).hexdigest()[-1], 16) % 2 == 0
        else ARMS[::-1]
    )


def validate_task_vector(
    tasks: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(tasks, (str, bytes)) or len(tasks) != SELECTED_COUNT:
        raise ValueError("V2.49.43 task denominator drifted")
    columns = visible_columns()
    output: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_cohorts: set[str] = set()
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.49.43 runtime input must be opaque_id and question")
        opaque = item.get("opaque_id")
        question = item.get("question")
        if (
            not isinstance(opaque, str)
            or not opaque.startswith("task_")
            or len(opaque) != 29
            or opaque in seen_ids
            or not isinstance(question, str)
            or not all(column in question for column in columns)
            or "<ENTITIES>" in question
            or "<COUNTRIES>" in question
        ):
            raise ValueError("V2.49.43 visible task binding drifted")
        cohort = parse_visible_cohort(question)
        if cohort in seen_cohorts:
            raise ValueError("V2.49.43 visible cohorts are not unique")
        seen_ids.add(opaque)
        seen_cohorts.add(cohort)
        output.append({"opaque_id": opaque, "question": question})
    return output


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order", "parse_visible_cohort", "parse_visible_countries",
    "parse_visible_entities", "payload_sha256", "protected_watcher_snapshot",
    "sealed", "sha256", "validate_task_vector", "visible_columns",
]
