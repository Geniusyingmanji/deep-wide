"""Strict-priority joint-or-grounded record fallback for changed-safe edits.

V2.53.87 established that all twenty third-call joint envelopes and tables
were valid, but every third-call ``records`` list was empty.  The already-paid
grounded-plan responses contained eleven raw records on eight tasks.  This
append-only successor retains both observations without adding an effect:

* a non-empty third-call records list has unconditional priority, even if its
  records later fail verification;
* only when the third-call list is exactly empty may the same-forward grounded
  records be selected; and
* the two sources are never merged, unioned, retried, or selected according to
  verification outcome.

Whichever raw source is selected is replayed through V2.53.60 page/quote/row/
field verification and V2.53.69 deterministic changed-safe editing.  Grounded
records are checked only against the exact first-wave page surface visible to
that call; joint records are checked against the complete two-wave synthesis
surface.  The base table always comes from the third response.  Physical caps
remain ``4 query / 14 fetch / 3 model`` and the candidate has no model effect.

All state is task-local.  Runtime input remains visible ``opaque_id`` and
``question`` plus injected same-forward clients.  This module has no file,
environment, process, credential, evaluator, benchmark-label, mapping, gold,
score, reward, or historical-result capability.  Entropy/information gain is
shadow-only and assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import types
from collections.abc import Callable, Mapping, Sequence
from types import SimpleNamespace
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24259_deterministic_table_normalizer as table_normalizer
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25346_grounded_fact_bootstrap as bootstrap
from . import v25360_quote_coordinate_partial_field_record as verifier
from . import v25369_changed_safe_verified_coordinate_edit as editor
from . import v25370_shared_synthesis_changed_safe_runtime as changed_parent
from . import v25375_schema_total_changed_safe_runtime as schema_parent
from . import v25383_joint_synthesis_changed_safe_runtime as joint_parent
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25389_hybrid_joint_or_grounded_record_fallback_runtime_v1"
ROLE = "v25389_hybrid_record_fallback_runtime_result"
RECEIPT_ROLE = "v25389_content_free_hybrid_record_fallback_receipt"
STAGE_RECEIPT_ROLE = "v25389_content_free_hybrid_record_fallback_stage_receipt"
PHASES = changed_parent.PHASES
CONTROL_ARM = changed_parent.CONTROL_ARM
CANDIDATE_ARM = changed_parent.CANDIDATE_ARM
SCHEMA_SOURCES = schema_parent.SCHEMA_SOURCES
ProductionOnlyStageError = schema_parent.ProductionOnlyStageError
RECORD_SOURCES = frozenset({"joint", "grounded", "none"})


def _raw_record_count(record_output: object) -> int:
    try:
        parsed = json.loads(str(record_output))
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0
    records = parsed.get("records") if isinstance(parsed, dict) else None
    return len(records) if isinstance(records, list) else 0


class _HybridSynthesisInner(joint_parent._JointSynthesisInner):
    """Capture the stripped grounded records before returning the parent plan."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> None:
        super().__init__(bounded, question=question)
        self.grounded_record_output = json.dumps(
            {"records": []}, ensure_ascii=False, separators=(",", ":")
        )
        self.grounded_prepared_records: dict[str, Any] | None = None
        self.selected_record_source = "none"
        self.selected_raw_record_count = 0
        self.editor_record_channel_armed = False

    def _grounded(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        self.grounded_plan_entry_count += 1
        response = self._bounded.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        split = bootstrap._joint_output(score._model_text(response))
        self.grounded_record_output = str(split["record_output"])
        self.grounded_records_member_present = bool(
            split["records_member_present"]
        )
        self.grounded_records_stripped_count = _raw_record_count(
            self.grounded_record_output
        )
        return table_normalizer._replace_text(response, str(split["parent_output"]))

    def choose_record_source(self) -> str:
        """Choose solely from pre-verification raw list emptiness."""

        if self.envelope_record_count > 0:
            source = "joint"
            count = self.envelope_record_count
        elif self.grounded_records_stripped_count > 0:
            source = "grounded"
            count = self.grounded_records_stripped_count
        else:
            source = "none"
            count = 0
        self.selected_record_source = source
        self.selected_raw_record_count = count
        return source


class _TaskLocalVerifier:
    def __init__(self, hybrid: _HybridSynthesisInner) -> None:
        self._hybrid = hybrid

    def prepare_record_proposal(
        self,
        question: str,
        columns: Sequence[str],
        pages: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if len(columns) == 1:
            del question, pages
            return {"v25389_one_column_identity_noop": True}
        grounded = verifier.prepare_record_proposal(question, columns, pages)
        self._hybrid.grounded_prepared_records = copy.deepcopy(grounded)
        source = self._hybrid.choose_record_source()
        if source == "joint":
            prepared = self._hybrid.prepared_records
            if prepared is None:
                raise ValueError("V2.53.89 joint verifier state is absent")
        else:
            # The empty-source path uses a valid empty proposal over the
            # grounded page state; it cannot create an edit.
            prepared = grounded
        if (
            str(prepared.get("question")) != str(question)
            or tuple(prepared.get("columns") or ()) != tuple(columns)
        ):
            raise ValueError("V2.53.89 selected verifier state drifted")
        return copy.deepcopy(prepared)


class _TaskLocalEditor:
    def __init__(self, hybrid: _HybridSynthesisInner) -> None:
        self._hybrid = hybrid

    def apply_changed_safe_verified_coordinates(self, **kwargs: Any) -> dict[str, Any]:
        columns = kwargs.get("columns")
        if (
            isinstance(columns, Sequence)
            and not isinstance(columns, (str, bytes))
            and len(columns) == 1
        ):
            return schema_parent._one_column_identity_editor(**kwargs)
        base = str(kwargs.get("base_prediction"))
        source = self._hybrid.choose_record_source()
        base_ready = bool(
            self._hybrid.joint_envelope_exact
            and self._hybrid.joint_table_normalizable
            and self._hybrid.normalized_table == base
        )
        copied = dict(kwargs)
        if base_ready and source == "joint" and self._hybrid.prepared_records is not None:
            copied["prepared"] = copy.deepcopy(self._hybrid.prepared_records)
            copied["record_output"] = self._hybrid.record_output
            copied["model_call_attempted"] = True
            self._hybrid.editor_record_channel_armed = True
        elif (
            base_ready
            and source == "grounded"
            and self._hybrid.grounded_prepared_records is not None
        ):
            copied["prepared"] = copy.deepcopy(
                self._hybrid.grounded_prepared_records
            )
            copied["record_output"] = self._hybrid.grounded_record_output
            copied["model_call_attempted"] = True
            self._hybrid.editor_record_channel_armed = True
        else:
            copied["record_output"] = json.dumps(
                {"records": []}, ensure_ascii=False, separators=(",", ":")
            )
            copied["model_call_attempted"] = bool(base_ready)
            self._hybrid.editor_record_channel_armed = bool(base_ready)
        return editor.apply_changed_safe_verified_coordinates(**copied)

    @staticmethod
    def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
        return editor.validate_result(value)

    @staticmethod
    def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
        return editor.validate_receipt(value)


def _isolated_parent(
    projector: schema_parent._TaskLocalProjector,
    hybrid: _HybridSynthesisInner,
) -> Callable[..., dict[str, Any]]:
    local_verifier = _TaskLocalVerifier(hybrid)
    local_editor = _TaskLocalEditor(hybrid)
    empty_namespace = dict(changed_parent._empty_editor.__globals__)
    empty_namespace.update({"verifier": local_verifier, "editor": local_editor})
    empty_editor = types.FunctionType(
        changed_parent._empty_editor.__code__,
        empty_namespace,
        name="v25389_task_local_empty_editor",
        argdefs=changed_parent._empty_editor.__defaults__,
        closure=changed_parent._empty_editor.__closure__,
    )
    empty_editor.__kwdefaults__ = dict(
        changed_parent._empty_editor.__kwdefaults__ or {}
    )
    namespace = dict(changed_parent.run_paired_task.__globals__)
    namespace.update(
        {
            "query_parent": SimpleNamespace(projected_plan=projector.projected_plan),
            "verifier": local_verifier,
            "editor": local_editor,
            "_empty_editor": empty_editor,
        }
    )
    cloned = types.FunctionType(
        changed_parent.run_paired_task.__code__,
        namespace,
        name="v25389_task_local_hybrid_record_parent",
        argdefs=changed_parent.run_paired_task.__defaults__,
        closure=changed_parent.run_paired_task.__closure__,
    )
    cloned.__kwdefaults__ = dict(changed_parent.run_paired_task.__kwdefaults__ or {})
    cloned.__annotations__ = dict(changed_parent.run_paired_task.__annotations__)
    return cloned


_INTEGER_FIELDS = (
    "model_entry_count",
    "grounded_raw_record_count",
    "joint_raw_record_count",
    "selected_raw_record_count",
    "verified_record_count",
    "verified_field_count",
    "missing_row_rejected_field_count",
    "unchanged_verified_coordinate_count",
    "changed_safe_coordinate_count",
    "positive_signed_credit_count",
)
_DYNAMIC_FLAGS = (
    "grounded_records_member_present",
    "joint_envelope_exact",
    "joint_table_normalizable",
    "joint_nonempty_preempts_grounded",
    "grounded_fallback_selected",
    "no_record_source_selected",
    "editor_record_channel_armed",
    "record_output_strictly_valid",
    "second_wave_completed",
    "base_synthesis_model_success",
    "candidate_prediction_changed",
    "attributable_prediction_change",
)
_TRUE_FLAGS = (
    "record_source_selected_before_quote_or_edit_verification",
    "nonempty_joint_source_has_unconditional_priority",
    "grounded_source_allowed_only_when_joint_raw_list_empty",
    "joint_and_grounded_records_never_merged_or_unioned",
    "grounded_records_reverified_against_first_wave_page_surface",
    "joint_records_reverified_against_two_wave_synthesis_surface",
    "selected_records_require_same_response_base_table_row",
    "invalid_selected_source_cannot_fall_through_to_other_source",
    "candidate_is_only_deterministic_changed_safe_edit",
    "query4_fetch14_model3_caps_unchanged",
    "task_local_model_projector_verifier_and_editor_state",
)
_FALSE_FLAGS = (
    "additional_model_search_fetch_token_context_wall_or_network_budget",
    "contains_question_query_url_page_quote_identity_field_value_prediction_answer_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
    "module_global_state_mutated",
    "benchmark_launch_or_evaluator_authorized",
)


def _receipt(
    hybrid: _HybridSynthesisInner, parent_result: Mapping[str, Any]
) -> dict[str, Any]:
    checked = changed_parent.validate_result(parent_result)
    parent_receipt = changed_parent.validate_receipt(checked["content_free_receipt"])
    edit = editor.validate_receipt(parent_receipt["changed_safe_edit_receipt"])
    source = hybrid.choose_record_source()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "record_source": source,
        "model_entry_count": hybrid.plan_entry_count
        + hybrid.grounded_plan_entry_count
        + hybrid.synthesis_entry_count,
        "grounded_raw_record_count": hybrid.grounded_records_stripped_count,
        "joint_raw_record_count": hybrid.envelope_record_count,
        "selected_raw_record_count": hybrid.selected_raw_record_count,
        "verified_record_count": int(edit["verified_record_count"]),
        "verified_field_count": int(edit["verified_field_count"]),
        "missing_row_rejected_field_count": int(
            edit["missing_row_rejected_field_count"]
        ),
        "unchanged_verified_coordinate_count": int(
            edit["unchanged_verified_coordinate_count"]
        ),
        "changed_safe_coordinate_count": int(edit["changed_safe_coordinate_count"]),
        "positive_signed_credit_count": 0,
        "grounded_records_member_present": hybrid.grounded_records_member_present,
        "joint_envelope_exact": hybrid.joint_envelope_exact,
        "joint_table_normalizable": hybrid.joint_table_normalizable,
        "joint_nonempty_preempts_grounded": source == "joint",
        "grounded_fallback_selected": source == "grounded",
        "no_record_source_selected": source == "none",
        "editor_record_channel_armed": hybrid.editor_record_channel_armed,
        "record_output_strictly_valid": bool(edit["record_output_strictly_valid"]),
        "second_wave_completed": bool(parent_receipt["second_wave_completed"]),
        "base_synthesis_model_success": bool(
            parent_receipt["base_synthesis_model_success"]
        ),
        "candidate_prediction_changed": bool(checked["prediction_changed"]),
        "attributable_prediction_change": bool(
            checked["attributable_prediction_change"]
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
    source = copied.get("record_source")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "record_source",
        *_INTEGER_FIELDS,
        *_DYNAMIC_FLAGS,
        "parent_result_payload_sha256",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    priority_source = (
        "joint"
        if copied.get("joint_raw_record_count", 0) > 0
        else "grounded"
        if copied.get("grounded_raw_record_count", 0) > 0
        else "none"
    )
    selected_count = {
        "joint": copied.get("joint_raw_record_count", 0),
        "grounded": copied.get("grounded_raw_record_count", 0),
        "none": 0,
    }.get(source)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or source not in RECORD_SOURCES
        or source != priority_source
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _INTEGER_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in _DYNAMIC_FLAGS)
        or copied["model_entry_count"] > 3
        or copied["selected_raw_record_count"] != selected_count
        or copied["positive_signed_credit_count"] != 0
        or copied["joint_nonempty_preempts_grounded"] is not (source == "joint")
        or copied["grounded_fallback_selected"] is not (source == "grounded")
        or copied["no_record_source_selected"] is not (source == "none")
        or source == "grounded" and copied["joint_raw_record_count"] != 0
        or source == "none"
        and (
            copied["joint_raw_record_count"] != 0
            or copied["grounded_raw_record_count"] != 0
        )
        or copied["base_synthesis_model_success"]
        and not (
            copied["joint_envelope_exact"]
            and copied["joint_table_normalizable"]
        )
        or copied["candidate_prediction_changed"]
        is not copied["attributable_prediction_change"]
        or copied["candidate_prediction_changed"]
        and copied["changed_safe_coordinate_count"] <= 0
        or copied["verified_record_count"] > copied["selected_raw_record_count"]
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.89 hybrid receipt drifted")
    if parent_result is not None:
        checked = changed_parent.validate_result(parent_result)
        parent_receipt = changed_parent.validate_receipt(
            checked["content_free_receipt"]
        )
        edit = editor.validate_receipt(parent_receipt["changed_safe_edit_receipt"])
        if (
            copied["parent_result_payload_sha256"]
            != checked["result_payload_sha256"]
            or copied["model_entry_count"]
            != parent_receipt["physical_model_forward_count"]
            or copied["second_wave_completed"]
            is not parent_receipt["second_wave_completed"]
            or copied["base_synthesis_model_success"]
            is not parent_receipt["base_synthesis_model_success"]
            or copied["record_output_strictly_valid"]
            is not edit["record_output_strictly_valid"]
            or copied["verified_record_count"] != edit["verified_record_count"]
            or copied["verified_field_count"] != edit["verified_field_count"]
            or copied["missing_row_rejected_field_count"]
            != edit["missing_row_rejected_field_count"]
            or copied["unchanged_verified_coordinate_count"]
            != edit["unchanged_verified_coordinate_count"]
            or copied["changed_safe_coordinate_count"]
            != edit["changed_safe_coordinate_count"]
            or copied["candidate_prediction_changed"]
            is not checked["prediction_changed"]
            or copied["attributable_prediction_change"]
            is not checked["attributable_prediction_change"]
        ):
            raise ValueError("V2.53.89 hybrid/parent binding drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    schema_receipt: Mapping[str, Any],
    hybrid_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked = changed_parent.validate_result(parent_result)
    schema = schema_parent.validate_schema_receipt(schema_receipt)
    hybrid = validate_receipt(hybrid_receipt, parent_result=checked)
    candidate = checked["predictions"][CANDIDATE_ARM]
    control = checked["predictions"][CONTROL_ARM]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": candidate,
        "prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prediction_kind": (
            "model_generated"
            if checked["model_success"][CANDIDATE_ARM]
            else "fallback"
        ),
        "control_prediction_sha256": hashlib.sha256(control.encode()).hexdigest(),
        "prediction_changed": checked["prediction_changed"],
        "changed_safe_coordinate_count": checked["changed_safe_coordinate_count"],
        "attributable_prediction_change": checked[
            "attributable_prediction_change"
        ],
        "schema_totality_receipt": copy.deepcopy(schema),
        "hybrid_record_fallback_receipt": copy.deepcopy(hybrid),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked["result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_hybrid_changed_safe_candidate": True,
        "shared_control_not_exported_as_scored_prediction": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("private_parent_result")
    schema = copied.get("schema_totality_receipt")
    hybrid = copied.get("hybrid_record_fallback_receipt")
    if (
        not isinstance(raw, Mapping)
        or not isinstance(schema, Mapping)
        or not isinstance(hybrid, Mapping)
    ):
        raise ValueError("V2.53.89 private result surface is absent")
    expected = _wrap_result(raw, schema, hybrid)
    if copied != expected:
        raise ValueError("V2.53.89 result adapter drifted")
    return copied


def _stage_receipt(result: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_result(result)
    raw = changed_parent.validate_result(checked["private_parent_result"])
    parent_receipt = changed_parent.validate_receipt(raw["content_free_receipt"])
    schema = schema_parent.validate_schema_receipt(
        checked["schema_totality_receipt"]
    )
    hybrid = validate_receipt(
        checked["hybrid_record_fallback_receipt"], parent_result=raw
    )
    budget = cap.validate_budget_receipt(
        parent_receipt["outer_physical_budget_receipt"]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "schema_totality_receipt": copy.deepcopy(schema),
        "hybrid_record_fallback_receipt": copy.deepcopy(hybrid),
        "parent_content_free_receipt": copy.deepcopy(parent_receipt),
        "parent_result_payload_sha256": raw["result_payload_sha256"],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(budget),
        "scored_prediction_is_hybrid_changed_safe_candidate": True,
        "record_source_priority_is_preverification_and_task_local": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential": False,
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
    schema = copied.get("schema_totality_receipt")
    hybrid = copied.get("hybrid_record_fallback_receipt")
    parent_receipt = copied.get("parent_content_free_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "scored_prediction_is_hybrid_changed_safe_candidate",
        "record_source_priority_is_preverification_and_task_local",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
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
        "schema_totality_receipt",
        "hybrid_record_fallback_receipt",
        "parent_content_free_receipt",
        "parent_result_payload_sha256",
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
        or not isinstance(schema, Mapping)
        or schema_parent.validate_schema_receipt(schema) != dict(schema)
        or not isinstance(hybrid, Mapping)
        or validate_receipt(hybrid) != dict(hybrid)
        or not isinstance(parent_receipt, Mapping)
        or changed_parent.validate_receipt(parent_receipt) != dict(parent_receipt)
        or hybrid["parent_result_payload_sha256"]
        != copied.get("parent_result_payload_sha256")
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or parent_receipt["outer_physical_budget_receipt"] != budget
        or hybrid["model_entry_count"] != budget["model_admitted_count"]
        or hybrid["second_wave_completed"]
        is not parent_receipt["second_wave_completed"]
        or hybrid["base_synthesis_model_success"]
        is not parent_receipt["base_synthesis_model_success"]
        or hybrid["changed_safe_coordinate_count"]
        != parent_receipt["changed_safe_edit_receipt"][
            "changed_safe_coordinate_count"
        ]
        or hybrid["candidate_prediction_changed"]
        is not parent_receipt["candidate_prediction_changed"]
        or hybrid["attributable_prediction_change"]
        is not parent_receipt["attributable_prediction_change"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.89 stage receipt drifted")
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
        or not isinstance(model._inner_limiter, DeadlineAwareGlobalModelSlotLimiter)
        or model._synthesis_entry_count != 0
    ):
        raise ValueError("V2.53.89 hard-capped model wiring drifted")
    projector = schema_parent._TaskLocalProjector(visible["question"])
    hybrid = _HybridSynthesisInner(
        model._inner_limiter, question=visible["question"]
    )
    hybrid_model = cap.HardCappedModelLimiter(hybrid, budget)
    isolated = _isolated_parent(projector, hybrid)
    parent_result = changed_parent.validate_result(
        isolated(
            visible,
            model=hybrid_model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    )
    schema_receipt = schema_parent._schema_receipt(projector, visible["question"])
    hybrid_receipt = _receipt(hybrid, parent_result)
    result = validate_result(
        _wrap_result(parent_result, schema_receipt, hybrid_receipt)
    )
    return result, _stage_receipt(result)


__all__ = [
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "RECORD_SOURCES",
    "ROLE",
    "SCHEMA_SOURCES",
    "STAGE_RECEIPT_ROLE",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
