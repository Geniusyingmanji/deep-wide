#!/usr/bin/env python3
"""Freeze a fresh, binary-entity-disjoint Debian source-package population.

The formal entry point writes a create-exclusive attempt claim before reading
the local dpkg database or repository history.  It then checks every admitted
candidate exactly once using bounded concurrent, fixed-argument ``git log``
pickaxes.  Package identities are persisted only inside the visible questions
that a later runtime may receive; no hidden identity map or stratum is stored.
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
from concurrent.futures import Future, ThreadPoolExecutor, wait
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402
from scripts import design_v25239_source_package_shadow_population as design  # noqa: E402


DATE = "20260812"
ROLE = "v25240_source_package_shadow_population_freeze"
CLAIM_ROLE = "v25240_source_package_shadow_population_attempt_claim"
OUTPUT = Path(f"results/v25240_source_package_shadow_population_freeze_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(
    f"results/v25240_source_package_shadow_population_attempt_claim_v1_{DATE}.json"
)
SOURCE = Path("scripts/freeze_v25240_source_package_shadow_population.py")
TEST = Path("tests/test_freeze_v25240_source_package_shadow_population.py")
DESIGN = design.OUTPUT
DESIGN_SHA256 = "0e9001197709453f8ade48a499f51c189887212885f75b107da1b05406fcb6f7"
STRATA = design.STRATA
TASKS_PER_STRATUM = design.TASKS_PER_STRATUM
PACKAGES_PER_TASK = design.PACKAGES_PER_TASK
PACKAGES_PER_STRATUM = design.PACKAGES_PER_STRATUM
TASK_COUNT = design.TASK_COUNT
HISTORY_PATHS = design.HISTORY_PATHS
DPKG_ARGUMENT_VECTOR = design.DPKG_ARGUMENT_VECTOR
HISTORY_WORKERS = 16
HISTORY_TIMEOUT_SECONDS = 30
SELECTION_WALL_CEILING_SECONDS = 240
COORDINATOR_WAIT_SECONDS = SELECTION_WALL_CEILING_SECONDS - HISTORY_TIMEOUT_SECONDS - 5
PACKAGE = re.compile(r"[a-z0-9][a-z0-9+.-]*")
SHORT_ALPHA = re.compile(r"[a-z]{5,8}")
LONG_ALPHA = re.compile(r"[a-z]{9,16}")
SINGLE_HYPHEN_ALPHA = re.compile(r"[a-z]+-[a-z]+")
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
QUESTION = re.compile(
    r"\AResearch these four public Debian source packages in the given order: "
    r"`([a-z0-9][a-z0-9+.-]*)`, `([a-z0-9][a-z0-9+.-]*)`, "
    r"`([a-z0-9][a-z0-9+.-]*)`, and `([a-z0-9][a-z0-9+.-]*)`\. "
    r"Return exactly one Markdown table with one row per package in the same "
    r"order\. Columns exactly: Package \| Latest stable version \| License \| "
    r"Short purpose\. Use Unknown for any unavailable cell; do not omit a "
    r"package\.\Z"
)
REQUIRED_COLUMNS = ("Package", "Latest stable version", "License", "Short purpose")


def _ordinary(relative: Path) -> Path:
    return base._ordinary(relative)


def _resolve_parent(parent_commit: str) -> str:
    if not isinstance(parent_commit, str) or re.fullmatch(r"[0-9a-f]{40}", parent_commit) is None:
        raise ValueError("V2.52.40 selection parent is not a full commit id")
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", parent_commit + "^{commit}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=False,
        shell=False,
    )
    if completed.returncode != 0 or completed.stderr.strip() or completed.stdout.strip() != parent_commit:
        raise RuntimeError("V2.52.40 selection parent resolution failed")
    return parent_commit


def _design_barrier() -> bool:
    if base.sha256(DESIGN) != DESIGN_SHA256:
        return False
    raw = json.loads(_ordinary(DESIGN).read_text(encoding="utf-8"))
    checked = design.validate_design(raw)
    authorization = checked["authorization"]
    return bool(
        checked["role"] == design.ROLE
        and checked["pre_design_capacity_probe"]["counts"] == design.CAPACITY_PROBE
        and authorization["source_package_selector_implementation_build_only"] is True
        and authorization["formal_dpkg_query_history_scan_selection_or_task_freeze"] is False
        and authorization["shadow_external_protocol_or_launch"] is False
    )


def _stratum(package: str) -> str | None:
    value = str(package)
    if PACKAGE.fullmatch(value) is None or not 4 <= len(value) <= 48:
        return None
    if SHORT_ALPHA.fullmatch(value) is not None:
        return "short_alpha"
    if LONG_ALPHA.fullmatch(value) is not None:
        return "long_alpha"
    if SINGLE_HYPHEN_ALPHA.fullmatch(value) is not None:
        return "single_hyphen_alpha"
    if any(character.isdigit() for character in value):
        return "digit_bearing"
    return None


def _parse_dpkg(stdout: str) -> tuple[list[str], dict[str, int]]:
    if not isinstance(stdout, str):
        raise TypeError("V2.52.40 dpkg output must be text")
    binaries: set[str] = set()
    source_values: list[str] = []
    malformed = 0
    noninstalled_or_invalid = 0
    for raw in stdout.splitlines():
        parts = raw.split("\t")
        if len(parts) != 3:
            malformed += 1
            continue
        status, binary, source = parts
        if status != "ii " or PACKAGE.fullmatch(binary) is None or len(binary) > 48:
            noninstalled_or_invalid += 1
            continue
        binaries.add(binary)
        if source and PACKAGE.fullmatch(source) is not None and len(source) <= 48:
            source_values.append(source)
    sources = sorted(set(source_values) - binaries)
    counts = Counter(_stratum(package) or "excluded_other" for package in sources)
    accounting = {
        "installed_binary_unique_count": len(binaries),
        "source_name_disjoint_from_all_installed_binary_names_count": len(sources),
        "malformed_line_count": malformed,
        "noninstalled_or_invalid_binary_line_count": noninstalled_or_invalid,
        **{name: int(counts[name]) for name in STRATA},
        "excluded_other": int(counts["excluded_other"]),
    }
    return sources, accounting


def _read_source_packages() -> tuple[list[str], dict[str, int]]:
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
        raise RuntimeError("V2.52.40 fixed dpkg-query failed")
    return _parse_dpkg(completed.stdout)


def _snapshot_sha256(packages: Sequence[str]) -> str:
    if list(packages) != sorted(set(packages)):
        raise ValueError("V2.52.40 canonical source snapshot drifted")
    return base.payload_sha256(list(packages))


def _rank(package: str, *, stratum: str, snapshot_sha256: str) -> str:
    if _stratum(package) != stratum or stratum not in STRATA:
        raise ValueError("V2.52.40 ranking stratum drifted")
    if re.fullmatch(r"[0-9a-f]{64}", str(snapshot_sha256)) is None:
        raise ValueError("V2.52.40 snapshot hash drifted")
    return hashlib.sha256(
        f"v25239\0{snapshot_sha256}\0{stratum}\0{package}".encode()
    ).hexdigest()


def _history_probe(package: str, *, parent_commit: str) -> dict[str, Any]:
    if PACKAGE.fullmatch(package) is None or re.fullmatch(r"[0-9a-f]{40}", parent_commit) is None:
        raise ValueError("V2.52.40 history probe input drifted")
    try:
        completed = subprocess.run(
            [
                "git", "log", parent_commit, "-i", "-S", package,
                "--format=%H", "--", *HISTORY_PATHS,
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=HISTORY_TIMEOUT_SECONDS,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "hits": 0,
            "completed": False,
            "timed_out": True,
            "returncode_zero": False,
            "stderr_empty": True,
        }
    return {
        "hits": sum(bool(line.strip()) for line in completed.stdout.splitlines())
        if completed.returncode == 0 and not completed.stderr.strip()
        else 0,
        "completed": True,
        "timed_out": False,
        "returncode_zero": completed.returncode == 0,
        "stderr_empty": not completed.stderr.strip(),
    }


def _scan_history(
    packages: Sequence[str], *, parent_commit: str
) -> tuple[dict[str, int], dict[str, Any]]:
    ordered = list(packages)
    if ordered != sorted(set(ordered)) or not ordered:
        raise ValueError("V2.52.40 admitted history vector drifted")
    started = time.monotonic()
    executor = ThreadPoolExecutor(max_workers=HISTORY_WORKERS)
    futures: dict[Future[dict[str, Any]], str] = {
        executor.submit(_history_probe, package, parent_commit=parent_commit): package
        for package in ordered
    }
    done, not_done = wait(futures, timeout=COORDINATOR_WAIT_SECONDS)
    for future in not_done:
        future.cancel()
    executor.shutdown(wait=True, cancel_futures=True)
    rows: dict[str, dict[str, Any]] = {}
    coordinator_cancelled = 0
    for future, package in futures.items():
        if future.cancelled():
            coordinator_cancelled += 1
            continue
        try:
            rows[package] = future.result()
        except BaseException:
            rows[package] = {
                "hits": 0,
                "completed": False,
                "timed_out": False,
                "returncode_zero": False,
                "stderr_empty": True,
            }
    timed_out = sum(row["timed_out"] is True for row in rows.values())
    nonzero = sum(
        row["completed"] is True and row["returncode_zero"] is False
        for row in rows.values()
    )
    stderr_nonempty = sum(row["stderr_empty"] is False for row in rows.values())
    incomplete = sum(row["completed"] is False for row in rows.values())
    all_succeeded = bool(
        len(rows) == len(ordered)
        and coordinator_cancelled == 0
        and timed_out == 0
        and nonzero == 0
        and stderr_nonempty == 0
        and incomplete == 0
        and time.monotonic() - started <= SELECTION_WALL_CEILING_SECONDS
    )
    receipt = {
        "worker_cap": HISTORY_WORKERS,
        "per_candidate_timeout_seconds": HISTORY_TIMEOUT_SECONDS,
        "whole_selection_wall_ceiling_seconds": SELECTION_WALL_CEILING_SECONDS,
        "submitted_count": len(ordered),
        "completed_count": len(rows) - incomplete,
        "coordinator_cancelled_count": coordinator_cancelled,
        "subprocess_timeout_count": timed_out,
        "subprocess_nonzero_returncode_count": nonzero,
        "subprocess_stderr_nonempty_count": stderr_nonempty,
        "subprocess_incomplete_or_exception_count": incomplete,
        "all_admitted_candidates_checked_exactly_once": len(futures) == len(ordered),
        "all_history_probes_succeeded_within_wall_ceiling": all_succeeded,
    }
    if not all_succeeded:
        raise RuntimeError("V2.52.40 bounded history scan failed closed")
    return {package: int(rows[package]["hits"]) for package in ordered}, receipt


def _select(
    packages: Sequence[str], *, snapshot_sha256: str, parent_commit: str
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    categorized = {
        stratum: sorted(package for package in packages if _stratum(package) == stratum)
        for stratum in STRATA
    }
    admitted = sorted(package for values in categorized.values() for package in values)
    history_hits, probe_receipt = _scan_history(admitted, parent_commit=parent_commit)
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
        if len(history_zero) < PACKAGES_PER_STRATUM:
            raise RuntimeError("V2.52.40 insufficient history-zero source capacity")
        chosen = history_zero[:PACKAGES_PER_STRATUM]
        if global_seen.intersection(chosen):
            raise RuntimeError("V2.52.40 cross-stratum source collision")
        global_seen.update(chosen)
        selected[stratum] = chosen
        per_stratum[stratum] = {
            "candidate_capacity": len(ranked),
            "history_positive_package_count": sum(history_hits[package] > 0 for package in ranked),
            "history_introduction_hit_total": sum(history_hits[package] for package in ranked),
            "history_zero_capacity": len(history_zero),
            "selected_count": len(chosen),
        }
    if len(global_seen) != len(STRATA) * PACKAGES_PER_STRATUM:
        raise RuntimeError("V2.52.40 selected source denominator drifted")
    return selected, {"probe": probe_receipt, "per_stratum": per_stratum}


def _question(packages: Sequence[str]) -> str:
    if (
        isinstance(packages, (str, bytes))
        or len(packages) != PACKAGES_PER_TASK
        or len(set(packages)) != PACKAGES_PER_TASK
        or any(PACKAGE.fullmatch(str(package)) is None for package in packages)
    ):
        raise ValueError("V2.52.40 question package vector drifted")
    first, second, third, fourth = map(str, packages)
    return (
        "Research these four public Debian source packages in the given order: "
        f"`{first}`, `{second}`, `{third}`, and `{fourth}`. "
        "Return exactly one Markdown table with one row per package in the same "
        "order. Columns exactly: Package | Latest stable version | License | "
        "Short purpose. Use Unknown for any unavailable cell; do not omit a package."
    )


def _packages_from_question(question: str) -> tuple[str, ...]:
    match = QUESTION.fullmatch(str(question))
    if match is None:
        raise ValueError("V2.52.40 visible question grammar drifted")
    return tuple(match.groups())


def _task_vector(selected: Mapping[str, Sequence[str]]) -> list[dict[str, str]]:
    if set(selected) != set(STRATA):
        raise ValueError("V2.52.40 selected stratum set drifted")
    tasks: list[dict[str, str]] = []
    for offset in range(TASKS_PER_STRATUM):
        for stratum in STRATA:
            start = offset * PACKAGES_PER_TASK
            group = list(selected[stratum])[start : start + PACKAGES_PER_TASK]
            question = _question(group)
            opaque_id = "task_" + hashlib.sha256(
                f"v25240\0{len(tasks)}\0{question}".encode()
            ).hexdigest()[:24]
            tasks.append({"opaque_id": opaque_id, "question": question})
    return validate_task_vector(tasks)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.40 task denominator drifted")
    output: list[dict[str, str]] = []
    packages: list[str] = []
    opaque_ids: list[str] = []
    for index, raw in enumerate(values):
        if not isinstance(raw, Mapping) or set(raw) != {"opaque_id", "question"}:
            raise ValueError("V2.52.40 runtime boundary drifted")
        opaque_id = raw.get("opaque_id")
        question = raw.get("question")
        if not isinstance(opaque_id, str) or OPAQUE_ID.fullmatch(opaque_id) is None or not isinstance(question, str):
            raise ValueError("V2.52.40 task field drifted")
        group = _packages_from_question(question)
        expected_id = "task_" + hashlib.sha256(
            f"v25240\0{index}\0{question}".encode()
        ).hexdigest()[:24]
        if opaque_id != expected_id or question != _question(group):
            raise ValueError("V2.52.40 task seal drifted")
        stratum = STRATA[index % len(STRATA)]
        if any(_stratum(package) != stratum for package in group):
            raise ValueError("V2.52.40 interleaved stratum drifted")
        packages.extend(group)
        opaque_ids.append(opaque_id)
        output.append({"opaque_id": opaque_id, "question": question})
    if len(packages) != len(STRATA) * PACKAGES_PER_STRATUM or len(set(packages)) != len(packages) or len(set(opaque_ids)) != TASK_COUNT:
        raise ValueError("V2.52.40 task uniqueness drifted")
    return output


def build_attempt_claim(*, parent_commit: str, now: int | None = None) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", str(parent_commit)) is None:
        raise ValueError("V2.52.40 claim parent drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CLAIM_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "design": {"path": str(DESIGN), "sha256": DESIGN_SHA256},
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
        set(copied) != {
            "artifact_version", "role", "created_at_unix", "design",
            "selection_parent_commit", "result_path",
            "attempt_authority_consumed_before_dpkg_or_history_effect",
            "retry_resume_replacement_selective_backfill_or_second_freeze",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("selection_parent_commit"))) is None
        or copied.get("result_path") != str(OUTPUT)
        or copied.get("attempt_authority_consumed_before_dpkg_or_history_effect") is not True
        or copied.get("retry_resume_replacement_selective_backfill_or_second_freeze") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.40 attempt claim drifted")
    return copied


def build_freeze(*, parent_commit: str, now: int | None = None) -> dict[str, Any]:
    if not _design_barrier():
        raise RuntimeError("V2.52.40 design barrier failed")
    resolved = _resolve_parent(parent_commit)
    packages, source_counts = _read_source_packages()
    snapshot = _snapshot_sha256(packages)
    selected, history = _select(packages, snapshot_sha256=snapshot, parent_commit=resolved)
    tasks = _task_vector(selected)
    selected_packages = [
        package for task in tasks for package in _packages_from_question(task["question"])
    ]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "status": "frozen",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "design": {"path": str(DESIGN), "sha256": DESIGN_SHA256},
        "attempt_claim": {"path": str(ATTEMPT_CLAIM)},
        "selection_parent_commit": resolved,
        "source_receipt": {
            "argument_vector": list(DPKG_ARGUMENT_VECTOR),
            "shell": False,
            "returncode_zero": True,
            "stderr_empty": True,
            "canonical_disjoint_source_snapshot_sha256": snapshot,
            "source_counts": source_counts,
            "admitted_source_names_disjoint_from_all_installed_binary_names": True,
            "package_version_description_architecture_or_installed_file_read": False,
            "network_or_external_snapshot_endpoint_called": False,
        },
        "history_receipt": {
            "history_paths": list(HISTORY_PATHS),
            "git_log_argument_vectors_only": True,
            "shell": False,
            **history,
            "history_zero_selected_total": len(selected_packages),
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
    counts = source.get("source_counts") or {}
    history = copied.get("history_receipt") or {}
    probe = history.get("probe") or {}
    per_stratum = history.get("per_stratum") or {}
    population = copied.get("population") or {}
    authorization = copied.get("authorization") or {}
    try:
        tasks = validate_task_vector(population.get("task_vector"))
    except (TypeError, ValueError):
        tasks = []
    selected = [package for task in tasks for package in _packages_from_question(task["question"])]
    expected_counts = {
        "installed_binary_unique_count",
        "source_name_disjoint_from_all_installed_binary_names_count",
        "malformed_line_count", "noninstalled_or_invalid_binary_line_count",
        *STRATA, "excluded_other",
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
    expected_history_row = {
        "candidate_capacity", "history_positive_package_count",
        "history_introduction_hit_total", "history_zero_capacity", "selected_count",
    }
    if (
        set(copied) != {
            "artifact_version", "role", "status", "created_at_unix", "design",
            "attempt_claim", "selection_parent_commit", "source_receipt",
            "history_receipt", "population",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "freeze_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("status") != "frozen"
        or copied.get("design") != {"path": str(DESIGN), "sha256": DESIGN_SHA256}
        or copied.get("attempt_claim") != {"path": str(ATTEMPT_CLAIM)}
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("selection_parent_commit"))) is None
        or set(source) != {
            "argument_vector", "shell", "returncode_zero", "stderr_empty",
            "canonical_disjoint_source_snapshot_sha256", "source_counts",
            "admitted_source_names_disjoint_from_all_installed_binary_names",
            "package_version_description_architecture_or_installed_file_read",
            "network_or_external_snapshot_endpoint_called",
        }
        or source.get("argument_vector") != list(DPKG_ARGUMENT_VECTOR)
        or source.get("shell") is not False
        or source.get("returncode_zero") is not True
        or source.get("stderr_empty") is not True
        or re.fullmatch(r"[0-9a-f]{64}", str(source.get("canonical_disjoint_source_snapshot_sha256"))) is None
        or set(counts) != expected_counts
        or any(isinstance(counts.get(name), bool) or not isinstance(counts.get(name), int) or counts[name] < 0 for name in expected_counts)
        or counts.get("source_name_disjoint_from_all_installed_binary_names_count")
        != sum(counts[name] for name in (*STRATA, "excluded_other"))
        or source.get("admitted_source_names_disjoint_from_all_installed_binary_names") is not True
        or source.get("package_version_description_architecture_or_installed_file_read") is not False
        or source.get("network_or_external_snapshot_endpoint_called") is not False
        or set(history) != {
            "history_paths", "git_log_argument_vectors_only", "shell", "probe",
            "per_stratum", "history_zero_selected_total",
            "manual_choice_reorder_replacement_or_selective_backfill",
        }
        or history.get("history_paths") != list(HISTORY_PATHS)
        or history.get("git_log_argument_vectors_only") is not True
        or history.get("shell") is not False
        or set(probe) != expected_probe
        or probe.get("worker_cap") != HISTORY_WORKERS
        or probe.get("per_candidate_timeout_seconds") != HISTORY_TIMEOUT_SECONDS
        or probe.get("whole_selection_wall_ceiling_seconds") != SELECTION_WALL_CEILING_SECONDS
        or probe.get("submitted_count") != sum(counts[name] for name in STRATA)
        or probe.get("completed_count") != probe.get("submitted_count")
        or any(probe.get(name) != 0 for name in (
            "coordinator_cancelled_count", "subprocess_timeout_count",
            "subprocess_nonzero_returncode_count", "subprocess_stderr_nonempty_count",
            "subprocess_incomplete_or_exception_count",
        ))
        or probe.get("all_admitted_candidates_checked_exactly_once") is not True
        or probe.get("all_history_probes_succeeded_within_wall_ceiling") is not True
        or set(per_stratum) != set(STRATA)
        or any(
            not isinstance(row, Mapping)
            or set(row) != expected_history_row
            or row.get("candidate_capacity") != counts[name]
            or row.get("history_positive_package_count", -1) < 0
            or row.get("history_zero_capacity", -1) < PACKAGES_PER_STRATUM
            or row.get("candidate_capacity") != row.get("history_positive_package_count") + row.get("history_zero_capacity")
            or row.get("history_introduction_hit_total", -1) < row.get("history_positive_package_count", 0)
            or row.get("selected_count") != PACKAGES_PER_STRATUM
            for name, row in per_stratum.items()
        )
        or history.get("history_zero_selected_total") != len(STRATA) * PACKAGES_PER_STRATUM
        or history.get("manual_choice_reorder_replacement_or_selective_backfill") is not False
        or set(population) != {
            "task_count", "package_count", "packages_per_task", "task_vector",
            "task_vector_sha256", "ordered_visible_package_vector_sha256",
            "opaque_id_vector_sha256", "question_vector_sha256",
            "hidden_identity_list_stratum_mapping_or_item_hash_persisted",
            "stratum_field_passed_to_runtime", "runtime_keys_exactly_opaque_id_and_question",
        }
        or len(tasks) != TASK_COUNT
        or population.get("task_count") != TASK_COUNT
        or population.get("package_count") != len(selected)
        or population.get("package_count") != len(STRATA) * PACKAGES_PER_STRATUM
        or population.get("packages_per_task") != PACKAGES_PER_TASK
        or population.get("task_vector_sha256") != base.payload_sha256(tasks)
        or population.get("ordered_visible_package_vector_sha256") != base.payload_sha256(selected)
        or population.get("opaque_id_vector_sha256") != base.payload_sha256([task["opaque_id"] for task in tasks])
        or population.get("question_vector_sha256") != base.payload_sha256([task["question"] for task in tasks])
        or population.get("hidden_identity_list_stratum_mapping_or_item_hash_persisted") is not False
        or population.get("stratum_field_passed_to_runtime") is not False
        or population.get("runtime_keys_exactly_opaque_id_and_question") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization != {
            "local_population_frozen": True,
            "shadow_reliability_protocol_design": True,
            "shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "same_population_retry_resume_rerun_replacement_or_selective_backfill": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.40 source package population freeze drifted")
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


def execute(*, parent_commit: str) -> dict[str, Any]:
    if (ROOT / ATTEMPT_CLAIM).exists() or (ROOT / ATTEMPT_CLAIM).is_symlink() or (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError("V2.52.40 attempt or result surface is not pristine")
    claim = build_attempt_claim(parent_commit=parent_commit)
    publish_exclusive(ROOT / ATTEMPT_CLAIM, claim)
    value = build_freeze(parent_commit=parent_commit)
    publish_exclusive(ROOT / OUTPUT, value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze",))
    parser.add_argument("--parent", required=True)
    args = parser.parse_args()
    value = execute(parent_commit=args.parent)
    print(json.dumps({
        "path": str(OUTPUT),
        "task_count": value["population"]["task_count"],
        "package_count": value["population"]["package_count"],
        "protocol_design": value["authorization"]["shadow_reliability_protocol_design"],
        "external_launch": value["authorization"]["shadow_external_activation_or_launch"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
