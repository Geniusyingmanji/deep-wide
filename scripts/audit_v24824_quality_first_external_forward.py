#!/usr/bin/env python3
"""Content-free post-freeze audit for V2.48.24."""

from __future__ import annotations

import hashlib
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

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24819_quality_first_controller import ARMS  # noqa: E402
from deepwide_agent.v24823_quality_first_accounting import (  # noqa: E402
    validate_envelope,
)


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.48.24 audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.24 audit expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def build(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, read(ROOT / contract.PROTOCOL))
    forward = read(ROOT / contract.FORWARD_RESULT)
    freeze = read(ROOT / contract.PREDICTION_FREEZE)
    summary = read(ROOT / contract.RUN_SUMMARY)
    findings: list[str] = []
    if (
        forward.get("role") != "v24824_forward_result"
        or not sealed(forward, "result_payload_sha256")
        or not sealed(freeze, "freeze_payload_sha256")
        or not sealed(summary, "summary_payload_sha256")
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or freeze.get("predictions_sha256")
        != contract.sha256(ROOT / contract.PREDICTIONS)
        or freeze.get("private_population_gold_or_evaluator_opened_or_hashed")
        is not False
    ):
        findings.append("forward_freeze_or_summary_invalid")
    rows = [
        json.loads(line)
        for line in (ROOT / contract.PREDICTIONS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(rows) != contract.SELECTED_COUNT:
        findings.append("prediction_denominator_drifted")
    totals: Counter[str] = Counter()
    terminal: Counter[str] = Counter()
    decisions: Counter[str] = Counter()
    valid = 0
    adaptive_equals_fixed = 0
    mandatory_override = 0
    cost_stops = 0
    signed_credit = 0
    for row in rows:
        predictions = row.get("predictions") if isinstance(row, Mapping) else None
        if not isinstance(predictions, Mapping) or set(predictions) != set(ARMS):
            findings.append("prediction_arm_schema_drifted")
            continue
        for arm in ARMS:
            if row.get("prediction_sha256", {}).get(arm) != hashlib.sha256(
                str(predictions[arm]).encode()
            ).hexdigest():
                findings.append("prediction_hash_drifted")
        if predictions["coverage_risk_adaptive"] == predictions["fixed_full_budget"]:
            adaptive_equals_fixed += 1
    for position in range(1, contract.SELECTED_COUNT + 1):
        directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
        try:
            child = validate_child_receipt(
                read(directory / "child_terminal_receipt.json")
            )
            model = validate_model(
                read(directory / "model_slot_receipt.json"),
                expected_cap=contract.MODEL_SLOT_CAP,
            )
            health = validate_transport_health(
                read(directory / "transport_health.json")
            )
            terminal[str(child["exception_type"] or "none")] += 1
            totals["terminal_receipts"] += 1
            totals["model_slot_acquisitions"] += model["acquisitions"]
            totals["model_slot_timeouts"] += model["slot_timeouts"]
            totals["hosted_search_attempts"] += health["hosted_search_attempts"]
            totals["hard_fetch_helper_calls"] += health["hard_fetch_helper_calls"]
            totals["fetch_deadline_rejections"] += health[
                "fetch_deadline_rejections"
            ]
            if child["result_envelope_written"]:
                envelope = validate_envelope(read(directory / "result.json"))
                accounting = envelope["effect_accounting"]
                decision = envelope["result"]["adaptive_decision"]
                totals["logical_model_calls"] += accounting["logical_model_calls"]
                totals["logical_search_queries"] += accounting[
                    "logical_search_queries"
                ]
                totals["provider_response_calls"] += accounting[
                    "provider_response_calls"
                ]
                totals["provider_attempts"] += accounting["provider_attempts"]
                totals["fetch_calls"] += accounting["fetch_calls"]
                decisions[str(decision["decision"])] += 1
                mandatory_override += int(
                    decision["mandatory_coverage_override_applied"] is True
                )
                cost_stops += int(
                    decision["cost_sensitive_stopping_applied"] is True
                )
                signed_credit += int(
                    decision["entropy_assigns_signed_credit"] is True
                    or decision[
                        "terminal_utility_signed_credit_observed_for_this_action"
                    ]
                    is True
                )
                valid += 1
        except (
            KeyError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            totals["invalid_task_artifacts"] += 1
    checks = {
        "prediction_denominator_exact": len(rows) == contract.SELECTED_COUNT,
        "all_terminal_receipts_valid": totals["terminal_receipts"]
        == contract.SELECTED_COUNT
        and totals["invalid_task_artifacts"] == 0,
        "valid_results_reconcile_summary": valid
        == summary.get("valid_task_results")
        and contract.SELECTED_COUNT - valid
        == summary.get("projected_failure_tasks"),
        "all_results_valid": valid == contract.SELECTED_COUNT,
        "model_effects_complete": totals["logical_model_calls"]
        == 2 * contract.SELECTED_COUNT
        and totals["model_slot_acquisitions"] == 2 * contract.SELECTED_COUNT
        and totals["model_slot_timeouts"] == 0,
        "logical_search_queries_complete": totals["logical_search_queries"]
        == 4 * contract.SELECTED_COUNT,
        "provider_batch_calls_not_forced_equal_logical_queries": totals[
            "provider_response_calls"
        ]
        >= contract.SELECTED_COUNT
        and totals["provider_response_calls"] <= totals["logical_search_queries"],
        "provider_attempts_cover_responses": totals["provider_attempts"]
        >= totals["provider_response_calls"],
        "fetch_effects_complete": totals["fetch_calls"]
        == 10 * contract.SELECTED_COUNT
        and totals["hard_fetch_helper_calls"]
        + totals["fetch_deadline_rejections"]
        == 10 * contract.SELECTED_COUNT,
        "quality_first_expand_exact32": decisions == {"expand": 32},
        "mandatory_coverage_override_exact32": mandatory_override == 32,
        "cost_sensitive_stop_zero": cost_stops == 0,
        "adaptive_prediction_equals_fixed_full_exact32": adaptive_equals_fixed
        == 32
        and summary.get("adaptive_prediction_equals_fixed_full_count") == 32,
        "entropy_or_terminal_signed_credit_zero": signed_credit == 0,
    }
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "counts": {key: int(number) for key, number in sorted(totals.items())},
        "adaptive_decision_counts": dict(sorted(decisions.items())),
        "mandatory_coverage_override_count": mandatory_override,
        "cost_sensitive_stopping_count": cost_stops,
        "adaptive_prediction_equals_fixed_full_count": adaptive_equals_fixed,
        "entropy_or_terminal_signed_credit_count": signed_credit,
        "terminal_exception_counts": dict(sorted(terminal.items())),
        "checks": checks,
        "findings": sorted(name for name, okay in checks.items() if not okay),
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "protected_watchers": contract.protected_watcher_snapshot(),
        "authorization": {
            "postfreeze_external_evaluator_protocol": all(checks.values()),
            "same_population_retry_resume_or_rerun": False,
            "evaluator_execution": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if value["findings"]:
        raise RuntimeError(f"V2.48.24 forward audit failed: {value['findings']}")
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
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
    artifact = build()
    publish(ROOT / contract.FORWARD_AUDIT, artifact)
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_AUDIT),
                "audit_valid": artifact["audit_valid"],
                "counts": artifact["counts"],
                "decisions": artifact["adaptive_decision_counts"],
            },
            sort_keys=True,
        )
    )
