"""Paired-runtime integration for V2.49.88 short authority queries.

The model proxy intercepts only the single planning response already admitted
by V2.49.86.  It replaces the private query vector with the deterministic
V2.49.88 vector when the visible tagged identity, explicit authority phrase,
and robust schema are all available.  Synthesis responses pass through byte
for byte.  No model call, search query, fetch target, token, context, byte, or
wall cap is added.

The wrapper returns the unchanged V2.49.86 paired result plus one content-free
query receipt.  It accepts only the visible task and injected bounded clients;
there is no benchmark-label, mapping, gold, evaluator, score, reward,
historical-result, or credential capability.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24986_robust_paired_runtime as parent
from .clients import parse_json_object
from .v24257_score_first_runtime import ScoreFirstLimits, _model_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24981_late_page_bound_fetch import LatePageBoundSearchClient
from .v24988_short_authority_queries import (
    build_short_queries,
    validate_receipt as validate_short_query_receipt,
)


POLICY_ID = "v24989_short_authority_query_paired_runtime_v1"
ROLE = "v24989_short_authority_query_paired_result"


@dataclasses.dataclass(frozen=True)
class _TextResult:
    text: str


def _replace_text(value: Any, text: str) -> Any:
    if isinstance(value, str):
        return text
    if dataclasses.is_dataclass(value):
        return dataclasses.replace(value, text=text)
    return _TextResult(text=text)


class ShortQueryPlanningModel(DeadlineAwareGlobalModelSlotLimiter):
    """Type-preserving proxy over the already bounded production limiter."""

    def __init__(self, inner: DeadlineAwareGlobalModelSlotLimiter, *, question: str) -> None:
        if not isinstance(inner, DeadlineAwareGlobalModelSlotLimiter):
            raise ValueError("V2.49.89 requires the bounded global model limiter")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("V2.49.89 visible question is absent")
        # Do not initialize a second limiter or allocate another slot surface.
        self.inner = inner
        self.question = question.strip()
        self.receipts: list[dict[str, Any]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        try:
            result = self.inner.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        except BaseException:
            if json_mode:
                transformed = build_short_queries(
                    self.question,
                    [],
                    provider_query_vector_valid=False,
                )
                self.receipts.append(
                    copy.deepcopy(transformed["content_free_receipt"])
                )
            raise
        if not json_mode:
            return result
        try:
            value = parse_json_object(_model_text(result))
        except (TypeError, ValueError):
            value = {}
        raw_queries = value.get("queries")
        provider_query_vector_valid = isinstance(raw_queries, list)
        provider_queries = list(raw_queries) if provider_query_vector_valid else []
        transformed = build_short_queries(
            self.question,
            provider_queries,
            provider_query_vector_valid=provider_query_vector_valid,
        )
        self.receipts.append(copy.deepcopy(transformed["content_free_receipt"]))
        if transformed["content_free_receipt"]["strategy_applied"] is not True:
            return result
        output = dict(value)
        output["queries"] = list(transformed["queries"])
        return _replace_text(
            result,
            json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        )


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: LatePageBoundSearchClient,
    limits: ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    question = str(task.get("question") or "") if isinstance(task, Mapping) else ""
    proxy = ShortQueryPlanningModel(model, question=question)
    kwargs: dict[str, Any] = {
        "model": proxy,
        "search": search,
        "limits": limits,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    base = parent.run_paired_task(task, **kwargs)
    if len(proxy.receipts) != 1:
        raise RuntimeError("V2.49.89 planning receipt cardinality drifted")
    short_receipt = copy.deepcopy(proxy.receipts[0])
    inherited = base["robust_runtime_receipt"]
    # The parent sees the already transformed JSON response.  Restore the
    # actual provider/planner count so the nested receipt does not claim that
    # deterministic queries were model-generated.
    base["robust_runtime_receipt"] = parent._runtime_receipt(
        {
            "first_synthesis_arm": inherited["first_synthesis_arm"],
            "provider_unique_query_count": short_receipt[
                "provider_unique_query_count"
            ],
            "completed_query_count": inherited["completed_query_count"],
            "deterministically_added_query_count": (
                inherited["completed_query_count"]
                - short_receipt["provider_unique_query_count"]
            ),
            "robust_visible_schema_column_count": inherited[
                "robust_visible_schema_column_count"
            ],
            "normalizer_attempt_count": inherited["normalizer_attempt_count"],
            "exact_table_count": inherited["exact_table_count"],
            "normalizer_recovery_count": inherited["normalizer_recovery_count"],
            "normalizer_unrecoverable_count": inherited[
                "normalizer_unrecoverable_count"
            ],
        }
    )
    base.pop("result_payload_sha256", None)
    base["result_payload_sha256"] = payload_sha256(base)
    parent.validate_result(base)
    value = copy.deepcopy(base)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["short_query_receipt"] = short_receipt
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    receipt = copied.get("short_query_receipt")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(receipt, Mapping)
        or validate_short_query_receipt(receipt) != dict(receipt)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.89 paired result drifted")
    base = copy.deepcopy(copied)
    base.pop("short_query_receipt", None)
    base["role"] = parent.ROLE
    base["policy_id"] = parent.POLICY_ID
    base.pop("result_payload_sha256", None)
    base["result_payload_sha256"] = payload_sha256(base)
    parent.validate_result(base)
    robust = copied["robust_runtime_receipt"]
    applied = receipt["strategy_applied"]
    expected_output_count = (
        robust["completed_query_count"]
        if applied
        else robust["provider_unique_query_count"]
    )
    if (
        receipt["output_query_count"] != expected_output_count
        or (applied and receipt["output_query_count"] != 4)
        or receipt["provider_unique_query_count"]
        != robust["provider_unique_query_count"]
        or robust["deterministically_added_query_count"]
        != robust["completed_query_count"] - receipt["provider_unique_query_count"]
    ):
        raise ValueError("V2.49.89 query/runtime receipt binding drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "ROLE",
    "ShortQueryPlanningModel",
    "run_paired_task",
    "validate_result",
]
