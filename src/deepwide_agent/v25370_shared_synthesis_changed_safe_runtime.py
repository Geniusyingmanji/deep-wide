"""Shared-synthesis runtime with deterministic changed-safe candidate edits.

The V2.53.67 gate used two independent production syntheses.  Even with a
verified-prefix treatment, equal outputs could mean either page redundancy or
model insensitivity, while unequal outputs could contain independent sampling
noise.  This successor removes both ambiguities:

1. one visible-only plan call and one joint grounded-plan/record call are
   shared;
2. all four queries, search responses, fetches, and page bytes are shared;
3. exactly one production synthesis creates the control/base table; and
4. V2.53.69 deterministically edits only unique verified coordinates whose
   value differs from that base cell.

The normal physical ceiling is therefore four queries, fourteen fetches, and
three model calls.  There is no second synthesis or candidate model effect.
The runtime accepts only visible ``opaque_id``/``question`` plus injected
hard-capped clients.  It has no filesystem, environment, process, credential,
evaluator, benchmark-label, mapping, gold, score, reward, or historical-result
capability.  Entropy/information gain remains shadow-only and assigns no
signed credit.  This build authorizes no external or benchmark launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24982_paired_production_runtime as counters
from . import v24986_robust_paired_runtime as robust
from . import v24990_query_vector_paired_runtime as compact
from . import v24999_shared_response_selection_runtime as shared
from . import v25117_grounded_target_record_plan as target_plan
from . import v25119_grounded_target_record_paired_runtime as frontier
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25346_grounded_fact_bootstrap as bootstrap
from . import v25349_shared_prefix_grounded_fact_paired_runtime as paired_parent
from . import v25354_pre_effect_query_compatible_grounded_fact_runtime as query_parent
from . import v25360_quote_coordinate_partial_field_record as verifier
from . import v25369_changed_safe_verified_coordinate_edit as editor
from .clients import parse_json_object
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25370_shared_synthesis_changed_safe_runtime_v1"
ROLE = "v25370_shared_synthesis_changed_safe_runtime_result"
RECEIPT_ROLE = "v25370_content_free_shared_synthesis_changed_safe_runtime_receipt"
ARMS = ("shared_base_table", "changed_safe_verified_edit")
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = paired_parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES

_COUNT_FIELDS = (
    "planned_query_count",
    "physical_query_count",
    "physical_fetch_count",
    "physical_model_forward_count",
    "model_provider_request_count",
    "model_provider_attempt_count",
    "system_total_tokens",
    "shared_page_count",
    "base_production_prompt_characters",
    "control_prediction_characters",
    "candidate_prediction_characters",
    "input_provider_query_string_count",
    "compatible_provider_query_seed_count",
    "transformed_or_rejected_provider_query_count",
    "emitted_query_seed_count",
    "changed_safe_coordinate_count",
    "positive_signed_credit_count",
)
_DYNAMIC_FLAGS = (
    "first_wave_completed",
    "grounded_plan_model_call_attempted",
    "grounded_plan_model_call_success",
    "grounded_plan_strategy_applied",
    "second_wave_completed",
    "base_synthesis_attempted",
    "base_synthesis_model_success",
    "base_table_exact_canonical",
    "candidate_prediction_changed",
    "attributable_prediction_change",
    "candidate_identity_handoff",
    "visible_fallback_query_seed_used",
    "editor_validation_failed",
)
_TRUE_FLAGS = (
    "one_visible_plan_and_one_joint_grounded_plan_call_shared",
    "control_and_candidate_share_queries_search_responses_fetches_and_page_bytes",
    "one_shared_production_synthesis_is_the_control_base_table",
    "candidate_only_effect_is_local_changed_safe_verified_coordinate_edit",
    "candidate_has_no_independent_model_or_sampling_effect",
    "v25360_quote_coordinate_verifier_and_v25369_editor_replayed",
    "pre_effect_query_projection_precedes_first_search_or_fetch",
    "query4_fetch14_model3_physical_caps_enforced_before_effect",
    "invalid_missing_ambiguous_conflicting_or_unchanged_coordinate_is_noop",
    "schema_row_order_row_keys_and_other_cells_preserved",
    "page_text_treated_as_untrusted_data",
)
_FALSE_FLAGS = (
    "additional_model_call_for_candidate",
    "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
    "benchmark_launch_or_evaluator_authorized",
)


def _safe_failure(exc: BaseException) -> str:
    return paired_parent._safe_failure(exc)


def _empty_editor(
    *,
    base: str,
    columns: Sequence[str],
    question: str,
    first_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    visible_pages, _counts = bootstrap._grounded_visible_pages(first_pages)
    prepared = verifier.prepare_record_proposal(question, columns, visible_pages)
    return editor.apply_changed_safe_verified_coordinates(
        base_prediction=base,
        columns=columns,
        prepared=prepared,
        record_output='{"records":[]}',
        model_call_attempted=False,
    )


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    grounded = target_plan.validate_receipt(value["grounded_plan_receipt"])
    changed = editor.validate_receipt(value["changed_safe_edit_receipt"])
    first = value.get("first_wave_receipt")
    second = value.get("second_wave_receipt")
    budget = cap.validate_budget_receipt(value["outer_physical_budget_receipt"])
    failures = copy.deepcopy(dict(value["failure_types"]))
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        **{name: bool(value[name]) for name in _DYNAMIC_FLAGS},
        "base_normalizer_status": str(value["base_normalizer_status"]),
        "editor_failure_type": value["editor_failure_type"],
        "failure_types": failures,
        "grounded_plan_receipt": copy.deepcopy(grounded),
        "changed_safe_edit_receipt": copy.deepcopy(changed),
        "first_wave_receipt": copy.deepcopy(first),
        "second_wave_receipt": copy.deepcopy(second),
        "outer_physical_budget_receipt": copy.deepcopy(budget),
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    grounded = copied.get("grounded_plan_receipt")
    changed = copied.get("changed_safe_edit_receipt")
    first = copied.get("first_wave_receipt")
    second = copied.get("second_wave_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    failures = copied.get("failure_types")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *_DYNAMIC_FLAGS,
        "base_normalizer_status",
        "editor_failure_type",
        "failure_types",
        "grounded_plan_receipt",
        "changed_safe_edit_receipt",
        "first_wave_receipt",
        "second_wave_receipt",
        "outer_physical_budget_receipt",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in _DYNAMIC_FLAGS)
        or copied["planned_query_count"] != 4
        or copied["physical_query_count"] > cap.QUERY_CAP
        or copied["physical_fetch_count"] > cap.FETCH_CAP
        or copied["physical_model_forward_count"] > 3
        or copied["physical_model_forward_count"]
        != 1
        + int(copied["grounded_plan_model_call_attempted"])
        + int(copied["base_synthesis_attempted"])
        or copied["model_provider_request_count"]
        > copied["physical_model_forward_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied["input_provider_query_string_count"] > 4
        or copied["compatible_provider_query_seed_count"]
        > copied["input_provider_query_string_count"]
        or copied["transformed_or_rejected_provider_query_count"]
        > copied["input_provider_query_string_count"]
        or not 1 <= copied["emitted_query_seed_count"] <= 4
        or copied["visible_fallback_query_seed_used"]
        is not (
            copied["compatible_provider_query_seed_count"] == 0
            and copied["emitted_query_seed_count"] == 1
        )
        or copied.get("base_normalizer_status")
        not in {"not_attempted", "exact", "normalized", "unrecoverable"}
        or copied["base_synthesis_model_success"]
        and not copied["base_synthesis_attempted"]
        or copied["first_wave_completed"] is not (first is not None)
        or copied["second_wave_completed"] is not (second is not None)
        or copied["second_wave_completed"] and not copied["first_wave_completed"]
        or copied["grounded_plan_model_call_success"]
        and not copied["grounded_plan_model_call_attempted"]
        or not isinstance(grounded, Mapping)
        or target_plan.validate_receipt(grounded) != dict(grounded)
        or copied["grounded_plan_model_call_attempted"]
        is not grounded["model_call_attempted"]
        or copied["grounded_plan_strategy_applied"]
        is not grounded["strategy_applied"]
        or not isinstance(changed, Mapping)
        or editor.validate_receipt(changed) != dict(changed)
        or copied["changed_safe_coordinate_count"]
        != changed["changed_safe_coordinate_count"]
        or copied["base_table_exact_canonical"]
        is not changed["base_table_exact_canonical"]
        or copied["candidate_prediction_changed"]
        is not changed["candidate_prediction_changed"]
        or copied["candidate_identity_handoff"]
        is not changed["candidate_identity_handoff"]
        or copied["attributable_prediction_change"]
        is not bool(
            copied["base_synthesis_model_success"]
            and copied["candidate_prediction_changed"]
            and copied["changed_safe_coordinate_count"] > 0
        )
        or (first is not None and shared.validate_first_receipt(first) != dict(first))
        or (
            second is not None
            and frontier.validate_second_wave_receipt(second) != dict(second)
        )
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or copied["physical_query_count"] != budget["query_admitted_count"]
        or copied["physical_fetch_count"] != budget["fetch_admitted_count"]
        or copied["physical_model_forward_count"] != budget["model_admitted_count"]
        or budget["query_rejected_count"]
        + budget["fetch_rejected_count"]
        + budget["model_rejected_count"]
        != 0
        or not isinstance(failures, Mapping)
        or set(failures)
        != {"plan", "grounded_plan", "editor", "retrieval", "synthesis"}
        or set(failures.get("retrieval") or {}) != set(PHASES)
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for name, item in failures.items()
            if name != "retrieval"
        )
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for item in failures["retrieval"].values()
        )
        or copied["editor_validation_failed"]
        is not (copied.get("editor_failure_type") is not None)
        or copied.get("editor_failure_type") != failures["editor"]
        or copied.get("editor_failure_type") is not None
        and (
            not isinstance(copied["editor_failure_type"], str)
            or not copied["editor_failure_type"]
            or len(copied["editor_failure_type"]) > 128
        )
        or copied["control_prediction_characters"] <= 0
        or copied["candidate_prediction_characters"] <= 0
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.70 shared-synthesis receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = monotonic()
    visible = score.validate_visible_task(task)
    if not isinstance(budget, cap.PhysicalEffectBudget):
        raise ValueError("V2.53.70 requires one physical effect budget")
    initial_budget = cap.validate_budget_receipt(budget.receipt())
    if any(
        initial_budget[name] != 0
        for name in (
            "query_requested_count",
            "fetch_requested_count",
            "model_requested_count",
        )
    ):
        raise ValueError("V2.53.70 requires a pristine physical budget")
    if (
        not isinstance(model, cap.HardCappedModelLimiter)
        or model._budget is not budget
        or not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], cap.HardCappedSearchClient)
            or searches[phase]._budget is not budget
            or searches[phase]._phase != phase
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.53.70 hard-capped client wiring drifted")
    limits.validate()
    if (
        limits.wall_seconds != 240
        or limits.model_calls != 3
        or limits.search_queries != 4
        or limits.fetch_targets != 10
        or limits.search_results_per_query != 3
        or limits.evidence_chars != 60_000
        or limits.page_chars != 5_000
    ):
        raise ValueError("V2.53.70 production-shaped budget drifted")

    # Prove a valid visible-only fallback before any provider/search/fetch effect.
    plan, query_observation = query_parent.projected_plan(
        {}, visible["question"], limits
    )
    model_before = counters._counter(model, counters._MODEL_COUNTERS)
    search_before = {
        phase: counters._counter(searches[phase], counters._SEARCH_COUNTERS)
        for phase in PHASES
    }
    observers = {
        phase: compact._EffectObserver(searches[phase]) for phase in PHASES
    }
    failures: dict[str, Any] = {
        "plan": None,
        "grounded_plan": None,
        "editor": None,
        "retrieval": {phase: None for phase in PHASES},
        "synthesis": None,
    }
    try:
        response = model.complete(
            score.PLAN_SYSTEM,
            score.PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan, query_observation = query_parent.projected_plan(
            parse_json_object(counters._model_text(response)),
            visible["question"],
            limits,
        )
    except BaseException as exc:
        failures["plan"] = _safe_failure(exc)

    queries = list(plan["queries"])
    first: dict[str, Any] | None = None
    second: dict[str, Any] | None = None
    first_pages: list[dict[str, str]] = []
    try:
        first = shared._run_first_wave(
            queries[:2],
            search=observers[FIRST_PHASE],
            search_results_per_query=limits.search_results_per_query,
        )
        first_pages = counters._pages(first["page_batches"])
    except BaseException as exc:
        failures["retrieval"][FIRST_PHASE] = _safe_failure(exc)

    prepared_plan = target_plan.prepare_plan(
        visible["question"], plan["columns"], queries, first_pages
    )
    grounded_output = ""
    grounded_attempted = bool(first_pages)
    grounded_success = False
    if grounded_attempted:
        try:
            response = model.complete(
                bootstrap.joint_system(str(prepared_plan["system"])),
                str(prepared_plan["user"]),
                max_output_tokens=target_plan.PLAN_OUTPUT_TOKEN_CAP,
                json_mode=True,
            )
            grounded_output = counters._model_text(response)
            grounded_success = True
        except BaseException as exc:
            failures["grounded_plan"] = _safe_failure(exc)
    split = bootstrap._joint_output(grounded_output)
    grounded = target_plan.select_plan(
        prepared_plan,
        str(split["parent_output"]),
        model_call_attempted=grounded_attempted,
    )
    grounded_receipt = grounded["content_free_receipt"]

    second_pages = {arm: [] for arm in frontier.ARMS}
    if first is not None:
        try:
            second = frontier._run_second_wave(
                grounded["queries"],
                search=observers[SECOND_PHASE],
                first_wave_page_batches=first["page_batches"],
                plan=grounded,
                columns=plan["columns"],
                search_results_per_query=limits.search_results_per_query,
                exclude_urls=first["selected_urls"],
            )
            second_pages = {
                arm: copy.deepcopy(second["pages"][arm])
                for arm in frontier.ARMS
            }
        except BaseException as exc:
            failures["retrieval"][SECOND_PHASE] = _safe_failure(exc)
    else:
        failures["retrieval"][SECOND_PHASE] = "SharedFirstWaveFailure"

    pages = paired_parent._shared_union_pages(first_pages, second_pages)
    evidence = compact._compact_evidence(pages, limits)
    base_user = score.SYNTHESIS_USER.format(
        question=visible["question"],
        columns=json.dumps(plan["columns"], ensure_ascii=False),
        evidence=evidence,
    )
    base = counters._fallback(plan["columns"])
    synthesis_attempted = False
    synthesis_success = False
    normalizer_status = "not_attempted"
    if pages:
        synthesis_attempted = True
        try:
            response = model.complete(
                score.SYNTHESIS_SYSTEM,
                base_user,
                max_output_tokens=limits.synthesis_output_tokens,
                json_mode=False,
            )
            parsed, normalizer_status = robust._normalize_synthesis(
                counters._model_text(response),
                plan["columns"],
                visible["question"],
            )
            if parsed is None:
                raise ValueError("V2.53.70 base synthesis table contract failed")
            base = parsed
            synthesis_success = True
        except BaseException as exc:
            normalizer_status = "unrecoverable"
            failures["synthesis"] = _safe_failure(exc)

    edited: dict[str, Any]
    try:
        if not synthesis_success:
            edited = _empty_editor(
                base=base,
                columns=plan["columns"],
                question=visible["question"],
                first_pages=first_pages,
            )
        else:
            visible_pages, _page_counts = bootstrap._grounded_visible_pages(
                first_pages
            )
            prepared_records = verifier.prepare_record_proposal(
                visible["question"], plan["columns"], visible_pages
            )
            edited = editor.apply_changed_safe_verified_coordinates(
                base_prediction=base,
                columns=plan["columns"],
                prepared=prepared_records,
                record_output=str(split["record_output"]),
                model_call_attempted=bool(
                    grounded_attempted and split["records_member_present"]
                ),
            )
    except BaseException as exc:
        failures["editor"] = _safe_failure(exc)
        edited = _empty_editor(
            base=base,
            columns=plan["columns"],
            question=visible["question"],
            first_pages=first_pages,
        )
    edited = editor.validate_result(edited)
    edit_receipt = editor.validate_receipt(edited["content_free_receipt"])
    control = str(edited["control_prediction"])
    candidate = str(edited["candidate_prediction"])
    if control != base:
        raise RuntimeError("V2.53.70 editor control is not shared base")

    predictions = {CONTROL_ARM: control, CANDIDATE_ARM: candidate}
    model_success = {arm: synthesis_success for arm in ARMS}
    normalizers = {arm: normalizer_status for arm in ARMS}
    changed = control != candidate
    attributable = bool(
        synthesis_success
        and changed
        and edit_receipt["changed_safe_coordinate_count"] > 0
    )
    model_cost = counters._delta(
        counters._counter(model, counters._MODEL_COUNTERS), model_before
    )
    search_cost = {
        phase: counters._delta(
            counters._counter(searches[phase], counters._SEARCH_COUNTERS),
            search_before[phase],
        )
        for phase in PHASES
    }
    cost = {
        "model": model_cost,
        "search": search_cost,
        "system_total_tokens": model_cost["total_tokens"]
        + sum(search_cost[phase]["total_tokens"] for phase in PHASES),
    }
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    receipt = _receipt(
        {
            "planned_query_count": 4,
            "physical_query_count": budget_receipt["query_admitted_count"],
            "physical_fetch_count": budget_receipt["fetch_admitted_count"],
            "physical_model_forward_count": budget_receipt["model_admitted_count"],
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "system_total_tokens": cost["system_total_tokens"],
            "shared_page_count": len(pages),
            "base_production_prompt_characters": len(base_user),
            "control_prediction_characters": len(control),
            "candidate_prediction_characters": len(candidate),
            "input_provider_query_string_count": int(
                query_observation["input_provider_query_string_count"]
            ),
            "compatible_provider_query_seed_count": int(
                query_observation["compatible_provider_query_seed_count"]
            ),
            "transformed_or_rejected_provider_query_count": int(
                query_observation["transformed_or_rejected_provider_query_count"]
            ),
            "emitted_query_seed_count": int(
                query_observation["emitted_query_seed_count"]
            ),
            "changed_safe_coordinate_count": int(
                edit_receipt["changed_safe_coordinate_count"]
            ),
            "positive_signed_credit_count": 0,
            "first_wave_completed": first is not None,
            "grounded_plan_model_call_attempted": grounded_attempted,
            "grounded_plan_model_call_success": grounded_success,
            "grounded_plan_strategy_applied": grounded_receipt["strategy_applied"],
            "second_wave_completed": second is not None,
            "base_synthesis_attempted": synthesis_attempted,
            "base_synthesis_model_success": synthesis_success,
            "base_table_exact_canonical": edit_receipt["base_table_exact_canonical"],
            "candidate_prediction_changed": changed,
            "attributable_prediction_change": attributable,
            "candidate_identity_handoff": not changed,
            "visible_fallback_query_seed_used": bool(
                query_observation["visible_fallback_query_seed_used"]
            ),
            "editor_validation_failed": failures["editor"] is not None,
            "base_normalizer_status": normalizer_status,
            "editor_failure_type": failures["editor"],
            "failure_types": failures,
            "grounded_plan_receipt": grounded_receipt,
            "changed_safe_edit_receipt": edit_receipt,
            "first_wave_receipt": None if first is None else first["receipt"],
            "second_wave_receipt": None if second is None else second["receipt"],
            "outer_physical_budget_receipt": budget_receipt,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "model_success": model_success,
        "normalizer_status": normalizers,
        "failure_types": copy.deepcopy(failures),
        "prediction_changed": changed,
        "changed_safe_coordinate_count": int(
            edit_receipt["changed_safe_coordinate_count"]
        ),
        "attributable_prediction_change": attributable,
        "unattributable_prediction_change": False,
        "elapsed_seconds": round(max(0.0, monotonic() - started), 6),
        "cost": cost,
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    successes = copied.get("model_success")
    normalizers = copied.get("normalizer_status")
    failures = copied.get("failure_types")
    cost = copied.get("cost")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "predictions",
        "prediction_sha256",
        "model_success",
        "normalizer_status",
        "failure_types",
        "prediction_changed",
        "changed_safe_coordinate_count",
        "attributable_prediction_change",
        "unattributable_prediction_change",
        "elapsed_seconds",
        "cost",
        "content_free_receipt",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(copied.get("opaque_id"), str)
        or score.OPAQUE_ID.fullmatch(copied["opaque_id"]) is None
        or set(predictions or {}) != set(ARMS)
        or any(
            not isinstance(predictions[arm], str) or not predictions[arm]
            for arm in ARMS
        )
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or set(successes or {}) != set(ARMS)
        or any(not isinstance(successes[arm], bool) for arm in ARMS)
        or len(set(successes.values())) != 1
        or set(normalizers or {}) != set(ARMS)
        or len(set(normalizers.values())) != 1
        or not isinstance(failures, Mapping)
        or not isinstance(cost, Mapping)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or set(cost.get("model") or {}) != set(counters._MODEL_COUNTERS)
        or set(cost.get("search") or {}) != set(PHASES)
        or any(
            set(cost["search"][phase]) != set(counters._SEARCH_COUNTERS)
            for phase in PHASES
        )
        or cost["system_total_tokens"]
        != cost["model"]["total_tokens"]
        + sum(cost["search"][phase]["total_tokens"] for phase in PHASES)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["model_provider_request_count"] != cost["model"]["requests"]
        or receipt["model_provider_attempt_count"] != cost["model"]["attempts"]
        or receipt["system_total_tokens"] != cost["system_total_tokens"]
        or receipt["control_prediction_characters"]
        != len(predictions[CONTROL_ARM])
        or receipt["candidate_prediction_characters"]
        != len(predictions[CANDIDATE_ARM])
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or copied.get("changed_safe_coordinate_count")
        != receipt["changed_safe_coordinate_count"]
        or copied.get("attributable_prediction_change")
        is not receipt["attributable_prediction_change"]
        or copied.get("unattributable_prediction_change") is not False
        or failures != receipt["failure_types"]
        or any(
            successes[arm] is not receipt["base_synthesis_model_success"]
            or normalizers[arm] != receipt["base_normalizer_status"]
            for arm in ARMS
        )
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or copied["elapsed_seconds"] < 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.70 shared-synthesis result drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SECOND_PHASE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
]
