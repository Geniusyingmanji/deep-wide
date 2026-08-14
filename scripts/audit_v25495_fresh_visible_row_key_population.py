#!/usr/bin/env python3
"""Audit the frozen V2.54.94 visible-row-key external population."""

from __future__ import annotations

import copy
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

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25486_outcome_blind_iana_detail_population as prior  # noqa: E402
from deepwide_agent import v25494_fresh_visible_row_key_population as population  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base  # noqa: E402
from scripts import audit_v25493_visible_row_key_detail_build as build  # noqa: E402


DATE = "20260814"
ROLE = "v25495_fresh_visible_row_key_population_audit"
IMPLEMENTATION_COMMIT = "2ad2daa9d14a979cb8f994fe2e71bd16c16c9040"
SOURCE = Path("scripts/audit_v25495_fresh_visible_row_key_population.py")
TEST = Path("tests/test_audit_v25495_fresh_visible_row_key_population.py")
POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25494_fresh_visible_row_key_population.py"
)
POPULATION_TEST = Path("tests/test_v25494_fresh_visible_row_key_population.py")
BUILD_AUDIT = Path(
    "results/v25493_visible_row_key_detail_build_audit_v1_20260814.json"
)
OUTPUT = Path(
    f"results/v25495_fresh_visible_row_key_population_audit_v1_{DATE}.json"
)
FIXED_HASHES = {
    BUILD_AUDIT: "2a303830f225018a2b2debafffbd831533f403b08367a6f65bb30d278a76a378",
    POPULATION_SOURCE: "947ebe124856f79f9fe2045c2bc77fc27eca43bea91f3afd5ab9437358a3fecd",
    POPULATION_TEST: "ad364b2c9254ce1763096e849755975a7f81239f566e3038c9bc1cdf606a2b71",
}
CHECK_NAMES = frozenset(
    {
        "git_clean_head_equals_target_main",
        "population_audit_parent_and_population_files_tracked",
        "selection_parent_exact",
        "population_implementation_commit_in_head_history",
        "v25493_clean_build_population_design_authority_bound",
        "fixed_parent_and_population_hashes_exact",
        "identity_and_task_vectors_exact_twenty_unique_and_hash_bound",
        "zero_exact_question_or_opaque_overlap_with_latest_consumed_population",
        "explicit_visible_row_key_and_public_index_url_only",
        "public_index_structure_observation_exact_twenty",
        "public_index_observation_opened_no_detail_page_field_prediction_or_quality",
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages",
        "population_selection_is_label_blind_and_outcome_free",
        "historical_per_task_forward_page_prediction_score_quality_or_outcome_never_read",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "model_search_detail_fetch_evaluator_or_benchmark_not_called",
        "positive_signed_credit_zero",
    }
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
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
        == 0
    )


def _build_barrier() -> dict[str, Any]:
    value = json.loads(base._ordinary(BUILD_AUDIT).read_text(encoding="utf-8"))
    build.validate_audit(value)
    if (
        base.sha256(BUILD_AUDIT) != FIXED_HASHES[BUILD_AUDIT]
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "fresh_outcome_blind_external_population_design"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.54.95 build barrier drifted")
    return value


def build_audit(
    *, now: int | None = None, tracked: bool = True
) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    clean = not _git("status", "--porcelain")
    selection_parent = _git("rev-parse", population.SELECTION_PARENT_COMMIT)
    implementation_in_history = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", IMPLEMENTATION_COMMIT, "HEAD"],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        ).returncode
        == 0
    )
    build_barrier = _build_barrier()
    fixed = {str(path): base.sha256(path) for path in FIXED_HASHES}
    identities = population.identity_vector()
    tasks = population.task_vector()
    prior_tasks = prior.task_vector()
    snapshot = watchers.watcher_snapshot()
    explicit = {
        SOURCE,
        TEST,
        POPULATION_SOURCE,
        POPULATION_TEST,
        BUILD_AUDIT,
    }
    untracked = sorted(str(path) for path in explicit if tracked and not _tracked(path))
    reported_clean = clean if tracked else True
    policy = population.source_policy()
    structural_observation = {
        "public_index_url": population.INDEX_URL,
        "observed_anchor_child_count": 20,
        "all_identity_anchors_exact": True,
        "all_child_paths_exact_domains_root_db_identity_html": True,
        "detail_page_or_field_body_opened": False,
        "prediction_evaluator_score_quality_or_historical_result_opened": False,
    }
    checks = {
        "git_clean_head_equals_target_main": reported_clean and head == target,
        "population_audit_parent_and_population_files_tracked": not untracked,
        "selection_parent_exact": selection_parent
        == population.SELECTION_PARENT_COMMIT,
        "population_implementation_commit_in_head_history": implementation_in_history,
        "v25493_clean_build_population_design_authority_bound": bool(build_barrier),
        "fixed_parent_and_population_hashes_exact": all(
            fixed[str(path)] == expected for path, expected in FIXED_HASHES.items()
        ),
        "identity_and_task_vectors_exact_twenty_unique_and_hash_bound": (
            len(identities) == 20
            and len(set(identities)) == 20
            and len(tasks) == 20
            and population.payload_sha256(identities)
            == population.EXPECTED_IDENTITY_VECTOR_SHA256
            and population.payload_sha256(tasks)
            == population.EXPECTED_TASK_VECTOR_SHA256
        ),
        "zero_exact_question_or_opaque_overlap_with_latest_consumed_population": (
            not ({task["opaque_id"] for task in tasks} & {task["opaque_id"] for task in prior_tasks})
            and not ({task["question"] for task in tasks} & {task["question"] for task in prior_tasks})
        ),
        "explicit_visible_row_key_and_public_index_url_only": all(
            f"<DOMAIN>{identity}</DOMAIN>" in task["question"]
            and task["question"].count(population.INDEX_URL) == 1
            for identity, task in zip(identities, tasks, strict=True)
        ),
        "public_index_structure_observation_exact_twenty": (
            structural_observation["observed_anchor_child_count"] == 20
            and structural_observation["all_identity_anchors_exact"] is True
            and structural_observation[
                "all_child_paths_exact_domains_root_db_identity_html"
            ]
            is True
        ),
        "public_index_observation_opened_no_detail_page_field_prediction_or_quality": (
            structural_observation["detail_page_or_field_body_opened"] is False
            and structural_observation[
                "prediction_evaluator_score_quality_or_historical_result_opened"
            ]
            is False
        ),
        "runtime_boundary_exactly_opaque_id_question_and_same_forward_pages": policy[
            "runtime_boundary"
        ]
        == ["opaque_id", "question", "same_forward_public_pages"],
        "population_selection_is_label_blind_and_outcome_free": (
            policy[
                "detail_page_field_value_prediction_evaluator_score_or_quality_opened_for_selection"
            ]
            is False
            and policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
            is False
        ),
        "historical_per_task_forward_page_prediction_score_quality_or_outcome_never_read": policy[
            "historical_per_task_forward_page_prediction_score_metric_quality_or_outcome_read"
        ]
        is False,
        "protected_watchers_unchanged": snapshot
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in watchers.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": base._lease_inactive(),
        "model_search_detail_fetch_evaluator_or_benchmark_not_called": True,
        "positive_signed_credit_zero": population.mechanism_gate()[
            "positive_signed_credit_count"
        ]
        == 0,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_commit": IMPLEMENTATION_COMMIT,
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "clean": reported_clean,
        },
        "fixed_artifact_hashes": fixed,
        "selection": {
            "identity_count": 20,
            "task_count": 20,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "latest_consumed_task_vector_sha256": population.PRIOR_TASK_VECTOR_SHA256,
            "question_overlap_count": 0,
            "opaque_id_overlap_count": 0,
            "individual_task_retention_replacement_or_ranking": False,
        },
        "public_index_structural_observation": structural_observation,
        "source_policy": policy,
        "mechanism_gate": population.mechanism_gate(),
        "protected_watchers": snapshot,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "historical_per_task_forward_page_prediction_score_metric_quality_or_outcome_read": False,
        "detail_page_field_value_prediction_score_or_per_task_outcome_persisted": False,
        "model_search_detail_fetch_evaluator_benchmark_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "fresh_external_protocol_design": not findings,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "reuse_prior_execution_authority_or_population": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = base.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    selection = copied.get("selection")
    structure = copied.get("public_index_structural_observation")
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("implementation_commit") != IMPLEMENTATION_COMMIT
        or copied.get("selection_parent_commit") != population.SELECTION_PARENT_COMMIT
        or not isinstance(checks, Mapping)
        or set(checks) != CHECK_NAMES
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or not isinstance(selection, Mapping)
        or selection.get("identity_count") != 20
        or selection.get("task_count") != 20
        or selection.get("identity_vector_sha256")
        != population.EXPECTED_IDENTITY_VECTOR_SHA256
        or selection.get("task_vector_sha256")
        != population.EXPECTED_TASK_VECTOR_SHA256
        or selection.get("question_overlap_count") != 0
        or selection.get("opaque_id_overlap_count") != 0
        or not isinstance(structure, Mapping)
        or structure.get("observed_anchor_child_count") != 20
        or structure.get("detail_page_or_field_body_opened") is not False
        or structure.get(
            "prediction_evaluator_score_quality_or_historical_result_opened"
        )
        is not False
        or copied.get("model_search_detail_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "fresh_external_protocol_design": valid,
            "external_forward": False,
            "postfreeze_truth_or_quality": False,
            "deepwidebench_forward_or_evaluator": False,
            "reuse_prior_execution_authority_or_population": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.95 population audit drifted")
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
    if value["findings"]:
        raise RuntimeError(value["findings"])
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
