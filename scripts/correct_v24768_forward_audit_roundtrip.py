#!/usr/bin/env python3
"""Append-only correction for the V2.47.65 audit round-trip validator.

The original audit artifact is sealed and scientifically correct, but its
validator compared a findings list in insertion order after JSON publication
with ``sort_keys=True`` reordered the gate-check mapping.  This correction
does not rewrite the executed source, predictions, result, summary, freeze, or
original audit.  It validates the original seal and gate semantics using
order-insensitive findings equality, records the content-free NO-GO metrics,
and grants no rerun, quality, private truth, evaluator, or benchmark authority.
"""

from __future__ import annotations

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

from deepwide_agent import v24765_zero_effect_execution_contract as contract  # noqa: E402
from scripts import audit_v24765_zero_effect_forward as original  # noqa: E402


OUTPUT = Path("results/v24768_v24765_forward_audit_roundtrip_correction_v1_20260807.json")
ORIGINAL_AUDIT = contract.FORWARD_AUDIT


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.68 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.68 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def validate_original_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    checks = copied.get("gate_checks")
    findings = copied.get("findings")
    health = copied.get("forward_health_go")
    mechanism = copied.get("mechanism_go")
    if (
        copied.get("role") != "v24765_zero_effect_forward_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or not checks
        or not all(isinstance(passed, bool) for passed in checks.values())
        or not isinstance(findings, list)
        or any(not isinstance(name, str) for name in findings)
        or sorted(findings) != sorted(name for name, passed in checks.items() if not passed)
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
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.68 original audit semantics drifted")
    return copied


def build_correction(*, now: int | None = None) -> dict[str, Any]:
    audit = validate_original_audit(_read(ROOT / ORIGINAL_AUDIT))
    forward = contract.validate_forward_result(_read(ROOT / contract.FORWARD_RESULT))
    summary = contract.validate_run_summary(_read(ROOT / contract.RUN_SUMMARY))
    freeze = contract.validate_prediction_freeze(_read(ROOT / contract.PREDICTION_FREEZE))
    if (
        audit.get("forward_result_sha256") != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or audit.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or audit.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or freeze.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
    ):
        raise RuntimeError("V2.47.68 frozen parent chain drifted")
    metrics = audit["content_free_metrics"]
    corrected = {
        "artifact_version": 1,
        "role": "v24768_v24765_forward_audit_roundtrip_correction",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "original_forward_audit_sha256": contract.sha256(ROOT / ORIGINAL_AUDIT),
        },
        "correction": {
            "original_audit_payload_seal_valid": True,
            "original_gate_semantics_valid": True,
            "original_validator_failure_reproduced_as_findings_order_only": True,
            "original_artifact_rewritten": False,
            "executed_source_or_prediction_rewritten": False,
            "order_insensitive_findings_validation": True,
        },
        "forward_conclusion": {
            "selected_tasks": summary["selected_tasks"],
            "terminal_arm_predictions": forward["terminal_arm_predictions"],
            "valid_task_results": metrics["valid_task_results"],
            "projected_failure_tasks": metrics["projected_failure_tasks"],
            "forward_wall_seconds": metrics["forward_wall_seconds"],
            "parent_failure_taxonomy_counts": audit[
                "parent_failure_taxonomy_counts"
            ],
            "forward_health_go": audit["forward_health_go"],
            "mechanism_go": audit["mechanism_go"],
            "changed_task_count": metrics["changed_task_count"],
            "changed_cell_count": metrics["changed_cell_count"],
            "page_with_exact_record_count": metrics[
                "page_with_exact_record_count"
            ],
            "ordinary_record_count": metrics["ordinary_record_count"],
            "findings": list(audit["findings"]),
        },
        "source_policy": {
            "prediction_jsonl_opened_or_parsed": False,
            "prediction_jsonl_bytes_hashed_for_freeze_integrity": True,
            "private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "authorization": {
            "original_forward_audit_superseded_for_roundtrip_validation": True,
            "additional_forward_retry_resume_or_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    corrected["correction_payload_sha256"] = contract.payload_sha256(corrected)
    return validate_correction(corrected)


def validate_correction(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    conclusion = copied.get("forward_conclusion", {})
    if (
        copied.get("role")
        != "v24768_v24765_forward_audit_roundtrip_correction"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("correction")
        != {
            "original_audit_payload_seal_valid": True,
            "original_gate_semantics_valid": True,
            "original_validator_failure_reproduced_as_findings_order_only": True,
            "original_artifact_rewritten": False,
            "executed_source_or_prediction_rewritten": False,
            "order_insensitive_findings_validation": True,
        }
        or conclusion.get("selected_tasks") != 8
        or conclusion.get("terminal_arm_predictions") != 16
        or conclusion.get("valid_task_results") != 8
        or conclusion.get("projected_failure_tasks") != 0
        or conclusion.get("forward_health_go") is not True
        or conclusion.get("mechanism_go") is not False
        or conclusion.get("changed_task_count") != 0
        or conclusion.get("changed_cell_count") != 0
        or conclusion.get("page_with_exact_record_count") != 0
        or conclusion.get("ordinary_record_count") != 0
        or copied.get("authorization")
        != {
            "original_forward_audit_superseded_for_roundtrip_validation": True,
            "additional_forward_retry_resume_or_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "correction_payload_sha256")
    ):
        raise RuntimeError("V2.47.68 correction drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    correction = build_correction()
    _publish(ROOT / OUTPUT, correction)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "forward_health_go": correction["forward_conclusion"][
                    "forward_health_go"
                ],
                "mechanism_go": correction["forward_conclusion"]["mechanism_go"],
                "rerun_authorized": correction["authorization"][
                    "additional_forward_retry_resume_or_rerun"
                ],
            },
            sort_keys=True,
        )
    )
