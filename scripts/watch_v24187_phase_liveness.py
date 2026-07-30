#!/usr/bin/env python3
"""Continuously publish the observation-only V2.41.87 liveness report."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_CONTROL_FILES = {
    "scripts/preregister_v24187_phase_liveness.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/watch_v24187_phase_liveness.py",
    "scripts/audit_v24187_phase_liveness_activation.py",
    "tests/test_preregister_v24187_phase_liveness.py",
    "tests/test_audit_v24187_phase_liveness.py",
    "tests/test_watch_v24187_phase_liveness.py",
    "tests/test_audit_v24187_phase_liveness_activation.py",
}
EXPECTED_ABSENT = {"scripts/__init__.py", "sitecustomize.py", "usercustomize.py"}


def _payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _bootstrap() -> None:
    if __name__ != "__main__" or sys.argv[1:] in (["--help"], ["-h"]):
        return
    if not (
        sys.flags.isolated
        and sys.flags.safe_path
        and sys.flags.no_user_site
        and sys.flags.dont_write_bytecode
    ):
        raise RuntimeError("V2.41.87 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.87 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.87 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw = Path(
        option(
            "--protocol",
            "results/v24187_phase_liveness_preregistration_v1_20260730.json",
        )
    )
    unresolved = raw if raw.is_absolute() else root / raw
    protocol = unresolved.resolve(strict=False)
    expected = (
        root
        / "results/v24187_phase_liveness_preregistration_v1_20260730.json"
    ).resolve(strict=False)
    if (
        root != ROOT.resolve()
        or protocol != expected
        or unresolved.is_symlink()
        or not protocol.is_file()
        or not protocol.is_relative_to(root / "results")
    ):
        raise RuntimeError("V2.41.87 bootstrap protocol is noncanonical")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("role") != "v24187_phase_liveness_preregistration"
        or value.get("protocol_id")
        != "v24187_phase_aware_campaign_liveness_v1"
        or not isinstance(manifest, dict)
        or set(manifest) != EXPECTED_CONTROL_FILES
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
        or set(control.get("must_remain_absent", [])) != EXPECTED_ABSENT
        or any(
            (root / name).exists() or (root / name).is_symlink()
            for name in EXPECTED_ABSENT
        )
        or option("--poll-seconds", "60") != "60"
        or option("--proc-root", "/proc") != "/proc"
    ):
        raise RuntimeError("V2.41.87 bootstrap manifest or execution drifted")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            not target.is_file()
            or target.is_symlink()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.87 bootstrap control bytes drifted")


_bootstrap()
sys.path.insert(0, str(ROOT))

from scripts.audit_v24187_phase_liveness import build_report  # noqa: E402
from scripts.preregister_v24187_phase_liveness import (  # noqa: E402
    DEFAULT_PROTOCOL,
    DEFAULT_STATE,
    validate_protocol,
)


def _target(root: Path, raw: Path, expected: str) -> Path:
    supplied = raw if raw.is_absolute() else root / raw
    target = supplied.resolve(strict=False)
    frozen = (root / expected).resolve(strict=False)
    if (
        target != frozen
        or supplied.is_symlink()
        or not target.is_relative_to(root / "outputs")
    ):
        raise RuntimeError("V2.41.87 state path differs from protocol")
    return target


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary = Path(raw)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def run_once(
    root: Path,
    *,
    protocol: Path = DEFAULT_PROTOCOL,
    state: Path = DEFAULT_STATE,
    proc_root: Path = Path("/proc"),
    now: int | None = None,
) -> dict:
    root = root.resolve()
    verified = validate_protocol(root, protocol)
    execution = verified["value"]["execution"]
    target = _target(root, state, execution["state_path"])
    report = build_report(
        root,
        now=now,
        freshness_seconds=execution["state_freshness_seconds"],
        transition_grace_seconds=execution["transition_grace_seconds"],
        proc_root=proc_root,
        protocol_record={
            "path": str(verified["path"].relative_to(root)),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
    )
    _atomic_json(target, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 60 or args.proc_root != "/proc":
        raise RuntimeError("V2.41.87 execution parameters drifted")
    while True:
        value = run_once(
            Path(args.root),
            protocol=Path(args.protocol),
            state=Path(args.state),
            proc_root=Path(args.proc_root),
        )
        print(
            json.dumps(
                {
                    "role": value["role"],
                    "created_at_unix": value["created_at_unix"],
                    "overall_status": value["overall_status"],
                    "current_phase": value["current_phase"]["phase"],
                    "critical_findings": value["critical_findings"],
                    "degraded_findings": value["degraded_findings"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if args.once:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
