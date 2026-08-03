#!/usr/bin/env python3
"""Freeze the terminal V2.43.30 pair and publish an evaluator-blocking NO-GO.

The one exact-220 forward already terminated.  This append-only recovery reads
only its frozen prediction rows and sealed task receipts.  It has no forward,
model, search, fetch, mapping, or evaluator execution path and never emits task
content or identifiers.
"""

from __future__ import annotations

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
    ACTIVATION,
    ARMS,
    EVALUATOR_GATE,
    EVALUATOR_ROOT,
    EVALUATOR_START,
    EXECUTION_START,
    FINAL_RESULT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_PATH,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    POSTAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    selected_ids,
    sha256,
    validate_forward_contract,
)
from scripts import run_v24330_shared_prefix_exact220 as runner  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.v24330_shared_prefix_exact220_control import (  # noqa: E402
    DECISION_CONTRACT,
    validate_protocol,
)


DIAGNOSTIC = OUTPUT_ROOT / "pair_forward_nogo_diagnostic.json"
RESULT = Path("results/v24330_shared_prefix_exact220_forward_nogo_v1_20260803.json")
AUDIT = Path(
    "results/v24330_shared_prefix_exact220_forward_nogo_audit_v1_20260803.json"
)
RESULT_NAME = "result.json"
MODEL_NAME = "model_slot_receipt.json"
TRANSPORT_NAME = "transport_health.json"
CHILD_NAME = "child_terminal_receipt.json"
PARENT_NAME = "parent_exit_receipt.json"
RUNNER_MARKERS = (
    "scripts/run_v24330_shared_prefix_exact220.py",
    "scripts/run_v24330_shared_prefix_exact220_task.py",
)
EVALUATOR_SURFACES = (
    EVALUATOR_GATE,
    EVALUATOR_START,
    EVALUATOR_ROOT,
    FINAL_RESULT,
    POSTAUDIT,
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


def _task_directories(root: Path) -> list[Path]:
    task_root = root / TASK_ROOT
    if task_root.is_symlink() or not task_root.is_dir():
        raise RuntimeError("V2.43.30 terminal task root is absent")
    expected = [
        task_root / f"task_{position:04d}"
        for position in range(1, SELECTED_COUNT + 1)
    ]
    if any(path.is_symlink() or not path.is_dir() for path in expected):
        raise RuntimeError("V2.43.30 terminal task partition is incomplete")
    present = sorted(path for path in task_root.glob("task_*") if path.is_dir())
    if present != expected:
        raise RuntimeError("V2.43.30 terminal task partition drifted")
    return expected


def _process_present(marker: str) -> bool:
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker):
            return True
    return False


def _assert_closed_surface(root: Path) -> None:
    if (root / FORWARD_RESULT).exists() or (root / FORWARD_RESULT).is_symlink():
        raise RuntimeError("V2.43.30 success forward result unexpectedly exists")
    if (root / PAIR_SUMMARY).exists() or (root / PAIR_SUMMARY).is_symlink():
        raise RuntimeError("V2.43.30 success pair summary unexpectedly exists")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in EVALUATOR_SURFACES
    ):
        raise RuntimeError("V2.43.30 evaluator-side surface unexpectedly exists")
    if any(_process_present(marker) for marker in RUNNER_MARKERS):
        raise RuntimeError("V2.43.30 forward process is still active")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        raise RuntimeError("V2.43.30 shared API lease is still active")


def _freeze_value(
    root: Path,
    contract: Mapping[str, Any],
    arm: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "arm": arm,
        "selected": SELECTED_COUNT,
        "terminal": SELECTED_COUNT,
        "selected_opaque_ids_sha256": contract["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS[arm]),
        "run_summary_sha256": sha256(root / RUN_SUMMARY[arm]),
        "prediction_hashes_sha256": payload_sha256(
            [row["prediction_sha256"] for row in rows]
        ),
        "both_arms_terminal_before_mapping_gold_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    runner.validate_prediction_freeze(root, contract, arm, value)
    return value


def _state(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    _assert_closed_surface(root)
    contract = validate_forward_contract(root)
    validate_protocol(root)
    ids = selected_ids(contract)
    rows = {
        arm: runner._read_runtime_rows(root / RUNTIME_PREDICTIONS[arm], arm)
        for arm in ARMS
    }
    summaries = {
        arm: runner.validate_arm_summary(read_object(root / RUN_SUMMARY[arm]), arm)
        for arm in ARMS
    }
    for arm in ARMS:
        if [row["opaque_id"] for row in rows[arm]] != ids:
            raise RuntimeError("V2.43.30 frozen runtime order drifted")

    completion = Counter()
    prefix = Counter()
    parent_taxonomy = Counter()
    aggregate = Counter()
    complete = Counter()
    incomplete = Counter()
    task_manifest: list[dict[str, Any]] = []
    directories = _task_directories(root)
    for index, directory in enumerate(directories):
        envelope_path = directory / RESULT_NAME
        model_path = directory / MODEL_NAME
        transport_path = directory / TRANSPORT_NAME
        child_path = directory / CHILD_NAME
        parent_path = directory / PARENT_NAME
        for path in (
            envelope_path,
            model_path,
            transport_path,
            child_path,
            parent_path,
        ):
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("V2.43.30 terminal task artifact is absent")
        envelope = validate_envelope(read_object(envelope_path))
        model = validate_model_receipt(
            read_object(model_path), expected_cap=MODEL_SLOT_CAP
        )
        transport = validate_transport_health(read_object(transport_path))
        validate_child_receipt(read_object(child_path))
        parent = validate_parent_receipt(read_object(parent_path))
        validate_observed_bundle(
            envelope,
            model_slot_receipt=model,
            transport_health=transport,
            expected_cap=MODEL_SLOT_CAP,
        )
        result = envelope["result"]
        receipt = result["shared_prefix_revision_receipt"]
        parent_taxonomy[str(parent["failure_taxonomy"])] += 1
        completion[str(result["completion_kind"])] += 1
        prefix[str(receipt["prefix_status"])] += 1
        if parent["failure_taxonomy"] != "success":
            raise RuntimeError("V2.43.30 terminal parent was not successful")
        for arm in ARMS:
            row = rows[arm][index]
            if (
                row["opaque_id"] != result["opaque_id"]
                or row["status"] != "completed"
                or row["prediction"] != result[f"{arm}_prediction"]
                or row["prediction_sha256"]
                != result[f"{arm}_prediction_sha256"]
                or row["candidate_identity_handoff"]
                is not receipt["candidate_identity_handoff"]
            ):
                raise RuntimeError("V2.43.30 frozen prediction/envelope drifted")

        logical = int(receipt["logical_model_admissions"])
        requests = int(receipt["provider_model_requests"])
        attempts = int(receipt["provider_model_attempts"])
        rejected = int(receipt["pre_provider_model_rejections"])
        acquisitions = int(model["acquisitions"])
        timeouts = int(model["slot_timeouts"])
        target = complete if receipt["effect_accounting_complete"] else incomplete
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
            }
        )
        if receipt["effect_accounting_complete"] and (
            logical != requests + rejected
            or requests != acquisitions
            or rejected != timeouts
        ):
            raise RuntimeError("V2.43.30 complete-task model conservation drifted")
        if not receipt["effect_accounting_complete"] and (
            int(receipt["unattributed_model_effects_lower_bound"])
            < acquisitions
        ):
            raise RuntimeError("V2.43.30 incomplete-task lower bound drifted")

        aggregate.update(
            {
                "valid_parent_receipts": 1,
                "valid_child_receipts": 1,
                "valid_result_envelopes": 1,
                "valid_model_receipts": 1,
                "valid_transport_receipts": 1,
                "logical_model_admissions": logical,
                "provider_model_requests": requests,
                "provider_model_attempts": attempts,
                "pre_provider_model_rejections": rejected,
                "slot_acquisitions": acquisitions,
                "slot_timeouts": timeouts,
                "provider_deadline_failures": int(
                    model["provider_deadline_failures"]
                ),
                "hosted_search_attempts": int(
                    transport["hosted_search_attempts"]
                ),
                "hosted_search_deadline_failures": int(
                    transport["hosted_search_deadline_failures"]
                ),
                "hard_fetch_helper_calls": int(
                    transport["hard_fetch_helper_calls"]
                ),
                "hard_fetch_deadline_failures": int(
                    transport["hard_fetch_deadline_failures"]
                ),
                "fetch_deadline_rejections": int(
                    transport["fetch_deadline_rejections"]
                ),
                "fetch_helper_failures": int(
                    transport["fetch_helper_failures"]
                ),
                "deadline_exhausted_tasks": int(
                    transport["deadline_exhausted"] is True
                ),
                "prefix_frozen_tasks": int(receipt["prefix_status"] == "frozen"),
                "prefix_producer_execution_count": int(
                    (receipt.get("prefix_bundle") or {}).get(
                        "producer_execution_count", 0
                    )
                ),
                "repeated_upstream_effects": sum(
                    int(receipt[name])
                    for name in (
                        "repeated_plan_model_effects_by_branches",
                        "repeated_core_search_effects_by_branches",
                        "repeated_core_fetch_effects_by_branches",
                    )
                ),
                "candidate_nonidentity_tasks": int(
                    receipt["candidate_identity_handoff"] is False
                ),
                "proposed_cell_changes": int(receipt["proposed_cell_changes"]),
                "admitted_cell_changes": int(receipt["admitted_cell_changes"]),
            }
        )
        task_manifest.append(
            {
                "position": index + 1,
                "result_sha256": sha256(envelope_path),
                "model_receipt_sha256": sha256(model_path),
                "transport_receipt_sha256": sha256(transport_path),
                "child_receipt_sha256": sha256(child_path),
                "parent_receipt_sha256": sha256(parent_path),
            }
        )

    entropy = sum(
        float(
            read_object(directory / RESULT_NAME)["result"][
                "shared_prefix_revision_receipt"
            ]["credited_conditional_entropy_reduction_nats"]
        )
        for directory in directories
    )
    projection = {
        "selected_pair_tasks": SELECTED_COUNT,
        "terminal_pair_tasks": SELECTED_COUNT,
        "prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "successful_pair_tasks": aggregate["valid_result_envelopes"],
        "failed_pair_tasks": SELECTED_COUNT - aggregate["valid_result_envelopes"],
        "parent_exit_taxonomy": dict(sorted(parent_taxonomy.items())),
        "completion_kinds": dict(sorted(completion.items())),
        "prefix_status": dict(sorted(prefix.items())),
        **{name: int(value) for name, value in sorted(aggregate.items())},
        "credited_conditional_entropy_reduction_nats": round(entropy, 12),
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
            "incomplete_task_lower_bounds": {
                name: int(incomplete[name])
                for name in (
                    "slot_acquisitions",
                    "slot_timeouts",
                    "unattributed_model_effects_lower_bound",
                    "unattributed_model_attempts_lower_bound",
                )
            },
            "complete_subset_conservation_verified": True,
            "global_naive_conservation_is_invalid_for_incomplete_fallbacks": True,
        },
        "task_artifact_manifest_sha256": payload_sha256(task_manifest),
    }
    if (
        summaries["baseline"]["completed"] != SELECTED_COUNT
        or summaries["candidate"]["completed"] != SELECTED_COUNT
        or summaries["baseline"]["failed"] != 0
        or summaries["candidate"]["failed"] != 0
        or summaries["baseline"]["forward_wall_seconds"]
        != summaries["candidate"]["forward_wall_seconds"]
        or aggregate["repeated_upstream_effects"] != 0
    ):
        raise RuntimeError("V2.43.30 terminal aggregate drifted")
    freezes = {
        arm: _freeze_value(root, contract, arm, rows[arm]) for arm in ARMS
    }
    return {
        "contract": contract,
        "rows": rows,
        "summaries": summaries,
        "projection": projection,
        "freezes": freezes,
    }


def _checks(state: Mapping[str, Any]) -> dict[str, bool]:
    pair = state["projection"]
    accounting = pair["effect_accounting"]
    limits = DECISION_CONTRACT
    return {
        "terminal_pair_tasks": pair["terminal_pair_tasks"] == SELECTED_COUNT,
        "prediction_rows_per_arm": pair["prediction_rows_per_arm"]
        == {arm: SELECTED_COUNT for arm in ARMS},
        "successful_pair_tasks": pair["successful_pair_tasks"] == SELECTED_COUNT,
        "valid_parent_receipts": pair["valid_parent_receipts"] == SELECTED_COUNT,
        "valid_child_receipts": pair["valid_child_receipts"] == SELECTED_COUNT,
        "valid_result_envelopes": pair["valid_result_envelopes"] == SELECTED_COUNT,
        "valid_model_receipts": pair["valid_model_receipts"] == SELECTED_COUNT,
        "valid_transport_receipts": pair["valid_transport_receipts"]
        == SELECTED_COUNT,
        "all_shared_prefixes_frozen": pair["prefix_frozen_tasks"] == SELECTED_COUNT,
        "effect_accounting_complete": accounting["complete_tasks"] == SELECTED_COUNT,
        "complete_subset_conservation": accounting[
            "complete_subset_conservation_verified"
        ]
        is True,
        "repeated_upstream_effects": pair["repeated_upstream_effects"]
        == limits["required_repeated_upstream_effects"],
        "candidate_nonidentity_tasks": pair["candidate_nonidentity_tasks"]
        >= limits["minimum_candidate_nonidentity_tasks"],
        "admitted_cell_changes": pair["admitted_cell_changes"]
        >= limits["minimum_admitted_cell_changes"],
        "positive_entropy_credit": pair[
            "credited_conditional_entropy_reduction_nats"
        ]
        >= limits["minimum_credited_conditional_entropy_reduction_nats"],
        "slot_timeouts": pair["slot_timeouts"] <= limits["maximum_slot_timeouts"],
        "provider_deadline_failures": pair["provider_deadline_failures"]
        <= limits["maximum_provider_deadline_failures"],
        "hard_fetch_deadline_failures": pair["hard_fetch_deadline_failures"]
        <= limits["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": pair["fetch_helper_failures"]
        <= limits["maximum_fetch_helper_failures"],
        "hosted_search_deadline_failures": pair[
            "hosted_search_deadline_failures"
        ]
        <= limits["maximum_hosted_search_deadline_failures"],
        "fetch_deadline_rejections": pair["fetch_deadline_rejections"]
        <= limits["maximum_fetch_deadline_rejections"],
        "deadline_exhausted_tasks": pair["deadline_exhausted_tasks"]
        <= limits["maximum_deadline_exhausted_tasks"],
    }


def _diagnostic(root: Path, state: Mapping[str, Any], *, now: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_forward_nogo_diagnostic",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": now,
        "runner_exit_stage": "post_exact220_pair_summary_validation",
        "runner_exit_code": 1,
        "runner_error_class": "pair_summary_global_model_conservation_rejected_incomplete_fallback_lower_bounds",
        "pair": state["projection"],
        "both_arm_runtime_predictions_written_before_runner_exit": True,
        "both_arm_run_summaries_written_before_runner_exit": True,
        "frozen_source_sha256": {
            "runtime_predictions": {
                arm: sha256(root / RUNTIME_PREDICTIONS[arm]) for arm in ARMS
            },
            "run_summaries": {
                arm: sha256(root / RUN_SUMMARY[arm]) for arm in ARMS
            },
        },
        "source_policy": {
            "task_content_or_identifier_emitted": False,
            "prediction_content_or_per_task_hash_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "forward_resume_retry_skip_or_rerun": False,
        },
    }
    value["diagnostic_payload_sha256"] = payload_sha256(value)
    return value


def _result(
    root: Path,
    state: Mapping[str, Any],
    diagnostic: Mapping[str, Any],
    *,
    now: int,
) -> dict[str, Any]:
    checks = _checks(state)
    failed = sorted(name for name, passed in checks.items() if not passed)
    if not failed:
        raise RuntimeError("V2.43.30 recovery unexpectedly passed all forward gates")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_forward_nogo",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": now,
        "status": "terminal_forward_gate_no_go",
        "selected_pair_tasks": SELECTED_COUNT,
        "terminal_prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "forward_wall_seconds": state["summaries"]["baseline"][
            "forward_wall_seconds"
        ],
        "pair": state["projection"],
        "forward_gate": {
            "checks": checks,
            "failed_checks": failed,
            "passed": False,
        },
        "provenance": {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "runtime_predictions_sha256": {
                arm: sha256(root / RUNTIME_PREDICTIONS[arm]) for arm in ARMS
            },
            "run_summary_sha256": {
                arm: sha256(root / RUN_SUMMARY[arm]) for arm in ARMS
            },
            "prediction_freeze_payload_sha256": {
                arm: state["freezes"][arm]["freeze_payload_sha256"]
                for arm in ARMS
            },
            "diagnostic_payload_sha256": diagnostic[
                "diagnostic_payload_sha256"
            ],
        },
        "both_arm_predictions_exact220_frozen": True,
        "failure_as_zero_predictions_frozen": True,
        "evaluation_authorized": False,
        "official_evaluator_called": False,
        "benchmark_score_available": False,
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "all_220_pair_predictions_frozen_before_postterminal_diagnosis": True,
            "task_question_query_url_page_prediction_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_selection": False,
        },
        "claims": {
            "public_exact220_forward_completed": True,
            "public_exact220_benchmark_score_available": False,
            "entropy_mechanism_activated": False,
            "quality_improvement_demonstrated": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
        "authorization": {
            "postterminal_content_free_diagnosis": True,
            "append_only_accounting_fix_design": True,
            "same_run_evaluator": False,
            "same_run_forward_resume_retry_or_rerun": False,
            "additional_rollout": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def build_publication(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    state = _state(root)
    timestamp = int(time.time()) if now is None else int(now)
    diagnostic = _diagnostic(root, state, now=timestamp)
    result = _result(root, state, diagnostic, now=timestamp)
    validate_diagnostic(root, diagnostic, state=state)
    validate_result(root, result, state=state, diagnostic=diagnostic)
    return {
        "state": state,
        "diagnostic": diagnostic,
        "result": result,
        "freezes": state["freezes"],
    }


def validate_diagnostic(
    root: Path,
    value: Mapping[str, Any],
    *,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = dict(state) if state is not None else _state(root)
    unsigned = dict(value)
    seal = unsigned.pop("diagnostic_payload_sha256", None)
    expected = _diagnostic(
        root, frozen, now=int(value.get("created_at_unix", -1))
    )
    if dict(value) != expected or seal != payload_sha256(unsigned):
        raise RuntimeError("V2.43.30 forward NO-GO diagnostic drifted")
    return dict(value)


def validate_result(
    root: Path,
    value: Mapping[str, Any],
    *,
    state: Mapping[str, Any] | None = None,
    diagnostic: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = dict(state) if state is not None else _state(root)
    diagnosis = (
        dict(diagnostic)
        if diagnostic is not None
        else read_object(root / DIAGNOSTIC)
    )
    validate_diagnostic(root, diagnosis, state=frozen)
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    expected = _result(
        root,
        frozen,
        diagnosis,
        now=int(value.get("created_at_unix", -1)),
    )
    if dict(value) != expected or seal != payload_sha256(unsigned):
        raise RuntimeError("V2.43.30 forward NO-GO result drifted")
    return dict(value)


def publish(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    targets = (
        root / DIAGNOSTIC,
        *(root / PREDICTION_FREEZE[arm] for arm in ARMS),
        root / RESULT,
    )
    if any(path.exists() or path.is_symlink() for path in targets):
        raise RuntimeError("V2.43.30 NO-GO publication surface is not pristine")
    publication = build_publication(root)
    created: list[Path] = []
    try:
        _publish_new(root / DIAGNOSTIC, publication["diagnostic"])
        created.append(root / DIAGNOSTIC)
        for arm in ARMS:
            path = root / PREDICTION_FREEZE[arm]
            _publish_new(path, publication["freezes"][arm])
            created.append(path)
        _publish_new(root / RESULT, publication["result"])
        created.append(root / RESULT)
        state = _state(root)
        validate_result(root, read_object(root / RESULT), state=state)
    except BaseException:
        for path in reversed(created):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        raise
    return publication["result"]


if __name__ == "__main__":
    published = publish(ROOT)
    print(
        json.dumps(
            {
                "path": str(RESULT),
                "status": published["status"],
                "failed_checks": published["forward_gate"]["failed_checks"],
            },
            sort_keys=True,
        )
    )
