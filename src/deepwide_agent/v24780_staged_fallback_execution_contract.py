"""Visible-only execution contract for the V2.47.80 external gate.

This module adds process paths and content-free validation around the frozen
V2.47.80 scientific protocol.  It has no evaluator or private-population
capability.  In particular, failure-as-zero preserves the four visible entity
rows instead of using the legacy one-row generic fallback.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v24257_score_first_runtime import validate_visible_task
from .v24743_generic_record_binding import _baseline_matrix
from .v24778_staged_fetch_fallback_runtime import (
    ARMS,
    validate_result as validate_runtime_result,
)
from .v24779_staged_fallback_contract import (
    ENTITY_GROUPS,
    QUESTIONS,
    task_vector as visible_task_vector,
)


DATE = "20260807"
PROTOCOL_ID = "v24780_staged_fetch_fallback_external_v1"
POLICY_ID = "v24780_staged_fallback_external_execution_v1"
PROTOCOL = Path(
    "results/v24780_staged_fallback_external_preregistration_v1_20260807.json"
)
READINESS = Path(f"results/v24780_staged_fallback_control_plane_readiness_v1_{DATE}.json")
PACKAGE_BUILD = Path(f"results/v24780_staged_fallback_package_audit_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24780_staged_fallback_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24780_staged_fallback_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24780_staged_fallback_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24780_staged_fallback_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24780_staged_fallback_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24780_staged_fallback_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = POLICY_ID
LEASE_PURPOSE = "benchmark_external_staged_fetch_fallback_mechanism_gate"
SELECTED_COUNT = 8
ARM_COUNT = 2
EXECUTOR_CONCURRENCY = 8
MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 195.0
EXPERIMENT_WALL_CEILING_SECONDS = 210.0
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
EXPECTED_COLUMNS = ("Organization", "Founded", "Country")
PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 10,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "wall_seconds": 180,
    "model_calls": 2,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
RESULT_NAME = "result.json"
MODEL_RECEIPT_NAME = "model_slot_receipt.json"
TRANSPORT_RECEIPT_NAME = "transport_health.json"
TERMINAL_RECEIPT_NAME = "child_terminal_receipt.json"
PARENT_RECEIPT_NAME = "parent_exit_receipt.json"
VISIBLE_TASK_NAME = "visible_task.json"
FORWARD_ROW_KEYS = frozenset(
    {"ordinal", "opaque_id", "predictions", "prediction_sha256", "runtime_result_valid"}
)
SUMMARY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "selected_tasks",
        "selected_arm_predictions",
        "valid_task_results",
        "projected_failure_tasks",
        "forward_wall_seconds",
        "experiment_wall_ceiling_seconds",
        "within_experiment_wall_ceiling",
        "changed_task_count",
        "changed_cell_count",
        "founded_changed_cell_count",
        "country_changed_cell_count",
        "nonunknown_changed_cell_count",
        "projection_backed_support_set_count",
        "initial_fetch_request_count",
        "reserve_fetch_request_count",
        "actual_fetch_request_count",
        "initial_usable_page_count",
        "reserve_usable_page_count",
        "actual_usable_page_count",
        "final_entity_slots_with_two_usable_identity_sources",
        "entity_slots_brought_to_two_sources_by_reserve",
        "reserve_target_entity_count",
        "failed_url_retry_count",
        "scheduler_contract_failed_task_count",
        "candidate_not_only_unknown_task_count",
        "semantic_safety_contract_failed_task_count",
        "parent_failure_taxonomy_counts",
        "all_task_ordinals_submitted_once",
        "resume_retry_skip_or_selective_rerun",
        "private_question_query_url_page_prediction_or_value_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "summary_payload_sha256",
    }
)
FREEZE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "policy_id",
        "selected_tasks",
        "selected_arm_predictions",
        "predictions_sha256",
        "run_summary_sha256",
        "all_predictions_terminal_before_private_truth_or_quality_open",
        "private_truth_or_quality_path_opened_or_hashed",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "freeze_payload_sha256",
    }
)
FORWARD_RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "policy_id",
        "created_at_unix",
        "selected_tasks",
        "terminal_arm_predictions",
        "prediction_freeze_sha256",
        "run_summary_sha256",
        "execution_start_sha256",
        "all_predictions_terminal_before_private_truth_or_quality_open",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "quality_or_evaluator_called",
        "resume_retry_skip_or_selective_rerun",
        "result_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in PROTECTED_WATCHERS:
        proc = proc_root / str(pid)
        stat = proc / "stat"
        cmdline = proc / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.47.80 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.47.80 protected watcher identity drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def visible_entities(question: str) -> list[str]:
    match = re.fullmatch(
        r"Use public web sources to return one Markdown table about these organizations:\n"
        r"<ENTITIES>\n(.*)\n</ENTITIES>\n"
        r"The column names are: Organization, Founded, Country\. "
        r"Use a four-digit founding year and the English country name\. "
        r"Use Unknown unless an exact value is supported by two independent public sources\. "
        r"Return one table only\.",
        str(question).strip(),
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("V2.47.80 visible task syntax drifted")
    values: list[str] = []
    for index, line in enumerate(match.group(1).splitlines(), 1):
        prefix = f"{index}. "
        if not line.startswith(prefix):
            raise ValueError("V2.47.80 visible entity numbering drifted")
        value = line[len(prefix) :].strip()
        if not value or "|" in value or "\n" in value or "\r" in value:
            raise ValueError("V2.47.80 visible entity is unsafe")
        values.append(value)
    if len(values) != 4 or len(set(values)) != 4:
        raise ValueError("V2.47.80 visible entity vector drifted")
    return values


def task_vector() -> list[dict[str, str]]:
    tasks = visible_task_vector()
    if (
        len(tasks) != SELECTED_COUNT
        or len(QUESTIONS) != SELECTED_COUNT
        or len(ENTITY_GROUPS) != SELECTED_COUNT
    ):
        raise RuntimeError("V2.47.80 visible population size drifted")
    output = []
    for ordinal, task in enumerate(tasks, 1):
        visible = validate_visible_task(task)
        entities = visible_entities(visible["question"])
        if entities != list(ENTITY_GROUPS[ordinal - 1]):
            raise RuntimeError("V2.47.80 visible population round trip drifted")
        output.append(visible)
    return output


def failure_prediction(task: Mapping[str, Any]) -> str:
    visible = validate_visible_task(task)
    entities = visible_entities(visible["question"])
    return (
        "```markdown\n| Organization | Founded | Country |\n"
        "| --- | --- | --- |\n"
        + "\n".join(f"| {entity} | Unknown | Unknown |" for entity in entities)
        + "\n```"
    )


def failure_predictions(task: Mapping[str, Any]) -> dict[str, str]:
    table = failure_prediction(task)
    return {arm: table for arm in ARMS}


def _unknown(value: object) -> bool:
    return str(value or "").strip().casefold() in {
        "",
        "-",
        "—",
        "?",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "未知",
        "不详",
    }


def content_free_observation(
    result: Mapping[str, Any], task: Mapping[str, Any]
) -> dict[str, int | bool]:
    validated = validate_runtime_result(result)
    visible = validate_visible_task(task)
    expected_entities = visible_entities(visible["question"])
    if validated.get("opaque_id") != visible["opaque_id"]:
        raise ValueError("V2.47.80 runtime opaque identity drifted")
    baseline = validated["predictions"]["baseline"]
    candidate = validated["predictions"]["staged_fallback_semantic"]
    before_columns, before_rows = _baseline_matrix(baseline)
    after_columns, after_rows = _baseline_matrix(candidate)
    if (
        before_columns != list(EXPECTED_COLUMNS)
        or after_columns != list(EXPECTED_COLUMNS)
        or len(before_rows) != 4
        or len(after_rows) != 4
        or [row[0] for row in before_rows] != expected_entities
        or [row[0] for row in after_rows] != expected_entities
    ):
        raise ValueError("V2.47.80 runtime table identity surface drifted")
    changed = founded = country = nonunknown = 0
    for before, after in zip(before_rows, after_rows, strict=True):
        for index in (1, 2):
            if before[index] == after[index]:
                continue
            changed += 1
            founded += int(index == 1)
            country += int(index == 2)
            nonunknown += int(not _unknown(before[index]))
    scheduler = validated["scheduler_receipt"]
    semantic = validated["semantic_receipt"]
    if changed != int(semantic["final_changed_cell_count"]):
        raise ValueError("V2.47.80 semantic changed-cell receipt drifted")
    return {
        "prediction_changed": baseline != candidate,
        "changed_cell_count": changed,
        "founded_changed_cell_count": founded,
        "country_changed_cell_count": country,
        "nonunknown_changed_cell_count": nonunknown,
        "projection_backed_support_set_count": int(
            semantic["projection_backed_eligible_support_set_count"]
        ),
        "initial_fetch_request_count": int(
            scheduler["initial_fetch_request_count"]
        ),
        "reserve_fetch_request_count": int(
            scheduler["reserve_fetch_request_count"]
        ),
        "actual_fetch_request_count": int(
            scheduler["actual_fetch_request_count"]
        ),
        "initial_usable_page_count": int(
            scheduler["initial_usable_page_count"]
        ),
        "reserve_usable_page_count": int(
            scheduler["reserve_usable_page_count"]
        ),
        "actual_usable_page_count": int(
            scheduler["actual_usable_page_count"]
        ),
        "final_entity_slots_with_two_usable_identity_sources": int(
            scheduler["final_entities_with_two_or_more_usable_identity_sources"]
        ),
        "entity_slots_brought_to_two_sources_by_reserve": sum(
            initial < 2 <= final
            for initial, final in zip(
                scheduler["initial_usable_identity_source_count_vector"],
                scheduler["final_usable_identity_source_count_vector"],
                strict=True,
            )
        ),
        "reserve_target_entity_count": int(
            scheduler["reserve_target_entity_count"]
        ),
        "failed_url_retry_count": int(scheduler["failed_url_retry_count"]),
        "scheduler_contract": bool(
            scheduler["same_model_query_and_total_fetch_target_caps_as_parent"]
            and scheduler["failed_url_retried"] is False
            and scheduler[
                "field_label_candidate_value_or_model_judgment_used_for_reserve_routing"
            ]
            is False
            and scheduler["actual_fetch_request_count"] <= 10
            and scheduler["failed_url_retry_count"] == 0
            and semantic["new_model_search_fetch_or_evaluator_effect"] == 0
        ),
        "candidate_changes_only_unknown": bool(
            semantic["candidate_changes_only_baseline_unknown_cells"]
        ),
        "semantic_safety_contract": bool(
            semantic["semantic_candidate_requires_projection_binding"]
            and semantic["semantic_candidate_requires_two_independent_sources"]
            and semantic["any_same_cell_value_conflict_abstains"]
            and scheduler["query_text_used_to_establish_alignment"] is False
            and scheduler["strict_two_independent_same_value_gate_changed"] is False
        ),
    }


def validate_forward_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    if (
        set(copied) != FORWARD_ROW_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or not 1 <= copied["ordinal"] <= SELECTED_COUNT
        or not isinstance(copied.get("opaque_id"), str)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(ARMS)
        or any(not isinstance(predictions[arm], str) for arm in ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or not isinstance(copied.get("runtime_result_valid"), bool)
    ):
        raise ValueError("V2.47.80 frozen prediction row drifted")
    expected = task_vector()[copied["ordinal"] - 1]
    if copied["opaque_id"] != expected["opaque_id"]:
        raise ValueError("V2.47.80 frozen prediction identity drifted")
    expected_entities = visible_entities(expected["question"])
    for arm in ARMS:
        columns, rows = _baseline_matrix(predictions[arm])
        if columns != list(EXPECTED_COLUMNS) or [row[0] for row in rows] != expected_entities:
            raise ValueError("V2.47.80 frozen prediction row identity drifted")
    if not copied["runtime_result_valid"] and predictions != failure_predictions(expected):
        raise ValueError("V2.47.80 failure-as-zero row drifted")
    return copied


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def validate_run_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    counts = SUMMARY_KEYS - {
        "role",
        "policy_id",
        "forward_wall_seconds",
        "experiment_wall_ceiling_seconds",
        "within_experiment_wall_ceiling",
        "parent_failure_taxonomy_counts",
        "all_task_ordinals_submitted_once",
        "resume_retry_skip_or_selective_rerun",
        "private_question_query_url_page_prediction_or_value_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "summary_payload_sha256",
    }
    taxonomy = copied.get("parent_failure_taxonomy_counts")
    if (
        set(copied) != SUMMARY_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24780_staged_fallback_forward_run_summary"
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied.get("selected_tasks") != SELECTED_COUNT
        or copied.get("selected_arm_predictions") != SELECTED_COUNT * ARM_COUNT
        or copied.get("valid_task_results") + copied.get("projected_failure_tasks")
        != SELECTED_COUNT
        or isinstance(copied.get("forward_wall_seconds"), bool)
        or not isinstance(copied.get("forward_wall_seconds"), (int, float))
        or not 0 <= float(copied["forward_wall_seconds"])
        or copied.get("experiment_wall_ceiling_seconds")
        != EXPERIMENT_WALL_CEILING_SECONDS
        or copied.get("within_experiment_wall_ceiling")
        is not (
            float(copied["forward_wall_seconds"])
            <= EXPERIMENT_WALL_CEILING_SECONDS
        )
        or copied.get("changed_task_count") > copied.get("valid_task_results")
        or copied.get("changed_cell_count")
        != copied.get("founded_changed_cell_count")
        + copied.get("country_changed_cell_count")
        or copied.get("actual_fetch_request_count")
        != copied.get("initial_fetch_request_count")
        + copied.get("reserve_fetch_request_count")
        or copied.get("actual_fetch_request_count") > SELECTED_COUNT * 10
        or copied.get("initial_fetch_request_count") > SELECTED_COUNT * 8
        or copied.get("reserve_fetch_request_count") > SELECTED_COUNT * 2
        or copied.get("actual_usable_page_count")
        != copied.get("initial_usable_page_count")
        + copied.get("reserve_usable_page_count")
        or copied.get("actual_usable_page_count")
        > copied.get("actual_fetch_request_count")
        or copied.get("failed_url_retry_count") != 0
        or not isinstance(taxonomy, Mapping)
        or any(
            not isinstance(name, str)
            or not name
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
            for name, amount in taxonomy.items()
        )
        or sum(taxonomy.values()) != SELECTED_COUNT
        or copied.get("all_task_ordinals_submitted_once") is not True
        or copied.get("resume_retry_skip_or_selective_rerun") is not False
        or copied.get("private_question_query_url_page_prediction_or_value_emitted")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or not _sealed(copied, "summary_payload_sha256")
    ):
        raise ValueError("V2.47.80 run summary drifted")
    return copied


def validate_prediction_freeze(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != FREEZE_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24780_staged_fallback_prediction_freeze"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("policy_id") != POLICY_ID
        or copied.get("selected_tasks") != SELECTED_COUNT
        or copied.get("selected_arm_predictions") != SELECTED_COUNT * ARM_COUNT
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("predictions_sha256", "")))
        is None
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("run_summary_sha256", "")))
        is None
        or copied.get("all_predictions_terminal_before_private_truth_or_quality_open")
        is not True
        or copied.get("private_truth_or_quality_path_opened_or_hashed") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or not _sealed(copied, "freeze_payload_sha256")
    ):
        raise ValueError("V2.47.80 prediction freeze drifted")
    return copied


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != FORWARD_RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v24780_staged_fallback_forward_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("selected_tasks") != SELECTED_COUNT
        or copied.get("terminal_arm_predictions") != SELECTED_COUNT * ARM_COUNT
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name, ""))) is None
            for name in (
                "prediction_freeze_sha256",
                "run_summary_sha256",
                "execution_start_sha256",
            )
        )
        or copied.get("all_predictions_terminal_before_private_truth_or_quality_open")
        is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("quality_or_evaluator_called") is not False
        or copied.get("resume_retry_skip_or_selective_rerun") is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.47.80 forward result drifted")
    return copied


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "content_free_observation",
    "failure_prediction",
    "failure_predictions",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_forward_result",
    "validate_forward_row",
    "validate_prediction_freeze",
    "validate_run_summary",
    "visible_entities",
]
