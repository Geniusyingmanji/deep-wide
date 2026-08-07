#!/usr/bin/env python3
"""Execute one authorized V2.47.84 external wave; no evaluator capability."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import socket
import subprocess
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

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    parent_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_observed_subprocess,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent import v24778_staged_fetch_fallback_runtime as base  # noqa: E402
from deepwide_agent import v24781_projection_conversion_funnel as funnel  # noqa: E402
from deepwide_agent.v24784_projection_funnel_integration import (  # noqa: E402
    validate_projection,
)
from deepwide_agent.v24784_projection_funnel_execution_contract import (  # noqa: E402
    ACTIVATION,
    ARM_COUNT,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    EXPERIMENT_WALL_CEILING_SECONDS,
    FORWARD_RESULT,
    FORWARD_STATUSES,
    FUNNEL_SUM_FIELDS,
    INTEGRATION_BUILD,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    MODEL_RECEIPT_NAME,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    PACKAGE_BUILD,
    PARENT_RECEIPT_NAME,
    PARENT_TIMEOUT_SECONDS,
    POLICY_ID,
    PREAUDIT,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PROTOCOL,
    PROTOCOL_ID,
    RESULT_NAME,
    RUN_SUMMARY,
    SELECTED_COUNT,
    STATUS_COUNT_FIELDS,
    TASK_ROOT,
    TERMINAL_RECEIPT_NAME,
    TRANSPORT_RECEIPT_NAME,
    VISIBLE_TASK_NAME,
    content_free_observation,
    failure_predictions,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    task_vector,
    validate_forward_result,
    validate_forward_row,
    validate_prediction_freeze,
    validate_run_summary,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


CHILD = Path("scripts/run_v24784_projection_funnel_task.py")


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.84 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.84 expected JSON object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def jsonl_new(path: Path, rows: list[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


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


def _active_runners(*, exclude_pid: int | None = None) -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    output: list[int] = []
    markers = (str(CHILD), "scripts/run_v24784_projection_funnel_external.py")
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        pid = int(parts[0])
        if pid != exclude_pid and any(marker in parts[2] for marker in markers):
            output.append(pid)
    return sorted(output)


def _manifest_valid(manifest: object) -> bool:
    if not isinstance(manifest, Mapping):
        return False
    for raw, digest in manifest.items():
        relative = Path(str(raw))
        path = ROOT / relative
        if (
            not isinstance(raw, str)
            or not isinstance(digest, str)
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.parts[:1] in {("evaluation",), ("outputs",)}
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(ROOT.resolve())
            or sha256(path) != digest
        ):
            return False
    return True


def _validate_launch_chain() -> dict[str, Any]:
    protocol = read(ROOT / PROTOCOL)
    build = read(ROOT / INTEGRATION_BUILD)
    package = read(ROOT / PACKAGE_BUILD)
    preaudit = read(ROOT / PREAUDIT)
    activation = read(ROOT / ACTIVATION)
    start = read(ROOT / EXECUTION_START)
    manifest = package.get("source_manifest")
    tasks = task_vector()
    if (
        protocol.get("role")
        != "v24784_projection_funnel_external_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or not sealed(protocol, "protocol_payload_sha256")
        or protocol.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or protocol.get("task_contract", {}).get("task_count") != SELECTED_COUNT
        or protocol.get("task_contract", {}).get("opaque_id_vector_sha256")
        != payload_sha256([task["opaque_id"] for task in tasks])
        or protocol.get("task_contract", {}).get("visible_question_vector_sha256")
        != payload_sha256([task["question"] for task in tasks])
        or build.get("role")
        != "v24784_projection_funnel_integration_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or not sealed(build, "audit_payload_sha256")
        or build.get("authorization", {}).get(
            "append_only_execution_contract_and_runner_build"
        )
        is not True
        or package.get("role") != "v24784_projection_funnel_package_audit"
        or package.get("audit_valid") is not True
        or package.get("findings") != []
        or not sealed(package, "audit_payload_sha256")
        or package.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _manifest_valid(manifest)
        or preaudit.get("role")
        != "v24784_projection_funnel_preactivation_audit"
        or preaudit.get("launch_authorized") is not True
        or not sealed(preaudit, "audit_payload_sha256")
        or preaudit.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or preaudit.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
        or preaudit.get("package_manifest_sha256") != payload_sha256(manifest)
        or preaudit.get("authorization")
        != {
            "activation_generation": True,
            "execution_start_generation": False,
            "one_external_forward_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        }
        or activation.get("role") != "v24784_projection_funnel_activation"
        or activation.get("launch_authorized") is not True
        or not sealed(activation, "activation_payload_sha256")
        or activation.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or activation.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
        or activation.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
        or activation.get("authorization")
        != {
            "execution_start_generation": True,
            "one_external_forward_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        }
        or start.get("role") != "v24784_projection_funnel_execution_start"
        or start.get("launch_authorized") is not True
        or not sealed(start, "execution_start_payload_sha256")
        or start.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or start.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
        or start.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
        or start.get("activation_sha256") != sha256(ROOT / ACTIVATION)
        or start.get("first_network_model_search_or_fetch_effect_started") is not False
        or start.get("authorization")
        != {
            "one_external_forward_launch": True,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        }
    ):
        raise RuntimeError("V2.47.84 launch authorization chain drifted")
    return {
        "protocol": protocol,
        "build": build,
        "package": package,
        "preaudit": preaudit,
        "activation": activation,
        "start": start,
    }


def _result_validator(task: Mapping[str, Any]):
    def validate(value: Mapping[str, Any]) -> dict[str, Any]:
        copied = validate_projection(value)
        content_free_observation(copied, task)
        return copied

    return validate


def run_task(position: int, task: dict[str, str]) -> dict[str, Any]:
    directory = ROOT / TASK_ROOT / f"task_{position:04d}"
    directory.mkdir(mode=0o700)
    new(directory / VISIBLE_TASK_NAME, task)
    command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(ROOT / CHILD),
        "--task",
        str(directory / VISIBLE_TASK_NAME),
        "--result",
        str(directory / RESULT_NAME),
        "--model-slot-directory",
        str(ROOT / MODEL_SLOT_DIRECTORY),
        "--model-receipt",
        str(directory / MODEL_RECEIPT_NAME),
        "--transport-receipt",
        str(directory / TRANSPORT_RECEIPT_NAME),
        "--terminal-receipt",
        str(directory / TERMINAL_RECEIPT_NAME),
    ]
    outcome = run_observed_subprocess(
        cwd=ROOT,
        output_root=ROOT / OUTPUT_ROOT,
        directory=directory,
        command=command,
        environment=environment(),
        timeout_seconds=PARENT_TIMEOUT_SECONDS,
        result_validator=_result_validator(task),
        model_receipt_validator=lambda value: validate_model_receipt(
            value, expected_cap=MODEL_SLOT_CAP
        ),
        transport_receipt_validator=validate_transport_health,
        result_name=RESULT_NAME,
        model_receipt_name=MODEL_RECEIPT_NAME,
        transport_receipt_name=TRANSPORT_RECEIPT_NAME,
        terminal_name=TERMINAL_RECEIPT_NAME,
        parent_name=PARENT_RECEIPT_NAME,
    )
    parent = validate_parent_receipt(read(directory / PARENT_RECEIPT_NAME))
    projection_valid = parent["failure_taxonomy"] == "success"
    result = validate_projection(read(directory / RESULT_NAME)) if projection_valid else None
    observation = (
        content_free_observation(result, task) if result is not None else None
    )
    return {
        "position": position,
        "task": task,
        "result": result,
        "observation": observation,
        "projection_valid": projection_valid,
        "parent_receipt": parent,
        "outcome_return_code": outcome.return_code,
    }


def run_task_total(position: int, task: dict[str, str]) -> dict[str, Any]:
    """Submit one ordinal once and preserve the denominator on parent errors."""

    try:
        return run_task(position, task)
    except Exception:
        directory = ROOT / TASK_ROOT / f"task_{position:04d}"
        receipt = parent_receipt(
            return_code=None,
            timed_out=False,
            elapsed_seconds=0.0,
            subprocess_exception=True,
            child_terminal_receipt_present=False,
            child_terminal_receipt_valid=False,
            result_envelope_present=False,
            result_envelope_valid=False,
            model_receipt_present=False,
            model_receipt_valid=False,
            transport_receipt_present=False,
            transport_receipt_valid=False,
        )
        try:
            if directory.is_symlink() or not directory.resolve(
                strict=False
            ).is_relative_to((ROOT / OUTPUT_ROOT).resolve()):
                raise RuntimeError("V2.47.84 failure receipt directory escaped")
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            parent_path = directory / PARENT_RECEIPT_NAME
            if not parent_path.exists() and not parent_path.is_symlink():
                new(parent_path, receipt)
        except (OSError, RuntimeError, ValueError):
            pass
        return {
            "position": position,
            "task": task,
            "result": None,
            "observation": None,
            "projection_valid": False,
            "parent_receipt": receipt,
            "outcome_return_code": None,
        }


def _freeze(outcomes: list[dict[str, Any]], wall: float) -> dict[str, Any]:
    if (
        len(outcomes) != SELECTED_COUNT
        or [item["position"] for item in outcomes]
        != list(range(1, SELECTED_COUNT + 1))
    ):
        raise RuntimeError("V2.47.84 scheduler ordinal drifted")
    rows: list[dict[str, Any]] = []
    observations: list[Mapping[str, Any]] = []
    taxonomy: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for item in outcomes:
        result = item["result"]
        observation = item["observation"]
        status = (
            str(result["status"])
            if item["projection_valid"] and result is not None
            else "parent_failure"
        )
        statuses[status] += 1
        base_valid = bool(result["base_result_valid"]) if result is not None else False
        funnel_valid = bool(result["funnel_receipt_valid"]) if result is not None else False
        predictions = (
            result["predictions"]
            if base_valid
            else failure_predictions(item["task"])
        )
        row = {
            "ordinal": item["position"],
            "opaque_id": item["task"]["opaque_id"],
            "predictions": predictions,
            "prediction_sha256": {
                arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
                for arm in base.ARMS
            },
            "runtime_status": status,
            "projection_valid": bool(item["projection_valid"]),
            "base_result_valid": base_valid,
            "funnel_receipt_valid": funnel_valid,
        }
        rows.append(validate_forward_row(row))
        if observation is not None:
            observations.append(observation)
        taxonomy[str(item["parent_receipt"]["failure_taxonomy"])] += 1
    jsonl_new(ROOT / PREDICTIONS, rows)
    valid_funnels = [item for item in observations if item["funnel_counts"] is not None]
    reason_counts: Counter[str] = Counter()
    for item in valid_funnels:
        receipt = item["funnel_counts"]
        # The fixed reason partition is present only in the validated child
        # receipt; re-read it from the corresponding result without exposing
        # any private catalog or content.
        result = next(
            outcome["result"]
            for outcome in outcomes
            if outcome["observation"] is item
        )
        reason_counts.update(result["projection_funnel_receipt"]["reason_counts"])
    summary = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_forward_run_summary",
        "policy_id": POLICY_ID,
        "selected_tasks": SELECTED_COUNT,
        "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
        "valid_projection_results": sum(item["projection_valid"] for item in outcomes),
        "base_valid_task_results": sum(bool(item["base_result_valid"]) for item in observations),
        "validated_funnel_task_count": len(valid_funnels),
        "projected_failure_tasks": statuses["base_runtime_failure"]
        + statuses["parent_failure"],
        "changed_task_count": sum(bool(item["prediction_changed"]) for item in observations),
        "changed_cell_count": sum(int(item["changed_cell_count"]) for item in observations),
        "founded_changed_cell_count": sum(int(item["founded_changed_cell_count"]) for item in observations),
        "country_changed_cell_count": sum(int(item["country_changed_cell_count"]) for item in observations),
        "nonunknown_changed_cell_count": sum(int(item["nonunknown_changed_cell_count"]) for item in observations),
        "projection_backed_support_set_count": sum(int(item["projection_backed_support_set_count"]) for item in observations),
        "initial_fetch_request_count": sum(int(item["initial_fetch_request_count"]) for item in observations),
        "reserve_fetch_request_count": sum(int(item["reserve_fetch_request_count"]) for item in observations),
        "actual_fetch_request_count": sum(int(item["actual_fetch_request_count"]) for item in observations),
        "initial_usable_page_count": sum(int(item["initial_usable_page_count"]) for item in observations),
        "reserve_usable_page_count": sum(int(item["reserve_usable_page_count"]) for item in observations),
        "actual_usable_page_count": sum(int(item["actual_usable_page_count"]) for item in observations),
        "final_entity_slots_with_two_usable_identity_sources": sum(int(item["final_entity_slots_with_two_usable_identity_sources"]) for item in observations),
        "entity_slots_brought_to_two_sources_by_reserve": sum(int(item["entity_slots_brought_to_two_sources_by_reserve"]) for item in observations),
        "reserve_target_entity_count": sum(int(item["reserve_target_entity_count"]) for item in observations),
        "failed_url_retry_count": sum(int(item["failed_url_retry_count"]) for item in observations),
        "scheduler_contract_failed_task_count": sum(
            item["base_result_valid"] and not item["scheduler_contract"]
            for item in observations
        ),
        "candidate_not_only_unknown_task_count": sum(
            item["base_result_valid"] and not item["candidate_changes_only_unknown"]
            for item in observations
        ),
        "semantic_safety_contract_failed_task_count": sum(
            item["base_result_valid"] and not item["semantic_safety_contract"]
            for item in observations
        ),
        **{
            f"status_{name}_count": int(statuses[name])
            for name in FORWARD_STATUSES
        },
        "projection_emitted_task_count": sum(
            int(item["funnel_counts"]["projection_emitted_pair_count"] > 0)
            for item in valid_funnels
        ),
        "projection_backed_support_task_count": sum(
            int(item["funnel_counts"]["projection_backed_eligible_support_set_count"] > 0)
            for item in valid_funnels
        ),
        "unconflicted_projection_backed_unknown_proposal_task_count": sum(
            int(item["funnel_counts"]["unconflicted_projection_backed_unknown_proposal_count"] > 0)
            for item in valid_funnels
        ),
        "task_local_joint_projection_backed_safe_change_task_count": sum(
            int(item["task_local_joint_projection_backed_safe_change"])
            for item in valid_funnels
        ),
        **{
            name: sum(int(item["funnel_counts"][name]) for item in valid_funnels)
            for name in FUNNEL_SUM_FIELDS
        },
        "funnel_reason_counts": {
            name: int(reason_counts[name]) for name in funnel.REASONS
        },
        "forward_wall_seconds": round(float(wall), 6),
        "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
        "within_experiment_wall_ceiling": float(wall)
        <= EXPERIMENT_WALL_CEILING_SECONDS,
        "parent_failure_taxonomy_counts": dict(sorted(taxonomy.items())),
        "all_task_ordinals_submitted_once": True,
        "resume_retry_skip_or_selective_rerun": False,
        "private_question_query_url_host_page_or_private_content_hash_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    summary["summary_payload_sha256"] = payload_sha256(summary)
    summary = validate_run_summary(summary)
    new(ROOT / RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "policy_id": POLICY_ID,
        "selected_tasks": SELECTED_COUNT,
        "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
        "predictions_sha256": sha256(ROOT / PREDICTIONS),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "all_predictions_terminal_before_private_truth_or_quality_open": True,
        "private_truth_or_quality_path_opened_or_hashed": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze)
    freeze = validate_prediction_freeze(freeze)
    new(ROOT / PREDICTION_FREEZE, freeze)
    return {"rows": rows, "summary": summary, "freeze": freeze}


def main() -> None:
    chain = _validate_launch_chain()
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.84 launch requires clean pushed HEAD")
    if protected_watcher_snapshot() != chain["start"].get("protected_watchers"):
        raise RuntimeError("V2.47.84 protected watcher drifted")
    if _active_runners(exclude_pid=os.getpid()):
        raise RuntimeError("V2.47.84 runner already active")
    for path in (ROOT / OUTPUT_ROOT, ROOT / FORWARD_RESULT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.47.84 forward surface is not pristine")
    tasks = task_vector()
    with socket.create_connection(("127.0.0.1", 9878), timeout=2):
        pass
    with acquire_deepwide_api_lease(
        ROOT, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=ROOT / LEASE_PATH
    ):
        (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True)
        (ROOT / MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)
        for index in range(1, MODEL_SLOT_CAP + 1):
            (ROOT / MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock").touch(mode=0o600)
        (ROOT / TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=EXECUTOR_CONCURRENCY
        ) as executor:
            futures = [
                executor.submit(run_task_total, ordinal, task)
                for ordinal, task in enumerate(tasks, 1)
            ]
            outcomes = [future.result() for future in futures]
        wall = max(0.0, time.monotonic() - started)
    outcomes.sort(key=lambda item: item["position"])
    frozen = _freeze(outcomes, wall)
    forward = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_forward_result",
        "protocol_id": PROTOCOL_ID,
        "policy_id": POLICY_ID,
        "created_at_unix": int(time.time()),
        "selected_tasks": SELECTED_COUNT,
        "terminal_arm_predictions": SELECTED_COUNT * ARM_COUNT,
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "all_predictions_terminal_before_private_truth_or_quality_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "quality_or_evaluator_called": False,
        "resume_retry_skip_or_selective_rerun": False,
    }
    forward["result_payload_sha256"] = payload_sha256(forward)
    forward = validate_forward_result(forward)
    new(ROOT / FORWARD_RESULT, forward)
    print(
        json.dumps(
            {
                "terminal": SELECTED_COUNT * ARM_COUNT,
                "validated_funnel_tasks": frozen["summary"][
                    "validated_funnel_task_count"
                ],
                "joint_safe_change_tasks": frozen["summary"][
                    "task_local_joint_projection_backed_safe_change_task_count"
                ],
                "wall_seconds": wall,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
