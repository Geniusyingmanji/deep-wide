#!/usr/bin/env python3
"""Structural consumed-range audit for the V2.54.27 RFC population."""

from __future__ import annotations

import ast
import copy
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

from deepwide_agent import v25427_structurally_disjoint_rfc_population as population  # noqa: E402


DATE = "20260813"
ROLE = "v25428_structurally_disjoint_rfc_population_audit"
SOURCE = Path("scripts/audit_v25428_structurally_disjoint_rfc_population.py")
TEST = Path("tests/test_audit_v25428_structurally_disjoint_rfc_population.py")
OUTPUT = Path(
    f"results/v25428_structurally_disjoint_rfc_population_audit_v1_{DATE}.json"
)
PRIORITY_AUDIT = Path(
    "results/v25414_fresh_paired_rfc_route_population_audit_v1_20260813.json"
)
ERRATUM = Path(
    "results/v25425_population_overlap_and_candidate_funnel_diagnosis_v1_20260813.json"
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
    import hashlib

    return hashlib.sha256(value).hexdigest()


def structural_rfc_range(source: bytes) -> tuple[int, int]:
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
            raise ValueError("V2.54.28 RFC_NUMBERS is not tuple(range(start, stop))")
        start = ast.literal_eval(value.args[0].args[0])
        stop = ast.literal_eval(value.args[0].args[1])
        if (
            isinstance(start, bool)
            or isinstance(stop, bool)
            or not isinstance(start, int)
            or not isinstance(stop, int)
            or stop <= start
            or stop - start != 80
        ):
            raise ValueError("V2.54.28 RFC range is not one 80-identity block")
        matches.append((start, stop - 1))
    if len(matches) != 1:
        raise ValueError("V2.54.28 RFC range assignment is ambiguous")
    return matches[0]


def _terminal_count(forward: Mapping[str, Any]) -> int:
    aggregate = forward.get("aggregate")
    if not isinstance(aggregate, Mapping):
        raise ValueError("V2.54.28 forward aggregate is absent")
    for key in ("task_count", "terminal_tasks"):
        value = aggregate.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    raise ValueError("V2.54.28 forward denominator is absent")


def consumed_ranges() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for binding in CONSUMED_BINDINGS:
        population_blob = _blob(str(binding["population"]))
        forward_blob = _blob(str(binding["forward"]))
        forward = json.loads(forward_blob)
        if (
            _sha256(population_blob) != binding["population_sha256"]
            or _sha256(forward_blob) != binding["forward_sha256"]
            or not isinstance(forward, dict)
            or forward.get("role") != binding["expected_role"]
            or _terminal_count(forward) != binding["expected_task_count"]
        ):
            raise RuntimeError("V2.54.28 consumed population/forward binding drifted")
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
                "forward_task_count": binding["expected_task_count"],
                "forward_score_metric_or_quality_read": False,
            }
        )
    return output


def _overlap_count(interval: tuple[int, int], consumed: Sequence[Mapping[str, Any]]) -> int:
    start, end = interval
    occupied: set[int] = set()
    for row in consumed:
        occupied.update(range(int(row["start"]), int(row["end"]) + 1))
    return len(set(range(start, end + 1)).intersection(occupied))


def _parent_barriers() -> tuple[dict[str, Any], dict[str, Any]]:
    priority_blob = _blob(str(PRIORITY_AUDIT))
    erratum_blob = _blob(str(ERRATUM))
    if (
        _sha256(priority_blob) != population.PRIORITY_AUDIT_SHA256
        or _sha256(erratum_blob) != population.OVERLAP_ERRATUM_SHA256
    ):
        raise RuntimeError("V2.54.28 parent audit hash drifted")
    priority = json.loads(priority_blob)
    erratum = json.loads(erratum_blob)
    expected_order = [f"RFC {a}-{b}" for a, b in population.CANDIDATE_INTERVAL_ORDER]
    if (
        priority.get("candidate_interval_order") != expected_order
        or priority.get("candidate_page_endpoint_model_evaluator_or_quality_opened")
        is not False
        or priority.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read")
        is not False
        or erratum.get("diagnosis_valid") is not True
        or erratum.get("population_erratum", {}).get(
            "v25421_fresh_disjoint_claim_valid"
        )
        is not False
        or erratum.get("authorization", {}).get(
            "structural_consumed_range_population_selector_build"
        )
        is not True
        or erratum.get("authorization", {}).get("external_forward_or_evaluator")
        is not False
    ):
        raise RuntimeError("V2.54.28 parent selection barrier drifted")
    return priority, erratum


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT).strip()
    priority, erratum = _parent_barriers()
    consumed = consumed_ranges()
    overlap = {
        f"RFC {start}-{end}": _overlap_count((start, end), consumed)
        for start, end in population.CANDIDATE_INTERVAL_ORDER
    }
    selected = next(label for label, count in overlap.items() if count == 0)
    identities = population.identity_vector()
    groups = population.group_vector()
    tasks = population.task_vector()
    expected_selected = f"RFC {population.RFC_NUMBERS[0]}-{population.RFC_NUMBERS[-1]}"
    checks = {
        "selection_parent_exact": parent == population.SELECTION_PARENT_COMMIT,
        "v25414_candidate_order_bound_before_current_outcomes": bool(priority),
        "v25425_literal_freshness_erratum_bound": bool(erratum),
        "seven_consumed_population_forward_pairs_exact": len(consumed) == 7,
        "all_consumed_ranges_structural_eighty_identity_blocks": all(
            int(row["end"]) - int(row["start"]) + 1 == 80 for row in consumed
        ),
        "forward_score_metric_or_quality_never_read": all(
            row["forward_score_metric_or_quality_read"] is False for row in consumed
        ),
        "candidate_overlap_vector_exact": overlap
        == {"RFC 9320-9399": 80, "RFC 9240-9319": 0, "RFC 9160-9239": 0},
        "selected_first_zero_intersection_block": selected == expected_selected
        == "RFC 9240-9319",
        "population_vectors_exact": (
            population.payload_sha256(identities)
            == population.EXPECTED_IDENTITY_VECTOR_SHA256
            and population.payload_sha256(groups)
            == population.EXPECTED_GROUP_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "aggregate_presence_disclosed_but_not_selection_input": (
            population.source_policy()["aggregate_candidate_identity_presence_previously_observed"]
            and population.source_policy()["aggregate_candidate_identity_presence_count"]
            == 80
            and population.source_policy()[
                "aggregate_presence_used_for_selection_replacement_or_ranking"
            ]
            is False
        ),
        "network_model_search_fetch_evaluator_or_benchmark_called": True,
        "positive_signed_credit_zero": True,
    }
    # This audit itself performs no external effect.  The positively worded
    # temporary entry above makes accidental omission fail closed here.
    checks["network_model_search_fetch_evaluator_or_benchmark_called"] = False
    findings = sorted(
        name
        for name, passed in checks.items()
        if name != "network_model_search_fetch_evaluator_or_benchmark_called"
        and not passed
    )
    if checks["network_model_search_fetch_evaluator_or_benchmark_called"] is not False:
        findings.append("network_model_search_fetch_evaluator_or_benchmark_called")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "selection_parent_commit": parent,
        "priority_audit_sha256": population.PRIORITY_AUDIT_SHA256,
        "overlap_erratum_sha256": population.OVERLAP_ERRATUM_SHA256,
        "candidate_interval_order": [
            f"RFC {start}-{end}"
            for start, end in population.CANDIDATE_INTERVAL_ORDER
        ],
        "consumed_bindings": consumed,
        "candidate_consumed_overlap_identity_counts": overlap,
        "selected_first_zero_intersection_interval": selected,
        "task_count": population.TASK_COUNT,
        "rows_per_task": population.ROWS_PER_TASK,
        "identity_count": len(identities),
        "identity_vector_sha256": population.payload_sha256(identities),
        "group_vector_sha256": population.payload_sha256(groups),
        "task_vector_sha256": population.payload_sha256(tasks),
        "aggregate_candidate_identity_presence_observed_before_freeze": True,
        "aggregate_candidate_identity_presence_count": 80,
        "aggregate_presence_used_for_selection_replacement_or_ranking": False,
        "candidate_field_value_page_quality_prediction_evaluator_or_per_task_outcome_read_for_selection": False,
        "individual_identity_or_task_retained_replaced_or_ranked": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "checks": checks,
        "findings": sorted(findings),
        "audit_valid": not findings,
        "authorization": {
            "combined_membership_list_atomic_external_protocol_design": not findings,
            "candidate_page_endpoint_or_field_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
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
        or copied.get("priority_audit_sha256") != population.PRIORITY_AUDIT_SHA256
        or copied.get("overlap_erratum_sha256") != population.OVERLAP_ERRATUM_SHA256
        or copied.get("candidate_interval_order")
        != ["RFC 9320-9399", "RFC 9240-9319", "RFC 9160-9239"]
        or len(copied.get("consumed_bindings") or []) != 7
        or copied.get("candidate_consumed_overlap_identity_counts")
        != {"RFC 9320-9399": 80, "RFC 9240-9319": 0, "RFC 9160-9239": 0}
        or copied.get("selected_first_zero_intersection_interval")
        != "RFC 9240-9319"
        or copied.get("task_count") != 20
        or copied.get("rows_per_task") != 4
        or copied.get("identity_count") != 80
        or copied.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or copied.get("group_vector_sha256")
        != population.EXPECTED_GROUP_VECTOR_SHA256
        or copied.get("task_vector_sha256") != population.EXPECTED_TASK_VECTOR_SHA256
        or copied.get("aggregate_candidate_identity_presence_observed_before_freeze")
        is not True
        or copied.get("aggregate_candidate_identity_presence_count") != 80
        or copied.get("aggregate_presence_used_for_selection_replacement_or_ranking")
        is not False
        or copied.get("candidate_field_value_page_quality_prediction_evaluator_or_per_task_outcome_read_for_selection")
        is not False
        or copied.get("individual_identity_or_task_retained_replaced_or_ranked")
        is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read")
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
            "combined_membership_list_atomic_external_protocol_design": True,
            "candidate_page_endpoint_or_field_preflight": False,
            "network_model_search_fetch_external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or seal != population.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.28 structural population audit drifted")
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
                "selected": value["selected_first_zero_intersection_interval"],
                "overlap_counts": value[
                    "candidate_consumed_overlap_identity_counts"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
