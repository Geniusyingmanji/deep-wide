"""Hard-deadline fetch bridge for V2.49.80 late-page projection.

The inherited helper already reads at most three million response bytes but
truncates decoded text to 5,000 characters before returning it.  This bridge
keeps that network-byte cap, fetch count, hard deadline, and 5k parent output
cap unchanged.  Its isolated helper applies the pure V2.49.80 projector after
decode/HTML extraction and before the inherited prefix boundary.

The visible question is injected by the caller and sent only to the helper for
the current fetch.  It is never read from the environment or persisted.  The
client retains content-free projection counters only.
"""

from __future__ import annotations

import copy
import json
import math
import os
import subprocess
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .v24263_global_model_limiter import payload_sha256
from .clients import canonicalize_url
from .v24287_hard_deadline_fetch import validate_fetch_result
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
    validate_thin_search_class,
)
from .v24980_late_page_bound_projection import (
    MAXIMUM_INPUT_PAGE_CHARACTERS,
    PAGE_CHARACTER_CAP,
    validate_receipt as validate_projection_receipt,
)


POLICY_ID = "v24981_hard_deadline_late_page_bound_fetch_v1"
ROLE = "v24981_content_free_late_page_fetch_receipt"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v24981_late_page_fetch_helper.py"
HELPER_RESULT_KEYS = frozenset(
    {
        "status",
        "url",
        "title",
        "text",
        "links",
        "projection_receipt",
        "parent_prefix",
    }
)

_AGGREGATE_COUNTS = (
    "fetch_calls_snapshot",
    "fetch_failures_snapshot",
    "helper_result_count",
    "projected_page_count",
    "mechanism_engaged_page_count",
    "exact_parent_prefix_handoff_page_count",
    "candidate_evidence_changed_page_count",
    "projection_failure_count",
    "input_content_characters",
    "input_characters_beyond_parent_prefix",
    "discovered_record_count",
    "admissible_record_count",
    "admissible_bound_observation_count",
    "retained_record_count",
    "retained_bound_observation_count",
    "compact_prefix_characters",
    "raw_prefix_characters_retained",
    "output_characters",
    "positive_signed_credit_count",
)


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = (ROOT / "scripts/run_v24981_late_page_fetch_helper.py").resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.49.81 helper identity drifted")
    return resolved


def _failure(status: str) -> dict[str, Any]:
    return {"status": status, "url": "", "title": "", "text": "", "links": []}


def validate_helper_result(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != HELPER_RESULT_KEYS:
        raise ValueError("V2.49.81 helper result schema drifted")
    copied = copy.deepcopy(dict(value))
    stripped = {
        name: copied[name]
        for name in value
        if name not in {"projection_receipt", "parent_prefix"}
    }
    checked = validate_fetch_result(stripped)
    receipt = copied.get("projection_receipt")
    if checked["status"] == "ok":
        if not isinstance(receipt, Mapping):
            raise ValueError("V2.49.81 successful helper omitted projection receipt")
        validated = validate_projection_receipt(receipt)
        parent_prefix = copied.get("parent_prefix")
        if (
            validated["output_characters"] != len(checked["text"])
            or len(checked["text"]) > PAGE_CHARACTER_CAP
            or not isinstance(parent_prefix, str)
            or not parent_prefix
            or len(parent_prefix) > PAGE_CHARACTER_CAP
        ):
            raise ValueError("V2.49.81 helper text/receipt binding drifted")
        copied["projection_receipt"] = validated
    elif receipt is not None or copied.get("parent_prefix") is not None:
        raise ValueError("V2.49.81 failed fetch retained projection receipt")
    return copied


class LatePageBoundFetchMixin:
    """Replace only the inherited helper boundary, not any effect budget."""

    def __init__(
        self,
        *args: Any,
        visible_question: str,
        late_page_fetch_helper: Path = HELPER,
        late_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if not isinstance(visible_question, str) or not visible_question.strip():
            raise ValueError("V2.49.81 visible question is absent")
        if (
            isinstance(self.max_page_chars, bool)
            or int(self.max_page_chars) != PAGE_CHARACTER_CAP
        ):
            raise ValueError("V2.49.81 parent page cap drifted")
        self._v24981_visible_question = visible_question.strip()
        self._v24981_fetch_helper = _ordinary_helper(late_page_fetch_helper)
        self._v24981_fetch_popen = late_page_fetch_popen
        self._v24981_projection_receipts: list[dict[str, Any]] = []
        self._v24981_parent_prefixes: dict[str, str] = {}
        self._v24981_helper_result_count = 0
        self._v24981_receipt_lock = threading.Lock()

    def _fetch_url(self, url: str) -> dict[str, Any]:
        self._stage_callback("public_fetch_effect_started")
        try:
            return self._fetch_url_late_page_bound(url)
        finally:
            self._stage_callback("public_fetch_effect_finished")

    def _fetch_url_late_page_bound(self, url: str) -> dict[str, Any]:
        self._increment("fetch_calls")
        remaining = self.remaining_effect_seconds()
        if remaining < self.minimum_attempt_seconds:
            self._increment("fetch_failures")
            self._increment("fetch_deadline_rejections")
            return _failure("task_deadline_exhausted")
        self._increment("hard_fetch_helper_calls")
        process = self._v24981_fetch_popen(
            [
                self.fetch_python_executable,
                "-I",
                "-B",
                str(self._v24981_fetch_helper),
            ],
            cwd=self._v24981_fetch_helper.parents[1],
            env={
                "HOME": os.environ.get("HOME", str(Path.home())),
                "USER": os.environ.get("USER", "azureuser"),
                "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
        remaining_after_launch = self.remaining_effect_seconds()
        if remaining_after_launch < self.minimum_attempt_seconds:
            self._terminate_group(process)
            self._increment("fetch_failures")
            self._increment("hard_fetch_deadline_failures")
            return _failure("task_deadline_exhausted_after_helper_launch")
        try:
            stdout, _ = process.communicate(
                json.dumps(
                    {
                        "url": str(url),
                        "question": self._v24981_visible_question,
                    },
                    ensure_ascii=False,
                ),
                timeout=min(
                    float(self.hard_fetch_deadline_seconds),
                    remaining_after_launch,
                ),
            )
        except subprocess.TimeoutExpired:
            self._terminate_group(process)
            self._increment("fetch_failures")
            self._increment("hard_fetch_deadline_failures")
            return _failure("hard_deadline_exceeded")
        if process.returncode != 0:
            self._increment("fetch_failures")
            self._increment("fetch_helper_failures")
            return _failure("helper_nonzero_exit")
        try:
            result = validate_helper_result(json.loads(stdout))
        except (json.JSONDecodeError, TypeError, ValueError):
            self._increment("fetch_failures")
            self._increment("fetch_helper_failures")
            return _failure("helper_invalid_result")
        with self._v24981_receipt_lock:
            self._v24981_helper_result_count += 1
            receipt = result.get("projection_receipt")
            if isinstance(receipt, Mapping):
                self._v24981_projection_receipts.append(copy.deepcopy(dict(receipt)))
                prefix = str(result.get("parent_prefix") or "")
                aliases = {
                    canonicalize_url(str(url)),
                    canonicalize_url(str(result.get("url") or "")),
                } - {""}
                for alias in aliases:
                    previous = self._v24981_parent_prefixes.get(alias)
                    if previous is not None and previous != prefix:
                        self._increment("fetch_failures")
                        self._increment("fetch_helper_failures")
                        return _failure("shadow_prefix_identity_conflict")
                    self._v24981_parent_prefixes[alias] = prefix
        if result["status"] != "ok":
            self._increment("fetch_failures")
        return {
            name: copy.deepcopy(result[name])
            for name in ("status", "url", "title", "text", "links")
        }

    def parent_prefix_for(self, url: str) -> str:
        canonical = canonicalize_url(str(url))
        if not canonical:
            return ""
        with self._v24981_receipt_lock:
            return str(self._v24981_parent_prefixes.get(canonical) or "")

    def late_page_projection_receipt(self) -> dict[str, Any]:
        with self._v24981_receipt_lock:
            receipts = [
                validate_projection_receipt(value)
                for value in copy.deepcopy(self._v24981_projection_receipts)
            ]
            helper_results = int(self._v24981_helper_result_count)
        sums = {
            name: sum(int(receipt[name]) for receipt in receipts)
            for name in (
                "projection_failure_count",
                "input_content_characters",
                "input_characters_beyond_parent_prefix",
                "discovered_record_count",
                "admissible_record_count",
                "admissible_bound_observation_count",
                "retained_record_count",
                "retained_bound_observation_count",
                "compact_prefix_characters",
                "raw_prefix_characters_retained",
                "output_characters",
                "positive_signed_credit_count",
            )
        }
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": ROLE,
            "policy_id": POLICY_ID,
            "fetch_calls_snapshot": int(self.fetch_calls),
            "fetch_failures_snapshot": int(self.fetch_failures),
            "helper_result_count": helper_results,
            "projected_page_count": len(receipts),
            "mechanism_engaged_page_count": sum(
                receipt["mechanism_engaged"] is True for receipt in receipts
            ),
            "exact_parent_prefix_handoff_page_count": sum(
                receipt["exact_parent_prefix_handoff"] is True for receipt in receipts
            ),
            "candidate_evidence_changed_page_count": sum(
                receipt["candidate_evidence_changed"] is True for receipt in receipts
            ),
            **sums,
            "maximum_network_response_bytes_per_fetch": 3_000_000,
            "parent_page_character_cap": PAGE_CHARACTER_CAP,
            "visible_question_read_from_environment_file_or_benchmark_metadata": False,
            "question_url_title_page_record_value_prediction_answer_hash_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_receipt(value)


class LatePageBoundSearchClient(
    LatePageBoundFetchMixin,
    ThinSameResponseCitationTitleBackfillSearchClient,
):
    """Frozen keyless search with only the fetch projection seam replaced."""


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_AGGREGATE_COUNTS,
        "maximum_network_response_bytes_per_fetch",
        "parent_page_character_cap",
        "visible_question_read_from_environment_file_or_benchmark_metadata",
        "question_url_title_page_record_value_prediction_answer_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    false_flags = (
        "visible_question_read_from_environment_file_or_benchmark_metadata",
        "question_url_title_page_record_value_prediction_answer_hash_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _AGGREGATE_COUNTS
        )
        or copied["projected_page_count"] > copied["helper_result_count"]
        or copied["mechanism_engaged_page_count"]
        > copied["projected_page_count"]
        or copied["exact_parent_prefix_handoff_page_count"]
        + copied["candidate_evidence_changed_page_count"]
        != copied["projected_page_count"]
        or copied["mechanism_engaged_page_count"]
        > copied["candidate_evidence_changed_page_count"]
        or copied["retained_record_count"] > copied["admissible_record_count"]
        or copied["retained_bound_observation_count"]
        > copied["admissible_bound_observation_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied.get("maximum_network_response_bytes_per_fetch")
        != MAXIMUM_INPUT_PAGE_CHARACTERS
        or copied.get("parent_page_character_cap") != PAGE_CHARACTER_CAP
        or copied.get("entropy_information_gain_shadow_only") is not True
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.81 late-page fetch receipt drifted")
    return copied


def validate_search_class() -> None:
    validate_thin_search_class()
    cls = LatePageBoundSearchClient
    fetch_owner = next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__)
    if (
        fetch_owner is not LatePageBoundFetchMixin
        or not issubclass(cls, ThinSameResponseCitationTitleBackfillSearchClient)
    ):
        raise RuntimeError("V2.49.81 search MRO drifted")


def validate_policy() -> dict[str, Any]:
    value = {
        "policy_id": POLICY_ID,
        "maximum_network_response_bytes_per_fetch": MAXIMUM_INPUT_PAGE_CHARACTERS,
        "parent_page_character_cap": PAGE_CHARACTER_CAP,
        "same_inherited_fetch_count_and_hard_deadline": True,
        "projection_after_decode_before_parent_prefix": True,
        "additional_search_fetch_model_token_context_wall_or_network_byte_cap": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    if (
        value["maximum_network_response_bytes_per_fetch"] != 3_000_000
        or value["parent_page_character_cap"] != 5_000
        or value[
            "additional_search_fetch_model_token_context_wall_or_network_byte_cap"
        ]
        is not False
    ):
        raise RuntimeError("V2.49.81 fetch policy drifted")
    return value


__all__ = [
    "HELPER",
    "LatePageBoundFetchMixin",
    "LatePageBoundSearchClient",
    "POLICY_ID",
    "ROLE",
    "validate_helper_result",
    "validate_policy",
    "validate_receipt",
    "validate_search_class",
]
