#!/usr/bin/env python3
"""Execute one capacity-bound, fresh-root, label-blind exact-220 run.

This module is invoked only by the separately activated V2.42.18 watcher while
it owns the shared API lease.  All four forward shards become exact terminal
before this module opens the evaluator mapping or starts the released
evaluator.  Forward retry, resume, selective rerun, and partial-score release
are intentionally unsupported.
"""

from __future__ import annotations

import ast
import concurrent.futures
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24194_capacity_ladder import settings_from_dict  # noqa: E402
from deepwide_agent.v24217_capacity_successor import (  # noqa: E402
    validate_freeze,
    validate_report,
)
from deepwide_agent.v24218_exact220_executor import (  # noqa: E402
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    aggregate_evidence_width,
    compile_schedule,
    file_sha256,
    payload_sha256,
    read_opaque_ids,
    sealed,
    validate_exact_partition,
    validate_terminal_shard,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    runtime_identity,
)
from scripts.build_v2410_rank_slot_candidate import (  # noqa: E402
    candidate_regular_file_manifest,
)
from scripts.finalize_fullset_rollout import (  # noqa: E402
    read_jsonl,
    sha256_file,
    summarize_rollout,
    validate_evaluator_contract,
    validate_prepare_attestation,
)
from scripts.preregister_v2408_combined_fasttrack import R1_FREEZES  # noqa: E402
from scripts.preregister_v24217_capacity_successor import (  # noqa: E402
    FREEZE as CAPACITY_FREEZE,
    OUTPUT as CAPACITY_PROTOCOL,
    PARENT_STATE as PACKAGE_STATE,
    REPORT as CAPACITY_REPORT,
    STATE as CAPACITY_STATE,
    V24194_PROTOCOL,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
)
from scripts.run_official_eval_local import (  # noqa: E402
    build_eval_run_contract,
    build_summary,
    initialize_or_resume_eval_output,
)
from scripts.publish_v24206_markdown_component import _write_candidate  # noqa: E402
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    manifest_sha256,
    text_manifest,
)
from scripts.run_v24216_package_gate import (  # noqa: E402
    PARENT_PUBLICATION,
    _baseline_files,
    _candidate_files,
    execution_template,
    validate_gate_decision,
    validate_parent_publication,
)


SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
SOURCE_IDS = {
    "test_s01": Path("configs/full220_v2403_r1_test_s01.ids"),
    "test_s02": Path("configs/full220_v2403_r1_test_s02.ids"),
    "test_s03": Path("configs/full220_v2403_r1_test_s03.ids"),
    "devval": Path("configs/full220_v2403_r1_devval_s04.ids"),
}
MAPPING = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
MATERIALIZATION = Path("results/v24218_exact220_materialization_v1_20260731.json")
EXECUTION_START = Path("results/v24218_exact220_execution_start_v1_20260731.json")
FORWARD_BARRIER = Path("results/v24218_exact220_forward_barrier_v1_20260731.json")
PREPARE_ROOT = Path("outputs/v24218_exact220_evaluator_prepare_v1_20260731")
EVALUATOR_ROOT = Path("outputs/v24218_exact220_official_eval_v1_20260731")
RESULT = Path("results/v24218_exact220_result_v1_20260731.json")
SUMMARY = PREPARE_ROOT / "conservative_summary.json"
SHARD_ROOTS = {
    tag: ROOT / f"outputs/v24218_exact220_{tag}_root_v1_20260731"
    for tag in EXPECTED_SHARDS
}
TARGETS = {
    tag: f"v24218_joint_package_{tag}_v1_20260731" for tag in EXPECTED_SHARDS
}


def _present(root: Path, relative: Path) -> bool:
    path = root / relative
    return path.exists() or path.is_symlink()


def _read_jsonl_exact(path: Path) -> list[dict[str, Any]]:
    rows = read_jsonl(path)
    if not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.42.18 JSONL contains a non-object")
    return rows


def _source_manifest(root: Path) -> tuple[list[dict[str, str]], str]:
    path = root / SOURCE_MANIFEST
    rows = _read_jsonl_exact(path)
    if (
        not rows
        or any(set(row) != {"opaque_id", "question"} for row in rows)
        or len({row["opaque_id"] for row in rows}) != len(rows)
    ):
        raise RuntimeError("V2.42.18 runtime manifest is not label-blind")
    return rows, file_sha256(path)


def validate_package_authority(root: Path = ROOT) -> dict[str, Any]:
    """Replay the selected package without opening benchmark task content."""

    state_path = root / PACKAGE_STATE
    state = read_object(state_path)
    accepted = {
        "complete_identity_handoff_no_package_gate_required",
        "complete_package_gate_go",
    }
    if (
        state.get("role") != "v24216_package_gate_watcher_state"
        or state.get("terminal") is not True
        or state.get("status") not in accepted
        or state.get("capacity_measurement_allowed") is not True
        or state.get("all220_freeze_design_allowed") is not True
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "mapping_gold_category_question_type_or_per_task_score_used_for_forward_routing"
        )
        is not False
        or not sealed(state, "state_payload_sha256")
    ):
        raise RuntimeError("V2.42.18 package authority is not terminal GO")
    publication = validate_parent_publication(root)
    identity = bool(publication.get("identity_handoff_only"))
    if identity:
        if state.get("status") != "complete_identity_handoff_no_package_gate_required":
            raise RuntimeError("V2.42.18 identity package/status mismatch")
        files = _baseline_files(publication)
        gate: dict[str, Any] | None = None
        mode = "selected_baseline_identity"
    else:
        if state.get("status") != "complete_package_gate_go":
            raise RuntimeError("V2.42.18 joint package/status mismatch")
        gate = validate_gate_decision(root)
        if (
            gate.get("passed") is not True
            or gate.get("capacity_measurement_allowed") is not True
            or gate.get("all220_freeze_design_allowed") is not True
            or gate.get("full220_launch_allowed") is not False
        ):
            raise RuntimeError("V2.42.18 package gate is not a valid GO")
        files = _candidate_files(publication)
        mode = "selected_joint_candidate"
    source = text_manifest(files)
    return {
        "mode": mode,
        "files": files,
        "source_manifest": source,
        "source_manifest_sha256": manifest_sha256(source),
        "package_state": {
            "path": str(PACKAGE_STATE),
            "sha256": file_sha256(state_path),
            "status": state["status"],
        },
        "publication": {
            "path": str(PARENT_PUBLICATION),
            "sha256": file_sha256(root / PARENT_PUBLICATION),
        },
        "gate_decision": (
            None
            if gate is None
            else {
                "path": "results/v24216_package_gate_decision_v1_20260731.json",
                "sha256": file_sha256(
                    root / "results/v24216_package_gate_decision_v1_20260731.json"
                ),
            }
        ),
        "identity_handoff_only": identity,
    }


def validate_capacity_authority(
    package: Mapping[str, Any], root: Path = ROOT
) -> dict[str, Any]:
    protocol = read_object(root / CAPACITY_PROTOCOL)
    source_protocol = read_object(root / V24194_PROTOCOL)
    settings = settings_from_dict(
        source_protocol["capacity_contract"]["settings"]
    )
    state_path = root / CAPACITY_STATE
    report_path = root / CAPACITY_REPORT
    freeze_path = root / CAPACITY_FREEZE
    state = read_object(state_path)
    report = read_object(report_path)
    freeze = read_object(freeze_path)
    if (
        state.get("role") != "v24217_capacity_successor_watcher_state"
        or state.get("terminal") is not True
        or state.get("status") != "complete_capacity_recommendation_available"
        or state.get("capacity_freeze_created") is not True
        or state.get("benchmark_forward_or_full220_launch_allowed") is not False
        or state.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or not sealed(state, "state_payload_sha256")
        or state.get("capacity_report", {}).get("sha256") != file_sha256(report_path)
        or state.get("capacity_freeze", {}).get("sha256") != file_sha256(freeze_path)
    ):
        raise RuntimeError("V2.42.18 capacity authority is not terminal GO")
    protocol_sha = file_sha256(root / CAPACITY_PROTOCOL)
    derived = validate_report(
        report,
        expected_settings=settings,
        protocol_path=str(CAPACITY_PROTOCOL),
        protocol_sha256=protocol_sha,
    )
    frozen = validate_freeze(
        freeze,
        report=report,
        expected_settings=settings,
        report_path=str(CAPACITY_REPORT),
        report_sha256=file_sha256(report_path),
        protocol_path=str(CAPACITY_PROTOCOL),
        protocol_sha256=protocol_sha,
    )
    parent = freeze.get("parent_package_gate") or {}
    package_state = package["package_state"]
    if (
        derived != frozen
        or frozen["selected"] <= 0
        or parent.get("path") != package_state["path"]
        or parent.get("sha256") != package_state["sha256"]
        or parent.get("status") != package_state["status"]
        or freeze.get("capacity_go") is not True
        or freeze.get("fixed_concurrency_for_entire_all220") is not True
        or freeze.get("new_output_roots_required") is not True
        or freeze.get("resume_or_selective_rerun_allowed") is not False
        or freeze.get("forward_failure_scored_as_zero") is not True
        or freeze.get("candidate_package_identity_must_match_parent_gate") is not True
        or freeze.get("full220_launch_allowed") is not False
    ):
        raise RuntimeError("V2.42.18 capacity/package binding drifted")
    return {
        **frozen,
        "state": {"path": str(CAPACITY_STATE), "sha256": file_sha256(state_path)},
        "report": {"path": str(CAPACITY_REPORT), "sha256": file_sha256(report_path)},
        "freeze": {"path": str(CAPACITY_FREEZE), "sha256": file_sha256(freeze_path)},
        "protocol": {"path": str(CAPACITY_PROTOCOL), "sha256": protocol_sha},
        "schedule": compile_schedule(frozen),
    }


def _required_forward_paths(files: Mapping[str, str]) -> frozenset[str]:
    source = files.get("scripts/preflight_deepwide.py")
    if not isinstance(source, str):
        raise RuntimeError("V2.42.18 package lacks preflight source")
    tree = ast.parse(source, filename="scripts/preflight_deepwide.py")
    values: list[object] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "REQUIRED_FORWARD_CODE_PATHS"
            for target in node.targets
        ):
            continue
        expression = node.value
        if (
            not isinstance(expression, ast.Call)
            or not isinstance(expression.func, ast.Name)
            or expression.func.id != "frozenset"
            or len(expression.args) != 1
        ):
            raise RuntimeError("V2.42.18 forward allowlist schema drifted")
        values.append(ast.literal_eval(expression.args[0]))
    if len(values) != 1 or not isinstance(values[0], (set, tuple, list)):
        raise RuntimeError("V2.42.18 forward allowlist is absent")
    output = frozenset(str(value) for value in values[0])
    if not output or not output.issubset(files):
        raise RuntimeError("V2.42.18 package forward closure is incomplete")
    return output


def _build_freeze(
    tag: str,
    *,
    files: Mapping[str, str],
    manifest_sha: str,
    ids_sha: str,
    template: Mapping[str, Any],
    capacity: Mapping[str, Any],
    package: Mapping[str, Any],
) -> dict[str, Any]:
    schema, version = runtime_identity(files["src/deepwide_agent/runtime.py"])
    required = _required_forward_paths(files)
    runtime = copy.deepcopy(template["runtime"])
    runtime["candidate_model_workers"] = capacity["workers"]
    runtime["row_model_workers"] = capacity["workers"]
    value: dict[str, Any] = {
        "freeze_status": "preregistered-v24218-fresh-root-exact220-single-owner",
        "pipeline_version": version,
        "state_schema_version": schema,
        "experiment_role": (
            "public exact-220 single rollout; fresh output roots; failure-as-zero; "
            "not held-out, Avg@4, leaderboard submission, or SOTA evidence"
        ),
        "runtime_boundary": ["opaque_id", "question"],
        "selection_rule": (
            "canonical preregistered opaque-ID shard; selection is independent of "
            "question content, labels, mapping, gold, evaluator rows, predictions, and outcomes"
        ),
        "selected_count": EXPECTED_COUNTS[tag],
        "selected_ids_file": f"configs/{TARGETS[tag]}/{tag}.ids",
        "selected_ids_sha256": ids_sha,
        "manifest": "data/runtime_manifest.jsonl",
        "manifest_sha256": manifest_sha,
        "code_sha256": {
            relative: hashlib.sha256(files[relative].encode()).hexdigest()
            for relative in sorted(required)
        },
        "model": copy.deepcopy(template["model"]),
        "search": copy.deepcopy(template["search"]),
        "runtime": runtime,
        "launch_gates": copy.deepcopy(template["launch_gates"]),
        "reporting": {
            "cold_start_required": True,
            "all_selected_ids_reported": True,
            "failed_or_unresolved_tasks_count_as_zero_for_conservative_fullset_aggregation": True,
            "evaluator_join_only_after_all_four_shards_exact_terminal": True,
            "forward_resume_or_selective_rerun_allowed": False,
            "fresh_root_claim_allowed": True,
            "historically_unseen_or_held_out_claim_allowed": False,
            "avg_at_4_claim_allowed": False,
            "leaderboard_or_sota_claim_allowed": False,
        },
        "fullset_partition": {
            "public_task_count": 220,
            "rollout_id": 2,
            "shard_count": 4,
            "shard_tag": tag,
            "shard_selected_count": EXPECTED_COUNTS[tag],
            "partition_disjoint_and_exhaustive": True,
        },
        "v24218_binding": {
            "package_state_sha256": package["package_state"]["sha256"],
            "package_publication_sha256": package["publication"]["sha256"],
            "package_source_manifest_sha256": package["source_manifest_sha256"],
            "capacity_freeze_sha256": capacity["freeze"]["sha256"],
            "executor_concurrency": capacity["schedule"]["executor_concurrency"],
            "agent_width": 1,
            "effective_evidence_width": "measured_post_terminal_only",
        },
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    return value


def _shard_paths(tag: str) -> dict[str, Path]:
    root = SHARD_ROOTS[tag]
    target = TARGETS[tag]
    return {
        "root": root,
        "ids": root / f"configs/{target}/{tag}.ids",
        "freeze": root / f"configs/{target}/{tag}.json",
        "preflight": root / f"outputs/{target}_preflight.json",
        "preflight_log": root / f"outputs/{target}_preflight.log",
        "forward_log": root / f"outputs/{target}_forward.log",
        "out": root / f"outputs/{target}_forward",
    }


def materialize_exact220(
    package: Mapping[str, Any], capacity: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    target = root / MATERIALIZATION
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    if any(path.exists() or path.is_symlink() for path in SHARD_ROOTS.values()):
        raise RuntimeError("V2.42.18 future candidate roots are not pristine")
    if any(_present(root, path) for path in (FORWARD_BARRIER, PREPARE_ROOT, EVALUATOR_ROOT, RESULT)):
        raise RuntimeError("V2.42.18 downstream output appeared before materialization")
    start_path = root / EXECUTION_START
    if start_path.is_symlink() or not start_path.is_file():
        raise RuntimeError("V2.42.18 materialization lacks execution start")
    start = read_object(start_path)
    if (
        start.get("role") != "v24218_exact220_execution_start"
        or not sealed(start, "execution_start_payload_sha256")
        or start.get("package_state") != package["package_state"]
        or start.get("package_publication") != package["publication"]
        or start.get("package_gate_decision") != package["gate_decision"]
        or start.get("package_mode") != package["mode"]
        or start.get("package_source_manifest_sha256")
        != package["source_manifest_sha256"]
        or start.get("capacity_state") != capacity["state"]
        or start.get("capacity_report") != capacity["report"]
        or start.get("capacity_freeze") != capacity["freeze"]
        or start.get("schedule") != capacity["schedule"]
        or start.get("runtime_boundary") != ["opaque_id", "question"]
        or start.get("fresh_exact220_forward_authorized") is not True
        or start.get("resume_or_selective_rerun_allowed") is not False
        or start.get("failure_as_zero") is not True
        or start.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.18 execution start authority drifted")
    manifest_rows, source_manifest_sha = _source_manifest(root)
    manifest_ids = {row["opaque_id"] for row in manifest_rows}
    ids_by_tag: dict[str, list[str]] = {}
    for tag in EXPECTED_SHARDS:
        ids = read_opaque_ids(root / SOURCE_IDS[tag], EXPECTED_COUNTS[tag])
        if not set(ids).issubset(manifest_ids):
            raise RuntimeError("V2.42.18 selected IDs are missing from manifest")
        ids_by_tag[tag] = ids
    partition_sha = validate_exact_partition(ids_by_tag)
    template = execution_template(root)
    if (
        template["model"].get("proxy_url") != "http://127.0.0.1:9878/responses"
        or template["model"].get("name") != "gpt-5.6-sol"
        or template["model"].get("reasoning_effort") != "high"
    ):
        raise RuntimeError("V2.42.18 execution template differs from capacity")
    files = package["files"]
    expected_source = package["source_manifest"]
    created: list[Path] = []
    shards: dict[str, Any] = {}
    try:
        for tag in EXPECTED_SHARDS:
            paths = _shard_paths(tag)
            candidate_root = paths["root"]
            candidate_root.mkdir(parents=True, exist_ok=False)
            created.append(candidate_root)
            (candidate_root / ".venv-eval").symlink_to(
                (root / ".venv-eval").resolve(), target_is_directory=True
            )
            _write_candidate(candidate_root, files)
            if candidate_regular_file_manifest(candidate_root, source_only=True) != expected_source:
                raise RuntimeError("V2.42.18 materialized package bytes drifted")
            manifest = candidate_root / "data/runtime_manifest.jsonl"
            manifest.parent.mkdir(parents=True, exist_ok=False)
            shutil.copyfile(root / SOURCE_MANIFEST, manifest)
            paths["ids"].parent.mkdir(parents=True, exist_ok=False)
            shutil.copyfile(root / SOURCE_IDS[tag], paths["ids"])
            freeze = _build_freeze(
                tag,
                files=files,
                manifest_sha=file_sha256(manifest),
                ids_sha=file_sha256(paths["ids"]),
                template=template,
                capacity=capacity,
                package=package,
            )
            publish_new(paths["freeze"], freeze)
            if paths["out"].exists() or paths["preflight"].exists():
                raise RuntimeError("V2.42.18 materialized shard is not cold")
            shards[tag] = {
                "root": str(candidate_root.relative_to(root)),
                "source_manifest_sha256": manifest_sha256(expected_source),
                "input_manifest_sha256": source_manifest_sha,
                "ids": {
                    "path": str(SOURCE_IDS[tag]),
                    "sha256": file_sha256(root / SOURCE_IDS[tag]),
                    "count": EXPECTED_COUNTS[tag],
                },
                "freeze": {
                    "path": str(paths["freeze"].relative_to(root)),
                    "sha256": file_sha256(paths["freeze"]),
                },
                "output": str(paths["out"].relative_to(root)),
                "preflight": str(paths["preflight"].relative_to(root)),
                "output_and_preflight_absent": True,
            }
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v24218_exact220_materialization",
            "label_blind": True,
            "package_mode": package["mode"],
            "package_state": package["package_state"],
            "package_publication": package["publication"],
            "package_gate_decision": package["gate_decision"],
            "package_source_manifest_sha256": package["source_manifest_sha256"],
            "capacity_freeze": capacity["freeze"],
            "execution_start": {
                "path": str(EXECUTION_START),
                "sha256": file_sha256(start_path),
            },
            "canonical_opaque_partition_sha256": partition_sha,
            "shards": shards,
            "schedule": capacity["schedule"],
            "selected_total": 220,
            "all_four_roots_materialized_before_any_preflight_or_forward": True,
            "all_output_and_preflight_paths_absent": True,
            "same_package_model_search_prompt_budget_threshold": True,
            "runtime_forward_inputs_exactly_opaque_id_and_question": True,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "resume_or_selective_rerun_allowed": False,
            "forward_failure_scored_as_zero": True,
            "full220_launch_allowed_only_by_v24218_active_owner": True,
            "leaderboard_submission_or_sota_claim": False,
        }
        value["materialization_payload_sha256"] = payload_sha256(value)
        publish_new(target, value)
        return value
    except BaseException:
        for path in reversed(created):
            shutil.rmtree(path, ignore_errors=True)
        raise


def validate_materialization(
    package: Mapping[str, Any], capacity: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    value = read_object(root / MATERIALIZATION)
    if (
        value.get("role") != "v24218_exact220_materialization"
        or not sealed(value, "materialization_payload_sha256")
        or value.get("package_state") != package["package_state"]
        or value.get("package_publication") != package["publication"]
        or value.get("package_source_manifest_sha256")
        != package["source_manifest_sha256"]
        or value.get("capacity_freeze") != capacity["freeze"]
        or value.get("execution_start")
        != {
            "path": str(EXECUTION_START),
            "sha256": file_sha256(root / EXECUTION_START),
        }
        or value.get("schedule") != capacity["schedule"]
        or value.get("selected_total") != 220
        or value.get("mapping_gold_category_question_type_evaluator_score_read")
        is not False
        or value.get("resume_or_selective_rerun_allowed") is not False
    ):
        raise RuntimeError("V2.42.18 materialization receipt drifted")
    rows = value.get("shards")
    if not isinstance(rows, dict) or set(rows) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.42.18 materialized shard map drifted")
    ids_by_tag: dict[str, list[str]] = {}
    template = execution_template(root)
    for tag in EXPECTED_SHARDS:
        paths = _shard_paths(tag)
        row = rows[tag]
        ids_sha = file_sha256(paths["ids"])
        manifest_sha = file_sha256(paths["root"] / "data/runtime_manifest.jsonl")
        expected_freeze = _build_freeze(
            tag,
            files=package["files"],
            manifest_sha=manifest_sha,
            ids_sha=ids_sha,
            template=template,
            capacity=capacity,
            package=package,
        )
        if (
            paths["root"].is_symlink()
            or not paths["root"].is_dir()
            or file_sha256(paths["freeze"]) != row["freeze"]["sha256"]
            or read_object(paths["freeze"]) != expected_freeze
            or ids_sha != row["ids"]["sha256"]
            or manifest_sha != row["input_manifest_sha256"]
            or candidate_regular_file_manifest(paths["root"], source_only=True)
            != package["source_manifest"]
        ):
            raise RuntimeError("V2.42.18 materialized shard bytes drifted")
        ids_by_tag[tag] = read_opaque_ids(paths["ids"], EXPECTED_COUNTS[tag])
    if validate_exact_partition(ids_by_tag) != value["canonical_opaque_partition_sha256"]:
        raise RuntimeError("V2.42.18 materialized partition drifted")
    return value


def _run_logged(
    command: list[str],
    *,
    cwd: Path,
    log: Path,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> None:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        PYTHONSAFEPATH="1",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as handle:
        completed = runner(
            command,
            cwd=cwd,
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
        handle.flush()
        os.fsync(handle.fileno())
    if completed.returncode != 0:
        raise RuntimeError(f"V2.42.18 command failed: {log}")


def terminal_shard(tag: str) -> dict[str, Any] | None:
    paths = _shard_paths(tag)
    if not paths["out"].exists():
        return None
    if not paths["out"].is_dir() or paths["out"].is_symlink():
        raise RuntimeError("V2.42.18 shard output is noncanonical")
    runtime = paths["out"] / "runtime_predictions.jsonl"
    summary = paths["out"] / "run_summary.json"
    if not runtime.is_file() or not summary.is_file():
        raise RuntimeError("V2.42.18 partial shard residue forbids retry")
    ids = read_opaque_ids(paths["ids"], EXPECTED_COUNTS[tag])
    rows = _read_jsonl_exact(runtime)
    run_config = read_object(paths["out"] / "run_config.json")
    freeze = read_object(paths["freeze"])
    preflight = read_object(paths["preflight"])
    report = validate_terminal_shard(
        tag=tag,
        ids=ids,
        runtime_rows=rows,
        summary=read_object(summary),
    )
    attestation = run_config.get("launch_attestation") or {}
    runtime_config = run_config.get("runtime") or {}
    static_checks = preflight.get("static_checks") or {}
    code_checks = preflight.get("code_checks") or {}
    required_probes = int(freeze["launch_gates"]["preflight_consecutive_successes"])
    model_probes = preflight.get("model_probes") or []
    capacity_probes = preflight.get("model_capacity_probes") or []
    search_probes = preflight.get("search_probes") or []
    search = freeze["search"]
    anthropic = run_config.get("anthropic_search")
    if (
        Path(str(run_config.get("manifest", ""))).resolve()
        != (paths["root"] / "data/runtime_manifest.jsonl").resolve()
        or run_config.get("selected") != EXPECTED_COUNTS[tag]
        or run_config.get("proxy_url") != freeze["model"]["proxy_url"]
        or run_config.get("model") != freeze["model"]["name"]
        or run_config.get("reasoning_effort") != freeze["model"]["reasoning_effort"]
        or run_config.get("service_tier") != freeze["model"]["service_tier"]
        or run_config.get("search_provider") != freeze["search"]["provider"]
        or run_config.get("search_workers") != search["workers"]
        or (
            search["provider"] == "anthropic"
            and (
                not isinstance(anthropic, dict)
                or anthropic.get("model") != search["model"]
                or anthropic.get("timeout") != search["timeout_seconds"]
                or anthropic.get("max_retries") != search["max_retries"]
                or anthropic.get("max_uses") != search["max_uses"]
                or anthropic.get("max_output_tokens") != search["max_output_tokens"]
                or anthropic.get("fetch_pages") != search["fetch_pages"]
                or anthropic.get("fetch_workers") != search["fetch_workers"]
                or anthropic.get("fetch_timeout") != search["fetch_timeout"]
            )
        )
        or any(runtime_config.get(name) != expected for name, expected in freeze["runtime"].items())
        or runtime_config.get("candidate_model_workers")
        != freeze["runtime"]["candidate_model_workers"]
        or runtime_config.get("row_model_workers")
        != freeze["runtime"]["row_model_workers"]
        or Path(str(attestation.get("freeze_file", ""))).resolve()
        != paths["freeze"].resolve()
        or attestation.get("freeze_sha256") != file_sha256(paths["freeze"])
        or Path(str(attestation.get("preflight_report", ""))).resolve()
        != paths["preflight"].resolve()
        or attestation.get("preflight_report_sha256")
        != file_sha256(paths["preflight"])
        or attestation.get("preflight_created_at_unix") != preflight.get("created_at_unix")
        or preflight.get("ready") is not True
        or preflight.get("freeze_sha256") != file_sha256(paths["freeze"])
        or preflight.get("selected_count") != EXPECTED_COUNTS[tag]
        or not isinstance(static_checks, dict)
        or not static_checks
        or not all(value is True for value in static_checks.values())
        or set(code_checks) != set(freeze["code_sha256"])
        or not all(value is True for value in code_checks.values())
        or preflight.get("historical_forward_artifact_hits") != []
        or preflight.get("consumed_online_diagnostic") is not False
        or any(
            len(rows) != required_probes
            or not all(isinstance(item, dict) and item.get("success") is True for item in rows)
            for rows in (model_probes, capacity_probes, search_probes)
        )
        or any(
            probe.get("input_utf8_bytes") != 400_000
            or probe.get("max_output_tokens") != freeze["runtime"]["candidate_tokens"]
            for probe in capacity_probes
        )
    ):
        raise RuntimeError("V2.42.18 terminal shard launch identity drifted")
    return {
        "tag": tag,
        **report,
        "ids_sha256": file_sha256(paths["ids"]),
        "freeze_sha256": file_sha256(paths["freeze"]),
        "preflight_sha256": file_sha256(paths["preflight"]),
        "runtime_predictions_sha256": file_sha256(runtime),
        "run_summary_sha256": file_sha256(summary),
        "run_config_sha256": file_sha256(paths["out"] / "run_config.json"),
        "contents_emitted": False,
    }


def run_preflight_once(
    tag: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    paths = _shard_paths(tag)
    if terminal_shard(tag) is not None:
        raise RuntimeError("V2.42.18 shard already ran; rerun is forbidden")
    if paths["preflight"].exists() or paths["out"].exists():
        raise RuntimeError("V2.42.18 preflight/output residue forbids retry")
    python = str(paths["root"] / ".venv-eval/bin/python")
    _run_logged(
        [
            python,
            "-I",
            "-B",
            str(paths["root"] / "scripts/preflight_deepwide.py"),
            "--freeze",
            str(paths["freeze"]),
            "--report",
            str(paths["preflight"]),
            "--consecutive",
            "2",
        ],
        cwd=paths["root"],
        log=paths["preflight_log"],
        runner=runner,
    )
    report = read_object(paths["preflight"])
    if (
        report.get("ready") is not True
        or report.get("freeze_sha256") != file_sha256(paths["freeze"])
        or report.get("selected_count") != EXPECTED_COUNTS[tag]
    ):
        raise RuntimeError("V2.42.18 fresh shard preflight did not pass")
    return {
        "tag": tag,
        "preflight_sha256": file_sha256(paths["preflight"]),
        "model_successes": sum(
            probe.get("success") is True for probe in report.get("model_probes") or []
        ),
        "model_capacity_successes": sum(
            probe.get("success") is True
            for probe in report.get("model_capacity_probes") or []
        ),
        "search_successes": sum(
            probe.get("success") is True for probe in report.get("search_probes") or []
        ),
        "contents_emitted": False,
    }


def run_forward_after_preflight(
    tag: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    paths = _shard_paths(tag)
    if terminal_shard(tag) is not None:
        raise RuntimeError("V2.42.18 shard already ran; rerun is forbidden")
    if not paths["preflight"].is_file() or paths["preflight"].is_symlink():
        raise RuntimeError("V2.42.18 forward lacks an ordinary fresh preflight")
    if paths["out"].exists() or paths["out"].is_symlink():
        raise RuntimeError("V2.42.18 forward output residue forbids retry")
    python = str(paths["root"] / ".venv-eval/bin/python")
    _run_logged(
        [
            python,
            "-I",
            "-B",
            str(paths["root"] / "scripts/launch_frozen_deepwide.py"),
            "--freeze",
            str(paths["freeze"]),
            "--preflight-report",
            str(paths["preflight"]),
            "--out-dir",
            str(paths["out"]),
        ],
        cwd=paths["root"],
        log=paths["forward_log"],
        runner=runner,
    )
    terminal = terminal_shard(tag)
    if terminal is None:
        raise RuntimeError("V2.42.18 forward returned without exact terminal shard")
    return terminal


def run_shard_once(
    tag: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    """Compatibility helper for a single shard; production uses wave barriers."""

    run_preflight_once(tag, runner=runner)
    return run_forward_after_preflight(tag, runner=runner)


def publish_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    target = root / FORWARD_BARRIER
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    materialization = validate_materialization(
        validate_package_authority(root),
        validate_capacity_authority(validate_package_authority(root), root),
        root=root,
    )
    shards: dict[str, Any] = {}
    for tag in EXPECTED_SHARDS:
        terminal = terminal_shard(tag)
        if terminal is None:
            raise RuntimeError("V2.42.18 forward barrier lacks a terminal shard")
        shards[tag] = terminal
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24218_exact220_forward_terminal_barrier",
        "materialization": {
            "path": str(MATERIALIZATION),
            "sha256": file_sha256(root / MATERIALIZATION),
        },
        "shards": shards,
        "selected": sum(row["selected"] for row in shards.values()),
        "completed": sum(row["completed"] for row in shards.values()),
        "failed": sum(row["failed"] for row in shards.values()),
        "all_four_shards_exact_terminal": True,
        "canonical_opaque_partition_sha256": materialization[
            "canonical_opaque_partition_sha256"
        ],
        "mapping_path_opened_or_hashed": False,
        "evaluator_input_result_or_score_opened": False,
        "forward_resume_or_selective_rerun_used": False,
        "failure_as_zero": True,
        "contents_emitted": False,
    }
    if value["selected"] != 220 or value["completed"] + value["failed"] != 220:
        raise RuntimeError("V2.42.18 forward barrier is not exact-220")
    value["barrier_payload_sha256"] = payload_sha256(value)
    publish_new(target, value)
    return value


def validate_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    value = read_object(root / FORWARD_BARRIER)
    if (
        value.get("role") != "v24218_exact220_forward_terminal_barrier"
        or not sealed(value, "barrier_payload_sha256")
        or value.get("selected") != 220
        or value.get("completed", -1) + value.get("failed", -1) != 220
        or value.get("all_four_shards_exact_terminal") is not True
        or value.get("mapping_path_opened_or_hashed") is not False
        or value.get("evaluator_input_result_or_score_opened") is not False
        or value.get("forward_resume_or_selective_rerun_used") is not False
        or value.get("materialization", {}).get("sha256")
        != file_sha256(root / MATERIALIZATION)
    ):
        raise RuntimeError("V2.42.18 forward barrier drifted")
    for tag in EXPECTED_SHARDS:
        if value.get("shards", {}).get(tag) != terminal_shard(tag):
            raise RuntimeError("V2.42.18 forward barrier shard drifted")
    return value


def _prepare_command(root: Path) -> list[str]:
    command = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/finalize_fullset_rollout.py"),
        "prepare",
        "--manifest",
        str(root / SOURCE_MANIFEST),
        "--mapping",
        str(root / MAPPING),
        "--rollout-id",
        "2",
        "--out-dir",
        str(root / PREPARE_ROOT),
    ]
    for tag in EXPECTED_SHARDS:
        paths = _shard_paths(tag)
        command.extend(["--ids", f"{tag}={paths['ids']}"])
        command.extend(
            [
                "--runtime",
                f"{tag}={paths['out'] / 'runtime_predictions.jsonl'}",
            ]
        )
        command.extend(
            ["--run-summary", f"{tag}={paths['out'] / 'run_summary.json'}"]
        )
    return command


def evaluate_after_barrier(
    *,
    root: Path = ROOT,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    barrier = validate_forward_barrier(root)
    if any(_present(root, path) for path in (PREPARE_ROOT, EVALUATOR_ROOT, RESULT)):
        raise RuntimeError("V2.42.18 evaluator residue forbids retry or resume")
    _run_logged(
        _prepare_command(root),
        cwd=root,
        log=root / PREPARE_ROOT.parent / "v24218_exact220_prepare.log",
        runner=runner,
    )
    predictions = root / PREPARE_ROOT / "official_predictions.jsonl"
    prediction_rows = _read_jsonl_exact(predictions)
    evaluate = [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions",
        str(predictions),
        "--out-dir",
        str(root / EVALUATOR_ROOT),
        "--proxy-url",
        "http://127.0.0.1:9878/responses",
        "--model",
        "gpt-5.6-sol",
        "--reasoning-effort",
        "low",
        "--judge-max-output-tokens",
        "8192",
        "--judge-timeout",
        "600",
        "--judge-max-retries",
        "12",
    ]
    if prediction_rows:
        _run_logged(
            evaluate,
            cwd=root,
            log=root / EVALUATOR_ROOT.parent / "v24218_exact220_evaluate.log",
            runner=runner,
        )
    else:
        official = (
            root
            / "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch"
        )
        contract = build_eval_run_contract(
            predictions_path=predictions,
            query_path=official / "data/overall_20250916.jsonl",
            answer_root=official / "data/overall_20250916_tables",
            predictions=[],
            proxy_url="http://127.0.0.1:9878/responses",
            model="gpt-5.6-sol",
            reasoning_effort="low",
            judge_max_output_tokens=8192,
            judge_timeout=600,
            judge_max_retries=12,
            requested_instance_ids=[],
            limit=0,
        )
        committed = initialize_or_resume_eval_output(
            root / EVALUATOR_ROOT,
            contract=contract,
            selected_instance_ids=[],
            resume=False,
        )
        if committed:
            raise RuntimeError("V2.42.18 zero-prediction evaluator has rows")
        (root / EVALUATOR_ROOT / "official_eval_results.jsonl").write_text(
            "", encoding="utf-8"
        )
        empty_summary = build_summary([], judge_calls=0)
        empty_summary.update(
            complete=True,
            selected_prediction_count=0,
            terminal_reason="exact_terminal_all220_with_zero_completed_predictions",
        )
        (root / EVALUATOR_ROOT / "summary.json").write_text(
            json.dumps(empty_summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _run_logged(
        [
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / "scripts/finalize_fullset_rollout.py"),
            "summarize",
            "--terminal-outcomes",
            str(root / PREPARE_ROOT / "terminal_outcomes_evaluator_joined.jsonl"),
            "--eval-results",
            str(root / EVALUATOR_ROOT / "official_eval_results.jsonl"),
            "--prepare-attestation",
            str(root / PREPARE_ROOT / "prepare_attestation.json"),
            "--output",
            str(root / SUMMARY),
        ],
        cwd=root,
        log=root / PREPARE_ROOT.parent / "v24218_exact220_summarize.log",
        runner=runner,
    )
    summary = validate_recomputed_summary(root)
    all220 = summary.get("groups", {}).get("all_220") or {}
    if (
        all220.get("selected") != 220
        or all220.get("runtime_completed") != barrier["completed"]
        or all220.get("runtime_failed") != barrier["failed"]
        or all220.get("conservative_all_selected", {}).get("denominator") != 220
        or summary.get("claims", {}).get("sota") is not False
    ):
        raise RuntimeError("V2.42.18 conservative evaluator summary drifted")
    return summary


def validate_recomputed_summary(root: Path = ROOT) -> dict[str, Any]:
    outcomes = root / PREPARE_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
    eval_results = root / EVALUATOR_ROOT / "official_eval_results.jsonl"
    prepare = root / PREPARE_ROOT / "prepare_attestation.json"
    provenance = validate_prepare_attestation(prepare, outcomes)
    expected = summarize_rollout(
        _read_jsonl_exact(outcomes),
        _read_jsonl_exact(eval_results),
        rollout_id=int(provenance["rollout_id"]),
    )
    expected["terminal_outcomes_sha256"] = sha256_file(outcomes)
    expected["eval_results_sha256"] = sha256_file(eval_results)
    expected["evaluator_provenance"] = validate_evaluator_contract(
        root / EVALUATOR_ROOT / "run_config.json",
        expected_predictions_path=root / PREPARE_ROOT / "official_predictions.jsonl",
        expected_predictions_sha256=provenance["official_predictions_sha256"],
        expected_selected_count=provenance["completed_predictions_exported"],
    )
    expected["rollout_provenance"] = provenance
    observed = read_object(root / SUMMARY)
    if observed != expected:
        raise RuntimeError("V2.42.18 evaluator summary differs from live replay")
    return observed


def _evidence_report() -> dict[str, Any]:
    states: list[Mapping[str, Any]] = []
    opened = 0
    missing = 0
    for tag in EXPECTED_SHARDS:
        task_root = _shard_paths(tag)["out"] / "tasks"
        for opaque_id in read_opaque_ids(_shard_paths(tag)["ids"], EXPECTED_COUNTS[tag]):
            path = task_root / opaque_id / "state.json"
            if path.is_symlink():
                raise RuntimeError("V2.42.18 task state is a symlink")
            if path.is_file():
                state = read_object(path)
                opened += 1
                states.append({"evidence": state.get("evidence")})
            elif path.exists():
                raise RuntimeError("V2.42.18 task state path is noncanonical")
            else:
                missing += 1
                states.append({"evidence": []})
    if len(states) != 220:
        raise RuntimeError("V2.42.18 evidence-width audit lacks exact-220 states")
    value = aggregate_evidence_width(states)
    value.update(
        task_state_files_opened=opened,
        task_state_files_missing_after_terminal_forward=missing,
        missing_state_evidence_width_policy="zero",
    )
    return value


def publish_result(
    package: Mapping[str, Any], capacity: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    target = root / RESULT
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    barrier = validate_forward_barrier(root)
    summary = validate_recomputed_summary(root)
    all220 = summary["groups"]["all_220"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24218_exact220_released_local_result",
        "status": "exact220_single_rollout_local_evaluator_complete_not_avg4_not_sota",
        "label_blind_forward": True,
        "package_mode": package["mode"],
        "package_state": package["package_state"],
        "package_publication": package["publication"],
        "capacity_freeze": capacity["freeze"],
        "execution_start": {
            "path": str(EXECUTION_START),
            "sha256": file_sha256(root / EXECUTION_START),
        },
        "materialization": {
            "path": str(MATERIALIZATION),
            "sha256": file_sha256(root / MATERIALIZATION),
        },
        "forward_barrier": {
            "path": str(FORWARD_BARRIER),
            "sha256": file_sha256(root / FORWARD_BARRIER),
        },
        "evaluator_summary": {
            "path": str(SUMMARY),
            "sha256": file_sha256(root / SUMMARY),
        },
        "schedule": capacity["schedule"],
        "width_accounting": {
            "executor_concurrency": capacity["schedule"]["executor_concurrency"],
            "agent_width": 1,
            "effective_evidence": _evidence_report(),
        },
        "selected": 220,
        "runtime_completed": barrier["completed"],
        "runtime_failed": barrier["failed"],
        "evaluator_valid": all220["evaluator_valid"],
        "evaluator_invalid_or_not_run": all220["evaluator_invalid_or_not_run"],
        "conservative_all_selected": all220["conservative_all_selected"],
        "cost_totals": all220["cost_totals"],
        "all_four_shards_terminal_before_mapping_or_evaluator": True,
        "forward_failure_and_evaluator_error_scored_as_zero": True,
        "resume_or_selective_rerun_used": False,
        "mapping_gold_category_question_type_evaluator_score_used_for_forward_routing": False,
        "avg_at_4": False,
        "leaderboard_submission": False,
        "sota": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    publish_new(target, value)
    return value


def validate_result(
    package: Mapping[str, Any], capacity: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    validate_materialization(package, capacity, root=root)
    value = read_object(root / RESULT)
    barrier = validate_forward_barrier(root)
    summary = read_object(root / SUMMARY)
    all220 = summary.get("groups", {}).get("all_220") or {}
    if (
        value.get("role") != "v24218_exact220_released_local_result"
        or not sealed(value, "result_payload_sha256")
        or value.get("status")
        != "exact220_single_rollout_local_evaluator_complete_not_avg4_not_sota"
        or value.get("package_mode") != package["mode"]
        or value.get("package_state") != package["package_state"]
        or value.get("package_publication") != package["publication"]
        or value.get("capacity_freeze") != capacity["freeze"]
        or value.get("execution_start")
        != {
            "path": str(EXECUTION_START),
            "sha256": file_sha256(root / EXECUTION_START),
        }
        or value.get("materialization", {}).get("sha256")
        != file_sha256(root / MATERIALIZATION)
        or value.get("forward_barrier", {}).get("sha256")
        != file_sha256(root / FORWARD_BARRIER)
        or value.get("evaluator_summary", {}).get("sha256")
        != file_sha256(root / SUMMARY)
        or value.get("schedule") != capacity["schedule"]
        or value.get("selected") != 220
        or value.get("runtime_completed") != barrier["completed"]
        or value.get("runtime_failed") != barrier["failed"]
        or value.get("runtime_completed", -1) + value.get("runtime_failed", -1)
        != 220
        or value.get("evaluator_valid") != all220.get("evaluator_valid")
        or value.get("evaluator_invalid_or_not_run")
        != all220.get("evaluator_invalid_or_not_run")
        or value.get("conservative_all_selected")
        != all220.get("conservative_all_selected")
        or value.get("cost_totals") != all220.get("cost_totals")
        or value.get("all_four_shards_terminal_before_mapping_or_evaluator")
        is not True
        or value.get("forward_failure_and_evaluator_error_scored_as_zero")
        is not True
        or value.get("resume_or_selective_rerun_used") is not False
        or value.get(
            "mapping_gold_category_question_type_evaluator_score_used_for_forward_routing"
        )
        is not False
        or value.get("avg_at_4") is not False
        or value.get("leaderboard_submission") is not False
        or value.get("sota") is not False
    ):
        raise RuntimeError("V2.42.18 released result drifted")
    width = value.get("width_accounting") or {}
    effective = width.get("effective_evidence") or {}
    if (
        width.get("executor_concurrency")
        != capacity["schedule"]["executor_concurrency"]
        or width.get("agent_width") != 1
        or effective.get("task_count") != 220
        or effective.get("post_terminal_task_state_files_opened") is not True
        or effective.get("question_or_prediction_fields_used") is not False
        or effective.get("mapping_gold_category_evaluator_score_read")
        is not False
        or effective.get("evidence_content_or_identifier_emitted") is not False
        or effective.get("task_state_files_opened", -1)
        + effective.get("task_state_files_missing_after_terminal_forward", -1)
        != 220
        or effective.get("missing_state_evidence_width_policy") != "zero"
        or effective != _evidence_report()
    ):
        raise RuntimeError("V2.42.18 width accounting drifted")
    return value


def run_exact220(
    package: Mapping[str, Any],
    capacity: Mapping[str, Any],
    *,
    root: Path = ROOT,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    phase: Callable[[str, Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if _present(root, MATERIALIZATION):
        raise RuntimeError("V2.42.18 execution materialization already exists")
    materialize_exact220(package, capacity, root=root)
    if phase:
        phase("materialized_all_four_fresh_roots", {"materialization_created": True})
    schedule = capacity["schedule"]
    for wave_number, tags in enumerate(schedule["waves"], start=1):
        if phase:
            phase(
                "running_preflight_wave",
                {"wave_number": wave_number, "wave_tags": list(tags)},
            )
        failures: list[BaseException] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(tags), thread_name_prefix=f"v24218-preflight-{wave_number}"
        ) as executor:
            futures = {
                executor.submit(run_preflight_once, tag, runner=runner): tag
                for tag in tags
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except BaseException as exc:  # preserve crash-only semantics after peers finish
                    failures.append(exc)
        if failures:
            raise failures[0]
        if phase:
            phase(
                "running_forward_wave",
                {"wave_number": wave_number, "wave_tags": list(tags)},
            )
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=len(tags), thread_name_prefix=f"v24218-forward-{wave_number}"
        ) as executor:
            futures = {
                executor.submit(run_forward_after_preflight, tag, runner=runner): tag
                for tag in tags
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except BaseException as exc:
                    failures.append(exc)
        if failures:
            raise failures[0]
    publish_forward_barrier(root)
    if phase:
        phase(
            "all_shards_terminal_mapping_gate_open",
            {"forward_barrier_created": True, "mapping_or_evaluator_opened": True},
        )
    evaluate_after_barrier(root=root, runner=runner)
    if phase:
        phase("released_evaluator_terminal", {"official_evaluator_called": True})
    return publish_result(package, capacity, root=root)


__all__ = [
    "CAPACITY_FREEZE",
    "CAPACITY_REPORT",
    "CAPACITY_STATE",
    "EVALUATOR_ROOT",
    "EXECUTION_START",
    "FORWARD_BARRIER",
    "MATERIALIZATION",
    "PREPARE_ROOT",
    "RESULT",
    "SHARD_ROOTS",
    "SUMMARY",
    "evaluate_after_barrier",
    "materialize_exact220",
    "publish_forward_barrier",
    "publish_result",
    "run_exact220",
    "run_forward_after_preflight",
    "run_preflight_once",
    "run_shard_once",
    "terminal_shard",
    "validate_capacity_authority",
    "validate_forward_barrier",
    "validate_materialization",
    "validate_package_authority",
    "validate_result",
    "validate_recomputed_summary",
]
