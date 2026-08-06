#!/usr/bin/env python3
"""Content-free post-forward audit for V2.46.51; never opens ROR gold."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24648_unknown_target_structured_runtime import (  # noqa: E402
    ARMS,
    validate_result,
)
from deepwide_agent.v24651_ror_external_contract import (  # noqa: E402
    FORWARD_AUDIT,
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)


LOOKUP_COUNTS = (
    "requested_target_count",
    "returned_result_count",
    "parseable_response_count",
    "unique_exact_response_count",
    "ambiguous_exact_response_count",
    "no_exact_response_count",
    "malformed_response_count",
    "projected_record_count",
)
DISCOVERY_COUNTS = (
    "candidate_evidence_page_count",
    "generic_model_visible_page_count",
    "targeted_structured_page_count",
    "page_with_any_explicit_ror_count",
    "official_api_page_count",
    "entity_page_hit_count",
    "unique_page_pair_hit_count",
    "ambiguous_page_hit_count",
    "unknown_target_unique_pair_count",
    "unknown_target_ambiguous_pair_count",
    "unknown_target_no_pair_count",
    "admitted_replacement_count",
    "nonunknown_target_pair_count",
    "exact_title_identity_pair_count",
    "structured_primary_identity_pair_count",
    "body_only_identity_rejected_pair_count",
)


def read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.51 forward audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.51 forward audit expected object")
    return value


def sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def build() -> dict:
    forward, freeze, summary = (
        read(ROOT / path)
        for path in (FORWARD_RESULT, PREDICTION_FREEZE, RUN_SUMMARY)
    )
    findings: list[str] = []
    if (
        forward.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_sha256")
        or not sealed(freeze, "freeze_sha256")
        or not sealed(summary, "summary_sha256")
    ):
        findings.append("forward_freeze_or_summary_invalid")
    if (
        forward.get("prediction_freeze_sha256") != sha256(ROOT / PREDICTION_FREEZE)
        or freeze.get("predictions_sha256") != sha256(ROOT / PREDICTIONS)
    ):
        findings.append("freeze_binding_drifted")
    rows = [
        json.loads(line)
        for line in (ROOT / PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != SELECTED_COUNT:
        findings.append("denominator_drifted")
    for row in rows:
        for arm in ARMS:
            if row.get("prediction_sha256", {}).get(arm) != hashlib.sha256(
                str(row.get("predictions", {}).get(arm, "")).encode()
            ).hexdigest():
                findings.append("prediction_hash_drifted")
    valid = acquisitions = slot_timeouts = 0
    generic_fetches = targeted_fetches = total_fetches = 0
    lookup = {name: 0 for name in LOOKUP_COUNTS}
    discovery = {name: 0 for name in DISCOVERY_COUNTS}
    for index in range(1, SELECTED_COUNT + 1):
        directory = ROOT / TASK_ROOT / f"task_{index:04d}"
        try:
            result = validate_result(read(directory / "result.json"))
            model = validate_model(
                read(directory / "model_slot_receipt.json"),
                expected_cap=MODEL_SLOT_CAP,
            )
            validate_transport_health(read(directory / "transport_health.json"))
            parent = read(directory / "parent_exit_receipt.json")
            terminal = read(directory / "child_terminal_receipt.json")
            if (
                parent.get("role") != "v24651_content_free_parent_exit_receipt"
                or parent.get("return_code") != 0
                or parent.get("timed_out") is not False
                or parent.get("task_result_valid") is not True
                or terminal.get("stage") != "result_envelope_written"
            ):
                raise ValueError
            receipt = result["receipt"]
            if (
                receipt.get("baseline_precedes_unknown_target_lookup") is not True
                or receipt.get("candidate_is_deterministic_exact_name_registry_baseline")
                is not True
                or receipt.get("quality_cost_pareto_not_equal_effect_causal_ablation")
                is not True
                or receipt.get("positive_task_credit_assigned") is not False
            ):
                raise ValueError
            valid += 1
            acquisitions += int(model["acquisitions"])
            slot_timeouts += int(model["slot_timeouts"])
            generic_fetches += int(receipt["generic_fetch_targets"])
            targeted_fetches += int(receipt["unknown_target_lookup_fetch_targets"])
            total_fetches += int(receipt["admitted_total_fetch_targets"])
            for name in lookup:
                lookup[name] += int(receipt["lookup"][name])
            for name in discovery:
                discovery[name] += int(receipt["discovery"][name])
        except (
            KeyError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            findings.append(f"task_{index:04d}_invalid")
    if valid != SELECTED_COUNT or acquisitions != SELECTED_COUNT * 2 or slot_timeouts != 0:
        findings.append("effect_accounting_drifted")
    if total_fetches != generic_fetches + targeted_fetches or total_fetches > SELECTED_COUNT * 10:
        findings.append("fetch_conservation_drifted")
    mechanism_triggered = discovery["admitted_replacement_count"] > 0
    value = {
        "artifact_version": 1,
        "role": "v24651_unknown_target_structured_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "checks": {
            "terminal_tasks": valid,
            "terminal_arm_predictions": len(rows) * len(ARMS),
            "model_slot_acquisitions": acquisitions,
            "model_slot_timeouts": slot_timeouts,
            "generic_fetch_targets": generic_fetches,
            "unknown_target_lookup_fetch_targets": targeted_fetches,
            "total_fetch_targets": total_fetches,
            "lookup": lookup,
            "discovery": discovery,
            "mechanism_triggered": mechanism_triggered,
            "predictions_frozen_before_gold_open": True,
            "gold_or_provenance_opened_or_hashed_by_audit": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "protected_watchers": protected_watcher_snapshot(),
        "findings": findings,
        "audit_valid": not findings,
        "forward_sha256": sha256(ROOT / FORWARD_RESULT),
        "authorization": {
            "postfreeze_external_evaluator_protocol_design": not findings
            and mechanism_triggered,
            "mechanism_no_go_without_evaluator": not findings
            and not mechanism_triggered,
            "dev64": False,
            "exact220": False,
        },
    }
    value["audit_sha256"] = payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.51 forward audit failed")
    return value


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    result = build()
    publish(ROOT / FORWARD_AUDIT, result)
    print(
        json.dumps(
            {
                "audit_valid": result["audit_valid"],
                "findings": result["findings"],
                "mechanism_triggered": result["checks"]["mechanism_triggered"],
            },
            sort_keys=True,
        )
    )
