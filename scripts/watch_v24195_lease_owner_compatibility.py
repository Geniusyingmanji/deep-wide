#!/usr/bin/env python3
"""Continuously publish the read-only V2.41.95 compatibility report."""

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
PROTOCOL = Path(
    "results/v24195_lease_owner_compatibility_preregistration_v1_20260731.json"
)
STATE = Path(
    "outputs/v24195_lease_owner_compatibility_watcher_state_v1_20260731.json"
)


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
        raise RuntimeError("V2.41.95 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.95 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.95 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw = Path(option("--protocol", str(PROTOCOL)))
    protocol = raw if raw.is_absolute() else root / raw
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or option("--poll-seconds", "10") != "10"
        or option("--proc-root", "/proc") != "/proc"
    ):
        raise RuntimeError("V2.41.95 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id") != "v24195_v24194_lease_owner_compatibility_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.95 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.95 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v24195_lease_owner_compatibility import build_report  # noqa: E402
from scripts.preregister_v24195_lease_owner_compatibility import (  # noqa: E402
    validate_protocol,
)


def _target(root: Path, raw: Path) -> Path:
    supplied = raw if raw.is_absolute() else root / raw
    target = supplied.resolve(strict=False)
    if (
        target != (root / STATE).resolve(strict=False)
        or supplied.is_symlink()
        or (root / "outputs") not in (target, *target.parents)
    ):
        raise RuntimeError("V2.41.95 state path is noncanonical")
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
    protocol: Path = PROTOCOL,
    state: Path = STATE,
    proc_root: Path = Path("/proc"),
    now: int | None = None,
) -> dict:
    root = root.resolve()
    validate_protocol(root, protocol)
    target = _target(root, state)
    value = build_report(root, protocol, now=now, proc_root=proc_root)
    _atomic_json(target, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(PROTOCOL))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 10 or args.proc_root != "/proc":
        raise RuntimeError("V2.41.95 execution parameters drifted")
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
                    "compatibility_mode": value["compatibility"]["mode"],
                    "critical_findings": value["critical_findings"],
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
