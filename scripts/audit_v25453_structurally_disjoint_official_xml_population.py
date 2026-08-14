#!/usr/bin/env python3
"""Outcome-blind consumed-range audit for the V2.54.52 RFC population."""

from __future__ import annotations

import copy
import hashlib
import json
import os
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

from deepwide_agent import v25452_structurally_disjoint_official_xml_population as population  # noqa: E402
from scripts import audit_v25443_structurally_disjoint_key_anchored_population as previous  # noqa: E402


DATE = "20260814"
ROLE = "v25453_structurally_disjoint_official_xml_population_audit"
SOURCE = Path(
    "scripts/audit_v25453_structurally_disjoint_official_xml_population.py"
)
TEST = Path(
    "tests/test_audit_v25453_structurally_disjoint_official_xml_population.py"
)
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25452_structurally_disjoint_official_xml_population.py"
)
POPULATION_TEST = Path(
    "tests/test_v25452_structurally_disjoint_official_xml_population.py"
)
OUTPUT = Path(
    "results/"
    f"v25453_structurally_disjoint_official_xml_population_audit_v1_{DATE}.json"
)
BUILD_AUDIT = Path(
    "results/v25451_official_rfc_xml_shared_build_audit_v1_20260814.json"
)
PREVIOUS_STRUCTURAL_AUDIT = Path(
    "results/v25443_structurally_disjoint_key_anchored_population_audit_v1_20260813.json"
)
BUILD_AUDIT_SHA256 = (
    "289ab2a5f7d3ae36dbdc550ec93a886f646a239d9b8177ab50122db82ce8c745"
)
PREVIOUS_STRUCTURAL_AUDIT_SHA256 = (
    "d1598a88e5452402a21e46e143f63d6693671cc9b3888586bea2a41b2614c53f"
)
CONSUMED_BINDINGS = (
    *previous.CONSUMED_BINDINGS,
    {
        "population": "src/deepwide_agent/v25442_structurally_disjoint_key_anchored_population.py",
        "population_sha256": "eb407c5c6c6ac770c39e705a0ca4ff47eebd92bfc3db03eb69acdce1bb693c3b",
        "forward": "results/v25446_key_anchored_metadata_shared_effect_external_forward_result_v1_20260813.json",
        "forward_sha256": "094d218250c226d2dd5bcfca9db7b0b4ca3323f06aa1af8fd3ad9bfcf22f72ef",
        "expected_role": "v25446_key_anchored_metadata_shared_effect_external_forward_result",
        "expected_task_count": 20,
    },
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    ).stdout


def _blob(relative: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{population.SELECTION_PARENT_COMMIT}:{relative}"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=True,
    )
    return bytes(completed.stdout)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.54.53 expected ordinary repository file")
    return path


def _file_sha256(relative: Path) -> str:
    return _sha256(_ordinary(relative).read_bytes())


def _tracked(relative: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
        == 0
    )


structural_rfc_range = previous.structural_rfc_range


def _terminal_counts(forward: Mapping[str, Any]) -> tuple[int, int]:
    aggregate = forward.get("aggregate")
    if not isinstance(aggregate, Mapping):
        raise ValueError("V2.54.53 forward aggregate is absent")
    task_count = aggregate.get("task_count")
    terminal_tasks = aggregate.get("terminal_tasks")
    if (
        isinstance(task_count, bool)
        or isinstance(terminal_tasks, bool)
        or not isinstance(task_count, int)
        or not isinstance(terminal_tasks, int)
    ):
        raise ValueError("V2.54.53 terminal forward denominator is absent")
    return task_count, terminal_tasks


def consumed_ranges() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for binding in CONSUMED_BINDINGS:
        population_blob = _blob(str(binding["population"]))
        forward_blob = _blob(str(binding["forward"]))
        forward = json.loads(forward_blob)
        if not isinstance(forward, dict):
            raise RuntimeError("V2.54.53 terminal forward shape drifted")
        task_count, terminal_tasks = _terminal_counts(forward)
        expected = int(binding["expected_task_count"])
        if (
            _sha256(population_blob) != binding["population_sha256"]
            or _sha256(forward_blob) != binding["forward_sha256"]
            or forward.get("role") != binding["expected_role"]
            or task_count != expected
            or terminal_tasks != expected
        ):
            raise RuntimeError("V2.54.53 consumed population/forward binding drifted")
        start, end = structural_rfc_range(population_blob)
        output.append(
            {
                "interval": f"RFC {start}-{end}",
                "start": start,
                "end": end,
                "population_path": binding["population"],
                "population_sha256": binding["population_sha256"],
                "forward_path": binding["forward"],
                "forward_sha256": binding["forward_sha256"],
                "forward_role": binding["expected_role"],
                "forward_task_count": task_count,
                "forward_terminal_tasks": terminal_tasks,
                "forward_score_metric_quality_or_per_task_outcome_read": False,
            }
        )
    return output


def _overlap_count(
    interval: tuple[int, int], consumed: Sequence[Mapping[str, Any]]
) -> int:
    start, end = interval
    occupied: set[int] = set()
    for row in consumed:
        occupied.update(range(int(row["start"]), int(row["end"]) + 1))
    return len(set(range(start, end + 1)).intersection(occupied))


def _parent_barriers() -> tuple[dict[str, Any], dict[str, Any]]:
    build_blob = _blob(str(BUILD_AUDIT))
    previous_blob = _blob(str(PREVIOUS_STRUCTURAL_AUDIT))
    if (
        _sha256(build_blob) != BUILD_AUDIT_SHA256
        or _sha256(previous_blob) != PREVIOUS_STRUCTURAL_AUDIT_SHA256
    ):
        raise RuntimeError("V2.54.53 parent audit hash drifted")
    build = json.loads(build_blob)
    prior = json.loads(previous_blob)
    if (
        build.get("role")
        != "v25451_official_rfc_xml_shared_clean_build_audit"
        or build.get("audit_valid") is not True
        or build.get("authorization", {}).get(
            "fresh_structurally_disjoint_population_design"
        )
        is not True
        or build.get("authorization", {}).get("external_forward") is not False
        or build.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or build.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or prior.get("role")
        != "v25443_structurally_disjoint_key_anchored_population_audit"
        or prior.get("audit_valid") is not True
        or prior.get("selected_interval") != "RFC 9080-9159"
        or prior.get("selected_consumed_overlap_identity_count") != 0
        or prior.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
    ):
        raise RuntimeError("V2.54.53 parent barrier drifted")
    return build, prior


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    if require_clean:
        head = _git("rev-parse", "HEAD").strip()
        target = _git("rev-parse", "target/main").strip()
        clean = not _git("status", "--porcelain").strip()
        tracked = all(
            _tracked(path)
            for path in (SOURCE, TEST, POPULATION_SOURCE, POPULATION_TEST)
        )
    else:
        head = target = "build-only"
        clean = tracked = True
    parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT).strip()
    build, prior = _parent_barriers()
    consumed = consumed_ranges()
    candidate = (population.RFC_NUMBERS[0], population.RFC_NUMBERS[-1])
    overlap = _overlap_count(candidate, consumed)
    lower_most_consumed_start = min(int(row["start"]) for row in consumed)
    expected_candidate = (
        lower_most_consumed_start - len(population.RFC_NUMBERS),
        lower_most_consumed_start - 1,
    )
    identities = population.identity_vector()
    groups = population.group_vector()
    tasks = population.task_vector()
    policy = population.source_policy()
    checks = {
        "git_clean_head_equals_target_main": clean and head == target,
        "population_and_audit_sources_tracked": tracked,
        "selection_parent_exact": parent == population.SELECTION_PARENT_COMMIT,
        "v25451_clean_build_audit_bound": bool(build),
        "v25443_previous_structural_audit_bound": bool(prior),
        "ten_consumed_population_terminal_forward_pairs_exact": len(consumed) == 10,
        "all_consumed_ranges_structural_eighty_identity_blocks": all(
            int(row["end"]) - int(row["start"]) + 1 == 80 for row in consumed
        ),
        "all_consumed_forwards_terminal_at_frozen_denominator": all(
            row["forward_task_count"] == row["forward_terminal_tasks"]
            for row in consumed
        ),
        "forward_score_metric_quality_or_per_task_outcome_never_read": all(
            row["forward_score_metric_quality_or_per_task_outcome_read"] is False
            for row in consumed
        ),
        "v25446_population_and_terminal_forward_now_consumed": any(
            row["interval"] == "RFC 9080-9159"
            and row["forward_role"]
            == "v25446_key_anchored_metadata_shared_effect_external_forward_result"
            for row in consumed
        ),
        "candidate_zero_consumed_intersection": overlap == 0,
        "selected_immediately_preceding_whole_block": candidate
        == expected_candidate
        == (9000, 9079),
        "population_vectors_exact": (
            population.payload_sha256(identities)
            == population.EXPECTED_IDENTITY_VECTOR_SHA256
            and population.payload_sha256(groups)
            == population.EXPECTED_GROUP_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "population_selection_is_label_blind_and_outcome_free": (
            policy[
                "candidate_endpoint_page_field_value_prediction_or_evaluator_used_for_selection"
            ]
            is False
            and policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is False
            and policy[
                "individual_identity_or_task_retention_replacement_or_ranking"
            ]
            is False
        ),
        "network_model_search_fetch_evaluator_or_benchmark_called": False,
        "positive_signed_credit_zero": True,
    }
    findings = sorted(
        name
        for name, passed in checks.items()
        if name != "network_model_search_fetch_evaluator_or_benchmark_called"
        and passed is not True
    )
    if checks["network_model_search_fetch_evaluator_or_benchmark_called"] is not False:
        findings.append("network_model_search_fetch_evaluator_or_benchmark_called")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": clean,
        },
        "source_sha256": {
            str(path): _file_sha256(path)
            for path in (SOURCE, TEST, POPULATION_SOURCE, POPULATION_TEST)
        },
        "selection_parent_commit": parent,
        "build_audit_sha256": BUILD_AUDIT_SHA256,
        "previous_structural_audit_sha256": PREVIOUS_STRUCTURAL_AUDIT_SHA256,
        "selection_rule": population.SELECTION_RULE,
        "consumed_bindings": consumed,
        "lower_most_consumed_interval_start": lower_most_consumed_start,
        "selected_interval": "RFC 9000-9079",
        "selected_consumed_overlap_identity_count": overlap,
        "task_count": population.TASK_COUNT,
        "rows_per_task": population.ROWS_PER_TASK,
        "identity_count": len(identities),
        "identity_vector_sha256": population.payload_sha256(identities),
        "group_vector_sha256": population.payload_sha256(groups),
        "task_vector_sha256": population.payload_sha256(tasks),
        "candidate_endpoint_page_field_value_prediction_evaluator_or_per_task_outcome_read_for_selection": False,
        "individual_identity_or_task_retained_replaced_or_ranked": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "official_xml_external_protocol_design": not findings,
            "candidate_page_endpoint_or_field_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "reuse_v25446_population_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    value["audit_payload_sha256"] = population.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    git = copied.get("git")
    source_sha256 = copied.get("source_sha256")
    if (
        copied.get("role") != ROLE
        or not isinstance(git, Mapping)
        or git.get("head") != git.get("target_main")
        or git.get("equal") is not True
        or git.get("clean") is not True
        or not isinstance(source_sha256, Mapping)
        or set(source_sha256)
        != {str(path) for path in (SOURCE, TEST, POPULATION_SOURCE, POPULATION_TEST)}
        or source_sha256
        != {
            str(path): _file_sha256(path)
            for path in (SOURCE, TEST, POPULATION_SOURCE, POPULATION_TEST)
        }
        or copied.get("selection_parent_commit") != population.SELECTION_PARENT_COMMIT
        or copied.get("build_audit_sha256") != BUILD_AUDIT_SHA256
        or copied.get("previous_structural_audit_sha256")
        != PREVIOUS_STRUCTURAL_AUDIT_SHA256
        or copied.get("selection_rule") != "immediately_preceding_whole_block"
        or len(copied.get("consumed_bindings") or []) != 10
        or copied.get("lower_most_consumed_interval_start") != 9080
        or copied.get("selected_interval") != "RFC 9000-9079"
        or copied.get("selected_consumed_overlap_identity_count") != 0
        or copied.get("task_count") != 20
        or copied.get("rows_per_task") != 4
        or copied.get("identity_count") != 80
        or copied.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or copied.get("group_vector_sha256")
        != population.EXPECTED_GROUP_VECTOR_SHA256
        or copied.get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or copied.get(
            "candidate_endpoint_page_field_value_prediction_evaluator_or_per_task_outcome_read_for_selection"
        )
        is not False
        or copied.get("individual_identity_or_task_retained_replaced_or_ranked")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or not isinstance(checks, Mapping)
        or checks.get("network_model_search_fetch_evaluator_or_benchmark_called")
        is not False
        or any(
            passed is not True
            for name, passed in checks.items()
            if name != "network_model_search_fetch_evaluator_or_benchmark_called"
        )
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or copied.get("authorization")
        != {
            "official_xml_external_protocol_design": True,
            "candidate_page_endpoint_or_field_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "reuse_v25446_population_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or seal != population.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.53 structural population audit drifted")
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
    value = build_audit()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "selected": value["selected_interval"],
                "overlap_count": value[
                    "selected_consumed_overlap_identity_count"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
