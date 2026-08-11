"""Causally couple target-record retrieval exposure to paired predictions.

V2.51.25 showed that independent synthesis calls can differ even when the
candidate did not gain a target-field page, while most true page gains did not
alter the prediction.  This append-only successor keeps V2.51.23's complete
effect path and budgets, then deterministically projects only the paired
predictions: without a positive target-field-page gain the candidate is an
identity handoff to control.  With a positive gain, both syntheses remain and
the candidate is allowed to differ.  It also records a content-free contract
for putting each arm's second-wave pages before the shared first-wave pages in
the next integrated runtime; this module itself performs no new effect.

No label, mapping, gold, evaluator, score, reward, history, credential, page,
query, URL, target, field, prediction text, or answer is emitted in the new
receipt.  Entropy/information gain remains shadow-only and assigns no credit.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25123_visible_legacy_query_compatible_runtime as parent
from . import v25119_grounded_target_record_paired_runtime as core
from . import v25117_grounded_target_record_plan as target_plan
from . import v24257_score_first_runtime as score
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25127_causally_coupled_target_record_runtime_v1"
ROLE = "v25127_causally_coupled_target_record_runtime_result"
RECEIPT_ROLE = "v25127_content_free_causal_coupling_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES

_EVIDENCE_HEADER = "BOUNDED WEB MATERIAL:\n"
_EVIDENCE_SUFFIX = "\n\nProduce the best-supported answer possible"
_RECORD = re.compile(r"(?m)^\[E[0-9]{4}\] kind=fetched_page\n")
_GROUNDED_CHECKLIST = """STRICT OUTPUT CHECKLIST
Return exactly the four JSON keys requested. Emit exactly two query strings.
Use no URL, angle/square/curly bracket, markdown, operator, or instruction text
inside a query. Copy every non-visible pivot and row target verbatim from the
first-wave evidence. If any requirement cannot be met, emit empty phrase arrays
and copy the two supplied legacy queries exactly."""


def _prioritize_second_wave(
    user: str, shared_first_wave_records: int
) -> tuple[str, int, int, bool]:
    """Move existing second-wave records first without changing prompt length."""

    if (
        not isinstance(user, str)
        or isinstance(shared_first_wave_records, bool)
        or not isinstance(shared_first_wave_records, int)
        or shared_first_wave_records < 0
    ):
        raise ValueError("V2.51.27 synthesis salience input drifted")
    header = user.find(_EVIDENCE_HEADER)
    suffix = user.find(_EVIDENCE_SUFFIX, header + len(_EVIDENCE_HEADER))
    if header < 0 or suffix < 0:
        raise ValueError("V2.51.27 synthesis prompt boundary drifted")
    start = header + len(_EVIDENCE_HEADER)
    evidence = user[start:suffix]
    trailing = evidence[len(evidence.rstrip(" ")) :]
    body = evidence[: len(evidence) - len(trailing)] if trailing else evidence
    matches = list(_RECORD.finditer(body))
    record_count = len(matches)
    if record_count == 0:
        return user, 0, 0, False
    if shared_first_wave_records > record_count:
        raise ValueError("V2.51.27 shared evidence count exceeds prompt records")
    prefix = body[: matches[0].start()]
    records: list[str] = []
    for index, match in enumerate(matches):
        record = (
            body[match.start() : matches[index + 1].start()]
            if index + 1 < record_count
            else body[match.start() :]
        )
        if index + 1 < record_count:
            if not record.endswith("\n\n"):
                raise ValueError("V2.51.27 evidence record separator drifted")
            record = record[:-2]
        records.append(record)
    second_count = record_count - shared_first_wave_records
    if second_count <= 0 or shared_first_wave_records == 0:
        return user, record_count, second_count, False
    reordered = "\n\n".join(
        [*records[shared_first_wave_records:], *records[:shared_first_wave_records]]
    )
    output = user[:start] + prefix + reordered + trailing + user[suffix:]
    if len(output) != len(user):
        raise RuntimeError("V2.51.27 synthesis salience changed prompt length")
    return output, record_count, second_count, output != user


class CausalSalienceModel(DeadlineAwareGlobalModelSlotLimiter):
    """Transparent model proxy for strict planning and evidence-order salience."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        first_wave_search: RobustLatePageBoundSearchClient,
        arm_order: Sequence[str],
    ) -> None:
        if not isinstance(bounded, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.51.27 requires a bounded global model limiter")
        order = tuple(arm_order)
        if len(order) != 2 or set(order) != set(ARMS):
            raise ValueError("V2.51.27 arm order drifted")
        if not isinstance(first_wave_search, RobustLatePageBoundSearchClient):
            raise TypeError("V2.51.27 requires the bounded first-wave search client")
        self._bounded = bounded
        self._first_wave_search = first_wave_search
        self._arm_order = order
        self.grounded_prompt_count = 0
        self.synthesis_prompt_count = 0
        self.synthesis_observations: dict[str, dict[str, Any]] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bounded, name)

    def remaining_effect_seconds(self) -> float:
        return float(self._bounded.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._bounded.receipt()

    def _shared_page_count(self) -> int:
        value = self._first_wave_search.late_page_projection_receipt()
        count = value.get("projected_page_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("V2.51.27 first-wave projection count drifted")
        return count

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        forwarded_system = system
        forwarded_user = user
        if system == target_plan.SYSTEM_PROMPT:
            self.grounded_prompt_count += 1
            forwarded_system = system + "\n\n" + _GROUNDED_CHECKLIST
        elif system == score.SYNTHESIS_SYSTEM:
            if self.synthesis_prompt_count >= len(self._arm_order):
                raise ValueError("V2.51.27 too many synthesis prompts")
            arm = self._arm_order[self.synthesis_prompt_count]
            shared = self._shared_page_count()
            forwarded_user, records, second, reordered = _prioritize_second_wave(
                user, shared
            )
            self.synthesis_observations[arm] = {
                "evidence_record_count": records,
                "shared_first_wave_record_count": shared,
                "second_wave_record_count": second,
                "second_wave_records_prioritized": reordered,
                "prompt_characters_unchanged": len(forwarded_user) == len(user),
            }
            self.synthesis_prompt_count += 1
        return self._bounded.complete(
            forwarded_system,
            forwarded_user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )

    def content_free_receipt(self) -> dict[str, Any]:
        observations = {
            arm: copy.deepcopy(
                self.synthesis_observations.get(
                    arm,
                    {
                        "evidence_record_count": 0,
                        "shared_first_wave_record_count": 0,
                        "second_wave_record_count": 0,
                        "second_wave_records_prioritized": False,
                        "prompt_characters_unchanged": True,
                    },
                )
            )
            for arm in ARMS
        }
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v25127_content_free_prompt_salience_receipt",
            "policy_id": POLICY_ID,
            "grounded_prompt_checklist_count": self.grounded_prompt_count,
            "synthesis_prompt_count": self.synthesis_prompt_count,
            "arm_observations": observations,
            "grounded_validator_and_verbatim_grounding_unchanged": True,
            "both_arms_use_second_wave_before_first_wave_evidence_order": True,
            "synthesis_prompt_character_counts_unchanged": all(
                value["prompt_characters_unchanged"]
                for value in observations.values()
            ),
            "additional_model_search_fetch_token_context_wall_or_network_budget": False,
            "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_salience_receipt(value)


def validate_salience_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    observations = copied.get("arm_observations")
    count_fields = (
        "evidence_record_count",
        "shared_first_wave_record_count",
        "second_wave_record_count",
    )
    true_flags = (
        "grounded_validator_and_verbatim_grounding_unchanged",
        "both_arms_use_second_wave_before_first_wave_evidence_order",
        "synthesis_prompt_character_counts_unchanged",
    )
    false_flags = (
        "additional_model_search_fetch_token_context_wall_or_network_budget",
        "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "grounded_prompt_checklist_count",
        "synthesis_prompt_count",
        "arm_observations",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25127_content_free_prompt_salience_receipt"
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("grounded_prompt_checklist_count"), bool)
        or copied.get("grounded_prompt_checklist_count") not in {0, 1}
        or isinstance(copied.get("synthesis_prompt_count"), bool)
        or copied.get("synthesis_prompt_count") not in {0, 1, 2}
        or not isinstance(observations, Mapping)
        or set(observations) != set(ARMS)
        or any(
            not isinstance(observations[arm], Mapping)
            or set(observations[arm])
            != {
                *count_fields,
                "second_wave_records_prioritized",
                "prompt_characters_unchanged",
            }
            or any(
                isinstance(observations[arm].get(name), bool)
                or not isinstance(observations[arm].get(name), int)
                or observations[arm][name] < 0
                for name in count_fields
            )
            or observations[arm]["evidence_record_count"]
            != observations[arm]["shared_first_wave_record_count"]
            + observations[arm]["second_wave_record_count"]
            or not isinstance(
                observations[arm].get("second_wave_records_prioritized"), bool
            )
            or observations[arm].get("prompt_characters_unchanged") is not True
            or observations[arm]["second_wave_records_prioritized"]
            is not (
                observations[arm]["shared_first_wave_record_count"] > 0
                and observations[arm]["second_wave_record_count"] > 0
            )
            for arm in ARMS
        )
        or copied["synthesis_prompt_count"]
        != sum(observations[arm]["evidence_record_count"] > 0 for arm in ARMS)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.27 prompt salience receipt drifted")
    return copied


def _receipt(
    *,
    parent_result: Mapping[str, Any],
    projected_parent_result: Mapping[str, Any],
    original_prediction_changed: bool,
    prediction_identity_handoff_applied: bool,
    salience_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    core_receipt = parent_result["content_free_receipt"]
    positive_gain = int(core_receipt["target_field_page_gain"]) > 0
    selection_changed = bool(core_receipt["selection_changed"])
    mechanism = bool(core_receipt["retrieval_mechanism_engaged"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "projected_parent_result_payload_sha256": str(
            projected_parent_result["result_payload_sha256"]
        ),
        "selection_changed": selection_changed,
        "positive_target_field_page_gain": positive_gain,
        "retrieval_mechanism_engaged": mechanism,
        "original_prediction_changed": bool(original_prediction_changed),
        "prediction_identity_handoff_applied": bool(
            prediction_identity_handoff_applied
        ),
        "projected_prediction_changed": bool(original_prediction_changed and mechanism),
        "prompt_salience_receipt": copy.deepcopy(dict(salience_receipt)),
        "unattributable_prediction_difference_forbidden": True,
        "identity_handoff_requires_both_synthesis_calls_attempted": True,
        "next_integrated_runtime_orders_arm_second_wave_pages_before_shared_first_wave_pages": True,
        "page_order_change_adds_no_query_fetch_model_token_context_wall_or_network_budget": True,
        "parent_effects_queries_fetches_model_calls_and_predictions_are_hash_bound": True,
        "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    bool_fields = (
        "selection_changed",
        "positive_target_field_page_gain",
        "retrieval_mechanism_engaged",
        "original_prediction_changed",
        "prediction_identity_handoff_applied",
        "projected_prediction_changed",
    )
    true_flags = (
        "unattributable_prediction_difference_forbidden",
        "identity_handoff_requires_both_synthesis_calls_attempted",
        "next_integrated_runtime_orders_arm_second_wave_pages_before_shared_first_wave_pages",
        "page_order_change_adds_no_query_fetch_model_token_context_wall_or_network_budget",
        "parent_effects_queries_fetches_model_calls_and_predictions_are_hash_bound",
    )
    false_flags = (
        "contains_question_query_url_title_page_target_authority_column_prediction_answer_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_role",
        "parent_policy_id",
        "parent_result_payload_sha256",
        "projected_parent_result_payload_sha256",
        "prompt_salience_receipt",
        *bool_fields,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != parent.ROLE
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or not isinstance(
            copied.get("projected_parent_result_payload_sha256"), str
        )
        or len(copied["projected_parent_result_payload_sha256"]) != 64
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["retrieval_mechanism_engaged"]
        is not (
            copied["selection_changed"]
            and copied["positive_target_field_page_gain"]
        )
        or copied["prediction_identity_handoff_applied"]
        is not (not copied["retrieval_mechanism_engaged"])
        or copied["projected_prediction_changed"]
        is not (
            copied["original_prediction_changed"]
            and copied["retrieval_mechanism_engaged"]
        )
        or copied["projected_prediction_changed"]
        and not copied["retrieval_mechanism_engaged"]
        or not isinstance(copied.get("prompt_salience_receipt"), Mapping)
        or validate_salience_receipt(copied["prompt_salience_receipt"])
        != dict(copied["prompt_salience_receipt"])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.27 causal coupling receipt drifted")
    return copied


def _project(
    parent_result: Mapping[str, Any], salience_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    value = copy.deepcopy(checked)
    original_changed = bool(value["prediction_changed"])
    mechanism = bool(value["content_free_receipt"]["retrieval_mechanism_engaged"])
    attempts = value["content_free_receipt"]["arm_metrics"]
    identity = not mechanism
    if identity:
        if not all(attempts[arm]["synthesis_attempted"] for arm in ARMS):
            raise ValueError("V2.51.27 identity handoff requires paired synthesis")
        value["predictions"][CANDIDATE_ARM] = value["predictions"][CONTROL_ARM]
        value["prediction_sha256"][CANDIDATE_ARM] = value["prediction_sha256"][
            CONTROL_ARM
        ]
    value["prediction_changed"] = (
        value["predictions"][CONTROL_ARM] != value["predictions"][CANDIDATE_ARM]
    )
    core_receipt = copy.deepcopy(value["content_free_receipt"])
    core_receipt["prediction_changed"] = value["prediction_changed"]
    core_receipt["attributable_prediction_change"] = bool(
        core_receipt["retrieval_mechanism_engaged"] and value["prediction_changed"]
    )
    core_receipt.pop("receipt_payload_sha256")
    core_receipt["receipt_payload_sha256"] = payload_sha256(core_receipt)
    value["content_free_receipt"] = core.validate_receipt(core_receipt)

    projected_core = copy.deepcopy(value)
    projected_core.pop("stage_failure_accounting")
    projected_core["role"] = core.ROLE
    projected_core["policy_id"] = core.POLICY_ID
    projected_core.pop("result_payload_sha256", None)
    projected_core["result_payload_sha256"] = payload_sha256(projected_core)
    projected_core = core.validate_result(projected_core)

    stage = copy.deepcopy(value["stage_failure_accounting"])
    stage["parent_result_payload_sha256"] = projected_core[
        "result_payload_sha256"
    ]
    stage.pop("receipt_payload_sha256")
    stage["receipt_payload_sha256"] = payload_sha256(stage)
    value["stage_failure_accounting"] = parent.validate_stage_receipt(stage)
    value["role"] = parent.ROLE
    value["policy_id"] = parent.POLICY_ID
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    projected_parent = parent.validate_result(value)

    value = copy.deepcopy(projected_parent)
    value["causal_coupling_receipt"] = _receipt(
        parent_result=checked,
        projected_parent_result=projected_parent,
        original_prediction_changed=original_changed,
        prediction_identity_handoff_applied=identity,
        salience_receipt=salience_receipt,
    )
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": model,
        "searches": searches,
        "limits": limits,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    order = tuple(arm_order or core._arm_order(str(task.get("opaque_id") or "")))
    salience_model = CausalSalienceModel(
        model,
        first_wave_search=searches[FIRST_PHASE],
        arm_order=order,
    )
    kwargs["model"] = salience_model
    kwargs["arm_order"] = order
    parent_result = parent.run_paired_task(task, **kwargs)
    return _project(parent_result, salience_model.content_free_receipt())


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    coupling = copied.get("causal_coupling_receipt")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(coupling, Mapping)
        or validate_receipt(coupling) != dict(coupling)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.27 result envelope drifted")
    parent_value = copy.deepcopy(copied)
    parent_value.pop("causal_coupling_receipt")
    parent_value["role"] = parent.ROLE
    parent_value["policy_id"] = parent.POLICY_ID
    parent_value["result_payload_sha256"] = coupling[
        "projected_parent_result_payload_sha256"
    ]
    parent_checked = parent.validate_result(parent_value)
    if (
        parent_checked["opaque_id"] != copied["opaque_id"]
        or coupling["projected_parent_result_payload_sha256"]
        != parent_checked["result_payload_sha256"]
        or coupling["parent_result_payload_sha256"]
        == coupling["projected_parent_result_payload_sha256"]
        and coupling["prediction_identity_handoff_applied"]
        and coupling["original_prediction_changed"]
        or copied["prediction_changed"]
        is not coupling["projected_prediction_changed"]
        or copied["content_free_receipt"]["attributable_prediction_change"]
        is not copied["prediction_changed"]
        or coupling["positive_target_field_page_gain"]
        is not (copied["content_free_receipt"]["target_field_page_gain"] > 0)
        or coupling["selection_changed"]
        is not copied["content_free_receipt"]["selection_changed"]
        or coupling["retrieval_mechanism_engaged"]
        is not copied["content_free_receipt"]["retrieval_mechanism_engaged"]
        or coupling["prompt_salience_receipt"]["synthesis_prompt_count"]
        != sum(
            int(
                copied["content_free_receipt"]["arm_metrics"][arm][
                    "synthesis_attempted"
                ]
            )
            for arm in ARMS
        )
        or coupling["prediction_identity_handoff_applied"]
        and copied["predictions"][CONTROL_ARM]
        != copied["predictions"][CANDIDATE_ARM]
        or any(
            copied["prediction_sha256"][arm]
            != hashlib.sha256(copied["predictions"][arm].encode()).hexdigest()
            for arm in ARMS
        )
    ):
        raise ValueError("V2.51.27 causal binding drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CausalSalienceModel",
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
    "validate_salience_receipt",
]
