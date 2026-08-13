#!/usr/bin/env python3
"""Post-freeze audit for the V2.53.17 disjoint population NO-GO."""

from __future__ import annotations

import copy
import hashlib
import json
import os
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
from scripts import run_v25317_disjoint_worldbank_population as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25320_disjoint_worldbank_population_nogo_audit"
OUTPUT = runner.POSTFREEZE_AUDIT
SOURCE = Path("scripts/audit_v25320_disjoint_worldbank_population_nogo.py")
TEST = Path("tests/test_audit_v25320_disjoint_worldbank_population_nogo.py")
START_COMMIT = "2017ae5d0988f4a42057cd698845cdf69b9add48"
FREEZE_COMMIT = "abc34151f3bb60186270ea4e777070e551313785"
EXPECTED_FIXED = {
    runner.EXECUTION_START: "4e3b72b2321262d795efbbc87c708ac1397d98349d7668573a59ac474a92bae1",
    runner.ATTEMPT_CLAIM: "b0c5bb8635d7cb42683dca0d1e76b2fd8a418cfd9f74307c9eeb4a3bdc2cb18b",
    runner.RESULT: "f5015143ccc03beb40785eb18d91507223c8dcdd30cb95156793a3d895fd9c65",
    runner.PREACTIVATION: "55c55adda8126a523d042acbc5ec91b8af7d803168c26e61b96a2f9ad0453b65",
    runner.CATALOG_RESPONSE: "cc875f9ce9b648cafb4ab52eeba25b46576734c1ce9fa559158d6748cc2b2c51",
}
EXPECTED_WATCHERS = {
    str(row["pid"]): row["start_ticks"] for row in runner.EXPECTED_WATCHERS
}
CHECK_NAMES = frozenset(
    {
        "fixed_start_claim_result_preactivation_and_catalog_exact",
        "start_single_file_and_freeze_exact39_file_commits",
        "start_and_freeze_commits_are_ancestors",
        "claim_and_result_validate_as_one_permanent_nogo_attempt",
        "catalog_body_exactly_binds_success_receipt",
        "candidate_vector_exact24_and_consumed_targets_excluded",
        "all48_target_receipts_terminal_with_one_attempt_each",
        "success36_files_exactly_bind_receipts",
        "failure12_are_transport_error_without_response_bytes",
        "failed_ordinals_exact7_through12_two_pages_each",
        "body_receipt_mismatch_and_consumed_response_overlap_zero",
        "population_private_file_target_entity_task_and_page_counts_zero",
        "provider_attempt_conservation_1_plus48",
        "retry_redirect_refetch_resume_backfill_replacement_zero",
        "model_search_evaluator_benchmark_effect_zero",
        "shared_api_lease_released_after_v25317_owner",
        "active_population_processes_zero",
        "protected_watchers_unchanged",
        "git_clean_head_equals_target_main",
        "label_blind_entropy_credit_and_successor_authority_zero",
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


def _watchers_exact(value: object) -> bool:
    return bool(
        isinstance(value, Mapping)
        and set(value) == set(EXPECTED_WATCHERS)
        and all(
            isinstance(value.get(pid), Mapping)
            and value[pid].get("present") is True
            and value[pid].get("start_ticks") == ticks
            and value[pid].get("matches_frozen_identity") is True
            for pid, ticks in EXPECTED_WATCHERS.items()
        )
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
    markers = (
        "run_v25317_disjoint_worldbank_population.py",
        "v25317_disjoint_worldbank_population",
        "v25297_worldbank_get_helper.py",
    )
    return sorted(
        int(line.strip().split(None, 1)[0])
        for line in completed.stdout.splitlines()
        if line.strip()
        and any(marker in line for marker in markers)
        and "audit_v25320_disjoint_worldbank_population_nogo.py" not in line
    )


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
        and hashlib.sha256(catalog).hexdigest()
        == result["catalog"]["response_sha256"]
    )
    successful: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    binding_valid = True
    expected_success_paths: list[str] = []
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
            binding_valid = bool(
                binding_valid
                and len(blob) == row["response_bytes"]
                and hashlib.sha256(blob).hexdigest() == row["response_sha256"]
            )
            expected_success_paths.append(str(Path(str(row["response_path"]))))
            successful.append(content_free)
        else:
            binding_valid = bool(
                binding_valid
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
        "response_binding_valid": binding_valid,
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
    lease = _lease_observation()
    active = _active_processes()
    watchers = base._watchers()
    expected_start_paths = [str(runner.EXECUTION_START)]
    expected_freeze_paths = sorted(
        [
            str(runner.ATTEMPT_CLAIM),
            str(runner.RESULT),
            str(runner.CATALOG_RESPONSE),
            *replay["expected_success_paths"],
        ]
    )
    failure_counts = dict(sorted(Counter(row["failure_code"] for row in failed).items()))
    checks = {
        "fixed_start_claim_result_preactivation_and_catalog_exact": _fixed()
        == {str(path): digest for path, digest in EXPECTED_FIXED.items()},
        "start_single_file_and_freeze_exact39_file_commits": (
            _changed_paths(START_COMMIT) == expected_start_paths
            and _changed_paths(FREEZE_COMMIT) == expected_freeze_paths
            and len(expected_freeze_paths) == 39
        ),
        "start_and_freeze_commits_are_ancestors": _ancestor(START_COMMIT, head)
        and _ancestor(FREEZE_COMMIT, head),
        "claim_and_result_validate_as_one_permanent_nogo_attempt": (
            claim["claim_is_permanent_even_on_crash_or_no_go"] is True
            and claim["single_catalog_and_single_48_response_batch_only"] is True
            and result["decision"] == "no_go"
            and result["failure_code"] == "target_transport_or_hard_wall"
        ),
        "catalog_body_exactly_binds_success_receipt": replay["catalog_bound"],
        "candidate_vector_exact24_and_consumed_targets_excluded": (
            result["candidate_target_count"] == 24
            and result["catalog"]["selected_candidate_count"] == 24
            and result["catalog"]["consumed_target_count"] == 24
            and set(key.casefold() for key in result["candidate_target_keys"]).isdisjoint(
                key.casefold() for key in runner._build_authority()["consumed_target_keys"]
            )
        ),
        "all48_target_receipts_terminal_with_one_attempt_each": (
            len(result["target_transport"]["rows"]) == 48
            and all(
                row["provider_attempt_count"] == 1
                and row["outcome"] in {"success", "failure"}
                for row in result["target_transport"]["rows"]
            )
        ),
        "success36_files_exactly_bind_receipts": len(successful) == 36
        and replay["response_binding_valid"],
        "failure12_are_transport_error_without_response_bytes": (
            len(failed) == 12
            and failure_counts == {"transport_error": 12}
            and all(
                row["http_status"] is None
                and row["response_bytes"] == 0
                and row["response_sha256"] is None
                for row in failed
            )
        ),
        "failed_ordinals_exact7_through12_two_pages_each": sorted(
            (row["candidate_ordinal"], row["page"]) for row in failed
        )
        == [(ordinal, page) for ordinal in range(7, 13) for page in (1, 2)],
        "body_receipt_mismatch_and_consumed_response_overlap_zero": (
            result["target_transport"]["response_body_receipt_mismatch_count"]
            == 0
            and result["target_transport"]["consumed_response_overlap_count"]
            == 0
        ),
        "population_private_file_target_entity_task_and_page_counts_zero": (
            not (ROOT / runner.POPULATION).exists()
            and not (ROOT / runner.POPULATION).is_symlink()
            and population["private_path"] is None
            and population["selected_target_count"] == 0
            and population["entity_count"] == 0
            and population["task_count"] == 0
            and population["rendered_page_count"] == 0
        ),
        "provider_attempt_conservation_1_plus48": (
            effects["catalog_provider_attempt_count"] == 1
            and effects["target_provider_attempt_count"] == 48
            and result["target_transport"]["successful_response_count"] == 36
        ),
        "retry_redirect_refetch_resume_backfill_replacement_zero": (
            effects["redirect_retry_refetch_resume_backfill_replacement_count"]
            == 0
            and all(
                row["redirect_retry_refetch_count"] == 0
                for row in result["target_transport"]["rows"]
            )
        ),
        "model_search_evaluator_benchmark_effect_zero": effects[
            "model_search_evaluator_or_benchmark_effect_count"
        ]
        == 0,
        "shared_api_lease_released_after_v25317_owner": (
            lease.get("owner") == "v25317_disjoint_worldbank_population_freeze"
            and lease.get("active") is False
            and isinstance(lease.get("released_at_unix"), int)
        ),
        "active_population_processes_zero": active == [],
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "git_clean_head_equals_target_main": clean and head == target,
        "label_blind_entropy_credit_and_successor_authority_zero": (
            result[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            ]
            is False
            and result["entropy_or_information_gain_assigns_signed_credit"]
            is False
            and result["authorization"]
            == {
                "external_monotone_fill_protocol_after_valid_postfreeze_audit": False,
                "external_forward_or_evaluator": False,
                "deepwidebench_dev64_exact220_forward_or_evaluator": False,
                "retry_resume_backfill_replacement_or_second_population_attempt": False,
                "avg_at_4_leaderboard_or_sota": False,
            }
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
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
        "fixed_inputs": _fixed(),
        "attempt": {
            "decision": result["decision"],
            "failure_code": result["failure_code"],
            "whole_elapsed_seconds": result["whole_elapsed_seconds"],
            "target_elapsed_seconds": result["target_transport"][
                "elapsed_seconds"
            ],
            "catalog_provider_attempt_count": effects[
                "catalog_provider_attempt_count"
            ],
            "target_provider_attempt_count": effects[
                "target_provider_attempt_count"
            ],
            "successful_target_response_count": len(successful),
            "failed_target_response_count": len(failed),
            "failure_code_counts": failure_counts,
            "failed_ordinal_pages": [
                [row["candidate_ordinal"], row["page"]] for row in failed
            ],
            "response_body_receipt_mismatch_count": result["target_transport"][
                "response_body_receipt_mismatch_count"
            ],
            "consumed_response_overlap_count": result["target_transport"][
                "consumed_response_overlap_count"
            ],
        },
        "population": {
            "candidate_target_count": result["candidate_target_count"],
            "candidate_target_keys_sha256": runner.payload_sha256(
                result["candidate_target_keys"]
            ),
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
            "v25317_retry_resume_refetch_backfill_replacement_or_second_population_attempt": False,
            "reuse_successful_partial_responses_for_population_or_successor": False,
            "external_monotone_fill_protocol_or_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
            "transport_capacity_successor_build_only": not findings,
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
    population = copied.get("population") or {}
    effects = copied.get("effect_accounting") or {}
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "git",
            "fixed_inputs",
            "attempt",
            "population",
            "effect_accounting",
            "lease_observation",
            "active_processes",
            "protected_watchers",
            "checks",
            "findings",
            "audit_valid",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "question_page_value_prediction_or_credential_emitted",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in EXPECTED_FIXED.items()}
        or attempt.get("decision") != "no_go"
        or attempt.get("failure_code") != "target_transport_or_hard_wall"
        or attempt.get("catalog_provider_attempt_count") != 1
        or attempt.get("target_provider_attempt_count") != 48
        or attempt.get("successful_target_response_count") != 36
        or attempt.get("failed_target_response_count") != 12
        or attempt.get("failure_code_counts") != {"transport_error": 12}
        or attempt.get("failed_ordinal_pages")
        != [[ordinal, page] for ordinal in range(7, 13) for page in (1, 2)]
        or attempt.get("response_body_receipt_mismatch_count") != 0
        or attempt.get("consumed_response_overlap_count") != 0
        or population
        != {
            "candidate_target_count": 24,
            "candidate_target_keys_sha256": population.get(
                "candidate_target_keys_sha256"
            ),
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
        or not _watchers_exact(copied.get("protected_watchers"))
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
            "v25317_retry_resume_refetch_backfill_replacement_or_second_population_attempt": False,
            "reuse_successful_partial_responses_for_population_or_successor": False,
            "external_monotone_fill_protocol_or_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
            "transport_capacity_successor_build_only": not expected_findings,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.20 population NO-GO audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
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
    if not value["audit_valid"]:
        raise SystemExit("V2.53.20 audit failed: " + ", ".join(value["findings"]))
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "decision": value["attempt"]["decision"],
                "successful_target_responses": value["attempt"][
                    "successful_target_response_count"
                ],
                "failed_target_responses": value["attempt"][
                    "failed_target_response_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
