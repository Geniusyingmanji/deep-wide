"""Value-preserving wire validation for V2.44.47 envelopes.

JSON object member order is not semantic, but a small number of frozen
V2.44.x validators use the protocol-declared order of count partitions as a
schema check.  Private artifacts are deliberately written with
``sort_keys=True``.  This adapter restores only those declared orders, proves
that the canonical JSON value is unchanged, and then performs the complete
V2.44.47 envelope/cross-artifact validation exactly once.

The returned capability object is intentionally distinct from a raw mapping.
Counts-only projection code can therefore require evidence that the complete
private envelope was validated before it reads any receipt.  This component
does not access files, environment variables, network services, models,
search, benchmark metadata, evaluator state, rewards, or scores.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import Any

from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24436_narrative_title_anchor_projection import REASONS
from .v24443_serialized_narrative_envelope import (
    normalize_serialized_envelope as normalize_parent_envelope,
)
from .v24447_third_source_entropy_to_decision import (
    THRESHOLD_PARTITION_FIELDS,
    validate_envelope as validate_v24447_envelope,
)


POLICY_ID = "v24448_value_preserving_serialized_third_source_envelope_v1"


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"V2.44.48 {label} is not an object")
    return dict(value)


def _ordered(
    value: object, order: tuple[str, ...], label: str
) -> dict[str, Any]:
    source = _object(value, label)
    if set(source) != set(order):
        raise ValueError(f"V2.44.48 {label} keys drifted")
    return {name: copy.deepcopy(source[name]) for name in order}


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _normalize_narrative_result(value: object, label: str) -> dict[str, Any]:
    result = copy.deepcopy(_object(value, label))
    projection = _object(
        result.get("narrative_title_projection"),
        f"{label} narrative projection",
    )
    receipt = _object(
        result.get("narrative_recovery_receipt"),
        f"{label} narrative receipt",
    )
    projection["reason_counts"] = _ordered(
        projection.get("reason_counts"),
        tuple(REASONS),
        f"{label} projection reason counts",
    )
    receipt["narrative_reason_counts"] = _ordered(
        receipt.get("narrative_reason_counts"),
        tuple(REASONS),
        f"{label} receipt reason counts",
    )
    result["narrative_title_projection"] = projection
    result["narrative_recovery_receipt"] = receipt
    return result


def normalize_serialized_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    """Restore protocol order without changing the serialized JSON value."""

    original = _object(value, "envelope")
    normalized = copy.deepcopy(original)
    normalized["parent_envelope"] = normalize_parent_envelope(
        _object(normalized.get("parent_envelope"), "parent envelope")
    )

    result = _object(normalized.get("third_source_result"), "third-source result")
    result["parent_result"] = _normalize_narrative_result(
        result.get("parent_result"), "third-source parent result"
    )
    extended = _object(
        result.get("extended_narrative_title_projection"),
        "extended narrative projection",
    )
    extended["reason_counts"] = _ordered(
        extended.get("reason_counts"),
        tuple(REASONS),
        "extended narrative reason counts",
    )
    result["extended_narrative_title_projection"] = extended
    recovery = _object(
        result.get("third_source_recovery_receipt"),
        "third-source recovery receipt",
    )
    recovery["threshold_failure_partition"] = _ordered(
        recovery.get("threshold_failure_partition"),
        tuple(THRESHOLD_PARTITION_FIELDS),
        "threshold failure partition",
    )
    result["third_source_recovery_receipt"] = recovery
    normalized["third_source_result"] = result

    if _canonical_json(original) != _canonical_json(normalized):
        raise ValueError("V2.44.48 normalization changed the JSON value")
    return normalized


class ValidatedSerializedThirdSourceEnvelope:
    """Opaque capability proving one complete V2.44.47 validation."""

    __slots__ = ("__observed_bundle_validated", "__projection_receipts", "__value")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use validate_serialized_envelope")

    @classmethod
    def _create(
        cls, value: Mapping[str, Any], *, observed_bundle_validated: bool
    ) -> "ValidatedSerializedThirdSourceEnvelope":
        instance = object.__new__(cls)
        instance.__value = copy.deepcopy(dict(value))
        instance.__projection_receipts = {
            "third_source_recovery_receipt": copy.deepcopy(
                value["third_source_result"]["third_source_recovery_receipt"]
            ),
            "effect_delta_receipt": copy.deepcopy(value["effect_delta_receipt"]),
        }
        instance.__observed_bundle_validated = bool(observed_bundle_validated)
        return instance

    def snapshot(self) -> dict[str, Any]:
        """Return an isolated in-memory copy for content-free projection."""

        return copy.deepcopy(self.__value)

    def observed_bundle_validated(self) -> bool:
        """Whether independent terminal artifacts were cross-validated."""

        return self.__observed_bundle_validated

    def counts_only_receipts(self) -> dict[str, Any]:
        """Return only validated, content-free receipts needed by projection."""

        if not self.__observed_bundle_validated:
            raise ValueError("V2.44.48 observed bundle was not validated")
        return copy.deepcopy(self.__projection_receipts)


def validate_serialized_envelope(
    value: Mapping[str, Any],
) -> ValidatedSerializedThirdSourceEnvelope:
    """Normalize wire order and run the complete V2.44.47 validator once."""

    validated = validate_v24447_envelope(normalize_serialized_envelope(value))
    return ValidatedSerializedThirdSourceEnvelope._create(
        validated, observed_bundle_validated=False
    )


def validate_serialized_observed_bundle(
    value: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    expected_cap: int,
) -> ValidatedSerializedThirdSourceEnvelope:
    """Validate one wire envelope and its independently persisted receipts."""

    validated = validate_v24447_envelope(normalize_serialized_envelope(value))
    model = validate_model_receipt(
        dict(model_slot_receipt), expected_cap=expected_cap
    )
    transport = validate_transport_health(transport_health)
    search = dict(search_single_shot_receipt)
    validate_search_receipt(search)
    if (
        validated["model_slot_receipt"] != model
        or validated["transport_health"] != transport
        or validated["search_single_shot_receipt"] != search
    ):
        raise ValueError("V2.44.48 terminal artifact drifted from envelope")
    return ValidatedSerializedThirdSourceEnvelope._create(
        validated, observed_bundle_validated=True
    )


__all__ = [
    "POLICY_ID",
    "ValidatedSerializedThirdSourceEnvelope",
    "normalize_serialized_envelope",
    "validate_serialized_envelope",
    "validate_serialized_observed_bundle",
]
