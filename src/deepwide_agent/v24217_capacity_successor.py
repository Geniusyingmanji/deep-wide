"""Pure report and freeze logic for the post-package-gate capacity successor.

The capacity measurement is the frozen V2.41.94 neutral probe.  This module
only wraps its content-free request metadata with the V2.42.16 package-gate
authority and derives a scheduling freeze.  It never receives benchmark task
content, predictions, mappings, labels, gold answers, or evaluator scores.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from deepwide_agent.v24194_capacity_ladder import (
    ProbeSettings,
    validate_capacity_report,
)


REPORT_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "protocol",
        "parent_package_gate",
        "execution_activation",
        "shared_api_lease",
        "measurement",
        "source_policy",
        "authorization",
        "report_payload_sha256",
    }
)
FREEZE_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "source_report",
        "protocol",
        "parent_package_gate",
        "endpoint",
        "model",
        "reasoning_effort",
        "service_tier",
        "model_request_concurrency_cap",
        "parallel_shard_cap",
        "per_shard_candidate_model_workers_cap",
        "per_shard_row_model_workers_cap",
        "worst_case_model_request_concurrency",
        "capacity_go",
        "same_all220_opaque_partition_required",
        "new_output_roots_required",
        "resume_or_selective_rerun_allowed",
        "forward_failure_scored_as_zero",
        "fixed_concurrency_for_entire_all220",
        "search_capacity_requires_separate_frozen_preflight",
        "candidate_package_identity_must_match_parent_gate",
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read",
        "full220_launch_allowed",
        "separate_single_owner_activation_required",
        "leaderboard_submission_or_sota_claim",
        "freeze_payload_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_identity(value: Mapping[str, Any], *, name: str) -> None:
    path = value.get("path")
    digest = value.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise RuntimeError(f"V2.42.17 {name} identity is invalid")


def build_report(
    measurement: dict[str, Any],
    *,
    protocol: dict[str, Any],
    parent_package_gate: dict[str, Any],
    execution_activation: dict[str, Any],
    shared_api_lease: dict[str, Any],
    created_at_unix: int,
    expected_settings: ProbeSettings,
) -> dict[str, Any]:
    """Bind one validated neutral measurement to the package-gate authority."""

    validate_capacity_report(measurement, expected_settings=expected_settings)
    for name, identity in (
        ("protocol", protocol),
        ("parent package gate", parent_package_gate),
        ("execution activation", execution_activation),
    ):
        _validate_identity(identity, name=name)
    if (
        parent_package_gate.get("status")
        not in {
            "complete_package_gate_go",
            "complete_identity_handoff_no_package_gate_required",
        }
        or parent_package_gate.get("capacity_measurement_allowed") is not True
        or parent_package_gate.get("all220_freeze_design_allowed") is not True
        or parent_package_gate.get("contents_emitted") is not False
        or shared_api_lease.get("owner")
        != "v24217_post_package_gate_neutral_capacity_v1"
        or shared_api_lease.get("purpose")
        != "neutral_capacity_after_v24216_go_for_next_fresh_all220"
        or shared_api_lease.get("owner_purpose_pid_and_lock_holder_exact") is not True
        or shared_api_lease.get("contents_emitted") is not False
        or isinstance(created_at_unix, bool)
        or not isinstance(created_at_unix, int)
    ):
        raise RuntimeError("V2.42.17 report authority is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24217_post_package_gate_neutral_capacity_report",
        "created_at_unix": created_at_unix,
        "protocol": dict(protocol),
        "parent_package_gate": dict(parent_package_gate),
        "execution_activation": dict(execution_activation),
        "shared_api_lease": dict(shared_api_lease),
        "measurement": measurement,
        "source_policy": {
            "neutral_fixed_payload_only": True,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "search_fetch_or_evaluator_api_called": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "response_text_or_response_id_persisted": False,
        },
        "authorization": {
            "capacity_recommendation_only": True,
            "full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["report_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(
    value: dict[str, Any],
    *,
    expected_settings: ProbeSettings,
    protocol_path: str,
    protocol_sha256: str,
) -> dict[str, int]:
    if (
        set(value) != REPORT_FIELDS
        or value.get("artifact_version") != 1
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("role")
        != "v24217_post_package_gate_neutral_capacity_report"
        or value.get("protocol")
        != {"path": protocol_path, "sha256": protocol_sha256}
        or not _sealed(value, "report_payload_sha256")
        or value.get("parent_package_gate", {}).get("status")
        not in {
            "complete_package_gate_go",
            "complete_identity_handoff_no_package_gate_required",
        }
        or value.get("parent_package_gate", {}).get("capacity_measurement_allowed")
        is not True
        or value.get("parent_package_gate", {}).get("all220_freeze_design_allowed")
        is not True
        or value.get("parent_package_gate", {}).get("contents_emitted") is not False
        or value.get("shared_api_lease", {}).get("owner")
        != "v24217_post_package_gate_neutral_capacity_v1"
        or value.get("shared_api_lease", {}).get("purpose")
        != "neutral_capacity_after_v24216_go_for_next_fresh_all220"
        or value.get("shared_api_lease", {}).get(
            "owner_purpose_pid_and_lock_holder_exact"
        )
        is not True
        or value.get("source_policy")
        != {
            "neutral_fixed_payload_only": True,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "search_fetch_or_evaluator_api_called": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "response_text_or_response_id_persisted": False,
        }
        or value.get("authorization")
        != {
            "capacity_recommendation_only": True,
            "full220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        }
    ):
        raise RuntimeError("V2.42.17 report envelope is invalid")
    for name in ("parent_package_gate", "execution_activation"):
        _validate_identity(value[name], name=name)
    measurement = value.get("measurement")
    if not isinstance(measurement, dict):
        raise RuntimeError("V2.42.17 measurement is absent")
    return validate_capacity_report(
        measurement, expected_settings=expected_settings
    )


def build_freeze(
    report: dict[str, Any],
    *,
    expected_settings: ProbeSettings,
    report_path: str,
    report_sha256: str,
    protocol_path: str,
    protocol_sha256: str,
    created_at_unix: int,
) -> dict[str, Any]:
    derived = validate_report(
        report,
        expected_settings=expected_settings,
        protocol_path=protocol_path,
        protocol_sha256=protocol_sha256,
    )
    selected = derived["selected"]
    workers = derived["workers"]
    shards = derived["shards"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24217_next_fresh_all220_capacity_freeze",
        "created_at_unix": created_at_unix,
        "source_report": {"path": report_path, "sha256": report_sha256},
        "protocol": {"path": protocol_path, "sha256": protocol_sha256},
        "parent_package_gate": dict(report["parent_package_gate"]),
        "endpoint": "http://127.0.0.1:9878/responses",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "service_tier": "priority",
        "model_request_concurrency_cap": selected,
        "parallel_shard_cap": shards,
        "per_shard_candidate_model_workers_cap": workers,
        "per_shard_row_model_workers_cap": workers,
        "worst_case_model_request_concurrency": shards * workers,
        "capacity_go": selected > 0,
        "same_all220_opaque_partition_required": True,
        "new_output_roots_required": True,
        "resume_or_selective_rerun_allowed": False,
        "forward_failure_scored_as_zero": True,
        "fixed_concurrency_for_entire_all220": True,
        "search_capacity_requires_separate_frozen_preflight": True,
        "candidate_package_identity_must_match_parent_gate": True,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "full220_launch_allowed": False,
        "separate_single_owner_activation_required": True,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    return value


def validate_freeze(
    value: dict[str, Any],
    *,
    report: dict[str, Any],
    expected_settings: ProbeSettings,
    report_path: str,
    report_sha256: str,
    protocol_path: str,
    protocol_sha256: str,
) -> dict[str, int]:
    if (
        set(value) != FREEZE_FIELDS
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or not _sealed(value, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.42.17 freeze envelope is invalid")
    expected = build_freeze(
        report,
        expected_settings=expected_settings,
        report_path=report_path,
        report_sha256=report_sha256,
        protocol_path=protocol_path,
        protocol_sha256=protocol_sha256,
        created_at_unix=int(value.get("created_at_unix", -1)),
    )
    if value != expected:
        raise RuntimeError("V2.42.17 freeze differs from recomputed capacity")
    return {
        "selected": int(value["model_request_concurrency_cap"]),
        "workers": int(value["per_shard_candidate_model_workers_cap"]),
        "shards": int(value["parallel_shard_cap"]),
    }
