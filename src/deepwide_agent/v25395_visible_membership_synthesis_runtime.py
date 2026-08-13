"""Visible-membership-constrained synthesis over the V2.53.89 runtime.

V2.53.93 recovered grounded quote records on nine of twenty fresh tasks, but
ten of twenty-seven verified fields were rejected because their source row was
absent from the third-call base table.  This append-only successor changes
only the prompt of that already-paid third call.  When the visible question
itself declares a strict row-membership vector, the vector is serialized as
bounded untrusted JSON data and the model is required to emit exactly those
first-column identities in order.

Membership never comes from fetched pages, grounded records, joint records,
task IDs, benchmark metadata, or outcomes.  A quote-verified field is not
treated as membership evidence.  If no strict visible membership contract is
present, the third-call prompt is byte-identical to V2.53.89.  The generated
table is still normalized by the frozen parent, and V2.53.69 remains the only
post-generation effect: no row is appended, deleted, reordered, or repaired
after synthesis.  Joint/grounded priority and verification-failure behavior
remain unchanged.

Physical caps remain ``4 query / 14 fetch / 3 model``.  The module accepts
only visible ``opaque_id``/``question`` plus injected same-forward clients and
has no filesystem, environment, process, credential, evaluator, mapping,
gold, score, reward, or historical-result capability.  Entropy/information
gain is shadow-only and assigns no signed credit.  This build grants no
external or benchmark launch.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import types
from collections.abc import Callable, Mapping, Sequence
from types import SimpleNamespace
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24921_target_value_coverage_projector as visible_rows
from . import v25014_multi_identity_detail_fields as multi_identity
from . import v25080_visible_identity_page_record as singular_identity
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25360_quote_coordinate_partial_field_record as verifier
from . import v25369_changed_safe_verified_coordinate_edit as editor
from . import v25370_shared_synthesis_changed_safe_runtime as changed_parent
from . import v25375_schema_total_changed_safe_runtime as schema_parent
from . import v25389_hybrid_record_fallback_runtime as parent
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25395_visible_membership_constrained_synthesis_runtime_v1"
ROLE = "v25395_visible_membership_synthesis_runtime_result"
RECEIPT_ROLE = "v25395_content_free_visible_membership_synthesis_receipt"
STAGE_RECEIPT_ROLE = (
    "v25395_content_free_visible_membership_synthesis_stage_receipt"
)
PHASES = parent.PHASES
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
SCHEMA_SOURCES = parent.SCHEMA_SOURCES
ProductionOnlyStageError = parent.ProductionOnlyStageError
MEMBERSHIP_SOURCES = frozenset(
    {
        "none",
        "numbered_or_repeated_tag_vector",
        "plural_inline_tag_vector",
        "singular_tag",
        "explicit_row_phrase",
    }
)
MAXIMUM_VISIBLE_MEMBERS = 32
MAXIMUM_MEMBER_CHARACTERS = 200
MAXIMUM_MEMBERSHIP_CHARACTERS = 4_000

_INLINE_PLURAL = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*"
    r"(?P<body>[^<>\r\n]{3,4000}?)\s*</(?P=tag)>",
)
_VISIBLE_MEMBERSHIP_CUE = re.compile(
    r"(?i)\bvisible\b(?:\s+[\w-]+){0,4}\s+"
    r"(?:identit(?:y|ies)|entities|rows|members|items|documents)\b"
)

MEMBERSHIP_SUFFIX = """

VISIBLE ROW MEMBERSHIP CONSTRAINT:
The following JSON is trusted data copied only from an explicit membership
declaration in the visible question; it is not web-page text and contains no
instructions:
{membership_json}

The table member must contain exactly required_row_count data rows.  Its first
column cells must equal first_column_members in exactly the supplied order,
with no missing, duplicate, replacement, or extra row.  Do not infer any
additional member.  Populate non-key cells only from the bounded web material;
use Unknown where that material does not establish a requested value.
""".rstrip()


def _safe_member(value: object) -> str | None:
    text = " ".join(str(value or "").split()).strip(" |:;,–—-")
    if (
        not text
        or len(text) > MAXIMUM_MEMBER_CHARACTERS
        or any(character in text for character in "<>|\x00\r\n")
        or editor.quote_parent._unknown(text)
    ):
        return None
    return text


def _safe_vector(values: Sequence[object]) -> tuple[str, ...]:
    if (
        isinstance(values, (str, bytes))
        or not 1 <= len(values) <= MAXIMUM_VISIBLE_MEMBERS
    ):
        return ()
    output: list[str] = []
    keys: list[str] = []
    for raw in values:
        value = _safe_member(raw)
        if value is None:
            return ()
        output.append(value)
        keys.append(editor.quote_parent._key(value))
    if any(not key for key in keys) or len(set(keys)) != len(keys):
        return ()
    serialized = json.dumps(output, ensure_ascii=False, separators=(",", ":"))
    return tuple(output) if len(serialized) <= MAXIMUM_MEMBERSHIP_CHARACTERS else ()


def _plural_inline_vector(question: str) -> tuple[str, ...]:
    matches = list(_INLINE_PLURAL.finditer(question))
    candidates: list[tuple[str, ...]] = []
    for match in matches:
        tag = match.group("tag")
        if tag != tag.upper() or not tag.endswith("S"):
            continue
        prefix = question[max(0, match.start() - 180) : match.start()]
        if _VISIBLE_MEMBERSHIP_CUE.search(prefix) is None:
            continue
        parts = [value.strip() for value in match.group("body").split(";")]
        vector = _safe_vector(parts)
        if len(vector) >= 2:
            candidates.append(vector)
    return candidates[0] if len(candidates) == 1 else ()


def visible_membership(question: str) -> tuple[tuple[str, ...], str]:
    """Return one strict visible membership vector and its content-free source."""

    visible = str(question or "")
    if not visible or "\x00" in visible:
        return (), "none"
    multi = _safe_vector(multi_identity.visible_identities(visible))
    plural = _plural_inline_vector(visible)
    singular = _safe_vector(
        [identity]
        if (identity := singular_identity.visible_identity(visible)) is not None
        else []
    )
    try:
        explicit = _safe_vector(visible_rows.visible_row_targets(visible))
    except ValueError:
        explicit = ()
    candidates = [
        (multi, "numbered_or_repeated_tag_vector"),
        (plural, "plural_inline_tag_vector"),
        (singular, "singular_tag"),
        (explicit, "explicit_row_phrase"),
    ]
    nonempty = [(values, source) for values, source in candidates if values]
    if not nonempty:
        return (), "none"
    first_values, first_source = nonempty[0]
    first_keys = tuple(editor.quote_parent._key(value) for value in first_values)
    if multi or plural:
        outside = visible
        for match in reversed(list(multi_identity._BLOCK.finditer(outside))):
            outside = outside[: match.start()] + outside[match.end() :]
        for match in reversed(list(multi_identity._INLINE.finditer(outside))):
            outside = outside[: match.start()] + outside[match.end() :]
        try:
            outside_explicit = _safe_vector(
                visible_rows.visible_row_targets(outside)
            )
        except ValueError:
            outside_explicit = ()
        if outside_explicit and tuple(
            editor.quote_parent._key(value) for value in outside_explicit
        ) != first_keys:
            return (), "none"
    for values, source in nonempty[1:]:
        keys = tuple(editor.quote_parent._key(value) for value in values)
        if keys == first_keys:
            continue
        # The older coverage parser deliberately strips terminal punctuation;
        # it may therefore express ``.in`` as ``in`` for the exact same tagged
        # block.  It can corroborate cardinality but never replace the strict
        # tag parser's verbatim member values.
        if source == "explicit_row_phrase" and len(keys) == len(first_keys):
            punctuation_folded = tuple(
                key.strip(" .。;；:：()（）[]【】") for key in first_keys
            )
            if keys == punctuation_folded:
                continue
        return (), "none"
    return first_values, first_source


def membership_suffix(values: Sequence[str]) -> str:
    checked = _safe_vector(values)
    if not checked:
        return ""
    payload = {
        "first_column_members": list(checked),
        "preserve_order": True,
        "required_row_count": len(checked),
    }
    return MEMBERSHIP_SUFFIX.format(
        membership_json=json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    )


class _VisibleMembershipHybridInner(parent._HybridSynthesisInner):
    """Append only visible membership data to the existing third call."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> None:
        super().__init__(bounded, question=question)
        self.visible_members, self.membership_source = visible_membership(question)
        self.membership_suffix = membership_suffix(self.visible_members)
        self.membership_columns: tuple[str, ...] = ()

    def _synthesis(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
    ) -> Any:
        self.membership_columns = tuple(
            parent.joint_parent.sparse._prompt_columns(
                str(user), ("Result", "Value")
            )
        )
        if not self.membership_suffix:
            return super()._synthesis(
                system, str(user), max_output_tokens=max_output_tokens
            )
        # Reproduce the frozen synthesis setup on the original prompt so the
        # verifier's same-forward page ordinals are not changed by treatment
        # text.  Only the bytes sent to the already-paid provider call gain the
        # visible membership suffix.
        del system
        self.synthesis_entry_count += 1
        columns = parent.joint_parent.sparse._prompt_columns(
            str(user), ("Result", "Value")
        )
        pages = parent.joint_parent.sparse._prompt_pages(str(user))
        self.synthesis_prompt_page_count = len(pages)
        if len(columns) >= 2:
            prepared = verifier.prepare_record_proposal(
                self._question, columns, pages
            )
            self.prepared_records = prepared
            self.verifier_bounded_page_count = int(prepared["bounded_page_count"])
            self.verifier_bounded_page_characters = int(
                prepared["bounded_page_characters"]
            )
            eligible = [int(page["page_ordinal"]) for page in prepared["pages"]]
            record_surface = (
                "Eligible page_ordinal values are "
                + json.dumps(eligible, separators=(",", ":"))
                + ". Ordinal N refers to [ENNNN] already displayed in "
                "BOUNDED WEB MATERIAL above. Only the first 2000 characters "
                "of each eligible E record are quote-verifiable; the shared "
                "aggregate verifier prefix is capped at 12000 characters. "
                "Do not quote any other region or ordinal."
            )
        else:
            self.prepared_records = None
            record_surface = "No non-key coordinate exists; records must be []."
        response = self._bounded.complete(
            parent.joint_parent.JOINT_SYNTHESIS_SYSTEM,
            str(user)
            + parent.joint_parent.JOINT_SYNTHESIS_USER_SUFFIX.format(
                record_surface=record_surface
            )
            + self.membership_suffix,
            max_output_tokens=max_output_tokens,
            json_mode=True,
        )
        text = score._model_text(response).strip()
        try:
            envelope = json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ValueError("V2.53.95 synthesis envelope is not exact JSON") from exc
        if (
            not isinstance(envelope, dict)
            or set(envelope) != {"table", "records"}
            or not isinstance(envelope.get("table"), str)
            or not envelope["table"].strip()
            or not isinstance(envelope.get("records"), list)
        ):
            raise ValueError("V2.53.95 synthesis envelope schema drifted")
        self.joint_envelope_exact = True
        self.envelope_record_count, self.envelope_field_count = (
            parent.joint_parent._safe_records(envelope["records"])
        )
        self.record_output = json.dumps(
            {"records": copy.deepcopy(envelope["records"])},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        normalized, _status = parent.joint_parent.robust._normalize_synthesis(
            str(envelope["table"]), columns, self._question
        )
        self.normalized_table = normalized
        self.joint_table_normalizable = normalized is not None
        return parent.table_normalizer._replace_text(
            response, str(envelope["table"])
        )


class _TaskLocalVerifier(parent._TaskLocalVerifier):
    """Preserve V2.53.89 source priority with normalized question binding."""

    def prepare_record_proposal(
        self,
        question: str,
        columns: Sequence[str],
        pages: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if len(columns) == 1:
            del question, pages
            return {"v25395_one_column_identity_noop": True}
        grounded = verifier.prepare_record_proposal(question, columns, pages)
        self._hybrid.grounded_prepared_records = copy.deepcopy(grounded)
        source = self._hybrid.choose_record_source()
        if source == "joint":
            prepared = self._hybrid.prepared_records
            if prepared is None:
                raise ValueError("V2.53.95 joint verifier state is absent")
        else:
            prepared = grounded
        if (
            editor.quote_parent._text(prepared.get("question"))
            != editor.quote_parent._text(question)
            or tuple(prepared.get("columns") or ()) != tuple(columns)
        ):
            raise ValueError("V2.53.95 selected verifier state drifted")
        return copy.deepcopy(prepared)


def _membership_counts(
    hybrid: _VisibleMembershipHybridInner,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    raw = changed_parent.validate_result(checked["private_parent_result"])
    base = str(raw["predictions"][CONTROL_ARM])
    matrix, canonical = editor._canonical_table(base, hybrid.membership_columns)
    observed = [] if matrix is None else [str(row[0]) for row in matrix[2:]]
    expected_keys = [
        editor.quote_parent._key(value) for value in hybrid.visible_members
    ]
    observed_keys = [editor.quote_parent._key(value) for value in observed]
    expected_set = set(expected_keys)
    observed_set = set(observed_keys)
    return {
        "visible_member_count": len(expected_keys),
        "membership_constraint_characters": len(hybrid.membership_suffix),
        "base_table_row_count": len(observed_keys),
        "base_visible_member_match_count": len(expected_set.intersection(observed_set)),
        "base_visible_member_missing_count": len(expected_set - observed_set),
        "base_nonmember_extra_count": len(observed_set - expected_set),
        "membership_constraint_applied": bool(expected_keys),
        "base_table_exact_canonical": bool(canonical),
        "base_visible_membership_order_exact": bool(
            expected_keys and observed_keys == expected_keys
        ),
        "base_visible_membership_exact": bool(
            expected_keys
            and canonical
            and observed_keys == expected_keys
            and len(observed_keys) == len(set(observed_keys))
        ),
    }


_INTEGER_FIELDS = (
    "visible_member_count",
    "membership_constraint_characters",
    "base_table_row_count",
    "base_visible_member_match_count",
    "base_visible_member_missing_count",
    "base_nonmember_extra_count",
    "positive_signed_credit_count",
)
_DYNAMIC_FLAGS = (
    "membership_constraint_applied",
    "base_table_exact_canonical",
    "base_visible_membership_order_exact",
    "base_visible_membership_exact",
)
_TRUE_FLAGS = (
    "membership_comes_only_from_strict_visible_question_grammar",
    "fetched_page_grounded_or_joint_record_never_creates_membership",
    "constraint_is_applied_before_the_existing_third_model_call",
    "no_constraint_returns_parent_third_call_prompt_byte_exact",
    "post_synthesis_row_append_delete_reorder_or_shape_change_forbidden",
    "joint_grounded_priority_and_verification_fallthrough_policy_unchanged",
    "frozen_normalizer_verifier_and_changed_safe_editor_replayed",
    "query4_fetch14_model3_caps_unchanged",
    "task_local_model_projector_verifier_and_editor_state",
)
_FALSE_FLAGS = (
    "additional_model_search_fetch_token_context_wall_or_network_budget",
    "contains_question_membership_identity_query_url_page_quote_field_value_prediction_answer_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
    "module_global_state_mutated",
    "benchmark_launch_or_evaluator_authorized",
)


def _receipt(
    hybrid: _VisibleMembershipHybridInner,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    counts = _membership_counts(hybrid, checked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "membership_source": hybrid.membership_source,
        **{name: int(counts.get(name, 0)) for name in _INTEGER_FIELDS},
        **{name: bool(counts[name]) for name in _DYNAMIC_FLAGS},
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
    source = copied.get("membership_source")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "membership_source",
        *_INTEGER_FIELDS,
        *_DYNAMIC_FLAGS,
        "parent_result_payload_sha256",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    applied = copied.get("membership_constraint_applied") is True
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or source not in MEMBERSHIP_SOURCES
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _INTEGER_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in _DYNAMIC_FLAGS)
        or copied["visible_member_count"] > MAXIMUM_VISIBLE_MEMBERS
        or applied is not (source != "none" and copied["visible_member_count"] > 0)
        or (not applied and copied["membership_constraint_characters"] != 0)
        or applied and copied["membership_constraint_characters"] <= 0
        or copied["base_visible_member_match_count"]
        > copied["visible_member_count"]
        or copied["base_visible_member_missing_count"]
        + copied["base_visible_member_match_count"]
        != copied["visible_member_count"]
        or copied["base_nonmember_extra_count"] > copied["base_table_row_count"]
        or copied["base_visible_membership_order_exact"]
        and not applied
        or copied["base_visible_membership_exact"]
        is not bool(
            applied
            and copied["base_table_exact_canonical"]
            and copied["base_visible_membership_order_exact"]
            and copied["base_visible_member_missing_count"] == 0
            and copied["base_nonmember_extra_count"] == 0
            and copied["base_table_row_count"] == copied["visible_member_count"]
        )
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.95 visible membership receipt drifted")
    if parent_result is not None:
        checked = parent.validate_result(parent_result)
        parent_hybrid = parent.validate_receipt(
            checked["hybrid_record_fallback_receipt"],
            parent_result=checked["private_parent_result"],
        )
        if (
            copied["parent_result_payload_sha256"]
            != checked["result_payload_sha256"]
            or parent_hybrid["model_entry_count"] > 3
        ):
            raise ValueError("V2.53.95 membership/parent binding drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    question: str,
    membership: Sequence[str],
    membership_source: str,
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    visible_question = str(question)
    visible = _safe_vector(membership)
    observed = validate_receipt(receipt, parent_result=checked)
    if (
        membership_source not in MEMBERSHIP_SOURCES
        or (bool(visible) is not (membership_source != "none"))
        or observed["membership_source"] != membership_source
        or observed["visible_member_count"] != len(visible)
        or visible_membership(visible_question) != (visible, membership_source)
    ):
        raise ValueError("V2.53.95 private membership binding drifted")
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
        "visible_membership_synthesis_receipt": copy.deepcopy(observed),
        "private_visible_membership": list(visible),
        "private_visible_question": visible_question,
        "private_membership_source": membership_source,
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_parent_hybrid_changed_safe_candidate": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("private_parent_result")
    membership = copied.get("private_visible_membership")
    question = copied.get("private_visible_question")
    source = copied.get("private_membership_source")
    receipt = copied.get("visible_membership_synthesis_receipt")
    if (
        not isinstance(raw, Mapping)
        or not isinstance(membership, list)
        or not isinstance(question, str)
        or not isinstance(source, str)
        or not isinstance(receipt, Mapping)
    ):
        raise ValueError("V2.53.95 private result surface is absent")
    expected = _wrap_result(raw, question, membership, source, receipt)
    if copied != expected:
        raise ValueError("V2.53.95 result adapter drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    membership = validate_receipt(
        checked["visible_membership_synthesis_receipt"],
        parent_result=checked["private_parent_result"],
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "visible_membership_synthesis_receipt": copy.deepcopy(membership),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "scored_prediction_is_parent_hybrid_changed_safe_candidate": True,
        "visible_membership_constraint_precedes_existing_third_call": True,
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
    membership = copied.get("visible_membership_synthesis_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "scored_prediction_is_parent_hybrid_changed_safe_candidate",
        "visible_membership_constraint_precedes_existing_third_call",
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
        "visible_membership_synthesis_receipt",
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
        or not isinstance(membership, Mapping)
        or validate_receipt(membership) != dict(membership)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or membership["parent_result_payload_sha256"]
        != copied.get("parent_runtime_result_payload_sha256")
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.95 stage receipt drifted")
    return copied


def _isolated_parent(
    projector: schema_parent._TaskLocalProjector,
    hybrid: _VisibleMembershipHybridInner,
) -> Callable[..., dict[str, Any]]:
    local_verifier = _TaskLocalVerifier(hybrid)
    local_editor = parent._TaskLocalEditor(hybrid)
    empty_namespace = dict(changed_parent._empty_editor.__globals__)
    empty_namespace.update({"verifier": local_verifier, "editor": local_editor})
    empty_editor = types.FunctionType(
        changed_parent._empty_editor.__code__,
        empty_namespace,
        name="v25395_task_local_empty_editor",
        argdefs=changed_parent._empty_editor.__defaults__,
        closure=changed_parent._empty_editor.__closure__,
    )
    empty_editor.__kwdefaults__ = dict(
        changed_parent._empty_editor.__kwdefaults__ or {}
    )
    namespace = dict(changed_parent.run_paired_task.__globals__)
    namespace.update(
        {
            "query_parent": SimpleNamespace(
                projected_plan=projector.projected_plan
            ),
            "verifier": local_verifier,
            "editor": local_editor,
            "_empty_editor": empty_editor,
        }
    )
    cloned = types.FunctionType(
        changed_parent.run_paired_task.__code__,
        namespace,
        name="v25395_task_local_visible_membership_parent",
        argdefs=changed_parent.run_paired_task.__defaults__,
        closure=changed_parent.run_paired_task.__closure__,
    )
    cloned.__kwdefaults__ = dict(
        changed_parent.run_paired_task.__kwdefaults__ or {}
    )
    cloned.__annotations__ = dict(changed_parent.run_paired_task.__annotations__)
    return cloned


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
        raise ValueError("V2.53.95 hard-capped model wiring drifted")
    projector = schema_parent._TaskLocalProjector(visible["question"])
    hybrid = _VisibleMembershipHybridInner(
        model._inner_limiter, question=visible["question"]
    )
    hybrid_model = cap.HardCappedModelLimiter(hybrid, budget)
    isolated = _isolated_parent(projector, hybrid)
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
    hybrid_receipt = parent._receipt(hybrid, changed)
    parent_result = parent.validate_result(
        parent._wrap_result(changed, schema_receipt, hybrid_receipt)
    )
    parent_stage = parent._stage_receipt(parent_result)
    membership_receipt = _receipt(hybrid, parent_result)
    result = validate_result(
        _wrap_result(
            parent_result,
            visible["question"],
            hybrid.visible_members,
            hybrid.membership_source,
            membership_receipt,
        )
    )
    return result, _stage_receipt(result, parent_stage)


__all__ = [
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "MEMBERSHIP_SOURCES",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "SCHEMA_SOURCES",
    "STAGE_RECEIPT_ROLE",
    "membership_suffix",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
    "visible_membership",
]
