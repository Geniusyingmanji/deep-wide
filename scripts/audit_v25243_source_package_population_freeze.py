#!/usr/bin/env python3
"""Post-freeze audit for the V2.52.40 visible source-package population."""

from __future__ import annotations

import ast
import copy
import json
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import freeze_v25240_source_package_shadow_population as freeze  # noqa: E402


DATE = "20260812"
ROLE = "v25243_source_package_population_postfreeze_audit"
OUTPUT = Path(f"results/v25243_source_package_population_postfreeze_audit_v1_{DATE}.json")
SOURCE = Path("scripts/audit_v25243_source_package_population_freeze.py")
TEST = Path("tests/test_audit_v25243_source_package_population_freeze.py")
CLAIM = freeze.ATTEMPT_CLAIM
POPULATION = freeze.OUTPUT
START = Path(f"results/v25242_source_package_population_execution_start_v1_{DATE}.json")
FIXED_HASHES = {
    CLAIM: "a5206b2d9e69b75ea713b38b529c5d14512c41eaae9808c3787f4d9ac8f18952",
    POPULATION: "45604e8e4c1d0670890289f9a165f9539bf7dcd50add3cfac4b62d1e638ddcdf",
    START: "ec2d0afef58f32411121f68be2aed55517f6fe1fa85c990bec5afb584baca584",
}
EXPECTED_SELECTION_PARENT = "2c25d51b8f4ffff2d5bd05f712168d20e74e951d"
payload_sha256 = base.payload_sha256


def _fixed_hashes() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in FIXED_HASHES}


def _load() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if any(base.sha256(path) != expected for path, expected in FIXED_HASHES.items()):
        raise RuntimeError("V2.52.43 fixed artifact hash drifted")
    claim = json.loads(base._ordinary(CLAIM).read_text(encoding="utf-8"))
    population = json.loads(base._ordinary(POPULATION).read_text(encoding="utf-8"))
    start = json.loads(base._ordinary(START).read_text(encoding="utf-8"))
    return freeze.validate_attempt_claim(claim), freeze.validate_freeze(population), start


def _semantic_audit() -> dict[str, Any]:
    tree = ast.parse(base._ordinary(freeze.SOURCE).read_text(encoding="utf-8"))
    privileged: list[dict[str, Any]] = []
    forbidden_imports: set[str] = set()
    process_calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            forbidden_imports.update(
                alias.name
                for alias in node.names
                if alias.name.split(".")[0] in {"requests", "httpx", "openai", "socket", "urllib"}
            )
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in {"requests", "httpx", "openai", "socket", "urllib"}:
                forbidden_imports.add(node.module or "")
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            process_calls += 1
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in {
                "category", "question_type", "task_category", "split",
                "ground_truth", "gold", "answer_key", "score", "reward",
            }
        ):
            privileged.append({"line": node.lineno, "field": node.slice.value})
    return {
        "privileged_runtime_field_accesses": sorted(privileged, key=lambda row: (row["line"], row["field"])),
        "forbidden_network_model_imports": sorted(forbidden_imports),
        "selector_subprocess_call_count": process_calls,
    }


def build_audit(*, now: int | None = None, tracked: bool = True) -> dict[str, Any]:
    claim, population, start = _load()
    tasks = freeze.validate_task_vector(population["population"]["task_vector"])
    counts = population["source_receipt"]["source_counts"]
    probe = population["history_receipt"]["probe"]
    per_stratum = population["history_receipt"]["per_stratum"]
    semantic = _semantic_audit()
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    explicit = {SOURCE, TEST, *FIXED_HASHES}
    untracked = sorted(str(path) for path in explicit if tracked and not base._tracked(path))
    watchers = base._watchers()
    lease_inactive = base._lease_inactive()
    start_parent = start.get("git_parent") or {}
    start_execution = start.get("execution_contract") or {}
    checks = {
        "claim_population_and_execution_start_hashes_match": _fixed_hashes() == {str(path): expected for path, expected in FIXED_HASHES.items()},
        "claim_and_population_exact_schema_validate": claim["role"] == freeze.CLAIM_ROLE and population["role"] == freeze.ROLE,
        "selection_parent_matches_pushed_start_commit": (
            population["selection_parent_commit"] == claim["selection_parent_commit"] == EXPECTED_SELECTION_PARENT
            and start_parent.get("head") == start_parent.get("target_main")
            and start_parent.get("head") == base._git("rev-parse", EXPECTED_SELECTION_PARENT + "^")
        ),
        "claim_sha_bound_by_population": population["attempt_claim"] == {"path": str(CLAIM), "sha256": FIXED_HASHES[CLAIM]},
        "source_entities_binary_disjoint_and_counts_conserve": (
            population["source_receipt"]["admitted_source_names_disjoint_from_all_installed_binary_names"] is True
            and counts["source_name_disjoint_from_all_installed_binary_names_count"]
            == sum(counts[name] for name in (*freeze.STRATA, "excluded_other"))
        ),
        "all_485_history_candidates_completed_exactly_once": (
            probe["submitted_count"] == probe["completed_count"] == sum(counts[name] for name in freeze.STRATA) == 485
            and probe["all_admitted_candidates_checked_exactly_once"] is True
            and probe["all_history_probes_succeeded_within_wall_ceiling"] is True
        ),
        "history_process_failure_counts_all_zero": all(
            probe[name] == 0
            for name in (
                "coordinator_cancelled_count", "subprocess_timeout_count",
                "subprocess_nonzero_returncode_count", "subprocess_stderr_nonempty_count",
                "subprocess_incomplete_or_exception_count",
            )
        ),
        "each_stratum_has_exact_64_selected_and_history_zero_capacity": all(
            row["selected_count"] == 64 and row["history_zero_capacity"] >= 64
            for row in per_stratum.values()
        ),
        "task_vector_exact64_package_exact256_visible_only": (
            len(tasks) == 64
            and population["population"]["package_count"] == 256
            and all(set(task) == {"opaque_id", "question"} for task in tasks)
            and population["population"]["hidden_identity_list_stratum_mapping_or_item_hash_persisted"] is False
            and population["population"]["stratum_field_passed_to_runtime"] is False
        ),
        "runtime_keys_exactly_opaque_id_and_question": population["population"]["runtime_keys_exactly_opaque_id_and_question"] is True,
        "start_command_single_attempt_and_internal_wall_bound": (
            start_execution.get("execute_exactly_once") is True
            and start_execution.get("internal_whole_selection_wall_ceiling_seconds") == 240
            and start_execution.get("retry_resume_replacement_selective_backfill_or_second_freeze") is False
        ),
        "selector_privileged_and_network_model_capabilities_zero": (
            semantic["privileged_runtime_field_accesses"] == []
            and semantic["forbidden_network_model_imports"] == []
            and semantic["selector_subprocess_call_count"] == 3
        ),
        "no_network_model_search_fetch_evaluator_benchmark_or_api_called": population["network_model_search_fetch_evaluator_benchmark_or_api_called"] is False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_not_read": population["mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"] is False,
        "entropy_or_information_gain_signed_credit_zero": population["entropy_or_information_gain_assigns_signed_credit"] is False,
        "population_only_authorizes_shadow_protocol_design": (
            population["authorization"]["shadow_reliability_protocol_design"] is True
            and population["authorization"]["shadow_external_activation_or_launch"] is False
            and population["authorization"]["candidate_activation_or_prediction_change"] is False
        ),
        "all_audit_sources_and_frozen_artifacts_tracked": not untracked,
        "git_clean_head_equals_target_main": (clean and head == target) if tracked else True,
        "protected_watchers_unchanged": all(row.get("matches_frozen_identity") is True for row in watchers.values()),
        "shared_api_lease_inactive": lease_inactive,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_artifact_hashes": _fixed_hashes(),
        "selection_receipt": {
            "selection_parent_commit": population["selection_parent_commit"],
            "source_name_disjoint_count": counts["source_name_disjoint_from_all_installed_binary_names_count"],
            "admitted_history_candidate_count": probe["submitted_count"],
            "completed_history_candidate_count": probe["completed_count"],
            "history_zero_capacity_by_stratum": {name: per_stratum[name]["history_zero_capacity"] for name in freeze.STRATA},
            "selected_by_stratum": {name: per_stratum[name]["selected_count"] for name in freeze.STRATA},
            "task_count": population["population"]["task_count"],
            "package_count": population["population"]["package_count"],
            "task_vector_sha256": population["population"]["task_vector_sha256"],
        },
        "semantic_audit": semantic,
        "untracked_sources": untracked,
        "runtime_state": {"shared_api_lease_inactive": lease_inactive, "protected_watchers": watchers},
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh64_shadow_reliability_protocol_design": not findings,
            "fresh64_shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    receipt = copied.get("selection_receipt") or {}
    semantic = copied.get("semantic_audit") or {}
    runtime = copied.get("runtime_state") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied) != {
            "artifact_version", "role", "created_at_unix", "git",
            "fixed_artifact_hashes", "selection_receipt", "semantic_audit",
            "untracked_sources", "runtime_state", "checks", "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_artifact_hashes") != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or set(receipt) != {
            "selection_parent_commit", "source_name_disjoint_count",
            "admitted_history_candidate_count", "completed_history_candidate_count",
            "history_zero_capacity_by_stratum", "selected_by_stratum", "task_count",
            "package_count", "task_vector_sha256",
        }
        or receipt.get("selection_parent_commit") != EXPECTED_SELECTION_PARENT
        or receipt.get("source_name_disjoint_count") != 564
        or receipt.get("admitted_history_candidate_count") != 485
        or receipt.get("completed_history_candidate_count") != 485
        or receipt.get("history_zero_capacity_by_stratum") != {
            "short_alpha": 151, "long_alpha": 93,
            "single_hyphen_alpha": 115, "digit_bearing": 90,
        }
        or receipt.get("selected_by_stratum") != {name: 64 for name in freeze.STRATA}
        or receipt.get("task_count") != 64
        or receipt.get("package_count") != 256
        or set(semantic) != {
            "privileged_runtime_field_accesses", "forbidden_network_model_imports",
            "selector_subprocess_call_count",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("forbidden_network_model_imports") != []
        or semantic.get("selector_subprocess_call_count") != 3
        or copied.get("untracked_sources") != []
        or set(runtime) != {"shared_api_lease_inactive", "protected_watchers"}
        or runtime.get("shared_api_lease_inactive") is not True
        or not all(row.get("matches_frozen_identity") is True for row in runtime.get("protected_watchers", {}).values())
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization != {
            "fresh64_shadow_reliability_protocol_design": True,
            "fresh64_shadow_external_activation_or_launch": False,
            "candidate_activation_or_prediction_change": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.43 source package population audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    base.publish(ROOT / OUTPUT, value)
    print(json.dumps({
        "path": str(OUTPUT), "audit_valid": value["audit_valid"],
        "findings": value["findings"],
        "tasks": value["selection_receipt"]["task_count"],
        "packages": value["selection_receipt"]["package_count"],
        "shadow_protocol_design": value["authorization"]["fresh64_shadow_reliability_protocol_design"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
