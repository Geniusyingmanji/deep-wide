#!/usr/bin/env python3
"""Content-free diagnosis of the V2.45.06 external NO-GO.

Only sealed public aggregates and one synthetic label-blind execution are
used.  No historical task directory, question, identifier, query, URL, page,
prediction, candidate, benchmark mapping, evaluator output, or credential is
opened or emitted.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)
from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (  # noqa: E402
    run_single_validation_v24503_task,
)
from scripts import v24506_record_bound_external_gate as gate  # noqa: E402


DATE = "20260805"
OUTPUT = Path(f"results/v24507_v24506_dual_bottleneck_diagnosis_v1_{DATE}.json")
RESULT = gate.RESULT
DECISION = gate.DECISION
POSTAUDIT = gate.POSTAUDIT


def _read(relative: Path) -> dict[str, Any]:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.45.07 expected repository file: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.07 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _profile_synthetic() -> dict[str, Any]:
    """Count validator calls on one synthetic in-memory execution."""

    from deepwide_agent import v24457_adaptive_entropy_support as adaptive
    from deepwide_agent import v24490_entropy_targeted_support_search as targeted
    from deepwide_agent import v24496_targeted_reserve_contradiction as reserve
    from test_v24342_semantic_active_runtime import limits
    from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK
    from test_v24412_receipt_snapshot_diagnosis import AdvancingClock
    from test_v24503_record_bound_reserve_integration import clients

    modules = {
        "v24457": adaptive,
        "v24490": targeted,
        "v24496": reserve,
    }
    originals = {name: module.validate_result for name, module in modules.items()}
    calls = {name: 0 for name in modules}

    def wrapper(name: str, original: Any) -> Any:
        def counted(*args: Any, **kwargs: Any) -> Any:
            calls[name] += 1
            return original(*args, **kwargs)

        return counted

    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    try:
        for name, module in modules.items():
            module.validate_result = wrapper(name, originals[name])
        clock = AdvancingClock()
        model, search = clients(
            Path(temporary.name), clock, mode="split_support"
        )
        started = time.perf_counter()
        with ExecutionValidationMemo() as memo:
            run_single_validation_v24503_task(
                TASK,
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        elapsed = max(0.0, time.perf_counter() - started)
        receipt = memo.content_free_receipt()
    finally:
        for name, module in modules.items():
            module.validate_result = originals[name]
        temporary.cleanup()
    return {
        "synthetic_execution_count": 1,
        "high_level_validator_calls": calls,
        "low_level_validation_memo_calls": int(receipt["total_calls"]),
        "low_level_validation_memo_misses": int(receipt["total_misses"]),
        "low_level_validation_memo_hits": int(receipt["total_hits"]),
        "low_level_validation_memo_mismatches": int(
            receipt["total_mismatches"]
        ),
        "synthetic_wall_seconds": round(elapsed, 6),
        "synthetic_clients_only": True,
        "task_question_identifier_query_url_page_prediction_or_value_emitted": False,
        "network_model_search_fetch_process_or_evaluator_called": False,
    }


def validate_report(value: dict[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    profile = copied.get("synthetic_profile")
    public = copied.get("public_result_evidence")
    diagnosis = copied.get("diagnosis")
    authorization = copied.get("authorization")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24507_v24506_dual_bottleneck_diagnosis"
        or not isinstance(public, dict)
        or public.get("selected") != 8
        or public.get("success_tasks") != 5
        or public.get("worker_hard_timeout_tasks") != 3
        or public.get("public_fetch_effect_finished_timeout_tasks") != 3
        or public.get("provider_search_fetch_deadline_failure_lower_bound") != 0
        or public.get("complete_success_target_plan_tasks") != 0
        or public.get("complete_success_record_bound_projection_tasks") != 0
        or public.get("same_population_rerun_allowed") is not False
        or not isinstance(profile, dict)
        or profile.get("synthetic_execution_count") != 1
        or profile.get("low_level_validation_memo_misses") != 8
        or profile.get("low_level_validation_memo_mismatches") != 0
        or profile.get("low_level_validation_memo_hits", 0) < 8
        or not isinstance(profile.get("high_level_validator_calls"), dict)
        or profile["high_level_validator_calls"].get("v24457", 0) <= 1
        or profile["high_level_validator_calls"].get("v24490", 0) <= 1
        or profile["high_level_validator_calls"].get("v24496", 0) <= 1
        or profile.get("synthetic_clients_only") is not True
        or profile.get(
            "task_question_identifier_query_url_page_prediction_or_value_emitted"
        )
        is not False
        or profile.get(
            "network_model_search_fetch_process_or_evaluator_called"
        )
        is not False
        or not isinstance(diagnosis, dict)
        or diagnosis.get("post_effect_local_validation_amplification_observed")
        is not True
        or diagnosis.get("target_plan_coverage_dead_zone_observed") is not True
        or diagnosis.get("provider_or_fetch_deadline_failure_observed") is not False
        or diagnosis.get("record_bound_projector_externally_exercised") is not False
        or diagnosis.get("benchmark_quality_or_sota_measured") is not False
        or not isinstance(authorization, dict)
        or authorization.get("execution_scoped_high_level_validation_memo_design")
        is not True
        or authorization.get("proposal_seeded_label_blind_target_plan_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in (
                "same_population_rerun",
                "new_external_probe_launch",
                "paired_dev64_or_exact220",
                "evaluator",
                "leaderboard_or_sota",
            )
        )
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("source_policy", {}).get(
            "historical_private_task_directory_or_page_opened"
        )
        is not False
        or not _sealed(copied, "diagnosis_payload_sha256")
    ):
        raise ValueError("V2.45.07 diagnosis drifted")
    return copied


def build_report(*, now: int | None = None) -> dict[str, Any]:
    result = gate.validate_public_result(_read(RESULT))
    decision = _read(DECISION)
    post = _read(POSTAUDIT)
    if (
        decision.get("passed") is not False
        or decision.get("status") != "fresh_targeted_external_no_go"
        or not _sealed(decision, "decision_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.07 closed parent artifacts drifted")
    mechanism = result["mechanism_aggregate"]
    observation = result["observation_aggregate"]
    supervision = result["supervision_aggregate"]
    deadline_failures = sum(
        int(observation.get(name, 0))
        for name in (
            "provider_deadline_failures_lower_bound",
            "hosted_search_deadline_failures_lower_bound",
            "hard_fetch_deadline_failures_lower_bound",
            "fetch_helper_failures_lower_bound",
        )
    )
    profile = _profile_synthetic()
    value = {
        "artifact_version": 1,
        "role": "v24507_v24506_dual_bottleneck_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "result": {"path": str(RESULT), "sha256": sha256(ROOT / RESULT)},
            "decision": {
                "path": str(DECISION),
                "sha256": sha256(ROOT / DECISION),
            },
            "postresult_audit": {
                "path": str(POSTAUDIT),
                "sha256": sha256(ROOT / POSTAUDIT),
            },
        },
        "public_result_evidence": {
            "selected": int(result["selected"]),
            "success_tasks": int(mechanism["success_tasks"]),
            "failure_as_zero_tasks": int(mechanism["failure_as_zero_tasks"]),
            "worker_hard_timeout_tasks": int(
                supervision["worker_hard_timeout_tasks"]
            ),
            "public_fetch_effect_finished_timeout_tasks": int(
                supervision["last_stage_counts"].get(
                    "public_fetch_effect_finished", 0
                )
            ),
            "provider_search_fetch_deadline_failure_lower_bound": deadline_failures,
            "complete_success_target_plan_tasks": int(
                mechanism["target_plan_tasks"]
            ),
            "complete_success_record_bound_projection_tasks": int(
                mechanism["record_bound_projection_tasks"]
            ),
            "batch_wall_seconds": float(result["batch_wall_seconds"]),
            "worker_wall_max_seconds": float(
                supervision["worker_wall_max_seconds"]
            ),
            "same_population_rerun_allowed": False,
        },
        "synthetic_profile": profile,
        "diagnosis": {
            "post_effect_local_validation_amplification_observed": True,
            "target_plan_coverage_dead_zone_observed": True,
            "provider_or_fetch_deadline_failure_observed": False,
            "record_bound_projector_externally_exercised": False,
            "benchmark_quality_or_sota_measured": False,
            "two_bottlenecks_are_independent_and_require_separate_successors": True,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "historical_private_task_directory_or_page_opened": False,
            "public_content_free_aggregates_and_synthetic_clients_only": True,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
        },
        "authorization": {
            "execution_scoped_high_level_validation_memo_design": True,
            "proposal_seeded_label_blind_target_plan_design": True,
            "same_population_rerun": False,
            "new_external_probe_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_report(value)


def publish_new(path: Path, value: dict[str, Any]) -> None:
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


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {"path": str(OUTPUT), "diagnosis": report["diagnosis"]},
            sort_keys=True,
        )
    )
