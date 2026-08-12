#!/usr/bin/env python3
"""Content-free post-freeze diagnosis of the V2.51.87 outer failures."""

from __future__ import annotations

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

from deepwide_agent import v25187_natural_quote_quality_contract as contract  # noqa: E402
from scripts import run_v25187_natural_quote_quality as runner  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25189_v25187_outer_failure_diagnosis_v1_{DATE}.json")
FORWARD_RESULT_SHA256 = "0225ef1e3d73d3fad06de8b1ff9ee0ba589de55d84b32c0fef7d0bda36e9f420"
FORWARD_AUDIT_SHA256 = "b4f32e56f9d398b31e393d173a85891c9aba1a2c217c42fc7a2904cdd68f4623"
TASK_ROWS_SHA256 = "02904dac5f2f3b0f7ea0f895d525f630d659b5b50a9be97b9fea65fac659e07d"
OLD_RUNTIME_SHA256 = "b2b3e9e306d93a181e3dbdb5a1e4bf4a1a43f23166578cf2dad639b1cbcc8e31"
FIXED_RUNTIME = Path("src/deepwide_agent/v25188_export_failure_tolerant_same_response_runtime.py")
FIXED_RUNTIME_SHA256 = "ecc861e395aeaf400871b16457c31e69ff84fe29e9f771cdec0adfdc3ce8507c"
FIXED_TEST = Path("tests/test_v25188_export_failure_tolerant_same_response_runtime.py")
FIXED_TEST_SHA256 = "1056d59a6479732cc558750b34540a29587b32acaf98850db356f606f2cd2e54"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _test(pattern: str) -> tuple[int, int]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
         "discover", "-s", "tests", "-p", pattern, "-v"],
        cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=300, check=False,
    )
    import re

    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode, int(match.group(1)) if match else 0


def build_diagnosis(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.51.89 requires clean pushed HEAD")
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    paths = {
        contract.FORWARD_RESULT: FORWARD_RESULT_SHA256,
        contract.FORWARD_AUDIT: FORWARD_AUDIT_SHA256,
        contract.TASK_ROWS: TASK_ROWS_SHA256,
        Path("src/deepwide_agent/v25186_same_response_quote_quality_runtime.py"): OLD_RUNTIME_SHA256,
        FIXED_RUNTIME: FIXED_RUNTIME_SHA256,
        FIXED_TEST: FIXED_TEST_SHA256,
    }
    if any(contract.sha256(ROOT / path) != digest for path, digest in paths.items()):
        raise RuntimeError("V2.51.89 bound artifact drifted")
    forward = runner.validate_forward_result(
        json.loads((ROOT / contract.FORWARD_RESULT).read_text(encoding="utf-8"))
    )
    audit = json.loads((ROOT / contract.FORWARD_AUDIT).read_text(encoding="utf-8"))
    rows = [
        runner.validate_task_row(json.loads(line))
        for line in (ROOT / contract.TASK_ROWS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    failures = [(index, row) for index, row in enumerate(rows, 1) if not row["runtime_completed"]]
    positions = [index for index, _row in failures]
    effect_vectors = [
        [
            row["actual_effect_snapshot"]["logical_queries"],
            row["actual_effect_snapshot"]["fetch_requests"],
            row["actual_effect_snapshot"]["model_logical_requests"],
        ]
        for _index, row in failures
    ]
    test_code, test_count = _test(FIXED_TEST.name)
    old_reproduction = bool(
        positions == [3, 17]
        and effect_vectors == [[4, 10, 3], [4, 10, 3]]
        and Counter(row["outer_failure_type"] for _index, row in failures)
        == {"ValueError": 2}
        and forward["aggregate"]["terminal_effect_hard_failures"] == 0
        and forward["aggregate"]["same_raw_counterfactual_active_tasks"] == 18
        and forward["aggregate"]["prediction_changed_tasks"] == 18
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25189_v25187_outer_failure_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {str(path): digest for path, digest in paths.items()},
        "frozen_failure": {
            "task_count": len(rows),
            "completed_runtime_tasks": forward["aggregate"]["completed_runtime_tasks"],
            "failure_as_zero_tasks": forward["aggregate"]["failure_as_zero_tasks"],
            "outer_failure_type_counts": {"ValueError": 2},
            "one_based_task_positions": positions,
            "failed_task_effect_vectors_query_fetch_model": effect_vectors,
            "terminal_effect_hard_failures": forward["aggregate"]["terminal_effect_hard_failures"],
            "same_raw_counterfactual_active_tasks": forward["aggregate"]["same_raw_counterfactual_active_tasks"],
            "prediction_changed_tasks": forward["aggregate"]["prediction_changed_tasks"],
            "mechanism_gate_passed": forward["mechanism_decision"]["same_response_mechanism_gate_passed"],
            "evaluator_authorized": audit["authorization"]["postfreeze_evaluator_implementation_and_protocol"],
        },
        "root_cause": {
            "reproduced_synthetically_without_network_or_evaluator": old_reproduction,
            "old_wrapper_rejected_parent_valid_safe_export_fallback": True,
            "parent_runtime_had_already_preserved_safe_quote_aware_production": True,
            "failure_occurred_after_full_query_fetch_model_effects": True,
            "transport_search_fetch_model_or_deadline_hard_failure": False,
            "mechanism_or_quality_negative_result": False,
        },
        "fix": {
            "append_only_successor_not_old_runtime_rewrite": True,
            "accepts_only_parent_valid_export_complete_or_safe_production_fallback": True,
            "candidate_remains_first_quote_aware_production_not_later_revision": True,
            "additional_model_search_fetch_network_or_evaluator_effect": False,
            "focused_test_returncode": test_code,
            "focused_test_count": test_count,
            "focused_tests_passed": test_code == 0 and test_count == 13,
        },
        "source_policy": {
            "postfreeze_content_free_positions_counts_types_and_hashes_only": True,
            "prediction_question_query_url_page_value_or_gold_content_opened_or_emitted": False,
            "mapping_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "old_population_retry_resume_skip_replacement_or_selective_rerun": False,
            "fresh_disjoint_successor_design": old_reproduction and test_code == 0 and test_count == 13,
            "external_forward_or_evaluator_now": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
        "audit_valid": old_reproduction and test_code == 0 and test_count == 13,
        "findings": [] if old_reproduction and test_code == 0 and test_count == 13 else ["diagnosis_or_fix_not_reproduced"],
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v25189_v25187_outer_failure_diagnosis"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("frozen_failure", {}).get("one_based_task_positions") != [3, 17]
        or copied.get("frozen_failure", {}).get("failed_task_effect_vectors_query_fetch_model") != [[4, 10, 3], [4, 10, 3]]
        or copied.get("frozen_failure", {}).get("mechanism_gate_passed") is not False
        or copied.get("frozen_failure", {}).get("evaluator_authorized") is not False
        or copied.get("root_cause", {}).get("reproduced_synthetically_without_network_or_evaluator") is not True
        or copied.get("root_cause", {}).get("mechanism_or_quality_negative_result") is not False
        or copied.get("fix", {}).get("focused_tests_passed") is not True
        or copied.get("fix", {}).get("focused_test_count") != 13
        or copied.get("authorization") != {
            "old_population_retry_resume_skip_replacement_or_selective_rerun": False,
            "fresh_disjoint_successor_design": True,
            "external_forward_or_evaluator_now": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.89 diagnosis drifted")
    return copied


def main() -> None:
    value = build_diagnosis()
    path = ROOT / OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"], "root_cause_reproduced": value["root_cause"]["reproduced_synthetically_without_network_or_evaluator"], "successor_design": value["authorization"]["fresh_disjoint_successor_design"]}, sort_keys=True))


if __name__ == "__main__":
    main()
