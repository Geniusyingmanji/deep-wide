"""Outcome-blind successor to the V2.55.32 population selection rule.

The first V2.55.33 name-list attempt failed closed because the raw consecutive
slice after ``.bradesco`` contains historical ccTLD identities.  No snapshot,
detail page, field value, question, prediction, evaluator, or quality result
was produced.  This successor changes only the name-level rule: scan the
official alphabetic list after the same predecessor, skip the complete frozen
consumed union, and take the first forty remaining identities in order.

The consumed union and predecessor remain exactly V2.55.32.  No identity is
selected by page reachability, parser success, field value, score, or outcome.
This pure module performs no I/O and authorizes one new redirect-disabled
official name-list snapshot only after its runner is committed and pushed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from . import v25532_official_tld_population_selection as parent


POLICY_ID = "v25534_skip_consumed_official_tld_selection_v1"
DATE = parent.DATE
OFFICIAL_ENDPOINT = parent.OFFICIAL_ENDPOINT
PREDECESSOR = parent.PREDECESSOR
SELECTED_IDENTITY_COUNT = parent.SELECTED_IDENTITY_COUNT
TASK_COUNT = parent.TASK_COUNT
ROWS_PER_TASK = parent.ROWS_PER_TASK
MAXIMUM_HTTP_ATTEMPTS = 1
MAXIMUM_RESPONSE_BYTES = parent.MAXIMUM_RESPONSE_BYTES
CONNECT_TIMEOUT_SECONDS = parent.CONNECT_TIMEOUT_SECONDS
READ_TIMEOUT_SECONDS = parent.READ_TIMEOUT_SECONDS
payload_sha256 = parent.payload_sha256
parse_official_names = parent.parse_official_names
consumed_identities = parent.consumed_identities
validate_pairs = parent.validate_pairs


def selected_identities(names: Sequence[str]) -> list[str]:
    copied = [str(value) for value in names]
    if copied != sorted(copied) or len(copied) != len(set(copied)):
        raise ValueError("V2.55.34 input names are not unique alphabetic order")
    try:
        start = copied.index(PREDECESSOR) + 1
    except ValueError as exc:
        raise ValueError("V2.55.34 predecessor absent") from exc
    consumed = consumed_identities()
    suffix = copied[start:]
    values = [value for value in suffix if value not in consumed][
        :SELECTED_IDENTITY_COUNT
    ]
    positions = [copied.index(value) for value in values]
    if (
        len(values) != SELECTED_IDENTITY_COUNT
        or len(set(values)) != SELECTED_IDENTITY_COUNT
        or set(values).intersection(consumed)
        or values != sorted(values)
        or positions != sorted(positions)
        or any(value <= PREDECESSOR for value in values)
        or any(len(value.removeprefix(".")) < 3 for value in values)
    ):
        raise ValueError("V2.55.34 skip-consumed block drifted")
    expected = []
    for value in suffix:
        if value in consumed:
            continue
        expected.append(value)
        if len(expected) == SELECTED_IDENTITY_COUNT:
            break
    if values != expected:
        raise ValueError("V2.55.34 first-unconsumed rule drifted")
    return values


def selection_policy() -> dict[str, Any]:
    return {
        "official_endpoint": OFFICIAL_ENDPOINT,
        "predecessor": PREDECESSOR,
        "selection_rule": "scan_after_predecessor_skip_complete_consumed_union_take_first_forty",
        "fixed_identity_count": SELECTED_IDENTITY_COUNT,
        "fixed_task_count": TASK_COUNT,
        "maximum_http_attempts": MAXIMUM_HTTP_ATTEMPTS,
        "allow_redirects": False,
        "v25533_old_raw_consecutive_rule_retry_or_reuse": False,
        "complete_v25532_consumed_union_frozen_unchanged": True,
        "skipped_identity_count_is_structural_name_only_not_an_outcome": True,
        "individual_unconsumed_identity_filter_rank_replace_retain_retry_or_backfill": False,
        "detail_endpoint_page_field_value_question_prediction_quality_or_outcome_read": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "external_mechanism_quality_deepwidebench_or_leaderboard_launch_authorized": False,
    }


def manifest() -> dict[str, Any]:
    consumed = consumed_identities()
    return {
        "policy_id": POLICY_ID,
        "date": DATE,
        "parent_policy_id": parent.POLICY_ID,
        "official_endpoint": OFFICIAL_ENDPOINT,
        "predecessor": PREDECESSOR,
        "consumed_identity_count": len(consumed),
        "consumed_identity_vector_sha256": payload_sha256(sorted(consumed)),
        "selection_policy": selection_policy(),
    }


def validate_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if copied != manifest():
        raise ValueError("V2.55.34 selection manifest drifted")
    return copied


__all__ = [
    "CONNECT_TIMEOUT_SECONDS",
    "DATE",
    "MAXIMUM_HTTP_ATTEMPTS",
    "MAXIMUM_RESPONSE_BYTES",
    "OFFICIAL_ENDPOINT",
    "POLICY_ID",
    "PREDECESSOR",
    "READ_TIMEOUT_SECONDS",
    "ROWS_PER_TASK",
    "SELECTED_IDENTITY_COUNT",
    "TASK_COUNT",
    "consumed_identities",
    "manifest",
    "parse_official_names",
    "payload_sha256",
    "selected_identities",
    "selection_policy",
    "validate_manifest",
    "validate_pairs",
]
