#!/usr/bin/env python3
"""Counts-only diagnosis of V2.50.57's zero-exposure exact-220 run.

Both 220 prediction vectors and evaluator results are frozen, audited, and
pushed before this script runs.  Opaque IDs and prediction hashes are used
only for in-memory alignment and are never emitted.  The output contains no
question, ID, prediction, page, URL, query, gold, category, or per-task metric.
It performs no network, model, search, fetch, evaluator, or credential access.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
CURRENT_RESULT = Path(
    "results/v25057_page_self_exact220_result_r2_20260811.json"
)
CURRENT_POSTAUDIT = Path(
    "results/v25057_page_self_exact220_postresult_audit_r2_20260811.json"
)
CURRENT_SUMMARY = Path(
    "outputs/v25057_page_self_exact220_r2_20260811/run_summary.json"
)
CURRENT_PREDICTIONS = Path(
    "outputs/v25057_page_self_exact220_r2_20260811/runtime_predictions.jsonl"
)
CURRENT_FREEZE = Path(
    "outputs/v25057_page_self_exact220_r2_20260811/prediction_freeze.json"
)
PARENT_RESULT = Path(
    "results/v25030_evidence_conditioned_exact220_result_v1_20260810.json"
)
PARENT_POSTAUDIT = Path(
    "results/v25030_evidence_conditioned_exact220_postresult_audit_v1_20260810.json"
)
PARENT_PREDICTIONS = Path(
    "outputs/v25030_evidence_conditioned_exact220_v1_20260810/runtime_predictions.jsonl"
)
PARENT_FREEZE = Path(
    "outputs/v25030_evidence_conditioned_exact220_v1_20260810/prediction_freeze.json"
)
OUTPUT = Path(
    "results/v25058_v25057_zero_exposure_diagnosis_v1_20260811.json"
)
PROJECTION_KEYS = {
    "changed_evidence_pages",
    "characters_beyond_5k_prefix",
    "exact_parent_prefix_handoff_pages",
    "mechanism_exposed_pages",
    "positive_signed_credit_count",
    "projected_pages",
}


def payload_sha256(value: object) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    if (
        path.is_absolute()
        or ".." in path.parts
        or absolute.is_symlink()
        or not absolute.is_file()
        or not absolute.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.50.58 expected ordinary repository JSON")
    value = json.loads(absolute.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.58 expected JSON object")
    return value


def _predictions(path: Path) -> list[dict[str, Any]]:
    absolute = ROOT / path
    if absolute.is_symlink() or not absolute.is_file():
        raise RuntimeError("V2.50.58 expected ordinary frozen predictions")
    rows = [
        json.loads(line)
        for line in absolute.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != 220 or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.58 expected fixed prediction denominator")
    for row in rows:
        if (
            not isinstance(row.get("opaque_id"), str)
            or not isinstance(row.get("prediction_sha256"), str)
            or len(row["prediction_sha256"]) != 64
            or row.get("label_blind") is not True
            or row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
        ):
            raise RuntimeError("V2.50.58 prediction barrier drifted")
    return rows


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    observed = unsigned.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(unsigned)


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    current_result = _json(CURRENT_RESULT)
    current_post = _json(CURRENT_POSTAUDIT)
    current_summary = _json(CURRENT_SUMMARY)
    current_freeze = _json(CURRENT_FREEZE)
    parent_result = _json(PARENT_RESULT)
    parent_post = _json(PARENT_POSTAUDIT)
    parent_freeze = _json(PARENT_FREEZE)
    if (
        current_post.get("audit_valid") is not True
        or current_post.get("findings") != []
        or parent_post.get("audit_valid") is not True
        or parent_post.get("findings") != []
        or not _sealed(current_post, "audit_payload_sha256")
        or not _sealed(parent_post, "audit_payload_sha256")
        or current_freeze.get("selected") != 220
        or current_freeze.get("terminal") != 220
        or parent_freeze.get("selected") != 220
        or parent_freeze.get("terminal") != 220
        or not _sealed(current_freeze, "freeze_payload_sha256")
        or not _sealed(parent_freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.50.58 frozen parent barrier drifted")
    current = _predictions(CURRENT_PREDICTIONS)
    parent = _predictions(PARENT_PREDICTIONS)
    if [row["opaque_id"] for row in current] != [row["opaque_id"] for row in parent]:
        raise RuntimeError("V2.50.58 prediction vector alignment drifted")
    same = sum(
        left["prediction_sha256"] == right["prediction_sha256"]
        for left, right in zip(current, parent, strict=True)
    )
    changed = 220 - same
    projection = dict(current_summary.get("page_self_projection") or {})
    if set(projection) != PROJECTION_KEYS:
        raise RuntimeError("V2.50.58 projection schema drifted")
    current_metrics = dict(current_result["metrics"]["all_220"])
    parent_metrics = dict(parent_result["metrics"]["all_220"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25058_v25057_zero_exposure_counts_only_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "postfreeze_zero_treatment_exposure_cold_replication_audited",
        "parents": {
            "v25057_result_sha256": sha256(CURRENT_RESULT),
            "v25057_postaudit_sha256": sha256(CURRENT_POSTAUDIT),
            "v25057_summary_sha256": sha256(CURRENT_SUMMARY),
            "v25057_prediction_freeze_sha256": sha256(CURRENT_FREEZE),
            "v25030_result_sha256": sha256(PARENT_RESULT),
            "v25030_postaudit_sha256": sha256(PARENT_POSTAUDIT),
            "v25030_prediction_freeze_sha256": sha256(PARENT_FREEZE),
        },
        "fixed_denominator": {
            "tasks": 220,
            "v25057_evaluator_valid": current_metrics["evaluator_valid"],
            "v25057_evaluator_error_as_zero": current_metrics[
                "evaluator_invalid_or_not_run"
            ],
            "v25030_evaluator_valid": parent_metrics["evaluator_valid"],
            "v25030_evaluator_error_as_zero": parent_metrics[
                "evaluator_invalid_or_not_run"
            ],
        },
        "production_exposure": {
            **projection,
            "mechanism_gate_passed": current_summary[
                "page_self_mechanism_gate_passed"
            ],
        },
        "cross_cold_run": {
            "prediction_hash_same_tasks": same,
            "prediction_hash_changed_tasks": changed,
            "v25057_whole_table_successes": current_metrics[
                "whole_table_successes"
            ],
            "v25030_whole_table_successes": parent_metrics[
                "whole_table_successes"
            ],
            "whole_table_success_delta": current_metrics[
                "whole_table_successes"
            ]
            - parent_metrics["whole_table_successes"],
            "v25057_quality_composite": current_metrics["quality_composite"],
            "v25030_quality_composite": parent_metrics["quality_composite"],
            "quality_composite_delta": current_metrics["quality_composite"]
            - parent_metrics["quality_composite"],
            "v25057_forward_wall_seconds": current_result["efficiency"][
                "forward_wall_seconds"
            ],
            "v25030_forward_wall_seconds": parent_result["efficiency"][
                "forward_wall_seconds"
            ],
        },
        "diagnosis": {
            "page_self_representation_naturally_reached_production": False,
            "v25057_is_effect_equivalent_to_raw_prefix_at_fetch_projection_boundary": True,
            "prediction_or_quality_difference_attributable_to_page_self_treatment": False,
            "prediction_hash_changes_are_cold_search_and_model_rollout_variation": True,
            "repeat_exact220_with_same_page_self_binding_is_authorized": False,
            "next_gate_requires_nonzero_natural_exposure_before_quality_or_exact220": True,
            "next_extractor_must_relax_identity_surface_binding_without_relaxing_source_target_value_atomicity": True,
            "entropy_or_information_gain_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "opaque_ids_or_prediction_hashes_used_only_for_in_memory_alignment": True,
            "question_id_prediction_page_url_query_gold_category_or_per_task_metric_emitted": False,
            "network_model_search_fetch_evaluator_or_credential_accessed": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "fresh_benchmark_external_mechanism_gate_design": True,
            "new_exact220_launch": False,
            "retry_resume_or_selective_rerun": False,
            "selective_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    exposure = copied.get("production_exposure") or {}
    cold = copied.get("cross_cold_run") or {}
    diagnosis = copied.get("diagnosis") or {}
    policy = copied.get("content_policy") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "authorization",
            "content_policy",
            "created_at_unix",
            "cross_cold_run",
            "diagnosis",
            "diagnosis_payload_sha256",
            "fixed_denominator",
            "parents",
            "production_exposure",
            "role",
            "status",
        }
        or set(exposure) != PROJECTION_KEYS | {"mechanism_gate_passed"}
        or set(cold)
        != {
            "prediction_hash_changed_tasks",
            "prediction_hash_same_tasks",
            "quality_composite_delta",
            "v25030_forward_wall_seconds",
            "v25030_quality_composite",
            "v25030_whole_table_successes",
            "v25057_forward_wall_seconds",
            "v25057_quality_composite",
            "v25057_whole_table_successes",
            "whole_table_success_delta",
        }
        or set(policy)
        != {
            "network_model_search_fetch_evaluator_or_credential_accessed",
            "opaque_ids_or_prediction_hashes_used_only_for_in_memory_alignment",
            "question_id_prediction_page_url_query_gold_category_or_per_task_metric_emitted",
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection",
        }
        or set(authorization)
        != {
            "fresh_benchmark_external_mechanism_gate_design",
            "leaderboard_or_sota",
            "new_exact220_launch",
            "retry_resume_or_selective_rerun",
            "selective_revaluation",
        }
        or copied.get("role")
        != "v25058_v25057_zero_exposure_counts_only_diagnosis"
        or copied.get("fixed_denominator", {}).get("tasks") != 220
        or exposure.get("projected_pages") != 1523
        or exposure.get("characters_beyond_5k_prefix") != 30104588
        or exposure.get("mechanism_exposed_pages") != 0
        or exposure.get("changed_evidence_pages") != 0
        or exposure.get("exact_parent_prefix_handoff_pages") != 1523
        or exposure.get("positive_signed_credit_count") != 0
        or exposure.get("mechanism_gate_passed") is not False
        or cold.get("prediction_hash_same_tasks") != 12
        or cold.get("prediction_hash_changed_tasks") != 208
        or cold.get("whole_table_success_delta") != -1
        or cold.get("quality_composite_delta") != -0.0003312325898634505
        or diagnosis.get(
            "page_self_representation_naturally_reached_production"
        )
        is not False
        or diagnosis.get(
            "prediction_or_quality_difference_attributable_to_page_self_treatment"
        )
        is not False
        or diagnosis.get(
            "next_gate_requires_nonzero_natural_exposure_before_quality_or_exact220"
        )
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or policy.get(
            "question_id_prediction_page_url_query_gold_category_or_per_task_metric_emitted"
        )
        is not False
        or policy.get(
            "network_model_search_fetch_evaluator_or_credential_accessed"
        )
        is not False
        or policy.get(
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection"
        )
        is not False
        or authorization.get("new_exact220_launch") is not False
        or authorization.get("retry_resume_or_selective_rerun") is not False
        or authorization.get("selective_revaluation") is not False
        or authorization.get("leaderboard_or_sota") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.58 zero-exposure diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    payload = (
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V2.50.58 publication made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "projected_pages": value["production_exposure"]["projected_pages"],
                "mechanism_exposed_pages": value["production_exposure"][
                    "mechanism_exposed_pages"
                ],
                "prediction_hash_changed_tasks": value["cross_cold_run"][
                    "prediction_hash_changed_tasks"
                ],
                "exact_delta": value["cross_cold_run"][
                    "whole_table_success_delta"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
