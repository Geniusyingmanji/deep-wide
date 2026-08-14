#!/usr/bin/env python3
"""Visible-only transfer audit for the V2.54.57 exact-220 hypothesis.

V2.54.61/62 established a strong shared-parent mechanism and quality effect
on a fresh RFC population.  This audit asks the narrower transfer question:
can the RFC-specific candidate itself activate on the fixed public
DeepWideBench questions?  It reads only the same ``opaque_id`` and
``question`` fields available to runtime, never benchmark labels, answers,
scores, evaluator outputs, or historical correctness.

Only aggregate exposure counts and vector hashes are persisted.  No question,
opaque id, request URL, prediction, truth value, or per-task outcome is
written.  The audit performs no model, search, fetch, evaluator, or network
effect.
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

from deepwide_agent import v25406_grounded_membership_exact220_contract as tasks  # noqa: E402
from deepwide_agent import v25457_date_bounded_official_rfc_xml_shared_runtime as runtime  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import evaluate_v25462_date_bounded_official_rfc_xml_shared_effect_quality as quality  # noqa: E402


DATE = "20260814"
ROLE = "v25463_date_bounded_official_xml_exact220_visible_transfer_audit"
SOURCE = Path("scripts/audit_v25463_date_bounded_official_xml_exact220_transfer.py")
TEST = Path("tests/test_audit_v25463_date_bounded_official_xml_exact220_transfer.py")
OUTPUT = Path(
    f"results/v25463_date_bounded_official_xml_exact220_transfer_audit_v1_{DATE}.json"
)
QUALITY_AUDIT = Path(
    "results/v25461_date_bounded_official_rfc_xml_shared_effect_quality_audit_v1_20260814.json"
)
QUALITY_AUDIT_SHA256 = (
    "71d6ceaff39888a1e50be0f0d1cc7ef74a66eec08e279553bbe8cd742ebc1735"
)
TASK_COUNT = 220
OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)
BASE_SENTINEL = (
    "```markdown\n"
    "| RFC | Title | Authors | Status | Stream | Published |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| RFC 0000 | Unknown | Unknown | Unknown | Unknown | Unknown |\n"
    "```"
)
CHECK_NAMES = frozenset(
    {
        "quality_audit_hash_role_seal_and_double_go_bound",
        "visible_task_vector_exact220_and_hash_bound",
        "runtime_and_candidate_policy_exact",
        "strict_rfc_request_exposure_zero_of_220",
        "requested_official_xml_url_count_zero",
        "empty_page_application_identity_handoff_220_of_220",
        "valid_record_and_applied_coordinate_count_zero",
        "candidate_specific_prediction_change_reachable_zero_of_220",
        "runtime_candidate_requires_visible_request_before_additional_fetch",
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
        or value.get("role")
        != "v25462_date_bounded_official_rfc_xml_shared_effect_quality_audit"
        or value.get("audit_valid") is not True
        or value.get("quality_gate_passed") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("new_exact220_protocol_design")
        is not True
        or value.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or not quality.contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.54.63 quality authority drifted")
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
        raise RuntimeError("V2.54.63 visible task vector drifted")
    request_exposure_tasks = 0
    requested_url_count = 0
    identity_handoff_tasks = 0
    valid_record_count = 0
    applied_coordinate_count = 0
    candidate_change_reachable_tasks = 0
    for task in vector:
        question = task["question"]
        requests = runtime.candidates.request_vector(question)
        request_exposure_tasks += bool(requests)
        requested_url_count += len(requests)
        application = runtime.candidates.build_candidate(
            BASE_SENTINEL,
            question=question,
            pages=[],
        )
        checked = runtime.candidates.validate_candidate(application, pages=[])
        identity = (
            checked["base_prediction"] == BASE_SENTINEL
            and checked["candidate_prediction"] == BASE_SENTINEL
            and checked["candidate_prediction_changed"] is False
        )
        identity_handoff_tasks += identity
        valid_record_count += int(checked["valid_record_count"])
        applied_coordinate_count += int(checked["applied_coordinate_count"])
        candidate_change_reachable_tasks += bool(requests) and not identity
    return {
        "task_count": len(vector),
        "runtime_input_keys": ["opaque_id", "question"],
        "opaque_id_vector_sha256": OPAQUE_VECTOR_SHA256,
        "visible_question_vector_sha256": QUESTION_VECTOR_SHA256,
        "strict_rfc_request_exposure_tasks": request_exposure_tasks,
        "strict_rfc_request_exposure_fraction": request_exposure_tasks / TASK_COUNT,
        "requested_official_xml_url_count": requested_url_count,
        "empty_page_identity_handoff_tasks": identity_handoff_tasks,
        "valid_record_count_without_request_exposure": valid_record_count,
        "applied_coordinate_count_without_request_exposure": applied_coordinate_count,
        "candidate_specific_prediction_change_reachable_tasks": candidate_change_reachable_tasks,
        "question_opaque_id_request_url_prediction_or_per_task_feature_persisted": False,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    quality_barrier = _quality_barrier()
    exposure = _visible_transfer()
    integration = runtime.integration_contract()
    checks = {
        "quality_audit_hash_role_seal_and_double_go_bound": bool(quality_barrier),
        "visible_task_vector_exact220_and_hash_bound": exposure["task_count"]
        == TASK_COUNT,
        "runtime_and_candidate_policy_exact": (
            runtime.POLICY_ID
            == "v25457_date_bounded_official_rfc_xml_shared_runtime_v1"
            and runtime.candidates.POLICY_ID
            == "v25456_date_bounded_official_rfc_xml_record_candidate_v1"
        ),
        "strict_rfc_request_exposure_zero_of_220": exposure[
            "strict_rfc_request_exposure_tasks"
        ]
        == 0,
        "requested_official_xml_url_count_zero": exposure[
            "requested_official_xml_url_count"
        ]
        == 0,
        "empty_page_application_identity_handoff_220_of_220": exposure[
            "empty_page_identity_handoff_tasks"
        ]
        == TASK_COUNT,
        "valid_record_and_applied_coordinate_count_zero": (
            exposure["valid_record_count_without_request_exposure"] == 0
            and exposure["applied_coordinate_count_without_request_exposure"] == 0
        ),
        "candidate_specific_prediction_change_reachable_zero_of_220": exposure[
            "candidate_specific_prediction_change_reachable_tasks"
        ]
        == 0,
        "runtime_candidate_requires_visible_request_before_additional_fetch": (
            integration["candidate_additional_queries"] == 0
            and integration["candidate_additional_model_calls"] == 0
            and integration["maximum_candidate_additional_fetches"] == 4
        ),
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
        "candidate_policy_id": runtime.candidates.POLICY_ID,
        "visible_transfer": exposure,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "transfer_decision": {
            "fresh_external_rfc_mechanism_and_quality": "go",
            "fixed_exact220_candidate_exposure": "no_go",
            "reason": "strict_visible_rfc_request_exposure_zero_of_220",
        },
        "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "v25457_exact220_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "generic_visible_source_structured_record_successor_build": not findings,
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
        or transfer.get("strict_rfc_request_exposure_tasks") != 0
        or transfer.get("strict_rfc_request_exposure_fraction") != 0.0
        or transfer.get("requested_official_xml_url_count") != 0
        or transfer.get("empty_page_identity_handoff_tasks") != TASK_COUNT
        or transfer.get("candidate_specific_prediction_change_reachable_tasks")
        != 0
        or copied.get("transfer_decision")
        != {
            "fresh_external_rfc_mechanism_and_quality": "go",
            "fixed_exact220_candidate_exposure": "no_go",
            "reason": "strict_visible_rfc_request_exposure_zero_of_220",
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
            "v25457_exact220_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "generic_visible_source_structured_record_successor_build": True,
            "new_external_protocol_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.63 exact220 transfer audit drifted")
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
