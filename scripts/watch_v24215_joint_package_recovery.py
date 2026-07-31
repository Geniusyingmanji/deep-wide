#!/usr/bin/env python3
"""Versioned V2.42.15 joint-package recovery watcher."""

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
    "results/v24215_selected_joint_package_recovery_preregistration_v1_20260731.json"
)
STATE = Path("outputs/v24215_selected_joint_package_recovery_state_v1_20260731.json")


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
        raise RuntimeError("V2.42.15 watcher requires python -I -B")
    args = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in args:
            return default
        if args.count(name) != 1 or args.index(name) + 1 >= len(args):
            raise RuntimeError(f"V2.42.15 invalid option: {name}")
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
        raise RuntimeError("V2.42.15 watcher execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24215_joint_package_entropy_path_recovery_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.42.15 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.42.15 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.activate_v24215_joint_package_recovery import (  # noqa: E402
    validate_activation,
)
from scripts.build_v2410_rank_slot_candidate import (  # noqa: E402
    candidate_regular_file_manifest,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    read_object,
    sha256,
)
from scripts.preregister_v24215_joint_package_recovery import (  # noqa: E402
    ACTIVATION,
    FAILED_AUDIT_PATH,
    FAILED_AUDIT_SHA256,
    OUTPUT,
    PARENT_PROTOCOL,
    PARENT_PROTOCOL_SHA256,
    PARENT_STATE,
    PUBLICATION,
    V24214_ACTIVATION,
    V24214_CANDIDATE,
    V24214_PROTOCOL,
    V24214_PUBLICATION,
    V24214_STATE,
    validate_protocol,
)
from scripts.publish_v24215_joint_package_recovery import (  # noqa: E402
    CANDIDATE_ROOT,
    build_recovery_publication,
    load_recovery_inputs,
    publish_new,
)


PARENT_PRETERMINAL_STATUSES = {
    "waiting_for_search_parent_and_gate2a_terminal",
    "waiting_for_search_parent_terminal",
    "waiting_for_gate2a_terminal",
}
PARENT_TERMINAL_STATUSES = {
    "complete_entropy_component_recovery_materialized",
    "complete_no_entropy_component_selected",
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


def _base(
    verified: dict[str, Any], *, now: int, activation: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": "v24215_selected_joint_package_recovery_state",
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
        "recovery_parent": {
            "path": FAILED_AUDIT_PATH,
            "sha256": FAILED_AUDIT_SHA256,
        },
        "execution_activation": activation,
        "parent_safe_state_envelope_opened": False,
        "selected_work_order_opened": False,
        "markdown_publication_opened": False,
        "scope_publication_opened": False,
        "search_publication_opened": False,
        "entropy_publication_opened": False,
        "v24214_protocol_activation_state_candidate_or_publication_reused_overwritten_or_resumed": False,
        "joint_package_publication_created": False,
        "identity_handoff_only": False,
        "joint_package_materialized": False,
        "single_deepest_cumulative_graph_used": False,
        "component_directory_overlay_used": False,
        "complete_parent_and_component_regression_rerun": False,
        "strict_component_activation_validated": False,
        "silent_component_drop_or_baseline_fallback_used": False,
        "package_gate_evaluated_or_launched": False,
        "dev64_launch_allowed": False,
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
        raise RuntimeError("V2.42.15 activation binding drifted")
    return {
        "path": str(ACTIVATION),
        "sha256": verified["sha256"],
        "watcher_pid": verified["value"]["watcher"]["pid"],
        "watcher_start_ticks": verified["value"]["watcher"]["start_ticks"],
    }


def _parent_state(root: Path) -> tuple[dict[str, Any], bool]:
    state = read_object(root / PARENT_STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "projection_only_action_arm_selected_instantiated_or_called",
        "joint_package_quality_gate_evaluated_or_launched",
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
    status = state.get("status")
    if (
        state.get("role")
        != "v24213_selected_entropy_component_recovery_state"
        or state.get("protocol", {}).get("path") != str(PARENT_PROTOCOL)
        or state.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or any(state.get(field) is not False for field in false_fields)
        or terminal not in {True, False}
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.15 parent safe envelope drifted")
    if terminal is False and (
        status not in PARENT_PRETERMINAL_STATUSES
        or state.get("selected_work_order_opened") is not False
        or state.get("search_publication_opened") is not False
        or state.get("gate2a_report_opened") is not False
        or state.get("action_model_opened") is not False
        or state.get("numeric_metrics_predictions_or_aggregates_read_before_both_terminal")
        is not False
    ):
        raise RuntimeError("V2.42.15 parent preterminal envelope drifted")
    if terminal is True and status not in PARENT_TERMINAL_STATUSES:
        raise RuntimeError("V2.42.15 parent terminal status drifted")
    return state, bool(terminal)


def _assert_failed_namespace_preserved(root: Path) -> None:
    if (
        not (root / FAILED_AUDIT_PATH).is_file()
        or (root / FAILED_AUDIT_PATH).is_symlink()
        or not (root / V24214_PROTOCOL).is_file()
        or (root / V24214_PROTOCOL).is_symlink()
        or not (root / V24214_ACTIVATION).is_file()
        or (root / V24214_ACTIVATION).is_symlink()
        or not (root / V24214_STATE).is_file()
        or (root / V24214_STATE).is_symlink()
        or (root / V24214_PUBLICATION).exists()
        or (root / V24214_PUBLICATION).is_symlink()
        or V24214_CANDIDATE.exists()
        or V24214_CANDIDATE.is_symlink()
    ):
        raise RuntimeError("V2.42.15 failed namespace preservation drifted")


def _existing_publication(
    root: Path, decision: str
) -> dict[str, Any] | None:
    if not _present(root, PUBLICATION):
        return None
    value = read_object(root / PUBLICATION)
    unsigned = dict(value)
    seal = unsigned.pop("publication_payload_sha256", None)
    false_fields = (
        "v24214_protocol_activation_state_candidate_or_publication_reused_overwritten_or_resumed",
        "component_directory_overlay_used",
        "silent_component_drop_or_baseline_fallback_used",
        "package_gate_evaluated_or_launched",
        "dev64_launch_allowed",
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
        value.get("role")
        != "v24215_selected_joint_package_recovery_publication"
        or value.get("label_blind") is not True
        or value.get("selected_work_order", {}).get("decision_sha256") != decision
        or value.get("recovery_parent", {}).get("sha256") != FAILED_AUDIT_SHA256
        or value.get("all_selected_components_covered_exactly_once") is not True
        or value.get("single_deepest_cumulative_graph_used") is not True
        or any(value.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.15 existing publication drifted")
    component = value.get("component_publication")
    if component is not None:
        if (
            not isinstance(component, dict)
            or Path(str(component.get("candidate_root"))).resolve(strict=False)
            != CANDIDATE_ROOT.resolve(strict=False)
            or candidate_regular_file_manifest(CANDIDATE_ROOT, source_only=True)
            != component.get("candidate_regular_file_manifest")
        ):
            raise RuntimeError("V2.42.15 existing candidate drifted")
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
        raise RuntimeError("V2.42.15 may only run in the canonical workspace")
    _assert_failed_namespace_preserved(root)
    verified = validate_protocol(root, protocol_path)
    created = int(time.time()) if now is None else int(now)
    activation = _activation(root, verified["sha256"])
    value = _base(verified, now=created, activation=activation)
    if activation is None:
        if _present(root, PUBLICATION) or CANDIDATE_ROOT.exists() or CANDIDATE_ROOT.is_symlink():
            raise RuntimeError("V2.42.15 output appeared before activation")
        value.update(status="waiting_for_execution_activation", reason="activation_absent")
    else:
        parent, terminal = _parent_state(root)
        value["parent_safe_state_envelope_opened"] = True
        value["parent_state"] = {
            "path": str(PARENT_STATE),
            "status": parent["status"],
            "terminal": terminal,
            "contents_emitted": False,
        }
        if not terminal:
            if _present(root, PUBLICATION) or CANDIDATE_ROOT.exists() or CANDIDATE_ROOT.is_symlink():
                raise RuntimeError("V2.42.15 output appeared before parent terminal")
            value.update(
                status="waiting_for_v24213_entropy_recovery_terminal",
                reason="parent_preterminal",
            )
        else:
            selected, base, recovery, publications = load_recovery_inputs(root)
            value["selected_work_order_opened"] = True
            value["markdown_publication_opened"] = True
            value["scope_publication_opened"] = True
            value["search_publication_opened"] = True
            value["entropy_publication_opened"] = True
            decision = str(recovery["decision_sha256"])
            publication = _existing_publication(root, decision)
            if publication is None:
                if CANDIDATE_ROOT.exists() or CANDIDATE_ROOT.is_symlink():
                    raise RuntimeError("V2.42.15 unsealed candidate appeared")
                publication = build_recovery_publication(
                    selected, base, recovery, publications
                )
                publish_new(root / PUBLICATION, publication)
            component = publication["component_publication"]
            identity = bool(publication["identity_handoff_only"])
            if (component is None) is not identity:
                raise RuntimeError("V2.42.15 publication disposition drifted")
            value.update(
                terminal=True,
                status=(
                    "complete_selected_baseline_identity_handoff_recovered"
                    if identity
                    else "complete_joint_package_recovery_revalidated"
                ),
                reason=publication["publication_disposition"],
                joint_package_publication_created=True,
                identity_handoff_only=identity,
                joint_package_materialized=component is not None,
                single_deepest_cumulative_graph_used=True,
                complete_parent_and_component_regression_rerun=component is not None,
                strict_component_activation_validated=component is not None,
                publication={
                    "path": str(PUBLICATION),
                    "sha256": sha256(root / PUBLICATION),
                    "decision_sha256": decision,
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
        raise RuntimeError("V2.42.15 poll interval drifted")
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
