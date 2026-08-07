#!/usr/bin/env python3
"""Publish the inert V2.47.61 zero-effect external protocol.

The protocol binds the fresh V2.47.60 visible population to the audited
V2.47.56 runtime.  Publication cannot preaudit, activate, launch, evaluate,
resume, retry, or selectively rerun anything.  The evaluator-only population
is neither opened nor hashed by this module.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24760_zero_effect_external_contract import (  # noqa: E402
    ENTITY_GROUPS,
    QUESTIONS,
    task_vector,
)


DATE = "20260806"
PROTOCOL_ID = "v24761_zero_effect_natural_structured_external_v1"
OUTPUT = Path(f"results/v24761_zero_effect_external_preregistration_v1_{DATE}.json")
BUILD_AUDIT = Path(f"results/v24757_zero_effect_integration_build_audit_v1_{DATE}.json")
CAPACITY_DIAGNOSIS = Path(
    f"results/v24759_v24758_population_capacity_diagnosis_v1_{DATE}.json"
)
POPULATION = Path(f"results/v24760_zero_effect_population_design_v1_{DATE}.json")
FUTURE_SURFACES = (
    Path(f"results/v24761_zero_effect_external_package_audit_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_activation_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_execution_start_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_forward_result_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_forward_audit_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_quality_preregistration_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_quality_result_v1_{DATE}.json"),
    Path(f"results/v24761_zero_effect_external_postresult_audit_v1_{DATE}.json"),
    Path(f"outputs/v24761_zero_effect_external_v1_{DATE}"),
)
DEPENDENCIES = (
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("src/deepwide_agent/v24259_deterministic_table_normalizer.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24286_visible_schema_runtime.py"),
    Path("src/deepwide_agent/v24308_child_exit_observability.py"),
    Path("src/deepwide_agent/v24325_shared_prefix_revision_runtime.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("src/deepwide_agent/v24754_generic_structured_page_adapter.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/v24760_zero_effect_external_contract.py"),
    Path("tests/test_v24743_generic_record_binding.py"),
    Path("tests/test_v24754_generic_structured_page_adapter.py"),
    Path("tests/test_v24756_zero_effect_structured_integration.py"),
    Path("scripts/preregister_v24761_zero_effect_external.py"),
    Path("tests/test_preregister_v24761_zero_effect_external.py"),
    BUILD_AUDIT,
    CAPACITY_DIAGNOSIS,
    POPULATION,
)
FORBIDDEN_DEPENDENCY_MARKERS = (
    "evaluation/",
    "private_population",
    "gold",
    "mapping",
    "external_evaluator",
    "quality_result",
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 10,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "wall_seconds": 180,
    "model_calls": 2,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
TASK_EXECUTORS = 8
MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 195
EXPERIMENT_WALL_CEILING_SECONDS = 210


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.61 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.61 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _tracked_ordinary(relative: Path) -> Path:
    path = ROOT / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked
    ):
        raise RuntimeError(f"V2.47.61 expected tracked dependency: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in DEPENDENCIES:
        text = str(relative).casefold()
        if any(marker in text for marker in FORBIDDEN_DEPENDENCY_MARKERS):
            raise RuntimeError("V2.47.61 evaluator/private dependency entered forward manifest")
        output[str(relative)] = sha256(_tracked_ordinary(relative))
    return output


def _parents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    build = _read(ROOT / BUILD_AUDIT)
    capacity = _read(ROOT / CAPACITY_DIAGNOSIS)
    population = _read(ROOT / POPULATION)
    if (
        build.get("role") != "v24757_zero_effect_integration_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("authorization", {}).get(
            "fresh_external_population_and_protocol_design"
        )
        is not True
        or build.get("authorization", {}).get("external_launch") is not False
        or build.get("authorization", {}).get("exact220") is not False
        or not _sealed(build, "audit_payload_sha256")
        or capacity.get("role")
        != "v24759_v24758_population_capacity_diagnosis"
        or capacity.get("content_free_capacity", {}).get(
            "exact_v24758_failure_reproduced"
        )
        is not True
        or capacity.get("authorization", {}).get("fresh_v24760_population_design")
        is not True
        or capacity.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is not False
        or not _sealed(capacity, "diagnosis_payload_sha256")
        or population.get("role") != "v24760_zero_effect_population_design"
        or population.get("freshness", {}).get("selected_entity_count") != 32
        or population.get("freshness", {}).get("canonical_overlap_with_history")
        != 0
        or population.get("task_shape", {}).get("task_count") != 8
        or population.get("capacity_repair", {}).get(
            "minimum_feasible_country_cap"
        )
        != 11
        or population.get("selection_timing", {}).get(
            "generic_web_search_or_endpoint_reachability_used_for_selection"
        )
        is not False
        or population.get("authorization", {}).get(
            "inert_external_protocol_publication"
        )
        is not True
        or population.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is not False
        or population.get("authorization", {}).get("exact220") is not False
        or not _sealed(population, "design_payload_sha256")
    ):
        raise RuntimeError("V2.47.61 parent chain drifted")
    return build, capacity, population


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        proc = proc_root / str(pid)
        raw = (proc / "stat").read_text(encoding="utf-8")
        ticks = int(raw[raw.rfind(")") + 2 :].split()[19])
        command = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.47.61 protected watcher drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.61 protocol publication requires clean pushed HEAD")
    if require_pristine and (
        (ROOT / OUTPUT).exists()
        or (ROOT / OUTPUT).is_symlink()
        or any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.47.61 protocol/future surface is not pristine")
    build, capacity, population = _parents()
    tasks = task_vector()
    if (
        len(tasks) != 8
        or len(ENTITY_GROUPS) != 8
        or len(QUESTIONS) != 8
        or any(set(task) != {"opaque_id", "question"} for task in tasks)
        or any(len(group) != 4 for group in ENTITY_GROUPS)
        or len({task["opaque_id"] for task in tasks}) != 8
    ):
        raise RuntimeError("V2.47.61 visible task vector drifted")
    manifest = dependency_manifest()
    value = {
        "artifact_version": 1,
        "role": "v24761_zero_effect_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parents": {
            "v24757_integration_build_audit_sha256": sha256(ROOT / BUILD_AUDIT),
            "v24759_capacity_diagnosis_sha256": sha256(ROOT / CAPACITY_DIAGNOSIS),
            "v24760_population_design_sha256": sha256(ROOT / POPULATION),
            "v24757_audit_valid": build.get("audit_valid") is True,
            "v24759_failure_reproduced": capacity.get(
                "content_free_capacity", {}
            ).get("exact_v24758_failure_reproduced")
            is True,
            "v24760_population_fresh": population.get("freshness", {}).get(
                "canonical_overlap_with_history"
            )
            == 0,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "population": {
            "scope": "fresh_education_organization_founded_country_schema_reachability",
            "historical_entity_count": 4_680,
            "fresh_entity_count": 32,
            "task_count": 8,
            "rows_per_task": 4,
            "country_count": population.get("freshness", {}).get(
                "selected_country_count"
            ),
            "country_max": population.get("freshness", {}).get(
                "selected_country_max"
            ),
            "geographically_balanced_quality_sample": False,
            "search_or_quality_outcome_used_for_selection": False,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "task_count": len(tasks),
            "row_count": sum(len(group) for group in ENTITY_GROUPS),
            "columns": ["Organization", "Founded", "Country"],
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
            "private_truth_provenance_or_quality_field_present": False,
        },
        "runtime": {
            "implementation": "v24756_zero_effect_generic_structured_integration_v1",
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "task_executors": TASK_EXECUTORS,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "experiment_wall_ceiling_seconds": EXPERIMENT_WALL_CEILING_SECONDS,
            "single_wave": True,
            "experiment_level_resume_retry_skip_or_selective_rerun": False,
            "provider_internal_retry_policy_fixed_before_outcome": True,
            "all_tasks_submitted_once": True,
            "adapter_replays_only_successfully_fetched_baseline_evidence": True,
            "adapter_additional_model_query_search_fetch_or_token_effect": 0,
        },
        "forward_health_gate": {
            "fixed_task_denominator": 8,
            "terminal_result_or_failure_as_zero_required_per_task": True,
            "all_prediction_pairs_frozen_before_quality_surface_open": True,
            "no_task_level_resume_retry_skip_or_selective_rerun": True,
            "protected_watchers": protected_watcher_snapshot(),
            "required_checks": [
                "eight_of_eight_terminal_ordinals",
                "fixed_denominator_failure_as_zero",
                "exactly_one_submission_per_task",
                "model_query_fetch_effects_within_frozen_caps",
                "adapter_effect_delta_exactly_zero_for_every_task",
                "prediction_freeze_precedes_private_truth_or_quality_read",
                "public_forward_aggregate_is_content_free",
                "experiment_wall_within_210_seconds",
            ],
        },
        "mechanism_gate_before_private_truth": {
            "minimum_changed_task_count": 2,
            "minimum_changed_cell_count": 4,
            "minimum_founded_changed_cell_count": 1,
            "minimum_country_changed_cell_count": 1,
            "minimum_page_with_exact_record_count": 2,
            "ordinary_cell_requires_two_registrably_independent_hosts": True,
            "conflict_or_single_source_abstains": True,
            "only_baseline_unknown_cells_mutable": True,
            "nonunknown_cell_change_count_required": 0,
            "adapter_additional_effect_required": 0,
            "zero_trigger_stops_without_private_truth_or_quality_read": True,
        },
        "quality_gate_after_prediction_freeze": {
            "fixed_task_denominator": 8,
            "failure_as_zero": True,
            "primary_metric": "exact_table_success_count",
            "required_exact_table_success_delta": 1,
            "candidate_cell_accuracy_nonregression": True,
            "candidate_incorrect_cell_count_nonincrease": True,
            "candidate_exact_correct_cell_count_strict_increase": True,
            "candidate_runtime_failure_count_nonincrease": True,
            "candidate_and_baseline_share_identical_forward_prefix": True,
            "selective_revaluation_or_error_rerun": False,
            "go_authorizes_only_visible_reachability_reaudit_and_disjoint_dev64_design": True,
        },
        "entropy_credit_scope": {
            "unknown_reduction_is_positive_credit": False,
            "prediction_change_is_positive_credit": False,
            "entropy_drop_is_positive_credit": False,
            "page_novelty_is_positive_credit": False,
            "credit_assignment_experiment": False,
            "observational_counts_may_be_reported_postfreeze": True,
            "outer_quality_or_intervention_required_before_any_future_credit_claim": True,
        },
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "private_population_truth_provenance_or_quality_file_opened_or_hashed": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "model_search_fetch_or_benchmark_forward_called_by_publication": False,
            "question_entity_url_page_prediction_or_answer_emitted": False,
        },
        "authorization": {
            "protocol_published": True,
            "runner_and_control_plane_build": True,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("dependency_manifest")
    task = copied.get("task_contract", {})
    runtime = copied.get("runtime", {})
    mechanism = copied.get("mechanism_gate_before_private_truth", {})
    quality = copied.get("quality_gate_after_prediction_freeze", {})
    credit = copied.get("entropy_credit_scope", {})
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24761_zero_effect_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(
            marker in path.casefold()
            for path in manifest
            for marker in FORBIDDEN_DEPENDENCY_MARKERS
        )
        or task.get("runtime_input_keys") != ["opaque_id", "question"]
        or task.get("task_count") != 8
        or task.get("row_count") != 32
        or task.get("columns") != ["Organization", "Founded", "Country"]
        or task.get("private_truth_provenance_or_quality_field_present") is not False
        or runtime.get("implementation")
        != "v24756_zero_effect_generic_structured_integration_v1"
        or runtime.get("model") != MODEL
        or runtime.get("search") != SEARCH
        or runtime.get("limits") != LIMITS
        or runtime.get("task_executors") != TASK_EXECUTORS
        or runtime.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or runtime.get("parent_timeout_seconds") != PARENT_TIMEOUT_SECONDS
        or runtime.get("experiment_wall_ceiling_seconds")
        != EXPERIMENT_WALL_CEILING_SECONDS
        or runtime.get("experiment_level_resume_retry_skip_or_selective_rerun")
        is not False
        or runtime.get("adapter_additional_model_query_search_fetch_or_token_effect")
        != 0
        or mechanism
        != {
            "minimum_changed_task_count": 2,
            "minimum_changed_cell_count": 4,
            "minimum_founded_changed_cell_count": 1,
            "minimum_country_changed_cell_count": 1,
            "minimum_page_with_exact_record_count": 2,
            "ordinary_cell_requires_two_registrably_independent_hosts": True,
            "conflict_or_single_source_abstains": True,
            "only_baseline_unknown_cells_mutable": True,
            "nonunknown_cell_change_count_required": 0,
            "adapter_additional_effect_required": 0,
            "zero_trigger_stops_without_private_truth_or_quality_read": True,
        }
        or quality
        != {
            "fixed_task_denominator": 8,
            "failure_as_zero": True,
            "primary_metric": "exact_table_success_count",
            "required_exact_table_success_delta": 1,
            "candidate_cell_accuracy_nonregression": True,
            "candidate_incorrect_cell_count_nonincrease": True,
            "candidate_exact_correct_cell_count_strict_increase": True,
            "candidate_runtime_failure_count_nonincrease": True,
            "candidate_and_baseline_share_identical_forward_prefix": True,
            "selective_revaluation_or_error_rerun": False,
            "go_authorizes_only_visible_reachability_reaudit_and_disjoint_dev64_design": True,
        }
        or credit
        != {
            "unknown_reduction_is_positive_credit": False,
            "prediction_change_is_positive_credit": False,
            "entropy_drop_is_positive_credit": False,
            "page_novelty_is_positive_credit": False,
            "credit_assignment_experiment": False,
            "observational_counts_may_be_reported_postfreeze": True,
            "outer_quality_or_intervention_required_before_any_future_credit_claim": True,
        }
        or any(copied.get("source_policy", {}).values())
        or authorization
        != {
            "protocol_published": True,
            "runner_and_control_plane_build": True,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.61 protocol drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    protocol = build_protocol()
    _publish(ROOT / OUTPUT, protocol)
    print(
        json.dumps(
            {
                "external_launch": protocol["authorization"][
                    "one_external_forward_launch"
                ],
                "output": str(OUTPUT),
                "protocol_id": PROTOCOL_ID,
                "task_count": protocol["task_contract"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
