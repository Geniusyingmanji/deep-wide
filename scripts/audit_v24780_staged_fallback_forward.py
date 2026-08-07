#!/usr/bin/env python3
"""Post-forward, pre-quality content-free audit for V2.47.80."""

from __future__ import annotations

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

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24780_staged_fallback_execution_contract import (  # noqa: E402
    FORWARD_AUDIT,
    FORWARD_RESULT,
    EXECUTION_START,
    MODEL_RECEIPT_NAME,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PARENT_RECEIPT_NAME,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    TRANSPORT_RECEIPT_NAME,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    validate_forward_result,
    validate_prediction_freeze,
    validate_run_summary,
)


HEALTH_CHECK_NAMES = (
    "eight_of_eight_terminal_ordinals",
    "fixed_denominator_failure_as_zero",
    "parent_taxonomy_matches_run_summary",
    "all_task_ordinals_submitted_once",
    "within_experiment_wall_ceiling",
    "eight_of_eight_content_free_effect_receipt_pairs_valid",
    "effect_receipts_match_parent_flags",
    "model_acquisitions_within_frozen_caps",
    "model_logical_attempts_within_frozen_caps",
    "physical_fetch_helpers_within_frozen_caps",
    "all_task_fetch_requests_within_frozen_caps",
    "hosted_search_attempts_within_transport_retry_cap",
    "successful_result_fetches_do_not_exceed_all_task_transport_requests",
    "physical_fetches_within_frozen_caps",
    "usable_page_accounting_exact",
    "failed_url_retry_count_zero",
    "scheduler_contract",
    "candidate_changes_only_unknown",
    "semantic_safety_contract",
    "nonunknown_cell_change_count_zero",
    "prediction_freeze_before_private_truth",
    "no_resume_retry_skip_or_selective_rerun",
)
MECHANISM_CHECK_NAMES = (
    "minimum_changed_tasks",
    "minimum_changed_cells",
    "minimum_projection_backed_support_sets",
    "minimum_reserve_fetch_requests",
    "minimum_reserve_usable_pages",
    "minimum_entity_slots_brought_to_two_sources_by_reserve",
    "minimum_final_entity_slots_with_two_usable_identity_sources",
)
GATE_CHECK_NAMES = frozenset((*HEALTH_CHECK_NAMES, *MECHANISM_CHECK_NAMES))
EFFECT_RECEIPT_KEYS = frozenset(
    {
        "ordinal",
        "parent_receipt_sha256",
        "parent_receipt_valid",
        "failure_taxonomy",
        "model_receipt_sha256",
        "model_receipt_present",
        "model_receipt_valid",
        "model_acquisitions",
        "model_slot_timeouts",
        "transport_receipt_sha256",
        "transport_receipt_present",
        "transport_receipt_valid",
        "hosted_search_attempts",
        "hard_fetch_helper_calls",
        "fetch_deadline_rejections",
        "parent_effect_receipt_flags_match",
    }
)
EFFECT_METRIC_NAMES = (
    "content_free_effect_receipt_pair_count",
    "valid_model_receipt_count",
    "valid_transport_receipt_count",
    "model_acquisition_count",
    "model_slot_timeout_count",
    "hosted_search_attempt_count",
    "hard_fetch_helper_call_count",
    "fetch_deadline_rejection_count",
    "all_task_fetch_request_count",
)
SUMMARY_METRIC_NAMES = (
    "valid_task_results",
    "projected_failure_tasks",
    "forward_wall_seconds",
    "changed_task_count",
    "changed_cell_count",
    "founded_changed_cell_count",
    "country_changed_cell_count",
    "nonunknown_changed_cell_count",
    "projection_backed_support_set_count",
    "initial_fetch_request_count",
    "reserve_fetch_request_count",
    "actual_fetch_request_count",
    "initial_usable_page_count",
    "reserve_usable_page_count",
    "actual_usable_page_count",
    "final_entity_slots_with_two_usable_identity_sources",
    "entity_slots_brought_to_two_sources_by_reserve",
    "reserve_target_entity_count",
    "failed_url_retry_count",
    "scheduler_contract_failed_task_count",
)
CONTENT_FREE_METRIC_NAMES = frozenset((*EFFECT_METRIC_NAMES, *SUMMARY_METRIC_NAMES))


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.80 forward audit expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.80 forward audit expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _collect_task_receipts() -> tuple[
    list[dict[str, Any]], Counter[str], dict[str, int]
]:
    """Read only content-free parent/model/transport receipts for all ordinals."""

    rows: list[dict[str, Any]] = []
    taxonomy: Counter[str] = Counter()
    for ordinal in range(1, SELECTED_COUNT + 1):
        directory = ROOT / TASK_ROOT / f"task_{ordinal:04d}"
        parent_path = directory / PARENT_RECEIPT_NAME
        model_path = directory / MODEL_RECEIPT_NAME
        transport_path = directory / TRANSPORT_RECEIPT_NAME
        parent: dict[str, Any] | None = None
        try:
            parent = validate_parent_receipt(_read(parent_path))
            parent_valid = True
            parent_digest: str | None = sha256(parent_path)
            failure_taxonomy = str(parent["failure_taxonomy"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            parent_valid = False
            parent_digest = None
            failure_taxonomy = "parent_receipt_missing_or_invalid"
        model_present = _present(model_path)
        try:
            model = validate_model_receipt(
                _read(model_path), expected_cap=MODEL_SLOT_CAP
            )
            model_valid = True
            model_digest: str | None = sha256(model_path)
            acquisitions: int | None = int(model["acquisitions"])
            slot_timeouts: int | None = int(model["slot_timeouts"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            model_valid = False
            model_digest = None
            acquisitions = None
            slot_timeouts = None
        transport_present = _present(transport_path)
        try:
            transport = validate_transport_health(_read(transport_path))
            transport_valid = True
            transport_digest: str | None = sha256(transport_path)
            hosted_attempts: int | None = int(transport["hosted_search_attempts"])
            hard_fetches: int | None = int(transport["hard_fetch_helper_calls"])
            deadline_rejections: int | None = int(
                transport["fetch_deadline_rejections"]
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            transport_valid = False
            transport_digest = None
            hosted_attempts = None
            hard_fetches = None
            deadline_rejections = None
        parent_flags_match = bool(
            parent_valid
            and parent is not None
            and parent["model_receipt_present"] is model_present
            and parent["model_receipt_valid"] is model_valid
            and parent["transport_receipt_present"] is transport_present
            and parent["transport_receipt_valid"] is transport_valid
        )
        rows.append(
            {
                "ordinal": ordinal,
                "parent_receipt_sha256": parent_digest,
                "parent_receipt_valid": parent_valid,
                "failure_taxonomy": failure_taxonomy,
                "model_receipt_sha256": model_digest,
                "model_receipt_present": model_present,
                "model_receipt_valid": model_valid,
                "model_acquisitions": acquisitions,
                "model_slot_timeouts": slot_timeouts,
                "transport_receipt_sha256": transport_digest,
                "transport_receipt_present": transport_present,
                "transport_receipt_valid": transport_valid,
                "hosted_search_attempts": hosted_attempts,
                "hard_fetch_helper_calls": hard_fetches,
                "fetch_deadline_rejections": deadline_rejections,
                "parent_effect_receipt_flags_match": parent_flags_match,
            }
        )
        taxonomy[failure_taxonomy] += 1
    metrics = {
        "content_free_effect_receipt_pair_count": len(rows),
        "valid_model_receipt_count": sum(row["model_receipt_valid"] for row in rows),
        "valid_transport_receipt_count": sum(
            row["transport_receipt_valid"] for row in rows
        ),
        "model_acquisition_count": sum(
            int(row["model_acquisitions"] or 0) for row in rows
        ),
        "model_slot_timeout_count": sum(
            int(row["model_slot_timeouts"] or 0) for row in rows
        ),
        "hosted_search_attempt_count": sum(
            int(row["hosted_search_attempts"] or 0) for row in rows
        ),
        "hard_fetch_helper_call_count": sum(
            int(row["hard_fetch_helper_calls"] or 0) for row in rows
        ),
        "fetch_deadline_rejection_count": sum(
            int(row["fetch_deadline_rejections"] or 0) for row in rows
        ),
    }
    metrics["all_task_fetch_request_count"] = (
        metrics["hard_fetch_helper_call_count"]
        + metrics["fetch_deadline_rejection_count"]
    )
    return rows, taxonomy, metrics


def _effect_cap_checks(
    task_receipts: list[Mapping[str, Any]],
    effect_metrics: Mapping[str, int],
    *,
    successful_result_fetches: int,
) -> dict[str, bool]:
    """Derive effect caps without reading results, predictions, pages, or labels."""

    return {
        "eight_of_eight_content_free_effect_receipt_pairs_valid": (
            effect_metrics["valid_model_receipt_count"] == SELECTED_COUNT
            and effect_metrics["valid_transport_receipt_count"] == SELECTED_COUNT
        ),
        "effect_receipts_match_parent_flags": all(
            item["parent_effect_receipt_flags_match"] for item in task_receipts
        ),
        "model_acquisitions_within_frozen_caps": (
            all(
                item["model_receipt_valid"]
                and item["model_acquisitions"] is not None
                and item["model_acquisitions"] <= 2
                for item in task_receipts
            )
            and effect_metrics["model_acquisition_count"] <= SELECTED_COUNT * 2
        ),
        "model_logical_attempts_within_frozen_caps": all(
            item["model_receipt_valid"]
            and item["model_acquisitions"] is not None
            and item["model_slot_timeouts"] is not None
            and item["model_acquisitions"] + item["model_slot_timeouts"] <= 2
            for item in task_receipts
        ),
        "physical_fetch_helpers_within_frozen_caps": (
            all(
                item["transport_receipt_valid"]
                and item["hard_fetch_helper_calls"] is not None
                and item["hard_fetch_helper_calls"] <= 10
                for item in task_receipts
            )
            and effect_metrics["hard_fetch_helper_call_count"]
            <= SELECTED_COUNT * 10
        ),
        "all_task_fetch_requests_within_frozen_caps": (
            all(
                item["transport_receipt_valid"]
                and item["hard_fetch_helper_calls"] is not None
                and item["fetch_deadline_rejections"] is not None
                and item["hard_fetch_helper_calls"]
                + item["fetch_deadline_rejections"]
                <= 10
                for item in task_receipts
            )
            and effect_metrics["all_task_fetch_request_count"]
            <= SELECTED_COUNT * 10
        ),
        "hosted_search_attempts_within_transport_retry_cap": (
            all(
                item["transport_receipt_valid"]
                and item["hosted_search_attempts"] is not None
                and item["hosted_search_attempts"] <= 2
                for item in task_receipts
            )
            and effect_metrics["hosted_search_attempt_count"]
            <= SELECTED_COUNT * 2
        ),
        "successful_result_fetches_do_not_exceed_all_task_transport_requests": (
            successful_result_fetches
            <= effect_metrics["all_task_fetch_request_count"]
        ),
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / PROTOCOL)
    summary = validate_run_summary(_read(ROOT / RUN_SUMMARY))
    freeze = validate_prediction_freeze(_read(ROOT / PREDICTION_FREEZE))
    forward = validate_forward_result(_read(ROOT / FORWARD_RESULT))
    if (
        protocol.get("role")
        != "v24780_staged_fallback_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or not _sealed(protocol, "protocol_payload_sha256")
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or freeze.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or forward.get("prediction_freeze_sha256")
        != sha256(ROOT / PREDICTION_FREEZE)
        or forward.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or forward.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
    ):
        raise RuntimeError("V2.47.80 forward audit parent drifted")
    task_receipts, taxonomy, effect_metrics = _collect_task_receipts()
    mechanism = protocol["mechanism_gate_before_private_truth"]
    effect_checks = _effect_cap_checks(
        task_receipts,
        effect_metrics,
        successful_result_fetches=summary["actual_fetch_request_count"],
    )
    checks = {
        "eight_of_eight_terminal_ordinals": len(task_receipts) == SELECTED_COUNT
        and all(item["parent_receipt_valid"] for item in task_receipts),
        "fixed_denominator_failure_as_zero": summary["selected_tasks"]
        == SELECTED_COUNT,
        "parent_taxonomy_matches_run_summary": dict(sorted(taxonomy.items()))
        == summary["parent_failure_taxonomy_counts"],
        "all_task_ordinals_submitted_once": summary[
            "all_task_ordinals_submitted_once"
        ],
        "within_experiment_wall_ceiling": summary[
            "within_experiment_wall_ceiling"
        ],
        **effect_checks,
        "physical_fetches_within_frozen_caps": (
            summary["initial_fetch_request_count"] <= SELECTED_COUNT * 8
            and summary["reserve_fetch_request_count"] <= SELECTED_COUNT * 2
            and summary["actual_fetch_request_count"] <= SELECTED_COUNT * 10
            and summary["actual_fetch_request_count"]
            == summary["initial_fetch_request_count"]
            + summary["reserve_fetch_request_count"]
        ),
        "usable_page_accounting_exact": (
            summary["actual_usable_page_count"]
            == summary["initial_usable_page_count"]
            + summary["reserve_usable_page_count"]
            and summary["actual_usable_page_count"]
            <= summary["actual_fetch_request_count"]
        ),
        "failed_url_retry_count_zero": summary["failed_url_retry_count"]
        == mechanism["failed_url_retry_count_required"],
        "scheduler_contract": summary["scheduler_contract_failed_task_count"]
        == 0,
        "candidate_changes_only_unknown": summary[
            "candidate_not_only_unknown_task_count"
        ]
        == 0,
        "semantic_safety_contract": summary[
            "semantic_safety_contract_failed_task_count"
        ]
        == 0,
        "nonunknown_cell_change_count_zero": summary[
            "nonunknown_changed_cell_count"
        ]
        == mechanism["nonunknown_cell_change_count_required"],
        "minimum_changed_tasks": summary["changed_task_count"]
        >= mechanism["minimum_changed_task_count"],
        "minimum_changed_cells": summary["changed_cell_count"]
        >= mechanism["minimum_changed_cell_count"],
        "minimum_projection_backed_support_sets": summary[
            "projection_backed_support_set_count"
        ]
        >= mechanism["minimum_projection_backed_support_set_count"],
        "minimum_reserve_fetch_requests": summary["reserve_fetch_request_count"]
        >= mechanism["minimum_reserve_fetch_request_count"],
        "minimum_reserve_usable_pages": summary["reserve_usable_page_count"]
        >= mechanism["minimum_reserve_usable_page_count"],
        "minimum_entity_slots_brought_to_two_sources_by_reserve": summary[
            "entity_slots_brought_to_two_sources_by_reserve"
        ]
        >= mechanism["minimum_entity_slots_brought_to_two_sources_by_reserve"],
        "minimum_final_entity_slots_with_two_usable_identity_sources": summary[
            "final_entity_slots_with_two_usable_identity_sources"
        ]
        >= mechanism[
            "minimum_final_entity_slots_with_two_usable_identity_sources"
        ],
        "prediction_freeze_before_private_truth": freeze[
            "all_predictions_terminal_before_private_truth_or_quality_open"
        ]
        and not freeze["private_truth_or_quality_path_opened_or_hashed"],
        "no_resume_retry_skip_or_selective_rerun": not summary[
            "resume_retry_skip_or_selective_rerun"
        ],
    }
    if set(checks) != GATE_CHECK_NAMES:
        raise RuntimeError("V2.47.80 forward audit gate surface drifted")
    health_go = all(checks[name] for name in HEALTH_CHECK_NAMES)
    mechanism_go = health_go and all(checks[name] for name in MECHANISM_CHECK_NAMES)
    findings = [name for name, passed in checks.items() if not passed]
    value = {
        "artifact_version": 1,
        "role": "v24780_staged_fallback_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "task_effect_receipts": task_receipts,
        "parent_failure_taxonomy_counts": dict(sorted(taxonomy.items())),
        "content_free_metrics": {
            **effect_metrics,
            **{
                key: summary[key]
                for key in SUMMARY_METRIC_NAMES
            },
        },
        "gate_checks": checks,
        "forward_health_go": health_go,
        "mechanism_go": mechanism_go,
        "findings": findings,
        "protected_watchers": protected_watcher_snapshot(),
        "source_policy": {
            "prediction_jsonl_opened_or_parsed": False,
            "prediction_jsonl_bytes_hashed_for_freeze_integrity": True,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "authorization": {
            "quality_preregistration_design": mechanism_go,
            "private_truth_or_quality_surface_open": False,
            "additional_forward_retry_resume_or_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("gate_checks")
    findings = copied.get("findings")
    health = copied.get("forward_health_go")
    mechanism = copied.get("mechanism_go")
    receipts = copied.get("task_effect_receipts")
    metrics = copied.get("content_free_metrics")
    hash_pattern = re.compile(r"[0-9a-f]{64}")
    receipts_are_mappings = isinstance(receipts, list) and all(
        isinstance(item, Mapping) for item in receipts
    )
    derived_effect_metrics: dict[str, int] | None = None
    derived_taxonomy: dict[str, int] | None = None
    if receipts_are_mappings:
        derived_effect_metrics = {
            "content_free_effect_receipt_pair_count": len(receipts),
            "valid_model_receipt_count": sum(
                item.get("model_receipt_valid") is True for item in receipts
            ),
            "valid_transport_receipt_count": sum(
                item.get("transport_receipt_valid") is True for item in receipts
            ),
            "model_acquisition_count": sum(
                int(item.get("model_acquisitions") or 0) for item in receipts
            ),
            "model_slot_timeout_count": sum(
                int(item.get("model_slot_timeouts") or 0) for item in receipts
            ),
            "hosted_search_attempt_count": sum(
                int(item.get("hosted_search_attempts") or 0) for item in receipts
            ),
            "hard_fetch_helper_call_count": sum(
                int(item.get("hard_fetch_helper_calls") or 0) for item in receipts
            ),
            "fetch_deadline_rejection_count": sum(
                int(item.get("fetch_deadline_rejections") or 0) for item in receipts
            ),
        }
        derived_effect_metrics["all_task_fetch_request_count"] = (
            derived_effect_metrics["hard_fetch_helper_call_count"]
            + derived_effect_metrics["fetch_deadline_rejection_count"]
        )
        derived_taxonomy = dict(
            sorted(
                Counter(
                    str(item.get("failure_taxonomy")) for item in receipts
                ).items()
            )
        )
    derived_effect_checks: dict[str, bool] | None = None
    if (
        receipts_are_mappings
        and derived_effect_metrics is not None
        and isinstance(metrics, Mapping)
        and isinstance(metrics.get("actual_fetch_request_count"), int)
    ):
        derived_effect_checks = _effect_cap_checks(
            receipts,
            derived_effect_metrics,
            successful_result_fetches=metrics["actual_fetch_request_count"],
        )
    if (
        copied.get("role") != "v24780_staged_fallback_forward_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or set(checks) != GATE_CHECK_NAMES
        or not all(isinstance(value, bool) for value in checks.values())
        or not isinstance(findings, list)
        or len(findings) != len(set(findings))
        or set(findings) != {name for name, passed in checks.items() if not passed}
        or not isinstance(health, bool)
        or not isinstance(mechanism, bool)
        or health != all(checks[name] for name in HEALTH_CHECK_NAMES)
        or mechanism
        != (health and all(checks[name] for name in MECHANISM_CHECK_NAMES))
        or not isinstance(receipts, list)
        or len(receipts) != SELECTED_COUNT
        or not receipts_are_mappings
        or [item.get("ordinal") for item in receipts]
        != list(range(1, SELECTED_COUNT + 1))
        or any(set(item) != EFFECT_RECEIPT_KEYS for item in receipts)
        or any(
            not isinstance(item["failure_taxonomy"], str)
            or not item["failure_taxonomy"]
            for item in receipts
        )
        or any(
            item[name] is not None
            and hash_pattern.fullmatch(str(item[name])) is None
            for item in receipts
            for name in (
                "parent_receipt_sha256",
                "model_receipt_sha256",
                "transport_receipt_sha256",
            )
        )
        or any(
            not isinstance(item[name], bool)
            for item in receipts
            for name in (
                "parent_receipt_valid",
                "model_receipt_present",
                "model_receipt_valid",
                "transport_receipt_present",
                "transport_receipt_valid",
                "parent_effect_receipt_flags_match",
            )
        )
        or any(
            item[name] is not None
            and (isinstance(item[name], bool) or not isinstance(item[name], int) or item[name] < 0)
            for item in receipts
            for name in (
                "model_acquisitions",
                "model_slot_timeouts",
                "hosted_search_attempts",
                "hard_fetch_helper_calls",
                "fetch_deadline_rejections",
            )
        )
        or any(
            (item["parent_receipt_sha256"] is None)
            is item["parent_receipt_valid"]
            or item["model_receipt_valid"]
            is not (
                item["model_receipt_present"]
                and item["model_receipt_sha256"] is not None
                and item["model_acquisitions"] is not None
                and item["model_slot_timeouts"] is not None
            )
            or item["transport_receipt_valid"]
            is not (
                item["transport_receipt_present"]
                and item["transport_receipt_sha256"] is not None
                and item["hosted_search_attempts"] is not None
                and item["hard_fetch_helper_calls"] is not None
                and item["fetch_deadline_rejections"] is not None
            )
            for item in receipts
        )
        or not isinstance(metrics, Mapping)
        or set(metrics) != CONTENT_FREE_METRIC_NAMES
        or any(
            isinstance(metrics.get(name), bool)
            or not isinstance(metrics.get(name), int)
            or metrics[name] < 0
            for name in EFFECT_METRIC_NAMES
        )
        or derived_effect_metrics is None
        or any(metrics[name] != derived_effect_metrics[name] for name in EFFECT_METRIC_NAMES)
        or copied.get("parent_failure_taxonomy_counts") != derived_taxonomy
        or derived_effect_checks is None
        or any(checks[name] is not passed for name, passed in derived_effect_checks.items())
        or copied.get("source_policy")
        != {
            "prediction_jsonl_opened_or_parsed": False,
            "prediction_jsonl_bytes_hashed_for_freeze_integrity": True,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        }
        or copied.get("authorization")
        != {
            "quality_preregistration_design": bool(mechanism),
            "private_truth_or_quality_surface_open": False,
            "additional_forward_retry_resume_or_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.80 forward audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    _publish(ROOT / FORWARD_AUDIT, audit)
    print(
        json.dumps(
            {
                "forward_health_go": audit["forward_health_go"],
                "mechanism_go": audit["mechanism_go"],
                "path": str(FORWARD_AUDIT),
            },
            sort_keys=True,
        )
    )
