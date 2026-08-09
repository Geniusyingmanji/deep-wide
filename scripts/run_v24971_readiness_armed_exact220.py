#!/usr/bin/env python3
"""Arm, await authorization, and run one label-blind exact-220 forward."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24970_same_process_search_readiness as readiness  # noqa: E402
from deepwide_agent import v24971_readiness_armed_exact220_contract as contract  # noqa: E402
from scripts import run_v24800_exact220 as engine  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as pacing  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def _git(*args: str, check: bool = True) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=check,
    ).stdout.strip()


def _clean_pushed() -> str:
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain") or head != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.49.71 runner requires clean pushed HEAD")
    return head


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.71 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.71 expected JSON object")
    return value


def _publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _head_contains_local(path: Path) -> bool:
    if not _tracked(path):
        return False
    completed = subprocess.run(
        ["git", "show", f"HEAD:{path.as_posix()}"], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    )
    return completed.returncode == 0 and completed.stdout == (ROOT / path).read_bytes()


def _ancestor(parent: str, child: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", parent, child], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_v24791_exact220.py",
        "scripts/run_v24791_exact220_task.py",
        "scripts/run_v24792_exact220.py",
        "scripts/run_v24792_exact220_task.py",
        "scripts/run_v24798_exact220.py",
        "scripts/run_v24798_exact220_task.py",
        "scripts/run_v24635_exact220.py",
        "scripts/run_v24635_exact220_task.py",
        "scripts/run_official_eval_local.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and "python" in parts[1].casefold()
            and int(parts[0]) != os.getpid()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _read_credentials(stream: Any = sys.stdin) -> tuple[str, ...]:
    serialized = stream.read()
    try:
        values = tuple(
            line.strip() for line in serialized.splitlines() if line.strip()
        )
    finally:
        serialized = ""
    if len(values) != contract.TAVILY_KEY_SLOT_CAP or len(set(values)) != len(values):
        raise RuntimeError("V2.49.71 requires exactly 12 distinct credentials on stdin")
    return values


def _pre_arm_barrier() -> tuple[dict[str, Any], str]:
    head = _clean_pushed()
    protocol = contract.validate_protocol(
        ROOT, _read(ROOT / contract.PROTOCOL)
    )
    contract.validate_preaudit(ROOT, _read(ROOT / contract.PREAUDIT))
    required = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        *map(Path, protocol["dependency_manifest"]),
    )
    if not all(_tracked(path) for path in required):
        raise RuntimeError("V2.49.71 arming dependency is not tracked")
    if _active_conflicts():
        raise RuntimeError("V2.49.71 conflicting benchmark or evaluator is active")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    for path in (
        contract.ARMED_RECEIPT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    ):
        if (ROOT / path).exists() or (ROOT / path).is_symlink():
            raise RuntimeError("V2.49.71 arming surface is not pristine")
    if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.49.71 protected watcher drifted before readiness")
    return protocol, head


def _await_execution_start(
    protocol: dict[str, Any],
    armed: dict[str, Any],
) -> dict[str, Any]:
    deadline = armed["authorization_deadline_unix"]
    while int(time.time()) <= deadline:
        path = ROOT / contract.EXECUTION_START
        try:
            if path.is_file() and not path.is_symlink():
                head = _clean_pushed()
                start = contract.validate_execution_start(ROOT, protocol)
                if (
                    head == start["authorization_parent_git_head"]
                    or not _ancestor(start["authorization_parent_git_head"], head)
                    or not _head_contains_local(contract.ARMED_RECEIPT)
                    or not _head_contains_local(contract.EXECUTION_START)
                ):
                    raise RuntimeError("V2.49.71 pushed authorization chain drifted")
                return start
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            pass
        time.sleep(1.0)
    raise TimeoutError("V2.49.71 execution authorization deadline expired")


def _configure_forward(
    credentials: tuple[str, ...],
    receipt: dict[str, Any],
    capability: readiness.SearchReadinessCapability,
    lease_record: dict[str, Any],
) -> None:
    pacing.contract = contract
    pacing.configure()

    def credentials_from_capability(_stream: Any = None) -> tuple[str, ...]:
        nonlocal credentials
        if not credentials:
            credentials = capability.consume(receipt)
        return credentials

    def validate_start(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
        return contract.validate_execution_start(root, protocol)

    @contextmanager
    def held_lease(
        _root: Path,
        *,
        owner: str,
        purpose: str,
        path: Path,
    ) -> Iterator[dict[str, Any]]:
        if (
            owner != contract.LEASE_OWNER
            or purpose != contract.LEASE_PURPOSE
            or path.resolve() != (ROOT / contract.LEASE_PATH).resolve()
        ):
            raise RuntimeError("V2.49.71 nested lease binding drifted")
        yield lease_record

    engine._read_credentials = credentials_from_capability
    engine.validate_execution_start = validate_start
    engine.acquire_deepwide_api_lease = held_lease


def main() -> None:
    credentials = _read_credentials()
    protocol, arming_head = _pre_arm_barrier()
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ) as lease_record:
        temporary = tempfile.TemporaryDirectory(
            prefix=".v24971-readiness-", dir=ROOT / "outputs"
        )
        readiness_root = Path(temporary.name) / "probe"
        readiness_root.mkdir(mode=0o700)
        try:
            receipt, capability = readiness.run_readiness(
                credentials, readiness_root
            )
        finally:
            credentials = ()
            temporary.cleanup()
        if capability is None or receipt["passed"] is not True:
            print(
                json.dumps(
                    {
                        "status": "readiness_rejected_no_benchmark_started",
                        "aggregate": receipt["aggregate"],
                    },
                    sort_keys=True,
                )
            )
            return
        armed = contract.build_armed_receipt(
            ROOT,
            receipt,
            pid=os.getpid(),
            start_ticks=contract.proc_start_ticks(os.getpid()),
            arming_git_head=arming_head,
            now=int(time.time()),
        )
        _publish_new(ROOT / contract.ARMED_RECEIPT, armed)
        print(
            json.dumps(
                {
                    "status": "armed_waiting_execution_start",
                    "path": str(contract.ARMED_RECEIPT),
                    "authorization_deadline_unix": armed[
                        "authorization_deadline_unix"
                    ],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        _await_execution_start(protocol, armed)
        _configure_forward((), receipt, capability, lease_record)
        engine.main()


if __name__ == "__main__":
    main()
