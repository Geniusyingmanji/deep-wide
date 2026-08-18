#!/usr/bin/env python3
"""Post-freeze aggregate diagnosis of V2.55.73 exact-220.

This script runs only after the V2.55.73 prediction freeze, pushed forward
audit, exactly-once official evaluation, and pushed post-result audit.  It
compares three already-frozen public exact-220 rollouts descriptively and
replays the real V2.53.95 task-local verifier over the fixed visible task
vector.  The replay has no model, search, fetch, network, evaluator, mapping,
or answer capability.

Per-task identifiers, questions, predictions, evaluator messages, scores, and
correctness are used only in memory to align frozen artifacts.  The published
artifact contains population aggregates only.  No outcome-derived route is
authorized; the diagnosed repair is the general canonical-column equality
contract already used by the quote verifier itself.
"""

from __future__ import annotations

import argparse
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

from deepwide_agent import v25065_quote_verified_record_binding as quote  # noqa: E402
from deepwide_agent import v25360_quote_coordinate_partial_field_record as verifier  # noqa: E402
from deepwide_agent import v25375_schema_total_changed_safe_runtime as schema  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25573_totality_exact220_contract as contract  # noqa: E402


DATE = "20260818"
ROLE = "v25574_v25573_exact220_postfreeze_aggregate_diagnosis"
SOURCE = Path("scripts/diagnose_v25574_v25573_exact220.py")
TEST = Path("tests/test_diagnose_v25574_v25573_exact220.py")
OUTPUT = Path(f"results/v25574_v25573_exact220_diagnosis_v1_{DATE}.json")

V25573_ROOT = contract.OUTPUT_ROOT
V25568_ROOT = Path("outputs/v25568_constraint_exact220_v1_20260814")
V25406_ROOT = Path("outputs/v25406_grounded_membership_exact220_v1_20260813")
V25379_ROOT = Path("outputs/v25379_changed_safe_exact220_v1_20260813")

V25573_RESULT = contract.RESULT
V25573_POSTAUDIT = contract.POSTAUDIT
V25568_RESULT = Path("results/v25568_constraint_exact220_result_v1_20260814.json")
V25568_POSTAUDIT = Path(
    "results/v25568_constraint_exact220_postresult_audit_v1_20260814.json"
)
V24857_RESULT = Path(
    "results/v24857_pacing_aware_exact220_result_v1_20260808.json"
)
V24857_POSTAUDIT = Path(
    "results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"
)
V25406_RESULT = Path(
    "results/v25406_grounded_membership_exact220_result_v1_20260813.json"
)
V25406_POSTAUDIT = Path(
    "results/v25406_grounded_membership_exact220_postresult_audit_v1_20260813.json"
)

FIXED_SHA256 = {
    V25573_RESULT: "eb20492548f73234947bbff8c8ab08a3e9ba7903741e39029e5aea6d039e26ef",
    V25573_POSTAUDIT: "a1ed547e02b849dd2999019d5ae998c06dc49df5682bbbaf71569c0a4f495b15",
    contract.FORWARD_RESULT: "bb83c6431490d28fa34419e711c031385c52095b02b684bfc845f8edde1218f0",
    V25573_ROOT / "frozen_task_results.jsonl": "550438d284b2290de66df6fde2fbb924145d92392b6c47df9a28ab60bb37d7fa",
    V25573_ROOT / "runtime_predictions.jsonl": "425d6dd8f5813d2c5b72a7950f59f0e66ca507740d48141a3f5758da0b3bc3ab",
    V25573_ROOT / "evaluator/conservative_summary.json": "3327d063b33ba1959df43b1c26c33c928f2e86f105e3b7ec9c89ef8ee923b68a",
    V25568_RESULT: "ddd20f25bd0137d1897f586157c51fc5f69b0c8f79ecbde588093f573a2657e6",
    V25568_POSTAUDIT: "00676537bffdf3a165ce737e3774fb8032acb8c2b0bec0414e708e674688927e",
    V25568_ROOT / "frozen_task_results.jsonl": "a45107f3dea7a723a474a3ea114d82df0bfb067180588cfbc2be9feb43eaa4e5",
    V25568_ROOT / "runtime_predictions.jsonl": "d8f77c683102d386ced39ce1c47a0bc7dd4841753f410eaf9cb1b7ffac254497",
    V25568_ROOT / "evaluator/conservative_summary.json": "ce22dc177bada5959febd182bcbe6156a877790d26c454a7f77a027a7f625d8f",
    V24857_RESULT: "a9e51c5c479a79e46f74574dac905bc607032be501b8a21a696106172f59f1d9",
    V24857_POSTAUDIT: "cf49f952533656d805ca13e807689ea1cd07215553b3f3f9b2dbbf11c115ca20",
    V25406_RESULT: "2f986c1307e97d5c65bcd7eb68e46f7660d383f708f1a01ce0bc11fb89b9f0e1",
    V25406_POSTAUDIT: "833ea45d69f3c664003ce9e67708af96e842c087889fb53342fe64f2c9636cf9",
    V25406_ROOT / "frozen_task_results.jsonl": "b40436dc45ec801adb8569ef890715eff1a0054642d98d482e5793dad11bfd75",
    V25379_ROOT / "frozen_task_results.jsonl": "f080bf3283319c6633ba58bb59ebd9bd8b14998b9e2624c0c218574653c7564d",
    Path("src/deepwide_agent/v25395_visible_membership_synthesis_runtime.py"): "b875c992b0c238281490b459cc4dad6baac7165c48a52f8b19eb4a0cfbfa0a19",
    Path("src/deepwide_agent/v25065_quote_verified_record_binding.py"): "256784b3d410cf399c43c9d96ce71727559e82834b78d944c0cf4d26bbe12e75",
    Path("src/deepwide_agent/v25370_shared_synthesis_changed_safe_runtime.py"): "cc173d39d2fc85098ac87297c4247fb93d4d954c00fefb3aaee056c75e03ce2e",
}


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=True).read_text())
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.74 expected a JSON object")
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
        raise RuntimeError("V2.55.74 expected JSONL objects")
    return values


def _summary(root: Path) -> dict[str, dict[str, Any]]:
    value = _read_json(root / "evaluator/conservative_summary.json")
    rows = value.get("per_task")
    if not isinstance(rows, list) or len(rows) != 220:
        raise RuntimeError("V2.55.74 conservative summary drifted")
    output = {str(row["opaque_id"]): row for row in rows}
    if len(output) != 220:
        raise RuntimeError("V2.55.74 summary identity drifted")
    return output


def _rows(root: Path) -> dict[str, dict[str, Any]]:
    values = _read_jsonl(root / "frozen_task_results.jsonl")
    output = {str(row["opaque_id"]): row for row in values}
    if len(values) != 220 or len(output) != 220:
        raise RuntimeError("V2.55.74 task row denominator drifted")
    return output


def _predictions(root: Path) -> dict[str, dict[str, Any]]:
    values = _read_jsonl(root / "runtime_predictions.jsonl")
    output = {str(row["opaque_id"]): row for row in values}
    if len(values) != 220 or len(output) != 220:
        raise RuntimeError("V2.55.74 prediction denominator drifted")
    return output


def _exact(row: Mapping[str, Any]) -> bool:
    return bool(row["evaluator_valid"] and float(row["metrics"]["score"]) == 1.0)


def _composite(row: Mapping[str, Any]) -> float:
    metrics = row["metrics"]
    return sum(
        float(metrics[name])
        for name in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
    ) / 4.0


def _metrics(ids: list[str], summary: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    values = [summary[identity] for identity in ids]
    return {
        "task_count": len(values),
        "evaluator_valid": sum(bool(value["evaluator_valid"]) for value in values),
        "whole_table_successes": sum(_exact(value) for value in values),
        "quality_composite_mean": (
            sum(_composite(value) for value in values) / len(values)
            if values
            else None
        ),
    }


class _NoRecordHybrid:
    """Minimum state needed to replay the real V2.53.95 verifier."""

    prepared_records = None
    grounded_prepared_records = None

    @staticmethod
    def choose_record_source() -> str:
        return "none"


def _validator_replay(
    tasks: list[dict[str, str]],
    limits: Any,
) -> tuple[set[str], dict[str, int]]:
    failures: set[str] = set()
    types: Counter[str] = Counter()
    for task in tasks:
        plan, _observation, _source = schema.projected_plan(
            {}, task["question"], limits
        )
        local = membership._TaskLocalVerifier(_NoRecordHybrid())
        try:
            local.prepare_record_proposal(task["question"], plan["columns"], ())
        except BaseException as exc:
            failures.add(task["opaque_id"])
            types[f"{type(exc).__name__}: {exc}"] += 1
    return failures, dict(sorted(types.items()))


def _artifact_barrier() -> None:
    drifted = [
        str(path)
        for path, digest in FIXED_SHA256.items()
        if contract.sha256(ROOT / path) != digest
    ]
    if drifted:
        raise RuntimeError(f"V2.55.74 fixed input hash drifted: {drifted}")
    for result_path, audit_path in (
        (V25573_RESULT, V25573_POSTAUDIT),
        (V25568_RESULT, V25568_POSTAUDIT),
        (V24857_RESULT, V24857_POSTAUDIT),
        (V25406_RESULT, V25406_POSTAUDIT),
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
            raise RuntimeError("V2.55.74 frozen result barrier drifted")


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    _artifact_barrier()
    tasks = contract.task_vector(ROOT)
    summaries = {
        "v25568": _summary(V25568_ROOT),
        "v25573": _summary(V25573_ROOT),
    }
    rows = {
        "v25379": _rows(V25379_ROOT),
        "v25406": _rows(V25406_ROOT),
        "v25568": _rows(V25568_ROOT),
        "v25573": _rows(V25573_ROOT),
    }
    predictions = {
        "v25568": _predictions(V25568_ROOT),
        "v25573": _predictions(V25573_ROOT),
    }
    identities = [task["opaque_id"] for task in tasks]
    expected = set(identities)
    if (
        len(identities) != 220
        or len(expected) != 220
        or any(set(value) != expected for value in summaries.values())
        or any(set(value) != expected for value in rows.values())
        or any(set(value) != expected for value in predictions.values())
    ):
        raise RuntimeError("V2.55.74 cross-version task alignment drifted")

    current_failures = {
        identity
        for identity in identities
        if not rows["v25573"][identity]["runtime_completed"]
    }
    v25406_failures = {
        identity
        for identity in identities
        if not rows["v25406"][identity]["runtime_completed"]
    }
    v25568_failures = {
        identity
        for identity in identities
        if not rows["v25568"][identity]["runtime_completed"]
    }
    recovered = sorted(v25568_failures - current_failures)
    common_runtime = sorted(expected - v25568_failures)

    limits = schema.score.ScoreFirstLimits(**contract.LIMITS)
    canonical_column_drift: set[str] = set()
    drift_membership = 0
    drift_schema_sources: Counter[str] = Counter()
    for task in tasks:
        plan, _observation, source = schema.projected_plan(
            {}, task["question"], limits
        )
        columns = tuple(plan["columns"])
        normalized = tuple(quote._text(value) for value in columns)
        if columns != normalized:
            canonical_column_drift.add(task["opaque_id"])
            members, _membership_source = membership.visible_membership(
                task["question"]
            )
            drift_membership += int(bool(members))
            drift_schema_sources[source] += 1
    replay_failures, replay_types = _validator_replay(tasks, limits)

    exact_patterns = Counter(
        "".join(
            "1" if _exact(summaries[version][identity]) else "0"
            for version in ("v25568", "v25573")
        )
        for identity in identities
    )
    prediction_equal = {
        f"{left}_vs_{right}": sum(
            predictions[left][identity]["prediction_sha256"]
            == predictions[right][identity]["prediction_sha256"]
            for identity in identities
        )
        for left, right in (("v25568", "v25573"),)
    }
    exact_overlap = {
        f"{left}_vs_{right}": {
            "both_exact": sum(
                _exact(summaries[left][identity])
                and _exact(summaries[right][identity])
                for identity in identities
            ),
            "left_only_exact": sum(
                _exact(summaries[left][identity])
                and not _exact(summaries[right][identity])
                for identity in identities
            ),
            "right_only_exact": sum(
                not _exact(summaries[left][identity])
                and _exact(summaries[right][identity])
                for identity in identities
            ),
        }
        for left, right in (("v25568", "v25573"),)
    }

    outer_effects = Counter()
    outer_health = Counter()
    for identity in current_failures:
        row = rows["v25573"][identity]
        snapshot = row["actual_effect_snapshot"]
        outer_effects[
            (
                snapshot["logical_queries"],
                snapshot["fetch_requests"],
                snapshot["model_logical_requests"],
                snapshot["model_provider_successes"],
            )
        ] += 1
        outer_health[
            sum(int(value) for value in row["effect_health"].values())
        ] += 1

    changed = [
        identity
        for identity in identities
        if rows["v25573"][identity]["runtime_completed"]
        and rows["v25573"][identity]["runtime_result"][
            "candidate_prediction_changed"
        ]
    ]
    current_result = _read_json(V25573_RESULT)["metrics"]["all_220"]
    previous_result = _read_json(V25568_RESULT)["metrics"]["all_220"]
    peak_result = _read_json(V24857_RESULT)["metrics"]["all_220"]

    checks = {
        "fixed_source_and_artifact_hashes_exact": True,
        "all_cross_version_vectors_align_exact220": True,
        "v25573_and_v25406_failure_sets_equal_eleven": (
            current_failures == v25406_failures and len(current_failures) == 11
        ),
        "all_eleven_failed_tasks_completed_in_v25379": all(
            rows["v25379"][identity]["runtime_completed"]
            and rows["v25379"][identity]["prediction_kind"] == "model_generated"
            for identity in current_failures
        ),
        "canonical_column_drift_set_equals_failure_set": (
            canonical_column_drift == current_failures
        ),
        "real_v25395_validator_replay_set_equals_failure_set": (
            replay_failures == current_failures
        ),
        "real_validator_replay_exception_is_selected_state_drift": replay_types
        == {"ValueError: V2.53.95 selected verifier state drifted": 11},
        "failure_set_is_not_membership_set": drift_membership == 2,
        "recovered_v25568_failures_are_29_without_exact_gain": (
            len(recovered) == 29
            and _metrics(recovered, summaries["v25568"])[
                "whole_table_successes"
            ]
            == 0
            and _metrics(recovered, summaries["v25573"])[
                "whole_table_successes"
            ]
            == 0
        ),
        "candidate_changed_tasks_are_four_without_exact": (
            len(changed) == 4
            and _metrics(changed, summaries["v25573"])[
                "whole_table_successes"
            ]
            == 0
        ),
        "entropy_or_information_gain_positive_signed_credit_zero": (
            _read_json(contract.FORWARD_RESULT)["positive_signed_credit_count"]
            == 0
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_sha256": {
            str(path): digest for path, digest in sorted(FIXED_SHA256.items(), key=lambda item: str(item[0]))
        },
        "all220_published_metrics": {
            "v24857": copy.deepcopy(peak_result),
            "v25568": copy.deepcopy(previous_result),
            "v25573": copy.deepcopy(current_result),
        },
        "reliability_funnel": {
            "v25568_outer_failure_tasks": len(v25568_failures),
            "v25573_outer_failure_tasks": len(current_failures),
            "v25568_failure_to_v25573_runtime_recovered_tasks": len(recovered),
            "recovered_canonical_model_generated_tasks": sum(
                rows["v25573"][identity]["canonical_projection"]
                for identity in recovered
            ),
            "recovered_safe_parent_handoff_tasks": sum(
                rows["v25573"][identity]["byte_exact_parent_handoff"]
                for identity in recovered
            ),
            "recovered_metrics_v25568": _metrics(
                recovered, summaries["v25568"]
            ),
            "recovered_metrics_v25573": _metrics(
                recovered, summaries["v25573"]
            ),
            "common_runtime_tasks": len(common_runtime),
            "common_runtime_metrics_v25568": _metrics(
                common_runtime, summaries["v25568"]
            ),
            "common_runtime_metrics_v25573": _metrics(
                common_runtime, summaries["v25573"]
            ),
            "v25573_candidate_changed_tasks": len(changed),
            "v25573_candidate_changed_metrics": _metrics(
                changed, summaries["v25573"]
            ),
        },
        "persistent_failure_diagnosis": {
            "v25406_failure_set_equal": current_failures == v25406_failures,
            "v25379_same_tasks_completed_model_generated": sum(
                rows["v25379"][identity]["runtime_completed"]
                and rows["v25379"][identity]["prediction_kind"]
                == "model_generated"
                for identity in current_failures
            ),
            "outer_failure_type_histogram": dict(
                sorted(
                    Counter(
                        str(rows["v25573"][identity]["outer_failure_type"])
                        for identity in current_failures
                    ).items()
                )
            ),
            "outer_stage_receipt_present_tasks": sum(
                rows["v25573"][identity]["content_free_stage_receipt"]
                is not None
                for identity in current_failures
            ),
            "query_fetch_model_success_histogram": {
                f"query{key[0]}_fetch{key[1]}_model{key[2]}_success{key[3]}": count
                for key, count in sorted(outer_effects.items())
            },
            "effect_health_event_count_histogram": {
                str(key): count for key, count in sorted(outer_health.items())
            },
            "visible_membership_present_tasks": drift_membership,
            "visible_membership_absent_tasks": len(current_failures)
            - drift_membership,
            "visible_schema_source_histogram": dict(
                sorted(drift_schema_sources.items())
            ),
            "raw_vs_canonical_column_drift_tasks": len(
                canonical_column_drift
            ),
            "raw_vs_canonical_column_drift_set_equals_outer_failure_set": (
                canonical_column_drift == current_failures
            ),
            "real_v25395_validator_replay_failure_tasks": len(
                replay_failures
            ),
            "real_v25395_validator_replay_failure_set_equals_outer_failure_set": (
                replay_failures == current_failures
            ),
            "real_v25395_validator_replay_exception_histogram": replay_types,
            "root_cause": "prepared_columns_are_nfkc_whitespace_canonical_but_v25395_compares_them_bytewise_to_raw_runtime_columns",
        },
        "rollout_variability_descriptive_not_causal": {
            "exact_pattern_order": ["v25568", "v25573"],
            "exact_pattern_histogram": dict(sorted(exact_patterns.items())),
            "prediction_byte_equal_counts": prediction_equal,
            "exact_overlap": exact_overlap,
            "independent_cold_rollouts_do_not_identify_wrapper_causality": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "decision": {
            "v25573_exact220_quality": "no_go",
            "next_build": "append_only_canonical_column_binding_totality_successor",
            "historical_module_bytes_must_remain_unchanged": True,
            "successor_must_compare_both_column_vectors_with_same_nfkc_whitespace_canonicalizer": True,
            "invalid_duplicate_overlong_or_forbidden_columns_remain_fail_closed": True,
            "full220_synthetic_replay_required_before_external_gate": True,
            "fresh_disjoint_quality_gate_required_before_new_exact220": True,
            "historical_per_task_outcome_runtime_routing": False,
            "deepwidebench_retry_resume_backfill_or_selective_rerun": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        },
        "postfreeze_offline_analysis_only": True,
        "contains_question_opaque_id_prediction_answer_evaluator_message_per_task_score_or_per_task_correctness": False,
        "external_network_model_provider_search_fetch_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "successor_build_and_local_synthetic_replay": not findings,
            "fresh_external_protocol": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    checks = copied.get("checks") or {}
    reliability = copied.get("reliability_funnel") or {}
    failure = copied.get("persistent_failure_diagnosis") or {}
    variability = copied.get("rollout_variability_descriptive_not_causal") or {}
    decision = copied.get("decision") or {}
    valid = copied.get("diagnosis_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("fixed_sha256")
        != {str(path): digest for path, digest in sorted(FIXED_SHA256.items(), key=lambda item: str(item[0]))}
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not all(checks.values())
        or reliability.get("v25568_outer_failure_tasks") != 40
        or reliability.get("v25573_outer_failure_tasks") != 11
        or reliability.get(
            "v25568_failure_to_v25573_runtime_recovered_tasks"
        )
        != 29
        or reliability.get("recovered_canonical_model_generated_tasks") != 24
        or reliability.get("recovered_safe_parent_handoff_tasks") != 5
        or reliability.get("common_runtime_tasks") != 180
        or reliability.get("v25573_candidate_changed_tasks") != 4
        or failure.get("v25406_failure_set_equal") is not True
        or failure.get("v25379_same_tasks_completed_model_generated") != 11
        or failure.get("outer_failure_type_histogram") != {"ValueError": 11}
        or failure.get("outer_stage_receipt_present_tasks") != 0
        or failure.get("query_fetch_model_success_histogram")
        != {
            "query4_fetch10_model3_success3": 10,
            "query4_fetch8_model3_success3": 1,
        }
        or failure.get("visible_membership_present_tasks") != 2
        or failure.get("visible_membership_absent_tasks") != 9
        or failure.get("raw_vs_canonical_column_drift_tasks") != 11
        or failure.get(
            "raw_vs_canonical_column_drift_set_equals_outer_failure_set"
        )
        is not True
        or failure.get("real_v25395_validator_replay_failure_tasks") != 11
        or failure.get(
            "real_v25395_validator_replay_failure_set_equals_outer_failure_set"
        )
        is not True
        or failure.get("real_v25395_validator_replay_exception_histogram")
        != {"ValueError: V2.53.95 selected verifier state drifted": 11}
        or failure.get("root_cause")
        != "prepared_columns_are_nfkc_whitespace_canonical_but_v25395_compares_them_bytewise_to_raw_runtime_columns"
        or variability.get("exact_pattern_order") != ["v25568", "v25573"]
        or variability.get("exact_pattern_histogram")
        != {"00": 211, "10": 5, "11": 4}
        or variability.get("independent_cold_rollouts_do_not_identify_wrapper_causality")
        is not True
        or decision
        != {
            "v25573_exact220_quality": "no_go",
            "next_build": "append_only_canonical_column_binding_totality_successor",
            "historical_module_bytes_must_remain_unchanged": True,
            "successor_must_compare_both_column_vectors_with_same_nfkc_whitespace_canonicalizer": True,
            "invalid_duplicate_overlong_or_forbidden_columns_remain_fail_closed": True,
            "full220_synthetic_replay_required_before_external_gate": True,
            "fresh_disjoint_quality_gate_required_before_new_exact220": True,
            "historical_per_task_outcome_runtime_routing": False,
            "deepwidebench_retry_resume_backfill_or_selective_rerun": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        }
        or copied.get("postfreeze_offline_analysis_only") is not True
        or copied.get("contains_question_opaque_id_prediction_answer_evaluator_message_per_task_score_or_per_task_correctness")
        is not False
        or copied.get(
            "external_network_model_provider_search_fetch_or_evaluator_called"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "successor_build_and_local_synthetic_replay": valid,
            "fresh_external_protocol": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.74 diagnosis drifted")
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
    value = build_diagnosis()
    if not args.validate_only:
        _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "findings": value["findings"],
                "root_cause": value["persistent_failure_diagnosis"][
                    "root_cause"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
