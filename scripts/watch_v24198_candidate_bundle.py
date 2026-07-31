#!/usr/bin/env python3
"""Wait for independent selection and capacity, then compile a bundle only."""

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
PROTOCOL = Path("results/v24198_candidate_bundle_preregistration_v1_20260731.json")
STATE_PATH = Path("outputs/v24198_candidate_bundle_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.41.98 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.98 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.98 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    raw_protocol = Path(option("--protocol", str(PROTOCOL)))
    protocol = raw_protocol if raw_protocol.is_absolute() else root / raw_protocol
    raw_state = Path(option("--state", str(STATE_PATH)))
    state = raw_state if raw_state.is_absolute() else root / raw_state
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or state.resolve(strict=False) != (root / STATE_PATH).resolve(strict=False)
        or state.is_symlink()
        or option("--poll-seconds", "60") != "60"
        or "--once" in arguments
    ):
        raise RuntimeError("V2.41.98 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24198_selected_candidate_bundle_compiler_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.98 watcher protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.98 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24197_parallel_all220 import (  # noqa: E402
    _object_snapshot,
    file_sha256,
    load_capacity_pair,
    payload_sha256,
)
from deepwide_agent.v24198_candidate_bundle import (  # noqa: E402
    BUNDLE,
    GO_RECEIPT,
    HANDOFF,
    QUALITY_TERMINAL_RECEIPT,
    SELECTION_PROTOCOL,
    build_bundle,
    build_go_receipt,
    payload_file_sha256,
    validate_handoff,
    validate_published_outputs,
)
from scripts.activate_v24198_candidate_bundle import validate_activation  # noqa: E402
from scripts.preregister_v24198_candidate_bundle import (  # noqa: E402
    ACTIVATION,
    CAPACITY_FREEZE,
    CAPACITY_REPORT,
    OUTPUT,
    STATE,
    publish_new,
    read_object,
    validate_protocol,
)


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


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    verified = validate_activation(root, ACTIVATION, protocol_path=OUTPUT)
    value = verified["value"]
    if value.get("protocol", {}).get("sha256") != protocol_sha:
        raise RuntimeError("V2.41.98 activation protocol binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "compiler_pid": value["compiler"]["pid"],
        "compiler_start_ticks": value["compiler"]["start_ticks"],
    }


def _base_state(
    verified: dict[str, Any],
    *,
    created: int,
    activation: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24198_candidate_bundle_watcher_state",
        "created_at_unix": created,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "capacity_pair_opened": False,
        "selector_protocol_opened": False,
        "quality_terminal_receipt_opened": False,
        "selected_candidate_handoff_opened": False,
        "candidate_publication_bytes_hashed": False,
        "candidate_freezes_opened": False,
        "candidate_manifest_bytes_hashed": False,
        "go_receipt_created": False,
        "candidate_bundle_created": False,
        "candidate_selection_or_gate_evaluated": False,
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


def _target(root: Path, raw: Path, expected: str) -> Path:
    unresolved = raw if raw.is_absolute() else root / raw
    target = unresolved.resolve(strict=False)
    if (
        target != (root / expected).resolve(strict=False)
        or unresolved.is_symlink()
        or not target.is_relative_to((root / "outputs").resolve())
    ):
        raise RuntimeError("V2.41.98 state path is noncanonical")
    return target


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _compile(
    root: Path,
    verified: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, int], dict[str, Any], dict[str, str]]:
    capacity, capacity_freeze, snapshots = load_capacity_pair(
        root,
        report_path=str(CAPACITY_REPORT),
        freeze_path=str(CAPACITY_FREEZE),
        protocol_sha256=verified["value"]["capacity_contract"][
            "parent_protocol_sha256"
        ],
    )
    handoff, handoff_sha = _object_snapshot(root / HANDOFF)
    selected = validate_handoff(
        root,
        handoff,
        handoff_path=str(HANDOFF),
        handoff_sha256=handoff_sha,
        compiler_protocol_sha256=verified["sha256"],
        capacity_freeze=capacity_freeze,
    )
    go = build_go_receipt(selected)
    bundle = build_bundle(
        selected,
        capacity_freeze_path=str(CAPACITY_FREEZE),
        capacity_freeze_sha256=snapshots["freeze_sha256"],
        go_receipt_path=str(GO_RECEIPT),
        go_receipt_sha256=payload_file_sha256(go),
    )
    return selected, go, bundle, capacity, capacity_freeze, snapshots


def run_cycle(
    root: Path,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.98 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    state_target = _target(
        root,
        state_path,
        verified["value"]["execution"]["state_path"],
    )
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base_state(verified, created=created, activation=activation)
    go_path = root / GO_RECEIPT
    bundle_path = root / BUNDLE
    if activation is None:
        if _present(root, GO_RECEIPT) or _present(root, BUNDLE):
            raise RuntimeError("V2.41.98 outputs appeared before activation")
        value.update(
            status="waiting_for_execution_activation",
            reason="identity_bound_bundle_compiler_activation_absent",
        )
    elif not _present(root, CAPACITY_REPORT):
        if _present(root, CAPACITY_FREEZE):
            raise RuntimeError("V2.41.98 capacity freeze exists without report")
        value.update(
            status="waiting_for_capacity_freeze",
            reason="v24196_capacity_pair_absent",
        )
    elif not _present(root, CAPACITY_FREEZE):
        value.update(
            status="waiting_for_capacity_freeze",
            reason="v24196_capacity_report_present_freeze_absent",
        )
    else:
        capacity, capacity_freeze, snapshots = load_capacity_pair(
            root,
            report_path=str(CAPACITY_REPORT),
            freeze_path=str(CAPACITY_FREEZE),
            protocol_sha256=verified["value"]["capacity_contract"][
                "parent_protocol_sha256"
            ],
        )
        value["capacity_pair_opened"] = True
        if capacity["selected"] <= 0:
            value.update(
                status="terminal_capacity_no_go_no_bundle",
                reason="v24196_serial_probe_failed",
                terminal=True,
            )
        elif not _present(root, SELECTION_PROTOCOL):
            if any(
                _present(root, path)
                for path in (QUALITY_TERMINAL_RECEIPT, HANDOFF, GO_RECEIPT, BUNDLE)
            ):
                raise RuntimeError("V2.41.98 downstream selection appeared before selector")
            value.update(
                status="waiting_for_selector_preregistration",
                reason="independent_candidate_selection_protocol_absent",
            )
        elif not _present(root, QUALITY_TERMINAL_RECEIPT):
            if any(_present(root, path) for path in (HANDOFF, GO_RECEIPT, BUNDLE)):
                raise RuntimeError("V2.41.98 handoff appeared before terminal selection")
            value.update(
                status="waiting_for_quality_chain_terminal_selection",
                reason="selector_exists_but_terminal_receipt_absent",
            )
        elif not _present(root, HANDOFF):
            if _present(root, GO_RECEIPT) or _present(root, BUNDLE):
                raise RuntimeError("V2.41.98 output appeared before selected handoff")
            value.update(
                status="waiting_for_selected_candidate_handoff",
                reason="terminal_selection_exists_but_integrated_handoff_absent",
            )
        else:
            selected, go, bundle, replay_capacity, replay_freeze, replay_snapshots = _compile(
                root, verified
            )
            if (
                replay_capacity != capacity
                or replay_freeze != capacity_freeze
                or replay_snapshots != snapshots
            ):
                raise RuntimeError("V2.41.98 capacity pair changed during compilation")
            if (bundle_path.exists() or bundle_path.is_symlink()) and not (
                go_path.exists() or go_path.is_symlink()
            ):
                raise RuntimeError("V2.41.98 bundle appeared before GO receipt")
            value.update(
                selector_protocol_opened=True,
                quality_terminal_receipt_opened=True,
                selected_candidate_handoff_opened=True,
                candidate_publication_bytes_hashed=True,
                candidate_freezes_opened=True,
            )
            if go_path.exists() or go_path.is_symlink():
                if read_object(go_path) != go:
                    raise RuntimeError("V2.41.98 existing GO receipt differs from replay")
            else:
                publish_new(go_path, go)
            value["go_receipt_created"] = True
            if file_sha256(go_path) != payload_file_sha256(go):
                raise RuntimeError("V2.41.98 GO receipt bytes differ from replay")
            candidate = validate_published_outputs(
                root,
                bundle=bundle,
                bundle_sha256=payload_file_sha256(bundle),
                capacity=capacity,
                capacity_freeze=capacity_freeze,
                capacity_freeze_path=str(CAPACITY_FREEZE),
                capacity_freeze_sha256=snapshots["freeze_sha256"],
            )
            value["candidate_manifest_bytes_hashed"] = True
            if bundle_path.exists() or bundle_path.is_symlink():
                if read_object(bundle_path) != bundle:
                    raise RuntimeError("V2.41.98 existing bundle differs from replay")
            else:
                publish_new(bundle_path, bundle)
            validate_published_outputs(
                root,
                bundle=read_object(bundle_path),
                bundle_sha256=file_sha256(bundle_path),
                capacity=capacity,
                capacity_freeze=capacity_freeze,
                capacity_freeze_path=str(CAPACITY_FREEZE),
                capacity_freeze_sha256=snapshots["freeze_sha256"],
            )
            value.update(
                status="complete_candidate_bundle_frozen",
                reason="independent_selection_capacity_and_candidate_live_validated",
                candidate_bundle_created=True,
                terminal=True,
                selected_candidate={
                    "target_name": candidate["target_name"],
                    "pipeline_version": candidate["pipeline_version"],
                    "state_schema_version": candidate["state_schema_version"],
                    "candidate_method_contract_sha256": candidate[
                        "candidate_method_contract_sha256"
                    ],
                },
                go_receipt={"path": str(GO_RECEIPT), "sha256": file_sha256(go_path)},
                bundle={"path": str(BUNDLE), "sha256": file_sha256(bundle_path)},
            )
    value["state_payload_sha256"] = payload_sha256(value)
    _atomic_json(state_target, value)
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
        raise RuntimeError("V2.41.98 poll interval drifted")
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
                    "created_at_unix": value["created_at_unix"],
                    "status": value["status"],
                    "reason": value["reason"],
                    "candidate_bundle_created": value["candidate_bundle_created"],
                    "benchmark_forward_or_full220_launch_allowed": value[
                        "benchmark_forward_or_full220_launch_allowed"
                    ],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
