"""Fresh native-layout external gate for mutual partial schema signatures."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24947_native_layout_signature_external_contract as parent


DATE = "20260809"
PROTOCOL_ID = "v24951_fresh_native_layout_mutual_partial_signature_external_v1"
HISTORICAL_BOUNDARY_COMMIT = "5c22a45d"
SELECTION_SEED = "v24951-native-layout-partial-record-rank-v1"
COHORT_SEED = "v24951-native-layout-partial-visible-cohort-v1"
SELECTED_COUNT = 18
ROWS_PER_TASK = 8
DISTRACTOR_ROWS_PER_TASK = 8
PAGE_ROWS_PER_TASK = ROWS_PER_TASK + DISTRACTOR_ROWS_PER_TASK
SELECTED_ENTITY_COUNT = SELECTED_COUNT * ROWS_PER_TASK
SELECTED_RECORD_COUNT = SELECTED_ENTITY_COUNT + DISTRACTOR_ROWS_PER_TASK
ARMS = ("parent_30k", "target_value_30k")
DEVELOPMENT_TARGET_KEYS = (*parent.DEVELOPMENT_TARGET_KEYS, *parent.TARGET_KEYS)
TARGETS = (
    {
        "label": "Agricultural land",
        "indicator": "AG.LND.AGRI.ZS",
        "year": "2021",
    },
)
TARGET_KEYS = ("AG.LND.AGRI.ZS@2021",)
CATALOG_URL = parent.CATALOG_URL
TARGET_URLS = (
    "https://api.worldbank.org/v2/country/all/indicator/AG.LND.AGRI.ZS"
    "?date=2021&format=json&per_page=400",
)
MODEL = parent.MODEL
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
TASK_WALL_SECONDS = parent.TASK_WALL_SECONDS
FETCH_TIMEOUT_SECONDS = parent.FETCH_TIMEOUT_SECONDS
FETCH_MAX_BYTES = parent.FETCH_MAX_BYTES
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS

BUILD_AUDIT = Path(
    f"results/v24951_partial_signature_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v24951_partial_signature_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24951_partial_signature_external_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24951_partial_signature_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v24951_partial_signature_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v24951_partial_signature_external_forward_audit_v1_{DATE}.json"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v24951_partial_signature_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24951_partial_signature_external_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24951_partial_signature_external_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24951_partial_signature_external_v1_{DATE}")
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

CONTROL = Path("scripts/control_v24951_partial_signature_external.py")
RUNNER = Path("scripts/run_v24951_partial_signature_external.py")
CHILD = Path("scripts/run_v24951_partial_signature_external_task.py")
EVALUATOR = Path("scripts/evaluate_v24951_partial_signature_external.py")
TEST = Path("tests/test_v24951_partial_signature_external.py")
CANDIDATE_AUDIT = Path(
    f"results/v24950_mutual_partial_signature_build_audit_v2_{DATE}.json"
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24951_partial_signature_external_contract.py"),
    Path("src/deepwide_agent/v24949_mutual_partial_signature_ledger.py"),
    Path("src/deepwide_agent/v24945_injective_schema_signature_ledger.py"),
    Path("src/deepwide_agent/v24942_compact_schema_bound_record_ledger.py"),
    Path("src/deepwide_agent/v24939_schema_bound_record_ledger.py"),
    Path("src/deepwide_agent/v24933_contextual_record_value_projector.py"),
    Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"),
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
    Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
    Path("src/deepwide_agent/native_search.py"),
    RUNNER,
    CHILD,
    Path("scripts/run_v24941_open_world_ledger_external_task.py"),
    Path("scripts/run_v24940_open_world_ledger_external.py"),
    Path("scripts/run_v24940_open_world_ledger_external_task.py"),
    Path("scripts/run_v24923_target_value_external.py"),
    Path("scripts/run_v24923_target_value_external_task.py"),
    Path("scripts/deepwide_api_lease.py"),
)
BUILD_SOURCES = (
    *RUNTIME_SOURCES,
    CONTROL,
    EVALUATOR,
    TEST,
    CANDIDATE_AUDIT,
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
sealed = parent.sealed
parse_visible_cohort = parent.parse_visible_cohort
parse_visible_countries = parent.parse_visible_countries
parse_visible_entities = parent.parse_visible_entities
protected_watcher_snapshot = parent.protected_watcher_snapshot


def visible_columns() -> list[str]:
    return [
        "Country or area",
        "Cohort",
        "ISO3",
        "Agricultural land [AG.LND.AGRI.ZS] @2021",
    ]


def native_page_columns() -> list[str]:
    return [
        "Area or Country",
        "Cohort",
        "ISO3",
        "Agricultural land (% of land area)",
    ]


def arm_order(opaque_id: str) -> tuple[str, str]:
    if not isinstance(opaque_id, str) or not opaque_id.startswith("task_"):
        raise ValueError("V2.49.51 opaque arm-order key drifted")
    return (
        ARMS
        if int(hashlib.sha256(opaque_id.encode()).hexdigest()[-1], 16) % 2 == 0
        else ARMS[::-1]
    )


def validate_task_vector(
    tasks: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(tasks, (str, bytes)) or len(tasks) != SELECTED_COUNT:
        raise ValueError("V2.49.51 task denominator drifted")
    columns = visible_columns()
    output: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_cohorts: set[str] = set()
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.49.51 runtime input must be opaque_id and question")
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
            raise ValueError("V2.49.51 visible task binding drifted")
        cohort = parse_visible_cohort(question)
        if cohort in seen_cohorts:
            raise ValueError("V2.49.51 visible cohorts are not unique")
        seen_ids.add(opaque)
        seen_cohorts.add(cohort)
        output.append({"opaque_id": opaque, "question": question})
    return output


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order",
    "native_page_columns",
    "parse_visible_cohort",
    "parse_visible_countries",
    "parse_visible_entities",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sealed",
    "sha256",
    "validate_task_vector",
    "visible_columns",
]
