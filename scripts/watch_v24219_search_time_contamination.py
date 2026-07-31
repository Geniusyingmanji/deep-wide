#!/usr/bin/env python3
"""Wait for V2.42.18, then run one offline V2.42.19 STC audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path(
    "results/v24219_search_time_contamination_preregistration_v1_20260731.json"
)
STATE = Path("outputs/v24219_search_time_contamination_watcher_state_v1_20260731.json")


def _bootstrap() -> None:
    if __name__ != "__main__" or sys.argv[1:] in (["--help"], ["-h"]):
        return
    if not (
        sys.flags.isolated
        and sys.flags.safe_path
        and sys.flags.no_user_site
        and sys.flags.dont_write_bytecode
    ):
        raise RuntimeError("V2.42.19 watcher requires python -I -B")
    args = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in args:
            return default
        if args.count(name) != 1 or args.index(name) + 1 >= len(args):
            raise RuntimeError(f"V2.42.19 invalid option: {name}")
        return args[args.index(name) + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw_protocol = Path(option("--protocol", str(PROTOCOL)))
    protocol = raw_protocol if raw_protocol.is_absolute() else root / raw_protocol
    raw_state = Path(option("--state", str(STATE)))
    state = raw_state if raw_state.is_absolute() else root / raw_state
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or state.resolve(strict=False) != (root / STATE).resolve(strict=False)
        or state.is_symlink()
        or option("--poll-seconds", "60") != "60"
        or "--once" in args
    ):
        raise RuntimeError("V2.42.19 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if (
        value.get("protocol_id") != "v24219_post_terminal_label_blind_stc_audit_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != digest
    ):
        raise RuntimeError("V2.42.19 bootstrap protocol is invalid")
    for relative, expected in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != expected
        ):
            raise RuntimeError("V2.42.19 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24219_search_time_contamination import payload_sha256  # noqa: E402
from scripts.activate_v24219_search_time_contamination import validate_activation  # noqa: E402
from scripts.preregister_v24219_search_time_contamination import (  # noqa: E402
    ACTIVATION,
    DETAIL,
    PARENT_STATE,
    PROTOCOL,
    REPORT,
    STATE,
    validate_protocol,
)
from scripts.run_v24219_search_time_contamination import (  # noqa: E402
    FORWARD_BARRIER,
    RESULT,
    file_sha256,
    publish_audit,
    validate_report,
    validate_terminal_authority,
)


def _present(root: Path, relative: Path) -> bool:
    target = root / relative
    return target.exists() or target.is_symlink()


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.19 expected an ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.19 JSON root is not an object")
    return value


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
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


def _seal(path: Path, value: dict[str, Any]) -> None:
    value.pop("state_payload_sha256", None)
    value["state_payload_sha256"] = payload_sha256(value)
    _atomic_json(path, value)


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    if not _present(root, ACTIVATION):
        return None
    value = validate_activation(root, ACTIVATION, protocol_path=PROTOCOL)
    if value["value"]["protocol"]["sha256"] != protocol_sha:
        raise RuntimeError("V2.42.19 activation binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": value["sha256"],
        "watcher_pid": value["value"]["watcher"]["pid"],
        "watcher_start_ticks": value["value"]["watcher"]["start_ticks"],
    }


def _base(
    verified: dict[str, Any], now: int, activation: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24219_search_time_contamination_watcher_state",
        "created_at_unix": now,
        "protocol": {
            "path": str(PROTOCOL),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "parent_safe_state_envelope_opened": False,
        "parent_terminal_result_and_barrier_validated": False,
        "task_manifest_or_evidence_opened": False,
        "audit_started": False,
        "report_created": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "shared_api_lease_acquired": False,
        "forward_result_evaluator_or_watcher_modified": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def _parent_state(root: Path) -> tuple[dict[str, Any], str]:
    state = _read_object(root / PARENT_STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    terminal = state.get("terminal")
    if (
        state.get("role") != "v24218_exact220_executor_watcher_state"
        or terminal not in {True, False}
        or seal != payload_sha256(unsigned)
        or state.get(
            "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing"
        )
        is not False
        or state.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.19 parent state envelope drifted")
    if not terminal:
        return state, "waiting"
    if state.get("status") == "complete_exact220_local_result_released_not_sota":
        return state, "complete"
    return state, "terminal_without_result"


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = PROTOCOL,
    state_path: Path = STATE,
    now: int | None = None,
    publisher=publish_audit,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.19 canonical execution boundary drifted")
    verified = validate_protocol(root, protocol_path)
    target = state_path if state_path.is_absolute() else root / state_path
    activation = _activation(root, verified["sha256"])
    value = _base(verified, int(time.time()) if now is None else int(now), activation)
    if activation is None:
        if _present(root, DETAIL) or _present(root, REPORT):
            raise RuntimeError("V2.42.19 audit output appeared before activation")
        value.update(
            status="waiting_for_execution_activation", reason="activation_absent"
        )
        _seal(target, value)
        return value

    parent, mode = _parent_state(root)
    value["parent_safe_state_envelope_opened"] = True
    value["parent_state"] = {
        "path": str(PARENT_STATE),
        "status": parent.get("status"),
        "terminal": parent.get("terminal"),
        "contents_emitted": False,
    }
    if mode == "waiting":
        if _present(root, DETAIL) or _present(root, REPORT):
            raise RuntimeError("V2.42.19 audit output appeared before parent terminal")
        value.update(
            status="waiting_for_v24218_exact220_terminal",
            reason="parent_preterminal",
        )
        _seal(target, value)
        return value
    if mode == "terminal_without_result":
        if _present(root, DETAIL) or _present(root, REPORT):
            raise RuntimeError("V2.42.19 audit output appeared after parent failure")
        value.update(
            status="terminal_parent_without_exact220_result",
            reason="parent_did_not_release_exact220_result",
            terminal=True,
        )
        _seal(target, value)
        return value

    authority = validate_terminal_authority(root)
    value["parent_terminal_result_and_barrier_validated"] = True
    if _present(root, REPORT):
        report = validate_report(root)
    else:
        value["audit_started"] = True
        value["task_manifest_or_evidence_opened"] = True
        report = publisher(root)
    value.update(
        status="complete_post_terminal_contamination_audit",
        reason="sealed_exact220_parent_and_label_blind_audit_terminal",
        terminal=True,
        task_manifest_or_evidence_opened=True,
        audit_started=True,
        report_created=True,
        report={"path": str(REPORT), "sha256": file_sha256(root / REPORT)},
        tasks_scanned=report["aggregate"]["tasks_scanned"],
        confirmed_eal=None,
    )
    _seal(target, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(PROTOCOL))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 60:
        raise RuntimeError("V2.42.19 watcher parameters drifted")
    while True:
        value = run_cycle(
            Path(args.root),
            protocol_path=Path(args.protocol),
            state_path=Path(args.state),
        )
        print(
            json.dumps(
                {
                    "role": value["role"],
                    "status": value["status"],
                    "reason": value["reason"],
                    "report_created": value["report_created"],
                }
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
