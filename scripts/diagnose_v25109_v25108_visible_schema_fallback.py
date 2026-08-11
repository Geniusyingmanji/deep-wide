#!/usr/bin/env python3
"""Label-blind diagnosis of the frozen V2.51.08 schema fallback failures."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24986_robust_paired_runtime as robust  # noqa: E402
from deepwide_agent import v25108_verified_field_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import run_v25108_verified_field_external as runner  # noqa: E402


OUTPUT = Path("results/v25109_v25108_visible_schema_fallback_diagnosis_v1_20260811.json")
EXPECTED_PARENTS = {
    "forward_result_sha256": "d37be0c74765a0bfd5b4f924bc84bd9bdb89d9a13e37bf9bae512336cfcc60dc",
    "forward_audit_sha256": "b23095efcb951462371f14ce1b9be15c749356001c440f98d44a1f3d915e3c2a",
    "task_rows_sha256": "95ab630b81f9dfa26e2ad659b88fb6b6da5e0910962fab405d668a75ab2aacb5",
}


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.09 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    return [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]


def _histogram(values: list[object]) -> dict[str, int]:
    return dict(sorted(Counter("None" if value is None else str(value) for value in values).items()))


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parents = {
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
    }
    if parents != EXPECTED_PARENTS:
        raise RuntimeError("V2.51.09 frozen parent hash drifted")
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    rows = _read_rows()
    tasks = contract.task_vector()
    limits = ScoreFirstLimits(**contract.LIMITS)
    fallback_plans = [
        robust.validated_robust_plan({}, task["question"], limits) for task in tasks
    ]
    plan_failures = [row["failure_types"]["plan"] for row in rows]
    proposal_failures = [row["failure_types"]["proposal"] for row in rows]
    representation_failures = [
        row["content_free_receipt"]["representation_failure_type"] for row in rows
    ]
    plan_transport = [value == "ModelRequestError" for value in plan_failures]
    proposal_transport = [value == "ModelRequestError" for value in proposal_failures]
    representation_invalid = [value == "ValueError" for value in representation_failures]
    plan_and_proposal_transport = [
        plan and proposal for plan, proposal in zip(plan_transport, proposal_transport, strict=True)
    ]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25109_v25108_visible_schema_fallback_content_free_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": parents,
        "frozen_parent": {
            "task_count": len(rows),
            "audit_valid": audit.get("audit_valid") is True and audit.get("findings") == [],
            "mechanism_gate_passed": forward["mechanism_decision"]["mechanism_gate_passed"],
            "completed_runtime_tasks": forward["aggregate"]["completed_runtime_tasks"],
            "representation_validation_failure_tasks": forward["aggregate"][
                "representation_validation_failure_tasks"
            ],
            "model_provider_requests": forward["aggregate"]["model_provider_requests"],
            "model_provider_attempts": forward["aggregate"]["model_provider_attempts"],
        },
        "visible_only_parser_reproduction": {
            "task_count": len(tasks),
            "declared_column_count": len(contract.COLUMNS),
            "all_tasks_use_columns_exactly_colon_pipe_form": all(
                "Columns exactly:" in task["question"]
                and task["question"].count(" | ") >= len(contract.COLUMNS) - 1
                for task in tasks
            ),
            "legacy_visible_parser_empty_tasks": sum(
                not robust.extract_robust_visible_columns(task["question"]) for task in tasks
            ),
            "empty_provider_fallback_result_only_tasks": sum(
                plan["columns"] == ["Result"] for plan in fallback_plans
            ),
            "empty_provider_fallback_column_count_histogram": _histogram(
                [len(plan["columns"]) for plan in fallback_plans]
            ),
            "network_model_search_fetch_evaluator_or_credential_access": False,
        },
        "failure_separation": {
            "plan_failure_type_histogram": _histogram(plan_failures),
            "proposal_failure_type_histogram": _histogram(proposal_failures),
            "representation_failure_type_histogram": _histogram(representation_failures),
            "plan_transport_failure_tasks": sum(plan_transport),
            "proposal_transport_failure_tasks": sum(proposal_transport),
            "representation_validation_failure_tasks": sum(representation_invalid),
            "plan_and_proposal_transport_failure_tasks": sum(plan_and_proposal_transport),
            "plan_transport_and_representation_failure_tasks": sum(
                plan and invalid
                for plan, invalid in zip(plan_transport, representation_invalid, strict=True)
            ),
            "proposal_only_transport_failure_without_representation_failure_tasks": sum(
                proposal and not plan and not invalid
                for plan, proposal, invalid in zip(
                    plan_transport, proposal_transport, representation_invalid, strict=True
                )
            ),
            "representation_failure_without_plan_transport_failure_tasks": sum(
                invalid and not plan
                for plan, invalid in zip(plan_transport, representation_invalid, strict=True)
            ),
        },
        "diagnosis": {
            "root_cause_is_missing_columns_exactly_visible_anchor": True,
            "pipe_separator_support_exists_but_is_unreachable_without_anchor": True,
            "plan_transport_failure_exposes_result_only_fallback": True,
            "eight_representation_failures_are_schema_fallback_secondary_failures": True,
            "proposal_transport_failure_is_not_itself_a_representation_validation_failure": True,
            "transport_and_representation_failures_must_be_accounted_separately": True,
            "next_parser_must_be_deterministic_visible_only_and_fail_closed": True,
            "next_runtime_must_preserve_four_physical_model_calls_and_equal_arm_budgets": True,
            "next_runtime_must_not_retry_resume_or_reuse_v25108_population": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "visible_questions_used_in_memory_only_for_label_blind_parser_reproduction": True,
            "question_column_identity_value_query_url_page_prediction_or_answer_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "v25108_retry_resume_evaluator_or_selective_revaluation": False,
            "append_only_parser_and_runtime_successor_build": True,
            "new_external_forward": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    parent = copied.get("frozen_parent") or {}
    reproduction = copied.get("visible_only_parser_reproduction") or {}
    separation = copied.get("failure_separation") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    required_true = (
        "root_cause_is_missing_columns_exactly_visible_anchor",
        "pipe_separator_support_exists_but_is_unreachable_without_anchor",
        "plan_transport_failure_exposes_result_only_fallback",
        "eight_representation_failures_are_schema_fallback_secondary_failures",
        "proposal_transport_failure_is_not_itself_a_representation_validation_failure",
        "transport_and_representation_failures_must_be_accounted_separately",
        "next_parser_must_be_deterministic_visible_only_and_fail_closed",
        "next_runtime_must_preserve_four_physical_model_calls_and_equal_arm_budgets",
        "next_runtime_must_not_retry_resume_or_reuse_v25108_population",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25109_v25108_visible_schema_fallback_content_free_diagnosis"
        or copied.get("parents") != EXPECTED_PARENTS
        or seal != contract.payload_sha256(unsigned)
        or parent.get("task_count") != 20
        or parent.get("audit_valid") is not True
        or parent.get("mechanism_gate_passed") is not False
        or parent.get("completed_runtime_tasks") != 20
        or parent.get("representation_validation_failure_tasks") != 8
        or reproduction.get("task_count") != 20
        or reproduction.get("declared_column_count") != 4
        or reproduction.get("all_tasks_use_columns_exactly_colon_pipe_form") is not True
        or reproduction.get("legacy_visible_parser_empty_tasks") != 20
        or reproduction.get("empty_provider_fallback_result_only_tasks") != 20
        or reproduction.get("empty_provider_fallback_column_count_histogram") != {"1": 20}
        or reproduction.get("network_model_search_fetch_evaluator_or_credential_access")
        is not False
        or separation.get("plan_transport_failure_tasks") != 8
        or separation.get("proposal_transport_failure_tasks") != 11
        or separation.get("representation_validation_failure_tasks") != 8
        or separation.get("plan_and_proposal_transport_failure_tasks") != 8
        or separation.get("plan_transport_and_representation_failure_tasks") != 8
        or separation.get(
            "proposal_only_transport_failure_without_representation_failure_tasks"
        )
        != 3
        or separation.get("representation_failure_without_plan_transport_failure_tasks") != 0
        or any(diagnosis.get(name) is not True for name in required_true)
        or diagnosis.get("entropy_or_information_gain_signed_credit_validated") is not False
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or authorization.get("append_only_parser_and_runtime_successor_build") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "append_only_parser_and_runtime_successor_build"
        )
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("content_policy", {}).get(
            "credential_value_read_persisted_hashed_or_emitted"
        )
        is not False
    ):
        raise RuntimeError("V2.51.09 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
