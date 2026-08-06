#!/usr/bin/env python3
"""Publish the inert V2.46.94 World Bank target-value protocol."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24686_worldbank_target_value_runtime import ARMS  # noqa: E402
from deepwide_agent.v24694_worldbank_external_contract import (  # noqa: E402
    ACTIVATION,
    ARM_COUNT,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PARENT_TIMEOUT_SECONDS,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    SEARCH,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    task_vector,
)
from deepwide_agent.v24696_worldbank_forward_contract import TASK_WALL_SECONDS  # noqa: E402
from deepwide_agent.v24696_worldbank_search_transport import HARD_FETCH_DEADLINE_SECONDS  # noqa: E402


DATE = "20260806"
BUILD_AUDIT = Path(f"results/v24696_worldbank_external_package_build_audit_v1_{DATE}.json")
SURFACE_AUDIT = Path(f"results/v24695_worldbank_surface_repair_build_audit_v1_{DATE}.json")
POPULATION = Path(f"results/v24690_worldbank_population_design_v1_{DATE}.json")
DEPENDENCIES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24468_total_wall_transport.py",
    "src/deepwide_agent/v24637_objective_alignment_runtime.py",
    "src/deepwide_agent/v24640_evidence_constrained_runtime.py",
    "src/deepwide_agent/v24644_primary_identity_pair_runtime.py",
    "src/deepwide_agent/v24675_expanded_visible_schema.py",
    "src/deepwide_agent/v24686_worldbank_target_value_runtime.py",
    "src/deepwide_agent/v24694_worldbank_external_contract.py",
    "src/deepwide_agent/v24696_worldbank_forward_contract.py",
    "src/deepwide_agent/v24696_worldbank_search_transport.py",
    "src/deepwide_agent/v24696_worldbank_runner_integration.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/v24468_total_wall_http_helper.py",
    "scripts/run_v24694_worldbank_task.py",
    "scripts/run_v24694_worldbank_forward.py",
    "tests/test_v24686_worldbank_target_value_runtime.py",
    "tests/test_v24696_worldbank_forward_package.py",
    str(BUILD_AUDIT),
    str(SURFACE_AUDIT),
    str(POPULATION),
)
FORBIDDEN_MARKERS = (
    "evaluation/",
    "external_evaluator",
    "worldbank_population_private",
    "worldbank_gold_v1",
    "worldbank_gold_provenance",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.94 expected object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.94 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    build = _read(ROOT / BUILD_AUDIT)
    surface = _read(ROOT / SURFACE_AUDIT)
    population = _read(ROOT / POPULATION)
    if (
        build.get("role") != "v24696_worldbank_external_package_build_audit"
        or build.get("protocol_id") != PROTOCOL_ID
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("authorization", {}).get("external_protocol_publication") is not True
        or build.get("authorization", {}).get("preactivation_audit") is not False
        or build.get("authorization", {}).get("activation_or_launch") is not False
        or not _sealed(build, "audit_payload_sha256")
        or surface.get("role") != "v24695_worldbank_surface_repair_build_audit"
        or surface.get("audit_valid") is not True
        or surface.get("authorization", {}).get("external_protocol_design") is not False
        or surface.get("authorization", {}).get("preactivation_or_launch") is not False
        or not _sealed(surface, "audit_payload_sha256")
        or population.get("role") != "v24690_worldbank_population_design"
        or population.get("task_count") != SELECTED_COUNT
        or population.get("selected_count") != 48
        or population.get("authorization", {}).get("external_protocol_design") is not True
        or population.get("authorization", {}).get("activation_or_launch") is not False
        or population.get("privacy", {}).get("forward_import_or_runtime_read_authorized") is not False
        or not _sealed(population, "design_sha256")
    ):
        raise RuntimeError("V2.46.94 protocol parent drifted")
    return build, surface, population


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.46.94 protocol requires clean pushed HEAD")
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            PROTOCOL,
            PREAUDIT,
            ACTIVATION,
            EXECUTION_START,
            FORWARD_RESULT,
            FORWARD_AUDIT,
            OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.46.94 future surface not pristine")
    _build, _surface, population = _parents()
    if any(marker in dependency for dependency in DEPENDENCIES for marker in FORBIDDEN_MARKERS):
        raise RuntimeError("V2.46.94 dependency includes evaluator surface")
    manifest = {path: sha256(ROOT / path) for path in DEPENDENCIES}
    tasks = task_vector()
    ids = [task["opaque_id"] for task in tasks]
    questions = [task["question"] for task in tasks]
    value = {
        "artifact_version": 1,
        "role": "v24694_worldbank_target_value_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "package_build_path": str(BUILD_AUDIT),
            "package_build_sha256": sha256(ROOT / BUILD_AUDIT),
            "surface_build_path": str(SURFACE_AUDIT),
            "surface_build_sha256": sha256(ROOT / SURFACE_AUDIT),
            "population_design_path": str(POPULATION),
            "population_design_sha256": sha256(ROOT / POPULATION),
        },
        "population": {
            "selected_task_count": SELECTED_COUNT,
            "selected_country_count": population["selected_count"],
            "selected_target_count": population["selected_count"] * 2,
            "selected_region_count": population["selected_region_count"],
            "selected_region_max": population["selected_region_max"],
            "historical_excluded_iso3_count": population["excluded_iso3_count"],
            "selected_visible_vector_sha256": population["selected_visible_vector_sha256"],
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_tasks": SELECTED_COUNT,
            "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
            "selected_ids": ids,
            "selected_ids_sha256": payload_sha256(ids),
            "visible_question_vector_sha256": payload_sha256(questions),
            "private_population_gold_provenance_and_evaluator_absent_from_forward_manifest": True,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "task_wall_seconds": TASK_WALL_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "hard_fetch_deadline_seconds": HARD_FETCH_DEADLINE_SECONDS,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
            "one_wave_no_resume_retry_skip_or_selective_rerun": True,
            "failure_as_zero": True,
        },
        "mechanism": {
            "runtime_policy": "v24686_worldbank_expanded_schema_target_value_v1",
            "arms": list(ARMS),
            "shared_plan_search_generic_fetch_evidence_prefix": True,
            "opaque_id_balanced_synthesis_order": True,
            "target_value_exact_address": "ISO3 x indicator x year",
            "fixed_generic_plus_exact_fetch_cap": [2, 8, 10],
            "missing_exact_official_record_projects_unknown": True,
            "target_value_may_correct_nonunknown": True,
            "decimal_lexeme_preserved": True,
            "entropy_shadow_only": True,
            "positive_task_credit_assigned": False,
            "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
        },
        "limits": LIMITS,
        "model": MODEL,
        "search": SEARCH,
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "single_owner_nonblocking": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "prediction_freeze_before_gold_or_provenance_or_evaluator_open": True,
            "same_run_evaluator_feedback_used_for_forward": False,
        },
        "authorization": {
            "preactivation_audit_generation": False,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_protocol()
    publish(ROOT / PROTOCOL, value)
    print(
        json.dumps(
            {
                "path": str(PROTOCOL),
                "tasks": SELECTED_COUNT,
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )
