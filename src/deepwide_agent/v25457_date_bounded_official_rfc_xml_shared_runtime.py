"""Shared runtime using the date-bounded official RFC XML primitive.

This successor keeps V2.54.50's one-parent execution, content-free capacity
receipt, deterministic official URL vector, exact non-redirect admission,
and 4-query / 14-fetch / 3-model envelope.  Only the pure candidate module
is rebound to V2.54.56 in a private function namespace; V2.54.50 globals are
not mutated.  The candidate still adds zero query/model calls and at most
four capacity-safe fetches.

Runtime inputs remain visible ``opaque_id`` and ``question`` plus injected
bounded clients.  No benchmark label, mapping, gold, evaluator, score,
reward, credential, truth, or historical result is available.  This module
grants no launch and assigns no entropy/information-gain credit.
"""

from __future__ import annotations

import types
from collections.abc import Callable
from typing import Any

from . import v25450_official_rfc_xml_shared_runtime as parent_runtime
from . import v25456_date_bounded_official_rfc_xml_record_candidate as candidates


POLICY_ID = "v25457_date_bounded_official_rfc_xml_shared_runtime_v1"
ROLE = "v25457_date_bounded_official_rfc_xml_shared_runtime_result"
RECEIPT_ROLE = "v25457_content_free_date_bounded_official_rfc_xml_shared_receipt"
STAGE_RECEIPT_ROLE = (
    "v25457_content_free_date_bounded_official_rfc_xml_shared_stage_receipt"
)
ARMS = ("shared_base_table", "date_bounded_official_rfc_xml_record_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent_runtime.PHASES
SECOND_PHASE = parent_runtime.SECOND_PHASE
ProductionOnlyStageError = parent_runtime.ProductionOnlyStageError
payload_sha256 = parent_runtime.payload_sha256


def _clone(function: Callable[..., Any], namespace: dict[str, Any]) -> Callable[..., Any]:
    cloned = types.FunctionType(
        function.__code__,
        namespace,
        name=function.__name__.replace("v25450", "v25457"),
        argdefs=function.__defaults__,
        closure=function.__closure__,
    )
    cloned.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    cloned.__annotations__ = dict(function.__annotations__)
    cloned.__doc__ = function.__doc__
    return cloned


_NAMESPACE = dict(parent_runtime.__dict__)
_NAMESPACE.update(
    {
        "POLICY_ID": POLICY_ID,
        "ROLE": ROLE,
        "RECEIPT_ROLE": RECEIPT_ROLE,
        "STAGE_RECEIPT_ROLE": STAGE_RECEIPT_ROLE,
        "ARMS": ARMS,
        "BASE_ARM": BASE_ARM,
        "CANDIDATE_ARM": CANDIDATE_ARM,
        "PHASES": PHASES,
        "SECOND_PHASE": SECOND_PHASE,
        "ProductionOnlyStageError": ProductionOnlyStageError,
        "candidates": candidates,
        "payload_sha256": payload_sha256,
    }
)

for _name in (
    "_safe_failure",
    "_exact_success_urls",
    "_official_pages",
    "_fetch_candidate",
    "_receipt",
    "validate_receipt",
    "_wrap_result",
    "validate_result",
    "_stage_receipt",
    "validate_stage_receipt",
    "run_task",
):
    _NAMESPACE[_name] = _clone(getattr(parent_runtime, _name), _NAMESPACE)

_safe_failure = _NAMESPACE["_safe_failure"]
_exact_success_urls = _NAMESPACE["_exact_success_urls"]
_official_pages = _NAMESPACE["_official_pages"]
_fetch_candidate = _NAMESPACE["_fetch_candidate"]
_receipt = _NAMESPACE["_receipt"]
validate_receipt = _NAMESPACE["validate_receipt"]
_wrap_result = _NAMESPACE["_wrap_result"]
validate_result = _NAMESPACE["validate_result"]
_stage_receipt = _NAMESPACE["_stage_receipt"]
validate_stage_receipt = _NAMESPACE["validate_stage_receipt"]
run_task = _NAMESPACE["run_task"]


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_runtime_policy_id": parent_runtime.POLICY_ID,
        "parent_forward_policy_id": parent_runtime.parent.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "candidate_module_bound_in_private_namespace": (
            _NAMESPACE["candidates"] is candidates
        ),
        "parent_runtime_global_candidate_unchanged": (
            parent_runtime.candidates is not candidates
        ),
        "arms": list(ARMS),
        "one_parent_forward_shared_by_base_and_candidate": True,
        "parent_key_anchored_candidate_not_composed": True,
        "date_bounded_official_xml_candidate_applied": True,
        "maximum_candidate_additional_fetches": 4,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_physical_queries": 4,
        "maximum_physical_fetches": 14,
        "normal_path_model_forwards": 3,
        "remaining_capacity_computed_only_from_content_free_budget_receipt": True,
        "over_cap_candidate_batch_never_attempted": True,
        "runtime_input_keys": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "ARMS",
    "BASE_ARM",
    "CANDIDATE_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "integration_contract",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
