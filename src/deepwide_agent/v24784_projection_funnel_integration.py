"""Trusted-child integration of V2.47.81 over one V2.47.78 task result.

One visible ``{opaque_id, question}`` task executes the unchanged V2.47.78
runtime exactly once.  The complete result is then fully validated inside the
same trusted child.  When its validated private semantic catalog exists,
V2.47.81 observes that exact catalog once and emits only its fixed-vocabulary
counts receipt.  The observer cannot change predictions or perform any model,
search, fetch, file, environment, process, benchmark, or evaluator effect.

The returned parent projection preserves the two ordinary prediction strings
and the existing content-free scheduler/semantic receipts, but excludes the
question, complete V2.47.78 result, pages, catalog, URLs, hosts, queries, and
private hashes.  Catalog absence and validation failures are explicit terminal
statuses and are never converted into fabricated all-zero funnel counts.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from . import v24778_staged_fetch_fallback_runtime as base
from . import v24781_projection_conversion_funnel as funnel


POLICY_ID = "v24784_projection_funnel_trusted_child_integration_v1"
ROLE = "v24784_projection_funnel_task_projection"
STATUSES = (
    "validated",
    "private_catalog_absent",
    "base_runtime_failure",
    "funnel_validation_failure",
)
PUBLIC_RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "base_result_valid",
        "funnel_receipt_valid",
        "predictions",
        "prediction_sha256",
        "scheduler_receipt",
        "semantic_receipt",
        "projection_funnel_receipt",
        "private_catalog_present",
        "base_runtime_executed_once",
        "base_result_validated_once_before_funnel",
        "private_catalog_observed_by_funnel_at_most_once",
        "counts_only_funnel_receipt_revalidation_may_repeat_without_private_access",
        "predictions_equal_validated_base_result",
        "catalog_or_private_content_serialized_to_public_projection",
        "question_query_url_host_page_or_private_content_hash_emitted",
        "additional_model_search_fetch_or_evaluator_effect",
        "positive_entropy_or_task_credit_assigned",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "result_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return base.payload_sha256(value)


def _projection(
    *,
    visible: Mapping[str, str],
    status: str,
    validated: Mapping[str, Any] | None,
    funnel_receipt: Mapping[str, Any] | None,
    base_executed: bool,
    base_validations: int,
    funnel_builds: int,
    funnel_validations: int,
    private_catalog_present: bool,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise ValueError("V2.47.84 terminal status drifted")
    base_valid = validated is not None
    funnel_valid = funnel_receipt is not None
    if base_valid:
        predictions = copy.deepcopy(dict(validated["predictions"]))
        hashes = copy.deepcopy(dict(validated["prediction_sha256"]))
        scheduler = copy.deepcopy(dict(validated["scheduler_receipt"]))
        semantic = copy.deepcopy(dict(validated["semantic_receipt"]))
    else:
        predictions = {}
        hashes = {}
        scheduler = None
        semantic = None
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": status,
        "base_result_valid": base_valid,
        "funnel_receipt_valid": funnel_valid,
        "predictions": predictions,
        "prediction_sha256": hashes,
        "scheduler_receipt": scheduler,
        "semantic_receipt": semantic,
        "projection_funnel_receipt": (
            copy.deepcopy(dict(funnel_receipt)) if funnel_valid else None
        ),
        "private_catalog_present": private_catalog_present,
        "base_runtime_executed_once": base_executed,
        "base_result_validated_once_before_funnel": base_valid
        and base_validations == 1,
        "private_catalog_observed_by_funnel_at_most_once": funnel_builds <= 1
        and funnel_validations <= 1,
        "counts_only_funnel_receipt_revalidation_may_repeat_without_private_access": True,
        "predictions_equal_validated_base_result": base_valid,
        "catalog_or_private_content_serialized_to_public_projection": False,
        "question_query_url_host_page_or_private_content_hash_emitted": False,
        "additional_model_search_fetch_or_evaluator_effect": 0,
        "positive_entropy_or_task_credit_assigned": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_sha256"] = payload_sha256(value)
    return validate_projection(value)


def run_v24784_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    """Run the frozen base once and observe its validated catalog once."""

    visible = validate_visible_task(task)
    base_executed = False
    base_validations = 0
    funnel_builds = 0
    funnel_validations = 0
    try:
        base_executed = True
        validated = base.run_v24778_task(
            visible,
            model=model,
            search=search,
            limits=limits,
            monotonic=monotonic,
        )
        # ``run_v24778_task`` returns only through its terminal
        # ``validate_result`` call.  Count that single complete validation;
        # do not replay the expensive private semantic validator here.
        base_validations += 1
    except Exception:
        return _projection(
            visible=visible,
            status="base_runtime_failure",
            validated=None,
            funnel_receipt=None,
            base_executed=base_executed,
            base_validations=base_validations,
            funnel_builds=funnel_builds,
            funnel_validations=funnel_validations,
            private_catalog_present=False,
        )
    catalog = validated.get("private_semantic_catalog")
    if catalog is None:
        return _projection(
            visible=visible,
            status="private_catalog_absent",
            validated=validated,
            funnel_receipt=None,
            base_executed=base_executed,
            base_validations=base_validations,
            funnel_builds=funnel_builds,
            funnel_validations=funnel_validations,
            private_catalog_present=False,
        )
    try:
        funnel_builds += 1
        receipt = funnel.build_projection_conversion_funnel(catalog)
        # The builder returns only through ``validate_receipt``.  As with the
        # base result, record that one validation rather than replaying it.
        funnel_validations += 1
    except Exception:
        return _projection(
            visible=visible,
            status="funnel_validation_failure",
            validated=validated,
            funnel_receipt=None,
            base_executed=base_executed,
            base_validations=base_validations,
            funnel_builds=funnel_builds,
            funnel_validations=funnel_validations,
            private_catalog_present=True,
        )
    return _projection(
        visible=visible,
        status="validated",
        validated=validated,
        funnel_receipt=receipt,
        base_executed=base_executed,
        base_validations=base_validations,
        funnel_builds=funnel_builds,
        funnel_validations=funnel_validations,
        private_catalog_present=True,
    )


def validate_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    status = copied.get("status")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    scheduler = copied.get("scheduler_receipt")
    semantic = copied.get("semantic_receipt")
    receipt = copied.get("projection_funnel_receipt")
    base_valid = copied.get("base_result_valid")
    funnel_valid = copied.get("funnel_receipt_valid")
    if (
        set(copied) != PUBLIC_RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("opaque_id"), str)
        or not copied["opaque_id"]
        or status not in STATUSES
        or not isinstance(base_valid, bool)
        or not isinstance(funnel_valid, bool)
        or not isinstance(predictions, Mapping)
        or not isinstance(hashes, Mapping)
        or copied.get("base_runtime_executed_once") is not True
        or copied.get("private_catalog_observed_by_funnel_at_most_once") is not True
        or copied.get(
            "counts_only_funnel_receipt_revalidation_may_repeat_without_private_access"
        )
        is not True
        or copied.get("catalog_or_private_content_serialized_to_public_projection")
        is not False
        or copied.get(
            "question_query_url_host_page_or_private_content_hash_emitted"
        )
        is not False
        or copied.get("additional_model_search_fetch_or_evaluator_effect") != 0
        or copied.get("positive_entropy_or_task_credit_assigned") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.84 task projection envelope drifted")
    if base_valid:
        if (
            set(predictions) != set(base.ARMS)
            or set(hashes) != set(base.ARMS)
            or any(not isinstance(predictions[arm], str) for arm in base.ARMS)
            or any(
                hashes[arm]
                != hashlib.sha256(predictions[arm].encode("utf-8")).hexdigest()
                for arm in base.ARMS
            )
            or not isinstance(scheduler, Mapping)
            or not isinstance(semantic, Mapping)
            or copied.get("base_result_validated_once_before_funnel") is not True
            or copied.get("predictions_equal_validated_base_result") is not True
        ):
            raise ValueError("V2.47.84 validated base projection drifted")
        base.validate_scheduler_receipt(scheduler)
        base.semantic.validate_semantic_receipt(semantic)
    elif (
        predictions
        or hashes
        or scheduler is not None
        or semantic is not None
        or copied.get("private_catalog_present") is not False
        or copied.get("base_result_validated_once_before_funnel") is not False
        or copied.get("predictions_equal_validated_base_result") is not False
    ):
        raise ValueError("V2.47.84 base failure projection drifted")
    if funnel_valid:
        if status != "validated" or not isinstance(receipt, Mapping):
            raise ValueError("V2.47.84 valid funnel status drifted")
        funnel.validate_receipt(receipt)
    elif receipt is not None or status == "validated":
        raise ValueError("V2.47.84 absent funnel projection drifted")
    if (
        (status == "validated" and (not base_valid or not funnel_valid or not copied["private_catalog_present"]))
        or (status == "private_catalog_absent" and (not base_valid or funnel_valid or copied["private_catalog_present"]))
        or (status == "base_runtime_failure" and (base_valid or funnel_valid))
        or (status == "funnel_validation_failure" and (not base_valid or funnel_valid or not copied["private_catalog_present"]))
    ):
        raise ValueError("V2.47.84 terminal status semantics drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "PUBLIC_RESULT_KEYS",
    "ROLE",
    "STATUSES",
    "run_v24784_task",
    "validate_projection",
]
