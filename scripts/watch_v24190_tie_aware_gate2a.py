#!/usr/bin/env python3
"""Wait for and consume the tie-aware true-continuation Gate-2A."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = Path(
    "results/v24190_tie_aware_gate2a_consumer_preregistration_v1_20260730.json"
)
STATE = Path("outputs/v24190_tie_aware_gate2a_consumer_state_v1_20260730.json")
REPORT = Path(
    "results/v24190_tie_aware_true_continuation_gate2a_report_v1_20260730.json"
)
ACTIVATION = Path(
    "results/v24190_tie_aware_gate2a_consumer_activation_audit_v1_20260730.json"
)
SOURCE_STATE = Path(
    "outputs/v24159_true_continuation_reachability_state_v1_20260729.json"
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
        raise RuntimeError("V2.41.90 consumer requires python -I -B")
    arguments = list(sys.argv[1:])

    def option(name: str, default: str) -> str:
        if name not in arguments:
            return default
        if arguments.count(name) != 1:
            raise RuntimeError(f"V2.41.90 option is not unique: {name}")
        index = arguments.index(name)
        if index + 1 >= len(arguments):
            raise RuntimeError(f"V2.41.90 option lacks a value: {name}")
        return arguments[index + 1]

    root = Path(option("--root", str(ROOT))).resolve()
    protocol_raw = Path(option("--protocol", str(PROTOCOL)))
    protocol = protocol_raw if protocol_raw.is_absolute() else root / protocol_raw
    state_raw = Path(option("--state", str(STATE)))
    state = state_raw if state_raw.is_absolute() else root / state_raw
    report_raw = Path(option("--report", str(REPORT)))
    report = report_raw if report_raw.is_absolute() else root / report_raw
    if (
        root != ROOT.resolve()
        or protocol.resolve(strict=False) != (root / PROTOCOL).resolve(strict=False)
        or protocol.is_symlink()
        or not protocol.is_file()
        or state.resolve(strict=False) != (root / STATE).resolve(strict=False)
        or state.is_symlink()
        or report.resolve(strict=False) != (root / REPORT).resolve(strict=False)
        or report.is_symlink()
        or option("--poll-seconds", "60") != "60"
        or option("--proc-root", "/proc") != "/proc"
    ):
        raise RuntimeError("V2.41.90 consumer path or execution drifted")
    value = json.loads(protocol.read_text(encoding="utf-8"))
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("protocol_id")
        != "v24190_tie_aware_true_continuation_gate2a_consumer_v1"
        or not isinstance(manifest, dict)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != _payload_sha(manifest)
    ):
        raise RuntimeError("V2.41.90 bootstrap protocol is invalid")
    for relative, digest in manifest.items():
        target = root / relative
        if (
            target.is_symlink()
            or not target.is_file()
            or hashlib.sha256(target.read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError("V2.41.90 control bytes drifted")


_bootstrap()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24123_release import validate_job_manifest  # noqa: E402
from deepwide_agent.v24190_tie_aware_gate2a import (  # noqa: E402
    evaluate_tie_aware_gate2a,
)
from scripts.preregister_v24162_canonical_gate2a_consumer import (  # noqa: E402
    BRANCH_ROOT,
    MANIFEST,
    MODEL,
    PARENT_GATE2A_REPORT,
    PREDICTION_SEAL,
)
from scripts.preregister_v24190_tie_aware_gate2a import (  # noqa: E402
    PARENT_REPORT,
    PARENT_STATE,
    validate_protocol,
)
from scripts.run_v24123_release import (  # noqa: E402
    _read_validated_bundle_aggregate,
    _verify_audit_prediction_replay,
)
from scripts.watch_v24162_canonical_gate2a_consumer import (  # noqa: E402
    assert_canonical_module_identity as assert_parent_canonical_module_identity,
)
from scripts.v24159_true_continuation_reachability import (  # noqa: E402
    atomic_json,
    object_sha256,
    publish_new,
    read_object,
    sha256,
)


WAITING = {
    "waiting_for_p12_trial2_exact220_release",
    "waiting_for_avg4_four_exact220_release",
    "waiting_for_observational_gate1_terminal_receipt",
    "waiting_for_shared_api_lease",
    "waiting_for_fresh_capture_preflight",
    "fit_calibration_in_progress",
    "waiting_for_fresh_neutral_preflight",
    "audit_in_progress",
}
TERMINAL_NO_REPORT = {
    "gate1_no_go_true_continuation_not_launched",
    "capture_attempt_failed_no_api_reissue",
    "fit_calibration_model_support_no_go",
}


def assert_canonical_module_identity() -> dict[str, Any]:
    parent = assert_parent_canonical_module_identity()
    forbidden = sorted(
        name
        for name in sys.modules
        if name == "src.deepwide_agent" or name.startswith("src.deepwide_agent.")
    )
    tie_module = evaluate_tie_aware_gate2a.__module__
    if forbidden or tie_module != "deepwide_agent.v24190_tie_aware_gate2a":
        raise RuntimeError("V2.41.90 canonical module identity guard failed")
    return {
        **parent,
        "tie_aware_evaluator_module": tie_module,
        "forbidden_src_deepwide_agent_loaded": False,
    }


def _target(root: Path, raw: Path, expected: Path, parent: str) -> Path:
    unresolved = raw if raw.is_absolute() else root / raw
    target = unresolved.resolve(strict=False)
    if (
        target != (root / expected).resolve(strict=False)
        or unresolved.is_symlink()
        or not target.is_relative_to((root / parent).resolve())
    ):
        raise RuntimeError("V2.41.90 output path is noncanonical")
    return target


def _activation_ready(root: Path, verified: dict[str, Any]) -> bool:
    path = root / ACTIVATION
    if not path.exists() and not path.is_symlink():
        return False
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.41.90 activation path is invalid")
    value = read_object(path)
    if (
        value.get("role") != "v24190_tie_aware_gate2a_consumer_activation_audit"
        or value.get("activation_valid") is not True
        or value.get("protocol", {}).get("sha256") != verified["sha256"]
        or value.get("boundary", {}).get("v24162_parent_consumer_preserved")
        is not True
        or value.get("boundary", {}).get("v24190_consumer_exactly_one")
        is not True
    ):
        raise RuntimeError("V2.41.90 activation audit is invalid")
    return True


def _waiting_state(
    verified: dict[str, Any],
    source: dict[str, Any],
    parent: dict[str, Any],
    identity: dict[str, Any],
    *,
    activation_ready: bool,
) -> dict[str, Any]:
    source_truth = {
        key: source.get(key)
        for key in (
            "mapping_or_gold_read",
            "evaluator_or_score_read",
            "api_or_benchmark_forward_called",
            "shared_api_lease_acquired",
        )
    }
    if any(not isinstance(value, bool) for value in source_truth.values()):
        raise RuntimeError("V2.41.90 source truth is not boolean")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24190_tie_aware_gate2a_consumer_state",
        "protocol": {
            "path": str(PROTOCOL),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
        },
        "status": "waiting_for_true_continuation_audit_terminal",
        "source_status": source.get("status"),
        "source_terminal": source.get("terminal") is True,
        "source_truth": source_truth,
        "parent_consumer_status": parent.get("status"),
        "parent_strict_gate2a_evaluated": parent.get("strict_gate2a_evaluated") is True,
        "canonical_module_identity": identity,
        "activation_ready": activation_ready,
        "manifest_prediction_or_outcome_opened": False,
        "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer": False,
        "network_model_search_fetch_or_evaluator_api_called_by_consumer": False,
        "tie_aware_gate2a_evaluated": False,
        "tie_aware_gate2a_passed": False,
        "controller_design_allowed": False,
        "controller_implementation_or_pilot_launch_allowed": False,
        "training_credit_allowed": False,
        "full220_controller_launch_allowed": False,
        "benchmark_or_sota_claim": False,
        "terminal": source.get("status") in TERMINAL_NO_REPORT,
    }
    value["state_payload_sha256"] = object_sha256(value)
    return value


def _validate_parent_report(root: Path) -> dict[str, Any]:
    path = root / PARENT_REPORT
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(path)
    value = read_object(path)
    unsigned = copy.deepcopy(value)
    seal = unsigned.pop("report_payload_sha256", None)
    if (
        value.get("role")
        != "v24162_canonical_strict_true_continuation_gate2a_report"
        or value.get("controller_implementation_or_pilot_launch_allowed") is not False
        or value.get("training_credit_allowed") is not False
        or value.get("full220_controller_launch_allowed") is not False
        or value.get("benchmark_or_sota_claim") is not False
        or seal != object_sha256(unsigned)
    ):
        raise RuntimeError("V2.41.90 parent V2.41.62 report is invalid")
    return value


def _evaluate(
    root: Path, verified: dict[str, Any], identity: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    assert_canonical_module_identity()
    manifest_path = root / MANIFEST
    prediction_path = root / PREDICTION_SEAL
    model_path = root / MODEL
    if any(
        path.is_symlink() or not path.is_file()
        for path in (manifest_path, prediction_path, model_path)
    ):
        raise FileNotFoundError("V2.41.90 source artifact set is incomplete")
    manifest = read_object(manifest_path)
    validate_job_manifest(manifest)
    prediction = read_object(prediction_path)
    replay = _verify_audit_prediction_replay(root, manifest)
    if replay.get("verified") is not True:
        raise RuntimeError("V2.41.90 audit prediction live replay failed")
    parent_report = _validate_parent_report(root)
    parent_state = read_object(root / PARENT_STATE)
    if (
        parent_state.get("role") != "v24162_canonical_gate2a_consumer_state"
        or parent_state.get("terminal") is not True
        or parent_state.get("strict_gate2a_evaluated") is not True
        or parent_state.get("strict_report", {}).get("sha256")
        != sha256(root / PARENT_REPORT)
    ):
        raise RuntimeError("V2.41.90 parent terminal state is invalid")
    branch_root = root / BRANCH_ROOT
    if branch_root.is_symlink() or not branch_root.is_dir():
        raise FileNotFoundError(branch_root)
    aggregates = [
        _read_validated_bundle_aggregate(root, bundle)
        for bundle in manifest["bundles"]
    ]
    if len(aggregates) != len(manifest["bundles"]):
        raise RuntimeError("V2.41.90 aggregate replay is incomplete")
    gate = evaluate_tie_aware_gate2a(
        manifest,
        aggregates,
        prediction,
        settings=verified["value"]["tie_aware_contract"]["settings"],
    )
    parent_gate = parent_report.get("gate2a") or {}
    replayed_parent = gate["parent_strict_gate_replay"]
    if parent_gate != replayed_parent:
        raise RuntimeError("V2.41.90 parent strict-gate replay differs from report")
    report: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24190_tie_aware_true_continuation_gate2a_report",
        "protocol": {
            "path": str(PROTOCOL),
            "sha256": verified["sha256"],
            "decision_contract_sha256": verified["value"][
                "decision_contract_sha256"
            ],
        },
        "sources": {
            "manifest": {"path": str(MANIFEST), "sha256": sha256(manifest_path)},
            "prediction_seal": {
                "path": str(PREDICTION_SEAL),
                "sha256": sha256(prediction_path),
            },
            "model": {"path": str(MODEL), "sha256": sha256(model_path)},
            "parent_v24162_report": {
                "path": str(PARENT_REPORT),
                "sha256": sha256(root / PARENT_REPORT),
                "status": parent_gate.get("status"),
                "passed": parent_gate.get("passed"),
                "authoritative_for_controller_design": False,
            },
            "prediction_live_replay_receipt_sha256": object_sha256(replay),
            "aggregate_count": len(aggregates),
            "aggregate_set_sha256": object_sha256(aggregates),
        },
        "canonical_module_identity": identity,
        "gate2a": gate,
        "mapping_gold_category_question_type_evaluator_score_or_outcome_read": True,
        "read_scope": "sealed_post_terminal_source_artifacts_only",
        "network_model_search_fetch_or_evaluator_api_called": False,
        "source_runner_parent_consumer_or_branch_mutated": False,
        "controller_design_allowed": gate["passed"],
        "controller_implementation_or_pilot_launch_allowed": False,
        "training_credit_allowed": False,
        "full220_controller_launch_allowed": False,
        "benchmark_or_sota_claim": False,
    }
    report["report_payload_sha256"] = object_sha256(report)
    state: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24190_tie_aware_gate2a_consumer_state",
        "protocol": report["protocol"],
        "status": f"tie_aware_gate2a_{gate['status']}",
        "source_status": "audit_terminal",
        "source_terminal": True,
        "parent_consumer_status": parent_state.get("status"),
        "parent_strict_gate2a_evaluated": True,
        "canonical_module_identity": identity,
        "activation_ready": True,
        "manifest_prediction_or_outcome_opened": True,
        "mapping_gold_category_question_type_evaluator_score_or_outcome_read_by_consumer": True,
        "read_scope": "sealed_post_terminal_source_artifacts_only",
        "network_model_search_fetch_or_evaluator_api_called_by_consumer": False,
        "tie_aware_gate2a_evaluated": True,
        "tie_aware_gate2a_passed": gate["passed"],
        "tie_aware_report": {"path": str(REPORT), "sha256": None},
        "controller_design_allowed": gate["passed"],
        "controller_implementation_or_pilot_launch_allowed": False,
        "training_credit_allowed": False,
        "full220_controller_launch_allowed": False,
        "benchmark_or_sota_claim": False,
        "terminal": True,
    }
    return report, state


def run_once(
    root: Path,
    *,
    protocol_path: Path = PROTOCOL,
    state_path: Path = STATE,
    report_path: Path = REPORT,
) -> dict[str, Any]:
    root = root.resolve()
    verified = validate_protocol(root, protocol_path)
    state_target = _target(root, state_path, STATE, "outputs")
    report_target = _target(root, report_path, REPORT, "results")
    source_path = root / SOURCE_STATE
    parent_path = root / PARENT_STATE
    if any(path.is_symlink() or not path.is_file() for path in (source_path, parent_path)):
        raise RuntimeError("V2.41.90 safe source state is unavailable")
    source = read_object(source_path)
    parent = read_object(parent_path)
    identity = assert_canonical_module_identity()
    if (
        source.get("role") != "v24159_true_continuation_reachability_state"
        or parent.get("role") != "v24162_canonical_gate2a_consumer_state"
    ):
        raise RuntimeError("V2.41.90 source state role drifted")
    status = str(source.get("status") or "")
    activation_ready = _activation_ready(root, verified)
    if status in WAITING or status in TERMINAL_NO_REPORT:
        value = _waiting_state(
            verified,
            source,
            parent,
            identity,
            activation_ready=activation_ready,
        )
        atomic_json(state_target, value)
        return value
    if status != "audit_terminal" or source.get("terminal") is not True:
        raise RuntimeError("V2.41.90 source status is unregistered")
    if not activation_ready:
        value = _waiting_state(
            verified, source, parent, identity, activation_ready=False
        )
        atomic_json(state_target, value)
        return value
    if parent.get("strict_gate2a_evaluated") is not True or parent.get("terminal") is not True:
        value = _waiting_state(
            verified, source, parent, identity, activation_ready=True
        )
        atomic_json(state_target, value)
        return value
    report, state = _evaluate(root, verified, identity)
    payload = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode()
    if report_target.exists() or report_target.is_symlink():
        if (
            report_target.is_symlink()
            or not report_target.is_file()
            or report_target.read_bytes() != payload
        ):
            raise RuntimeError("V2.41.90 tie-aware report drifted")
    else:
        publish_new(report_target, report)
    state["tie_aware_report"]["sha256"] = sha256(report_target)
    state["state_payload_sha256"] = object_sha256(state)
    atomic_json(state_target, state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(PROTOCOL))
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--report", default=str(REPORT))
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.poll_seconds != 60 or args.proc_root != "/proc":
        raise RuntimeError("V2.41.90 execution parameters drifted")
    while True:
        value = run_once(
            Path(args.root),
            protocol_path=Path(args.protocol),
            state_path=Path(args.state),
            report_path=Path(args.report),
        )
        print(
            json.dumps(
                {
                    "role": value["role"],
                    "status": value["status"],
                    "source_status": value["source_status"],
                    "tie_aware_gate2a_evaluated": value[
                        "tie_aware_gate2a_evaluated"
                    ],
                    "tie_aware_gate2a_passed": value["tie_aware_gate2a_passed"],
                }
            ),
            flush=True,
        )
        if args.once or value["terminal"]:
            return
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
