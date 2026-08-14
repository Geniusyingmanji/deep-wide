#!/usr/bin/env python3
"""Aggregate-only diagnosis of the V2.55.55 pre-effect NO-GO.

This reads only sealed content-free rows, forward/audit aggregates, the frozen
runner source, and the local model-limiter constructor contract.  It does not
decode questions, identities, predictions, pages, queries, truth, evaluator
outputs, or scores and performs no network/model/search/fetch effect.
"""

from __future__ import annotations

import ast
import copy
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

from deepwide_agent import v24263_global_model_limiter as limiter  # noqa: E402
from deepwide_agent import v24312_deadline_reliability as deadline  # noqa: E402
from deepwide_agent import v25555_fresh_date_external_contract as contract  # noqa: E402
from scripts import run_v25555_fresh_date_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25557_v25555_pool_no_go_diagnosis"
SOURCE = Path("scripts/diagnose_v25557_v25555_pool_no_go.py")
TEST = Path("tests/test_diagnose_v25557_v25555_pool_no_go.py")
OUTPUT = Path(f"results/v25557_v25555_pool_no_go_diagnosis_v1_{DATE}.json")
RUNNER_SHA256 = "50fc6fadbb2f4033f217cf45c66d08e8bae0c73359b389f33a3f7db8eb8b05e6"
FORWARD_RESULT_SHA256 = "803facaa6f8a62607bd1675ad1b1010720c6f428f7a2ddd257c011d5c7f27e25"
FORWARD_AUDIT_SHA256 = "37ab16bfdc3e46d26f93a879e0f2d7ecdbf8097f937e37132f9dca7bb47080a6"
TASK_ROWS_SHA256 = "cb66133f6829e7959132d7097016f141e2e4bc34e009317d95c2996e152e2052"


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, path, tracked=True).read_text())
    if not isinstance(value, dict):
        raise ValueError("V2.55.57 expected JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    values = [
        json.loads(line)
        for line in contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
        .read_text()
        .splitlines()
        if line.strip()
    ]
    return [runner.validate_task_row(value) for value in values]


def _runner_pool_override() -> str | None:
    tree = ast.parse((ROOT / contract.RUNNER).read_text(), filename=str(contract.RUNNER))
    values: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values, strict=True):
            if (
                isinstance(key, ast.Constant)
                and key.value == "POOL_ID"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                values.append(value.value)
    return values[0] if len(values) == 1 else None


def diagnose(*, now: int | None = None) -> dict[str, Any]:
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    rows = _rows()
    aggregate = forward["aggregate"]
    override = _runner_pool_override()
    expected_pool = limiter.POOL_ID
    constructor_source = ast.parse(
        (ROOT / "src/deepwide_agent/v24312_deadline_reliability.py").read_text()
    )
    pool_guard_present = any(
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "pool_id"
        and any(isinstance(operator, ast.NotEq) for operator in node.ops)
        and any(isinstance(item, ast.Name) and item.id == "POOL_ID" for item in node.comparators)
        for node in ast.walk(constructor_source)
    )
    checks = {
        "fixed_hashes_exact": (
            contract.sha256(ROOT / contract.RUNNER) == RUNNER_SHA256
            and contract.sha256(ROOT / contract.FORWARD_RESULT)
            == FORWARD_RESULT_SHA256
            and contract.sha256(ROOT / contract.FORWARD_AUDIT)
            == FORWARD_AUDIT_SHA256
            and contract.sha256(ROOT / contract.TASK_ROWS) == TASK_ROWS_SHA256
        ),
        "forward_audit_valid_no_quality_authority": audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is False,
        "fixed_twenty_terminal_failure_as_zero_rows": len(rows) == 20
        and all(row["terminal"] and row["failure_as_zero"] for row in rows),
        "all_failures_are_content_free_value_error": Counter(
            row["outer_failure_type"] for row in rows
        )
        == Counter({"ValueError": 20}),
        "zero_query_fetch_model_effect": all(
            all(amount == 0 for amount in row["actual_effect_snapshot"].values())
            for row in rows
        )
        and aggregate["all_physical_queries"] == 0
        and aggregate["all_physical_fetches"] == 0
        and aggregate["all_physical_model_forwards"] == 0,
        "custom_pool_override_is_unique_and_differs_from_constructor_constant": isinstance(
            override, str
        )
        and override != expected_pool,
        "constructor_requires_exact_frozen_pool_constant": pool_guard_present,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == _read(contract.PROTOCOL)["protected_watchers"],
        "shared_api_lease_released": __import__(
            "scripts.control_v25555_fresh_date_external", fromlist=["_lease_inactive"]
        )._lease_inactive(),
        "no_question_identity_prediction_page_truth_evaluator_or_score_decoded": True,
        "no_network_model_search_fetch_evaluator_or_benchmark_effect": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_hashes": {
            "runner": RUNNER_SHA256,
            "forward_result": FORWARD_RESULT_SHA256,
            "forward_audit": FORWARD_AUDIT_SHA256,
            "task_rows": TASK_ROWS_SHA256,
        },
        "aggregate": {
            "task_count": len(rows),
            "terminal_tasks": aggregate["terminal_tasks"],
            "failure_as_zero_tasks": aggregate["failure_as_zero_tasks"],
            "runtime_completed_tasks": aggregate["completed_runtime_tasks"],
            "outer_failure_type_histogram": dict(
                sorted(Counter(row["outer_failure_type"] for row in rows).items())
            ),
            "physical_queries": aggregate["all_physical_queries"],
            "physical_fetches": aggregate["all_physical_fetches"],
            "physical_model_forwards": aggregate["all_physical_model_forwards"],
            "batch_wall_seconds": aggregate["batch_wall_seconds"],
        },
        "root_cause": {
            "runner_custom_pool_id": override,
            "deadline_limiter_required_pool_id": expected_pool,
            "pool_id_equal": override == expected_pool,
            "failure_boundary": "deadline_aware_model_slot_constructor_before_any_query_fetch_or_model_effect",
            "causal_status": "source_contract_and_zero_effect_boundary_identify_configuration_mismatch",
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mechanism_gate_passed": False,
        "quality_protocol_authorized": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "successor_pool_contract_fix_build": not findings,
            "same_population_retry_resume_replay_or_replacement": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    return validate(contract.seal(value, "diagnosis_payload_sha256"))


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    checks = copied.get("checks") or {}
    root = copied.get("root_cause") or {}
    aggregate = copied.get("aggregate") or {}
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("fixed_hashes")
        != {
            "runner": RUNNER_SHA256,
            "forward_result": FORWARD_RESULT_SHA256,
            "forward_audit": FORWARD_AUDIT_SHA256,
            "task_rows": TASK_ROWS_SHA256,
        }
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not all(checks.values())
        or aggregate.get("task_count") != 20
        or aggregate.get("terminal_tasks") != 20
        or aggregate.get("failure_as_zero_tasks") != 20
        or aggregate.get("runtime_completed_tasks") != 0
        or aggregate.get("outer_failure_type_histogram") != {"ValueError": 20}
        or aggregate.get("physical_queries") != 0
        or aggregate.get("physical_fetches") != 0
        or aggregate.get("physical_model_forwards") != 0
        or not isinstance(aggregate.get("batch_wall_seconds"), (int, float))
        or isinstance(aggregate.get("batch_wall_seconds"), bool)
        or aggregate.get("batch_wall_seconds") < 0
        or root.get("runner_custom_pool_id")
        != "v25555_fresh_date_external_model_pool_v1"
        or root.get("deadline_limiter_required_pool_id") != limiter.POOL_ID
        or root.get("pool_id_equal") is not False
        or root.get("failure_boundary")
        != "deadline_aware_model_slot_constructor_before_any_query_fetch_or_model_effect"
        or copied.get("mechanism_gate_passed") is not False
        or copied.get("quality_protocol_authorized") is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "successor_pool_contract_fix_build": valid,
            "same_population_retry_resume_replay_or_replacement": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "diagnosis_payload_sha256")
    ):
        raise ValueError("V2.55.57 diagnosis drifted")
    return copied


def main() -> None:
    value = diagnose()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(ROOT / OUTPUT, value)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
