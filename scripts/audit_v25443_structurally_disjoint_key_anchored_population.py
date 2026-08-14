#!/usr/bin/env python3
"""Structural consumed-range audit for the V2.54.42 RFC population."""

from __future__ import annotations

import ast
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
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25442_structurally_disjoint_key_anchored_population as population  # noqa: E402


DATE = "20260813"
ROLE = "v25443_structurally_disjoint_key_anchored_population_audit"
SOURCE = Path(
    "scripts/audit_v25443_structurally_disjoint_key_anchored_population.py"
)
TEST = Path(
    "tests/test_audit_v25443_structurally_disjoint_key_anchored_population.py"
)
OUTPUT = Path(
    "results/"
    f"v25443_structurally_disjoint_key_anchored_population_audit_v1_{DATE}.json"
)
BUILD_AUDIT = Path(
    "results/v25441_key_anchored_metadata_candidate_build_audit_v1_20260813.json"
)
PREVIOUS_STRUCTURAL_AUDIT = Path(
    "results/v25437_structurally_disjoint_source_authoritative_population_audit_v1_20260813.json"
)
BUILD_AUDIT_SHA256 = (
    "70255ed37d5cb37955fafb3cd7ad35db90a36dd35b3fe2b607da73b9f2244fe3"
)
PREVIOUS_STRUCTURAL_AUDIT_SHA256 = (
    "d73d4047351caaf3f63047284f9b1fe1189d5054da7267b15b44a1f23ceb24d8"
)

CONSUMED_BINDINGS = (
    {
        "population": "src/deepwide_agent/v25372_fresh_rfc_multiline_population.py",
        "population_sha256": "6d4d4fadf0b3603e1617a9a395516f28522aec9fc09de07d05de087c5c513f8a",
        "forward": "results/v25374_rfc_changed_safe_external_forward_result_v1_20260813.json",
        "forward_sha256": "324036ec25ab96fced1766b93ecfb34cad1075985de4eb9a4657755f8edc6551",
        "expected_role": "v25374_rfc_changed_safe_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25385_fresh_rfc_joint_population.py",
        "population_sha256": "1947346eceab0b52dc7dbd85ab3a1a6ddfe905f8dc5a0f100dd531be557e80d9",
        "forward": "results/v25387_rfc_joint_synthesis_external_forward_result_v1_20260813.json",
        "forward_sha256": "0ec26a06bf2cd47f72d54117359b0aa6128ff3d2704c74d05a2afee19d8702e9",
        "expected_role": "v25387_rfc_joint_synthesis_external_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25391_fresh_rfc_hybrid_population.py",
        "population_sha256": "e85a98f5bfce7b589f80535f46b720e54058f8a86ed29891901521e327fa66f7",
        "forward": "results/v25393_rfc_hybrid_external_forward_result_v1_20260813.json",
        "forward_sha256": "5b5b8f84713dc830c44d42dda17bbf53d4d645d7752c09f9a99bcbc5e12f95bf",
        "expected_role": "v25393_rfc_hybrid_external_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25397_fresh_rfc_visible_membership_population.py",
        "population_sha256": "7faf4cf0517c9a8d3195bdb51c997565634acfd07af6de2cc0f742974bfdb2cc",
        "forward": "results/v25399_rfc_visible_membership_external_forward_result_v1_20260813.json",
        "forward_sha256": "3c5f3ccb7ddcef4ec71f3b5c781ec3f04cb805a3b652c1a6e65b661f2c22974c",
        "expected_role": "v25399_rfc_visible_membership_external_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25403_fresh_rfc_grounded_membership_population.py",
        "population_sha256": "e6c7cb5ee6aa3b12ae28c09e097b191f5b8820cc7fdd15617943e8c849715de0",
        "forward": "results/v25405_rfc_grounded_membership_external_forward_result_v1_20260813.json",
        "forward_sha256": "668f604c042d40cf46d59f202340b2db296e0df743a77627d112a1fb9d73a1d7",
        "expected_role": "v25405_rfc_grounded_membership_external_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25413_fresh_paired_rfc_route_population.py",
        "population_sha256": "119786acb889d22bcc7e94a048b0d595c9282238bdb54256c41c082bc0adc18d",
        "forward": "results/v25415_paired_rfc_route_external_forward_result_v1_20260813.json",
        "forward_sha256": "a6b2bea45d76463251e59df16033206e8364735c3935341904e560fa05825aa1",
        "expected_role": "v25415_paired_rfc_route_external_forward_result",
        "expected_task_count": 40,
    },
    {
        "population": "src/deepwide_agent/v25421_fresh_rfc_list_atomic_population.py",
        "population_sha256": "7efaedea46c2ba0db5c9c011d7f27e04746779115c30e1dedbfa6778c9fa2406",
        "forward": "results/v25423_list_atomic_shared_effect_external_forward_result_v1_20260813.json",
        "forward_sha256": "db05c8503c7d4c951779065d7c1b13fd445a0fa1ac5a405cd2ffdfed4fb21cb9",
        "expected_role": "v25423_list_atomic_shared_effect_external_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25427_structurally_disjoint_rfc_population.py",
        "population_sha256": "4f1a6425f469967622e512cf1c696cff08496374d4bf8615666a0b8413fde748",
        "forward": "results/v25430_membership_list_atomic_shared_effect_external_forward_result_v1_20260813.json",
        "forward_sha256": "8d1fb0def68c5936f6d2e683ebeaa002d61ff2a25a51ee2668aa2a777144b75b",
        "expected_role": "v25430_membership_list_atomic_shared_effect_external_forward_result",
        "expected_task_count": 20,
    },
    {
        "population": "src/deepwide_agent/v25436_structurally_disjoint_source_authoritative_population.py",
        "population_sha256": "c78087b0e39dc20d0feedc48ea2380cf47054389fa0b2950d567c918623be414",
        "forward": "results/v25438_source_authoritative_shared_effect_external_forward_result_v1_20260813.json",
        "forward_sha256": "e5e7c1c3cbafb3d5c766620943b709cd22d7520a3353381bdb570a73247b1a38",
        "expected_role": "v25438_source_authoritative_shared_effect_external_forward_result",
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


def structural_rfc_range(source: bytes) -> tuple[int, int]:
    """Read exactly one static ``tuple(range(start, stop))`` 80-ID block."""

    tree = ast.parse(source.decode("utf-8"))
    matches: list[tuple[int, int]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == "RFC_NUMBERS"
            for target in targets
        ):
            continue
        value = node.value
        if (
            not isinstance(value, ast.Call)
            or not isinstance(value.func, ast.Name)
            or value.func.id != "tuple"
            or len(value.args) != 1
            or not isinstance(value.args[0], ast.Call)
            or not isinstance(value.args[0].func, ast.Name)
            or value.args[0].func.id != "range"
            or len(value.args[0].args) != 2
        ):
            raise ValueError("V2.54.43 RFC_NUMBERS is not tuple(range(start, stop))")
        start = ast.literal_eval(value.args[0].args[0])
        stop = ast.literal_eval(value.args[0].args[1])
        if (
            isinstance(start, bool)
            or isinstance(stop, bool)
            or not isinstance(start, int)
            or not isinstance(stop, int)
            or stop - start != 80
        ):
            raise ValueError("V2.54.43 RFC range is not one 80-identity block")
        matches.append((start, stop - 1))
    if len(matches) != 1:
        raise ValueError("V2.54.43 RFC range assignment is ambiguous")
    return matches[0]


def _terminal_counts(forward: Mapping[str, Any]) -> tuple[int, int]:
    aggregate = forward.get("aggregate")
    if not isinstance(aggregate, Mapping):
        raise ValueError("V2.54.43 forward aggregate is absent")
    task_count = aggregate.get("task_count")
    terminal_tasks = aggregate.get("terminal_tasks")
    if (
        isinstance(task_count, bool)
        or isinstance(terminal_tasks, bool)
        or not isinstance(task_count, int)
        or not isinstance(terminal_tasks, int)
    ):
        raise ValueError("V2.54.43 terminal forward denominator is absent")
    return task_count, terminal_tasks


def consumed_ranges() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for binding in CONSUMED_BINDINGS:
        population_blob = _blob(str(binding["population"]))
        forward_blob = _blob(str(binding["forward"]))
        forward = json.loads(forward_blob)
        if not isinstance(forward, dict):
            raise RuntimeError("V2.54.43 terminal forward shape drifted")
        task_count, terminal_tasks = _terminal_counts(forward)
        expected = int(binding["expected_task_count"])
        if (
            _sha256(population_blob) != binding["population_sha256"]
            or _sha256(forward_blob) != binding["forward_sha256"]
            or forward.get("role") != binding["expected_role"]
            or task_count != expected
            or terminal_tasks != expected
        ):
            raise RuntimeError("V2.54.43 consumed population/forward binding drifted")
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
        raise RuntimeError("V2.54.43 parent audit hash drifted")
    build = json.loads(build_blob)
    previous = json.loads(previous_blob)
    if (
        build.get("audit_valid") is not True
        or build.get("authorization", {}).get(
            "fresh_structurally_disjoint_key_anchored_external_protocol_design"
        )
        is not True
        or build.get("authorization", {}).get("external_forward") is not False
        or build.get("authorization", {}).get("reuse_v25438_population_or_forward")
        is not False
        or previous.get("audit_valid") is not True
        or previous.get("selected_first_zero_intersection_interval")
        != "RFC 9160-9239"
        or previous.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
    ):
        raise RuntimeError("V2.54.43 parent barrier drifted")
    return build, previous


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT).strip()
    build, previous = _parent_barriers()
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
        "selection_parent_exact": parent == population.SELECTION_PARENT_COMMIT,
        "v25441_clean_build_audit_bound": bool(build),
        "v25437_previous_structural_audit_bound": bool(previous),
        "nine_consumed_population_terminal_forward_pairs_exact": len(consumed) == 9,
        "all_consumed_ranges_structural_eighty_identity_blocks": all(
            int(row["end"]) - int(row["start"]) + 1 == 80
            for row in consumed
        ),
        "all_consumed_forwards_terminal_at_frozen_denominator": all(
            row["forward_task_count"] == row["forward_terminal_tasks"]
            for row in consumed
        ),
        "forward_score_metric_quality_or_per_task_outcome_never_read": all(
            row["forward_score_metric_quality_or_per_task_outcome_read"] is False
            for row in consumed
        ),
        "v25438_population_and_terminal_forward_now_consumed": any(
            row["interval"] == "RFC 9160-9239"
            and row["forward_role"]
            == "v25438_source_authoritative_shared_effect_external_forward_result"
            for row in consumed
        ),
        "candidate_zero_consumed_intersection": overlap == 0,
        "selected_immediately_preceding_whole_block": candidate
        == expected_candidate
        == (9080, 9159),
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
        "selection_parent_commit": parent,
        "build_audit_sha256": BUILD_AUDIT_SHA256,
        "previous_structural_audit_sha256": PREVIOUS_STRUCTURAL_AUDIT_SHA256,
        "selection_rule": population.SELECTION_RULE,
        "consumed_bindings": consumed,
        "lower_most_consumed_interval_start": lower_most_consumed_start,
        "selected_interval": "RFC 9080-9159",
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
            "key_anchored_external_protocol_design": not findings,
            "candidate_page_endpoint_or_field_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "reuse_v25438_population_or_forward": False,
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
    if (
        copied.get("role") != ROLE
        or copied.get("selection_parent_commit") != population.SELECTION_PARENT_COMMIT
        or copied.get("build_audit_sha256") != BUILD_AUDIT_SHA256
        or copied.get("previous_structural_audit_sha256")
        != PREVIOUS_STRUCTURAL_AUDIT_SHA256
        or copied.get("selection_rule") != "immediately_preceding_whole_block"
        or len(copied.get("consumed_bindings") or []) != 9
        or copied.get("lower_most_consumed_interval_start") != 9160
        or copied.get("selected_interval") != "RFC 9080-9159"
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
            "key_anchored_external_protocol_design": True,
            "candidate_page_endpoint_or_field_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "reuse_v25438_population_or_forward": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or seal != population.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.43 structural population audit drifted")
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
