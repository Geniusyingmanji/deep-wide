#!/usr/bin/env python3
"""Publish one hierarchical successor decision from status envelopes only."""

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
PROTOCOL = Path("results/v24200_hierarchical_successor_preregistration_v1_20260731.json")
STATE = Path("outputs/v24200_hierarchical_successor_watcher_state_v1_20260731.json")


def _payload_sha(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _bootstrap() -> None:
    if __name__ != "__main__" or sys.argv[1:] in (["--help"], ["-h"]):
        return
    if not (
        sys.flags.isolated
        and sys.flags.safe_path
        and sys.flags.no_user_site
        and sys.flags.dont_write_bytecode
    ):
        raise RuntimeError("V2.42.00 watcher requires python -I -B")
    args = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in args:
            return default
        if args.count(name) != 1 or args.index(name) + 1 >= len(args):
            raise RuntimeError(f"V2.42.00 invalid option: {name}")
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
        raise RuntimeError("V2.42.00 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id") != "v24200_hierarchical_baseline_integrated_package_gate_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.00 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if target.is_symlink() or not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise RuntimeError("V2.42.00 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import (  # noqa: E402
    derive_successor_decision,
    payload_sha256,
)
from scripts.activate_v24200_successor import validate_activation  # noqa: E402
from scripts.preregister_v24200_successor import (  # noqa: E402
    ACTIVATION,
    DECISION_RECEIPT,
    ENTROPY_ROOT,
    OUTPUT,
    SOURCE_PATHS,
    publish_new,
    read_object,
    validate_protocol,
)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
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


def _present(root: Path, path: Path) -> bool:
    return (root / path).exists() or (root / path).is_symlink()


def _base(verified: dict[str, Any], *, now: int, activation: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24200_hierarchical_successor_watcher_state",
        "created_at_unix": now,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "source_status_envelopes_opened": False,
        "source_numeric_metrics_reports_predictions_or_aggregates_read": False,
        "hierarchical_baseline_selected": False,
        "eligible_components_selected": False,
        "integrated_package_built_or_opened": False,
        "package_gate_evaluated_or_launched": False,
        "decision_receipt_created": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "terminal": False,
    }


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    if not _present(root, ACTIVATION):
        return None
    verified = validate_activation(root, ACTIVATION, protocol_path=OUTPUT)
    if verified["value"]["protocol"]["sha256"] != protocol_sha:
        raise RuntimeError("V2.42.00 activation binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": verified["value"]["watcher"]["pid"],
        "watcher_start_ticks": verified["value"]["watcher"]["start_ticks"],
    }


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.00 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, now=created, activation=activation)
    if activation is None:
        if _present(root, DECISION_RECEIPT):
            raise RuntimeError("V2.42.00 decision appeared before activation")
        value.update(status="waiting_for_execution_activation", reason="activation_absent")
    else:
        states = {name: read_object(root / path) for name, path in SOURCE_PATHS.items()}
        entropy_root = read_object(root / ENTROPY_ROOT)
        value["source_status_envelopes_opened"] = True
        decision, statuses = derive_successor_decision(states, entropy_root=entropy_root)
        value["source_status_classifications"] = statuses
        if decision is None:
            if _present(root, DECISION_RECEIPT):
                raise RuntimeError("V2.42.00 decision appeared before all sources terminal")
            value.update(status="waiting_for_quality_chain_terminal", reason="one_or_more_sources_waiting")
        else:
            value["hierarchical_baseline_selected"] = True
            value["eligible_components_selected"] = True
            receipt: dict[str, Any] = {
                "artifact_version": 1,
                "role": "v24200_hierarchical_successor_decision",
                "created_at_unix": created,
                "label_blind": True,
                "protocol": {
                    "path": str(OUTPUT),
                    "sha256": verified["sha256"],
                    "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
                },
                "source_status_classifications": statuses,
                "decision": decision,
                "integrated_package_built_or_opened": False,
                "package_gate_evaluated_or_launched": False,
                "benchmark_forward_or_full220_launch_allowed": False,
                "mapping_gold_category_question_type_evaluator_score_read": False,
                "leaderboard_submission_or_sota_claim": False,
            }
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            path = root / DECISION_RECEIPT
            if path.exists():
                if read_object(path) != receipt:
                    raise RuntimeError("V2.42.00 decision receipt differs from replay")
            else:
                publish_new(path, receipt)
            value.update(
                terminal=True,
                status="complete_hierarchical_successor_decision",
                reason="entire_quality_chain_terminal",
                decision_receipt_created=True,
                decision_receipt={"path": str(DECISION_RECEIPT), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
            )
    value["state_payload_sha256"] = payload_sha256(value)
    target = state_path if state_path.is_absolute() else root / state_path
    _atomic_json(target, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 60:
        raise RuntimeError("V2.42.00 poll interval drifted")
    while True:
        value = run_cycle(Path(args.root), protocol_path=Path(args.protocol), state_path=Path(args.state))
        print(json.dumps({k: value[k] for k in ("role", "created_at_unix", "status", "reason", "terminal")}), flush=True)
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
