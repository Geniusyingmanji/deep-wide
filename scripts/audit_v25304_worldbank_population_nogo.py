#!/usr/bin/env python3
"""Post-attempt audit for the pre-provider V2.53.01 population NO-GO."""

from __future__ import annotations

import copy
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
ROLE = "v25304_worldbank_population_preprovider_nogo_audit"
OUTPUT = runner.POSTFREEZE_AUDIT
SOURCE = Path("scripts/audit_v25304_worldbank_population_nogo.py")
TEST = Path("tests/test_audit_v25304_worldbank_population_nogo.py")
EXECUTION_COMMIT = "3c5a7971393189d008a3c86c486c54cf719bc24e"
RESULT_COMMIT = "0639153e4a1bf24dee21d626d438273ebf81654c"
EXPECTED_FIXED = {
    runner.EXECUTION_START: "35325aaae282b95ff8de418dac32194a679577ac7e272be6383c73526be97f64",
    runner.ATTEMPT_CLAIM: "d874e3e92b0a29fd272c7c94c5a31306a3f9c449e3c700bad252c5aee467b181",
    runner.RESULT: "488f8096e2eb44ad22bb73ffaceff0d21d9ee3cf4ecfc4a6cbff39f2d0e2ef60",
    runner.PREACTIVATION: "6c5c4aa06bcee850f13523d62081274dd885fc22f0994ec8b77178ea56d2acb1",
    runner.SOURCE: "1430b366c97d2b9d96624fce8b0621094c8b250fed7f4dac0f401eea72766f99",
    runner.HELPER: "a8049e892669d17bcc940f0c13b029207aa68d8f6677552ab7a5347f19c88ce4",
    runner.TEST: "d3c71b07b6419d66e512a7eaf39013b3a0678a726fd6548ad8282c4990be4214",
    runner.REVOCATION: runner.REVOCATION_SHA256,
}
EXPECTED_WATCHERS = {
    str(row["pid"]): row["start_ticks"] for row in runner.EXPECTED_WATCHERS
}
CHECK_NAMES = frozenset(
    {
        "fixed_start_claim_result_preactivation_sources_and_revocation_exact",
        "execution_and_result_commits_are_ancestors",
        "claim_valid_and_permanent",
        "result_valid_fixed_no_go",
        "catalog_and_target_provider_attempts_zero",
        "network_model_search_evaluator_benchmark_effects_zero",
        "retry_resume_refetch_backfill_replacement_zero",
        "catalog_target_raw_bytes_and_population_output_absent",
        "shared_api_lease_released_after_v25301_owner",
        "active_v25301_processes_zero",
        "protected_watchers_unchanged",
        "git_clean_head_equals_target_main",
        "label_blind_and_entropy_signed_credit_zero",
    }
)


def _fixed() -> dict[str, str]:
    return {str(path): base.sha256(path) for path in EXPECTED_FIXED}


def _ancestor(commit: str, head: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, head],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


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
                "v25301_worldbank_population",
                "run_v25297_worldbank_population_freeze.py",
                "v25297_worldbank_get_helper.py",
            )
        )
        and "audit_v25304_worldbank_population_nogo.py" not in line
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    head = base._git("rev-parse", "HEAD")
    target = base._git("rev-parse", "target/main")
    clean = not base._git("status", "--porcelain")
    claim = runner.validate_attempt_claim(
        json.loads(base._ordinary(runner.ATTEMPT_CLAIM).read_text(encoding="utf-8"))
    )
    result = runner.validate_result(
        json.loads(base._ordinary(runner.RESULT).read_text(encoding="utf-8"))
    )
    effects = result["effect_accounting"]
    catalog = result["catalog"]
    transport = result["target_transport"]
    population = result["population"]
    lease = _lease_observation()
    active = _active_processes()
    watchers = base._watchers()
    output_absent = not (ROOT / runner.OUTPUT_ROOT).exists() and not (
        ROOT / runner.OUTPUT_ROOT
    ).is_symlink()
    checks = {
        "fixed_start_claim_result_preactivation_sources_and_revocation_exact": _fixed()
        == {str(path): digest for path, digest in EXPECTED_FIXED.items()},
        "execution_and_result_commits_are_ancestors": _ancestor(EXECUTION_COMMIT, head)
        and _ancestor(RESULT_COMMIT, head),
        "claim_valid_and_permanent": claim["claim_is_permanent_even_on_crash_or_no_go"]
        is True
        and claim["retry_resume_backfill_replacement_or_second_attempt"] is False,
        "result_valid_fixed_no_go": result["decision"] == "no_go"
        and result["failure_code"]
        == "local_helper_supervisor_value_error_pre_provider",
        "catalog_and_target_provider_attempts_zero": effects[
            "catalog_provider_attempt_count"
        ]
        == 0
        and effects["target_provider_attempt_count"] == 0
        and catalog["provider_attempt_count"] == 0
        and transport["provider_attempt_count"] == 0,
        "network_model_search_evaluator_benchmark_effects_zero": effects[
            "public_worldbank_network_or_api_called"
        ]
        is False
        and effects["model_search_evaluator_or_benchmark_effect_count"] == 0,
        "retry_resume_refetch_backfill_replacement_zero": effects[
            "redirect_retry_refetch_resume_backfill_replacement_count"
        ]
        == 0,
        "catalog_target_raw_bytes_and_population_output_absent": output_absent
        and catalog["response_bytes"] == 0
        and catalog["response_sha256"] is None
        and transport["rows"] == []
        and transport["successful_response_count"] == 0
        and population["private_path"] is None
        and population["selected_target_count"] == 0
        and population["task_count"] == 0,
        "shared_api_lease_released_after_v25301_owner": lease.get("owner")
        == "v25301_worldbank_population_freeze"
        and lease.get("active") is False
        and isinstance(lease.get("released_at_unix"), int),
        "active_v25301_processes_zero": active == [],
        "protected_watchers_unchanged": _watchers_exact(watchers),
        "git_clean_head_equals_target_main": clean and head == target,
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
        "git": {"head": head, "target_main": target, "clean": clean, "equal": head == target},
        "fixed_inputs": _fixed(),
        "attempt": {
            "claim_sha256": EXPECTED_FIXED[runner.ATTEMPT_CLAIM],
            "result_sha256": EXPECTED_FIXED[runner.RESULT],
            "decision": result["decision"],
            "failure_code": result["failure_code"],
            "catalog_provider_attempt_count": effects["catalog_provider_attempt_count"],
            "target_provider_attempt_count": effects["target_provider_attempt_count"],
            "public_worldbank_network_or_api_called": effects[
                "public_worldbank_network_or_api_called"
            ],
            "output_root_exists": not output_absent,
        },
        "lease_observation": lease,
        "active_processes": active,
        "protected_watchers": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "v25301_retry_resume_reuse_or_population_recovery": False,
            "successor_helper_supervisor_repair_build_only": not findings,
            "successor_population_freeze_or_external_forward": False,
            "postfreeze_evaluator": False,
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
    authorization = copied.get("authorization") or {}
    expected_findings = sorted(name for name, passed in checks.items() if not passed)
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_inputs")
        != {str(path): digest for path, digest in EXPECTED_FIXED.items()}
        or copied.get("attempt")
        != {
            "claim_sha256": EXPECTED_FIXED[runner.ATTEMPT_CLAIM],
            "result_sha256": EXPECTED_FIXED[runner.RESULT],
            "decision": "no_go",
            "failure_code": "local_helper_supervisor_value_error_pre_provider",
            "catalog_provider_attempt_count": 0,
            "target_provider_attempt_count": 0,
            "public_worldbank_network_or_api_called": False,
            "output_root_exists": False,
        }
        or not isinstance(copied.get("active_processes"), list)
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
            "v25301_retry_resume_reuse_or_population_recovery": False,
            "successor_helper_supervisor_repair_build_only": not findings,
            "successor_population_freeze_or_external_forward": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or signature != runner.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.04 population NO-GO audit drifted")
    return copied


def main() -> None:
    value = build_audit()
    if not value["audit_valid"]:
        raise SystemExit("V2.53.04 audit failed: " + ", ".join(value["findings"]))
    runner.publish_json_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "audit_valid": True,
                "findings": [],
                "catalog_provider_attempts": 0,
                "target_provider_attempts": 0,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
