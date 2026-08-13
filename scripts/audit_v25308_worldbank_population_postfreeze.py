#!/usr/bin/env python3
"""Post-freeze audit for the V2.53.05 fresh World Bank population."""

from __future__ import annotations

import copy
import hashlib
import json
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

from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import run_v25297_worldbank_population_freeze as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25308_worldbank_population_postfreeze_audit"
OUTPUT = runner.POSTFREEZE_AUDIT
SOURCE = Path("scripts/audit_v25308_worldbank_population_postfreeze.py")
TEST = Path("tests/test_audit_v25308_worldbank_population_postfreeze.py")
START_COMMIT = "b0021b65d6a97f2711864f3eee41ab9a576f11a6"
FREEZE_COMMIT = "2499cdbd95a5588b553d60be4ffa3db674c7f757"
EXPECTED_FIXED = {
    runner.EXECUTION_START: "bdf0f2e6f915b2cd43f731f44f6187045de9eb04f95476cfab6f7314e55abd1e",
    runner.ATTEMPT_CLAIM: "ad31f9431673f82335fe3f2b6bdb588d7f30316fac4c16ffb195dffebebb31e2",
    runner.RESULT: "6abbce3cb6271cde5046479b78a8436ba41fbb383679c102d857731d262e600b",
    runner.PREACTIVATION: "5916d94866e1e7d73a613f6471bc6de4bfc1421a21f4a0968e4a6479441ad727",
    runner.SOURCE: "d6cac9b0393018fac13a9899219b0a22ebd4493e783b0fb434cc47bcb1854be0",
    runner.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    runner.TEST: "dd861223851df0712913d8e9cb802a32d0ed0d3d932b88d4cc332467fdaaaa91",
    runner.CATALOG_RESPONSE: "cc875f9ce9b648cafb4ab52eeba25b46576734c1ce9fa559158d6748cc2b2c51",
    runner.POPULATION: "ced33e651b0d72a65a59d4106ea5b68316f25bd5b31ca9a54f8f1c9d2689fcec",
}
EXPECTED_WATCHERS = {
    str(row["pid"]): row["start_ticks"] for row in runner.EXPECTED_WATCHERS
}
CHECK_NAMES = frozenset(
    {
        "fixed_start_claim_result_preactivation_sources_catalog_and_population_exact",
        "start_single_file_commit_and_freeze_exact52_file_commit",
        "start_and_freeze_commits_are_ancestors",
        "claim_and_result_validate_as_single_go_attempt",
        "catalog_replay_selects_same_exact24_fresh_candidates",
        "all48_response_files_exactly_bind_receipts",
        "all24_two_page_targets_reparse_with_complete_coverage",
        "selector_replay_reconstructs_same_population",
        "private_population_payload_and_file_hash_valid",
        "selected_quartet_144_entities_8_pages_12_tasks_exact",
        "provider_attempt_conservation_1_plus48",
        "retry_redirect_refetch_resume_backfill_replacement_zero",
        "model_search_evaluator_benchmark_effect_zero",
        "shared_api_lease_released_after_v25305_owner",
        "active_population_processes_zero",
        "protected_watchers_unchanged",
        "git_clean_head_equals_target_main",
        "label_blind_and_entropy_signed_credit_zero",
    }
)


def _fixed() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in EXPECTED_FIXED}


def _changed_paths(commit: str) -> list[str]:
    return sorted(
        value
        for value in base._git(
            "diff-tree", "--no-commit-id", "--name-only", "-r", commit
        ).splitlines()
        if value
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
    return sorted(
        int(line.strip().split(None, 1)[0])
        for line in completed.stdout.splitlines()
        if line.strip()
        and any(
            marker in line
            for marker in (
                "v25305_worldbank_population",
                "run_v25297_worldbank_population_freeze.py",
                "v25297_worldbank_get_helper.py",
            )
        )
        and "audit_v25308_worldbank_population_postfreeze.py" not in line
    )


def _replay() -> dict[str, Any]:
    historical, historical_manifest = runner.historical_indicator_manifest()
    catalog_blob = base._ordinary(runner.CATALOG_RESPONSE).read_bytes()
    targets, catalog_stats = runner.parse_catalog(catalog_blob, historical=historical)
    target_keys = [target.key for target in targets]
    result = runner.validate_result(
        json.loads(base._ordinary(runner.RESULT).read_text(encoding="utf-8"))
    )
    rows = result["target_transport"]["rows"]
    by_pair = {
        (int(row["candidate_ordinal"]), int(row["page"])): row for row in rows
    }
    candidates: dict[runner.runtime.TargetSpec, tuple[bytes, bytes]] = {}
    response_vector: list[dict[str, Any]] = []
    binding_valid = True
    for index, target in enumerate(targets, 1):
        blobs: list[bytes] = []
        for page in (1, 2):
            row = by_pair.get((index, page)) or {}
            expected = runner.TARGET_RESPONSE_ROOT / f"response_{index:02d}_page_{page}.bin"
            path = base._ordinary(expected)
            blob = path.read_bytes()
            digest = hashlib.sha256(blob).hexdigest()
            binding_valid = bool(
                binding_valid
                and row.get("target_key") == target.key
                and row.get("response_path") == str(expected)
                and row.get("response_bytes") == len(blob)
                and row.get("response_sha256") == digest
                and row.get("provider_attempt_count") == 1
                and row.get("outcome") == "success"
            )
            blobs.append(blob)
            response_vector.append(
                {
                    "path": str(expected),
                    "bytes": len(blob),
                    "sha256": digest,
                    "target_key": target.key,
                    "page": page,
                }
            )
        runner.runtime.parse_target_pages(blobs, target=target)
        candidates[target] = (blobs[0], blobs[1])
    replayed = runner.runtime.select_and_render_population(
        candidates,
        historical_target_keys=[
            f"{indicator}@{runner.runtime.TARGET_YEAR}" for indicator in historical
        ],
    )
    private_path = base._ordinary(runner.POPULATION)
    private = json.loads(private_path.read_text(encoding="utf-8"))
    unsigned_private = dict(private)
    private_seal = unsigned_private.pop("population_payload_sha256", None)
    private_valid = bool(
        private.get("artifact_version") == 1
        and private.get("role") == "v25305_private_frozen_worldbank_population"
        and private.get("candidate_target_keys") == target_keys
        and private.get("historical_indicator_manifest_sha256")
        == runner.payload_sha256(sorted(historical))
        and private.get("population") == replayed
        and private_seal == runner.payload_sha256(unsigned_private)
        and runner.sha256(private_path) == result["population"]["private_sha256"]
    )
    return {
        "historical_indicator_manifest": historical_manifest,
        "catalog_stats": catalog_stats,
        "target_keys": target_keys,
        "response_vector": response_vector,
        "response_vector_sha256": runner.payload_sha256(response_vector),
        "response_binding_valid": binding_valid,
        "replayed_population": replayed,
        "private_population_valid": private_valid,
        "result": result,
        "private": private,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target_main = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    claim = runner.validate_attempt_claim(
        json.loads(base._ordinary(runner.ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    )
    replay = _replay()
    result = replay["result"]
    population = replay["replayed_population"]
    effects = result["effect_accounting"]
    lease = _lease_observation()
    active = _active_processes()
    watchers = base._watchers()
    expected_start_paths = [str(runner.EXECUTION_START)]
    expected_freeze_paths = sorted(
        [str(runner.ATTEMPT_CLAIM), str(runner.RESULT)]
        + [row["path"] for row in replay["response_vector"]]
        + [str(runner.CATALOG_RESPONSE), str(runner.POPULATION)]
    )
    checks = {
        "fixed_start_claim_result_preactivation_sources_catalog_and_population_exact": _fixed()
        == {str(path): digest for path, digest in EXPECTED_FIXED.items()},
        "start_single_file_commit_and_freeze_exact52_file_commit": _changed_paths(
            START_COMMIT
        )
        == expected_start_paths
        and _changed_paths(FREEZE_COMMIT) == expected_freeze_paths
        and len(expected_freeze_paths) == 52,
        "start_and_freeze_commits_are_ancestors": _ancestor(START_COMMIT, head)
        and _ancestor(FREEZE_COMMIT, head),
        "claim_and_result_validate_as_single_go_attempt": claim[
            "single_catalog_and_single_48_response_batch_only"
        ]
        is True
        and result["decision"] == "go"
        and result["failure_code"] is None,
        "catalog_replay_selects_same_exact24_fresh_candidates": len(
            replay["target_keys"]
        )
        == 24
        and replay["target_keys"] == result["candidate_target_keys"]
        and replay["catalog_stats"]["selected_candidate_count"] == 24,
        "all48_response_files_exactly_bind_receipts": len(
            replay["response_vector"]
        )
        == 48
        and replay["response_binding_valid"] is True,
        "all24_two_page_targets_reparse_with_complete_coverage": len(
            replay["target_keys"]
        )
        == 24,
        "selector_replay_reconstructs_same_population": replay["private"][
            "population"
        ]
        == population,
        "private_population_payload_and_file_hash_valid": replay[
            "private_population_valid"
        ]
        is True,
        "selected_quartet_144_entities_8_pages_12_tasks_exact": len(
            population["target_keys"]
        )
        == 4
        and len(population["entities"]) == 144
        and len(population["pages"]) == 8
        and len(population["tasks"]) == 12
        and result["population"]["selected_target_keys"]
        == population["target_keys"],
        "provider_attempt_conservation_1_plus48": effects[
            "catalog_provider_attempt_count"
        ]
        == 1
        and effects["target_provider_attempt_count"] == 48
        and result["target_transport"]["successful_response_count"] == 48,
        "retry_redirect_refetch_resume_backfill_replacement_zero": effects[
            "redirect_retry_refetch_resume_backfill_replacement_count"
        ]
        == 0
        and all(
            row["redirect_retry_refetch_count"] == 0
            for row in result["target_transport"]["rows"]
        ),
        "model_search_evaluator_benchmark_effect_zero": effects[
            "model_search_evaluator_or_benchmark_effect_count"
        ]
        == 0,
        "shared_api_lease_released_after_v25305_owner": lease.get("owner")
        == "v25305_worldbank_population_freeze"
        and lease.get("active") is False
        and isinstance(lease.get("released_at_unix"), int),
        "active_population_processes_zero": active == [],
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "git_clean_head_equals_target_main": clean and head == target_main,
        "label_blind_and_entropy_signed_credit_zero": result[
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        ]
        is False
        and result["entropy_or_information_gain_assigns_signed_credit"] is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target_main,
            "clean": clean,
            "equal": head == target_main,
        },
        "fixed_inputs": _fixed(),
        "population": {
            "candidate_target_count": len(replay["target_keys"]),
            "candidate_target_keys_sha256": runner.payload_sha256(
                replay["target_keys"]
            ),
            "response_vector_sha256": replay["response_vector_sha256"],
            "selected_target_keys": population["target_keys"],
            "entity_count": len(population["entities"]),
            "entities_sha256": runner.payload_sha256(population["entities"]),
            "rendered_page_count": len(population["pages"]),
            "rendered_pages_sha256": runner.payload_sha256(population["pages"]),
            "task_count": len(population["tasks"]),
            "task_vector_sha256": runner.payload_sha256(population["tasks"]),
        },
        "effect_accounting": copy.deepcopy(effects),
        "lease_observation": lease,
        "active_processes": active,
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "v25305_retry_resume_refetch_backfill_replacement_or_second_population_freeze": False,
            "external_monotone_fill_mechanism_protocol_design": not findings,
            "external_monotone_fill_forward_or_postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
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
    population = copied.get("population") or {}
    effects = copied.get("effect_accounting") or {}
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in EXPECTED_FIXED.items()}
        or population.get("candidate_target_count") != 24
        or population.get("selected_target_keys")
        != [
            "fi.res.xgld.cd@2022",
            "sl.ind.empl.ma.zs@2022",
            "er.h2o.fwin.zs@2022",
            "sl.emp.totl.sp.zs@2022",
        ]
        or population.get("entity_count") != 144
        or population.get("rendered_page_count") != 8
        or population.get("task_count") != 12
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
        or copied.get("audit_valid") is not (not findings)
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "v25305_retry_resume_refetch_backfill_replacement_or_second_population_freeze": False,
            "external_monotone_fill_mechanism_protocol_design": not findings,
            "external_monotone_fill_forward_or_postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.08 World Bank population audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.53.08 audit failed: " + ", ".join(value["findings"]))
    runner.publish_json_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "audit_valid": True,
                "findings": [],
                "candidate_targets": value["population"]["candidate_target_count"],
                "selected_targets": value["population"]["selected_target_keys"],
                "entities": value["population"]["entity_count"],
                "tasks": value["population"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
