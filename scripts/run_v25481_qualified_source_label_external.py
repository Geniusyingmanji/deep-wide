#!/usr/bin/env python3
"""Run the single authorized V2.54.81 qualified-label shared-parent gate."""

from __future__ import annotations

import copy
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24982_paired_production_runtime as counters
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap
from deepwide_agent import v25370_shared_synthesis_changed_safe_runtime as base_runtime
from deepwide_agent import v25375_schema_total_changed_safe_runtime as parent_runtime
from deepwide_agent import v25472_qualified_source_label_runtime as runtime
from deepwide_agent import v25481_qualified_source_label_external_contract as contract
from scripts import run_v25469_row_key_source_external as harness
from scripts import v25478_clone_safe_runner_namespace as clone_safe


TASK_ROLE = "v25481_qualified_source_label_frozen_task_result"
FORWARD_ROLE = "v25481_qualified_source_label_external_forward_result"
FREEZE_ROLE = "v25481_qualified_source_label_prediction_freeze"
ARMS = runtime.ARMS

SOURCE_NAMES = (
    "_read", "_publish_json", "_publish_jsonl", "_clean_pushed",
    "_lease_inactive", "_active_conflicts", "_search", "_empty_effect_snapshot",
    "_effect_snapshot", "_health", "_health_snapshot", "_validate_cost",
    "_prepare_output", "_fallback_prediction",
    "_task_metadata", "_metadata", "_decode_completed", "_terminal_outer_failure",
    "_from_runtime", "validate_task_row", "validate_aggregate", "aggregate_rows",
    "run_one_task", "run_forward",
)
_SOURCE_FUNCTIONS = {name: getattr(harness, name) for name in SOURCE_NAMES}
_NAMESPACE, _CLONES = clone_safe.clone_group(
    _SOURCE_FUNCTIONS,
    visible_globals=harness.__dict__,
    overrides={
        "contract": contract,
        "runtime": runtime,
        "counters": counters,
        "cap": cap,
        "base_runtime": base_runtime,
        "parent_runtime": parent_runtime,
        "TASK_ROLE": TASK_ROLE,
        "FORWARD_ROLE": FORWARD_ROLE,
        "FREEZE_ROLE": FREEZE_ROLE,
        "ARMS": ARMS,
    },
    rename_from="v25469",
    rename_to="v25481",
)
_CLONE_NAMESPACE_RECEIPT = clone_safe.content_free_receipt(
    _SOURCE_FUNCTIONS, _NAMESPACE
)
if (
    _CLONE_NAMESPACE_RECEIPT["unresolved_function_count"] != 0
    or _CLONE_NAMESPACE_RECEIPT["unresolved_global_name_count"] != 0
    or not all(
        _CLONE_NAMESPACE_RECEIPT[name]
        for name in (
            "fcntl_resolved",
            "socket_resolved",
            "subprocess_resolved",
            "thread_pool_executor_resolved",
            "as_completed_resolved",
            "lease_helper_resolved",
        )
    )
):
    raise RuntimeError("V2.54.81 clone namespace is incomplete")

globals().update({name:_CLONES[name] for name in (
    "_read", "_publish_json", "_publish_jsonl", "_clean_pushed",
    "_lease_inactive", "_active_conflicts", "_search", "_empty_effect_snapshot",
    "_effect_snapshot", "_health", "_health_snapshot", "_validate_cost",
    "_prepare_output", "_fallback_prediction",
    "_task_metadata", "_metadata", "_decode_completed", "_terminal_outer_failure",
    "_from_runtime", "validate_task_row", "validate_aggregate", "aggregate_rows",
)})
AGGREGATE_INTEGER_FIELDS = harness.AGGREGATE_INTEGER_FIELDS
validate_aggregate = _CLONES["validate_aggregate"]


def clone_namespace_receipt() -> dict[str, Any]:
    """Return only the content-free pre-effect namespace attestation."""

    return copy.deepcopy(_CLONE_NAMESPACE_RECEIPT)


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    expected = {
        "one_external_forward": True,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    current = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    parents = contract.git(ROOT, "rev-list", "--parents", "-n", "1", current).split()
    changed = sorted(
        line.strip()
        for line in contract.git(
            ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current
        ).splitlines()
        if line.strip()
    )
    if (
        start.get("role") != "v25481_qualified_source_label_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("task_vector_sha256") != protocol["population"]["task_vector_sha256"]
        or start.get("clue_vector_sha256") != protocol["population"]["clue_vector_sha256"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("authorization") != expected
        or not contract.sealed(start, "execution_start_payload_sha256")
        or current != target
        or len(parents) != 2
        or parents[1] != start.get("git_head")
        or changed != [str(contract.EXECUTION_START)]
    ):
        raise RuntimeError("V2.54.81 execution start drifted")
    return protocol, start


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    value = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    completed = value["completed_runtime_tasks"]
    checks = {
        "fixed_task_denominator": value["task_count"] == gate["fixed_task_denominator"],
        "all_tasks_terminal": value["terminal_tasks"] == gate["required_terminal_tasks"],
        "all_runtime_tasks_completed": completed == gate["required_completed_runtime_tasks"],
        "zero_outer_failure": value["outer_failure_tasks"] <= gate["maximum_outer_failure_tasks"],
        "zero_naked_outer_failure": value["naked_outer_failure_tasks"] <= gate["maximum_naked_outer_failure_tasks"],
        "parent_role_exact": value["parent_role_tasks"] == contract.TASK_COUNT,
        "synthesis_capture_valid_exact": value["synthesis_capture_valid_tasks"] == gate["required_synthesis_capture_valid_tasks"],
        "minimum_accepted_unique_identity_page_tasks": value["accepted_unique_identity_page_tasks"] >= gate["minimum_accepted_unique_identity_page_tasks"],
        "minimum_available_candidate_tasks": value["available_candidate_tasks"] >= gate["minimum_available_candidate_tasks"],
        "minimum_applied_candidate_tasks": value["applied_candidate_tasks"] >= gate["minimum_applied_candidate_tasks"],
        "minimum_prediction_changed_tasks": value["prediction_changed_tasks"] >= gate["minimum_prediction_changed_tasks"],
        "zero_application_failure": value["application_failure_tasks"] <= gate["maximum_application_failure_tasks"],
        "zero_budget_rejection": value["budget_rejection_tasks"] <= gate["maximum_budget_rejection_tasks"],
        "exact_completed_query_budget": value["completed_physical_queries"] == gate["exact_physical_queries_per_completed_task"] * completed,
        "completed_fetch_cap_preserved": value["completed_physical_fetches"] <= gate["maximum_physical_fetches_per_completed_task"] * completed,
        "completed_model_budget_preserved": value["completed_physical_model_forwards"] <= gate["maximum_normal_path_model_forwards_per_completed_task"] * completed,
        "all_rows_per_task_hard_caps": value["per_task_hard_cap_preserved_tasks"] == contract.TASK_COUNT,
        "candidate_change_implies_applied_coordinates": value["prediction_changed_tasks"] == 0 or value["applied_coordinate_count_total"] > 0,
        "positive_signed_credit_zero": value["positive_signed_credit_count"] == gate["positive_signed_credit_count"],
    }
    failed=sorted(name for name,passed in checks.items() if not passed)
    return {"checks":checks,"failed_checks":failed,"mechanism_gate_passed":not failed,"postfreeze_quality_protocol_authorized":not failed,"deepwidebench_forward_evaluator_leaderboard_or_sota":False}


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied=copy.deepcopy(dict(value));aggregate=copied.get("aggregate")
    if copied.get("role")!=FORWARD_ROLE or copied.get("protocol_id")!=contract.PROTOCOL_ID or not isinstance(aggregate,Mapping) or validate_aggregate(aggregate)!=dict(aggregate) or copied.get("mechanism_decision")!=mechanism_decision(aggregate) or copied.get("authorization")!={"forward_audit":True,"postfreeze_quality_protocol":False,"deepwidebench_forward_evaluator_leaderboard_or_sota":False,"retry_resume_replay_backfill_replacement_or_selective_revaluation":False} or not contract.sealed(copied,"result_payload_sha256"):raise ValueError("V2.54.81 forward result drifted")
    return copied


_NAMESPACE.update({"_validate_start":_validate_start,"mechanism_decision":mechanism_decision,"validate_forward_result":validate_forward_result})
run_one_task = _CLONES["run_one_task"]
run_forward = _CLONES["run_forward"]


def main()->None:
    value=run_forward();print(json.dumps({"path":str(contract.FORWARD_RESULT),"aggregate":value["aggregate"],"mechanism_decision":value["mechanism_decision"]},sort_keys=True))


if __name__=="__main__":main()
