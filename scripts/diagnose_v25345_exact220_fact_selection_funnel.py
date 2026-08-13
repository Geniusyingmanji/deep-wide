#!/usr/bin/env python3
"""Aggregate-only fact-selection funnel across three frozen exact-220 runs.

V2.52.67 and V2.53.42 store questions, predictions, task identities, and
runtime envelopes in their frozen task rows.  This diagnosis never
materializes those values.  It lexically selects only sealed content-free
receipts and finite terminal flags, validates the receipts with the frozen
runtime validators, and emits aggregate counts only.

V2.48.57 predates the record/observation receipts.  Its already-published
aggregate forward result is therefore reported as ``not_instrumented`` rather
than incorrectly treating unobserved record counts as zero.

This is post-freeze analysis.  It cannot authorize a retry, model/search/fetch
effect, evaluator call, runtime treatment, or another DeepWideBench rollout.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24999_shared_response_selection_runtime as shared  # noqa: E402
from deepwide_agent import v25119_grounded_target_record_paired_runtime as paired  # noqa: E402
from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25265_production_only_totality_runtime as production  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from deepwide_agent import v25271_validated_production_checkpoint_runtime as checkpoint  # noqa: E402
from deepwide_agent import v25342_checkpoint_exact220_adapter as adapter  # noqa: E402
from scripts import diagnose_v25228_v25208_production_totality as nested  # noqa: E402
from scripts import diagnose_v25270_v25267_production_only_reliability as reliability  # noqa: E402


DATE = "20260813"
ROLE = "v25345_exact220_fact_selection_aggregate_diagnosis"
SOURCE = Path("scripts/diagnose_v25345_exact220_fact_selection_funnel.py")
TEST = Path("tests/test_diagnose_v25345_exact220_fact_selection_funnel.py")
OUTPUT = Path(
    f"results/v25345_exact220_fact_selection_funnel_diagnosis_v1_{DATE}.json"
)

RUNS = {
    "v24857": {
        "result": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "forward": Path(
            "results/v24857_pacing_aware_exact220_forward_result_v1_20260808.json"
        ),
        "postaudit": Path(
            "results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"
        ),
    },
    "v25267": {
        "result": Path(
            "results/v25267_production_only_exact220_result_v1_20260812.json"
        ),
        "forward": Path(
            "results/v25267_production_only_exact220_forward_result_v1_20260812.json"
        ),
        "postaudit": Path(
            "results/v25267_production_only_exact220_postresult_audit_v1_20260812.json"
        ),
        "rows": Path(
            "outputs/v25267_production_only_exact220_v1_20260812/frozen_task_results.jsonl"
        ),
    },
    "v25342": {
        "result": Path(
            "results/v25342_checkpoint_exact220_result_v1_20260813.json"
        ),
        "forward": Path(
            "results/v25342_checkpoint_exact220_forward_result_v1_20260813.json"
        ),
        "postaudit": Path(
            "results/v25344_checkpoint_exact220_postresult_audit_v1_20260813.json"
        ),
        "rows": Path(
            "outputs/v25342_checkpoint_exact220_v1_20260813/frozen_task_results.jsonl"
        ),
    },
}
REVISION_DIAGNOSES = {
    "v25137_sparse_revision": Path(
        "results/v25138_v25137_sparse_production_diagnosis_v1_20260812.json"
    ),
    "v25141_targeted_revision": Path(
        "results/v25142_v25141_targeted_revision_diagnosis_v1_20260812.json"
    ),
    "v25248_shadow_overshoot": Path(
        "results/v25252_v25248_shadow_no_go_diagnosis_v1_20260812.json"
    ),
}
EXPECTED_SHA256 = {
    "v24857.result": "a9e51c5c479a79e46f74574dac905bc607032be501b8a21a696106172f59f1d9",
    "v24857.forward": "1b03564da3dae00bbbfb75e1fd68f425e2fd12c40eac615b6a69558040680581",
    "v24857.postaudit": "cf49f952533656d805ca13e807689ea1cd07215553b3f3f9b2dbbf11c115ca20",
    "v25267.result": "45231ef9e8bd09b55daa6de53e7310865df036cdb5ac2ce7390853e2ff853953",
    "v25267.forward": "8e31dc56d5b878042398552174d2a5bf6f046ee5df39a2d414e8517f463e2d71",
    "v25267.postaudit": "086e9863c63bd7f8413d84c6f43ce2dbb0b33e26f352469c8b4cde220cd35e68",
    "v25267.rows": "ea15f93e9126f18dbcb4c9272551045176396b6cb67af9a2b3d02c38b6330526",
    "v25342.result": "ae0cba954f3b7102db2ba7c111af6ab9173009ffdbddcb8463eed1095107a4eb",
    "v25342.forward": "d01ba68af2757088a67c5987215de75cc1b30f2e4fc9e91c0f78ae6b1b81902f",
    "v25342.postaudit": "f073351abab6dc311b57d17493f12bcd61309145337d25d25c08846bb5c5f745",
    "v25342.rows": "0807b7b51b9c46a06e1162dbfffcaaa7e08b1da6dae26532828a631a34241e8e",
    "revision.v25137_sparse_revision": "d5a86211c770b02dc280fa1bd792f8cca02921aa51deed2d6ae2056f314f26cb",
    "revision.v25141_targeted_revision": "61d4dd42b58d86dc55248889ed4ab4f86cc4d997ef465dda9f4de931dfff829d",
    "revision.v25248_shadow_overshoot": "f9c0eb558092ff92c16a939bc951da2fbde2989b54dbebb91fdd794dd22fe4ec",
}

EXPECTED_AGGREGATE_SHA256 = (
    "2eefad3ce651731208a886907e18ad458fe3301a2c17b430ca465090fc229b77"
)

V25267_PARENT = ("runtime_result", "parent_result")
V25342_PARENT = (
    "runtime_result",
    "checkpoint_runtime_result",
    "parent_result",
)
V25342_CHECKPOINT_RECEIPT = (
    "runtime_result",
    "checkpoint_runtime_result",
    "content_free_receipt",
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.53.45 expected ordinary repository file: {relative}")
    return path


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.45 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], seal_name: str) -> bool:
    unsigned = copy.deepcopy(dict(value))
    seal = unsigned.pop(seal_name, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def _parent_path(prefix: Sequence[str], *suffix: str) -> tuple[str, ...]:
    return (*tuple(prefix), *suffix)


def _validated_parent_funnel(
    line: str, *, parent_prefix: Sequence[str]
) -> dict[str, Any]:
    paired_value = nested._selected_nested_value(
        line, _parent_path(parent_prefix, "content_free_receipt")
    )
    first_value = nested._selected_nested_value(
        line,
        _parent_path(
            parent_prefix,
            "physical_wave_receipts",
            "shared_first_wave",
        ),
    )
    second_value = nested._selected_nested_value(
        line,
        _parent_path(
            parent_prefix,
            "physical_wave_receipts",
            "shared_second_wave_union",
        ),
    )
    selection_value = nested._selected_nested_value(
        line, _parent_path(parent_prefix, "selection_receipt")
    )
    if not all(
        isinstance(value, Mapping)
        for value in (paired_value, first_value, second_value, selection_value)
    ):
        raise RuntimeError("V2.53.45 selected parent receipt is not an object")
    parent_receipt = paired.validate_receipt(paired_value)
    first = shared.validate_first_receipt(first_value)
    second = paired.validate_second_wave_receipt(second_value)
    selection = paired.selector.validate_receipt(selection_value)
    if (
        parent_receipt["selection_receipt"] != selection
        or second["selection_receipt"] != selection
        or parent_receipt[
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or parent_receipt["entropy_or_information_gain_assigns_signed_credit"]
        is not False
    ):
        raise RuntimeError("V2.53.45 content-free parent cross-binding drifted")
    first_fetch = first["fetch_receipt"]
    second_fetch = second["fetch_receipt"]
    candidate = parent_receipt["arm_metrics"][paired.CANDIDATE_ARM]
    control = parent_receipt["arm_metrics"][paired.CONTROL_ARM]
    return {
        "grounded_plan_strategy_applied": parent_receipt[
            "grounded_plan_strategy_applied"
        ],
        "selection_strategy_eligible": parent_receipt[
            "selection_strategy_eligible"
        ],
        "selection_changed": parent_receipt["selection_changed"],
        "retrieval_mechanism_engaged": parent_receipt[
            "retrieval_mechanism_engaged"
        ],
        "positive_target_field_page_gain": (
            parent_receipt["target_field_page_gain"] > 0
        ),
        "positive_target_field_pair_gain": (
            parent_receipt["target_field_pair_gain"] > 0
        ),
        "attributable_prediction_change": parent_receipt[
            "attributable_prediction_change"
        ],
        "prediction_changed": parent_receipt["prediction_changed"],
        "usable_pages": first["usable_page_count"]
        + second["physical_union_usable_page_count"],
        "projected_pages": first_fetch["projected_page_count"]
        + second_fetch["projected_page_count"],
        "input_content_characters": first_fetch["input_content_characters"]
        + second_fetch["input_content_characters"],
        "input_characters_beyond_parent_prefix": first_fetch[
            "input_characters_beyond_parent_prefix"
        ]
        + second_fetch["input_characters_beyond_parent_prefix"],
        "discovered_records": first_fetch["discovered_record_count"]
        + second_fetch["discovered_record_count"],
        "admissible_records": first_fetch["admissible_record_count"]
        + second_fetch["admissible_record_count"],
        "admissible_observations": first_fetch[
            "admissible_bound_observation_count"
        ]
        + second_fetch["admissible_bound_observation_count"],
        "retained_records": first_fetch["retained_record_count"]
        + second_fetch["retained_record_count"],
        "retained_observations": first_fetch[
            "retained_bound_observation_count"
        ]
        + second_fetch["retained_bound_observation_count"],
        "mechanism_engaged_pages": first_fetch["mechanism_engaged_page_count"]
        + second_fetch["mechanism_engaged_page_count"],
        "unique_search_urls": selection["unique_search_url_count"],
        "unique_page_link_urls": selection["unique_page_link_url_count"],
        "target_field_bearing_urls": selection["target_field_bearing_url_count"],
        "target_record_urls": selection["target_record_url_count"],
        "target_structured_record_urls": selection[
            "target_structured_record_url_count"
        ],
        "candidate_usable_pages": candidate["usable_page_count"],
        "candidate_evidence_characters": parent_receipt[
            "candidate_evidence_characters"
        ],
        "control_evidence_characters": parent_receipt[
            "control_evidence_characters"
        ],
        "candidate_model_success": candidate["model_success"],
        "control_model_success": control["model_success"],
    }


def safe_v25267_row(line: str) -> dict[str, Any]:
    """Decode only V2.52.67 terminal flags and sealed content-free receipts."""

    safe = reliability.safe_row(line)
    output = {
        "runtime_completed": bool(safe["runtime_completed"]),
        "failure_as_zero": bool(safe["failure_as_zero"]),
        "parent_result_retained": False,
        "parent_funnel": None,
    }
    receipt = safe.get("content_free_receipt")
    if isinstance(receipt, Mapping) and receipt["parent_result_valid"]:
        output["parent_result_retained"] = True
        output["parent_funnel"] = _validated_parent_funnel(
            line, parent_prefix=V25267_PARENT
        )
    return output


def safe_v25342_row(line: str) -> dict[str, Any]:
    """Decode only V2.53.42 terminal flags and sealed content-free receipts."""

    selected = reliability._selected_top_level(line)
    stage_value = selected["content_free_stage_receipt"]
    budget_value = selected["content_free_budget_receipt"]
    checkpoint_value = nested._selected_nested_value(
        line, V25342_CHECKPOINT_RECEIPT
    )
    if not all(
        isinstance(value, Mapping)
        for value in (stage_value, budget_value, checkpoint_value)
    ):
        raise RuntimeError("V2.53.45 checkpoint receipt is not an object")
    stage = adapter.validate_stage_receipt(stage_value)
    budget = cap.validate_budget_receipt(budget_value)
    receipt = checkpoint.validate_receipt(checkpoint_value)
    expected_kind = (
        "model_generated"
        if receipt["checkpoint_provider_output_valid"]
        else "fallback"
    )
    if (
        selected["terminal"] is not True
        or selected["runtime_completed"] is not True
        or selected["failure_as_zero"] is not False
        or selected["outer_failure_type"] is not None
        or selected["prediction_kind"] != expected_kind
        or stage["runtime_returned"] is not True
        or stage["failure_present"] is not False
        or stage["outer_physical_budget_receipt"] != budget
        or receipt["physical_query_count"] != budget["query_admitted_count"]
        or receipt["physical_fetch_count"] != budget["fetch_admitted_count"]
        or receipt["physical_model_forward_count"] != budget["model_admitted_count"]
        or any(
            selected[name] is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "retry_resume_skip_backfill_replacement_or_selective_rerun",
                "contains_question_query_url_page_answer_or_credential_outside_prediction",
            )
        )
    ):
        raise RuntimeError("V2.53.45 checkpoint row drifted")
    output = {
        "runtime_completed": True,
        "failure_as_zero": False,
        "parent_result_retained": bool(receipt["parent_result_retained"]),
        "checkpoint_recovery_event": bool(
            receipt["post_checkpoint_recoverable_failure_present"]
        ),
        "parent_funnel": None,
    }
    if receipt["parent_result_retained"]:
        output["parent_funnel"] = _validated_parent_funnel(
            line, parent_prefix=V25342_PARENT
        )
    return output


FUNNEL_BOOLEAN_FIELDS = (
    "grounded_plan_strategy_applied",
    "selection_strategy_eligible",
    "selection_changed",
    "retrieval_mechanism_engaged",
    "positive_target_field_page_gain",
    "positive_target_field_pair_gain",
    "attributable_prediction_change",
    "prediction_changed",
    "candidate_model_success",
    "control_model_success",
)
FUNNEL_COUNT_FIELDS = (
    "usable_pages",
    "projected_pages",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "discovered_records",
    "admissible_records",
    "admissible_observations",
    "retained_records",
    "retained_observations",
    "mechanism_engaged_pages",
    "unique_search_urls",
    "unique_page_link_urls",
    "target_field_bearing_urls",
    "target_record_urls",
    "target_structured_record_urls",
    "candidate_usable_pages",
    "candidate_evidence_characters",
    "control_evidence_characters",
)


def _aggregate_instrumented(name: str) -> dict[str, Any]:
    if name not in {"v25267", "v25342"}:
        raise ValueError("V2.53.45 unknown instrumented run")
    parser = safe_v25267_row if name == "v25267" else safe_v25342_row
    rows = [
        parser(line)
        for line in _ordinary(RUNS[name]["rows"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(rows) != 220:
        raise RuntimeError("V2.53.45 fixed denominator drifted")
    funnels = [row["parent_funnel"] for row in rows if row["parent_funnel"]]
    output: dict[str, Any] = {
        "fixed_task_denominator": len(rows),
        "runtime_completed_tasks": sum(row["runtime_completed"] for row in rows),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in rows),
        "observable_parent_funnel_tasks": len(funnels),
        "parent_funnel_unavailable_tasks": len(rows) - len(funnels),
        "record_observation_instrumentation": "available_on_observable_parent_funnel",
        "funnel_boolean_task_counts": {
            field: sum(bool(funnel[field]) for funnel in funnels)
            for field in FUNNEL_BOOLEAN_FIELDS
        },
        "funnel_count_totals": {
            field: sum(int(funnel[field]) for funnel in funnels)
            for field in FUNNEL_COUNT_FIELDS
        },
        "positive_signed_credit_count": 0,
    }
    if name == "v25267":
        output["checkpoint_recovery_event_tasks"] = 0
        output["parent_funnel_unavailable_due_to_outer_failure_tasks"] = sum(
            row["failure_as_zero"] for row in rows
        )
        output["parent_funnel_unavailable_after_completed_runtime_tasks"] = sum(
            row["runtime_completed"] and not row["parent_result_retained"]
            for row in rows
        )
    else:
        recovery = sum(row["checkpoint_recovery_event"] for row in rows)
        output["checkpoint_recovery_event_tasks"] = recovery
        output["parent_funnel_unavailable_due_to_outer_failure_tasks"] = 0
        output["parent_funnel_unavailable_after_completed_runtime_tasks"] = sum(
            row["runtime_completed"] and not row["parent_result_retained"]
            for row in rows
        )
        if recovery != output[
            "parent_funnel_unavailable_after_completed_runtime_tasks"
        ]:
            raise RuntimeError("V2.53.45 checkpoint observability accounting drifted")
    return output


def _validate_result_and_audit(name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    result = _read_json(RUNS[name]["result"])
    audit = _read_json(RUNS[name]["postaudit"])
    metrics = result.get("metrics", {}).get("all_220", {})
    claims = result.get("claims", {})
    if (
        not _sealed(result, "result_payload_sha256")
        or result.get("status") != "exact220_single_rollout_complete"
        or result.get("selected") != 220
        or metrics.get("selected") != 220
        or claims.get("avg_at_4") is not False
        or claims.get("leaderboard_submitted") is not False
        or claims.get("sota") is not False
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
    ):
        raise RuntimeError(f"V2.53.45 frozen {name} result barrier drifted")
    return result, audit


def _quality_summary(name: str) -> dict[str, Any]:
    result, _audit = _validate_result_and_audit(name)
    metrics = result["metrics"]["all_220"]
    efficiency = result["efficiency"]
    return {
        "selected": metrics["selected"],
        "whole_table_successes": metrics["whole_table_successes"],
        "score": metrics["score"],
        "entity_acc": metrics["entity_acc"],
        "f1_by_row": metrics["f1_by_row"],
        "f1_by_item": metrics["f1_by_item"],
        "column_f1": metrics["column_f1"],
        "quality_composite": metrics["quality_composite"],
        "evaluator_valid": metrics["evaluator_valid"],
        "evaluator_invalid_or_not_run": metrics[
            "evaluator_invalid_or_not_run"
        ],
        "model_generated_tables": metrics["model_generated_tables"],
        "fallback_tables": metrics["fallback_tables"],
        "system_total_tokens": metrics["system_total_tokens"],
        "forward_wall_seconds": efficiency["forward_wall_seconds"],
        "evaluator_parallel_wall_seconds": efficiency[
            "evaluator_parallel_wall_seconds"
        ],
    }


def _v24857_legacy_funnel() -> dict[str, Any]:
    forward = _read_json(RUNS["v24857"]["forward"])
    direct = forward.get("direct_search_totals", {})
    control = forward.get("fixed_full_budget_control_totals", {})
    if (
        not _sealed(forward, "result_payload_sha256")
        or forward.get("selected") != 220
        or forward.get("terminal_predictions") != 220
        or forward.get("official_evaluator_called") is not False
        or direct.get("valid_receipts") != 220
        or control.get("valid_control_receipts") != 220
        or control.get("task_results") != 220
    ):
        raise RuntimeError("V2.53.45 V2.48.57 aggregate forward barrier drifted")
    return {
        "fixed_task_denominator": 220,
        "runtime_completed_tasks": 220,
        "failure_as_zero_tasks": 0,
        "record_observation_instrumentation": "not_instrumented",
        "record_or_observation_zero_claimed": False,
        "successful_queries": direct["successful_queries"],
        "projected_url_leads": direct["projected_url_leads"],
        "fetches_attempted": control["total_fetches_attempted"],
        "second_wave_executed_tasks": control["second_wave_executed_tasks"],
        "record_observation_funnel_cross_version_comparison_authorized": False,
        "positive_signed_credit_count": 0,
    }


def _revision_history() -> dict[str, Any]:
    values = {
        name: _read_json(path) for name, path in REVISION_DIAGNOSES.items()
    }
    for name, value in values.items():
        if not _sealed(value, "diagnosis_payload_sha256"):
            raise RuntimeError(f"V2.53.45 revision diagnosis seal drifted: {name}")
    sparse = values["v25137_sparse_revision"]["aggregate"]
    targeted = values["v25141_targeted_revision"]["aggregate"]
    overshoot = values["v25248_shadow_overshoot"]["diagnosis"]
    output = {
        "v25137_sparse_revision": {
            "provider_forward_tasks": sparse["revision_provider_forward_tasks"],
            "provider_valid_tasks": sparse["revision_provider_valid_tasks"],
            "attributable_prediction_changed_tasks": sparse[
                "attributable_prediction_changed_tasks"
            ],
        },
        "v25141_targeted_revision": {
            "provider_forward_tasks": targeted["revision_provider_forward_tasks"],
            "provider_valid_tasks": targeted["revision_provider_valid_tasks"],
            "proposed_changed_cells": targeted[
                "targeted_rejected_changed_cells"
            ]
            + targeted["targeted_applied_changed_cells"],
            "applied_changed_cells": targeted["targeted_applied_changed_cells"],
            "attributable_prediction_changed_tasks": targeted[
                "attributable_prediction_changed_tasks"
            ],
        },
        "v25248_shadow_overshoot": {
            "provider_valid_tasks": overshoot[
                "overshoot_revision_provider_valid_tasks"
            ],
            "final_prediction_changed_tasks": overshoot[
                "overshoot_final_prediction_changed_from_production_tasks"
            ],
            "attributable_prediction_changed_tasks": overshoot[
                "overshoot_attributable_prediction_change_tasks"
            ],
        },
        "direct_fourth_model_call_restoration_supported": False,
    }
    return output


def _parents(*, require_clean: bool) -> dict[str, str]:
    if require_clean and (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.53.45 requires clean pushed HEAD")
    observed: dict[str, str] = {}
    for name, paths in RUNS.items():
        for kind, path in paths.items():
            observed[f"{name}.{kind}"] = contract.sha256(_ordinary(path))
    for name, path in REVISION_DIAGNOSES.items():
        observed[f"revision.{name}"] = contract.sha256(_ordinary(path))
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.53.45 frozen parent hash drifted")
    for name in RUNS:
        _validate_result_and_audit(name)
    return observed


def _aggregate() -> dict[str, Any]:
    return {
        "quality": {name: _quality_summary(name) for name in RUNS},
        "fact_selection_funnel": {
            "v24857": _v24857_legacy_funnel(),
            "v25267": _aggregate_instrumented("v25267"),
            "v25342": _aggregate_instrumented("v25342"),
        },
        "revision_history": _revision_history(),
    }


def build_diagnosis(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    aggregate = _aggregate()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": _parents(require_clean=require_clean),
        "aggregate": aggregate,
        "diagnosis": {
            "v25342_is_latest_complete_rollout_but_not_observed_single_rollout_peak": True,
            "v24857_record_observation_counts_are_unobserved_not_zero": True,
            "v25267_and_v25342_have_comparable_record_observation_instrumentation": True,
            "v25342_observes_one_retained_record_and_two_observations_across_1506_pages": True,
            "high_search_and_page_volume_does_not_convert_to_record_observations": True,
            "page_to_record_to_admissible_observation_is_the_primary_observed_bottleneck": True,
            "zero_attributable_prediction_change_is_censored_by_local_identity_replay": True,
            "zero_prediction_change_cannot_alone_establish_retrieval_failure": True,
            "historical_revision_provider_success_does_not_support_direct_fourth_call_restoration": True,
            "next_successor_should_change_fact_representation_before_first_production_synthesis": True,
            "next_successor_should_share_search_responses_and_page_bytes_with_control": True,
            "next_successor_should_preserve_query_fetch_model_token_context_and_wall_caps": True,
            "next_mechanism_gate_requires_more_retained_admissible_observations_and_attributable_prediction_change": True,
            "entropy_information_gain_remains_shadow_only_and_cannot_create_credit_sign": True,
            "aggregate_cross_rollout_score_difference_is_not_a_causal_mechanism_effect": True,
        },
        "content_policy": {
            "task_rows_opened_only_for_lexical_content_free_receipt_selection": True,
            "sealed_runtime_receipts_validated_with_frozen_validators": True,
            "v24857_uses_published_aggregate_forward_only": True,
            "opaque_id_question_query_url_title_page_prediction_answer_mapping_gold_category_split_evaluator_metric_score_or_credential_decoded_hashed_or_emitted": False,
            "task_identifier_or_per_task_metric_emitted": False,
            "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
            "historical_outcome_authorized_as_future_runtime_router_signal": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "aggregate_only_fact_selection_diagnosis": True,
            "shared_prefix_fact_representation_successor_build_only": True,
            "runtime_activation_or_prediction_change": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
            "external_forward_or_new_deepwidebench_rollout": False,
            "avg_at_4_leaderboard_or_sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    aggregate = copied.get("aggregate")
    diagnosis = copied.get("diagnosis")
    policy = copied.get("content_policy")
    authorization = copied.get("authorization")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "parents",
            "aggregate",
            "diagnosis",
            "content_policy",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("parents") != EXPECTED_SHA256
        or not isinstance(aggregate, Mapping)
        or contract.payload_sha256(aggregate) != EXPECTED_AGGREGATE_SHA256
        or aggregate.get("quality", {}).get("v25342", {}).get(
            "whole_table_successes"
        )
        != 6
        or aggregate.get("quality", {}).get("v24857", {}).get(
            "whole_table_successes"
        )
        != 9
        or aggregate.get("fact_selection_funnel", {}).get("v24857", {}).get(
            "record_observation_instrumentation"
        )
        != "not_instrumented"
        or aggregate.get("fact_selection_funnel", {}).get("v24857", {}).get(
            "record_or_observation_zero_claimed"
        )
        is not False
        or aggregate.get("fact_selection_funnel", {}).get("v25267", {}).get(
            "observable_parent_funnel_tasks"
        )
        != 208
        or aggregate.get("fact_selection_funnel", {}).get("v25342", {}).get(
            "observable_parent_funnel_tasks"
        )
        != 209
        or aggregate.get("fact_selection_funnel", {})
        .get("v25267", {})
        .get("funnel_count_totals", {})
        .get("retained_records")
        != 0
        or aggregate.get("fact_selection_funnel", {})
        .get("v25342", {})
        .get("funnel_count_totals", {})
        .get("retained_records")
        != 1
        or aggregate.get("fact_selection_funnel", {})
        .get("v25342", {})
        .get("funnel_count_totals", {})
        .get("retained_observations")
        != 2
        or aggregate.get("fact_selection_funnel", {})
        .get("v25342", {})
        .get("funnel_boolean_task_counts", {})
        .get("attributable_prediction_change")
        != 0
        or aggregate.get("revision_history", {}).get(
            "direct_fourth_model_call_restoration_supported"
        )
        is not False
        or not isinstance(diagnosis, Mapping)
        or not diagnosis
        or any(value is not True for value in diagnosis.values())
        or policy
        != {
            "task_rows_opened_only_for_lexical_content_free_receipt_selection": True,
            "sealed_runtime_receipts_validated_with_frozen_validators": True,
            "v24857_uses_published_aggregate_forward_only": True,
            "opaque_id_question_query_url_title_page_prediction_answer_mapping_gold_category_split_evaluator_metric_score_or_credential_decoded_hashed_or_emitted": False,
            "task_identifier_or_per_task_metric_emitted": False,
            "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
            "historical_outcome_authorized_as_future_runtime_router_signal": False,
        }
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "aggregate_only_fact_selection_diagnosis": True,
            "shared_prefix_fact_representation_successor_build_only": True,
            "runtime_activation_or_prediction_change": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
            "external_forward_or_new_deepwidebench_rollout": False,
            "avg_at_4_leaderboard_or_sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.45 diagnosis drifted")
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
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("diagnose",))
    args = parser.parse_args()
    if args.command == "diagnose":
        value = build_diagnosis()
        publish_exclusive(ROOT / OUTPUT, value)
        print(
            json.dumps(
                {
                    "path": str(OUTPUT),
                    "v25342_retained_records": value["aggregate"][
                        "fact_selection_funnel"
                    ]["v25342"]["funnel_count_totals"]["retained_records"],
                    "new_exact220_rollout": value["authorization"][
                        "external_forward_or_new_deepwidebench_rollout"
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
