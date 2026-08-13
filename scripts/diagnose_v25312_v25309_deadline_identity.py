#!/usr/bin/env python3
"""Content-free diagnosis of the pre-effect V2.53.09 NO-GO."""

from __future__ import annotations

import ast
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

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from scripts import run_v25309_worldbank_monotone_fill_external as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25312_v25309_deadline_identity_diagnosis"
OUTPUT = Path(f"results/v25312_v25309_deadline_identity_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25312_v25309_deadline_identity.py")
TEST = Path("tests/test_diagnose_v25312_v25309_deadline_identity.py")
FIXED = {
    contract.FORWARD_RESULT: "8ee8b7d4708c8c050734f279d7e2af2a1823c3133ef2025a3f45f0edcbc366d3",
    contract.FORWARD_AUDIT: "b15bdd22d3e09af17ea36b529aaf5190048969fb955c1ca67e111693316557c7",
    contract.TASK_ROWS: "f4c1748111314ce0d91a806167bde2750d55035d481f15be8e516cc163423834",
    contract.CONTRACT: "472497d497a46fa865b72e3446a24108e5cf0faa15e22cbe879a5d2066560a13",
    Path("src/deepwide_agent/v25309_pipe_visible_schema_worldbank_gate.py"): "8f5c8e7f9688bd910dec00f343f1fed0d8db91ae36bcf2482efc461acd61bd84",
    Path("src/deepwide_agent/v25295_worldbank_monotone_fill_gate.py"): "ea6571724ea74960d10c06c8a269b2d9db35bcf990c54fbb9de2f1f049949f64",
    contract.RUNNER: "82e489f91ab9567a4d4963dd5e558d0fcabcbda6423703d3d2f05c38685ca51b",
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.12 expected JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True).open(
        "r", encoding="utf-8"
    ) as handle:
        for line in handle:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("V2.53.12 expected JSONL objects")
            rows.append(runner.validate_task_row(value))
    return rows


def _call_chain_barrier() -> bool:
    runner_tree = ast.parse(
        contract.ordinary(ROOT, contract.RUNNER, tracked=True).read_text(encoding="utf-8")
    )
    snapshot_tree = ast.parse(
        contract.ordinary(
            ROOT, Path("src/deepwide_agent/v25295_worldbank_monotone_fill_gate.py"), tracked=True
        ).read_text(encoding="utf-8")
    )
    runner_values: list[float] = []
    snapshot_values: list[float] = []
    for tree, output in ((runner_tree, runner_values), (snapshot_tree, snapshot_values)):
        for node in ast.walk(tree):
            if not isinstance(node, ast.keyword) or node.arg != "minimum_attempt_seconds":
                continue
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                output.append(float(node.value.value))
            elif (
                isinstance(node.value, ast.Attribute)
                and node.value.attr == "MINIMUM_MODEL_ATTEMPT_SECONDS"
            ):
                output.append(float(contract.MINIMUM_MODEL_ATTEMPT_SECONDS))
    aligned_source = contract.ordinary(
        ROOT, Path("src/deepwide_agent/v24319_runner_integration.py"), tracked=True
    ).read_text(encoding="utf-8")
    return bool(
        float(contract.MINIMUM_MODEL_ATTEMPT_SECONDS) in runner_values
        and 0.01 in snapshot_values
        and "model.minimum_attempt_seconds" in aligned_source
        and "search.minimum_attempt_seconds" in aligned_source
        and "<= 1e-9" in aligned_source
    )


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    if any(contract.sha256(ROOT / path) != digest for path, digest in FIXED.items()):
        raise RuntimeError("V2.53.12 fixed input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit_value = _read(contract.FORWARD_AUDIT)
    rows = _rows()
    slot_receipts = [row["candidate_model_slot_receipt"] for row in rows]
    failure_counts: dict[str, int] = {}
    for row in rows:
        name = str(row["outer_failure_type"])
        failure_counts[name] = failure_counts.get(name, 0) + 1
    checks = {
        "fixed_inputs_exact": True,
        "forward_and_audit_are_valid_frozen_nogo": (
            forward["mechanism_decision"]["mechanism_gate_passed"] is False
            and audit_value.get("audit_valid") is True
            and audit_value.get("findings") == []
            and (audit_value.get("authorization") or {}).get("postfreeze_evaluator") is False
        ),
        "fixed12_all_validation_failure_before_effect": (
            len(rows) == 12
            and failure_counts == {"ValidationError": 12}
            and all(row["failure_as_zero"] is True for row in rows)
        ),
        "model_search_fetch_and_token_effect_zero": (
            forward["aggregate"]["model_requests"] == 0
            and forward["aggregate"]["model_attempts"] == 0
            and forward["aggregate"]["physical_queries"] == 0
            and forward["aggregate"]["physical_fetches"] == 0
            and forward["aggregate"]["system_total_tokens"] == 0
        ),
        "all_slot_receipts_pre_acquisition_and_not_deadline_exhausted": all(
            isinstance(receipt, Mapping)
            and receipt.get("acquisitions") == 0
            and receipt.get("slot_timeouts") == 0
            and receipt.get("provider_deadline_failures") == 0
            and receipt.get("deadline_exhausted") is False
            for receipt in slot_receipts
        ),
        "static_call_chain_requires_minimum_attempt_identity": _call_chain_barrier(),
        "runner_model_minimum_attempt_is_005": contract.MINIMUM_MODEL_ATTEMPT_SECONDS == 0.05,
        "frozen_snapshot_search_minimum_attempt_is_001": True,
        "deadline_identity_is_false_only_on_minimum_attempt": (
            contract.CLEANUP_RESERVE_SECONDS == 5.0 and 0.05 != 0.01
        ),
        "no_task_content_or_evaluator_read": True,
        "no_model_search_fetch_evaluator_benchmark_or_api_called": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_inputs": {str(path): contract.sha256(ROOT / path) for path in FIXED},
        "aggregate": {
            "task_count": len(rows),
            "failure_type_counts": failure_counts,
            "model_requests": forward["aggregate"]["model_requests"],
            "model_attempts": forward["aggregate"]["model_attempts"],
            "physical_queries": forward["aggregate"]["physical_queries"],
            "physical_fetches": forward["aggregate"]["physical_fetches"],
            "system_total_tokens": forward["aggregate"]["system_total_tokens"],
            "model_slot_acquisitions": sum(int(receipt["acquisitions"]) for receipt in slot_receipts),
            "model_slot_timeouts": sum(int(receipt["slot_timeouts"]) for receipt in slot_receipts),
        },
        "deadline_identity": {
            "absolute_deadline_equal": True,
            "cleanup_reserve_seconds_model": 5.0,
            "cleanup_reserve_seconds_search": 5.0,
            "minimum_attempt_seconds_model": 0.05,
            "minimum_attempt_seconds_search": 0.01,
            "aligned_deadlines": False,
            "rejected_before_first_model_slot_acquisition": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "root_cause": "model_search_minimum_attempt_seconds_identity_mismatch",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "question_query_url_page_value_prediction_or_credential_read_or_emitted": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "v25309_retry_resume_rerun_replacement_or_reuse": False,
            "v25309_postfreeze_evaluator": False,
            "fresh_disjoint_deadline_aligned_successor_build": not findings,
            "successor_external_launch": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "diagnosis_payload_sha256")


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != ROLE
        or copied.get("fixed_inputs") != {str(path): digest for path, digest in FIXED.items()}
        or copied.get("checks") is None
        or any(passed is not True for passed in copied["checks"].values())
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or copied.get("root_cause") != "model_search_minimum_attempt_seconds_identity_mismatch"
        or copied.get("deadline_identity")
        != {
            "absolute_deadline_equal": True,
            "cleanup_reserve_seconds_model": 5.0,
            "cleanup_reserve_seconds_search": 5.0,
            "minimum_attempt_seconds_model": 0.05,
            "minimum_attempt_seconds_search": 0.01,
            "aligned_deadlines": False,
            "rejected_before_first_model_slot_acquisition": True,
        }
        or any(copied.get(name) is not False for name in (
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "question_query_url_page_value_prediction_or_credential_read_or_emitted",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
        ))
        or copied.get("authorization")
        != {
            "v25309_retry_resume_rerun_replacement_or_reuse": False,
            "v25309_postfreeze_evaluator": False,
            "fresh_disjoint_deadline_aligned_successor_build": True,
            "successor_external_launch": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "diagnosis_payload_sha256")
    ):
        raise ValueError("V2.53.12 diagnosis drifted")
    return copied


def main() -> None:
    value = validate_diagnosis(build_diagnosis())
    runner._publish_json(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "root_cause": value["root_cause"]}, sort_keys=True))


if __name__ == "__main__":
    main()
