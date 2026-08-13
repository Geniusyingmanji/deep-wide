#!/usr/bin/env python3
"""Post-freeze audit for the V2.53.30 rate-paced population NO-GO."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import run_v25330_rate_paced_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25334_rate_paced_worldbank_population_nogo_audit"
OUTPUT = runner.POSTFREEZE_AUDIT
SOURCE = Path("scripts/audit_v25334_rate_paced_worldbank_population_nogo.py")
TEST = Path("tests/test_audit_v25334_rate_paced_worldbank_population_nogo.py")
START_COMMIT = "1ab653128647edcf249ce1c84115cd915a31ed7e"
FREEZE_COMMIT = "384829b5ab96fd85fa06279fc4fb032ff2e3a7f5"
EXPECTED_FIXED = {
    runner.EXECUTION_START: "3052f591d0ea2743d51b7199e55771ad5bd142d7ca7825b8a016db4f32da163e",
    runner.PREACTIVATION: "7836549ff3b4d98da64ad951bfdbfb6b135e5ffd7c303ab627cf3556b980d085",
    runner.ATTEMPT_CLAIM: "34154cef040b1517f3a11a88e54a0e4ef556d221cdc1bc01893217abf7fa974c",
    runner.RESULT: "71db9cf2f6090b324a5bd2179e27268c0829efa5dda1ed5fe52587651bfc1282",
    runner.CATALOG_RESPONSE: "cc875f9ce9b648cafb4ab52eeba25b46576734c1ce9fa559158d6748cc2b2c51",
}
EXPECTED_FAILED_PAIRS = [[9, 2], [10, 1], [14, 2], [15, 1], [15, 2], [23, 2]]
CHECK_NAMES = frozenset(
    {
        "fixed_start_preactivation_claim_result_and_catalog_exact",
        "start_single_file_and_freeze_exact45_file_commits",
        "start_and_freeze_commits_are_ancestors",
        "claim_and_result_validate_as_one_permanent_nogo_attempt",
        "catalog_body_exactly_binds_success_receipt",
        "candidate_vector_exact24_and_prior72_targets_excluded",
        "all48_target_receipts_terminal_with_one_attempt_each",
        "success42_files_exactly_bind_receipts",
        "failure6_are_transport_error_without_response_bytes",
        "failed_pairs_exact",
        "actual_starts_ticket_ordered_and_minimum_one_second_paced",
        "body_receipt_mismatch_and_consumed_response_overlap_zero",
        "population_private_file_target_entity_task_and_page_counts_zero",
        "provider_attempt_conservation_1_plus48",
        "retry_redirect_refetch_resume_backfill_replacement_zero",
        "model_search_evaluator_benchmark_effect_zero",
        "one_second_pacing_did_not_reach_all48_and_is_not_quality_evidence",
        "shared_api_lease_released_after_v25330_owner",
        "active_population_processes_zero",
        "protected_watchers_unchanged",
        "git_clean_head_equals_target_main",
        "label_blind_entropy_credit_and_all_downstream_authority_zero",
    }
)


def _fixed() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in EXPECTED_FIXED}


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        line
        for line in base._git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        if line
    )


def _ancestor(commit: str, head: str) -> bool:
    return (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, head],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
    )


def _lease_observation() -> dict[str, Any]:
    path = ROOT / "outputs/deepwide_benchmark_api.lease.lock"
    if path.is_symlink() or not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return copy.deepcopy(value) if isinstance(value, Mapping) else {}


def _active_processes() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    )
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        argv = parts[1].split()
        runner_entry = any(
            token.endswith("/scripts/run_v25330_rate_paced_worldbank_population.py")
            or token == "scripts/run_v25330_rate_paced_worldbank_population.py"
            for token in argv[:8]
        )
        helper_entry = any(
            token.endswith("/scripts/v25297_worldbank_get_helper.py")
            or token == "scripts/v25297_worldbank_get_helper.py"
            for token in argv[:8]
        )
        if runner_entry or helper_entry:
            output.append(int(parts[0]))
    return sorted(output)


def _replay() -> dict[str, Any]:
    claim = runner.validate_attempt_claim(
        json.loads(base._ordinary(runner.ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    )
    result = runner.validate_result(
        json.loads(base._ordinary(runner.RESULT).read_text(encoding="utf-8"))
    )
    catalog = base._ordinary(runner.CATALOG_RESPONSE).read_bytes()
    catalog_bound = bool(
        len(catalog) == result["catalog"]["response_bytes"]
        and hashlib.sha256(catalog).hexdigest() == result["catalog"]["response_sha256"]
    )
    successful: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    expected_success_paths: list[str] = []
    response_binding_valid = True
    for row in result["target_transport"]["rows"]:
        content_free = {
            "candidate_ordinal": int(row["candidate_ordinal"]),
            "page": int(row["page"]),
            "outcome": str(row["outcome"]),
            "failure_code": row["failure_code"],
            "http_status": row["http_status"],
            "provider_attempt_count": int(row["provider_attempt_count"]),
            "elapsed_seconds": float(row["elapsed_seconds"]),
            "response_bytes": int(row["response_bytes"]),
            "response_sha256": row["response_sha256"],
        }
        if row["outcome"] == "success":
            path = base._ordinary(Path(str(row["response_path"])))
            blob = path.read_bytes()
            response_binding_valid = bool(
                response_binding_valid
                and len(blob) == row["response_bytes"]
                and hashlib.sha256(blob).hexdigest() == row["response_sha256"]
            )
            expected_success_paths.append(str(Path(str(row["response_path"]))))
            successful.append(content_free)
        else:
            response_binding_valid = bool(
                response_binding_valid
                and row["response_path"] is None
                and row["response_bytes"] == 0
                and row["response_sha256"] is None
            )
            failed.append(content_free)
    return {
        "claim": claim,
        "result": result,
        "catalog_bound": catalog_bound,
        "successful": successful,
        "failed": failed,
        "response_binding_valid": response_binding_valid,
        "expected_success_paths": sorted(expected_success_paths),
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    replay = _replay()
    claim = replay["claim"]
    result = replay["result"]
    successful = replay["successful"]
    failed = replay["failed"]
    effects = result["effect_accounting"]
    population = result["population"]
    transport = result["target_transport"]
    failure_counts = dict(sorted(Counter(row["failure_code"] for row in failed).items()))
    failed_pairs = [[row["candidate_ordinal"], row["page"]] for row in failed]
    lease = _lease_observation()
    active = _active_processes()
    watchers = base._watchers()
    freeze_paths = _changed_paths(FREEZE_COMMIT)
    checks = {
        "fixed_start_preactivation_claim_result_and_catalog_exact": _fixed()
        == {str(path): digest for path, digest in EXPECTED_FIXED.items()},
        "start_single_file_and_freeze_exact45_file_commits": (
            _changed_paths(START_COMMIT) == [str(runner.EXECUTION_START)]
            and len(freeze_paths) == 45
            and str(runner.ATTEMPT_CLAIM) in freeze_paths
            and str(runner.RESULT) in freeze_paths
            and str(runner.CATALOG_RESPONSE) in freeze_paths
            and sum(path.endswith(".bin") for path in freeze_paths) == 43
        ),
        "start_and_freeze_commits_are_ancestors": _ancestor(START_COMMIT, head)
        and _ancestor(FREEZE_COMMIT, head),
        "claim_and_result_validate_as_one_permanent_nogo_attempt": (
            result["decision"] == "no_go"
            and result["failure_code"] == "target_transport_or_hard_wall"
            and result["git_head"] == START_COMMIT
            and claim["git_head"] == START_COMMIT
            and result["attempt_claim"]["sha256"] == base.sha256(runner.ATTEMPT_CLAIM)
        ),
        "catalog_body_exactly_binds_success_receipt": replay["catalog_bound"],
        "candidate_vector_exact24_and_prior72_targets_excluded": (
            result["candidate_target_count"] == 24
            and len(set(item.casefold() for item in result["candidate_target_keys"])) == 24
            and not set(item.casefold() for item in result["candidate_target_keys"]).intersection(
                item.casefold() for item in runner._authority()["consumed_target_keys"]
            )
        ),
        "all48_target_receipts_terminal_with_one_attempt_each": (
            len(transport["rows"]) == 48
            and transport["provider_attempt_count"] == 48
            and all(row["provider_attempt_count"] == 1 for row in transport["rows"])
        ),
        "success42_files_exactly_bind_receipts": (
            len(successful) == 42
            and len(replay["expected_success_paths"]) == 42
            and replay["response_binding_valid"]
        ),
        "failure6_are_transport_error_without_response_bytes": (
            len(failed) == 6
            and failure_counts == {"transport_error": 6}
            and all(
                row["http_status"] is None
                and row["provider_attempt_count"] == 1
                and row["response_bytes"] == 0
                and row["response_sha256"] is None
                and 15.17 <= row["elapsed_seconds"] < 15.20
                for row in failed
            )
        ),
        "failed_pairs_exact": failed_pairs == EXPECTED_FAILED_PAIRS,
        "actual_starts_ticket_ordered_and_minimum_one_second_paced": (
            transport["configured_minimum_start_interval_seconds"] == 1.0
            and transport["observed_minimum_start_interval_seconds"] >= 1.0
            and transport["starts_follow_fixed_work_order"] is True
            and len(transport["request_start_offsets_seconds"]) == 48
            and all(
                transport["request_start_offsets_seconds"][index]
                - transport["request_start_offsets_seconds"][index - 1]
                >= 0.999
                for index in range(1, 48)
            )
        ),
        "body_receipt_mismatch_and_consumed_response_overlap_zero": (
            transport["response_body_receipt_mismatch_count"] == 0
            and transport["consumed_response_overlap_count"] == 0
        ),
        "population_private_file_target_entity_task_and_page_counts_zero": (
            population["selected_target_count"] == 0
            and population["entity_count"] == 0
            and population["task_count"] == 0
            and population["rendered_page_count"] == 0
            and population["private_path"] is None
            and population["private_sha256"] is None
            and not (ROOT / runner.POPULATION).exists()
        ),
        "provider_attempt_conservation_1_plus48": (
            effects["catalog_provider_attempt_count"] == 1
            and effects["target_provider_attempt_count"] == 48
        ),
        "retry_redirect_refetch_resume_backfill_replacement_zero": effects[
            "redirect_retry_refetch_resume_backfill_replacement_count"
        ]
        == 0,
        "model_search_evaluator_benchmark_effect_zero": effects[
            "model_search_evaluator_or_benchmark_effect_count"
        ]
        == 0,
        "one_second_pacing_did_not_reach_all48_and_is_not_quality_evidence": (
            transport["concurrency"] == 6
            and transport["configured_minimum_start_interval_seconds"] == 1.0
            and len(failed) == 6
            and population["task_count"] == 0
        ),
        "shared_api_lease_released_after_v25330_owner": (
            lease.get("owner") == "v25330_rate_paced_worldbank_population_freeze"
            and lease.get("active") is False
            and isinstance(lease.get("released_at_unix"), int)
        ),
        "active_population_processes_zero": active == [],
        "protected_watchers_unchanged": runner.third._protected_watcher_artifact_exact(watchers),
        "git_clean_head_equals_target_main": clean and head == target,
        "label_blind_entropy_credit_and_all_downstream_authority_zero": (
            result[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            ]
            is False
            and result["entropy_or_information_gain_assigns_signed_credit"] is False
            and result["authorization"]
            == {
                "postfreeze_audit": False,
                "external_monotone_fill_protocol_or_forward": False,
                "postfreeze_evaluator": False,
                "deepwidebench_dev64_exact220_forward_or_evaluator": False,
                "retry_resume_backfill_replacement_or_second_population_attempt": False,
            }
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target, "clean": clean},
        "fixed_inputs": _fixed(),
        "attempt": {
            "decision": result["decision"],
            "failure_code": result["failure_code"],
            "whole_elapsed_seconds": result["whole_elapsed_seconds"],
            "target_elapsed_seconds": transport["elapsed_seconds"],
            "catalog_provider_attempt_count": effects["catalog_provider_attempt_count"],
            "target_provider_attempt_count": effects["target_provider_attempt_count"],
            "target_concurrency": transport["concurrency"],
            "configured_minimum_start_interval_seconds": transport["configured_minimum_start_interval_seconds"],
            "observed_minimum_start_interval_seconds": transport["observed_minimum_start_interval_seconds"],
            "maximum_observed_concurrency": transport["maximum_observed_concurrency"],
            "successful_target_response_count": len(successful),
            "failed_target_response_count": len(failed),
            "failure_code_counts": failure_counts,
            "failed_ordinal_pages": failed_pairs,
            "response_body_receipt_mismatch_count": transport["response_body_receipt_mismatch_count"],
            "consumed_response_overlap_count": transport["consumed_response_overlap_count"],
        },
        "bounded_conclusion": {
            "actual_provider_starts_were_at_least_one_second_apart": True,
            "one_second_pacing_did_not_eliminate_transport_failures": True,
            "pattern_proves_unique_causal_root_cause": False,
            "partial_successes_are_not_population_quality_or_entropy_credit_evidence": True,
            "all48_success_reached": False,
            "population_go_reached": False,
        },
        "population": {
            "candidate_target_count": result["candidate_target_count"],
            "candidate_target_keys_sha256": runner.payload_sha256(result["candidate_target_keys"]),
            "selected_target_count": population["selected_target_count"],
            "entity_count": population["entity_count"],
            "task_count": population["task_count"],
            "rendered_page_count": population["rendered_page_count"],
            "private_population_exists": False,
        },
        "effect_accounting": copy.deepcopy(effects),
        "lease_observation": lease,
        "active_processes": active,
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "question_page_value_prediction_or_credential_emitted": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "v25330_retry_resume_refetch_backfill_replacement_or_second_population_attempt": False,
            "reuse_successful_partial_responses_for_population_or_successor": False,
            "external_monotone_fill_protocol_or_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
            "next_transport_diagnosis_build_only": not findings,
        },
    }
    value["audit_payload_sha256"] = runner.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks") or {}
    findings = copied.get("findings")
    attempt = copied.get("attempt") or {}
    conclusion = copied.get("bounded_conclusion") or {}
    population = copied.get("population") or {}
    effects = copied.get("effect_accounting") or {}
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git", "fixed_inputs",
            "attempt", "bounded_conclusion", "population", "effect_accounting",
            "lease_observation", "active_processes", "protected_watchers", "checks",
            "findings", "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "question_page_value_prediction_or_credential_emitted",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs") != {str(path): digest for path, digest in EXPECTED_FIXED.items()}
        or attempt.get("decision") != "no_go"
        or attempt.get("failure_code") != "target_transport_or_hard_wall"
        or attempt.get("catalog_provider_attempt_count") != 1
        or attempt.get("target_provider_attempt_count") != 48
        or attempt.get("target_concurrency") != 6
        or attempt.get("configured_minimum_start_interval_seconds") != 1.0
        or not isinstance(attempt.get("observed_minimum_start_interval_seconds"), (int, float))
        or float(attempt["observed_minimum_start_interval_seconds"]) < 1.0
        or attempt.get("maximum_observed_concurrency") != 6
        or attempt.get("successful_target_response_count") != 42
        or attempt.get("failed_target_response_count") != 6
        or attempt.get("failure_code_counts") != {"transport_error": 6}
        or attempt.get("failed_ordinal_pages") != EXPECTED_FAILED_PAIRS
        or attempt.get("response_body_receipt_mismatch_count") != 0
        or attempt.get("consumed_response_overlap_count") != 0
        or conclusion
        != {
            "actual_provider_starts_were_at_least_one_second_apart": True,
            "one_second_pacing_did_not_eliminate_transport_failures": True,
            "pattern_proves_unique_causal_root_cause": False,
            "partial_successes_are_not_population_quality_or_entropy_credit_evidence": True,
            "all48_success_reached": False,
            "population_go_reached": False,
        }
        or population
        != {
            "candidate_target_count": 24,
            "candidate_target_keys_sha256": population.get("candidate_target_keys_sha256"),
            "selected_target_count": 0,
            "entity_count": 0,
            "task_count": 0,
            "rendered_page_count": 0,
            "private_population_exists": False,
        }
        or not isinstance(population.get("candidate_target_keys_sha256"), str)
        or len(population["candidate_target_keys_sha256"]) != 64
        or effects
        != {
            "catalog_provider_attempt_count": 1,
            "target_provider_attempt_count": 48,
            "redirect_retry_refetch_resume_backfill_replacement_count": 0,
            "model_search_evaluator_or_benchmark_effect_count": 0,
            "public_worldbank_network_or_api_called": True,
        }
        or copied.get("active_processes") != []
        or not runner.third._protected_watcher_artifact_exact(copied.get("protected_watchers"))
        or set(checks) != CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or findings != expected_findings
        or copied.get("audit_valid") is not (not expected_findings)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
                "question_page_value_prediction_or_credential_emitted",
                "entropy_or_information_gain_assigns_signed_credit",
            )
        )
        or authorization
        != {
            "v25330_retry_resume_refetch_backfill_replacement_or_second_population_attempt": False,
            "reuse_successful_partial_responses_for_population_or_successor": False,
            "external_monotone_fill_protocol_or_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
            "next_transport_diagnosis_build_only": not expected_findings,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.34 population NO-GO audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.53.34 audit failed: " + ", ".join(value["findings"]))
    runner.publish_json_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "success": value["attempt"]["successful_target_response_count"],
                "failure": value["attempt"]["failed_target_response_count"],
                "minimum_start_interval_seconds": value["attempt"]["observed_minimum_start_interval_seconds"],
                "audit_payload_sha256": value["audit_payload_sha256"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
