#!/usr/bin/env python3
"""Content-free causal-funnel diagnosis for frozen V2.51.25 NO-GO."""

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

from deepwide_agent import v25125_visible_query_recovery_external_contract as contract  # noqa: E402
from scripts import run_v25125_visible_query_recovery_external as runner  # noqa: E402


OUTPUT = Path("results/v25126_v25125_recovery_mechanism_diagnosis_v1_20260811.json")
EXPECTED_HASHES = {
    str(contract.FORWARD_RESULT): "ac833f6fdf6fcc14e130dbedc9b2a171d690d38404cd752af16971f301ad8be8",
    str(contract.FORWARD_AUDIT): "850106d7fdeedbd8ab3d6f0cbad9f2fb2030adec8c663b97ab5f240a683cee1e",
    str(contract.TASK_ROWS): "146493a7b0c411c47dd06b9feddab6442fdd41761aeaef551dc1268ff27bf4d0",
    str(contract.PREDICTION_FREEZE): "58897835f625225f89583e74050e4894e09b96934d570547ecccf295798883bd",
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.26 expected JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    return [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]


def _count(rows: list[dict[str, Any]], predicate: Any) -> int:
    return sum(
        bool(
            predicate(
                row,
                row["content_free_receipt"],
                row["grounded_plan_receipt"],
                row["stage_failure_accounting"],
            )
        )
        for row in rows
    )


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    observed_hashes = {
        name: contract.sha256(ROOT / Path(name)) for name in EXPECTED_HASHES
    }
    if observed_hashes != EXPECTED_HASHES:
        raise RuntimeError("V2.51.26 frozen parent hash barrier drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    rows = _rows()
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or forward.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not False
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.51.26 parent decision barrier drifted")
    funnel = {
        "terminal_tasks": len(rows),
        "completed_runtime_tasks": _count(rows, lambda r, _c, _g, _s: r["runtime_completed"]),
        "failure_as_zero_tasks": _count(rows, lambda r, _c, _g, _s: r["failure_as_zero"]),
        "compatible_visible_query_seed_tasks": _count(
            rows, lambda _r, _c, _g, s: s["emitted_query_seed_count"] > 0
        ),
        "plan_model_effect_failure_tasks": _count(
            rows, lambda _r, _c, _g, s: s["plan_model_effect_failed"]
        ),
        "plan_output_validation_failure_tasks": _count(
            rows, lambda _r, _c, _g, s: s["plan_output_validation_failed"]
        ),
        "grounded_plan_strict_valid_tasks": _count(
            rows, lambda _r, _c, g, _s: g["model_output_strictly_valid"]
        ),
        "grounded_plan_strategy_applied_tasks": _count(
            rows, lambda _r, _c, g, _s: g["strategy_applied"]
        ),
        "strict_valid_but_strategy_handoff_tasks": _count(
            rows,
            lambda _r, _c, g, _s: g["model_output_strictly_valid"]
            and not g["strategy_applied"],
        ),
        "selection_changed_tasks": _count(
            rows, lambda _r, c, _g, _s: c["selection_changed"]
        ),
        "positive_target_field_page_gain_tasks": _count(
            rows, lambda _r, c, _g, _s: c["target_field_page_gain"] > 0
        ),
        "prediction_changed_tasks": _count(
            rows, lambda r, _c, _g, _s: r["prediction_changed"]
        ),
        "prediction_changed_without_selection_change_tasks": _count(
            rows, lambda r, c, _g, _s: r["prediction_changed"] and not c["selection_changed"]
        ),
        "prediction_changed_with_selection_but_no_field_page_gain_tasks": _count(
            rows,
            lambda r, c, _g, _s: r["prediction_changed"]
            and c["selection_changed"]
            and c["target_field_page_gain"] <= 0,
        ),
        "prediction_changed_with_positive_field_page_gain_tasks": _count(
            rows,
            lambda r, c, _g, _s: r["prediction_changed"]
            and c["target_field_page_gain"] > 0,
        ),
        "prediction_unchanged_despite_positive_field_page_gain_tasks": _count(
            rows,
            lambda r, c, _g, _s: not r["prediction_changed"]
            and c["target_field_page_gain"] > 0,
        ),
        "unattributable_prediction_changed_tasks": _count(
            rows,
            lambda r, c, _g, _s: r["prediction_changed"]
            and not c["attributable_prediction_change"],
        ),
        "attributable_prediction_changed_tasks": _count(
            rows, lambda _r, c, _g, _s: c["attributable_prediction_change"]
        ),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25126_v25125_content_free_recovery_mechanism_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": observed_hashes,
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "diagnosis": {
            "mechanism_gate_passed": False,
            "evaluator_quality_deepwidebench_or_sota_conclusion_forbidden": True,
            "visible_query_compatibility_and_runtime_totality_succeeded": (
                funnel["completed_runtime_tasks"] == 20
                and funnel["compatible_visible_query_seed_tasks"] == 20
                and funnel["plan_model_effect_failure_tasks"] == 0
                and funnel["plan_output_validation_failure_tasks"] == 0
            ),
            "grounded_plan_application_is_a_major_coverage_bottleneck": (
                funnel["grounded_plan_strategy_applied_tasks"] == 8
            ),
            "independent_synthesis_sampling_creates_unattributable_differences": (
                funnel["prediction_changed_without_selection_change_tasks"] == 3
                and funnel[
                    "prediction_changed_with_selection_but_no_field_page_gain_tasks"
                ]
                == 1
                and funnel["unattributable_prediction_changed_tasks"] == 4
            ),
            "most_positive_retrieval_gains_do_not_change_prediction": (
                funnel["positive_target_field_page_gain_tasks"] == 6
                and funnel["prediction_unchanged_despite_positive_field_page_gain_tasks"]
                == 5
            ),
            "next_runtime_must_apply_prediction_identity_handoff_without_actual_positive_field_page_gain": True,
            "next_runtime_must_make_actual_incremental_target_field_pages_salient_before_candidate_synthesis": True,
            "next_plan_should_improve_grounded_output_repair_without_relaxing_verbatim_grounding": True,
            "next_candidate_must_use_fresh_disjoint_population": True,
            "v25125_retry_resume_replacement_or_selective_rerun_forbidden": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_target_authority_column_prediction_answer_or_credential_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_counts_booleans_failure_types_and_parent_hashes_aggregated": True,
        },
        "authorization": {
            "v25125_evaluator_or_quality_result": False,
            "v25125_retry_resume_skip_replacement_or_selective_rerun": False,
            "new_disjoint_build_only_successor_design": True,
            "new_external_launch": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    funnel = copied.get("content_free_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    required_true = (
        "evaluator_quality_deepwidebench_or_sota_conclusion_forbidden",
        "visible_query_compatibility_and_runtime_totality_succeeded",
        "grounded_plan_application_is_a_major_coverage_bottleneck",
        "independent_synthesis_sampling_creates_unattributable_differences",
        "most_positive_retrieval_gains_do_not_change_prediction",
        "next_runtime_must_apply_prediction_identity_handoff_without_actual_positive_field_page_gain",
        "next_runtime_must_make_actual_incremental_target_field_pages_salient_before_candidate_synthesis",
        "next_plan_should_improve_grounded_output_repair_without_relaxing_verbatim_grounding",
        "next_candidate_must_use_fresh_disjoint_population",
        "v25125_retry_resume_replacement_or_selective_rerun_forbidden",
    )
    if (
        copied.get("role")
        != "v25126_v25125_content_free_recovery_mechanism_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or copied.get("parents") != EXPECTED_HASHES
        or diagnosis.get("mechanism_gate_passed") is not False
        or any(diagnosis.get(name) is not True for name in required_true)
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("terminal_tasks") != 20
        or funnel.get("completed_runtime_tasks") != 20
        or funnel.get("failure_as_zero_tasks") != 0
        or funnel.get("grounded_plan_strict_valid_tasks") != 10
        or funnel.get("grounded_plan_strategy_applied_tasks") != 8
        or funnel.get("strict_valid_but_strategy_handoff_tasks") != 2
        or funnel.get("selection_changed_tasks") != 8
        or funnel.get("positive_target_field_page_gain_tasks") != 6
        or funnel.get("prediction_changed_tasks") != 5
        or funnel.get("unattributable_prediction_changed_tasks") != 4
        or funnel.get("attributable_prediction_changed_tasks") != 1
        or funnel.get("prediction_unchanged_despite_positive_field_page_gain_tasks")
        != 5
        or authorization.get("new_disjoint_build_only_successor_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "new_disjoint_build_only_successor_design"
        )
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
    ):
        raise RuntimeError("V2.51.26 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    payload = (
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
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
