#!/usr/bin/env python3
"""Append-only V2.47.48 successor with isolated unittest discovery."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24747_cross_domain_gate as base  # noqa: E402


DATE = "20260806"
OLD_PROTOCOL = Path(f"results/v24747_cross_domain_preregistration_v1_{DATE}.json")
PARENT_FAILURE = Path(
    f"results/v24747_cross_domain_preactivation_failure_v1_{DATE}.json"
)
SCRIPT = Path("scripts/v24748_cross_domain_gate.py")
SCRIPT_TEST = Path("tests/test_v24748_cross_domain_gate.py")


def _configure() -> None:
    base.PROTOCOL_ID = "v24748_cross_domain_generic_binding_gate_v1"
    base.PROTOCOL = Path(
        f"results/v24748_cross_domain_preregistration_v1_{DATE}.json"
    )
    base.PREAUDIT = Path(
        f"results/v24748_cross_domain_preactivation_audit_v1_{DATE}.json"
    )
    base.ACTIVATION = Path(
        f"results/v24748_cross_domain_activation_v1_{DATE}.json"
    )
    base.EXECUTION_START = Path(
        f"results/v24748_cross_domain_execution_start_v1_{DATE}.json"
    )
    base.RESULT = Path(f"results/v24748_cross_domain_result_v1_{DATE}.json")
    base.DECISION = Path(f"results/v24748_cross_domain_decision_v1_{DATE}.json")
    base.POSTAUDIT = Path(
        f"results/v24748_cross_domain_postresult_audit_v1_{DATE}.json"
    )
    base.OUTPUT_ROOT = Path(f"outputs/v24748_cross_domain_gate_v1_{DATE}")
    base.PREDICTIONS = base.OUTPUT_ROOT / "frozen_predictions.jsonl"
    base.PREDICTION_FREEZE = base.OUTPUT_ROOT / "prediction_freeze.json"
    base.RUN_SUMMARY = base.OUTPUT_ROOT / "run_summary.json"
    base.ATTEMPT_CLAIM = base.OUTPUT_ROOT / "attempt_claim.json"
    base.LEASE_OWNER = base.PROTOCOL_ID
    base.RUNNER_MARKER = "scripts/v24748_cross_domain_gate.py run"
    base.SCRIPT = SCRIPT
    base.SCRIPT_TEST = SCRIPT_TEST
    base.EXPECTED_TESTS = 34
    base.TEST_SUITES = (
        (base.BINDER_TEST, 12),
        (base.DESIGN_TEST, 4),
        (base.RUNTIME_TEST, 6),
        (base.HELPER_TEST, 3),
        (Path("tests/test_v24747_cross_domain_gate.py"), 7),
        (SCRIPT_TEST, 2),
    )
    base.CONTROL_SURFACE = (
        base.RUNTIME_SOURCE,
        base.BINDER_SOURCE,
        base.CONTRACT_SOURCE,
        base.HELPER_SOURCE,
        Path("scripts/v24747_cross_domain_gate.py"),
        SCRIPT,
        base.LEASE_SOURCE,
        base.RUNTIME_TEST,
        base.BINDER_TEST,
        base.DESIGN_TEST,
        base.HELPER_TEST,
        Path("tests/test_v24747_cross_domain_gate.py"),
        SCRIPT_TEST,
        base.POPULATION,
        OLD_PROTOCOL,
        PARENT_FAILURE,
    )
    base.FORWARD_AST_SURFACE = (
        base.RUNTIME_SOURCE,
        base.BINDER_SOURCE,
        base.CONTRACT_SOURCE,
        base.HELPER_SOURCE,
        Path("scripts/v24747_cross_domain_gate.py"),
        SCRIPT,
    )


def _run_tests() -> tuple[bool, int, str]:
    """Run exact test files under isolated Python via discovery paths."""

    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    outputs = []
    observed_total = 0
    passed = True
    python = ROOT / ".venv-eval/bin/python"
    for suite, expected in base.TEST_SUITES:
        completed = subprocess.run(
            [
                str(python),
                "-I",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                suite.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
        outputs.append(completed.stdout)
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        observed_total += observed
        passed = passed and completed.returncode == 0 and observed == expected
    output = "\n".join(outputs)
    return (
        passed and observed_total == base.EXPECTED_TESTS,
        observed_total,
        output,
    )


_configure()
base._run_tests = _run_tests


def successor_bindings() -> dict[str, object]:
    failure = base._read(ROOT, PARENT_FAILURE)
    old_protocol = base._read(ROOT, OLD_PROTOCOL)
    old_execution = old_protocol.get("execution", {})
    old_task = old_protocol.get("task_contract", {})
    old_gates = old_protocol.get("gates", {})
    old_protocol_sha256 = base.sha256(ROOT / OLD_PROTOCOL)
    old_source_sha256 = base.sha256(ROOT / "scripts/v24747_cross_domain_gate.py")
    task_vector_sha256 = base.payload_sha256(base._tasks())
    request_vector_sha256 = base.payload_sha256(base._request_vector())
    gate_vector_sha256 = base.payload_sha256(base.REQUIRED_CHECKS)
    budget_vector = {
        "tasks": base.TASK_COUNT,
        "requests": base.REQUEST_COUNT,
        "workers": base.WORKERS,
        "hard_wall_seconds": base.HARD_WALL_SECONDS,
        "socket_timeout_seconds": base.SOCKET_TIMEOUT_SECONDS,
        "experiment_wall_ceiling_seconds": base.EXPERIMENT_WALL_CEILING_SECONDS,
    }
    return {
        "old_protocol_sha256": old_protocol_sha256,
        "parent_failure_sha256": base.sha256(ROOT / PARENT_FAILURE),
        "parent_failure_seal_valid": base._sealed(
            failure, "failure_payload_sha256"
        ),
        "failure_declared_protocol_hash_matches": failure.get("bindings", {}).get(
            "protocol_file_sha256"
        )
        == old_protocol_sha256,
        "failure_declared_source_hash_matches": failure.get("bindings", {}).get(
            "gate_source_sha256"
        )
        == old_source_sha256,
        "old_activation_authorized": failure.get("disposition", {}).get(
            "v24747_protocol_activation_authorized"
        ),
        "task_vector_sha256": task_vector_sha256,
        "request_vector_sha256": request_vector_sha256,
        "gate_vector_sha256": gate_vector_sha256,
        "budget_vector_sha256": base.payload_sha256(budget_vector),
        "task_vector_matches_old_protocol": (
            old_task.get("task_count") == base.TASK_COUNT
            and old_task.get("opaque_id_vector_sha256")
            == base.payload_sha256([task["opaque_id"] for task in base._tasks()])
            and old_task.get("visible_question_vector_sha256")
            == base.payload_sha256([task["question"] for task in base._tasks()])
        ),
        "request_vector_matches_old_protocol": (
            old_execution.get("unique_request_count") == base.REQUEST_COUNT
            and old_execution.get("request_url_vector_sha256")
            == request_vector_sha256
        ),
        "gate_vector_matches_old_protocol": old_gates.get("required_checks")
        == list(base.REQUIRED_CHECKS),
        "budget_vector_matches_old_protocol": all(
            (
                old_task.get("task_count") == budget_vector["tasks"],
                old_execution.get("unique_request_count") == budget_vector["requests"],
                old_execution.get("workers") == budget_vector["workers"],
                old_execution.get("hard_total_wall_seconds")
                == budget_vector["hard_wall_seconds"],
                old_execution.get("socket_timeout_seconds")
                == budget_vector["socket_timeout_seconds"],
                old_execution.get("experiment_wall_ceiling_seconds")
                == budget_vector["experiment_wall_ceiling_seconds"],
            )
        ),
        "only_control_change": "isolated_unittest_discovery_by_exact_filename",
    }


COMMANDS = base.COMMANDS


if __name__ == "__main__":
    bindings = successor_bindings()
    if (
        bindings["parent_failure_seal_valid"] is not True
        or bindings["failure_declared_protocol_hash_matches"] is not True
        or bindings["failure_declared_source_hash_matches"] is not True
        or bindings["old_activation_authorized"] is not False
        or bindings["task_vector_matches_old_protocol"] is not True
        or bindings["request_vector_matches_old_protocol"] is not True
        or bindings["gate_vector_matches_old_protocol"] is not True
        or bindings["budget_vector_matches_old_protocol"] is not True
    ):
        raise RuntimeError("V2.47.48 parent failure binding drifted")
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        raise SystemExit(
            "usage: v24748_cross_domain_gate.py "
            "{protocol|preaudit|activate|start|run|postaudit}"
        )
    COMMANDS[sys.argv[1]]()
