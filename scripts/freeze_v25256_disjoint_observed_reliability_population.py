#!/usr/bin/env python3
"""Freeze a fresh V2.52.55 observed-reliability population.

Formal execution is gated by a future single-file pushed execution-start.
The attempt claim is create-exclusive and precedes dpkg or history effects.
Only selected identities inside visible questions are persisted; the old
identity set, strata, history outcomes, and per-item hashes are never emitted.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402
from scripts import design_v25255_disjoint_observed_reliability_population as design  # noqa: E402
from scripts import freeze_v25240_source_package_shadow_population as old  # noqa: E402


DATE = "20260812"
ROLE = "v25256_disjoint_observed_reliability_population_freeze"
CLAIM_ROLE = "v25256_disjoint_observed_reliability_population_attempt_claim"
OUTPUT = Path(f"results/v25256_disjoint_observed_reliability_population_freeze_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25256_disjoint_observed_reliability_population_attempt_claim_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25258_disjoint_observed_reliability_population_execution_start_v1_{DATE}.json")
BUILD_AUDIT = Path(f"results/v25257_disjoint_observed_reliability_selector_build_audit_v1_{DATE}.json")
SOURCE = Path("scripts/freeze_v25256_disjoint_observed_reliability_population.py")
TEST = Path("tests/test_freeze_v25256_disjoint_observed_reliability_population.py")
DESIGN = design.OUTPUT
DESIGN_SHA256 = "99b5ce5212d98a751cf586094137de7d2d1bac101cfa5e1b467086384e193ca9"
OLD_POPULATION = design.OLD_POPULATION
OLD_POPULATION_SHA256 = "45604e8e4c1d0670890289f9a165f9539bf7dcd50add3cfac4b62d1e638ddcdf"
STRATA = design.STRATA
PACKAGES_BY_STRATUM = design.PACKAGES_BY_STRATUM
TASKS_BY_STRATUM = design.TASKS_BY_STRATUM
PACKAGES_PER_TASK = design.PACKAGES_PER_TASK
PACKAGE_COUNT = design.PACKAGE_COUNT
TASK_COUNT = design.TASK_COUNT
HISTORY_PATHS = design.HISTORY_PATHS
DPKG_ARGUMENT_VECTOR = design.DPKG_ARGUMENT_VECTOR
PACKAGE = old.PACKAGE
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
QUESTION = re.compile(
    r"\AResearch these two public Debian source packages in the given order: "
    r"`([a-z0-9][a-z0-9+.-]*)` and `([a-z0-9][a-z0-9+.-]*)`\. "
    r"Return exactly one Markdown table with one row per package in the same "
    r"order\. Columns exactly: Package \| Latest stable version \| License \| "
    r"Short purpose\. Use Unknown for any unavailable cell; do not omit a package\.\Z"
)
REQUIRED_COLUMNS = ("Package", "Latest stable version", "License", "Short purpose")


def _ordinary(relative: Path, *, tracked: bool = True) -> Path:
    path = base._ordinary(relative)
    if tracked:
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError("V2.52.56 expected tracked repository file")
    return path


def _design_barrier() -> bool:
    if base.sha256(DESIGN) != DESIGN_SHA256:
        return False
    value = design.validate_design(json.loads(_ordinary(DESIGN).read_text(encoding="utf-8")))
    return bool(
        value["authorization"]["selector_implementation_and_build_audit_only"] is True
        and value["authorization"]["formal_dpkg_history_selection_or_task_freeze"] is False
        and value["authorization"]["fresh_external_protocol_or_launch"] is False
    )


def _old_entities() -> set[str]:
    path = _ordinary(OLD_POPULATION)
    if base.sha256(OLD_POPULATION) != OLD_POPULATION_SHA256:
        raise RuntimeError("V2.52.56 old population hash drifted")
    value = old.validate_freeze(json.loads(path.read_text(encoding="utf-8")))
    output = {
        package
        for task in value["population"]["task_vector"]
        for package in old._packages_from_question(task["question"])
    }
    if len(output) != 256:
        raise RuntimeError("V2.52.56 old visible entity denominator drifted")
    return output


def _rank(package: str, *, stratum: str, snapshot_sha256: str) -> str:
    if old._stratum(package) != stratum or stratum not in STRATA:
        raise ValueError("V2.52.56 ranking stratum drifted")
    if re.fullmatch(r"[0-9a-f]{64}", str(snapshot_sha256)) is None:
        raise ValueError("V2.52.56 snapshot hash drifted")
    return hashlib.sha256(
        f"v25255\0{snapshot_sha256}\0{stratum}\0{package}".encode()
    ).hexdigest()


def _select(
    packages: Sequence[str],
    *,
    snapshot_sha256: str,
    parent_commit: str,
    old_entities: set[str],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    canonical = sorted(set(map(str, packages)))
    if list(packages) != canonical or len(old_entities) != 256:
        raise ValueError("V2.52.56 canonical selection input drifted")
    categorized = {
        stratum: sorted(package for package in canonical if old._stratum(package) == stratum)
        for stratum in STRATA
    }
    admitted = sorted(package for values in categorized.values() for package in values)
    history_hits, probe = old._scan_history(admitted, parent_commit=parent_commit)
    selected: dict[str, list[str]] = {}
    per_stratum: dict[str, dict[str, int]] = {}
    global_seen: set[str] = set()
    for stratum in STRATA:
        ranked = sorted(
            categorized[stratum],
            key=lambda package: (
                _rank(package, stratum=stratum, snapshot_sha256=snapshot_sha256),
                package,
            ),
        )
        history_zero = [package for package in ranked if history_hits[package] == 0]
        disjoint = [package for package in history_zero if package not in old_entities]
        required = PACKAGES_BY_STRATUM[stratum]
        if len(disjoint) < required:
            raise RuntimeError("V2.52.56 insufficient disjoint history-zero capacity")
        chosen = disjoint[:required]
        if global_seen.intersection(chosen) or old_entities.intersection(chosen):
            raise RuntimeError("V2.52.56 selected entity collision")
        global_seen.update(chosen)
        selected[stratum] = chosen
        per_stratum[stratum] = {
            "candidate_capacity": len(ranked),
            "history_positive_package_count": sum(history_hits[package] > 0 for package in ranked),
            "history_introduction_hit_total": sum(history_hits[package] for package in ranked),
            "history_zero_capacity": len(history_zero),
            "old_visible_entity_excluded_from_history_zero_count": sum(package in old_entities for package in history_zero),
            "disjoint_history_zero_capacity": len(disjoint),
            "selected_count": len(chosen),
        }
    if len(global_seen) != PACKAGE_COUNT:
        raise RuntimeError("V2.52.56 selected entity denominator drifted")
    return selected, {"probe": probe, "per_stratum": per_stratum}


def _question(packages: Sequence[str]) -> str:
    if (
        isinstance(packages, (str, bytes))
        or len(packages) != 2
        or len(set(packages)) != 2
        or any(PACKAGE.fullmatch(str(package)) is None for package in packages)
    ):
        raise ValueError("V2.52.56 question entity vector drifted")
    first, second = map(str, packages)
    return (
        "Research these two public Debian source packages in the given order: "
        f"`{first}` and `{second}`. Return exactly one Markdown table with one "
        "row per package in the same order. Columns exactly: Package | Latest "
        "stable version | License | Short purpose. Use Unknown for any unavailable "
        "cell; do not omit a package."
    )


def _packages_from_question(question: str) -> tuple[str, str]:
    match = QUESTION.fullmatch(str(question))
    if match is None:
        raise ValueError("V2.52.56 visible question grammar drifted")
    return match.group(1), match.group(2)


def _task_vector(selected: Mapping[str, Sequence[str]]) -> list[dict[str, str]]:
    if set(selected) != set(STRATA):
        raise ValueError("V2.52.56 selected stratum set drifted")
    groups: dict[str, list[list[str]]] = {}
    for stratum in STRATA:
        values = list(selected[stratum])
        if len(values) != PACKAGES_BY_STRATUM[stratum]:
            raise ValueError("V2.52.56 selected stratum denominator drifted")
        groups[stratum] = [values[index : index + 2] for index in range(0, len(values), 2)]
    tasks: list[dict[str, str]] = []
    for offset in range(max(TASKS_BY_STRATUM.values())):
        for stratum in STRATA:
            if offset >= TASKS_BY_STRATUM[stratum]:
                continue
            question = _question(groups[stratum][offset])
            opaque_id = "task_" + hashlib.sha256(
                f"v25256\0{len(tasks)}\0{question}".encode()
            ).hexdigest()[:24]
            tasks.append({"opaque_id": opaque_id, "question": question})
    return validate_task_vector(tasks)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.56 task denominator drifted")
    output: list[dict[str, str]] = []
    packages: list[str] = []
    strata_counts = {name: 0 for name in STRATA}
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.52.56 runtime task boundary drifted")
        opaque_id = raw.get("opaque_id")
        question = raw.get("question")
        if not isinstance(opaque_id, str) or OPAQUE_ID.fullmatch(opaque_id) is None or not isinstance(question, str):
            raise ValueError("V2.52.56 visible task field drifted")
        group = _packages_from_question(question)
        expected_id = "task_" + hashlib.sha256(
            f"v25256\0{index}\0{question}".encode()
        ).hexdigest()[:24]
        derived = {old._stratum(package) for package in group}
        if opaque_id != expected_id or question != _question(group) or len(derived) != 1:
            raise ValueError("V2.52.56 visible task seal drifted")
        stratum = next(iter(derived))
        if stratum not in STRATA:
            raise ValueError("V2.52.56 visible task shape drifted")
        strata_counts[stratum] += 1
        packages.extend(group)
        output.append({"opaque_id": opaque_id, "question": question})
    if (
        len(packages) != PACKAGE_COUNT
        or len(set(packages)) != PACKAGE_COUNT
        or strata_counts != TASKS_BY_STRATUM
        or len({row["opaque_id"] for row in output}) != TASK_COUNT
    ):
        raise ValueError("V2.52.56 task uniqueness or balance drifted")
    return output


def build_attempt_claim(
    *, parent_commit: str, execution_start_sha256: str, now: int | None = None
) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", str(parent_commit)) is None or re.fullmatch(
        r"[0-9a-f]{64}", str(execution_start_sha256)
    ) is None:
        raise ValueError("V2.52.56 claim authority drifted")
    value = {
        "artifact_version": 1,
        "role": CLAIM_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "design": {"path": str(DESIGN), "sha256": DESIGN_SHA256},
        "execution_start": {"path": str(EXECUTION_START), "sha256": execution_start_sha256},
        "selection_parent_commit": parent_commit,
        "result_path": str(OUTPUT),
        "attempt_authority_consumed_before_dpkg_or_history_effect": True,
        "retry_resume_replacement_selective_backfill_or_second_freeze": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    value["claim_payload_sha256"] = base.payload_sha256(value)
    return validate_attempt_claim(value)


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("claim_payload_sha256", None)
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "design",
            "execution_start", "selection_parent_commit", "result_path",
            "attempt_authority_consumed_before_dpkg_or_history_effect",
            "retry_resume_replacement_selective_backfill_or_second_freeze",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or not isinstance(copied.get("execution_start"), Mapping)
        or set(copied["execution_start"]) != {"path", "sha256"}
        or copied["execution_start"].get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(copied["execution_start"].get("sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("selection_parent_commit"))) is None
        or copied.get("result_path") != str(OUTPUT)
        or copied.get("attempt_authority_consumed_before_dpkg_or_history_effect") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "retry_resume_replacement_selective_backfill_or_second_freeze",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.56 attempt claim drifted")
    return copied


def build_freeze(
    *,
    parent_commit: str,
    attempt_claim_sha256: str,
    execution_start_sha256: str,
    now: int | None = None,
) -> dict[str, Any]:
    if not _design_barrier():
        raise RuntimeError("V2.52.56 design barrier failed")
    if any(
        re.fullmatch(r"[0-9a-f]{64}", str(value)) is None
        for value in (attempt_claim_sha256, execution_start_sha256)
    ):
        raise ValueError("V2.52.56 freeze authority hash drifted")
    resolved = old._resolve_parent(parent_commit)
    packages, source_counts = old._read_source_packages()
    snapshot = old._snapshot_sha256(packages)
    old_entities = _old_entities()
    selected, history = _select(
        packages,
        snapshot_sha256=snapshot,
        parent_commit=resolved,
        old_entities=old_entities,
    )
    tasks = _task_vector(selected)
    selected_packages = [
        package for task in tasks for package in _packages_from_question(task["question"])
    ]
    overlap = old_entities.intersection(selected_packages)
    if overlap:
        raise RuntimeError("V2.52.56 old population overlap drifted")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "status": "frozen",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "design": {"path": str(DESIGN), "sha256": DESIGN_SHA256},
        "execution_start": {"path": str(EXECUTION_START), "sha256": execution_start_sha256},
        "attempt_claim": {"path": str(ATTEMPT_CLAIM), "sha256": attempt_claim_sha256},
        "selection_parent_commit": resolved,
        "source_receipt": {
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "shell": False,
            "returncode_zero": True,
            "stderr_empty": True,
            "canonical_disjoint_source_snapshot_sha256": snapshot,
            "source_counts": source_counts,
            "package_version_description_architecture_or_installed_file_read": False,
            "network_or_external_snapshot_endpoint_called": False,
        },
        "old_population_exclusion_receipt": {
            "old_population_path": str(OLD_POPULATION),
            "old_population_sha256": OLD_POPULATION_SHA256,
            "old_visible_entity_count": len(old_entities),
            "selected_entity_overlap_count": len(overlap),
            "old_identity_list_or_per_item_hash_persisted": False,
        },
        "history_receipt": {
            "history_paths": list(HISTORY_PATHS),
            "git_log_argument_vectors_only": True,
            "shell": False,
            **history,
            "history_zero_disjoint_selected_total": len(selected_packages),
            "manual_choice_reorder_replacement_or_selective_backfill": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "package_count": len(selected_packages),
            "packages_per_task": PACKAGES_PER_TASK,
            "task_vector": tasks,
            "task_vector_sha256": base.payload_sha256(tasks),
            "ordered_visible_package_vector_sha256": base.payload_sha256(selected_packages),
            "opaque_id_vector_sha256": base.payload_sha256([task["opaque_id"] for task in tasks]),
            "question_vector_sha256": base.payload_sha256([task["question"] for task in tasks]),
            "hidden_identity_list_stratum_mapping_or_item_hash_persisted": False,
            "stratum_field_passed_to_runtime": False,
            "runtime_keys_exactly_opaque_id_and_question": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "local_population_frozen": True,
            "observed_reliability_protocol_design": True,
            "external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "same_population_retry_resume_rerun_replacement_or_selective_backfill": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["freeze_payload_sha256"] = base.payload_sha256(value)
    return validate_freeze(value)


def validate_freeze(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("freeze_payload_sha256", None)
    source = copied.get("source_receipt") or {}
    counts = source.get("source_counts") or {}
    exclusion = copied.get("old_population_exclusion_receipt") or {}
    history = copied.get("history_receipt") or {}
    probe = history.get("probe") or {}
    per_stratum = history.get("per_stratum") or {}
    population = copied.get("population") or {}
    authorization = copied.get("authorization") or {}
    expected_source = {
        "argument_vector", "shell", "returncode_zero", "stderr_empty",
        "canonical_disjoint_source_snapshot_sha256", "source_counts",
        "package_version_description_architecture_or_installed_file_read",
        "network_or_external_snapshot_endpoint_called",
    }
    expected_exclusion = {
        "old_population_path", "old_population_sha256", "old_visible_entity_count",
        "selected_entity_overlap_count", "old_identity_list_or_per_item_hash_persisted",
    }
    expected_history = {
        "history_paths", "git_log_argument_vectors_only", "shell", "probe",
        "per_stratum", "history_zero_disjoint_selected_total",
        "manual_choice_reorder_replacement_or_selective_backfill",
    }
    expected_probe = {
        "worker_cap", "per_candidate_timeout_seconds",
        "whole_selection_wall_ceiling_seconds", "submitted_count", "completed_count",
        "coordinator_cancelled_count", "subprocess_timeout_count",
        "subprocess_nonzero_returncode_count", "subprocess_stderr_nonempty_count",
        "subprocess_incomplete_or_exception_count",
        "all_admitted_candidates_checked_exactly_once",
        "all_history_probes_succeeded_within_wall_ceiling",
    }
    expected_population = {
        "task_count", "package_count", "packages_per_task", "task_vector",
        "task_vector_sha256", "ordered_visible_package_vector_sha256",
        "opaque_id_vector_sha256", "question_vector_sha256",
        "hidden_identity_list_stratum_mapping_or_item_hash_persisted",
        "stratum_field_passed_to_runtime", "runtime_keys_exactly_opaque_id_and_question",
    }
    try:
        tasks = validate_task_vector(population.get("task_vector"))
    except (TypeError, ValueError):
        tasks = []
    selected = [package for task in tasks for package in _packages_from_question(task["question"])]
    expected_history_row = {
        "candidate_capacity", "history_positive_package_count",
        "history_introduction_hit_total", "history_zero_capacity",
        "old_visible_entity_excluded_from_history_zero_count",
        "disjoint_history_zero_capacity", "selected_count",
    }
    if (
        set(copied)
        != {
            "artifact_version", "role", "status", "created_at_unix", "design",
            "execution_start", "attempt_claim", "selection_parent_commit",
            "source_receipt", "old_population_exclusion_receipt", "history_receipt",
            "population",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "freeze_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("status") != "frozen"
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or not isinstance(copied.get("execution_start"), Mapping)
        or set(copied["execution_start"]) != {"path", "sha256"}
        or copied["execution_start"].get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(copied["execution_start"].get("sha256"))) is None
        or not isinstance(copied.get("attempt_claim"), Mapping)
        or set(copied["attempt_claim"]) != {"path", "sha256"}
        or copied["attempt_claim"].get("path") != str(ATTEMPT_CLAIM)
        or re.fullmatch(r"[0-9a-f]{64}", str(copied["attempt_claim"].get("sha256"))) is None
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("selection_parent_commit"))) is None
        or set(source) != expected_source
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("shell") is not False
        or source.get("returncode_zero") is not True
        or source.get("stderr_empty") is not True
        or re.fullmatch(r"[0-9a-f]{64}", str(source.get("canonical_disjoint_source_snapshot_sha256"))) is None
        or not isinstance(counts, Mapping)
        or source.get("package_version_description_architecture_or_installed_file_read") is not False
        or source.get("network_or_external_snapshot_endpoint_called") is not False
        or set(exclusion) != expected_exclusion
        or exclusion
        != {
            "old_population_path": str(OLD_POPULATION),
            "old_population_sha256": OLD_POPULATION_SHA256,
            "old_visible_entity_count": 256,
            "selected_entity_overlap_count": 0,
            "old_identity_list_or_per_item_hash_persisted": False,
        }
        or set(history) != expected_history
        or history.get("history_paths") != list(HISTORY_PATHS)
        or history.get("git_log_argument_vectors_only") is not True
        or history.get("shell") is not False
        or not isinstance(probe, Mapping)
        or set(probe) != expected_probe
        or probe.get("submitted_count") != sum(int(counts.get(name, 0)) for name in STRATA)
        or probe.get("completed_count") != probe.get("submitted_count")
        or any(
            probe.get(name) != 0
            for name in (
                "coordinator_cancelled_count", "subprocess_timeout_count",
                "subprocess_nonzero_returncode_count", "subprocess_stderr_nonempty_count",
                "subprocess_incomplete_or_exception_count",
            )
        )
        or probe.get("all_admitted_candidates_checked_exactly_once") is not True
        or probe.get("all_history_probes_succeeded_within_wall_ceiling") is not True
        or set(per_stratum) != set(STRATA)
        or any(
            not isinstance(row, Mapping)
            or set(row) != expected_history_row
            or row.get("candidate_capacity") != counts.get(name)
            or row.get("history_zero_capacity")
            != row.get("disjoint_history_zero_capacity")
            + row.get("old_visible_entity_excluded_from_history_zero_count")
            or row.get("disjoint_history_zero_capacity", -1) < PACKAGES_BY_STRATUM[name]
            or row.get("selected_count") != PACKAGES_BY_STRATUM[name]
            for name, row in per_stratum.items()
        )
        or history.get("history_zero_disjoint_selected_total") != PACKAGE_COUNT
        or history.get("manual_choice_reorder_replacement_or_selective_backfill") is not False
        or set(population) != expected_population
        or len(tasks) != TASK_COUNT
        or population.get("task_count") != TASK_COUNT
        or population.get("package_count") != PACKAGE_COUNT
        or population.get("packages_per_task") != PACKAGES_PER_TASK
        or population.get("task_vector_sha256") != base.payload_sha256(tasks)
        or population.get("ordered_visible_package_vector_sha256") != base.payload_sha256(selected)
        or population.get("opaque_id_vector_sha256") != base.payload_sha256([task["opaque_id"] for task in tasks])
        or population.get("question_vector_sha256") != base.payload_sha256([task["question"] for task in tasks])
        or population.get("hidden_identity_list_stratum_mapping_or_item_hash_persisted") is not False
        or population.get("stratum_field_passed_to_runtime") is not False
        or population.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "network_model_search_fetch_evaluator_benchmark_or_api_called",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "local_population_frozen": True,
            "observed_reliability_protocol_design": True,
            "external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "same_population_retry_resume_rerun_replacement_or_selective_backfill": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.56 population freeze drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


__all__ = [
    "ATTEMPT_CLAIM", "BUILD_AUDIT", "CLAIM_ROLE", "DESIGN", "DESIGN_SHA256",
    "DPKG_ARGUMENT_VECTOR", "EXECUTION_START", "HISTORY_PATHS", "OLD_POPULATION",
    "OLD_POPULATION_SHA256", "OUTPUT", "PACKAGE_COUNT", "PACKAGES_BY_STRATUM",
    "PACKAGES_PER_TASK", "QUESTION", "REQUIRED_COLUMNS", "ROLE", "SOURCE", "STRATA",
    "TASKS_BY_STRATUM", "TASK_COUNT", "TEST", "_design_barrier", "_old_entities",
    "_packages_from_question", "_question", "_rank", "_select", "_task_vector",
    "build_attempt_claim", "build_freeze", "publish_exclusive", "validate_attempt_claim",
    "validate_freeze", "validate_task_vector",
]
