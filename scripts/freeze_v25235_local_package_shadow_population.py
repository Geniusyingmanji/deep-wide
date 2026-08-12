#!/usr/bin/env python3
"""Deterministically freeze a local-package shadow reliability population.

The only environment read is one fixed ``dpkg-query`` argument vector.  The
only repository-history read is a fixed argument-vector ``git log -i -S``
pickaxe over fixed repository-relative paths.  No shell, network, model,
search provider, evaluator, benchmark metadata, credential, package version,
description, architecture, or installed-file list is read.

Selected package names are persisted only as part of the visible questions
that the future runtime will receive.  Morphology is construction-time state
and is not included in any task row or runtime input.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402
from scripts import revise_v25234_local_package_shadow_population_r2 as design  # noqa: E402


DATE = "20260812"
ROLE = "v25235_local_package_shadow_population_freeze"
OUTPUT = Path(f"results/v25235_local_package_shadow_population_freeze_v1_{DATE}.json")
SOURCE = Path("scripts/freeze_v25235_local_package_shadow_population.py")
TEST = Path("tests/test_freeze_v25235_local_package_shadow_population.py")
DESIGN = design.OUTPUT
DESIGN_SHA256 = "5cae2cbf6842f49cd2b33180883dc6898a9dfcb598cfc0a4ed6f50ac01b28b3b"
MORPHOLOGIES = design.parent.MORPHOLOGIES
TASKS_PER_MORPHOLOGY = design.parent.TASKS_PER_MORPHOLOGY
PACKAGES_PER_TASK = design.parent.PACKAGES_PER_TASK
PACKAGES_PER_MORPHOLOGY = design.parent.PACKAGES_PER_MORPHOLOGY
TASK_COUNT = design.parent.TASK_COUNT
HISTORY_PATHS = design.parent.HISTORY_PATHS
DPKG_ARGUMENT_VECTOR = design.parent.DPKG_ARGUMENT_VECTOR
PACKAGE = re.compile(r"[a-z0-9][a-z0-9+.-]*")
COMPACT_ALPHA = re.compile(r"[a-z]{5,12}")
HYPHEN_ALPHA = re.compile(r"[a-z-]{7,36}")
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
QUESTION = re.compile(
    r"\AResearch these four public Debian packages in the given order: "
    r"`([a-z0-9][a-z0-9+.-]*)`, `([a-z0-9][a-z0-9+.-]*)`, "
    r"`([a-z0-9][a-z0-9+.-]*)`, and `([a-z0-9][a-z0-9+.-]*)`\. "
    r"Return exactly one Markdown table with one row per package in the same "
    r"order\. Columns exactly: Package \| Latest stable version \| License \| "
    r"Short purpose\. Use Unknown for any unavailable cell; do not omit a "
    r"package\.\Z"
)
REQUIRED_COLUMNS = (
    "Package",
    "Latest stable version",
    "License",
    "Short purpose",
)


def _ordinary(relative: Path) -> Path:
    return base._ordinary(relative)


def _resolve_parent(parent_commit: str) -> str:
    if not isinstance(parent_commit, str) or not parent_commit:
        raise ValueError("V2.52.35 selection parent is absent")
    return subprocess.run(
        ["git", "rev-parse", "--verify", parent_commit + "^{commit}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _design_barrier() -> bool:
    if base.sha256(DESIGN) != DESIGN_SHA256:
        return False
    raw = json.loads(_ordinary(DESIGN).read_text(encoding="utf-8"))
    checked = design.validate_revision(raw)
    authorization = checked["authorization"]
    return bool(
        checked["role"] == design.ROLE
        and checked["correction"]["corrected_counts"] == design.CORRECTED_COUNTS
        and authorization["local_population_selector_implementation_build_only"]
        is True
        and authorization["formal_dpkg_query_history_scan_or_population_freeze"]
        is False
        and authorization["shadow_external_protocol_or_launch"] is False
    )


def _morphology(package: str) -> str | None:
    value = str(package)
    if PACKAGE.fullmatch(value) is None or len(value) > 36:
        return None
    if COMPACT_ALPHA.fullmatch(value) is not None:
        return "compact_alpha"
    if 4 <= len(value) <= 36 and any(character.isdigit() for character in value):
        return "digit_bearing"
    if HYPHEN_ALPHA.fullmatch(value) is not None:
        hyphens = value.count("-")
        if hyphens == 1:
            return "single_hyphen_alpha"
        if hyphens >= 2:
            return "multi_hyphen_alpha"
    return None


def _parse_dpkg(stdout: str) -> tuple[list[str], dict[str, int]]:
    if not isinstance(stdout, str):
        raise TypeError("V2.52.35 dpkg output must be text")
    installed: set[str] = set()
    excluded = 0
    malformed = 0
    for raw in stdout.splitlines():
        if "\t" not in raw:
            malformed += 1
            continue
        status, package = raw.split("\t", 1)
        if status != "ii ":
            excluded += 1
            continue
        if PACKAGE.fullmatch(package) is None or len(package) > 36:
            excluded += 1
            continue
        installed.add(package)
    ordered = sorted(installed)
    counts = Counter(_morphology(package) or "excluded_other" for package in ordered)
    accounting = {
        "installed_unique_accepted_name_count": len(ordered),
        "malformed_line_count": malformed,
        "noninstalled_or_invalid_name_line_count": excluded,
        **{name: int(counts[name]) for name in MORPHOLOGIES},
        "excluded_other": int(counts["excluded_other"]),
    }
    return ordered, accounting


def _read_installed_packages() -> tuple[list[str], dict[str, int]]:
    completed = subprocess.run(
        list(DPKG_ARGUMENT_VECTOR),
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
        shell=False,
    )
    if completed.returncode != 0 or completed.stderr.strip():
        raise RuntimeError("V2.52.35 fixed dpkg-query failed")
    return _parse_dpkg(completed.stdout)


def _snapshot_sha256(packages: Sequence[str]) -> str:
    if list(packages) != sorted(set(packages)):
        raise ValueError("V2.52.35 canonical package snapshot drifted")
    return base.payload_sha256(list(packages))


def _rank(package: str, *, morphology: str, snapshot_sha256: str) -> str:
    if _morphology(package) != morphology or morphology not in MORPHOLOGIES:
        raise ValueError("V2.52.35 ranking morphology drifted")
    if (
        not isinstance(snapshot_sha256, str)
        or len(snapshot_sha256) != 64
        or any(character not in "0123456789abcdef" for character in snapshot_sha256)
    ):
        raise ValueError("V2.52.35 snapshot hash drifted")
    return hashlib.sha256(
        f"v25234\0{snapshot_sha256}\0{morphology}\0{package}".encode()
    ).hexdigest()


def _history_hits(package: str, *, parent_commit: str) -> int:
    if PACKAGE.fullmatch(package) is None:
        raise ValueError("V2.52.35 history package drifted")
    completed = subprocess.run(
        [
            "git",
            "log",
            parent_commit,
            "-i",
            "-S",
            package,
            "--format=%H",
            "--",
            *HISTORY_PATHS,
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
        shell=False,
    )
    return sum(bool(line.strip()) for line in completed.stdout.splitlines())


def _select(
    packages: Sequence[str],
    *,
    snapshot_sha256: str,
    parent_commit: str,
) -> tuple[dict[str, list[str]], dict[str, dict[str, int]]]:
    categorized = {
        morphology: [
            package for package in packages if _morphology(package) == morphology
        ]
        for morphology in MORPHOLOGIES
    }
    selected: dict[str, list[str]] = {}
    history: dict[str, dict[str, int]] = {}
    global_seen: set[str] = set()
    for morphology in MORPHOLOGIES:
        ranked = sorted(
            categorized[morphology],
            key=lambda package: (
                _rank(
                    package,
                    morphology=morphology,
                    snapshot_sha256=snapshot_sha256,
                ),
                package,
            ),
        )
        chosen: list[str] = []
        scanned = positive = hit_total = 0
        for package in ranked:
            hits = _history_hits(package, parent_commit=parent_commit)
            scanned += 1
            positive += int(hits > 0)
            hit_total += hits
            if hits == 0:
                chosen.append(package)
            if len(chosen) == PACKAGES_PER_MORPHOLOGY:
                break
        if len(chosen) != PACKAGES_PER_MORPHOLOGY:
            raise RuntimeError("V2.52.35 insufficient history-zero package capacity")
        if global_seen.intersection(chosen):
            raise RuntimeError("V2.52.35 cross-morphology package collision")
        global_seen.update(chosen)
        selected[morphology] = chosen
        history[morphology] = {
            "candidate_capacity": len(ranked),
            "scanned_count": scanned,
            "history_positive_package_count": positive,
            "history_introduction_hit_total": hit_total,
            "history_zero_selected_count": len(chosen),
        }
    if len(global_seen) != len(MORPHOLOGIES) * PACKAGES_PER_MORPHOLOGY:
        raise RuntimeError("V2.52.35 selected package denominator drifted")
    return selected, history


def _question(packages: Sequence[str]) -> str:
    if (
        isinstance(packages, (str, bytes))
        or len(packages) != PACKAGES_PER_TASK
        or len(set(packages)) != PACKAGES_PER_TASK
        or any(PACKAGE.fullmatch(str(package)) is None for package in packages)
    ):
        raise ValueError("V2.52.35 question package vector drifted")
    first, second, third, fourth = map(str, packages)
    return (
        "Research these four public Debian packages in the given order: "
        f"`{first}`, `{second}`, `{third}`, and `{fourth}`. "
        "Return exactly one Markdown table with one row per package in the same "
        "order. Columns exactly: Package | Latest stable version | License | "
        "Short purpose. Use Unknown for any unavailable cell; do not omit a "
        "package."
    )


def _task_vector(selected: Mapping[str, Sequence[str]]) -> list[dict[str, str]]:
    if set(selected) != set(MORPHOLOGIES):
        raise ValueError("V2.52.35 selected morphology set drifted")
    tasks: list[dict[str, str]] = []
    for offset in range(TASKS_PER_MORPHOLOGY):
        for morphology in MORPHOLOGIES:
            values = list(selected[morphology])
            start = offset * PACKAGES_PER_TASK
            group = values[start : start + PACKAGES_PER_TASK]
            question = _question(group)
            opaque_id = "task_" + hashlib.sha256(
                f"v25235\0{len(tasks)}\0{question}".encode()
            ).hexdigest()[:24]
            tasks.append({"opaque_id": opaque_id, "question": question})
    return validate_task_vector(tasks)


def _packages_from_question(question: str) -> tuple[str, ...]:
    match = QUESTION.fullmatch(str(question))
    if match is None:
        raise ValueError("V2.52.35 visible question grammar drifted")
    return tuple(match.groups())


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.35 task denominator drifted")
    output: list[dict[str, str]] = []
    packages: list[str] = []
    opaque_ids: list[str] = []
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.52.35 runtime boundary drifted")
        opaque_id = raw.get("opaque_id")
        question = raw.get("question")
        if (
            not isinstance(opaque_id, str)
            or OPAQUE_ID.fullmatch(opaque_id) is None
            or not isinstance(question, str)
        ):
            raise ValueError("V2.52.35 task field drifted")
        group = _packages_from_question(question)
        expected_id = "task_" + hashlib.sha256(
            f"v25235\0{index}\0{question}".encode()
        ).hexdigest()[:24]
        if opaque_id != expected_id or question != _question(group):
            raise ValueError("V2.52.35 task seal drifted")
        morphology = MORPHOLOGIES[index % len(MORPHOLOGIES)]
        if any(_morphology(package) != morphology for package in group):
            raise ValueError("V2.52.35 interleaved morphology drifted")
        packages.extend(group)
        opaque_ids.append(opaque_id)
        output.append({"opaque_id": opaque_id, "question": question})
    if (
        len(packages) != len(MORPHOLOGIES) * PACKAGES_PER_MORPHOLOGY
        or len(set(packages)) != len(packages)
        or len(set(opaque_ids)) != TASK_COUNT
    ):
        raise ValueError("V2.52.35 task uniqueness drifted")
    return output


def build_freeze(
    *,
    parent_commit: str,
    now: int | None = None,
) -> dict[str, Any]:
    if not _design_barrier():
        raise RuntimeError("V2.52.35 design barrier failed")
    resolved = _resolve_parent(parent_commit)
    packages, source_counts = _read_installed_packages()
    snapshot = _snapshot_sha256(packages)
    selected, history = _select(
        packages,
        snapshot_sha256=snapshot,
        parent_commit=resolved,
    )
    tasks = _task_vector(selected)
    selected_packages = [
        package for task in tasks for package in _packages_from_question(task["question"])
    ]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "design": {"path": str(DESIGN), "sha256": DESIGN_SHA256},
        "selection_parent_commit": resolved,
        "source_receipt": {
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "shell": False,
            "returncode_zero": True,
            "stderr_empty": True,
            "canonical_snapshot_sha256": snapshot,
            "canonical_snapshot_package_count": len(packages),
            "source_counts": source_counts,
            "package_version_description_architecture_or_installed_file_read": False,
            "network_or_external_snapshot_endpoint_called": False,
        },
        "history_receipt": {
            "history_paths": list(HISTORY_PATHS),
            "git_log_argument_vectors_only": True,
            "shell": False,
            "per_morphology": history,
            "history_zero_selected_total": sum(
                row["history_zero_selected_count"] for row in history.values()
            ),
            "manual_choice_reorder_replacement_or_selective_backfill": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "package_count": len(selected_packages),
            "packages_per_task": PACKAGES_PER_TASK,
            "task_vector": tasks,
            "task_vector_sha256": base.payload_sha256(tasks),
            "ordered_visible_package_vector_sha256": base.payload_sha256(
                selected_packages
            ),
            "opaque_id_vector_sha256": base.payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "question_vector_sha256": base.payload_sha256(
                [task["question"] for task in tasks]
            ),
            "hidden_identity_list_morphology_mapping_or_item_hash_persisted": False,
            "morphology_field_passed_to_runtime": False,
            "runtime_keys_exactly_opaque_id_and_question": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "local_population_frozen": True,
            "shadow_reliability_protocol_design": True,
            "shadow_external_activation_or_launch": False,
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
    history = copied.get("history_receipt") or {}
    per_morphology = history.get("per_morphology") or {}
    population = copied.get("population") or {}
    tasks = population.get("task_vector")
    authorization = copied.get("authorization") or {}
    try:
        checked_tasks = validate_task_vector(tasks)
    except (TypeError, ValueError):
        checked_tasks = []
    selected_packages = [
        package
        for task in checked_tasks
        for package in _packages_from_question(task["question"])
    ]
    source_count_names = {
        "installed_unique_accepted_name_count",
        "malformed_line_count",
        "noninstalled_or_invalid_name_line_count",
        *MORPHOLOGIES,
        "excluded_other",
    }
    source_counts = source.get("source_counts")
    source_expected = {
        "argument_vector",
        "shell",
        "returncode_zero",
        "stderr_empty",
        "canonical_snapshot_sha256",
        "canonical_snapshot_package_count",
        "source_counts",
        "package_version_description_architecture_or_installed_file_read",
        "network_or_external_snapshot_endpoint_called",
    }
    history_expected = {
        "history_paths",
        "git_log_argument_vectors_only",
        "shell",
        "per_morphology",
        "history_zero_selected_total",
        "manual_choice_reorder_replacement_or_selective_backfill",
    }
    history_row_expected = {
        "candidate_capacity",
        "scanned_count",
        "history_positive_package_count",
        "history_introduction_hit_total",
        "history_zero_selected_count",
    }
    population_expected = {
        "task_count",
        "package_count",
        "packages_per_task",
        "task_vector",
        "task_vector_sha256",
        "ordered_visible_package_vector_sha256",
        "opaque_id_vector_sha256",
        "question_vector_sha256",
        "hidden_identity_list_morphology_mapping_or_item_hash_persisted",
        "morphology_field_passed_to_runtime",
        "runtime_keys_exactly_opaque_id_and_question",
    }
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "design",
            "selection_parent_commit",
            "source_receipt",
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
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or not isinstance(copied.get("selection_parent_commit"), str)
        or len(copied["selection_parent_commit"]) != 40
        or any(
            character not in "0123456789abcdef"
            for character in copied["selection_parent_commit"]
        )
        or set(source) != source_expected
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("shell") is not False
        or source.get("returncode_zero") is not True
        or source.get("stderr_empty") is not True
        or not isinstance(source.get("canonical_snapshot_sha256"), str)
        or len(source["canonical_snapshot_sha256"]) != 64
        or not isinstance(source.get("canonical_snapshot_package_count"), int)
        or source["canonical_snapshot_package_count"] < len(selected_packages)
        or not isinstance(source_counts, Mapping)
        or set(source_counts) != source_count_names
        or any(
            isinstance(source_counts.get(name), bool)
            or not isinstance(source_counts.get(name), int)
            or source_counts[name] < 0
            for name in source_count_names
        )
        or source_counts["installed_unique_accepted_name_count"]
        != sum(source_counts[name] for name in MORPHOLOGIES)
        + source_counts["excluded_other"]
        or source["canonical_snapshot_package_count"]
        != source_counts["installed_unique_accepted_name_count"]
        or source.get("package_version_description_architecture_or_installed_file_read")
        is not False
        or source.get("network_or_external_snapshot_endpoint_called") is not False
        or set(history) != history_expected
        or history.get("history_paths") != list(HISTORY_PATHS)
        or history.get("git_log_argument_vectors_only") is not True
        or history.get("shell") is not False
        or set(per_morphology) != set(MORPHOLOGIES)
        or any(
            not isinstance(row, Mapping)
            or set(row) != history_row_expected
            or any(
                isinstance(row.get(name), bool)
                or not isinstance(row.get(name), int)
                or row[name] < 0
                for name in history_row_expected
            )
            or row.get("candidate_capacity", 0) < PACKAGES_PER_MORPHOLOGY
            or row.get("scanned_count", 0) < PACKAGES_PER_MORPHOLOGY
            or row.get("history_zero_selected_count") != PACKAGES_PER_MORPHOLOGY
            or row["scanned_count"]
            != row["history_positive_package_count"]
            + row["history_zero_selected_count"]
            or row["history_introduction_hit_total"]
            < row["history_positive_package_count"]
            or row["candidate_capacity"] < row["scanned_count"]
            for row in per_morphology.values()
        )
        or history.get("history_zero_selected_total")
        != len(MORPHOLOGIES) * PACKAGES_PER_MORPHOLOGY
        or history.get("manual_choice_reorder_replacement_or_selective_backfill")
        is not False
        or set(population) != population_expected
        or len(checked_tasks) != TASK_COUNT
        or population.get("task_count") != TASK_COUNT
        or population.get("package_count") != len(selected_packages)
        or population.get("package_count")
        != len(MORPHOLOGIES) * PACKAGES_PER_MORPHOLOGY
        or population.get("packages_per_task") != PACKAGES_PER_TASK
        or population.get("task_vector_sha256") != base.payload_sha256(checked_tasks)
        or population.get("ordered_visible_package_vector_sha256")
        != base.payload_sha256(selected_packages)
        or population.get("opaque_id_vector_sha256")
        != base.payload_sha256([task["opaque_id"] for task in checked_tasks])
        or population.get("question_vector_sha256")
        != base.payload_sha256([task["question"] for task in checked_tasks])
        or population.get("hidden_identity_list_morphology_mapping_or_item_hash_persisted")
        is not False
        or population.get("morphology_field_passed_to_runtime") is not False
        or population.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "local_population_frozen": True,
            "shadow_reliability_protocol_design": True,
            "shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "same_population_retry_resume_rerun_replacement_or_selective_backfill": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.35 local package population freeze drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
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
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze",))
    parser.add_argument("--parent", required=True)
    args = parser.parse_args()
    if args.command == "freeze":
        value = build_freeze(parent_commit=args.parent)
        publish_exclusive(ROOT / OUTPUT, value)
        print(
            json.dumps(
                {
                    "path": str(OUTPUT),
                    "task_count": value["population"]["task_count"],
                    "package_count": value["population"]["package_count"],
                    "protocol_design": value["authorization"][
                        "shadow_reliability_protocol_design"
                    ],
                    "external_launch": value["authorization"][
                        "shadow_external_activation_or_launch"
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
