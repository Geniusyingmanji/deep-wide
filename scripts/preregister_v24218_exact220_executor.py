#!/usr/bin/env python3
"""Freeze the V2.42.18 post-capacity single-owner exact-220 executor."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24218_exact220_executor import (  # noqa: E402
    payload_sha256,
    read_opaque_ids,
    validate_exact_partition,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    _start_ticks,
    ordinary,
    publish_new,
    read_object,
    sha256,
)
from scripts.run_v24218_exact220_executor import (  # noqa: E402
    EVALUATOR_ROOT,
    FORWARD_BARRIER,
    MATERIALIZATION,
    PREPARE_ROOT,
    RESULT,
    SHARD_ROOTS,
    SOURCE_IDS,
    SOURCE_MANIFEST,
    SUMMARY,
)
from scripts.preregister_v2408_combined_fasttrack import R1_FREEZES  # noqa: E402


ROLE = "v24218_exact220_executor_preregistration"
PROTOCOL_ID = "v24218_post_capacity_single_owner_fresh_exact220_v1"
OUTPUT = Path("results/v24218_exact220_executor_preregistration_v1_20260731.json")
STATE = Path("outputs/v24218_exact220_executor_watcher_state_v1_20260731.json")
ACTIVATION = Path("results/v24218_exact220_executor_activation_v1_20260731.json")
WAIT_AUDIT = Path("results/v24218_exact220_executor_wait_audit_v1_20260731.json")
EXECUTION_START = Path("results/v24218_exact220_execution_start_v1_20260731.json")

PARENT_PACKAGE_PROTOCOL = Path(
    "results/v24216_package_gate_preregistration_v1_20260731.json"
)
PARENT_PACKAGE_PROTOCOL_SHA256 = (
    "5ad2ba72fda4dc516f922ddc33066a72054c7b082abee50dc7ac0b201a42b714"
)
PARENT_PACKAGE_ACTIVATION = Path(
    "results/v24216_package_gate_activation_v1_20260731.json"
)
PARENT_PACKAGE_ACTIVATION_SHA256 = (
    "fe3f285142086be6e7e64db5872bbe21b35b103d95747a76f0844bf74c2e30e5"
)
PARENT_PACKAGE_WAIT_AUDIT = Path(
    "results/v24216_package_gate_wait_audit_v1_20260731.json"
)
PARENT_PACKAGE_WAIT_AUDIT_SHA256 = (
    "75f70b056e0e780901205e461267e5bd08089c1820d4546e2a8ac181cd491dcb"
)
PARENT_PACKAGE_STATE = Path(
    "outputs/v24216_package_gate_watcher_state_v1_20260731.json"
)

PARENT_CAPACITY_PROTOCOL = Path(
    "results/v24217_capacity_successor_preregistration_v1_20260731.json"
)
PARENT_CAPACITY_PROTOCOL_SHA256 = (
    "5a003bd04858f7a8d2c769386a7d6735b388f262520508741cc9895d28cf45bb"
)
PARENT_CAPACITY_ACTIVATION = Path(
    "results/v24217_capacity_successor_activation_v1_20260731.json"
)
PARENT_CAPACITY_ACTIVATION_SHA256 = (
    "b73fc14fb89e5068dbf0c54f3b0b538a91497db0c6809c732a0d8886f63990f8"
)
PARENT_CAPACITY_WAIT_AUDIT = Path(
    "results/v24217_capacity_successor_wait_audit_v1_20260731.json"
)
PARENT_CAPACITY_WAIT_AUDIT_SHA256 = (
    "20a19f8e6f49f80d4ded3e18fb3b861833860c4501e11cc25a47592003f58c68"
)
PARENT_CAPACITY_STATE = Path(
    "outputs/v24217_capacity_successor_watcher_state_v1_20260731.json"
)
PARENT_CAPACITY_REPORT = Path(
    "results/v24217_capacity_successor_report_v1_20260731.json"
)
PARENT_CAPACITY_FREEZE = Path(
    "results/v24217_next_fresh_all220_capacity_freeze_v1_20260731.json"
)

WATCHER_MARKER = "scripts/watch_v24218_exact220_executor.py"
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24218_fresh_exact220_single_owner_v1"
LEASE_PURPOSE = "capacity_bound_joint_package_fresh_exact220_and_released_evaluator"

PROTECTED_PROCESS_MARKERS = {
    "r1_launcher": "scripts/launch_frozen_deepwide.py",
    "r1_forward": "scripts/run_deepwide_agent.py",
    "v24194_capacity": "scripts/watch_v24194_capacity_ladder.py",
    "v24196_capacity": "scripts/watch_v24196_capacity_executor.py",
    "v24213_entropy": "scripts/watch_v24213_entropy_recovery.py",
    "v24215_package": "scripts/watch_v24215_joint_package_recovery.py",
    "v24216_gate": "scripts/watch_v24216_package_gate.py",
    "v24217_capacity": "scripts/watch_v24217_capacity_successor.py",
}
FORBIDDEN_CONTROL_LITERALS = (
    "gh" + "p_",
    "github" + "_pat_",
    "tvly" + "-dev-",
    "s" + "k-",
)
CREDENTIAL_LITERAL = re.compile(
    r"(?:" + "|".join(re.escape(value) for value in FORBIDDEN_CONTROL_LITERALS)
    + r")[A-Za-z0-9_-]{16,}"
)

CONTROL_FILES = (
    "src/deepwide_agent/v24194_capacity_ladder.py",
    "src/deepwide_agent/v24216_package_gate.py",
    "src/deepwide_agent/v24217_capacity_successor.py",
    "src/deepwide_agent/v24218_exact220_executor.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/audit_v24205_markdown_rebase_feasibility.py",
    "scripts/build_v2410_rank_slot_candidate.py",
    "scripts/deepwide_api_lease.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/finalize_v2408_combined_dev64.py",
    "scripts/preregister_v2408_combined_fasttrack.py",
    "scripts/preregister_v24210_search_component.py",
    "scripts/preregister_v24217_capacity_successor.py",
    "scripts/publish_v24206_markdown_component.py",
    "scripts/replay_v24201_repo_local_candidate_dag.py",
    "scripts/run_official_eval_local.py",
    "scripts/run_v24216_package_gate.py",
    "scripts/run_v24218_exact220_executor.py",
    "scripts/preregister_v24218_exact220_executor.py",
    "scripts/watch_v24218_exact220_executor.py",
    "scripts/activate_v24218_exact220_executor.py",
    "scripts/audit_v24218_exact220_executor_wait.py",
    "tests/test_v24218_exact220_executor.py",
    "tests/test_watch_v24218_exact220_executor.py",
    "tests/test_preregister_v24218_exact220_executor.py",
    "tests/test_activate_v24218_exact220_executor.py",
    "tests/test_audit_v24218_exact220_executor_wait.py",
)

FUTURE_PATHS = (
    OUTPUT,
    STATE,
    ACTIVATION,
    WAIT_AUDIT,
    EXECUTION_START,
    MATERIALIZATION,
    FORWARD_BARRIER,
    PREPARE_ROOT,
    EVALUATOR_ROOT,
    SUMMARY,
    RESULT,
    *tuple(Path(path.relative_to(ROOT)) for path in SHARD_ROOTS.values()),
)
DECISION_FIELDS = (
    "protocol_id",
    "parent_contract",
    "candidate_contract",
    "capacity_contract",
    "schedule_contract",
    "crash_only_contract",
    "lease_contract",
    "execution",
    "source_policy",
    "authorization",
    "safe_wait_boundary",
    "control_surface",
)


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def _receipt(root: Path, path: Path, digest: str, role: str) -> dict[str, str]:
    value = read_object(ordinary(root, path, digest))
    if value.get("role") != role:
        raise RuntimeError("V2.42.18 parent receipt role drifted")
    return {"path": str(path), "sha256": digest}


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _package_wait(root: Path) -> dict[str, Any]:
    state = read_object(ordinary(root, PARENT_PACKAGE_STATE))
    if (
        state.get("role") != "v24216_package_gate_watcher_state"
        or state.get("terminal") is not False
        or state.get("capacity_measurement_allowed") is not False
        or state.get("all220_freeze_design_allowed") is not False
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing"
        )
        is not False
        or not _sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.18 package parent wait envelope drifted")
    return {
        "path": str(PARENT_PACKAGE_STATE),
        "status": state.get("status"),
        "terminal": False,
        "contents_emitted": False,
    }


def _capacity_wait(root: Path) -> dict[str, Any]:
    state = read_object(ordinary(root, PARENT_CAPACITY_STATE))
    if (
        state.get("role") != "v24217_capacity_successor_watcher_state"
        or state.get("terminal") is not False
        or state.get("capacity_report_created") is not False
        or state.get("capacity_freeze_created") is not False
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or not _sealed(state, "state_payload_sha256")
        or _present(root, PARENT_CAPACITY_REPORT)
        or _present(root, PARENT_CAPACITY_FREEZE)
    ):
        raise RuntimeError("V2.42.18 capacity parent wait envelope drifted")
    return {
        "path": str(PARENT_CAPACITY_STATE),
        "status": state.get("status"),
        "terminal": False,
        "report_and_freeze_absent": True,
        "contents_emitted": False,
    }


def protected_processes(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    rows = process_snapshot(proc_root)
    output: dict[str, Any] = {}
    used: set[int] = set()
    for name, marker in PROTECTED_PROCESS_MARKERS.items():
        matches: list[dict[str, Any]] = []
        for row in rows:
            argv = [str(value) for value in row.get("argv") or []]
            script = actual_python_script(argv)
            if script is not None and (script == marker or script.endswith("/" + marker)):
                matches.append({"pid": int(row["pid"]), "argv": argv})
        if len(matches) != 1 or matches[0]["pid"] in used:
            raise RuntimeError(f"V2.42.18 protected process drifted: {marker}")
        match = matches[0]
        used.add(match["pid"])
        isolated = name not in {"r1_launcher", "r1_forward"}
        if isolated and not all(flag in match["argv"] for flag in ("-I", "-B")):
            raise RuntimeError(f"V2.42.18 protected watcher is not isolated: {marker}")
        output[name] = {
            "marker": marker,
            "pid": match["pid"],
            "start_ticks": _start_ticks(proc_root, match["pid"]),
            "python_isolated_no_bytecode_required": isolated,
            "command_line_emitted": False,
        }
    return output


def _lease_wait(root: Path, proc_root: Path) -> dict[str, Any]:
    value = lease_observation(root, proc_root)
    if (
        value.get("active") is not False
        or value.get("ordinary") is not True
        or value.get("record_valid") is not True
        or value.get("lock_holder_pids") != []
    ):
        raise RuntimeError("V2.42.18 shared lease is active at freeze")
    return {
        "present": value.get("present"),
        "active": False,
        "ordinary": True,
        "record_valid": True,
        "lock_holder_count": 0,
        "contents_emitted": False,
    }


def _static_audit(root: Path) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for relative in CONTROL_FILES:
        source = ordinary(root, relative).read_text(encoding="utf-8")
        if CREDENTIAL_LITERAL.search(source):
            raise RuntimeError("V2.42.18 credential-like literal entered control surface")
        tree = ast.parse(source, filename=relative)
        network: set[str] = set()
        subprocess_refs: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                network.update(
                    alias.name
                    for alias in node.names
                    if alias.name in {"requests", "httpx", "urllib", "socket"}
                )
            elif isinstance(node, ast.ImportFrom) and node.module in {
                "requests",
                "httpx",
                "urllib",
                "socket",
            }:
                network.add(str(node.module))
            elif (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "subprocess"
            ):
                subprocess_refs.add(node.attr)
        allowed_network = {
            "scripts/run_official_eval_local.py": {"requests"},
            "scripts/deepwide_api_lease.py": {"socket"},
        }.get(relative, set())
        if not network.issubset(allowed_network):
            raise RuntimeError("V2.42.18 direct network capability escaped adapters")
        allowed_subprocess = {
            "scripts/build_v2410_rank_slot_candidate.py",
            "scripts/run_v24216_package_gate.py",
            "scripts/run_v24218_exact220_executor.py",
            "scripts/finalize_v2408_combined_dev64.py",
            "scripts/preregister_v24210_search_component.py",
            "scripts/publish_v24206_markdown_component.py",
        }
        if subprocess_refs and relative not in allowed_subprocess:
            raise RuntimeError("V2.42.18 subprocess capability escaped runners")
        output[relative] = {
            "sha256": sha256(root / relative),
            "direct_network_imports": sorted(network),
            "subprocess_references": sorted(subprocess_refs),
            "network_or_subprocess_authorized_adapter": bool(
                network or subprocess_refs
            ),
        }
    return output


def _fixed(root: Path) -> dict[str, Any]:
    ids_by_tag = {
        tag: read_opaque_ids(root / path, {"test_s01": 52, "test_s02": 52, "test_s03": 52, "devval": 64}[tag])
        for tag, path in SOURCE_IDS.items()
    }
    partition = {
        tag: {
            "path": str(SOURCE_IDS[tag]),
            "sha256": sha256(ordinary(root, SOURCE_IDS[tag])),
            "count": len(ids_by_tag[tag]),
        }
        for tag in ("test_s01", "test_s02", "test_s03", "devval")
    }
    template_source = Path(R1_FREEZES[-1])
    return {
        "parent_contract": {
            "package": {
                "protocol": _receipt(
                    root,
                    PARENT_PACKAGE_PROTOCOL,
                    PARENT_PACKAGE_PROTOCOL_SHA256,
                    "v24216_package_gate_preregistration",
                ),
                "activation": _receipt(
                    root,
                    PARENT_PACKAGE_ACTIVATION,
                    PARENT_PACKAGE_ACTIVATION_SHA256,
                    "v24216_package_gate_activation",
                ),
                "wait_audit": _receipt(
                    root,
                    PARENT_PACKAGE_WAIT_AUDIT,
                    PARENT_PACKAGE_WAIT_AUDIT_SHA256,
                    "v24216_package_gate_wait_audit",
                ),
                "state_path": str(PARENT_PACKAGE_STATE),
                "accepted_terminal_statuses": [
                    "complete_identity_handoff_no_package_gate_required",
                    "complete_package_gate_go",
                ],
                "no_go_stops_without_materialization_or_api": True,
            },
            "capacity": {
                "protocol": _receipt(
                    root,
                    PARENT_CAPACITY_PROTOCOL,
                    PARENT_CAPACITY_PROTOCOL_SHA256,
                    "v24217_capacity_successor_preregistration",
                ),
                "activation": _receipt(
                    root,
                    PARENT_CAPACITY_ACTIVATION,
                    PARENT_CAPACITY_ACTIVATION_SHA256,
                    "v24217_capacity_successor_activation",
                ),
                "wait_audit": _receipt(
                    root,
                    PARENT_CAPACITY_WAIT_AUDIT,
                    PARENT_CAPACITY_WAIT_AUDIT_SHA256,
                    "v24217_capacity_successor_wait_audit",
                ),
                "state_path": str(PARENT_CAPACITY_STATE),
                "report_path": str(PARENT_CAPACITY_REPORT),
                "freeze_path": str(PARENT_CAPACITY_FREEZE),
                "accepted_terminal_status": "complete_capacity_recommendation_available",
                "no_go_stops_without_materialization_or_api": True,
            },
        },
        "candidate_contract": {
            "identity_handoff_uses_selected_baseline_bytes": True,
            "package_go_uses_joint_candidate_bytes": True,
            "materialize_four_new_repo_local_roots_before_any_preflight": True,
            "canonical_shards": {
                "test_s01": 52,
                "test_s02": 52,
                "test_s03": 52,
                "devval": 64,
            },
            "canonical_opaque_partition": partition,
            "canonical_opaque_partition_sha256": validate_exact_partition(ids_by_tag),
            "runtime_manifest": {
                "path": str(SOURCE_MANIFEST),
                "sha256": sha256(ordinary(root, SOURCE_MANIFEST)),
                "bytes_hashed_but_question_rows_not_parsed_at_protocol_freeze": True,
            },
            "execution_template_source": {
                "path": str(template_source),
                "sha256": sha256(ordinary(root, template_source)),
            },
            "same_package_model_search_prompt_budget_threshold_all_shards": True,
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_evaluator_gold_or_score_unavailable_to_forward": True,
        },
        "capacity_contract": {
            "v24217_report_and_freeze_recomputed_from_protocol": True,
            "package_state_identity_must_match_capacity_freeze_parent": True,
            "capacity_go_required": True,
            "candidate_and_row_workers_overridden_only_to_frozen_cap": True,
            "model_endpoint_name_reasoning_and_service_tier_must_match": True,
            "search_preflight_fresh_for_every_shard": True,
        },
        "schedule_contract": {
            "executor_concurrency_from_parallel_shard_cap": True,
            "candidate_and_row_model_workers_from_capacity_freeze": True,
            "agent_width": 1,
            "effective_evidence_width_measured_post_terminal": True,
            "fixed_concurrency_for_entire_exact220": True,
            "wave_order": ["test_s01", "test_s02", "test_s03", "devval"],
            "all_shards_terminal_before_mapping_or_evaluator": True,
            "forward_failure_and_evaluator_error_scored_as_zero": True,
        },
        "crash_only_contract": {
            "execution_start_before_materialization_preflight_forward_or_api": True,
            "start_without_result_is_terminal_incomplete_no_retry": True,
            "forward_resume_or_selective_rerun_allowed": False,
            "preflight_reuse_across_shards_allowed": False,
            "partial_mapping_evaluator_or_score_release_allowed": False,
            "result_overwrite_allowed": False,
        },
        "lease_contract": {
            "path": str(LEASE),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "one_lease_held_across_materialization_forward_and_evaluator": True,
            "owner_purpose_pid_lock_holder_activation_and_start_ticks_required": True,
            "suppress_only_expected_unknown_owner_liveness_findings": True,
            "preserve_and_fail_on_unrelated_parent_findings": True,
        },
        "execution": {
            "watcher_marker": WATCHER_MARKER,
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "proc_root": "/proc",
            "state_path": str(STATE),
            "activation_path": str(ACTIVATION),
            "wait_audit_path": str(WAIT_AUDIT),
            "execution_start_path": str(EXECUTION_START),
            "materialization_path": str(MATERIALIZATION),
            "forward_barrier_path": str(FORWARD_BARRIER),
            "result_path": str(RESULT),
            "quiet_observations_before_lease": 2,
        },
        "source_policy": {
            "preterminal_parent_safe_envelopes_only": True,
            "runtime_question_visible_only_inside_authorized_forward": True,
            "runtime_tool_trace_same_task_only": True,
            "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_route": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "task_content_prediction_or_evidence_emitted_by_control_state": False,
        },
        "authorization": {
            "watcher_active_after_activation": True,
            "four_root_materialization_after_both_parent_go_and_lease": True,
            "fresh_exact220_forward_after_execution_start": True,
            "mapping_and_released_evaluator_after_four_terminal_shards": True,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "existing_benchmark_or_watcher_modification_or_termination": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve() or proc_root.resolve() != Path("/proc"):
        raise RuntimeError("V2.42.18 canonical freeze boundary drifted")
    absent = all(not _present(root, path) for path in FUTURE_PATHS)
    if require_pristine and not absent:
        raise RuntimeError("V2.42.18 create-exclusive boundary is not pristine")
    fixed = _fixed(root)
    manifest = {relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        **fixed,
        "safe_wait_boundary": {
            "all_future_protocol_state_activation_execution_and_run_paths_absent": absent,
            "package_parent": _package_wait(root),
            "capacity_parent": _capacity_wait(root),
            "shared_api_lease": _lease_wait(root, proc_root),
            "protected_processes": protected_processes(proc_root),
            "mapping_or_evaluator_opened": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "full220_launch_allowed": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
            "must_remain_absent_at_freeze": [str(path) for path in FUTURE_PATHS],
            "static_capability_audit": _static_audit(root),
        },
    }
    value["decision_contract_sha256"] = payload_sha256(
        {field: value[field] for field in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    value = read_object(target)
    fixed = _fixed(root)
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    safe = value.get("safe_wait_boundary") or {}
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or any(value.get(field) != expected for field, expected in fixed.items())
        or safe.get(
            "all_future_protocol_state_activation_execution_and_run_paths_absent"
        )
        is not True
        or safe.get("package_parent", {}).get("terminal") is not False
        or safe.get("capacity_parent", {}).get("terminal") is not False
        or safe.get("shared_api_lease", {}).get("active") is not False
        or safe.get("mapping_or_evaluator_opened") is not False
        or safe.get("full220_launch_allowed") is not False
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or control.get("file_count") != len(CONTROL_FILES)
        or control.get("manifest_sha256") != payload_sha256(manifest)
        or control.get("must_remain_absent_at_freeze")
        != [str(path) for path in FUTURE_PATHS]
        or value.get("decision_contract_sha256")
        != payload_sha256({field: value[field] for field in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.42.18 protocol contract drifted")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, relative)) != digest:
            raise RuntimeError("V2.42.18 control surface drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.18 protocol output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
