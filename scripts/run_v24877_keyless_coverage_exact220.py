#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.77 exact-220 forward."""

from __future__ import annotations

import copy
import json
import os
import socket
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24877_keyless_coverage_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24860_coverage_revision_integration import (  # noqa: E402
    RESULT_ROLE as COVERAGE_RESULT_ROLE,
    validate_integration_receipt,
)
from deepwide_agent.v24861_coverage_revision_exact_task import (  # noqa: E402
    validate_envelope,
)
from deepwide_agent.v24874_keyless_coverage_bundle import (  # noqa: E402
    BACKFILL_NAME,
    COVERAGE_NAME,
    EFFECT_NAME,
    FINAL_MODEL_NAME,
    SINGLE_NAME,
    TRANSPORT_NAME,
    validate_bundle,
    validate_effect_receipt,
)
from deepwide_agent.v24876_keyless_coverage_subprocess_gate import (  # noqa: E402
    PARENT_NAME,
    run_observed_bundle_subprocess,
    validate_parent_bundle_receipt,
)
from scripts import run_v24635_exact220 as algorithm  # noqa: E402
from scripts import run_v24800_exact220 as fixed_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


PREAUDIT_ROLE = "v24877_keyless_coverage_exact220_preactivation_audit"
START_ROLE = "v24877_keyless_coverage_exact220_execution_start"


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.77 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.77 expected JSON object")
    return value


def _task_command(root: Path, directory: Path) -> list[str]:
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / contract.CHILD_MARKER),
        "--task",
        str(directory / "visible_task.json"),
    ]


def _child_env() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "TERM": "xterm-256color",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _validate_bundle(_value: dict[str, Any], directory: Path) -> None:
    validate_bundle(
        output_root=ROOT / contract.OUTPUT_ROOT,
        directory=directory,
        expected_model_slot_cap=contract.MODEL_SLOT_CAP,
    )


def _run_one_task(
    root: Path,
    protocol: dict[str, Any],
    position: int,
    task: dict[str, str],
    directory: Path,
    *,
    popen: Any = subprocess.Popen,
) -> Any:
    del protocol
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    algorithm._new_json(directory / "visible_task.json", task)
    observed, gate = run_observed_bundle_subprocess(
        cwd=root,
        output_root=root / contract.OUTPUT_ROOT,
        directory=directory,
        command=_task_command(root, directory),
        environment=_child_env(),
        timeout_seconds=float(contract.LIMITS["wall_seconds"]) + 30.0,
        expected_model_slot_cap=contract.MODEL_SLOT_CAP,
        popen=popen,
    )
    validate_parent_bundle_receipt(gate)
    model_value: dict[str, Any] | None = None
    model_present = (directory / FINAL_MODEL_NAME).is_file()
    try:
        if model_present:
            model_value = validate_model(
                _read(directory / FINAL_MODEL_NAME),
                expected_cap=contract.MODEL_SLOT_CAP,
            )
    except (OSError, RuntimeError, TypeError, ValueError):
        model_value = None
    transport = algorithm._empty_transport()
    transport_valid = False
    try:
        transport = validate_transport_health(_read(directory / TRANSPORT_NAME))
        transport_valid = True
    except (OSError, RuntimeError, TypeError, ValueError):
        pass
    single = None
    backfill = None
    try:
        single = _read(directory / SINGLE_NAME)
        algorithm.validate_single(single)
    except (OSError, RuntimeError, TypeError, ValueError):
        single = None
    try:
        backfill = algorithm.validate_backfill(_read(directory / BACKFILL_NAME))
    except (OSError, RuntimeError, TypeError, ValueError):
        backfill = None
    accepted = (
        observed.receipt["failure_taxonomy"] == "success"
        and gate["disposition"] == "success"
        and observed.return_code == 0
        and not observed.timed_out
        and not observed.subprocess_exception
        and model_value is not None
        and transport_valid
        and single is not None
        and backfill is not None
    )
    if accepted:
        try:
            _validate_bundle({}, directory)
            result = validate_envelope(_read(directory / "result.json"))["result"]
            return algorithm.TaskOutcome(
                position,
                result,
                observed.receipt,
                True,
                model_present,
                True,
                int(model_value["acquisitions"]),
                int(model_value["slot_timeouts"]),
                True,
                transport,
                True,
                single,
                True,
                backfill,
            )
        except (KeyError, OSError, RuntimeError, TypeError, ValueError):
            accepted = False
    progress = algorithm._safe_progress(directory / "safe_progress.json")
    result = algorithm._fallback(
        task,
        failure=str(gate["disposition"]),
        elapsed=float(observed.receipt["elapsed_seconds"]),
        progress=progress,
        model_receipt=model_value,
        timed_out=gate["disposition"] == "hard_deadline_timeout",
    )
    return algorithm.TaskOutcome(
        position,
        result,
        observed.receipt,
        False,
        model_present,
        model_value is not None,
        int(model_value.get("acquisitions", 0)) if model_value else 0,
        int(model_value.get("slot_timeouts", 0)) if model_value else 0,
        transport_valid,
        transport,
        single is not None,
        single,
        backfill is not None,
        backfill,
    )


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_v24831_keyless_exact220.py",
        "scripts/run_v24831_keyless_exact220_task.py",
        "scripts/run_v24635_exact220.py",
        "scripts/run_v24635_exact220_task.py",
        "scripts/run_official_eval_local.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _project_authorization(value: dict[str, Any], role: str, field: str) -> dict[str, Any]:
    copied = copy.deepcopy(value)
    copied["role"] = role
    copied.pop(field, None)
    copied[field] = contract.payload_sha256(copied)
    return copied


def validate_execution_start(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    audit = _read(root / contract.PREAUDIT)
    start = _read(root / contract.EXECUTION_START)
    if audit.get("role") != PREAUDIT_ROLE or start.get("role") != START_ROLE:
        raise RuntimeError("V2.48.77 execution authorization drifted")
    projected_audit = _project_authorization(
        audit,
        "v24831_keyless_exact220_preactivation_audit",
        "audit_payload_sha256",
    )
    projected_start = _project_authorization(
        start,
        "v24831_keyless_exact220_execution_start",
        "execution_start_payload_sha256",
    )
    audit_unsigned = dict(projected_audit)
    audit_seal = audit_unsigned.pop("audit_payload_sha256", None)
    start_unsigned = dict(projected_start)
    start_seal = start_unsigned.pop("execution_start_payload_sha256", None)
    if (
        projected_audit.get("audit_valid") is not True
        or projected_audit.get("findings") != []
        or projected_audit.get("protocol_sha256")
        != contract.sha256(root / contract.PROTOCOL)
        or projected_audit.get("dependency_manifest_sha256")
        != protocol["dependency_manifest_sha256"]
        or projected_audit.get("authorization")
        != {
            "execution_start_generation": True,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or audit_seal != contract.payload_sha256(audit_unsigned)
        or projected_start.get("status") != "authorized_not_started"
        or projected_start.get("findings") != []
        or projected_start.get("protocol_sha256")
        != contract.sha256(root / contract.PROTOCOL)
        or projected_start.get("preactivation_audit_sha256")
        != contract.sha256(root / contract.PREAUDIT)
        or projected_start.get("dependency_manifest_sha256")
        != protocol["dependency_manifest_sha256"]
        or projected_start.get("selected") != 220
        or projected_start.get("executor_concurrency") != 20
        or projected_start.get("model_slot_cap") != 8
        or projected_start.get("runtime_input_contract")
        != ["opaque_id", "question"]
        or projected_start.get("protected_watchers")
        != protocol["execution"]["protected_watchers"]
        or projected_start.get("first_network_model_search_or_fetch_effect_started")
        is not False
        or projected_start.get("authorization")
        != {
            "single_fresh_exact220_forward": True,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or start_seal != contract.payload_sha256(start_unsigned)
    ):
        raise RuntimeError("V2.48.77 execution authorization drifted")
    return start


def configure_algorithm() -> None:
    bindings = {
        "PROTOCOL_ID": contract.PROTOCOL_ID,
        "CHILD_MARKER": contract.CHILD_MARKER,
        "CHILD_TERMINAL_NAME": "child_terminal_receipt.json",
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "TASK_ROOT": contract.TASK_ROOT,
        "RUNTIME_PREDICTIONS": contract.RUNTIME_PREDICTIONS,
        "RUN_SUMMARY": contract.RUN_SUMMARY,
        "PREDICTION_FREEZE": contract.PREDICTION_FREEZE,
        "SAFE_PROGRESS": contract.SAFE_PROGRESS,
        "EXECUTOR_CONCURRENCY": contract.EXECUTOR_CONCURRENCY,
        "MODEL_SLOT_CAP": contract.MODEL_SLOT_CAP,
        "LIMITS": contract.LIMITS,
        "PARENT_DEADLINE_GRACE_SECONDS": 30.0,
        "RECEIPT_NAME": FINAL_MODEL_NAME,
        "TRANSPORT_NAME": TRANSPORT_NAME,
        "PARENT_EXIT_NAME": PARENT_NAME,
        "_validate_bundle": _validate_bundle,
        "_child_env": _child_env,
        "task_command": _task_command,
        "run_one_task": _run_one_task,
        "validate_v24318_result": _validate_scheduler_result,
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)


def _progress(completed: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24877_keyless_coverage_exact220_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "completed": completed,
        "unfinished": contract.SELECTED_COUNT - completed,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["progress_payload_sha256"] = contract.payload_sha256(value)
    return value


def _validate_scheduler_result(value: dict[str, Any], arm: str) -> None:
    if value.get("role") != COVERAGE_RESULT_ROLE:
        algorithm._v24877_parent_validate_scheduler_result(value, arm)
        return
    if arm != "baseline":
        raise ValueError("V2.48.77 scheduler arm drifted")
    parent = value.get("parent_result")
    receipt = value.get("coverage_revision_receipt")
    if not isinstance(parent, dict) or not isinstance(receipt, dict):
        raise ValueError("V2.48.77 scheduler coverage result drifted")
    algorithm._v24877_parent_validate_scheduler_result(parent, arm)
    validated = validate_integration_receipt(receipt)
    prediction = value.get("prediction")
    if (
        not isinstance(prediction, str)
        or not prediction
        or value.get("opaque_id") != parent.get("opaque_id")
        or value.get("columns") != parent.get("columns")
        or bool(prediction != parent.get("prediction"))
        != bool(validated["prediction_changed"])
    ):
        raise ValueError("V2.48.77 scheduler prediction binding drifted")


def _coverage_totals(root: Path) -> dict[str, Any]:
    dispositions: Counter[str] = Counter()
    valid = changed = logical_calls = admitted_cells = admitted_rows = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        directory = root / contract.TASK_ROOT / f"task_{position:04d}"
        try:
            validate_bundle(
                output_root=root / contract.OUTPUT_ROOT,
                directory=directory,
                expected_model_slot_cap=contract.MODEL_SLOT_CAP,
            )
            receipt = validate_integration_receipt(_read(directory / COVERAGE_NAME))
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            continue
        valid += 1
        dispositions[str(receipt["disposition"])] += 1
        changed += int(receipt["prediction_changed"])
        logical_calls += int(receipt["logical_revision_call_admitted"])
        nested = receipt["coverage_receipt"]
        admitted_cells += int(nested["admitted_existing_unknown_fills"]) + int(
            nested["admitted_existing_overrides"]
        )
        admitted_rows += int(nested["admitted_new_rows"])
    return {
        "task_results": contract.SELECTED_COUNT,
        "valid_bundles": valid,
        "invalid_or_missing_bundles": contract.SELECTED_COUNT - valid,
        "disposition_counts": dict(sorted(dispositions.items())),
        "logical_revision_calls": logical_calls,
        "prediction_changed_tasks": changed,
        "admitted_existing_cell_changes": admitted_cells,
        "admitted_new_rows": admitted_rows,
        "entropy_or_information_gain_used_for_admission_or_routing": False,
        "entropy_or_information_gain_shadow_measurement_only": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def _effect_totals(root: Path) -> dict[str, Any]:
    fields = (
        "admitted_logical_queries",
        "executed_logical_queries",
        "actual_fetches",
        "usable_pages",
        "parent_response_calls",
        "parent_failed_query_rows",
        "provider_attempts",
        "transport_failures",
        "hard_total_wall_timeouts",
        "status_2xx",
        "status_3xx",
        "status_408",
        "status_409",
        "status_429",
        "status_4xx_other",
        "status_5xx",
        "status_other",
        "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures",
        "fetch_deadline_rejections",
        "fetch_helper_failures",
    )
    totals = {name: 0 for name in fields}
    valid = 0
    for position in range(1, contract.SELECTED_COUNT + 1):
        directory = root / contract.TASK_ROOT / f"task_{position:04d}"
        try:
            envelope = validate_envelope(_read(directory / "result.json"))
            effect = validate_effect_receipt(
                _read(directory / EFFECT_NAME), envelope=envelope
            )
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            continue
        valid += 1
        for name in fields:
            totals[name] += int(effect[name])
    return {
        "task_results": contract.SELECTED_COUNT,
        "valid_effect_receipts": valid,
        "invalid_or_missing_effect_receipts": contract.SELECTED_COUNT - valid,
        **totals,
        "logical_queries_equal_http_responses_required": False,
        "fetch_cap_equal_actual_fetches_required": False,
        "entropy_or_information_gain_used_for_admission": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def _fixed_full_budget_totals(outcomes: list[Any]) -> dict[str, Any]:
    projected = [
        SimpleNamespace(
            result=(
                item.result["parent_result"]
                if item.result.get("role") == COVERAGE_RESULT_ROLE
                else item.result
            )
        )
        for item in outcomes
    ]
    original_contract = fixed_runner.contract
    try:
        fixed_runner.contract = contract
        return fixed_runner._fixed_full_budget_totals(projected)
    finally:
        fixed_runner.contract = original_contract


def main() -> None:
    configure_algorithm()
    if not hasattr(algorithm, "_v24877_parent_validate_scheduler_result"):
        from deepwide_agent.v24318_deadline_conservation_runtime import (
            validate_v24318_result,
        )

        algorithm._v24877_parent_validate_scheduler_result = validate_v24318_result
    root = ROOT
    protocol = contract.validate_frozen_protocol(
        root, _read(root / contract.PROTOCOL)
    )
    start = validate_execution_start(root, protocol)
    tasks = contract.task_vector(root, protocol)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True,
    ).stdout.strip()
    if head != remote or dirty:
        raise RuntimeError("V2.48.77 launch requires clean pushed HEAD")
    required = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        *map(Path, protocol["dependency_manifest"]),
    )
    if any(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        ).returncode != 0
        for path in required
    ):
        raise RuntimeError("V2.48.77 launch dependency is not tracked")
    conflicts = _active_conflicts()
    if conflicts:
        raise RuntimeError(f"V2.48.77 conflicting benchmark/evaluator active: {conflicts}")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    for path in (root / contract.FORWARD_RESULT, root / contract.OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.48.77 forward surface is not pristine")
    with acquire_deepwide_api_lease(
        root,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=root / contract.LEASE_PATH,
    ):
        if contract.protected_watcher_snapshot() != protocol["execution"][
            "protected_watchers"
        ]:
            raise RuntimeError("V2.48.77 protected watcher drifted before effect")
        (root / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        algorithm._prepare_slots(root)
        (root / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = algorithm.execute_forward(
            root,
            protocol,
            tasks,
            task_runner=_run_one_task,
            progress_writer=lambda value: algorithm._atomic_json(
                root / contract.SAFE_PROGRESS,
                _progress(int(value["completed"])),
            ),
        )
        wall = max(0.0, time.monotonic() - started)
    rows = [algorithm._runtime_row(item.result) for item in outcomes]
    algorithm._write_jsonl_new(root / contract.RUNTIME_PREDICTIONS, rows)
    summary = algorithm._summary(outcomes, wall)
    summary["role"] = "v24877_keyless_coverage_exact220_run_summary"
    summary["protocol_id"] = contract.PROTOCOL_ID
    summary["executor_concurrency"] = contract.EXECUTOR_CONCURRENCY
    summary["fixed_full_budget_control_totals"] = _fixed_full_budget_totals(outcomes)
    summary["coverage_revision_totals"] = _coverage_totals(root)
    summary["keyless_effect_totals"] = _effect_totals(root)
    summary.pop("summary_payload_sha256", None)
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    algorithm._new_json(root / contract.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24877_keyless_coverage_exact220_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "terminal": contract.SELECTED_COUNT,
        "runtime_predictions_sha256": contract.sha256(
            root / contract.RUNTIME_PREDICTIONS
        ),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "prediction_hashes_sha256": contract.payload_sha256(
            [row["prediction_sha256"] for row in rows]
        ),
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    algorithm._new_json(root / contract.PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24877_keyless_coverage_exact220_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "terminal_predictions": contract.SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "fixed_full_budget_control_totals": summary[
            "fixed_full_budget_control_totals"
        ],
        "coverage_revision_totals": summary["coverage_revision_totals"],
        "keyless_effect_totals": summary["keyless_effect_totals"],
        "prediction_freeze_sha256": contract.sha256(
            root / contract.PREDICTION_FREEZE
        ),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "execution_start_sha256": contract.sha256(root / contract.EXECUTION_START),
        "execution_start_payload_sha256": start[
            "execution_start_payload_sha256"
        ],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "official_evaluator_called": False,
        "retry_resume_skip_or_selective_rerun_launched": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    algorithm._new_json(root / contract.FORWARD_RESULT, forward)
    algorithm._atomic_json(
        root / contract.SAFE_PROGRESS, _progress(contract.SELECTED_COUNT)
    )
    print(
        json.dumps(
            {
                "terminal": contract.SELECTED_COUNT,
                "wall_seconds": wall,
                "fallback_tables": summary["fallback_tables"],
                "coverage_revision_totals": summary["coverage_revision_totals"],
                "forward_result": str(contract.FORWARD_RESULT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
