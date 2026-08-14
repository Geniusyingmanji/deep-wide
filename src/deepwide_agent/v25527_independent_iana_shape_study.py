"""Frozen, evaluation-disjoint public IANA page-shape study contract.

V2.55.26 localised the V2.55.25 loss to the parser stage, after exact URL,
visible row, and page-surface binding.  This contract freezes eight public
IANA identities that were already consumed by V2.55.09.  They are disjoint
from V2.55.25 and are permanently ineligible for any successor mechanism or
quality population.  The study may fetch each exact public URL once solely to
observe the text produced by the production HTML extractor.

This pure module performs no I/O.  It contains no benchmark task, prediction,
truth, evaluator signal, score, credential, or per-task outcome and grants no
benchmark launch authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25509_fresh_multirow_uncertainty_population as consumed
from . import v25523_fresh_source_bound_population as frozen_forward


POLICY_ID = "v25527_independent_iana_page_shape_study_v1"
DATE = "20260814"
IANA_PREFIX = "https://www.iana.org/domains/root/db/"
STUDY_IDENTITIES = (
    ".aaa",
    ".abbott",
    ".abudhabi",
    ".academy",
    ".aero",
    ".africa",
    ".amazon",
    ".americanfamily",
)
EXPECTED_IDENTITY_VECTOR_SHA256 = (
    "f31c43a6f35b2abf8ff55373b0411ebc168650db72b1037ac5639ba7d911ad57"
)
EXPECTED_URL_VECTOR_SHA256 = (
    "7ba46a023af2e293baedb1da216f415e74bf44baf090c6c078034314c594e6cb"
)
MAXIMUM_TOTAL_HTTP_REQUESTS = len(STUDY_IDENTITIES)
MAXIMUM_REQUESTS_PER_URL = 1
MAXIMUM_RESPONSE_BYTES = 1_000_000
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS = 30


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def identity_vector() -> list[str]:
    values = list(STUDY_IDENTITIES)
    consumed_rows = {
        identity for pair in consumed.PAIRS for identity in pair
    }
    frozen_rows = {
        identity for pair in frozen_forward.PAIRS for identity in pair
    }
    if (
        len(values) != 8
        or len(set(values)) != len(values)
        or any(
            re.fullmatch(r"\.[a-z][a-z0-9-]{2,62}", identity) is None
            for identity in values
        )
        or not set(values).issubset(consumed_rows)
        or set(values).intersection(frozen_rows)
    ):
        raise RuntimeError("V2.55.27 research identity vector drifted")
    observed = payload_sha256(values)
    if (
        EXPECTED_IDENTITY_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_IDENTITY_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.27 research identity hash drifted")
    return values


def url_vector() -> list[str]:
    values = [
        IANA_PREFIX + identity.removeprefix(".") + ".html"
        for identity in identity_vector()
    ]
    observed = payload_sha256(values)
    if (
        EXPECTED_URL_VECTOR_SHA256 != "TO_BE_FROZEN"
        and observed != EXPECTED_URL_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.27 research URL hash drifted")
    return values


def study_policy() -> dict[str, Any]:
    return {
        "purpose": "observe_production_extracted_text_shape_for_public_iana_detail_pages",
        "identity_selection_source": "already_consumed_v25509_static_population",
        "identities_frozen_before_any_v25527_network_access": True,
        "identities_disjoint_from_v25525_frozen_forward_population": True,
        "identities_permanently_excluded_from_future_mechanism_quality_or_confirmation_populations": True,
        "exact_public_urls_only": True,
        "maximum_total_http_requests": MAXIMUM_TOTAL_HTTP_REQUESTS,
        "maximum_requests_per_url": MAXIMUM_REQUESTS_PER_URL,
        "redirects_allowed": False,
        "search_model_fetch_provider_evaluator_or_benchmark_api_used": False,
        "ordinary_public_https_get_is_the_only_authorized_effect": True,
        "raw_html_used_only_as_input_to_the_frozen_production_html_extractor": True,
        "stored_page_fixture_is_extracted_public_text_not_benchmark_data": True,
        "identity_or_page_content_may_not_select_filter_rank_replace_or_retain_future_tasks": True,
        "v25525_task_rows_questions_pages_predictions_or_per_task_outcomes_read": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "external_mechanism_quality_deepwidebench_or_leaderboard_launch_authorized": False,
    }


def manifest() -> dict[str, Any]:
    identities = identity_vector()
    urls = url_vector()
    return {
        "policy_id": POLICY_ID,
        "date": DATE,
        "identities": identities,
        "urls": urls,
        "identity_vector_sha256": payload_sha256(identities),
        "url_vector_sha256": payload_sha256(urls),
        "study_policy": study_policy(),
    }


def validate_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    expected = manifest()
    if copied != expected:
        raise ValueError("V2.55.27 research manifest drifted")
    return copied


def validate_identity_vector(values: Sequence[object]) -> list[str]:
    copied = [str(value) for value in values]
    if copied != identity_vector():
        raise ValueError("V2.55.27 research identity order drifted")
    return copied


__all__ = [
    "CONNECT_TIMEOUT_SECONDS",
    "DATE",
    "EXPECTED_IDENTITY_VECTOR_SHA256",
    "EXPECTED_URL_VECTOR_SHA256",
    "IANA_PREFIX",
    "MAXIMUM_REQUESTS_PER_URL",
    "MAXIMUM_RESPONSE_BYTES",
    "MAXIMUM_TOTAL_HTTP_REQUESTS",
    "POLICY_ID",
    "READ_TIMEOUT_SECONDS",
    "STUDY_IDENTITIES",
    "identity_vector",
    "manifest",
    "payload_sha256",
    "study_policy",
    "url_vector",
    "validate_identity_vector",
    "validate_manifest",
]
