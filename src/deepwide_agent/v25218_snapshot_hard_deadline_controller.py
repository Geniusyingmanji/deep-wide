"""Hard total-wall controller for the four V2.52.17 snapshot attempts.

Each frozen stratum runs in one short-lived fork child.  Response bytes cross
the child boundary only through inherited anonymous memory maps; control data
crosses content-free pipes.  The parent enforces one absolute batch deadline,
terminates then kills any surviving child, and discards every body unless all
four children finish with mutually consistent sealed receipts.

Importing this module starts no child and performs no network or file effect.
The default worker is V2.52.17, but tests may inject a fork-inherited fake.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import mmap
import multiprocessing
import time
from collections.abc import Callable, Mapping
from multiprocessing.connection import wait
from typing import Any

from . import v25217_single_snapshot_transport as transport


POLICY_ID = "v25218_snapshot_hard_deadline_controller_v1"
ROLE = "v25218_content_free_snapshot_batch_receipt"
STRATA = tuple(transport.ENDPOINTS)
MAXIMUM_HARD_DEADLINE_SECONDS = 180.0
MINIMUM_HARD_DEADLINE_SECONDS = 0.05
TERMINATE_GRACE_SECONDS = 0.20
KILL_GRACE_SECONDS = 0.50
FAILURE_CODES = (
    "start_method",
    "child_transport_failure",
    "child_result_shape",
    "child_receipt_drift",
    "child_body_binding",
    "child_nonzero_exit",
    "hard_deadline",
    "controller_error",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _worker(
    stratum: str,
    buffer: mmap.mmap,
    connection: Any,
    fetch: Callable[..., tuple[bytes, dict[str, Any]]],
) -> None:
    message: dict[str, Any]
    try:
        body, receipt = fetch(stratum)
        checked = transport.validate_receipt(receipt)
        if (
            checked["terminal_outcome"] != "success"
            or not isinstance(body, bytes)
            or len(body) != checked["response_bytes"]
            or hashlib.sha256(body).hexdigest() != checked["response_sha256"]
            or len(body) > transport.ENDPOINTS[stratum]["maximum_response_bytes"]
        ):
            message = {
                "kind": "transport_failure",
                "transport_receipt": checked,
            }
        else:
            buffer.seek(0)
            buffer.write(body)
            message = {
                "kind": "success",
                "transport_receipt": checked,
            }
    except BaseException:
        message = {
            "kind": "worker_error",
            "transport_receipt": None,
        }
    try:
        connection.send(message)
    except BaseException:
        pass
    finally:
        try:
            connection.close()
        except BaseException:
            pass


def _stop(process: Any) -> None:
    if process is None or not process.is_alive():
        return
    try:
        process.terminate()
    except (ProcessLookupError, OSError):
        return
    process.join(timeout=TERMINATE_GRACE_SECONDS)
    if not process.is_alive():
        return
    try:
        process.kill()
    except (ProcessLookupError, OSError):
        return
    process.join(timeout=KILL_GRACE_SECONDS)


def _child_row(
    *,
    started: bool,
    message_received: bool,
    kind: str,
    exit_code: int | None,
    transport_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "started": started,
        "message_received": message_received,
        "kind": kind,
        "exit_code": exit_code,
        "transport_receipt": (
            copy.deepcopy(dict(transport_receipt))
            if transport_receipt is not None
            else None
        ),
    }


def _receipt(
    *,
    hard_deadline_seconds: float,
    elapsed_seconds: float,
    terminal_outcome: str,
    failure_code: str | None,
    children: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    total_bytes = sum(
        int((row.get("transport_receipt") or {}).get("response_bytes", 0))
        for row in children.values()
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "strata": list(STRATA),
        "child_count": len(STRATA),
        "fork_start_method_required": True,
        "anonymous_shared_memory_only": True,
        "hard_deadline_seconds": float(hard_deadline_seconds),
        "elapsed_seconds": round(float(elapsed_seconds), 6),
        "terminal_outcome": terminal_outcome,
        "failure_code": failure_code,
        "children": copy.deepcopy(dict(children)),
        "successful_transport_count": sum(
            row.get("kind") == "success" for row in children.values()
        ),
        "transport_response_bytes_total": total_bytes,
        "partial_bodies_returned_on_failure": False,
        "raw_snapshot_file_pipe_queue_or_persistent_store_used": False,
        "contains_url_body_identity_record_value_question_prediction_evidence_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "model_search_evaluator_benchmark_or_api_effect": False,
        "population_freeze_external_forward_or_runtime_compatibility_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    children = copied.get("children")
    deadline = copied.get("hard_deadline_seconds")
    elapsed = copied.get("elapsed_seconds")
    outcome = copied.get("terminal_outcome")
    failure = copied.get("failure_code")
    false_flags = (
        "partial_bodies_returned_on_failure",
        "raw_snapshot_file_pipe_queue_or_persistent_store_used",
        "contains_url_body_identity_record_value_question_prediction_evidence_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "model_search_evaluator_benchmark_or_api_effect",
        "population_freeze_external_forward_or_runtime_compatibility_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "strata",
            "child_count",
            "fork_start_method_required",
            "anonymous_shared_memory_only",
            "hard_deadline_seconds",
            "elapsed_seconds",
            "terminal_outcome",
            "failure_code",
            "children",
            "successful_transport_count",
            "transport_response_bytes_total",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("strata") != list(STRATA)
        or copied.get("child_count") != len(STRATA)
        or copied.get("fork_start_method_required") is not True
        or copied.get("anonymous_shared_memory_only") is not True
        or isinstance(deadline, bool)
        or not isinstance(deadline, (int, float))
        or not math.isfinite(float(deadline))
        or not MINIMUM_HARD_DEADLINE_SECONDS
        <= float(deadline)
        <= MAXIMUM_HARD_DEADLINE_SECONDS
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or not 0 <= float(elapsed) <= float(deadline) + 2.0
        or outcome not in {"success", "failure"}
        or failure not in {None, *FAILURE_CODES}
        or (failure is None) is not (outcome == "success")
        or not isinstance(children, Mapping)
        or set(children) != set(STRATA)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.18 snapshot batch receipt drifted")
    success_count = 0
    total_bytes = 0
    for stratum in STRATA:
        row = children[stratum]
        if (
            not isinstance(row, Mapping)
            or set(row)
            != {
                "started",
                "message_received",
                "kind",
                "exit_code",
                "transport_receipt",
            }
            or not isinstance(row.get("started"), bool)
            or not isinstance(row.get("message_received"), bool)
            or row.get("kind")
            not in {
                "success",
                "transport_failure",
                "worker_error",
                "no_message",
                "hard_deadline",
                "not_started",
            }
            or (
                row.get("exit_code") is not None
                and (
                    isinstance(row.get("exit_code"), bool)
                    or not isinstance(row.get("exit_code"), int)
                )
            )
        ):
            raise ValueError("V2.52.18 child row drifted")
        nested = row.get("transport_receipt")
        if nested is not None:
            if not isinstance(nested, Mapping):
                raise ValueError("V2.52.18 child receipt shape drifted")
            checked = transport.validate_receipt(nested)
            if checked["stratum"] != stratum or checked != dict(nested):
                raise ValueError("V2.52.18 child receipt binding drifted")
            total_bytes += int(checked["response_bytes"])
        if row["kind"] == "success":
            if (
                nested is None
                or nested["terminal_outcome"] != "success"
                or row["message_received"] is not True
                or row["started"] is not True
                or row["exit_code"] != 0
            ):
                raise ValueError("V2.52.18 successful child drifted")
            success_count += 1
        elif row["kind"] == "transport_failure" and (
            nested is None or nested["terminal_outcome"] != "failure"
        ):
            raise ValueError("V2.52.18 failed child drifted")
    if (
        copied.get("successful_transport_count") != success_count
        or copied.get("transport_response_bytes_total") != total_bytes
        or outcome == "success"
        and success_count != len(STRATA)
        or outcome == "failure"
        and success_count == len(STRATA)
    ):
        raise ValueError("V2.52.18 aggregate child accounting drifted")
    return copied


def run_snapshot_batch(
    *,
    fetch: Callable[..., tuple[bytes, dict[str, Any]]] = transport.fetch_snapshot,
    hard_deadline_seconds: float = MAXIMUM_HARD_DEADLINE_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[dict[str, bytes], dict[str, Any]]:
    if (
        isinstance(hard_deadline_seconds, bool)
        or not isinstance(hard_deadline_seconds, (int, float))
        or not math.isfinite(float(hard_deadline_seconds))
        or not MINIMUM_HARD_DEADLINE_SECONDS
        <= float(hard_deadline_seconds)
        <= MAXIMUM_HARD_DEADLINE_SECONDS
    ):
        raise ValueError("V2.52.18 invalid hard deadline")
    started_at = monotonic()
    if "fork" not in multiprocessing.get_all_start_methods():
        children = {
            stratum: _child_row(
                started=False,
                message_received=False,
                kind="not_started",
                exit_code=None,
                transport_receipt=None,
            )
            for stratum in STRATA
        }
        return {}, _receipt(
            hard_deadline_seconds=float(hard_deadline_seconds),
            elapsed_seconds=0.0,
            terminal_outcome="failure",
            failure_code="start_method",
            children=children,
        )

    context = multiprocessing.get_context("fork")
    buffers: dict[str, mmap.mmap] = {}
    processes: dict[str, Any] = {}
    parents: dict[str, Any] = {}
    child_rows: dict[str, dict[str, Any]] = {}
    messages: dict[str, dict[str, Any]] = {}
    failure_code: str | None = None
    try:
        for stratum in STRATA:
            buffers[stratum] = mmap.mmap(
                -1, transport.ENDPOINTS[stratum]["maximum_response_bytes"]
            )
            parent_connection, child_connection = context.Pipe(duplex=False)
            parents[stratum] = parent_connection
            process = context.Process(
                target=_worker,
                args=(stratum, buffers[stratum], child_connection, fetch),
                daemon=False,
            )
            processes[stratum] = process
            process.start()
            child_connection.close()

        pending = set(STRATA)
        connection_to_stratum = {
            parents[stratum]: stratum for stratum in STRATA
        }
        absolute_deadline = started_at + float(hard_deadline_seconds)
        while pending:
            remaining = absolute_deadline - monotonic()
            if remaining <= 0:
                failure_code = "hard_deadline"
                break
            ready = wait(
                [parents[stratum] for stratum in pending], timeout=remaining
            )
            if not ready:
                failure_code = "hard_deadline"
                break
            for connection in ready:
                stratum = connection_to_stratum[connection]
                try:
                    message = connection.recv()
                except (EOFError, OSError):
                    message = None
                if isinstance(message, Mapping):
                    messages[stratum] = copy.deepcopy(dict(message))
                pending.discard(stratum)

        if failure_code is not None:
            for process in processes.values():
                _stop(process)
        else:
            for process in processes.values():
                remaining = max(
                    0.0,
                    started_at
                    + float(hard_deadline_seconds)
                    - monotonic(),
                )
                process.join(timeout=remaining)
            if any(process.is_alive() for process in processes.values()):
                failure_code = "hard_deadline"
                for process in processes.values():
                    _stop(process)

        for stratum in STRATA:
            process = processes.get(stratum)
            message = messages.get(stratum)
            if failure_code == "hard_deadline" and message is None:
                kind = "hard_deadline"
            elif message is None:
                kind = "no_message"
            else:
                kind = str(message.get("kind") or "worker_error")
            nested = (
                message.get("transport_receipt")
                if isinstance(message, Mapping)
                else None
            )
            child_rows[stratum] = _child_row(
                started=process is not None,
                message_received=message is not None,
                kind=kind,
                exit_code=(process.exitcode if process is not None else None),
                transport_receipt=(nested if isinstance(nested, Mapping) else None),
            )

        if failure_code is None:
            if any(row["kind"] == "transport_failure" for row in child_rows.values()):
                failure_code = "child_transport_failure"
            elif any(row["kind"] == "worker_error" for row in child_rows.values()):
                failure_code = "controller_error"
            elif any(row["kind"] not in {"success", "transport_failure"} for row in child_rows.values()):
                failure_code = "child_result_shape"
            elif any(row["exit_code"] != 0 for row in child_rows.values()):
                failure_code = "child_nonzero_exit"

        bodies: dict[str, bytes] = {}
        if failure_code is None:
            try:
                for stratum in STRATA:
                    nested = transport.validate_receipt(
                        child_rows[stratum]["transport_receipt"]
                    )
                    size = int(nested["response_bytes"])
                    buffers[stratum].seek(0)
                    body = buffers[stratum].read(size)
                    if (
                        len(body) != size
                        or hashlib.sha256(body).hexdigest()
                        != nested["response_sha256"]
                    ):
                        failure_code = "child_body_binding"
                        bodies = {}
                        break
                    bodies[stratum] = body
            except BaseException:
                failure_code = "child_receipt_drift"
                bodies = {}

        elapsed = monotonic() - started_at
        if elapsed > float(hard_deadline_seconds) and failure_code is None:
            failure_code = "hard_deadline"
            bodies = {}
        return bodies, _receipt(
            hard_deadline_seconds=float(hard_deadline_seconds),
            elapsed_seconds=max(
                0.0,
                min(float(elapsed), float(hard_deadline_seconds) + 2.0),
            ),
            terminal_outcome="success" if failure_code is None else "failure",
            failure_code=failure_code,
            children=child_rows,
        )
    except BaseException:
        for process in processes.values():
            _stop(process)
        for stratum in STRATA:
            process = processes.get(stratum)
            child_rows[stratum] = _child_row(
                started=process is not None,
                message_received=False,
                kind="worker_error" if process is not None else "not_started",
                exit_code=(process.exitcode if process is not None else None),
                transport_receipt=None,
            )
        elapsed = monotonic() - started_at
        return {}, _receipt(
            hard_deadline_seconds=float(hard_deadline_seconds),
            elapsed_seconds=max(
                0.0,
                min(float(elapsed), float(hard_deadline_seconds) + 2.0),
            ),
            terminal_outcome="failure",
            failure_code="controller_error",
            children=child_rows,
        )
    finally:
        for process in processes.values():
            _stop(process)
        for connection in parents.values():
            try:
                connection.close()
            except BaseException:
                pass
        for buffer in buffers.values():
            try:
                buffer.close()
            except BaseException:
                pass


__all__ = [
    "FAILURE_CODES",
    "MAXIMUM_HARD_DEADLINE_SECONDS",
    "POLICY_ID",
    "ROLE",
    "STRATA",
    "run_snapshot_batch",
    "validate_receipt",
]
