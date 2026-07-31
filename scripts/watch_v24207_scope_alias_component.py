#!/usr/bin/env python3
"""Publish the frozen branch-scope binding after V2.42.06 terminates."""

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
PROTOCOL = Path("results/v24207_selected_scope_alias_component_preregistration_v1_20260731.json")
STATE = Path("outputs/v24207_selected_scope_alias_component_watcher_state_v1_20260731.json")


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
        raise RuntimeError("V2.42.07 watcher requires python -I -B")
    args = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in args:
            return default
        if args.count(name) != 1 or args.index(name) + 1 >= len(args):
            raise RuntimeError(f"V2.42.07 invalid option: {name}")
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
        raise RuntimeError("V2.42.07 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24207_selected_branch_scope_namespace_alias_publisher_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.07 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.07 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24203_materialization_audit import (  # noqa: E402
    reject_forbidden_metadata,
)
from scripts.activate_v24207_scope_alias_component import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24207_scope_alias_component import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PARENT_PROTOCOL,
    PARENT_PROTOCOL_SHA256,
    PARENT_STATE,
    PUBLICATION,
    SELECTED_WORK_ORDER,
    publish_new,
    read_object,
    validate_protocol,
)
from scripts.publish_v24207_scope_alias_component import (  # noqa: E402
    MARKDOWN_PUBLICATION,
    build_selected_publication,
    load_inputs,
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
        "role": "v24207_selected_scope_alias_component_watcher_state",
        "created_at_unix": now,
        "protocol": {
            "path": str(OUTPUT),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"]["decision_contract_sha256"],
            "control_manifest_sha256": verified["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": activation,
        "parent_safe_state_envelope_opened": False,
        "parent_selected_work_order_opened": False,
        "parent_markdown_publication_opened": False,
        "parent_numeric_metrics_reports_predictions_or_aggregates_read": False,
        "component_publication_created": False,
        "branch_scope_component_published": False,
        "historical_p12_binding_selected": False,
        "mainline_zero_byte_namespace_alias_selected": False,
        "historical_scope_patch_reapplied": False,
        "candidate_bytes_modified_or_materialized": False,
        "search_yield_or_entropy_implemented": False,
        "joint_package_built_or_materialized": False,
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
        raise RuntimeError("V2.42.07 activation binding drifted")
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
        "parent_numeric_metrics_reports_predictions_or_aggregates_read",
        "branch_scope_patch_or_namespace_alias_applied",
        "search_yield_or_entropy_implemented",
        "joint_package_built_or_materialized",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    terminal = state.get("terminal")
    if (
        state.get("role") != "v24206_selected_markdown_component_watcher_state"
        or state.get("protocol", {}).get("path") != str(PARENT_PROTOCOL)
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or state.get("parent_safe_state_envelope_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or terminal not in {True, False}
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.07 parent safe state envelope drifted")
    if terminal is False:
        if (
            state.get("status") != "waiting_for_v24204_terminal_work_order"
            or state.get("parent_selected_work_order_opened") is not False
            or state.get("component_publication_created") is not False
        ):
            raise RuntimeError("V2.42.07 parent preterminal state drifted")
    else:
        if (
            state.get("status")
            not in {
                "complete_no_markdown_component_selected",
                "complete_historical_p12_markdown_binding",
                "complete_selected_baseline_markdown_rebase",
            }
            or state.get("parent_selected_work_order_opened") is not True
            or state.get("component_publication_created") is not True
        ):
            raise RuntimeError("V2.42.07 parent terminal state drifted")
    return state, bool(terminal)


def _existing_publication(root: Path, order: dict[str, Any]) -> dict[str, Any] | None:
    if not _present(root, PUBLICATION):
        return None
    value = read_object(root / PUBLICATION)
    unsigned = dict(value)
    seal = unsigned.pop("publication_payload_sha256", None)
    false_fields = (
        "historical_scope_patch_reapplied",
        "candidate_bytes_modified_or_materialized",
        "search_yield_or_entropy_implemented",
        "joint_package_built_or_materialized",
        "package_gate_evaluated_or_launched",
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
        value.get("role") != "v24207_selected_scope_alias_component_publication"
        or value.get("label_blind") is not True
        or value.get("publication_order") != order
        or value.get("selected_work_order", {}).get("decision_sha256")
        != order["decision_sha256"]
        or any(value.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.07 existing publication drifted")
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
        raise RuntimeError("V2.42.07 may only run in the canonical workspace")
    verified = validate_protocol(root, protocol_path)
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, now=created, activation=activation)
    if activation is None:
        if _present(root, PUBLICATION):
            raise RuntimeError("V2.42.07 publication appeared before activation")
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
            if _present(root, PUBLICATION):
                raise RuntimeError("V2.42.07 publication appeared before parent terminal")
            value.update(
                status="waiting_for_v24206_terminal_markdown_publication",
                reason="parent_markdown_component_preterminal",
            )
        else:
            selected, order, markdown = load_inputs(root)
            value["parent_selected_work_order_opened"] = True
            value["parent_markdown_publication_opened"] = True
            publication = _existing_publication(root, order)
            if publication is None:
                publication = build_selected_publication(selected, order, markdown)
                publish_new(root / PUBLICATION, publication)
            mode = order["publication_mode"]
            if mode == "no_op_component_absent":
                status = "complete_no_branch_scope_component_selected"
                reason = "selected_work_order_has_no_branch_scope_component"
            elif mode == "bind_historical_schema70_bytes":
                status = "complete_historical_p12_scope_binding"
                reason = "selected_p12_bound_to_byte_exact_schema70_publication"
            else:
                status = "complete_mainline_scope_namespace_alias"
                reason = "selected_mainline_scope_hook_bound_by_zero_byte_alias"
            value.update(
                terminal=True,
                status=status,
                reason=reason,
                component_publication_created=True,
                branch_scope_component_published=publication[
                    "branch_scope_component_published"
                ],
                historical_p12_binding_selected=(mode == "bind_historical_schema70_bytes"),
                mainline_zero_byte_namespace_alias_selected=(
                    mode == "bind_zero_byte_mainline_scope_namespace_alias"
                ),
                publication={
                    "path": str(PUBLICATION),
                    "sha256": hashlib.sha256((root / PUBLICATION).read_bytes()).hexdigest(),
                    "disposition": order["disposition"],
                    "component_present": publication["component_publication"] is not None,
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
        raise RuntimeError("V2.42.07 poll interval drifted")
    while True:
        value = run_cycle(
            Path(args.root), protocol_path=Path(args.protocol), state_path=Path(args.state)
        )
        print(
            json.dumps(
                {key: value[key] for key in ("role", "created_at_unix", "status", "reason", "terminal")}
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
