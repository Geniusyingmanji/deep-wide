"""One-parent integration for V2.54.71 qualified source labels.

The V2.54.65 runtime already executes the frozen V2.53.75 parent once and
captures the paid third synthesis prompt's exact columns and same-forward page
records.  This successor changes only the pure post-parent candidate module to
V2.54.71 in an immutable private namespace.  Provider requests, search/fetch
effects, model calls, tokens, context, deadlines, and runtime inputs are
unchanged: at most four queries, fourteen fetches, and three normal-path model
forwards over visible ``opaque_id`` and ``question`` only.

No benchmark label, mapping, gold, evaluator, score, reward, credential, or
historical outcome is available.  Entropy/information gain assigns no signed
credit.  This build grants no external or DeepWideBench launch.
"""

from __future__ import annotations

import types
from collections.abc import Callable
from typing import Any

from . import v25465_row_key_bound_structured_source_runtime as parent_runtime
from . import v25471_qualified_source_label_candidate as candidates


POLICY_ID = "v25472_qualified_source_label_runtime_v1"
ROLE = "v25472_qualified_source_label_runtime_result"
RECEIPT_ROLE = "v25472_content_free_qualified_source_label_receipt"
STAGE_RECEIPT_ROLE = "v25472_content_free_qualified_source_label_stage_receipt"
ARMS = ("shared_parent_table", "qualified_source_label_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent_runtime.PHASES
ProductionOnlyStageError = parent_runtime.ProductionOnlyStageError
payload_sha256 = parent_runtime.payload_sha256


def _clone(function: Callable[..., Any], namespace: dict[str, Any]) -> Callable[..., Any]:
    cloned = types.FunctionType(
        function.__code__,
        namespace,
        name=function.__name__.replace("v25465", "v25472"),
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
        "ProductionOnlyStageError": ProductionOnlyStageError,
        "candidates": candidates,
        "payload_sha256": payload_sha256,
    }
)

for _name in (
    "_base",
    "_application",
    "_receipt",
    "validate_receipt",
    "_wrap_result",
    "validate_result",
    "_stage_receipt",
    "validate_stage_receipt",
    "run_task",
):
    _NAMESPACE[_name] = _clone(getattr(parent_runtime, _name), _NAMESPACE)

_CaptureModel = parent_runtime._CaptureModel
_base = _NAMESPACE["_base"]
_application = _NAMESPACE["_application"]
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
        "parent_policy_id": parent_runtime.parent.POLICY_ID,
        "capture_parent_policy_id": parent_runtime.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "candidate_module_bound_in_private_namespace": _NAMESPACE["candidates"] is candidates,
        "parent_module_global_candidate_unchanged": parent_runtime.candidates is not candidates,
        "one_parent_forward_only": True,
        "parent_completed_table_supplies_row_keys": True,
        "same_forward_pages_captured_without_prompt_or_request_mutation": True,
        "maximum_physical_queries": 4,
        "maximum_physical_fetches": 14,
        "normal_path_model_forwards": 3,
        "additional_candidate_provider_effects": 0,
        "runtime_input_keys": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "ARMS", "BASE_ARM", "CANDIDATE_ARM", "PHASES", "POLICY_ID",
    "ProductionOnlyStageError", "RECEIPT_ROLE", "ROLE", "STAGE_RECEIPT_ROLE",
    "integration_contract", "run_task", "validate_receipt", "validate_result",
    "validate_stage_receipt",
]
