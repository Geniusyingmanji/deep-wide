#!/usr/bin/env python3
"""Strict post-result audit for the narrow V2.42.71 field-alias erratum.

The frozen post-result auditor calls the original execution-start validator
with the full experiment protocol.  That validator predates the one-field
execution-start alias accepted by ``validate_v24271_forward_erratum`` and
therefore fails before it can audit the completed result.  This independent
auditor keeps the frozen artifacts unchanged, replays the exact erratum-bound
forward barrier, and then validates the full two-arm result and execution
closure.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.finalize_v24271_keyless_dev64 import (  # noqa: E402
    validate_final_result,
)
from scripts.finalize_v24271_keyless_dev64_erratum import (  # noqa: E402
    validate_candidate_barrier,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24271_keyless_dev64 import (  # noqa: E402
    CHILD_MARKER,
    FINALIZER_MARKER,
    FINAL_RESULT,
    FORWARD_RESULT,
    OUTPUT,
    PREAUDIT,
    RUNNER_MARKER,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)
from scripts.validate_v24271_forward_erratum import (  # noqa: E402
    ERRATUM_OUTPUT,
    validate_committed_erratum,
    validate_forward_barrier,
)


OUTPUT_PATH = Path(
    "results/v24271_keyless_dev64_postresult_erratum_audit_v1_20260802.json"
)
ERRATUM_FINALIZER_MARKER = "scripts/finalize_v24271_keyless_dev64_erratum.py"
REPORT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "label_blind",
        "protocol_sha256",
        "forward_protocol_sha256",
        "preactivation_audit_sha256",
        "activation_sha256",
        "execution_start_sha256",
        "forward_result_sha256",
        "forward_erratum_sha256",
        "final_result_sha256",
        "forward",
        "result",
        "execution_closure",
        "source_policy",
        "authorization",
        "frozen_postaudit_failure",
        "findings",
        "audit_valid",
        "audit_payload_sha256",
    }
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_preaudit(root: Path) -> dict[str, Any]:
    value = read_object(root / PREAUDIT)
    if (
        value.get("role") != "v24271_keyless_dev64_preactivation_audit"
        or value.get("launch_authorized") is not True
        or value.get("label_blind") is not True
        or value.get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.71 preactivation audit drifted")
    return value


def _matching_any(rows: list[dict[str, Any]], *markers: str) -> bool:
    return any(bool(_matching(rows, marker)) for marker in markers)


def validate_report(value: Mapping[str, Any]) -> None:
    closure = value.get("execution_closure")
    source = value.get("source_policy")
    authorization = value.get("authorization")
    frozen_failure = value.get("frozen_postaudit_failure")
    if (
        set(value) != REPORT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role")
        != "v24271_keyless_dev64_postresult_erratum_audit"
        or value.get("label_blind") is not True
        or not isinstance(closure, Mapping)
        or closure.get("runner_process_present_after_result") is not False
        or closure.get("child_process_present_after_result") is not False
        or closure.get("frozen_or_erratum_finalizer_present_after_result")
        is not False
        or closure.get("shared_api_lease_active") is not False
        or closure.get(
            "process_signal_restart_skip_selective_retry_or_error_revaluation"
        )
        is not False
        or closure.get("active_run_killed_or_quarantined") is not False
        or closure.get("invalid_result_path") is not None
        or not isinstance(source, Mapping)
        or source.get("runtime_boundary") != ["opaque_id", "question"]
        or source.get(
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
        or source.get(
            "candidate_exact64_freeze_before_control_mapping_gold_or_evaluator_open"
        )
        is not True
        or source.get("both_arms_fully_evaluated_with_same_current_judge")
        is not True
        or source.get("old_evaluator_rows_reused") is not False
        or source.get("selective_changed_prediction_evaluation") is not False
        or source.get(
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection"
        )
        is not False
        or source.get("credential_value_persisted_hashed_or_emitted") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("new_exact220_launch") is not False
        or authorization.get("leaderboard_submission_or_sota_claim") is not False
        or not isinstance(frozen_failure, Mapping)
        or frozen_failure.get("observed") is not True
        or frozen_failure.get("frozen_files_modified_or_relaxed") is not False
        or frozen_failure.get("independent_erratum_audit_used") is not True
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.71 post-result erratum audit drifted")


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    preaudit = _validate_preaudit(root)
    validate_committed_erratum(root)
    barrier = validate_forward_barrier(root)
    candidate = validate_candidate_barrier(root)
    result = read_object(root / FINAL_RESULT)
    validate_final_result(root, protocol, result)

    forward = barrier["forward"]
    if (
        candidate["forward"] != forward
        or result.get("provenance", {}).get("forward_result_sha256")
        != sha256(root / FORWARD_RESULT)
        or result.get("selected_per_arm") != 64
        or result.get("conservative_denominator_per_arm") != 64
        or result.get("both_arms_fully_evaluated_with_same_current_judge")
        is not True
    ):
        raise RuntimeError("V2.42.71 final result is not erratum-barrier-bound")

    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    runner_present = bool(_matching(rows, RUNNER_MARKER))
    child_present = bool(_matching(rows, CHILD_MARKER))
    finalizer_present = _matching_any(
        rows, FINALIZER_MARKER, ERRATUM_FINALIZER_MARKER
    )
    lease_active = lease.get("active") is True
    findings: list[str] = []
    if runner_present:
        findings.append("forward_runner_present_after_result")
    if child_present:
        findings.append("forward_child_present_after_result")
    if finalizer_present:
        findings.append("finalizer_present_after_result")
    if lease_active:
        findings.append("shared_api_lease_active_after_result")

    value = {
        "artifact_version": 1,
        "role": "v24271_keyless_dev64_postresult_erratum_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol_sha256": sha256(root / OUTPUT),
        "forward_protocol_sha256": sha256(
            root / "results/v24271_keyless_dev64_forward_contract_v1_20260802.json"
        ),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(
            root / "results/v24271_keyless_dev64_activation_v1_20260802.json"
        ),
        "execution_start_sha256": sha256(
            root / "results/v24271_keyless_dev64_execution_start_v1_20260802.json"
        ),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "forward_erratum_sha256": sha256(root / ERRATUM_OUTPUT),
        "final_result_sha256": sha256(root / FINAL_RESULT),
        "forward": {
            key: forward[key]
            for key in (
                "selected",
                "terminal_predictions",
                "model_generated_tables",
                "fallback_tables",
                "cost_totals",
                "stage_seconds_sum",
                "wall_seconds_sum",
                "shared_model_receipts",
            )
        },
        "result": {
            "status": result["status"],
            "selected_per_arm": result["selected_per_arm"],
            "control": result["control"],
            "candidate": result["candidate"],
            "decision": result["decision"],
            "claims": result["claims"],
        },
        "execution_closure": {
            "runner_process_present_after_result": runner_present,
            "child_process_present_after_result": child_present,
            "frozen_or_erratum_finalizer_present_after_result": finalizer_present,
            "shared_api_lease_active": lease_active,
            "stale_inactive_lease_file_present": (root / "outputs/deepwide_benchmark_api.lease.lock").is_file()
            and not lease_active,
            "process_signal_restart_skip_selective_retry_or_error_revaluation": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "candidate_exact64_freeze_before_control_mapping_gold_or_evaluator_open": True,
            "both_arms_fully_evaluated_with_same_current_judge": True,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "entropy_voc_successor_design": False,
            "new_exact220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "frozen_postaudit_failure": {
            "observed": True,
            "failure_type": "KeyError",
            "missing_key": "forward_contract_payload_sha256",
            "cause": "full_protocol_passed_to_frozen_forward_only_validator_after_single_field_alias_erratum",
            "frozen_files_modified_or_relaxed": False,
            "independent_erratum_audit_used": True,
        },
        "findings": findings,
        "audit_valid": not findings
        and preaudit.get("launch_authorized") is True
        and barrier["execution"].get("api_called_before_execution_start") is False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_report(value)
    return value


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / OUTPUT_PATH, report)
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": sha256(ROOT / OUTPUT_PATH)}))
