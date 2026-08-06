"""Concurrency-safe integration of the expanded visible-schema parser.

The frozen V2.43.18/V2.43.19/V2.46.30 stack imports its parser as a module
global.  Replacing that global during a 20-way run would create cross-task
state and race-dependent routing.  This successor instead creates a private
function namespace for one treated task.  The frozen path is called directly
whenever it already parses a schema or the expanded parser also abstains.

The only treatment is an explicit visible-schema parse.  Model, query, fetch,
token, deadline, search, title-backfill, fallback, and evaluator behavior are
unchanged.  The runtime boundary remains exactly ``{opaque_id, question}``.
"""

from __future__ import annotations

import copy
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from . import v24318_deadline_conservation_runtime as conservation
from . import v24319_runner_integration as runner
from . import v24630_exact220_task_integration as exact
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24294_staged_reserve import StagedReservePolicy
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24675_expanded_visible_schema import extract_expanded_visible_columns


POLICY_ID = "v24677_concurrency_safe_expanded_visible_schema_v1"
RECEIPT_ROLE = "v24677_expanded_visible_schema_transition_receipt"
ENVELOPE_ROLE = "v24677_expanded_visible_schema_exact220_task_envelope"


@dataclass(frozen=True)
class ExpandedConservationOutcome:
    result: dict[str, Any]
    schema_transition_receipt: dict[str, Any]


@dataclass(frozen=True)
class ExpandedExact220TaskOutcome:
    result: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    citation_title_backfill_receipt: dict[str, Any]
    schema_transition_receipt: dict[str, Any]


def _clone_function(
    function: Callable[..., Any], replacements: Mapping[str, Any], *, name: str
) -> Callable[..., Any]:
    namespace = dict(function.__globals__)
    namespace.update(dict(replacements))
    cloned = types.FunctionType(
        function.__code__,
        namespace,
        name=name,
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    cloned.__annotations__ = dict(function.__annotations__)
    return cloned


def _transition(question: str) -> tuple[list[str], list[str], dict[str, Any]]:
    frozen = extract_robust_visible_columns(question)
    expanded = extract_expanded_visible_columns(question)
    if frozen and expanded != frozen:
        raise ValueError("V2.46.77 changed a frozen nonempty schema")
    incremental = not frozen and bool(expanded)
    status = (
        "incremental_explicit_schema"
        if incremental
        else "frozen_schema_preserved"
        if frozen
        else "no_unambiguous_explicit_schema"
    )
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "status": status,
        "frozen_parser_column_count": len(frozen),
        "expanded_parser_column_count": len(expanded),
        "incremental_schema_applied": incremental,
        "frozen_nonempty_schema_preserved_exactly": not frozen or expanded == frozen,
        "function_namespace_is_task_local": True,
        "module_global_parser_mutated": False,
        "model_query_fetch_token_deadline_or_search_policy_changed": False,
        "question_column_name_opaque_id_query_url_page_prediction_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return frozen, expanded, validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    frozen = copied.get("frozen_parser_column_count")
    expanded = copied.get("expanded_parser_column_count")
    incremental = copied.get("incremental_schema_applied")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "status",
        "frozen_parser_column_count",
        "expanded_parser_column_count",
        "incremental_schema_applied",
        "frozen_nonempty_schema_preserved_exactly",
        "function_namespace_is_task_local",
        "module_global_parser_mutated",
        "model_query_fetch_token_deadline_or_search_policy_changed",
        "question_column_name_opaque_id_query_url_page_prediction_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(frozen, bool)
        or not isinstance(frozen, int)
        or frozen < 0
        or isinstance(expanded, bool)
        or not isinstance(expanded, int)
        or expanded < 0
        or not isinstance(incremental, bool)
        or copied.get("status")
        not in {
            "incremental_explicit_schema",
            "frozen_schema_preserved",
            "no_unambiguous_explicit_schema",
        }
        or (copied["status"] == "incremental_explicit_schema")
        is not (frozen == 0 and expanded > 0 and incremental)
        or (copied["status"] == "frozen_schema_preserved")
        is not (frozen > 0 and expanded == frozen and not incremental)
        or (copied["status"] == "no_unambiguous_explicit_schema")
        is not (frozen == expanded == 0 and not incremental)
        or copied.get("frozen_nonempty_schema_preserved_exactly") is not True
        or copied.get("function_namespace_is_task_local") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "module_global_parser_mutated",
                "model_query_fetch_token_deadline_or_search_policy_changed",
                "question_column_name_opaque_id_query_url_page_prediction_or_credential_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.77 schema transition receipt drifted")
    return copied


def _isolated_conservation_task() -> Callable[..., dict[str, Any]]:
    isolated_parent = _clone_function(
        conservation._run_parent,
        {"extract_robust_visible_columns": extract_expanded_visible_columns},
        name="v24677_task_local_expanded_run_parent",
    )
    return _clone_function(
        conservation.run_v24318_task,
        {"_run_parent": isolated_parent},
        name="v24677_task_local_expanded_conservation_task",
    )


def run_v24677_conservation_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> ExpandedConservationOutcome:
    visible = validate_visible_task(task)
    _frozen, _expanded, receipt = _transition(visible["question"])
    function = (
        _isolated_conservation_task()
        if receipt["incremental_schema_applied"]
        else conservation.run_v24318_task
    )
    result = function(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        reserve_policy=reserve_policy,
        monotonic=monotonic,
        progress=progress,
    )
    conservation.validate_v24318_result(result, arm)
    return ExpandedConservationOutcome(copy.deepcopy(result), receipt)


def _isolated_exact_task(
    receipt_sink: list[dict[str, Any]],
) -> Callable[..., exact.IntegratedExact220TaskOutcome]:
    def treated_conservation(
        task: Mapping[str, Any],
        *,
        arm: str,
        model: Any,
        search: Any,
        limits: ScoreFirstLimits,
        two_wave_policy: TwoWavePolicy,
        reserve_policy: StagedReservePolicy | None = None,
        monotonic: Callable[[], float],
        progress: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        outcome = run_v24677_conservation_task(
            task,
            arm=arm,
            model=model,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            reserve_policy=reserve_policy,
            monotonic=monotonic,
            progress=progress,
        )
        receipt_sink.append(outcome.schema_transition_receipt)
        return outcome.result

    isolated_runner = _clone_function(
        runner.run_v24319_task,
        {"run_v24318_task": treated_conservation},
        name="v24677_task_local_expanded_runner_task",
    )
    return _clone_function(
        exact.run_v24630_task,
        {"run_v24319_task": isolated_runner},
        name="v24677_task_local_expanded_exact220_task",
    )


def run_v24677_exact220_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> ExpandedExact220TaskOutcome:
    visible = validate_visible_task(task)
    if arm != "baseline":
        raise ValueError("V2.46.77 exact220 integration requires the frozen baseline arm")
    _frozen, _expanded, precomputed = _transition(visible["question"])
    if precomputed["incremental_schema_applied"]:
        receipts: list[dict[str, Any]] = []
        parent = _isolated_exact_task(receipts)(
            visible,
            arm=arm,
            model=model,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            monotonic=monotonic,
            progress=progress,
        )
        if len(receipts) != 1 or receipts[0] != precomputed:
            raise RuntimeError("V2.46.77 task-local treatment receipt drifted")
        receipt = receipts[0]
    else:
        parent = exact.run_v24630_task(
            visible,
            arm=arm,
            model=model,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            monotonic=monotonic,
            progress=progress,
        )
        receipt = precomputed
    exact.validate_cross_artifacts(
        parent.result,
        arm=arm,
        model_slot_receipt=parent.model_slot_receipt,
        transport_health=parent.transport_health,
        search_single_shot_receipt=parent.search_single_shot_receipt,
        citation_title_backfill_receipt=parent.citation_title_backfill_receipt,
        expected_cap=int(parent.model_slot_receipt["slot_cap"]),
    )
    return ExpandedExact220TaskOutcome(
        copy.deepcopy(parent.result),
        copy.deepcopy(parent.model_slot_receipt),
        copy.deepcopy(parent.transport_health),
        copy.deepcopy(parent.search_single_shot_receipt),
        copy.deepcopy(parent.citation_title_backfill_receipt),
        copy.deepcopy(receipt),
    )


def build_envelope(
    outcome: ExpandedExact220TaskOutcome, *, arm: str
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": POLICY_ID,
        "arm": arm,
        "result": copy.deepcopy(outcome.result),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "citation_title_backfill_receipt": copy.deepcopy(
            outcome.citation_title_backfill_receipt
        ),
        "schema_transition_receipt": copy.deepcopy(
            outcome.schema_transition_receipt
        ),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_evaluator_called_by_envelope_builder": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    return validate_envelope(value)


def validate_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("envelope_payload_sha256", None)
    model = copied.get("model_slot_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "arm",
        "result",
        "model_slot_receipt",
        "transport_health",
        "search_single_shot_receipt",
        "citation_title_backfill_receipt",
        "schema_transition_receipt",
        "private_task_content_present",
        "private_task_content_emitted_to_public_aggregate",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_evaluator_called_by_envelope_builder",
        "envelope_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ENVELOPE_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("arm") != "baseline"
        or not isinstance(model, Mapping)
        or not isinstance(copied.get("result"), Mapping)
        or copied.get("private_task_content_present") is not True
        or copied.get("private_task_content_emitted_to_public_aggregate") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_evaluator_called_by_envelope_builder") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.77 exact220 task envelope drifted")
    validate_receipt(copied["schema_transition_receipt"])
    exact.validate_cross_artifacts(
        copied["result"],
        arm="baseline",
        model_slot_receipt=model,
        transport_health=copied["transport_health"],
        search_single_shot_receipt=copied["search_single_shot_receipt"],
        citation_title_backfill_receipt=copied[
            "citation_title_backfill_receipt"
        ],
        expected_cap=int(model.get("slot_cap", -1)),
    )
    return copied


__all__ = [
    "ENVELOPE_ROLE",
    "ExpandedConservationOutcome",
    "ExpandedExact220TaskOutcome",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "build_envelope",
    "run_v24677_conservation_task",
    "run_v24677_exact220_task",
    "validate_envelope",
    "validate_receipt",
]
