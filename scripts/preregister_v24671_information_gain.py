#!/usr/bin/env python3
"""Publish the design-only V2.46.71 information-gain external protocol."""

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

from deepwide_agent.v24671_ror_external_contract import (  # noqa: E402
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
    TREATMENT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    task_vector,
)


DATE = "20260806"
BUILD_AUDIT = Path(f"results/v24672_external_package_build_audit_v1_{DATE}.json")
POPULATION = Path(f"results/v24670_ror_population_design_v1_{DATE}.json")
DEPENDENCIES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24333_programmatic_support_catalog.py",
    "src/deepwide_agent/v24523_conservative_alias_title_projection.py",
    "src/deepwide_agent/v24529_alias_seeded_target_acquisition.py",
    "src/deepwide_agent/v24547_alias_surface_observability.py",
    "src/deepwide_agent/v24637_objective_alignment_runtime.py",
    "src/deepwide_agent/v24639_ror_objective_runtime.py",
    "src/deepwide_agent/v24644_primary_identity_pair_runtime.py",
    "src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py",
    "src/deepwide_agent/v24659_support_closure_runtime.py",
    "src/deepwide_agent/v24661_support_closure_task_runtime.py",
    "src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py",
    "src/deepwide_agent/v24671_ror_external_contract.py",
    "src/deepwide_agent/v24671_runner_integration.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/run_v24671_ror_task.py",
    "scripts/run_v24671_information_gain.py",
    "scripts/audit_v24671_forward.py",
    "tests/test_v24668_visible_surface_information_gain_runtime.py",
    "tests/test_v24671_forward_package.py",
    str(BUILD_AUDIT),
    str(POPULATION),
)
FORBIDDEN_MARKERS = (
    "evaluation/",
    "external_evaluator",
    "ror_population_private",
    "ror_gold_v1",
    "ror_gold_provenance",
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
        raise RuntimeError("V2.46.71 expected object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.71 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parents() -> tuple[dict[str, Any], dict[str, Any]]:
    build = _read(ROOT / BUILD_AUDIT)
    population = _read(ROOT / POPULATION)
    if (
        build.get("role") != "v24672_external_package_build_audit"
        or build.get("protocol_id") != PROTOCOL_ID
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("authorization", {}).get("external_protocol_publication")
        is not True
        or build.get("authorization", {}).get("preactivation_audit") is not False
        or build.get("authorization", {}).get("activation_or_launch") is not False
        or build.get("authorization", {}).get("evaluator") is not False
        or not _sealed(build, "audit_payload_sha256")
        or population.get("role") != "v24670_ror_population_design"
        or population.get("selected_count") != 48
        or population.get("historical_entity_count") != 4_576
        or population.get("historical_canonical_count") != 4_576
        or population.get("excluded_v24664_entity_count") != 48
        or not _sealed(population, "design_sha256")
    ):
        raise RuntimeError("V2.46.71 protocol parent drifted")
    return build, population


def build_protocol(
    *, now: int | None = None, require_clean=True, require_pristine=True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.46.71 protocol requires clean pushed HEAD")
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
        raise RuntimeError("V2.46.71 future surface not pristine")
    _build, population = _parents()
    if any(
        marker in dependency
        for dependency in DEPENDENCIES
        for marker in FORBIDDEN_MARKERS
    ):
        raise RuntimeError("V2.46.71 dependency includes evaluator surface")
    manifest = {path: sha256(ROOT / path) for path in DEPENDENCIES}
    tasks = task_vector()
    ids = [task["opaque_id"] for task in tasks]
    questions = [task["question"] for task in tasks]
    value = {
        "artifact_version": 1,
        "role": "v24671_information_gain_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "package_build_path": str(BUILD_AUDIT),
            "package_build_sha256": sha256(ROOT / BUILD_AUDIT),
            "population_design_path": str(POPULATION),
            "population_design_sha256": sha256(ROOT / POPULATION),
            "v24664_strict_closure_citation_omission_hypothesis_falsified": True,
        },
        "population": {
            "immutable_ror_commit": population["commit"],
            "immutable_ror_tree": population["directory_tree_sha1"],
            "historical_entity_count": population["historical_entity_count"],
            "historical_canonical_count": population["historical_canonical_count"],
            "excluded_v24664_entity_count": population["excluded_v24664_entity_count"],
            "fresh_entity_count": population["selected_count"],
            "fresh_country_count": population["selected_country_count"],
            "selected_visible_vector_sha256": population[
                "selected_visible_vector_sha256"
            ],
            "selected_record_vector_sha256": population[
                "selected_record_vector_sha256"
            ],
            "literal_and_canonical_overlap_with_history": 0,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_tasks": SELECTED_COUNT,
            "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
            "entities_per_task": 4,
            "selected_ids": ids,
            "selected_ids_sha256": payload_sha256(ids),
            "visible_question_vector_sha256": payload_sha256(questions),
            "private_population_gold_provenance_and_evaluator_absent_from_forward_manifest": True,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
            "one_wave_no_resume_retry_skip_or_selective_rerun": True,
            "failure_as_zero": True,
        },
        "mechanism": {
            "runtime_policy": "v24668_visible_surface_information_gain_acquisition_v1",
            "one_stable_row_major_unknown_target": True,
            "four_targeted_fetches_concentrated_on_one_target": True,
            "source_representative_selected_before_global_budget_cut": True,
            "visible_title_and_normalized_url_path_information_gain_priority": True,
            "query_text_cannot_self_prove_surface_alignment": True,
            "fetched_page_text_is_only_active_support": True,
            "minimum_independent_support_sources": 2,
            "unresolved_and_nonsupporting_declared_ids_preserved": True,
            "proposal_value_changed_by_closure": False,
            "support_threshold_relaxed": False,
            "epistemic_action_credit_can_be_positive": True,
            "positive_decision_credit_before_safe_change_and_postfreeze_outer_utility": False,
            "postfreeze_outer_utility_design_requires_positive_epistemic_credit_and_safe_admission": True,
            "quality_cost_pareto_gate_not_equal_effect_causal_ablation": True,
        },
        "limits": LIMITS,
        "model": MODEL,
        "search": SEARCH,
        "treatment": TREATMENT,
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "single_owner_nonblocking": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read": False,
            "prediction_freeze_before_evaluator_surface_open": True,
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
