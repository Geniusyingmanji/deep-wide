"""Hard worker cutoff and content-free stage checkpointing for V2.44.69.

The existing child process owns the public terminal receipt.  It launches the
actual runtime as a new process group and waits only until a frozen worker
deadline.  If effects, deterministic validation, or serialization overrun,
the supervisor kills the whole group, reads one hash-chained content-free
stage checkpoint, writes a minimal failure snapshot, and returns control to
the existing terminal-receipt wrapper before the parent deadline.

The stage journal contains only a fixed enum, ordinal, monotonic sequence, and
hash chain.  It cannot carry task text, identifiers, prompts, responses,
queries, URLs, pages, predictions, values, credentials, labels, gold, reward,
score, or evaluator state.
"""

from __future__ import annotations

import ctypes
import json
import math
import os
import re
import signal
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

from .v24308_child_exit_observability import child_receipt, payload_sha256
from .v24309_runner_exit_integration import _new_json
from .v24397_failure_observability import build_failure_snapshot
from .v24399_failure_observable_runner import FAILURE_NAME


POLICY_ID = "v24469_bounded_worker_supervisor_v1"
STAGE_PREFIX = "content_free_stage_"
STAGE_SUFFIX = ".json"
WORKER_RECEIPT_NAME = "worker_timeout_receipt.json"
CHECKPOINT_ROLE = "v24469_content_free_stage_checkpoint"
WORKER_RECEIPT_ROLE = "v24469_worker_supervision_receipt"
STAGES = (
    "worker_entered",
    "model_constructed",
    "search_constructed",
    "runtime_entered",
    "model_effect_started",
    "model_effect_finished",
    "hosted_search_effect_started",
    "hosted_search_effect_finished",
    "public_fetch_effect_started",
    "public_fetch_effect_finished",
    "parent_runtime_returned",
    "adaptive_support_entered",
    "adaptive_support_returned",
    "complete_validation_entered",
    "complete_validation_returned",
    "artifact_persistence_entered",
    "certificate_persistence_entered",
    "worker_complete",
)
STAGE_SET = frozenset(STAGES)
CHECKPOINT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "ordinal",
        "sequence",
        "stage",
        "previous_checkpoint_sha256",
        "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "network_model_search_fetch_or_evaluator_called_by_checkpoint_builder",
        "checkpoint_payload_sha256",
    }
)
WORKER_RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "ordinal",
        "last_stage",
        "last_stage_sequence",
        "worker_hard_timeout",
        "failure_snapshot_written",
        "checkpoint_chain_valid",
        "model_effect_started_lower_bound",
        "model_effect_finished_lower_bound",
        "hosted_search_effect_started_lower_bound",
        "hosted_search_effect_finished_lower_bound",
        "public_fetch_effect_started_lower_bound",
        "public_fetch_effect_finished_lower_bound",
        "complete_validation_entered",
        "complete_validation_returned",
        "elapsed_seconds",
        "return_code",
        "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "receipt_payload_sha256",
    }
)
HEX64 = re.compile(r"[0-9a-f]{64}")


def _ordinary_directory(directory: Path) -> Path:
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.44.69 task directory is not ordinary")
    return directory.resolve()


def _stage_path(checkpoint_directory: Path, sequence: int) -> Path:
    return _ordinary_directory(checkpoint_directory) / (
        f"{STAGE_PREFIX}{sequence:06d}{STAGE_SUFFIX}"
    )


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    base = _ordinary_directory(path.parent)
    if path.resolve(strict=False).parent != base:
        raise RuntimeError("V2.44.69 checkpoint escaped task directory")
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        directory_descriptor = os.open(
            base, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        )
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        if path.exists() and not path.is_symlink():
            path.unlink()
        raise


def build_checkpoint(
    *,
    ordinal: int,
    sequence: int,
    stage: str,
    previous_checkpoint_sha256: str | None,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 1
        or stage not in STAGE_SET
        or previous_checkpoint_sha256 is not None
        and HEX64.fullmatch(previous_checkpoint_sha256) is None
    ):
        raise ValueError("V2.44.69 checkpoint input drifted")
    value = {
        "artifact_version": 1,
        "role": CHECKPOINT_ROLE,
        "policy_id": POLICY_ID,
        "ordinal": ordinal,
        "sequence": sequence,
        "stage": stage,
        "previous_checkpoint_sha256": previous_checkpoint_sha256,
        "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_or_evaluator_called_by_checkpoint_builder": False,
    }
    value["checkpoint_payload_sha256"] = payload_sha256(value)
    return validate_checkpoint(value)


def validate_checkpoint(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("checkpoint_payload_sha256", None)
    previous = copied.get("previous_checkpoint_sha256")
    if (
        set(copied) != CHECKPOINT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != CHECKPOINT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or isinstance(copied.get("sequence"), bool)
        or not isinstance(copied.get("sequence"), int)
        or copied["sequence"] < 1
        or copied.get("stage") not in STAGE_SET
        or previous is not None
        and (not isinstance(previous, str) or HEX64.fullmatch(previous) is None)
        or any(
            copied.get(name) is not False
            for name in (
                "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "network_model_search_fetch_or_evaluator_called_by_checkpoint_builder",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.69 checkpoint drifted")
    return copied


class StageJournal:
    def __init__(self, checkpoint_directory: Path, *, ordinal: int) -> None:
        # Checkpoints live outside the proof-carrying task artifact directory;
        # the latter has an exact-file surface enforced by V2.44.59.
        self.directory = _ordinary_directory(checkpoint_directory)
        self.ordinal = ordinal
        self.sequence = 0
        self.previous: str | None = None
        self.lock = threading.Lock()

    def record(self, stage: str) -> dict[str, Any]:
        with self.lock:
            self.sequence += 1
            value = build_checkpoint(
                ordinal=self.ordinal,
                sequence=self.sequence,
                stage=stage,
                previous_checkpoint_sha256=self.previous,
            )
            _write_new(_stage_path(self.directory, self.sequence), value)
            self.previous = str(value["checkpoint_payload_sha256"])
            return value


def read_checkpoints(
    checkpoint_directory: Path, *, ordinal: int
) -> list[dict[str, Any]]:
    directory = _ordinary_directory(checkpoint_directory)
    paths = sorted(directory.iterdir(), key=lambda path: path.name)
    values: list[dict[str, Any]] = []
    previous: str | None = None
    for expected_sequence, path in enumerate(paths, start=1):
        expected_name = f"{STAGE_PREFIX}{expected_sequence:06d}{STAGE_SUFFIX}"
        if path.name != expected_name or path.is_symlink() or not path.is_file():
            raise RuntimeError("V2.44.69 checkpoint surface drifted")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise RuntimeError("V2.44.69 checkpoint is not an object")
        value = validate_checkpoint(raw)
        if (
            value["ordinal"] != ordinal
            or value["sequence"] != expected_sequence
            or value["previous_checkpoint_sha256"] != previous
        ):
            raise RuntimeError("V2.44.69 checkpoint chain drifted")
        values.append(value)
        previous = str(value["checkpoint_payload_sha256"])
    return values


def read_checkpoint(
    checkpoint_directory: Path, *, ordinal: int
) -> dict[str, Any] | None:
    values = read_checkpoints(checkpoint_directory, ordinal=ordinal)
    return values[-1] if values else None


def remove_checkpoint(checkpoint_directory: Path) -> None:
    directory = _ordinary_directory(checkpoint_directory)
    for path in tuple(directory.iterdir()):
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.name.startswith(STAGE_PREFIX)
            or not path.name.endswith(STAGE_SUFFIX)
        ):
            raise RuntimeError("V2.44.69 checkpoint cleanup rejected path")
        path.unlink()


def bind_worker_to_parent(*, expected_parent_pid: int) -> None:
    if (
        isinstance(expected_parent_pid, bool)
        or not isinstance(expected_parent_pid, int)
        or expected_parent_pid <= 1
    ):
        raise ValueError("V2.44.69 expected parent PID is invalid")
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL) != 0:  # PR_SET_PDEATHSIG
        raise OSError(ctypes.get_errno(), "V2.44.69 prctl failed")
    if os.getppid() != expected_parent_pid:
        raise RuntimeError("V2.44.69 parent exited before worker initialization")


def _terminate_group(process: Any) -> None:
    try:
        os.killpg(int(process.pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(int(process.pid), signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.5)
    except subprocess.TimeoutExpired:
        return


def _environment(parent_pid: int) -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "DEEPWIDE_EXPECTED_SUPERVISOR_PID": str(parent_pid),
    }


def _publish_timeout_failure(
    directory: Path,
    *,
    checkpoint_directory: Path,
    ordinal: int,
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
) -> tuple[list[dict[str, Any]], bool]:
    try:
        checkpoints = read_checkpoints(checkpoint_directory, ordinal=ordinal)
        checkpoint_chain_valid = True
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        checkpoints = []
        checkpoint_chain_valid = False
    snapshot = build_failure_snapshot(
        TimeoutError(),
        failure_stage="runtime",
        model_receipt=None,
        transport_health=None,
        search_receipt=None,
        expected_model_cap=expected_model_cap,
    )
    writer(FAILURE_NAME, snapshot)
    return checkpoints, checkpoint_chain_valid


def build_worker_receipt(
    *,
    ordinal: int,
    last_stage: str | None,
    last_stage_sequence: int,
    worker_hard_timeout: bool,
    failure_snapshot_written: bool,
    checkpoints: Sequence[Mapping[str, Any]],
    checkpoint_chain_valid: bool,
    elapsed_seconds: float,
    return_code: int | None,
) -> dict[str, Any]:
    stages = [str(value.get("stage")) for value in checkpoints]
    counts = {
        stage: stages.count(stage)
        for stage in (
            "model_effect_started",
            "model_effect_finished",
            "hosted_search_effect_started",
            "hosted_search_effect_finished",
            "public_fetch_effect_started",
            "public_fetch_effect_finished",
        )
    }
    value = {
        "artifact_version": 1,
        "role": WORKER_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "ordinal": ordinal,
        "last_stage": last_stage,
        "last_stage_sequence": last_stage_sequence,
        "worker_hard_timeout": worker_hard_timeout,
        "failure_snapshot_written": failure_snapshot_written,
        "checkpoint_chain_valid": checkpoint_chain_valid,
        "model_effect_started_lower_bound": counts["model_effect_started"],
        "model_effect_finished_lower_bound": counts["model_effect_finished"],
        "hosted_search_effect_started_lower_bound": counts[
            "hosted_search_effect_started"
        ],
        "hosted_search_effect_finished_lower_bound": counts[
            "hosted_search_effect_finished"
        ],
        "public_fetch_effect_started_lower_bound": counts[
            "public_fetch_effect_started"
        ],
        "public_fetch_effect_finished_lower_bound": counts[
            "public_fetch_effect_finished"
        ],
        "complete_validation_entered": "complete_validation_entered" in stages,
        "complete_validation_returned": "complete_validation_returned" in stages,
        "elapsed_seconds": round(float(elapsed_seconds), 6),
        "return_code": return_code,
        "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_worker_receipt(value)


def validate_worker_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    stage = copied.get("last_stage")
    sequence = copied.get("last_stage_sequence")
    elapsed = copied.get("elapsed_seconds")
    return_code = copied.get("return_code")
    count_fields = (
        "model_effect_started_lower_bound",
        "model_effect_finished_lower_bound",
        "hosted_search_effect_started_lower_bound",
        "hosted_search_effect_finished_lower_bound",
        "public_fetch_effect_started_lower_bound",
        "public_fetch_effect_finished_lower_bound",
    )
    if (
        set(copied) != WORKER_RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != WORKER_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or stage is not None
        and stage not in STAGE_SET
        or isinstance(sequence, bool)
        or not isinstance(sequence, int)
        or sequence < 0
        or (stage is None) is not (sequence == 0)
        or not isinstance(copied.get("worker_hard_timeout"), bool)
        or not isinstance(copied.get("failure_snapshot_written"), bool)
        or not isinstance(copied.get("checkpoint_chain_valid"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or copied["model_effect_finished_lower_bound"]
        > copied["model_effect_started_lower_bound"]
        or copied["hosted_search_effect_finished_lower_bound"]
        > copied["hosted_search_effect_started_lower_bound"]
        or copied["public_fetch_effect_finished_lower_bound"]
        > copied["public_fetch_effect_started_lower_bound"]
        or not isinstance(copied.get("complete_validation_entered"), bool)
        or not isinstance(copied.get("complete_validation_returned"), bool)
        or copied.get("complete_validation_returned") is True
        and copied.get("complete_validation_entered") is not True
        or copied.get("worker_hard_timeout") is True
        and copied.get("failure_snapshot_written") is not True
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or elapsed < 0
        or return_code is not None
        and (isinstance(return_code, bool) or not isinstance(return_code, int))
        or any(
            copied.get(name) is not False
            for name in (
                "contains_task_question_opaque_id_prompt_response_query_url_page_prediction_candidate_value_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.69 worker receipt drifted")
    return copied


def supervise_worker(
    *,
    ordinal: int,
    cwd: Path,
    directory: Path,
    checkpoint_directory: Path,
    command: Sequence[str],
    timeout_seconds: float,
    expected_model_cap: int,
    writer: Callable[[str, Mapping[str, Any]], None],
    terminal_name: str = "child_terminal_receipt.json",
    popen: Any = subprocess.Popen,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(float(timeout_seconds))
        or timeout_seconds <= 0
        or isinstance(expected_model_cap, bool)
        or not isinstance(expected_model_cap, int)
        or not 1 <= expected_model_cap <= 32
        or not command
        or any(not isinstance(part, str) or not part for part in command)
    ):
        raise ValueError("V2.44.69 invalid worker contract")
    directory = _ordinary_directory(directory)
    checkpoint_directory = _ordinary_directory(checkpoint_directory)
    terminal = directory / terminal_name
    if terminal.exists() or terminal.is_symlink():
        raise FileExistsError(terminal)
    parent_pid = os.getpid()
    started = monotonic()
    process = popen(
        list(command),
        cwd=cwd,
        env=_environment(parent_pid),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    remaining = max(0.0, float(timeout_seconds) - (monotonic() - started))
    timed_out = remaining <= 0
    if not timed_out:
        try:
            return_code = int(process.wait(timeout=remaining))
        except subprocess.TimeoutExpired:
            timed_out = True
            return_code = None
    else:
        return_code = None
    if timed_out:
        _terminate_group(process)
        checkpoints, checkpoint_chain_valid = _publish_timeout_failure(
            directory,
            checkpoint_directory=checkpoint_directory,
            ordinal=ordinal,
            expected_model_cap=expected_model_cap,
            writer=writer,
        )
        elapsed = max(0.0, monotonic() - started)
        checkpoint = checkpoints[-1] if checkpoints else None
        timeout = build_worker_receipt(
            ordinal=ordinal,
            last_stage=checkpoint["stage"] if checkpoint is not None else None,
            last_stage_sequence=(
                checkpoint["sequence"] if checkpoint is not None else 0
            ),
            worker_hard_timeout=True,
            failure_snapshot_written=True,
            checkpoints=checkpoints,
            checkpoint_chain_valid=checkpoint_chain_valid,
            elapsed_seconds=elapsed,
            return_code=None,
        )
        writer(WORKER_RECEIPT_NAME, timeout)
        _new_json(
            terminal,
            child_receipt(
                stage="child_exception",
                exception_type="TimeoutError",
                model_receipt_written=False,
                transport_receipt_written=False,
                result_envelope_written=False,
            ),
        )
        try:
            remove_checkpoint(checkpoint_directory)
        except (OSError, RuntimeError):
            pass
        return timeout
    checkpoints = read_checkpoints(checkpoint_directory, ordinal=ordinal)
    checkpoint = checkpoints[-1] if checkpoints else None
    if return_code != 0:
        elapsed = max(0.0, monotonic() - started)
        receipt = build_worker_receipt(
            ordinal=ordinal,
            last_stage=checkpoint["stage"] if checkpoint is not None else None,
            last_stage_sequence=(
                checkpoint["sequence"] if checkpoint is not None else 0
            ),
            worker_hard_timeout=False,
            failure_snapshot_written=(directory / FAILURE_NAME).is_file(),
            checkpoints=checkpoints,
            checkpoint_chain_valid=True,
            elapsed_seconds=elapsed,
            return_code=return_code,
        )
        writer(WORKER_RECEIPT_NAME, receipt)
        remove_checkpoint(checkpoint_directory)
        if not terminal.is_file() or terminal.is_symlink():
            raise RuntimeError("V2.44.69 nonzero worker lacks terminal receipt")
        return receipt
    if not terminal.is_file() or terminal.is_symlink():
        remove_checkpoint(checkpoint_directory)
        raise RuntimeError("V2.44.69 worker exited without valid terminal surface")
    if checkpoint is None or checkpoint["stage"] != "worker_complete":
        remove_checkpoint(checkpoint_directory)
        raise RuntimeError("V2.44.69 worker completed without terminal checkpoint")
    remove_checkpoint(checkpoint_directory)
    return build_worker_receipt(
        ordinal=ordinal,
        last_stage="worker_complete",
        last_stage_sequence=checkpoint["sequence"],
        worker_hard_timeout=False,
        failure_snapshot_written=False,
        checkpoints=checkpoints,
        checkpoint_chain_valid=True,
        elapsed_seconds=max(0.0, monotonic() - started),
        return_code=return_code,
    )


__all__ = [
    "STAGE_PREFIX",
    "STAGES",
    "WORKER_RECEIPT_NAME",
    "StageJournal",
    "bind_worker_to_parent",
    "build_checkpoint",
    "build_worker_receipt",
    "read_checkpoints",
    "read_checkpoint",
    "remove_checkpoint",
    "supervise_worker",
    "validate_checkpoint",
    "validate_worker_receipt",
]
