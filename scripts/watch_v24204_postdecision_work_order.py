#!/usr/bin/env python3
"""Select one frozen V2.42.04 work order after V2.42.00 terminates."""

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
PROTOCOL = Path("results/v24204_postdecision_work_order_preregistration_v1_20260731.json")
STATE = Path("outputs/v24204_postdecision_work_order_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.42.04 watcher requires python -I -B")
    args = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in args:
            return default
        if args.count(name) != 1 or args.index(name) + 1 >= len(args):
            raise RuntimeError(f"V2.42.04 invalid option: {name}")
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
        raise RuntimeError("V2.42.04 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id") != "v24204_content_free_postdecision_work_order_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.04 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.04 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import (  # noqa: E402
    SOURCE_ORDER,
    decision_from_statuses,
    payload_sha256,
)
from deepwide_agent.v24204_postdecision_work_order import (  # noqa: E402
    reject_forbidden_metadata,
    select_work_order,
)
from scripts.activate_v24204_postdecision_work_order import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24204_postdecision_work_order import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PARENT_DECISION,
    PARENT_PROTOCOL,
    PARENT_PROTOCOL_SHA256,
    PARENT_STATE,
    SELECTED_WORK_ORDER,
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


def _present(root: Path, path: Path) -> bool:
    return (root / path).exists() or (root / path).is_symlink()


def _base(
    verified: dict[str, Any], *, now: int, activation: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24204_postdecision_work_order_watcher_state",
        "created_at_unix": now,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "execution_activation": activation,
        "parent_safe_state_envelope_opened": False,
        "parent_content_free_decision_receipt_opened": False,
        "parent_numeric_metrics_reports_predictions_or_aggregates_read": False,
        "selected_work_order_published": False,
        "identity_handoff_selected": False,
        "nonempty_blocked_work_order_selected": False,
        "candidate_code_built_merged_or_materialized": False,
        "component_implementation_publisher_invoked": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
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
        raise RuntimeError("V2.42.04 activation binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": verified["value"]["watcher"]["pid"],
        "watcher_start_ticks": verified["value"]["watcher"]["start_ticks"],
    }


def _parent_state(root: Path) -> tuple[dict[str, Any], bool]:
    state = read_object(root / PARENT_STATE)
    reject_forbidden_metadata(state)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "source_numeric_metrics_reports_predictions_or_aggregates_read",
        "integrated_package_built_or_opened",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    terminal = state.get("terminal")
    if (
        state.get("role") != "v24200_hierarchical_successor_watcher_state"
        or state.get("protocol", {}).get("path") != str(PARENT_PROTOCOL)
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or state.get("source_status_envelopes_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or terminal not in {True, False}
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.04 parent safe state envelope drifted")
    if terminal is False:
        if (
            state.get("status") != "waiting_for_quality_chain_terminal"
            or state.get("hierarchical_baseline_selected") is not False
            or state.get("eligible_components_selected") is not False
            or state.get("decision_receipt_created") is not False
        ):
            raise RuntimeError("V2.42.04 parent preterminal state drifted")
    else:
        if (
            state.get("status") != "complete_hierarchical_successor_decision"
            or state.get("hierarchical_baseline_selected") is not True
            or state.get("eligible_components_selected") is not True
            or state.get("decision_receipt_created") is not True
        ):
            raise RuntimeError("V2.42.04 parent terminal state drifted")
    return state, bool(terminal)


def _parent_decision(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = read_object(root / PARENT_DECISION)
    reject_forbidden_metadata(receipt)
    unsigned = dict(receipt)
    seal = unsigned.pop("receipt_payload_sha256", None)
    statuses = receipt.get("source_status_classifications")
    decision = receipt.get("decision")
    if (
        receipt.get("role") != "v24200_hierarchical_successor_decision"
        or receipt.get("label_blind") is not True
        or receipt.get("protocol", {}).get("path") != str(PARENT_PROTOCOL)
        or receipt.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or set(statuses or {}) != set(SOURCE_ORDER)
        or any(value not in {"go", "no_go"} for value in (statuses or {}).values())
        or not isinstance(decision, dict)
        or decision_from_statuses(statuses) != decision
        or receipt.get("integrated_package_built_or_opened") is not False
        or receipt.get("package_gate_evaluated_or_launched") is not False
        or receipt.get("benchmark_forward_or_full220_launch_allowed") is not False
        or receipt.get("mapping_gold_category_question_type_evaluator_score_read")
        is not False
        or receipt.get("leaderboard_submission_or_sota_claim") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.04 parent decision receipt drifted")
    return receipt, select_work_order(decision)


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.04 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, now=created, activation=activation)
    if activation is None:
        if _present(root, SELECTED_WORK_ORDER):
            raise RuntimeError("V2.42.04 selected work order appeared before activation")
        value.update(status="waiting_for_execution_activation", reason="activation_absent")
    else:
        parent_state, parent_terminal = _parent_state(root)
        value["parent_safe_state_envelope_opened"] = True
        value["parent_state"] = {
            "path": str(PARENT_STATE),
            "status": parent_state["status"],
            "terminal": parent_terminal,
            "contents_emitted": False,
        }
        if not parent_terminal:
            if _present(root, SELECTED_WORK_ORDER):
                raise RuntimeError("V2.42.04 selected work order appeared before parent terminal")
            value.update(
                status="waiting_for_v24200_terminal_decision",
                reason=(
                    "parent_decision_path_present_waiting_for_terminal_state_commit"
                    if _present(root, PARENT_DECISION)
                    else "parent_quality_chain_preterminal"
                ),
            )
        else:
            receipt, work_order = _parent_decision(root)
            value["parent_content_free_decision_receipt_opened"] = True
            selected: dict[str, Any] = {
                "artifact_version": 1,
                "role": "v24204_selected_postdecision_work_order",
                "created_at_unix": created,
                "label_blind": True,
                "protocol": {
                    "path": str(OUTPUT),
                    "sha256": verified["sha256"],
                    "decision_contract_sha256": verified["value"][
                        "decision_contract_sha256"
                    ],
                },
                "parent_decision": {
                    "path": str(PARENT_DECISION),
                    "sha256": hashlib.sha256(
                        (root / PARENT_DECISION).read_bytes()
                    ).hexdigest(),
                    "receipt_payload_sha256": receipt["receipt_payload_sha256"],
                    "decision_payload_sha256": receipt["decision"][
                        "decision_payload_sha256"
                    ],
                },
                "selected_work_order": work_order,
                "candidate_code_built_merged_or_materialized": False,
                "component_implementation_publisher_invoked": False,
                "package_gate_evaluated_or_launched": False,
                "shared_api_lease_acquired": False,
                "network_model_search_fetch_evaluator_or_api_called": False,
                "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
                "benchmark_forward_or_full220_launch_allowed": False,
                "leaderboard_submission_or_sota_claim": False,
            }
            selected["selected_payload_sha256"] = payload_sha256(selected)
            target = root / SELECTED_WORK_ORDER
            if target.exists():
                if read_object(target) != selected:
                    raise RuntimeError("V2.42.04 selected work order differs from replay")
            else:
                publish_new(target, selected)
            identity = work_order["identity_handoff_only"]
            value.update(
                terminal=True,
                status=(
                    "complete_identity_handoff_work_order"
                    if identity
                    else "complete_blocked_nonempty_integration_work_order"
                ),
                reason=(
                    "byte_exact_baseline_identity_handoff_selected"
                    if identity
                    else "selected_components_require_separate_publications_and_joint_audit"
                ),
                selected_work_order_published=True,
                identity_handoff_selected=identity,
                nonempty_blocked_work_order_selected=not identity,
                selected_work_order={
                    "path": str(SELECTED_WORK_ORDER),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "disposition": work_order["disposition"],
                    "contents_emitted": False,
                },
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
        raise RuntimeError("V2.42.04 poll interval drifted")
    while True:
        value = run_cycle(
            Path(args.root),
            protocol_path=Path(args.protocol),
            state_path=Path(args.state),
        )
        print(
            json.dumps(
                {
                    key: value[key]
                    for key in ("role", "created_at_unix", "status", "reason", "terminal")
                }
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
