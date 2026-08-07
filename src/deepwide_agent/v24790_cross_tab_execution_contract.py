"""Execution and freeze contract for the V2.47.90 selected-target wave.

Only visible ``opaque_id``/``question`` tasks and fixed-vocabulary receipts
cross the runtime boundary.  Benchmark labels, truth, evaluator state, and the
private V2.47.89 population are deliberately outside this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24778_staged_fetch_fallback_runtime as base
from . import v24790_cross_tab_integration as integration
from . import v24790_full_catalog_selected_target as selected
from .v24257_score_first_runtime import validate_visible_task
from .v24743_generic_record_binding import _baseline_matrix
from .v24789_cross_tab_population_contract import task_vector as visible_task_vector


DATE = "20260807"
PROTOCOL_ID = "v24790_selected_unknown_cross_tab_external_v2"
POLICY_ID = "v24790_selected_unknown_cross_tab_execution_v2"
PROTOCOL = Path(f"results/v24790_cross_tab_external_preregistration_v2_{DATE}.json")
INTEGRATION_BUILD = Path(
    f"results/v24790_cross_tab_integration_build_audit_v2_{DATE}.json"
)
READINESS = Path(f"results/v24790_cross_tab_control_plane_readiness_v2_{DATE}.json")
PACKAGE_BUILD = Path(f"results/v24790_cross_tab_package_audit_v2_{DATE}.json")
PREAUDIT = Path(f"results/v24790_cross_tab_preactivation_audit_v2_{DATE}.json")
ACTIVATION = Path(f"results/v24790_cross_tab_activation_v2_{DATE}.json")
EXECUTION_START = Path(f"results/v24790_cross_tab_execution_start_v2_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24790_cross_tab_forward_result_v2_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24790_cross_tab_forward_audit_v2_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24790_cross_tab_external_v2_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = POLICY_ID
LEASE_PURPOSE = "benchmark_external_selected_unknown_same_group_mechanism_gate"

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

FORWARD_STATUSES = (*integration.STATUSES, "parent_failure")
STATUS_COUNT_FIELDS = tuple(f"status_{name}_count" for name in FORWARD_STATUSES)
SELECTED_SUM_FIELDS = (
    "target_count",
    "unknown_target_count",
    "zero_projection_target_count",
    "projection_group_count",
    "unknown_projection_group_count",
    "unknown_single_source_projection_group_count",
    "unknown_two_or_more_source_projection_group_count",
    "catalog_candidate_group_count",
    "catalog_eligible_support_set_count",
    "projection_backed_support_group_count",
    "unconflicted_unknown_proposal_group_count",
    "changed_target_count",
    "changed_to_projected_value_group_count",
    "strict_joint_safe_change_group_count",
)
SELECTED_TASK_FLAGS = (
    "has_unknown_projection_group",
    "has_unknown_two_or_more_source_projection_group",
    "has_projection_backed_support_group",
    "has_unconflicted_unknown_proposal_group",
    "has_changed_target",
    "has_strict_joint_safe_change_group",
)
SELECTED_TASK_COUNT_FIELDS = tuple(f"{name}_task_count" for name in SELECTED_TASK_FLAGS)
OBSERVATION_KEYS = frozenset(
    {
        "status",
        "base_result_valid",
        "selected_receipt_valid",
        "prediction_changed",
        "changed_cell_count",
        "nonunknown_changed_cell_count",
        "selected_counts",
        "selected_task_local",
        "selected_receipt_contract",
        "initial_fetch_request_count",
        "reserve_fetch_request_count",
        "actual_fetch_request_count",
        "initial_usable_page_count",
        "reserve_usable_page_count",
        "actual_usable_page_count",
        "failed_url_retry_count",
        "scheduler_contract",
        "semantic_safety_contract",
    }
)
FORWARD_ROW_KEYS = frozenset(
    {
        "ordinal",
        "opaque_id",
        "predictions",
        "prediction_sha256",
        "runtime_status",
        "projection_valid",
        "base_result_valid",
        "selected_receipt_valid",
    }
)
SUMMARY_COUNT_FIELDS = (
    "selected_tasks",
    "selected_arm_predictions",
    "valid_projection_results",
    "base_valid_task_results",
    "selected_receipt_valid_task_count",
    "projected_failure_tasks",
    "prediction_changed_task_count",
    "changed_cell_count",
    "nonunknown_changed_cell_count",
    "initial_fetch_request_count",
    "reserve_fetch_request_count",
    "actual_fetch_request_count",
    "initial_usable_page_count",
    "reserve_usable_page_count",
    "actual_usable_page_count",
    "failed_url_retry_count",
    "scheduler_contract_failed_task_count",
    "semantic_safety_contract_failed_task_count",
    *STATUS_COUNT_FIELDS,
    *SELECTED_TASK_COUNT_FIELDS,
    *SELECTED_SUM_FIELDS,
)
SUMMARY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        *SUMMARY_COUNT_FIELDS,
        "forward_wall_seconds",
        "experiment_wall_ceiling_seconds",
        "within_experiment_wall_ceiling",
        "parent_failure_taxonomy_counts",
        "all_task_ordinals_submitted_once",
        "missing_selected_receipts_not_aggregated_as_zero",
        "cross_task_or_cross_group_margins_used_as_joint",
        "resume_retry_skip_or_selective_rerun",
        "private_question_query_url_host_page_or_private_content_hash_emitted",
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
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
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
        stat_path = proc / "stat"
        cmdline = proc / "cmdline"
        if not stat_path.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.47.90 protected watcher is absent")
        raw = stat_path.read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.47.90 protected watcher identity drifted")
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
        raise ValueError("V2.47.90 visible task syntax drifted")
    values: list[str] = []
    for index, line in enumerate(match.group(1).splitlines(), 1):
        prefix = f"{index}. "
        if not line.startswith(prefix):
            raise ValueError("V2.47.90 visible entity numbering drifted")
        value = line[len(prefix) :].strip()
        if not value or "|" in value or "\n" in value or "\r" in value:
            raise ValueError("V2.47.90 visible entity is unsafe")
        values.append(value)
    if len(values) != 4 or len(set(values)) != 4:
        raise ValueError("V2.47.90 visible entity vector drifted")
    return values


def task_vector() -> list[dict[str, str]]:
    tasks = visible_task_vector()
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.47.90 visible population size drifted")
    output = []
    for task in tasks:
        visible = validate_visible_task(task)
        visible_entities(visible["question"])
        if set(visible) != {"opaque_id", "question"}:
            raise RuntimeError("V2.47.90 runtime task key drifted")
        output.append(visible)
    if len({task["opaque_id"] for task in output}) != SELECTED_COUNT:
        raise RuntimeError("V2.47.90 opaque identity vector drifted")
    return output


def failure_prediction(task: Mapping[str, Any]) -> str:
    entities = visible_entities(validate_visible_task(task)["question"])
    return (
        "```markdown\n| Organization | Founded | Country |\n"
        "| --- | --- | --- |\n"
        + "\n".join(f"| {entity} | Unknown | Unknown |" for entity in entities)
        + "\n```"
    )


def failure_predictions(task: Mapping[str, Any]) -> dict[str, str]:
    value = failure_prediction(task)
    return {arm: value for arm in base.ARMS}


def _unknown(value: object) -> bool:
    return str(value or "").strip().casefold() in {
        "", "-", "—", "?", "n/a", "na", "none", "null", "unknown", "未知", "不详"
    }


def content_free_observation(
    result: Mapping[str, Any], task: Mapping[str, Any]
) -> dict[str, Any]:
    validated = integration.validate_projection(result)
    visible = validate_visible_task(task)
    if validated["opaque_id"] != visible["opaque_id"]:
        raise ValueError("V2.47.90 runtime opaque identity drifted")
    base_valid = bool(validated["base_result_valid"])
    receipt_valid = bool(validated["selected_receipt_valid"])
    changed = nonunknown = 0
    scheduler: Mapping[str, Any] | None = None
    semantic: Mapping[str, Any] | None = None
    if base_valid:
        expected_entities = visible_entities(visible["question"])
        before_columns, before_rows = _baseline_matrix(validated["predictions"]["baseline"])
        after_columns, after_rows = _baseline_matrix(
            validated["predictions"]["staged_fallback_semantic"]
        )
        if (
            before_columns != list(EXPECTED_COLUMNS)
            or after_columns != list(EXPECTED_COLUMNS)
            or [row[0] for row in before_rows] != expected_entities
            or [row[0] for row in after_rows] != expected_entities
        ):
            raise ValueError("V2.47.90 runtime table identity surface drifted")
        for before, after in zip(before_rows, after_rows, strict=True):
            for index in (1, 2):
                if before[index] != after[index]:
                    changed += 1
                    nonunknown += int(not _unknown(before[index]))
        scheduler = validated["scheduler_receipt"]
        semantic = validated["semantic_receipt"]
        if changed != int(semantic["final_changed_cell_count"]):
            raise ValueError("V2.47.90 changed-cell receipt drifted")

    selected_counts: dict[str, int] | None = None
    task_local: dict[str, bool] | None = None
    receipt_contract = False
    if receipt_valid:
        receipt = selected.validate_receipt(validated["selected_cross_tab_receipt"])
        cross_tab = receipt["cross_tab_receipt"]
        selected_counts = {name: int(cross_tab[name]) for name in SELECTED_SUM_FIELDS}
        local = cross_tab["task_local_joint"]
        task_local = {name: bool(local[name]) for name in SELECTED_TASK_FLAGS}
        receipt_contract = bool(
            receipt["selected_target_count"] == 1
            and receipt["selected_target_is_baseline_unknown"]
            and receipt["selected_by_canonical_row_major_order"]
            and receipt["full_target_catalog_validated"]
            and receipt["full_target_catalog_and_projection_vector_mutated"] is False
            and receipt["single_target_catalog_rebuilt"] is False
            and receipt["other_visible_entities_retained_as_segment_boundaries"]
            and receipt["prediction_bytes_changed_by_observer"] is False
            and cross_tab["same_catalog_and_predictions_observed_without_mutation"]
            and cross_tab["cross_task_or_cross_group_margins_used_as_joint"] is False
        )

    scheduler_contract = bool(
        base_valid
        and scheduler is not None
        and scheduler["same_model_query_and_total_fetch_target_caps_as_parent"]
        and scheduler["failed_url_retried"] is False
        and scheduler["field_label_candidate_value_or_model_judgment_used_for_reserve_routing"] is False
        and scheduler["actual_fetch_request_count"] <= LIMITS["fetch_targets"]
        and scheduler["failed_url_retry_count"] == 0
    )
    semantic_safety = bool(
        base_valid
        and semantic is not None
        and semantic["candidate_changes_only_baseline_unknown_cells"]
        and semantic["semantic_candidate_requires_projection_binding"]
        and semantic["semantic_candidate_requires_two_independent_sources"]
        and semantic["any_same_cell_value_conflict_abstains"]
        and semantic["new_model_search_fetch_or_evaluator_effect"] == 0
    )
    value = {
        "status": validated["status"],
        "base_result_valid": base_valid,
        "selected_receipt_valid": receipt_valid,
        "prediction_changed": bool(
            base_valid
            and validated["predictions"]["baseline"]
            != validated["predictions"]["staged_fallback_semantic"]
        ),
        "changed_cell_count": changed,
        "nonunknown_changed_cell_count": nonunknown,
        "selected_counts": selected_counts,
        "selected_task_local": task_local,
        "selected_receipt_contract": receipt_contract,
        "initial_fetch_request_count": int(scheduler["initial_fetch_request_count"])
        if scheduler is not None else 0,
        "reserve_fetch_request_count": int(scheduler["reserve_fetch_request_count"])
        if scheduler is not None else 0,
        "actual_fetch_request_count": int(scheduler["actual_fetch_request_count"])
        if scheduler is not None else 0,
        "initial_usable_page_count": int(scheduler["initial_usable_page_count"])
        if scheduler is not None else 0,
        "reserve_usable_page_count": int(scheduler["reserve_usable_page_count"])
        if scheduler is not None else 0,
        "actual_usable_page_count": int(scheduler["actual_usable_page_count"])
        if scheduler is not None else 0,
        "failed_url_retry_count": int(scheduler["failed_url_retry_count"])
        if scheduler is not None else 0,
        "scheduler_contract": scheduler_contract,
        "semantic_safety_contract": semantic_safety,
    }
    if set(value) != OBSERVATION_KEYS:
        raise ValueError("V2.47.90 observation schema drifted")
    if (selected_counts is None) is not (not receipt_valid):
        raise ValueError("V2.47.90 missing receipt did not remain explicit")
    if (task_local is None) is not (not receipt_valid):
        raise ValueError("V2.47.90 missing joint did not remain explicit")
    if receipt_valid and not receipt_contract:
        raise ValueError("V2.47.90 selected receipt safety contract drifted")
    return value


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
        or copied.get("runtime_status") not in FORWARD_STATUSES
        or not isinstance(copied.get("projection_valid"), bool)
        or not isinstance(copied.get("base_result_valid"), bool)
        or not isinstance(copied.get("selected_receipt_valid"), bool)
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(base.ARMS)
        or any(not isinstance(predictions[arm], str) for arm in base.ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(base.ARMS)
        or any(hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in base.ARMS)
    ):
        raise ValueError("V2.47.90 frozen prediction row drifted")
    expected = task_vector()[copied["ordinal"] - 1]
    if copied["opaque_id"] != expected["opaque_id"]:
        raise ValueError("V2.47.90 frozen prediction identity drifted")
    expected_entities = visible_entities(expected["question"])
    for arm in base.ARMS:
        columns, rows = _baseline_matrix(predictions[arm])
        if columns != list(EXPECTED_COLUMNS) or [row[0] for row in rows] != expected_entities:
            raise ValueError("V2.47.90 frozen prediction table drifted")
    if not copied["base_result_valid"] and predictions != failure_predictions(expected):
        raise ValueError("V2.47.90 failure-as-zero row drifted")
    if copied["runtime_status"] == "parent_failure" and copied["projection_valid"]:
        raise ValueError("V2.47.90 parent failure projection drifted")
    if copied["runtime_status"] != "parent_failure" and not copied["projection_valid"]:
        raise ValueError("V2.47.90 child projection validity drifted")
    if copied["selected_receipt_valid"] is not (copied["runtime_status"] == "validated"):
        raise ValueError("V2.47.90 selected receipt status drifted")
    return copied


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def validate_run_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    taxonomy = copied.get("parent_failure_taxonomy_counts")
    if (
        set(copied) != SUMMARY_KEYS
        or copied.get("artifact_version") != 2
        or copied.get("role") != "v24790_cross_tab_forward_run_summary_v2"
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in SUMMARY_COUNT_FIELDS
        )
        or copied["selected_tasks"] != SELECTED_COUNT
        or copied["selected_arm_predictions"] != SELECTED_COUNT * ARM_COUNT
        or sum(copied[name] for name in STATUS_COUNT_FIELDS) != SELECTED_COUNT
        or copied["valid_projection_results"] != SELECTED_COUNT - copied["status_parent_failure_count"]
        or copied["base_valid_task_results"]
        != copied["status_validated_count"]
        + copied["status_no_baseline_unknown_target_count"]
        + copied["status_private_catalog_absent_count"]
        + copied["status_selected_catalog_or_observer_failure_count"]
        or copied["selected_receipt_valid_task_count"] != copied["status_validated_count"]
        or copied["projected_failure_tasks"]
        != copied["status_base_runtime_failure_count"] + copied["status_parent_failure_count"]
        or copied["prediction_changed_task_count"] > copied["base_valid_task_results"]
        or copied["nonunknown_changed_cell_count"] != 0
        or copied["actual_fetch_request_count"]
        != copied["initial_fetch_request_count"] + copied["reserve_fetch_request_count"]
        or copied["actual_fetch_request_count"] > SELECTED_COUNT * LIMITS["fetch_targets"]
        or copied["actual_usable_page_count"]
        != copied["initial_usable_page_count"] + copied["reserve_usable_page_count"]
        or copied["actual_usable_page_count"] > copied["actual_fetch_request_count"]
        or copied["failed_url_retry_count"] != 0
        or copied["target_count"] != copied["selected_receipt_valid_task_count"]
        or copied["unknown_target_count"] != copied["selected_receipt_valid_task_count"]
        or copied["unknown_projection_group_count"] > copied["projection_group_count"]
        or copied["unknown_single_source_projection_group_count"]
        + copied["unknown_two_or_more_source_projection_group_count"]
        != copied["unknown_projection_group_count"]
        or copied["projection_backed_support_group_count"] > copied["catalog_eligible_support_set_count"]
        or copied["projection_backed_support_group_count"] > copied["projection_group_count"]
        or copied["unconflicted_unknown_proposal_group_count"] > copied["projection_backed_support_group_count"]
        or copied["changed_to_projected_value_group_count"] > copied["changed_target_count"]
        or copied["strict_joint_safe_change_group_count"] > copied["unconflicted_unknown_proposal_group_count"]
        or copied["strict_joint_safe_change_group_count"] > copied["changed_to_projected_value_group_count"]
        or any(copied[name] > copied["selected_receipt_valid_task_count"] for name in SELECTED_TASK_COUNT_FIELDS)
        or copied["has_strict_joint_safe_change_group_task_count"]
        > copied["has_unconflicted_unknown_proposal_group_task_count"]
        or copied["has_strict_joint_safe_change_group_task_count"]
        > copied["has_changed_target_task_count"]
        or not isinstance(taxonomy, Mapping)
        or any(
            not isinstance(name, str) or not name
            or isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0
            for name, amount in taxonomy.items()
        )
        or sum(taxonomy.values()) != SELECTED_COUNT
        or isinstance(copied.get("forward_wall_seconds"), bool)
        or not isinstance(copied.get("forward_wall_seconds"), (int, float))
        or float(copied["forward_wall_seconds"]) < 0
        or copied.get("experiment_wall_ceiling_seconds") != EXPERIMENT_WALL_CEILING_SECONDS
        or copied.get("within_experiment_wall_ceiling")
        is not (float(copied["forward_wall_seconds"]) <= EXPERIMENT_WALL_CEILING_SECONDS)
        or copied.get("all_task_ordinals_submitted_once") is not True
        or copied.get("missing_selected_receipts_not_aggregated_as_zero") is not True
        or copied.get("cross_task_or_cross_group_margins_used_as_joint") is not False
        or copied.get("resume_retry_skip_or_selective_rerun") is not False
        or copied.get("private_question_query_url_host_page_or_private_content_hash_emitted") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or not _sealed(copied, "summary_payload_sha256")
    ):
        raise ValueError("V2.47.90 run summary drifted")
    return copied


def validate_prediction_freeze(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != FREEZE_KEYS
        or copied.get("artifact_version") != 2
        or copied.get("role") != "v24790_cross_tab_prediction_freeze_v2"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("policy_id") != POLICY_ID
        or copied.get("selected_tasks") != SELECTED_COUNT
        or copied.get("selected_arm_predictions") != SELECTED_COUNT * ARM_COUNT
        or any(re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name, ""))) is None for name in ("predictions_sha256", "run_summary_sha256"))
        or copied.get("all_predictions_terminal_before_private_truth_or_quality_open") is not True
        or copied.get("private_truth_or_quality_path_opened_or_hashed") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or not _sealed(copied, "freeze_payload_sha256")
    ):
        raise ValueError("V2.47.90 prediction freeze drifted")
    return copied


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied) != FORWARD_RESULT_KEYS
        or copied.get("artifact_version") != 2
        or copied.get("role") != "v24790_cross_tab_forward_result_v2"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("selected_tasks") != SELECTED_COUNT
        or copied.get("terminal_arm_predictions") != SELECTED_COUNT * ARM_COUNT
        or any(re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name, ""))) is None for name in ("prediction_freeze_sha256", "run_summary_sha256", "execution_start_sha256"))
        or copied.get("all_predictions_terminal_before_private_truth_or_quality_open") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or copied.get("quality_or_evaluator_called") is not False
        or copied.get("resume_retry_skip_or_selective_rerun") is not False
        or not _sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.47.90 forward result drifted")
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
