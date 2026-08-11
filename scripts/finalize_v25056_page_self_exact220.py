#!/usr/bin/env python3
"""Audit and evaluate frozen V2.50.56 page-self exact-220 predictions."""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25056_page_self_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25030_evidence_conditioned_exact220 as parent  # noqa: E402


EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"
_PARENT_CONFIGURE = parent.configure


def _projection_counts(receipts: list[dict[str, Any]]) -> dict[str, int]:
    fetches = [
        wave_receipt["fetch_receipt"]
        for receipt in receipts
        for wave_receipt in (
            receipt.get("first_wave_receipt"),
            receipt.get("second_wave_receipt"),
        )
        if isinstance(wave_receipt, dict)
    ]
    return {
        "projected_pages": sum(int(item["projected_page_count"]) for item in fetches),
        "mechanism_exposed_pages": sum(
            int(item["mechanism_engaged_page_count"]) for item in fetches
        ),
        "changed_evidence_pages": sum(
            int(item["candidate_evidence_changed_page_count"]) for item in fetches
        ),
        "exact_parent_prefix_handoff_pages": sum(
            int(item["exact_parent_prefix_handoff_page_count"]) for item in fetches
        ),
        "characters_beyond_5k_prefix": sum(
            int(item["input_characters_beyond_parent_prefix"]) for item in fetches
        ),
        "positive_signed_credit_count": sum(
            int(item["positive_signed_credit_count"]) for item in fetches
        ),
    }


def _native_forward_barrier() -> dict[str, Any]:
    protocol = contract.validate_protocol(
        ROOT, parent.base._read(ROOT / contract.PROTOCOL)
    )
    forward = parent.base._read(ROOT / contract.FORWARD_RESULT)
    summary = parent.base._read(ROOT / contract.RUN_SUMMARY)
    freeze = parent.base._read(ROOT / contract.PREDICTION_FREEZE)
    prediction_rows = parent.base._read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS)
    result_rows = parent.base._read_jsonl(ROOT / contract.RUNTIME_RESULTS)
    receipt_rows = parent.base._read_jsonl(ROOT / contract.TASK_RECEIPTS)
    tasks = contract.task_vector(ROOT, protocol)
    result_rows = [runtime.validate_result(row) for row in result_rows]
    receipt_rows = [runtime.validate_receipt(row) for row in receipt_rows]
    prediction_hashes = [row.get("prediction_sha256") for row in prediction_rows]
    projection = _projection_counts(receipt_rows)
    gate = bool(
        projection["mechanism_exposed_pages"] >= 1
        and projection["changed_evidence_pages"]
        == projection["mechanism_exposed_pages"]
        and projection["projected_pages"]
        == projection["mechanism_exposed_pages"]
        + projection["exact_parent_prefix_handoff_pages"]
        and projection["positive_signed_credit_count"] == 0
        and summary.get("all_tasks_within_resource_caps") is True
    )
    if (
        forward.get("role") != contract.FORWARD_ROLE
        or forward.get("protocol_id") != contract.PROTOCOL_ID
        or forward.get("selected") != 220
        or forward.get("terminal_predictions") != 220
        or forward.get("model_generated_tables", -1)
        + forward.get("fallback_tables", -1)
        != 220
        or forward.get("all_tasks_within_resource_caps") is not True
        or forward.get("official_evaluator_called") is not False
        or forward.get("retry_resume_skip_or_selective_rerun_launched") is not False
        or forward.get("mapping_gold_category_question_type_split_answer_evaluator_score_reward_read") is not False
        or forward.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or not contract.sealed(forward, "result_payload_sha256")
        or summary.get("role") != contract.SUMMARY_ROLE
        or summary.get("selected") != 220
        or summary.get("completed") != 220
        or summary.get("failed") != 0
        or summary.get("model_generated_tables", -1)
        + summary.get("fallback_tables", -1)
        != 220
        or summary.get("all_tasks_within_resource_caps") is not True
        or summary.get("official_evaluator_called") is not False
        or summary.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or summary.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or summary.get("page_self_projection") != projection
        or summary.get("page_self_mechanism_gate_passed") is not gate
        or not contract.sealed(summary, "summary_payload_sha256")
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
        != contract.payload_sha256(prediction_hashes)
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or len(prediction_rows) != len(result_rows)
        or len(result_rows) != len(receipt_rows)
        or len(receipt_rows) != 220
        or [row.get("opaque_id") for row in prediction_rows]
        != [task["opaque_id"] for task in tasks]
        or [row.get("opaque_id") for row in result_rows]
        != [task["opaque_id"] for task in tasks]
        or any(
            row.get("status") != "completed"
            or row.get("label_blind") is not True
            or row.get("mapping_gold_category_question_type_split_evaluator_score_read")
            is not False
            or not isinstance(row.get("prediction"), str)
            or not row["prediction"]
            or row.get("prediction_sha256")
            != result_rows[index]["prediction_sha256"]
            or row.get("prediction") != result_rows[index]["prediction"]
            or receipt_rows[index] != result_rows[index]["content_free_receipt"]
            for index, row in enumerate(prediction_rows)
        )
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("run_summary_sha256")
        != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or forward.get("runtime_results_sha256")
        != contract.sha256(ROOT / contract.RUNTIME_RESULTS)
    ):
        raise RuntimeError("V2.50.56 frozen forward barrier drifted")
    return {
        "protocol": protocol,
        "forward": forward,
        "summary": summary,
        "freeze": freeze,
        "runtime_rows": prediction_rows,
    }


def _parent_evaluator_contract() -> dict[str, Any]:
    value = copy.deepcopy(
        parent.base._read(ROOT / parent.base.PARENT_EVALUATOR_PROTOCOL).get(
            "evaluator_contract"
        )
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.56 parent evaluator contract absent")
    value.pop("opened_only_after_v24635_exact220_prediction_freeze", None)
    value["opened_only_after_v24791_exact220_prediction_freeze"] = True
    value[contract.EVALUATOR_FREEZE_BINDING_FIELD] = True
    value["mapping_query_answer_or_gold_bytes_opened_or_hashed"] = True
    value["evaluator_unconditional_on_page_self_mechanism_gate"] = True
    return value


def _build_native_forward_audit() -> dict[str, Any]:
    barrier = _native_forward_barrier()
    head = contract.git(ROOT, "rev-parse", "HEAD")
    remote = contract.git(ROOT, "rev-parse", "target/main")
    tracked = all(
        parent.base._tracked(path)
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
        "fixed220_evaluator_unconditional_on_mechanism_gate": True,
        "forward_artifacts_committed_and_pushed": head == remote and tracked,
        "worktree_clean": contract.git(ROOT, "status", "--porcelain") == "",
        "shared_api_lease_released": parent.base._lease_inactive(),
        "forward_runner_absent": not parent.base._active((contract.RUNNER_MARKER,)),
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
            "native_role": contract.FORWARD_AUDIT_NATIVE_ROLE,
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
            "page_self_projection": barrier["summary"]["page_self_projection"],
            "page_self_mechanism_gate_passed": barrier["summary"][
                "page_self_mechanism_gate_passed"
            ],
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


def configure() -> None:
    parent.contract = contract
    parent.runtime = runtime
    parent.EVALUATOR_ROOT = EVALUATOR_ROOT
    parent._native_forward_barrier = _native_forward_barrier
    parent._parent_evaluator_contract = _parent_evaluator_contract
    _PARENT_CONFIGURE()
    parent.base.EVALUATOR_OWNER = contract.EVALUATOR_OWNER
    parent.base.EVALUATOR_PURPOSE = contract.EVALUATOR_PURPOSE
    parent.base.REFERENCES = {
        "v24857_best": Path(
            "results/v24857_pacing_aware_exact220_result_v1_20260808.json"
        ),
        "v25030_latest_complete": Path(
            "results/v25030_evidence_conditioned_exact220_result_v1_20260810.json"
        ),
    }
    parent.base.CONTROL_FILES = (
        str(contract.FINALIZER),
        str(contract.RUNNER),
        str(contract.CONTROL),
        str(contract.SOURCE),
        str(contract.RUNTIME),
        str(contract.FETCH),
        str(contract.FETCH_HELPER),
        str(contract.REPRESENTATION),
        str(contract.TEST),
        "scripts/finalize_v24791_exact220.py",
        "scripts/run_official_eval_local.py",
        "scripts/finalize_v24287_exact220.py",
        "scripts/finalize_fullset_rollout.py",
        "scripts/deepwide_api_lease.py",
    )
    parent.base._forward_barrier = _native_forward_barrier
    parent.base._parent_evaluator_contract = _parent_evaluator_contract


def main() -> None:
    parent.configure = configure
    parent._build_native_forward_audit = _build_native_forward_audit
    parent.main()


if __name__ == "__main__":
    main()
