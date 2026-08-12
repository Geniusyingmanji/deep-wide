#!/usr/bin/env python3
"""Content-free diagnosis of the invalid V2.52.03 quality evaluation."""

from __future__ import annotations

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

from deepwide_agent import v25204_cran_dcf_parser as parser  # noqa: E402
from deepwide_agent import v25203_post_effect_tolerant_quality_contract as contract  # noqa: E402
from scripts import evaluate_v25203_post_effect_tolerant_quality as evaluator  # noqa: E402


OUTPUT = Path("results/v25205_v25203_evaluator_invalid_diagnosis_v1_20260812.json")


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    snapshot = evaluator.validate_gold_snapshot(
        json.loads((ROOT / contract.POSTFREEZE_GOLD).read_text(encoding="utf-8"))
    )
    result = evaluator.validate_result(
        json.loads((ROOT / contract.RESULT).read_text(encoding="utf-8"))
    )
    synthetic = (
        "Package: unrelated\nVersion: 1\nLicense_is_FOSS: yes\n\n"
        "Package: selected\nVersion: 2\nLicense: GPL-2 | GPL-3\n"
        "NeedsCompilation: yes\n"
    )
    old_rejected = False
    try:
        evaluator.parse_dcf_records(synthetic)
    except ValueError:
        old_rejected = True
    records, observation = parser.parse_with_observation(synthetic)
    checks = {
        "quality_result_is_not_a_valid_model_quality_measurement": snapshot[
            "valid_rows"
        ]
        == 0
        and all(
            arm["evaluator_valid"] == 0
            and arm["evaluator_invalid_or_not_run"] == contract.TASK_COUNT
            for arm in result["metrics"]["arms"].values()
        ),
        "network_or_parse_root_cause_is_not_observable_from_frozen_snapshot": snapshot[
            "http_status"
        ]
        == 0
        and snapshot["response_bytes"] == 0
        and snapshot["decompressed_bytes"] == 0,
        "old_parser_rejects_valid_cran_underscore_field_synthetically": old_rejected,
        "successor_parser_accepts_same_valid_cran_shape": len(records) == 2
        and observation["parse_completed"] is True
        and observation["record_count"] == 2,
        "same_population_refetch_or_revaluation_forbidden": result["authorization"][
            "retry_refetch_selective_revaluation"
        ]
        is False,
        "deepwidebench_and_sota_authority_withheld": result["authorization"][
            "deepwidebench_exact220_launch_now"
        ]
        is False
        and result["authorization"]["leaderboard_or_sota"] is False,
        "entropy_information_gain_signed_credit_not_validated": result[
            "claim_scope"
        ]["entropy_or_information_gain_credit_validated"]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25205_v25203_evaluator_invalid_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "gold_snapshot_sha256": contract.sha256(ROOT / contract.POSTFREEZE_GOLD),
            "quality_result_sha256": contract.sha256(ROOT / contract.RESULT),
            "old_evaluator_sha256": contract.sha256(ROOT / contract.EVALUATOR),
            "successor_parser_sha256": contract.sha256(
                ROOT / "src/deepwide_agent/v25204_cran_dcf_parser.py"
            ),
        },
        "diagnosis": {
            "v25203_mechanism_gate_remains_valid": True,
            "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go": True,
            "actual_failed_stage_is_unidentified_due_to_catch_all": True,
            "old_parser_has_independent_reproducible_cran_key_grammar_bug": True,
            "old_parser_bug_is_plausible_but_not_proven_unique_cause_of_network_run": True,
            "successor_requires_finite_stage_observation_and_fresh_population": True,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "frozen_gold_rows_and_quality_aggregate_opened_read_only_for_validation": True,
            "frozen_package_and_value_content_persisted_or_emitted_by_diagnosis": False,
            "prediction_question_or_raw_response_bytes_opened_or_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "mapping_category_question_type_split_score_reward_or_historical_correctness_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "fresh_disjoint_quality_successor_design": not findings,
            "same_population_refetch_revalue_retry_resume_or_replacement": False,
            "deepwidebench_exact220_leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "diagnosis_payload_sha256")


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected_source_policy = {
        "frozen_gold_rows_and_quality_aggregate_opened_read_only_for_validation": True,
        "frozen_package_and_value_content_persisted_or_emitted_by_diagnosis": False,
        "prediction_question_or_raw_response_bytes_opened_or_emitted": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "mapping_category_question_type_split_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    if (
        copied.get("role") != "v25205_v25203_evaluator_invalid_diagnosis"
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not copied.get("checks")
        or not all(copied["checks"].values())
        or copied.get("diagnosis", {}).get(
            "v25203_quality_outcome_is_evaluator_invalid_not_model_no_go"
        )
        is not True
        or copied.get("diagnosis", {}).get(
            "old_parser_bug_is_plausible_but_not_proven_unique_cause_of_network_run"
        )
        is not True
        or copied.get("source_policy") != expected_source_policy
        or copied.get("authorization")
        != {
            "fresh_disjoint_quality_successor_design": True,
            "same_population_refetch_revalue_retry_resume_or_replacement": False,
            "deepwidebench_exact220_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.52.05 evaluator-invalid diagnosis drifted")
    return copied


def main() -> None:
    value = validate_diagnosis(build_diagnosis())
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(OUTPUT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
