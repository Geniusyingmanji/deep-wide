"""Visible-only contract for the fresh V2.48.15 external successor."""

from __future__ import annotations

import copy
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24809_worldbank_budget_ladder_smoke_contract as parent
from .v24686_worldbank_target_value_runtime import _visible_contract


DATE = "20260807"
PROTOCOL_ID = "v24815_fresh_worldbank_batched_accounting_smoke_v1"
BUILD_AUDIT = Path(f"results/v24815_worldbank_successor_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24815_worldbank_successor_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24815_worldbank_successor_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24815_worldbank_successor_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24815_worldbank_successor_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24815_worldbank_successor_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24815_worldbank_successor_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24815_worldbank_successor_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24815_worldbank_successor_forward_v1"
LEASE_PURPOSE = "fresh_disjoint_batched_accounting_external_smoke"
RUNNER_MARKER = "scripts/run_v24815_worldbank_successor_forward.py"
CHILD_MARKER = "scripts/run_v24815_worldbank_successor_task.py"
SELECTED_COUNT = 12
ARM_COUNT = parent.ARM_COUNT
EXECUTOR_CONCURRENCY = 12
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
TARGETS = copy.deepcopy(parent.TARGETS)
ADAPTIVE_POLICY = parent.ADAPTIVE_POLICY
POPULATION_PRIVATE = Path(
    f"evaluation/v24814_fresh_worldbank_population_private_v1_{DATE}.json"
)
POPULATION_DESIGN = Path(
    f"results/v24814_fresh_worldbank_population_design_v1_{DATE}.json"
)
ACCOUNTING_AUDIT = Path(
    f"results/v24812_batched_search_accounting_build_audit_v1_{DATE}.json"
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24815_worldbank_successor_contract.py"),
    Path("src/deepwide_agent/v24812_batched_search_accounting.py"),
    Path("scripts/run_v24815_worldbank_successor_forward.py"),
    Path("scripts/run_v24815_worldbank_successor_task.py"),
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
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def validate_task_vector(tasks: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if (
        not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes))
        or len(tasks) != SELECTED_COUNT
    ):
        raise ValueError("V2.48.15 task denominator drifted")
    output = []
    seen = set()
    expected_columns = [
        "Country",
        *(f"{target['label']} [{target['indicator']}] @{target['year']}" for target in TARGETS),
    ]
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.48.15 visible task schema drifted")
        opaque, question = item.get("opaque_id"), item.get("question")
        if (
            not isinstance(opaque, str) or not opaque.startswith("task_")
            or len(opaque) != 29 or opaque in seen or not isinstance(question, str)
        ):
            raise ValueError("V2.48.15 visible task identity drifted")
        visible = _visible_contract(question)
        if len(visible["countries"]) != 4 or visible["columns"] != expected_columns:
            raise ValueError("V2.48.15 visible task contract drifted")
        seen.add(opaque)
        output.append({"opaque_id": opaque, "question": question})
    return output


def dependency_manifest(root: Path) -> dict[str, str]:
    output = {}
    for relative in RUNTIME_SOURCES:
        path = root / relative
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode == 0
        if (
            relative.is_absolute() or ".." in relative.parts
            or relative.parts[:1] in {("evaluation",), ("outputs",)}
            or path.is_symlink() or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve()) or not tracked
        ):
            raise RuntimeError(f"V2.48.15 runtime source drifted: {relative}")
        output[str(relative)] = sha256(path)
    return dict(sorted(output.items()))


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    tasks = validate_task_vector(copied.get("visible_tasks") or [])
    manifest = dependency_manifest(root)
    execution = copied.get("execution") or {}
    if (
        copied.get("role") != "v24815_worldbank_successor_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("build_audit_sha256") != sha256(root / BUILD_AUDIT)
        or copied.get("task_contract") != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "arm_count": ARM_COUNT,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
        }
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL or execution.get("search") != SEARCH
        or execution.get("limits") != LIMITS
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "activation": False, "single_smoke_forward": False,
            "evaluator": False, "public_dev64_or_exact220": False,
        }
    ):
        raise RuntimeError("V2.48.15 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "dependency_manifest", "payload_sha256", "protected_watcher_snapshot",
    "sha256", "validate_protocol", "validate_task_vector",
]
