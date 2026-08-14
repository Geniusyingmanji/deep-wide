#!/usr/bin/env python3
"""Label-blind transfer audit for the V2.54.84 IANA-detail intervention.

V2.54.88/89 established a fresh shared-parent mechanism and quality GO for
the exact ``Domain | Type | TLD Manager`` workload.  This audit asks whether
that exact intervention is visibly applicable to the fixed DeepWideBench 220
questions.  It reads only frozen ``opaque_id`` and ``question`` values and
uses pure visible-schema parsing.  It never reads labels, answers, gold,
scores, evaluator outputs, historical correctness, predictions, or pages.

Only content-free aggregate counts and vector hashes are persisted.  The
audit performs no model, search, fetch, evaluator, benchmark, or network
effect and authorizes no forward.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as visible_schema  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as tasks  # noqa: E402
from deepwide_agent import v25483_row_key_iana_detail_candidate as candidate  # noqa: E402
from deepwide_agent import v25484_row_key_iana_detail_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import evaluate_v25489_iana_detail_quality as quality  # noqa: E402


DATE = "20260814"
ROLE = "v25490_iana_detail_exact220_visible_transfer_audit"
SOURCE = Path("scripts/audit_v25490_iana_detail_exact220_transfer.py")
TEST = Path("tests/test_audit_v25490_iana_detail_exact220_transfer.py")
OUTPUT = Path(f"results/v25490_iana_detail_exact220_transfer_audit_v1_{DATE}.json")
QUALITY_AUDIT = Path("results/v25488_iana_detail_quality_audit_v1_20260814.json")
QUALITY_AUDIT_SHA256 = (
    "f8a3d6ca8fb00d72e93dc6ec4c4288cba5557a13429915b5fc75877ce4e30373"
)
TASK_COUNT = 220
OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)
TARGET_COLUMNS = ("Domain", "Type", "TLD Manager")
CHECK_NAMES = frozenset(
    {
        "quality_audit_hash_role_seal_and_double_go_bound",
        "visible_task_vector_exact220_and_hash_bound",
        "runtime_and_candidate_policy_exact",
        "iana_authority_phrase_exposure_zero_of_220",
        "exact_target_schema_exposure_zero_of_220",
        "candidate_requires_exact_target_schema_and_visible_authority",
        "candidate_direct_request_cap_one_and_parent_row_key_only",
        "exact_intervention_transfer_is_provably_identity_only",
        "no_task_retention_replacement_ranking_or_selective_rerun",
        "mapping_gold_label_truth_score_reward_or_historical_result_not_read",
        "network_model_search_fetch_evaluator_or_benchmark_not_called",
        "entropy_information_gain_signed_credit_zero",
    }
)


def _quality_barrier() -> dict[str, Any]:
    path = base._ordinary(QUALITY_AUDIT)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        base.sha256(QUALITY_AUDIT) != QUALITY_AUDIT_SHA256
        or value.get("role") != "v25489_iana_detail_shared_parent_quality_audit"
        or value.get("audit_valid") is not True
        or value.get("quality_gate_passed") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("new_exact220_protocol_design")
        is not True
        or value.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or not quality.contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.54.90 quality authority drifted")
    return value


def _visible_transfer() -> dict[str, Any]:
    vector = tasks.task_vector(ROOT)
    if (
        len(vector) != TASK_COUNT
        or any(set(task) != {"opaque_id", "question"} for task in vector)
        or tasks.payload_sha256([task["opaque_id"] for task in vector])
        != OPAQUE_VECTOR_SHA256
        or tasks.payload_sha256([task["question"] for task in vector])
        != QUESTION_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.90 visible task vector drifted")
    target_schema_tasks = 0
    authority_phrase_tasks = 0
    both_tasks = 0
    exact_schema_tasks = 0
    empty_schema_tasks = 0
    for task in vector:
        question = task["question"]
        columns = tuple(visible_schema.extract_exact_visible_columns(question))
        has_schema = columns == TARGET_COLUMNS
        has_authority = "IANA Root Zone Database" in question
        target_schema_tasks += int(has_schema)
        authority_phrase_tasks += int(has_authority)
        both_tasks += int(has_schema and has_authority)
        exact_schema_tasks += int(bool(columns))
        empty_schema_tasks += int(not columns)
    return {
        "task_count": len(vector),
        "runtime_input_keys": ["opaque_id", "question"],
        "opaque_id_vector_sha256": OPAQUE_VECTOR_SHA256,
        "visible_question_vector_sha256": QUESTION_VECTOR_SHA256,
        "target_schema": list(TARGET_COLUMNS),
        "exact_visible_schema_tasks": exact_schema_tasks,
        "empty_exact_visible_schema_tasks": empty_schema_tasks,
        "exact_target_schema_tasks": target_schema_tasks,
        "iana_authority_phrase_tasks": authority_phrase_tasks,
        "joint_target_schema_and_authority_tasks": both_tasks,
        "exact_intervention_reachable_upper_bound_tasks": both_tasks,
        "question_opaque_id_or_per_task_feature_persisted": False,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    barrier = _quality_barrier()
    exposure = _visible_transfer()
    primitive = candidate.integration_contract()
    integration = runtime.integration_contract()
    checks = {
        "quality_audit_hash_role_seal_and_double_go_bound": bool(barrier),
        "visible_task_vector_exact220_and_hash_bound": exposure["task_count"]
        == TASK_COUNT,
        "runtime_and_candidate_policy_exact": (
            runtime.POLICY_ID == "v25484_row_key_iana_detail_runtime_v1"
            and candidate.POLICY_ID == "v25483_row_key_iana_detail_candidate_v1"
        ),
        "iana_authority_phrase_exposure_zero_of_220": exposure[
            "iana_authority_phrase_tasks"
        ]
        == 0,
        "exact_target_schema_exposure_zero_of_220": exposure[
            "exact_target_schema_tasks"
        ]
        == 0,
        "candidate_requires_exact_target_schema_and_visible_authority": (
            primitive["visible_iana_authority_phrase_required"] is True
            and primitive["official_url_derived_only_from_completed_parent_row_key"]
            is True
        ),
        "candidate_direct_request_cap_one_and_parent_row_key_only": (
            primitive["maximum_direct_requests"] == 1
            and integration["maximum_candidate_additional_fetches"] == 1
            and integration["candidate_additional_queries"] == 0
            and integration["candidate_additional_model_calls"] == 0
        ),
        "exact_intervention_transfer_is_provably_identity_only": exposure[
            "exact_intervention_reachable_upper_bound_tasks"
        ]
        == 0,
        "no_task_retention_replacement_ranking_or_selective_rerun": True,
        "mapping_gold_label_truth_score_reward_or_historical_result_not_read": True,
        "network_model_search_fetch_evaluator_or_benchmark_not_called": True,
        "entropy_information_gain_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "quality_audit": {
            "path": str(QUALITY_AUDIT),
            "sha256": QUALITY_AUDIT_SHA256,
            "mechanism_and_quality_double_go": True,
        },
        "runtime_policy_id": runtime.POLICY_ID,
        "candidate_policy_id": candidate.POLICY_ID,
        "visible_transfer": exposure,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "transfer_decision": {
            "fresh_external_iana_detail_mechanism_and_quality": "go",
            "fixed_exact220_exact_intervention": "no_go",
            "reason": "target_schema_and_iana_authority_joint_exposure_zero_of_220",
        },
        "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "v25484_exact220_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "generic_row_key_detail_successor_build": not findings,
            "new_external_protocol_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    transfer = copied.get("visible_transfer")
    if (
        copied.get("role") != ROLE
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not isinstance(transfer, Mapping)
        or transfer.get("task_count") != TASK_COUNT
        or transfer.get("opaque_id_vector_sha256") != OPAQUE_VECTOR_SHA256
        or transfer.get("visible_question_vector_sha256")
        != QUESTION_VECTOR_SHA256
        or transfer.get("exact_target_schema_tasks") != 0
        or transfer.get("iana_authority_phrase_tasks") != 0
        or transfer.get("joint_target_schema_and_authority_tasks") != 0
        or transfer.get("exact_intervention_reachable_upper_bound_tasks") != 0
        or copied.get("transfer_decision")
        != {
            "fresh_external_iana_detail_mechanism_and_quality": "go",
            "fixed_exact220_exact_intervention": "no_go",
            "reason": "target_schema_and_iana_authority_joint_exposure_zero_of_220",
        }
        or copied.get(
            "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "v25484_exact220_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "generic_row_key_detail_successor_build": True,
            "new_external_protocol_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.90 exact220 transfer audit drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "visible_transfer": value["visible_transfer"],
                "transfer_decision": value["transfer_decision"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
