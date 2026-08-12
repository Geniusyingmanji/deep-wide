"""Schema-total sparse production successor for V2.51.34.

V2.51.30 paid for two synthesis generations on every completed task although
only three tasks had a same-forward target-field page gain.  This build-only
successor keeps V2.51.34's plan, grounded two-wave retrieval, URL selection,
page projection, prompt salience, and hard caps, but changes the synthesis
effect policy:

* the stable arm is the single production synthesis;
* the candidate synthesis reaches the provider only after a same-forward,
  source/identity/field-bound page gain has been mechanically verified;
* without verified gain, the production response is replayed locally;
* a revision provider/normalizer failure, or any later parent projection
  failure, preserves the already-normalized production prediction verbatim.

The inherited parent still observes two arm entrypoints so its frozen causal
and accounting validators remain executable, but a local replay is not a
provider effect.  The new receipt distinguishes synthesis entrypoints,
provider forwards, provider requests, and validated outputs.  Runtime task
input remains exactly ``opaque_id`` and ``question`` plus injected bounded
clients.  No benchmark label, mapping, gold, evaluator, score, reward,
history, credential, file, environment, process, or network capability is
introduced.  Entropy/information gain assigns no signed credit, and this
module grants no benchmark or evaluator launch authority.
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
from . import v25110_exact_visible_schema as exact_schema
from . import v25117_grounded_target_record_plan as target_plan
from . import v25119_grounded_target_record_paired_runtime as paired
from . import v25123_visible_legacy_query_compatible_runtime as legacy
from . import v25134_schema_total_causal_salience_runtime as parent
from .clients import canonicalize_url, parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25135_schema_total_sparse_production_runtime_v1"
ROLE = "v25135_schema_total_sparse_production_runtime_result"
RECEIPT_ROLE = "v25135_content_free_sparse_production_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES
SCHEMA_SOURCES = parent.SCHEMA_SOURCES

_MODEL_COUNTERS = counters._MODEL_COUNTERS
_SEARCH_COUNTERS = counters._SEARCH_COUNTERS
_EVIDENCE_HEADER = "BOUNDED WEB MATERIAL:\n"
_EVIDENCE_SUFFIX = "\n\nProduce the best-supported answer possible"


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _validate_boundary(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
) -> dict[str, str]:
    """Reject wiring, budget, and privileged-input drift before any effect."""

    visible = score.validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.51.35 requires a bounded global model limiter")
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], RobustLatePageBoundSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.51.35 requires two distinct robust search clients")
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
        raise ValueError("V2.51.35 production-shaped budget drifted")
    if any(
        any(counters._counter(searches[phase], _SEARCH_COUNTERS).values())
        for phase in PHASES
    ):
        raise ValueError("V2.51.35 requires pristine search clients")
    return visible


def _prompt_columns(user: str, fallback: Sequence[str]) -> tuple[str, ...]:
    marker = "\n\nREQUIRED COLUMNS:\n"
    end_marker = "\n\n" + _EVIDENCE_HEADER
    start = user.find(marker)
    end = user.find(end_marker, start + len(marker))
    if start >= 0 and end >= 0:
        try:
            value = json.loads(user[start + len(marker) : end])
            if isinstance(value, list):
                columns = target_plan._safe_columns(value)
                if columns:
                    return columns
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return target_plan._safe_columns(list(fallback))


def _prompt_pages(user: str) -> list[dict[str, str]]:
    """Recover only the already-rendered same-forward page records."""

    start = user.find(_EVIDENCE_HEADER)
    end = user.find(_EVIDENCE_SUFFIX, start + len(_EVIDENCE_HEADER))
    if start < 0 or end < 0:
        raise ValueError("V2.51.35 synthesis prompt boundary drifted")
    body = user[start + len(_EVIDENCE_HEADER) : end]
    matches = list(parent.causal._RECORD.finditer(body))
    output: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        record = body[match.end() : stop].strip()
        lines = record.splitlines()
        if len(lines) < 3 or not lines[0].startswith("title=") or not lines[1].startswith("url=") or not lines[2].startswith("content="):
            raise ValueError("V2.51.35 evidence record grammar drifted")
        url = canonicalize_url(lines[1][len("url=") :].strip())
        if not url:
            raise ValueError("V2.51.35 evidence URL drifted")
        output.append(
            {
                "title": lines[0][len("title=") :],
                "url": url,
                "content": "\n".join(
                    [lines[2][len("content=") :], *lines[3:]]
                ).rstrip(),
            }
        )
    return output


def _page_identity(pages: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    return tuple(canonicalize_url(str(page.get("url") or "")) for page in pages)


class SparseProductionModel(DeadlineAwareGlobalModelSlotLimiter):
    """Transparent bounded proxy that suppresses dense second synthesis."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
        first_wave_search: RobustLatePageBoundSearchClient,
        limits: score.ScoreFirstLimits,
    ) -> None:
        if not isinstance(bounded, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.51.35 requires a bounded global model limiter")
        if not isinstance(first_wave_search, RobustLatePageBoundSearchClient):
            raise TypeError("V2.51.35 requires a bounded first-wave search client")
        self._bounded = bounded
        self._question = str(question)
        self._first_wave_search = first_wave_search
        self._limits = limits
        self.plan_provider_forward_count = 0
        self.grounded_plan_provider_forward_count = 0
        self.production_synthesis_entry_count = 0
        self.production_synthesis_provider_forward_count = 0
        self.revision_synthesis_entry_count = 0
        self.revision_synthesis_provider_forward_count = 0
        self.plan_failure_type: str | None = None
        self.grounded_plan_failure_type: str | None = None
        self.gain_verification_failure_type: str | None = None
        self.production_failure_type: str | None = None
        self.revision_failure_type: str | None = None
        self._raw_plan: dict[str, Any] = {}
        self._grounded_output = ""
        self._grounded_attempted = False
        self._production_response: Any = None
        self._production_user = ""
        self.production_prediction: str | None = None
        self.revision_prediction: str | None = None
        self.production_provider_valid_output = False
        self.revision_provider_valid_output = False
        self.identity_replay_used = False
        self.selection_changed = False
        self.target_field_page_gain = 0
        self.target_field_pair_gain = 0
        self.complete_target_field_page_gain = 0
        self.verified_gain = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bounded, name)

    def remaining_effect_seconds(self) -> float:
        return float(self._bounded.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._bounded.receipt()

    def _columns(self) -> tuple[str, ...]:
        return parent._total_columns(self._raw_plan, self._question)[0]

    def _completed_plan(self) -> dict[str, Any]:
        value = copy.deepcopy(self._raw_plan)
        columns, _source = parent._total_columns(value, self._question)
        seeds, _observation = legacy._query_seeds(value, self._question)
        value["columns"] = list(columns)
        value["queries"] = seeds
        return exact_schema.validated_exact_plan(value, self._question, self._limits)

    def _selected_grounded_plan(
        self, pages: Sequence[Mapping[str, str]]
    ) -> dict[str, Any]:
        plan = self._completed_plan()
        receipt = self._first_wave_search.late_page_projection_receipt()
        count = receipt.get("projected_page_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("V2.51.35 first-wave projection count drifted")
        if count > len(pages):
            raise ValueError("V2.51.35 first-wave page count exceeds evidence")
        shared = list(pages[len(pages) - count :]) if count else []
        prepared = target_plan.prepare_plan(
            self._question, plan["columns"], plan["queries"], shared
        )
        return target_plan.select_plan(
            prepared,
            self._grounded_output,
            model_call_attempted=self._grounded_attempted,
        )

    def _verify_gain(
        self,
        control_user: str,
        candidate_user: str,
        columns: Sequence[str],
    ) -> None:
        try:
            control_pages = _prompt_pages(control_user)
            candidate_pages = _prompt_pages(candidate_user)
            grounded = self._selected_grounded_plan(control_pages)
            observations = {
                CONTROL_ARM: paired._page_field_counts(
                    control_pages,
                    row_targets=grounded["row_targets"],
                    pivots=grounded["pivots"],
                    authority_terms=grounded["authority_terms"],
                    columns=columns,
                ),
                CANDIDATE_ARM: paired._page_field_counts(
                    candidate_pages,
                    row_targets=grounded["row_targets"],
                    pivots=grounded["pivots"],
                    authority_terms=grounded["authority_terms"],
                    columns=columns,
                ),
            }
            control = observations[CONTROL_ARM]
            candidate = observations[CANDIDATE_ARM]
            self.selection_changed = _page_identity(control_pages) != _page_identity(
                candidate_pages
            )
            self.target_field_page_gain = (
                candidate["target_field_page_count"]
                - control["target_field_page_count"]
            )
            self.target_field_pair_gain = (
                candidate["target_field_pair_count"]
                - control["target_field_pair_count"]
            )
            self.complete_target_field_page_gain = (
                candidate["complete_target_field_page_count"]
                - control["complete_target_field_page_count"]
            )
            self.verified_gain = bool(
                self.selection_changed and self.target_field_page_gain > 0
            )
        except BaseException as exc:
            self.gain_verification_failure_type = _safe_failure(exc)
            self.selection_changed = False
            self.target_field_page_gain = 0
            self.target_field_pair_gain = 0
            self.complete_target_field_page_gain = 0
            self.verified_gain = False

    def _production(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        self.production_synthesis_entry_count = 1
        self.production_synthesis_provider_forward_count = 1
        columns = _prompt_columns(user, self._columns())
        fallback = counters._fallback(columns)
        try:
            response = self._bounded.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            parsed, _status = robust._normalize_synthesis(
                score._model_text(response), columns, self._question
            )
            if parsed is None:
                raise ValueError("V2.51.35 production synthesis contract failed")
        except BaseException as exc:
            self.production_failure_type = _safe_failure(exc)
            self._production_response = fallback
            normalized, _status = robust._normalize_synthesis(
                fallback, columns, self._question
            )
            self.production_prediction = normalized or fallback
            return fallback
        self._production_response = response
        self.production_prediction = parsed
        self.production_provider_valid_output = True
        return response

    def _revision(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool,
    ) -> Any:
        self.revision_synthesis_entry_count = 1
        if self._production_response is None or self.production_prediction is None:
            raise RuntimeError("V2.51.35 revision preceded production")
        columns = _prompt_columns(user, self._columns())
        self._verify_gain(self._production_user, user, columns)
        eligible = bool(self.verified_gain and self.production_provider_valid_output)
        if not eligible:
            self.identity_replay_used = True
            return self._production_response
        self.revision_synthesis_provider_forward_count = 1
        try:
            response = self._bounded.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            parsed, _status = robust._normalize_synthesis(
                score._model_text(response), columns, self._question
            )
            if parsed is None:
                raise ValueError("V2.51.35 revision synthesis contract failed")
        except BaseException as exc:
            self.revision_failure_type = _safe_failure(exc)
            self.identity_replay_used = True
            return self._production_response
        self.revision_prediction = parsed
        self.revision_provider_valid_output = True
        return response

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        if system == score.PLAN_SYSTEM:
            self.plan_provider_forward_count += 1
            try:
                response = self._bounded.complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
                self._raw_plan = parse_json_object(score._model_text(response))
                return response
            except BaseException as exc:
                self.plan_failure_type = _safe_failure(exc)
                self._raw_plan = {}
                raise
        if system.startswith(target_plan.SYSTEM_PROMPT):
            self.grounded_plan_provider_forward_count += 1
            self._grounded_attempted = True
            try:
                response = self._bounded.complete(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
                self._grounded_output = score._model_text(response)
                return response
            except BaseException as exc:
                self.grounded_plan_failure_type = _safe_failure(exc)
                self._grounded_output = ""
                raise
        if system == score.SYNTHESIS_SYSTEM:
            if self.production_synthesis_entry_count == 0:
                self._production_user = str(user)
                return self._production(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
            if self.revision_synthesis_entry_count == 0:
                return self._revision(
                    system,
                    user,
                    max_output_tokens=max_output_tokens,
                    json_mode=json_mode,
                )
            raise ValueError("V2.51.35 too many synthesis entrypoints")
        raise ValueError("V2.51.35 unexpected model stage")


def _receipt(
    *,
    sparse: SparseProductionModel,
    schema_source: str,
    effective_column_count: int,
    final_prediction: str,
    post_effect_failure: str | None,
    model_cost: Mapping[str, int],
    physical_query_count: int,
    physical_fetch_count: int,
    system_total_tokens: int,
) -> dict[str, Any]:
    production = sparse.production_prediction
    if production is None:
        production = counters._fallback(sparse._columns())
    revision_eligible = bool(
        sparse.revision_synthesis_entry_count
        and sparse.verified_gain
        and sparse.production_provider_valid_output
    )
    preservation_required = bool(
        sparse.revision_failure_type is not None or post_effect_failure is not None
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "schema_source": schema_source,
        "effective_column_count": int(effective_column_count),
        "plan_provider_forward_count": sparse.plan_provider_forward_count,
        "grounded_plan_provider_forward_count": sparse.grounded_plan_provider_forward_count,
        "production_synthesis_entry_count": sparse.production_synthesis_entry_count,
        "production_synthesis_provider_forward_count": sparse.production_synthesis_provider_forward_count,
        "revision_synthesis_entry_count": sparse.revision_synthesis_entry_count,
        "revision_synthesis_provider_forward_count": sparse.revision_synthesis_provider_forward_count,
        "provider_forward_count": (
            sparse.plan_provider_forward_count
            + sparse.grounded_plan_provider_forward_count
            + sparse.production_synthesis_provider_forward_count
            + sparse.revision_synthesis_provider_forward_count
        ),
        "model_provider_request_count": int(model_cost["requests"]),
        "model_provider_attempt_count": int(model_cost["attempts"]),
        "physical_query_count": int(physical_query_count),
        "physical_fetch_count": int(physical_fetch_count),
        "system_total_tokens": int(system_total_tokens),
        "selection_changed": sparse.selection_changed,
        "target_field_page_gain": sparse.target_field_page_gain,
        "target_field_pair_gain": sparse.target_field_pair_gain,
        "complete_target_field_page_gain": sparse.complete_target_field_page_gain,
        "verified_source_identity_field_gain": sparse.verified_gain,
        "production_provider_output_valid": sparse.production_provider_valid_output,
        "production_fallback_used": not sparse.production_provider_valid_output,
        "revision_eligible": revision_eligible,
        "revision_provider_output_valid": sparse.revision_provider_valid_output,
        "identity_replay_used": sparse.identity_replay_used,
        "gain_verification_failure_present": sparse.gain_verification_failure_type
        is not None,
        "revision_failure_present": sparse.revision_failure_type is not None,
        "post_effect_failure_present": post_effect_failure is not None,
        "production_prediction_preserved": bool(
            not preservation_required or final_prediction == production
        ),
        "final_prediction_changed_from_production": final_prediction != production,
        "one_production_synthesis_without_verified_gain": True,
        "second_provider_synthesis_only_after_same_forward_verified_gain": True,
        "revision_or_posteffect_failure_preserves_production_prediction": True,
        "same_forward_source_identity_field_binding_required": True,
        "provider_replay_is_not_counted_as_provider_effect": True,
        "physical_model_forward_cap": 4,
        "no_gain_physical_model_forward_cap": 3,
        "physical_query_cap": 4,
        "physical_fetch_cap": 14,
        "per_task_wall_second_cap": 240,
        "per_task_evidence_character_cap": 60_000,
        "contains_question_column_query_url_title_page_target_prediction_answer_opaque_id_or_credential": False,
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
    counts = (
        "effective_column_count",
        "plan_provider_forward_count",
        "grounded_plan_provider_forward_count",
        "production_synthesis_entry_count",
        "production_synthesis_provider_forward_count",
        "revision_synthesis_entry_count",
        "revision_synthesis_provider_forward_count",
        "provider_forward_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "physical_query_count",
        "physical_fetch_count",
        "system_total_tokens",
        "physical_model_forward_cap",
        "no_gain_physical_model_forward_cap",
        "physical_query_cap",
        "physical_fetch_cap",
        "per_task_wall_second_cap",
        "per_task_evidence_character_cap",
    )
    signed = (
        "target_field_page_gain",
        "target_field_pair_gain",
        "complete_target_field_page_gain",
    )
    bool_fields = (
        "selection_changed",
        "verified_source_identity_field_gain",
        "production_provider_output_valid",
        "production_fallback_used",
        "revision_eligible",
        "revision_provider_output_valid",
        "identity_replay_used",
        "gain_verification_failure_present",
        "revision_failure_present",
        "post_effect_failure_present",
        "production_prediction_preserved",
        "final_prediction_changed_from_production",
    )
    true_flags = (
        "one_production_synthesis_without_verified_gain",
        "second_provider_synthesis_only_after_same_forward_verified_gain",
        "revision_or_posteffect_failure_preserves_production_prediction",
        "same_forward_source_identity_field_binding_required",
        "provider_replay_is_not_counted_as_provider_effect",
    )
    false_flags = (
        "contains_question_column_query_url_title_page_target_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "schema_source",
        *counts,
        *signed,
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
        or copied.get("schema_source") not in SCHEMA_SOURCES
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            for name in signed
        )
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or not 1 <= copied["effective_column_count"] <= 20
        or copied["plan_provider_forward_count"] != 1
        or copied["grounded_plan_provider_forward_count"] not in {0, 1}
        or copied["production_synthesis_entry_count"] not in {0, 1}
        or copied["production_synthesis_provider_forward_count"]
        != copied["production_synthesis_entry_count"]
        or copied["revision_synthesis_entry_count"] not in {0, 1}
        or copied["revision_synthesis_provider_forward_count"] not in {0, 1}
        or copied["provider_forward_count"]
        != copied["plan_provider_forward_count"]
        + copied["grounded_plan_provider_forward_count"]
        + copied["production_synthesis_provider_forward_count"]
        + copied["revision_synthesis_provider_forward_count"]
        or copied["provider_forward_count"] > 4
        or copied["model_provider_request_count"] > copied["provider_forward_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or copied["physical_query_count"] > 4
        or copied["physical_fetch_count"] > 14
        or copied["verified_source_identity_field_gain"]
        is not bool(copied["selection_changed"] and copied["target_field_page_gain"] > 0)
        or copied["production_provider_output_valid"]
        and copied["production_synthesis_provider_forward_count"] != 1
        or copied["production_fallback_used"]
        is copied["production_provider_output_valid"]
        or copied["revision_eligible"]
        is not bool(
            copied["revision_synthesis_entry_count"]
            and copied["verified_source_identity_field_gain"]
            and copied["production_provider_output_valid"]
        )
        or copied["revision_synthesis_provider_forward_count"]
        != int(copied["revision_eligible"])
        or copied["revision_provider_output_valid"]
        and (
            not copied["revision_eligible"]
            or copied["revision_failure_present"]
        )
        or copied["identity_replay_used"]
        is not bool(
            copied["revision_synthesis_entry_count"]
            and not copied["revision_provider_output_valid"]
        )
        or not copied["verified_source_identity_field_gain"]
        and copied["revision_synthesis_provider_forward_count"] != 0
        or copied["post_effect_failure_present"]
        and copied["final_prediction_changed_from_production"]
        or (copied["revision_failure_present"] or copied["post_effect_failure_present"])
        and not copied["production_prediction_preserved"]
        or copied["final_prediction_changed_from_production"]
        and not copied["revision_provider_output_valid"]
        or copied["physical_model_forward_cap"] != 4
        or copied["no_gain_physical_model_forward_cap"] != 3
        or copied["physical_query_cap"] != 4
        or copied["physical_fetch_cap"] != 14
        or copied["per_task_wall_second_cap"] != 240
        or copied["per_task_evidence_character_cap"] != 60_000
        or not copied["verified_source_identity_field_gain"]
        and copied["provider_forward_count"] > 3
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.35 sparse production receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = _validate_boundary(task, model=model, searches=searches, limits=limits)
    model_before = counters._counter(model, _MODEL_COUNTERS)
    search_before = {
        phase: counters._counter(searches[phase], _SEARCH_COUNTERS)
        for phase in PHASES
    }
    sparse = SparseProductionModel(
        model,
        question=visible["question"],
        first_wave_search=searches[FIRST_PHASE],
        limits=limits,
    )
    parent_result: dict[str, Any] | None = None
    post_effect_failure: str | None = None
    try:
        parent_result = parent.validate_result(
            parent.run_paired_task(
                visible,
                model=sparse,
                searches=searches,
                limits=limits,
                arm_order=ARMS,
                monotonic=monotonic,
            )
        )
    except BaseException as exc:
        post_effect_failure = _safe_failure(exc)

    model_cost = counters._delta(
        counters._counter(model, _MODEL_COUNTERS), model_before
    )
    search_cost = {
        phase: counters._delta(
            counters._counter(searches[phase], _SEARCH_COUNTERS),
            search_before[phase],
        )
        for phase in PHASES
    }
    system_total_tokens = model_cost["total_tokens"] + sum(
        value["total_tokens"] for value in search_cost.values()
    )
    if parent_result is not None:
        parent_receipt = parent_result["content_free_receipt"]
        physical_query_count = int(parent_receipt["physical_query_count"])
        physical_fetch_count = int(parent_receipt["physical_fetch_count"])
        schema_source = str(parent_result["schema_totality_receipt"]["schema_source"])
        effective_column_count = int(
            parent_result["schema_totality_receipt"]["effective_column_count"]
        )
        production = parent_result["predictions"][CONTROL_ARM]
        final_prediction = parent_result["predictions"][CANDIDATE_ARM]
    else:
        physical_query_count = 2 * sum(
            value["calls"] for value in search_cost.values()
        )
        physical_fetch_count = sum(
            value["fetch_calls"] for value in search_cost.values()
        )
        columns, schema_source = parent._total_columns(
            sparse._raw_plan, visible["question"]
        )
        effective_column_count = len(columns)
        production = sparse.production_prediction or counters._fallback(columns)
        final_prediction = production

    receipt = _receipt(
        sparse=sparse,
        schema_source=schema_source,
        effective_column_count=effective_column_count,
        final_prediction=final_prediction,
        post_effect_failure=post_effect_failure,
        model_cost=model_cost,
        physical_query_count=physical_query_count,
        physical_fetch_count=physical_fetch_count,
        system_total_tokens=system_total_tokens,
    )
    failures = {
        "plan": sparse.plan_failure_type,
        "grounded_plan": sparse.grounded_plan_failure_type,
        "gain_verification": sparse.gain_verification_failure_type,
        "production": sparse.production_failure_type,
        "revision": sparse.revision_failure_type,
        "post_effect": post_effect_failure,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "production_prediction": production,
        "production_prediction_sha256": hashlib.sha256(production.encode()).hexdigest(),
        "prediction": final_prediction,
        "prediction_sha256": hashlib.sha256(final_prediction.encode()).hexdigest(),
        "prediction_kind": (
            "model_generated"
            if sparse.production_provider_valid_output
            else "fallback"
        ),
        "failure_types": failures,
        "parent_result": copy.deepcopy(parent_result),
        "parent_result_payload_sha256": (
            None
            if parent_result is None
            else parent_result["result_payload_sha256"]
        ),
        "cost": {
            "model": model_cost,
            "search": search_cost,
            "system_total_tokens": system_total_tokens,
        },
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
    production = copied.get("production_prediction")
    prediction = copied.get("prediction")
    failures = copied.get("failure_types")
    parent_result = copied.get("parent_result")
    cost = copied.get("cost")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "production_prediction",
        "production_prediction_sha256",
        "prediction",
        "prediction_sha256",
        "prediction_kind",
        "failure_types",
        "parent_result",
        "parent_result_payload_sha256",
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
        or not isinstance(production, str)
        or not production
        or not isinstance(prediction, str)
        or not prediction
        or copied.get("production_prediction_sha256")
        != hashlib.sha256(production.encode()).hexdigest()
        or copied.get("prediction_sha256")
        != hashlib.sha256(prediction.encode()).hexdigest()
        or copied.get("prediction_kind") not in {"model_generated", "fallback"}
        or not isinstance(failures, Mapping)
        or set(failures)
        != {
            "plan",
            "grounded_plan",
            "gain_verification",
            "production",
            "revision",
            "post_effect",
        }
        or any(
            failure is not None
            and (
                not isinstance(failure, str)
                or not failure
                or len(failure) > 128
            )
            for failure in failures.values()
        )
        or not isinstance(cost, Mapping)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or not isinstance(cost.get("model"), Mapping)
        or set(cost["model"]) != set(_MODEL_COUNTERS)
        or any(
            isinstance(cost["model"].get(name), bool)
            or not isinstance(cost["model"].get(name), int)
            or cost["model"][name] < 0
            for name in _MODEL_COUNTERS
        )
        or set(cost.get("search") or {}) != set(PHASES)
        or any(
            not isinstance(cost["search"].get(phase), Mapping)
            or set(cost["search"][phase]) != set(_SEARCH_COUNTERS)
            or any(
                isinstance(cost["search"][phase].get(name), bool)
                or not isinstance(cost["search"][phase].get(name), int)
                or cost["search"][phase][name] < 0
                for name in _SEARCH_COUNTERS
            )
            for phase in PHASES
        )
        or cost.get("system_total_tokens")
        != cost["model"]["total_tokens"]
        + sum(cost["search"][phase]["total_tokens"] for phase in PHASES)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["model_provider_request_count"] != cost["model"]["requests"]
        or receipt["model_provider_attempt_count"] != cost["model"]["attempts"]
        or receipt["system_total_tokens"] != cost["system_total_tokens"]
        or receipt["gain_verification_failure_present"]
        is not (failures["gain_verification"] is not None)
        or receipt["revision_failure_present"]
        is not (failures["revision"] is not None)
        or receipt["post_effect_failure_present"]
        is not (failures["post_effect"] is not None)
        or receipt["production_prediction_preserved"]
        is not bool(
            failures["revision"] is None
            and failures["post_effect"] is None
            or prediction == production
        )
        or receipt["final_prediction_changed_from_production"]
        is not (prediction != production)
        or copied["prediction_kind"]
        != ("model_generated" if receipt["production_provider_output_valid"] else "fallback")
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.35 sparse production result envelope drifted")

    if parent_result is None:
        if (
            copied.get("parent_result_payload_sha256") is not None
            or failures["post_effect"] is None
            or prediction != production
        ):
            raise ValueError("V2.51.35 preservation fallback drifted")
        return copied

    checked_parent = parent.validate_result(parent_result)
    core = checked_parent["content_free_receipt"]
    schema_receipt = checked_parent["schema_totality_receipt"]
    if (
        failures["post_effect"] is not None
        or copied.get("parent_result_payload_sha256")
        != checked_parent["result_payload_sha256"]
        or production != checked_parent["predictions"][CONTROL_ARM]
        or prediction != checked_parent["predictions"][CANDIDATE_ARM]
        or cost != checked_parent["cost"]
        or receipt["schema_source"] != schema_receipt["schema_source"]
        or receipt["effective_column_count"]
        != schema_receipt["effective_column_count"]
        or receipt["physical_query_count"] != core["physical_query_count"]
        or receipt["physical_fetch_count"] != core["physical_fetch_count"]
        or not receipt["gain_verification_failure_present"]
        and (
            receipt["selection_changed"] != core["selection_changed"]
            or receipt["target_field_page_gain"]
            != core["target_field_page_gain"]
            or receipt["target_field_pair_gain"]
            != core["target_field_pair_gain"]
            or receipt["complete_target_field_page_gain"]
            != core["complete_target_field_page_gain"]
            or receipt["verified_source_identity_field_gain"]
            != core["retrieval_mechanism_engaged"]
        )
        or receipt["production_synthesis_entry_count"]
        != int(core["arm_metrics"][CONTROL_ARM]["synthesis_attempted"])
        or receipt["revision_synthesis_entry_count"]
        != int(core["arm_metrics"][CANDIDATE_ARM]["synthesis_attempted"])
    ):
        raise ValueError("V2.51.35 sparse production parent binding drifted")
    return copied


run_sparse_production_task = run_task


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
    "SparseProductionModel",
    "run_sparse_production_task",
    "run_task",
    "validate_receipt",
    "validate_result",
]
