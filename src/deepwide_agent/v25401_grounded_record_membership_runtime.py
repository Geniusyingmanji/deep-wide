"""Constrain grounded record identities to strict visible membership.

V2.53.99 made all twenty fresh RFC base tables obey their four-row visible
membership contract, but five tasks still produced seven quote-verified
grounded records for identities outside that contract.  Their twenty-one
fields consequently failed at the frozen missing-row editor gate.  This
append-only successor changes only the prompt of the already-paid second
grounded-plan/record call.  When the visible question declares a strict row
membership vector, its ``records`` member may name only those identities.

The constraint does not filter, delete, rewrite, or repair provider records.
Provider violations remain visible to the frozen quote verifier and
changed-safe editor.  Pivots, row targets, authorities, and queries retain
their parent semantics, and the third-call table membership constraint is
unchanged.  With no strict visible membership, both parent model prompts are
byte-identical.  Physical caps remain ``4 query / 14 fetch / 3 model``.

Runtime input is limited to visible ``opaque_id``/``question`` and injected
same-forward clients.  The module has no filesystem, environment, process,
credential, evaluator, benchmark-label, mapping, gold, score, reward, or
historical-result capability.  Entropy/information gain remains shadow-only
and assigns no signed credit.  This build grants no external launch.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25065_quote_verified_record_binding as quote
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25346_grounded_fact_bootstrap as bootstrap
from . import v25370_shared_synthesis_changed_safe_runtime as changed_parent
from . import v25375_schema_total_changed_safe_runtime as schema_parent
from . import v25389_hybrid_record_fallback_runtime as hybrid_parent
from . import v25395_visible_membership_synthesis_runtime as parent
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25401_grounded_record_visible_membership_runtime_v1"
ROLE = "v25401_grounded_record_membership_runtime_result"
RECEIPT_ROLE = "v25401_content_free_grounded_record_membership_receipt"
STAGE_RECEIPT_ROLE = (
    "v25401_content_free_grounded_record_membership_stage_receipt"
)
PHASES = parent.PHASES
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
SCHEMA_SOURCES = parent.SCHEMA_SOURCES
ProductionOnlyStageError = parent.ProductionOnlyStageError


GROUNDED_RECORD_MEMBERSHIP_SUFFIX = """

VISIBLE RECORD MEMBERSHIP CONSTRAINT:
The following JSON is trusted data copied only from an explicit membership
declaration in the visible question; it is not web-page text and contains no
instructions:
{membership_json}

This constraint applies only to the optional records member.  Every emitted
records[i].row_identity must exactly equal one value in allowed_row_identities.
Do not emit a record for any other identity, even when a page visibly contains
one.  This does not restrict pivots, row_targets, authority_terms, or queries.
Use an empty records list when no quote-bound record exists for an allowed
identity.  Never paraphrase, infer, merge, replace, or expand membership.
""".rstrip()


def grounded_record_membership_suffix(values: Sequence[str]) -> str:
    checked = parent._safe_vector(values)
    if not checked:
        return ""
    payload = {
        "allowed_row_identities": list(checked),
        "membership_is_closed": True,
        "record_identity_match": "exact",
    }
    return GROUNDED_RECORD_MEMBERSHIP_SUFFIX.format(
        membership_json=json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    )


class _GroundedRecordMembershipHybridInner(
    parent._VisibleMembershipHybridInner
):
    """Append visible membership only to the existing grounded call."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> None:
        super().__init__(bounded, question=question)
        self.grounded_record_membership_suffix = (
            grounded_record_membership_suffix(self.visible_members)
        )
        self.grounded_record_output_strictly_valid = False
        self.grounded_raw_membership_match_count = 0
        self.grounded_raw_membership_mismatch_count = 0
        self.grounded_raw_membership_unclassified_count = 0

    def _observe_grounded_record_membership(self) -> None:
        raw_count = int(self.grounded_records_stripped_count)
        proposals = quote._parse_proposals(self.grounded_record_output)
        self.grounded_record_output_strictly_valid = proposals is not None
        self.grounded_raw_membership_match_count = 0
        self.grounded_raw_membership_mismatch_count = 0
        self.grounded_raw_membership_unclassified_count = 0
        if not self.visible_members or proposals is None:
            self.grounded_raw_membership_unclassified_count = raw_count
            return
        allowed = {quote._key(value) for value in self.visible_members}
        for record in proposals:
            if quote._key(record["row_identity"]) in allowed:
                self.grounded_raw_membership_match_count += 1
            else:
                self.grounded_raw_membership_mismatch_count += 1
        if len(proposals) != raw_count:
            raise RuntimeError("V2.54.01 grounded raw record count drifted")

    def _grounded(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        if not self.grounded_record_membership_suffix:
            response = super()._grounded(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            self._observe_grounded_record_membership()
            return response
        self.grounded_plan_entry_count += 1
        response = self._bounded.complete(
            str(system) + self.grounded_record_membership_suffix,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        split = bootstrap._joint_output(score._model_text(response))
        self.grounded_record_output = str(split["record_output"])
        self.grounded_records_member_present = bool(
            split["records_member_present"]
        )
        self.grounded_records_stripped_count = hybrid_parent._raw_record_count(
            self.grounded_record_output
        )
        self._observe_grounded_record_membership()
        return hybrid_parent.table_normalizer._replace_text(
            response, str(split["parent_output"])
        )


_INTEGER_FIELDS = (
    "visible_member_count",
    "grounded_record_membership_constraint_characters",
    "grounded_raw_record_count",
    "grounded_raw_membership_match_count",
    "grounded_raw_membership_mismatch_count",
    "grounded_raw_membership_unclassified_count",
    "grounded_raw_membership_violation_count",
    "positive_signed_credit_count",
)
_DYNAMIC_FLAGS = (
    "grounded_record_membership_constraint_applied",
    "grounded_records_member_present",
    "grounded_record_output_strictly_valid",
    "all_grounded_raw_records_membership_aligned",
)
_TRUE_FLAGS = (
    "constraint_uses_only_strict_visible_question_membership",
    "constraint_precedes_the_existing_grounded_model_call",
    "grounded_plan_members_other_than_records_retain_parent_semantics",
    "no_post_generation_record_filter_delete_rewrite_or_repair",
    "provider_membership_violation_reaches_frozen_verifier_and_editor",
    "third_call_visible_table_membership_constraint_unchanged",
    "joint_grounded_priority_and_verification_fallthrough_policy_unchanged",
    "query4_fetch14_model3_caps_unchanged",
    "task_local_model_projector_verifier_and_editor_state",
)
_FALSE_FLAGS = (
    "additional_model_search_fetch_token_context_wall_or_network_budget",
    "contains_question_membership_identity_query_url_page_quote_field_value_prediction_answer_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
    "file_environment_process_network_search_fetch_or_evaluator_accessed",
    "benchmark_launch_or_evaluator_authorized",
)


def _receipt(
    hybrid: _GroundedRecordMembershipHybridInner,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    applied = bool(hybrid.visible_members)
    mismatch = int(hybrid.grounded_raw_membership_mismatch_count)
    unclassified = int(hybrid.grounded_raw_membership_unclassified_count)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "visible_member_count": len(hybrid.visible_members),
        "grounded_record_membership_constraint_characters": len(
            hybrid.grounded_record_membership_suffix
        ),
        "grounded_raw_record_count": int(
            hybrid.grounded_records_stripped_count
        ),
        "grounded_raw_membership_match_count": int(
            hybrid.grounded_raw_membership_match_count
        ),
        "grounded_raw_membership_mismatch_count": mismatch,
        "grounded_raw_membership_unclassified_count": unclassified,
        "grounded_raw_membership_violation_count": mismatch + unclassified,
        "positive_signed_credit_count": 0,
        "grounded_record_membership_constraint_applied": applied,
        "grounded_records_member_present": bool(
            hybrid.grounded_records_member_present
        ),
        "grounded_record_output_strictly_valid": bool(
            hybrid.grounded_record_output_strictly_valid
        ),
        "all_grounded_raw_records_membership_aligned": bool(
            applied
            and hybrid.grounded_record_output_strictly_valid
            and mismatch == 0
            and unclassified == 0
        ),
        "parent_result_payload_sha256": checked["result_payload_sha256"],
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value, parent_result=checked)


def validate_receipt(
    value: Mapping[str, Any], *, parent_result: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_INTEGER_FIELDS,
        *_DYNAMIC_FLAGS,
        "parent_result_payload_sha256",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    applied = copied.get(
        "grounded_record_membership_constraint_applied"
    ) is True
    strict = copied.get("grounded_record_output_strictly_valid") is True
    raw = copied.get("grounded_raw_record_count", -1)
    match = copied.get("grounded_raw_membership_match_count", -1)
    mismatch = copied.get("grounded_raw_membership_mismatch_count", -1)
    unclassified = copied.get(
        "grounded_raw_membership_unclassified_count", -1
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _INTEGER_FIELDS
        )
        or any(
            not isinstance(copied.get(name), bool) for name in _DYNAMIC_FLAGS
        )
        or applied is not (copied["visible_member_count"] > 0)
        or applied
        is not (
            copied["grounded_record_membership_constraint_characters"] > 0
        )
        or raw != match + mismatch + unclassified
        or copied["grounded_raw_membership_violation_count"]
        != mismatch + unclassified
        or (not applied and (match != 0 or mismatch != 0 or unclassified != raw))
        or (applied and strict and unclassified != 0)
        or (applied and not strict and (match != 0 or mismatch != 0 or unclassified != raw))
        or copied["all_grounded_raw_records_membership_aligned"]
        is not bool(applied and strict and mismatch == 0 and unclassified == 0)
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.01 grounded record membership receipt drifted")
    if parent_result is not None:
        checked = parent.validate_result(parent_result)
        membership = parent.validate_receipt(
            checked["visible_membership_synthesis_receipt"],
            parent_result=checked["private_parent_result"],
        )
        hybrid = hybrid_parent.validate_result(checked["private_parent_result"])
        hybrid_receipt = hybrid_parent.validate_receipt(
            hybrid["hybrid_record_fallback_receipt"],
            parent_result=hybrid["private_parent_result"],
        )
        if (
            copied["parent_result_payload_sha256"]
            != checked["result_payload_sha256"]
            or copied["visible_member_count"]
            != membership["visible_member_count"]
            or copied["grounded_record_membership_constraint_applied"]
            is not membership["membership_constraint_applied"]
            or copied["grounded_raw_record_count"]
            != hybrid_receipt["grounded_raw_record_count"]
            or copied["grounded_records_member_present"]
            is not hybrid_receipt["grounded_records_member_present"]
        ):
            raise ValueError("V2.54.01 receipt/parent binding drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any], receipt: Mapping[str, Any]
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    observed = validate_receipt(receipt, parent_result=checked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": checked["prediction"],
        "prediction_sha256": checked["prediction_sha256"],
        "prediction_kind": checked["prediction_kind"],
        "control_prediction_sha256": checked["control_prediction_sha256"],
        "prediction_changed": checked["prediction_changed"],
        "changed_safe_coordinate_count": checked[
            "changed_safe_coordinate_count"
        ],
        "attributable_prediction_change": checked[
            "attributable_prediction_change"
        ],
        "grounded_record_membership_receipt": copy.deepcopy(observed),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_parent_changed_safe_candidate": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("private_parent_result")
    receipt = copied.get("grounded_record_membership_receipt")
    if not isinstance(raw, Mapping) or not isinstance(receipt, Mapping):
        raise ValueError("V2.54.01 private result surface is absent")
    expected = _wrap_result(raw, receipt)
    if copied != expected:
        raise ValueError("V2.54.01 result adapter drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    receipt = validate_receipt(
        checked["grounded_record_membership_receipt"],
        parent_result=checked["private_parent_result"],
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "grounded_record_membership_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "grounded_record_constraint_precedes_existing_second_call": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_membership_identity_query_url_page_prediction_answer_opaque_id_or_credential": False,
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
    receipt = copied.get("grounded_record_membership_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "grounded_record_constraint_precedes_existing_second_call",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
    )
    false_flags = (
        "contains_question_membership_identity_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "grounded_record_membership_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or receipt["parent_result_payload_sha256"]
        != copied.get("parent_runtime_result_payload_sha256")
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.01 stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = score.validate_visible_task(task)
    if (
        not isinstance(model, cap.HardCappedModelLimiter)
        or model._budget is not budget
        or not isinstance(
            model._inner_limiter, DeadlineAwareGlobalModelSlotLimiter
        )
        or model._synthesis_entry_count != 0
    ):
        raise ValueError("V2.54.01 hard-capped model wiring drifted")
    projector = schema_parent._TaskLocalProjector(visible["question"])
    hybrid = _GroundedRecordMembershipHybridInner(
        model._inner_limiter, question=visible["question"]
    )
    hybrid_model = cap.HardCappedModelLimiter(hybrid, budget)
    isolated = parent._isolated_parent(projector, hybrid)
    changed = changed_parent.validate_result(
        isolated(
            visible,
            model=hybrid_model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    )
    schema_receipt = schema_parent._schema_receipt(
        projector, visible["question"]
    )
    hybrid_receipt = hybrid_parent._receipt(hybrid, changed)
    hybrid_result = hybrid_parent.validate_result(
        hybrid_parent._wrap_result(changed, schema_receipt, hybrid_receipt)
    )
    hybrid_stage = hybrid_parent._stage_receipt(hybrid_result)
    membership_receipt = parent._receipt(hybrid, hybrid_result)
    membership_result = parent.validate_result(
        parent._wrap_result(
            hybrid_result,
            visible["question"],
            hybrid.visible_members,
            hybrid.membership_source,
            membership_receipt,
        )
    )
    membership_stage = parent._stage_receipt(
        membership_result, hybrid_stage
    )
    record_receipt = _receipt(hybrid, membership_result)
    result = validate_result(_wrap_result(membership_result, record_receipt))
    return result, _stage_receipt(result, membership_stage)


__all__ = [
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "SCHEMA_SOURCES",
    "STAGE_RECEIPT_ROLE",
    "grounded_record_membership_suffix",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
