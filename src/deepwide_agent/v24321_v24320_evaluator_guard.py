"""Fail-closed evaluator guard for the frozen V2.43.20 paired-dev64 run.

This module is deliberately post-forward.  It may inspect frozen prediction
artifacts, but it has no mapping, answer, evaluator, model, search, or network
capability.  Its only positive authorization is opening the already frozen
V2.43.20 evaluator after every forward-integrity invariant is exact.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .v24320_forward_contract import (
    ACTIVATION,
    ARMS,
    EXECUTION_START,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    FULL_PROTOCOL,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    payload_sha256,
    read_object,
    sha256,
    validate_forward_contract,
)


POLICY_ID = "v24321_v24320_fail_closed_evaluator_guard_v1"
ROLE = "v24321_v24320_evaluator_guard_decision"
DATE = "20260803"
PREREGISTRATION = Path(
    f"results/v24321_v24320_evaluator_guard_preregistration_v1_{DATE}.json"
)
SOURCE_FILES = (
    "src/deepwide_agent/v24321_v24320_evaluator_guard.py",
    "scripts/preregister_v24321_v24320_evaluator_guard.py",
    "scripts/publish_v24321_v24320_evaluator_gate.py",
    "scripts/finalize_v24320_guarded_by_v24321.py",
    "tests/test_v24321_v24320_evaluator_guard.py",
)
DECISION = Path(
    f"results/v24321_v24320_evaluator_guard_decision_v1_{DATE}.json"
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def integrity_checks(
    forward: Mapping[str, Any], summaries: Mapping[str, Mapping[str, Any]]
) -> dict[str, bool]:
    checks: dict[str, bool] = {
        "both_arms_exact64": forward.get("terminal_predictions_per_arm")
        == {arm: SELECTED_COUNT for arm in ARMS},
        "prediction_freeze_precedes_evaluator": forward.get(
            "both_arms_exact64_before_mapping_gold_or_evaluator_open"
        )
        is True,
        "forward_mapping_or_evaluator_closed": forward.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is False
        and forward.get("official_evaluator_called") is False,
    }
    shared = forward.get("shared_model_receipts")
    for arm in ARMS:
        summary = summaries.get(arm, {})
        observability = summary.get("parent_exit_observability", {})
        mechanism = summary.get("mechanism_totals", {})
        receipt = shared.get(arm, {}) if isinstance(shared, Mapping) else {}
        prefix = f"{arm}_"
        checks.update(
            {
                prefix + "fixed_denominator": summary.get("selected")
                == SELECTED_COUNT
                and summary.get("completed") == SELECTED_COUNT
                and summary.get("failed") == 0,
                prefix + "parent_receipts_exact": observability.get(
                    "receipts_present"
                )
                == SELECTED_COUNT
                and observability.get("receipts_valid") == SELECTED_COUNT,
                prefix + "child_model_transport_exact": observability.get(
                    "valid_child_terminal_receipts"
                )
                == SELECTED_COUNT
                and observability.get("valid_model_slot_receipts")
                == SELECTED_COUNT
                and observability.get("valid_transport_receipts")
                == SELECTED_COUNT,
                prefix + "parent_success_exact": observability.get(
                    "accepted_parent_successes"
                )
                == SELECTED_COUNT
                and observability.get("non_success_parent_exits") == 0,
                prefix + "effect_counts_exact": observability.get(
                    "incomplete_effect_counts"
                )
                == 0
                and mechanism.get("effect_count_complete") == SELECTED_COUNT
                and mechanism.get("effect_attribution_complete")
                == SELECTED_COUNT
                and mechanism.get("provider_attempt_count_complete")
                == SELECTED_COUNT
                and mechanism.get("fourth_model_effect") == 0,
                prefix + "conservation_exact": receipt.get("valid")
                == SELECTED_COUNT
                and receipt.get("invalid") == 0
                and receipt.get("all_complete_counts_match") is True
                and receipt.get("logical_admissions_lower_bound")
                == receipt.get("provider_requests_lower_bound", -1)
                + receipt.get("pre_provider_rejections_lower_bound", -1)
                and receipt.get("provider_requests_lower_bound")
                == receipt.get("slot_acquisitions_from_valid_receipts")
                and receipt.get("pre_provider_rejections_lower_bound")
                == receipt.get("slot_timeouts_from_valid_receipts"),
            }
        )
    return checks


def validate_preregistration(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    manifest = value.get("source_manifest")
    expected_parent = {
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
    }
    if (
        value.get("role")
        != "v24321_v24320_evaluator_guard_preregistration"
        or value.get("policy_id") != POLICY_ID
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(SOURCE_FILES)
        or value.get("source_manifest_sha256") != payload_sha256(manifest)
        or value.get("parent_provenance") != expected_parent
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("authorization", {}).get("evaluator_before_positive_guard")
        is not False
        or value.get("authorization", {}).get("exact220_leaderboard_or_sota")
        is not False
        or not _sealed(value, "preregistration_payload_sha256")
    ):
        raise ValueError("V2.43.21 evaluator guard preregistration drifted")
    for relative, digest in manifest.items():
        path = root / relative
        if (
            Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root)
            or sha256(path) != digest
        ):
            raise ValueError("V2.43.21 evaluator guard source manifest drifted")
    return dict(value)


def build_decision(
    root: Path,
    *,
    evaluator_surface_absent: bool,
    runner_and_children_absent: bool,
    shared_lease_inactive: bool,
    protected_watchers_unchanged: bool,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    validate_preregistration(root, read_object(root / PREREGISTRATION))
    from scripts.run_v24320_paired_dev64 import validate_forward_result

    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, contract, forward)
    summaries = {arm: read_object(root / RUN_SUMMARY[arm]) for arm in ARMS}
    checks = integrity_checks(forward, summaries)
    checks.update(
        {
            "evaluator_surface_absent": evaluator_surface_absent is True,
            "runner_and_children_absent": runner_and_children_absent is True,
            "shared_lease_inactive": shared_lease_inactive is True,
            "protected_watchers_unchanged": protected_watchers_unchanged is True,
        }
    )
    passed = all(checks.values())
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "provenance": {
            "guard_preregistration_sha256": sha256(root / PREREGISTRATION),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "protocol_sha256": sha256(root / FULL_PROTOCOL),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "prediction_freeze_sha256": {
                arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
            },
            "run_summary_sha256": {
                arm: sha256(root / RUN_SUMMARY[arm]) for arm in ARMS
            },
        },
        "checks": checks,
        "passed": passed,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "source_policy": {
            "post_both_arm_prediction_freeze": True,
            "question_prediction_or_opaque_id_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "authorization": {
            "v24320_evaluator": passed,
            "resume_skip_selective_retry_or_error_revaluation": False,
            "exact220_leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    passed = isinstance(checks, Mapping) and bool(checks) and all(
        item is True for item in checks.values()
    )
    if (
        value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or any(not isinstance(item, bool) for item in checks.values())
        or value.get("passed") is not passed
        or value.get("failed_checks")
        != sorted(name for name, ok in checks.items() if not ok)
        or value.get("authorization", {}).get("v24320_evaluator") is not passed
        or value.get("authorization", {}).get("exact220_leaderboard_or_sota")
        is not False
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise ValueError("V2.43.21 evaluator guard decision drifted")
    return dict(value)


def validate_live_decision(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    output = validate_decision(value)
    validate_preregistration(root, read_object(root / PREREGISTRATION))
    expected = {
        "guard_preregistration_sha256": sha256(root / PREREGISTRATION),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "run_summary_sha256": {
            arm: sha256(root / RUN_SUMMARY[arm]) for arm in ARMS
        },
    }
    if output.get("provenance") != expected:
        raise ValueError("V2.43.21 live evaluator guard provenance drifted")
    return output


__all__ = [
    "DATE",
    "DECISION",
    "POLICY_ID",
    "PREREGISTRATION",
    "ROLE",
    "build_decision",
    "integrity_checks",
    "validate_decision",
    "validate_live_decision",
    "validate_preregistration",
]
