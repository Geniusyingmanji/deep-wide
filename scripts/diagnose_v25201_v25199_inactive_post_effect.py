#!/usr/bin/env python3
"""Content-free diagnosis of the V2.51.99 inactive post-effect failure."""

from __future__ import annotations

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

from deepwide_agent import (  # noqa: E402
    v25199_invariant_observable_quality_contract as parent_contract,
)
from deepwide_agent import (  # noqa: E402
    v25200_post_effect_tolerant_vertical_receipt as fix,
)
from scripts import run_v25199_invariant_observable_quality as parent_runner  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25201_v25199_inactive_post_effect_diagnosis_v1_{DATE}.json")
FORWARD_RESULT_SHA256 = "77c14119844a633d7edebf97d3dc0b5234d9f5eb424936ad7777ebf98d3a8cff"
FORWARD_AUDIT_SHA256 = "dd6b692691de25e71401de0eec60f311561b3e45ce0f38870441074ea435d30c"
INVARIANT_AGGREGATE_SHA256 = "8b9ce3dba56b641c6a2b7cc2df0f77be3f73dfbdfecb09c7d3ab9f2f6ea944ad"
FIX_SHA256 = "7dada08c77d1116eb104c8d3b05620b269f33524facc217e1312262d1391378c"
TEST_SHA256 = "9cb073a1fc9ab13d4c0618878df38e71b99a32498ba811ec584b8e3c5ab6135f"
TEST = Path("tests/test_v25200_post_effect_tolerant_vertical_receipt.py")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _test() -> tuple[int, int]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            TEST.name,
            "-v",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    import re

    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode, int(match.group(1)) if match else 0


def build_diagnosis(
    *,
    now: int | None = None,
    require_clean: bool = True,
    focused_test_result: tuple[int, int] | None = None,
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.52.01 requires clean pushed HEAD")
    paths = {
        parent_contract.FORWARD_RESULT: FORWARD_RESULT_SHA256,
        parent_contract.FORWARD_AUDIT: FORWARD_AUDIT_SHA256,
        parent_contract.INVARIANT_OBSERVATION_AGGREGATE: INVARIANT_AGGREGATE_SHA256,
        Path("src/deepwide_agent/v25200_post_effect_tolerant_vertical_receipt.py"): FIX_SHA256,
        TEST: TEST_SHA256,
    }
    if any(parent_contract.sha256(ROOT / path) != digest for path, digest in paths.items()):
        raise RuntimeError("V2.52.01 bound artifact drifted")
    forward = parent_runner.validate_forward_result(
        json.loads((ROOT / parent_contract.FORWARD_RESULT).read_text(encoding="utf-8"))
    )
    audit = json.loads((ROOT / parent_contract.FORWARD_AUDIT).read_text(encoding="utf-8"))
    invariant = parent_runner.validate_invariant_observation_aggregate(
        json.loads(
            (ROOT / parent_contract.INVARIANT_OBSERVATION_AGGREGATE).read_text(
                encoding="utf-8"
            )
        )
    )
    test_code, test_count = focused_test_result or _test()
    exact_observation = bool(
        forward["aggregate"]["failure_as_zero_tasks"] == 1
        and forward["aggregate"]["outer_failure_stage_counts"]
        == {"runtime": 1, "conversion": 0, "row_validation": 0}
        and forward["aggregate"]["outer_failure_code_counts"]
        == {"v25158_receipt_validation": 1}
        and invariant["v25158_receipt_failure_tasks"] == 1
        and invariant["v25158_invariant_observed_failure_tasks"] == 1
        and invariant["v25158_invariant_observer_missing_tasks"] == 0
        and invariant["violation_code_counts"] == {"inactive_dynamic_zero": 1}
        and audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit.get("authorization", {}).get(
            "postfreeze_evaluator_implementation_and_protocol"
        )
        is False
    )
    static_uniqueness = bool(
        exact_observation
        and test_code == 0
        and test_count == 21
        and fix.SAFE_STATE_CODE == "inactive_parent_post_effect_failure_only"
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25201_v25199_inactive_post_effect_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {str(path): digest for path, digest in paths.items()},
        "frozen_failure": {
            "task_count": forward["aggregate"]["task_count"],
            "completed_runtime_tasks": forward["aggregate"]["completed_runtime_tasks"],
            "failure_as_zero_tasks": forward["aggregate"]["failure_as_zero_tasks"],
            "outer_failure_stage_counts": forward["aggregate"]["outer_failure_stage_counts"],
            "outer_failure_code_counts": forward["aggregate"]["outer_failure_code_counts"],
            "invariant_violation_code_counts": invariant["violation_code_counts"],
            "mechanism_gate_passed": forward["mechanism_decision"]["same_response_mechanism_gate_passed"],
            "evaluator_authorized": audit["authorization"]["postfreeze_evaluator_implementation_and_protocol"],
        },
        "root_cause": {
            "invariant_observation_complete": exact_observation,
            "inactive_dynamic_zero_has_one_static_parent_post_effect_explanation": static_uniqueness,
            "candidate_selector_projection_provider_and_revision_dynamics_require_candidate_entry": True,
            "candidate_entry_was_zero_under_the_observed_violation": True,
            "independent_parent_post_effect_failure_can_precede_candidate_entry": True,
            "frozen_v25158_validator_incorrectly_required_parent_post_effect_false_when_candidate_inactive": True,
            "transport_search_fetch_model_or_deadline_hard_failure": False,
            "mechanism_or_quality_negative_result": False,
        },
        "fix": {
            "append_only_successor_not_frozen_validator_rewrite": True,
            "frozen_validator_called_before_compatibility": True,
            "surrogate_changes_only_parent_post_effect_flag_and_must_pass_frozen_validator": True,
            "original_receipt_returned_byte_identical": True,
            "candidate_count_dynamic_prediction_effect_budget_or_credit_changed": False,
            "focused_test_returncode": test_code,
            "focused_test_count": test_count,
            "focused_tests_passed": test_code == 0 and test_count == 21,
        },
        "source_policy": {
            "content_free_aggregate_codes_hashes_and_static_source_logic_only": True,
            "prediction_question_query_url_page_identity_key_value_or_gold_content_opened_or_emitted": False,
            "mapping_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "old_population_retry_resume_skip_replacement_or_selective_rerun": False,
            "fresh_disjoint_successor_design": static_uniqueness,
            "external_forward_or_evaluator_now": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
        "audit_valid": static_uniqueness,
        "findings": [] if static_uniqueness else ["diagnosis_or_fix_not_reproduced"],
    }
    value["diagnosis_payload_sha256"] = parent_contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v25201_v25199_inactive_post_effect_diagnosis"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("frozen_failure", {}).get("failure_as_zero_tasks") != 1
        or copied.get("frozen_failure", {}).get("outer_failure_code_counts")
        != {"v25158_receipt_validation": 1}
        or copied.get("frozen_failure", {}).get("invariant_violation_code_counts")
        != {"inactive_dynamic_zero": 1}
        or copied.get("root_cause", {}).get(
            "inactive_dynamic_zero_has_one_static_parent_post_effect_explanation"
        )
        is not True
        or copied.get("fix", {}).get("focused_tests_passed") is not True
        or copied.get("fix", {}).get("focused_test_count") != 21
        or copied.get("authorization")
        != {
            "old_population_retry_resume_skip_replacement_or_selective_rerun": False,
            "fresh_disjoint_successor_design": True,
            "external_forward_or_evaluator_now": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != parent_contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.52.01 diagnosis drifted")
    return copied


def main() -> None:
    value = build_diagnosis()
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "root_cause": value["root_cause"][
                    "inactive_dynamic_zero_has_one_static_parent_post_effect_explanation"
                ],
                "successor_design": value["authorization"][
                    "fresh_disjoint_successor_design"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
