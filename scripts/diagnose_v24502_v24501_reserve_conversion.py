#!/usr/bin/env python3
"""Content-free diagnosis of the V2.45.01 reserve conversion NO-GO.

The historical side reads only the frozen public result, decision and
post-result audit.  A separate synthetic matrix exercises the frozen
production projector with invented Alpha/Beta records.  Synthetic failures
are source-level counterexamples, never claims about the deleted task pages.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent.v24436_narrative_title_anchor_projection import (  # noqa: E402
    build_narrative_title_anchor_projection,
)
from scripts import v24501_reserve_external_gate as gate  # noqa: E402


RESULT = Path("results/v24501_reserve_external_result_v1_20260805.json")
DECISION = Path("results/v24501_reserve_external_decision_v1_20260805.json")
POSTAUDIT = Path(
    "results/v24501_reserve_external_postresult_audit_v1_20260805.json"
)
PROJECTOR = Path(
    "src/deepwide_agent/v24436_narrative_title_anchor_projection.py"
)
RESERVE = Path(
    "src/deepwide_agent/v24496_targeted_reserve_contradiction.py"
)
OUTPUT = Path(
    "results/v24502_v24501_reserve_conversion_diagnosis_v1_20260805.json"
)
SYNTHETIC_BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2024 |
| Beta | 2024 |
```"""
SYNTHETIC_CASES = (
    ("same_line_narrative", "Alpha was founded in 2025.", True),
    ("same_line_label_value", "Established: 2025", True),
    ("split_label_and_year", "Established\n2025", False),
    ("bare_year", "2025", False),
    ("visible_other_row_relation", "Beta was founded in 2025.", False),
    ("nonvisible_foreign_subject_relation", "Gamma was founded in 2025.", True),
)


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.45.02 nonordinary input: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.02 expected object")
    return value


def _synthetic_matrix() -> dict[str, bool]:
    output: dict[str, bool] = {}
    for ordinal, (name, content, _expected) in enumerate(SYNTHETIC_CASES, start=1):
        projection = build_narrative_title_anchor_projection(
            SYNTHETIC_BASELINE,
            [
                {
                    "host": f"synthetic-{ordinal}.example",
                    "title": "Alpha official history",
                    "content": content,
                    "fetch_integrity": True,
                }
            ],
        )
        output[name] = any(
            item["row_key"] == "Alpha" and item["value"] == "2025"
            for item in projection["observations"]
        )
    return output


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result = gate.validate_public_result(_read(RESULT))
    decision = _read(DECISION)
    postaudit = _read(POSTAUDIT)
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    timing = result["stage_timing_aggregate"]
    supervision = result["supervision_aggregate"]
    matrix = _synthetic_matrix()
    expected_matrix = {name: expected for name, _content, expected in SYNTHETIC_CASES}
    if (
        decision.get("status") != "fresh_targeted_external_no_go"
        or decision.get("passed") is not False
        or decision.get("authorization", {}).get("diagnostic_successor_design")
        is not True
        or decision.get("authorization", {}).get("fresh_paired_dev64_design")
        is not False
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
        or matrix != expected_matrix
    ):
        raise RuntimeError("V2.45.02 parent closure or synthetic matrix drifted")
    reliable = (
        result["reliability_passed"] is True
        and result["parent_validation_passed"] is True
        and result["latency_passed"] is True
        and observation["success_tasks"] == 8
        and timing["parent_success_tasks"] == 8
        and supervision["worker_success_tasks"] == 8
        and observation["slot_timeouts_lower_bound"] == 0
        and observation["provider_deadline_failures_lower_bound"] == 0
        and observation["hosted_search_deadline_failures_lower_bound"] == 0
        and observation["hard_fetch_deadline_failures_lower_bound"] == 0
        and observation["fetch_helper_failures_lower_bound"] == 0
    )
    conversion_boundary = (
        mechanism["reserve_engaged_tasks"] == 1
        and mechanism["reserve_usable_page_tasks"] == 1
        and mechanism["reserve_new_observation_tasks"] == 0
        and mechanism["safe_change_improvement_tasks"] == 0
        and mechanism["positive_decision_credit_gain_tasks"] == 0
        and mechanism["total_decision_credit_gain_nats"] == 0
    )
    value = {
        "artifact_version": 1,
        "role": "v24502_v24501_reserve_conversion_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(ROOT / RESULT)},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(ROOT / DECISION),
            },
            "postaudit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(ROOT / POSTAUDIT),
            },
        },
        "source_manifest": {
            str(PROJECTOR): sha256(ROOT / PROJECTOR),
            str(RESERVE): sha256(ROOT / RESERVE),
        },
        "observed_public_aggregate": {
            "selected": 8,
            "success_tasks": mechanism["success_tasks"],
            "target_plan_tasks": mechanism["target_plan_tasks"],
            "reserve_engaged_tasks": mechanism["reserve_engaged_tasks"],
            "reserve_selected_source_count": mechanism[
                "total_reserve_selected_source_count"
            ],
            "reserve_usable_page_count": mechanism[
                "total_reserve_usable_page_count"
            ],
            "reserve_new_observation_count": mechanism[
                "total_reserve_new_observation_count"
            ],
            "safe_change_improvement_tasks": mechanism[
                "safe_change_improvement_tasks"
            ],
            "positive_decision_credit_gain_tasks": mechanism[
                "positive_decision_credit_gain_tasks"
            ],
            "total_decision_credit_gain_nats": mechanism[
                "total_decision_credit_gain_nats"
            ],
            "batch_wall_seconds": result["batch_wall_seconds"],
            "reliability_parent_validation_and_latency_passed": reliable,
        },
        "historical_inferences": {
            "usable_reserve_page_failed_to_produce_target_bound_observation": conversion_boundary,
            "observed_failure_is_not_transport_provider_fetch_validation_or_latency": reliable,
            "historical_page_format_is_known": False,
            "split_label_year_caused_historical_failure_is_proven": False,
            "foreign_subject_misattribution_occurred_historically_is_proven": False,
            "specific_extractor_branch_caused_historical_failure_is_proven": False,
        },
        "synthetic_projector_matrix": matrix,
        "synthetic_source_findings": {
            "split_label_and_year_record_is_not_projected": not matrix[
                "split_label_and_year"
            ],
            "bare_year_remains_rejected": not matrix["bare_year"],
            "visible_other_row_relation_remains_rejected": not matrix[
                "visible_other_row_relation"
            ],
            "nonvisible_foreign_subject_can_be_title_misattributed": matrix[
                "nonvisible_foreign_subject_relation"
            ],
            "synthetic_counterexamples_are_not_historical_task_facts": True,
        },
        "diagnosis": "usable_page_to_target_bound_observation_is_the_observed_conversion_boundary",
        "source_policy": {
            "historical_task_question_identifier_query_url_page_prediction_candidate_private_result_opened": False,
            "temporary_execution_directory_opened": False,
            "benchmark_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
            "synthetic_alpha_beta_content_only": True,
        },
        "authorization": {
            "append_only_record_bound_projector_design": True,
            "same_population_rerun_retry_or_revaluation": False,
            "historical_task_specific_query_or_threshold_change": False,
            "new_external_probe_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_report(value)


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    observed = copied.get("observed_public_aggregate")
    historical = copied.get("historical_inferences")
    synthetic = copied.get("synthetic_source_findings")
    source = copied.get("source_policy")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24502_v24501_reserve_conversion_diagnosis"
        or not isinstance(observed, Mapping)
        or observed.get("selected") != 8
        or observed.get("success_tasks") != 8
        or observed.get("target_plan_tasks") != 1
        or observed.get("reserve_engaged_tasks") != 1
        or observed.get("reserve_selected_source_count") != 1
        or observed.get("reserve_usable_page_count") != 1
        or observed.get("reserve_new_observation_count") != 0
        or observed.get("safe_change_improvement_tasks") != 0
        or observed.get("positive_decision_credit_gain_tasks") != 0
        or observed.get("total_decision_credit_gain_nats") != 0
        or observed.get(
            "reliability_parent_validation_and_latency_passed"
        )
        is not True
        or not isinstance(historical, Mapping)
        or historical.get(
            "usable_reserve_page_failed_to_produce_target_bound_observation"
        )
        is not True
        or historical.get(
            "observed_failure_is_not_transport_provider_fetch_validation_or_latency"
        )
        is not True
        or any(
            historical.get(name) is not False
            for name in (
                "historical_page_format_is_known",
                "split_label_year_caused_historical_failure_is_proven",
                "foreign_subject_misattribution_occurred_historically_is_proven",
                "specific_extractor_branch_caused_historical_failure_is_proven",
            )
        )
        or not isinstance(synthetic, Mapping)
        or any(synthetic.get(name) is not True for name in synthetic)
        or copied.get("diagnosis")
        != "usable_page_to_target_bound_observation_is_the_observed_conversion_boundary"
        or not isinstance(source, Mapping)
        or source.get("synthetic_alpha_beta_content_only") is not True
        or any(
            source.get(name) is not False
            for name in source
            if name != "synthetic_alpha_beta_content_only"
        )
        or not isinstance(authorization, Mapping)
        or authorization.get("append_only_record_bound_projector_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "append_only_record_bound_projector_design"
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.45.02 diagnosis drifted")
    return copied


def main() -> None:
    value = build_report()
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({"path": str(OUTPUT), "diagnosis": value["diagnosis"]}))


if __name__ == "__main__":
    main()
