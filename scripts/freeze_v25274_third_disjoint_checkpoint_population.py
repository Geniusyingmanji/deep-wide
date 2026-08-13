#!/usr/bin/env python3
"""Build-only selector for the third disjoint checkpoint population.

There is intentionally no command-line entrypoint.  A future pushed
execution-start must create and publish the create-exclusive attempt claim
before calling :func:`build_freeze`.  The selector uses only local dpkg source
names and bounded Git literal-history probes; it performs no network, model,
search, fetch, evaluator, or benchmark effect.
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

from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import design_v25273_third_disjoint_checkpoint_population as design  # noqa: E402
from scripts import freeze_v25240_source_package_shadow_population as first  # noqa: E402
from scripts import freeze_v25256_disjoint_observed_reliability_population as second  # noqa: E402


DATE = "20260812"
ROLE = "v25274_third_disjoint_checkpoint_population_freeze"
CLAIM_ROLE = "v25274_third_disjoint_checkpoint_population_attempt_claim"
OUTPUT = Path(f"results/v25274_third_disjoint_checkpoint_population_freeze_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25274_third_disjoint_checkpoint_population_attempt_claim_v1_{DATE}.json")
BUILD_AUDIT = Path(f"results/v25275_third_disjoint_checkpoint_selector_build_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25276_third_disjoint_checkpoint_population_execution_start_v1_{DATE}.json")
SOURCE = Path("scripts/freeze_v25274_third_disjoint_checkpoint_population.py")
TEST = Path("tests/test_freeze_v25274_third_disjoint_checkpoint_population.py")
DESIGN = design.OUTPUT
DESIGN_SHA256 = "5e5672e87bf8fcd6c72e31ef6379aa28f292398c86252ad1a6542b7c33fa905d"
FIRST_POPULATION = design.FIRST_POPULATION
FIRST_POPULATION_SHA256 = design.FIXED_HASHES[FIRST_POPULATION]
SECOND_POPULATION = design.SECOND_POPULATION
SECOND_POPULATION_SHA256 = design.FIXED_HASHES[SECOND_POPULATION]
STRATA = design.STRATA
PACKAGES_BY_STRATUM = design.PACKAGES_BY_STRATUM
TASKS_BY_STRATUM = design.TASKS_BY_STRATUM
PACKAGES_PER_TASK = design.PACKAGES_PER_TASK
PACKAGE_COUNT = design.PACKAGE_COUNT
TASK_COUNT = design.TASK_COUNT
HISTORY_PATHS = design.HISTORY_PATHS
DPKG_ARGUMENT_VECTOR = design.DPKG_ARGUMENT_VECTOR
PACKAGE = first.PACKAGE
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
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    return path


def _design_barrier() -> bool:
    if contract.sha256(_ordinary(DESIGN)) != DESIGN_SHA256:
        return False
    value = design.validate_design(json.loads(_ordinary(DESIGN).read_text(encoding="utf-8")))
    return bool(
        value["authorization"]["selector_implementation_and_build_audit_only"] is True
        and value["authorization"]["formal_dpkg_history_selection_or_task_freeze"] is False
        and value["authorization"]["fresh_external_protocol_or_launch"] is False
        and value["authorization"]["deepwidebench_forward_or_evaluator"] is False
    )


def _prior_entities() -> set[str]:
    first_path = _ordinary(FIRST_POPULATION)
    second_path = _ordinary(SECOND_POPULATION)
    if (
        contract.sha256(first_path) != FIRST_POPULATION_SHA256
        or contract.sha256(second_path) != SECOND_POPULATION_SHA256
    ):
        raise RuntimeError("V2.52.74 prior population hash drifted")
    first_value = first.validate_freeze(json.loads(first_path.read_text(encoding="utf-8")))
    second_value = second.validate_freeze(json.loads(second_path.read_text(encoding="utf-8")))
    first_entities = {
        package
        for task in first_value["population"]["task_vector"]
        for package in first._packages_from_question(task["question"])
    }
    second_entities = {
        package
        for task in second_value["population"]["task_vector"]
        for package in second._packages_from_question(task["question"])
    }
    if len(first_entities) != 256 or len(second_entities) != 128:
        raise RuntimeError("V2.52.74 prior entity denominator drifted")
    if first_entities.intersection(second_entities):
        raise RuntimeError("V2.52.74 prior populations unexpectedly overlap")
    output = first_entities | second_entities
    if len(output) != 384:
        raise RuntimeError("V2.52.74 prior union denominator drifted")
    return output


def _rank(package: str, *, stratum: str, snapshot_sha256: str) -> str:
    if first._stratum(package) != stratum or stratum not in STRATA:
        raise ValueError("V2.52.74 ranking stratum drifted")
    if re.fullmatch(r"[0-9a-f]{64}", str(snapshot_sha256)) is None:
        raise ValueError("V2.52.74 source snapshot hash drifted")
    return hashlib.sha256(
        f"v25273\0{snapshot_sha256}\0{stratum}\0{package}".encode()
    ).hexdigest()


def _select(
    packages: Sequence[str],
    *,
    snapshot_sha256: str,
    parent_commit: str,
    prior_entities: set[str],
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    canonical = sorted(set(map(str, packages)))
    if list(packages) != canonical or len(prior_entities) != 384:
        raise ValueError("V2.52.74 canonical selection input drifted")
    categorized = {
        stratum: sorted(
            package for package in canonical if first._stratum(package) == stratum
        )
        for stratum in STRATA
    }
    # Scan the full canonical source vector exactly once.  This preserves the
    # preregistered 564-candidate aggregate and prevents hidden prefiltering.
    history_hits, probe = first._scan_history(canonical, parent_commit=parent_commit)
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
        disjoint = [package for package in history_zero if package not in prior_entities]
        required = PACKAGES_BY_STRATUM[stratum]
        if len(disjoint) < required:
            raise RuntimeError("V2.52.74 insufficient disjoint history-zero capacity")
        chosen = disjoint[:required]
        if global_seen.intersection(chosen) or prior_entities.intersection(chosen):
            raise RuntimeError("V2.52.74 selected entity collision")
        global_seen.update(chosen)
        selected[stratum] = chosen
        per_stratum[stratum] = {
            "candidate_capacity": len(ranked),
            "history_positive_package_count": sum(
                history_hits[package] > 0 for package in ranked
            ),
            "history_introduction_hit_total": sum(history_hits[package] for package in ranked),
            "history_zero_capacity": len(history_zero),
            "prior_visible_entity_excluded_from_history_zero_count": sum(
                package in prior_entities for package in history_zero
            ),
            "disjoint_history_zero_capacity": len(disjoint),
            "selected_count": len(chosen),
        }
    if len(global_seen) != PACKAGE_COUNT:
        raise RuntimeError("V2.52.74 selected entity denominator drifted")
    return selected, {"probe": probe, "per_stratum": per_stratum}


def _question(packages: Sequence[str]) -> str:
    if (
        isinstance(packages, (str, bytes))
        or len(packages) != 2
        or len(set(packages)) != 2
        or any(PACKAGE.fullmatch(str(package)) is None for package in packages)
    ):
        raise ValueError("V2.52.74 question entity vector drifted")
    first_package, second_package = map(str, packages)
    return (
        "Research these two public Debian source packages in the given order: "
        f"`{first_package}` and `{second_package}`. Return exactly one Markdown "
        "table with one row per package in the same order. Columns exactly: "
        "Package | Latest stable version | License | Short purpose. Use Unknown "
        "for any unavailable cell; do not omit a package."
    )


def _packages_from_question(question: str) -> tuple[str, str]:
    match = QUESTION.fullmatch(str(question))
    if match is None:
        raise ValueError("V2.52.74 visible question grammar drifted")
    return match.group(1), match.group(2)


def _task_vector(selected: Mapping[str, Sequence[str]]) -> list[dict[str, str]]:
    if set(selected) != set(STRATA):
        raise ValueError("V2.52.74 selected stratum set drifted")
    groups: dict[str, list[list[str]]] = {}
    for stratum in STRATA:
        values = list(selected[stratum])
        if len(values) != PACKAGES_BY_STRATUM[stratum]:
            raise ValueError("V2.52.74 selected stratum denominator drifted")
        groups[stratum] = [values[index : index + 2] for index in range(0, len(values), 2)]
    tasks: list[dict[str, str]] = []
    for offset in range(max(TASKS_BY_STRATUM.values())):
        for stratum in STRATA:
            if offset >= TASKS_BY_STRATUM[stratum]:
                continue
            question = _question(groups[stratum][offset])
            opaque_id = "task_" + hashlib.sha256(
                f"v25274\0{len(tasks)}\0{question}".encode()
            ).hexdigest()[:24]
            tasks.append({"opaque_id": opaque_id, "question": question})
    return validate_task_vector(tasks)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.74 task denominator drifted")
    output: list[dict[str, str]] = []
    packages: list[str] = []
    strata_counts = {name: 0 for name in STRATA}
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.52.74 runtime task boundary drifted")
        opaque_id = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque_id, str)
            or OPAQUE_ID.fullmatch(opaque_id) is None
            or not isinstance(question, str)
        ):
            raise ValueError("V2.52.74 visible task field drifted")
        group = _packages_from_question(question)
        derived = {first._stratum(package) for package in group}
        expected_id = "task_" + hashlib.sha256(
            f"v25274\0{index}\0{question}".encode()
        ).hexdigest()[:24]
        if opaque_id != expected_id or question != _question(group) or len(derived) != 1:
            raise ValueError("V2.52.74 visible task seal drifted")
        stratum = next(iter(derived))
        if stratum not in STRATA:
            raise ValueError("V2.52.74 visible task stratum drifted")
        strata_counts[stratum] += 1
        packages.extend(group)
        output.append({"opaque_id": opaque_id, "question": question})
    if (
        len(packages) != PACKAGE_COUNT
        or len(set(packages)) != PACKAGE_COUNT
        or strata_counts != TASKS_BY_STRATUM
        or len({row["opaque_id"] for row in output}) != TASK_COUNT
    ):
        raise ValueError("V2.52.74 task uniqueness or balance drifted")
    return output


def build_attempt_claim(
    *, parent_commit: str, execution_start_sha256: str, now: int | None = None
) -> dict[str, Any]:
    if (
        re.fullmatch(r"[0-9a-f]{40}", str(parent_commit)) is None
        or re.fullmatch(r"[0-9a-f]{64}", str(execution_start_sha256)) is None
    ):
        raise ValueError("V2.52.74 claim authority drifted")
    value: dict[str, Any] = {
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
    value["claim_payload_sha256"] = contract.payload_sha256(value)
    return validate_attempt_claim(value)


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("claim_payload_sha256", None)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "design",
            "execution_start",
            "selection_parent_commit",
            "result_path",
            "attempt_authority_consumed_before_dpkg_or_history_effect",
            "retry_resume_replacement_selective_backfill_or_second_freeze",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or not isinstance(copied.get("execution_start"), Mapping)
        or set(copied["execution_start"]) != {"path", "sha256"}
        or copied["execution_start"].get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(copied["execution_start"].get("sha256")))
        is None
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("selection_parent_commit")))
        is None
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
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.74 attempt claim drifted")
    return copied


def build_freeze(
    *,
    parent_commit: str,
    attempt_claim_sha256: str,
    execution_start_sha256: str,
    now: int | None = None,
) -> dict[str, Any]:
    if not _design_barrier():
        raise RuntimeError("V2.52.74 design barrier failed")
    if any(
        re.fullmatch(r"[0-9a-f]{64}", str(value)) is None
        for value in (attempt_claim_sha256, execution_start_sha256)
    ):
        raise ValueError("V2.52.74 freeze authority hash drifted")
    resolved = first._resolve_parent(parent_commit)
    packages, source_counts = first._read_source_packages()
    snapshot = first._snapshot_sha256(packages)
    prior_entities = _prior_entities()
    selected, history = _select(
        packages,
        snapshot_sha256=snapshot,
        parent_commit=resolved,
        prior_entities=prior_entities,
    )
    tasks = _task_vector(selected)
    selected_packages = [
        package for task in tasks for package in _packages_from_question(task["question"])
    ]
    overlap = prior_entities.intersection(selected_packages)
    if overlap:
        raise RuntimeError("V2.52.74 prior population overlap drifted")
    value: dict[str, Any] = {
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
        "prior_population_exclusion_receipt": {
            "first_population_path": str(FIRST_POPULATION),
            "first_population_sha256": FIRST_POPULATION_SHA256,
            "second_population_path": str(SECOND_POPULATION),
            "second_population_sha256": SECOND_POPULATION_SHA256,
            "prior_visible_entity_count": len(prior_entities),
            "selected_entity_overlap_count": len(overlap),
            "prior_identity_list_or_per_item_hash_persisted": False,
        },
        "history_receipt": {
            "history_paths": list(HISTORY_PATHS),
            "git_log_argument_vectors_only": True,
            "shell": False,
            "probe": history["probe"],
            "per_stratum": history["per_stratum"],
            "history_zero_disjoint_selected_total": len(selected_packages),
            "manual_choice_reorder_cross_stratum_fill_replacement_or_selective_backfill": False,
        },
        "population": {
            "task_count": len(tasks),
            "package_count": len(selected_packages),
            "packages_per_task": PACKAGES_PER_TASK,
            "task_vector": tasks,
            "task_vector_sha256": contract.payload_sha256(tasks),
            "ordered_visible_package_vector_sha256": contract.payload_sha256(
                selected_packages
            ),
            "runtime_keys": ["opaque_id", "question"],
            "hidden_identity_mapping_or_stratum_field_persisted": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "local_population_frozen": True,
            "paired_checkpoint_reliability_protocol_design": True,
            "external_activation_or_launch": False,
            "same_population_retry_resume_rerun_replacement_or_selective_backfill": False,
            "deepwidebench_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["freeze_payload_sha256"] = contract.payload_sha256(value)
    return validate_freeze(value)


def validate_freeze(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("freeze_payload_sha256", None)
    source = copied.get("source_receipt") or {}
    prior = copied.get("prior_population_exclusion_receipt") or {}
    history = copied.get("history_receipt") or {}
    population = copied.get("population") or {}
    authorization = copied.get("authorization") or {}
    try:
        tasks = validate_task_vector(population.get("task_vector"))
    except (TypeError, ValueError):
        tasks = []
    selected = [
        package for task in tasks for package in _packages_from_question(task["question"])
    ]
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "status",
            "created_at_unix",
            "design",
            "execution_start",
            "attempt_claim",
            "selection_parent_commit",
            "source_receipt",
            "prior_population_exclusion_receipt",
            "history_receipt",
            "population",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "freeze_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("status") != "frozen"
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or not isinstance(copied.get("execution_start"), Mapping)
        or set(copied["execution_start"]) != {"path", "sha256"}
        or copied["execution_start"].get("path") != str(EXECUTION_START)
        or not isinstance(copied.get("attempt_claim"), Mapping)
        or set(copied["attempt_claim"]) != {"path", "sha256"}
        or copied["attempt_claim"].get("path") != str(ATTEMPT_CLAIM)
        or any(
            re.fullmatch(r"[0-9a-f]{64}", str(row.get("sha256"))) is None
            for row in (copied["execution_start"], copied["attempt_claim"])
        )
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("selection_parent_commit")))
        is None
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("shell") is not False
        or source.get("returncode_zero") is not True
        or source.get("stderr_empty") is not True
        or source.get("network_or_external_snapshot_endpoint_called") is not False
        or prior
        != {
            "first_population_path": str(FIRST_POPULATION),
            "first_population_sha256": FIRST_POPULATION_SHA256,
            "second_population_path": str(SECOND_POPULATION),
            "second_population_sha256": SECOND_POPULATION_SHA256,
            "prior_visible_entity_count": 384,
            "selected_entity_overlap_count": 0,
            "prior_identity_list_or_per_item_hash_persisted": False,
        }
        or history.get("history_paths") != list(HISTORY_PATHS)
        or history.get("git_log_argument_vectors_only") is not True
        or history.get("shell") is not False
        or not isinstance(history.get("probe"), Mapping)
        or history["probe"].get("all_history_probes_succeeded_within_wall_ceiling")
        is not True
        or history["probe"].get("submitted_count") != source.get("source_counts", {}).get(
            "source_name_disjoint_from_all_installed_binary_names_count"
        )
        or set(history.get("per_stratum") or {}) != set(STRATA)
        or any(
            history["per_stratum"][name].get("selected_count")
            != PACKAGES_BY_STRATUM[name]
            or history["per_stratum"][name].get("disjoint_history_zero_capacity", -1)
            < PACKAGES_BY_STRATUM[name]
            for name in STRATA
        )
        or history.get("history_zero_disjoint_selected_total") != PACKAGE_COUNT
        or history.get(
            "manual_choice_reorder_cross_stratum_fill_replacement_or_selective_backfill"
        )
        is not False
        or population.get("task_count") != TASK_COUNT
        or population.get("package_count") != PACKAGE_COUNT
        or population.get("packages_per_task") != 2
        or population.get("task_vector_sha256") != contract.payload_sha256(tasks)
        or population.get("ordered_visible_package_vector_sha256")
        != contract.payload_sha256(selected)
        or population.get("runtime_keys") != ["opaque_id", "question"]
        or population.get("hidden_identity_mapping_or_stratum_field_persisted") is not False
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
            "paired_checkpoint_reliability_protocol_design": True,
            "external_activation_or_launch": False,
            "same_population_retry_resume_rerun_replacement_or_selective_backfill": False,
            "deepwidebench_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.74 population freeze drifted")
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
    "ATTEMPT_CLAIM",
    "BUILD_AUDIT",
    "CLAIM_ROLE",
    "DESIGN",
    "DESIGN_SHA256",
    "DPKG_ARGUMENT_VECTOR",
    "EXECUTION_START",
    "FIRST_POPULATION",
    "FIRST_POPULATION_SHA256",
    "HISTORY_PATHS",
    "OUTPUT",
    "PACKAGE_COUNT",
    "PACKAGES_BY_STRATUM",
    "PACKAGES_PER_TASK",
    "QUESTION",
    "REQUIRED_COLUMNS",
    "ROLE",
    "SECOND_POPULATION",
    "SECOND_POPULATION_SHA256",
    "SOURCE",
    "STRATA",
    "TASKS_BY_STRATUM",
    "TASK_COUNT",
    "TEST",
    "_design_barrier",
    "_packages_from_question",
    "_prior_entities",
    "_question",
    "_rank",
    "_select",
    "_task_vector",
    "build_attempt_claim",
    "build_freeze",
    "publish_exclusive",
    "validate_attempt_claim",
    "validate_freeze",
    "validate_task_vector",
]
