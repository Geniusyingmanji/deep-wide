"""One-parent production integration for V2.54.40 metadata candidates.

The V2.54.34 wrapper already captures authority-bound pages from the paid
third synthesis call without changing a provider request.  This successor
keeps that parent and capture path byte-for-byte, but binds every candidate
registry, application, receipt, and replay validator to the audited V2.54.40
key-anchored metadata primitive in a private immutable function namespace.

There is no module-global mutation or monkeypatch.  The parent still executes
once with four physical queries, at most fourteen fetches, and exactly three
normal-path model forwards.  Candidate application remains pure and adds no
provider effect.  Runtime inputs remain visible ``opaque_id`` and ``question``
plus injected capped clients.  No benchmark label, mapping, gold, evaluator,
score, reward, credential, or historical result is available.  Entropy or
information gain assigns no signed credit.  This build grants no launch.
"""

from __future__ import annotations

import types
from collections.abc import Callable, Mapping
from typing import Any

from . import v25434_source_authoritative_shared_runtime as parent_runtime
from . import v25440_key_anchored_metadata_candidate as candidates


POLICY_ID = "v25444_key_anchored_metadata_shared_runtime_v1"
ROLE = "v25444_key_anchored_metadata_shared_runtime_result"
RECEIPT_ROLE = "v25444_content_free_key_anchored_metadata_shared_receipt"
STAGE_RECEIPT_ROLE = "v25444_content_free_key_anchored_metadata_stage_receipt"
ARMS = ("shared_base_table", "key_anchored_metadata_candidate")
BASE_ARM, CANDIDATE_ARM = ARMS
PHASES = parent_runtime.PHASES
ProductionOnlyStageError = parent_runtime.ProductionOnlyStageError
CONTENT_FREE_FLAG = parent_runtime.CONTENT_FREE_FLAG
payload_sha256 = parent_runtime.payload_sha256

_INTEGER_FIELDS = parent_runtime._INTEGER_FIELDS
_DYNAMIC_FLAGS = parent_runtime._DYNAMIC_FLAGS
_TRUE_FLAGS = parent_runtime._TRUE_FLAGS
_FALSE_FLAGS = tuple(
    candidates.PRIVILEGED_READ_FLAG
    if name == parent_runtime.candidates.PRIVILEGED_READ_FLAG
    else name
    for name in parent_runtime._FALSE_FLAGS
)

# Capture is unchanged and has no candidate-generator dependency.
_SourceAuthoritativeCaptureHybrid = parent_runtime._SourceAuthoritativeCaptureHybrid


def _clone(
    function: Callable[..., Any], namespace: dict[str, Any]
) -> Callable[..., Any]:
    cloned = types.FunctionType(
        function.__code__,
        namespace,
        name=function.__name__.replace("v25434", "v25444"),
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
        "CONTENT_FREE_FLAG": CONTENT_FREE_FLAG,
        "_INTEGER_FIELDS": _INTEGER_FIELDS,
        "_DYNAMIC_FLAGS": _DYNAMIC_FLAGS,
        "_TRUE_FLAGS": _TRUE_FLAGS,
        "_FALSE_FLAGS": _FALSE_FLAGS,
        "_SourceAuthoritativeCaptureHybrid": _SourceAuthoritativeCaptureHybrid,
        "candidates": candidates,
        "payload_sha256": payload_sha256,
    }
)

for _name in (
    "_safe_failure",
    "_url_bindings",
    "_authority_bound_pages",
    "_parent_runner",
    "_shared_base",
    "_application",
    "_receipt",
    "_receipt_matches_application",
    "validate_receipt",
    "_wrap_result",
    "validate_result",
    "_stage_receipt",
    "validate_stage_receipt",
    "run_task",
):
    _NAMESPACE[_name] = _clone(getattr(parent_runtime, _name), _NAMESPACE)

_safe_failure = _NAMESPACE["_safe_failure"]
_url_bindings = _NAMESPACE["_url_bindings"]
_authority_bound_pages = _NAMESPACE["_authority_bound_pages"]
_parent_runner = _NAMESPACE["_parent_runner"]
_shared_base = _NAMESPACE["_shared_base"]
_application = _NAMESPACE["_application"]
_receipt = _NAMESPACE["_receipt"]
_receipt_matches_application = _NAMESPACE["_receipt_matches_application"]
validate_receipt = _NAMESPACE["validate_receipt"]
_wrap_result = _NAMESPACE["_wrap_result"]
validate_result = _NAMESPACE["validate_result"]
_stage_receipt = _NAMESPACE["_stage_receipt"]
validate_stage_receipt = _NAMESPACE["validate_stage_receipt"]
run_task = _NAMESPACE["run_task"]


def integration_contract() -> dict[str, Any]:
    """Return content-free invariants for build and external audits."""

    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent_runtime.POLICY_ID,
        "candidate_policy_id": candidates.POLICY_ID,
        "candidate_module_bound_in_private_namespace": (
            _NAMESPACE["candidates"] is candidates
        ),
        "parent_module_global_candidate_unchanged": (
            parent_runtime.candidates is not candidates
        ),
        "one_parent_forward_only": True,
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
