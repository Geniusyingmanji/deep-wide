#!/usr/bin/env python3
"""Project a full-220 result when every candidate prediction equals control.

This is post-freeze evaluator-side analysis.  It opens both frozen prediction
vectors and the already-released V2.42.67 aggregate result.  It makes zero new
evaluator calls and cannot authorize a rerun, re-evaluation, leaderboard, or
SOTA claim.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402


RESULT = Path("results/v24718_v24714_identity_full220_result_v1_20260806.json")
POSTAUDIT = Path(
    "results/v24718_v24714_identity_full220_postresult_audit_v1_20260806.json"
)
CONTROL_RESULT = Path("results/v24267_exact220_result_v1_20260802.json")
CONTROL_EVALUATOR_RESULTS = Path(
    "outputs/v24267_exact220_v1_20260802/evaluator/official_eval/official_eval_results.jsonl"
)
CONTROL_EVALUATOR_SUMMARY = Path(
    "outputs/v24267_exact220_v1_20260802/evaluator/conservative_summary.json"
)
FORWARD_AUDIT = contract.FORWARD_AUDIT


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    return contract.read_object(ROOT / path)


def prediction_identity() -> dict[str, Any]:
    control = contract.read_jsonl(ROOT / contract.CONTROL_PREDICTIONS)
    candidate = contract.read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS)
    if (
        len(control) != contract.SELECTED_COUNT
        or len(candidate) != contract.SELECTED_COUNT
        or len({row.get("opaque_id") for row in control}) != contract.SELECTED_COUNT
        or len({row.get("opaque_id") for row in candidate}) != contract.SELECTED_COUNT
    ):
        raise RuntimeError("V2.47.18 prediction denominator drifted")
    control_by_id = {row["opaque_id"]: row for row in control}
    candidate_by_id = {row["opaque_id"]: row for row in candidate}
    if set(control_by_id) != set(candidate_by_id):
        raise RuntimeError("V2.47.18 prediction ID set drifted")
    same_hash = same_bytes = valid_hash = 0
    for opaque_id, before in control_by_id.items():
        after = candidate_by_id[opaque_id]
        before_prediction = str(before.get("prediction", ""))
        after_prediction = str(after.get("prediction", ""))
        if (
            hashlib.sha256(before_prediction.encode("utf-8")).hexdigest()
            == before.get("prediction_sha256")
            and hashlib.sha256(after_prediction.encode("utf-8")).hexdigest()
            == after.get("prediction_sha256")
        ):
            valid_hash += 1
        same_hash += int(before.get("prediction_sha256") == after.get("prediction_sha256"))
        same_bytes += int(before_prediction == after_prediction)
    return {
        "selected": contract.SELECTED_COUNT,
        "valid_prediction_hash_tasks": valid_hash,
        "same_prediction_hash_tasks": same_hash,
        "same_prediction_bytes_tasks": same_bytes,
        "different_prediction_tasks": contract.SELECTED_COUNT - same_bytes,
        "identity_complete": (
            valid_hash == same_hash == same_bytes == contract.SELECTED_COUNT
        ),
    }


def _control_valid() -> dict[str, Any]:
    value = _read(CONTROL_RESULT)
    metrics = value.get("metrics")
    if (
        value.get("role") != "v24267_exact220_result"
        or value.get("status") != "exact220_single_rollout_complete"
        or value.get("selected") != contract.SELECTED_COUNT
        or value.get("conservative_denominator") != contract.SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or not isinstance(metrics, dict)
        or metrics.get("whole_table_successes") != 7
        or metrics.get("score") != 7 / 220
        or value.get("claims", {}).get("avg_at_4") is not False
        or value.get("claims", {}).get("sota") is not False
        or value.get("provenance", {}).get("official_eval_results_sha256")
        != contract.sha256(ROOT / CONTROL_EVALUATOR_RESULTS)
        or value.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(ROOT / CONTROL_EVALUATOR_SUMMARY)
        or not contract.sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.18 control result drifted")
    return value


def _forward_nogo_valid() -> dict[str, Any]:
    value = _read(FORWARD_AUDIT)
    if (
        value.get("role") != "v24714_sparse_full220_forward_audit"
        or value.get("audit_valid") is not False
        or value.get("authorization")
        != {
            "postfreeze_evaluator_protocol_publication": False,
            "evaluator_execution": False,
            "additional_forward_resume_retry_or_rerun": False,
            "leaderboard_or_sota": False,
        }
        or value.get("observed", {}).get("terminal_predictions") != 220
        or value.get("observed", {}).get("changed_prediction_hash_tasks") != 0
        or value.get("observed", {}).get("unchanged_prediction_hash_tasks") != 220
        or not contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.18 forward no-go audit drifted")
    return value


def build_result(*, now: int | None = None) -> dict[str, Any]:
    if (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or (ROOT / RESULT).exists()
        or (ROOT / RESULT).is_symlink()
        or (ROOT / POSTAUDIT).exists()
        or (ROOT / POSTAUDIT).is_symlink()
    ):
        raise RuntimeError("V2.47.18 requires clean pushed pristine result surface")
    identity = prediction_identity()
    if identity.get("identity_complete") is not True:
        raise RuntimeError("V2.47.18 candidate is not prediction-identical to control")
    control = _control_valid()
    forward_audit = _forward_nogo_valid()
    metrics = json.loads(json.dumps(control["metrics"]))
    value = {
        "artifact_version": 1,
        "role": "v24718_v24714_identity_full220_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "full220_prediction_identity_result_no_new_evaluator_calls",
        "selected": contract.SELECTED_COUNT,
        "conservative_denominator": contract.SELECTED_COUNT,
        "identity": identity,
        "metrics": metrics,
        "delta_vs_v24267_control": {
            "whole_table_successes": 0,
            "score": 0.0,
            "entity_acc": 0.0,
            "f1_by_row": 0.0,
            "f1_by_item": 0.0,
            "column_f1": 0.0,
            "quality_composite": 0.0,
        },
        "mechanism": {
            "route_eligible_tasks": forward_audit["observed"]["route_eligible_tasks"],
            "applied_tasks": forward_audit["observed"]["applied_tasks"],
            "changed_prediction_tasks": 0,
            "worldbank_bulk_download_successes": forward_audit["observed"][
                "bulk_download_successes"
            ],
            "worldbank_bulk_download_failures": 1,
            "forward_wall_seconds": _read(contract.RUN_SUMMARY)["forward_wall_seconds"],
            "mechanism_status": "no_go_transport_fail_closed_identity",
        },
        "provenance": {
            "candidate_runtime_predictions_sha256": contract.sha256(
                ROOT / contract.RUNTIME_PREDICTIONS
            ),
            "candidate_prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "candidate_forward_result_sha256": contract.sha256(
                ROOT / contract.FORWARD_RESULT
            ),
            "candidate_forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
            "control_result_sha256": contract.sha256(ROOT / CONTROL_RESULT),
            "control_runtime_predictions_sha256": contract.sha256(
                ROOT / contract.CONTROL_PREDICTIONS
            ),
            "reused_official_eval_results_sha256": contract.sha256(
                ROOT / CONTROL_EVALUATOR_RESULTS
            ),
            "reused_conservative_summary_sha256": contract.sha256(
                ROOT / CONTROL_EVALUATOR_SUMMARY
            ),
        },
        "evaluation": {
            "new_evaluator_calls": 0,
            "historical_rows_reused": contract.SELECTED_COUNT,
            "reuse_key": ["opaque_id", "prediction_sha256", "prediction_bytes"],
            "reuse_allowed_only_after_candidate_prediction_freeze": True,
            "selective_retry_or_revaluation": False,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_used_by_forward": False,
            "control_result_and_evaluator_hashes_opened_postfreeze_only": True,
            "same_run_evaluator_feedback_used_for_forward": False,
            "exploratory_due_to_v24707_preimplementation_incident": True,
        },
        "claims": {
            "complete_full220_prediction_and_result": True,
            "fresh_full220_search_execution": False,
            "new_evaluator_execution": False,
            "unseen_or_heldout": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
            "benchmark_improvement": False,
            "entropy_credit_validated": False,
        },
        "authorization": {
            "additional_forward_resume_retry_or_rerun": False,
            "additional_evaluator_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    metrics = value.get("metrics", {})
    if (
        value.get("role") != "v24718_v24714_identity_full220_result"
        or value.get("selected") != 220
        or value.get("identity", {}).get("identity_complete") is not True
        or value.get("identity", {}).get("same_prediction_bytes_tasks") != 220
        or metrics.get("whole_table_successes") != 7
        or metrics.get("score") != 7 / 220
        or value.get("evaluation", {}).get("new_evaluator_calls") != 0
        or value.get("evaluation", {}).get("historical_rows_reused") != 220
        or value.get("claims", {}).get("benchmark_improvement") is not False
        or value.get("claims", {}).get("sota") is not False
        or value.get("authorization", {}).get("additional_evaluator_or_revaluation")
        is not False
        or not contract.sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.47.18 identity result drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_result()
    publish(ROOT / RESULT, value)
    print(json.dumps({"path": str(RESULT), "status": value["status"],
                      "whole_table_successes": value["metrics"]["whole_table_successes"],
                      "score": value["metrics"]["score"],
                      "new_evaluator_calls": value["evaluation"]["new_evaluator_calls"]}, sort_keys=True))
