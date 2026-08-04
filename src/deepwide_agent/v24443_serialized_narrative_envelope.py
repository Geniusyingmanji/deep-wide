"""Value-preserving validation for serialized V2.44.38 envelopes.

V2.44.42 exposed a wire-format bug rather than a retrieval failure.  The
V2.44.38 envelope validates before it is written, but the private artifact
writer deliberately serializes JSON with ``sort_keys=True``.  V2.44.36 and
V2.44.37 then treated the insertion order of their six-reason count mappings
as identity, so the parent rejected every otherwise valid child envelope
after reading it back from disk.

JSON object member order is not semantic.  This adapter restores only the
protocol-declared order of those two reason mappings, proves that the
canonical JSON value did not change, and then delegates to the complete
V2.44.38 envelope and cross-artifact validators.  It does not alter evidence,
counts, predictions, seals, receipts, or any external-effect contract.

The component performs no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from typing import Any

from .v24436_narrative_title_anchor_projection import REASONS
from .v24438_bounded_narrative_effect_runner import (
    validate_envelope as validate_v24438_envelope,
    validate_observed_bundle as validate_v24438_observed_bundle,
)


POLICY_ID = "v24443_value_preserving_serialized_narrative_envelope_v1"


def _object(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"V2.44.43 {label} is not an object")
    return value


def _ordered_reasons(value: object, label: str) -> dict[str, Any]:
    reasons = _object(value, label)
    if set(reasons) != set(REASONS):
        raise ValueError(f"V2.44.43 {label} keys drifted")
    return {reason: copy.deepcopy(reasons[reason]) for reason in REASONS}


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def normalize_serialized_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    """Restore protocol order without changing the JSON value."""

    original = _object(value, "envelope")
    normalized = copy.deepcopy(dict(original))
    result = _object(
        normalized.get("narrative_title_result"), "narrative title result"
    )
    projection = _object(
        result.get("narrative_title_projection"), "narrative title projection"
    )
    receipt = _object(
        result.get("narrative_recovery_receipt"), "narrative recovery receipt"
    )
    projection["reason_counts"] = _ordered_reasons(
        projection.get("reason_counts"), "projection reason counts"
    )
    receipt["narrative_reason_counts"] = _ordered_reasons(
        receipt.get("narrative_reason_counts"), "receipt reason counts"
    )
    if _canonical_json(original) != _canonical_json(normalized):
        raise ValueError("V2.44.43 normalization changed the JSON value")
    return normalized


def validate_serialized_envelope(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a memory-built or JSON-round-tripped V2.44.38 envelope."""

    return validate_v24438_envelope(normalize_serialized_envelope(value))


def validate_serialized_observed_bundle(
    value: Mapping[str, Any],
    *,
    model_slot_receipt: Mapping[str, Any],
    transport_health: Mapping[str, Any],
    search_single_shot_receipt: Mapping[str, Any],
    expected_cap: int,
) -> dict[str, Any]:
    """Run the unchanged V2.44.38 cross-artifact checks after normalization."""

    return validate_v24438_observed_bundle(
        normalize_serialized_envelope(value),
        model_slot_receipt=model_slot_receipt,
        transport_health=transport_health,
        search_single_shot_receipt=search_single_shot_receipt,
        expected_cap=expected_cap,
    )


__all__ = [
    "POLICY_ID",
    "normalize_serialized_envelope",
    "validate_serialized_envelope",
    "validate_serialized_observed_bundle",
]
