"""Checkpoint-protected runtime integration for the grounded fact bootstrap.

This build-only successor wraps the already hard-capped model limiter with a
type-compatible proxy.  The proxy intercepts exactly two *existing* call
sites: the grounded-plan call and the first production synthesis call.  It
adds no call.  The grounded response is split into a frozen-parent-compatible
four-member plan plus private fact proposals; at production time, proposals
are verified against the exact first-wave page subset shown to that grounded
call and only verified records may replace an equal-length prefix of the
existing evidence.

The V2.52.71 checkpoint machinery still runs and validates in memory.  Its
legacy result/receipt is deliberately not nested in the new output because
the legacy receipt describes an unchanged production prompt.  Instead this
module publishes a new finite content-free envelope binding the checkpoint,
physical effect counts, recovery disposition, and bootstrap receipt.

No filesystem, process, environment, network, credential, evaluator,
benchmark-label, mapping, gold, score, reward, or historical-result capability
is introduced.  Entropy/information gain remains shadow-only and assigns no
signed credit.  This module authorizes no external or benchmark launch.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v25135_sparse_production_runtime as sparse
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25271_validated_production_checkpoint_runtime as checkpoint
from . import v25346_grounded_fact_bootstrap as bootstrap
from .v24257_score_first_runtime import SYNTHESIS_SYSTEM, ScoreFirstLimits
from .v24259_deterministic_table_normalizer import _replace_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25347_checkpoint_grounded_fact_bootstrap_runtime_v1"
ROLE = "v25347_checkpoint_grounded_fact_bootstrap_runtime_result"
RECEIPT_ROLE = "v25347_content_free_checkpoint_grounded_fact_receipt"
PROXY_RECEIPT_ROLE = "v25347_content_free_grounded_fact_model_proxy_receipt"
STAGE_RECEIPT_ROLE = "v25347_content_free_checkpoint_grounded_fact_stage_receipt"


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


class GroundedFactModelProxy(DeadlineAwareGlobalModelSlotLimiter):
    """Type-compatible, zero-additional-call treatment proxy."""

    def __init__(
        self,
        inner: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
        first_wave_search: RobustLatePageBoundSearchClient,
    ) -> None:
        if not isinstance(inner, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.53.47 requires a bounded model limiter")
        if not isinstance(first_wave_search, RobustLatePageBoundSearchClient):
            raise TypeError("V2.53.47 requires the first-wave search client")
        self._inner_limiter = inner
        self._question = str(question)
        self._first_wave_search = first_wave_search
        self._raw_grounded_output = ""
        self._grounded_entry_count = 0
        self._production_entry_count = 0
        self._bootstrap_value: dict[str, Any] | None = None
        self._bootstrap_failure_type: str | None = None
        self._parent_production_user_characters = 0
        self._candidate_production_user_characters = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner_limiter, name)

    def remaining_effect_seconds(self) -> float:
        return float(self._inner_limiter.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._inner_limiter.receipt()

    def _first_wave_pages(self, production_user: str) -> list[dict[str, str]]:
        pages = sparse._prompt_pages(production_user)
        observed = self._first_wave_search.late_page_projection_receipt()
        count = observed.get("projected_page_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("V2.53.47 first-wave page count drifted")
        if count > len(pages):
            raise ValueError("V2.53.47 first-wave page count exceeds prompt")
        # V2.51.27 moves second-wave records before the shared first wave.
        return list(pages[len(pages) - count :]) if count else []

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        system_text = str(system)
        user_text = str(user)
        if system_text.startswith(sparse.target_plan.SYSTEM_PROMPT):
            self._grounded_entry_count += 1
            if self._grounded_entry_count != 1:
                raise ValueError("V2.53.47 duplicate grounded-plan entry")
            response = self._inner_limiter.complete(
                bootstrap.joint_system(system_text),
                user_text,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            self._raw_grounded_output = sparse.score._model_text(response)
            return _replace_text(
                response,
                bootstrap.parent_grounded_output(self._raw_grounded_output),
            )
        if system_text == SYNTHESIS_SYSTEM:
            self._production_entry_count += 1
            if self._production_entry_count != 1:
                raise ValueError("V2.53.47 unexpected delegated synthesis entry")
            forwarded = user_text
            self._parent_production_user_characters = len(user_text)
            try:
                columns = sparse._prompt_columns(user_text, ("Result",))
                self._bootstrap_value = bootstrap.build_bootstrap(
                    question=self._question,
                    columns=columns,
                    first_wave_pages=self._first_wave_pages(user_text),
                    grounded_model_output=self._raw_grounded_output,
                    production_user=user_text,
                    model_call_attempted=self._grounded_entry_count == 1,
                )
                forwarded = str(
                    self._bootstrap_value["candidate_production_user"]
                )
            except BaseException as exc:
                self._bootstrap_failure_type = _safe_failure(exc)
                self._bootstrap_value = None
                forwarded = user_text
            self._candidate_production_user_characters = len(forwarded)
            if len(forwarded) != len(user_text):
                raise RuntimeError("V2.53.47 production prompt length drifted")
            return self._inner_limiter.complete(
                system_text,
                forwarded,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        return self._inner_limiter.complete(
            system_text,
            user_text,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )

    def content_free_receipt(self) -> dict[str, Any]:
        raw = self._bootstrap_value
        component = (
            None
            if raw is None
            else bootstrap.validate_receipt(raw["content_free_receipt"])
        )
        changed = bool(
            component is not None
            and component["candidate_production_prompt_changed"]
        )
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": PROXY_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "grounded_plan_entry_count": self._grounded_entry_count,
            "production_synthesis_entry_count": self._production_entry_count,
            "additional_model_call_count": 0,
            "parent_production_user_characters": self._parent_production_user_characters,
            "candidate_production_user_characters": self._candidate_production_user_characters,
            "bootstrap_component_present": component is not None,
            "bootstrap_failure_present": self._bootstrap_failure_type is not None,
            "bootstrap_failure_type": self._bootstrap_failure_type,
            "candidate_production_prompt_changed": changed,
            "bootstrap_component_receipt": copy.deepcopy(component),
            "one_grounded_plan_and_one_production_call_delegated_at_most_once": True,
            "model_counter_and_deadline_receipt_delegate_to_inner_limiter": True,
            "bootstrap_failure_returns_parent_production_user_byte_exact": True,
            "additional_query_fetch_model_token_context_wall_or_network_budget": False,
            "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_proxy_receipt(value)


def validate_proxy_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    component = copied.get("bootstrap_component_receipt")
    failure = copied.get("bootstrap_failure_present") is True
    present = copied.get("bootstrap_component_present") is True
    true_flags = (
        "one_grounded_plan_and_one_production_call_delegated_at_most_once",
        "model_counter_and_deadline_receipt_delegate_to_inner_limiter",
        "bootstrap_failure_returns_parent_production_user_byte_exact",
    )
    false_flags = (
        "additional_query_fetch_model_token_context_wall_or_network_budget",
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    counts = (
        "grounded_plan_entry_count",
        "production_synthesis_entry_count",
        "additional_model_call_count",
        "parent_production_user_characters",
        "candidate_production_user_characters",
        "positive_signed_credit_count",
    )
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id", *counts,
            "bootstrap_component_present", "bootstrap_failure_present",
            "bootstrap_failure_type", "candidate_production_prompt_changed",
            "bootstrap_component_receipt", *true_flags, *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != PROXY_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["grounded_plan_entry_count"] not in {0, 1}
        or copied["production_synthesis_entry_count"] not in {0, 1}
        or copied["additional_model_call_count"] != 0
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(copied.get("bootstrap_component_present"), bool)
        or not isinstance(copied.get("bootstrap_failure_present"), bool)
        or not isinstance(copied.get("candidate_production_prompt_changed"), bool)
        or failure
        is not (
            isinstance(copied.get("bootstrap_failure_type"), str)
            and 0 < len(copied["bootstrap_failure_type"]) <= 128
        )
        or present and (
            not isinstance(component, Mapping)
            or bootstrap.validate_receipt(component) != dict(component)
        )
        or not present and component is not None
        or present and failure
        or copied["candidate_production_prompt_changed"]
        is not bool(
            present and component["candidate_production_prompt_changed"]
        )
        or copied["parent_production_user_characters"]
        != copied["candidate_production_user_characters"]
        or copied["candidate_production_prompt_changed"]
        and copied["production_synthesis_entry_count"] != 1
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.47 grounded fact proxy receipt drifted")
    return copied


def _integration_receipt(
    inner: Mapping[str, Any], proxy: Mapping[str, Any]
) -> dict[str, Any]:
    parent = checkpoint.validate_result(inner)
    checked_proxy = validate_proxy_receipt(proxy)
    parent_receipt = parent["content_free_receipt"]
    checkpoint_present = parent["production_checkpoint"] is not None
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "checkpoint_present": checkpoint_present,
        "checkpoint_provider_output_valid": bool(
            checkpoint_present
            and parent["production_checkpoint"]["production_provider_output_valid"]
        ),
        "checkpoint_recovery_event_present": bool(
            parent_receipt["post_checkpoint_recoverable_failure_present"]
        ),
        "checkpoint_recovery_disposition": str(
            parent_receipt["recovery_disposition"]
        ),
        "plan_provider_forward_count": parent_receipt[
            "plan_provider_forward_count"
        ],
        "grounded_plan_provider_forward_count": parent_receipt[
            "grounded_plan_provider_forward_count"
        ],
        "production_synthesis_provider_forward_count": parent_receipt[
            "production_synthesis_provider_forward_count"
        ],
        "revision_provider_forward_count": parent_receipt[
            "revision_provider_forward_count"
        ],
        "provider_forward_count": parent_receipt["provider_forward_count"],
        "model_provider_request_count": parent_receipt[
            "model_provider_request_count"
        ],
        "model_provider_attempt_count": parent_receipt[
            "model_provider_attempt_count"
        ],
        "physical_query_count": parent_receipt["physical_query_count"],
        "physical_fetch_count": parent_receipt["physical_fetch_count"],
        "physical_model_forward_count": parent_receipt[
            "physical_model_forward_count"
        ],
        "system_total_tokens": parent_receipt["system_total_tokens"],
        "microstage_failure_count": parent_receipt[
            "microstage_failure_count"
        ],
        "candidate_production_prompt_changed": checked_proxy[
            "candidate_production_prompt_changed"
        ],
        "grounded_fact_proxy_receipt": copy.deepcopy(checked_proxy),
        "checkpoint_runtime_validated_before_content_free_projection": True,
        "checkpoint_prediction_and_cost_preserved_in_outer_envelope": True,
        "legacy_prompt_unchanged_claim_not_reexported": True,
        "legacy_private_parent_envelope_not_persisted": True,
        "validated_checkpoint_never_replaced_by_visible_fallback": True,
        "additional_query_fetch_model_or_token_effect_for_bootstrap": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_answer_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    proxy = copied.get("grounded_fact_proxy_receipt")
    counts = (
        "plan_provider_forward_count", "grounded_plan_provider_forward_count",
        "production_synthesis_provider_forward_count",
        "revision_provider_forward_count", "provider_forward_count",
        "model_provider_request_count", "model_provider_attempt_count",
        "physical_query_count", "physical_fetch_count",
        "physical_model_forward_count", "system_total_tokens",
        "microstage_failure_count", "positive_signed_credit_count",
    )
    dynamic = (
        "checkpoint_present", "checkpoint_provider_output_valid",
        "checkpoint_recovery_event_present",
        "candidate_production_prompt_changed",
    )
    true_flags = (
        "checkpoint_runtime_validated_before_content_free_projection",
        "checkpoint_prediction_and_cost_preserved_in_outer_envelope",
        "legacy_prompt_unchanged_claim_not_reexported",
        "legacy_private_parent_envelope_not_persisted",
        "validated_checkpoint_never_replaced_by_visible_fallback",
    )
    false_flags = (
        "additional_query_fetch_model_or_token_effect_for_bootstrap",
        "contains_question_query_url_title_page_quote_record_identity_field_value_answer_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id", *dynamic,
            "checkpoint_recovery_disposition", *counts,
            "grounded_fact_proxy_receipt", *true_flags, *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic)
        or copied["checkpoint_recovery_disposition"]
        not in checkpoint.RECOVERY_DISPOSITIONS
        or copied["plan_provider_forward_count"] not in {0, 1}
        or copied["grounded_plan_provider_forward_count"] not in {0, 1}
        or copied["production_synthesis_provider_forward_count"] not in {0, 1}
        or copied["revision_provider_forward_count"] != 0
        or copied["provider_forward_count"]
        != copied["plan_provider_forward_count"]
        + copied["grounded_plan_provider_forward_count"]
        + copied["production_synthesis_provider_forward_count"]
        or copied["model_provider_request_count"]
        > copied["provider_forward_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or copied["physical_model_forward_count"]
        != copied["provider_forward_count"]
        or copied["physical_query_count"] > cap.QUERY_CAP
        or copied["physical_fetch_count"] > cap.FETCH_CAP
        or copied["physical_model_forward_count"] > cap.MODEL_CAP
        or copied["positive_signed_credit_count"] != 0
        or copied["checkpoint_provider_output_valid"]
        and not copied["checkpoint_present"]
        or copied["checkpoint_recovery_event_present"]
        is not copied["checkpoint_recovery_disposition"].endswith(
            "preserved_after_post_checkpoint_failure"
        )
        or not isinstance(proxy, Mapping)
        or validate_proxy_receipt(proxy) != dict(proxy)
        or copied["candidate_production_prompt_changed"]
        is not proxy["candidate_production_prompt_changed"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.47 integration receipt drifted")
    return copied


def _stage_receipt(
    parent_stage: Mapping[str, Any], proxy: Mapping[str, Any]
) -> dict[str, Any]:
    checked = checkpoint.validate_stage_receipt(parent_stage)
    checked_proxy = validate_proxy_receipt(proxy)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "checkpoint_stage_entered_counts": copy.deepcopy(
            checked["stage_entered_counts"]
        ),
        "checkpoint_stage_completed_counts": copy.deepcopy(
            checked["stage_completed_counts"]
        ),
        "checkpoint_stage_failure_types": copy.deepcopy(
            checked["stage_failure_types"]
        ),
        "checkpoint_failure_count": checked["failure_count"],
        "checkpoint_kind": checked["checkpoint_kind"],
        "checkpoint_recovery_disposition": checked["recovery_disposition"],
        "parent_result_retained": checked["parent_result_retained"],
        "outer_physical_budget_receipt": copy.deepcopy(
            checked["outer_physical_budget_receipt"]
        ),
        "candidate_production_prompt_changed": checked_proxy[
            "candidate_production_prompt_changed"
        ],
        "grounded_fact_proxy_receipt": copy.deepcopy(checked_proxy),
        "checkpoint_stage_validated_before_projection": True,
        "legacy_stage_prompt_claim_not_reexported": True,
        "additional_query_fetch_model_or_token_effect_for_bootstrap": False,
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    entered = copied.get("checkpoint_stage_entered_counts")
    completed = copied.get("checkpoint_stage_completed_counts")
    failures = copied.get("checkpoint_stage_failure_types")
    budget = copied.get("outer_physical_budget_receipt")
    proxy = copied.get("grounded_fact_proxy_receipt")
    true_flags = (
        "checkpoint_stage_validated_before_projection",
        "legacy_stage_prompt_claim_not_reexported",
    )
    false_flags = (
        "additional_query_fetch_model_or_token_effect_for_bootstrap",
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id",
            "checkpoint_stage_entered_counts",
            "checkpoint_stage_completed_counts",
            "checkpoint_stage_failure_types", "checkpoint_failure_count",
            "checkpoint_kind", "checkpoint_recovery_disposition",
            "parent_result_retained", "outer_physical_budget_receipt",
            "candidate_production_prompt_changed",
            "grounded_fact_proxy_receipt", *true_flags, *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(entered, Mapping)
        or not isinstance(completed, Mapping)
        or not isinstance(failures, Mapping)
        or set(entered) != set(checkpoint.STAGES)
        or set(completed) != set(checkpoint.STAGES)
        or set(failures) != set(checkpoint.STAGES)
        or copied.get("checkpoint_failure_count")
        != sum(failures[name] is not None for name in checkpoint.STAGES)
        or copied.get("checkpoint_kind") is not None
        and copied["checkpoint_kind"] not in checkpoint.CHECKPOINT_KINDS
        or copied.get("checkpoint_recovery_disposition")
        not in checkpoint.RECOVERY_DISPOSITIONS
        or not isinstance(copied.get("parent_result_retained"), bool)
        or not isinstance(copied.get("candidate_production_prompt_changed"), bool)
        or not isinstance(proxy, Mapping)
        or validate_proxy_receipt(proxy) != dict(proxy)
        or copied["candidate_production_prompt_changed"]
        is not proxy["candidate_production_prompt_changed"]
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.47 stage receipt drifted")
    return copied


def _build_result(
    inner: Mapping[str, Any],
    proxy_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    parent = checkpoint.validate_result(inner)
    checked_proxy = validate_proxy_receipt(proxy_receipt)
    raw_checkpoint = parent["production_checkpoint"]
    checked_checkpoint = (
        None
        if raw_checkpoint is None
        else checkpoint.validate_checkpoint(raw_checkpoint)
    )
    receipt = _integration_receipt(parent, checked_proxy)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": parent["opaque_id"],
        "status": "terminal",
        "prediction": parent["prediction"],
        "prediction_sha256": parent["prediction_sha256"],
        "prediction_kind": parent["prediction_kind"],
        "production_checkpoint": copy.deepcopy(checked_checkpoint),
        "production_checkpoint_payload_sha256": (
            None
            if checked_checkpoint is None
            else checked_checkpoint["checkpoint_payload_sha256"]
        ),
        "cost": copy.deepcopy(parent["cost"]),
        "inner_checkpoint_result_payload_sha256": parent[
            "result_payload_sha256"
        ],
        "inner_checkpoint_result_role": parent["role"],
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
    prediction = copied.get("prediction")
    raw_checkpoint = copied.get("production_checkpoint")
    receipt = copied.get("content_free_receipt")
    cost = copied.get("cost")
    if (
        set(copied)
        != {
            "artifact_version", "role", "policy_id", "opaque_id", "status",
            "prediction", "prediction_sha256", "prediction_kind",
            "production_checkpoint", "production_checkpoint_payload_sha256",
            "cost", "inner_checkpoint_result_payload_sha256",
            "inner_checkpoint_result_role", "content_free_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized", "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(copied.get("opaque_id"), str)
        or sparse.score.OPAQUE_ID.fullmatch(copied["opaque_id"]) is None
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("prediction_sha256")
        != hashlib.sha256(prediction.encode()).hexdigest()
        or copied.get("prediction_kind")
        not in {"model_generated", "fallback", "visible_fallback"}
        or not isinstance(cost, Mapping)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or not isinstance(cost.get("model"), Mapping)
        or set(cost["model"]) != set(sparse._MODEL_COUNTERS)
        or set(cost.get("search") or {}) != set(checkpoint.PHASES)
        or any(
            not isinstance(cost["search"].get(phase), Mapping)
            or set(cost["search"][phase]) != set(sparse._SEARCH_COUNTERS)
            for phase in checkpoint.PHASES
        )
        or cost["system_total_tokens"]
        != cost["model"]["total_tokens"]
        + sum(cost["search"][phase]["total_tokens"] for phase in checkpoint.PHASES)
        or not isinstance(
            copied.get("inner_checkpoint_result_payload_sha256"), str
        )
        or len(copied["inner_checkpoint_result_payload_sha256"]) != 64
        or copied.get("inner_checkpoint_result_role")
        not in {checkpoint.ROLE, checkpoint.RECOVERY_ROLE}
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["model_provider_request_count"]
        != cost["model"]["requests"]
        or receipt["model_provider_attempt_count"]
        != cost["model"]["attempts"]
        or receipt["system_total_tokens"] != cost["system_total_tokens"]
        or receipt["checkpoint_present"] is not (raw_checkpoint is not None)
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
        raise ValueError("V2.53.47 result envelope drifted")
    if raw_checkpoint is not None:
        if not isinstance(raw_checkpoint, Mapping):
            raise ValueError("V2.53.47 checkpoint envelope drifted")
        checked = checkpoint.validate_checkpoint(raw_checkpoint)
        if (
            copied["production_checkpoint_payload_sha256"]
            != checked["checkpoint_payload_sha256"]
            or prediction != checked["prediction"]
            or copied["prediction_kind"]
            != (
                "model_generated"
                if checked["production_provider_output_valid"]
                else "fallback"
            )
            or receipt["checkpoint_provider_output_valid"]
            is not checked["production_provider_output_valid"]
        ):
            raise ValueError("V2.53.47 checkpoint binding drifted")
    elif (
        copied.get("production_checkpoint_payload_sha256") is not None
        or copied["prediction_kind"] != "visible_fallback"
    ):
        raise ValueError("V2.53.47 visible fallback binding drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = sparse._validate_boundary(
        task, model=model, searches=searches, limits=limits
    )
    proxy = GroundedFactModelProxy(
        model,
        question=visible["question"],
        first_wave_search=searches[sparse.FIRST_PHASE],
    )
    parent, parent_stage = checkpoint.run_task(
        visible,
        model=proxy,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    checked_parent = checkpoint.validate_result(parent)
    checked_parent_stage = checkpoint.validate_stage_receipt(parent_stage)
    proxy_receipt = proxy.content_free_receipt()
    return _build_result(checked_parent, proxy_receipt), _stage_receipt(
        checked_parent_stage, proxy_receipt
    )


__all__ = [
    "GroundedFactModelProxy", "POLICY_ID", "PROXY_RECEIPT_ROLE",
    "RECEIPT_ROLE", "ROLE", "STAGE_RECEIPT_ROLE", "run_task",
    "validate_proxy_receipt", "validate_receipt", "validate_result",
    "validate_stage_receipt",
]
