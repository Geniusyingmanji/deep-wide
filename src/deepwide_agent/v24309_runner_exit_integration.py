"""Append-only runner integration for V2.43.08 content-free exit receipts."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from .v24308_child_exit_observability import (
    child_receipt,
    coarse_exception_type,
    parent_receipt,
    validate_child_receipt,
    validate_parent_receipt,
)


CHILD_TERMINAL_NAME = "child_terminal_receipt.json"
PARENT_EXIT_NAME = "parent_exit_receipt.json"
RESULT_NAME = "result_envelope.json"
MODEL_RECEIPT_NAME = "model_receipt.json"
TRANSPORT_RECEIPT_NAME = "transport_receipt.json"
T = TypeVar("T")


@dataclass(frozen=True)
class ObservedChildOutcome:
    return_code: int | None
    timed_out: bool
    subprocess_exception: bool
    receipt: dict[str, Any]


def _ordinary_directory(output_root: Path, directory: Path) -> Path:
    base = output_root.resolve()
    if output_root.is_symlink() or not output_root.is_dir():
        raise RuntimeError("V2.43.09 output root is not an ordinary directory")
    if directory.is_symlink() or not directory.is_dir():
        raise RuntimeError("V2.43.09 task root is not an ordinary directory")
    resolved = directory.resolve()
    if not resolved.is_relative_to(base):
        raise RuntimeError("V2.43.09 task root escaped the output root")
    return resolved


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _present(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _artifact_names(*names: str) -> tuple[str, ...]:
    if (
        len(set(names)) != len(names)
        or any(
            not isinstance(name, str)
            or not name
            or name in {".", ".."}
            or Path(name).name != name
            for name in names
        )
    ):
        raise ValueError("V2.43.09 artifact names must be distinct basenames")
    return names


def _read_object(path: Path) -> dict[str, Any]:
    if not _present(path):
        raise RuntimeError("V2.43.09 expected an ordinary artifact")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.09 expected an object artifact")
    return value


def _valid(path: Path, validator: Callable[[Mapping[str, Any]], object]) -> bool:
    if not _present(path):
        return False
    try:
        validator(_read_object(path))
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return False
    return True


def run_child_with_terminal_receipt(
    *,
    output_root: Path,
    directory: Path,
    action: Callable[[], T],
    result_name: str = RESULT_NAME,
    model_receipt_name: str = MODEL_RECEIPT_NAME,
    transport_receipt_name: str = TRANSPORT_RECEIPT_NAME,
    terminal_name: str = CHILD_TERMINAL_NAME,
) -> T:
    """Run one child action and create a content-free terminal receipt last."""

    directory = _ordinary_directory(output_root, directory)
    _artifact_names(
        result_name,
        model_receipt_name,
        transport_receipt_name,
        terminal_name,
    )
    terminal = directory / terminal_name
    result = directory / result_name
    model = directory / model_receipt_name
    transport = directory / transport_receipt_name
    if terminal.exists() or terminal.is_symlink():
        raise FileExistsError(terminal)
    try:
        value = action()
    except BaseException as error:
        _new_json(
            terminal,
            child_receipt(
                stage="child_exception",
                exception_type=coarse_exception_type(error),
                model_receipt_written=_present(model),
                transport_receipt_written=_present(transport),
                result_envelope_written=_present(result),
            ),
        )
        raise
    _new_json(
        terminal,
        child_receipt(
            stage="result_envelope_written"
            if _present(result)
            else "runtime_returned",
            exception_type=None,
            model_receipt_written=_present(model),
            transport_receipt_written=_present(transport),
            result_envelope_written=_present(result),
        ),
    )
    return value


def _terminate_group(process: Any) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait(timeout=2)


def run_observed_subprocess(
    *,
    cwd: Path,
    output_root: Path,
    directory: Path,
    command: Sequence[str],
    environment: Mapping[str, str],
    timeout_seconds: float,
    result_validator: Callable[[Mapping[str, Any]], object],
    model_receipt_validator: Callable[[Mapping[str, Any]], object],
    transport_receipt_validator: Callable[[Mapping[str, Any]], object],
    result_name: str = RESULT_NAME,
    model_receipt_name: str = MODEL_RECEIPT_NAME,
    transport_receipt_name: str = TRANSPORT_RECEIPT_NAME,
    terminal_name: str = CHILD_TERMINAL_NAME,
    parent_name: str = PARENT_EXIT_NAME,
    popen: Any = subprocess.Popen,
) -> ObservedChildOutcome:
    """Launch a child and create one sealed, content-free parent exit receipt."""

    directory = _ordinary_directory(output_root, directory)
    _artifact_names(
        result_name,
        model_receipt_name,
        transport_receipt_name,
        terminal_name,
        parent_name,
    )
    if (
        not command
        or any(not isinstance(part, str) or not part for part in command)
        or isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
    ):
        raise ValueError("V2.43.09 invalid subprocess contract")
    parent_path = directory / parent_name
    if parent_path.exists() or parent_path.is_symlink():
        raise FileExistsError(parent_path)

    started = time.monotonic()
    return_code: int | None = None
    timed_out = False
    subprocess_exception = False
    process: Any | None = None
    try:
        process = popen(
            list(command),
            cwd=cwd,
            env=dict(environment),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            return_code = process.wait(timeout=float(timeout_seconds))
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_group(process)
            return_code = process.returncode
        except OSError:
            _terminate_group(process)
            process = None
            subprocess_exception = True
            return_code = None
    except Exception:
        subprocess_exception = True

    child_path = directory / terminal_name
    result_path = directory / result_name
    model_path = directory / model_receipt_name
    transport_path = directory / transport_receipt_name
    child_present = _present(child_path)
    child_valid = _valid(child_path, validate_child_receipt)
    result_present = _present(result_path)
    model_present = _present(model_path)
    transport_present = _present(transport_path)
    receipt = parent_receipt(
        return_code=return_code,
        timed_out=timed_out,
        elapsed_seconds=max(0.0, time.monotonic() - started),
        subprocess_exception=subprocess_exception,
        child_terminal_receipt_present=child_present,
        child_terminal_receipt_valid=child_valid,
        result_envelope_present=result_present,
        result_envelope_valid=_valid(result_path, result_validator),
        model_receipt_present=model_present,
        model_receipt_valid=_valid(model_path, model_receipt_validator),
        transport_receipt_present=transport_present,
        transport_receipt_valid=_valid(
            transport_path, transport_receipt_validator
        ),
    )
    validate_parent_receipt(receipt)
    _new_json(parent_path, receipt)
    return ObservedChildOutcome(
        return_code=return_code,
        timed_out=timed_out,
        subprocess_exception=subprocess_exception,
        receipt=receipt,
    )


__all__ = [
    "CHILD_TERMINAL_NAME",
    "MODEL_RECEIPT_NAME",
    "ObservedChildOutcome",
    "PARENT_EXIT_NAME",
    "RESULT_NAME",
    "TRANSPORT_RECEIPT_NAME",
    "run_child_with_terminal_receipt",
    "run_observed_subprocess",
]
