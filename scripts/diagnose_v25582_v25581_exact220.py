#!/usr/bin/env python3
"""Post-freeze aggregate diagnosis of the V2.55.81 exact-220 rollout.

The script reads already-frozen forward receipts and evaluator outputs only
after the prediction freeze and exactly-once evaluation.  Per-task identities,
visible questions, predictions, evaluator errors, and scores exist only in
memory for alignment and aggregation.  The published artifact contains no
per-task material and cannot authorize feedback into this consumed rollout.

No model, search, fetch, network, mapping, truth, or evaluator capability is
imported or called.  Entropy/information gain remains shadow-only and receives
zero signed credit.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
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

from deepwide_agent import v24921_target_value_coverage_projector as coverage  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25581_canonical_totality_exact220_contract as contract  # noqa: E402


DATE = "20260818"
ROLE = "v25582_v25581_exact220_postfreeze_aggregate_diagnosis"
SOURCE = Path("scripts/diagnose_v25582_v25581_exact220.py")
TEST = Path("tests/test_diagnose_v25582_v25581_exact220.py")
OUTPUT = Path(f"results/v25582_v25581_exact220_diagnosis_v1_{DATE}.json")
IMPLEMENTATION_COMMIT = "61908686f88b78122aa05cbce9dda83285dd17be"

V25581_ROOT = contract.OUTPUT_ROOT
V25573_ROOT = Path("outputs/v25573_totality_exact220_v1_20260814")
V25406_ROOT = Path("outputs/v25406_grounded_membership_exact220_v1_20260813")
V25379_ROOT = Path("outputs/v25379_changed_safe_exact220_v1_20260813")

V25581_RESULT = contract.RESULT
V25581_POSTAUDIT = contract.POSTAUDIT
V25573_RESULT = Path("results/v25573_totality_exact220_result_v1_20260814.json")
V25573_POSTAUDIT = Path(
    "results/v25573_totality_exact220_postresult_audit_v1_20260814.json"
)
V25406_RESULT = Path(
    "results/v25406_grounded_membership_exact220_result_v1_20260813.json"
)
V25406_POSTAUDIT = Path(
    "results/v25406_grounded_membership_exact220_postresult_audit_v1_20260813.json"
)
V25379_RESULT = Path(
    "results/v25379_changed_safe_exact220_result_v1_20260813.json"
)
V25379_POSTAUDIT = Path(
    "results/v25381_changed_safe_exact220_postresult_audit_v1_20260813.json"
)
V24857_RESULT = Path(
    "results/v24857_pacing_aware_exact220_result_v1_20260808.json"
)
V24857_POSTAUDIT = Path(
    "results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"
)

FIXED_SHA256 = {
    V25581_RESULT: "91adc409db05298fc0dd1fdbca8c73c31ae06e7e33927c649755a2bcdd395987",
    V25581_POSTAUDIT: "9e1bbd5e14f0de07a4427c15938072668a272b487dfe2e026c3096c6f305d696",
    contract.FORWARD_RESULT: "277f07830baa5604f5f0d0b35177753cfaaa4a2c6a8eee45cf6d604de61d4aab",
    V25581_ROOT / "frozen_task_results.jsonl": "249fd9fb229e998f28a5e08bc773d75cde6c40120df6f933db074de9cdb5d1bf",
    V25581_ROOT / "runtime_predictions.jsonl": "e79f0d7bb2551ef6b97606d7634492c4c267aed6ee1480ef62d1901a3e46ed4e",
    V25581_ROOT / "run_summary.json": "5d25c3264ec57f471fef1dfbee64f6e79ba8c148e074e51c2828b7367bc4ed78",
    V25581_ROOT / "evaluator/conservative_summary.json": "3b75bc100b5403d585b525d4c618a588a29179cb5ad4a08deb913bfcb7591c21",
    V25573_RESULT: "eb20492548f73234947bbff8c8ab08a3e9ba7903741e39029e5aea6d039e26ef",
    V25573_POSTAUDIT: "a1ed547e02b849dd2999019d5ae998c06dc49df5682bbbaf71569c0a4f495b15",
    V25573_ROOT / "frozen_task_results.jsonl": "550438d284b2290de66df6fde2fbb924145d92392b6c47df9a28ab60bb37d7fa",
    V25573_ROOT / "evaluator/conservative_summary.json": "3327d063b33ba1959df43b1c26c33c928f2e86f105e3b7ec9c89ef8ee923b68a",
    V25406_RESULT: "2f986c1307e97d5c65bcd7eb68e46f7660d383f708f1a01ce0bc11fb89b9f0e1",
    V25406_POSTAUDIT: "833ea45d69f3c664003ce9e67708af96e842c087889fb53342fe64f2c9636cf9",
    V25406_ROOT / "frozen_task_results.jsonl": "b40436dc45ec801adb8569ef890715eff1a0054642d98d482e5793dad11bfd75",
    V25406_ROOT / "evaluator/conservative_summary.json": "aef52158373540ca0fa9422d287f7a7fcabc52a5d634fd7f363148e72ec820ac",
    V25379_RESULT: "4669c0d725699a5e57b205a23a74c151a5f08980aa69629d57437795fd0b8338",
    V25379_POSTAUDIT: "ca776c6b65f1eb1f5a552fd745aa920db5469e1fb78b0c860b16cab1f33c1869",
    V25379_ROOT / "frozen_task_results.jsonl": "f080bf3283319c6633ba58bb59ebd9bd8b14998b9e2624c0c218574653c7564d",
    V25379_ROOT / "evaluator/conservative_summary.json": "d5185ea9bda82940a1f9954dbe47f2e8b54e670b126779de4f300a07723ba0aa",
    V24857_RESULT: "a9e51c5c479a79e46f74574dac905bc607032be501b8a21a696106172f59f1d9",
    V24857_POSTAUDIT: "cf49f952533656d805ca13e807689ea1cd07215553b3f3f9b2dbbf11c115ca20",
    Path("src/deepwide_agent/v25581_canonical_totality_exact220_contract.py"): "eb55a3e3984aa693cd742fbe1dc90ac2eba7b819068ea3c738160810fba87d9c",
    Path("src/deepwide_agent/v25117_grounded_target_record_plan.py"): "f159fb853e73444494c84b9385b0997366e466be591138356f3ef3f5ce436a5d",
    Path("src/deepwide_agent/v25118_target_record_frontier_selection.py"): "a4fd91cb9c6beaa2e3dc6177addba14eb306e3c16086d45a89d7097a6ed612d9",
    Path("src/deepwide_agent/v25370_shared_synthesis_changed_safe_runtime.py"): "cc173d39d2fc85098ac87297c4247fb93d4d954c00fefb3aaee056c75e03ce2e",
    Path("src/deepwide_agent/v25389_hybrid_record_fallback_runtime.py"): "cb881bc40332f2e8727b9437fbd1ea158dd6ce7e41dbe3d1a3e3a4a915cc92d8",
    Path("src/deepwide_agent/v25395_visible_membership_synthesis_runtime.py"): "b875c992b0c238281490b459cc4dad6baac7165c48a52f8b19eb4a0cfbfa0a19",
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"): "4579affb4bbff7c84da5404bb233b41bd7e2a259ad49c635f756b262e7d2369d",
}

SHARED_ROLE = "v25370_content_free_shared_synthesis_changed_safe_runtime_receipt"
FRONTIER_ROLE = "v25118_content_free_target_record_frontier_selection_receipt"
HYBRID_ROLE = "v25389_content_free_hybrid_record_fallback_receipt"
MEMBERSHIP_ROLE = "v25395_content_free_visible_membership_synthesis_receipt"
METRIC_NAMES = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")

_EN_EXPLICIT_ROW = re.compile(
    r"(?:return|include|find)\s+(?:the\s+)?row\s+for\s+([^.;\n]+)",
    re.I,
)
_ZH_EXPLICIT_ROW = re.compile(
    r"(?:返回|包括|查找)(?:关于|对应)?\s*([^。；\n]{2,160})(?:的)?(?:行|记录)",
    re.I,
)


def _read_json(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=tracked).read_text()
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.82 expected a JSON object")
    return value


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    values = [
        json.loads(line)
        for line in contract.ordinary(ROOT, relative, tracked=True)
        .read_text()
        .splitlines()
        if line.strip()
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.55.82 expected JSONL objects")
    return values


def _rows(root: Path) -> dict[str, dict[str, Any]]:
    values = _read_jsonl(root / "frozen_task_results.jsonl")
    output = {str(value["opaque_id"]): value for value in values}
    if len(values) != 220 or len(output) != 220:
        raise RuntimeError("V2.55.82 task-row denominator drifted")
    return output


def _summary(root: Path) -> dict[str, dict[str, Any]]:
    value = _read_json(root / "evaluator/conservative_summary.json")
    rows = value.get("per_task")
    if not isinstance(rows, list) or len(rows) != 220:
        raise RuntimeError("V2.55.82 evaluator denominator drifted")
    output = {str(row["opaque_id"]): row for row in rows}
    if len(output) != 220:
        raise RuntimeError("V2.55.82 evaluator identity drifted")
    return output


def _receipt(value: Mapping[str, Any], role: str) -> dict[str, Any]:
    found: dict[str, dict[str, Any]] = {}

    def walk(item: Any) -> None:
        if isinstance(item, Mapping):
            if item.get("role") == role:
                copied = copy.deepcopy(dict(item))
                key = json.dumps(
                    copied, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                found[key] = copied
            for child in item.values():
                walk(child)
        elif isinstance(item, list):
            for child in item:
                walk(child)

    walk(value)
    if len(found) != 1:
        raise RuntimeError(f"V2.55.82 expected one unique {role} receipt")
    return next(iter(found.values()))


def _exact(row: Mapping[str, Any]) -> bool:
    return bool(row["evaluator_valid"] and float(row["metrics"]["score"]) == 1.0)


def _metric_block(
    identities: list[str], summary: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    rows = [summary[identity] for identity in identities]
    output: dict[str, Any] = {
        "fixed_denominator": len(rows),
        "evaluator_valid": sum(bool(row["evaluator_valid"]) for row in rows),
        "whole_table_successes": sum(_exact(row) for row in rows),
    }
    for name in METRIC_NAMES:
        output[name] = (
            sum(float(row["metrics"][name]) for row in rows) / len(rows)
            if rows
            else None
        )
    output["quality_composite"] = (
        sum(float(output[name]) for name in METRIC_NAMES) / 4.0 if rows else None
    )
    return output


def _quality_bands(
    identities: list[str], summary: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    rows = [summary[identity] for identity in identities if summary[identity]["evaluator_valid"]]
    output: dict[str, Any] = {"evaluator_valid_denominator": len(rows)}
    for name in METRIC_NAMES:
        values = [float(row["metrics"][name]) for row in rows]
        output[name] = {
            "equal_zero": sum(value == 0.0 for value in values),
            "below_0_2": sum(value < 0.2 for value in values),
            "at_least_0_5": sum(value >= 0.5 for value in values),
        }
    return output


def _artifact_barrier() -> None:
    if IMPLEMENTATION_COMMIT not in contract.git(ROOT, "rev-list", "HEAD").splitlines():
        raise RuntimeError("V2.55.82 implementation commit is not in history")
    drifted = [
        str(path)
        for path, digest in FIXED_SHA256.items()
        if contract.sha256(ROOT / path) != digest
    ]
    if drifted:
        raise RuntimeError(f"V2.55.82 fixed input hash drifted: {drifted}")
    for result_path, audit_path in (
        (V25581_RESULT, V25581_POSTAUDIT),
        (V25573_RESULT, V25573_POSTAUDIT),
        (V25406_RESULT, V25406_POSTAUDIT),
        (V25379_RESULT, V25379_POSTAUDIT),
        (V24857_RESULT, V24857_POSTAUDIT),
    ):
        result = _read_json(result_path)
        audit = _read_json(audit_path)
        if (
            result.get("status") != "exact220_single_rollout_complete"
            or result.get("selected") != 220
            or result.get("claims", {}).get("sota") is not False
            or audit.get("audit_valid") is not True
            or audit.get("findings") != []
        ):
            raise RuntimeError("V2.55.82 frozen result barrier drifted")


def _evaluator_error_taxonomy(
    identities: list[str], summary: Mapping[str, Mapping[str, Any]]
) -> dict[str, int]:
    output: Counter[str] = Counter()
    for identity in identities:
        row = summary[identity]
        if row["evaluator_valid"]:
            continue
        error = str(row.get("evaluator_error") or "")
        if "internal error" in error:
            output["official_internal_error"] += 1
        elif "out-of-range metrics" in error:
            output["official_out_of_range_metrics"] += 1
        else:
            output["other_terminal_error"] += 1
    return dict(sorted(output.items()))


def _build_unsigned(*, now: int) -> dict[str, Any]:
    _artifact_barrier()
    tasks = contract.task_vector(ROOT)
    identities = [str(task["opaque_id"]) for task in tasks]
    expected = set(identities)
    rows = {
        "v25379": _rows(V25379_ROOT),
        "v25406": _rows(V25406_ROOT),
        "v25573": _rows(V25573_ROOT),
        "v25581": _rows(V25581_ROOT),
    }
    summaries = {
        "v25379": _summary(V25379_ROOT),
        "v25406": _summary(V25406_ROOT),
        "v25573": _summary(V25573_ROOT),
        "v25581": _summary(V25581_ROOT),
    }
    if (
        len(tasks) != 220
        or len(expected) != 220
        or any(set(value) != expected for value in rows.values())
        or any(set(value) != expected for value in summaries.values())
    ):
        raise RuntimeError("V2.55.82 cross-version exact-220 alignment drifted")

    current_rows = rows["v25581"]
    current_summary = summaries["v25581"]
    shared = {
        identity: _receipt(current_rows[identity]["runtime_result"], SHARED_ROLE)
        for identity in identities
    }
    frontier = {
        identity: _receipt(current_rows[identity]["runtime_result"], FRONTIER_ROLE)
        for identity in identities
    }
    hybrid = {
        identity: _receipt(current_rows[identity]["runtime_result"], HYBRID_ROLE)
        for identity in identities
    }
    membership_receipts = {
        identity: _receipt(
            current_rows[identity]["runtime_result"], MEMBERSHIP_ROLE
        )
        for identity in identities
    }

    fallback = [
        identity
        for identity in identities
        if current_rows[identity]["prediction_kind"] == "fallback"
    ]
    generated = [
        identity
        for identity in identities
        if current_rows[identity]["prediction_kind"] == "model_generated"
    ]
    failure_classes: Counter[str] = Counter()
    for identity in fallback:
        failures = shared[identity]["failure_types"]
        plan_failure = failures["plan"]
        synthesis_failure = failures["synthesis"]
        if plan_failure is None and synthesis_failure == "ValueError":
            failure_classes["local_unrecoverable_table_normalization"] += 1
        elif plan_failure is None and synthesis_failure == "ModelRequestError":
            failure_classes["synthesis_model_request_error"] += 1
        elif (
            plan_failure == "ModelRequestError"
            and synthesis_failure == "ModelRequestError"
        ):
            failure_classes["plan_and_synthesis_model_request_error"] += 1
        else:
            failure_classes["other"] += 1

    grammar_sources: Counter[str] = Counter()
    grammar_sizes: Counter[str] = Counter()
    explicit_vector_sizes: Counter[str] = Counter()
    cue_counts: Counter[str] = Counter()
    membership_ids: list[str] = []
    for task in tasks:
        question = str(task["question"])
        values, source = membership.visible_membership(question)
        grammar_sources[source] += 1
        grammar_sizes[f"{source}:{len(values)}"] += 1
        explicit_vector_sizes[str(len(coverage.visible_row_targets(question)))] += 1
        cue_counts["english_return_include_find_row_for"] += int(
            _EN_EXPLICIT_ROW.search(question) is not None
        )
        cue_counts["chinese_return_include_find_row_record"] += int(
            _ZH_EXPLICIT_ROW.search(question) is not None
        )
        if source == "explicit_row_phrase":
            membership_ids.append(str(task["opaque_id"]))

    membership_rows = [membership_receipts[identity] for identity in membership_ids]
    previous_failures = [
        identity
        for identity in identities
        if not rows["v25573"][identity]["runtime_completed"]
    ]
    previous_failure_set = set(previous_failures)
    remaining = [identity for identity in identities if identity not in previous_failure_set]
    exact_transitions = Counter(
        (
            "1" if _exact(summaries["v25573"][identity]) else "0"
        )
        + ("1" if _exact(current_summary[identity]) else "0")
        for identity in identities
    )

    evaluator_taxonomy = _evaluator_error_taxonomy(identities, current_summary)
    current_result = _read_json(V25581_RESULT)["metrics"]["all_220"]
    previous_result = _read_json(V25573_RESULT)["metrics"]["all_220"]
    peak_result = _read_json(V24857_RESULT)["metrics"]["all_220"]

    fallback_diagnosis = {
        "fallback_tasks": len(fallback),
        "all_completed_search_and_fetch": all(
            current_rows[identity]["actual_effect_snapshot"]["logical_queries"] == 4
            and current_rows[identity]["actual_effect_snapshot"]["fetch_requests"] == 10
            for identity in fallback
        ),
        "query_fetch_model_histogram": dict(
            sorted(
                Counter(
                    "query{}_fetch{}_model{}".format(
                        current_rows[identity]["actual_effect_snapshot"][
                            "logical_queries"
                        ],
                        current_rows[identity]["actual_effect_snapshot"][
                            "fetch_requests"
                        ],
                        current_rows[identity]["actual_effect_snapshot"][
                            "model_logical_requests"
                        ],
                    )
                    for identity in fallback
                ).items()
            )
        ),
        "provider_success_histogram": dict(
            sorted(
                Counter(
                    str(
                        current_rows[identity]["actual_effect_snapshot"][
                            "model_provider_successes"
                        ]
                    )
                    for identity in fallback
                ).items()
            )
        ),
        "grounded_plan_model_success_tasks": sum(
            bool(shared[identity]["grounded_plan_model_call_success"])
            for identity in fallback
        ),
        "base_synthesis_success_tasks": sum(
            bool(shared[identity]["base_synthesis_model_success"])
            for identity in fallback
        ),
        "base_normalizer_status_histogram": dict(
            sorted(
                Counter(
                    str(shared[identity]["base_normalizer_status"])
                    for identity in fallback
                ).items()
            )
        ),
        "failure_taxonomy": dict(sorted(failure_classes.items())),
        "joint_envelope_exact_tasks": sum(
            bool(hybrid[identity]["joint_envelope_exact"])
            for identity in fallback
        ),
        "joint_table_normalizable_tasks": sum(
            bool(hybrid[identity]["joint_table_normalizable"])
            for identity in fallback
        ),
        "search_nonexecution_is_supported_as_root_cause": False,
    }

    quality_diagnosis = {
        "published_all220": copy.deepcopy(current_result),
        "model_generated_fixed_denominator": _metric_block(
            generated, current_summary
        ),
        "evaluator_valid_quality_bands": _quality_bands(
            identities, current_summary
        ),
        "evaluator_invalid_or_not_run": len(identities)
        - sum(current_summary[identity]["evaluator_valid"] for identity in identities),
        "evaluator_terminal_error_taxonomy": evaluator_taxonomy,
        "invalid_rows_remain_failure_as_zero_without_revaluation": True,
        "dominant_observed_quality_bottleneck": "row_and_value_completeness",
    }

    record_funnel = {
        "grounded_target_plan_strategy_tasks": sum(
            bool(shared[identity]["grounded_plan_strategy_applied"])
            for identity in identities
        ),
        "target_record_frontier_eligible_tasks": sum(
            bool(frontier[identity]["strategy_eligible"])
            for identity in identities
        ),
        "target_record_frontier_engaged_tasks": sum(
            bool(frontier[identity]["mechanism_engaged"])
            for identity in identities
        ),
        "grounded_record_source_tasks": sum(
            hybrid[identity]["record_source"] == "grounded"
            for identity in identities
        ),
        "selected_grounded_raw_records": sum(
            int(hybrid[identity]["grounded_raw_record_count"])
            for identity in identities
        ),
        "joint_raw_records": sum(
            int(hybrid[identity]["joint_raw_record_count"])
            for identity in identities
        ),
        "verified_records": sum(
            int(hybrid[identity]["verified_record_count"])
            for identity in identities
        ),
        "verified_fields": sum(
            int(hybrid[identity]["verified_field_count"])
            for identity in identities
        ),
        "missing_base_row_rejected_fields": sum(
            int(hybrid[identity]["missing_row_rejected_field_count"])
            for identity in identities
        ),
        "changed_safe_coordinates": sum(
            int(hybrid[identity]["changed_safe_coordinate_count"])
            for identity in identities
        ),
        "attributable_prediction_change_tasks": sum(
            bool(hybrid[identity]["attributable_prediction_change"])
            for identity in identities
        ),
        "record_correction_identified_as_quality_treatment": False,
    }

    membership_regression = {
        "grammar_source_histogram": dict(sorted(grammar_sources.items())),
        "grammar_source_and_size_histogram": dict(sorted(grammar_sizes.items())),
        "coverage_parser_vector_size_histogram": dict(
            sorted(explicit_vector_sizes.items())
        ),
        "fallback_cue_histogram": dict(sorted(cue_counts.items())),
        "constraint_applied_tasks": len(membership_ids),
        "constraint_source": "explicit_row_phrase",
        "visible_member_count_histogram": dict(
            sorted(
                Counter(
                    str(row["visible_member_count"]) for row in membership_rows
                ).items()
            )
        ),
        "base_table_row_count_histogram": dict(
            sorted(
                Counter(
                    str(row["base_table_row_count"]) for row in membership_rows
                ).items()
            )
        ),
        "base_visible_membership_exact_tasks": sum(
            bool(row["base_visible_membership_exact"])
            for row in membership_rows
        ),
        "same_fixed_grammar_subset_metrics": {
            version: _metric_block(membership_ids, summaries[version])
            for version in ("v25379", "v25406", "v25573", "v25581")
        },
        "implementation_semantic_finding": "coverage_only_explicit_row_fallback_is_promoted_to_exact_closed_set_membership",
        "cold_cross_version_metrics_are_regression_signal_not_causal_effect": True,
    }

    cross_version = {
        "published_all220_metrics": {
            "v24857_project_peak": copy.deepcopy(peak_result),
            "v25573_predecessor": copy.deepcopy(previous_result),
            "v25581_current": copy.deepcopy(current_result),
        },
        "v25573_outer_failure_tasks": len(previous_failures),
        "same_tasks_v25581_model_generated_canonical_handoff": sum(
            current_rows[identity]["prediction_kind"] == "model_generated"
            and current_rows[identity].get("canonical_column_handoff") is True
            for identity in previous_failures
        ),
        "same_tasks_v25581_fallback": sum(
            current_rows[identity]["prediction_kind"] == "fallback"
            for identity in previous_failures
        ),
        "same_tasks_metrics_v25573": _metric_block(
            previous_failures, summaries["v25573"]
        ),
        "same_tasks_metrics_v25581": _metric_block(
            previous_failures, current_summary
        ),
        "remaining_209_metrics_v25573": _metric_block(
            remaining, summaries["v25573"]
        ),
        "remaining_209_metrics_v25581": _metric_block(
            remaining, current_summary
        ),
        "exact_transition_order": ["v25573", "v25581"],
        "exact_transition_histogram": dict(sorted(exact_transitions.items())),
        "independent_cold_rollouts_do_not_identify_wrapper_causality": True,
    }

    checks = {
        "fixed_source_and_artifact_hashes_exact": True,
        "all_cross_version_vectors_align_exact220": True,
        "fallback_count_exact10": len(fallback) == 10,
        "fallback_search_fetch_model_effects_complete": fallback_diagnosis[
            "all_completed_search_and_fetch"
        ]
        and fallback_diagnosis["query_fetch_model_histogram"]
        == {"query4_fetch10_model3": 10},
        "fallback_taxonomy_exact": failure_classes
        == {
            "local_unrecoverable_table_normalization": 6,
            "plan_and_synthesis_model_request_error": 1,
            "synthesis_model_request_error": 3,
        },
        "fallback_grounded_plan_success_and_base_synthesis_failure_exact": (
            fallback_diagnosis["grounded_plan_model_success_tasks"] == 10
            and fallback_diagnosis["base_synthesis_success_tasks"] == 0
            and fallback_diagnosis["base_normalizer_status_histogram"]
            == {"unrecoverable": 10}
            and fallback_diagnosis["provider_success_histogram"]
            == {"1": 1, "2": 3, "3": 6}
        ),
        "evaluator_invalid_taxonomy_exact": evaluator_taxonomy
        == {
            "official_internal_error": 4,
            "official_out_of_range_metrics": 1,
        },
        "quality_bands_exact": quality_diagnosis[
            "evaluator_valid_quality_bands"
        ]["f1_by_row"]
        == {"equal_zero": 125, "below_0_2": 147, "at_least_0_5": 41},
        "record_funnel_exact_and_zero_treatment": record_funnel
        == {
            "grounded_target_plan_strategy_tasks": 63,
            "target_record_frontier_eligible_tasks": 10,
            "target_record_frontier_engaged_tasks": 9,
            "grounded_record_source_tasks": 8,
            "selected_grounded_raw_records": 12,
            "joint_raw_records": 0,
            "verified_records": 3,
            "verified_fields": 3,
            "missing_base_row_rejected_fields": 3,
            "changed_safe_coordinates": 0,
            "attributable_prediction_change_tasks": 0,
            "record_correction_identified_as_quality_treatment": False,
        },
        "membership_grammar_exact11_singleton_chinese_fallback": (
            grammar_sources == {"explicit_row_phrase": 11, "none": 209}
            and grammar_sizes
            == {"explicit_row_phrase:1": 11, "none:0": 209}
            and cue_counts
            == {
                "chinese_return_include_find_row_record": 11,
                "english_return_include_find_row_for": 0,
            }
        ),
        "membership_active_subset_collapses_after_v25379": (
            len(membership_ids) == 11
            and membership_regression["base_table_row_count_histogram"]
            == {"0": 2, "1": 9}
            and membership_regression["same_fixed_grammar_subset_metrics"][
                "v25379"
            ]["entity_acc"]
            == 0.8181818181818182
            and all(
                membership_regression["same_fixed_grammar_subset_metrics"][
                    version
                ][name]
                == 0.0
                for version in ("v25406", "v25573", "v25581")
                for name in METRIC_NAMES
            )
        ),
        "v25573_failure_recovery_exact10_plus1": (
            len(previous_failures) == 11
            and cross_version[
                "same_tasks_v25581_model_generated_canonical_handoff"
            ]
            == 10
            and cross_version["same_tasks_v25581_fallback"] == 1
            and cross_version["same_tasks_metrics_v25581"][
                "whole_table_successes"
            ]
            == 1
        ),
        "exact_transition_is_four_stable_plus_one_new": exact_transitions
        == {"00": 215, "01": 1, "11": 4},
        "entropy_or_information_gain_positive_signed_credit_zero": (
            _read_json(contract.FORWARD_RESULT)["positive_signed_credit_count"]
            == 0
            and all(
                shared[identity]["positive_signed_credit_count"] == 0
                and hybrid[identity]["positive_signed_credit_count"] == 0
                for identity in identities
            )
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    return {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(now),
        "fixed_sha256": {
            str(path): digest
            for path, digest in sorted(FIXED_SHA256.items(), key=lambda item: str(item[0]))
        },
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "fallback_diagnosis": fallback_diagnosis,
        "quality_diagnosis": quality_diagnosis,
        "record_correction_funnel": record_funnel,
        "visible_membership_regression": membership_regression,
        "cross_version_descriptive_not_causal": cross_version,
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": valid,
        "decision": {
            "v25581_exact220_quality": "no_go_below_project_peak",
            "primary_bottleneck": "row_and_value_completeness_not_search_nonexecution",
            "candidate_designs_for_fresh_task_disjoint_gate": [
                "same_response_zero_extra_effect_robust_table_recovery",
                "provenance_bound_record_to_table_completion",
                "declarative_only_closed_set_membership_contract",
            ],
            "verified_record_may_not_create_a_row_without_independent_membership_provenance": True,
            "coverage_cue_may_not_be_promoted_to_closed_set_membership": True,
            "same_response_recovery_must_be_deterministic_and_fail_closed": True,
            "fresh_disjoint_mechanism_gate_before_postfreeze_quality_gate": True,
            "historical_per_task_outcome_runtime_routing": False,
            "deepwidebench_retry_resume_backfill_or_selective_rerun": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        },
        "postfreeze_offline_analysis_only": True,
        "contains_task_identity_question_prediction_answer_evaluator_message_or_per_task_correctness": False,
        "external_network_model_provider_search_fetch_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_task_disjoint_external_gate_design": valid,
            "local_synthetic_replay": valid,
            "external_forward": False,
            "postfreeze_quality_evaluator": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    unsigned = _build_unsigned(now=int(time.time()) if now is None else int(now))
    value = copy.deepcopy(unsigned)
    value["diagnosis_payload_sha256"] = contract.payload_sha256(unsigned)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    timestamp = copied.get("created_at_unix")
    if not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError("V2.55.82 diagnosis timestamp drifted")
    seal = copied.pop("diagnosis_payload_sha256", None)
    expected = _build_unsigned(now=timestamp)
    if copied != expected or seal != contract.payload_sha256(expected):
        raise ValueError("V2.55.82 diagnosis drifted")
    copied["diagnosis_payload_sha256"] = seal
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
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
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.validate_only:
        value = validate_diagnosis(_read_json(OUTPUT, tracked=False))
    else:
        value = build_diagnosis()
        _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "fallback_tasks": value["fallback_diagnosis"]["fallback_tasks"],
                "membership_regression_tasks": value[
                    "visible_membership_regression"
                ]["constraint_applied_tasks"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
