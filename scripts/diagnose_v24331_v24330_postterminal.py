#!/usr/bin/env python3
"""Content-free post-terminal taxonomy for the frozen V2.43.30 NO-GO.

The exact-220 forward and both prediction freezes are immutable.  This script
reads only sealed result/effect receipts, emits aggregate counts, and has no
forward, model, search, fetch, mapping, evaluator, or scoring path.  In
particular, incomplete total-fallback receipts are treated as independent
lower bounds; their semantic last stage is never inferred.
"""

from __future__ import annotations

import json
import os
import re
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

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24326_runner_integration import (  # noqa: E402
    validate_envelope,
    validate_observed_bundle,
)
from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PROTOCOL_ID,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    read_object,
    sha256,
)
from scripts import (  # noqa: E402
    audit_v24330_shared_prefix_exact220_forward_nogo as parent_audit,
)
from scripts import (  # noqa: E402
    publish_v24330_shared_prefix_exact220_forward_nogo as parent,
)


OUTPUT = Path("results/v24331_v24330_content_free_taxonomy_v1_20260803.json")
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
CHILD_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"
DEADLINE_FLAGS = (
    "slot_timeout",
    "provider_deadline",
    "hosted_search_deadline",
    "hard_fetch_deadline",
    "fetch_deadline_rejection",
    "deadline_exhausted",
)
HEALTH_FLAGS = (
    "slot_timeout",
    "provider_deadline",
    "hosted_search_deadline",
    "hard_fetch_deadline",
    "fetch_helper_failure",
    "fetch_deadline_rejection",
    "deadline_exhausted",
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.31 expected ordinary file: {relative}")
    return path


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = read_object(_ordinary(root, parent.RESULT))
    diagnostic = read_object(_ordinary(root, parent.DIAGNOSTIC))
    audit = read_object(_ordinary(root, parent.AUDIT))
    parent.validate_result(root, result, diagnostic=diagnostic)
    parent_audit.validate_audit(
        root,
        audit,
        result=result,
        diagnostic=diagnostic,
    )
    if (
        result.get("status") != "terminal_forward_gate_no_go"
        or result.get("evaluation_authorized") is not False
        or result.get("official_evaluator_called") is not False
        or result.get("benchmark_score_available") is not False
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
    ):
        raise RuntimeError("V2.43.31 frozen parent authorization drifted")
    return result, diagnostic, audit


def _task_directories(root: Path) -> list[Path]:
    base = root / TASK_ROOT
    if base.is_symlink() or not base.is_dir():
        raise RuntimeError("V2.43.31 frozen task root is absent")
    expected = [base / f"task_{index:04d}" for index in range(1, SELECTED_COUNT + 1)]
    if any(path.is_symlink() or not path.is_dir() for path in expected):
        raise RuntimeError("V2.43.31 frozen task partition is incomplete")
    present = sorted(path for path in base.glob("task_*") if path.is_dir())
    if present != expected:
        raise RuntimeError("V2.43.31 frozen task partition drifted")
    return expected


def _deadline_pattern(model: Mapping[str, Any], transport: Mapping[str, Any]) -> str:
    active: list[str] = []
    if int(model["slot_timeouts"]) > 0:
        active.append("slot_timeout")
    if int(model["provider_deadline_failures"]) > 0:
        active.append("provider_deadline")
    if int(transport["hosted_search_deadline_failures"]) > 0:
        active.append("hosted_search_deadline")
    if int(transport["hard_fetch_deadline_failures"]) > 0:
        active.append("hard_fetch_deadline")
    if int(transport["fetch_helper_failures"]) > 0:
        active.append("fetch_helper_failure")
    if int(transport["fetch_deadline_rejections"]) > 0:
        active.append("fetch_deadline_rejection")
    if transport["deadline_exhausted"] is True:
        active.append("deadline_exhausted")
    return "+".join(active) if active else "none"


def _source_stratum(item: Mapping[str, Any]) -> tuple[Any, ...]:
    admission = item["admission_receipt"]
    evidence = admission["anonymous_evidence"]
    return (
        str(admission["disposition"]),
        "unknown" if item["baseline_cell_unknown"] else "known",
        bool(evidence["fetch_integrity"]),
        int(evidence["independent_sources"]),
        int(evidence["corroborating_sources"]),
        int(evidence["evidence_chars"]) > 0,
    )


def _aggregate(root: Path) -> dict[str, Any]:
    completion: Counter[str] = Counter()
    prefix: Counter[str] = Counter()
    fallback: Counter[str] = Counter()
    stage_vectors: Counter[str] = Counter()
    recoverable_stages: Counter[str] = Counter()
    recoverable_types: Counter[str] = Counter()
    dispositions: Counter[str] = Counter()
    source_strata: Counter[tuple[Any, ...]] = Counter()
    deadline_patterns: Counter[str] = Counter()
    complete_patterns: Counter[str] = Counter()
    incomplete_patterns: Counter[str] = Counter()
    complete = Counter()
    incomplete = Counter()
    transport_totals = Counter()
    proposed = 0
    admitted = 0
    entropy_credit = 0.0

    for directory in _task_directories(root):
        paths = {
            "result": directory / RESULT_NAME,
            "model": directory / MODEL_NAME,
            "transport": directory / TRANSPORT_NAME,
            "child": directory / CHILD_NAME,
            "parent": directory / PARENT_NAME,
        }
        if any(path.is_symlink() or not path.is_file() for path in paths.values()):
            raise RuntimeError("V2.43.31 frozen task artifact is absent")
        envelope = validate_envelope(read_object(paths["result"]))
        model = validate_model_receipt(
            read_object(paths["model"]), expected_cap=MODEL_SLOT_CAP
        )
        transport = validate_transport_health(read_object(paths["transport"]))
        validate_child_receipt(read_object(paths["child"]))
        parent_receipt = validate_parent_receipt(read_object(paths["parent"]))
        validate_observed_bundle(
            envelope,
            model_slot_receipt=model,
            transport_health=transport,
            expected_cap=MODEL_SLOT_CAP,
        )
        if parent_receipt["failure_taxonomy"] != "success":
            raise RuntimeError("V2.43.31 parent receipt is not terminal success")

        result = envelope["result"]
        receipt = result["shared_prefix_revision_receipt"]
        is_complete = receipt["effect_accounting_complete"] is True
        target = complete if is_complete else incomplete
        logical = int(receipt["logical_model_admissions"])
        requests = int(receipt["provider_model_requests"])
        attempts = int(receipt["provider_model_attempts"])
        rejected = int(receipt["pre_provider_model_rejections"])
        acquisitions = int(model["acquisitions"])
        timeouts = int(model["slot_timeouts"])
        target.update(
            {
                "tasks": 1,
                "logical_model_admissions": logical,
                "provider_model_requests": requests,
                "provider_model_attempts": attempts,
                "pre_provider_model_rejections": rejected,
                "slot_acquisitions": acquisitions,
                "slot_timeouts": timeouts,
                "unattributed_model_effects_lower_bound": int(
                    receipt["unattributed_model_effects_lower_bound"]
                ),
                "unattributed_model_attempts_lower_bound": int(
                    receipt["unattributed_model_attempts_lower_bound"]
                ),
                "unattributed_search_effects_lower_bound": int(
                    receipt["unattributed_search_effects_lower_bound"]
                ),
                "unattributed_fetch_effects_lower_bound": int(
                    receipt["unattributed_fetch_effects_lower_bound"]
                ),
            }
        )
        if is_complete and (
            logical != requests + rejected
            or requests != acquisitions
            or rejected != timeouts
            or any(
                int(receipt[name]) != 0
                for name in (
                    "unattributed_model_effects_lower_bound",
                    "unattributed_model_attempts_lower_bound",
                    "unattributed_search_effects_lower_bound",
                    "unattributed_fetch_effects_lower_bound",
                )
            )
        ):
            raise RuntimeError("V2.43.31 complete-task conservation drifted")
        if not is_complete and (
            receipt["model_effect_stages"] != []
            or logical != 0
            or requests != 0
            or attempts != 0
            or rejected != 0
            or int(receipt["unattributed_model_effects_lower_bound"])
            < acquisitions
            or int(receipt["unattributed_model_attempts_lower_bound"])
            < acquisitions
        ):
            raise RuntimeError("V2.43.31 incomplete-task lower bound drifted")

        completion[str(result["completion_kind"])] += 1
        prefix[str(receipt["prefix_status"])] += 1
        fallback[str(receipt["fallback_type"] or "none")] += 1
        stages = receipt["model_effect_stages"]
        stage_vectors["+".join(stages) if stages else "unattributed"] += 1
        for failure in receipt["recoverable_failures"]:
            recoverable_stages[str(failure["stage"])] += 1
            recoverable_types[str(failure["type"])] += 1
        for item in receipt["cell_admissions"]:
            disposition = str(item["admission_receipt"]["disposition"])
            dispositions[disposition] += 1
            source_strata[_source_stratum(item)] += 1
        proposed += int(receipt["proposed_cell_changes"])
        admitted += int(receipt["admitted_cell_changes"])
        entropy_credit += float(
            receipt["credited_conditional_entropy_reduction_nats"]
        )

        pattern = _deadline_pattern(model, transport)
        deadline_patterns[pattern] += 1
        (complete_patterns if is_complete else incomplete_patterns)[pattern] += 1
        transport_totals.update(
            {
                "slot_acquisitions": acquisitions,
                "slot_timeouts": timeouts,
                "provider_deadline_failures": int(
                    model["provider_deadline_failures"]
                ),
                "hosted_search_attempts": int(transport["hosted_search_attempts"]),
                "hosted_search_deadline_failures": int(
                    transport["hosted_search_deadline_failures"]
                ),
                "hard_fetch_helper_calls": int(
                    transport["hard_fetch_helper_calls"]
                ),
                "hard_fetch_deadline_failures": int(
                    transport["hard_fetch_deadline_failures"]
                ),
                "fetch_helper_failures": int(transport["fetch_helper_failures"]),
                "fetch_deadline_rejections": int(
                    transport["fetch_deadline_rejections"]
                ),
                "deadline_exhausted_tasks": int(
                    transport["deadline_exhausted"] is True
                ),
            }
        )

    complete_conservation = (
        complete["logical_model_admissions"]
        == complete["provider_model_requests"]
        + complete["pre_provider_model_rejections"]
        and complete["provider_model_requests"] == complete["slot_acquisitions"]
        and complete["pre_provider_model_rejections"] == complete["slot_timeouts"]
    )
    incomplete_with_deadline = sum(
        count
        for pattern, count in incomplete_patterns.items()
        if any(flag in pattern.split("+") for flag in DEADLINE_FLAGS)
    )
    incomplete_with_health_event = sum(
        count
        for pattern, count in incomplete_patterns.items()
        if any(flag in pattern.split("+") for flag in HEALTH_FLAGS)
    )
    return {
        "selected_tasks": int(complete["tasks"] + incomplete["tasks"]),
        "completion_kinds": dict(sorted(completion.items())),
        "prefix_status": dict(sorted(prefix.items())),
        "fallback_types": dict(sorted(fallback.items())),
        "attributed_model_stage_vectors": dict(sorted(stage_vectors.items())),
        "recoverable_failure_stages": dict(sorted(recoverable_stages.items())),
        "recoverable_failure_types": dict(sorted(recoverable_types.items())),
        "effect_accounting": {
            "complete_tasks": int(complete["tasks"]),
            "incomplete_tasks": int(incomplete["tasks"]),
            "complete_task_totals": {
                name: int(complete[name])
                for name in (
                    "logical_model_admissions",
                    "provider_model_requests",
                    "provider_model_attempts",
                    "pre_provider_model_rejections",
                    "slot_acquisitions",
                    "slot_timeouts",
                )
            },
            "incomplete_task_independent_lower_bounds": {
                name: int(incomplete[name])
                for name in (
                    "slot_acquisitions",
                    "slot_timeouts",
                    "unattributed_model_effects_lower_bound",
                    "unattributed_model_attempts_lower_bound",
                    "unattributed_search_effects_lower_bound",
                    "unattributed_fetch_effects_lower_bound",
                )
            },
            "complete_subset_conservation_verified": complete_conservation,
            "incomplete_semantic_last_stage_available": False,
            "incomplete_stage_inferred_or_imputed": False,
            "global_equality_asserted_across_incomplete_lower_bounds": False,
        },
        "admission": {
            "proposed_cell_changes": proposed,
            "admitted_cell_changes": admitted,
            "credited_conditional_entropy_reduction_nats": round(
                entropy_credit, 12
            ),
            "dispositions": dict(sorted(dispositions.items())),
            "source_support_strata": [
                {
                    "disposition": key[0],
                    "baseline_cell_state": key[1],
                    "fetch_integrity": key[2],
                    "independent_sources": key[3],
                    "corroborating_sources": key[4],
                    "declared_evidence_has_characters": key[5],
                    "count": count,
                }
                for key, count in sorted(source_strata.items())
            ],
        },
        "transport": {
            "totals": {
                name: int(value) for name, value in sorted(transport_totals.items())
            },
            "deadline_or_health_patterns": dict(sorted(deadline_patterns.items())),
            "complete_task_patterns": dict(sorted(complete_patterns.items())),
            "incomplete_task_patterns": dict(sorted(incomplete_patterns.items())),
            "incomplete_tasks_with_deadline_flag": incomplete_with_deadline,
            "incomplete_tasks_with_any_transport_health_event": (
                incomplete_with_health_event
            ),
            "incomplete_tasks_without_transport_health_event": int(
                incomplete["tasks"] - incomplete_with_health_event
            ),
        },
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result, diagnostic, audit = _parents(root)
    aggregate = _aggregate(root)
    if aggregate["selected_tasks"] != SELECTED_COUNT:
        raise RuntimeError("V2.43.31 denominator drifted")
    effect = aggregate["effect_accounting"]
    admission = aggregate["admission"]
    transport = aggregate["transport"]
    if (
        effect["complete_tasks"] != 157
        or effect["incomplete_tasks"] != 63
        or admission["proposed_cell_changes"] != 19
        or admission["admitted_cell_changes"] != 0
        or sum(admission["dispositions"].values()) != 19
        or not effect["complete_subset_conservation_verified"]
    ):
        raise RuntimeError("V2.43.31 frozen aggregate drifted")
    value = {
        "artifact_version": 1,
        "role": "v24331_v24330_content_free_postterminal_taxonomy",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_nogo_sha256": sha256(root / parent.RESULT),
            "forward_nogo_audit_sha256": sha256(root / parent.AUDIT),
            "forward_nogo_diagnostic_sha256": sha256(root / parent.DIAGNOSTIC),
            "forward_nogo_result_payload_sha256": result["result_payload_sha256"],
            "forward_nogo_audit_payload_sha256": audit["audit_payload_sha256"],
            "forward_nogo_diagnostic_payload_sha256": diagnostic[
                "diagnostic_payload_sha256"
            ],
        },
        "boundary": {
            "postterminal_only": True,
            "both_exact220_arm_freezes_preexisted": True,
            "same_run_forward_resume_retry_rerun_or_selective_retry": False,
            "mapping_gold_category_question_type_split_evaluator_or_score_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "task_identifier_question_query_url_page_cell_value_evidence_id_or_prediction_emitted": False,
            "per_task_hash_or_position_emitted": False,
        },
        "aggregate": aggregate,
        "conclusions": {
            "entropy_threshold_was_primary_admission_bottleneck": False,
            "evidence_binding_or_source_independence_was_primary_admission_bottleneck": True,
            "all_incomplete_fallbacks_explained_by_deadline_or_transport_health": False,
            "incomplete_semantic_stage_recoverable_from_frozen_receipts": False,
            "aggregate_validator_requires_complete_and_incomplete_strata": True,
            "same_run_evaluation_authorized": False,
            "new_exact220_authorized": False,
            "quality_improvement_demonstrated": False,
            "sota_supported": False,
        },
        "next_work": {
            "aggregate_validator": (
                "strict conservation for complete tasks; independent lower bounds "
                "only for incomplete tasks; promotion still fails above frozen "
                "incomplete-task gate"
            ),
            "fault_matrix": [
                "complete_success",
                "complete_fallback",
                "incomplete_fallback_valid_lower_bounds",
                "tampered_lower_bound_rejection",
            ],
            "evidence_admission": (
                "construct eligible two-host unknown support and three-host override "
                "sets before revision; keep invalid citations quarantined"
            ),
            "benchmark_external_before_new_benchmark": True,
        },
        "authorization": {
            "append_only_aggregate_validator_design": True,
            "benchmark_external_fault_matrix": True,
            "benchmark_external_evidence_admission_test": True,
            "same_run_evaluator": False,
            "same_run_forward_resume_retry_or_rerun": False,
            "additional_dev64": False,
            "new_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if SECRET.search(encoded) or OPAQUE.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.43.31 report emitted prohibited content")
    value["taxonomy_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "taxonomy_payload_sha256"):
        raise RuntimeError("V2.43.31 taxonomy drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "complete_tasks": report["aggregate"]["effect_accounting"][
                    "complete_tasks"
                ],
                "incomplete_tasks": report["aggregate"]["effect_accounting"][
                    "incomplete_tasks"
                ],
                "admission_dispositions": report["aggregate"]["admission"][
                    "dispositions"
                ],
            },
            sort_keys=True,
        )
    )
