#!/usr/bin/env python3
"""Select a predeclared integrated slot from terminal status envelopes only."""

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
    "results/v24199_candidate_selector_controller_preregistration_v1_20260731.json"
)
SELECTOR_PROTOCOL = Path(
    "results/v24198_selected_candidate_selector_preregistration_v1_20260731.json"
)
STATE = Path("outputs/v24199_candidate_selector_watcher_state_v1_20260731.json")
TERMINAL_RECEIPT = Path(
    "results/v24198_selected_candidate_terminal_receipt_v1_20260731.json"
)
SELECTED_HANDOFF = Path(
    "results/v24198_selected_candidate_handoff_v1_20260731.json"
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
        raise RuntimeError("V2.41.99 watcher requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.99 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.99 option lacks a value: {name}")
        return arguments[index + 1]

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
        or "--once" in arguments
    ):
        raise RuntimeError("V2.41.99 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24199_outcome_before_inheritance_selector_controller_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.99 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.99 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24197_parallel_all220 import (  # noqa: E402
    file_sha256,
    load_capacity_pair,
    payload_sha256,
)
from deepwide_agent.v24198_candidate_bundle import (  # noqa: E402
    CANONICAL_ID_FILES,
    COMPILER_PROTOCOL,
)
from deepwide_agent.v24199_candidate_selector import (  # noqa: E402
    ENTROPY_ROOT_SOURCE,
    QUALITY_SOURCES,
    derive_terminal_vector,
    object_snapshot,
    slot_for_vector,
    validate_candidate_handoff,
)
from scripts.activate_v24199_candidate_selector import validate_activation  # noqa: E402
from scripts.preregister_v24199_candidate_selector import (  # noqa: E402
    ACTIVATION,
    CAPACITY_FREEZE,
    CAPACITY_PROTOCOL_SHA256,
    CAPACITY_REPORT,
    OUTPUT,
    publish_new,
    read_object,
    validate_protocol,
    validate_selector,
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


def _target(root: Path, raw: Path, expected: Path, parent: str) -> Path:
    unresolved = raw if raw.is_absolute() else root / raw
    target = unresolved.resolve(strict=False)
    if (
        target != (root / expected).resolve(strict=False)
        or unresolved.is_symlink()
        or not target.is_relative_to((root / parent).resolve())
    ):
        raise RuntimeError("V2.41.99 path is noncanonical")
    return target


def _present(root: Path, path: str | Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _activation(root: Path, protocol_sha: str) -> dict[str, Any] | None:
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return None
    verified = validate_activation(root, ACTIVATION, protocol_path=OUTPUT)
    value = verified["value"]
    if value.get("protocol", {}).get("sha256") != protocol_sha:
        raise RuntimeError("V2.41.99 activation protocol binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "selector_pid": value["selector"]["pid"],
        "selector_start_ticks": value["selector"]["start_ticks"],
    }


def _base_state(
    verified: dict[str, Any], *, created: int, activation: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24199_candidate_selector_watcher_state",
        "created_at_unix": created,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "selector_protocol": verified["value"]["selector_protocol"],
        "execution_activation": activation,
        "quality_status_envelopes_opened": False,
        "quality_numeric_values_reports_predictions_or_aggregates_read": False,
        "capacity_pair_opened": False,
        "candidate_slot_selected": False,
        "candidate_publication_opened": False,
        "candidate_handoff_opened": False,
        "candidate_freezes_opened": False,
        "candidate_built_merged_or_frozen_by_selector": False,
        "terminal_receipt_created": False,
        "selected_handoff_created": False,
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


def _quality_states(root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    states = {
        name: object_snapshot(root / spec["path"])[0]
        for name, spec in QUALITY_SOURCES.items()
    }
    entropy_root = object_snapshot(root / ENTROPY_ROOT_SOURCE["path"])[0]
    return states, entropy_root


def _terminal_receipt(
    selected: dict[str, Any],
    *,
    created: int,
    selector_reference: dict[str, str],
    quality_sources: dict[str, dict[str, Any]],
    capacity_reference: dict[str, str],
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24198_selected_candidate_terminal_receipt",
        "created_at_unix": created,
        "label_blind": True,
        "decision": "go",
        "selector_protocol": selector_reference,
        "all_required_quality_gates_terminal": True,
        "candidate_selection_rule_live_replayed": True,
        "selected_candidate_publication": selected["publication"],
        "selected_pipeline_version": selected["pipeline_version"],
        "selected_state_schema_version": selected["state_schema_version"],
        "selected_candidate_method_contract_sha256": selected[
            "candidate_method_contract_sha256"
        ],
        "canonical_all220_integrated_freezes_ready": True,
        "benchmark_forward_launch_allowed": False,
        "mapping_gold_category_question_type_evaluator_score_read_by_bundle_compiler": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["terminal_receipt_payload_sha256"] = payload_sha256(value)
    return value


def _selected_handoff(
    selected: dict[str, Any],
    terminal_reference: dict[str, str],
    *,
    created: int,
    selector_reference: dict[str, str],
    compiler_protocol_sha256: str,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24198_selected_candidate_handoff",
        "created_at_unix": created,
        "label_blind": True,
        "decision": "go",
        "compiler_protocol": {
            "path": str(COMPILER_PROTOCOL),
            "sha256": compiler_protocol_sha256,
        },
        "selection_protocol": selector_reference,
        "quality_chain_terminal_receipt": terminal_reference,
        "candidate_publication": selected["publication"],
        "selection_was_frozen_before_bundle_compilation": True,
        "candidate_selected_by_predeclared_quality_gates": True,
        "selection_not_made_by_bundle_compiler": True,
        "target_name": selected["target_name"],
        "pipeline_version": selected["pipeline_version"],
        "state_schema_version": selected["state_schema_version"],
        "candidate_method_contract_sha256": selected[
            "candidate_method_contract_sha256"
        ],
        "model": selected["model"],
        "shard_order": ["test_s01", "test_s02", "test_s03", "devval"],
        "shards": selected["shards"],
        "selected_total": 220,
        "all_output_directories_absent_at_handoff": True,
        "same_pipeline_code_prompt_search_budget_threshold": True,
        "forward_failure_scored_as_zero": True,
        "resume_or_selective_rerun_allowed": False,
        "dev64_is_gate_not_primary_result": True,
        "all220_is_primary_result": True,
        "search_capacity_preflight_required": True,
        "benchmark_forward_launch_allowed": False,
        "separate_executor_activation_required": True,
        "runtime_mapping_gold_category_question_type_evaluator_score_read": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["handoff_payload_sha256"] = payload_sha256(value)
    return value


def run_cycle(
    root: Path,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.99 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    selector_verified = validate_selector(root, SELECTOR_PROTOCOL)
    if selector_verified["sha256"] != verified["value"]["selector_protocol"]["sha256"]:
        raise RuntimeError("V2.41.99 selector protocol drifted")
    state_target = _target(root, state_path, STATE, "outputs")
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base_state(verified, created=created, activation=activation)
    outputs_present = _present(root, TERMINAL_RECEIPT) or _present(root, SELECTED_HANDOFF)
    if activation is None:
        if outputs_present:
            raise RuntimeError("V2.41.99 outputs appeared before activation")
        value.update(
            status="waiting_for_execution_activation",
            reason="identity_bound_selector_activation_absent",
        )
    elif not _present(root, CAPACITY_REPORT):
        if _present(root, CAPACITY_FREEZE) or outputs_present:
            raise RuntimeError("V2.41.99 capacity/output order is invalid")
        value.update(
            status="waiting_for_capacity_freeze",
            reason="v24196_capacity_pair_absent",
        )
    elif not _present(root, CAPACITY_FREEZE):
        if outputs_present:
            raise RuntimeError("V2.41.99 outputs appeared before capacity freeze")
        value.update(
            status="waiting_for_capacity_freeze",
            reason="v24196_capacity_report_present_freeze_absent",
        )
    else:
        capacity, capacity_freeze, snapshots = load_capacity_pair(
            root,
            report_path=str(CAPACITY_REPORT),
            freeze_path=str(CAPACITY_FREEZE),
            protocol_sha256=CAPACITY_PROTOCOL_SHA256,
        )
        value["capacity_pair_opened"] = True
        if capacity["selected"] <= 0:
            if outputs_present:
                raise RuntimeError("V2.41.99 selector outputs exist after capacity NO-GO")
            value.update(
                status="terminal_capacity_no_go_no_selection",
                reason="v24196_serial_probe_failed",
                terminal=True,
            )
        else:
            states, entropy_root = _quality_states(root)
            value["quality_status_envelopes_opened"] = True
            vector, statuses = derive_terminal_vector(
                states, entropy_root=entropy_root
            )
            value["quality_statuses"] = statuses
            if vector is None:
                if outputs_present:
                    raise RuntimeError("V2.41.99 outputs appeared before quality terminal")
                value.update(
                    status="waiting_for_entire_quality_chain_terminal",
                    reason="one_or_more_predeclared_quality_statuses_waiting",
                )
            else:
                slots = verified["value"]["inheritance_contract"]["slot_manifest"]
                slot_name = slot_for_vector(slots, vector)
                slot = slots[slot_name]
                value.update(
                    candidate_slot_selected=True,
                    selected_slot=slot_name,
                    terminal_feature_vector=vector,
                )
                publication_present = _present(
                    root, slot["candidate_publication_path"]
                )
                handoff_present = _present(root, slot["candidate_handoff_path"])
                if not publication_present:
                    if handoff_present or outputs_present:
                        raise RuntimeError("V2.41.99 handoff/output appeared before slot publication")
                    value.update(
                        status="waiting_for_integrated_candidate_slot",
                        reason="selected_slot_publication_absent_no_fallback",
                    )
                elif not handoff_present:
                    if outputs_present:
                        raise RuntimeError("V2.41.99 selector output appeared before slot handoff")
                    value.update(
                        status="waiting_for_integrated_candidate_slot",
                        reason="selected_slot_handoff_absent_no_fallback",
                    )
                else:
                    selected = validate_candidate_handoff(
                        root,
                        slot_name=slot_name,
                        slot=slot,
                        selector_protocol_sha256=selector_verified["sha256"],
                        capacity=capacity,
                        capacity_freeze=capacity_freeze,
                    )
                    value.update(
                        candidate_publication_opened=True,
                        candidate_handoff_opened=True,
                        candidate_freezes_opened=True,
                    )
                    selector_reference = {
                        "path": str(SELECTOR_PROTOCOL),
                        "sha256": selector_verified["sha256"],
                    }
                    terminal_created = max(created, selected["created_at_unix"])
                    terminal = _terminal_receipt(
                        selected,
                        created=terminal_created,
                        selector_reference=selector_reference,
                        quality_sources=states,
                        capacity_reference={
                            "path": str(CAPACITY_FREEZE),
                            "sha256": snapshots["freeze_sha256"],
                        },
                    )
                    terminal_path = root / TERMINAL_RECEIPT
                    if terminal_path.exists() or terminal_path.is_symlink():
                        if read_object(terminal_path) != terminal:
                            raise RuntimeError("V2.41.99 terminal receipt differs from replay")
                    else:
                        publish_new(terminal_path, terminal)
                    value["terminal_receipt_created"] = True
                    terminal_reference = {
                        "path": str(TERMINAL_RECEIPT),
                        "sha256": file_sha256(terminal_path),
                    }
                    selected_handoff = _selected_handoff(
                        selected,
                        terminal_reference,
                        created=terminal_created,
                        selector_reference=selector_reference,
                        compiler_protocol_sha256=verified["value"]["parent"][
                            "protocol"
                        ]["sha256"],
                    )
                    output_path = root / SELECTED_HANDOFF
                    if output_path.exists() or output_path.is_symlink():
                        if read_object(output_path) != selected_handoff:
                            raise RuntimeError("V2.41.99 selected handoff differs from replay")
                    else:
                        publish_new(output_path, selected_handoff)
                    value.update(
                        status="complete_selected_candidate_handoff_frozen",
                        reason="unique_predeclared_slot_and_integrated_candidate_validated",
                        selected_handoff_created=True,
                        terminal=True,
                        terminal_receipt=terminal_reference,
                        selected_handoff={
                            "path": str(SELECTED_HANDOFF),
                            "sha256": file_sha256(output_path),
                        },
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
        raise RuntimeError("V2.41.99 poll interval drifted")
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
                    "candidate_slot_selected": value["candidate_slot_selected"],
                    "selected_handoff_created": value["selected_handoff_created"],
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
