#!/usr/bin/env python3
"""Audit the single V2.52.60 forward without evaluator or task content."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from scripts import control_v25260_observed_reliability_external as build_control  # noqa: E402
from scripts import run_v25260_observed_reliability_external as runner  # noqa: E402


SOURCE = Path("scripts/audit_v25263_observed_reliability_forward.py")
TEST = Path("tests/test_audit_v25263_observed_reliability_forward.py")
EXPECTED_FORWARD_COMMIT_PATHS = tuple(
    sorted(
        {
            str(contract.ATTEMPT_CLAIM),
            str(contract.FORWARD_RESULT),
            str(contract.TASK_ROWS),
            str(contract.PREDICTION_FREEZE),
            str(contract.SAFE_PROGRESS),
            *(
                str(contract.MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock")
                for index in range(1, contract.MODEL_SLOT_CAP + 1)
            ),
        }
    )
)
AUDIT_CHECK_NAMES = {
    "protocol_forward_claim_rows_validate",
    "forward_commit_is_single_pushed_fixed_surface_child_of_start",
    "exact_task_denominator_and_order",
    "aggregate_recomputes_exactly",
    "reliability_decision_recomputes_exactly",
    "claim_hash_bound",
    "task_rows_hash_bound",
    "prediction_freeze_valid_and_hash_bound",
    "safe_progress_terminal_and_content_free",
    "stage_and_budget_receipts_have_no_forbidden_keys",
    "completed_predictions_preserve_observed_parent",
    "physical_effect_and_per_task_maxima_within_preregistered_caps",
    "effect_budget_receipt_parity_exact",
    "protected_watchers_unchanged",
    "shared_api_lease_released",
    "forward_or_evaluator_process_absent",
    "entropy_credit_candidate_evaluator_and_220_authority_zero",
}


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.63 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    output: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("V2.52.63 expected JSONL objects")
            output.append(value)
    return output


def _recursive_keys(value: object) -> set[str]:
    output: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            output.add(str(key))
            output.update(_recursive_keys(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            output.update(_recursive_keys(child))
    return output


def forward_commit_boundary(*, head: str | None = None) -> bool:
    current = contract.git(ROOT, "rev-parse", "HEAD") if head is None else head
    target = contract.git(ROOT, "rev-parse", "target/main")
    try:
        parents = contract.git(ROOT, "rev-list", "--parents", "-n", "1", current).split()
        changed = tuple(
            sorted(
                line.strip()
                for line in contract.git(
                    ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current
                ).splitlines()
                if line.strip()
            )
        )
        start = _read(contract.EXECUTION_START)
        start_head = start.get("git_head")
        start_commit = contract.git(ROOT, "rev-parse", f"{current}^")
        start_parents = contract.git(
            ROOT, "rev-list", "--parents", "-n", "1", start_commit
        ).split()
        start_changed = tuple(
            sorted(
                line.strip()
                for line in contract.git(
                    ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", start_commit
                ).splitlines()
                if line.strip()
            )
        )
    except BaseException:
        return False
    return bool(
        current == target
        and len(parents) == 2
        and parents[0] == current
        and parents[1] == start_commit
        and changed == EXPECTED_FORWARD_COMMIT_PATHS
        and len(start_parents) == 2
        and start_parents[0] == start_commit
        and start_parents[1] == start_head
        and start_changed == (str(contract.EXECUTION_START),)
    )


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    if tracked and contract.git(ROOT, "status", "--porcelain"):
        raise RuntimeError("V2.52.63 requires clean worktree")
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=tracked))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT, tracked=tracked))
    claim = runner.validate_attempt_claim(_read(contract.ATTEMPT_CLAIM, tracked=tracked))
    rows = [runner.validate_task_row(row) for row in _read_jsonl(contract.TASK_ROWS, tracked=tracked)]
    aggregate = runner.aggregate_rows(
        rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    decision = runner.reliability_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE, tracked=tracked)
    progress = _read(contract.SAFE_PROGRESS, tracked=tracked)
    forbidden_receipt_keys = {
        "question", "url", "host", "title", "page", "package", "answer",
        "prediction", "category", "question_type", "task_category", "split",
        "ground_truth", "gold", "answer_key", "score", "reward", "message",
        "traceback", "frame", "exception_repr",
    }
    receipts = [
        {
            "stage": row["content_free_stage_receipt"],
            "budget": row["content_free_budget_receipt"],
        }
        for row in rows
    ]
    gate = protocol["reliability_gate"]
    parity = all(
        row["actual_effect_snapshot"]["logical_queries"]
        == row["content_free_budget_receipt"]["query_admitted_count"]
        and row["actual_effect_snapshot"]["fetch_requests"]
        == row["content_free_budget_receipt"]["fetch_admitted_count"]
        and row["actual_effect_snapshot"]["model_logical_requests"]
        == row["content_free_budget_receipt"]["model_admitted_count"]
        for row in rows
    )
    checks = {
        "protocol_forward_claim_rows_validate": True,
        "forward_commit_is_single_pushed_fixed_surface_child_of_start": (
            forward_commit_boundary() if tracked else True
        ),
        "exact_task_denominator_and_order": (
            len(rows) == contract.TASK_COUNT
            and [row["opaque_id"] for row in rows]
            == [task["opaque_id"] for task in contract.task_vector(ROOT)]
        ),
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "reliability_decision_recomputes_exactly": decision == forward["reliability_decision"],
        "claim_hash_bound": (
            forward["attempt_claim_sha256"] == contract.sha256(ROOT / contract.ATTEMPT_CLAIM)
            and claim["execution_start_sha256"] == contract.sha256(ROOT / contract.EXECUTION_START)
        ),
        "task_rows_hash_bound": forward["task_rows_sha256"] == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid_and_hash_bound": (
            contract.sealed(freeze, "freeze_payload_sha256")
            and forward["prediction_freeze_sha256"] == contract.sha256(ROOT / contract.PREDICTION_FREEZE)
            and freeze.get("task_rows_sha256") == contract.sha256(ROOT / contract.TASK_ROWS)
            and freeze.get("selected") == contract.TASK_COUNT
            and freeze.get("terminal") == contract.TASK_COUNT
        ),
        "safe_progress_terminal_and_content_free": (
            contract.sealed(progress, "progress_payload_sha256")
            and progress.get("selected") == contract.TASK_COUNT
            and progress.get("completed") == contract.TASK_COUNT
            and progress.get("unfinished") == 0
            and progress.get("contains_question_package_query_url_page_prediction_or_credential") is False
        ),
        "stage_and_budget_receipts_have_no_forbidden_keys": (
            not _recursive_keys(receipts).intersection(forbidden_receipt_keys)
        ),
        "completed_predictions_preserve_observed_parent": all(
            not row["runtime_completed"]
            or (
                row["prediction"]
                == row["runtime_result"]["predictions"][runner.runtime.parent.CONTROL_ARM]
                == row["runtime_result"]["predictions"][runner.runtime.parent.CANDIDATE_ARM]
            )
            for row in rows
        ),
        "physical_effect_and_per_task_maxima_within_preregistered_caps": (
            aggregate["physical_queries"] <= gate["maximum_physical_queries_total"]
            and aggregate["physical_fetches"] <= gate["maximum_physical_fetches_total"]
            and aggregate["physical_model_forwards"] <= gate["maximum_model_forwards_total"]
            and aggregate["maximum_queries_on_one_task"] <= contract.PHYSICAL_CAPS["queries_per_task"]
            and aggregate["maximum_fetches_on_one_task"] <= contract.PHYSICAL_CAPS["fetches_per_task"]
            and aggregate["maximum_model_forwards_on_one_task"] <= contract.PHYSICAL_CAPS["model_forwards_per_task"]
        ),
        "effect_budget_receipt_parity_exact": parity,
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["execution"]["protected_watchers"],
        "shared_api_lease_released": build_control._lease_inactive(),
        "forward_or_evaluator_process_absent": not build_control._active_conflicts(),
        "entropy_credit_candidate_evaluator_and_220_authority_zero": (
            aggregate["positive_signed_credit_count"] == 0
            and forward["authorization"]["candidate_activation_or_prediction_change"] is False
            and forward["authorization"]["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"] is False
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25263_observed_reliability_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "attempt_claim_sha256": contract.sha256(ROOT / contract.ATTEMPT_CLAIM),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "aggregate": aggregate,
        "reliability_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "evaluator_or_quality_metric_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "postforward_reliability_diagnosis": not findings,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            "retry_resume_skip_replacement_or_selective_rerun": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    aggregate = copied.get("aggregate")
    decision = copied.get("reliability_decision")
    checks = copied.get("checks") or {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "protocol_sha256", "execution_start_sha256", "attempt_claim_sha256",
            "forward_result_sha256", "task_rows_sha256", "prediction_freeze_sha256",
            "aggregate", "reliability_decision", "checks", "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "evaluator_or_quality_metric_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25263_observed_reliability_forward_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name))) is None
            for name in (
                "protocol_sha256", "execution_start_sha256", "attempt_claim_sha256",
                "forward_result_sha256", "task_rows_sha256", "prediction_freeze_sha256",
            )
        )
        or not isinstance(aggregate, Mapping)
        or runner.validate_aggregate(aggregate) != dict(aggregate)
        or decision != runner.reliability_decision(aggregate)
        or set(checks) != AUDIT_CHECK_NAMES
        or any(passed is not True for passed in checks.values())
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("evaluator_or_quality_metric_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("authorization")
        != {
            "postforward_reliability_diagnosis": True,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            "retry_resume_skip_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.63 forward audit drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("forward-audit",))
    parser.parse_args()
    value = build_audit()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    value = validate_audit(value)
    runner._publish_json(ROOT / contract.FORWARD_AUDIT, value)
    print(json.dumps({"path": str(contract.FORWARD_AUDIT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
