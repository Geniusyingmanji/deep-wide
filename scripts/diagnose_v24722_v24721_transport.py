#!/usr/bin/env python3
"""Content-free post-terminal diagnosis of the frozen V2.47.21 NO-GO."""

from __future__ import annotations

import hashlib
import json
import os
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

from scripts import v24721_worldbank_transport_gate as parent  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24722_v24721_transport_diagnosis_v1_{DATE}.json")
RESULT = parent.RESULT
DECISION = parent.DECISION
POSTAUDIT = parent.POSTAUDIT


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.22 expected object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result = parent.validate_result(_read(RESULT))
    decision = parent.validate_decision(_read(DECISION), result=result)
    audit = _read(POSTAUDIT)
    if (
        decision.get("status") != "transport_no_go"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("decision_status") != "transport_no_go"
        or audit.get("authorization", {}).get("additional_transport_retry_or_rerun")
        is not False
    ):
        raise RuntimeError("V2.47.22 frozen parent chain drifted")
    receipts = result["receipts"]
    primary = [
        item
        for item in receipts
        if item["representation"] == parent.PRIMARY_REPRESENTATION
    ]
    comparator = [
        item
        for item in receipts
        if item["representation"] == parent.COMPARATOR_REPRESENTATION
    ]
    primary_failure_targets = Counter(
        item["target_key"] for item in primary if not item["success"]
    )
    repeated_primary_failure_target_count = sum(
        count == parent.WAVES for count in primary_failure_targets.values()
    )
    intermittent_primary_failure_target_count = sum(
        0 < count < parent.WAVES for count in primary_failure_targets.values()
    )
    comparisons = result["dual_representation_comparisons"]
    value = {
        "artifact_version": 1,
        "role": "v24722_v24721_transport_postterminal_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result_sha256": _sha256(RESULT),
            "decision_sha256": _sha256(DECISION),
            "postresult_audit_sha256": _sha256(POSTAUDIT),
        },
        "transport": {
            "requests": len(receipts),
            "primary_requests": len(primary),
            "primary_successes": sum(item["success"] for item in primary),
            "primary_failures": sum(not item["success"] for item in primary),
            "primary_failure_type_counts": dict(
                sorted(
                    Counter(
                        str(item["failure_type"])
                        for item in primary
                        if not item["success"]
                    ).items()
                )
            ),
            "primary_failures_at_socket_wall": sum(
                not item["success"]
                and item["elapsed_seconds"] >= parent.SOCKET_TIMEOUT_SECONDS - 0.25
                for item in primary
            ),
            "repeated_primary_failure_target_count": repeated_primary_failure_target_count,
            "intermittent_primary_failure_target_count": intermittent_primary_failure_target_count,
            "comparator_requests": len(comparator),
            "comparator_successes": sum(item["success"] for item in comparator),
            "comparator_failures": sum(not item["success"] for item in comparator),
            "all_wave_walls_within_ceiling": result["checks"][
                "all_wave_walls_within_ceiling"
            ],
            "experiment_wall_within_ceiling": result["checks"][
                "experiment_wall_within_ceiling"
            ],
        },
        "representation": {
            "joint_success_comparisons": len(comparisons),
            "joint_common_value_mismatch_total": sum(
                item["common_value_mismatch_count"] for item in comparisons
            ),
            "joint_symmetric_difference_total": sum(
                item["symmetric_difference_count"] for item in comparisons
            ),
            "joint_comparisons_with_zero_common_value_mismatch": sum(
                item["common_value_mismatch_count"] == 0 for item in comparisons
            ),
            "joint_comparisons_with_five_code_domain_difference": sum(
                item["symmetric_difference_count"] == 5 for item in comparisons
            ),
            "bulk_record_count_set": sorted(
                {item["left_record_count"] for item in comparisons}
            ),
            "aggregate_record_count_set": sorted(
                {item["right_record_count"] for item in comparisons}
            ),
        },
        "diagnosis": {
            "primary_transport_is_not_reliable_enough": True,
            "bulk_comparator_is_candidate_for_fresh_population_gate": True,
            "common_domain_values_disagree": False,
            "full_domain_representation_equivalence_established": False,
            "same_population_retry_or_rerun_authorized": False,
            "benchmark_dev64_or_exact220_authorized": False,
            "next_requirement": "fresh_indicator_population_bulk_primary_with_explicit_semantic_domain_projection",
        },
        "source_policy": {
            "response_country_value_or_content_read": False,
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
            "same_population_retry_resume_or_selective_rerun": False,
        },
        "authorization": {
            "fresh_indicator_population_design": True,
            "same_population_transport_retry_or_rerun": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = parent.payload_sha256(value)
    validate_diagnosis(value)
    return value


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    transport = copied.get("transport", {})
    representation = copied.get("representation", {})
    if (
        copied.get("role")
        != "v24722_v24721_transport_postterminal_diagnosis"
        or copied.get("parents")
        != {
            "result_sha256": _sha256(RESULT),
            "decision_sha256": _sha256(DECISION),
            "postresult_audit_sha256": _sha256(POSTAUDIT),
        }
        or transport.get("requests") != parent.TOTAL_REQUESTS
        or transport.get("primary_requests") != parent.WAVES * len(parent.runtime.TARGETS)
        or transport.get("primary_successes") != 9
        or transport.get("primary_failures") != 3
        or transport.get("primary_failure_type_counts") != {"transport_error": 3}
        or transport.get("primary_failures_at_socket_wall") != 3
        or transport.get("repeated_primary_failure_target_count") != 1
        or transport.get("intermittent_primary_failure_target_count") != 1
        or transport.get("comparator_requests") != parent.WAVES * len(parent.runtime.TARGETS)
        or transport.get("comparator_successes") != 12
        or transport.get("comparator_failures") != 0
        or representation.get("joint_success_comparisons") != 9
        or representation.get("joint_common_value_mismatch_total") != 0
        or representation.get("joint_symmetric_difference_total") != 45
        or representation.get("joint_comparisons_with_zero_common_value_mismatch")
        != 9
        or representation.get("joint_comparisons_with_five_code_domain_difference")
        != 9
        or representation.get("bulk_record_count_set") != [265]
        or representation.get("aggregate_record_count_set") != [260]
        or copied.get("diagnosis", {}).get("same_population_retry_or_rerun_authorized")
        is not False
        or copied.get("diagnosis", {}).get("benchmark_dev64_or_exact220_authorized")
        is not False
        or any(copied.get("source_policy", {}).values())
        or copied.get("authorization")
        != {
            "fresh_indicator_population_design": True,
            "same_population_transport_retry_or_rerun": False,
            "benchmark_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        or seal != parent.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.22 diagnosis drifted")
    return copied


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    value = build_diagnosis()
    descriptor = os.open(
        ROOT / OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    main()
