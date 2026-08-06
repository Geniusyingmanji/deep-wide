#!/usr/bin/env python3
"""Post-freeze evaluator and fixed-denominator decision for V2.46.79."""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import audit_v24683_v24679_schema_dev64_forward as forward_audit  # noqa: E402
from scripts import finalize_v24657_unknown_cell_targeted_dev64 as engine  # noqa: E402
from scripts import v24679_schema_dev64_control as forward_control  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
)


DATE = "20260806"
EVALUATOR_GATE = Path(f"results/v24684_schema_dev64_evaluator_gate_v1_{DATE}.json")
EVALUATOR_START = Path(
    f"results/v24684_schema_dev64_evaluator_start_v1_{DATE}.json"
)
FINAL_RESULT = Path(f"results/v24679_schema_dev64_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24679_schema_dev64_postresult_audit_v1_{DATE}.json")
EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"
PARENT_EVALUATOR_PROTOCOL = Path(
    "results/v24287_exact220_preregistration_v1_20260803.json"
)
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
EVALUATOR_WORKERS_PER_ARM = 8
TOTAL_EVALUATOR_WORKERS = 16
EVALUATOR_OWNER = "v24684_v24679_schema_dev64_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed64_paired_schema_dev64_evaluator"
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
BOOTSTRAP_SEED = 24684
BOOTSTRAP_RESAMPLES = 10_000
ARM_ROOTS = {arm: EVALUATOR_ROOT / arm for arm in contract.ARMS}
JOINED = {
    arm: ARM_ROOTS[arm] / "terminal_outcomes_evaluator_joined.jsonl"
    for arm in contract.ARMS
}
OFFICIAL = {
    arm: ARM_ROOTS[arm] / "official_predictions.jsonl" for arm in contract.ARMS
}
PREPARE = {arm: ARM_ROOTS[arm] / "prepare_attestation.json" for arm in contract.ARMS}
RUNS = {arm: ARM_ROOTS[arm] / "official_eval_workers" for arm in contract.ARMS}
LOGS = {arm: ARM_ROOTS[arm] / "logs" for arm in contract.ARMS}
MERGED = {
    arm: ARM_ROOTS[arm] / "official_eval_results.jsonl" for arm in contract.ARMS
}
MERGE = {arm: ARM_ROOTS[arm] / "merge_attestation.json" for arm in contract.ARMS}
SUMMARY = {
    arm: ARM_ROOTS[arm] / "conservative_summary.json" for arm in contract.ARMS
}
CONTROL_FILES = (
    "src/deepwide_agent/v24679_schema_dev64_contract.py",
    "scripts/audit_v24495_targeted_conversion_projection_build.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/audit_v24683_v24679_schema_dev64_forward.py",
    "scripts/v24679_schema_dev64_control.py",
    "scripts/finalize_v24684_v24679_schema_dev64.py",
    "tests/test_finalize_v24684_v24679_schema_dev64.py",
    "scripts/finalize_v24657_unknown_cell_targeted_dev64.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/deepwide_api_lease.py",
    str(PARENT_EVALUATOR_PROTOCOL),
    str(contract.FORWARD_AUDIT),
)
TEST_SUITES = (
    ("test_v24679_schema_dev64.py", 9),
    ("test_audit_v24683_v24679_schema_dev64_forward.py", 5),
    ("test_v24657_unknown_cell_targeted_dev64.py", 12),
    ("test_finalize_v24684_v24679_schema_dev64.py", 11),
)
EXPECTED_TEST_COUNT = 37
GATE_AUTHORIZATION = {
    "evaluator_start_design": True,
    "evaluator_execution": False,
    "additional_forward_resume_retry_or_rerun": False,
    "exact220": False,
    "leaderboard_or_sota": False,
}
START_AUTHORIZATION = {
    "one_postfreeze_fixed64_both_arm_evaluator_execution": True,
    "additional_evaluator_retry_or_revaluation": False,
    "additional_forward_resume_retry_or_rerun": False,
    "exact220": False,
    "leaderboard_or_sota": False,
}


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def _read(path: Path) -> dict[str, Any]:
    return contract.read_object(ROOT / path)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        marker in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "finalize_v24684" not in line
    )


def _port_listening() -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
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


def _run_tests() -> list[dict[str, Any]]:
    import re

    output: list[dict[str, Any]] = []
    for filename, expected in TEST_SUITES:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                filename,
            ],
            cwd=ROOT,
            env={
                "HOME": os.environ.get("HOME", str(Path.home())),
                "USER": os.environ.get("USER", "azureuser"),
                "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        output.append(
            {
                "file": filename,
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": completed.returncode == 0 and observed == expected,
            }
        )
    return output


def _parent_evaluator_contract() -> dict[str, Any]:
    parent = _read(PARENT_EVALUATOR_PROTOCOL)
    unsigned = dict(parent)
    seal = unsigned.pop("protocol_payload_sha256", None)
    evaluator = parent.get("evaluator_contract")
    if (
        parent.get("role") != "v24287_exact220_preregistration"
        or not isinstance(evaluator, Mapping)
        or evaluator.get("mapping_query_answer_or_gold_bytes_opened_or_hashed")
        is not False
        or evaluator.get("mapping", {}).get("path") != str(MAPPING_PATH)
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.84 evaluator identity parent drifted")
    return json.loads(json.dumps(evaluator))


def validate_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    del root
    forward_contract = contract.validate_forward_contract(ROOT)
    forward_control.validate_protocol(ROOT)
    audit = _read(contract.FORWARD_AUDIT)
    forward_audit.validate_audit(audit)
    forward = _read(contract.FORWARD_RESULT)
    pair = _read(contract.PAIR_SUMMARY)
    selected = list(forward_contract["task_contract"]["selected_opaque_ids"])
    arms: dict[str, Any] = {}
    for arm in contract.ARMS:
        rows, summary, freeze = forward_audit._validate_freeze(arm, selected)
        arms[arm] = {
            "rows": rows,
            "summary": summary,
            "freeze": freeze,
            "sources": {
                "forward_contract_sha256": contract.sha256(
                    ROOT / contract.FORWARD_CONTRACT
                ),
                "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
                "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
                "prediction_freeze_sha256": contract.sha256(
                    ROOT / contract.PREDICTION_FREEZE[arm]
                ),
                "runtime_predictions_sha256": contract.sha256(
                    ROOT / contract.RUNTIME_PREDICTIONS[arm]
                ),
                "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY[arm]),
            },
        }
    changed = sum(
        left["prediction_sha256"] != right["prediction_sha256"]
        for left, right in zip(
            arms["baseline"]["rows"], arms["candidate"]["rows"], strict=True
        )
    )
    if (
        audit.get("reliability_gate", {}).get("passed") is not True
        or audit.get("authorization", {}).get("postfreeze_evaluator_gate_design")
        is not True
        or forward.get("changed_candidate_tasks") != changed
        or changed != 7
        or pair.get("changed_candidate_tasks") != changed
        or pair.get("baseline_runtime_failures") != 0
        or pair.get("candidate_runtime_failures") != 0
        or forward.get("both_arms_exact64_before_mapping_gold_or_evaluator_open")
        is not True
        or forward.get("official_evaluator_called") is not False
    ):
        raise RuntimeError("V2.46.84 forward barrier drifted")
    return {
        "contract": forward_contract,
        "audit": audit,
        "forward": forward,
        "pair": pair,
        "ids": selected,
        "arms": arms,
        "changed": changed,
        "identity": contract.SELECTED_COUNT - changed,
    }


def build_evaluator_gate(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_pristine: bool = True,
    run_tests: bool = True,
) -> dict[str, Any]:
    barrier = validate_forward_barrier()
    evaluator = _parent_evaluator_contract()
    source_manifest = {
        relative: contract.sha256(ROOT / relative) for relative in CONTROL_FILES
    }
    tests = _run_tests() if run_tests else []
    test_count = sum(item["observed_test_count"] for item in tests)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = _tracked(contract.FORWARD_RESULT) and _tracked(contract.FORWARD_AUDIT)
    lease = lease_observation(ROOT, Path("/proc"))
    active = any(
        _active(marker)
        for marker in (contract.RUNNER_MARKER, contract.CHILD_MARKER, str(EVALUATOR_ROOT))
    )
    future = (EVALUATOR_GATE, EVALUATOR_START, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
    pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in future
    )
    proxy = _port_listening()
    watchers = contract.protected_watcher_snapshot()
    secrets = [
        relative
        for relative in CONTROL_FILES
        if common.SECRET.search((ROOT / relative).read_text(encoding="utf-8"))
    ]
    findings: list[str] = []
    if require_clean and head != remote:
        findings.append("evaluator_package_commit_not_pushed")
    if require_clean and not clean:
        findings.append("worktree_not_clean")
    if not tracked:
        findings.append("forward_result_or_audit_not_tracked")
    if require_pristine and not pristine:
        findings.append("evaluator_surface_not_pristine")
    if run_tests and (
        any(not item["passed"] for item in tests) or test_count != EXPECTED_TEST_COUNT
    ):
        findings.append("evaluator_package_tests_failed_or_count_drifted")
    if secrets:
        findings.append("credential_literal_in_evaluator_control_surface")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("forward_or_evaluator_process_active")
    if not proxy:
        findings.append("keyless_proxy_not_listening")
    if watchers != barrier["contract"]["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24684_schema_dev64_evaluator_gate",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "evaluator_gate_go" if not findings else "evaluator_gate_no_go",
        "findings": findings,
        "passed": not findings,
        "forward_barrier": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "prediction_freeze_sha256": {
                arm: contract.sha256(ROOT / contract.PREDICTION_FREEZE[arm])
                for arm in contract.ARMS
            },
            "selected_per_arm": contract.SELECTED_COUNT,
            "changed_candidate_predictions": barrier["changed"],
            "identity_candidate_predictions": barrier["identity"],
            "both_arm_predictions_frozen_before_evaluator_resource_open": True,
        },
        "evaluation_contract": {
            "fixed_denominator_per_arm": contract.SELECTED_COUNT,
            "baseline_provider_evaluations": contract.SELECTED_COUNT,
            "candidate_changed_provider_evaluations": barrier["changed"],
            "candidate_identity_judgments_reused_from_baseline": barrier["identity"],
            "unique_provider_evaluations": contract.SELECTED_COUNT + barrier["changed"],
            "evaluator_workers_per_arm_maximum": EVALUATOR_WORKERS_PER_ARM,
            "total_evaluator_workers_maximum": TOTAL_EVALUATOR_WORKERS,
            "routing_keys": ["opaque_id", "prediction_sha256", "instance_id"],
            "mapping_gold_category_question_type_split_score_or_reward_used_for_routing": False,
            "worker_error_rows_terminal_failure_as_zero": True,
            "no_resume_selective_retry_revaluation_or_prediction_selection": True,
        },
        "decision_contract": dict(forward_control.DECISION_CONTRACT),
        "evaluator_contract": evaluator,
        "evaluator_identity_parent": {
            "path": str(PARENT_EVALUATOR_PROTOCOL),
            "sha256": contract.sha256(ROOT / PARENT_EVALUATOR_PROTOCOL),
        },
        "source_manifest": source_manifest,
        "source_manifest_sha256": contract.payload_sha256(source_manifest),
        "tests": {
            "suites": tests,
            "test_count": test_count,
            "passed": (not run_tests)
            or (
                all(item["passed"] for item in tests)
                and test_count == EXPECTED_TEST_COUNT
            ),
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "runtime_state": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "forward_result_and_audit_tracked": tracked,
            "shared_api_lease_active": lease.get("active"),
            "forward_or_evaluator_process_active": active,
            "evaluator_surface_pristine": pristine,
            "protected_watchers": watchers,
            "keyless_proxy_listening_without_request": proxy,
        },
        "source_policy": {
            "mapping_query_answer_gold_evaluator_bytes_opened_or_hashed_by_gate": False,
            "official_evaluator_called_by_gate": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "claims": {
            "development_population_not_unseen": True,
            "benchmark_score_available_before_evaluator": False,
            "public_full220_result": False,
            "sota": False,
        },
        "authorization": {
            **GATE_AUTHORIZATION,
            "evaluator_start_design": not findings,
        },
    }
    value["gate_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_evaluator_gate(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    gate = dict(value) if value is not None else _read(EVALUATOR_GATE)
    barrier = validate_forward_barrier()
    manifest = gate.get("source_manifest")
    if (
        gate.get("role") != "v24684_schema_dev64_evaluator_gate"
        or gate.get("protocol_id") != contract.PROTOCOL_ID
        or gate.get("status") != "evaluator_gate_go"
        or gate.get("findings") != []
        or gate.get("passed") is not True
        or gate.get("forward_barrier", {}).get("selected_per_arm")
        != contract.SELECTED_COUNT
        or gate.get("forward_barrier", {}).get("changed_candidate_predictions")
        != barrier["changed"]
        or gate.get("forward_barrier", {}).get("identity_candidate_predictions")
        != barrier["identity"]
        or gate.get("forward_barrier", {}).get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or gate.get("forward_barrier", {}).get("forward_audit_sha256")
        != contract.sha256(ROOT / contract.FORWARD_AUDIT)
        or gate.get("evaluation_contract", {}).get("fixed_denominator_per_arm")
        != contract.SELECTED_COUNT
        or gate.get("evaluation_contract", {}).get("unique_provider_evaluations")
        != contract.SELECTED_COUNT + barrier["changed"]
        or gate.get("evaluation_contract", {}).get(
            "candidate_identity_judgments_reused_from_baseline"
        )
        != barrier["identity"]
        or gate.get("decision_contract") != forward_control.DECISION_CONTRACT
        or gate.get("evaluator_contract") != _parent_evaluator_contract()
        or not isinstance(manifest, Mapping)
        or gate.get("source_manifest_sha256") != contract.payload_sha256(manifest)
        or any(contract.sha256(ROOT / relative) != digest for relative, digest in manifest.items())
        or gate.get("source_policy", {}).get(
            "mapping_query_answer_gold_evaluator_bytes_opened_or_hashed_by_gate"
        )
        is not False
        or gate.get("source_policy", {}).get("official_evaluator_called_by_gate")
        is not False
        or gate.get("tests", {}).get("passed") is not True
        or gate.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or gate.get("tests", {}).get(
            "network_model_search_fetch_or_evaluator_called"
        )
        is not False
        or gate.get("runtime_state", {}).get("head_equals_target_main") is not True
        or gate.get("runtime_state", {}).get("worktree_clean") is not True
        or gate.get("runtime_state", {}).get(
            "forward_result_and_audit_tracked"
        )
        is not True
        or gate.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or gate.get("runtime_state", {}).get("forward_or_evaluator_process_active")
        is not False
        or gate.get("runtime_state", {}).get("evaluator_surface_pristine") is not True
        or gate.get("runtime_state", {}).get("protected_watchers")
        != contract.protected_watcher_snapshot()
        or gate.get("runtime_state", {}).get(
            "keyless_proxy_listening_without_request"
        )
        is not True
        or gate.get("claims", {}).get("sota") is not False
        or gate.get("authorization") != GATE_AUTHORIZATION
        or not _sealed(gate, "gate_payload_sha256")
    ):
        raise RuntimeError("V2.46.84 evaluator gate drifted")
    return gate


def build_evaluator_start(*, now: int | None = None) -> dict[str, Any]:
    gate = validate_evaluator_gate()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = _tracked(EVALUATOR_GATE)
    lease = lease_observation(ROOT, Path("/proc"))
    future = (EVALUATOR_START, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
    pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in future
    )
    findings: list[str] = []
    if head != remote:
        findings.append("evaluator_gate_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not tracked:
        findings.append("evaluator_gate_not_tracked")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not pristine:
        findings.append("evaluator_execution_surface_not_pristine")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    if contract.protected_watcher_snapshot() != gate["runtime_state"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24684_schema_dev64_evaluator_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "evaluator_ready" if not findings else "evaluator_rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "gate_base_commit": head,
        "target_main_at_start": remote,
        "evaluator_gate_tracked": tracked,
        "evaluator_gate_sha256": contract.sha256(ROOT / EVALUATOR_GATE),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "prediction_freeze_sha256": {
            arm: contract.sha256(ROOT / contract.PREDICTION_FREEZE[arm])
            for arm in contract.ARMS
        },
        "fixed_denominator_per_arm": contract.SELECTED_COUNT,
        "unique_provider_evaluations": gate["evaluation_contract"][
            "unique_provider_evaluations"
        ],
        "evaluator_workers_per_arm_maximum": EVALUATOR_WORKERS_PER_ARM,
        "total_evaluator_workers_maximum": TOTAL_EVALUATOR_WORKERS,
        "shared_api_lease_active_before_start": lease.get("active"),
        "evaluator_execution_surface_pristine": pristine,
        "mapping_query_answer_gold_evaluator_bytes_opened_or_hashed_before_start": False,
        "official_evaluator_called_before_start": False,
        "protected_watchers": contract.protected_watcher_snapshot(),
        "authorization": dict(START_AUTHORIZATION),
    }
    value["start_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.84 evaluator start failed: " + ",".join(findings))
    return value


def validate_evaluator_start(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    start = dict(value) if value is not None else _read(EVALUATOR_START)
    gate = validate_evaluator_gate()
    if (
        start.get("role") != "v24684_schema_dev64_evaluator_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "evaluator_ready"
        or start.get("findings") != []
        or start.get("execution_authorized") is not True
        or start.get("gate_base_commit") != start.get("target_main_at_start")
        or start.get("evaluator_gate_tracked") is not True
        or start.get("evaluator_gate_sha256") != contract.sha256(ROOT / EVALUATOR_GATE)
        or start.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or start.get("forward_audit_sha256")
        != contract.sha256(ROOT / contract.FORWARD_AUDIT)
        or start.get("prediction_freeze_sha256")
        != {
            arm: contract.sha256(ROOT / contract.PREDICTION_FREEZE[arm])
            for arm in contract.ARMS
        }
        or start.get("fixed_denominator_per_arm") != contract.SELECTED_COUNT
        or start.get("unique_provider_evaluations")
        != gate["evaluation_contract"]["unique_provider_evaluations"]
        or start.get("evaluator_workers_per_arm_maximum")
        != EVALUATOR_WORKERS_PER_ARM
        or start.get("total_evaluator_workers_maximum") != TOTAL_EVALUATOR_WORKERS
        or start.get("shared_api_lease_active_before_start") is not False
        or start.get("evaluator_execution_surface_pristine") is not True
        or start.get(
            "mapping_query_answer_gold_evaluator_bytes_opened_or_hashed_before_start"
        )
        is not False
        or start.get("official_evaluator_called_before_start") is not False
        or start.get("protected_watchers") != contract.protected_watcher_snapshot()
        or start.get("authorization") != START_AUTHORIZATION
        or not _sealed(start, "start_payload_sha256")
    ):
        raise RuntimeError("V2.46.84 evaluator start drifted")
    return start


def _configure_engine() -> None:
    assignments = {
        "ARMS": contract.ARMS,
        "EVALUATOR_ROOT": EVALUATOR_ROOT,
        "ARM_ROOTS": ARM_ROOTS,
        "JOINED": JOINED,
        "OFFICIAL": OFFICIAL,
        "PREPARE": PREPARE,
        "RUNS": RUNS,
        "LOGS": LOGS,
        "MERGED": MERGED,
        "MERGE": MERGE,
        "SUMMARY": SUMMARY,
        "EVALUATOR_WORKERS_PER_ARM": EVALUATOR_WORKERS_PER_ARM,
        "TOTAL_EVALUATOR_WORKERS": TOTAL_EVALUATOR_WORKERS,
        "SELECTED_COUNT": contract.SELECTED_COUNT,
        "PROTOCOL_ID": contract.PROTOCOL_ID,
        "PROTOCOL": EVALUATOR_GATE,
        "EVALUATOR_START": EVALUATOR_START,
        "FORWARD_CONTRACT": contract.FORWARD_CONTRACT,
        "FORWARD_RESULT": contract.FORWARD_RESULT,
        "PREDICTION_FREEZE": contract.PREDICTION_FREEZE,
        "RUNTIME_PREDICTIONS": contract.RUNTIME_PREDICTIONS,
        "RUN_SUMMARY": contract.RUN_SUMMARY,
        "SOURCE_MANIFEST": contract.SOURCE_MANIFEST,
        "MAPPING_PATH": MAPPING_PATH,
        "LEASE_PATH": contract.LEASE_PATH,
        "EVALUATOR_LEASE_OWNER": EVALUATOR_OWNER,
        "EVALUATOR_LEASE_PURPOSE": EVALUATOR_PURPOSE,
        "QUALITY": QUALITY,
    }
    for name, value in assignments.items():
        setattr(engine, name, value)
    engine.validate_forward_contract = contract.validate_forward_contract
    engine.validate_forward_barrier = validate_forward_barrier
    engine.validate_protocol = lambda root=ROOT: validate_evaluator_gate()


def validate_live_evaluator_identity(gate: Mapping[str, Any]) -> dict[str, Any]:
    _configure_engine()
    return engine.validate_live_evaluator_identity(ROOT, gate)


def prepare_arm(
    gate: Mapping[str, Any], barrier: Mapping[str, Any], arm: str
) -> dict[str, Any]:
    state = barrier["arms"][arm]
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(ROOT / contract.SOURCE_MANIFEST),
        mapping_rows=read_jsonl(ROOT / MAPPING_PATH),
        shards=[("devval", barrier["ids"], state["rows"], state["summary"])],
        rollout_id=1,
    )
    if len(joined) != contract.SELECTED_COUNT or len(official) != contract.SELECTED_COUNT:
        raise RuntimeError(f"V2.46.84 {arm} evaluator prepare is not terminal64")
    (ROOT / ARM_ROOTS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
    engine._write_jsonl_new(ROOT / JOINED[arm], joined)
    engine._write_jsonl_new(ROOT / OFFICIAL[arm], official)
    value = {
        **base,
        "phase": "post_both_arm_exact64_schema_evaluator_prepare",
        "arm": arm,
        "evaluator_gate_sha256": contract.sha256(ROOT / EVALUATOR_GATE),
        "evaluator_start_sha256": contract.sha256(ROOT / EVALUATOR_START),
        "both_arm_prediction_freeze_sha256": {
            name: contract.sha256(ROOT / contract.PREDICTION_FREEZE[name])
            for name in contract.ARMS
        },
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "prediction_identity_reuse_only_after_official_prepare": True,
        "mapping_sha256": contract.sha256(ROOT / MAPPING_PATH),
        "manifest_sha256": contract.sha256(ROOT / contract.SOURCE_MANIFEST),
        "source_hashes": state["sources"],
        "terminal_outcomes_sha256": contract.sha256(ROOT / JOINED[arm]),
        "official_predictions_sha256": contract.sha256(ROOT / OFFICIAL[arm]),
    }
    value["prepare_payload_sha256"] = contract.payload_sha256(value)
    _new_json(ROOT / PREPARE[arm], value)
    return {"joined": joined, "official": official, "attestation": value}


def _arm_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    _configure_engine()
    value = engine._arm_metrics(summary)
    engine._validate_arm_metrics(value)
    return value


def paired_uncertainty(summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, dict[str, Mapping[str, Any]]] = {}
    order: list[str] = []
    for arm in contract.ARMS:
        rows = list(summaries[arm]["per_task"])
        mapping = {str(row["opaque_id"]): row for row in rows}
        if len(rows) != contract.SELECTED_COUNT or len(mapping) != contract.SELECTED_COUNT:
            raise RuntimeError("V2.46.84 uncertainty identity drifted")
        by_arm[arm] = mapping
        if arm == "baseline":
            order = [str(row["opaque_id"]) for row in rows]
    if set(by_arm["candidate"]) != set(order):
        raise RuntimeError("V2.46.84 uncertainty task mismatch")
    deltas = [
        sum(
            float(by_arm["candidate"][opaque]["metrics"][name])
            - float(by_arm["baseline"][opaque]["metrics"][name])
            for name in QUALITY
        )
        / len(QUALITY)
        for opaque in order
    ]
    generator = random.Random(BOOTSTRAP_SEED)
    estimates = sorted(
        sum(deltas[generator.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(BOOTSTRAP_RESAMPLES)
    )
    interval = [estimates[249], estimates[9749]]
    return {
        "task_count": contract.SELECTED_COUNT,
        "bootstrap_unit": "paired_frozen_historical_dev_task",
        "seed": BOOTSTRAP_SEED,
        "resamples": BOOTSTRAP_RESAMPLES,
        "estimand": "mean paired failure-as-zero composite delta on historical dev64",
        "mean": sum(deltas) / len(deltas),
        "median": statistics.median(deltas),
        "positive": sum(value > 0 for value in deltas),
        "zero": sum(value == 0 for value in deltas),
        "negative": sum(value < 0 for value in deltas),
        "minimum": min(deltas),
        "maximum": max(deltas),
        "percentile_95_interval": interval,
        "interval_width": interval[1] - interval[0],
        "fixed_denominator_failure_as_zero": True,
        "predictions_frozen_before_evaluator": True,
        "unseen_future_population_or_sota_inference": False,
    }


def decision(
    metrics: Mapping[str, Mapping[str, Any]], barrier: Mapping[str, Any]
) -> dict[str, Any]:
    gate = forward_control.DECISION_CONTRACT
    baseline = metrics["baseline"]
    candidate = metrics["candidate"]
    delta = {
        name: candidate[name] - baseline[name]
        for name in (*QUALITY, "quality_composite", "whole_table_successes")
    }
    checks = {
        "changed_candidate_tasks": barrier["changed"]
        >= gate["minimum_changed_candidate_tasks_for_evaluator_gate"],
        "quality_composite_delta": delta["quality_composite"]
        >= gate["minimum_quality_composite_delta_for_go"],
        "entity_acc_delta": delta["entity_acc"]
        >= gate["minimum_entity_acc_delta_for_go"],
        "f1_by_row_delta": delta["f1_by_row"]
        >= gate["minimum_f1_by_row_delta_for_go"],
        "f1_by_item_delta": delta["f1_by_item"]
        >= gate["minimum_f1_by_item_delta_for_go"],
        "column_f1_delta": delta["column_f1"]
        >= gate["minimum_column_f1_delta_for_go"],
        "whole_table_success_delta": delta["whole_table_successes"]
        >= gate["minimum_whole_table_success_delta_for_go"],
        "candidate_minus_baseline_runtime_failures": candidate["runtime_failed"]
        - baseline["runtime_failed"]
        <= gate["maximum_candidate_minus_baseline_runtime_failures_for_go"],
        "candidate_minus_baseline_evaluator_failures": candidate[
            "evaluator_invalid_or_not_run"
        ]
        - baseline["evaluator_invalid_or_not_run"]
        <= gate["maximum_candidate_minus_baseline_evaluator_failures_for_go"],
    }
    passed = all(checks.values())
    return {
        "status": "go" if passed else "no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "candidate_minus_baseline": delta,
        "gate": dict(gate),
        "go_scope": "fresh_exact220_design_only_not_launch",
    }


def _stored_inputs() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    _configure_engine()
    evaluated, summaries = engine._stored_final_inputs(ROOT)
    barrier = validate_forward_barrier()
    evaluated["pairing"] = {
        "identity_instance_count": barrier["identity"],
        "changed_candidate_instance_count": barrier["changed"],
        "routing_keys": ["instance_id", "prediction_sha256"],
        "mapping_gold_category_question_type_split_score_or_reward_used_for_routing": False,
    }
    return evaluated, summaries


def build_final_result(
    barrier: Mapping[str, Any],
    evaluated: Mapping[str, Any],
    summaries: Mapping[str, Mapping[str, Any]],
    live: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = {arm: _arm_metrics(summaries[arm]) for arm in contract.ARMS}
    uncertainty = paired_uncertainty(summaries)
    gate = decision(metrics, barrier)
    pairing = evaluated["pairing"]
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "development_gate_go" if gate["passed"] else "development_gate_no_go",
        "selected_per_arm": contract.SELECTED_COUNT,
        "conservative_denominator_per_arm": contract.SELECTED_COUNT,
        "failure_as_zero": True,
        "both_arms_exact64_before_mapping_or_evaluator_open": True,
        "both_arms_complete_under_same_current_judge": True,
        "baseline": metrics["baseline"],
        "candidate": metrics["candidate"],
        "mechanism": {
            "incremental_schema_tasks": contract.EXPECTED_TREATED_COUNT,
            "fresh_baseline_children": contract.SELECTED_COUNT,
            "fresh_candidate_children": contract.EXPECTED_TREATED_COUNT,
            "same_run_baseline_reused_candidate_tasks": 56,
            "changed_candidate_tasks": barrier["changed"],
            "prediction_identity_evaluator_reuse_tasks": pairing[
                "identity_instance_count"
            ],
            "provider_evaluated_unique_predictions": contract.SELECTED_COUNT
            + pairing["changed_candidate_instance_count"],
            "runtime_failures_per_arm": {
                arm: barrier["pair"][f"{arm}_runtime_failures"]
                for arm in contract.ARMS
            },
        },
        "paired_uncertainty": uncertainty,
        "decision": gate,
        "efficiency": {
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
            "evaluator_parallel_wall_seconds": evaluated["parallel_wall_seconds"],
            "evaluator_workers_maximum": TOTAL_EVALUATOR_WORKERS,
        },
        "provenance": {
            "evaluator_gate_sha256": contract.sha256(ROOT / EVALUATOR_GATE),
            "evaluator_start_sha256": contract.sha256(ROOT / EVALUATOR_START),
            "forward_contract_sha256": contract.sha256(ROOT / contract.FORWARD_CONTRACT),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "prediction_freeze_sha256": {
                arm: contract.sha256(ROOT / contract.PREDICTION_FREEZE[arm])
                for arm in contract.ARMS
            },
            **dict(live),
            **{
                f"{arm}_merged_eval_results_sha256": contract.sha256(ROOT / MERGED[arm])
                for arm in contract.ARMS
            },
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read_by_forward": False,
            "mapping_opened_only_after_both_arm_prediction_freeze_and_evaluator_start": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "selective_retry_or_error_revaluation": False,
        },
        "authorization": {
            "fresh_exact220_design": gate["passed"],
            "fresh_exact220_launch": False,
            "additional_dev64_or_avg4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "claims": {
            "development_population_not_unseen": True,
            "expanded_visible_schema_development_gate": True,
            "public_full220_result": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
    }
    value["result_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_final_result(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result = dict(value) if value is not None else _read(FINAL_RESULT)
    barrier = validate_forward_barrier()
    evaluated, summaries = _stored_inputs()
    metrics = {arm: _arm_metrics(summaries[arm]) for arm in contract.ARMS}
    uncertainty = paired_uncertainty(summaries)
    gate = decision(metrics, barrier)
    live = validate_live_evaluator_identity(validate_evaluator_gate())
    expected = build_final_result(barrier, evaluated, summaries, live)
    expected["created_at_unix"] = result.get("created_at_unix")
    expected["result_payload_sha256"] = contract.payload_sha256(
        {key: value for key, value in expected.items() if key != "result_payload_sha256"}
    )
    if (
        result != expected
        or result.get("baseline") != metrics["baseline"]
        or result.get("candidate") != metrics["candidate"]
        or result.get("paired_uncertainty") != uncertainty
        or result.get("decision") != gate
        or result.get("mechanism", {}).get("prediction_identity_evaluator_reuse_tasks")
        != 57
        or result.get("mechanism", {}).get("provider_evaluated_unique_predictions")
        != 71
        or result.get("claims", {}).get("sota") is not False
        or result.get("authorization", {}).get("fresh_exact220_launch") is not False
        or not _sealed(result, "result_payload_sha256")
    ):
        raise RuntimeError("V2.46.84 final result drifted")
    return result


def build_postaudit(result: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_final_result(result)
    lease = lease_observation(ROOT, Path("/proc"))
    watchers = contract.protected_watcher_snapshot()
    expected_watchers = contract.validate_forward_contract(ROOT)["execution"][
        "protected_watchers"
    ]
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != expected_watchers:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24679_schema_dev64_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "result_sha256": contract.sha256(ROOT / FINAL_RESULT),
        "result_status": validated["status"],
        "shared_api_lease_active": lease.get("active"),
        "protected_watchers": watchers,
        "mapping_opened_only_after_both_arm_freeze_and_evaluator_start": True,
        "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        "selective_retry_or_error_revaluation": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_exact220_design": validated["decision"]["passed"]
            and not findings,
            "fresh_exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_postaudit(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    audit = dict(value) if value is not None else _read(POSTAUDIT)
    result = validate_final_result()
    if (
        audit.get("role") != "v24679_schema_dev64_postresult_audit"
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("result_sha256") != contract.sha256(ROOT / FINAL_RESULT)
        or audit.get("result_status") != result["status"]
        or audit.get("shared_api_lease_active") is not False
        or audit.get("protected_watchers") != contract.protected_watcher_snapshot()
        or audit.get("mapping_opened_only_after_both_arm_freeze_and_evaluator_start")
        is not True
        or audit.get(
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection"
        )
        is not False
        or audit.get("selective_retry_or_error_revaluation") is not False
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("authorization")
        != {
            "fresh_exact220_design": result["decision"]["passed"],
            "fresh_exact220_launch": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.84 postresult audit drifted")
    return audit


def finalize(
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    start = validate_evaluator_start()
    barrier = validate_forward_barrier()
    gate = validate_evaluator_gate()
    if (
        _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or _git("status", "--porcelain")
    ):
        raise RuntimeError("V2.46.84 evaluator execution requires clean pushed HEAD")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (EVALUATOR_ROOT, FINAL_RESULT, POSTAUDIT)
    ):
        raise RuntimeError("V2.46.84 evaluator execution surface is not pristine")
    _configure_engine()
    with acquire_deepwide_api_lease(
        ROOT,
        owner=EVALUATOR_OWNER,
        purpose=EVALUATOR_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        live = validate_live_evaluator_identity(gate)
        (ROOT / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        prepared = {
            arm: prepare_arm(gate, barrier, arm) for arm in contract.ARMS
        }
        evaluated = engine.run_all_evaluators(
            ROOT, gate, prepared, command_runner=command_runner
        )
    summaries: dict[str, dict[str, Any]] = {}
    for arm in contract.ARMS:
        summaries[arm] = summarize_rollout(
            prepared[arm]["joined"], evaluated["arms"][arm]["rows"], rollout_id=1
        )
        _new_json(ROOT / SUMMARY[arm], summaries[arm])
    result = build_final_result(barrier, evaluated, summaries, live)
    _new_json(ROOT / FINAL_RESULT, result)
    validate_final_result(result)
    postaudit = build_postaudit(result)
    _new_json(ROOT / POSTAUDIT, postaudit)
    validate_postaudit(postaudit)
    del start
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("gate", "start", "run"))
    args = parser.parse_args()
    if args.command == "gate":
        value = build_evaluator_gate()
        validate_evaluator_gate(value)
        _new_json(ROOT / EVALUATOR_GATE, value)
        print(json.dumps({"path": str(EVALUATOR_GATE), "status": value["status"]}, sort_keys=True))
    elif args.command == "start":
        value = build_evaluator_start()
        validate_evaluator_start(value)
        _new_json(ROOT / EVALUATOR_START, value)
        print(json.dumps({"path": str(EVALUATOR_START), "status": value["status"]}, sort_keys=True))
    else:
        value = finalize()
        print(
            json.dumps(
                {
                    "path": str(FINAL_RESULT),
                    "status": value["status"],
                    "failed_checks": value["decision"]["failed_checks"],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
