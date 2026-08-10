"""Append-only V2.50.39 recovery contract after V2.50.38 zero-effect failure.

The only forward configuration fix is the inherited robust fetcher's frozen
``max_page_chars=5000`` requirement.  All task/query/order vectors, prompts,
budgets, gates, models, search grouping, and label-blind policies remain those
of V2.50.38.  A new output/result namespace prevents retrying the invalidated
V2.50.38 start.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25038_batching_external_contract as parent


DATE = "20260810"
PROTOCOL_ID = "v25039_source_only_split2_vs_oneshot4_external_recovery_v1"
FAILURE = Path(f"results/v25038_batching_external_pre_effect_failure_v1_{DATE}.json")
BUILD_AUDIT = Path(f"results/v25039_batching_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25039_batching_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25039_batching_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25039_batching_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25039_batching_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25039_batching_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(
    f"results/v25039_batching_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25039_batching_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25039_batching_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25039_batching_external_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_pypi_gold.json"

SOURCE = Path("src/deepwide_agent/v25039_batching_external_contract.py")
RUNNER = Path("scripts/run_v25039_batching_external.py")
CONTROL = Path("scripts/control_v25039_batching_external.py")
TEST = Path("tests/test_v25039_batching_external.py")
EVALUATOR = Path("scripts/evaluate_v25039_batching_external.py")
LOCAL_SOURCES = (SOURCE, RUNNER, CONTROL, TEST)
FORWARD_SOURCES = (SOURCE, RUNNER)

ARMS = parent.ARMS
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
TASK_COUNT = parent.TASK_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
MODEL_OUTPUT_TOKENS = parent.MODEL_OUTPUT_TOKENS
TASK_DEADLINE_SECONDS = parent.TASK_DEADLINE_SECONDS
EVIDENCE_CHARS = parent.EVIDENCE_CHARS
MINIMUM_USABLE_PAGES = parent.MINIMUM_USABLE_PAGES
MINIMUM_RAW_CHARACTERS = parent.MINIMUM_RAW_CHARACTERS
LEAD_CAP = parent.LEAD_CAP
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = {**copy.deepcopy(parent.SEARCH), "max_page_chars": 5_000}
EXPECTED_WATCHERS = parent.EXPECTED_WATCHERS
PROJECTS = parent.PROJECTS
QUERY_PATTERNS = parent.QUERY_PATTERNS
COLUMNS = parent.COLUMNS
FALLBACK_TABLE = parent.FALLBACK_TABLE
LEASE_PATH = parent.LEASE_PATH
SECRET = parent.SECRET
FRESHNESS_PARENT_COMMIT = parent.FRESHNESS_PARENT_COMMIT

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
seal = parent.seal
sealed = parent.sealed
git = parent.git
ordinary = parent.ordinary
watcher_snapshot = parent.watcher_snapshot
task_vector = parent.task_vector
validate_task_vector = parent.validate_task_vector
query_vector = parent.query_vector
arm_order_vector = parent.arm_order_vector
mechanism_gate = parent.mechanism_gate
quality_gate = parent.quality_gate


def source_policy() -> dict[str, Any]:
    value = copy.deepcopy(parent.source_policy())
    value.update(
        {
            "v25038_pre_effect_failure_bound_and_not_retried": True,
            "only_forward_fix_max_page_chars_20000_to_parent_required_5000": True,
            "new_output_and_result_namespace": True,
        }
    )
    return value


def _validate_failure(root: Path) -> dict[str, Any]:
    path = ordinary(root, FAILURE, tracked=True)
    value = __import__("json").loads(path.read_text(encoding="utf-8"))
    unsigned = dict(value)
    observed = unsigned.pop("failure_payload_sha256", None)
    if (
        not isinstance(value, dict)
        or value.get("role") != "v25038_batching_external_pre_effect_failure"
        or value.get("search_provider_attempts") != 0
        or value.get("fetch_helper_calls") != 0
        or value.get("model_provider_attempts") != 0
        or value.get("prediction_freeze_created") is not False
        or value.get("forward_result_created") is not False
        or value.get("pypi_gold_or_evaluator_opened") is not False
        or value.get("retry_resume_or_selective_rerun_under_failed_protocol")
        is not False
        or observed != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.50.39 failure parent drifted")
    return value


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    original = parent.FORWARD_SOURCES
    try:
        parent.FORWARD_SOURCES = FORWARD_SOURCES
        return parent.forward_dependency_closure(root)
    finally:
        parent.FORWARD_SOURCES = original


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {*forward_dependency_closure(root), CONTROL, TEST, FAILURE}
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.50.39 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    failure = _validate_failure(root)
    future = (
        PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT,
        EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, OUTPUT_ROOT, EVALUATOR,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.50.39 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25039_batching_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent_failure": {
            "path": str(FAILURE),
            "sha256": sha256(root / FAILURE),
            "zero_effect": True,
            "invalidated_v25038_start_not_reused": True,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(task_vector()),
            "query_vector_sha256": payload_sha256(query_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "byte_equal_to_v25038": True,
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "physical_query_grouping_split_2_plus_2_vs_one_shot_4",
            "only_recovery_fix": "max_page_chars_20000_to_5000",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "lead_cap_per_arm": LEAD_CAP,
            "control_split_wave_lead_caps": [6, 4],
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "minimum_usable_pages": MINIMUM_USABLE_PAGES,
            "minimum_raw_characters": MINIMUM_RAW_CHARACTERS,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "model": MODEL,
            "search": SEARCH,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_selective_rerun_or_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = dependency_manifest(root, tracked=True)
    build_path = root / BUILD_AUDIT
    expected_build = sha256(build_path) if build_path.is_file() and not build_path.is_symlink() else None
    if (
        copied.get("role") != "v25039_batching_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("build_audit_sha256") != expected_build
        or copied.get("parent_failure")
        != {
            "path": str(FAILURE),
            "sha256": sha256(root / FAILURE),
            "zero_effect": True,
            "invalidated_v25038_start_not_reused": True,
        }
        or copied.get("population", {}).get("task_vector_sha256")
        != payload_sha256(task_vector())
        or copied.get("population", {}).get("query_vector_sha256")
        != payload_sha256(query_vector())
        or copied.get("population", {}).get("arm_order_vector_sha256")
        != payload_sha256(arm_order_vector())
        or copied.get("execution", {}).get("only_recovery_fix")
        != "max_page_chars_20000_to_5000"
        or copied.get("execution", {}).get("search") != SEARCH
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get(
            "deepwidebench_dev64_exact220_or_sota"
        )
        is not False
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.39 protocol drifted")
    _validate_failure(root)
    return copied


__all__ = [
    "ARMS", "BUILD_AUDIT", "CANDIDATE_ARM", "COLUMNS", "CONTROL",
    "CONTROL_ARM", "EVALUATOR", "EVALUATOR_PROTOCOL", "EVIDENCE_CHARS",
    "EXECUTION_START", "EXECUTOR_CONCURRENCY", "EXPECTED_WATCHERS", "FAILURE",
    "FALLBACK_TABLE", "FORWARD_AUDIT", "FORWARD_RESULT", "FORWARD_SOURCES",
    "FRESHNESS_PARENT_COMMIT", "GOLD_SNAPSHOT", "LEAD_CAP", "LEASE_PATH",
    "LOCAL_SOURCES", "MINIMUM_RAW_CHARACTERS", "MINIMUM_USABLE_PAGES", "MODEL",
    "MODEL_OUTPUT_TOKENS", "MODEL_SLOT_CAP", "OUTPUT_ROOT", "POSTAUDIT", "PREAUDIT",
    "PROJECTS", "PROTOCOL", "PROTOCOL_ID", "PREDICTION_FREEZE", "QUERY_PATTERNS",
    "RESULT", "RUNNER", "SEARCH", "SOURCE", "TASK_COUNT", "TASK_DEADLINE_SECONDS",
    "TASK_ROWS", "TEST", "arm_order_vector", "build_protocol", "dependency_manifest",
    "forward_dependency_closure", "git", "mechanism_gate", "ordinary",
    "payload_sha256", "quality_gate", "query_vector", "seal", "sealed", "sha256",
    "source_policy", "task_vector", "validate_protocol", "validate_task_vector",
    "watcher_snapshot",
]
