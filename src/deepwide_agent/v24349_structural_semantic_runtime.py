"""Duplicate-safe successor to the V2.43.42 semantic-active runtime.

Both arms share one plan, search, fetch vector, baseline synthesis, and the
same deterministic structural normalization.  Only the candidate receives the
semantic support catalog and entropy-gated revision.  This module is runtime
only: it has no benchmark selection, evaluator, or scoring capability.
"""

from __future__ import annotations

import copy
import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from . import v24325_shared_prefix_revision_runtime as base
from . import v24342_semantic_active_runtime as semantic
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24323_shared_prefix_cell_entropy import (
    build_shared_prefix_receipt,
    payload_sha256,
)
from .v24334_support_catalog_revision_gate import apply_catalog_revision
from .v24335_programmatic_support_runtime import (
    _legacy_admissions,
    _render_catalog,
)
from .v24341_semantic_evidence_projection import build_semantic_active_catalog
from .v24348_structural_table_normalizer import (
    build_stage_receipt,
    normalize_baseline_table,
    semantic_targets,
    validate_normalization_receipt,
    validate_normalization_result,
    validate_stage_receipt,
)


POLICY_ID = "v24349_duplicate_safe_semantic_entropy_runtime_v1"
ROLE = "v24349_structural_semantic_task_result"
RECEIPT_ROLE = "v24349_structural_semantic_runtime_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "semantic_result",
        "structural_receipt",
        "structural_private_state",
        "result_sha256",
    }
)
STRUCTURAL_PRIVATE_KEYS = frozenset(
    {
        "normalization_result",
        "content_free_stage_receipt",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "normalization_applied_to_shared_baseline_before_arm_branch",
        "same_normalized_baseline_for_baseline_and_candidate",
        "candidate_only_adds_semantic_support_and_entropy_gate",
        "normalization_receipt",
        "content_free_stage_receipt",
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


class _StructuralFailure(RuntimeError):
    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(stage)
        self.stage = stage
        self.reason = reason


def _unknown_marker(question: str) -> str:
    return "未知" if any("\u4e00" <= character <= "\u9fff" for character in question) else "Unknown"


def _normalization_reason(receipt: Mapping[str, Any]) -> tuple[str, str]:
    if int(receipt["duplicate_identity_group_count"]) > 0:
        return "duplicate_identity_normalization", "duplicate_identity_detected"
    if int(receipt["empty_identity_group_count"]) > 0:
        return "duplicate_identity_normalization", "empty_identity_excluded"
    return "semantic_target_construction", "none"


def _structural_receipt(
    normalization: Mapping[str, Any] | None,
    stage_receipt: Mapping[str, Any] | None,
    *,
    complete: bool,
) -> dict[str, Any]:
    normal_public = (
        copy.deepcopy(dict(normalization["normalization_receipt"]))
        if normalization is not None
        else None
    )
    stage_public = copy.deepcopy(dict(stage_receipt)) if stage_receipt is not None else None
    if normal_public is not None:
        validate_normalization_receipt(normal_public)
    if stage_public is not None:
        validate_stage_receipt(stage_public)
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "normalization_applied_to_shared_baseline_before_arm_branch": complete,
        "same_normalized_baseline_for_baseline_and_candidate": complete,
        "candidate_only_adds_semantic_support_and_entropy_gate": complete,
        "normalization_receipt": normal_public,
        "content_free_stage_receipt": stage_public,
        "question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_structural_receipt(value)
    return value


def validate_structural_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    normalization = value.get("normalization_receipt")
    stage = value.get("content_free_stage_receipt")
    complete = value.get("normalization_applied_to_shared_baseline_before_arm_branch")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(complete, bool)
        or value.get("same_normalized_baseline_for_baseline_and_candidate") is not complete
        or value.get("candidate_only_adds_semantic_support_and_entropy_gate") is not complete
        or (normalization is not None and not isinstance(normalization, Mapping))
        or (stage is not None and not isinstance(stage, Mapping))
        or complete != isinstance(normalization, Mapping)
        or value.get("question_prompt_response_query_url_page_prediction_answer_opaque_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.49 structural receipt drifted")
    if isinstance(normalization, Mapping):
        validate_normalization_receipt(normalization)
    if isinstance(stage, Mapping):
        validate_stage_receipt(stage)
    if complete and not isinstance(stage, Mapping):
        raise ValueError("V2.43.49 complete structural stage receipt is absent")
    if isinstance(stage, Mapping) and stage["effect_accounting_complete"] is not complete:
        raise ValueError("V2.43.49 structural stage completeness drifted")
    return dict(value)


def _wrap(
    semantic_result: Mapping[str, Any],
    normalization: Mapping[str, Any] | None,
    stage_receipt: Mapping[str, Any] | None,
    *,
    complete: bool,
) -> dict[str, Any]:
    receipt = _structural_receipt(normalization, stage_receipt, complete=complete)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "semantic_result": copy.deepcopy(dict(semantic_result)),
        "structural_receipt": receipt,
        "structural_private_state": {
            "normalization_result": (
                copy.deepcopy(dict(normalization)) if normalization is not None else None
            ),
            "content_free_stage_receipt": (
                copy.deepcopy(dict(stage_receipt)) if stage_receipt is not None else None
            ),
        },
    }
    value["result_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    semantic_result = value.get("semantic_result")
    receipt = value.get("structural_receipt")
    private = value.get("structural_private_state")
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(semantic_result, Mapping)
        or not isinstance(receipt, Mapping)
        or not isinstance(private, Mapping)
        or set(private) != STRUCTURAL_PRIVATE_KEYS
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.49 result identity drifted")
    semantic.validate_result(semantic_result)
    structural = validate_structural_receipt(receipt)
    normalization = private["normalization_result"]
    stage = private["content_free_stage_receipt"]
    complete = structural["normalization_applied_to_shared_baseline_before_arm_branch"]
    if complete:
        if not isinstance(normalization, Mapping) or not isinstance(stage, Mapping):
            raise ValueError("V2.43.49 structural replay state is absent")
        validate_normalization_result(
            normalization,
            unknown_marker=str(normalization["unknown_marker"]),
        )
        validate_stage_receipt(stage)
        if (
            structural["normalization_receipt"]
            != normalization["normalization_receipt"]
            or structural["content_free_stage_receipt"] != stage
            or semantic_result["core_result"]["baseline_prediction"]
            != normalization["normalized_table"]
        ):
            raise ValueError("V2.43.49 shared baseline normalization drifted")
    elif normalization is not None:
        raise ValueError("V2.43.49 fallback persisted normalization content")
    elif stage is not None and structural["content_free_stage_receipt"] != stage:
        raise ValueError("V2.43.49 fallback stage receipt drifted")
    core_complete = semantic_result["core_result"]["shared_prefix_revision_receipt"][
        "effect_accounting_complete"
    ]
    if complete is not core_complete:
        raise ValueError("V2.43.49 structural/core completeness drifted")
    return dict(value)


def run_v24349_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    policy = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    policy.validate()
    if policy.model_calls != 3 or policy.search_queries != 4 or policy.fetch_targets != 10:
        raise ValueError("V2.43.49 fixed pair budget drifted")
    started = float(monotonic())
    budget = base._PairBudget(policy, started, monotonic)
    model_before = base._counter_snapshot(model, base.MODEL_COUNTERS)
    search_before = base._counter_snapshot(search, base.SEARCH_COUNTERS)
    failures: list[dict[str, str]] = []
    trace: list[str] = []

    def recovered(stage: str, error: BaseException) -> None:
        failures.append({"stage": stage, "type": base.coarse_exception_type(error)})

    if not budget.admit_model("plan"):
        raise RuntimeError("V2.43.49 plan was not admitted")
    trace.append("plan_model_admitted")
    plan_provider_returned = False
    try:
        raw_plan = model.complete(
            base.PLAN_SYSTEM,
            base.PLAN_USER.format(question=visible["question"], query_limit=4),
            max_output_tokens=policy.plan_output_tokens,
            json_mode=True,
        )
        plan_provider_returned = True
        plan = base._validated_plan(
            base.parse_json_object(base._model_text(raw_plan)), visible["question"], policy
        )
    except Exception as error:
        recovered("plan", error)
        plan = base._validated_plan({}, visible["question"], policy)
    columns = base.extract_robust_visible_columns(visible["question"]) or list(plan["columns"])
    queries = base._complete_query_vector(visible["question"], plan["queries"], 4)

    union = base.TaskUnionDiscoverySearchClient(search)
    core_query_count = budget.admit_search(len(queries))
    core_queries = queries[:core_query_count]
    search_call_before = base._counter_snapshot(search, base.SEARCH_COUNTERS)
    trace.append("hosted_search_attempted")
    try:
        search_batches = (
            union.search_many(
                core_queries,
                max_results=policy.search_results_per_query,
                search_depth="advanced",
                include_raw_content=False,
            )
            if core_queries
            else []
        )
    except Exception as error:
        recovered("core_search", error)
        search_batches = []
    search_effects = base._counter_delta(
        base._counter_snapshot(search, base.SEARCH_COUNTERS), search_call_before
    )["calls"]
    all_leads = base._lead_requests(search_batches, 12)
    core_leads = all_leads[:7]
    reserve_leads = base._reserve_diversity_leads(
        all_leads[7:], core_values=core_leads, limit=3
    )

    core_fetch_count = budget.admit_fetch(min(7, len(core_leads)))
    core_fetch_before = base._counter_snapshot(search, base.SEARCH_COUNTERS)
    trace.append("core_fetch_attempted")
    try:
        core_batches = union.fetch_urls(core_leads[:core_fetch_count]) if core_fetch_count else []
    except Exception as error:
        recovered("core_fetch", error)
        core_batches = []
    core_fetch_effects = base._counter_delta(
        base._counter_snapshot(search, base.SEARCH_COUNTERS), core_fetch_before
    )["fetch_calls"]
    core_pages = base._page_vector(core_batches, prefix="C", page_chars=policy.page_chars)

    prefix_bundle: dict[str, Any] | None = None
    prefix_status = "unavailable"
    if plan_provider_returned and core_pages and core_fetch_count and search_effects > 0:
        prefix = build_shared_prefix_receipt(
            visible_plan_sha256=payload_sha256(plan),
            planned_query_vector_sha256=payload_sha256(queries),
            first_wave_search_receipt_sha256=payload_sha256(
                {"queries": core_queries, "search_batches": search_batches}
            ),
            core_evidence_vector_sha256=payload_sha256(core_pages),
            plan_model_effects=1,
            first_wave_search_effects=search_effects,
            first_wave_fetch_effects=core_fetch_effects,
            core_usable_pages=len(core_pages),
        )
        prefix_bundle = base.build_prefix_bundle(prefix)
        prefix_status = "frozen"

    reserve_fetch_count = budget.admit_fetch(min(3, len(reserve_leads)))
    reserve_fetch_before = base._counter_snapshot(search, base.SEARCH_COUNTERS)
    trace.append("reserve_fetch_attempted")
    try:
        reserve_batches = union.fetch_urls(reserve_leads[:reserve_fetch_count]) if reserve_fetch_count else []
    except Exception as error:
        recovered("reserve_fetch", error)
        reserve_batches = []
    reserve_fetch_effects = base._counter_delta(
        base._counter_snapshot(search, base.SEARCH_COUNTERS), reserve_fetch_before
    )["fetch_calls"]
    reserve_pages = base._page_vector(reserve_batches, prefix="R", page_chars=policy.page_chars)
    shared_evidence = base._format_evidence(
        [*core_pages, *reserve_pages], character_cap=policy.evidence_chars
    )
    trace.append("shared_active_evidence_frozen")

    if not budget.admit_model("baseline_synthesis"):
        raise RuntimeError("V2.43.49 baseline synthesis was not admitted")
    trace.append("baseline_model_admitted")
    baseline_provider_failed = False
    baseline_recovery_attempted = False
    try:
        raw_baseline = model.complete(
            base.SYNTHESIS_SYSTEM,
            base.SYNTHESIS_USER.format(
                question=visible["question"],
                columns=json.dumps(columns, ensure_ascii=False),
                evidence=shared_evidence,
            ),
            max_output_tokens=policy.synthesis_output_tokens,
            json_mode=False,
        )
        raw_baseline_table = base._canonical_table(
            base._model_text(raw_baseline), columns, visible["question"]
        )
    except Exception as error:
        recovered("baseline_synthesis", error)
        raw_baseline_table = None
        baseline_provider_failed = True
    if raw_baseline_table is None and budget.admit_model("baseline_recovery"):
        baseline_recovery_attempted = True
        trace.append("baseline_recovery_model_admitted")
        try:
            raw_recovery = model.complete(
                base.SYNTHESIS_SYSTEM,
                base.SYNTHESIS_USER.format(
                    question=visible["question"],
                    columns=json.dumps(columns, ensure_ascii=False),
                    evidence=shared_evidence,
                ),
                max_output_tokens=policy.repair_output_tokens,
                json_mode=False,
            )
            raw_baseline_table = base._canonical_table(
                base._model_text(raw_recovery), columns, visible["question"]
            )
        except Exception as error:
            recovered("baseline_recovery", error)
            raw_baseline_table = None
    if raw_baseline_table is None:
        raw_baseline_table = base.build_best_effort_prediction(visible["question"], columns)

    try:
        normalization = normalize_baseline_table(
            raw_baseline_table,
            unknown_marker=_unknown_marker(visible["question"]),
        )
    except ValueError as error:
        raise _StructuralFailure("baseline_table_parse", "table_parse_rejected") from error
    baseline = str(normalization["normalized_table"])
    structural_stage, structural_reason = _normalization_reason(
        normalization["normalization_receipt"]
    )
    stage_receipt = build_stage_receipt(
        stage=structural_stage,
        reason=structural_reason,
        effect_accounting_complete=True,
        model_requests_lower_bound=int(
            base._counter_delta(
                base._counter_snapshot(model, base.MODEL_COUNTERS), model_before
            )["requests"]
        ),
        model_attempts_lower_bound=int(
            base._counter_delta(
                base._counter_snapshot(model, base.MODEL_COUNTERS), model_before
            )["attempts"]
        ),
        search_calls_lower_bound=int(
            base._counter_delta(
                base._counter_snapshot(search, base.SEARCH_COUNTERS), search_before
            )["calls"]
        ),
        fetch_calls_lower_bound=int(
            base._counter_delta(
                base._counter_snapshot(search, base.SEARCH_COUNTERS), search_before
            )["fetch_calls"]
        ),
    )

    candidate = baseline
    semantic_catalog: dict[str, Any] | None = None
    status = "not_built_ineligible_path"
    revision_admitted = False
    revision_returned = False
    model_proposal: str | None = None
    parsed_proposal: dict[str, Any] | None = None
    proposed_table: str | None = None
    cell_support: object = []
    gate: dict[str, Any] | None = None
    resolutions: list[dict[str, Any]] = []
    legacy_admissions: list[dict[str, Any]] = []
    proposed_changes = 0
    admitted_changes = 0
    if (
        prefix_status == "frozen"
        and not baseline_provider_failed
        and not baseline_recovery_attempted
        and budget.remaining() > 0
    ):
        try:
            targets = semantic_targets(
                normalization,
                unknown_marker=_unknown_marker(visible["question"]),
            )
            semantic_catalog = build_semantic_active_catalog(
                targets,
                semantic._plain_pages(core_pages),
                semantic._plain_pages(reserve_pages),
            )
            trace.append("semantic_catalog_built")
            base_catalog = semantic_catalog["active_catalog"]["base_catalog"]
            status = (
                "built_eligible"
                if base_catalog["eligible_support_set_count"] > 0
                else "built_empty"
            )
            if base_catalog["eligible_support_set_count"] > 0 and budget.admit_model(
                "candidate_revision"
            ):
                revision_admitted = True
                trace.append("revision_model_admitted")
                try:
                    raw_revision = model.complete(
                        semantic.REVISION_SYSTEM,
                        semantic.REVISION_USER.format(
                            question=visible["question"],
                            columns=json.dumps(columns, ensure_ascii=False),
                            baseline=baseline,
                            evidence=shared_evidence,
                            support_catalog=_render_catalog(base_catalog),
                        ),
                        max_output_tokens=policy.repair_output_tokens,
                        json_mode=True,
                    )
                    revision_returned = True
                    model_proposal = base._model_text(raw_revision)
                    parsed_proposal = base.parse_json_object(model_proposal)
                    proposed_table = base._canonical_table(
                        str(parsed_proposal.get("candidate_table", "")),
                        columns,
                        visible["question"],
                    )
                    cell_support = parsed_proposal.get("cell_support")
                    if proposed_table is not None:
                        gate = apply_catalog_revision(
                            baseline=baseline,
                            proposed=proposed_table,
                            cell_support=cell_support,
                            catalog=base_catalog,
                        )
                        candidate = str(gate["candidate_table"])
                        proposed_changes = int(gate["proposed_cell_changes"])
                        admitted_changes = int(gate["admitted_cell_changes"])
                        legacy_admissions = _legacy_admissions(
                            baseline=baseline,
                            candidate=candidate,
                            cell_support=cell_support,
                            catalog=base_catalog,
                        )
                        resolutions = semantic._active_resolutions_for_admitted(
                            baseline=baseline,
                            candidate=candidate,
                            cell_support=cell_support,
                            semantic_catalog=semantic_catalog,
                        )
                except Exception as error:
                    recovered("candidate_revision", error)
                    candidate = baseline
                    gate = None
                    proposed_table = None
                    cell_support = []
                    resolutions = []
                    legacy_admissions = []
                    proposed_changes = 0
                    admitted_changes = 0
        except Exception as error:
            recovered("candidate_revision", error)
            semantic_catalog = None
            status = "runtime_fallback"
            candidate = baseline

    model_cost = base._counter_delta(
        base._counter_snapshot(model, base.MODEL_COUNTERS), model_before
    )
    search_cost = base._counter_delta(
        base._counter_snapshot(search, base.SEARCH_COUNTERS), search_before
    )
    core_receipt = base._receipt(
        prefix_status=prefix_status,
        prefix_bundle=prefix_bundle,
        baseline=baseline,
        candidate=candidate,
        admissions=legacy_admissions,
        proposed_changes=proposed_changes,
        admitted_changes=admitted_changes,
        budget=budget,
        core_queries=core_query_count,
        reserve_queries=0,
        core_search_provider_effects=search_effects,
        reserve_search_provider_effects=0,
        core_fetch_targets=core_fetch_count,
        reserve_fetch_targets=reserve_fetch_count,
        core_network_fetch_effects=core_fetch_effects,
        reserve_network_fetch_effects=reserve_fetch_effects,
        core_pages=core_pages,
        reserve_pages=reserve_pages,
        fallback_type=None,
        recoverable_failures=failures,
        provider_model_requests=model_cost["requests"],
        provider_model_attempts=model_cost["attempts"],
    )
    cost = {
        "model": model_cost,
        "search": search_cost,
        "system_total_tokens": model_cost["total_tokens"] + search_cost["total_tokens"],
    }
    try:
        core_result = base._result(
            visible=visible,
            columns=columns,
            baseline=baseline,
            candidate=candidate,
            receipt=core_receipt,
            cost=cost,
            elapsed=float(monotonic()) - started,
            completion_kind=(
                "paired"
                if candidate != baseline
                else "identity_no_reserve"
                if prefix_status == "frozen"
                else "identity_fallback"
            ),
        )
    except ValueError as error:
        raise _StructuralFailure(
            "result_validation", "structural_validation_rejected"
        ) from error
    try:
        mechanism = semantic._mechanism_receipt(
            catalog_status=status,
            raw_core_pages=core_pages,
            raw_reserve_pages=reserve_pages,
            shared_evidence=shared_evidence,
            evidence_character_cap=policy.evidence_chars,
            semantic_catalog=semantic_catalog,
            revision_model_admitted=revision_admitted,
            revision_model_returned=revision_returned,
            model_proposal=model_proposal,
            revision_gate_result=gate,
            active_resolutions=resolutions,
            candidate_identity_handoff=candidate == baseline,
            complete=True,
        )
        semantic_result = semantic._wrap(
            core_result,
            mechanism,
            raw_core_pages=core_pages,
            raw_reserve_pages=reserve_pages,
            shared_active_evidence=shared_evidence,
            semantic_active_catalog=semantic_catalog,
            model_proposal=model_proposal,
            parsed_proposal=parsed_proposal,
            proposed_table=proposed_table,
            cell_support=cell_support,
            revision_gate_result=gate,
            active_resolution_receipts=resolutions,
            stage_trace=trace,
        )
    except ValueError as error:
        raise _StructuralFailure(
            "result_validation", "structural_validation_rejected"
        ) from error
    return _wrap(semantic_result, normalization, stage_receipt, complete=True)


def run_v24349_total_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    chosen = limits or ScoreFirstLimits(
        wall_seconds=180,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )
    chosen.validate()
    started = float(monotonic())
    model_before = base._counter_snapshot(model, base.MODEL_COUNTERS)
    search_before = base._counter_snapshot(search, base.SEARCH_COUNTERS)
    try:
        return run_v24349_task(
            visible,
            model=model,
            search=search,
            limits=chosen,
            monotonic=monotonic,
        )
    except Exception as error:
        model_cost = base._counter_delta(
            base._counter_snapshot(model, base.MODEL_COUNTERS), model_before
        )
        search_cost = base._counter_delta(
            base._counter_snapshot(search, base.SEARCH_COUNTERS), search_before
        )
        columns = base.extract_robust_visible_columns(visible["question"]) or ["Result"]
        prediction = base.build_best_effort_prediction(visible["question"], columns)
        budget = base._PairBudget(chosen, started, monotonic)
        core_receipt = base._receipt(
            prefix_status="runtime_fallback",
            prefix_bundle=None,
            baseline=prediction,
            candidate=prediction,
            admissions=[],
            proposed_changes=0,
            admitted_changes=0,
            budget=budget,
            core_queries=0,
            reserve_queries=0,
            core_search_provider_effects=0,
            reserve_search_provider_effects=0,
            core_fetch_targets=0,
            reserve_fetch_targets=0,
            core_network_fetch_effects=0,
            reserve_network_fetch_effects=0,
            core_pages=[],
            reserve_pages=[],
            fallback_type=base.coarse_exception_type(error),
            recoverable_failures=[],
            provider_model_requests=0,
            provider_model_attempts=0,
            effect_accounting_complete=False,
            unattributed_model_effects_lower_bound=model_cost["requests"],
            unattributed_model_attempts_lower_bound=model_cost["attempts"],
            unattributed_search_effects_lower_bound=search_cost["calls"],
            unattributed_fetch_effects_lower_bound=search_cost["fetch_calls"],
        )
        core_result = base._result(
            visible=visible,
            columns=columns,
            baseline=prediction,
            candidate=prediction,
            receipt=core_receipt,
            cost={
                "model": model_cost,
                "search": search_cost,
                "system_total_tokens": model_cost["total_tokens"] + search_cost["total_tokens"],
            },
            elapsed=float(monotonic()) - started,
            completion_kind="identity_fallback",
        )
        mechanism = semantic._mechanism_receipt(
            catalog_status="runtime_fallback",
            raw_core_pages=None,
            raw_reserve_pages=None,
            shared_evidence=None,
            evidence_character_cap=chosen.evidence_chars,
            semantic_catalog=None,
            revision_model_admitted=False,
            revision_model_returned=False,
            model_proposal=None,
            revision_gate_result=None,
            active_resolutions=[],
            candidate_identity_handoff=True,
            complete=False,
        )
        semantic_result = semantic._wrap(
            core_result,
            mechanism,
            raw_core_pages=None,
            raw_reserve_pages=None,
            shared_active_evidence=None,
            semantic_active_catalog=None,
            model_proposal=None,
            parsed_proposal=None,
            proposed_table=None,
            cell_support=None,
            revision_gate_result=None,
            active_resolution_receipts=[],
            stage_trace=[],
        )
        stage_receipt = None
        if isinstance(error, _StructuralFailure):
            stage_receipt = build_stage_receipt(
                stage=error.stage,
                reason=error.reason,
                effect_accounting_complete=False,
                model_requests_lower_bound=int(model_cost["requests"]),
                model_attempts_lower_bound=int(model_cost["attempts"]),
                search_calls_lower_bound=int(search_cost["calls"]),
                fetch_calls_lower_bound=int(search_cost["fetch_calls"]),
            )
        return _wrap(semantic_result, None, stage_receipt, complete=False)


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "run_v24349_task",
    "run_v24349_total_task",
    "validate_result",
    "validate_structural_receipt",
]
