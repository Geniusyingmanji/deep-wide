#!/usr/bin/env python3
"""Post-freeze audit and official evaluator for V2.50.30 exact-220.

The mature V2.47.91 32-worker evaluator framework is reused through a narrow
role projection.  Native V2.50.30 forward artifacts are validated first and
remain immutable; only the in-memory barrier shape is projected.
"""

from __future__ import annotations

import json
import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25030_evidence_conditioned_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24791_exact220 as base  # noqa: E402


EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"


def _publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _native_forward_barrier() -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, base._read(ROOT / contract.PROTOCOL))
    forward = base._read(ROOT / contract.FORWARD_RESULT)
    summary = base._read(ROOT / contract.RUN_SUMMARY)
    freeze = base._read(ROOT / contract.PREDICTION_FREEZE)
    prediction_rows = base._read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS)
    result_rows = base._read_jsonl(ROOT / contract.RUNTIME_RESULTS)
    receipt_rows = base._read_jsonl(ROOT / contract.TASK_RECEIPTS)
    tasks = contract.task_vector(ROOT, protocol)
    result_rows = [runtime.validate_result(row) for row in result_rows]
    receipt_rows = [runtime.validate_receipt(row) for row in receipt_rows]
    prediction_hashes = [row.get("prediction_sha256") for row in prediction_rows]
    if (
        forward.get("role") != "v25030_evidence_conditioned_exact220_forward_result"
        or forward.get("protocol_id") != contract.PROTOCOL_ID
        or forward.get("selected") != 220
        or forward.get("terminal_predictions") != 220
        or forward.get("model_generated_tables", -1) + forward.get("fallback_tables", -1) != 220
        or forward.get("all_tasks_within_resource_caps") is not True
        or forward.get("official_evaluator_called") is not False
        or forward.get("retry_resume_skip_or_selective_rerun_launched") is not False
        or forward.get("mapping_gold_category_question_type_split_answer_evaluator_score_reward_read") is not False
        or forward.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or not contract.sealed(forward, "result_payload_sha256")
        or summary.get("role") != "v25030_evidence_conditioned_exact220_run_summary"
        or summary.get("selected") != 220 or summary.get("completed") != 220
        or summary.get("failed") != 0
        or summary.get("model_generated_tables", -1) + summary.get("fallback_tables", -1) != 220
        or summary.get("all_tasks_within_resource_caps") is not True
        or summary.get("official_evaluator_called") is not False
        or summary.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or summary.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or not contract.sealed(summary, "summary_payload_sha256")
        or freeze.get("role") != "v25030_evidence_conditioned_exact220_prediction_freeze"
        or freeze.get("selected") != 220 or freeze.get("terminal") != 220
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("runtime_results_sha256") != contract.sha256(ROOT / contract.RUNTIME_RESULTS)
        or freeze.get("content_free_task_receipts_sha256") != contract.sha256(ROOT / contract.TASK_RECEIPTS)
        or freeze.get("runtime_predictions_sha256") != contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or freeze.get("prediction_hashes_sha256") != contract.payload_sha256(prediction_hashes)
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or len(prediction_rows) != len(result_rows) or len(result_rows) != len(receipt_rows)
        or len(receipt_rows) != 220
        or [row.get("opaque_id") for row in prediction_rows] != [task["opaque_id"] for task in tasks]
        or [row.get("opaque_id") for row in result_rows] != [task["opaque_id"] for task in tasks]
        or any(
            row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
            or not isinstance(row.get("prediction"), str) or not row["prediction"]
            or row.get("prediction_sha256") != result_rows[index]["prediction_sha256"]
            or row.get("prediction") != result_rows[index]["prediction"]
            or receipt_rows[index] != result_rows[index]["content_free_receipt"]
            for index, row in enumerate(prediction_rows)
        )
        or forward.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or forward.get("runtime_results_sha256") != contract.sha256(ROOT / contract.RUNTIME_RESULTS)
    ):
        raise RuntimeError("V2.50.30 frozen forward barrier drifted")
    # Downstream evaluator code only consumes these generic fields and frozen
    # rows.  No native file is rewritten or resealed by this projection.
    return {
        "protocol": protocol,
        "forward": forward,
        "summary": summary,
        "freeze": freeze,
        "runtime_rows": prediction_rows,
    }


def configure() -> None:
    base.contract = contract
    assignments = {
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": contract.EVALUATOR_PROTOCOL,
        "FINAL_RESULT": contract.RESULT,
        "POSTAUDIT": contract.POSTAUDIT,
        "EVALUATOR_ROOT": EVALUATOR_ROOT,
        "PREPARE_ATTESTATION": EVALUATOR_ROOT / "prepare_attestation.json",
        "JOINED_OUTCOMES": EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": EVALUATOR_ROOT / "official_predictions.jsonl",
        "EVALUATOR_RUNS": EVALUATOR_ROOT / "official_eval_workers",
        "EVALUATOR_LOGS": EVALUATOR_ROOT / "logs",
        "MERGED_RESULTS": EVALUATOR_ROOT / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": EVALUATOR_ROOT / "merge_attestation.json",
        "SUMMARY": EVALUATOR_ROOT / "conservative_summary.json",
        "EVALUATOR_OWNER": "v25030_evidence_conditioned_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v25030_exact220_evaluator",
        "CONTROL_FILES": (
            str(contract.FINALIZER),
            str(contract.RUNNER),
            str(contract.CONTROL),
            str(contract.SOURCE),
            str(contract.RUNTIME),
            str(contract.TEST),
            "scripts/finalize_v24791_exact220.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
        "REFERENCES": {
            "v24857_best": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
            "v24969_latest_complete": Path("results/v24969_pacing_aware_replication_result_v1_20260809.json"),
        },
    }
    for name, value in assignments.items():
        setattr(base, name, value)
    base._forward_barrier = _native_forward_barrier
    base._parent_evaluator_contract = _parent_evaluator_contract


def _parent_evaluator_contract() -> dict[str, Any]:
    value = base.copy.deepcopy(
        base._read(ROOT / base.PARENT_EVALUATOR_PROTOCOL).get("evaluator_contract")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.30 parent evaluator contract absent")
    value.pop("opened_only_after_v24635_exact220_prediction_freeze", None)
    value["opened_only_after_v24791_exact220_prediction_freeze"] = True
    value["native_v25030_prediction_freeze_bound_by_role_projection"] = True
    value["mapping_query_answer_or_gold_bytes_opened_or_hashed"] = True
    return value


def _build_native_forward_audit() -> dict[str, Any]:
    barrier = _native_forward_barrier()
    head = contract.git(ROOT, "rev-parse", "HEAD")
    remote = contract.git(ROOT, "rev-parse", "target/main")
    tracked = all(
        base._tracked(path)
        for path in (
            contract.FORWARD_RESULT,
            contract.PREDICTION_FREEZE,
            contract.RUNTIME_PREDICTIONS,
            contract.RUNTIME_RESULTS,
            contract.TASK_RECEIPTS,
            contract.RUN_SUMMARY,
        )
    )
    checks = {
        "exact220_native_barrier_valid": True,
        "forward_artifacts_committed_and_pushed": head == remote and tracked,
        "worktree_clean": contract.git(ROOT, "status", "--porcelain") == "",
        "shared_api_lease_released": base._lease_inactive(),
        "forward_runner_absent": not base._active((contract.RUNNER_MARKER,)),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == barrier["protocol"]["execution"]["protected_watchers"],
        "future_evaluator_surface_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (
                contract.FORWARD_AUDIT,
                contract.EVALUATOR_PROTOCOL,
                contract.RESULT,
                contract.POSTAUDIT,
                EVALUATOR_ROOT,
            )
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v24791_exact220_forward_audit",
            "native_role": "v25030_evidence_conditioned_exact220_forward_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
            "runtime_results_sha256": contract.sha256(ROOT / contract.RUNTIME_RESULTS),
            "content_free_task_receipts_sha256": contract.sha256(ROOT / contract.TASK_RECEIPTS),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "selected": 220,
            "terminal_predictions": 220,
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "authorization": {
                "postfreeze_exact220_evaluator_protocol": not findings,
                "forward_retry_resume_skip_or_rerun": False,
                "selective_evaluation_or_revaluation": False,
                "leaderboard_or_sota": False,
            },
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_audit": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "audit_payload_sha256",
    )


def main() -> None:
    configure()
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "audit":
        value = _build_native_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        _publish_new(ROOT / contract.FORWARD_AUDIT, value)
        print(json.dumps({"path": str(contract.FORWARD_AUDIT), "audit_valid": True, "findings": []}, sort_keys=True))
        return
    sys.argv = [sys.argv[0], args.command]
    base.main()


if __name__ == "__main__":
    main()
