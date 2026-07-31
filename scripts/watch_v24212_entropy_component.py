#!/usr/bin/env python3
"""Publish V2.42.12 only after search-parent and Gate-2A terminal states."""

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
PROTOCOL = Path("results/v24212_selected_entropy_component_preregistration_v1_20260731.json")
STATE = Path("outputs/v24212_selected_entropy_component_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.42.12 watcher requires python -I -B")
    args = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in args:
            return default
        if args.count(name) != 1 or args.index(name) + 1 >= len(args):
            raise RuntimeError(f"V2.42.12 invalid option: {name}")
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
        raise RuntimeError("V2.42.12 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24212_selected_parent_entropy_component_publisher_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.12 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.12 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.activate_v24212_entropy_component import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    ACTIVATION,
    GATE2A_PROTOCOL,
    GATE2A_PROTOCOL_SHA256,
    GATE2A_STATE,
    OUTPUT,
    PUBLICATION,
    SEARCH_PROTOCOL,
    SEARCH_PROTOCOL_SHA256,
    SEARCH_STATE,
    publish_new,
    validate_protocol,
)
from scripts.publish_v24212_entropy_component import (  # noqa: E402
    ACTION_MODEL,
    CANDIDATE_ROOT,
    GATE2A_REPORT,
    build_selected_publication,
    load_selected_inputs,
)


SEARCH_TERMINAL_STATUSES = {
    "complete_no_search_component_selected",
    "complete_search_component_materialized",
    "complete_search_component_retired_no_go",
    "complete_search_component_retired_incomplete",
}
GATE2A_TERMINAL_STATUSES = {
    "replicate_aware_gate2a_pass",
    "replicate_aware_gate2a_fail",
    "replicate_aware_gate2a_not_evaluable",
}


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


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.12 expected an ordinary state file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.12 expected one state object")
    return value


def _base(
    verified: dict[str, Any], *, now: int, activation: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24212_selected_entropy_component_watcher_state",
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
        "search_parent_safe_state_envelope_opened": False,
        "gate2a_safe_state_envelope_opened": False,
        "selected_work_order_opened": False,
        "search_publication_opened": False,
        "gate2a_report_opened": False,
        "action_model_opened": False,
        "numeric_metrics_predictions_or_aggregates_read_before_both_terminal": False,
        "component_publication_created": False,
        "entropy_component_published": False,
        "entropy_component_absent_noop": False,
        "candidate_materialized": False,
        "real_state_transition_adapters_included": False,
        "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency": False,
        "projection_only_action_arm_selected_instantiated_or_called": False,
        "joint_package_quality_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing": False,
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
        raise RuntimeError("V2.42.12 activation binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": verified["value"]["watcher"]["pid"],
        "watcher_start_ticks": verified["value"]["watcher"]["start_ticks"],
    }


def _search_parent_state(root: Path) -> tuple[dict[str, Any], bool]:
    state = _read_object(root / SEARCH_STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "entropy_controller_published_or_implemented",
        "joint_package_built_or_materialized",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    terminal = state.get("terminal")
    if (
        state.get("role") != "v24210_selected_search_component_watcher_state"
        or state.get("protocol", {}).get("path") != str(SEARCH_PROTOCOL)
        or state.get("protocol", {}).get("sha256") != SEARCH_PROTOCOL_SHA256
        or state.get("scope_parent_safe_state_envelope_opened") is not True
        or state.get("search_quality_safe_state_envelope_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or terminal not in {True, False}
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.12 search-parent safe envelope drifted")
    if terminal is False and state.get("status") not in {
        "waiting_for_scope_and_search_quality_terminal",
        "waiting_for_scope_parent_terminal",
        "waiting_for_search_quality_terminal",
    }:
        raise RuntimeError("V2.42.12 search-parent preterminal status drifted")
    if terminal is True and state.get("status") not in SEARCH_TERMINAL_STATUSES:
        raise RuntimeError("V2.42.12 search-parent terminal status drifted")
    return state, bool(terminal)


def _gate2a_state(root: Path) -> tuple[dict[str, Any], bool]:
    state = _read_object(root / GATE2A_STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "controller_implementation_or_pilot_launch_allowed",
        "training_credit_allowed",
        "full220_controller_launch_allowed",
        "benchmark_or_sota_claim",
    )
    terminal = state.get("terminal")
    if (
        state.get("role") != "v24193_replicate_aware_gate2a_consumer_state"
        or state.get("protocol", {}).get("path") != str(GATE2A_PROTOCOL)
        or state.get("protocol", {}).get("sha256") != GATE2A_PROTOCOL_SHA256
        or any(state.get(field) is not False for field in false_fields)
        or terminal not in {True, False}
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.12 Gate-2A safe envelope drifted")
    if terminal is False and (
        state.get("status") != "waiting_for_v24192_abstain_aware_gate2a_terminal"
        or state.get("manifest_model_prediction_aggregate_or_outcome_opened")
        is not False
        or state.get(
            "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer"
        )
        is not False
    ):
        raise RuntimeError("V2.42.12 Gate-2A preterminal status drifted")
    if terminal is True and state.get("status") not in GATE2A_TERMINAL_STATUSES:
        raise RuntimeError("V2.42.12 Gate-2A terminal status drifted")
    return state, bool(terminal)


def _existing_publication(root: Path, decision: str) -> dict[str, Any] | None:
    if not _present(root, PUBLICATION):
        return None
    value = _read_object(root / PUBLICATION)
    unsigned = dict(value)
    seal = unsigned.pop("publication_payload_sha256", None)
    false_fields = (
        "projection_only_action_arm_selected_instantiated_or_called",
        "joint_package_quality_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    if (
        value.get("role") != "v24212_selected_entropy_component_publication"
        or value.get("label_blind") is not True
        or value.get("selected_work_order", {}).get("decision_sha256") != decision
        or any(value.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.12 existing publication drifted")
    return value


def run_cycle(
    root: Path = ROOT,
    *,
    protocol_path: Path = OUTPUT,
    state_path: Path = STATE,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.12 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, now=created, activation=activation)
    if activation is None:
        if (
            _present(root, PUBLICATION)
            or CANDIDATE_ROOT.exists()
            or CANDIDATE_ROOT.is_symlink()
        ):
            raise RuntimeError("V2.42.12 output appeared before activation")
        value.update(
            status="waiting_for_execution_activation", reason="activation_absent"
        )
    else:
        search_state, search_terminal = _search_parent_state(root)
        gate_state, gate_terminal = _gate2a_state(root)
        value["search_parent_safe_state_envelope_opened"] = True
        value["gate2a_safe_state_envelope_opened"] = True
        value["search_parent_state"] = {
            "path": str(SEARCH_STATE),
            "status": search_state["status"],
            "terminal": search_terminal,
            "contents_emitted": False,
        }
        value["gate2a_state"] = {
            "path": str(GATE2A_STATE),
            "status": gate_state["status"],
            "terminal": gate_terminal,
            "contents_emitted": False,
        }
        if not search_terminal or not gate_terminal:
            if (
                _present(root, PUBLICATION)
                or CANDIDATE_ROOT.exists()
                or CANDIDATE_ROOT.is_symlink()
            ):
                raise RuntimeError("V2.42.12 output appeared before both parents terminal")
            if not search_terminal and not gate_terminal:
                status = "waiting_for_search_parent_and_gate2a_terminal"
                reason = "search_parent_and_gate2a_preterminal"
            elif not search_terminal:
                status = "waiting_for_search_parent_terminal"
                reason = "search_parent_preterminal"
            else:
                status = "waiting_for_gate2a_terminal"
                reason = "gate2a_preterminal"
            value.update(status=status, reason=reason)
        else:
            selected, order, search_order, markdown, scope, search = (
                load_selected_inputs(root)
            )
            gate_passed = gate_state["status"] == "replicate_aware_gate2a_pass"
            if (order is not None) is not gate_passed:
                raise RuntimeError(
                    "V2.42.12 selected entropy component differs from Gate-2A"
                )
            value["selected_work_order_opened"] = True
            value["search_publication_opened"] = True
            value["gate2a_report_opened"] = order is not None
            value["action_model_opened"] = order is not None
            decision = selected["selected_work_order"]["decision_sha256"]
            publication = _existing_publication(root, decision)
            if publication is None:
                publication = build_selected_publication(
                    selected,
                    order,
                    search_order,
                    markdown,
                    scope,
                    search,
                )
                publish_new(root / PUBLICATION, publication)
            disposition = publication["publication_disposition"]
            value.update(
                terminal=True,
                status=(
                    "complete_entropy_component_materialized"
                    if publication["entropy_component_published"]
                    else "complete_no_entropy_component_selected"
                ),
                reason=disposition,
                component_publication_created=True,
                entropy_component_published=publication[
                    "entropy_component_published"
                ],
                entropy_component_absent_noop=publication[
                    "entropy_component_absent_noop"
                ],
                candidate_materialized=publication["component_publication"]
                is not None,
                real_state_transition_adapters_included=publication[
                    "real_state_transition_adapters_included"
                ],
                historical_module_containing_revoked_projection_arm_present_as_adapter_dependency=publication[
                    "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency"
                ],
                publication={
                    "path": str(PUBLICATION),
                    "sha256": hashlib.sha256(
                        (root / PUBLICATION).read_bytes()
                    ).hexdigest(),
                    "disposition": disposition,
                    "component_present": publication["component_publication"]
                    is not None,
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
        raise RuntimeError("V2.42.12 poll interval drifted")
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
                    for key in (
                        "role",
                        "created_at_unix",
                        "status",
                        "reason",
                        "terminal",
                    )
                }
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
