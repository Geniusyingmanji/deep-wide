"""Pure one-shot selection rule for the next disjoint TLD population.

The repository-frozen public namespace sequence ends at ``.bradesco``.  This
contract fixes the official IANA alphabetic TLD-name endpoint and selects the
next forty consecutive names after that exact predecessor.  The block is not
filtered, ranked, replaced, or retained using detail pages, field values,
predictions, quality, or outcomes.  Any overlap with the union of all prior
TLD populations and the V2.55.27 research identities fails closed.

This module performs no I/O, assigns zero entropy/IG signed credit, and
authorizes only a single redirect-disabled public name-list snapshot after
the contract and runner are committed and pushed.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25018_multi_identity_external_contract as namespace
from . import v25509_fresh_multirow_uncertainty_population as prior9
from . import v25516_fresh_evidence_coverage_population as prior16
from . import v25523_fresh_source_bound_population as prior23
from . import v25527_independent_iana_shape_study as research


POLICY_ID = "v25532_official_tld_population_selection_v1"
DATE = "20260814"
OFFICIAL_ENDPOINT = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
PREDECESSOR = ".bradesco"
SELECTED_IDENTITY_COUNT = 40
TASK_COUNT = 20
ROWS_PER_TASK = 2
MAXIMUM_HTTP_ATTEMPTS = 1
MAXIMUM_RESPONSE_BYTES = 200_000
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 30
EXPECTED_PREDECESSOR_SOURCE_SHA256 = (
    "18ae1923ea180fc3ca971d67d1769b867694fd8281b1f6798b73c6c225fdc023"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _flatten(values: Sequence[Sequence[str]]) -> set[str]:
    return {str(identity) for pair in values for identity in pair}


def consumed_identities() -> frozenset[str]:
    historical = {
        str(value) for value in namespace.HISTORICAL_TLD_COHORT
    } | {str(value) for value in namespace.TLD_COHORT}
    explicit = (
        _flatten(prior9.PAIRS)
        | _flatten(prior16.PAIRS)
        | _flatten(prior23.PAIRS)
        | set(research.STUDY_IDENTITIES)
    )
    if (
        not explicit.issubset(historical)
        or namespace.TLD_COHORT[-1] != PREDECESSOR
        or payload_sha256(list(namespace.TLD_COHORT))
        != EXPECTED_PREDECESSOR_SOURCE_SHA256
    ):
        raise RuntimeError("V2.55.32 consumed identity boundary drifted")
    return frozenset(historical | explicit)


def parse_official_names(raw: str) -> list[str]:
    if not isinstance(raw, str) or not raw or "\x00" in raw:
        raise ValueError("V2.55.32 official name list is empty")
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or not lines[0].startswith("# Version "):
        raise ValueError("V2.55.32 official name-list version header drifted")
    values: list[str] = []
    for line in lines[1:]:
        if not line:
            continue
        if line != line.strip() or line != line.upper():
            raise ValueError("V2.55.32 official name spelling drifted")
        lowered = "." + line.casefold()
        if re.fullmatch(r"\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", lowered) is None:
            raise ValueError("V2.55.32 official TLD syntax drifted")
        values.append(lowered)
    if len(values) < 1000 or len(values) != len(set(values)) or values != sorted(values):
        raise ValueError("V2.55.32 official alphabetic name vector drifted")
    return values


def selected_identities(names: Sequence[str]) -> list[str]:
    copied = [str(value) for value in names]
    if copied != sorted(copied) or len(copied) != len(set(copied)):
        raise ValueError("V2.55.32 input names are not unique alphabetic order")
    try:
        start = copied.index(PREDECESSOR) + 1
    except ValueError as exc:
        raise ValueError("V2.55.32 predecessor absent") from exc
    values = copied[start : start + SELECTED_IDENTITY_COUNT]
    consumed = consumed_identities()
    if (
        len(values) != SELECTED_IDENTITY_COUNT
        or any(len(value.removeprefix(".")) < 3 for value in values)
        or set(values).intersection(consumed)
        or any(value <= PREDECESSOR for value in values)
    ):
        raise ValueError("V2.55.32 consecutive disjoint block drifted")
    return values


def validate_pairs(values: Sequence[Sequence[str]]) -> list[tuple[str, str]]:
    copied = [tuple(str(item) for item in pair) for pair in values]
    flattened = [identity for pair in copied for identity in pair]
    if (
        len(copied) != TASK_COUNT
        or any(len(pair) != ROWS_PER_TASK for pair in copied)
        or len(flattened) != SELECTED_IDENTITY_COUNT
        or len(set(flattened)) != SELECTED_IDENTITY_COUNT
        or flattened != sorted(flattened)
        or set(flattened).intersection(consumed_identities())
    ):
        raise ValueError("V2.55.32 pair vector drifted")
    return copied


def selection_policy() -> dict[str, Any]:
    return {
        "official_endpoint": OFFICIAL_ENDPOINT,
        "predecessor": PREDECESSOR,
        "selection_rule": "next_exact_forty_consecutive_official_alphabetic_names_after_predecessor",
        "fixed_identity_count": SELECTED_IDENTITY_COUNT,
        "fixed_task_count": TASK_COUNT,
        "maximum_http_attempts": MAXIMUM_HTTP_ATTEMPTS,
        "allow_redirects": False,
        "predecessor_and_all_prior_tld_populations_count_as_consumed": True,
        "v25527_research_identities_count_as_consumed_and_permanently_excluded": True,
        "individual_identity_filter_rank_replace_retain_retry_or_backfill": False,
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
        "official_endpoint": OFFICIAL_ENDPOINT,
        "predecessor": PREDECESSOR,
        "consumed_identity_count": len(consumed),
        "consumed_identity_vector_sha256": payload_sha256(sorted(consumed)),
        "selection_policy": selection_policy(),
    }


def validate_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if copied != manifest():
        raise ValueError("V2.55.32 selection manifest drifted")
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
