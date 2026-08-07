#!/usr/bin/env python3
"""Post-forward, pre-quality content-free audit for V2.47.75."""

from __future__ import annotations

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

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
from deepwide_agent.v24775_visible_entity_fair_execution_contract import (  # noqa: E402
    FORWARD_AUDIT,
    FORWARD_RESULT,
    EXECUTION_START,
    OUTPUT_ROOT,
    PARENT_RECEIPT_NAME,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    validate_forward_result,
    validate_prediction_freeze,
    validate_run_summary,
)


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.75 forward audit expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.75 forward audit expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / PROTOCOL)
    summary = validate_run_summary(_read(ROOT / RUN_SUMMARY))
    freeze = validate_prediction_freeze(_read(ROOT / PREDICTION_FREEZE))
    forward = validate_forward_result(_read(ROOT / FORWARD_RESULT))
    if (
        protocol.get("role")
        != "v24775_visible_entity_fair_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or not _sealed(protocol, "protocol_payload_sha256")
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
        or freeze.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or forward.get("prediction_freeze_sha256")
        != sha256(ROOT / PREDICTION_FREEZE)
        or forward.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or forward.get("execution_start_sha256") != sha256(ROOT / EXECUTION_START)
    ):
        raise RuntimeError("V2.47.75 forward audit parent drifted")
    parents = []
    taxonomy: Counter[str] = Counter()
    for ordinal in range(1, SELECTED_COUNT + 1):
        path = ROOT / TASK_ROOT / f"task_{ordinal:04d}" / PARENT_RECEIPT_NAME
        try:
            receipt = validate_parent_receipt(_read(path))
            valid = True
            digest: str | None = sha256(path)
            failure_taxonomy = str(receipt["failure_taxonomy"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            valid = False
            digest = None
            failure_taxonomy = "parent_receipt_missing_or_invalid"
        parents.append(
            {
                "ordinal": ordinal,
                "parent_receipt_sha256": digest,
                "parent_receipt_valid": valid,
                "failure_taxonomy": failure_taxonomy,
            }
        )
        taxonomy[failure_taxonomy] += 1
    mechanism = protocol["mechanism_gate_before_private_truth"]
    checks = {
        "eight_of_eight_terminal_ordinals": len(parents) == SELECTED_COUNT
        and all(item["parent_receipt_valid"] for item in parents),
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
        "scheduler_and_semantic_effect_exactly_zero": summary[
            "scheduler_or_semantic_effect_nonzero_task_count"
        ]
        == mechanism["scheduler_and_semantic_additional_effect_required"],
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
        "minimum_founded_changed_cells": summary["founded_changed_cell_count"]
        >= mechanism["minimum_founded_changed_cell_count"],
        "minimum_country_changed_cells": summary["country_changed_cell_count"]
        >= mechanism["minimum_country_changed_cell_count"],
        "minimum_projection_backed_support_sets": summary[
            "projection_backed_support_set_count"
        ]
        >= mechanism["minimum_projection_backed_support_set_count"],
        "minimum_entity_slots_with_two_requested_aligned_sources": summary[
            "entity_slots_with_two_requested_aligned_sources"
        ]
        >= mechanism[
            "minimum_entity_slots_with_two_requested_aligned_sources"
        ],
        "prediction_freeze_before_private_truth": freeze[
            "all_predictions_terminal_before_private_truth_or_quality_open"
        ]
        and not freeze["private_truth_or_quality_path_opened_or_hashed"],
        "no_resume_retry_skip_or_selective_rerun": not summary[
            "resume_retry_skip_or_selective_rerun"
        ],
    }
    health_names = (
        "eight_of_eight_terminal_ordinals",
        "fixed_denominator_failure_as_zero",
        "all_task_ordinals_submitted_once",
        "parent_taxonomy_matches_run_summary",
        "within_experiment_wall_ceiling",
        "scheduler_and_semantic_effect_exactly_zero",
        "candidate_changes_only_unknown",
        "semantic_safety_contract",
        "nonunknown_cell_change_count_zero",
        "prediction_freeze_before_private_truth",
        "no_resume_retry_skip_or_selective_rerun",
    )
    mechanism_names = tuple(name for name in checks if name not in health_names)
    health_go = all(checks[name] for name in health_names)
    mechanism_go = health_go and all(checks[name] for name in mechanism_names)
    findings = [name for name, passed in checks.items() if not passed]
    value = {
        "artifact_version": 1,
        "role": "v24775_visible_entity_fair_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "parent_receipts": parents,
        "parent_failure_taxonomy_counts": dict(sorted(taxonomy.items())),
        "content_free_metrics": {
            key: summary[key]
            for key in (
                "valid_task_results",
                "projected_failure_tasks",
                "forward_wall_seconds",
                "changed_task_count",
                "changed_cell_count",
                "founded_changed_cell_count",
                "country_changed_cell_count",
                "nonunknown_changed_cell_count",
                "projection_backed_support_set_count",
                "entity_slots_with_two_requested_aligned_sources",
            )
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
    if (
        copied.get("role") != "v24775_visible_entity_fair_forward_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or not all(isinstance(value, bool) for value in checks.values())
        or not isinstance(findings, list)
        or findings != [name for name, passed in checks.items() if not passed]
        or not isinstance(health, bool)
        or not isinstance(mechanism, bool)
        or mechanism is not (health and all(checks.values()))
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
        raise RuntimeError("V2.47.75 forward audit drifted")
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
