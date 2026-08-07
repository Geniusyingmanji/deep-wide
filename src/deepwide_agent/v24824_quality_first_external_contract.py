"""Visible-only contract for the V2.48.24 quality-first external gate."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24815_worldbank_successor_contract as parent
from .v24686_worldbank_target_value_runtime import _visible_contract
from .v24819_quality_first_controller import QualityFirstPolicy


DATE = "20260807"
PROTOCOL_ID = "v24824_quality_first_cell_disjoint_external_gate_v1"
BUILD_AUDIT = Path(
    f"results/v24824_quality_first_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v24824_quality_first_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24824_quality_first_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24824_quality_first_external_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24824_quality_first_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v24824_quality_first_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v24824_quality_first_external_forward_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24824_quality_first_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24824_quality_first_external_forward_v1"
LEASE_PURPOSE = "target_cell_disjoint_quality_first_mechanism_gate"
RUNNER_MARKER = "scripts/run_v24824_quality_first_external_forward.py"
CHILD_MARKER = "scripts/run_v24824_quality_first_external_task.py"
SELECTED_COUNT = 32
ARM_COUNT = 3
EXECUTOR_CONCURRENCY = 16
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
PARENT_TIMEOUT_SECONDS = parent.PARENT_TIMEOUT_SECONDS
TASK_WALL_SECONDS = parent.TASK_WALL_SECONDS
CLEANUP_RESERVE_SECONDS = parent.CLEANUP_RESERVE_SECONDS
MINIMUM_ATTEMPT_SECONDS = parent.MINIMUM_ATTEMPT_SECONDS
MODEL_SLOT_POOL_ID = parent.MODEL_SLOT_POOL_ID
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
LIMITS = copy.deepcopy(parent.LIMITS)
TARGETS = (
    {
        "label": "Population ages 0-14 (%)",
        "indicator": "SP.POP.0014.TO.ZS",
        "year": "2023",
    },
    {
        "label": "Population ages 15-64 (%)",
        "indicator": "SP.POP.1564.TO.ZS",
        "year": "2023",
    },
)
QUALITY_FIRST_POLICY = QualityFirstPolicy()
POPULATION_PRIVATE = Path(
    f"evaluation/v24822_cell_disjoint_worldbank_population_private_v1_{DATE}.json"
)
POPULATION_DESIGN = Path(
    f"results/v24822_cell_disjoint_worldbank_population_design_v1_{DATE}.json"
)
POPULATION_AUDIT = Path(
    f"results/v24822_population_publication_audit_v1_{DATE}.json"
)
CONTROLLER_AUDIT = Path(
    f"results/v24819_quality_first_controller_build_audit_v1_{DATE}.json"
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24824_quality_first_external_contract.py"),
    Path("src/deepwide_agent/v24823_quality_first_accounting.py"),
    Path("src/deepwide_agent/v24819_quality_first_controller.py"),
    Path("scripts/run_v24824_quality_first_external_forward.py"),
    Path("scripts/run_v24824_quality_first_external_task.py"),
    Path("src/deepwide_agent/v24804_shared_prefix_budget_ladder.py"),
    Path("src/deepwide_agent/v24696_worldbank_search_transport.py"),
    Path("src/deepwide_agent/v24686_worldbank_target_value_runtime.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24316_deadline_search.py"),
    Path("src/deepwide_agent/v24312_deadline_reliability.py"),
    Path("src/deepwide_agent/v24309_runner_exit_integration.py"),
    Path("src/deepwide_agent/v24325_shared_prefix_revision_runtime.py"),
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24263_global_model_limiter.py"),
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("src/deepwide_agent/v24637_objective_alignment_runtime.py"),
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("src/deepwide_agent/clients.py"),
    Path("scripts/deepwide_api_lease.py"),
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
protected_watcher_snapshot = parent.protected_watcher_snapshot


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def policy_dict() -> dict[str, Any]:
    return dataclasses.asdict(QUALITY_FIRST_POLICY)


def validate_task_vector(
    tasks: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if (
        not isinstance(tasks, Sequence)
        or isinstance(tasks, (str, bytes))
        or len(tasks) != SELECTED_COUNT
    ):
        raise ValueError("V2.48.24 task denominator drifted")
    expected_columns = [
        "Country",
        *(
            f"{target['label']} [{target['indicator']}] @{target['year']}"
            for target in TARGETS
        ),
    ]
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    questions: set[str] = set()
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.48.24 visible task schema drifted")
        opaque = item.get("opaque_id")
        question = item.get("question")
        if (
            not isinstance(opaque, str)
            or not opaque.startswith("task_")
            or len(opaque) != 29
            or opaque in seen
            or not isinstance(question, str)
            or question in questions
        ):
            raise ValueError("V2.48.24 visible task identity drifted")
        visible = _visible_contract(question)
        if len(visible["countries"]) != 4 or visible["columns"] != expected_columns:
            raise ValueError("V2.48.24 visible task contract drifted")
        seen.add(opaque)
        questions.add(question)
        output.append({"opaque_id": opaque, "question": question})
    return output


def dependency_manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in RUNTIME_SOURCES:
        path = root / relative
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode == 0
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.parts[:1] in {("evaluation",), ("outputs",)}
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
            or not tracked
        ):
            raise RuntimeError(f"V2.48.24 runtime source drifted: {relative}")
        output[str(relative)] = sha256(path)
    return dict(sorted(output.items()))


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    tasks = validate_task_vector(copied.get("visible_tasks") or [])
    manifest = dependency_manifest(root)
    execution = copied.get("execution") or {}
    expected_population = {
        "public_design_path": str(POPULATION_DESIGN),
        "public_design_sha256": sha256(root / POPULATION_DESIGN),
        "publication_audit_path": str(POPULATION_AUDIT),
        "publication_audit_sha256": sha256(root / POPULATION_AUDIT),
        "private_population_file_sha256": sha256(root / POPULATION_PRIVATE),
        "selected_tasks": SELECTED_COUNT,
        "selected_entities": 128,
        "selected_gold_cells": 256,
        "selected_target_pair_overlap": 0,
        "selected_gold_cell_overlap": 0,
        "selected_entity_overlap": 119,
        "entity_disjoint_claim": False,
        "target_cell_disjoint_claim": True,
        "private_population_opened_only_by_protocol_builder": True,
        "private_record_or_value_projected_to_visible_tasks": False,
    }
    expected_execution = {
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "model": MODEL,
        "search": SEARCH,
        "limits": LIMITS,
        "quality_first_policy": policy_dict(),
        "three_arms": [
            "first_wave_only",
            "fixed_full_budget",
            "coverage_risk_adaptive",
        ],
        "shared_prefix_hard_barrier": True,
        "prefix_failure_projects_all_arms_to_same_failure": True,
        "mandatory_visible_cell_coverage_precedes_cost_stopping": True,
        "expected_adaptive_decision": "expand",
        "expected_adaptive_decision_count": SELECTED_COUNT,
        "expected_adaptive_prediction_equals_fixed_full_count": SELECTED_COUNT,
        "entropy_information_gain_feature_weight": 0.0,
        "entropy_assigns_signed_credit": False,
        "no_resume_retry_skip_or_selective_rerun": True,
        "protected_watchers": protected_watcher_snapshot(),
    }
    expected_source_policy = {
        "runtime_reads_only_opaque_id_and_question": True,
        "runtime_dependency_manifest_contains_evaluation_path": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "private_population_gold_values_absent_from_protocol": True,
        "country_entity_overlap_disclosed_not_used_for_routing": True,
        "same_task_evaluator_feedback_used_for_forward": False,
        "entropy_or_signed_credit_validated_by_this_run": False,
    }
    expected_authorization = {
        "preactivation_audit_generation": True,
        "activation": False,
        "single_external_forward": False,
        "evaluator": False,
        "public_dev64_or_exact220": False,
    }
    if (
        copied.get("role")
        != "v24824_quality_first_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("build_audit_sha256") != sha256(root / BUILD_AUDIT)
        or copied.get("controller_build_audit_sha256")
        != sha256(root / CONTROLLER_AUDIT)
        or copied.get("population_binding") != expected_population
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("task_contract")
        != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "arm_count": ARM_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        or execution != expected_execution
        or copied.get("source_policy") != expected_source_policy
        or copied.get("authorization") != expected_authorization
    ):
        raise RuntimeError("V2.48.24 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "dependency_manifest",
    "payload_sha256",
    "policy_dict",
    "protected_watcher_snapshot",
    "sha256",
    "validate_protocol",
    "validate_task_vector",
]
