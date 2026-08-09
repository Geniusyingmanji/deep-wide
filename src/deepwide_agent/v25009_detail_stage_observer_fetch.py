"""Zero-algorithm-effect observer for V2.50.04 detail-stage receipts.

The frozen V2.50.05 helper intentionally returned only the inherited parent
projection receipt.  This append-only boundary runs one equivalent helper and
unwraps its *identical* parent result before the frozen V2.49.81 fetch mixin
sees it.  Only a seven-bit, content-free stage signature and numeric counters
from the V2.50.04 receipt are retained in memory.

The observer never retains a URL, title, page, question, field label/value,
record, prediction, task identifier, credential, gold, evaluator output, or
benchmark label.  It adds no network, search, fetch, model, token, byte,
context, retry, process, or wall-clock cap and assigns no entropy/IG credit.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import threading
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .v24981_late_page_bound_fetch import (
    LatePageBoundFetchMixin,
    validate_helper_result as validate_parent_helper_result,
)
from .v25004_identity_bound_detail_fields import (
    validate_receipt as validate_detail_receipt,
)
from .v25005_detail_field_fetch import (
    HELPER as PARENT_HELPER,
    DetailFieldLatePageBoundSearchClient,
    validate_search_class as validate_parent_search_class,
)


POLICY_ID = "v25009_detail_stage_counts_only_observer_v1"
ROLE = "v25009_content_free_detail_stage_observer_receipt"
HELPER_ROLE = "v25009_observed_detail_field_helper_envelope"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v25009_detail_stage_observer_fetch_helper.py"
_SIGNATURE = re.compile(r"^c[01]p[01]a[01]s[01]f[01]d[01]r[01]$")
_SUM_FIELDS = (
    "input_page_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_identity_count",
    "visible_schema_column_count",
    "visible_target_field_count",
    "identity_url_path_match_count",
    "authority_url_token_match_count",
    "identity_page_surface_match_count",
    "raw_detail_candidate_line_count",
    "target_detail_candidate_count",
    "duplicate_or_conflicting_target_count",
    "discovered_record_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)
_PAGE_COUNT_FIELDS = (
    "visible_contract_ready_page_count",
    "identity_url_path_bound_page_count",
    "authority_url_token_bound_page_count",
    "identity_page_surface_bound_page_count",
    "all_target_fields_unique_page_count",
    "discovered_record_page_count",
    "retained_record_page_count",
)
_PARENT_DETAIL_BINDINGS = (
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "visible_schema_column_count",
    "discovered_record_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "projection_failure_count",
    "positive_signed_credit_count",
)


def _ordinary_helper(path: Path = HELPER) -> Path:
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != HELPER.resolve()
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.50.09 observer helper identity drifted")
    return resolved


def _stage_bits(receipt: Mapping[str, Any]) -> tuple[int, ...]:
    checked = validate_detail_receipt(receipt)
    contract_ready = int(
        checked["visible_identity_count"] == 1
        and checked["visible_target_field_count"] > 0
    )
    fields_unique = int(
        checked["visible_target_field_count"] > 0
        and checked["duplicate_or_conflicting_target_count"] == 0
    )
    return (
        contract_ready,
        int(checked["identity_url_path_match_count"] == 1),
        int(checked["authority_url_token_match_count"] == 1),
        int(checked["identity_page_surface_match_count"] == 1),
        fields_unique,
        int(checked["discovered_record_count"] == 1),
        int(checked["retained_record_count"] == 1),
    )


def detail_stage_signature(receipt: Mapping[str, Any]) -> str:
    c, p, a, s, f, d, r = _stage_bits(receipt)
    return f"c{c}p{p}a{a}s{s}f{f}d{d}r{r}"


def build_helper_envelope(
    parent_result: Mapping[str, Any],
    detail_field_receipt: Mapping[str, Any] | None,
) -> dict[str, Any]:
    parent = validate_parent_helper_result(parent_result)
    detail = None
    if parent["status"] == "ok":
        if not isinstance(detail_field_receipt, Mapping):
            raise ValueError("V2.50.09 successful helper omitted detail receipt")
        detail = validate_detail_receipt(detail_field_receipt)
        parent_receipt = parent["projection_receipt"]
        if any(parent_receipt[name] != detail[name] for name in _PARENT_DETAIL_BINDINGS):
            raise ValueError("V2.50.09 parent/detail receipt binding drifted")
    elif detail_field_receipt is not None:
        raise ValueError("V2.50.09 failed helper retained detail receipt")
    value = {
        "artifact_version": 1,
        "role": HELPER_ROLE,
        "parent_result": copy.deepcopy(parent),
        "detail_field_receipt": copy.deepcopy(detail),
        "one_public_fetch_only": True,
        "parent_result_unmodified": True,
        "additional_network_search_fetch_model_token_byte_context_retry_process_or_wall_cap": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    return validate_helper_envelope(value)


def validate_helper_envelope(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.50.09 observer helper envelope is not an object")
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "parent_result",
        "detail_field_receipt",
        "one_public_fetch_only",
        "parent_result_unmodified",
        "additional_network_search_fetch_model_token_byte_context_retry_process_or_wall_cap",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != HELPER_ROLE
        or copied.get("one_public_fetch_only") is not True
        or copied.get("parent_result_unmodified") is not True
        or copied.get(
            "additional_network_search_fetch_model_token_byte_context_retry_process_or_wall_cap"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
    ):
        raise ValueError("V2.50.09 observer helper envelope drifted")
    parent = validate_parent_helper_result(copied.get("parent_result"))
    detail = copied.get("detail_field_receipt")
    if parent["status"] == "ok":
        if not isinstance(detail, Mapping):
            raise ValueError("V2.50.09 successful envelope omitted detail receipt")
        detail = validate_detail_receipt(detail)
        parent_receipt = parent["projection_receipt"]
        if any(parent_receipt[name] != detail[name] for name in _PARENT_DETAIL_BINDINGS):
            raise ValueError("V2.50.09 envelope cross-binding drifted")
        copied["detail_field_receipt"] = detail
    elif detail is not None:
        raise ValueError("V2.50.09 failed envelope retained detail receipt")
    copied["parent_result"] = parent
    return copied


class _CountsObserver:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._receipts: list[dict[str, Any]] = []
        self._invalid_envelopes = 0

    def observe(self, receipt: Mapping[str, Any]) -> None:
        checked = validate_detail_receipt(receipt)
        with self._lock:
            self._receipts.append(copy.deepcopy(checked))

    def invalid(self) -> None:
        with self._lock:
            self._invalid_envelopes += 1

    def snapshot(self) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            return copy.deepcopy(self._receipts), int(self._invalid_envelopes)


class _ObservedProcess:
    def __init__(self, process: Any, observer: _CountsObserver) -> None:
        self._process = process
        self._observer = observer

    @property
    def pid(self) -> int:
        return int(self._process.pid)

    @property
    def returncode(self) -> int | None:
        return self._process.returncode

    def communicate(self, value: str, timeout: float | None = None):
        stdout, stderr = self._process.communicate(value, timeout=timeout)
        if self._process.returncode != 0:
            return stdout, stderr
        try:
            envelope = validate_helper_envelope(json.loads(stdout))
        except (json.JSONDecodeError, TypeError, ValueError):
            self._observer.invalid()
            return stdout, stderr
        detail = envelope["detail_field_receipt"]
        if isinstance(detail, Mapping):
            self._observer.observe(detail)
        return json.dumps(envelope["parent_result"], ensure_ascii=False), stderr

    def wait(self, timeout: float | None = None):
        return self._process.wait(timeout=timeout)


class _ObservedPopen:
    def __init__(
        self,
        observer: _CountsObserver,
        *,
        helper: Path,
        popen: Any,
    ) -> None:
        self._observer = observer
        self._helper = _ordinary_helper(helper)
        self._popen = popen

    def __call__(self, command: Any, **kwargs: Any) -> _ObservedProcess:
        if (
            not isinstance(command, list)
            or len(command) != 4
            or Path(str(command[-1])).resolve() != PARENT_HELPER.resolve()
        ):
            raise ValueError("V2.50.09 parent helper command drifted")
        observed = [*command[:-1], str(self._helper)]
        return _ObservedProcess(self._popen(observed, **kwargs), self._observer)


def _observer_receipt(
    receipts: list[dict[str, Any]],
    *,
    invalid_envelopes: int,
    parent_fetch_calls: int,
    parent_helper_results: int,
) -> dict[str, Any]:
    checked = [validate_detail_receipt(value) for value in receipts]
    signatures = dict(sorted(Counter(detail_stage_signature(row) for row in checked).items()))
    bits = [_stage_bits(row) for row in checked]
    sums = {name: sum(int(row[name]) for row in checked) for name in _SUM_FIELDS}
    page_counts = {
        name: sum(row[index] for row in bits)
        for index, name in enumerate(_PAGE_COUNT_FIELDS)
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_fetch_calls_snapshot": int(parent_fetch_calls),
        "parent_helper_result_count": int(parent_helper_results),
        "observed_detail_receipt_count": len(checked),
        "invalid_observer_envelope_count": int(invalid_envelopes),
        **sums,
        **page_counts,
        "stage_signature_counts": signatures,
        "parent_fetch_return_value_or_parent_projection_receipt_mutated": False,
        "url_title_page_question_field_label_value_record_prediction_task_identifier_or_credential_retained": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_network_search_fetch_model_token_byte_context_retry_process_or_wall_cap": False,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_observer_receipt(value)


def validate_observer_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    signatures = copied.get("stage_signature_counts")
    counts = (
        "parent_fetch_calls_snapshot",
        "parent_helper_result_count",
        "observed_detail_receipt_count",
        "invalid_observer_envelope_count",
        *_SUM_FIELDS,
        *_PAGE_COUNT_FIELDS,
    )
    false_flags = (
        "parent_fetch_return_value_or_parent_projection_receipt_mutated",
        "url_title_page_question_field_label_value_record_prediction_task_identifier_or_credential_retained",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_network_search_fetch_model_token_byte_context_retry_process_or_wall_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    signature_page_counts = {name: 0 for name in _PAGE_COUNT_FIELDS}
    signature_chain_valid = True
    if isinstance(signatures, Mapping):
        for signature, amount in signatures.items():
            if (
                not isinstance(signature, str)
                or _SIGNATURE.fullmatch(signature) is None
                or isinstance(amount, bool)
                or not isinstance(amount, int)
                or amount <= 0
            ):
                signature_chain_valid = False
                continue
            bits = tuple(int(signature[index]) for index in (1, 3, 5, 7, 9, 11, 13))
            if bits[5] and not all(bits[:5]) or bits[6] and not bits[5]:
                signature_chain_valid = False
            for name, bit in zip(_PAGE_COUNT_FIELDS, bits, strict=True):
                signature_page_counts[name] += bit * amount
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        "stage_signature_counts",
        *false_flags,
        "entropy_information_gain_shadow_only",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or not isinstance(signatures, Mapping)
        or any(
            not isinstance(name, str)
            or _SIGNATURE.fullmatch(name) is None
            or isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
            for name, amount in signatures.items()
        )
        or not signature_chain_valid
        or sum(signatures.values()) != copied["observed_detail_receipt_count"]
        or any(
            copied[name] != signature_page_counts[name]
            for name in _PAGE_COUNT_FIELDS
        )
        or copied["input_page_count"] != copied["observed_detail_receipt_count"]
        or copied["observed_detail_receipt_count"] > copied["parent_helper_result_count"]
        or copied["parent_helper_result_count"] > copied["parent_fetch_calls_snapshot"]
        or any(
            copied[name] > copied["observed_detail_receipt_count"]
            for name in _PAGE_COUNT_FIELDS
        )
        or copied["positive_signed_credit_count"] != 0
        or copied["identity_url_path_match_count"]
        != copied["identity_url_path_bound_page_count"]
        or copied["authority_url_token_match_count"]
        != copied["authority_url_token_bound_page_count"]
        or copied["identity_page_surface_match_count"]
        != copied["identity_page_surface_bound_page_count"]
        or copied["discovered_record_count"]
        != copied["discovered_record_page_count"]
        or copied["retained_record_count"] != copied["retained_record_page_count"]
        or copied["retained_record_page_count"]
        > copied["discovered_record_page_count"]
        or copied["discovered_record_page_count"]
        > copied["all_target_fields_unique_page_count"]
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("entropy_information_gain_shadow_only") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.09 detail-stage observer receipt drifted")
    return copied


class DetailStageObservedSearchClient(DetailFieldLatePageBoundSearchClient):
    """V2.50.05-equivalent fetch plus an in-memory counts-only observer."""

    def __init__(
        self,
        *args: Any,
        detail_stage_observer_helper: Path = HELPER,
        detail_stage_observer_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        self._v25009_observer = _CountsObserver()
        adapter = _ObservedPopen(
            self._v25009_observer,
            helper=detail_stage_observer_helper,
            popen=detail_stage_observer_popen,
        )
        if "late_page_fetch_popen" in kwargs:
            raise ValueError("V2.50.09 owns the transparent helper adapter")
        super().__init__(*args, late_page_fetch_popen=adapter, **kwargs)

    def detail_stage_observer_receipt(self) -> dict[str, Any]:
        receipts, invalid = self._v25009_observer.snapshot()
        parent = self.late_page_projection_receipt()
        return _observer_receipt(
            receipts,
            invalid_envelopes=invalid,
            parent_fetch_calls=int(parent["fetch_calls_snapshot"]),
            parent_helper_results=int(parent["helper_result_count"]),
        )


def validate_search_class() -> None:
    validate_parent_search_class()
    owner = next(
        base for base in DetailStageObservedSearchClient.__mro__ if "_fetch_url" in base.__dict__
    )
    if (
        owner is not LatePageBoundFetchMixin
        or not issubclass(DetailStageObservedSearchClient, DetailFieldLatePageBoundSearchClient)
        or _ordinary_helper() != HELPER.resolve()
    ):
        raise RuntimeError("V2.50.09 observer search binding drifted")


__all__ = [
    "DetailStageObservedSearchClient",
    "HELPER",
    "HELPER_ROLE",
    "POLICY_ID",
    "ROLE",
    "build_helper_envelope",
    "detail_stage_signature",
    "validate_helper_envelope",
    "validate_observer_receipt",
    "validate_search_class",
]
