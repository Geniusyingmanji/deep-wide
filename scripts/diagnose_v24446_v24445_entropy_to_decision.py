#!/usr/bin/env python3
"""Content-free diagnosis of the V2.44.45 mechanism NO-GO.

The frozen result proves that serialized-envelope validation is repaired and
that narrative evidence creates positive epistemic credit.  It does not prove
why no selected target crossed the unchanged safe-change gate, because the
public projection intentionally omits per-target posterior values.  This
diagnosis separates what is proved from what remains unmeasured and freezes a
bounded successor work order without authorizing another run.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent.v24388_uncertainty_credit import (  # noqa: E402
    KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    MINIMUM_ALTERNATIVE_POSTERIOR,
    UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
)
from deepwide_agent.v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    MAXIMUM_ACTIVE_SOURCES,
)
from scripts import v24445_serialized_narrative_external_gate as gate  # noqa: E402


DATE = "20260804"
DIAGNOSIS = Path(
    f"results/v24446_v24445_entropy_to_decision_diagnosis_v1_{DATE}.json"
)
RESULT = gate.RESULT
DECISION = gate.DECISION
POSTAUDIT = gate.POSTAUDIT


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.44.46 expected object")
    return value


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result = gate.validate_public_result(_read(RESULT))
    decision = gate.validate_decision(ROOT, value=_read(DECISION))
    postaudit = gate.validate_postaudit(ROOT, value=_read(POSTAUDIT))
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    failed_checks = sorted(
        name for name, passed in mechanism["checks"].items() if not passed
    )
    if (
        result.get("diagnostic_complete") is not True
        or result.get("mechanism_passed") is not False
        or result.get("passed") is not False
        or decision.get("status")
        != "fresh_serialized_narrative_external_diagnostic_complete_mechanism_no_go"
        or decision.get("diagnostic_route") != "entropy_to_decision_successor"
        or failed_checks
        != [
            "batch_wall_within_ceiling",
            "narrative_positive_decision_credit",
            "narrative_safe_change_tasks",
        ]
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
    ):
        raise RuntimeError("V2.44.46 parent closure drifted")
    value = {
        "artifact_version": 1,
        "role": "v24446_v24445_entropy_to_decision_diagnosis",
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
        "wire_repair_evidence": {
            "selected": int(result["selected"]),
            "parent_success_tasks": int(observation["success_tasks"]),
            "parent_failure_tasks": int(observation["failure_tasks"]),
            "result_envelope_invalid_tasks": int(
                observation["parent_taxonomy_counts"].get(
                    "result_envelope_invalid", 0
                )
            ),
            "child_result_envelopes_written": int(
                observation["child_stage_counts"].get(
                    "result_envelope_written", 0
                )
            ),
            "diagnostic_complete": bool(result["diagnostic_complete"]),
        },
        "entropy_to_decision_evidence": {
            "narrative_projection_tasks": int(
                mechanism["narrative_projection_tasks"]
            ),
            "narrative_novel_observation_tasks": int(
                mechanism["narrative_novel_observation_tasks"]
            ),
            "narrative_positive_epistemic_tasks": int(
                mechanism["narrative_positive_epistemic_tasks"]
            ),
            "narrative_positive_epistemic_target_count": int(
                mechanism["narrative_positive_epistemic_target_count"]
            ),
            "narrative_epistemic_credit_total_nats": float(
                mechanism["narrative_epistemic_credit_total_nats"]
            ),
            "narrative_candidate_changed_cell_count": int(
                mechanism["narrative_candidate_changed_cell_count"]
            ),
            "narrative_safe_change_count": int(
                mechanism["narrative_safe_change_count"]
            ),
            "narrative_decision_credit_total_nats": float(
                mechanism["narrative_decision_credit_total_nats"]
            ),
            "known_baseline_minimum_support_sources": KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
            "unknown_baseline_minimum_support_sources": UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
            "minimum_alternative_posterior": MINIMUM_ALTERNATIVE_POSTERIOR,
            "required_support_margin": 1,
            "current_active_source_cap": MAXIMUM_ACTIVE_SOURCES,
            "active_source_cap_alone_cannot_supply_known_baseline_minimum": (
                MAXIMUM_ACTIVE_SOURCES < KNOWN_ALTERNATIVE_MINIMUM_SOURCES
            ),
            "candidate_change_is_not_equivalent_to_safe_entropy_resolution": True,
            "per_target_threshold_failure_partition_available": False,
            "third_source_alone_proven_sufficient": False,
        },
        "latency_evidence": {
            "batch_wall_seconds": float(mechanism["batch_wall_seconds"]),
            "batch_wall_ceiling_seconds": float(
                gate.GATES["maximum_batch_wall_seconds"]
            ),
            "model_requests": int(mechanism["model_requests"]),
            "model_attempts": int(mechanism["model_attempts"]),
            "model_slot_cap": int(result["model_slot_cap"]),
            "slot_total_wait_seconds": float(mechanism["slot_total_wait_seconds"]),
            "slot_max_wait_seconds": float(mechanism["slot_max_wait_seconds"]),
            "slot_timeouts": int(mechanism["slot_timeouts"]),
            "provider_deadline_failures": int(
                mechanism["provider_deadline_failures"]
            ),
            "hosted_search_attempts": int(mechanism["hosted_search_attempts"]),
            "hard_fetch_helper_calls": int(mechanism["hard_fetch_helper_calls"]),
            "post_child_validation_wall_seconds_available": False,
            "model_provider_wall_seconds_available": False,
            "search_provider_wall_seconds_available": False,
            "fetch_wall_seconds_available": False,
            "replay_is_only_latency_cause_proven": False,
            "provider_is_only_latency_cause_proven": False,
        },
        "successor_work_order": {
            "preserve_safe_change_thresholds": True,
            "preserve_runtime_boundary_exactly_opaque_id_and_question": True,
            "allow_at_most_one_additional_active_source": True,
            "additional_logical_query_or_search_batch": 0,
            "additional_model_request": 0,
            "additional_fetch_target_cap": 1,
            "total_fetch_target_cap": 11,
            "active_source_cap": 3,
            "require_source_disjointness": True,
            "publish_counts_only_threshold_failure_partition": True,
            "threshold_partition_fields": [
                "insufficient_support_count",
                "no_active_support_count",
                "posterior_below_threshold_count",
                "support_margin_below_threshold_count",
                "safe_change_count",
            ],
            "single_complete_envelope_and_cross_artifact_validation_required": True,
            "projection_may_consume_only_the_already_validated_envelope": True,
            "publish_content_free_child_and_post_child_stage_timings": True,
            "old_v24445_rerun": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "task_query_url_page_prediction_value_or_content_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "claims": {
            "wire_bug_fixed": True,
            "positive_epistemic_credit_measured": True,
            "entropy_to_safe_decision_proven": False,
            "latency_root_cause_uniquely_identified": False,
            "benchmark_quality_measured": False,
            "sota": False,
        },
        "authorization": {
            "bounded_entropy_to_decision_successor_design": True,
            "external_probe_launch": False,
            "old_v24445_rerun": False,
            "paired_dev64": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_diagnosis(value: dict[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    authorization = value.get("authorization")
    claims = value.get("claims")
    order = value.get("successor_work_order")
    if (
        value.get("role") != "v24446_v24445_entropy_to_decision_diagnosis"
        or not isinstance(authorization, dict)
        or authorization.get("bounded_entropy_to_decision_successor_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "external_probe_launch",
                "old_v24445_rerun",
                "paired_dev64",
                "exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or not isinstance(claims, dict)
        or claims.get("wire_bug_fixed") is not True
        or claims.get("positive_epistemic_credit_measured") is not True
        or any(
            claims.get(name) is not False
            for name in (
                "entropy_to_safe_decision_proven",
                "latency_root_cause_uniquely_identified",
                "benchmark_quality_measured",
                "sota",
            )
        )
        or not isinstance(order, dict)
        or order.get("preserve_safe_change_thresholds") is not True
        or order.get("additional_logical_query_or_search_batch") != 0
        or order.get("additional_model_request") != 0
        or order.get("additional_fetch_target_cap") != 1
        or order.get("old_v24445_rerun") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.44.46 diagnosis drifted")
    return dict(value)


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    validate_diagnosis(diagnosis)
    publish_new(ROOT / DIAGNOSIS, diagnosis)
    print(json.dumps({"path": str(DIAGNOSIS), "valid": True}))
