#!/usr/bin/env python3
"""Content-free eligibility diagnosis for the V2.52.90 third-slot treatment."""

from __future__ import annotations

import copy
import hashlib
import json
import re
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

from deepwide_agent import v24630_exact220_task_integration as parent  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from deepwide_agent import v25289_monotone_unknown_fill as core  # noqa: E402
from deepwide_agent import v25290_monotone_unknown_fill_integration as candidate  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import audit_v25291_monotone_unknown_fill_build as build_audit  # noqa: E402


DATE = "20260813"
ROLE = "v25292_monotone_unknown_fill_eligibility_diagnosis"
OUTPUT = Path(
    f"results/v25292_monotone_unknown_fill_eligibility_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25292_monotone_unknown_fill_eligibility.py")
TEST = Path("tests/test_diagnose_v25292_monotone_unknown_fill_eligibility.py")
BUILD_AUDIT = build_audit.OUTPUT
LEGACY_ROOT = Path("outputs/v24857_pacing_aware_exact220_v1_20260808")
LEGACY_RUNTIME = LEGACY_ROOT / "runtime_predictions.jsonl"
LEGACY_SUMMARY = LEGACY_ROOT / "run_summary.json"
LEGACY_FORWARD_AUDIT = Path(
    "results/v24857_pacing_aware_exact220_forward_audit_v1_20260808.json"
)
HISTORICAL_CONVERSION_RESULT = Path(
    "results/v24884_mapping_recovery_exact220_forward_result_v1_20260808.json"
)
HISTORICAL_CONVERSION_AUDIT = Path(
    "results/v24884_mapping_recovery_exact220_forward_audit_v1_20260808.json"
)
FIXED_INPUTS = {
    BUILD_AUDIT: (
        "6c714a6d20c90a401c311da4c8aa4477ef1570019821b17431daeed0a1455aeb"
    ),
    LEGACY_RUNTIME: (
        "efa0c153f2ec287dcd92627dc0ee37ef4cb6390c178ec04c0b68bf0cf23e7c30"
    ),
    LEGACY_SUMMARY: (
        "f34fc04629b4424bf87aa8284a2188f7d9edcada8768da34732863b3db39de38"
    ),
    LEGACY_FORWARD_AUDIT: (
        "dacd35b31f78a8e04ee39b23efbd275a0c44a367e62e8ca90e7caf21bc092fe0"
    ),
    HISTORICAL_CONVERSION_RESULT: (
        "e7f602c3ea4a24468dfb94074e010ed33b81105fb3d3205dd006a60241d35d73"
    ),
    HISTORICAL_CONVERSION_AUDIT: (
        "c397002d27de7917b1e88fcd4ba0605920d045a72b70cb262fb58a871a394749"
    ),
}
SELECTED = 220
EXPECTED_RESULT_VECTOR_SHA256 = (
    "b768b3dfdc6b87719945767545152e843a149046f34713f94ad9af96ec996456"
)
EXPECTED_RESULT_PATH_SHA256 = (
    "25c0cb9d22ab895518251d0421de62716325d72df0fa3e5a40196f18a9b9f62d"
)
EXPECTED_RESULT_CONTENT_SHA256 = (
    "86e58935747b1d14582c1b0e1f2abec7248cf62be0348f0aea70624b3a298667"
)
EXPECTED_TASK_FILES = frozenset(
    {
        "child_terminal_receipt.json",
        "citation_title_backfill_receipt.json",
        "direct_search_receipt.json",
        "model_slot_receipt.json",
        "pacing_aware_admission_receipt.json",
        "parent_exit_receipt.json",
        "rate_aware_search_receipt.json",
        "result.json",
        "safe_progress.json",
        "search_single_shot_receipt.json",
        "transport_health.json",
        "visible_task.json",
    }
)
EXPECTED_CROSS_TAB = {
    "parent_ineligible_without_unknown": 1,
    "parent_ineligible_with_unknown": 1,
    "parent_eligible_without_unknown": 177,
    "parent_eligible_with_unknown": 41,
}
EXPECTED_UNKNOWN_BINS = {
    "zero": 178,
    "one_to_three": 13,
    "four_to_ten": 11,
    "eleven_to_fifty": 11,
    "fifty_one_or_more": 7,
}
EXPECTED_MODEL_CALL_DISTRIBUTION = {"2": 218, "3": 2}
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "source_and_test_tracked",
        "fixed_inputs_exact",
        "v25291_build_audit_valid_and_design_only",
        "legacy_forward_is_frozen_label_blind_220",
        "legacy_result_vector_exact220_hash_bound",
        "all_legacy_envelopes_validate_and_match_runtime_freeze",
        "unknown_counts_recomputed_with_v25289_semantics",
        "legacy_telemetry_semantic_difference_explained_and_not_used",
        "prepage_eligibility_exact41_nonzero",
        "same_forward_page_bytes_absent_from_frozen_task_surface",
        "full_eligibility_supported_fill_and_prediction_change_not_inferred",
        "historical_conversion_zero_is_bound_but_not_transferred",
        "no_external_effect_performed",
    }
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _read_object(relative: Path) -> dict[str, Any]:
    value = json.loads(base._ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.92 expected a repository JSON object")
    return value


def _fixed_inputs() -> dict[str, str]:
    observed = {str(path): base.sha256(path) for path in FIXED_INPUTS}
    expected = {str(path): digest for path, digest in FIXED_INPUTS.items()}
    if observed != expected:
        raise RuntimeError("V2.52.92 fixed input hash drifted")
    return observed


def _result_paths() -> list[Path]:
    return [
        LEGACY_ROOT / "tasks" / f"task_{position:04d}" / "result.json"
        for position in range(1, SELECTED + 1)
    ]


def _result_vector() -> list[dict[str, str]]:
    vector = [
        {"path": str(path), "sha256": base.sha256(path)}
        for path in _result_paths()
    ]
    if (
        len(vector) != SELECTED
        or seal.payload_sha256(vector) != EXPECTED_RESULT_VECTOR_SHA256
        or seal.payload_sha256([row["path"] for row in vector])
        != EXPECTED_RESULT_PATH_SHA256
        or seal.payload_sha256([row["sha256"] for row in vector])
        != EXPECTED_RESULT_CONTENT_SHA256
    ):
        raise RuntimeError("V2.52.92 frozen result vector drifted")
    return vector


def _parent_barrier() -> dict[str, Any]:
    fixed = _fixed_inputs()
    build = build_audit.validate_audit(_read_object(BUILD_AUDIT))
    forward = _read_object(LEGACY_FORWARD_AUDIT)
    summary = _read_object(LEGACY_SUMMARY)
    historical = _read_object(HISTORICAL_CONVERSION_RESULT)
    historical_audit = _read_object(HISTORICAL_CONVERSION_AUDIT)
    coverage = historical.get("coverage_revision_totals") or {}
    if (
        build["audit_valid"] is not True
        or build["findings"] != []
        or build["authorization"][
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design"
        ]
        is not True
        or build["authorization"]["external_activation_or_launch"] is not False
        or build["authorization"][
            "deepwidebench_dev64_exact220_forward_or_evaluator"
        ]
        is not False
        or forward.get("role") != "v24800_exact220_forward_audit"
        or forward.get("protocol_id")
        != "v24857_same_pass_pacing_aware_fixed_full_budget_exact220_v1"
        or forward.get("selected") != SELECTED
        or forward.get("terminal_predictions") != SELECTED
        or forward.get("model_generated_tables") != SELECTED
        or forward.get("fallback_tables") != 0
        or forward.get("audit_valid") is not True
        or forward.get("findings") != []
        or summary.get("selected") != SELECTED
        or summary.get("completed") != SELECTED
        or summary.get("failed") != 0
        or summary.get("model_generated_tables") != SELECTED
        or summary.get("fallback_tables") != 0
        or summary.get("parent_exit_taxonomy") != {"success": SELECTED}
        or summary.get("official_evaluator_called") is not False
        or summary.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or historical.get("role")
        != "v24884_mapping_recovery_exact220_forward_result"
        or historical.get("protocol_id")
        != "v24884_mapping_recovery_fixed_budget_exact220_v1"
        or historical.get("selected") != SELECTED
        or historical.get("terminal_predictions") != SELECTED
        or historical.get("official_evaluator_called") is not False
        or coverage.get("logical_revision_calls") != 153
        or coverage.get("admitted_existing_cell_changes") != 0
        or coverage.get("admitted_new_rows") != 0
        or coverage.get("prediction_changed_tasks") != 0
        or historical_audit.get("role") != "v24791_exact220_forward_audit"
        or historical_audit.get("protocol_id")
        != historical.get("protocol_id")
        or historical_audit.get("audit_valid") is not True
        or historical_audit.get("findings") != []
        or historical_audit.get("forward_result_sha256")
        != FIXED_INPUTS[HISTORICAL_CONVERSION_RESULT]
    ):
        raise RuntimeError("V2.52.92 parent authority drifted")
    return {
        "fixed_inputs": fixed,
        "build": build,
        "forward": forward,
        "summary": summary,
        "historical": historical,
        "historical_audit": historical_audit,
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _unknown_bin(count: int) -> str:
    if count == 0:
        return "zero"
    if count <= 3:
        return "one_to_three"
    if count <= 10:
        return "four_to_ten"
    if count <= 50:
        return "eleven_to_fifty"
    return "fifty_one_or_more"


def _runtime_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    path = base._ordinary(LEGACY_RUNTIME)
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("V2.52.92 runtime row is not an object")
            opaque_id = value.get("opaque_id")
            cost = value.get("cost") or {}
            model_calls = (cost if isinstance(cost, Mapping) else {}).get(
                "model_calls"
            )
            prediction = value.get("prediction")
            if (
                set(value)
                != {
                    "completion_kind",
                    "cost",
                    "elapsed_seconds",
                    "label_blind",
                    "mapping_gold_category_question_type_split_evaluator_score_read",
                    "opaque_id",
                    "prediction",
                    "prediction_sha256",
                    "status",
                }
                or not isinstance(opaque_id, str)
                or OPAQUE.fullmatch(opaque_id) is None
                or opaque_id in rows
                or value.get("status") != "completed"
                or value.get("label_blind") is not True
                or value.get(
                    "mapping_gold_category_question_type_split_evaluator_score_read"
                )
                is not False
                or not isinstance(prediction, str)
                or not prediction
                or value.get("prediction_sha256") != _sha256_text(prediction)
                or isinstance(model_calls, bool)
                or not isinstance(model_calls, int)
                or model_calls not in {2, 3}
            ):
                raise RuntimeError("V2.52.92 runtime row drifted")
            rows[opaque_id] = {
                "prediction_sha256": value["prediction_sha256"],
                "model_calls": model_calls,
            }
    if len(rows) != SELECTED:
        raise RuntimeError("V2.52.92 runtime denominator drifted")
    return rows


def _scan_legacy_population() -> dict[str, Any]:
    _result_vector()
    runtime = _runtime_rows()
    cross = Counter()
    unknown_bins = Counter()
    model_calls = Counter()
    total_unknown = 0
    legacy_telemetry_unknown = 0
    telemetry_delta = Counter()
    validated = 0
    filenames_exact = 0
    for path in _result_paths():
        directory = base._ordinary(path).parent
        names = frozenset(item.name for item in directory.iterdir())
        if names == EXPECTED_TASK_FILES:
            filenames_exact += 1
        envelope = parent.validate_envelope(_read_object(path))
        result = envelope["result"]
        opaque_id = result["opaque_id"]
        if (
            opaque_id not in runtime
            or runtime[opaque_id]["prediction_sha256"]
            != result["prediction_sha256"]
            or runtime[opaque_id]["model_calls"]
            != result["cost"]["model"]["requests"]
        ):
            raise RuntimeError("V2.52.92 runtime/envelope binding drifted")
        try:
            unknown = candidate._baseline_unknown_count(result["prediction"])
        except (TypeError, ValueError) as exc:
            raise RuntimeError("V2.52.92 prediction table drifted") from exc
        telemetry_unknown = (
            (result.get("telemetry") or {}).get("table") or {}
        ).get("unknown_cell_count")
        if (
            isinstance(telemetry_unknown, bool)
            or not isinstance(telemetry_unknown, int)
            or telemetry_unknown < 0
        ):
            raise RuntimeError("V2.52.92 legacy Unknown telemetry drifted")
        eligible = candidate.legacy._parent_eligible(result)
        cross[(eligible, unknown > 0)] += 1
        unknown_bins[_unknown_bin(unknown)] += 1
        model_calls[int(result["cost"]["model"]["requests"])] += 1
        total_unknown += unknown
        legacy_telemetry_unknown += telemetry_unknown
        telemetry_delta[unknown - telemetry_unknown] += 1
        validated += 1
    if set(runtime) != {
        parent.validate_envelope(_read_object(path))["result"]["opaque_id"]
        for path in _result_paths()
    }:
        raise RuntimeError("V2.52.92 task identity vector drifted")
    cross_tab = {
        "parent_ineligible_without_unknown": cross[(False, False)],
        "parent_ineligible_with_unknown": cross[(False, True)],
        "parent_eligible_without_unknown": cross[(True, False)],
        "parent_eligible_with_unknown": cross[(True, True)],
    }
    bins = {name: unknown_bins[name] for name in EXPECTED_UNKNOWN_BINS}
    calls = {str(name): model_calls[name] for name in sorted(model_calls)}
    if (
        validated != SELECTED
        or filenames_exact != SELECTED
        or cross_tab != EXPECTED_CROSS_TAB
        or bins != EXPECTED_UNKNOWN_BINS
        or calls != EXPECTED_MODEL_CALL_DISTRIBUTION
        or total_unknown != 1465
        or legacy_telemetry_unknown != 1424
        or telemetry_delta != Counter({0: 217, -1: 2, 43: 1})
    ):
        raise RuntimeError("V2.52.92 aggregate drifted")
    return {
        "frozen_task_denominator": SELECTED,
        "validated_parent_envelopes": validated,
        "runtime_prediction_rows_reconciled": SELECTED,
        "task_directory_file_sets_exact": filenames_exact,
        "logical_model_call_distribution": calls,
        "parent_unknown_cross_tab": cross_tab,
        "parent_eligible_tasks": (
            cross_tab["parent_eligible_without_unknown"]
            + cross_tab["parent_eligible_with_unknown"]
        ),
        "tasks_with_unknown": (
            cross_tab["parent_ineligible_with_unknown"]
            + cross_tab["parent_eligible_with_unknown"]
        ),
        "prepage_eligible_tasks": cross_tab["parent_eligible_with_unknown"],
        "prepage_eligibility_rate": round(
            cross_tab["parent_eligible_with_unknown"] / SELECTED, 12
        ),
        "total_unknown_cells": total_unknown,
        "unknown_cell_count_coarse_bins": bins,
        "legacy_telemetry_unknown_cells": legacy_telemetry_unknown,
        "v25289_minus_legacy_unknown_count_distribution": {
            str(key): telemetry_delta[key] for key in sorted(telemetry_delta)
        },
        "unknown_count_exact_parity_tasks": telemetry_delta[0],
        "unknown_count_semantic_difference_tasks": SELECTED - telemetry_delta[0],
        "legacy_telemetry_counts_row_key_cells": True,
        "v25290_counts_only_mutable_non_key_value_cells": True,
        "legacy_telemetry_recognizes_none_marker": False,
        "v25289_recognizes_none_marker": True,
        "legacy_telemetry_used_for_v25290_eligibility": False,
        "same_forward_page_bytes_persisted": False,
        "same_forward_page_prefix_completeness_reconstructable": False,
        "revision_prompt_chars_reconstructable": False,
        "full_v25290_eligibility_reconstructable": False,
        "supported_unknown_fill_observed": False,
        "attributable_prediction_change_observed": False,
        "prepage_eligible_is_upper_bound_not_full_eligibility": True,
    }


def _historical_conversion_risk(value: Mapping[str, Any]) -> dict[str, Any]:
    coverage = value["coverage_revision_totals"]
    effects = value["keyless_effect_totals"]
    return {
        "source_protocol": value["protocol_id"],
        "frozen_task_denominator": value["selected"],
        "valid_bundles": coverage["valid_bundles"],
        "usable_pages": effects["usable_pages"],
        "logical_revision_calls": coverage["logical_revision_calls"],
        "invalid_proposal_tasks": coverage["disposition_counts"][
            "identity_invalid_proposal"
        ],
        "no_supported_change_tasks": coverage["disposition_counts"][
            "identity_no_supported_change"
        ],
        "admitted_existing_cell_changes": coverage[
            "admitted_existing_cell_changes"
        ],
        "admitted_new_rows": coverage["admitted_new_rows"],
        "prediction_changed_tasks": coverage["prediction_changed_tasks"],
        "same_runtime_candidate_or_support_threshold_as_v25290": False,
        "transferred_as_v25290_event_rate_or_quality_effect": False,
        "interpretation": (
            "conversion_risk_prior_only_not_a_v25290_counterfactual"
        ),
    }


def _decision() -> dict[str, Any]:
    return {
        "prepage_parent_and_unknown_eligibility": "nonzero_41_of_220",
        "prepage_eligibility_is_a_natural_entry_upper_bound": True,
        "full_page_prefix_and_prompt_eligibility_established": False,
        "supported_unknown_fill_established": False,
        "attributable_prediction_change_established": False,
        "quality_or_exact_gain_established": False,
        "historical_zero_conversion_is_a_material_risk": True,
        "historical_zero_conversion_transfers_as_effect_estimate": False,
        "next_step": "fresh_disjoint_shared_prefix_protocol_design_only",
        "external_launch_before_protocol_build_and_preactivation_audit": False,
        "public_deepwidebench_220_before_external_causal_go": False,
        "reason": (
            "natural_prepage_entry_exists_but_page_support_conversion_and_utility_remain_unidentified"
        ),
    }


def _future_gate() -> dict[str, Any]:
    return {
        "fresh_disjoint_benchmark_external_population": True,
        "selection_independent_of_v24857_per_task_prediction_or_outcome": True,
        "runtime_keys": ["opaque_id", "question"],
        "control_and_candidate_share_parent_forward_and_page_bytes": True,
        "mechanism_before_evaluator": {
            "parent_and_unknown_prepage_eligible_nonzero": True,
            "complete_page_prefix_eligible_nonzero": True,
            "prompt_within_cap_eligible_nonzero": True,
            "supported_unknown_fill_nonzero": True,
            "attributable_prediction_change_nonzero": True,
            "query_and_fetch_effect_equal": True,
            "total_model_calls_at_most_three": True,
        },
        "zero_supported_fill_or_prediction_change": "strict_no_go_without_evaluator",
        "postfreeze_quality_go": {
            "candidate_exact_strictly_greater": True,
            "entity_row_item_column_composite_nonregression": True,
            "fallback_invalid_outer_failure_nonincrease": True,
        },
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
    }


def build_diagnosis(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    authority = _parent_barrier()
    observed = _scan_legacy_population()
    historical = _historical_conversion_risk(authority["historical"])
    source_hashes = {
        str(path): base.sha256(path) for path in (SOURCE, TEST)
    }
    untracked = sorted(
        str(path)
        for path in (SOURCE, TEST)
        if tracked and not base._tracked(path)
    )
    checks = {
        "git_clean_head_equals_target_main": clean and head == target,
        "source_and_test_tracked": not untracked,
        "fixed_inputs_exact": authority["fixed_inputs"]
        == {str(path): digest for path, digest in FIXED_INPUTS.items()},
        "v25291_build_audit_valid_and_design_only": authority["build"][
            "audit_valid"
        ]
        is True,
        "legacy_forward_is_frozen_label_blind_220": (
            authority["forward"]["audit_valid"] is True
            and authority["summary"]["official_evaluator_called"] is False
            and observed["frozen_task_denominator"] == SELECTED
        ),
        "legacy_result_vector_exact220_hash_bound": (
            len(_result_vector()) == SELECTED
        ),
        "all_legacy_envelopes_validate_and_match_runtime_freeze": (
            observed["validated_parent_envelopes"] == SELECTED
            and observed["runtime_prediction_rows_reconciled"] == SELECTED
        ),
        "unknown_counts_recomputed_with_v25289_semantics": (
            observed["tasks_with_unknown"] == 42
            and observed["total_unknown_cells"] == 1465
        ),
        "legacy_telemetry_semantic_difference_explained_and_not_used": (
            observed["legacy_telemetry_unknown_cells"] == 1424
            and observed["unknown_count_exact_parity_tasks"] == 217
            and observed["unknown_count_semantic_difference_tasks"] == 3
            and observed["legacy_telemetry_used_for_v25290_eligibility"]
            is False
        ),
        "prepage_eligibility_exact41_nonzero": (
            observed["prepage_eligible_tasks"] == 41
        ),
        "same_forward_page_bytes_absent_from_frozen_task_surface": (
            observed["task_directory_file_sets_exact"] == SELECTED
            and observed["same_forward_page_bytes_persisted"] is False
        ),
        "full_eligibility_supported_fill_and_prediction_change_not_inferred": (
            observed["full_v25290_eligibility_reconstructable"] is False
            and observed["supported_unknown_fill_observed"] is False
            and observed["attributable_prediction_change_observed"] is False
        ),
        "historical_conversion_zero_is_bound_but_not_transferred": (
            historical["logical_revision_calls"] == 153
            and historical["prediction_changed_tasks"] == 0
            and historical["transferred_as_v25290_event_rate_or_quality_effect"]
            is False
        ),
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "source_hashes": source_hashes,
        "fixed_inputs": authority["fixed_inputs"],
        "frozen_result_vector": {
            "count": SELECTED,
            "vector_sha256": EXPECTED_RESULT_VECTOR_SHA256,
            "path_sha256": EXPECTED_RESULT_PATH_SHA256,
            "content_sha256": EXPECTED_RESULT_CONTENT_SHA256,
            "individual_paths_or_hashes_emitted": False,
        },
        "observed_legacy_aggregate": observed,
        "historical_conversion_risk": historical,
        "decision": _decision(),
        "future_gate_requirements": _future_gate(),
        "content_policy": {
            "runtime_prediction_rows_and_task_envelopes_opened": True,
            "prediction_opened_only_to_recompute_unknown_count_and_hash_parity": True,
            "task_identity_parsed_only_for_one_to_one_reconciliation": True,
            "task_identity_prediction_or_per_task_count_persisted_or_emitted": False,
            "visible_task_files_opened": False,
            "question_query_url_page_answer_or_credential_opened": False,
            "mapping_gold_category_question_type_split_evaluator_metric_score_or_reward_opened": False,
            "historical_per_task_correctness_used_for_selection_or_runtime_routing": False,
            "aggregate_only_output": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read_for_runtime_routing": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design": not findings,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = seal.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    git = copied.get("git") or {}
    source_hashes = copied.get("source_hashes") or {}
    vector = copied.get("frozen_result_vector") or {}
    observed = copied.get("observed_legacy_aggregate") or {}
    historical = copied.get("historical_conversion_risk") or {}
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    authorization = copied.get("authorization") or {}
    policy = copied.get("content_policy") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    expected_source_hashes = {
        str(path): base.sha256(path) for path in (SOURCE, TEST)
    }
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "source_hashes",
            "fixed_inputs",
            "frozen_result_vector",
            "observed_legacy_aggregate",
            "historical_conversion_risk",
            "decision",
            "future_gate_requirements",
            "content_policy",
            "checks",
            "findings",
            "diagnosis_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read_for_runtime_routing",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or not all(isinstance(git.get(name), str) for name in ("head", "target_main"))
        or git.get("equal") is not (git.get("head") == git.get("target_main"))
        or not isinstance(git.get("clean"), bool)
        or source_hashes != expected_source_hashes
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in FIXED_INPUTS.items()}
        or vector
        != {
            "count": SELECTED,
            "vector_sha256": EXPECTED_RESULT_VECTOR_SHA256,
            "path_sha256": EXPECTED_RESULT_PATH_SHA256,
            "content_sha256": EXPECTED_RESULT_CONTENT_SHA256,
            "individual_paths_or_hashes_emitted": False,
        }
        or observed
        != {
            "frozen_task_denominator": SELECTED,
            "validated_parent_envelopes": SELECTED,
            "runtime_prediction_rows_reconciled": SELECTED,
            "task_directory_file_sets_exact": SELECTED,
            "logical_model_call_distribution": EXPECTED_MODEL_CALL_DISTRIBUTION,
            "parent_unknown_cross_tab": EXPECTED_CROSS_TAB,
            "parent_eligible_tasks": 218,
            "tasks_with_unknown": 42,
            "prepage_eligible_tasks": 41,
            "prepage_eligibility_rate": round(41 / SELECTED, 12),
            "total_unknown_cells": 1465,
            "unknown_cell_count_coarse_bins": EXPECTED_UNKNOWN_BINS,
            "legacy_telemetry_unknown_cells": 1424,
            "v25289_minus_legacy_unknown_count_distribution": {
                "-1": 2,
                "0": 217,
                "43": 1,
            },
            "unknown_count_exact_parity_tasks": 217,
            "unknown_count_semantic_difference_tasks": 3,
            "legacy_telemetry_counts_row_key_cells": True,
            "v25290_counts_only_mutable_non_key_value_cells": True,
            "legacy_telemetry_recognizes_none_marker": False,
            "v25289_recognizes_none_marker": True,
            "legacy_telemetry_used_for_v25290_eligibility": False,
            "same_forward_page_bytes_persisted": False,
            "same_forward_page_prefix_completeness_reconstructable": False,
            "revision_prompt_chars_reconstructable": False,
            "full_v25290_eligibility_reconstructable": False,
            "supported_unknown_fill_observed": False,
            "attributable_prediction_change_observed": False,
            "prepage_eligible_is_upper_bound_not_full_eligibility": True,
        }
        or historical
        != {
            "source_protocol": "v24884_mapping_recovery_fixed_budget_exact220_v1",
            "frozen_task_denominator": SELECTED,
            "valid_bundles": 160,
            "usable_pages": 956,
            "logical_revision_calls": 153,
            "invalid_proposal_tasks": 57,
            "no_supported_change_tasks": 96,
            "admitted_existing_cell_changes": 0,
            "admitted_new_rows": 0,
            "prediction_changed_tasks": 0,
            "same_runtime_candidate_or_support_threshold_as_v25290": False,
            "transferred_as_v25290_event_rate_or_quality_effect": False,
            "interpretation": "conversion_risk_prior_only_not_a_v25290_counterfactual",
        }
        or copied.get("decision") != _decision()
        or copied.get("future_gate_requirements") != _future_gate()
        or policy
        != {
            "runtime_prediction_rows_and_task_envelopes_opened": True,
            "prediction_opened_only_to_recompute_unknown_count_and_hash_parity": True,
            "task_identity_parsed_only_for_one_to_one_reconciliation": True,
            "task_identity_prediction_or_per_task_count_persisted_or_emitted": False,
            "visible_task_files_opened": False,
            "question_query_url_page_answer_or_credential_opened": False,
            "mapping_gold_category_question_type_split_evaluator_metric_score_or_reward_opened": False,
            "historical_per_task_correctness_used_for_selection_or_runtime_routing": False,
            "aggregate_only_output": True,
        }
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("diagnosis_valid") is not (not expected_findings)
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read_for_runtime_routing"
        )
        is not False
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or set(authorization)
        != {
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design",
            "external_activation_or_launch",
            "postfreeze_evaluator",
            "deepwidebench_dev64_exact220_forward_or_evaluator",
            "candidate_quality_avg_at_4_leaderboard_or_sota",
        }
        or authorization.get(
            "fresh_disjoint_shared_prefix_external_population_and_protocol_design"
        )
        is not copied.get("diagnosis_valid")
        or any(
            authorization.get(name) is not False
            for name in (
                "external_activation_or_launch",
                "postfreeze_evaluator",
                "deepwidebench_dev64_exact220_forward_or_evaluator",
                "candidate_quality_avg_at_4_leaderboard_or_sota",
            )
        )
        or signature != seal.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.92 eligibility diagnosis drifted")
    encoded = json.dumps(copied, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) is not None:
        raise ValueError("V2.52.92 diagnosis emitted a task identity")
    return copied


def main() -> int:
    value = build_diagnosis()
    if not value["diagnosis_valid"]:
        raise SystemExit(
            "V2.52.92 diagnosis failed: " + ", ".join(value["findings"])
        )
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise SystemExit("V2.52.92 diagnosis output already exists")
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "prepage_eligible_tasks": value["observed_legacy_aggregate"][
                    "prepage_eligible_tasks"
                ],
                "full_eligibility_reconstructable": value[
                    "observed_legacy_aggregate"
                ]["full_v25290_eligibility_reconstructable"],
                "findings": value["findings"],
                "diagnosis_payload_sha256": value[
                    "diagnosis_payload_sha256"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
