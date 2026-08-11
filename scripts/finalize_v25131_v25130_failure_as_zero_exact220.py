#!/usr/bin/env python3
"""Post-freeze failure-as-zero audit/evaluator adapter for V2.51.30.

V2.51.30 froze 220 terminal predictions, including outer failures projected to
the preregistered fallback table.  Its first finalizer incorrectly required a
causal receipt on those outer-failure rows.  This append-only adapter does not
modify or rerun any forward row.  It separates forward-integrity validity from
the mechanism coverage decision, then evaluates every frozen prediction once
under the preregistered unconditional official-evaluator rule.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24791_exact220 as base  # noqa: E402
from scripts import run_v25130_causal_salience_exact220 as runner  # noqa: E402


SOURCE = Path("scripts/finalize_v25131_v25130_failure_as_zero_exact220.py")
TEST = Path("tests/test_finalize_v25131_v25130_failure_as_zero_exact220.py")
EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"


def _publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _mechanism_decision(summary: dict[str, Any]) -> dict[str, Any]:
    completed = int(summary.get("runtime_completed", -1))
    failures = int(summary.get("failure_as_zero_tasks", -1))
    checks = {
        "fixed_terminal_denominator": summary.get("selected") == 220
        and summary.get("completed") == 220
        and completed + failures == 220,
        "all_runtime_tasks_completed": completed == 220 and failures == 0,
        "all_completed_rows_have_causal_receipts": summary.get(
            "causal_coupling_receipt_valid_tasks"
        )
        == completed,
        "all_220_causal_receipts_present": summary.get(
            "causal_coupling_receipt_valid_tasks"
        )
        == 220,
        "causal_identity_partition_exact_on_completed_rows": summary.get(
            "causal_identity_partition_valid_tasks"
        )
        == completed
        and summary.get("prediction_identity_handoff_tasks", -1)
        + summary.get("retrieval_mechanism_engaged_tasks", -1)
        == completed,
        "zero_unattributable_prediction_changes": summary.get(
            "unattributable_prediction_changed_tasks"
        )
        == 0,
        "zero_identity_handoff_prediction_changes": summary.get(
            "identity_handoff_prediction_changed_tasks"
        )
        == 0,
        "paired_synthesis_receipts_complete_on_completed_rows": summary.get(
            "paired_synthesis_salience_tasks"
        )
        == completed,
        "prompt_lengths_preserved_on_completed_rows": summary.get(
            "prompt_length_preserved_tasks"
        )
        == completed,
        "all_terminal_rows_within_resource_caps": summary.get(
            "all_tasks_within_resource_caps"
        )
        is True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "completed_row_causal_safety_passed": all(
            checks[name]
            for name in (
                "all_completed_rows_have_causal_receipts",
                "causal_identity_partition_exact_on_completed_rows",
                "zero_unattributable_prediction_changes",
                "zero_identity_handoff_prediction_changes",
                "paired_synthesis_receipts_complete_on_completed_rows",
                "prompt_lengths_preserved_on_completed_rows",
            )
        ),
        "postfreeze_official_evaluator_unconditional_on_mechanism_coverage": True,
        "retry_resume_replacement_or_selective_rerun_authorized": False,
    }


def _forward_barrier() -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, base._read(ROOT / contract.PROTOCOL))
    forward = base._read(ROOT / contract.FORWARD_RESULT)
    summary = base._read(ROOT / contract.RUN_SUMMARY)
    freeze = base._read(ROOT / contract.PREDICTION_FREEZE)
    predictions = base._read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS)
    results = [
        runner.validate_task_row(row)
        for row in base._read_jsonl(ROOT / contract.RUNTIME_RESULTS)
    ]
    receipts = base._read_jsonl(ROOT / contract.TASK_RECEIPTS)
    tasks = contract.task_vector(ROOT, protocol)
    hashes = [row.get("prediction_sha256") for row in predictions]
    recomputed = runner._aggregate(
        results, float(summary.get("forward_wall_seconds", 0))
    )
    decision = _mechanism_decision(summary)
    if (
        forward.get("role") != contract.FORWARD_ROLE
        or forward.get("protocol_id") != contract.PROTOCOL_ID
        or forward.get("selected") != 220
        or forward.get("terminal_predictions") != 220
        or forward.get("model_generated_tables", -1)
        + forward.get("fallback_tables", -1)
        != 220
        or forward.get("unattributable_prediction_changed_tasks") != 0
        or forward.get("all_tasks_within_resource_caps") is not True
        or forward.get("official_evaluator_called") is not False
        or forward.get("retry_resume_skip_or_selective_rerun_launched") is not False
        or forward.get(
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read"
        )
        is not False
        or not contract.sealed(forward, "result_payload_sha256")
        or summary != recomputed
        or summary.get("role") != contract.SUMMARY_ROLE
        or summary.get("selected") != 220
        or summary.get("completed") != 220
        or summary.get("runtime_completed", -1)
        + summary.get("failure_as_zero_tasks", -1)
        != 220
        or summary.get("model_generated_tables", -1)
        + summary.get("fallback_tables", -1)
        != 220
        or summary.get("unattributable_prediction_changed_tasks") != 0
        or summary.get("official_evaluator_called") is not False
        or summary.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or not contract.sealed(summary, "summary_payload_sha256")
        or decision["completed_row_causal_safety_passed"] is not True
        or freeze.get("role") != contract.FREEZE_ROLE
        or freeze.get("selected") != 220
        or freeze.get("terminal") != 220
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("runtime_results_sha256")
        != contract.sha256(ROOT / contract.RUNTIME_RESULTS)
        or freeze.get("content_free_task_receipts_sha256")
        != contract.sha256(ROOT / contract.TASK_RECEIPTS)
        or freeze.get("runtime_predictions_sha256")
        != contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256")
        != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or freeze.get("prediction_hashes_sha256")
        != contract.payload_sha256(hashes)
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or len(predictions) != len(results)
        or len(results) != len(receipts)
        or len(receipts) != 220
        or [row.get("opaque_id") for row in predictions]
        != [task["opaque_id"] for task in tasks]
        or [row.get("opaque_id") for row in results]
        != [task["opaque_id"] for task in tasks]
        or any(
            row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            or row.get("prediction")
            != results[index]["predictions"][contract.CANDIDATE_ARM]
            or row.get("prediction_sha256")
            != results[index]["prediction_sha256"][contract.CANDIDATE_ARM]
            or receipts[index].get("opaque_id") != results[index]["opaque_id"]
            or receipts[index].get("content_free_receipt")
            != results[index]["content_free_receipt"]
            or receipts[index].get("causal_coupling_receipt")
            != results[index]["causal_coupling_receipt"]
            or receipts[index].get("stage_failure_accounting")
            != results[index]["stage_failure_accounting"]
            or receipts[index].get("actual_effect_snapshot")
            != results[index]["actual_effect_snapshot"]
            for index, row in enumerate(predictions)
        )
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("run_summary_sha256")
        != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or forward.get("runtime_results_sha256")
        != contract.sha256(ROOT / contract.RUNTIME_RESULTS)
    ):
        raise RuntimeError("V2.51.31 frozen failure-as-zero barrier drifted")
    return {
        "protocol": protocol,
        "forward": forward,
        "summary": summary,
        "freeze": freeze,
        "runtime_rows": predictions,
        "mechanism_decision": decision,
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
        "JOINED_OUTCOMES": EVALUATOR_ROOT
        / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": EVALUATOR_ROOT / "official_predictions.jsonl",
        "EVALUATOR_RUNS": EVALUATOR_ROOT / "official_eval_workers",
        "EVALUATOR_LOGS": EVALUATOR_ROOT / "logs",
        "MERGED_RESULTS": EVALUATOR_ROOT / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": EVALUATOR_ROOT / "merge_attestation.json",
        "SUMMARY": EVALUATOR_ROOT / "conservative_summary.json",
        "EVALUATOR_OWNER": contract.EVALUATOR_OWNER,
        "EVALUATOR_PURPOSE": contract.EVALUATOR_PURPOSE,
        "CONTROL_FILES": (
            str(SOURCE),
            str(TEST),
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
            "v24857_best": contract.BASELINE_RESULT,
            "v24969_latest_complete": contract.LATEST_COMPLETE_RESULT,
        },
    }
    for name, value in assignments.items():
        setattr(base, name, value)
    base._forward_barrier = _forward_barrier


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    barrier = _forward_barrier()
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
        "exact220_terminal_failure_as_zero_barrier_valid": True,
        "forward_artifacts_committed_and_pushed": head == remote and tracked,
        "worktree_clean": contract.git(ROOT, "status", "--porcelain") == "",
        "shared_api_lease_released": base._lease_inactive(),
        "forward_runner_absent": not base._active((contract.RUNNER_MARKER,)),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot()
        == barrier["protocol"]["execution"]["protected_watchers"],
        "completed_row_causal_safety_passed": barrier["mechanism_decision"][
            "completed_row_causal_safety_passed"
        ]
        is True,
        "zero_unattributable_prediction_change": barrier["summary"][
            "unattributable_prediction_changed_tasks"
        ]
        == 0,
        "official_evaluator_is_unconditional_on_mechanism_coverage": barrier[
            "protocol"
        ]["mechanism_gate"]["postfreeze_evaluator_unconditional_on_observed_quality"]
        is True,
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
            "native_role": "v25131_v25130_failure_as_zero_exact220_forward_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "runtime_predictions_sha256": contract.sha256(
                ROOT / contract.RUNTIME_PREDICTIONS
            ),
            "runtime_results_sha256": contract.sha256(
                ROOT / contract.RUNTIME_RESULTS
            ),
            "content_free_task_receipts_sha256": contract.sha256(
                ROOT / contract.TASK_RECEIPTS
            ),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "selected": 220,
            "terminal_predictions": 220,
            "runtime_completed": barrier["summary"]["runtime_completed"],
            "failure_as_zero_tasks": barrier["summary"]["failure_as_zero_tasks"],
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
            "mechanism_decision": barrier["mechanism_decision"],
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
        value = build_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        _publish_new(ROOT / contract.FORWARD_AUDIT, value)
        print(
            json.dumps(
                {
                    "path": str(contract.FORWARD_AUDIT),
                    "audit_valid": True,
                    "mechanism_gate_passed": value["mechanism_decision"][
                        "mechanism_gate_passed"
                    ],
                    "failed_mechanism_checks": value["mechanism_decision"][
                        "failed_checks"
                    ],
                    "findings": [],
                },
                sort_keys=True,
            )
        )
        return
    sys.argv = [sys.argv[0], args.command]
    base.main()


if __name__ == "__main__":
    main()
